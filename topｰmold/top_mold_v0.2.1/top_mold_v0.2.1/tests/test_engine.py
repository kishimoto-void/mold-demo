import copy
import json
import unittest

from top_mold.engine import (
    MODES, decide, detect_mode_signals, load_config, parse_mode_lock_command,
    update_lock, validate_config,
)


class ModeClassificationTests(unittest.TestCase):
    def test_all_five_modes_have_clear_action_triggers(self):
        cases = {
            "work": "このファイルを作成して",
            "verify": "厳密にテストして",
            "design": "全体を設計して",
            "research": "最新情報を調べて",
            "chat": "今日は雑談しよう",
        }
        for expected, prompt in cases.items():
            with self.subTest(expected=expected, prompt=prompt):
                self.assertEqual(decide(prompt).primary_mode, expected)

    def test_topic_nouns_alone_do_not_select_a_mode(self):
        text = "数学のテスト、設計、調査について書かれたメモを読んだ。"
        result = decide(text)
        self.assertEqual(result.primary_mode, "chat")
        self.assertEqual(result.secondary_modes, [])

    def test_topic_mention_of_test_is_not_verification_request(self):
        self.assertNotIn("verify", [s.mode for s in detect_mode_signals("テストの経験を説明して")])
        self.assertNotIn("verify", [s.mode for s in detect_mode_signals("This test case documents the result.")])

    def test_chat_request_is_recognized_even_when_topic_is_technical(self):
        self.assertEqual(decide("モールドの設計について雑談しよう").primary_mode, "chat")

    def test_compound_create_and_test_preserves_both_modes(self):
        result = decide("トップモールドのファイル一式を作成して、厳密にテストを追加して")
        modes = [result.primary_mode] + result.secondary_modes
        self.assertEqual(result.primary_mode, "work")
        self.assertIn("verify", modes)
        self.assertEqual(len(modes), len(set(modes)))

    def test_first_requested_action_controls_primary_in_compound_request(self):
        create_then_test = decide("ファイルを作成してから厳密にテストして")
        test_then_change = decide("厳密にテストしてから実装を変更して")
        self.assertEqual(create_then_test.primary_mode, "work")
        self.assertIn("verify", create_then_test.secondary_modes)
        self.assertEqual(test_then_change.primary_mode, "verify")
        self.assertIn("work", test_then_change.secondary_modes)

    def test_no_mode_signal_falls_back_to_default(self):
        self.assertEqual(decide("それはどういう意味？").primary_mode, "chat")
        self.assertEqual(decide("内容を見て", default_mode="design").primary_mode, "design")

    def test_default_mode_is_validated(self):
        with self.assertRaises(ValueError):
            decide("hello", default_mode="unknown")

    def test_active_lock_overrides_auto_classification(self):
        result = decide("厳密にテストして、実装して", mode_lock="design")
        self.assertEqual(result.primary_mode, "design")
        self.assertTrue(result.mode_locked)
        self.assertEqual(result.secondary_modes, [])
        self.assertIn("active_mode_lock_overrides_automatic_classification", result.notes)

    def test_invalid_mode_lock_rejected(self):
        with self.assertRaises(ValueError):
            decide("テストして", mode_lock="invalid")

    def test_explicit_lock_command_parsing_japanese_and_english(self):
        self.assertEqual(parse_mode_lock_command("今日は設計モードで固定"), ("design", False))
        self.assertEqual(parse_mode_lock_command("mode_lock=verify"), ("verify", False))
        self.assertEqual(parse_mode_lock_command("ロック解除"), (None, True))

    def test_lock_state_can_be_changed_and_unlocked(self):
        current, status = update_lock(None, "検証モードに固定")
        self.assertEqual((current, status), ("verify", "locked"))
        current, status = update_lock(current, "設計の話をして")
        self.assertEqual((current, status), ("verify", "unchanged"))
        current, status = update_lock(current, "モード固定を解除")
        self.assertEqual((current, status), (None, "unlocked"))


