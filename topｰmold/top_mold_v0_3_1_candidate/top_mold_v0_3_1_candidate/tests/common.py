import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_json(name):
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))

def valid_intake():
    return read_json("intake.example.json")

def valid_task():
    return read_json("task.example.json")

def valid_registry():
    return read_json("processor_registry.json")
