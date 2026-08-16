from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.vit_general import GeneralVitAuthority, GeneralVitPacketAdmission, admit_general_packet

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "registries/authority/DSAI3V_VIT_GENERAL_AUTHORITY_v0_1.json"
DECISION = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/dsai3v-wp11/DSAI3V_G_VIT_GENERAL_OPERATOR_PASS.json"
PIP = "d" * 64
GEN = "e" * 64
PLACEMENT = "f" * 64


def admitted(packet_id: str, programme_id: str, gate_class: str = "AUTO_EXECUTABLE") -> GeneralVitPacketAdmission:
    return GeneralVitPacketAdmission(
        packet_id,
        programme_id,
        gate_class,
        "NONE",
        True,
        True,
        True,
        pip_id=PIP,
        vit_generation_id=GEN,
        vit_placement_id=PLACEMENT,
    )


class DsaiVitV03Wp11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority_record = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        cls.authority = GeneralVitAuthority.from_record(cls.authority_record)

    def test_operator_pass_and_general_authority_are_exact(self) -> None:
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["gate_id"], "DSAI3V-G-VIT-GENERAL")
        self.authority.validate()
        self.assertEqual(self.authority.routing_scope, "NORMAL_ALREADY_AUTHORISED_AUTO_EXECUTABLE_POPULATION")
        self.assertFalse(self.authority.parallel_physical_merge)
        self.assertEqual(self.authority.grt_g3, "NOT_AUTHORISED")

    def test_independent_lane_smoke_admits_only_existing_owner_authority(self) -> None:
        lane_a = admitted("SMOKE-A", "PROGRAMME-A")
        lane_b = admitted("SMOKE-B", "PROGRAMME-B", "AUTO_RATIFIABLE")
        self.assertEqual(admit_general_packet(self.authority, lane_a), "ALLOW_VIT_GENERAL_SERIALIZED_GATEWAY")
        self.assertEqual(admit_general_packet(self.authority, lane_b), "ALLOW_VIT_GENERAL_SERIALIZED_GATEWAY")

    def test_eligible_work_without_vit_lineage_fails_closed(self) -> None:
        missing = GeneralVitPacketAdmission("missing", "P", "AUTO_EXECUTABLE", "NONE", True, True, True)
        self.assertEqual(admit_general_packet(self.authority, missing), "DENY_VIT_LINEAGE")

    def test_reserved_or_unowned_work_fails_closed(self) -> None:
        self.assertEqual(admit_general_packet(self.authority, GeneralVitPacketAdmission("r", "P", "OPERATOR_REQUIRED", "NONE", True, True, True)), "DENY_RESERVED_GATE")
        self.assertEqual(admit_general_packet(self.authority, GeneralVitPacketAdmission("a", "P", "AUTO_EXECUTABLE", "NEW_AUTHORITY", True, True, True)), "DENY_AUTHORITY_DELTA")
        self.assertEqual(admit_general_packet(self.authority, GeneralVitPacketAdmission("o", "P", "AUTO_EXECUTABLE", "NONE", False, True, True)), "DENY_OWNER_AUTHORITY")
        self.assertEqual(admit_general_packet(self.authority, GeneralVitPacketAdmission("b", "P", "AUTO_EXECUTABLE", "NONE", True, True, True, reserved_boundary_pending=True)), "DENY_RESERVED_BOUNDARY")


if __name__ == "__main__":
    unittest.main()
