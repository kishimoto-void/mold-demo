import tempfile
import unittest
from pathlib import Path

from core.errors import RegistryError
from core.registry import load_mold_registry, validate_mold_registry, validate_processor_registry
from tests.common import read_json


class RegistryTests(unittest.TestCase):
    def test_example_mold_registry_is_valid(self):
        registry = read_json("mold_registry.json")
        self.assertEqual(len(validate_mold_registry(registry)), len(registry["molds"]))

    def test_mold_registry_requires_explicit_schema_version(self):
        registry = read_json("mold_registry.json")
        registry["schema_version"] = "9.0"
        with self.assertRaisesRegex(RegistryError, "schema_version 1.0"):
            validate_mold_registry(registry)

    def test_mold_registry_rejects_duplicate_ids_and_missing_metadata(self):
        registry = read_json("mold_registry.json")
        registry["molds"].append(dict(registry["molds"][0]))
        with self.assertRaisesRegex(RegistryError, "duplicate mold id"):
            validate_mold_registry(registry)
        registry = read_json("mold_registry.json")
        del registry["molds"][0]["version"]
        with self.assertRaisesRegex(RegistryError, "version"):
            validate_mold_registry(registry)

    def test_processor_registry_rejects_boolean_priority(self):
        registry = read_json("processor_registry.json")
        registry["processors"][0]["priority"] = True
        with self.assertRaisesRegex(RegistryError, "priority must be an integer"):
            validate_processor_registry(registry)

    def test_mold_registry_loader_reports_invalid_json_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(RegistryError, "cannot load mold registry"):
                load_mold_registry(path)

if __name__ == "__main__":
    unittest.main()
