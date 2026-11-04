"""Generate a frozen, synthetic-only holdout for KAVACH evaluation.

Run from the repository root with:
    python -m eval.independent_holdout.generate

This generator has its own fixed seed and templates. It does not import or
read the existing gold sets, development corpus, or benchmark generator.
"""

import hashlib
import json
import random
from pathlib import Path

from kavach.detectors import gstin_check_char, luhn_valid, verhoeff_check_digit


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "eval" / "independent_holdout" / "dataset.jsonl"
SEED = 20261103


def _base58(data):
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = int.from_bytes(data, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    zeroes = len(data) - len(data.lstrip(b"\0"))
    return "1" * zeroes + (encoded or "1")


def _bitcoin_test_address(rng):
    """Make a checksum-valid, randomly generated Base58Check address."""
    import hashlib

    payload = b"\x00" + bytes(rng.randrange(256) for _ in range(20))
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return _base58(payload + checksum)


def _iban(rng):
    """Create a checksum-valid GB-shaped synthetic IBAN."""
    body = "GB00TEST" + "".join(str(rng.randrange(10)) for _ in range(14))
    rearranged = body[4:] + body[:4]
    numeric = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearranged)
    check = 98 - (int(numeric) % 97)
    return f"GB{check:02d}{body[4:]}"


def _row(row_id, tag, lang, prefix, value, suffix, entity_type=None, difficulty=None):
    text = prefix + value + suffix
    entities = []
    if entity_type:
        start = len(prefix)
        entities.append({"type": entity_type, "start": start, "end": start + len(value)})
    result = {
        "id": row_id,
        "lang": lang,
        "tag": tag,
        "text": text,
        "entities": entities,
        "split": "test",
    }
    if difficulty:
        result["difficulty"] = difficulty
    return result