class IndependentAxesTests(unittest.TestCase):
    def test_free_opinion_is_modifier_not_mode(self):
        result = decide("ChatGPT的にどう思う？")
        self.assertTrue(result.free_opinion)
        self.assertEqual(result.primary_mode, "chat")

    def test_free_opinion_does_not_cancel_verification(self):
        result = decide("この案を厳密にテストして、ChatGPT的にどう思う？")
        self.assertEqual(result.primary_mode, "verify")
        self.assertTrue(result.free_opinion)
        self.assertIn("free_opinion_enabled_without_disabling_fact_hypothesis_separation", result.notes)

    def test_explicit_depth_does_not_change_mode(self):
        expert = decide("専門家モードで設計して")
        concise = decide("要点だけで設計して")
        self.assertEqual(expert.primary_mode, "design")
        self.assertEqual(expert.depth, "expert")
        self.assertEqual(concise.primary_mode, "design")
        self.assertEqual(concise.depth, "concise")

    def test_output_contract_does_not_change_mode(self):
        result = decide("設計して、成果物はZIPにして")
        self.assertEqual(result.primary_mode, "design")
        self.assertEqual(result.output_contract, "zip")
        self.assertIn("output_contract_is_independent_of_task_mode", result.notes)

    def test_output_only_constraint_is_detected(self):
        result = decide("この内容をZIPだけで納品して。余計な説明なし")
        self.assertEqual(result.output_contract, "zip")
        self.assertTrue(result.output_only)

    def test_zip_detection_handles_japanese_adjacent_to_ascii(self):
        for prompt in ("ZIPだけで", "ZIPを作成して", "ZIP形式で出して", "zipファイルが必要"):
            with self.subTest(prompt=prompt):
                self.assertEqual(decide(prompt).output_contract, "zip")

    def test_all_output_contracts(self):
        cases = {
            "JSONで出力": "json",
            "ソースコードを出して": "code",
            "Markdown形式にして": "markdown",
            "表にして": "table",
            "報告書にして": "document",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(decide(prompt).output_contract, expected)

    def test_expert_has_priority_over_concise_when_both_explicit(self):
        result = decide("専門家モードで要点だけ説明して")
        self.assertEqual(result.depth, "expert")

    def test_output_format_and_mode_lock_are_orthogonal(self):
        result = decide("JSONで出力して検証して", mode_lock="design")
        self.assertEqual(result.primary_mode, "design")
        self.assertEqual(result.output_contract, "json")


class ConfigValidationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()

    def test_bundled_config_loads_and_has_required_shape(self):
        self.assertEqual(self.config["schema"], "top-mold/v0.2")
        validate_config(self.config)
        self.assertTrue(self.config["mode"]["auto_classification"])
        self.assertEqual(self.config["human_analysis"]["default"], "opt_in")

    def test_invalid_schema_fails(self):
        bad = copy.deepcopy(self.config)
        bad["schema"] = "top-mold/v9"
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_boolean_dial_fails_even_though_bool_is_an_int_subclass(self):
        bad = copy.deepcopy(self.config)
        bad["dials"]["proactiveness"] = True
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_out_of_range_dial_fails(self):
        bad = copy.deepcopy(self.config)
        bad["dials"]["concision"] = 101
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_missing_independent_axis_fails(self):
        bad = copy.deepcopy(self.config)
        del bad["independent_axes"]["output_contract"]
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_invalid_human_analysis_default_fails(self):
        bad = copy.deepcopy(self.config)
        bad["human_analysis"]["default"] = "always_guess"
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_schema_requires_supported_lock(self):
        bad = copy.deepcopy(self.config)
        bad["mode"]["mode_lock"] = "surprise"
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_boolean_scale_bounds_are_rejected(self):
        bad = copy.deepcopy(self.config)
        bad["dials"]["scale"]["min"] = False
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_non_object_human_analysis_fails_closed(self):
        bad = copy.deepcopy(self.config)
        bad["human_analysis"] = []
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_supported_modes_must_not_have_duplicates(self):
        bad = copy.deepcopy(self.config)
        bad["mode"]["supported_modes"] = ["work", "verify", "design", "research", "work"]
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_sensitive_storage_gate_cannot_be_disabled_silently(self):
        bad = copy.deepcopy(self.config)
        bad["memory_policy"]["sensitive_storage_requires_clear_purpose"] = False
        with self.assertRaises(ValueError):
            validate_config(bad)

    def test_domain_kernel_and_dial_semantics_are_required(self):
        bad = copy.deepcopy(self.config)
        del bad["dial_semantics"]["generalization"]
        with self.assertRaises(ValueError):
            validate_config(bad)


class InputRobustnessTests(unittest.TestCase):
    def test_non_string_text_raises_type_error(self):
        with self.assertRaises(TypeError):
            decide(None)  # type: ignore[arg-type]

    def test_empty_input_is_safe(self):
        result = decide("")
        self.assertEqual(result.primary_mode, "chat")
        self.assertEqual(result.signals, [])

    def test_decision_is_json_serializable(self):
        encoded = json.dumps(decide("設計してZIPにして").to_dict(), ensure_ascii=False)
        self.assertIn('"primary_mode": "design"', encoded)

    def test_supported_modes_are_closed_set(self):
        self.assertEqual(set(MODES), {"work", "verify", "design", "research", "chat"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
