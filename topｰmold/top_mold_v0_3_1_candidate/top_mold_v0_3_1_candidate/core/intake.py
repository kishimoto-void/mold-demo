"""Validate structured intake packets; no semantic interpretation of free text is attempted."""
from copy import deepcopy
from .errors import IntakeError

DECISIONS = {"READY", "CLARIFICATION_REQUIRED", "BLOCKED"}
PRIORITIES = {"must", "should", "could"}
SOURCES = {"explicit", "inferred"}
IMPACTS = {"low", "medium", "high"}


def _object(value, name):
    if not isinstance(value, dict):
        raise IntakeError(f"{name} must be an object")
    return value


def _nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise IntakeError(f"{name} must be a non-empty string")
    return value


def _list(value, name):
    if not isinstance(value, list):
        raise IntakeError(f"{name} must be a list")
    return value


def _check_unique_ids(items, name):
    ids = []
    for i, item in enumerate(items):
        item = _object(item, f"{name}[{i}]")
        ids.append(_nonempty(item.get("id"), f"{name}[{i}].id"))
    if len(ids) != len(set(ids)):
        raise IntakeError(f"{name} contains duplicate ids")


def validate_intake_packet(packet):
    packet = _object(packet, "intake packet")
    required = ("schema_version", "raw_request", "normalized_goal", "atomic_requirements",
                "known_constraints", "assumptions", "open_questions", "acceptance_criteria",
                "routing", "decision")
    missing = [key for key in required if key not in packet]
    if missing:
        raise IntakeError(f"missing required fields: {', '.join(missing)}")
    if packet["schema_version"] != "1.0":
        raise IntakeError("unsupported intake schema_version")
    _nonempty(packet["raw_request"], "raw_request")
    _nonempty(packet["normalized_goal"], "normalized_goal")
    if "task_id" in packet:
        _nonempty(packet["task_id"], "task_id")
    if "context_refs" in packet:
        context_refs = _list(packet["context_refs"], "context_refs")
        if any(not isinstance(ref, str) or not ref.strip() for ref in context_refs):
            raise IntakeError("context_refs must contain non-empty strings")
        if len(context_refs) != len(set(context_refs)):
            raise IntakeError("context_refs must not contain duplicates")

    reqs = _list(packet["atomic_requirements"], "atomic_requirements")
    _check_unique_ids(reqs, "atomic_requirements")
    for i, req in enumerate(reqs):
        _nonempty(req.get("text"), f"atomic_requirements[{i}].text")
        if not isinstance(req.get("priority"), str) or req.get("priority") not in PRIORITIES:
            raise IntakeError(f"atomic_requirements[{i}].priority must be must/should/could")
        if not isinstance(req.get("source"), str) or req.get("source") not in SOURCES:
            raise IntakeError(f"atomic_requirements[{i}].source must be explicit/inferred")

    constraints = _list(packet["known_constraints"], "known_constraints")
    _check_unique_ids(constraints, "known_constraints")
    for i, constraint in enumerate(constraints):
        _nonempty(constraint.get("kind"), f"known_constraints[{i}].kind")
        if not isinstance(constraint.get("severity", "must"), str) or constraint.get("severity", "must") not in PRIORITIES:
            raise IntakeError(f"known_constraints[{i}].severity must be must/should/could")
        if "value" not in constraint:
            raise IntakeError(f"known_constraints[{i}].value is required")
        kind, value = constraint["kind"], constraint["value"]
        if kind == "forbidden_execution_mode" and (not isinstance(value, str) or not value.strip()):
            raise IntakeError(f"known_constraints[{i}].value must be a non-empty execution mode")
        if kind == "allowed_execution_modes":
            allowed_modes = _list(value, f"known_constraints[{i}].value")
            if any(not isinstance(mode, str) or not mode.strip() for mode in allowed_modes):
                raise IntakeError(f"known_constraints[{i}].value must contain non-empty execution modes")
            if len(allowed_modes) != len(set(allowed_modes)):
                raise IntakeError(f"known_constraints[{i}].value must not contain duplicate modes")
        if kind == "requires_approval" and not isinstance(value, bool):
            raise IntakeError(f"known_constraints[{i}].value must be boolean for requires_approval")

    assumptions = _list(packet["assumptions"], "assumptions")
    _check_unique_ids(assumptions, "assumptions")
    for i, assumption in enumerate(assumptions):
        _nonempty(assumption.get("statement"), f"assumptions[{i}].statement")
        confidence = assumption.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise IntakeError(f"assumptions[{i}].confidence must be between 0 and 1")
        if not isinstance(assumption.get("impact"), str) or assumption.get("impact") not in IMPACTS:
            raise IntakeError(f"assumptions[{i}].impact must be low/medium/high")
        if not isinstance(assumption.get("source", "inferred"), str) or assumption.get("source", "inferred") not in SOURCES:
            raise IntakeError(f"assumptions[{i}].source must be explicit/inferred")

    questions = _list(packet["open_questions"], "open_questions")
    _check_unique_ids(questions, "open_questions")
    for i, question in enumerate(questions):
        _nonempty(question.get("question"), f"open_questions[{i}].question")
        if not isinstance(question.get("blocking"), bool):
            raise IntakeError(f"open_questions[{i}].blocking must be boolean")

    criteria = _list(packet["acceptance_criteria"], "acceptance_criteria")
    _check_unique_ids(criteria, "acceptance_criteria")
    for i, criterion in enumerate(criteria):
        _nonempty(criterion.get("text"), f"acceptance_criteria[{i}].text")

    routing = _object(packet["routing"], "routing")
    input_types = _list(routing.get("input_types"), "routing.input_types")
    if any(not isinstance(x, str) or not x.strip() for x in input_types):
        raise IntakeError("routing.input_types must contain non-empty strings")
    if len(input_types) != len(set(input_types)):
        raise IntakeError("routing.input_types must not contain duplicates")
    capabilities = _list(routing.get("required_capabilities"), "routing.required_capabilities")
    if any(not isinstance(x, str) or not x.strip() for x in capabilities):
        raise IntakeError("routing.required_capabilities must contain non-empty strings")
    if len(capabilities) != len(set(capabilities)):
        raise IntakeError("routing.required_capabilities must not contain duplicates")
    output_contract = _object(routing.get("output_contract"), "routing.output_contract")
    output_types = _list(output_contract.get("required_types"), "routing.output_contract.required_types")
    if any(not isinstance(x, str) or not x.strip() for x in output_types):
        raise IntakeError("routing.output_contract.required_types must contain non-empty strings")
    if len(output_types) != len(set(output_types)):
        raise IntakeError("routing.output_contract.required_types must not contain duplicates")
    if not isinstance(routing.get("risk_level", "low"), str) or routing.get("risk_level", "low") not in IMPACTS:
        raise IntakeError("routing.risk_level must be low/medium/high")
    policy = routing.get("policy", {})
    _object(policy, "routing.policy")
    for key in ("approval_required", "approval_granted"):
        if key in policy and not isinstance(policy[key], bool):
            raise IntakeError(f"routing.policy.{key} must be boolean")
    for key in ("allowed_execution_modes", "forbidden_execution_modes"):
        if key in policy:
            values = _list(policy[key], f"routing.policy.{key}")
            if any(not isinstance(x, str) or not x.strip() for x in values):
                raise IntakeError(f"routing.policy.{key} must contain non-empty strings")
            if len(values) != len(set(values)):
                raise IntakeError(f"routing.policy.{key} must not contain duplicates")

    decision = _object(packet["decision"], "decision")
    status = decision.get("status")
    if not isinstance(status, str) or status not in DECISIONS:
        raise IntakeError("decision.status must be READY/CLARIFICATION_REQUIRED/BLOCKED")
    blocking = [q for q in questions if q["blocking"]]
    if status == "READY" and blocking:
        raise IntakeError("contradictory decision: READY cannot contain blocking open questions")
    if status == "CLARIFICATION_REQUIRED" and not blocking:
        raise IntakeError("CLARIFICATION_REQUIRED requires at least one blocking open question")
    if status == "BLOCKED":
        _nonempty(decision.get("reason"), "decision.reason")
    return deepcopy(packet)


def task_from_intake(packet):
    normalized = validate_intake_packet(packet)
    status = normalized["decision"]["status"]
    if status != "READY":
        raise IntakeError(f"cannot create Task Envelope while decision is {status}")
    route = normalized["routing"]
    return {
        "schema_version": "1.0",
        "task_id": normalized.get("task_id", "TASK-FROM-INTAKE"),
        "goal": normalized["normalized_goal"],
        "input_types": list(route["input_types"]),
        "required_capabilities": list(route["required_capabilities"]),
        "output_contract": deepcopy(route["output_contract"]),
        "constraints": deepcopy(normalized["known_constraints"]),
        "policy": deepcopy(route.get("policy", {})),
        "risk_level": route.get("risk_level", "low"),
        "context_refs": deepcopy(normalized.get("context_refs", [])),
        "acceptance_criteria": deepcopy(normalized["acceptance_criteria"]),
        "assumptions": deepcopy(normalized["assumptions"]),
    }
