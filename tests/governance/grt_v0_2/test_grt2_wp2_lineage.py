from __future__ import annotations

import unittest

from ovc.programme_genesis.grt_v0_2.protocols import finding_id, make_finding, make_lineage


class GRT2WP2LineageTests(unittest.TestCase):
    def test_logical_identity_ignores_path_message_and_evidence_order(self) -> None:
        identity = finding_id("GRT-R201", "ARTIFACT:implementation:alpha", "OWNED_BY")
        first = make_finding(
            rule_id="GRT-R201",
            subject_artifact_id="ARTIFACT:implementation:alpha",
            relation_role="OWNED_BY",
            debt_extent={"missing_owner": 1},
            first_seen_tree="a" * 40,
            applicability_evidence=["path:z", "path:a"],
            violation_evidence=["message:one"],
        )
        second = make_finding(
            rule_id="GRT-R201",
            subject_artifact_id="ARTIFACT:implementation:alpha",
            relation_role="OWNED_BY",
            debt_extent={"missing_owner": 1},
            first_seen_tree="a" * 40,
            applicability_evidence=["path:a", "path:z"],
            violation_evidence=["message:two"],
        )
        self.assertEqual(identity, first["finding_id"])
        self.assertEqual(first["finding_id"], second["finding_id"])
        self.assertNotEqual(identity, finding_id("GRT-R201", "ARTIFACT:implementation:beta", "OWNED_BY"))

    def test_move_lineage_preserves_logical_finding_identity(self) -> None:
        fid = finding_id("GRT-R001", "ARTIFACT:doc:one", "PLACEMENT")
        first = make_lineage([fid], [fid], "MOVE", ["tree:z", "tree:a"])
        second = make_lineage([fid], [fid], "MOVE", ["tree:a", "tree:z"])
        self.assertEqual(first, second)
        self.assertEqual(first["authority_effect"], "NONE_LINEAGE_ONLY")
        self.assertEqual(first["predecessor_finding_ids"], first["successor_finding_ids"])


if __name__ == "__main__":
    unittest.main()
