"""KAVACH API: scan text and documents, and mask PII in AI chat requests."""

import ipaddress
import json
import logging
import math
import os
import re
import secrets
import threading
import time
from collections import deque
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from pypdf import Configuration, PdfReader
from pypdf._configuration import CURRENT_CONFIGURATION

from kavach import analyze
from kavach.global_detector import analyze_global, preload_analyzer
from kavach.agent import (
    AGENT_ENABLED,
    OLLAMA_MODEL,
    OLLAMA_URL,
    review_findings,
    validate_ollama_url,
)
from kavach.audit import database_status, list_recent_runs, record_run

# --------------------------------------------------
# Configuration
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kavach")

UPSTREAM = os.getenv(
    "UPSTREAM_BASE_URL",
    "https://api.openai.com/v1",
).rstrip("/")

BLOCK_HIGH = os.getenv("KAVACH_BLOCK_HIGH", "0") == "1"

ALLOWED_UPSTREAM_HOSTS = {
    host.strip().lower()
    for host in os.getenv(
        "KAVACH_ALLOWED_UPSTREAM_HOSTS",
        "api.openai.com",
    ).split(",")
    if host.strip()
}

ALLOW_LOCAL_UPSTREAM = (
    os.getenv("KAVACH_ALLOW_LOCAL_UPSTREAM", "0") == "1"
)

ALLOWED_HOSTS = [
    host.strip().lower()
    for host in os.getenv(
        "KAVACH_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

OWNER_ACCESS_MODE = os.getenv("KAVACH_OWNER_ACCESS_MODE", "local").strip().lower()
if OWNER_ACCESS_MODE not in {"local", "token"}:
    raise RuntimeError(
        "KAVACH_OWNER_ACCESS_MODE must be either 'local' or 'token'."
    )

STATIC = Path(__file__).parent / "static"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SCAN_REQUEST_BODY_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
MAX_PDF_PAGES = 20

MAX_CHAT_BODY_BYTES = 1 * 1024 * 1024
MAX_CHAT_MESSAGES = 100
MAX_CHAT_TEXT_CHARS = 20000

MAX_UPSTREAM_RESPONSE_BYTES = 5 * 1024 * 1024
UPSTREAM_TIMEOUT = 60


def _rate_limit_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        configured_value = int(raw_value)
        if 1 <= configured_value <= 1000:
            return configured_value
    except ValueError:
        pass
    logger.warning("Ignoring invalid %s configuration; using the default.", name)
    return default


RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMITS = {
    "/api/scan": _rate_limit_from_env("KAVACH_RATE_LIMIT_SCAN_PER_MINUTE", 30),
    "/api/scan-file": _rate_limit_from_env("KAVACH_RATE_LIMIT_SCAN_FILE_PER_MINUTE", 10),
    "/v1/chat/completions": _rate_limit_from_env("KAVACH_RATE_LIMIT_CHAT_PER_MINUTE", 20),
}
RATE_LIMIT_LOCK = threading.Lock()

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; font-src 'self' data:; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; "
    "frame-src 'none'; frame-ancestors 'none'"
)

# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="KAVACH",
    description="India-aware PII guardrail for AI tools",
    version="1.2.4",
)

# A configured token remains stable across restarts.
# Otherwise, generate a random token for this server process.
_configured_api_token = os.getenv("KAVACH_API_TOKEN", "").strip()
if OWNER_ACCESS_MODE == "token" and len(_configured_api_token) < 40:
    raise RuntimeError(
        "KAVACH_API_TOKEN must contain at least 40 characters when "
        "KAVACH_OWNER_ACCESS_MODE is 'token'."
    )
API_TOKEN = _configured_api_token or secrets.token_urlsafe(32)
app.state.api_token = API_TOKEN
app.state.owner_access_mode = OWNER_ACCESS_MODE
app.state.rate_limit_events = {}

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
)

app.mount(
    "/static",
    StaticFiles(directory=STATIC),
    name="static",
)

# --------------------------------------------------
# Owner API access and browser write protection
# --------------------------------------------------

