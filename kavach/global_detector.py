"""Global sensitive-data detection layer for KAVACH.

Combines KAVACH's existing India-aware detector, Presidio global
recognizers, contextual rules, and high-priority secret detection.
"""

import re
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine

from kavach.detectors import Finding, mask, risk, scan


# Map Presidio entity names to KAVACH finding types.
# URL is excluded because partial URL matches can overlap email addresses.
_ENTITY_MAP = {
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "CREDIT_CARD": "CARD",
    "IBAN_CODE": "IBAN",
    "IP_ADDRESS": "IP_ADDRESS",
    "MAC_ADDRESS": "MAC_ADDRESS",

    # Additional global information types
    "CRYPTO": "CRYPTO",
    "MEDICAL_LICENSE": "MEDICAL_LICENSE",
    "NRP": "NRP",

    # Regional identifiers
    "US_SSN": "US_SSN",
    "US_ITIN": "US_ITIN",
    "US_DRIVER_LICENSE": "US_DRIVER_LICENSE",
    "US_PASSPORT": "US_PASSPORT",
    "US_BANK_NUMBER": "US_BANK_NUMBER",
    "UK_NINO": "UK_NINO",
    "UK_NHS": "UK_NHS",
    "UK_PASSPORT": "UK_PASSPORT",
    "AU_ABN": "AU_ABN",
    "AU_ACN": "AU_ACN",
    "AU_TFN": "AU_TFN",
    "AU_MEDICARE": "AU_MEDICARE",
}


# Minimum confidence thresholds for selected recognizers.
# These are initial settings and require evaluation against test data.
_MIN_SCORE = {
    "PERSON": 0.65,
    "LOCATION": 0.65,
    "CRYPTO": 0.50,
    "MEDICAL_LICENSE": 0.40,
    "NRP": 0.65,
}


# Broad geographic names should not automatically be treated as
# sensitive personal locations.
_BROAD_LOCATIONS = {
    "united states",
    "u.s.",
    "usa",
    "united kingdom",
    "u.k.",
    "uk",
    "india",
    "canada",
    "australia",
    "new zealand",
    "europe",
    "asia",
    "africa",
    "north america",
    "south america",
    "oceania",
}


_PERSONAL_LOCATION_CONTEXT = re.compile(
    r"\b(?:live|lives|living|reside|resides|residing|"
    r"located|based|stay|stays|staying|moved)\s+"
    r"(?:in|at|to|from)\s+(?:the\s+)?$",
    re.IGNORECASE,
)


# Organizational labels should not automatically be treated as
# personal locations, for example "London team" or "Paris office".
_NONPERSONAL_LOCATION_CONTEXT = re.compile(
    r"^\s+(?:team|office|branch|headquarters|department|"
    r"division|group|staff)\b",
    re.IGNORECASE,
)


# An NRP finding should have personal-identity or affiliation context.
# This helps avoid treating ordinary terms such as "Bitcoin" as NRP.
_NRP_PERSONAL_CONTEXT = re.compile(
    r"\b(?:"
    r"am|is|are|was|were|"
    r"identify as|identifies as|identified as|"
    r"identify with|identifies with|identified with|"
    r"belong to|belongs to|belonged to|"
    r"affiliated with|"
    r"member of|"
    r"practice|practices|practiced|"
    r"follow|follows|followed"
    r")\s+(?:(?:a|an|the)\s+)?$",
    re.IGNORECASE,
)


# Initial contextual rules for selected medical and confidential
# business information. These are not comprehensive classifiers.
_CONTEXT_RULES = [
    (
        "MEDICAL_INFO",
        re.compile(
            r"\b(?:the\s+)?(?:patient|i|he|she|they)\s+"
            r"(?:has|have|had|was diagnosed with|were diagnosed with|"
            r"suffers from|is taking|are taking|takes|take)\b"
            r"[^.!?\n]{0,120}\b"
            r"(?:diabetes|metformin|hypertension|cancer|asthma|HIV|"
            r"depression|anxiety|arthritis|epilepsy|medication|"
            r"prescription|diagnosis|medical history|blood pressure|"
            r"lab results?)\b[^.!?\n]*[.!?]?",
            re.IGNORECASE,
        ),
        0.80,
    ),
    (
        "CONFIDENTIAL_BUSINESS",
        re.compile(
            r"\b(?:our|the)\s+(?:fictional\s+)?company\b"
            r"[^.!?\n]{0,150}\b"
            r"(?:confidential|non-public|unannounced|proprietary|"
            r"trade secret|customer list|product roadmap|"
            r"layoff plan|source code)\b"
            r"[^.!?\n]*[.!?]?",
            re.IGNORECASE,
        ),
        0.80,
    ),
]


