import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "validate_blind_gold.py"


def rows(positive=21, negative=9):
    types = ["AADHAAR", "PAN", "PHONE", "CARD", "EMAIL", "UPI_ID", "GSTIN", "IFSC", "API_KEY"]
    out = []
    for i in range(positive):
        tag = "tricky" if i % 3 == 0 else "real"
        out.append(f"en:{tag} | Synthetic fictional scenario {i} [[{types[i % len(types)]}:SYNTH{i:03d}]]")
    for i in range(negative):
        out.append(f"en:neg | Fictional reference REF-{i:05d} status request")
    return "\n".join(out) + "\n"


class BlindGoldValidatorTests(unittest.TestCase):
    def run_validator(self, content, participants=3):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "gold_hidden.txt"
            path.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(path), "--participants", str(participants)],
                capture_output=True, text=True, check=False,
            )

    def test_accepts_30_row_three_person_file(self):
        result = self.run_validator(rows())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VALIDATION PASSED", result.stdout)

    def test_rejects_positive_row_without_annotation(self):
        content = rows().replace("[[AADHAAR:SYNTH000]]", "SYNTH000", 1)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("positive row must contain", result.stdout)

    def test_rejects_negative_row_with_annotation(self):
        content = rows().replace("Fictional reference REF-00000 status request", "Fictional [[EMAIL:x@example.test]] reference", 1)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("negative row must not contain", result.stdout)

    def test_rejects_wrong_row_count(self):
        result = self.run_validator(rows(20, 9))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected 21 positive rows", result.stdout)

    def test_accepts_40_row_four_person_file(self):
        result = self.run_validator(rows(28, 12), participants=4)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VALIDATION PASSED", result.stdout)

    def test_rejects_unsupported_entity_type(self):
        content = rows().replace("[[AADHAAR:SYNTH000]]", "[[PASSPORT:SYNTH000]]", 1)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported entity type", result.stdout)

    def test_rejects_unmatched_entity_marker(self):
        content = rows().replace("[[AADHAAR:SYNTH000]]", "[[AADHAAR:SYNTH000]", 1)
        result = self.run_validator(content)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("malformed or unmatched", result.stdout)

    def test_does_not_print_prompt_text(self):
        secretish = "Unique synthetic sentinel KAVACH_NEVER_PRINT_987654"
        content = rows().replace("Synthetic fictional scenario 0", secretish, 1)
        result = self.run_validator(content)
        self.assertNotIn(secretish, result.stdout)
        self.assertNotIn(secretish, result.stderr)


if __name__ == "__main__":
    unittest.main()
