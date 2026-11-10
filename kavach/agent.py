
"""Optional local LLM review for KAVACH detector findings.

The agent is advisory only: it never changes findings, masking, or policy.
Only sanitized context and finding metadata are sent to Ollama.
"""

import json
import ipaddress
import os
import re
from urllib.parse import urlsplit

import httpx


OLLAMA_URL = os.getenv(
    "KAVACH_OLLAMA_URL",
    "http://127.0.0.1:11434/api/generate",
)
OLLAMA_MODEL = os.getenv("KAVACH_OLLAMA_MODEL", "llama3.2:3b")
AGENT_TIMEOUT = float(os.getenv("KAVACH_AGENT_TIMEOUT", "30"))

# Disabled unless explicitly enabled.
AGENT_ENABLED = os.getenv("KAVACH_AGENT_ENABLED", "0") == "1"


def validate_ollama_url(url: str) -> str:
    """Accept only HTTP(S) URLs addressed directly to a loopback host."""
    try:
        if not isinstance(url, str) or any(
            char.isspace() or ord(char) < 32 or ord(char) == 127
            for char in url
        ):
            raise ValueError

        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port

        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or "\\" in url
            or (port is not None and port == 0)
        ):
            raise ValueError

        hostname = hostname.lower()
        if hostname != "localhost":
            # Reject DNS names, scoped IPv6 literals, and every non-loopback
            # address. Only parsed IP literals are accepted here.
            if "%" in hostname or not ipaddress.ip_address(hostname).is_loopback:
                raise ValueError

    except (ValueError, UnicodeError):
        raise ValueError(
            "KAVACH_OLLAMA_URL must use localhost or a loopback IP address."
        ) from None

    return url


def _sanitize_context(_text: str, _start: int, _end: int) -> str:
    """Withhold source text; regex redaction cannot guarantee privacy."""
    return "[REDACTED]"


def _safe_review_list(value) -> list[str]:
    """Keep bounded, plain-text advisory fields from the local model."""
    if not isinstance(value, list):
        return []

    safe = []
    for item in value[:5]:
        if isinstance(item, str) and item.strip():
            safe.append(item.strip()[:160])
    return safe


def review_findings(text: str, findings: list[dict]) -> dict:
    """Ask the local model for advisory reviews; never alter scan results."""
    if not AGENT_ENABLED:
        return {"status": "disabled", "reviews": []}

    if not findings:
        return {"status": "no_findings", "reviews": []}

    candidates = []
    for index, finding in enumerate(findings[:10]):
        start = finding.get("start")
        end = finding.get("end")

        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(text)
        ):
            continue

        finding_type = str(finding.get("type", "UNKNOWN"))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,39}", finding_type):
            finding_type = "UNKNOWN"

        candidates.append({
            "id": index,
            "type": finding_type,
            "confidence": round(
                max(0.0, min(1.0, float(finding.get("confidence", 0.0)))),
                2,
            ),
            "context": _sanitize_context(text, start, end),
        })

    if not candidates:
        return {"status": "no_valid_candidates", "reviews": []}

    prompt = (
        "You are an advisory reviewer for a privacy detector. "
        "Review each candidate using only its type and confidence. "
        "Source context is withheld and represented by [REDACTED]. "
        "Do not infer or reconstruct source values. "
        "Return JSON only in this format: "
        '{"reviews":[{"id":0,"assessment":"likely|uncertain|unlikely",'
        '"reason":"brief reason","privacy_concerns":[],'
        '"recommendations":[]}]}. '
        "Privacy concerns and recommendations must be brief and based only "
        "on the candidate type and confidence. Do not infer source values. "
        "Do not recommend sending, unmasking, or revealing sensitive data. "
        "Candidates:\n"
        + json.dumps(candidates, ensure_ascii=True)
    )

    try:
        ollama_url = validate_ollama_url(OLLAMA_URL)
        response = httpx.post(
            ollama_url,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=AGENT_TIMEOUT,
            trust_env=False,
            follow_redirects=False,
        )
        response.raise_for_status()
        response_data = response.json()
        if not isinstance(response_data, dict):
            return {"status": "unavailable", "reviews": []}

        raw = response_data.get("response")
        if not isinstance(raw, str):
            return {"status": "unavailable", "reviews": []}

        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {"status": "unavailable", "reviews": []}

        model_reviews = parsed.get("reviews")
        if not isinstance(model_reviews, list):
            return {"status": "unavailable", "reviews": []}

        allowed_ids = {item["id"] for item in candidates}
        reviews = []

        for item in model_reviews:
            if not isinstance(item, dict):
                continue
            if item.get("id") not in allowed_ids:
                continue
            if item.get("assessment") not in {
                "likely", "uncertain", "unlikely"
            }:
                continue

            safe_review = {
                "id": item["id"],
                "assessment": item["assessment"],
                "reason": str(item.get("reason", ""))[:160],
            }
            for field in ("privacy_concerns", "recommendations"):
                safe_values = _safe_review_list(item.get(field))
                if safe_values:
                    safe_review[field] = safe_values
            reviews.append(safe_review)

        return {"status": "ok", "reviews": reviews}

    except httpx.TimeoutException:
        return {
            "status": "unavailable",
            "reviews": [],
            "reason": "timeout",
        }
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        # Fail safely: the caller's original detector results remain unchanged.
        return {"status": "unavailable", "reviews": []}
