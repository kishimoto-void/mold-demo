import tempfile
import unittest
import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch
from core.startup import inspect_persona_file
from core.demo_runner import run_demo
from core.planner import build_plan
from core.personalization import load_dial_catalog, default_settings, save_settings
from main import build_parser, main, ROOT
from tests.common import read_json

class StartupTests(unittest.TestCase):
    def test_absent_empty_present_and_error_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            absent = inspect_persona_file(base / "absent.md")
            self.assertEqual(absent.status, "ABSENT")
            empty_file = base / "empty.md"
            empty_file.write_text("  \n", encoding="utf-8")
            self.assertEqual(inspect_persona_file(empty_file).status, "EMPTY")
            present_file = base / "present.md"
            present_file.write_text("profile", encoding="utf-8")
            self.assertEqual(inspect_persona_file(present_file).status, "PRESENT")
            self.assertEqual(inspect_persona_file(base).status, "ERROR")

    def test_invalid_utf8_is_error_not_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.md"
            path.write_bytes(b"\xff\xfe")
            self.assertEqual(inspect_persona_file(path).status, "ERROR")

    def test_cli_rejects_multiple_operations_instead_of_silently_ignoring_one(self):
        parser = build_parser()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["--demo", "DEMO-001", "--task", "config/task.example.json"])


    def test_task_route_is_independent_of_corrupt_personalization_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_settings = Path(tmp) / "bad-settings.json"
            bad_settings.write_text("{broken", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                result = main(["--task", str(ROOT / "config" / "task.example.json"), "--settings", str(bad_settings)])
            self.assertEqual(result, 0)
            self.assertIn('"plan_status": "COMPLETE"', out.getvalue())

    def test_advanced_dials_requires_configure(self):
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                main(["--advanced-dials"])

    def test_all_demos_run_without_invoking_external_execution(self):
        for number in range(1, 6):
            with self.subTest(demo=number):
                output = run_demo(f"DEMO-{number:03d}", ROOT)
                self.assertIn("demo_id", output)

    def test_demo_005_plan_only_is_complete(self):
        output = run_demo("DEMO-005", ROOT)
        self.assertIn('"plan_status": "COMPLETE"', output)
        self.assertIn('"execution_invoked": false', output)

    def test_result_envelope_cli_validates_expected_task_id(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = main(["--result", str(ROOT / "config" / "result.not_executed.example.json"),
                           "--expected-task-id", "TASK-EXAMPLE-001"])
        self.assertEqual(result, 0)
        self.assertIn('"semantic_correctness": "NOT_ASSESSED"', out.getvalue())

    def test_result_envelope_cli_rejects_task_id_mismatch(self):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = main(["--result", str(ROOT / "config" / "result.not_executed.example.json"),
                           "--expected-task-id", "TASK-OTHER"])
        self.assertEqual(result, 2)
        self.assertIn("does not match", err.getvalue())

    def test_trace_cli_builds_record_without_raw_request(self):
        task = read_json("task.example.json")
        task["raw_request"] = "secret user request text"
        plan = build_plan(task, read_json("processor_registry.json"))
        with tempfile.TemporaryDirectory() as tmp:
            task_path = Path(tmp) / "task.json"
            plan_path = Path(tmp) / "plan.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                result = main(["--trace", str(task_path), str(plan_path)])
        self.assertEqual(result, 0)
        self.assertNotIn("secret user request text", out.getvalue())
        self.assertIn('"raw_input_included": false', out.getvalue())

    def test_expected_task_id_requires_result_operation(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--expected-task-id", "TASK-1"])

    def test_request_fingerprint_requires_trace_operation(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--fingerprint-request"])

    def test_first_interactive_start_shows_dials_once_and_saves_defaults(self):
        class FakeTTY(io.StringIO):
            def isatty(self):
                return True
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "runtime" / "settings.json"
            persona = Path(tmp) / "persona.md"
            stdin = FakeTTY("2\nn\n")
            out = io.StringIO()
            with patch("sys.stdin", stdin), contextlib.redirect_stdout(out):
                result = main(["--settings", str(settings), "--persona", str(persona)])
            self.assertEqual(result, 0)
            self.assertTrue(settings.exists())
            self.assertFalse(persona.exists())
            self.assertIn("初期ダイヤル", out.getvalue())
            self.assertIn("次回以降の通常起動", out.getvalue())

    def test_later_interactive_start_does_not_repeat_first_setup(self):
        class FakeTTY(io.StringIO):
            def isatty(self):
                return True
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "settings.json"
            persona = Path(tmp) / "persona.md"
            catalog = load_dial_catalog(ROOT / "config" / "dials.json")
            save_settings(settings, default_settings(catalog), catalog)
            out = io.StringIO()
            with patch("sys.stdin", FakeTTY("")), contextlib.redirect_stdout(out):
                result = main(["--settings", str(settings), "--persona", str(persona)])
            self.assertEqual(result, 0)
            self.assertNotIn("初回セットアップ", out.getvalue())
            self.assertNotIn("初期ダイヤル", out.getvalue())

    def test_noninteractive_first_start_does_not_block_or_persist_defaults(self):
        class FakePipe(io.StringIO):
            def isatty(self):
                return False
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "settings.json"
            out = io.StringIO()
            with patch("sys.stdin", FakePipe("")), contextlib.redirect_stdout(out):
                result = main(["--settings", str(settings), "--persona", str(Path(tmp) / "persona.md")])
            self.assertEqual(result, 0)
            self.assertFalse(settings.exists())
            self.assertIn("対話端末で起動するか", out.getvalue())

    def test_dangling_symlink_is_not_treated_as_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "missing-target.md"
            link = Path(tmp) / "persona.md"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are not supported in this environment")
            self.assertEqual(inspect_persona_file(link).status, "ERROR")

    def test_demo_001_never_depends_on_or_writes_repository_runtime_path(self):
        before = (ROOT / "runtime" / "demo_absent_persona.md").exists()
        output = json.loads(run_demo("DEMO-001", ROOT))
        after = (ROOT / "runtime" / "demo_absent_persona.md").exists()
        self.assertEqual(output["persona_state"], "ABSENT")
        self.assertFalse(output["repository_files_modified"])
        self.assertEqual(before, after)

    def test_guided_first_setup_creates_persona_template_only_after_choice(self):
        class FakeTTY(io.StringIO):
            def isatty(self):
                return True
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "settings.json"
            persona = Path(tmp) / "config" / "persona.md"
            out = io.StringIO()
            with patch("sys.stdin", FakeTTY("1\nn\n")), contextlib.redirect_stdout(out):
                result = main(["--settings", str(settings), "--persona", str(persona)])
            self.assertEqual(result, 0)
            self.assertTrue(settings.exists())
            self.assertTrue(persona.exists())
            self.assertTrue(persona.read_text(encoding="utf-8").strip())

    def test_demo_001_reports_repeatable_absent_state(self):
        first = json.loads(run_demo("DEMO-001", ROOT))
        second = json.loads(run_demo("DEMO-001", ROOT))
        self.assertEqual(first["persona_state"], "ABSENT")
        self.assertEqual(second["persona_state"], "ABSENT")
        self.assertEqual(first["expected"], "ABSENT")

if __name__ == "__main__":
    unittest.main()