def _origin_matches_request(origin: str, request: Request) -> bool:
    """Accept only origins matching the current request's origin."""
    try:
        parsed = urlsplit(origin)

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            return False

        return (
            parsed.scheme.lower() == request.url.scheme.lower()
            and parsed.hostname.lower()
            == (request.url.hostname or "").lower()
            and parsed.port == request.url.port
        )
    except ValueError:
        return False


def _secure_response_headers(response, request: Request):
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/") or request.url.path == "/v1/chat/completions":
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


def _rate_limit_allowed(request: Request, now: float | None = None) -> bool:
    """Apply a process-local per-route, per-client-IP rolling-window limit."""
    limit = RATE_LIMITS.get(request.url.path)
    if limit is None:
        return True

    client_host = request.client.host if request.client else "unknown"
    bucket_key = (request.url.path, client_host)
    if now is None:
        now = time.monotonic()
    with RATE_LIMIT_LOCK:
        events = request.app.state.rate_limit_events
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        for key, timestamps in list(events.items()):
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if not timestamps:
                del events[key]
        timestamps = events.setdefault(bucket_key, deque())
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
        if len(timestamps) >= limit:
            return False
        timestamps.append(now)
        return True


def _request_client_is_loopback(request: Request) -> bool:
    """Trust only the direct ASGI peer address, never forwarding headers."""
    client = request.client
    if client is None:
        return False
    try:
        address = ipaddress.ip_address(client.host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_loopback


@app.middleware("http")
async def enforce_same_origin_for_writes(request: Request, call_next):
    """Enforce owner API access and same-origin writes."""

    protected_api_path = (
        request.url.path.startswith("/api/")
        or request.url.path == "/v1/chat/completions"
    )

    if protected_api_path:
        if (
            request.app.state.owner_access_mode == "local"
            and not _request_client_is_loopback(request)
        ):
            return _secure_response_headers(JSONResponse(
                status_code=403,
                content={"detail": "Owner APIs are available only from this device."},
            ), request)

        if request.app.state.owner_access_mode == "token":
            supplied_token = request.headers.get("x-kavach-token", "")
            expected_token = request.app.state.api_token
            if not secrets.compare_digest(supplied_token, expected_token):
                return _secure_response_headers(JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing KAVACH API token."},
                ), request)

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")

        # Origin checks supplement owner access controls; they do not authorize access.
        if origin and not _origin_matches_request(origin, request):
            return _secure_response_headers(JSONResponse(
                status_code=403,
                content={"detail": "Cross-origin requests are not allowed."},
            ), request)

    if request.method == "POST" and not _rate_limit_allowed(request):
        response = JSONResponse(
            status_code=429,
            content={"detail": "Request limit reached. Please wait before trying again."},
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
        )
        return _secure_response_headers(response, request)

    if request.method == "POST" and request.url.path == "/api/scan-file":
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError:
                return _secure_response_headers(JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."}), request)
            if declared_length < 0:
                return _secure_response_headers(JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."}), request)
            if declared_length > MAX_SCAN_REQUEST_BODY_BYTES:
                return _secure_response_headers(JSONResponse(status_code=413, content={"detail": "Upload request is too large."}), request)

        # Bound the raw multipart body before Starlette parses/spools the upload.
        chunks = []
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > MAX_SCAN_REQUEST_BODY_BYTES:
                return _secure_response_headers(JSONResponse(status_code=413, content={"detail": "Upload request is too large."}), request)
            chunks.append(chunk)
        request._body = b"".join(chunks)

    response = await call_next(request)
    return _secure_response_headers(response, request)


# --------------------------------------------------
# Upstream URL validation
# --------------------------------------------------

def validate_upstream_url():
    """
    Permit explicitly allowlisted HTTPS providers,
    or the explicitly enabled local mock on 127.0.0.1:8001.

    Hostname allowlisting is not complete SSRF protection.
    Production deployments should also enforce network egress rules.
    """
    try:
        if not UPSTREAM or any(
            char.isspace() or ord(char) < 32
            for char in UPSTREAM
        ):
            raise ValueError("Invalid URL characters")

        parsed = urlsplit(UPSTREAM)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port

        if not hostname:
            raise ValueError("Missing hostname")

        hostname = hostname.lower()

        if (
            parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/", "/v1"}
        ):
            raise ValueError("Unsupported URL components")

        if "\\" in UPSTREAM or hostname.endswith("."):
            raise ValueError("Unsupported hostname format")

        if not hostname.isascii():
            raise ValueError("Hostname must be ASCII")

        # IP literals are forbidden except for the local mock.
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            ip = None

        if ip is not None and hostname != "127.0.0.1":
            raise ValueError("IP destinations are not permitted")

        if hostname == "127.0.0.1":
            if not ALLOW_LOCAL_UPSTREAM:
                raise ValueError("Local upstream is disabled")

            if scheme != "http" or port != 8001:
                raise ValueError("Invalid local mock destination")

            if parsed.path not in {"", "/", "/v1"}:
                raise ValueError("Invalid local mock API path")

        else:
            # Validate DNS hostname syntax.
            labels = hostname.split(".")
            if (
                len(hostname) > 253
                or len(labels) < 2
                or any(
                    not label
                    or len(label) > 63
                    or not re.fullmatch(
                        r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?",
                        label,
                    )
                    for label in labels
                )
            ):
                raise ValueError("Invalid hostname")

            # Exact hostname allowlist: no wildcard matching.
            if hostname not in ALLOWED_UPSTREAM_HOSTS:
                raise ValueError("Hostname is not allowlisted")

            if scheme != "https" or port not in (None, 443):
                raise ValueError("Invalid public scheme or port")

        if scheme not in {"http", "https"}:
            raise ValueError("Unsupported URL scheme")

    except (ValueError, UnicodeError):
        raise HTTPException(
            status_code=500,
            detail="Invalid or disallowed upstream API URL configuration.",
        )

    return f"{UPSTREAM}/chat/completions"


def configured_upstream_hostname():
    """Return the configured hostname for diagnostic logging."""
    try:
        return urlsplit(UPSTREAM).hostname or "(missing)"
    except ValueError:
        return "(invalid URL)"


@app.on_event("startup")
async def report_upstream_configuration():
    """Log owner access mode and upstream configuration status."""
    if OWNER_ACCESS_MODE == "local":
        logger.warning(
            "Owner APIs are restricted to loopback clients; remote deployment "
            "requires KAVACH_OWNER_ACCESS_MODE=token and a configured token."
        )
    else:
        logger.info("Owner APIs require the configured KAVACH_API_TOKEN.")

    try:
        preload_ms = preload_analyzer()
        logger.info(
            "KAVACH startup: Presidio analyzer ready in %.2f ms",
            preload_ms,
        )
    except Exception as exc:
        logger.warning(
            "KAVACH startup: Presidio analyzer preload failed (%s); "
            "global detection will use its existing fallback behavior.",
            type(exc).__name__,
        )

    host = configured_upstream_hostname()

    try:
        validate_upstream_url()
        logger.info(
            "KAVACH startup: upstream host=%s; validation=allowed",
            host,
        )
    except HTTPException:
        logger.warning(
            "KAVACH startup: upstream host=%s; validation=REJECTED",
            host,
        )


# --------------------------------------------------
# Homepage and health
# --------------------------------------------------

@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    ollama = {"status": "disabled", "model_available": None}
    if AGENT_ENABLED:
        try:
            configured_url = urlsplit(validate_ollama_url(OLLAMA_URL))
            tags_url = f"{configured_url.scheme}://{configured_url.netloc}/api/tags"
            response = httpx.get(
                tags_url,
                timeout=0.5,
                trust_env=False,
                follow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
            models = payload.get("models", []) if isinstance(payload, dict) else []
            available_models = {
                item.get("name") for item in models
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            } if isinstance(models, list) else set()
            ollama = {
                "status": "available",
                "model_available": OLLAMA_MODEL in available_models,
            }
        except Exception:
            ollama = {"status": "unavailable", "model_available": False}

    return {
        "status": "ok",
        "version": "1.2.4",
        "database": database_status(),
        "ollama": ollama,
    }


@app.get("/healthz")
def public_health():
    """Minimal public liveness response with no owner diagnostics."""
    return {"status": "ok"}


# --------------------------------------------------
# Scan pasted text
# --------------------------------------------------

class ScanIn(BaseModel):
    text: str = Field(max_length=20000)
    mode: str = Field(default="label", pattern="^(label|partial)$")


def _finish_scan_performance(
    result: dict,
    started: float,
    ollama_review_ms: float | None = None,
) -> None:
    performance = result.setdefault("performance", {})
    performance.setdefault("native_detection_ms", 0.0)
    performance.setdefault("presidio_initialization_ms", None)
    performance.setdefault("presidio_detection_ms", None)
    performance.setdefault("global_detection_ms", None)
    if ollama_review_ms is not None or "ollama_review_ms" not in performance:
        performance["ollama_review_ms"] = (
            round(ollama_review_ms, 2)
            if ollama_review_ms is not None
            else None
        )
    performance["total_backend_processing_ms"] = round(
        (time.perf_counter() - started) * 1000,
        2,
    )


@app.post("/api/scan")
def scan_text(body: ScanIn):
    started = time.perf_counter()
    result = analyze(body.text, body.mode)

    ollama_review_ms = None
    if AGENT_ENABLED:
        review_started = time.perf_counter()
        result["agent_review"] = review_findings(
            body.text,
            result["findings"],
        )
        ollama_review_ms = (time.perf_counter() - review_started) * 1000

    _finish_scan_performance(result, started, ollama_review_ms)
    return result


@app.post("/api/scan-global")
def scan_global_text(body: ScanIn):
    started = time.perf_counter()
    result = analyze_global(body.text, body.mode)
    _finish_scan_performance(result, started)
    return result


@app.post("/api/agentic/scan")
def scan_agentic(body: ScanIn):
    started = time.perf_counter()
    # Both Protect modes use this exact deterministic detector/masking pass.
    # The local analyst receives a copy of finding metadata and can only add
    # advisory review data; it cannot change the result returned to the user.
    result = analyze_global(body.text, body.mode)
    findings = result.get("findings", [])
    if not isinstance(findings, list):
        findings = []

    review_started = time.perf_counter()
    try:
        agent_review = review_findings(
            body.text,
            [dict(item) for item in findings if isinstance(item, dict)],
        )
        if not isinstance(agent_review, dict):
            agent_review = {"status": "unavailable", "reviews": []}
    except Exception:
        agent_review = {"status": "unavailable", "reviews": []}
    ollama_review_ms = (time.perf_counter() - review_started) * 1000

    _finish_scan_performance(result, started, ollama_review_ms)
    global_detection = result.get("global_detection")
    global_detection_status = (
        global_detection.get("status", "unavailable")
        if isinstance(global_detection, dict)
        else "unavailable"
    )
    verification_status = "not_run"
    requires_human_review = (
        global_detection_status != "ok"
        or verification_status != "passed"
    )
    result.update({
        "workflow": "KAVACH Autonomous Privacy Workflow",
        "status": "completed",
        "agent_enabled": AGENT_ENABLED,
        "agent_review": agent_review,
        "agent_execution": {
            "status": agent_review.get("status", "unavailable"),
            "tool_calls": [],
            "fallback_used": False,
            "review_reason_codes": [],
        },
        "verification": {"status": verification_status},
        "requires_human_review": requires_human_review,
        "steps": [
            {
                "name": "global_scan",
                "status": global_detection_status,
                "findings_count": len(findings),
            },
            {
                "name": "ai_privacy_review",
                "status": str(agent_review.get("status", "unavailable")),
            },
        ],
    })

    audit = {"status": "unavailable"}
    audit_started = time.perf_counter()
    try:
        audit["run_id"] = record_run(
            workflow_name="global_privacy_workflow",
            status="completed",
            source="api",
            mode=body.mode,
            findings=findings,
            risk=result.get("risk", {}),
            agent_review=agent_review,
            verification_status=verification_status,
            requires_human_review=requires_human_review,
            steps=[
                {
                    "name": "global_scan",
                    "status": global_detection_status,
                    "findings_count": len(findings),
                },
                {
                    "name": "ai_privacy_review",
                    "status": str(agent_review.get("status", "unavailable")),
                },
            ],
        )
        audit["status"] = "saved"
    except Exception as exc:
        audit["reason"] = type(exc).__name__
    result.setdefault("performance", {})["audit_write_ms"] = round(
        (time.perf_counter() - audit_started) * 1000,
        2,
    )
    result["audit"] = audit
    return result


@app.get("/api/agentic/history")
def agentic_history(limit: int = Query(default=20, ge=1, le=100)):
    """Return bounded workflow metadata without prompt contents."""
    return {"runs": list_recent_runs(limit)}


# --------------------------------------------------
# Scan TXT and PDF documents
# --------------------------------------------------

@app.post("/api/scan-file")
async def scan_file(file: UploadFile = File(...)):
    started = time.perf_counter()
    filename = Path(file.filename or "uploaded_file").name
    extension = Path(filename).suffix.lower()

    try:
        if extension not in {".txt", ".pdf"}:
            raise HTTPException(
                status_code=415,
                detail="Only TXT and PDF files are supported.",
            )

        content = await file.read(MAX_UPLOAD_BYTES + 1)

        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File is too large. Maximum size is 5 MB.",
            )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The file is empty.",
            )

        page_count = None

        if extension == ".txt":
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="The TXT file must use UTF-8 text encoding.",
                )

        else:
            if b"%PDF-" not in content[:1024]:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file does not appear to be a valid PDF.",
                )

            try:
                # These pypdf limits are scoped to this synchronous parse/extraction
                # so concurrent requests do not change one another's settings.
                pdf_configuration = Configuration(
                    maximum_declared_stream_length=MAX_UPLOAD_BYTES,
                    array_based_stream_maximum_output_length=20 * 1024 * 1024,
                    array_maximum_element_count=20_000,
                    dictionary_maximum_element_count=20_000,
                    jbig2_maximum_output_length=20 * 1024 * 1024,
                    lzw_maximum_output_length=20 * 1024 * 1024,
                    run_length_maximum_output_length=20 * 1024 * 1024,
                    zlib_maximum_output_length=20 * 1024 * 1024,
                    brotli_maximum_output_length=20 * 1024 * 1024,
                    stream_filters_maximum_length=8,
                    stream_decoding_work_maximum_length=40 * 1024 * 1024,
                    stream_parsing_work_maximum_count=500_000,
                    page_tree_maximum_entries=1_000,
                    page_tree_maximum_depth=40,
                    xform_maximum_invocations_per_extraction=1_000,
                )
                config_token = CURRENT_CONFIGURATION.set(pdf_configuration)
                try:
                    reader = PdfReader(
                        BytesIO(content),
                        strict=False,
                        root_object_recovery_limit=1_000,
                    )

                    if reader.is_encrypted:
                        raise HTTPException(
                            status_code=400,
                            detail="Password-protected PDFs are not supported.",
                        )

                    page_count = len(reader.pages)

                    if page_count > MAX_PDF_PAGES:
                        raise HTTPException(
                            status_code=413,
                            detail="PDFs are limited to 20 pages.",
                        )

                    text = "\n".join(
                        page.extract_text() or ""
                        for page in reader.pages
                    )
                finally:
                    CURRENT_CONFIGURATION.reset(config_token)

            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Could not read this PDF. Try a valid, text-based PDF.",
                )

        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="No readable text found. Scanned-image PDFs need OCR.",
            )

        result = analyze_global(text, mode="label")
        performance = dict(result.get("performance", {}))
        performance["ollama_review_ms"] = None
        performance["total_backend_processing_ms"] = round(
            (time.perf_counter() - started) * 1000,
            2,
        )

        return {
            "filename": filename,
            "page_count": page_count,
            "findings": result.get("findings", []),
            "global_detection": result.get("global_detection", {}),
            "masked_text": result.get("masked_text", ""),
            "risk": result.get("risk", {}),
            "count": len(result.get("findings", [])),
            "performance": performance,
        }

    finally:
        await file.close()


