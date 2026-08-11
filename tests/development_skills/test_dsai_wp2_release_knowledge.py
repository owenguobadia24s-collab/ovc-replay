from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from ovc.development.skills.environment import EnvironmentManifestError, build_execution_environment_manifest
from ovc.development.skills.knowledge import KnowledgePackError, build_dependency_graph, compile_knowledge_pack, propagate_knowledge_staleness
from ovc.development.skills.release import build_skill_release_bundle, resolve_field_classification
from ovc.development.skills.resolution import build_resolution_records, build_skill_read_model
from ovc.development.skills.registry import validate_against_schema


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "schemas/development/skills"


def schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


class DSAIWP2ReleaseKnowledgeTests(unittest.TestCase):
    def test_normative_hash_is_stable_and_descriptive_change_is_exempt_only_when_explicit(self) -> None:
        fields = {"procedure":"freeze","permission":"read-only","description":"first wording"}
        classes = {"procedure":"NORMATIVE","permission":"NORMATIVE","description":"DESCRIPTIVE"}
        a = build_skill_release_bundle(skill_id="OVC-SKILL-001", logical_name="ovc-preflight", semantic_version="0.1.0", fields=fields, field_classification=classes, source_refs=["design"])
        changed_description = dict(fields, description="second wording")
        b = build_skill_release_bundle(skill_id="OVC-SKILL-001", logical_name="ovc-preflight", semantic_version="0.1.0", fields=changed_description, field_classification=classes, source_refs=["design"])
        self.assertEqual(a["release_id"], b["release_id"])
        changed_normative = dict(fields, procedure="different")
        c = build_skill_release_bundle(skill_id="OVC-SKILL-001", logical_name="ovc-preflight", semantic_version="0.1.0", fields=changed_normative, field_classification=classes, source_refs=["design"])
        self.assertNotEqual(a["release_id"], c["release_id"])
        validate_against_schema(a, schema("skill_release_bundle_v0_1.schema.json"))

    def test_unclassified_or_unknown_classification_defaults_normative(self) -> None:
        fields = {"procedure":"x","ambiguous":"y"}
        self.assertEqual(resolve_field_classification(fields, {"procedure":"DESCRIPTIVE","ambiguous":"MIXED"})["ambiguous"], "NORMATIVE")
        a = build_skill_release_bundle(skill_id="OVC-SKILL-001", logical_name="ovc-preflight", semantic_version="0.1.0", fields=fields, field_classification={"procedure":"DESCRIPTIVE"}, source_refs=["design"])
        b = build_skill_release_bundle(skill_id="OVC-SKILL-001", logical_name="ovc-preflight", semantic_version="0.1.0", fields=dict(fields, ambiguous="z"), field_classification={"procedure":"DESCRIPTIVE"}, source_refs=["design"])
        self.assertNotEqual(a["release_id"], b["release_id"])

    def test_knowledge_pack_dual_hash_and_missing_source_fail_closed(self) -> None:
        fixture = json.loads((ROOT / "fixtures/development_skills/wp2_knowledge_sources_v0_1.json").read_text(encoding="utf-8"))
        manifest = compile_knowledge_pack(knowledge_pack_id="KP-GOV-001", source_requirements=fixture["requirements"], source_records=fixture["records"], compiled_content={"rules":["a","b"]})
        validate_against_schema(manifest, schema("knowledge_pack_manifest_v0_1.schema.json"))
        self.assertEqual(len(manifest["source_set_hash"]), 64)
        self.assertEqual(len(manifest["compiled_pack_hash"]), 64)
        missing = copy.deepcopy(fixture["records"]); missing.pop("DSA-DESIGN")
        with self.assertRaisesRegex(KnowledgePackError, "missing source record"):
            compile_knowledge_pack(knowledge_pack_id="KP-GOV-001", source_requirements=fixture["requirements"], source_records=missing, compiled_content={})

    def test_fragment_drift_selective_and_ambiguous_fallback_whole_pack(self) -> None:
        graph = build_dependency_graph(knowledge_pack_id="KP-GOV-001", edges=[
            {"source_artifact_id":"DSA-DESIGN","fragment_selector":"section:3.3","fragment_hash":"1"*64,"dependent_capability_id":"PACKET_PREFLIGHT","dependent_release_id":"R1"},
            {"source_artifact_id":"DSA-DESIGN","fragment_selector":"section:10","fragment_hash":"2"*64,"dependent_capability_id":"AUTHORITY_RESOLUTION","dependent_release_id":"R2"},
        ])
        current = {"DSA-DESIGN":{"fragments":{"section:3.3":"9"*64,"section:10":"2"*64},"selectors_valid":True}}
        selective = propagate_knowledge_staleness(graph=graph, current_source_records=current)
        self.assertFalse(selective["whole_pack_stale"])
        self.assertEqual(selective["stale_release_ids"], ["R1"])
        ambiguous = {"DSA-DESIGN":{"fragments":current["DSA-DESIGN"]["fragments"],"selectors_valid":False}}
        whole = propagate_knowledge_staleness(graph=graph, current_source_records=ambiguous)
        self.assertTrue(whole["whole_pack_stale"])
        self.assertEqual(whole["stale_release_ids"], ["R1","R2"])
        validate_against_schema(graph, schema("knowledge_dependency_graph_v0_1.schema.json"))

    def test_environment_reproducibility_is_explicit_and_windows_fixture_is_deterministic(self) -> None:
        fixture = json.loads((ROOT / "fixtures/development_skills/wp2_windows_environment_v0_1.json").read_text(encoding="utf-8"))
        a = build_execution_environment_manifest(**fixture)
        b = build_execution_environment_manifest(**fixture)
        self.assertEqual(a, b)
        validate_against_schema(a, schema("execution_environment_manifest_v0_1.schema.json"))
        bad = dict(fixture, reproducibility_class="INFER")
        with self.assertRaises(EnvironmentManifestError):
            build_execution_environment_manifest(**bad)

    def test_read_model_and_resolution_records_rebuild_deterministically(self) -> None:
        release = build_skill_release_bundle(skill_id="OVC-SKILL-001", logical_name="ovc-preflight", semantic_version="0.1.0", fields={"procedure":"x"}, field_classification={}, source_refs=["design"])
        env_fixture = json.loads((ROOT / "fixtures/development_skills/wp2_windows_environment_v0_1.json").read_text(encoding="utf-8"))
        env = build_execution_environment_manifest(**env_fixture)
        inputs = dict(capabilities=[{"capability_id":"PACKET_PREFLIGHT"}], skills=[{"skill_id":"OVC-SKILL-001"}], releases=[release], knowledge_packs=[], environments=[env])
        a = build_skill_read_model(**inputs); b = build_skill_read_model(**inputs)
        self.assertEqual(a["read_model_id"], b["read_model_id"])
        manifest, receipt, packet = build_resolution_records(packet_id="P1", environment_id=env["environment_id"], required_capability_ids=["PACKET_PREFLIGHT"], candidate_release_ids=[release["release_id"]], resolved_release_ids=[], reason_codes=["NO_QUALIFIED_RELEASE"], knowledge_pack_ids=[])
        self.assertEqual(receipt["status"], "NOT_RESOLVED")
        validate_against_schema(manifest, schema("skill_resolution_manifest_v0_1.schema.json"))
        validate_against_schema(receipt, schema("skill_resolution_receipt_v0_1.schema.json"))
        validate_against_schema(packet, schema("packet_skill_resolution_v0_1.schema.json"))


if __name__ == "__main__":
    unittest.main()
