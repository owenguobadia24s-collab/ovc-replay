from __future__ import annotations

import unittest

from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest, PacketIntegrationPayload, VitContractError
from ovc.development.skills.vit_ledger import (
    IntegrationTicket,
    LedgerPlacement,
    VirtualIntegrationLedger,
    classify_payload_conflict,
    safe_bypass,
    schedule_ready,
    selective_invalidation,
)

class DsaiVitV03Wp3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.auth = IntegrationAuthorityManifest("PLAN","WP","G","AUTO_EXECUTABLE","NONE",("source",))
        self.dep = DependencyFrontier((), "NONE")

    def _pip(self, packet: str, path: str, content: str = "a") -> PacketIntegrationPayload:
        auth = IntegrationAuthorityManifest("PLAN",packet,"G","AUTO_EXECUTABLE","NONE",("source",))
        return PacketIntegrationPayload("P",packet,({"op":"MODIFY","path":path,"blob_sha":content*40,"mode":"100644"},),auth,self.dep,{})

    def test_ledger_exact_resubmission_is_idempotent_and_mutation_conflict_fails(self) -> None:
        ledger = VirtualIntegrationLedger()
        placement = LedgerPlacement("p","a"*40,"b"*40,"profile",0,"dep","auth")
        self.assertEqual(ledger.append(placement), placement)
        self.assertEqual(ledger.append(placement), placement)
        self.assertEqual(len(ledger.placements), 1)
        with self.assertRaises(VitContractError):
            ledger.append(LedgerPlacement("p","a"*40,"c"*40,"profile",0,"dep","auth"))

    def test_conflict_classification_is_conservative(self) -> None:
        a = self._pip("A","one.txt","a")
        b = self._pip("B","two.txt","b")
        c = self._pip("C","one.txt","c")
        delete_auth = IntegrationAuthorityManifest("PLAN","D","G","AUTO_EXECUTABLE","NONE",("source",))
        d = PacketIntegrationPayload("P","D",({"op":"DELETE","path":"one.txt"},),delete_auth,self.dep,{})
        self.assertEqual(classify_payload_conflict(a,b), "COMMUTATIVE")
        self.assertEqual(classify_payload_conflict(a,c), "ORDER_SENSITIVE")
        self.assertEqual(classify_payload_conflict(a,d), "MUTUALLY_EXCLUSIVE")

    def test_safe_bypass_is_dependency_and_conflict_guarded(self) -> None:
        pa = self._pip("A","one.txt","a")
        pb = self._pip("B","two.txt","b")
        pc = self._pip("C","one.txt","c")
        blocked = IntegrationTicket("P","A",pa.payload_id,0,(),True)
        good = IntegrationTicket("P","B",pb.payload_id,1,(),False)
        conflict = IntegrationTicket("P","C",pc.payload_id,2,(),False)
        dependent = IntegrationTicket("P","B",pb.payload_id,3,("A",),False)
        payloads = {pa.payload_id:pa,pb.payload_id:pb,pc.payload_id:pc}
        self.assertTrue(safe_bypass(blocked,good,payloads))
        self.assertFalse(safe_bypass(blocked,conflict,payloads))
        self.assertFalse(safe_bypass(blocked,dependent,payloads))

    def test_scheduler_is_work_conserving_without_unsafe_bypass(self) -> None:
        pa = self._pip("A","one.txt","a")
        pb = self._pip("B","two.txt","b")
        pc = self._pip("C","one.txt","c")
        tickets = (
            IntegrationTicket("P","A",pa.payload_id,0,(),True),
            IntegrationTicket("P","B",pb.payload_id,1,(),False),
            IntegrationTicket("P","C",pc.payload_id,2,(),False),
        )
        selected = schedule_ready(tickets,(),{pa.payload_id:pa,pb.payload_id:pb,pc.payload_id:pc})
        self.assertEqual([t.packet_id for t in selected], ["B"])

    def test_selective_invalidation_never_escalates_unnecessarily(self) -> None:
        self.assertEqual(selective_invalidation(payload_id="p",predecessor_only=True).severity,"PLACEMENT_RECOMPUTE_ONLY")
        self.assertEqual(selective_invalidation(payload_id="p",assurance_base_changed=True).severity,"ASSURANCE_RENEWAL_REQUIRED")
        self.assertEqual(selective_invalidation(payload_id="p",dependency_changed=True).severity,"PAYLOAD_REBUILD_REQUIRED")
        self.assertEqual(selective_invalidation(payload_id="p",authority_changed=True).severity,"AUTHORITY_REVIEW_REQUIRED")
        with self.assertRaises(VitContractError):
            selective_invalidation(payload_id="p",predecessor_only=True,dependency_changed=True)

if __name__ == "__main__":
    unittest.main()
