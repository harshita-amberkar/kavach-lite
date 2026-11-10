import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

import kavach.global_detector as global_detector
from kavach.global_detector import analyze_global, preload_analyzer


class GlobalDetectorInitializationTests(unittest.TestCase):
    def test_preload_initializes_one_shared_analyzer_for_concurrent_scans(self):
        class FakeAnalyzer:
            def get_supported_entities(self, language):
                self.asserted_language = language
                return ["EMAIL_ADDRESS", "PHONE_NUMBER"]

        analyzer = FakeAnalyzer()
        with (
            patch.object(global_detector, "_ANALYZER_CACHE", None),
            patch.object(
                global_detector, "AnalyzerEngine", return_value=analyzer
            ) as factory,
        ):
            preload_duration = preload_analyzer()
            with ThreadPoolExecutor(max_workers=8) as pool:
                cached = list(pool.map(lambda _: global_detector._get_analyzer(), range(16)))

        self.assertGreaterEqual(preload_duration, 0)
        self.assertEqual(factory.call_count, 1)
        self.assertTrue(all(item[0] is analyzer for item in cached))
        self.assertEqual(cached[0][1], ("EMAIL_ADDRESS", "PHONE_NUMBER"))


class GlobalDetectorContextTests(unittest.TestCase):
    def analyze_with_mock(self, text, entity_type, value):
        start = text.index(value)
        prediction = SimpleNamespace(
            entity_type=entity_type,
            start=start,
            end=start + len(value),
            score=0.99,
        )

        class FakeAnalyzer:
            def analyze(self, text, language, entities):
                return [prediction]

        with patch(
            "kavach.global_detector._get_analyzer",
            return_value=(FakeAnalyzer(), (entity_type,)),
        ):
            return analyze_global(text)

    def detected_types(self, result):
        return [finding["type"] for finding in result["findings"]]

    def test_hinglish_particle_is_not_person(self):
        text = "is code ko optimize karo please"
        result = self.analyze_with_mock(text, "PERSON", "ko")
        self.assertNotIn("PERSON", self.detected_types(result))

    def test_devanagari_instruction_is_not_person(self):
        value = "\u092c\u093f\u0902\u0926\u0941\u0913\u0902 \u092e\u0947\u0902 \u0938\u092e\u091d\u093e\u090f\u0902"
        text = f"\u0915\u0943\u092a\u092f\u093e \u092f\u0939 \u0930\u093f\u092a\u094b\u0930\u094d\u091f \u092a\u093e\u0902\u091a {value}\u0964"
        self.assertFalse(value.isascii())
        result = self.analyze_with_mock(text, "PERSON", value)
        self.assertNotIn("PERSON", self.detected_types(result))

    def test_order_id_is_not_phone(self):
        value = "153100330923"
        text = f"Order ID {value} was dispatched today."
        result = self.analyze_with_mock(text, "PHONE_NUMBER", value)
        self.assertNotIn("PHONE", self.detected_types(result))

    def test_contextually_labelled_english_name_is_kept(self):
        value = "John Smith"
        text = f"My name is {value}."
        result = self.analyze_with_mock(text, "PERSON", value)
        self.assertIn("PERSON", self.detected_types(result))

    def test_phone_without_identifier_label_is_kept(self):
        value = "153100330923"
        text = f"Call me at {value} tomorrow."
        result = self.analyze_with_mock(text, "PHONE_NUMBER", value)
        self.assertIn("PHONE", self.detected_types(result))

    def test_global_results_include_separate_detection_timings(self):
        result = self.analyze_with_mock(
            "Contact sample@example.com",
            "EMAIL_ADDRESS",
            "sample@example.com",
        )

        performance = result["performance"]
        for field in (
            "native_detection_ms",
            "presidio_initialization_ms",
            "presidio_detection_ms",
            "global_detection_ms",
        ):
            self.assertIsInstance(performance[field], float)
            self.assertGreaterEqual(performance[field], 0)

    def test_analyzer_initialization_failure_keeps_deterministic_fallback(self):
        with patch(
            "kavach.global_detector._get_analyzer",
            side_effect=RuntimeError("analyzer unavailable"),
        ):
            result = analyze_global("Contact sample@example.com")

        self.assertEqual(result["global_detection"]["status"], "unavailable")
        self.assertIn("EMAIL", self.detected_types(result))
        self.assertGreaterEqual(
            result["performance"]["presidio_initialization_ms"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
