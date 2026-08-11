from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from ovc.development.identity import canonical_json_bytes, canonical_sha256
from ovc.development.skills.enums import SkillAvailability, SkillExecutionStatus, SkillMaturity
from ovc.development.skills.registry import CORE_SCHEMAS, REGISTRY_FILES, RegistryValidationError, load_and_validate_registries, validate_core_object, validate_registry_bundle
from ovc.development.skills.registry_cli import main as registry_cli_main


ROOT = Path(__file__).resolve().parents[2]


def load_bundle() -> dict:
    root = ROOT / "registries/development/skills"
    return {name: json.loads((root / filename).read_text(encoding="utf-8")) for name, (filename, _) in REGISTRY_FILES.items()}


class DSAIWP1RegistryTests(unittest.TestCase):
    def test_seed_registries_validate_and_are_non_authoritative(self) -> None:
        result = load_and_validate_registries(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["registry_hashes"]), 5)
        self.assertEqual(registry_cli_main(["validate", "--root", str(ROOT)]), 0)

    def test_golden_core_objects_validate(self) -> None:
        fixture = json.loads((ROOT / "fixtures/development_skills/wp1_golden_core_objects_v0_1.json").read_text(encoding="utf-8"))
        self.assertEqual(set(fixture), set(CORE_SCHEMAS))
        for object_type, value in fixture.items():
            digest = validate_core_object(ROOT, object_type, value)
            self.assertEqual(len(digest), 64)

    def test_duplicate_logical_ids_fail_closed(self) -> None:
        bundle = load_bundle()
        duplicate = copy.deepcopy(bundle["skills"]["entries"][0])
        duplicate["skill_id"] = "OVC-SKILL-999"
        bundle["skills"]["entries"].append(duplicate)
        with self.assertRaisesRegex(RegistryValidationError, "duplicate logical_name"):
            validate_registry_bundle(ROOT, bundle)

    def test_unknown_mandatory_capability_fails_closed(self) -> None:
        bundle = load_bundle()
        bundle["skills"]["entries"][0]["required_capability_ids"].append("UNKNOWN_CAPABILITY")
        with self.assertRaisesRegex(RegistryValidationError, "unknown mandatory capabilities"):
            validate_registry_bundle(ROOT, bundle)

    def test_unknown_execution_tool_fails_closed(self) -> None:
        bundle = load_bundle()
        bundle["execution_profiles"]["entries"][0]["tool_ids"].append("unknown-tool")
        with self.assertRaisesRegex(RegistryValidationError, "unknown tools"):
            validate_registry_bundle(ROOT, bundle)

    def test_registry_projection_cannot_grant_authority(self) -> None:
        bundle = load_bundle()
        bundle["permissions"]["authority_effect"] = "ACTIVATE"
        with self.assertRaises(RegistryValidationError):
            validate_registry_bundle(ROOT, bundle)

    def test_canonical_round_trip_and_role_hash(self) -> None:
        bundle = load_bundle()
        raw = canonical_json_bytes(bundle)
        recovered = json.loads(raw.decode("utf-8"))
        self.assertEqual(raw, canonical_json_bytes(recovered))
        self.assertEqual(canonical_sha256(bundle, role="DSAI_REGISTRY_BUNDLE_TEST"), canonical_sha256(recovered, role="DSAI_REGISTRY_BUNDLE_TEST"))

    def test_source_precedence_and_reuse_are_explicit(self) -> None:
        contract = (ROOT / "contracts/development/skills/OVC_DEVELOPMENT_SKILLS_CORE_OBJECT_CONTRACT_v0_1.md").read_text(encoding="utf-8")
        self.assertIn("OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED", contract)
        self.assertIn("OVC-DSAI-IMPLEMENTATION-PLAN-0.2", contract)
        self.assertIn("OVC_SHARED_DEVELOPMENT_SERVICES_CONTRACT_v0_1.md", contract)
        self.assertIn("Missing authority is never inferred", contract)

    def test_vocabularies_remain_orthogonal(self) -> None:
        self.assertEqual({row.value for row in SkillMaturity}, {"EXPERIMENTAL","QUALIFIED","TRUSTED"})
        self.assertIn("REVOKED", {row.value for row in SkillAvailability})
        self.assertIn("NOT_EVALUABLE", {row.value for row in SkillExecutionStatus})

    def test_wp1_schemas_are_closed_top_level_draft_2020(self) -> None:
        for path in sorted((ROOT / "schemas/development/skills").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["type"], "object")
            self.assertFalse(schema["additionalProperties"], path)


if __name__ == "__main__":
    unittest.main()
