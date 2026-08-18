from __future__ import annotations

import unittest

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_predecessor import (
    OpenVitPlacement,
    resolve_vit_train_predecessor,
)
from ovc.development.skills.vit_routing import build_vit_lineage_record


AUTHORITY = "a" * 64
FRONTIER = "b" * 64


def _lineage(
    *,
    packet: str,
    train: str,
    ordinal: int,
    predecessor_tree: str,
    result_tree: str,
):
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "TEST-PROGRAMME",
        "packet_id": packet,
        "logical_changes": [
            {
                "op": "ADD",
                "path": f"fixtures/{packet}.json",
                "blob_sha": "c" * 40,
                "mode": "100644",
            }
        ],
        "authority_manifest_id": AUTHORITY,
        "dependency_frontier_id": FRONTIER,
        "completion_transition": {"status": "COMPLETED"},
    }
    return build_vit_lineage_record(
        programme_id="TEST-PROGRAMME",
        packet_id=packet,
        pip_identity_payload=pip,
        train_generation_id=train,
        ordinal=ordinal,
        predecessor_tree_sha=predecessor_tree,
        result_tree_sha=result_tree,
        apply_profile="INTEGRATION_APPLY_PROFILE_REFERENCE_v0_1",
    )


class VitPredecessorResolutionTests(unittest.TestCase):
    def test_unrelated_earlier_ready_pr_cannot_hold_lease_when_predecessor_is_physical(self) -> None:
        physical = "1" * 40
        current = _lineage(
            packet="CURRENT",
            train="CURRENT-TRAIN",
            ordinal=5,
            predecessor_tree=physical,
            result_tree="2" * 40,
        )
        unrelated_earlier = OpenVitPlacement(
            pr_number=7,
            head_sha="3" * 40,
            lineage_record=_lineage(
                packet="UNRELATED",
                train="OTHER-TRAIN",
                ordinal=0,
                predecessor_tree=physical,
                result_tree="4" * 40,
            ),
        )

        predecessor = resolve_vit_train_predecessor(
            current_lineage_record=current,
            current_main_tree=physical,
            open_placements=(unrelated_earlier,),
        )

        self.assertIsNone(predecessor)

    def test_actual_vit_predecessor_can_have_higher_pr_number(self) -> None:
        expected = "5" * 40
        current = _lineage(
            packet="CURRENT",
            train="SHARED-TRAIN",
            ordinal=2,
            predecessor_tree=expected,
            result_tree="6" * 40,
        )
        actual = OpenVitPlacement(
            pr_number=900,
            head_sha="7" * 40,
            lineage_record=_lineage(
                packet="ACTUAL",
                train="SHARED-TRAIN",
                ordinal=1,
                predecessor_tree="8" * 40,
                result_tree=expected,
            ),
        )
        unrelated_lower = OpenVitPlacement(
            pr_number=1,
            head_sha="9" * 40,
            lineage_record=_lineage(
                packet="LOWER",
                train="OTHER-TRAIN",
                ordinal=0,
                predecessor_tree="8" * 40,
                result_tree="a" * 40,
            ),
        )

        predecessor = resolve_vit_train_predecessor(
            current_lineage_record=current,
            current_main_tree="0" * 40,
            open_placements=(unrelated_lower, actual),
        )

        self.assertIsNotNone(predecessor)
        assert predecessor is not None
        self.assertEqual(predecessor.pr_number, 900)
        self.assertEqual(predecessor.result_tree, expected)

    def test_cross_train_exact_placement_tree_is_still_real_predecessor(self) -> None:
        expected = "b" * 40
        current = _lineage(
            packet="CURRENT",
            train="CURRENT-PLACEMENT-TRAIN",
            ordinal=3,
            predecessor_tree=expected,
            result_tree="c" * 40,
        )
        predecessor_candidate = OpenVitPlacement(
            pr_number=50,
            head_sha="d" * 40,
            lineage_record=_lineage(
                packet="UPSTREAM",
                train="UPSTREAM-PACKET-TRAIN",
                ordinal=9,
                predecessor_tree="e" * 40,
                result_tree=expected,
            ),
        )

        predecessor = resolve_vit_train_predecessor(
            current_lineage_record=current,
            current_main_tree="f" * 40,
            open_placements=(predecessor_candidate,),
        )

        self.assertIsNotNone(predecessor)
        assert predecessor is not None
        self.assertEqual(predecessor.pr_number, 50)

    def test_missing_exact_vit_predecessor_fails_closed(self) -> None:
        current = _lineage(
            packet="CURRENT",
            train="TRAIN",
            ordinal=1,
            predecessor_tree="1" * 40,
            result_tree="2" * 40,
        )
        unrelated = OpenVitPlacement(
            pr_number=1,
            head_sha="3" * 40,
            lineage_record=_lineage(
                packet="UNRELATED",
                train="TRAIN",
                ordinal=0,
                predecessor_tree="4" * 40,
                result_tree="5" * 40,
            ),
        )

        with self.assertRaisesRegex(
            VitContractError, "VIT_PLACEMENT_PREDECESSOR_NOT_PHYSICAL"
        ):
            resolve_vit_train_predecessor(
                current_lineage_record=current,
                current_main_tree="0" * 40,
                open_placements=(unrelated,),
            )

    def test_ambiguous_exact_tree_predecessor_fails_closed(self) -> None:
        expected = "6" * 40
        current = _lineage(
            packet="CURRENT",
            train="TRAIN",
            ordinal=3,
            predecessor_tree=expected,
            result_tree="7" * 40,
        )
        candidates = tuple(
            OpenVitPlacement(
                pr_number=number,
                head_sha=hex_digit * 40,
                lineage_record=_lineage(
                    packet=f"P{number}",
                    train="TRAIN",
                    ordinal=number,
                    predecessor_tree="8" * 40,
                    result_tree=expected,
                ),
            )
            for number, hex_digit in ((1, "9"), (2, "a"))
        )

        with self.assertRaisesRegex(
            VitContractError, "VIT_TRAIN_PREDECESSOR_AMBIGUOUS"
        ):
            resolve_vit_train_predecessor(
                current_lineage_record=current,
                current_main_tree="0" * 40,
                open_placements=candidates,
            )


if __name__ == "__main__":
    unittest.main()
