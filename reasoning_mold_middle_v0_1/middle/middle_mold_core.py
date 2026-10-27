"""
Generic Middle Mold — v0.1.0 prototype

Purpose:
- Convert a goal/constraints/context payload into an explicit, reviewable process plan.
- Keep observed facts, assumptions, hypotheses, and unknowns separate.
- Provide a generic process substrate; programming/debugging is a demonstration profile.
- Do not call an LLM, execute code, infer hidden user intent, or silently repair missing specs.

Provisional hypotheses:
- The minimum neutral input contract uses goal, constraints, and context.
- Context keys `observations`, `hypotheses`, and `unknowns` are optional lists.
- Debugging-specific checks are selected only when `task_domain="programming_debugging"`.
- Field names and required inputs are checked by Joint Program; semantic correctness is not inferred here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import json


VERSION = "0.1.0"
CONTRACT_VERSION = "1.1.0"


class MiddleErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    INSUFFICIENT_INPUT = "insufficient_input"
    INVALID_CONTEXT = "invalid_context"


class MiddleError(ValueError):
    def __init__(self, code: MiddleErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code.value, "message": str(self)}


@dataclass(frozen=True)
class MiddleRequest:
    """Neutral request from Top Mold. Values should be observable and task-scoped."""
    goal: str
    constraints: Tuple[str, ...] = ()
    context: Mapping[str, Any] = field(default_factory=dict)
    task_domain: str = "generic"
    requested_outputs: Tuple[str, ...] = ("process_plan", "knowns", "hypotheses", "unknowns")

    def validate(self) -> None:
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise MiddleError(MiddleErrorCode.INVALID_REQUEST, "goal must be a non-empty string")
        for name, values in (
            ("constraints", self.constraints),
            ("requested_outputs", self.requested_outputs),
        ):
            if isinstance(values, (str, bytes)):
                raise MiddleError(MiddleErrorCode.INVALID_REQUEST, f"{name} must be a sequence")
            if any(not isinstance(v, str) or not v.strip() for v in values):
                raise MiddleError(MiddleErrorCode.INVALID_REQUEST, f"{name} must contain non-empty strings")
        if not isinstance(self.context, Mapping):
            raise MiddleError(MiddleErrorCode.INVALID_CONTEXT, "context must be a mapping")
        if not isinstance(self.task_domain, str) or not self.task_domain.strip():
            raise MiddleError(MiddleErrorCode.INVALID_REQUEST, "task_domain must be a non-empty string")


@dataclass(frozen=True)
class ProcessStep:
    step_id: str
    action: str
    purpose: str
    expected_artifact: str
    completion_check: str
    status: str = "planned"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessPlan:
    mold_name: str
    mold_version: str
    contract_version: str
    task_domain: str
    goal: str
    constraints: Tuple[str, ...]
    knowns: Tuple[str, ...]
    hypotheses: Tuple[str, ...]
    unknowns: Tuple[str, ...]
    steps: Tuple[ProcessStep, ...]
    evaluation_checks: Tuple[str, ...]
    stop_conditions: Tuple[str, ...]
    assumptions: Tuple[str, ...]
    limitations: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mold_name": self.mold_name,
            "mold_version": self.mold_version,
            "contract_version": self.contract_version,
            "task_domain": self.task_domain,
            "goal": self.goal,
            "constraints": list(self.constraints),
            "knowns": list(self.knowns),
            "hypotheses": list(self.hypotheses),
            "unknowns": list(self.unknowns),
            "steps": [step.to_dict() for step in self.steps],
            "evaluation_checks": list(self.evaluation_checks),
            "stop_conditions": list(self.stop_conditions),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class MiddleMold:
    """Generic process planner. Produces a plan; it does not execute the plan."""

    name = "Generic Middle Mold"

    def build_plan(self, request: MiddleRequest) -> ProcessPlan:
        request.validate()
        context = request.context
        knowns = self._string_tuple(context.get("observations", ()), "observations")
        hypotheses = self._string_tuple(context.get("hypotheses", ()), "hypotheses")
        unknowns = self._string_tuple(context.get("unknowns", ()), "unknowns")
        assumptions = [
            "The stated goal and constraints are the authoritative task boundary.",
            "Context items are treated as supplied observations or hypotheses according to their field, not independently verified facts.",
            "No missing requirement is silently inferred as confirmed.",
        ]
        if not knowns:
            unknowns = self._append_unique(
                unknowns,
                ("No explicit observations were supplied; collect evidence before asserting a root cause.",),
            )
        if not hypotheses:
            hypotheses = self._append_unique(
                hypotheses,
                ("Cause or solution candidates remain open until supported by observations.",),
            )

        steps = self._generic_steps()
        checks = [
            "Each conclusion is traceable to an observation, a stated rule, or a labelled hypothesis.",
            "Unknown or contradictory requirements remain explicit instead of being silently filled.",
            "The proposed result satisfies the stated goal and every explicit constraint, or records why it cannot.",
            "A verification method and an observable pass/fail condition are defined before declaring completion.",
        ]
        stops = [
            "Stop and request clarification when a missing requirement changes the solution materially.",
            "Do not claim success when the verification step has not been run or its result is unavailable.",
            "If evidence contradicts the current hypothesis, retain the discrepancy and revise the plan.",
        ]
        limitations = [
            "This is a plan generator, not an LLM executor, compiler, test runner, or proof engine.",
            "Hypotheses supplied in context are not automatically validated.",
            "The debugging profile contains generic checks; it cannot know repository-specific contracts without being given them.",
        ]

        if request.task_domain == "programming_debugging":
            steps = self._debug_steps()
            checks.extend([
                "Reproduce the failure with a minimal input or a failing test before changing code, when feasible.",
                "Separate observed failure, suspected cause, and confirmed root cause.",
                "Add or update a regression test that fails before the fix and passes after it, when feasible.",
                "Run the relevant test suite and report the actual result; never report an unrun test as passed.",
                "Check that the fix does not violate existing interfaces or change unrelated behaviour.",
            ])
            assumptions.append(
                "Programming/debugging is a demonstration profile selected explicitly by task_domain."
            )

        return ProcessPlan(
            mold_name=self.name,
            mold_version=VERSION,
            contract_version=CONTRACT_VERSION,
            task_domain=request.task_domain,
            goal=request.goal.strip(),
            constraints=tuple(request.constraints),
            knowns=knowns,
            hypotheses=hypotheses,
            unknowns=unknowns,
            steps=tuple(steps),
            evaluation_checks=tuple(checks),
            stop_conditions=tuple(stops),
            assumptions=tuple(assumptions),
            limitations=tuple(limitations),
        )

    @staticmethod
    def _string_tuple(value: Any, field_name: str) -> Tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise MiddleError(
                MiddleErrorCode.INVALID_CONTEXT,
                f"context.{field_name} must be a sequence of strings",
            )
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise MiddleError(
                MiddleErrorCode.INVALID_CONTEXT,
                f"context.{field_name} must contain non-empty strings",
            )
        return tuple(value)

    @staticmethod
    def _append_unique(existing: Tuple[str, ...], additions: Sequence[str]) -> Tuple[str, ...]:
        result = list(existing)
        for item in additions:
            if item not in result:
                result.append(item)
        return tuple(result)

    @staticmethod
    def _generic_steps() -> List[ProcessStep]:
        return [
            ProcessStep("M1", "Normalize the goal and constraints",
                        "Define the requested outcome and the boundaries of acceptable solutions.",
                        "A goal/constraint summary",
                        "Every explicit constraint is preserved; ambiguity is listed."),
            ProcessStep("M2", "Separate observations, hypotheses, and unknowns",
                        "Prevent interpretation from being mistaken for evidence.",
                        "Knowns / hypotheses / unknowns lists",
                        "Every item has a clear epistemic category."),
            ProcessStep("M3", "Generate and compare candidate approaches",
                        "Keep plausible alternatives open until evidence or constraints distinguish them.",
                        "Candidate approaches with trade-offs",
                        "Candidates are compared against the same criteria."),
            ProcessStep("M4", "Define verification and failure conditions",
                        "Make success testable before accepting a candidate.",
                        "Verification plan with pass/fail criteria",
                        "Each major claim has an observable check or is marked unverified."),
            ProcessStep("M5", "Converge provisionally and preserve residuals",
                        "Produce an actionable result without hiding unresolved uncertainty.",
                        "Recommendation, rationale, residual unknowns",
                        "The output distinguishes selected option, evidence, and open questions."),
        ]

    @staticmethod
    def _debug_steps() -> List[ProcessStep]:
        return [
            ProcessStep("D1", "Capture the failure",
                        "Record exact input, expected result, actual result, environment, and reproduction steps.",
                        "Minimal reproducible failure report",
                        "The observed failure can be reproduced or the reproduction gap is explicit."),
            ProcessStep("D2", "Map the contract and execution path",
                        "Identify the violated interface, invariant, dependency, or state transition.",
                        "Relevant code path and contract checklist",
                        "The affected boundary and expected behaviour are named."),
            ProcessStep("D3", "Form competing cause hypotheses",
                        "Avoid committing to the first plausible explanation.",
                        "Ranked hypotheses with supporting and contradicting evidence",
                        "Each hypothesis has a discriminating test or observation."),
            ProcessStep("D4", "Design the smallest discriminating test",
                        "Reduce ambiguity before changing implementation.",
                        "Failing test, minimal reproduction, or explicit manual check",
                        "The test would produce different outcomes for the leading hypotheses."),
            ProcessStep("D5", "Apply the narrowest justified change",
                        "Fix the demonstrated cause while preserving unrelated contracts.",
                        "Patch proposal and expected behavioural change",
                        "The change maps to evidence and does not silently widen scope."),
            ProcessStep("D6", "Verify and record residual uncertainty",
                        "Check regression risk and report only tests actually executed.",
                        "Test results, regression coverage, unresolved risks",
                        "Actual test outcomes and any unrun checks are reported separately."),
        ]


def build_debug_demo() -> ProcessPlan:
    """Reproducible demo with illustrative—not normative—debugging context."""
    request = MiddleRequest(
        goal="Find and correct a reproducible input-validation defect without breaking the public contract.",
        constraints=(
            "Do not change unrelated behaviour.",
            "Do not infer an unconfirmed root cause.",
            "Report tests as passed only if they were executed.",
        ),
        task_domain="programming_debugging",
        context={
            "observations": (
                "A test reports that malformed input is accepted.",
                "The intended acceptance condition is described in the task statement.",
            ),
            "hypotheses": (
                "The validation predicate may omit an edge case.",
                "The test fixture may not represent the stated malformed input.",
            ),
            "unknowns": (
                "The exact function and failing input have not yet been supplied.",
            ),
        },
    )
    return MiddleMold().build_plan(request)


if __name__ == "__main__":
    plan = build_debug_demo()
    print(f"{plan.mold_name} v{plan.mold_version}")
    print("Domain:", plan.task_domain)
    print("Steps:", " -> ".join(step.step_id for step in plan.steps))
    print("Knowns:", len(plan.knowns), "| Hypotheses:", len(plan.hypotheses), "| Unknowns:", len(plan.unknowns))
    print("Execution: plan only (no code or tests executed by Middle Mold)")
