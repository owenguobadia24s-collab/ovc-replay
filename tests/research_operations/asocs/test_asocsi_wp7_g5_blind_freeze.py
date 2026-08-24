from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
WP7 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp7"
REC = ROOT / "records/research_operations/asocs/wp7"
STATE = ROOT / "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_19_WP7_G5_BLIND_EVIDENCE_FROZEN.json"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def csha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

class TestASOCSIWP7G5BlindFreeze(unittest.TestCase):
    def test_locked_prefix_and_session3plus(self):
        r1=load(REC/"ASOCSI_WP7_SESSION_01_HUMAN_INPUT_RECEIPT_v0_1.json")
        r2=load(REC/"ASOCSI_WP7_SESSION_02_HUMAN_INPUT_RECEIPT_v0_1.json")
        self.assertEqual(r1["source_artifact"]["sha256"],"9aaa80991365cf290122caef513f0e8d706a7b1283475fa041d01d8e5f9f1a0e")
        self.assertEqual(r2["source_artifact"]["sha256"],"f7662775a647c496fd09b45e3f7d0840559e4e079ef6c0ce3a5c7b2183c260db")
        self.assertTrue(r1["immutable"] and r2["immutable"])
        b=load(REC/"ASOCSI_WP7_SESSION_03_10_HUMAN_INPUT_RECEIPTS_v0_1.json")
        rows=b["session_3_plus"]
        self.assertEqual([x["session"] for x in rows],list(range(3,11)))
        self.assertEqual(sum(x["presentation_count"] for x in rows),179)
        self.assertEqual(sum(x["reviewed_count"] for x in rows),179)
        self.assertTrue(all(x["all_frozen_before_reveal"] and x["case_order_sha256"]==x["expected_case_order_sha256"] for x in rows))
        self.assertEqual(sum(x["submitted_identity_mismatch_count"] for x in rows),11)
        self.assertEqual(sum(x["tradingview_trace_count"] for x in rows),0)

    def test_normalization_is_derived_only(self):
        n=load(WP7/"ASOCSI_G5_BLIND_RECORD_IDENTITY_NORMALIZATION_v0_1.json")
        self.assertEqual(n["mismatch_count"],11)
        self.assertFalse(n["human_fields_changed"])
        self.assertTrue(n["raw_artifacts_preserved"])
        self.assertFalse(n["reveal_occurred_before_repair"])
        self.assertEqual({x["session"] for x in n["records"]},{7,9,10})
        self.assertTrue(all(x["submitted_blind_record_sha256"]!=x["canonical_blind_record_sha256"] for x in n["records"]))

    def test_g5_freeze_and_authority(self):
        f=load(WP7/"ASOCSI_G5_BLIND_EVIDENCE_FREEZE_v0_1.json")
        self.assertEqual((f["population"]["presentation_count"],f["population"]["unique_review_unit_count"],f["population"]["hidden_repeat_count"]),(229,218,11))
        self.assertTrue(f["human_review"]["all_frozen_before_reveal"])
        self.assertFalse(f["blindness"]["reveal_started"] or f["blindness"]["hidden_repeat_identities_reviewer_exposed"])
        a=load(WP7/"ASOCSI_G5_AUTHORITY_MANIFEST_v0_1.json"); d=load(WP7/"ASOCSI_G5_DEPENDENCY_FRONTIER_v0_1.json")
        p=load(WP7/"ASOCSI_WP7_G5_PACKET_v0_1.json"); dec=load(WP7/"ASOCSI_G5_DELEGATED_DECISION_v0_1.json")
        self.assertEqual(p["authority_manifest_id"],csha(a)); self.assertEqual(p["dependency_frontier_id"],csha(d))
        self.assertEqual(dec["basis"]["authority_manifest_id"],csha(a)); self.assertEqual(dec["basis"]["dependency_frontier_id"],csha(d))
        self.assertEqual(dec["decision"],"PASS"); self.assertEqual(dec["authority_delta"],"NONE")

    def test_state_stops_at_wp8_human_boundary(self):
        s=load(STATE); p=load(POINTER)
        self.assertEqual(s["status"],"COMPLETED")
        self.assertEqual(s["next_packet"],"ASOCSI-WP8-STAGED-REVEAL-AND-ADJUDICATION")
        self.assertEqual(s["stop_boundary"],"ASOCSI-WP8-STAGED-REVEAL-HUMAN_ADJUDICATION_REQUIRED")
        self.assertEqual(p["current_state"],str(STATE.relative_to(ROOT)).replace("\\","/"))
        self.assertEqual(p["next_packet"],s["next_packet"])

if __name__ == "__main__": unittest.main()
