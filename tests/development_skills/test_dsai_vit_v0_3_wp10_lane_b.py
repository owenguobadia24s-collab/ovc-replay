from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.vit_live_pilot import (
    LivePilotAuthority,
    LivePilotPacketAdmission,
    admit_live_pilot_packet,
)

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = ROOT / "registries/authority/DSAI3V_VIT_PILOT_AUTHORITY_v0_1.json"
PACKET_PATH = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-wp10/DSAI3V_WP10_LANE_B_PACKET.json"


class DsaiVitV03Wp10LaneBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority_record = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
        cls.authority = LivePilotAuthority.from_record(cls.authority_record)
        cls.packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))

    def test_lane_b_is_exactly_second_serial_low_risk_pilot_lane(self) -> None:
        self.assertEqual(self.packet["packet_id"], "DSAI3V-WP10-Q6-LANE-B")
        self.assertEqual(self.packet["packet_class"], "LOW_RISK_IMPLEMENTATION")
        self.assertEqual(self.packet["packet_class_policy"], "EXACT_ALLOWLIST_ONLY")
        self.assertEqual(self.packet["authority_delta"], "NONE")
        self.assertEqual(self.packet["prospective_order"], 2)
        self.assertFalse(self.packet["parallel_physical_merge"])
        self.assertEqual(self.packet["physical_gateway"], "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY")

    def test_lane_a_physical_result_is_lane_b_exact_predecessor(self) -> None:
        self.assertEqual(
            self.packet["baseline_main"],
            self.packet["lane_a_materialisation_commit"],
        )
        self.assertEqual(
            self.packet["baseline_main"],
            "08a60a6d0daa04bf9ac907960c98e5c619411c41",
        )
        self.assertEqual(
            self.packet["lane_a_observed_tree"],
            "8e2a067138feedc9c8d031b301243fe14569e15f",
        )

    def test_current_operator_approved_pilot_authority_revalidates(self) -> None:
        self.authority.validate()
        packet = LivePilotPacketAdmission(
            packet_id=self.packet["packet_id"],
            packet_class=self.packet["packet_class"],
            gate_class="AUTO_EXECUTABLE",
            authority_delta=self.packet["authority_delta"],
            prerequisites_pass=True,
            qa_pass=True,
            pip_id="d" * 64,
            vit_generation_id="e" * 64,
            vit_placement_id="f" * 64,
        )
        self.assertEqual(
            admit_live_pilot_packet(self.authority, packet),
            "ALLOW_LIVE_SERIALIZED_GATEWAY",
        )

    def test_general_activation_remains_reserved_during_lane_b(self) -> None:
        self.assertEqual(
            self.authority_record["allowed_packet_classes"],
            ["LOW_RISK_IMPLEMENTATION"],
        )
        self.assertFalse(self.authority_record["serialization"]["parallel_physical_merge"])
        self.assertTrue(self.authority_record["reserved_authority_unchanged"])
        self.assertEqual(self.authority_record["grt_binding"]["grt_g3"], "NOT_AUTHORISED")


if __name__ == "__main__":
    unittest.main()
