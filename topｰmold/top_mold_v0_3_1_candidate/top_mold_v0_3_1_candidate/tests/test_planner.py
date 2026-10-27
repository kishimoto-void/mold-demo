import unittest
from copy import deepcopy
from core.planner import build_plan
from core.errors import PlanningError, RegistryError
from tests.common import valid_task, valid_registry

class PlannerTests(unittest.TestCase):
    def test_example_route_is_complete_and_plan_only(self):
        plan = build_plan(valid_task(), valid_registry())
        self.assertEqual(plan["plan_status"], "COMPLETE")
        self.assertEqual([s["processor_id"] for s in plan["steps"]], ["PROC-001", "PROC-002", "PROC-003"])
        self.assertFalse(plan["execution_invoked"])
        self.assertEqual(plan["execution_status"], "NOT_INVOKED")

    def test_route_is_deterministic(self):
        task, registry = valid_task(), valid_registry()
        self.assertEqual(build_plan(task, registry), build_plan(task, registry))

    def test_disabled_processor_is_never_selected(self):
        plan = build_plan(valid_task(), valid_registry())
        self.assertNotIn("PROC-005", [x["processor_id"] for x in plan["steps"]])

    def test_forbidden_mode_is_excluded(self):
        task, registry = valid_task(), valid_registry()
        task["policy"]["forbidden_execution_modes"] = ["local", "external_api"]
        plan = build_plan(task, registry)
        self.assertNotEqual(plan["plan_status"], "COMPLETE")
        self.assertTrue(all(s["execution_mode"] not in {"local", "external_api"} for s in plan["steps"]))

    def test_approval_gate_blocks_all_planning(self):
        task, registry = valid_task(), valid_registry()
        task["policy"].update({"approval_required": True, "approval_granted": False})
        plan = build_plan(task, registry)
        self.assertEqual(plan["plan_status"], "BLOCKED")
        self.assertEqual(plan["steps"], [])
        self.assertEqual(plan["diagnostics"][0]["code"], "APPROVAL_REQUIRED")

    def test_missing_provider_is_reported(self):
        task, registry = valid_task(), valid_registry()
        task["required_capabilities"] = ["teleport"]
        plan = build_plan(task, registry)
        self.assertIn("teleport", plan["unmet_capabilities"])
        self.assertIn("NO_PROVIDER", [d["code"] for d in plan["diagnostics"]])

    def test_incompatible_input_types_are_reported(self):
        task, registry = valid_task(), valid_registry()
        task["input_types"] = ["image"]
        plan = build_plan(task, registry)
        self.assertIn("INPUT_TYPE_MISMATCH", [d["code"] for d in plan["diagnostics"]])

    def test_required_output_contract_is_enforced(self):
        task, registry = valid_task(), valid_registry()
        task["output_contract"]["required_types"] = ["nonexistent_type"]
        plan = build_plan(task, registry)
        self.assertEqual(plan["plan_status"], "PARTIAL")
        self.assertEqual(plan["unmet_output_types"], ["nonexistent_type"])

    def test_unknown_mandatory_constraint_prevents_complete_status(self):
        task, registry = valid_task(), valid_registry()
        task["constraints"] = [{"id":"C-X","kind":"magic_constraint","value":"x","severity":"must"}]
        plan = build_plan(task, registry)
        self.assertEqual(plan["plan_status"], "PARTIAL")
        self.assertIn("HARD_CONSTRAINT_UNVERIFIED", [d["code"] for d in plan["diagnostics"]])

    def test_duplicate_processor_ids_are_rejected(self):
        registry = valid_registry()
        registry["processors"].append(deepcopy(registry["processors"][0]))
        with self.assertRaises(RegistryError):
            build_plan(valid_task(), registry)

    def test_bad_task_shape_is_reported_as_planning_error(self):
        task = valid_task()
        task["risk_level"] = []
        with self.assertRaises(PlanningError):
            build_plan(task, valid_registry())


    def test_complete_route_search_backtracks_around_bad_high_priority_choice(self):
        task = {"schema_version":"1.0", "task_id":"TASK-BACKTRACK", "goal":"choose a compatible route",
                "input_types":["text"], "required_capabilities":["prepare", "finish"],
                "output_contract":{"required_types":["done"]}, "constraints":[], "policy":{}, "risk_level":"low"}
        registry = {"schema_version":"1.0", "processors":[
            {"id":"PROC-001","version":"1","status":"active","capabilities":["prepare"],"accepts":["text"],"produces":["dead_end"],"execution_mode":"local","priority":100},
            {"id":"PROC-002","version":"1","status":"active","capabilities":["prepare"],"accepts":["text"],"produces":["ready"],"execution_mode":"local","priority":50},
            {"id":"PROC-003","version":"1","status":"active","capabilities":["finish"],"accepts":["ready"],"produces":["done"],"execution_mode":"local","priority":100}
        ]}
        plan = build_plan(task, registry)
        self.assertEqual(plan["plan_status"], "COMPLETE")
        self.assertEqual([s["processor_id"] for s in plan["steps"]], ["PROC-002", "PROC-003"])

    def test_explicit_empty_allow_list_denies_all_modes(self):
        task, registry = valid_task(), valid_registry()
        task["policy"]["allowed_execution_modes"] = []
        plan = build_plan(task, registry)
        self.assertNotEqual(plan["plan_status"], "COMPLETE")
        self.assertTrue(any(d["code"] == "FORBIDDEN_EXECUTION_MODE" for d in plan["diagnostics"]))

    def test_unverified_soft_constraint_is_visible(self):
        task, registry = valid_task(), valid_registry()
        task["constraints"] = [{"id":"C-SOFT","kind":"custom_style","value":"bright","severity":"should"}]
        plan = build_plan(task, registry)
        self.assertEqual(plan["plan_status"], "COMPLETE")
        self.assertTrue(any(d["code"] == "UNSUPPORTED_SOFT_CONSTRAINT" for d in plan["diagnostics"]))
        self.assertTrue(any("remain unverified" in w for w in plan["warnings"]))

    def test_empty_capabilities_is_partial_not_success(self):
        task, registry = valid_task(), valid_registry()
        task["required_capabilities"] = []
        plan = build_plan(task, registry)
        self.assertEqual(plan["plan_status"], "PARTIAL")
        self.assertIn("EMPTY_REQUIRED_CAPABILITIES", [d["code"] for d in plan["diagnostics"]])

    def test_approval_constraint_cannot_be_weakened_by_later_false_constraint(self):
        task, registry = valid_task(), valid_registry()
        task["policy"]["approval_required"] = True
        task["constraints"] = [{"id": "C-1", "kind": "requires_approval", "value": False, "severity": "must"}]
        plan = build_plan(task, registry)
        self.assertEqual(plan["plan_status"], "BLOCKED")
        self.assertEqual(plan["steps"], [])
        self.assertIn("APPROVAL_REQUIRED", [d["code"] for d in plan["diagnostics"]])

    def test_search_node_limit_stops_pathological_search_as_partial(self):
        task = {"schema_version":"1.0", "task_id":"TASK-LIMIT", "goal":"bounded route search",
                "input_types":["text"], "required_capabilities":["prepare", "finish"],
                "output_contract":{"required_types":["done"]}, "constraints":[], "policy":{}, "risk_level":"low"}
        registry = {"schema_version":"1.0", "processors":[
            {"id":"PROC-001","version":"1","status":"active","capabilities":["prepare"],"accepts":["text"],"produces":["dead"],"execution_mode":"local","priority":100},
            {"id":"PROC-002","version":"1","status":"active","capabilities":["prepare"],"accepts":["text"],"produces":["ready"],"execution_mode":"local","priority":50},
            {"id":"PROC-003","version":"1","status":"active","capabilities":["finish"],"accepts":["ready"],"produces":["done"],"execution_mode":"local","priority":100}
        ]}
        plan = build_plan(task, registry, max_search_nodes=1)
        self.assertNotEqual(plan["plan_status"], "COMPLETE")
        self.assertIn("PLANNING_SEARCH_LIMIT", [d["code"] for d in plan["diagnostics"]])

    def test_search_node_limit_must_be_positive_integer(self):
        with self.assertRaises(PlanningError):
            build_plan(valid_task(), valid_registry(), max_search_nodes=True)

    def test_unverified_constraint_is_not_mislabelled_as_a_proven_violation(self):
        task, registry = valid_task(), valid_registry()
        task["constraints"] = [{"id":"C-X","kind":"magic_constraint","value":"x","severity":"must"}]
        plan = build_plan(task, registry)
        self.assertEqual(plan["constraint_violations"], [])
        self.assertEqual(len(plan["unverified_constraints"]), 1)

    def test_empty_allowed_modes_constraint_is_valid_but_blocks_all_routes(self):
        task, registry = valid_task(), valid_registry()
        task["constraints"] = [{"id": "C-EMPTY", "kind": "allowed_execution_modes", "value": [], "severity": "must"}]
        plan = build_plan(task, registry)
        self.assertNotEqual(plan["plan_status"], "COMPLETE")
        self.assertIn("FORBIDDEN_EXECUTION_MODE", [d["code"] for d in plan["diagnostics"]])

    def test_route_depth_limit_is_a_typed_error_not_recursion_failure(self):
        task, registry = valid_task(), valid_registry()
        task["required_capabilities"] = [f"cap-{i}" for i in range(257)]
        with self.assertRaisesRegex(PlanningError, "256-step safety limit"):
            build_plan(task, registry)

if __name__ == "__main__":
    unittest.main()
