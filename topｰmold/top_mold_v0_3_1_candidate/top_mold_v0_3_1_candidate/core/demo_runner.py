"""Small, safe demonstrations. All examples are plan-only and side-effect free."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from .planner import build_plan
from .personalization import load_dial_catalog, default_settings, update_dial, complexity_advice
from .startup import inspect_persona_file
from .registry import load_processor_registry


def _task(root):
    return json.loads((root / "config" / "task.example.json").read_text(encoding="utf-8"))


def run_demo(demo_id, root):
    root = Path(root)
    if demo_id == "DEMO-001":
        with TemporaryDirectory(prefix="top-mold-demo-") as tmp:
            target = Path(tmp) / "absent-persona.md"
            state = inspect_persona_file(target)
        return json.dumps({"demo_id": demo_id, "persona_state": state.status,
                           "expected": "ABSENT", "file_modified": False,
                           "repository_files_modified": False}, ensure_ascii=False, indent=2)
    if demo_id == "DEMO-002":
        state = inspect_persona_file(root / "config" / "persona.example.md")
        return json.dumps({"demo_id": demo_id, "persona_state": state.status,
                           "existing_file_overwritten": False}, ensure_ascii=False, indent=2)
    if demo_id == "DEMO-003":
        catalog = load_dial_catalog(root / "config" / "dials.json")
        before = default_settings(catalog)
        after = update_dial(before, catalog, "D-002", 5)
        changed = sorted(d for d in set(before["values"]) | set(after["values"])
                         if before["values"].get(d) != after["values"].get(d))
        return json.dumps({"demo_id": demo_id, "changed_dials": changed,
                           "other_settings_preserved": changed == ["D-002"]}, ensure_ascii=False, indent=2)
    if demo_id == "DEMO-004":
        catalog = load_dial_catalog(root / "config" / "dials.json")
        settings = default_settings(catalog)
        for dial_id in ["D-009", "D-010"]:
            settings = update_dial(settings, catalog, dial_id, 3)
        return json.dumps({"demo_id": demo_id, "active_dials": len(settings["active_dial_ids"]),
                           "advice": complexity_advice(settings, 10),
                           "settings_auto_merged": False}, ensure_ascii=False, indent=2)
    if demo_id == "DEMO-005":
        task = _task(root)
        registry = load_processor_registry(root / "config" / "processor_registry.json")
        return json.dumps({"demo_id": demo_id, "result": build_plan(task, registry)}, ensure_ascii=False, indent=2)
    raise ValueError(f"unsupported demo id: {demo_id}")
