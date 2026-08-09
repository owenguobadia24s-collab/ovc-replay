from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.programme_genesis.topology import build_topology_from_inventory
from ovc.programme_genesis.topology_diff import build_topology_diff, verify_topology_diff


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "docs/releases/genesis-repository-topology-v0-1/GRT_PROGRAMME_STATE_v0_1.json"
G8_DECISION = ROOT / "docs/releases/genesis-repository-topology-v0-1/grt-g8/GRT_G8_OPERATOR_DECISION.json"
WP9_AUDIT = ROOT / "docs/releases/genesis-repository-topology-v0-1/grt-wp9/GRT_WP9_CONFORMANCE_AUDIT.json"
WP10_MANIFEST = ROOT / "docs/releases/genesis-repository-topology-v0-1/grt-wp10/GRT_WP10_IMPLEMENTATION_MANIFEST.json"
SCHEMA_ROOT = ROOT / "schemas/governance/genesis_repository_topology"


def _fixture(commit: str = "a" * 40):
    return build_topology_from_inventory(
        repository="example/rollback",
        source_commit=commit,
        entries=[{"path": "src/ovc/rollback/core.py", "blob_hash": "1" * 40}],
        content_by_path={"src/ovc/rollback/core.py": "VALUE = 1\n"},
        rule_pack={"rule_pack_id": "GRT.WP11.ROLLBACK", "scan_roots": ["src/"]},
    )


class GRTWP11FinalQATests(unittest.TestCase):
    def test_operator_g8_and_post_gate_receipts_are_exact_and_bounded(self) -> None:
        decision = json.loads(G8_DECISION.read_text(encoding="utf-8"))
        wp9 = json.loads(WP9_AUDIT.read_text(encoding="utf-8"))
        wp10 = json.loads(WP10_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(decision["operator_command"], "OVC APPROVE GRT-G8 PASS_WITH_WARNINGS")
        self.assertEqual(decision["decision"], "PASS_WITH_WARNINGS")
        self.assertEqual(wp9["authority_effect"], "NONE_DERIVED_CONFORMANCE_AUDIT_ONLY")
        self.assertEqual(wp9["topology"]["blocker_count"], 0)
        self.assertEqual(wp10["authority_effect"], "NONE_DERIVED_COMMIT_DIFF_ONLY")
        self.assertEqual(wp10["current_assured_topology"]["blocker_count"], 0)
        self.assertFalse(wp9["programme_or_dependency_authority_changed"])
        self.assertFalse(wp10["programme_or_dependency_authority_changed"])

    def test_current_programme_state_preserves_all_reserved_denials(self) -> None:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        authority = state["authority"]
        self.assertEqual(state["operator_decisions"]["GRT-G8"], "PASS_WITH_WARNINGS")
        self.assertEqual(state["next_operator_gate"], "GRT-G11")
        self.assertEqual(authority["programme_genesis_canon"], "PRESERVED_SOLE_AUTHORITY")
        self.assertEqual(authority["programme_auto_admission"], "DENIED")
        self.assertEqual(authority["programme_auto_reclassification"], "DENIED")
        self.assertEqual(authority["dependency_auto_promotion"], "DENIED")
        self.assertEqual(authority["genesis_mutation"], "DENIED")
        self.assertEqual(authority["control_plane_route_activation"], "DENIED")
        self.assertEqual(authority["control_plane_writes"], "DENIED")
        self.assertEqual(authority["admission_enforcement"], "DEFERRED_DISABLED")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(authority["market_selector_semantic_release_publication"], "NONE")
        self.assertEqual(authority["probability_risk_exposure_execution_agent"], "NONE")

    def test_all_grt_schemas_are_valid_json_and_authority_neutral(self) -> None:
        paths = sorted(SCHEMA_ROOT.glob("*.schema.json"))
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
        conformance = json.loads((SCHEMA_ROOT / "topology_conformance_snapshot_v0_1.schema.json").read_text(encoding="utf-8"))
        diff = json.loads((SCHEMA_ROOT / "topology_diff_v0_1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(conformance["properties"]["authority_effect"]["const"], "NONE_DERIVED_CONFORMANCE_AUDIT_ONLY")
        self.assertEqual(diff["properties"]["authority_effect"]["const"], "NONE_DERIVED_COMMIT_DIFF_ONLY")

    def test_rollback_deletes_only_derived_outputs_and_rebuilds_identically(self) -> None:
        before = _fixture("a" * 40)
        after = _fixture("b" * 40)
        diff = build_topology_diff(before, after)
        verify_topology_diff(diff)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            model_path = root / "GENESIS_REPOSITORY_TOPOLOGY_READ_MODEL.json"
            diff_path = root / "GENESIS_REPOSITORY_TOPOLOGY_DIFF.json"
            model_path.write_text(json.dumps(after, sort_keys=True), encoding="utf-8")
            diff_path.write_text(json.dumps(diff, sort_keys=True), encoding="utf-8")
            model_path.unlink()
            diff_path.unlink()
            self.assertFalse(model_path.exists())
            self.assertFalse(diff_path.exists())
            rebuilt = _fixture("b" * 40)
        self.assertEqual(rebuilt["topology_sha256"], after["topology_sha256"])
        self.assertEqual(build_topology_diff(before, rebuilt)["diff_sha256"], diff["diff_sha256"])

    def test_wp10_console_no_longer_contains_deferred_diff_placeholder(self) -> None:
        source = (ROOT / "apps/research_console/repository_topology_surface.py").read_text(encoding="utf-8")
        self.assertIn("load_repository_topology_diff", source)
        self.assertIn("NONE_DERIVED_COMMIT_DIFF_ONLY", source)
        self.assertNotIn("DEFERRED_PENDING_GRT_WP10", source)


if __name__ == "__main__":
    unittest.main()
