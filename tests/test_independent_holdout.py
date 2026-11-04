import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval.independent_holdout import run as holdout


class IndependentHoldoutValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "dataset.jsonl"

    def write_rows(self, rows):
        content = "".join(json.dumps(row) + "\n" for row in rows)
        self.path.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.path.with_suffix(".jsonl.sha256").write_text(digest + "  dataset.jsonl\n", encoding="ascii")
        return digest

    def test_approved_dataset_matches_pinned_hash(self):
        rows, digest = holdout._load_and_verify(holdout.DEFAULT_DATASET)
        self.assertEqual(digest, holdout.APPROVED_DATASET_SHA256)
        self.assertEqual(len(rows), 60)

    def test_unapproved_dataset_is_rejected_even_with_matching_sidecar(self):
        digest = self.write_rows([{"id": 1, "tag": "neg", "text": "fixture", "entities": []}])
        self.assertNotEqual(digest, holdout.APPROVED_DATASET_SHA256)
        with self.assertRaisesRegex(ValueError, "pinned approved"):
            holdout._load_and_verify(self.path)

    def test_positive_without_gold_is_rejected(self):
        digest = self.write_rows([{"id": 1, "tag": "real", "text": "fixture", "entities": []}])
        with patch.object(holdout, "APPROVED_DATASET_SHA256", digest):
            with self.assertRaisesRegex(ValueError, "require gold entities"):
                holdout._load_and_verify(self.path)

    def test_empty_or_out_of_bounds_annotation_is_rejected(self):
        for entity in (
            {"type": "EMAIL", "start": 0, "end": 0},
            {"type": "EMAIL", "start": 0, "end": 99},
            {"type": "EMAIL", "start": 0, "end": 1},
        ):
            rows = [{"id": 1, "tag": "tricky", "text": " x ", "entities": [entity]}]
            digest = self.write_rows(rows)
            with patch.object(holdout, "APPROVED_DATASET_SHA256", digest):
                with self.assertRaises(ValueError):
                    holdout._load_and_verify(self.path)

    def test_negative_with_annotation_is_rejected(self):
        rows = [{"id": 1, "tag": "neg", "text": "x", "entities": [{"type": "EMAIL", "start": 0, "end": 1}]}]
        digest = self.write_rows(rows)
        with patch.object(holdout, "APPROVED_DATASET_SHA256", digest):
            with self.assertRaisesRegex(ValueError, "negative holdout"):
                holdout._load_and_verify(self.path)

    def test_every_detector_gets_same_warmup_prompt(self):
        seen = []
        systems = {"one": seen.append, "two": seen.append}
        holdout._prewarm_systems(systems)
        self.assertEqual(seen, [holdout.WARMUP_TEXT, holdout.WARMUP_TEXT])


if __name__ == "__main__":
    unittest.main()
