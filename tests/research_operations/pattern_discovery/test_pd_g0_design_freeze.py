from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTRACT_ROOT = ROOT / "contracts" / "research_operations" / "pattern_discovery"
SCHEMA_ROOT = ROOT / "schemas" / "research_operations" / "pattern_discovery"
REGISTRY_ROOT = ROOT / "registries" / "research_operations" / "pattern_discovery"
PLAN_BINDING = ROOT / "docs" / "implementation-plans" / "OVC_C2_PATTERN_DISCOVERY_AND_REVIEW_LAYER_v0_3_SOURCE_BINDING.md"
GATE_PACKET = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "PD_G0_OPERATOR_GATE_PACKET.md"
DECISION_RECORD = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "PD_G0_OPERATOR_DECISION.md"


class PatternDiscoveryDesignFreezeTests(unittest.TestCase):
    def test_required_artifacts_exist(self) -> None:
        required = [
            PLAN_BINDING,
            CONTRACT_ROOT / "PATTERN_DISCOVERY_AUTHORITY_CONTRACT_v0_3.md",
            CONTRACT_ROOT / "PATTERN_DISCOVERY_SCALE_CONTROLS_AND_BACKPRESSURE_CONTRACT_v0_2.md",
            CONTRACT_ROOT / "PD_CLUSTERING_ALGORITHM_AND_POPULATION_DECISION_v0_2.md",
            CONTRACT_ROOT / "PATTERN_DISCOVERY_NOVELTY_UI_AND_PRICE_STRIP_CONTRACT_v0_1.md",
            CONTRACT_ROOT / "C2_PATTERN_DISCOVERY_EVIDENCE_BRIDGE_AUTHORITY_CONTRACT_v0_2.md",
            CONTRACT_ROOT / "PATTERN_DISCOVERY_FAILURE_MODE_MATRIX_v0_1.md",
            REGISTRY_ROOT / "PATTERN_DISCOVERY_IMPLEMENTATION_REGISTRY_v0_3.yaml",
            REGISTRY_ROOT / "PATTERN_DISCOVERY_TRIGGER_REGISTRY_v0_1.yaml",
            GATE_PACKET,
            DECISION_RECORD,
        ]
        missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
        self.assertEqual([], missing)

    def test_governing_plan_hash_is_pinned(self) -> None:
        text = PLAN_BINDING.read_text(encoding="utf-8")
        self.assertIn("03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa", text)
        self.assertIn("3c0785ddb571a4af6de4bf5756a1dfae7e2d3557", text)

    def test_json_schemas_parse_and_close_objects(self) -> None:
        schemas = sorted(SCHEMA_ROOT.glob("*.schema.json"))
        self.assertGreaterEqual(len(schemas), 4)
        for path in schemas:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("https://json-schema.org/draft/2020-12/schema", data["$schema"])
            self.assertIn("$id", data)
            self.assertIn("title", data)
            serialized = json.dumps(data, sort_keys=True)
            self.assertNotIn('"probability"', serialized)
            self.assertNotIn('"trade_direction"', serialized)
            self.assertNotIn('"mfe"', serialized.lower())
            self.assertNotIn('"mae"', serialized.lower())

    def test_authority_contract_denies_downstream_authority(self) -> None:
        text = (CONTRACT_ROOT / "PATTERN_DISCOVERY_AUTHORITY_CONTRACT_v0_3.md").read_text(encoding="utf-8")
        for denied in [
            "mutate selectors",
            "promote clusters to episodes",
            "probability",
            "exposure",
            "execution authority",
            "self-approve",
        ]:
            self.assertIn(denied, text)

    def test_capacity_and_control_rules_are_frozen(self) -> None:
        text = (CONTRACT_ROOT / "PATTERN_DISCOVERY_SCALE_CONTROLS_AND_BACKPRESSURE_CONTRACT_v0_2.md").read_text(encoding="utf-8")
        expected = [
            "Maximum simultaneously open windows per instrument: 20",
            "Maximum queue promotions per instrument per eligible UTC day: 12",
            "Maximum unresolved review-queue depth per instrument: 50",
            "500 active candidates",
            "MATCHED_CONTROL",
            "POPULATION_CONTROL",
            "SUPPRESSED_*",
        ]
        for value in expected:
            self.assertIn(value, text)

    def test_pam_decision_is_verifiable(self) -> None:
        text = (CONTRACT_ROOT / "PD_CLUSTERING_ALGORITHM_AND_POPULATION_DECISION_v0_2.md").read_text(encoding="utf-8")
        self.assertIn("Partitioning Around Medoids", text)
        self.assertIn("0.25 D_state_path", text)
        self.assertIn("normalized Levenshtein", text)
        self.assertIn("Jaccard", text)
        self.assertIn("UNASSIGNED_SMALL_SAMPLE", text)
        self.assertRegex(text, re.compile(r"lower `k`.*lower total within-cluster distance", re.S))

    def test_novelty_cannot_activate_automatically(self) -> None:
        text = (CONTRACT_ROOT / "PATTERN_DISCOVERY_NOVELTY_UI_AND_PRICE_STRIP_CONTRACT_v0_1.md").read_text(encoding="utf-8")
        self.assertIn("Novelty contributes no ranking weight", text)
        self.assertIn("explicit operator gate", text)
        self.assertIn("60 completed valid candidate windows", text)
        self.assertIn("12 valid controls", text)
        self.assertIn("10 eligible operating days", text)

    def test_evidence_bridge_is_idempotent_and_atomic(self) -> None:
        text = (CONTRACT_ROOT / "C2_PATTERN_DISCOVERY_EVIDENCE_BRIDGE_AUTHORITY_CONTRACT_v0_2.md").read_text(encoding="utf-8")
        for required in [
            "globally unique and idempotent",
            "commit atomically",
            "every 30 seconds for up to 5 minutes",
            "Streamlit does not receive",
            "Audit chain",
        ]:
            self.assertIn(required.lower(), text.lower())

    def test_trigger_events_are_preserved_and_precedence_is_display_only(self) -> None:
        failure_text = (CONTRACT_ROOT / "PATTERN_DISCOVERY_FAILURE_MODE_MATRIX_v0_1.md").read_text(encoding="utf-8")
        scale_text = (CONTRACT_ROOT / "PATTERN_DISCOVERY_SCALE_CONTROLS_AND_BACKPRESSURE_CONTRACT_v0_2.md").read_text(encoding="utf-8")
        self.assertIn("All TriggerEvents remain preserved", failure_text)
        self.assertIn("Persist every TriggerEvent", scale_text)
        self.assertIn("queue presentation and closure-profile choice only", failure_text)

    def test_operator_approval_retains_design_boundary_as_programme_advances(self) -> None:
        registry = (REGISTRY_ROOT / "PATTERN_DISCOVERY_IMPLEMENTATION_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        decision = DECISION_RECORD.read_text(encoding="utf-8")
        self.assertIn("status: APPROVED", registry)
        self.assertIn("packet_id: PD-00", registry)
        self.assertIn("status: COMPLETED", registry)
        self.assertRegex(registry, re.compile(r"packet_id: PD-WP1\s+status: COMPLETED", re.S))
        self.assertIn("ACTIVE_NOVELTY_RANKING", registry)
        self.assertIn("EVIDENCE_BRIDGE_WRITE", registry)
        self.assertIn("PROBABILITY", registry)
        self.assertIn("OVC APPROVE PD-G0", decision)
        self.assertIn("Merge into `main` is not granted", decision)


if __name__ == "__main__":
    unittest.main()
