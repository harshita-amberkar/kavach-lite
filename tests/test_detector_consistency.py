import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from kavach.detectors import scan
from kavach.global_detector import analyze_global


FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "extension"
    / "tests"
    / "detection_consistency.json"
)


class DetectorConsistencyTests(unittest.TestCase):
    def test_native_and_global_results_match_shared_cases(self):
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

        for case in cases:
            with self.subTest(case=case["name"]):
                native_types = [item.type for item in scan(case["text"])]
                self.assertEqual(native_types, case["native_types"])

                presidio = case.get("presidio")
                predictions = []
                if presidio:
                    start = case["text"].index(presidio["value"])
                    predictions.append(SimpleNamespace(
                        entity_type=presidio["entity"],
                        start=start,
                        end=start + len(presidio["value"]),
                        score=0.99,
                    ))

                class FixtureAnalyzer:
                    def analyze(self, text, language, entities):
                        return predictions

                enabled_entities = (
                    (presidio["entity"],)
                    if presidio else ("PERSON",)
                )

                with patch(
                    "kavach.global_detector._get_analyzer",
                    return_value=(FixtureAnalyzer(), enabled_entities),
                ):
                    result = analyze_global(case["text"])

                global_types = [
                    item["type"] for item in result["findings"]
                ]
                self.assertEqual(global_types, case["global_types"])
                self.assertEqual(
                    result["global_detection"]["status"],
                    "ok",
                )


if __name__ == "__main__":
    unittest.main()
