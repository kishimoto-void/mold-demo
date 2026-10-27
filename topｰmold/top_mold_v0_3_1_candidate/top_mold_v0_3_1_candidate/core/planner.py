"""Deterministic, plan-only capability routing."""
from copy import deepcopy
from .errors import PlanningError
from .registry import validate_processor_registry

RISK_LEVELS = {"low", "medium", "high"}
MAX_ROUTE_STEPS = 256


def _nonempty_str(value, field):
    if not isinstance(value, str) or not value.strip():
        raise PlanningError(f"{field} must be a non-empty string")


def _string_list(value, field):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise PlanningError(f"{field} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise PlanningError(f"{field} must not contain duplicates")
    return value


def validate_task(task):
    if not isinstance(task, dict):
        raise PlanningError("task envelope must be an object")
    if task.get("schema_version") != "1.0":
        raise PlanningError("unsupported or missing task schema_version")
    _nonempty_str(task.get("task_id"), "task_id")
    _nonempty_str(task.get("goal"), "goal")
    input_types = _string_list(task.get("input_types"), "input_types")
    required = _string_list(task.get("required_capabilities"), "required_capabilities")
    if len(required) > MAX_ROUTE_STEPS:
        raise PlanningError(f"required_capabilities exceeds the {MAX_ROUTE_STEPS}-step safety limit")
    contract = task.get("output_contract")
    if not isinstance(contract, dict):
        raise PlanningError("output_contract must be an object")
    required_types = _string_list(contract.get("required_types"), "output_contract.required_types")
    if not required_types:
        raise PlanningError("output_contract.required_types must not be empty")
    constraints = task.get("constraints", [])
    if not isinstance(constraints, list):
        raise PlanningError("constraints must be a list")
    for index, item in enumerate(constraints):
        if not isinstance(item, dict):
            raise PlanningError(f"constraints[{index}] must be an object")
        _nonempty_str(item.get("kind"), f"constraints[{index}].kind")
        if "value" not in item:
            raise PlanningError(f"constraints[{index}].value is required")
        if not isinstance(item.get("severity", "must"), str) or item.get("severity", "must") not in {"must", "should", "could"}:
            raise PlanningError(f"constraints[{index}].severity is invalid")
        kind = item["kind"]
        if kind == "forbidden_execution_mode" and (not isinstance(item["value"], str) or not item["value"].strip()):
            raise PlanningError(f"constraints[{index}].value must be an execution-mode string")
        if kind == "allowed_execution_modes":
            _string_list(item["value"], f"constraints[{index}].value")
            # An explicit empty list means deny every execution mode.
        if kind == "requires_approval" and not isinstance(item["value"], bool):
            raise PlanningError(f"constraints[{index}].value must be boolean")
    policy = task.get("policy", {})
    if not isinstance(policy, dict):
        raise PlanningError("policy must be an object")
    for key in ("allowed_execution_modes", "forbidden_execution_modes"):
        if key in policy:
            _string_list(policy[key], f"policy.{key}")
    if "allowed_execution_modes" in policy and not policy["allowed_execution_modes"]:
        # An explicit empty allow-list means no mode is permitted, not "no restriction".
        pass
    for key in ("approval_required", "approval_granted"):
        if key in policy and not isinstance(policy[key], bool):
            raise PlanningError(f"policy.{key} must be boolean")
    risk = task.get("risk_level", "low")
    if not isinstance(risk, str) or risk not in RISK_LEVELS:
        raise PlanningError("risk_level must be low/medium/high")
    return {**deepcopy(task), "input_types": input_types, "required_capabilities": required,
            "output_contract": {**contract, "required_types": required_types}, "policy": dict(policy)}


def _policy_from_task(task):
    policy = dict(task.get("policy", {}))
    forbidden = set(policy.get("forbidden_execution_modes", []))
    allowed = set(policy["allowed_execution_modes"]) if "allowed_execution_modes" in policy else None
    approval_required = policy.get("approval_required", False)
    approval_granted = policy.get("approval_granted", False)
    hard_unmet = []
    soft_unverified = []
    for constraint in task.get("constraints", []):
        kind, value = constraint["kind"], constraint["value"]
        severity = constraint.get("severity", "must")
        if kind == "forbidden_execution_mode":
            forbidden.add(str(value))
        elif kind == "allowed_execution_modes":
            c_allowed = set(value) if isinstance(value, list) else set()
            allowed = c_allowed if allowed is None else allowed.intersection(c_allowed)
        elif kind == "requires_approval":
            # A task constraint may require approval, but a later false value must
            # never weaken an explicit requirement from policy or another constraint.
            approval_required = approval_required or value
        elif severity == "must":
            hard_unmet.append({"code": "UNSUPPORTED_HARD_CONSTRAINT", "constraint": constraint})
        else:
            soft_unverified.append({"code": "UNSUPPORTED_SOFT_CONSTRAINT", "constraint": constraint})
    return forbidden, allowed, approval_required, approval_granted, hard_unmet, soft_unverified


def build_plan(task, registry_data, *, max_search_nodes=10000):
    """Build a deterministic plan without invoking processors or adapters.

    ``max_search_nodes`` bounds worst-case search growth for wide registries.
    """
    if isinstance(max_search_nodes, bool) or not isinstance(max_search_nodes, int) or max_search_nodes < 1:
        raise PlanningError("max_search_nodes must be a positive integer")
    task = validate_task(task)
    registry = validate_processor_registry(registry_data)
    forbidden, allowed, approval_required, approval_granted, hard_unmet, soft_unverified = _policy_from_task(task)
    required_caps = task["required_capabilities"]
    required_outputs = task["output_contract"]["required_types"]
    diagnostics = []
    if hard_unmet:
        diagnostics.extend({"code": item["code"], "message": "A mandatory constraint has no registered evaluator.",
                            "details": item["constraint"]} for item in hard_unmet)
    if soft_unverified:
        diagnostics.extend({"code": item["code"], "message": "A non-mandatory constraint is not interpreted by the core planner.",
                            "details": item["constraint"]} for item in soft_unverified)
    if approval_required and not approval_granted:
        diagnostics.append({"code": "APPROVAL_REQUIRED", "message": "Required approval has not been recorded; no route was planned."})
        return {
            "schema_version": "1.0", "task_id": task["task_id"], "risk_level": task.get("risk_level", "low"),
            "plan_status": "BLOCKED", "plan_mode": "PLAN_ONLY", "execution_status": "NOT_INVOKED", "execution_invoked": False,
            "steps": [], "capability_coverage": {cap: False for cap in required_caps},
            "unmet_capabilities": list(required_caps), "unmet_output_types": list(required_outputs),
            "constraint_violations": [], "unverified_constraints": hard_unmet + soft_unverified,
            "diagnostics": diagnostics, "warnings": ["No processor or adapter was invoked."],
            "final_types": list(task["input_types"]),
        }
    if not required_caps:
        diagnostics.append({"code": "EMPTY_REQUIRED_CAPABILITIES", "message": "No required capabilities were provided."})
        status = "PARTIAL"
        return {
            "schema_version": "1.0", "task_id": task["task_id"], "plan_status": status,
            "plan_mode": "PLAN_ONLY", "execution_status": "NOT_INVOKED", "execution_invoked": False,
            "steps": [], "capability_coverage": {}, "unmet_capabilities": [],
            "unmet_output_types": list(required_outputs), "constraint_violations": [],
            "unverified_constraints": hard_unmet + soft_unverified,
            "diagnostics": diagnostics, "warnings": ["No processor or adapter was invoked."],
            "final_types": list(task["input_types"]),
        }

    processors = registry["processors"]
    active = [p for p in processors if p["status"] == "active"]
    candidates_by_cap = {}
    for cap in required_caps:
        eligible = [p for p in active if cap in p["capabilities"]
                    and p["execution_mode"] not in forbidden
                    and (allowed is None or p["execution_mode"] in allowed)]
        candidates_by_cap[cap] = sorted(eligible, key=lambda p: (-p["priority"], p["id"]))

    # Search for a complete compatible chain first. If none exists, return the longest
    # reachable prefix; ties preserve deterministic priority/ID ordering.
    def failure_for(cap, current_types):
        candidates = candidates_by_cap[cap]
        compatible = [p for p in candidates if not p["accepts"] or set(p["accepts"]).intersection(current_types)]
        if compatible:
            return None
        if not candidates:
            capable_any = [p for p in processors if cap in p["capabilities"] and p["status"] == "active"]
            if capable_any and all(p["execution_mode"] in forbidden or
                                    (allowed is not None and p["execution_mode"] not in allowed)
                                    for p in capable_any):
                return ("FORBIDDEN_EXECUTION_MODE", "All active processors for this capability violate the execution-mode policy.")
            return ("NO_PROVIDER", "No eligible active processor declares this capability.")
        return ("INPUT_TYPE_MISMATCH", "Eligible processors exist, but none accepts the current data types.")

    search_nodes = 0
    search_limit_reached = False

    def search(index, current_types, steps):
        nonlocal search_nodes, search_limit_reached
        if index == len(required_caps):
            return {"full": True, "steps": steps, "final_types": current_types, "failure": None}
        cap = required_caps[index]
        if search_nodes >= max_search_nodes:
            search_limit_reached = True
            return {"full": False, "steps": steps, "final_types": current_types,
                    "failure": (cap, ("PLANNING_SEARCH_LIMIT", "Route search reached the configured node limit."))}
        search_nodes += 1
        compatible = [p for p in candidates_by_cap[cap]
                      if not p["accepts"] or set(p["accepts"]).intersection(current_types)]
        if not compatible:
            return {"full": False, "steps": steps, "final_types": current_types,
                    "failure": (cap, failure_for(cap, current_types))}
        partial_results = []
        for processor in compatible:
            step = {"step_index": index + 1, "required_capability": cap,
                    "processor_id": processor["id"], "processor_version": processor["version"],
                    "execution_mode": processor["execution_mode"], "input_types": list(current_types),
                    "output_types": list(processor["produces"]), "status": "PLANNED"}
            found = search(index + 1, list(processor["produces"]), steps + [step])
            if found["full"]:
                return found
            partial_results.append(found)
            if search_limit_reached:
                break
        # max() keeps the first result on ties; candidates are already sorted by priority then ID.
        return max(partial_results, key=lambda item: len(item["steps"]))

    route = search(0, list(task["input_types"]), [])
    steps = route["steps"]
    final_types = route["final_types"]
    if not route["full"] and route["failure"]:
        failure_cap, failure_reason = route["failure"]
        if failure_reason:
            diagnostics.append({"code": failure_reason[0], "message": failure_reason[1], "capability": failure_cap})
    if search_limit_reached and not any(d.get("code") == "PLANNING_SEARCH_LIMIT" for d in diagnostics):
        diagnostics.append({"code": "PLANNING_SEARCH_LIMIT", "message": f"Route search stopped after {max_search_nodes} nodes; this plan is incomplete."})
    for step in steps:
        step["status"] = "PLANNED" if route["full"] else "PLANNED_PARTIAL"

    selected_caps = {step["required_capability"] for step in steps}
    coverage = {cap: cap in selected_caps for cap in required_caps}
    unmet_caps = [cap for cap in required_caps if not coverage[cap]]
    unmet_outputs = [out for out in required_outputs if out not in final_types]
    if unmet_outputs:
        diagnostics.append({"code": "OUTPUT_CONTRACT_UNMET", "message": "The planned route does not produce all required output types.", "unmet_output_types": unmet_outputs})
    if hard_unmet:
        diagnostics.append({"code": "HARD_CONSTRAINT_UNVERIFIED", "message": "A mandatory constraint cannot be validated by the core planner."})
    status = "COMPLETE" if not unmet_caps and not unmet_outputs and not hard_unmet else "PARTIAL"
    if not unmet_caps and not unmet_outputs and not hard_unmet:
        diagnostics.append({"code": "PLAN_CONTRACT_SATISFIED", "message": "Declared capabilities and output types are covered by the planned route."})
    warnings = ["Planning only: no LLM, tool, external service, or processor was invoked."]
    if hard_unmet:
        warnings.append("At least one mandatory constraint requires a specialized validator before execution.")
    if soft_unverified:
        warnings.append("One or more non-mandatory constraints remain unverified; inspect diagnostics.")
    return {
        "schema_version": "1.0", "task_id": task["task_id"], "risk_level": task.get("risk_level", "low"),
        "plan_status": status, "plan_mode": "PLAN_ONLY", "execution_status": "NOT_INVOKED", "execution_invoked": False,
        "steps": steps, "capability_coverage": coverage, "unmet_capabilities": unmet_caps,
        "unmet_output_types": unmet_outputs, "constraint_violations": [],
        "unverified_constraints": hard_unmet + soft_unverified,
        "diagnostics": diagnostics, "warnings": warnings, "final_types": final_types,
    }
