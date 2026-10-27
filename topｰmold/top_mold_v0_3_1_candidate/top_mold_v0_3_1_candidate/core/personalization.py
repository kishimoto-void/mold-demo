"""Portable personalization settings with explicit, non-authoritative dial overlays."""
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from .errors import DialConfigError

BASE_DIAL_IDS = [f"D-{n:03d}" for n in range(1, 9)]


def load_dial_catalog(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DialConfigError(f"cannot load dial catalog: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != "1.0" or not isinstance(data.get("dials"), list):
        raise DialConfigError("dial catalog must be an object with schema_version 1.0 and a dials list")
    catalog = {}
    for i, item in enumerate(data["dials"]):
        if not isinstance(item, dict):
            raise DialConfigError(f"dials[{i}] must be an object")
        dial_id, name = item.get("id"), item.get("name")
        if not isinstance(dial_id, str) or not dial_id.strip() or not isinstance(name, str) or not name.strip():
            raise DialConfigError(f"dials[{i}] requires non-empty id and name")
        dial_id, name = dial_id.strip(), name.strip()
        if dial_id in catalog:
            raise DialConfigError(f"duplicate dial id: {dial_id}")
        if not isinstance(item.get("description", ""), str):
            raise DialConfigError(f"dials[{i}].description must be a string")
        if not isinstance(item.get("advanced", False), bool):
            raise DialConfigError(f"dials[{i}].advanced must be boolean")
        catalog[dial_id] = {**item, "id": dial_id, "name": name}
    if not set(BASE_DIAL_IDS).issubset(catalog):
        raise DialConfigError("catalog must define D-001 through D-008")
    return catalog


def default_settings(catalog):
    return {"schema_version": "1.0", "active_dial_ids": list(BASE_DIAL_IDS),
            "values": {dial_id: 3 for dial_id in BASE_DIAL_IDS}}


def validate_settings(settings, catalog):
    if not isinstance(settings, dict):
        raise DialConfigError("settings must be an object")
    if settings.get("schema_version") != "1.0":
        raise DialConfigError("unsupported settings schema_version")
    active = settings.get("active_dial_ids")
    values = settings.get("values")
    if not isinstance(active, list) or any(not isinstance(x, str) or not x.strip() for x in active):
        raise DialConfigError("active_dial_ids must be a list of non-empty strings")
    if len(active) != len(set(active)):
        raise DialConfigError("active_dial_ids contains duplicates")
    unknown_active = sorted(set(active) - set(catalog))
    if unknown_active:
        raise DialConfigError(f"unregistered active dial ids: {', '.join(unknown_active)}")
    if not isinstance(values, dict):
        raise DialConfigError("values must be an object")
    if any(not isinstance(key, str) or not key.strip() for key in values):
        raise DialConfigError("values keys must be non-empty dial ID strings")
    unknown_values = sorted(set(values) - set(catalog))
    if unknown_values:
        raise DialConfigError(f"unregistered dial values: {', '.join(unknown_values)}")
    clean_values = {}
    for dial_id, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise DialConfigError(f"{dial_id} must be an integer from 1 to 5")
        clean_values[dial_id] = value
    for dial_id in active:
        clean_values.setdefault(dial_id, 3)
    return {"schema_version": "1.0", "active_dial_ids": list(active), "values": clean_values}


def load_settings(path, catalog):
    target = Path(path)
    try:
        if target.is_symlink() and not target.exists():
            raise DialConfigError("settings path is a dangling symlink; existing configuration was not replaced")
        if not target.exists():
            return default_settings(catalog)
        data = json.loads(target.read_text(encoding="utf-8"))
    except DialConfigError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DialConfigError(f"cannot load settings; existing file was not changed: {exc}") from exc
    return validate_settings(data, catalog)


def save_settings(path, settings, catalog):
    """Atomically replace settings only after validation and a successful temp write."""
    target = Path(path)
    normalized = validate_settings(settings, catalog)
    if target.is_symlink():
        raise DialConfigError("refusing to atomically replace a settings symlink; pass the target file path directly")
    temp_name = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent,
                                         prefix=f".{target.name}.", suffix=".tmp", delete=False) as temp:
            temp_name = temp.name
            json.dump(normalized, temp, ensure_ascii=False, indent=2)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_name, target)
    except OSError as exc:
        if temp_name and os.path.exists(temp_name):
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        raise DialConfigError(f"cannot save settings atomically: {exc}") from exc
    return normalized


def update_dial(settings, catalog, dial_id, value):
    if not isinstance(dial_id, str) or not dial_id.strip():
        raise DialConfigError("dial id must be a non-empty string")
    if dial_id not in catalog:
        raise DialConfigError(f"unregistered dial id: {dial_id}")
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise DialConfigError("dial value must be an integer from 1 to 5")
    updated = deepcopy(validate_settings(settings, catalog))
    if dial_id not in updated["active_dial_ids"]:
        updated["active_dial_ids"].append(dial_id)
    updated["values"][dial_id] = value
    return updated


def complexity_advice(settings, threshold=10):
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
        raise DialConfigError("complexity threshold must be a positive integer")
    if not isinstance(settings, dict):
        raise DialConfigError("settings must be an object")
    active = settings.get("active_dial_ids", [])
    if not isinstance(active, list) or any(not isinstance(item, str) or not item.strip() for item in active):
        raise DialConfigError("active_dial_ids must be a list of non-empty strings")
    if len(active) < threshold:
        return None
    return (f"有効な独立ダイヤルが {len(active)} 個あります。重複確認・グループ化を検討してください。"
            "これは提案のみで、統合・削除・値変更は自動実行しません。")


def select_visible_dials(catalog, settings, include_advanced=False):
    if not isinstance(catalog, dict) or not isinstance(settings, dict):
        raise DialConfigError("catalog and settings must be objects")
    active_ids = settings.get("active_dial_ids", [])
    if not isinstance(active_ids, list) or any(not isinstance(item, str) or not item.strip() for item in active_ids):
        raise DialConfigError("active_dial_ids must be a list of non-empty strings")
    if not isinstance(include_advanced, bool):
        raise DialConfigError("include_advanced must be boolean")
    active = set(active_ids)
    return {dial_id: spec for dial_id, spec in catalog.items()
            if dial_id in active or include_advanced or not spec.get("advanced", False)}


def build_dial_overlay(settings, catalog):
    normalized = validate_settings(settings, catalog)
    return {
        "schema_version": "1.0", "type": "personalization_dial_overlay",
        "authority": "presentation_preference_only",
        "note": "Dials steer requested output style; they do not create capability or override hard policy.",
        "dials": [{"id": dial_id, "name": catalog[dial_id]["name"],
                   "value": normalized["values"].get(dial_id, 3),
                   "description": catalog[dial_id].get("description", "")}
                  for dial_id in normalized["active_dial_ids"]],
    }


def build_personalization_overlay(settings, catalog, persona_seed=None, session_overrides=None):
    if persona_seed is not None and not isinstance(persona_seed, dict):
        raise DialConfigError("persona_seed must be an object or null")
    if session_overrides is not None and not isinstance(session_overrides, dict):
        raise DialConfigError("session_overrides must be an object or null")
    return {
        "schema_version": "1.0", "type": "personalization_overlay",
        "persona_seed": deepcopy(persona_seed),
        "dial_overlay": build_dial_overlay(settings, catalog),
        "session_overrides": deepcopy(session_overrides or {}),
        "precedence": ["hard_policy", "task_contract", "session_override", "dial_overlay", "persona_seed"],
        "authority": "presentation_preference_only",
        "warning": "This object is declarative. An adapter must interpret it; it does not control a model by itself.",
    }
