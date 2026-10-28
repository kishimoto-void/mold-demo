import json
import unittest
from pathlib import Path
from top_mold.engine import decide


class GoldenConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name("conformance_cases.json")
        cls.cases = json.loads(path.read_text(encoding="utf-8"))

    def test_all_golden_cases(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                result = decide(case["input"]).to_dict()
                if "primary" in case:
                    self.assertEqual(result["primary_mode"], case["primary"])
                if "secondary" in case:
                    self.assertEqual(result["secondary_modes"], case["secondary"])
                if "contains_modes" in case:
                    observed = {result["primary_mode"], *result["secondary_modes"]}
                    self.assertTrue(set(case["contains_modes"]).issubset(observed), observed)
                for key in ("free_opinion", "depth", "output_contract", "output_only"):
                    if key in case:
                        self.assertEqual(result[key], case[key])


if __name__ == "__main__":
    unittest.main(verbosity=2)
