import unittest

from kavach import scan


class HoldoutFalsePositiveTests(unittest.TestCase):

    def test_batch_timestamp_not_detected_as_aadhaar(self):
        text = (
            "Shipment batch 202610261532 is a timestamp, "
            "not an identity number."
        )

        findings = scan(text)

        self.assertFalse(
            any(
                finding.type in {"AADHAAR", "AADHAAR_POSSIBLE"}
                for finding in findings
            ),
            "A batch timestamp should not be classified as Aadhaar.",
        )

    def test_redacted_placeholder_not_detected_as_api_key(self):
        text = (
            "The source-code example contains "
            "sk-REDACTED-PLACEHOLDER, not a usable API key."
        )

        findings = scan(text)

        self.assertFalse(
            any(finding.type == "API_KEY" for finding in findings),
            "An explicit redacted placeholder should not be an API key.",
        )

    def test_credential_like_token_is_still_detected(self):
        text = (
            "Token: "
            "sk-proj-kavachholdoutA81f29d47c12b36e75f90a14c8276d11"
        )

        findings = scan(text)

        self.assertTrue(
            any(finding.type == "API_KEY" for finding in findings),
            "Placeholder filtering must not disable API-key detection.",
        )


if __name__ == "__main__":
    unittest.main()