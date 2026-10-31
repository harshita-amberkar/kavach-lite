"""Systems under test. Each returns [(type, start, end)] for a text."""

import re

from kavach import scan
from kavach.global_detector import analyze_global
from kavach.detectors import _UPI_HANDLES


def kavach(text):
    """Run the Kavach detector."""
    return [
        (
            "AADHAAR" if f.type == "AADHAAR_POSSIBLE" else f.type,
            f.start,
            f.end,
        )
        for f in scan(text)
    ]

def kavach_global(text):
    """Run the complete KAVACH global detection engine."""
    result = analyze_global(text)
    return [
        (
            "AADHAAR" if finding["type"] == "AADHAAR_POSSIBLE"
            else finding["type"],
            finding["start"],
            finding["end"],
        )
        for finding in result.get("findings", [])
    ]


def kavach_block(text):
    """Kavach findings at block level only: AADHAAR_POSSIBLE (warn tier) is dropped."""
    return [
        (f.type, f.start, f.end)
        for f in scan(text)
        if f.type != "AADHAAR_POSSIBLE"
    ]

_NAIVE = [
    ("AADHAAR", r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
    ("PAN", r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    ("PHONE", r"(?:\+91[- ]?)?\b[6-9]\d{9}\b"),
    ("CARD", r"\b(?:\d[ -]?){15}\d\b"),
    ("EMAIL", r"[\w.+-]+@[\w-]+\.[\w.]+"),
    ("UPI_ID", r"[\w.\-]{2,}@[a-z]{2,}\b"),
    ("GSTIN", r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\w[Z]\w\b"),
]


def regex_only(text):
    """Run the simple regex-only baseline."""
    out = []

    for entity_type, pattern in _NAIVE:
        out += [
            (entity_type, match.start(), match.end())
            for match in re.finditer(pattern, text)
        ]

    return out


_DEV = str.maketrans("०१२३४५६७८९", "0123456789")


def presidio(custom=False, norm=False):
    """
    Run the Presidio baseline.

    Requirements:
        pip install presidio-analyzer
        python -m spacy download en_core_web_lg

    custom=True adds GSTIN and UPI recognizers.
    norm=True normalises Devanagari digits before analysis.
    """
    from presidio_analyzer import (
        AnalyzerEngine,
        Pattern,
        PatternRecognizer,
        RecognizerRegistry,
    )
    from presidio_analyzer.predefined_recognizers import (
        InAadhaarRecognizer,
        InPanRecognizer,
    )

    reg = RecognizerRegistry()
    reg.load_predefined_recognizers()

    # Explicitly add Indian Aadhaar and PAN recognizers.
    reg.add_recognizer(InAadhaarRecognizer())
    reg.add_recognizer(InPanRecognizer())

    if custom:
        # Custom GSTIN recognizer.
        reg.add_recognizer(
            PatternRecognizer(
                supported_entity="GSTIN",
                patterns=[
                    Pattern(
                        "gstin",
                        r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b",
                        0.85,
                    )
                ],
            )
        )

        # Use the same UPI handle collection as Kavach.
        handles = "|".join(
            re.escape(handle)
            for handle in sorted(
                _UPI_HANDLES,
                key=len,
                reverse=True,
            )
        )

        reg.add_recognizer(
            PatternRecognizer(
                supported_entity="UPI_ID",
                patterns=[
                    Pattern(
                        "upi",
                        rf"(?i)(?<![\w.\-@])[\w.\-]{{2,64}}@(?:{_UPI_HANDLES})(?![\w\-]|\.[a-z])",
                        0.85,
                    )
                ],
            )
        )

    eng = AnalyzerEngine(registry=reg)

    entity_map = {
        "GSTIN": "GSTIN",
        "UPI_ID": "UPI_ID",
        "IN_AADHAAR": "AADHAAR",
        "IN_PAN": "PAN",
        "PHONE_NUMBER": "PHONE",
        "CREDIT_CARD": "CARD",
        "EMAIL_ADDRESS": "EMAIL",
    }

    def prepare(text):
        if norm:
            return text.translate(_DEV)
        return text

    def analyze(text):
        prepared_text = prepare(text)

        return [
            (
                entity_map[result.entity_type],
                result.start,
                result.end,
            )
            for result in eng.analyze(
                text=prepared_text,
                language="en",
                score_threshold=0.4,
            )
            if result.entity_type in entity_map
        ]

    return analyze


def available():
    """Return all detector systems that can be loaded."""
    systems = {
        "kavach": kavach,
        "kavach_global": kavach_global,
        "kavach_block": kavach_block,
        "regex_only": regex_only,
    }

    try:
        systems["presidio"] = presidio()
        systems["presidio_custom"] = presidio(custom=True)
        systems["presidio_norm"] = presidio(custom=True, norm=True)
    except Exception as error:
        print("Presidio skipped:", type(error).__name__, str(error))

    return systems