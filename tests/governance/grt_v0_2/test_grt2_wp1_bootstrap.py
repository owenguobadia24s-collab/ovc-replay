from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import (
    DIALECT,
    BootstrapValidationError,
    load_json,
    validate_instance,
    validate_manifest_dag,
    validate_registry_unique,
    validate_schema,
)
from ovc.programme_genesis.grt_v0_2.serialization import (
    CanonicalJSONError,
    canonical_json_v1_bytes,
    canonical_sha256,
)


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "schemas/governance/grt_v0_2"
REGISTRIES = ROOT / "registries/governance/grt_v0_2"
FIXTURES = ROOT / "fixtures/governance/grt_v0_2/wp1"


class GRT2WP1BootstrapTests(unittest.TestCase):
    def test_all_declared_schemas_use_supported_dialect_and_profile(self) -> None:
        manifest = load_json(REGISTRIES / "GRT_BOOTSTRAP_VALIDATION_MANIFEST_v0_1.json")
        self.assertEqual(manifest["schema_dialect"], DIALECT)
        self.assertEqual(manifest["profile_id"], "ovc-grt-bootstrap-subset-v1")
        self.assertEqual(len(manifest["schemas"]), 13)
        for entry in manifest["schemas"]:
            schema = load_json(ROOT / entry["path"])
            validate_schema(schema)
            self.assertEqual(schema["$schema"], DIALECT)
        order = validate_manifest_dag(manifest)
        self.assertEqual(set(order), {entry["schema_id"] for entry in manifest["schemas"]})

    def test_valid_root_and_malformed_root(self) -> None:
        schema = load_json(SCHEMAS / "repository_root_record.schema.json")
        validate_instance(load_json(FIXTURES / "valid_root_record.json"), schema)
        with self.assertRaisesRegex(BootstrapValidationError, "INSTANCE_REQUIRED"):
            validate_instance(
                load_json(FIXTURES / "invalid_root_record_missing_path.json"),
                schema,
            )

    def test_unknown_dialect_and_keyword_fail_closed(self) -> None:
        with self.assertRaisesRegex(BootstrapValidationError, "DIALECT_UNSUPPORTED"):
            validate_schema(load_json(FIXTURES / "invalid_unknown_dialect.schema.json"))
        with self.assertRaisesRegex(BootstrapValidationError, "UNKNOWN_KEYWORD"):
            validate_schema(load_json(FIXTURES / "invalid_unknown_keyword.schema.json"))

    def test_in_memory_self_reference_and_manifest_cycle_fail_closed(self) -> None:
        recursive: dict[str, object] = {
            "$schema": DIALECT,
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
        recursive["properties"] = {"self": recursive}
        with self.assertRaisesRegex(BootstrapValidationError, "SELF_REFERENCE"):
            validate_schema(recursive)
        with self.assertRaisesRegex(BootstrapValidationError, "MANIFEST_CYCLE"):
            validate_manifest_dag(
                load_json(FIXTURES / "invalid_cyclic_bootstrap_manifest.json")
            )

    def test_duplicate_registry_identity_fails_closed(self) -> None:
        registry = load_json(FIXTURES / "invalid_duplicate_root_registry.json")
        with self.assertRaisesRegex(BootstrapValidationError, "DUPLICATE_ID"):
            validate_registry_unique(
                registry,
                collection_field="roots",
                identity_field="root_id",
            )

    def test_canonical_json_is_order_stable_and_strict(self) -> None:
        left = {"b": [2, 1], "a": {"z": "é", "n": 1.0}}
        right = {"a": {"n": 1, "z": "é"}, "b": [2, 1]}
        self.assertEqual(canonical_json_v1_bytes(left), canonical_json_v1_bytes(right))
        self.assertEqual(canonical_sha256(left), canonical_sha256(right))
        with self.assertRaisesRegex(CanonicalJSONError, "NEGATIVE_ZERO"):
            canonical_json_v1_bytes({"value": -0.0})
        with self.assertRaisesRegex(CanonicalJSONError, "NONFINITE"):
            canonical_json_v1_bytes({"value": math.inf})
        with self.assertRaisesRegex(CanonicalJSONError, "OBJECT_KEY_NOT_STRING"):
            canonical_json_v1_bytes({1: "forbidden"})

    def test_registry_roundtrip_preserves_canonical_hash(self) -> None:
        registry = load_json(REGISTRIES / "GRT_ARTIFACT_CLASS_REGISTRY_v0_2.json")
        payload = {key: value for key, value in registry.items() if key != "registry_hash"}
        self.assertEqual(registry["registry_hash"], canonical_sha256(payload))
        reloaded = json.loads(canonical_json_v1_bytes(registry))
        self.assertEqual(registry, reloaded)


if __name__ == "__main__":
    unittest.main()
