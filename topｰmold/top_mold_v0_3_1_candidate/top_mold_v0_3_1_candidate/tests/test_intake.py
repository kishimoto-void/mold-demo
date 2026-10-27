import unittest
from copy import deepcopy
from core.intake import validate_intake_packet, task_from_intake
from core.errors import IntakeError
from tests.common import valid_intake

class IntakeTests(unittest.TestCase):
    def test_valid_packet_round_trips_without_mutating_input(self):
        packet = valid_intake()
        original = deepcopy(packet)
        normalized = validate_intake_packet(packet)
        self.assertEqual(normalized, original)
        self.assertEqual(packet, original)

    def test_ready_packet_becomes_task_envelope(self):
        task = task_from_intake(valid_intake())
        self.assertEqual(task["task_id"], "TASK-INTAKE-EXAMPLE-001")
        self.assertEqual(task["required_capabilities"], ["analyze", "summarize", "validate"])

    def test_ready_with_blocking_question_is_rejected(self):
        packet = valid_intake()
        packet["open_questions"] = [{"id":"Q-1","question":"Which format?","blocking":True}]
        with self.assertRaisesRegex(IntakeError, "READY cannot contain blocking"):
            validate_intake_packet(packet)

    def test_clarification_requires_blocking_question(self):
        packet = valid_intake()
        packet["decision"]["status"] = "CLARIFICATION_REQUIRED"
        with self.assertRaisesRegex(IntakeError, "requires at least one blocking"):
            validate_intake_packet(packet)

    def test_nonready_packet_cannot_become_task(self):
        packet = valid_intake()
        packet["decision"] = {"status":"BLOCKED","reason":"No permission"}
        with self.assertRaisesRegex(IntakeError, "cannot create Task Envelope"):
            task_from_intake(packet)

    def test_duplicate_requirement_ids_are_rejected(self):
        packet = valid_intake()
        packet["atomic_requirements"].append(deepcopy(packet["atomic_requirements"][0]))
        with self.assertRaisesRegex(IntakeError, "duplicate ids"):
            validate_intake_packet(packet)

    def test_invalid_confidence_is_rejected(self):
        packet = valid_intake()
        packet["assumptions"][0]["confidence"] = 1.1
        with self.assertRaisesRegex(IntakeError, "between 0 and 1"):
            validate_intake_packet(packet)

    def test_unhashable_priority_fails_as_contract_error_not_typeerror(self):
        packet = valid_intake()
        packet["atomic_requirements"][0]["priority"] = []
        with self.assertRaises(IntakeError):
            validate_intake_packet(packet)

    def test_missing_mandatory_field_is_rejected(self):
        packet = valid_intake()
        del packet["raw_request"]
        with self.assertRaisesRegex(IntakeError, "missing required fields"):
            validate_intake_packet(packet)

    def test_blocked_reason_must_be_nonempty_string(self):
        packet = valid_intake()
        packet["decision"] = {"status": "BLOCKED", "reason": 123}
        with self.assertRaisesRegex(IntakeError, "decision.reason"):
            validate_intake_packet(packet)

    def test_duplicate_routing_type_ids_and_capabilities_are_rejected_early(self):
        packet = valid_intake()
        packet["routing"]["required_capabilities"] = ["analyze", "analyze"]
        with self.assertRaisesRegex(IntakeError, "required_capabilities must not contain duplicates"):
            validate_intake_packet(packet)
        packet = valid_intake()
        packet["routing"]["input_types"] = ["text", "text"]
        with self.assertRaisesRegex(IntakeError, "input_types must not contain duplicates"):
            validate_intake_packet(packet)

    def test_optional_task_id_and_context_refs_are_validated(self):
        packet = valid_intake()
        packet["task_id"] = []
        with self.assertRaisesRegex(IntakeError, "task_id"):
            validate_intake_packet(packet)
        packet = valid_intake()
        packet["context_refs"] = ["ctx-1", 4]
        with self.assertRaisesRegex(IntakeError, "context_refs"):
            validate_intake_packet(packet)

    def test_known_constraint_value_types_are_checked_at_intake(self):
        packet = valid_intake()
        packet["known_constraints"] = [{"id": "C-1", "kind": "requires_approval", "value": "yes"}]
        with self.assertRaisesRegex(IntakeError, "requires_approval"):
            validate_intake_packet(packet)

    def test_empty_allowed_execution_mode_constraint_means_deny_all_not_invalid(self):
        packet = valid_intake()
        packet["known_constraints"] = [{"id": "C-1", "kind": "allowed_execution_modes", "value": [], "severity": "must"}]
        normalized = validate_intake_packet(packet)
        self.assertEqual(normalized["known_constraints"][0]["value"], [])

if __name__ == "__main__":
    unittest.main()
