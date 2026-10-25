"""Preliminary synthetic benchmark for KAVACH's global detector.

Uses fictional/demo data only.
Does not save prompts or results to disk.

Run from the project root with:
    python -m eval.global_benchmark
"""

import time
from collections import defaultdict
from statistics import median

from kavach.global_detector import analyze_global


# Build test-only PEM markers from fragments so simple secret scanners
# do not mistake benchmark fixtures for actual private-key material.
_TEST_PRIVATE_KEY_BEGIN = "-----BEGIN " + "PRIVATE KEY-----"
_TEST_PRIVATE_KEY_END = "-----END " + "PRIVATE KEY-----"
_TEST_PRIVATE_KEY_BODY = "TEST-ONLY-NOT-A-REAL-KEY"


# Each expected entity is represented by (type, exact substring).
CASES = [
    # ---------------------------------------------------------
    # Positive cases: sensitive data that should be detected
    # ---------------------------------------------------------
    {
        "name": "Email",
        "text": "Contact demo.user@example.com for support.",
        "expected": [("EMAIL", "demo.user@example.com")],
    },
    {
        "name": "IBAN",
        "text": "Test beneficiary IBAN: GB82WEST12345698765432.",
        "expected": [("IBAN", "GB82WEST12345698765432")],
    },
    {
        "name": "IPv4 address",
        "text": "Example IPv4 address: 192.0.2.15.",
        "expected": [("IP_ADDRESS", "192.0.2.15")],
    },
    {
        "name": "MAC address",
        "text": "Example MAC address: 02:00:00:00:00:01.",
        "expected": [("MAC_ADDRESS", "02:00:00:00:00:01")],
    },
    {
        "name": "US SSN",
        "text": "Synthetic test SSN: 000-00-0000.",
        "expected": [("US_SSN", "000-00-0000")],
    },
    {
        "name": "Person",
        "text": "Please contact John Smith before delivery.",
        "expected": [("PERSON", "John Smith")],
    },
    {
        "name": "Personal location",
        "text": "I live in the United States.",
        "expected": [("LOCATION", "United States")],
    },
    {
        "name": "Medical information",
        "text": "The patient has diabetes and takes metformin.",
        "expected": [
            ("MEDICAL_INFO", "diabetes and takes metformin")
        ],
    },
    {
        "name": "Confidential business information",
        "text": (
            "Our fictional company has an unannounced "
            "acquisition plan."
        ),
        "expected": [
            (
                "CONFIDENTIAL_BUSINESS",
                "unannounced acquisition plan",
            )
        ],
    },
    {
        "name": "Bearer token",
        "text": (
            "Authorization: Bearer "
            "demo_token_12345678901234567890"
        ),
        "expected": [
            ("API_KEY", "demo_token_12345678901234567890")
        ],
    },
    {
        "name": "Database URL",
        "text": (
            "DATABASE_URL=postgresql://demo:"
            "DEMO_PASSWORD_PLACEHOLDER@db.example.invalid:"
            "5432/sampledb"
        ),
        "expected": [
            (
                "API_KEY",
                "postgresql://demo:DEMO_PASSWORD_PLACEHOLDER"
                "@db.example.invalid:5432/sampledb",
            )
        ],
    },
    {
        "name": "Private key block",
        "text": "\n".join(
            (
                _TEST_PRIVATE_KEY_BEGIN,
                _TEST_PRIVATE_KEY_BODY,
                _TEST_PRIVATE_KEY_END,
            )
        ),
        "expected": [
            (
                "API_KEY",
                "\n".join(
                    (
                        _TEST_PRIVATE_KEY_BEGIN,
                        _TEST_PRIVATE_KEY_BODY,
                        _TEST_PRIVATE_KEY_END,
                    )
                ),
            )
        ],
    },
    {
        "name": "Test credit card",
        "text": "Test card: 4111 1111 1111 1111.",
        "expected": [
            ("CARD", "4111 1111 1111 1111")
        ],
    },
    {
        "name": "Test phone",
        "text": "Call the fictional test line +1 202-555-0100.",
        "expected": [
            ("PHONE", "+1 202-555-0100")
        ],
    },

    # ---------------------------------------------------------
    # Additional global recognizer tests
    # ---------------------------------------------------------
    {
        "name": "Cryptocurrency wallet address",
        "text": (
            "Bitcoin wallet address: "
            "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"
        ),
        "expected": [
            ("CRYPTO", "1BoatSLRHtKNngkdXEeobR76b53LETtpyT")
        ],
    },
    {
        "name": "Personal religious affiliation",
        "text": "The fictional person is Muslim.",
        "expected": [("NRP", "Muslim")],
    },
    {
        "name": "DEA medical license format",
        "text": "DEA registration number: AB1234563",
        "expected": [
            ("MEDICAL_LICENSE", "AB1234563")
        ],
    },
    {
        "name": "Invalid DEA checksum",
        "text": "DEA registration number: AB1234567",
        "expected": [],
        "negative": True,
    },

    # ---------------------------------------------------------
    # Original negative cases: ordinary text should not be
    # flagged as sensitive
    # ---------------------------------------------------------
    {
        "name": "Broad location used as a team name",
        "text": (
            "The United States team is preparing a public report."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Ordinary company news",
        "text": (
            "Our fictional company published its annual report "
            "last week."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Ordinary public documentation",
        "text": (
            "Please read the public documentation before "
            "the next meeting."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Ordinary version number",
        "text": "Version 3.14 was released on Friday.",
        "expected": [],
        "negative": True,
    },
    {
        "name": "General wellness discussion",
        "text": (
            "Everyone discussed general wellness at the "
            "public meeting."
        ),
        "expected": [],
        "negative": True,
    },

    # ---------------------------------------------------------
    # Additional difficult negative cases
    # ---------------------------------------------------------
    {
        "name": "Medical topic without personal information",
        "text": (
            "The article discusses diabetes in a biology textbook."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Publicly announced acquisition",
        "text": (
            "The company publicly announced its acquisition last year."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Location in ordinary news",
        "text": (
            "The London team published its annual report."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Software version",
        "text": (
            "The application version is 3.14.159."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "SSN-shaped ticket reference",
        "text": (
            "Ticket reference 000-00-0000 is invalid."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "General API security documentation",
        "text": (
            "The manual explains how API keys work "
            "without providing credentials."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Public medical research",
        "text": (
            "Researchers published a study about medical treatments."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Ordinary business report",
        "text": (
            "Our fictional company published its quarterly "
            "revenue report."
        ),
        "expected": [],
        "negative": True,
    },
    {
        "name": "Bitcoin mentioned in ordinary documentation",
        "text": (
            "Bitcoin is discussed in the public documentation."
        ),
        "expected": [],
        "negative": True,
    },
]


def overlaps(prediction, gold):
    """Check whether prediction and gold spans sufficiently overlap."""
    overlap = (
        min(prediction["end"], gold["end"])
        - max(prediction["start"], gold["start"])
    )

    return (
        prediction["type"] == gold["type"]
        and overlap >= 0.5 * (gold["end"] - gold["start"])
    )


def metric(numerator, denominator):
    """Return a metric value, using zero for an undefined denominator."""
    return numerator / denominator if denominator else 0.0


def main():
    counts = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0}
    )

    totals = {"tp": 0, "fp": 0, "fn": 0}
    timings = []

    negative_total = 0
    negative_flagged = 0

    print("KAVACH GLOBAL DETECTOR — SYNTHETIC BENCHMARK")
    print("=" * 52)
    print(f"Total cases: {len(CASES)}")

    for case in CASES:
        text = case["text"]
        expected = case["expected"]
        is_negative = case.get("negative", False)

        if is_negative:
            negative_total += 1

        started = time.perf_counter()
        result = analyze_global(text, mode="label")
        elapsed_ms = (time.perf_counter() - started) * 1000
        timings.append(elapsed_ms)

        predictions = []

        for finding in result.get("findings", []):
            if not isinstance(finding, dict):
                continue

            start = finding.get("start")
            end = finding.get("end")
            entity_type = finding.get("type")

            if (
                isinstance(start, int)
                and isinstance(end, int)
                and end > start
                and entity_type
            ):
                predictions.append({
                    "type": entity_type,
                    "start": start,
                    "end": end,
                })

        # A negative prompt is flagged if any finding is returned.
        if is_negative and predictions:
            negative_flagged += 1

        used = set()

        # Match expected findings to actual predictions.
        for entity_type, value in expected:
            start = text.find(value)

            if start < 0:
                raise ValueError(
                    f"Expected substring missing in {case['name']}"
                )

            gold = {
                "type": entity_type,
                "start": start,
                "end": start + len(value),
            }

            hit = next(
                (
                    i
                    for i, prediction in enumerate(predictions)
                    if i not in used and overlaps(prediction, gold)
                ),
                None,
            )

            if hit is None:
                counts[entity_type]["fn"] += 1
                totals["fn"] += 1
            else:
                used.add(hit)
                counts[entity_type]["tp"] += 1
                totals["tp"] += 1

        # Every unmatched prediction is a false positive.
        for i, prediction in enumerate(predictions):
            if i not in used:
                entity_type = prediction["type"]
                counts[entity_type]["fp"] += 1
                totals["fp"] += 1

        expected_types = (
            ", ".join(entity_type for entity_type, _ in expected)
            or "NONE"
        )

        detected_types = (
            ", ".join(prediction["type"] for prediction in predictions)
            or "NONE"
        )

        print(
            f"{case['name']}: "
            f"expected=[{expected_types}] "
            f"detected=[{detected_types}]"
        )

    # ---------------------------------------------------------
    # Overall metrics
    # ---------------------------------------------------------
    print("\nMETRICS")
    print("-" * 52)

    precision = metric(
        totals["tp"],
        totals["tp"] + totals["fp"],
    )

    recall = metric(
        totals["tp"],
        totals["tp"] + totals["fn"],
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    print(
        f"Overall: TP={totals['tp']} "
        f"FP={totals['fp']} FN={totals['fn']}"
    )

    print(
        f"Precision={precision:.3f} "
        f"Recall={recall:.3f} "
        f"F1={f1:.3f}"
    )

    # ---------------------------------------------------------
    # Per-type metrics
    # ---------------------------------------------------------
    print("\nPER-TYPE METRICS")
    print("-" * 52)

    for entity_type in sorted(counts):
        c = counts[entity_type]

        p = metric(
            c["tp"],
            c["tp"] + c["fp"],
        )

        r = metric(
            c["tp"],
            c["tp"] + c["fn"],
        )

        f = (
            2 * p * r / (p + r)
            if p + r
            else 0.0
        )

        print(
            f"{entity_type}: "
            f"P={p:.3f} R={r:.3f} F1={f:.3f} "
            f"(TP={c['tp']}, FP={c['fp']}, FN={c['fn']})"
        )

    # ---------------------------------------------------------
    # Negative prompt performance
    # ---------------------------------------------------------
    false_positive_rate = metric(
        negative_flagged,
        negative_total,
    )

    print("\nNEGATIVE CASES")
    print("-" * 52)

    print(
        f"Flagged {negative_flagged}/{negative_total} "
        f"negative prompts "
        f"(prompt-level false-positive rate="
        f"{false_positive_rate:.3f})"
    )

    # ---------------------------------------------------------
    # Latency
    # ---------------------------------------------------------
    print(
        f"\nMedian scan latency: {median(timings):.3f} ms"
    )

    print("No benchmark prompts or reports were saved to disk.")
    print(
        "Note: this is a small synthetic benchmark, "
        "not evidence of universal detection coverage."
    )


if __name__ == "__main__":
    main()