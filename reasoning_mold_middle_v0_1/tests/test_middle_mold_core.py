import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from middle.middle_mold_core import (
    MiddleError,
    MiddleErrorCode,
    MiddleMold,
    MiddleRequest,
    build_debug_demo,
)


def test_generic_request_builds_five_step_plan():
    plan = MiddleMold().build_plan(MiddleRequest(goal="Compare two implementation options"))
    assert len(plan.steps) == 5
    assert plan.task_domain == "generic"
    assert plan.goal == "Compare two implementation options"
    assert plan.contract_version == "1.1.0"


def test_debug_demo_builds_six_step_plan():
    plan = build_debug_demo()
    assert plan.task_domain == "programming_debugging"
    assert [step.step_id for step in plan.steps] == ["D1", "D2", "D3", "D4", "D5", "D6"]
    assert any("reproduce" in step.purpose.lower() or "reproduced" in step.completion_check.lower() for step in plan.steps)


def test_observations_hypotheses_unknowns_are_kept_separate():
    request = MiddleRequest(
        goal="Investigate a bug",
        context={
            "observations": ["Crash occurs on empty input."],
            "hypotheses": ["The parser assumes a non-empty list."],
            "unknowns": ["The caller contract is not documented."],
        },
    )
    plan = MiddleMold().build_plan(request)
    assert plan.knowns == ("Crash occurs on empty input.",)
    assert plan.hypotheses == ("The parser assumes a non-empty list.",)
    assert plan.unknowns == ("The caller contract is not documented.",)


def test_missing_observations_preserve_uncertainty():
    plan = MiddleMold().build_plan(MiddleRequest(goal="Investigate a bug"))
    assert any("No explicit observations" in item for item in plan.unknowns)
    assert any("remain open" in item for item in plan.hypotheses)


def test_blank_goal_is_rejected():
    with pytest.raises(MiddleError) as exc:
        MiddleMold().build_plan(MiddleRequest(goal="  "))
    assert exc.value.code == MiddleErrorCode.INVALID_REQUEST


def test_context_list_with_blank_item_is_rejected():
    request = MiddleRequest(
        goal="Investigate a bug",
        context={"observations": ["valid", "  "]},
    )
    with pytest.raises(MiddleError) as exc:
        MiddleMold().build_plan(request)
    assert exc.value.code == MiddleErrorCode.INVALID_CONTEXT


def test_context_field_must_be_a_sequence_not_a_string():
    request = MiddleRequest(goal="Investigate a bug", context={"unknowns": "not a list"})
    with pytest.raises(MiddleError) as exc:
        MiddleMold().build_plan(request)
    assert exc.value.code == MiddleErrorCode.INVALID_CONTEXT


def test_plan_serializes_to_json_compatible_dict():
    plan = build_debug_demo()
    payload = plan.to_dict()
    assert payload["mold_name"] == "Generic Middle Mold"
    assert isinstance(payload["steps"], list)
    assert payload["steps"][0]["step_id"] == "D1"
    assert '"hypotheses"' in plan.to_json()


def test_debug_plan_never_claims_tests_were_run():
    plan = build_debug_demo()
    assert any("not been run" in item for item in plan.stop_conditions)
    assert any("not an LLM executor" in item for item in plan.limitations)


def test_request_constraints_are_preserved_without_rewriting():
    constraints = ("Keep the public API unchanged.", "Do not reorder steps.")
    plan = MiddleMold().build_plan(MiddleRequest(goal="Review a patch", constraints=constraints))
    assert plan.constraints == constraints


def test_unknown_task_domain_is_generic_not_auto_classified():
    plan = MiddleMold().build_plan(MiddleRequest(goal="Debug an issue"))
    assert plan.task_domain == "generic"
    assert [s.step_id for s in plan.steps] == ["M1", "M2", "M3", "M4", "M5"]
