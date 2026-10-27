"""Consistency validation for processor result envelopes.

This validates whether status claims agree with the declared fields. It does not
establish factual or semantic correctness of outputs.
"""
from copy import deepcopy
from .errors import PlanningError

RESULT_STATUSES = {"NOT_EXECUTED", "SUCCESS", "PARTIAL", "FAILED", "SKIPPED"}
EXECUTION_STATUSES = {"NOT_INVOKED", "SUCCEEDED", "FAILED", "SKIPPED"}
VERIFICATION_STATUSES = {"NOT_RUN", "UNVERIFIED", "VERIFIED", "FAILED"}
CHECK_STATUSES = {"PASS", "FAIL", "UNVERIFIED", "SKIPPED"}


def _string(value, field):
    if not isinstance(value, str) or not value.strip():
        raise PlanningError(f"{field} must be a non-empty string")
    return value


def _string_array(value, field, *, allow_empty=True, unique=False):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise PlanningError(f"{field} must be a list of non-empty strings")
    if not allow_empty and not value:
        raise PlanningError(f"{field} must not be empty")
    if unique and len(value) != len(set(value)):
        raise PlanningError(f"{field} must not contain duplicates")
    return value


def validate_result_envelope(result, expected_task_id=None):
    """Validate result/status consistency, without asserting semantic truth."""
    if not isinstance(result, dict):
        raise PlanningError("result envelope must be an object")
    if result.get("schema_version") != "1.0":
        raise PlanningError("unsupported or missing result schema_version")
    for field in ("result_id", "task_id", "processor_id", "processor_version"):
        _string(result.get(field), field)
    if expected_task_id is not None:
        _string(expected_task_id, "expected_task_id")
        if result["task_id"] != expected_task_id:
            raise PlanningError("result task_id does not match the expected task_id")

    execution_status = result.get("execution_status")
    result_status = result.get("result_status")
    if not isinstance(execution_status, str) or execution_status not in EXECUTION_STATUSES:
        raise PlanningError("execution_status is invalid")
    if not isinstance(result_status, str) or result_status not in RESULT_STATUSES:
        raise PlanningError("result_status is invalid")

    output_types = _string_array(result.get("output_types"), "output_types", unique=True)
    outputs = result.get("outputs")
    if not isinstance(outputs, (dict, list)):
        raise PlanningError("outputs must be an object or list")
    evidence_refs = _string_array(result.get("evidence_refs", []), "evidence_refs", unique=True)
    assumptions = result.get("assumptions", [])
    unresolved = result.get("unresolved_items", [])
    _string_array(assumptions, "assumptions")
    _string_array(unresolved, "unresolved_items")

    verification = result.get("verification")
    if not isinstance(verification, dict):
        raise PlanningError("verification must be an object")
    verification_status = verification.get("status")
    if not isinstance(verification_status, str) or verification_status not in VERIFICATION_STATUSES:
        raise PlanningError("verification.status is invalid")
    checks = verification.get("checks", [])
    if not isinstance(checks, list):
        raise PlanningError("verification.checks must be a list")
    seen_check_ids = set()
    for i, check in enumerate(checks):
        if not isinstance(check, dict):
            raise PlanningError(f"verification.checks[{i}] must be an object")
        check_id = _string(check.get("id"), f"verification.checks[{i}].id")
        if check_id in seen_check_ids:
            raise PlanningError("verification check IDs must be unique")
        seen_check_ids.add(check_id)
        if not isinstance(check.get("status"), str) or check.get("status") not in CHECK_STATUSES:
            raise PlanningError(f"verification.checks[{i}].status is invalid")

    error = result.get("error")
    if result_status == "NOT_EXECUTED":
        if execution_status != "NOT_INVOKED" or verification_status != "NOT_RUN":
            raise PlanningError("NOT_EXECUTED requires NOT_INVOKED and verification NOT_RUN")
        if output_types or outputs not in ({}, []):
            raise PlanningError("NOT_EXECUTED cannot contain claimed outputs")
        if checks:
            raise PlanningError("NOT_EXECUTED cannot claim verification checks")
    elif result_status == "SUCCESS":
        if execution_status != "SUCCEEDED" or verification_status != "VERIFIED":
            raise PlanningError("SUCCESS requires SUCCEEDED execution and VERIFIED result")
        if not output_types or outputs in ({}, []):
            raise PlanningError("SUCCESS requires output types and non-empty outputs")
        if not checks or any(c["status"] != "PASS" for c in checks):
            raise PlanningError("SUCCESS requires non-empty all-PASS verification checks")
        if unresolved:
            raise PlanningError("SUCCESS cannot retain unresolved items")
    elif result_status == "PARTIAL":
        if execution_status not in {"SUCCEEDED", "FAILED"}:
            raise PlanningError("PARTIAL requires an attempted execution")
        if not unresolved and verification_status == "VERIFIED" and all(c["status"] == "PASS" for c in checks):
            raise PlanningError("PARTIAL requires unresolved items or non-verified checks")
    elif result_status == "FAILED":
        if execution_status not in {"FAILED", "SUCCEEDED"} or verification_status not in {"FAILED", "UNVERIFIED"}:
            raise PlanningError("FAILED requires failed execution or a failed/unverified verification")
        if not isinstance(error, dict) or not isinstance(error.get("code"), str) or not error.get("code", "").strip():
            raise PlanningError("FAILED requires an error object with a non-empty code")
    elif result_status == "SKIPPED":
        if execution_status != "SKIPPED" or verification_status != "NOT_RUN":
            raise PlanningError("SKIPPED requires execution_status SKIPPED and verification NOT_RUN")
        if output_types or outputs not in ({}, []):
            raise PlanningError("SKIPPED cannot contain claimed outputs")
        if checks:
            raise PlanningError("SKIPPED cannot claim verification checks")

    normalized = deepcopy(result)
    normalized.setdefault("evidence_refs", [])
    normalized.setdefault("assumptions", [])
    normalized.setdefault("unresolved_items", [])
    normalized["claims_validated"] = True
    normalized["semantic_correctness"] = "NOT_ASSESSED"
    return normalized
