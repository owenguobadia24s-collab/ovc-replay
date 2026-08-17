from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from ovc.development.skills.vit_completion_closeout import persist_non_churning_completion_closeout
from ovc.development.skills.vit_completion_runtime import persist_physical_completion
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import PhysicalMaterialisationTransaction,ReceiptStore

class TestCompletionCloseout(unittest.TestCase):
 def tx(self,g="g1"):
  return PhysicalMaterialisationTransaction(vit_generation_id=g,ticket_id="t",train_generation_id="tr",expected_predecessor_commit="a"*40,expected_predecessor_tree="b"*40,expected_result_tree="c"*40,authority_frontier_id="a1",assurance_frontier_id="q1",materialisation_profile="LIVE_PHYSICAL_MAIN")
 def proof(self,s,next_packet="WP2",g="g1"):
  tx=self.tx(g); r=persist_physical_completion(transaction=tx,observed_commit="d"*40,observed_tree="c"*40,programme_id="P",packet_id="WP1",implementation_ref="i",qa_ref="q",gate_decision_ref="g",payload_id="p",next_packet=next_packet,receipt_store=s)
  return {"transaction_id":tx.transaction_id,"exact_tree_equal":True,"four_content_addressed_receipts_present":True,"receipt_ids":{k:r[k] for k in ("materialisation_receipt_id","completion_receipt_id","development_latency_receipt_id","attachment_id")}}
 def test_success_idempotency_and_no_git_closeout(self):
  with tempfile.TemporaryDirectory() as td:
   s=ReceiptStore(td); p=self.proof(s); a=persist_non_churning_completion_closeout(receipt_store=s,proof=p); b=persist_non_churning_completion_closeout(receipt_store=s,proof=p)
   self.assertEqual(a,b); self.assertEqual(a["status"],"COMPLETED"); self.assertFalse(a["ordinary_closeout_pr_required"]); self.assertFalse(a["canonical_git_state_mutated"])
   rel=list((Path(td)/"successor-releases").glob("*.json")); self.assertEqual(len(rel),1); r=json.loads(rel[0].read_text()); self.assertFalse(r["execution_started"]); self.assertFalse(r["authority_inferred"])
 def test_terminal_has_no_release(self):
  with tempfile.TemporaryDirectory() as td:
   s=ReceiptStore(td); a=persist_non_churning_completion_closeout(receipt_store=s,proof=self.proof(s,None)); self.assertEqual(a["successor_release_status"],"PROGRAMME_TERMINAL"); self.assertIsNone(a["successor_release_id"])
 def test_duplicate_transaction_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   s=ReceiptStore(td); persist_non_churning_completion_closeout(receipt_store=s,proof=self.proof(s,g="g1"))
   with self.assertRaisesRegex(VitContractError,"VIT_DUPLICATE_EFFECTIVE_PACKET_COMPLETION"): persist_non_churning_completion_closeout(receipt_store=s,proof=self.proof(s,g="g2"))
 def test_tree_mismatch_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   s=ReceiptStore(td); p=self.proof(s); p["exact_tree_equal"]=False
   with self.assertRaisesRegex(VitContractError,"POST_WRITE_TREE_MISMATCH"): persist_non_churning_completion_closeout(receipt_store=s,proof=p)

if __name__=="__main__": unittest.main()