# Detect complete high-priority secrets before ordinary recognizers.
# Use synthetic credentials for testing; never place real credentials
# in test samples or source code.
_SECRET_RULES = [
    (
        "API_KEY",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
            r"[\s\S]*?"
            r"-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.IGNORECASE,
        ),
        0.99,
    ),
    (
        "API_KEY",
        re.compile(
            r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|"
            r"mongodb(?:\+srv)?|redis|mssql|sqlserver)://"
            r"[^\s\"'`<>]+"
        ),
        0.98,
    ),
    (
        "API_KEY",
        re.compile(
            r"(?i)\b(?:authorization\s*:\s*)?bearer\s+"
            r"[A-Za-z0-9._~+/-]+=*"
        ),
        0.98,
    ),
    (
        "API_KEY",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{5,}"
            r"\.[A-Za-z0-9_-]{5,}"
            r"\.[A-Za-z0-9_-]{5,}\b"
        ),
        0.98,
    ),
]


@lru_cache(maxsize=1)
def _get_analyzer():
    """Initialize Presidio once and return supported English entities."""
    analyzer = AnalyzerEngine()

    supported = set(
        analyzer.get_supported_entities(language="en")
    )

    entities = tuple(
        entity
        for entity in _ENTITY_MAP
        if entity in supported
    )

    return analyzer, entities


def _serialize(findings):
    """Return finding metadata without raw sensitive values."""
    return [
        {
            "type": finding.type,
            "start": finding.start,
            "end": finding.end,
            "confidence": finding.confidence,
        }
        for finding in sorted(
            findings,
            key=lambda item: (item.start, item.end),
        )
    ]


def _overlaps(start, end, findings):
    """Return True when a span intersects an existing finding."""
    return any(
        start < existing.end and end > existing.start
        for existing in findings
    )


def _should_keep_location(
    value: str,
    text: str,
    start: int,
) -> bool:
    """Filter organizational and broad locations without personal context."""
    normalized = " ".join(
        value.casefold().strip(" .").split()
    )

    preceding_context = text[
        max(0, start - 60):start
    ].casefold()

    end = start + len(value)
    following_context = text[end:end + 40]

    # Explicit personal-location context takes priority.
    if _PERSONAL_LOCATION_CONTEXT.search(preceding_context):
        return True

    # Suppress locations used as organizational labels.
    if _NONPERSONAL_LOCATION_CONTEXT.search(following_context):
        return False

    # Broad geographic names require personal-location context.
    if normalized in _BROAD_LOCATIONS:
        return False

    return True


def _should_keep_nrp(
    value: str,
    text: str,
    start: int,
) -> bool:
    """Keep NRP findings only when surrounding context suggests
    personal identity, belief, or affiliation.
    """
    preceding_context = text[
        max(0, start - 100):start
    ]

    # The pattern must match immediately before the detected entity.
    return bool(
        _NRP_PERSONAL_CONTEXT.search(preceding_context)
    )


def _detect_special_secrets(text: str) -> list[Finding]:
    """Find complete high-priority secret spans."""
    secrets = []

    for entity_type, pattern, confidence in _SECRET_RULES:
        for match in pattern.finditer(text):
            start, end = match.span()

            if start < 0 or end <= start or end > len(text):
                continue

            # Prefer the first, higher-priority rule if spans overlap.
            if _overlaps(start, end, secrets):
                continue

            secrets.append(
                Finding(
                    type=entity_type,
                    start=start,
                    end=end,
                    confidence=confidence,
                    value=match.group(0),
                )
            )

    return secrets


