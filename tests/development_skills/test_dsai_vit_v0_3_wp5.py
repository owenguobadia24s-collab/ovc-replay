from __future__ import annotations

import tempfile
import unittest

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import (
    PacketCompletionReceipt,
    PhysicalIntegrationLease,
    PhysicalMaterialisationTransaction,
    ReceiptStore,
    authorize_materialisation,
    materialisation_receipt,
    recover_unknown_write,
    validate_lease,
)

class DsaiVitV03Wp5Tests(unittest.TestCase):
    def _tx(self, profile: str = "ISOLATED_REHEARSAL") -> PhysicalMaterialisationTransaction:
        return PhysicalMaterialisationTransaction("vit:1","ticket:1","train:1","a"*40,"b"*40,"c"*40,"auth:1","assure:1",profile)

    def test_live_physical_main_remains_operator_denied(self) -> None:
        self.assertEqual(authorize_materialisation(self._tx("LIVE_PHYSICAL_MAIN"),pilot_authority_active=False),"WAITING_OPERATOR_AUTHORITY")
        self.assertEqual(authorize_materialisation(self._tx(),pilot_authority_active=False),"ALLOW_ISOLATED_REHEARSAL")

    def test_lease_is_exact_predecessor_guard(self) -> None:
        lease = PhysicalIntegrationLease("lease","a"*40,"b"*40,"controller")
        self.assertEqual(validate_lease(lease,"a"*40,"b"*40),"LEASE_VALID")
        self.assertEqual(validate_lease(lease,"d"*40,"b"*40),"PREDECESSOR_MOVED")
        self.assertEqual(validate_lease(PhysicalIntegrationLease("l","a"*40,"b"*40,"x",False),"a"*40,"b"*40),"LEASE_UNAVAILABLE")

    def test_exact_tree_equality_controls_materialisation_receipt(self) -> None:
        tx = self._tx()
        good = materialisation_receipt(tx,"d"*40,"c"*40)
        self.assertTrue(good.equality)
        self.assertEqual(good.outcome,"MATERIALISED_EQUIVALENT")
        bad = materialisation_receipt(tx,"d"*40,"e"*40)
        self.assertFalse(bad.equality)
        self.assertEqual(bad.outcome,"POST_WRITE_TREE_MISMATCH")

    def test_unknown_write_recovery_never_infers_success(self) -> None:
        tx = self._tx()
        self.assertEqual(recover_unknown_write(tx,"a"*40,"b"*40),"WRITE_NOT_EFFECTIVE_RETRYABLE")
        self.assertEqual(recover_unknown_write(tx,"d"*40,"c"*40),"WRITE_EFFECTIVE_RECEIPT_RECOVERY_REQUIRED")
        self.assertEqual(recover_unknown_write(tx,"d"*40,"e"*40),"POST_WRITE_STATE_UNKNOWN")

    def test_receipt_store_is_idempotent_rebuildable_and_divergence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = ReceiptStore(td)
            completion = PacketCompletionReceipt("P","WP5","impl","qa","gate","pip","vit","mat","WP6")
            path = store.put(completion,completion.receipt_id)
            self.assertEqual(store.put(completion,completion.receipt_id),path)
            index = store.rebuild_index()
            completion_key = store.packet_completion_generation_index_key(
                programme_id=completion.programme_id,
                packet_id=completion.packet_id,
                vit_generation_id=completion.vit_generation_id,
            )
            self.assertEqual(index[completion_key],path.name)
            path.write_text("{}",encoding="utf-8")
            with self.assertRaises(VitContractError):
                store.put(completion,completion.receipt_id)

if __name__ == "__main__":
    unittest.main()