# --------------------------------------------------
# Read chat body with a strict size limit
# --------------------------------------------------

async def read_limited_request_body(request: Request) -> bytes:
    content_length = request.headers.get("content-length")

    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid Content-Length header.",
            )

        if declared_length < 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid Content-Length header.",
            )

        if declared_length > MAX_CHAT_BODY_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Chat request is too large. Maximum size is 1 MB.",
            )

    body = bytearray()

    async for chunk in request.stream():
        body.extend(chunk)

        if len(body) > MAX_CHAT_BODY_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Chat request is too large. Maximum size is 1 MB.",
            )

    return bytes(body)


# --------------------------------------------------
# Validate and mask chat messages
# --------------------------------------------------

ALLOWED_CHAT_FIELDS = {
    "model",
    "messages",
    "temperature",
    "top_p",
    "n",
    "max_tokens",
    "max_completion_tokens",
    "presence_penalty",
    "frequency_penalty",
    "seed",
    "stream",
}

NUMERIC_CHAT_FIELDS = {
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
}

INTEGER_CHAT_FIELDS = {
    "n",
    "max_tokens",
    "max_completion_tokens",
    "seed",
}


def reject_duplicate_keys(pairs):
    """Reject ambiguous JSON objects containing duplicate keys."""
    result = {}

    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value

    return result


