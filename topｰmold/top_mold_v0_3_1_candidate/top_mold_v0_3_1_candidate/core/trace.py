"""Privacy-minimizing trace record builder. Does not persist or send records."""
from datetime import datetime, timezone
import hashlib
import platform
import uuid

TOP_MOLD_VERSION = "0.3.1-draft"
PLAN_STATUSES = {"COMPLETE", "PARTIAL", "BLOCKED"}
PLAN_MODES = {"PLAN_ONLY"}


def _need_string(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def build_trace_record(task, plan, *, include_request_fingerprint=False):
    """Create an in-memory trace record; raw request text is never included."""
    if not isinstance(task, dict) or not isinstance(plan, dict):
        raise ValueError("task and plan must be objects")
    if not isinstance(include_request_fingerprint, bool):
        raise ValueError("include_request_fingerprint must be boolean")
    task_id = task.get("task_id")
    _need_string(task_id, "task.task_id")
    if plan.get("task_id") != task_id:
        raise ValueError("task and plan task_id do not match")

    plan_status = plan.get("plan_status")
    plan_mode = plan.get("plan_mode")
    execution_status = plan.get("execution_status")
    if not isinstance(plan_status, str) or plan_status not in PLAN_STATUSES:
        raise ValueError("plan.plan_status is invalid")
    if not isinstance(plan_mode, str) or plan_mode not in PLAN_MODES:
        raise ValueError("plan.plan_mode is invalid")
    if execution_status != "NOT_INVOKED":
        raise ValueError("trace builder accepts plan-only records; execution_status must be NOT_INVOKED")
    execution_invoked = plan.get("execution_invoked")
    if execution_invoked is not False:
        raise ValueError("trace builder requires execution_invoked=false for plan-only records")

    steps = plan.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("plan.steps must be a list")
    selected_processors = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"plan.steps[{i}] must be an object")
        _need_string(step.get("processor_id"), f"plan.steps[{i}].processor_id")
        _need_string(step.get("processor_version"), f"plan.steps[{i}].processor_version")
        _need_string(step.get("execution_mode"), f"plan.steps[{i}].execution_mode")
        selected_processors.append({
            "id": step["processor_id"],
            "version": step["processor_version"],
            "execution_mode": step["execution_mode"],
        })

    diagnostics = plan.get("diagnostics", [])
    if not isinstance(diagnostics, list):
        raise ValueError("plan.diagnostics must be a list")
    diagnostic_codes = []
    for i, diagnostic in enumerate(diagnostics):
        if not isinstance(diagnostic, dict):
            raise ValueError(f"plan.diagnostics[{i}] must be an object")
        code = diagnostic.get("code")
        if code is not None:
            _need_string(code, f"plan.diagnostics[{i}].code")
            diagnostic_codes.append(code)

    record = {
        "schema_version": "1.0",
        "trace_id": "TRACE-" + uuid.uuid4().hex,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "top_mold_version": TOP_MOLD_VERSION,
        "task_id": task_id,
        "plan_status": plan_status,
        "plan_mode": plan_mode,
        "execution_status": execution_status,
        "execution_invoked": execution_invoked,
        "selected_processors": selected_processors,
        "diagnostic_codes": diagnostic_codes,
        "runtime": {"python_version": platform.python_version(), "platform": platform.system()},
        "raw_input_included": False,
    }
    if include_request_fingerprint:
        raw = task.get("raw_request", task.get("goal", ""))
        if not isinstance(raw, str):
            raise ValueError("request fingerprint source must be a string")
        record["request_fingerprint"] = {
            "algorithm": "sha256",
            "digest": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        }
        record["fingerprint_notice"] = "A digest can still be linkable; use only when correlation is necessary."
    return record
