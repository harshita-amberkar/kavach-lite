import unittest

from kavach import analyze, scan
from kavach.detectors import (
    verhoeff_check_digit,
    gstin_check_char,
    luhn_valid,
)


def aadhaar(body="23456789012"):
    return body + verhoeff_check_digit(body)


def types(text):
    return [f.type for f in scan(text)]


class DetectorTests(unittest.TestCase):
    def test_valid_aadhaar_detected_with_spaces(self):
        a = aadhaar()
        spaced = f"{a[:4]} {a[4:8]} {a[8:]}"
        self.assertEqual(
            types(f"my aadhaar is {spaced}"),
            ["AADHAAR"],
        )

    def test_invalid_12_digit_number_not_flagged(self):
        bad = "23456789012" + str(
            (int(verhoeff_check_digit("23456789012")) + 1) % 10
        )
        self.assertEqual(
            types(f"Order id {bad} shipped"),
            [],
        )

    def test_unverified_number_flagged_only_with_context(self):
        bad = "23456789012" + str(
            (int(verhoeff_check_digit("23456789012")) + 1) % 10
        )
        self.assertEqual(
            types(f"Aadhaar: {bad}"),
            ["AADHAAR_POSSIBLE"],
        )

    def test_devanagari_digits(self):
        a = aadhaar().translate(
            str.maketrans("0123456789", "०१२३४५६७८९")
        )
        self.assertEqual(
            types(f"मेरा आधार {a} है"),
            ["AADHAAR"],
        )

    def test_pan_upi_ifsc_phone_email(self):
        t = (
            "PAN ABCPE1234F, pay ramesh@okaxis, "
            "IFSC HDFC0001234, call +91 98765 43210, "
            "mail a.b@corp.in"
        )
        self.assertEqual(
            sorted(types(t)),
            sorted(["PAN", "UPI_ID", "IFSC", "PHONE", "EMAIL"]),
        )

    def test_email_with_bank_domain_is_not_upi(self):
        self.assertEqual(
            types("write to user@sbi.co.in"),
            ["EMAIL"],
        )

    def test_card_luhn(self):
        self.assertTrue(luhn_valid("4111111111111111"))
        self.assertEqual(
            types("card 4111 1111 1111 1111"),
            ["CARD"],
        )
        self.assertEqual(
            types("card 4111 1111 1111 1112"),
            [],
        )

    def test_gstin_checksum(self):
        base = "27AAPFU0939F1Z"
        g = base + gstin_check_char(base)

        self.assertEqual(
            types(f"GSTIN {g}"),
            ["GSTIN"],
        )

        bad = base + ("A" if g[-1] != "A" else "B")
        self.assertEqual(
            types(f"GSTIN {bad}"),
            [],
        )

    def test_secrets(self):
        # Construct the synthetic AWS-style key at runtime so the
        # source-code credential scanner doesn't match a full literal.
        test_key = "AKIA" + ("A" * 16)

        self.assertEqual(
            types("key " + test_key),
            ["API_KEY"],
        )
        self.assertEqual(
            types("password = hunter2hunter2"),
            ["API_KEY"],
        )

    def test_password_phrase_detection(self):
        self.assertIn(
            "PASSWORD",
            types("My password is BlueSky@42"),
        )
        self.assertNotIn(
            "PASSWORD",
            types("I forgot my password today"),
        )

    def test_otp_detection(self):
        self.assertIn(
            "OTP",
            types("Your verification code is 482193"),
        )
        self.assertNotIn(
            "OTP",
            types("The verification code expired yesterday"),
        )

    def test_passport_detection(self):
        self.assertIn(
            "PASSPORT",
            types("Passport number: N1234567"),
        )
        self.assertNotIn(
            "PASSPORT",
            types("The passport office opens tomorrow"),
        )

    def test_masking_and_risk(self):
        result = analyze(
            f"aadhaar {aadhaar()} email x@y.com"
        )
        self.assertIn("[AADHAAR]", result["masked_text"])
        self.assertIn("[EMAIL]", result["masked_text"])
        self.assertEqual(result["risk"]["level"], "high")

    def test_clean_text(self):
        result = analyze(
            "Summarise this quarterly report in 5 bullets."
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["risk"]["level"], "none")

    def test_card_whose_prefix_passes_aadhaar_checksum_is_still_a_card(self):
        pre = "42345678901"
        first12 = pre + verhoeff_check_digit(pre)

        card = next(
            first12 + f"{n:04d}"
            for n in range(10000)
            if luhn_valid(first12 + f"{n:04d}")
        )

        spaced = " ".join(
            card[i:i + 4]
            for i in range(0, 16, 4)
        )

        self.assertEqual(
            types(f"card {spaced}"),
            ["CARD"],
        )

    def test_lowercase_pan(self):
        self.assertEqual(
            types("pan abcpe1234f"),
            ["PAN"],
        )


if __name__ == "__main__":
    unittest.main()