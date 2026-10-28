import json
import unittest
from pathlib import Path
from top_mold.engine import load_config, validate_config

ROOT = Path(__file__).resolve().parents[1]


class V02ConfigurationTests(unittest.TestCase):
    def test_v02_config_has_independent_personalization_dials(self):
        cfg = load_config()
        self.assertIn("personalization_depth", cfg["dials"])
        self.assertIn("proactiveness", cfg["dials"])
        self.assertIn("initiative", cfg["dials"])
        self.assertIn("retention_preference", cfg["dials"])
        self.assertIn("personalization_and_proactiveness_are_independent", cfg["principles"])

    def test_domain_profiles_are_separately_configured(self):
        cfg = load_config()
        self.assertNotEqual(cfg["domain_profiles"]["shopping"]["depth"], cfg["domain_profiles"]["general"]["depth"])
        self.assertIn("learning", cfg["domain_profiles"])
        self.assertIn("events_entertainment", cfg["domain_profiles"])

    def test_invalid_domain_dial_is_rejected(self):
        cfg = load_config()
        cfg["domain_profiles"]["shopping"]["proactiveness"] = 101
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_invalid_new_global_dial_is_rejected(self):
        cfg = load_config()
        cfg["dials"]["personalization_depth"] = True
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_memory_policy_is_conservative_by_default(self):
        policy = load_config()["memory_policy"]
        self.assertEqual(policy["transient_content_default"], "session_only")
        self.assertEqual(policy["sensitive_data_default"], "do_not_persist_without_explicit_permission_and_clear_purpose")
        self.assertTrue(policy["decay_changes_priority_not_deletion"])
        self.assertTrue(policy["delete_requests_apply_to_archives"])


class StateTemplateTests(unittest.TestCase):
    def test_three_state_files_have_distinct_roles(self):
        latest = (ROOT / "state" / "LATEST.md").read_text(encoding="utf-8")
        database = (ROOT / "state" / "PROFILE_DATABASE.md").read_text(encoding="utf-8")
        archive = (ROOT / "state" / "ARCHIVE.md").read_text(encoding="utf-8")
        self.assertIn("compact state", latest.lower())
        self.assertIn("not intended to hold every chat message", database.lower())
        self.assertIn("not automatically included", archive.lower())

    def test_update_protocol_has_context_and_deletion_rules(self):
        protocol = (ROOT / "state" / "UPDATE_PROTOCOL.md").read_text(encoding="utf-8").lower()
        self.assertIn("do not assume the entire chat history is accessible", protocol)
        self.assertIn("deletion", protocol)
        self.assertIn("reviewable change", protocol)

    def test_profile_record_schema_is_valid_json(self):
        schema = json.loads((ROOT / "schemas" / "profile_record.schema.json").read_text(encoding="utf-8"))
        self.assertIn("record_id", schema["required"])
        self.assertIn("confidence", schema["properties"])
        self.assertIn("sensitivity", schema["properties"])

    def test_contract_covers_personal_hub_and_provider_limits(self):
        top = (ROOT / "TOP_MOLD.md").read_text(encoding="utf-8").lower()
        llm_readme = (ROOT / "LLM_README.md").read_text(encoding="utf-8").lower()
        self.assertIn("personal hub", top)
        self.assertIn("do not generate a prompt", llm_readme)
        self.assertIn("provider", top)
        self.assertIn("one-off joke", top)

    def test_unresolved_design_questions_are_explicitly_deferred(self):
        questions = (ROOT / "NEXT_VERSION_OPEN_QUESTIONS.md").read_text(encoding="utf-8").lower()
        self.assertIn("decay periods", questions)
        self.assertIn("conflicting edits", questions)
        self.assertIn("cross-provider conformance", questions)
        self.assertIn("not empirically validated", questions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
