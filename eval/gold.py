
"""Load hand-written gold prompts.

Format:
    lang[:tag] | text with [[TYPE:value]] marks

Tags:
    real   - realistic positive
    tricky - hard positive
    neg    - look-alike negative

If no tag is given, use 'real' when marks exist, otherwise 'neg'.
Lines starting with # are comments.
Unmarked text is treated as NOT sensitive.
"""

import re
from pathlib import Path

TYPES = {
    "AADHAAR", "PAN", "PHONE", "CARD", "EMAIL",
    "UPI_ID", "GSTIN", "IFSC", "API_KEY",
}

TAGS = {"real", "tricky", "neg"}

_MARK = re.compile(r"\[\[([A-Z_]+):(.*?)\]\]")


def load(path="eval/gold/gold.txt", split="test"):
    rows = []

    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\r\n")

            if not line.strip() or line.lstrip().startswith("#"):
                continue

            head, sep, raw = line.partition("|")

            if not sep:
                raise ValueError(f"line {n}: expected 'lang | text'")

            lang, _, tag = head.strip().partition(":")
            lang = lang.strip()
            tag = tag.strip()
            raw = raw.strip()

            text = ""
            entities = []
            pos = 0

            for match in _MARK.finditer(raw):
                entity_type = match.group(1)
                entity_value = match.group(2)

                if entity_type not in TYPES:
                    raise ValueError(
                        f"line {n}: unknown type {entity_type}"
                    )

                if not entity_value:
                    raise ValueError(
                        f"line {n}: empty value for {entity_type}"
                    )

                text += raw[pos:match.start()]

                start = len(text)
                text += entity_value
                end = len(text)

                entities.append({
                    "type": entity_type,
                    "start": start,
                    "end": end,
                })

                pos = match.end()

            text += raw[pos:]

            if "[[" in text or "]]" in text:
                raise ValueError(
                    f"line {n}: unmatched [[ or ]] "
                    "(check the mark syntax)"
                )

            if not lang:
                raise ValueError(
                    f"line {n}: missing language before '|'"
                )

            tag = tag or ("real" if entities else "neg")

            if tag not in TAGS:
                raise ValueError(
                    f"line {n}: unknown tag '{tag}' "
                    "(use real, tricky or neg)"
                )

            if tag == "neg" and entities:
                raise ValueError(
                    f"line {n}: tag 'neg' but the line has [[...]] marks"
                )

            if tag in ("real", "tricky") and not entities:
                raise ValueError(
                    f"line {n}: tag '{tag}' but the line has no [[...]] marks"
                )

            rows.append({
                "id": n,
                "lang": lang,
                "tag": tag,
                "text": text,
                "entities": entities,
                "split": split,
            })

    return rows
