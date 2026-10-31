#!/usr/bin/env python3
"""Validate KAVACH gold-file formatting without running the detector.

The script intentionally never prints prompt text or marked values.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ALLOWED_TYPES = {
    "AADHAAR", "PAN", "PHONE", "CARD", "EMAIL",
    "UPI_ID", "GSTIN", "IFSC", "API_KEY",
}
HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(real|tricky|neg)$")
ENTITY_RE = re.compile(r"\[\[([A-Z][A-Z0-9_]*):([^\]\r\n]+)\]\]")


def validate(path: Path, participants: int) -> int:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        print(f"ERROR: cannot read input file: {exc}", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print("ERROR: file must be valid UTF-8 text.", file=sys.stderr)
        return 2

    rows = []
    problems: list[str] = []
    for line_no, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        if raw.lstrip().startswith("#"):
            problems.append(f"line {line_no}: comments/headings are not allowed in the gold file")
            continue
        if "|" not in raw:
            problems.append(f"line {line_no}: missing '|' separator")
            continue
        header, text = raw.split("|", 1)
        header = header.strip()
        text = text.strip()
        match = HEADER_RE.fullmatch(header)
        if not match:
            problems.append(f"line {line_no}: expected explicit lang:real|tricky|neg tag")
            continue
        lang, tag = match.groups()
        if not text:
            problems.append(f"line {line_no}: prompt text is empty")
            continue
        entities = list(ENTITY_RE.finditer(text))
        malformed = (
            text.count("[[") != len(entities)
            or text.count("]]" ) != len(entities)
        )
        if malformed:
            problems.append(f"line {line_no}: malformed or unmatched entity annotation")
            continue
        invalid_types = sorted({m.group(1) for m in entities if m.group(1) not in ALLOWED_TYPES})
        empty_values = any(not m.group(2).strip() for m in entities)
        if invalid_types:
            problems.append(f"line {line_no}: unsupported entity type(s): {', '.join(invalid_types)}")
            continue
        if empty_values:
            problems.append(f"line {line_no}: entity annotation has an empty value")
            continue
        if tag == "neg" and entities:
            problems.append(f"line {line_no}: negative row must not contain entity markers")
            continue
        if tag in {"real", "tricky"} and not entities:
            problems.append(f"line {line_no}: positive row must contain at least one entity marker")
            continue
        plain = ENTITY_RE.sub(lambda m: m.group(2), text)
        fingerprint = re.sub(r"\s+", " ", plain).strip().casefold()
        rows.append({"line": line_no, "lang": lang.lower(), "tag": tag, "types": [m.group(1) for m in entities], "fingerprint": fingerprint})

    fingerprints = Counter(row["fingerprint"] for row in rows)
    duplicate_lines = [row["line"] for row in rows if fingerprints[row["fingerprint"]] > 1]
    counts = Counter(row["tag"] for row in rows)
    type_counts = Counter(t for row in rows for t in row["types"])
    expected_positive = participants * 7
    expected_negative = participants * 3

    if counts["real"] + counts["tricky"] != expected_positive:
        problems.append(f"expected {expected_positive} positive rows for {participants} participants; found {counts['real'] + counts['tricky']}")
    if counts["neg"] != expected_negative:
        problems.append(f"expected {expected_negative} negative rows for {participants} participants; found {counts['neg']}")
    if duplicate_lines:
        problems.append("possible duplicate prompt rows at line(s): " + ", ".join(map(str, sorted(set(duplicate_lines)))))

    print(f"Rows accepted: {len(rows)}")
    print(f"Tags: real={counts['real']}, tricky={counts['tricky']}, neg={counts['neg']}")
    print("Languages: " + (", ".join(f"{k}={v}" for k, v in sorted(Counter(r['lang'] for r in rows).items())) or "none"))
    print("Entity annotations: " + (", ".join(f"{k}={v}" for k, v in sorted(type_counts.items())) or "none"))
    if problems:
        print("\nVALIDATION FAILED:")
        for problem in problems:
            print(f"- {problem}")
        print("Prompt contents and synthetic values were not printed.")
        return 1
    missing = sorted(ALLOWED_TYPES - set(type_counts))
    print("\nVALIDATION PASSED: format and target row counts are valid.")
    if missing:
        print("Coverage note: no annotated examples for " + ", ".join(missing))
    print("Prompt contents and synthetic values were not printed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gold_file", type=Path)
    parser.add_argument("--participants", type=int, choices=(3, 4), default=3)
    args = parser.parse_args()
    return validate(args.gold_file, args.participants)


if __name__ == "__main__":
    raise SystemExit(main())
