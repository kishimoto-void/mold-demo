import json
import tempfile
import unittest
from pathlib import Path
from core.personalization import (load_dial_catalog, default_settings, validate_settings,
    update_dial, complexity_advice, build_personalization_overlay, save_settings, load_settings)
from core.errors import DialConfigError
from tests.common import ROOT

class PersonalizationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_dial_catalog(ROOT / "config" / "dials.json")

    def test_catalog_has_13_dials_and_defaults_to_eight(self):
        settings = default_settings(self.catalog)
        self.assertEqual(len(self.catalog), 13)
        self.assertEqual(len(settings["active_dial_ids"]), 8)

    def test_dial_value_must_be_integer_one_to_five(self):
        settings = default_settings(self.catalog)
        for value in (0, 6, True, 2.5, "3"):
            with self.subTest(value=value), self.assertRaises(DialConfigError):
                update_dial(settings, self.catalog, "D-001", value)

    def test_update_touches_only_requested_value_and_activates_explicitly_selected_dial(self):
        settings = default_settings(self.catalog)
        updated = update_dial(settings, self.catalog, "D-009", 4)
        self.assertEqual(updated["values"]["D-009"], 4)
        self.assertIn("D-009", updated["active_dial_ids"])
        self.assertEqual(updated["values"]["D-001"], settings["values"]["D-001"])

    def test_unknown_dial_never_silently_dropped(self):
        settings = default_settings(self.catalog)
        settings["active_dial_ids"].append("D-999")
        with self.assertRaisesRegex(DialConfigError, "unregistered active"):
            validate_settings(settings, self.catalog)

    def test_complexity_threshold_is_advisory_only(self):
        settings = default_settings(self.catalog)
        self.assertIsNone(complexity_advice(settings, 10))
        settings = update_dial(settings, self.catalog, "D-009", 3)
        settings = update_dial(settings, self.catalog, "D-010", 3)
        self.assertIsNotNone(complexity_advice(settings, 10))
        self.assertEqual(len(settings["active_dial_ids"]), 10)

    def test_overlay_does_not_claim_to_control_model_internals(self):
        overlay = build_personalization_overlay(default_settings(self.catalog), self.catalog, {"tone":"casual"})
        self.assertEqual(overlay["authority"], "presentation_preference_only")
        self.assertIn("hard_policy", overlay["precedence"])
        self.assertIn("does not control a model", overlay["warning"])

    def test_save_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            settings = update_dial(default_settings(self.catalog), self.catalog, "D-003", 4)
            save_settings(path, settings, self.catalog)
            self.assertEqual(load_settings(path, self.catalog), settings)

    def test_corrupt_existing_settings_are_not_replaced_by_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{bad", encoding="utf-8")
            with self.assertRaises(DialConfigError):
                load_settings(path, self.catalog)
            self.assertEqual(path.read_text(encoding="utf-8"), "{bad")

    def test_catalog_requires_supported_schema_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dials.json"
            path.write_text(json.dumps({"schema_version":"99.0", "dials": []}), encoding="utf-8")
            with self.assertRaisesRegex(DialConfigError, "schema_version 1.0"):
                load_dial_catalog(path)

    def test_settings_reject_non_string_value_keys_without_typeerror(self):
        settings = default_settings(self.catalog)
        settings["values"][3] = 3
        with self.assertRaisesRegex(DialConfigError, "keys must be"):
            validate_settings(settings, self.catalog)

    def test_settings_save_parent_path_error_is_reported_as_domain_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "not-a-directory"
            parent.write_text("file", encoding="utf-8")
            with self.assertRaisesRegex(DialConfigError, "cannot save settings atomically"):
                save_settings(parent / "settings.json", default_settings(self.catalog), self.catalog)

    def test_complexity_threshold_must_be_positive_integer(self):
        with self.assertRaisesRegex(DialConfigError, "positive integer"):
            complexity_advice(default_settings(self.catalog), True)

    def test_catalog_rejects_duplicate_ids_after_whitespace_canonicalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dials.json"
            data = json.loads((ROOT / "config" / "dials.json").read_text(encoding="utf-8"))
            data["dials"].append({"id":" D-001 ","name":"duplicate", "advanced":False})
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(DialConfigError, "duplicate dial id"):
                load_dial_catalog(path)

    def test_update_dial_rejects_non_string_id_as_domain_error(self):
        with self.assertRaisesRegex(DialConfigError, "dial id must be"):
            update_dial(default_settings(self.catalog), self.catalog, [], 3)

    def test_visible_dial_filter_rejects_malformed_public_inputs(self):
        from core.personalization import select_visible_dials
        with self.assertRaisesRegex(DialConfigError, "active_dial_ids"):
            select_visible_dials(self.catalog, {"active_dial_ids": [None]})

    def test_save_settings_refuses_to_replace_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.json"
            link = Path(tmp) / "settings.json"
            target.write_text("sentinel", encoding="utf-8")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are not supported in this environment")
            with self.assertRaisesRegex(DialConfigError, "refusing to atomically replace"):
                save_settings(link, default_settings(self.catalog), self.catalog)
            self.assertTrue(link.is_symlink())
            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")

    def test_load_settings_rejects_dangling_symlink_as_missing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "settings.json"
            try:
                link.symlink_to(Path(tmp) / "missing-target.json")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are not supported in this environment")
            with self.assertRaisesRegex(DialConfigError, "dangling symlink"):
                load_settings(link, self.catalog)

if __name__ == "__main__":
    unittest.main()
