import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NormativeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.top = (ROOT / "TOP_MOLD.md").read_text(encoding="utf-8")
        cls.readme = (ROOT / "LLM_README.md").read_text(encoding="utf-8")
        cls.config = json.loads((ROOT / "config" / "top_mold.json").read_text(encoding="utf-8"))

    def test_all_five_modes_are_documented(self):
        for name in ("work", "verify", "design", "research", "chat"):
            with self.subTest(mode=name):
                self.assertIn(f"`{name}`", self.top)

    def test_mode_depth_and_output_are_independent(self):
        self.assertIn("Independent control axes", self.top)
        self.assertIn("independent", self.top.lower())

    def test_free_opinion_does_not_cancel_verification(self):
        self.assertIn("MUST NOT erase a simultaneous request for strict verification", self.top)

    def test_integrity_rules_are_explicit(self):
        for phrase in (
            "NEVER claim a test ran unless it actually ran",
            "Do not claim files were read",
            "preferences were saved",
        ):
            with self.subTest(phrase=phrase):
                combined = self.top + self.readme
                self.assertIn(phrase, combined)

    def test_human_analysis_is_opt_in_by_default(self):
        self.assertEqual(self.config["human_analysis"]["default"], "opt_in")

    def test_pay_forward_and_portability_are_recorded(self):
        self.assertIn("pass forward", self.config["principles"]["pay_forward_design"])
        self.assertIn("model-neutral", self.top.lower())

    def test_user_dignity_is_protected_in_the_contract(self):
        self.assertIn("Correct errors without humiliating the user", self.top)

    def test_responsibility_boundary_does_not_shift_all_blame_to_user(self):
        self.assertIn("MUST NOT be used to blame the user for system defects", self.top)

    def test_llm_onboarding_mentions_testing_and_change_summary(self):
        self.assertIn("add a conformance case", self.readme)
        self.assertIn("change summary", self.readme.lower())

    def test_config_dial_values_are_in_range(self):
        for key, value in self.config["dials"].items():
            if key == "scale":
                continue
            with self.subTest(dial=key):
                self.assertIsInstance(value, int)
                self.assertGreaterEqual(value, self.config["dials"]["scale"]["min"])
                self.assertLessEqual(value, self.config["dials"]["scale"]["max"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