def analyze_global(text: str, mode: str = "label") -> dict:
    """Run KAVACH, global recognizers, and contextual secret rules."""

    # 1. Detect complete secrets and explicitly labelled US SSNs.
    secret_findings = _detect_special_secrets(text)

    # SSN-shaped numbers are ambiguous without a label.
    # Recognize them as US_SSN only when explicitly labelled.
    ssn_pattern = re.compile(
        r"\b(?:SSN|social security(?: number| no\.?)?)"
        r"\s*(?:is\s*)?[:#=]?\s*"
        r"(?P<value>\d{3}[- ]\d{2}[- ]\d{4})\b",
        re.IGNORECASE,
    )

    ssn_findings = []

    for match in ssn_pattern.finditer(text):
        start, end = match.span("value")

        if _overlaps(start, end, secret_findings):
            continue

        ssn_findings.append(
            Finding(
                type="US_SSN",
                start=start,
                end=end,
                confidence=0.99,
                value=match.group("value"),
            )
        )

    # Explicitly labelled SSNs and complete secrets take priority
    # over overlapping generic phone detections.
    priority_findings = secret_findings + ssn_findings

    deterministic = scan(text)

    combined = list(priority_findings)
    combined.extend(
        finding
        for finding in deterministic
        if not _overlaps(
            finding.start,
            finding.end,
            priority_findings,
        )
    )

    global_status = "ok"
    global_reason = None
    enabled_entities = []

    # 2. Run Presidio's supported global and regional recognizers.
    try:
        analyzer, entities = _get_analyzer()
        enabled_entities = list(entities)

        if not entities:
            raise RuntimeError(
                "No configured global entities are available"
            )

        results = analyzer.analyze(
            text=text,
            language="en",
            entities=list(entities),
        )

        # Prefer higher-scoring, longer candidates.
        for result in sorted(
            results,
            key=lambda item: (
                -float(item.score or 0.0),
                item.start,
                -(item.end - item.start),
            ),
        ):
            mapped_type = _ENTITY_MAP.get(result.entity_type)

            if mapped_type is None:
                continue

            start, end = result.start, result.end
            score = float(result.score or 0.0)

            if start < 0 or end <= start or end > len(text):
                continue

            if score < _MIN_SCORE.get(
                result.entity_type,
                0.35,
            ):
                continue

            value = text[start:end]

            # Require personal context for NRP predictions.
            if (
                result.entity_type == "NRP"
                and not _should_keep_nrp(
                    value,
                    text,
                    start,
                )
            ):
                continue

            # Filter broad geography and organizational labels.
            if (
                result.entity_type == "LOCATION"
                and not _should_keep_location(
                    value,
                    text,
                    start,
                )
            ):
                continue

            # Avoid very short, ambiguous location predictions.
            if (
                result.entity_type == "LOCATION"
                and len(value.strip()) < 3
            ):
                continue

            # Don't let overlapping findings produce competing masks.
            if _overlaps(start, end, combined):
                continue

            combined.append(
                Finding(
                    type=mapped_type,
                    start=start,
                    end=end,
                    confidence=max(0.0, min(1.0, score)),
                    value=value,
                )
            )

    except Exception as exc:
        # Retain deterministic and contextual detection if Presidio fails.
        global_status = "unavailable"
        global_reason = type(exc).__name__

    # 3. Run selected medical and business context rules.
    # These also run when Presidio is unavailable.
    for entity_type, pattern, confidence in _CONTEXT_RULES:
        for match in pattern.finditer(text):
            start, end = match.span()

            if start < 0 or end <= start or end > len(text):
                continue

            if _overlaps(start, end, combined):
                continue

            combined.append(
                Finding(
                    type=entity_type,
                    start=start,
                    end=end,
                    confidence=confidence,
                    value=match.group(0),
                )
            )

    # 4. Generate protected output and risk assessment.
    return {
        "findings": _serialize(combined),
        "masked_text": mask(text, combined, mode),
        "risk": risk(combined),
        "global_detection": {
            "status": global_status,
            "engine": "KAVACH + Presidio + contextual rules",
            "language": "en",
            "enabled_entities": enabled_entities,
            **(
                {"reason": global_reason}
                if global_reason
                else {}
            ),
        },
    }