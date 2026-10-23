import unittest
from eval.gen import generate

class GenTests(unittest.TestCase):
    def test_spans_point_at_values(self):
        for r in generate(300, seed=1):
            for e in r["entities"]:
                v = r["text"][e["start"]:e["end"]]
                self.assertTrue(len(v) >= 6, (r, e))
    def test_deterministic_and_has_negatives(self):
        a, b = generate(100, seed=3), generate(100, seed=3)
        self.assertEqual(a, b)
        self.assertTrue(any(not r["entities"] for r in a))
if __name__ == "__main__": unittest.main()
