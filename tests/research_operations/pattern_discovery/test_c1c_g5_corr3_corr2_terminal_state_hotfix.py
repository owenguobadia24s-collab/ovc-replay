from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery import pilot_corr2_review_closure as corr2
from ovc.research_operations.pattern_discovery.corr3_corr2_state_compat import (
    TERMINAL_CORR2_STATUS,
    load_corr2_authority_with_terminal_review,
)


DECISION_PATH = Path(
    "docs/releases/opt-b-c1-v2/corrective/c1c-g5/operator-gate/"
    "C1C_G5_CORRECTIVE_PILOT_REVIEW_OPERATOR_DECISION.json"
)
STATE_PATH = Path(
    "registries/research_operations/pattern_discovery/"
    "PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"
)
BUNDLE_PATH = Path(
    "docs/releases/opt-b-c1-v2/corrective/c1c-g5/operator-gate/"
    "C1C_G5_CORRECTIVE_PILOT_REVIEW_GATE_READY_BUNDLE.json"
)


def write_json(root: Path, relative: Path, value: object) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def materialize_authority(root: Path, *, status: str = TERMINAL_CORR2_STATUS) -> None:
    write_json(
        root,
        DECISION_PATH,
        {
            "gate_id": corr2.RETURN_GATE,
            "decision": "DEFER",
            "authorised_next_packet": {
                "packet_id": corr2.PACKET_ID,
                "machine_replay": "DENIED_NOT_REQUIRED",
            },
        },
    )
    write_json(
        root,
        STATE_PATH,
        {
            "corr2": {
                "packet_id": corr2.PACKET_ID,
                "status": status,
            }
        },
    )
    write_json(
        root,
        BUNDLE_PATH,
        {
            "gate_id": corr2.RETURN_GATE,
            "recommended_decision": {"decision": "DEFER"},
        },
    )


class Corr3Corr2TerminalStateHotfixTests(unittest.TestCase):
    def test_exact_signed_terminal_state_is_accepted_for_corr3(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            materialize_authority(root)
            authority = load_corr2_authority_with_terminal_review(root)

        self.assertEqual(
            authority["state"]["corr2"]["status"],
            TERMINAL_CORR2_STATUS,
        )
        self.assertEqual(
            authority["bundle"]["recommended_decision"]["decision"],
            "DEFER",
        )

    def test_unapproved_terminal_status_still_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            materialize_authority(root, status="COMPLETED_AND_PROMOTED")
            with self.assertRaisesRegex(
                corr2.Corr2ReviewError,
                "CORR2_STATE_NOT_EXECUTABLE:COMPLETED_AND_PROMOTED",
            ):
                load_corr2_authority_with_terminal_review(root)

    def test_replay_boundary_remains_denied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            materialize_authority(root)
            decision = json.loads((root / DECISION_PATH).read_text(encoding="utf-8"))
            decision["authorised_next_packet"]["machine_replay"] = "ALLOWED"
            write_json(root, DECISION_PATH, decision)
            with self.assertRaisesRegex(
                corr2.Corr2ReviewError,
                "CORR2_MACHINE_REPLAY_BOUNDARY_INVALID",
            ):
                load_corr2_authority_with_terminal_review(root)

    def test_gate_recommendation_must_remain_defer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            materialize_authority(root)
            bundle = json.loads((root / BUNDLE_PATH).read_text(encoding="utf-8"))
            bundle["recommended_decision"]["decision"] = "PASS"
            write_json(root, BUNDLE_PATH, bundle)
            with self.assertRaisesRegex(
                corr2.Corr2ReviewError,
                "CORR2_GATE_READY_SOURCE_MISMATCH",
            ):
                load_corr2_authority_with_terminal_review(root)


if __name__ == "__main__":
    unittest.main()
