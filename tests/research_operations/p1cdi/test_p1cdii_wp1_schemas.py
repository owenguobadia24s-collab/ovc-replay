from __future__ import annotations

import copy
from datetime import datetime
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class ContractValidationError(ValueError):
    pass


def _resolve(root: dict, reference: str) -> dict:
    if not reference.startswith("#/"):
        raise ContractValidationError(f"non-local reference: {reference}")
    node: object = root
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise ContractValidationError(f"unresolved reference: {reference}")
        node = node[part]
    if not isinstance(node, dict):
        raise ContractValidationError(f"reference is not a schema: {reference}")
    return node


def _matches(schema: dict, instance: object, root: dict) -> bool:
    try:
        validate_contract(schema, instance, root)
    except ContractValidationError:
        return False
    return True


def validate_contract(schema: dict, instance: object, root: dict | None = None) -> None:
    """Validate the closed WP1 schema vocabulary without a third-party dependency."""
    root = root or schema
    if "$ref" in schema:
        validate_contract(_resolve(root, schema["$ref"]), instance, root)
    for subschema in schema.get("allOf", []):
        validate_contract(subschema, instance, root)
    if "oneOf" in schema:
        matches = sum(_matches(subschema, instance, root) for subschema in schema["oneOf"])
        if matches != 1:
            raise ContractValidationError(f"oneOf matched {matches} branches")
    if "not" in schema and _matches(schema["not"], instance, root):
        raise ContractValidationError("not schema matched")
    if "if" in schema and _matches(schema["if"], instance, root) and "then" in schema:
        validate_contract(schema["then"], instance, root)
    if "const" in schema and instance != schema["const"]:
        raise ContractValidationError("const mismatch")
    if "enum" in schema and instance not in schema["enum"]:
        raise ContractValidationError("enum mismatch")

    expected = schema.get("type")
    if expected is not None:
        allowed = [expected] if isinstance(expected, str) else expected
        type_checks = {
            "object": lambda value: isinstance(value, dict),
            "array": lambda value: isinstance(value, list),
            "string": lambda value: isinstance(value, str),
            "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
            "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": lambda value: isinstance(value, bool),
            "null": lambda value: value is None,
        }
        if not any(type_checks[kind](instance) for kind in allowed):
            raise ContractValidationError(f"type mismatch: expected {allowed}")

    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        missing = set(schema.get("required", [])) - set(instance)
        if missing:
            raise ContractValidationError(f"missing properties: {sorted(missing)}")
        for name, value in instance.items():
            if name in properties:
                validate_contract(properties[name], value, root)
            elif schema.get("additionalProperties") is False:
                raise ContractValidationError(f"unexpected property: {name}")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate_contract(schema["additionalProperties"], value, root)

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise ContractValidationError("minItems mismatch")
        if schema.get("uniqueItems"):
            canonical = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in instance]
            if len(canonical) != len(set(canonical)):
                raise ContractValidationError("uniqueItems mismatch")
        if isinstance(schema.get("items"), dict):
            for value in instance:
                validate_contract(schema["items"], value, root)

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise ContractValidationError("minLength mismatch")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise ContractValidationError("pattern mismatch")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(instance.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ContractValidationError("date-time mismatch") from exc

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise ContractValidationError("minimum mismatch")


def assert_local_references_resolve(node: object, root: dict) -> None:
    if isinstance(node, dict):
        if "$ref" in node:
            _resolve(root, node["$ref"])
        for value in node.values():
            assert_local_references_resolve(value, root)
    elif isinstance(node, list):
        for value in node:
            assert_local_references_resolve(value, root)


class P1CDIIWP1SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pack = load_json("fixtures/research_operations/p1cdi/P1CDII_WP1_REFERENCE_OBJECTS_v0_1.json")
        cls.examples = pack["examples"]

    def test_all_wp1_schemas_declare_draft_2020_12_and_resolve_references(self) -> None:
        schema_dir = ROOT / "schemas/research_operations/p1cdi"
        schemas = sorted(schema_dir.glob("*.schema.json"))
        self.assertEqual(len(schemas), 13)
        for path in schemas:
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIsInstance(schema.get("oneOf", schema.get("type")), (list, str))
            assert_local_references_resolve(schema, schema)

    def test_reference_object_for_each_object_family_validates(self) -> None:
        self.assertEqual(len(self.examples), 10)
        for example in self.examples:
            schema = load_json(example["schema_path"])
            validate_contract(schema, example["record"])

    def test_programme_state_validates(self) -> None:
        schema = load_json("schemas/research_operations/p1cdi/p1cdii_programme_state_v0_1.schema.json")
        state = load_json("records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json")
        validate_contract(schema, state)

    def _example(self, record_type: str) -> tuple[dict, dict]:
        example = next(item for item in self.examples if item["record"]["record_type"] == record_type)
        return load_json(example["schema_path"]), copy.deepcopy(example["record"])

    def assert_invalid(self, schema: dict, record: dict) -> None:
        with self.assertRaises(ContractValidationError):
            validate_contract(schema, record)

    def test_non_exact_correspondence_cannot_auto_admit(self) -> None:
        schema, record = self._example("P1DistinctionCorrespondenceRecord")
        record["semantic_relation"] = "REFINES"
        record["executability"] = "AUTO_ADMITTED"
        self.assert_invalid(schema, record)

    def test_candidate_writes_and_recommendation_actuation_are_denied(self) -> None:
        schema, record = self._example("P1ProposalReadinessAssessment")
        record["candidate_write"] = "ALLOWED"
        self.assert_invalid(schema, record)

        schema, record = self._example("P1DiscoveryWorkRecommendation")
        record["actuation"] = "ALLOWED"
        self.assert_invalid(schema, record)

    def test_currentness_is_not_decision_bearing_before_g2_alg(self) -> None:
        schema, record = self._example("CurrentnessResolutionRecord")
        record["decision_bearing"] = True
        self.assert_invalid(schema, record)

    def test_visibility_and_validation_are_fail_closed(self) -> None:
        schema, record = self._example("P1CDIVisibilityDecision")
        record["classified_before_indexing"] = False
        self.assert_invalid(schema, record)
        record["classified_before_indexing"] = True
        record["validation_access"] = "ALLOWED"
        self.assert_invalid(schema, record)

    def test_projection_profile_and_unknown_fields_are_rejected(self) -> None:
        schema, record = self._example("P1DistinctionSemanticProjection")
        record["profile_id"] = "P1CDI-SEMANTIC-PROJECTION-v2"
        self.assert_invalid(schema, record)
        record["profile_id"] = "P1CDI-SEMANTIC-PROJECTION-v1"
        record["unapproved_field"] = "forbidden"
        self.assert_invalid(schema, record)


if __name__ == "__main__":
    unittest.main()