def generate(seed=SEED):
    rng = random.Random(seed)
    rows = []

    def positive(entity_type, value, real, tricky, lang="en"):
        row_id = len(rows) + 1
        rows.append(_row(row_id, "real", lang, *real(value), entity_type))
        row_id = len(rows) + 1
        rows.append(_row(row_id, "tricky", lang, *tricky(value), entity_type, "contextual_positive"))

    # India-aware identifiers and contact/credential types.
    aadhaar_base = "23456789012"
    aadhaar = aadhaar_base + verhoeff_check_digit(aadhaar_base)
    positive("AADHAAR", aadhaar, lambda v: ("Synthetic identity fixture: Aadhaar ", v, " is used only in this test."), lambda v: ("Config field `identity.uid` contains ", v, " for parser validation."))

    pan = "QXZPF" + "".join(str(rng.randrange(10)) for _ in range(4)) + "L"
    positive("PAN", pan, lambda v: ("Sandbox tax profile PAN: ", v, "."), lambda v: ("The mock JSON property pan_number is set to ", v, " before schema validation."))

    phone = "6" + "".join(str(rng.randrange(10)) for _ in range(9))
    positive("PHONE", phone, lambda v: ("Fictional test contact line ", v, " can receive a callback."), lambda v: ("`contact.mobile` in the sample payload is ", v, "; do not call it."))

    card_base = "4" + "".join(str(rng.randrange(10)) for _ in range(14))
    card = card_base + next(str(digit) for digit in range(10) if luhn_valid(card_base + str(digit)))
    positive("CARD", card, lambda v: ("Synthetic checkout card number: ", v, "."), lambda v: ("A test fixture stores the payment_pan value ", v, " in a disabled form."))

    email = "mira." + "".join(rng.choice("abcdefghjkmnpqrstuvwxyz") for _ in range(5)) + "@example.invalid"
    positive("EMAIL", email, lambda v: ("Send the mock receipt to ", v, "."), lambda v: ("The config's `notify_to` entry is written as ", v, " for this dry run."))

    upi = "fixture" + str(rng.randrange(100, 999)) + "@okaxis"
    positive("UPI_ID", upi, lambda v: ("Sandbox transfer handle: ", v, "."), lambda v: ("The payment.destination field contains ", v, " in the mock request."))

    gst_base = "27" + "QXZ" + "P" + "R" + "".join(str(rng.randrange(10)) for _ in range(4)) + "L1Z"
    gstin = gst_base + gstin_check_char(gst_base)
    positive("GSTIN", gstin, lambda v: ("Synthetic supplier registration GSTIN ", v, " is listed on the sandbox invoice."), lambda v: ("The mock record has a `gst_registration` field of ", v, "; validate its shape."))

    ifsc = "QWER0" + "".join(rng.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(6))
    positive("IFSC", ifsc, lambda v: ("Test branch routing code: ", v, "."), lambda v: ("In the fabricated bank fixture, `ifsc_code` equals ", v, "."))

    api_key = "sk-holdout-" + "".join(rng.choice("abcdef0123456789") for _ in range(28))
    positive("API_KEY", api_key, lambda v: ("Synthetic API credential for parser testing: ", v, "."), lambda v: ("A disabled mock authorization setting contains `token=`", v, " and is never usable."))

    # Global types represented by the current KAVACH Global entity map.
    ssn = "987-65-" + "".join(str(rng.randrange(10)) for _ in range(4))
    positive("US_SSN", ssn, lambda v: ("Fictional onboarding SSN field: ", v, "."), lambda v: ("The mock profile's `ssn_value` property is ", v, "; no real profile exists."))

    iban = _iban(rng)
    positive("IBAN", iban, lambda v: ("Synthetic beneficiary IBAN ", v, " is in the test transfer."), lambda v: ("The sandbox payload field beneficiary_iban contains ", v, "."))

    ip = "198.51.100." + str(rng.randrange(1, 255))
    positive("IP_ADDRESS", ip, lambda v: ("Fictional access log client address: ", v, "."), lambda v: ("In this simulated incident, the account's source_ip was ", v, "."))

    mac = "02:7A:3B:" + ":".join(f"{rng.randrange(256):02X}" for _ in range(3))
    positive("MAC_ADDRESS", mac, lambda v: ("Mock device hardware address ", v, " was added to the test inventory."), lambda v: ("The fabricated endpoint record lists mac_address=", v, " for correlation."))

    positive("PERSON", "Xanthe Rowan", lambda v: ("The fictional applicant name: ", v, "."), lambda v: ("Contact ", v, " for the mock dry run."))
    positive("LOCATION", "Pune", lambda v: ("The imaginary account holder currently lives in ", v, "."), lambda v: ("A mock user now resides in ", v, "."))

    medical = "The fictional patient was diagnosed with asthma during a mock appointment."
    medical_start = medical.index("The fictional patient")
    medical_end = medical.index(".")
    rows.append({"id": len(rows) + 1, "lang": "en", "tag": "real", "text": medical, "entities": [{"type": "MEDICAL_INFO", "start": medical_start, "end": medical_end}], "split": "test"})
    medical = "A demo intake note says the patient is taking prescription medication for epilepsy."
    medical_start = medical.index("the patient")
    medical_end = medical.index(".")
    rows.append({"id": len(rows) + 1, "lang": "en", "tag": "tricky", "text": medical, "entities": [{"type": "MEDICAL_INFO", "start": medical_start, "end": medical_end}], "split": "test", "difficulty": "contextual_positive"})

    business = "The fictional company has a confidential supplier pricing strategy for next quarter."
    rows.append({"id": len(rows) + 1, "lang": "en", "tag": "real", "text": business, "entities": [{"type": "CONFIDENTIAL_BUSINESS", "start": 0, "end": business.index(".")}], "split": "test"})
    business = "Our mock company is preparing a proprietary product roadmap for its internal review."
    rows.append({"id": len(rows) + 1, "lang": "en", "tag": "tricky", "text": business, "entities": [{"type": "CONFIDENTIAL_BUSINESS", "start": 0, "end": business.index(".")}], "split": "test", "difficulty": "contextual_positive"})

    crypto = _bitcoin_test_address(rng)
    positive("CRYPTO", crypto, lambda v: ("Synthetic cryptocurrency receiving address: ", v, "."), lambda v: ("The mock wallet export sets `destination_address` to ", v, "."))

    positive("NRP", "Zoroastrianism", lambda v: ("The fictional profile is affiliated with ", v, "."), lambda v: ("The mock biography says the person practices ", v, "."))

    dea_prefix = "AB"
    dea_digits = "".join(str(rng.randrange(10)) for _ in range(6))
    dea_check = str((sum(int(dea_digits[i]) for i in (0, 2, 4)) + 2 * sum(int(dea_digits[i]) for i in (1, 3, 5))) % 10)
    dea = dea_prefix + dea_digits + dea_check
    positive("MEDICAL_LICENSE", dea, lambda v: ("Synthetic practitioner registration number: ", v, "."), lambda v: ("The mock clinic's provider_license field contains ", v, "."))

    # Negative prompts include lookalikes and benign discussion. All values
    # are invented; hard negatives intentionally resemble identifiers.
    negatives = [
        ("Ticket reference 987-65-4321 was rejected by the fictional workflow.", "hard_negative"),
        ("Inventory SKU QXZPF7314L belongs to a mock device, not a tax record.", "hard_negative"),
        ("The build identifier is 202611031532 and the release is version 7.4.2.", "hard_negative"),
        ("The documentation names API_KEY as a setting but supplies no credential.", "hard_negative"),
        ("A sample says email the team at user [at] example [dot] invalid.", "hard_negative"),
        ("The India support team published its ordinary weekly report.", "hard_negative"),
        ("A textbook chapter discusses asthma without describing a patient.", "hard_negative"),
        ("The fictional firm announced its public quarterly earnings yesterday.", "hard_negative"),
        ("A mock shipment uses order number 123456789012 and batch 70418.", "hard_negative"),
        ("The example UPI syntax is written as name [at] bank, not as an account.", "hard_negative"),
        ("This note compares public routing-code standards without listing a code.", "hard_negative"),
        ("The payment amount is 1,23,456.78 and the invoice is due next month.", "hard_negative"),
        ("A technical article explains how Bitcoin signatures work.", "hard_negative"),
        ("The fictional character Xanthe appears in a public story set in Pune.", "hard_negative"),
        ("The test bench stores MAC examples as XX:XX:XX:XX:XX:XX placeholders.", "hard_negative"),
        ("The sample network documentation reserves 198.51.100.0/24 for examples.", "hard_negative"),
        ("An ordinary meeting agenda includes a discussion of Jain history.", "hard_negative"),
        ("The mock configuration contains `token = [REDACTED]` as a placeholder.", "hard_negative"),
        ("The test form has an empty field called beneficiary_iban.", "hard_negative"),
        ("A generic registration guide describes how clinics renew licenses.", "hard_negative"),
    ]
    for text, difficulty in negatives:
        rows.append({"id": len(rows) + 1, "lang": "en", "tag": "neg", "text": text, "entities": [], "split": "test", "difficulty": difficulty})

    return rows


def write(path=OUTPUT):
    rows = generate()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(content, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    checksum_path.write_text(f"{digest}  {path.name}\n", encoding="ascii", newline="\n")
    print(f"rows={len(rows)} real={sum(r['tag'] == 'real' for r in rows)} tricky={sum(r['tag'] == 'tricky' for r in rows)} negative={sum(r['tag'] == 'neg' for r in rows)}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    write()
