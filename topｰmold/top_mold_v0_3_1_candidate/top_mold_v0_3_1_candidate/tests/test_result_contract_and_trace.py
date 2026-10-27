import unittest
from copy import deepcopy

from core.errors import PlanningError
from core.planner import build_plan
from core.result_contract import validate_result_envelope
from core.trace import build_trace_record
from tests.common import valid_task, valid_registry, valid_intake, read_json
from core.intake import task_from_intake


class ResultEnvelopeTests(unittest.TestCase):
    def test_not_executed_example_is_accepted_without_claiming_semantic_truth(self):
        result = validate_result_envelope(read_json("result.not_executed.example.json"))
        self.assertTrue(result["claims_validated"])
        self.assertEqual(result["semantic_correctness"], "NOT_ASSESSED")
        self.assertEqual(result["result_status"], "NOT_EXECUTED")

    def test_expected_task_id_must_match(self):
        result = read_json("result.not_executed.example.json")
        with self.assertRaisesRegex(PlanningError, "does not match"):
            validate_result_envelope(result, expected_task_id="TASK-OTHER")

    def test_not_executed_cannot_claim_outputs(self):
        result = read_json("result.not_executed.example.json")
        result["output_types"] = ["summary"]
        result["outputs"] = {"summary": "fake"}
        with self.assertRaisesRegex(PlanningError, "cannot contain claimed outputs"):
            validate_result_envelope(result)

    def test_success_requires_execution_verified_output_and_pass_checks(self):
        result = {
            "schema_version": "1.0", "result_id": "RESULT-1", "task_id": "TASK-1",
            "processor_id": "PROC-1", "processor_version": "1.0",
            "execution_status": "SUCCEEDED", "result_status": "SUCCESS",
            "output_types": ["summary"], "outputs": {"summary": "some result"},
            "evidence_refs": ["source:1"], "assumptions": [], "unresolved_items": [],
            "verification": {"status": "VERIFIED", "checks": [{"id": "CHECK-1", "status": "PASS"}]}
        }
        output = validate_result_envelope(result)
        self.assertTrue(output["claims_validated"])
        self.assertEqual(output["semantic_correctness"], "NOT_ASSESSED")

    def test_success_without_verification_is_rejected(self):
        result = {
            "schema_version": "1.0", "result_id": "RESULT-1", "task_id": "TASK-1",
            "processor_id": "PROC-1", "processor_version": "1.0",
            "execution_status": "SUCCEEDED", "result_status": "SUCCESS",
            "output_types": ["summary"], "outputs": {"summary": "some result"},
            "verification": {"status": "VERIFIED", "checks": [{"id": "CHECK-1", "status": "UNVERIFIED"}]}
        }
        with self.assertRaisesRegex(PlanningError, "all-PASS"):
            validate_result_envelope(result)

    def test_duplicate_check_ids_are_rejected(self):
        result = {
            "schema_version": "1.0", "result_id": "RESULT-1", "task_id": "TASK-1",
            "processor_id": "PROC-1", "processor_version": "1.0",
            "execution_status": "SUCCEEDED", "result_status": "SUCCESS",
            "output_types": ["summary"], "outputs": {"summary": "ok"},
            "verification": {"status": "VERIFIED", "checks": [
                {"id": "CHECK-1", "status": "PASS"}, {"id": "CHECK-1", "status": "PASS"}]}
        }
        with self.assertRaisesRegex(PlanningError, "unique"):
            validate_result_envelope(result)

    def test_bool_is_not_a_confidence_like_string_array_member(self):
        result = read_json("result.not_executed.example.json")
        result["assumptions"] = [True]
        with self.assertRaisesRegex(PlanningError, "assumptions"):
            validate_result_envelope(result)


    def test_skipped_result_cannot_claim_checks(self):
        result = {
            "schema_version": "1.0", "result_id": "RESULT-SKIP", "task_id": "TASK-1",
            "processor_id": "PROC-1", "processor_version": "1.0",
            "execution_status": "SKIPPED", "result_status": "SKIPPED",
            "output_types": [], "outputs": {},
            "verification": {"status": "NOT_RUN", "checks": [{"id": "CHECK-1", "status": "PASS"}]}
        }
        with self.assertRaisesRegex(PlanningError, "cannot claim verification checks"):
            validate_result_envelope(result)

class TraceTests(unittest.TestCase):
    def setUp(self):
        self.task = valid_task()
        self.plan = build_plan(self.task, valid_registry())
        self.task["raw_request"] = "PRIVATE RAW TEXT SHOULD NOT BE INCLUDED"

    def test_trace_omits_raw_request_by_default(self):
        record = build_trace_record(self.task, self.plan)
        self.assertFalse(record["raw_input_included"])
        self.assertNotIn("raw_request", record)
        self.assertNotIn("PRIVATE RAW TEXT SHOULD NOT BE INCLUDED", str(record))

    def test_fingerprint_is_opt_in_and_warns_about_linkability(self):
        plain = build_trace_record(self.task, self.plan)
        hashed = build_trace_record(self.task, self.plan, include_request_fingerprint=True)
        self.assertNotIn("request_fingerprint", plain)
        self.assertEqual(hashed["request_fingerprint"]["algorithm"], "sha256")
        self.assertIn("linkable", hashed["fingerprint_notice"])

    def test_task_and_plan_ids_must_match(self):
        plan = deepcopy(self.plan)
        plan["task_id"] = "TASK-OTHER"
        with self.assertRaisesRegex(ValueError, "do not match"):
            build_trace_record(self.task, plan)

    def test_trace_rejects_unhashable_status_as_contract_error(self):
        plan = deepcopy(self.plan)
        plan["plan_status"] = []
        with self.assertRaisesRegex(ValueError, "plan_status is invalid"):
            build_trace_record(self.task, plan)

    def test_trace_records_only_processor_metadata_and_diagnostics(self):
        record = build_trace_record(self.task, self.plan)
        self.assertEqual(record["selected_processors"][0]["id"], self.plan["steps"][0]["processor_id"])
        self.assertEqual(record["diagnostic_codes"], [d["code"] for d in self.plan["diagnostics"]])
        self.assertEqual(record["execution_status"], "NOT_INVOKED")
        self.assertFalse(record["execution_invoked"])

    def test_fingerprint_option_must_be_boolean(self):
        with self.assertRaisesRegex(ValueError, "must be boolean"):
            build_trace_record(self.task, self.plan, include_request_fingerprint="false")

    def test_trace_refuses_to_label_an_executed_plan_as_plan_only(self):
        plan = deepcopy(self.plan)
        plan["execution_status"] = "SUCCEEDED"
        plan["execution_invoked"] = True
        with self.assertRaisesRegex(ValueError, "plan-only records"):
            build_trace_record(self.task, plan)

    def test_intake_to_plan_to_trace_pipeline_preserves_task_identity(self):
        packet = valid_intake()
        task = task_from_intake(packet)
        plan = build_plan(task, valid_registry())
        trace = build_trace_record(task, plan)
        self.assertEqual(trace["task_id"], task["task_id"])
        self.assertEqual(plan["plan_status"], "COMPLETE")
        self.assertEqual(trace["execution_status"], "NOT_INVOKED")

if __name__ == "__main__":
    unittest.main()
