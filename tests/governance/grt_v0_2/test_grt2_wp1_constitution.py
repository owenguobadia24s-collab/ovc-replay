from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.constitution import (
    ARTIFACT_CLASSES,
    CONSTITUTION_ID,
    CONSTITUTION_STATUS,
    LIFECYCLE_CLASSES,
    OBSERVED_ROOTS,
    RELATIONSHIP_TYPES,
    build_registry_bundle,
    validate_committed_bundle,
)
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
REGISTRIES = ROOT / "registries/governance/grt_v0_2"
CONTRACTS = ROOT / "contracts/governance/grt_v0_2"


class GRT2WP1ConstitutionTests(unittest.TestCase):
    def test_committed_constitution_bundle_is_exactly_rebuildable(self) -> None:
        receipt = validate_committed_bundle(ROOT)
        self.assertEqual(receipt["result"], "PASS")
        self.assertEqual(receipt["schema_count"], 13)
        self.assertEqual(receipt["registry_count"], 10)
        self.assertEqual(receipt["authority_effect"], "NONE_PRE_ENFORCEMENT")
        expected = build_registry_bundle(ROOT)
        for name, record in expected.items():
            committed = json.loads((REGISTRIES / name).read_text(encoding="utf-8"))
            self.assertEqual(committed, record)

    def test_constitution_is_inactive_and_operator_gates_are_preserved(self) -> None:
        record = json.loads(
            (REGISTRIES / "GRT_REPOSITORY_CONSTITUTION_v0_2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(record["constitution_id"], CONSTITUTION_ID)
        self.assertEqual(record["status"], CONSTITUTION_STATUS)
        self.assertEqual(record["activation"]["current"], "INACTIVE")
        self.assertEqual(
            record["activation"]["limited_enforcement_gate"],
            "GRT2-G2.5_OPERATOR_REQUIRED",
        )
        self.assertEqual(
            record["activation"]["full_enforcement_gate"],
            "GRT2-G3_OPERATOR_REQUIRED",
        )
        self.assertEqual(record["authority_effect"], "NONE_PRE_ENFORCEMENT")
        self.assertEqual(
            record["canonical_hash"],
            canonical_sha256(
                {
                    "constitution_id": record["constitution_id"],
                    "constitution_version": record["constitution_version"],
                    "core_bindings": record["core_bindings"],
                }
            ),
        )

    def test_exact_root_artifact_lifecycle_relationship_and_rule_sets(self) -> None:
        root_registry = json.loads(
            (REGISTRIES / "GRT_ROOT_REGISTRY_v0_2.json").read_text(encoding="utf-8")
        )
        artifact_registry = json.loads(
            (REGISTRIES / "GRT_ARTIFACT_CLASS_REGISTRY_v0_2.json").read_text(
                encoding="utf-8"
            )
        )
        lifecycle_registry = json.loads(
            (REGISTRIES / "GRT_LIFECYCLE_REGISTRY_v0_2.json").read_text(
                encoding="utf-8"
            )
        )
        relation_registry = json.loads(
            (REGISTRIES / "GRT_RELATIONSHIP_REGISTRY_v0_2.json").read_text(
                encoding="utf-8"
            )
        )
        rules = json.loads(
            (REGISTRIES / "GRT_RULE_BUNDLE_v0_2.json").read_text(encoding="utf-8")
        )
        self.assertEqual(tuple(item["path"] for item in root_registry["roots"]), OBSERVED_ROOTS)
        self.assertTrue(all(item["classification_status"] == "OBSERVED_PENDING_QUALIFICATION" for item in root_registry["roots"]))
        self.assertTrue(all(item["new_write_policy"] == "ADVISORY_ONLY_PRE_G3" for item in root_registry["roots"]))
        self.assertEqual(
            {item["artifact_class_id"] for item in artifact_registry["artifact_classes"]},
            set(ARTIFACT_CLASSES),
        )
        self.assertEqual(
            {item["lifecycle_class_id"] for item in lifecycle_registry["lifecycle_classes"]},
            set(LIFECYCLE_CLASSES),
        )
        self.assertEqual(
            {item["relationship_type"] for item in relation_registry["relationship_types"]},
            set(RELATIONSHIP_TYPES),
        )
        expected_rule_ids = {
            "GRT-R001","GRT-R005","GRT-R100","GRT-R200","GRT-R300",
            "GRT-R421","GRT-R500","GRT-R600","GRT-R700","GRT-R805",
            "GRT-R900","GRT-R954",
        }
        self.assertEqual({item["rule_id"] for item in rules["rules"]}, expected_rule_ids)
        self.assertEqual(len({item["canonical_hash"] for item in rules["rules"]}), 12)
        self.assertEqual(rules["authority_effect"], "NONE_PRE_ENFORCEMENT")

    def test_source_explicit_relationship_and_pgn_boundaries_are_preserved(self) -> None:
        relations = json.loads(
            (REGISTRIES / "GRT_RELATIONSHIP_REGISTRY_v0_2.json").read_text(
                encoding="utf-8"
            )
        )
        by_name = {item["relationship_type"]: item for item in relations["relationship_types"]}
        for name in ("OWNED_BY", "GOVERNED_BY", "CROSSWALKS_TO", "DEPENDS_ON"):
            self.assertEqual(
                by_name[name]["current_governance_evidence_minimum"],
                "SOURCE_EXPLICIT",
            )
        rule_bundle = json.loads(
            (REGISTRIES / "GRT_RULE_BUNDLE_v0_2.json").read_text(encoding="utf-8")
        )
        by_id = {item["rule_id"]: item for item in rule_bundle["rules"]}
        self.assertEqual(
            by_id["GRT-R300"]["remediation_class"],
            "PGN_AUTHORITY_REQUIRED_CURRENT",
        )
        self.assertEqual(
            by_id["GRT-R300"]["historical_policy"],
            "NO_PROVISIONAL_OR_INFERRED_CURRENT_CROSSWALK",
        )

    def test_all_policy_hashes_are_source_bound(self) -> None:
        constitution = json.loads(
            (REGISTRIES / "GRT_REPOSITORY_CONSTITUTION_v0_2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(constitution["policy_hashes"]), 8)
        for name, expected_hash in constitution["policy_hashes"].items():
            import hashlib
            actual = hashlib.sha256((CONTRACTS / name).read_bytes()).hexdigest()
            self.assertEqual(actual, expected_hash)


if __name__ == "__main__":
    unittest.main()
