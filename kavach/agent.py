
"""Optional local LLM review for KAVACH detector findings.

The agent is advisory only: it never changes findings, masking, or policy.
Only sanitized context and finding metadata are sent to Ollama.
"""

import json
import os
import re

import httpx


OLLAMA_URL = os.getenv(
    "KAVACH_OLLAMA_URL",
    "http://127.0.0.1:11434/api/generate",
)
OLLAMA_MODEL = os.getenv("KAVACH_OLLAMA_MODEL", "llama3.2:3b")
AGENT_TIMEOUT = float(os.getenv("KAVACH_AGENT_TIMEOUT", "8"))

# Disabled unless explicitly enabled.
AGENT_ENABLED = os.getenv("KAVACH_AGENT_ENABLED", "0") == "1"


def _sanitize_context(text: str, start: int, end: int) -> str:
    """Redact likely identifiers in the full text before extracting context."""
    marker = "__KAVACH_TARGET_MARKER_9F31__"
    while marker in text:
        marker += "_X"

    # Mark the detected value without exposing it.
    safe_text = text[:start] + marker + text[end:]

    # Redact likely sensitive values across the FULL text first.
    # This prevents identifiers from escaping detection at snippet boundaries.
    patterns = [
        # Email addresses
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",

        # Common API keys and access tokens
        r"\b(?:AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{36,})\b",
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        r"\bBearer\s+\S+",

        # Credentials explicitly labelled in text
        r"\b(?:api[_-]?key|secret|token|passwd|password|authorization)\b\s*[:=]\s*\S+",

        # Long number sequences, PAN, GSTIN, IFSC and IBAN-like values
        r"\b\d[\d\s-]{7,}\d\b",
        r"\b[A-Z]{5}\d{4}[A-Z]\b",
        r"\b(?:0[1-9]|[12]\d|3[0-8])[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b",
        r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",

        # Email-like and UPI-like identifiers
        r"\b[\w.-]{2,64}@[a-z][a-z0-9.-]{1,30}\b",
    ]

    for pattern in patterns:
        safe_text = re.sub(pattern, "[REDACTED]", safe_text, flags=re.I)

    # Only extract a short context after the full text has been sanitized.
    marker_index = safe_text.find(marker)
    if marker_index < 0:
        return "[REDACTED]"

    left = max(0, marker_index - 60)
    right = min(len(safe_text), marker_index + len(marker) + 60)

    return safe_text[left:right].replace(marker, "[REDACTED]")


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

        candidates.append({
            "id": index,
            "type": str(finding.get("type", "UNKNOWN"))[:40],
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
        "Review each candidate using only its type, confidence, and "
        "redacted context. Context may still contain unrecognized data. "
        "Do not infer or reconstruct redacted values. "
        "Return JSON only in this format: "
        '{"reviews":[{"id":0,"assessment":"likely|uncertain|unlikely",'
        '"reason":"brief reason"}]}. '
        "Do not recommend sending, unmasking, or revealing sensitive data. "
        "Candidates:\n"
        + json.dumps(candidates, ensure_ascii=True)
    )

    try:
        response = httpx.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=AGENT_TIMEOUT,
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

            reviews.append({
                "id": item["id"],
                "assessment": item["assessment"],
                "reason": str(item.get("reason", ""))[:160],
            })

        return {"status": "ok", "reviews": reviews}

    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        # Fail safely: the caller's original detector results remain unchanged.
        return {"status": "unavailable", "reviews": []}
