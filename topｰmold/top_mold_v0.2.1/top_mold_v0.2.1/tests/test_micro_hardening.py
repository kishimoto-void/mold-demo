import unittest
from top_mold.engine import decide, parse_mode_lock_command


class RequestMicroInterpretationTests(unittest.TestCase):
    def test_negative_output_format_does_not_win(self):
        result = decide("ZIPではなくMarkdown形式にして")
        self.assertEqual(result.output_contract, "markdown")

    def test_format_mentioned_for_explanation_is_not_output_contract(self):
        self.assertEqual(decide("JSON形式について説明して").output_contract, "auto")

    def test_negated_json_request_is_not_output_contract(self):
        self.assertEqual(decide("JSONを使わず普通の文章で説明して").output_contract, "auto")

    def test_positive_format_requests_are_still_recognized(self):
        cases = {
            "ZIPを作成して": "zip",
            "JSONで出力して": "json",
            "Markdown形式にして": "markdown",
            "ソースコードを出して": "code",
            "表にして": "table",
            "報告書にして": "document",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(decide(text).output_contract, expected)

    def test_multiple_explicit_output_formats_are_preserved(self):
        result = decide("Markdown形式で説明して、最後にJSONで出力して")
        self.assertEqual(result.output_contract, "markdown")
        self.assertEqual(result.output_contracts, ["markdown", "json"])
        self.assertIn("multiple_explicit_output_contracts_preserved_in_order", result.notes)

    def test_inner_format_does_not_override_outer_zip_container(self):
        result = decide("JSONを含めたZIPにして")
        self.assertEqual(result.primary_mode, "work")
        self.assertEqual(result.output_contract, "zip")
        self.assertEqual(result.output_contracts, ["zip"])

    def test_quoted_action_is_data_not_a_mode_request(self):
        result = decide("この文章に「設計して」と書かれている。意味を説明して")
        self.assertEqual(result.primary_mode, "chat")
        self.assertNotIn("design", [signal["mode"] for signal in result.signals])

    def test_quoted_instruction_to_write_is_a_work_request(self):
        result = decide("「設計して」という指示文を作って")
        self.assertEqual(result.primary_mode, "work")

    def test_forbidden_action_is_not_classified_as_requested(self):
        result = decide("テストしてはいけないので、ファイルを作成して")
        self.assertEqual(result.primary_mode, "work")
        self.assertNotIn("verify", [signal["mode"] for signal in result.signals])

    def test_english_negation_does_not_trigger_verification(self):
        result = decide("Do not test this; create the file.")
        self.assertEqual(result.primary_mode, "work")
        self.assertNotIn("verify", [signal["mode"] for signal in result.signals])

    def test_short_form_design_only_is_recognized(self):
        self.assertEqual(decide("テストしないで、設計だけして").primary_mode, "design")

    def test_lock_commands_inside_quotes_are_ignored(self):
        self.assertEqual(parse_mode_lock_command("設定例は「モード固定を解除」だ"), (None, False))

    def test_negated_unlock_does_not_clear_lock(self):
        self.assertEqual(parse_mode_lock_command("モード固定を解除しないで"), (None, False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