def reject_nonstandard_constant(value):
    """Reject NaN and Infinity in JSON input."""
    raise ValueError(f"Invalid JSON constant: {value}")


def validate_and_mask_chat_payload(payload: dict):
    unknown_fields = set(payload) - ALLOWED_CHAT_FIELDS

    if unknown_fields:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported chat request fields: "
                + ", ".join(sorted(unknown_fields))
            ),
        )

    model = payload.get("model")

    if (
        not isinstance(model, str)
        or not model.strip()
        or len(model) > 200
    ):
        raise HTTPException(
            status_code=400,
            detail="'model' must be a non-empty string of at most 200 characters.",
        )

    if "stream" in payload and not isinstance(payload["stream"], bool):
        raise HTTPException(
            status_code=400,
            detail="'stream' must be a boolean.",
        )

    if payload.get("stream") is True:
        raise HTTPException(
            status_code=422,
            detail="Streaming responses are not supported.",
        )

    for field in NUMERIC_CHAT_FIELDS:
        if field in payload:
            value = payload[field]

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or (isinstance(value, float) and not math.isfinite(value))
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"'{field}' must be a finite number.",
                )

    for field in INTEGER_CHAT_FIELDS:
        if field in payload:
            value = payload[field]

            if isinstance(value, bool) or not isinstance(value, int):
                raise HTTPException(
                    status_code=400,
                    detail=f"'{field}' must be an integer.",
                )

    messages = payload.get("messages")

    if not isinstance(messages, list):
        raise HTTPException(
            status_code=400,
            detail="'messages' must be a list.",
        )

    if not messages:
        raise HTTPException(
            status_code=400,
            detail="'messages' must not be empty.",
        )

    if len(messages) > MAX_CHAT_MESSAGES:
        raise HTTPException(
            status_code=413,
            detail="Too many chat messages. Maximum is 100.",
        )

    masked_messages = []
    redactions = 0
    worst = "none"
    risk_rank = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }

    for msg in messages:
        if not isinstance(msg, dict):
            raise HTTPException(
                status_code=400,
                detail="Every message must be a JSON object.",
            )

        if set(msg) != {"role", "content"}:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Each message must contain only 'role' and 'content'. "
                    "Tool calls and extra message fields are not supported."
                ),
            )

        role = msg["role"]

        if not isinstance(role, str) or role not in {
            "system",
            "user",
            "assistant",
        }:
            raise HTTPException(
                status_code=422,
                detail="Only system, user, and assistant roles are supported.",
            )

        content = msg["content"]

        if not isinstance(content, str):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Every chat message must have text-only string content. "
                    "Multimodal or non-string content is not supported."
                ),
            )

        if len(content) > MAX_CHAT_TEXT_CHARS:
            raise HTTPException(
                status_code=413,
                detail=(
                    "A chat message exceeds the maximum allowed length "
                    "of 20,000 characters."
                ),
            )

        result = analyze_global(content)
        findings = result.get("findings", [])
        redactions += len(findings)

        risk_data = result.get("risk", {})
        level = (
            risk_data.get("level", "none")
            if isinstance(risk_data, dict)
            else "none"
        )

        if level not in risk_rank:
            level = "none"

        if risk_rank[level] > risk_rank[worst]:
            worst = level

        masked_content = result.get("masked_text")

        if not isinstance(masked_content, str):
            raise HTTPException(
                status_code=500,
                detail="The scanner returned an invalid masking result.",
            )

        masked_messages.append({
            "role": role,
            "content": masked_content,
        })

    # Construct a fresh allowlisted payload.
    # Only the masked messages are forwarded upstream.
    masked_payload = {
        key: value
        for key, value in payload.items()
        if key in ALLOWED_CHAT_FIELDS and key != "messages"
    }

    masked_payload["messages"] = masked_messages
    masked_payload["stream"] = False

    return masked_payload, redactions, worst


