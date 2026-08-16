from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_live_pilot import (
    LivePilotAuthority,
    LivePilotMaterialisationReceipt,
    LivePilotPacketAdmission,
    admit_live_pilot_packet,
    evaluate_q6_receipts,
)

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "registries/authority/DSAI3V_VIT_PILOT_AUTHORITY_v0_1.json"
PIP = "d" * 64
GEN = "e" * 64
PLACEMENT = "f" * 64


def admitted_packet(packet_id: str = "Q6-LANE-A") -> LivePilotPacketAdmission:
    return LivePilotPacketAdmission(
        packet_id,
        "LOW_RISK_IMPLEMENTATION",
        "AUTO_EXECUTABLE",
        "NONE",
        True,
        True,
        pip_id=PIP,
        vit_generation_id=GEN,
        vit_placement_id=PLACEMENT,
    )


class DsaiVitV03Wp10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        record = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        cls.authority = LivePilotAuthority.from_record(record)

    def test_exact_pilot_authority_is_narrow_and_serial(self) -> None:
        self.authority.validate()
        self.assertEqual(self.authority.allowed_packet_classes, ("LOW_RISK_IMPLEMENTATION",))
        self.assertEqual(self.authority.grt_g3, "NOT_AUTHORISED")
        self.assertFalse(self.authority.parallel_physical_merge)
        self.assertFalse(self.authority.force_push)
        self.assertFalse(self.authority.history_rewrite)

    def test_lawful_low_risk_packet_is_admitted(self) -> None:
        self.assertEqual(admit_live_pilot_packet(self.authority, admitted_packet()), "ALLOW_LIVE_SERIALIZED_GATEWAY")

    def test_active_pilot_path_also_denies_missing_vit_lineage(self) -> None:
        packet = LivePilotPacketAdmission("missing", "LOW_RISK_IMPLEMENTATION", "AUTO_EXECUTABLE", "NONE", True, True)
        self.assertEqual(admit_live_pilot_packet(self.authority, packet), "DENY_VIT_LINEAGE")

    def test_packet_class_and_authority_laundering_fail_closed(self) -> None:
        wrong_class = LivePilotPacketAdmission("x", "SCIENTIFIC_PROMOTION", "AUTO_EXECUTABLE", "NONE", True, True)
        self.assertEqual(admit_live_pilot_packet(self.authority, wrong_class), "DENY_PACKET_CLASS")
        authority_delta = LivePilotPacketAdmission("y", "LOW_RISK_IMPLEMENTATION", "AUTO_EXECUTABLE", "NEW_AUTHORITY", True, True)
        self.assertEqual(admit_live_pilot_packet(self.authority, authority_delta), "DENY_AUTHORITY_DELTA")
        reserved = LivePilotPacketAdmission("z", "LOW_RISK_IMPLEMENTATION", "OPERATOR_REQUIRED", "NONE", True, True)
        self.assertEqual(admit_live_pilot_packet(self.authority, reserved), "DENY_RESERVED_GATE")

    def test_unready_packet_fails_closed(self) -> None:
        self.assertEqual(
            admit_live_pilot_packet(self.authority, LivePilotPacketAdmission("a", "LOW_RISK_IMPLEMENTATION", "AUTO_EXECUTABLE", "NONE", False, True)),
            "DENY_PREREQUISITE",
        )
        self.assertEqual(
            admit_live_pilot_packet(self.authority, LivePilotPacketAdmission("b", "LOW_RISK_IMPLEMENTATION", "AUTO_EXECUTABLE", "NONE", True, False)),
            "DENY_QA",
        )
        self.assertEqual(
            admit_live_pilot_packet(self.authority, LivePilotPacketAdmission("c", "LOW_RISK_IMPLEMENTATION", "AUTO_EXECUTABLE", "NONE", True, True, 1, 0)),
            "DENY_UNRESOLVED_FINDING",
        )

    def test_q6_receipt_evaluation_requires_multiple_serial_exact_lanes(self) -> None:
        a = LivePilotMaterialisationReceipt("A", "A", "p0", "c1", "t1", "m1", "t1")
        b = LivePilotMaterialisationReceipt("B", "B", "m1", "c2", "t2", "m2", "t2")
        result = evaluate_q6_receipts((a, b))
        self.assertTrue(result["q6_pass"])
        self.assertEqual(result["parallel_merges"], 0)
        self.assertEqual(result["unexplained_main_divergence"], 0)
        self.assertEqual(result["tree_mismatches"], 0)
        with self.assertRaises(VitContractError):
            evaluate_q6_receipts((a,))


if __name__ == "__main__":
    unittest.main()
