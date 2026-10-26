import json
import unittest

from eval.run import _error_record


class ErrorMetadataTests(unittest.TestCase):

    def setUp(self):
        self.private_marker = "SYNTHETIC_PRIVATE_TEST_MARKER"
        self.row = {
            "id": 17,
            "lang": "en",
            "tag": "real",
            "text": f"Contact {self.private_marker}",
        }

    def assert_no_raw_payload(self, record):
        forbidden_fields = {
            "text",
            "gold",
            "pred",
            "raw_value",
            "entity_value",
        }

        self.assertTrue(forbidden_fields.isdisjoint(record.keys()))
        self.assertNotIn(
            self.private_marker,
            json.dumps(record),
        )

    def test_false_negative_metadata(self):
        end = len(self.row["text"])

        record = _error_record(
            "kavach",
            "FN",
            self.row,
            expected_type="EMAIL",
            predicted_type=None,
            expected_span=(8, end),
        )

        self.assertEqual(record["kind"], "FN")
        self.assertEqual(record["expected_type"], "EMAIL")
        self.assertIsNone(record["predicted_type"])
        self.assertEqual(record["expected_span"], [8, end])
        self.assertIsNone(record["predicted_span"])
        self.assert_no_raw_payload(record)

    def test_false_positive_metadata(self):
        record = _error_record(
            "presidio",
            "FP",
            self.row,
            expected_type=None,
            predicted_type="AADHAAR",
            predicted_span=(8, 20),
        )

        self.assertEqual(record["kind"], "FP")
        self.assertIsNone(record["expected_type"])
        self.assertEqual(record["predicted_type"], "AADHAAR")
        self.assertIsNone(record["expected_span"])
        self.assertEqual(record["predicted_span"], [8, 20])
        self.assert_no_raw_payload(record)


if __name__ == "__main__":
    unittest.main()