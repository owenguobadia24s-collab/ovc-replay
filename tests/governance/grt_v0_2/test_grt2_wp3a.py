from __future__ import annotations

import json
import random
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import validate_instance
from ovc.programme_genesis.grt_v0_2.reference import ReferenceRuntimeError, build_reference_graph, classify_observation, observe_component, replay_b0_baseline

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/governance/grt_v0_2/wp3a/reference_graph_fixture.json"
BASE = ROOT / "registries/governance/grt_v0_2/baseline"
SCHEMA = ROOT / "schemas/governance/grt_v0_2/repository_reference_graph.schema.json"


def b0_rows():
    return [json.loads(line) for line in (BASE / "GRT_B0_BASELINE_MEMBERS_v0_1.jsonl").read_text(encoding="utf-8").splitlines() if line]


class GRT2WP3AReferenceTests(unittest.TestCase):
    def fixture(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_reference_graph_is_deterministic_and_schema_valid(self) -> None:
        fixture = self.fixture()
        graph_a = build_reference_graph(**fixture)
        shuffled = list(fixture["components"])
        random.Random(7).shuffle(shuffled)
        graph_b = build_reference_graph(tree_hash=fixture["tree_hash"], components=shuffled, bindings_by_path=fixture["bindings_by_path"])
        self.assertEqual(graph_a, graph_b)
        validate_instance(graph_a, json.loads(SCHEMA.read_text(encoding="utf-8")))
        self.assertEqual(graph_a["resolution_status"], "PARTIAL")
        self.assertEqual(graph_a["active_enforcement"], "NONE")

    def test_path_is_not_artifact_authority_and_filename_is_not_lifecycle(self) -> None:
        first = observe_component(tree_hash="1" * 40, path="docs/a/FINAL_RATIFIED.md", content_hash="a" * 40)
        moved = observe_component(tree_hash="1" * 40, path="docs/b/CURRENT.md", content_hash="a" * 40)
        first_artifact = classify_observation(first)
        moved_artifact = classify_observation(moved)
        self.assertEqual(first_artifact["artifact_id"], moved_artifact["artifact_id"])
        self.assertEqual(first_artifact["lifecycle_class"], "PROPOSED_UNADMITTED")
        self.assertEqual(first_artifact["artifact_status"], "PARTIAL")
        self.assertEqual(first_artifact["binding_status"], "CANDIDATE_RELATION")

    def test_source_explicit_identity_survives_move(self) -> None:
        binding = {"artifact_id": "OVC.X.v1", "artifact_type": "DOCUMENTATION", "lifecycle_class": "CURRENT_SUPPORTING"}
        a = classify_observation(observe_component(tree_hash="1" * 40, path="docs/a.md", content_hash="2" * 40), binding)
        b = classify_observation(observe_component(tree_hash="3" * 40, path="docs/moved/a.md", content_hash="2" * 40), binding)
        self.assertEqual(a["artifact_id"], b["artifact_id"])
        self.assertEqual(a["artifact_status"], "RESOLVED")

    def test_invalid_relationship_and_unclassified_path_fail_closed(self) -> None:
        obs = observe_component(tree_hash="1" * 40, path="src/x.py", content_hash="2" * 40)
        with self.assertRaises(ReferenceRuntimeError):
            classify_observation(obs, {"artifact_type": "IMPLEMENTATION", "lifecycle_class": "CURRENT_IMPLEMENTATION", "relationships": [{"relationship_type": "UNREGISTERED_RELATION", "object_artifact_id": "x"}]})
        unknown = observe_component(tree_hash="1" * 40, path="mystery/x.bin", content_hash="2" * 40)
        with self.assertRaises(ReferenceRuntimeError):
            classify_observation(unknown)

    def test_b0_reference_replay_is_exact_and_non_enforcing(self) -> None:
        receipt = replay_b0_baseline(b0_rows())
        self.assertEqual(receipt["member_count"], 569)
        self.assertEqual(receipt["membership_sha256"], "3587c224c07360751923e5718c5bedb432ce4a5c8cccd4061f73dd53ef07de5d")
        self.assertEqual(receipt["active_enforcement"], "NONE")
        self.assertEqual(receipt["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