# --------------------------------------------------
# AI chat proxy
# --------------------------------------------------

@app.post(
    "/v1/chat/completions",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "example": {
                            "model": "test-model",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "Hello, KAVACH!",
                                }
                            ],
                        },
                    },
                },
            },
        },
    },
)
async def chat_proxy(request: Request):
    # The middleware checks the KAVACH API token before this function runs.
    # Validate destination before reading or forwarding the body.
    upstream_url = validate_upstream_url()

    raw_body = await read_limited_request_body(request)

    if not raw_body:
        raise HTTPException(
            status_code=400,
            detail="The request body is empty.",
        )

    try:
        payload = json.loads(
            raw_body,
            parse_constant=reject_nonstandard_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        ValueError,
        RecursionError,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON request body.",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="The request body must be a JSON object.",
        )

    masked_payload, redactions, worst = validate_and_mask_chat_payload(
        payload
    )

    if BLOCK_HIGH and worst == "high":
        return JSONResponse(
            {
                "error": (
                    "Blocked: prompt contained high-risk personal data."
                )
            },
            status_code=422,
        )

    # This validates the upstream Bearer header format,
    # not whether the provider recognizes the credential.
    auth = request.headers.get("authorization")

    if (
        not auth
        or not auth.startswith("Bearer ")
        or not auth[7:].strip()
        or any(
            ord(char) < 32 or ord(char) == 127
            for char in auth
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="A valid Bearer Authorization header is required.",
        )

    try:
        async with httpx.AsyncClient(
            timeout=UPSTREAM_TIMEOUT,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            async with client.stream(
                "POST",
                upstream_url,
                json=masked_payload,
                headers={
                    "Authorization": auth,
                    "Content-Type": "application/json",
                },
            ) as upstream_response:
                response_body = bytearray()

                async for chunk in upstream_response.aiter_bytes():
                    response_body.extend(chunk)

                    if len(response_body) > MAX_UPSTREAM_RESPONSE_BYTES:
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                "The upstream response exceeded "
                                "the permitted size."
                            ),
                        )

                status_code = upstream_response.status_code

        try:
            response_data = json.loads(response_body)
        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            ValueError,
        ):
            response_data = {
                "error": "The upstream API returned invalid JSON."
            }

        return JSONResponse(
            content=response_data,
            status_code=status_code,
            headers={
                "X-Kavach-Redactions": str(redactions),
            },
        )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="The upstream AI service timed out.",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to the upstream AI service.",
        )
