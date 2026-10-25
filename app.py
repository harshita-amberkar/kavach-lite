
"""KAVACH API: scan text and documents, and mask PII in AI chat requests."""

import ipaddress
import json
import logging
import math
import os
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pypdf import PdfReader

from kavach import analyze
from kavach.global_detector import analyze_global
from kavach.agent import AGENT_ENABLED, review_findings
from kavach.agentic import run_agentic_workflow
from kavach.audit import list_recent_runs
from fastapi import FastAPI, HTTPException, UploadFile, File, Query

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

STATIC = Path(__file__).parent / "static"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 20

MAX_CHAT_BODY_BYTES = 1 * 1024 * 1024
MAX_CHAT_MESSAGES = 100
MAX_CHAT_TEXT_CHARS = 20000

MAX_UPSTREAM_RESPONSE_BYTES = 5 * 1024 * 1024
UPSTREAM_TIMEOUT = 60


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="KAVACH",
    description="India-aware PII guardrail for AI tools",
    version="1.2.4",
)

app.mount(
    "/static",
    StaticFiles(directory=STATIC),
    name="static",
)


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

        # Reject credentials, query strings, fragments, and
        # paths other than the expected API base paths.
        if (
            parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/", "/v1"}
        ):
            raise ValueError("Unsupported URL components")

        # Reject alternate hostname spellings.
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
    """Log whether the configured upstream passes validation."""

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
    return {
        "status": "ok",
        "version": "1.2.4",
    }


# --------------------------------------------------
# Scan pasted text
# --------------------------------------------------

class ScanIn(BaseModel):
    text: str = Field(max_length=20000)
    mode: str = Field(
        default="label",
        pattern="^(label|partial)$",
    )


@app.post("/api/scan")
def scan_text(body: ScanIn):
    result = analyze(body.text, body.mode)

    if AGENT_ENABLED:
        result["agent_review"] = review_findings(
            body.text,
            result["findings"],
        )

    return result

@app.post("/api/scan-global")
def scan_global_text(body: ScanIn):
    result = analyze_global(body.text, body.mode)

    if AGENT_ENABLED:
        result["agent_review"] = review_findings(
            body.text,
            result["findings"],
        )

    return result

@app.post("/api/agentic/scan")
def scan_agentic(body: ScanIn):
    return run_agentic_workflow(
        body.text,
        body.mode,
        source="api",
    )

@app.get("/api/agentic/history")
def agentic_history(
    limit: int = Query(default=20, ge=1, le=100)
):
    """Return bounded workflow metadata without prompt contents."""
    return {
        "runs": list_recent_runs(limit)
    }

# --------------------------------------------------
# Scan TXT and PDF documents
# --------------------------------------------------

@app.post("/api/scan-file")
async def scan_file(file: UploadFile = File(...)):
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
                reader = PdfReader(BytesIO(content), strict=False)

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

            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Could not read this PDF. "
                        "Try a valid, text-based PDF."
                    ),
                )

        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "No readable text found. "
                    "Scanned-image PDFs need OCR."
                ),
            )

        result = analyze_global(text, mode="label")

        return {
            "filename": filename,
            "page_count": page_count,
            "findings": result.get("findings", []),
            "global_detection": result.get("global_detection", {}),
            "masked_text": result.get("masked_text", ""),
            "risk": result.get("risk", {}),
            "count": len(result.get("findings", [])),
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
                or (
                    isinstance(value, float)
                    and not math.isfinite(value)
                )
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
                    "A chat message exceeds the maximum "
                    "allowed length of 20,000 characters."
                ),
            )

        result = analyze(content)

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

    # Build a fresh allowlisted payload.
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
    # Validate destination before reading or forwarding the body.
    # A rejected URL never reaches the HTTP client.
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
                "error": "Blocked: prompt contained high-risk personal data."
            },
            status_code=422,
        )

    # Require a non-empty Bearer token.
    # This validates header format, not whether the token is genuine.
    auth = request.headers.get("authorization")

    if (
        not auth
        or not auth.startswith("Bearer ")
        or not auth[7:].strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in auth)
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
