"""Strict processor registry loading and validation."""
import json
from pathlib import Path
from .errors import PlanningError, RegistryError

ALLOWED_STATUSES = {"active", "disabled", "deprecated", "experimental"}


def _strings(value, field, *, allow_empty=False):
    if not isinstance(value, list) or (not allow_empty and not value):
        raise RegistryError(f"{field} must be {'a possibly empty' if allow_empty else 'a non-empty'} list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise RegistryError(f"{field} must contain only non-empty strings")
    if len(set(value)) != len(value):
        raise RegistryError(f"{field} must not contain duplicates")
    return value


def validate_processor_registry(data):
    if not isinstance(data, dict):
        raise RegistryError("processor registry must be an object")
    if data.get("schema_version") != "1.0":
        raise RegistryError("unsupported or missing processor registry schema_version")
    processors = data.get("processors")
    if not isinstance(processors, list):
        raise RegistryError("processor registry must contain a processors list")
    seen = set()
    normalized = []
    for index, processor in enumerate(processors):
        prefix = f"processors[{index}]"
        if not isinstance(processor, dict):
            raise RegistryError(f"{prefix} must be an object")
        for key in ("id", "version", "status", "execution_mode"):
            if not isinstance(processor.get(key), str) or not processor[key].strip():
                raise RegistryError(f"{prefix}.{key} must be a non-empty string")
        pid = processor["id"]
        if pid in seen:
            raise RegistryError(f"duplicate processor id: {pid}")
        seen.add(pid)
        if processor["status"] not in ALLOWED_STATUSES:
            raise RegistryError(f"{prefix}.status is unsupported: {processor['status']}")
        capabilities = _strings(processor.get("capabilities"), f"{prefix}.capabilities")
        accepts = _strings(processor.get("accepts", []), f"{prefix}.accepts", allow_empty=True)
        produces = _strings(processor.get("produces"), f"{prefix}.produces")
        priority = processor.get("priority", 0)
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise RegistryError(f"{prefix}.priority must be an integer")
        normalized.append({**processor, "capabilities": capabilities, "accepts": accepts,
                           "produces": produces, "priority": priority})
    return {**data, "processors": normalized}


def load_processor_registry(path: str | Path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot load processor registry: {exc}") from exc
    return validate_processor_registry(data)


def validate_mold_registry(data):
    if not isinstance(data, dict) or data.get("schema_version") != "1.0":
        raise RegistryError("mold registry must be an object with schema_version 1.0")
    molds = data.get("molds")
    if not isinstance(molds, list):
        raise RegistryError("mold registry must contain a molds list")
    ids = []
    for index, item in enumerate(molds):
        if not isinstance(item, dict):
            raise RegistryError(f"molds[{index}] must be an object")
        for key in ("id", "name", "version", "status"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise RegistryError(f"molds[{index}].{key} must be a non-empty string")
        ids.append(item["id"])
    if len(ids) != len(set(ids)):
        raise RegistryError("duplicate mold id")
    return molds


def load_mold_registry(path: str | Path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot load mold registry: {exc}") from exc
    return validate_mold_registry(data)
