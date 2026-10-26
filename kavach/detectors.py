"""Kavach core: India-aware PII / secret detection and masking.

Pure Python, no dependencies. Checksum validation (Aadhaar Verhoeff,
GSTIN mod-36, and card Luhn) helps reduce false positives.
"""

import re
from dataclasses import dataclass

# ---------- checksums ----------

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
_GST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def verhoeff_valid(num: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def verhoeff_check_digit(num: str) -> str:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return str(_INV[c])


def luhn_valid(num: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(num)):
        n = int(ch)
        if i % 2 == 1:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def gstin_check_char(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        v = _GST.index(ch) * (1 if i % 2 == 0 else 2)
        total += v // 36 + v % 36
    return _GST[(36 - total % 36) % 36]


# ---------- rules ----------

_digits = lambda s: re.sub(r"\D", "", s)

_CTX = re.compile(
    r"aadhaar|aadhar|adhar|uidai|\buid\b|आधार",
    re.IGNORECASE,
)

_PLACEHOLDER_SECRET = re.compile(
    r"(?i)(?:"
    r"\b(?:redacted|placeholder|dummy|changeme|replace[_-]?me)\b"
    r"|\b(?:your|insert)[_-]?(?:api[_-]?)?key\b"
    r")"
)

_UPI_HANDLES = (
    "ybl|ibl|axl|okhdfcbank|okicici|okaxis|oksbi|paytm|apl|upi|sbi|"
    "hdfcbank|icici|axisbank|pnb|barodampay|kotak|indus|fbl|airtel|jio|postbank"
)

# Suppress phone matches when the number is labelled as an
# ordinary score, order ID, reference number, or transaction ID.
# The expression must match at the end of the text before the number.
_PHONE_NEGATIVE_CTX = re.compile(
    r"(?:"
    r"\bscore\b[^.!?\n]{0,25}"
    r"|\border\s*(?:id|number|no\.?)?\s*[:#-]?\s*"
    r"|\breference\s*(?:id|number|no\.?)?\s*[:#-]?\s*"
    r"|\btransaction\s*(?:id|number|no\.?)?\s*[:#-]?\s*"
    r")$",
    re.IGNORECASE,
)

# A checksum-valid 12-digit number labelled as an ordinary identifier is
# suppressed unless Aadhaar-specific context is also present. Devanagari
# words are listed without \b because combining marks are not word characters
# in Python's re module.
_AADHAAR_NEGATIVE_CTX = re.compile(
    r"(?:"
    r"\b(?:order|po|purchase\s+order|ticket|reference|ref|tracking|"
    r"consignment|invoice|transaction|txn|awb|case|batch|timestamp|"
    r"time\s+stamp|build|run|job|sequence|serial)\b"
    r"|ऑर्डर|ट्रैकिंग|टिकट"
    r")"
    r"\s*(?:(?:id|number|num|no\.?|क्रमांक|नंबर)\s*)?[:#\-]?\s*$",
    re.IGNORECASE,
)
# Each rule:
# name, regex, priority (lower wins overlaps), check, confidence

_RULES = [
    (
        "AADHAAR",
        r"(?<!\d)(?<!\d[\s-])[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}"
        r"(?!\d)(?![\s-]\d{4}(?!\d))",
        1,
        lambda r, t, s: verhoeff_valid(_digits(r)),
        0.98,
    ),
    (
        "GSTIN",
        r"\b(?:0[1-9]|[12]\d|3[0-8])[A-Z]{3}"
        r"[ABCFGHLJPT][A-Z]\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b",
        1,
        lambda r, t, s: gstin_check_char(r[:14]) == r[14],
        0.97,
    ),
    (
        "API_KEY",
        r"\bAKIA[0-9A-Z]{16}\b"
        r"|\bsk-[A-Za-z0-9_-]{20,}"
        r"|\bgh[pousr]_[A-Za-z0-9]{36,}",
        1,
        None,
        0.95,
    ),
    (
        "API_KEY",
        r"""(?i)\b(?:api[_-]?key|secret|token|passwd|password)\b"""
        r"""\s*[:=]\s*(?:"[^"\r\n]{8,}"|'[^'\r\n]{8,}'|[^\s'"`]{8,})""",
        1,
        None,
        0.85,
    ),
    (
        "CARD",
        r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)",
        2,
        lambda r, t, s: (
            13 <= len(_digits(r)) <= 19
            and luhn_valid(_digits(r))
        ),
        0.95,
    ),
    (
        "PAN",
        r"(?i)\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b",
        2,
        None,
        0.92,
    ),
    (
        "UPI_ID",
        rf"(?i)(?<![\w.@-])[\w.-]{{2,64}}"
        rf"@(?:{_UPI_HANDLES})(?![\w-]|\.[a-z])",
        3,
        None,
        0.93,
    ),
    (
        "IFSC",
        r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        3,
        None,
        0.88,
    ),
    (
        "EMAIL",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        4,
        None,
        0.97,
    ),
    (
        "PHONE",
        r"(?<!\d)(?:\+91[\-\s]?|91[\-\s]?|0)?"
        r"[6-9]\d{4}[\-\s]?\d{5}(?!\d)",
        5,
        None,
        0.85,
    ),
    # An unchecksummed 12-digit number is considered a possible
    # Aadhaar only when Aadhaar-related context appears before it.
    (
        "AADHAAR_POSSIBLE",
        r"(?<!\d)(?<!\d[\s-])[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}"
        r"(?!\d)(?![\s-]\d{4}(?!\d))",
        6,
        lambda r, t, s: bool(
            _CTX.search(t[max(0, s - 40):s])
        ),
        0.6,
    ),
    (
        "PASSWORD",
        r"(?i)\b(?:password|passcode|passwd|pwd|pin)\s+(?:is|was)\s+[^\s,;]{4,}",
        1,
        lambda r, t, s: bool(
            re.search(r"[\d@#$%^&*!_]", r.split()[-1])
        ),
        0.8,
    ),
    (
        "OTP",
        r"(?i)\b(?:otp|verification code|one[- ]time (?:password|passcode|code))"
        r"\s*(?:is|was|=|:)?\s*\d{4,8}(?!\d)",
        1,
        None,
        0.85,
    ),
    (
        "PASSPORT",
        r"(?i)\bpassport(?:\s*(?:no\.?|number|num|#))?\s*(?:is|:|=)?\s*[A-Z]\d{7}\b",
        1,
        None,
        0.85,
    ),
]

_COMPILED = [
    (name, re.compile(rx), priority, check, confidence)
    for name, rx, priority, check, confidence in _RULES
]

_WEIGHT = {
    "AADHAAR": 40,
    "CARD": 40,
    "API_KEY": 40,
    "PAN": 30,
    "GSTIN": 20,
    "UPI_ID": 15,
    "AADHAAR_POSSIBLE": 15,
    "PHONE": 10,
    "EMAIL": 8,
    "IFSC": 5,
    "PASSWORD": 40,
    "OTP": 30,
    "PASSPORT": 30,
    "PERSON": 15,
    "LOCATION": 15,
    "IBAN": 30,
    "IP_ADDRESS": 10,
    "MAC_ADDRESS": 10,
    "US_SSN": 30,
    "US_ITIN": 30,
    "US_DRIVER_LICENSE": 25,
    "US_PASSPORT": 25,
    "US_BANK_NUMBER": 25,
    "UK_NINO": 30,
    "UK_NHS": 25,
    "UK_PASSPORT": 25,
    "AU_ABN": 20,
    "AU_ACN": 20,
    "AU_TFN": 30,
    "AU_MEDICARE": 25,
    "MEDICAL_INFO": 30,
    "CONFIDENTIAL_BUSINESS": 25,

    # Additional global information types
    "CRYPTO": 30,
    "MEDICAL_LICENSE": 25,
    "NRP": 25,
}

# Devanagari digits -> ASCII. This preserves character offsets.
_DEVA = str.maketrans("०१२३४५६७८९", "0123456789")


@dataclass
class Finding:
    type: str
    start: int
    end: int
    confidence: float
    value: str = ""


def scan(text: str) -> list:
    """Detect sensitive data in text and return non-overlapping findings."""
    t = text.translate(_DEVA)
    hits = []

    for name, rx, priority, check, confidence in _COMPILED:
        for match in rx.finditer(t):
            raw_value = match.group(0)
            start = match.start()
            end = match.end()

            if check and not check(raw_value, t, start):
                continue

            if name == "API_KEY" and _PLACEHOLDER_SECRET.search(raw_value):
                continue

            if name == "PHONE":
                # Examine only the immediate text before the number.
                # A punctuation mark ends the relevant context.
                context = t[max(0, start - 40):start]

                if _PHONE_NEGATIVE_CTX.search(context):
                    continue

            hit_name, hit_conf = name, confidence

            if name == "AADHAAR":
                # Suppress Aadhaar-shaped numbers labelled as ordinary IDs.
                # Explicit Aadhaar context takes precedence over this rule.
                context = t[max(0, start - 60):start]

                if (
                    _AADHAAR_NEGATIVE_CTX.search(context)
                    and not _CTX.search(context)
                ):
                    continue

            hits.append(
                (
                    priority,
                    -(end - start),
                    start,
                    end,
                    hit_name,
                    hit_conf,
                )
            )

    hits.sort()

    kept = []

    for _, _, start, end, name, confidence in hits:
        if all(end <= f.start or start >= f.end for f in kept):
            kept.append(
                Finding(
                    name,
                    start,
                    end,
                    confidence,
                    text[start:end],
                )
            )

    return sorted(kept, key=lambda f: f.start)


def mask(text: str, findings: list, mode: str = "label") -> str:
    """Mask findings using labels or partial masking."""
    out = text

    for finding in sorted(
        findings,
        key=lambda f: f.start,
        reverse=True,
    ):
        if mode == "partial" and finding.type in (
            "AADHAAR",
            "CARD",
            "PHONE",
        ):
            digits = _digits(finding.value)
            replacement = (
                "X" * max(len(digits) - 4, 0)
                + digits[-4:]
            )
        else:
            replacement = f"[{finding.type}]"

        out = (
            out[:finding.start]
            + replacement
            + out[finding.end:]
        )

    return out


def risk(findings: list) -> dict:
    """Calculate an overall risk score and level."""
    score = min(
        100,
        sum(_WEIGHT.get(f.type, 5) for f in findings),
    )

    level = (
        "high" if score >= 40
        else "medium" if score >= 15
        else "low" if score
        else "none"
    )

    return {"score": score, "level": level}


def analyze(text: str, mode: str = "label") -> dict:
    """Return findings, masked text, and risk assessment."""
    findings = scan(text)

    return {
        "findings": [
            {
                "type": finding.type,
                "start": finding.start,
                "end": finding.end,
                "confidence": finding.confidence,
            }
            for finding in findings
        ],
        "masked_text": mask(text, findings, mode),
        "risk": risk(findings),
    }
