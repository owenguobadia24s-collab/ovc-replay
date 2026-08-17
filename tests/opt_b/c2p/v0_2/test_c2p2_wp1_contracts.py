from __future__ import annotations
import hashlib
import json
import unittest
from decimal import Decimal
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4]
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))
from ovc.opt_b.c2p_v0_2.canonical import canonical_bytes, CanonicalizationError

SCHEMA_DIR=ROOT/"schemas/opt_b/c2p/v0_2"
REG_DIR=ROOT/"registries/opt_b/c2p/v0_2"
FIX_DIR=ROOT/"fixtures/opt_b/c2p/v0_2/packs"
QA_DIR=ROOT/"qa/opt_b/c2p/v0_2"

class WP1ContractsTest(unittest.TestCase):
    def test_exact_catalogue_counts_and_closed_schemas(self):
        contracts=list((ROOT/"contracts/opt_b/c2p/v0_2").glob("*.md"))
        schemas=list(SCHEMA_DIR.glob("*.json"))
        registries=[p for p in REG_DIR.glob("*.json") if p.name not in {"C2P_CANONICAL_SERIALIZATION_PROFILE_v0_2.json","DEFERRED_RECONCILIATION_NAMESPACE_RESERVATION.json"}]
        self.assertEqual(len(contracts),15)
        self.assertEqual(len(schemas),14)
        self.assertEqual(len(registries),12)
        for p in schemas:
            data=json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data["type"],"object",p.name)
            self.assertIs(data["additionalProperties"],False,p.name)
            self.assertTrue(data["required"],p.name)

    def test_registry_uniqueness_and_no_active_pack(self):
        for p in REG_DIR.glob("*.json"):
            d=json.loads(p.read_text(encoding="utf-8"))
            entries=d.get("entries",[])
            ids=[e.get("id",e.get("object_pack_id")) for e in entries]
            self.assertEqual(len(ids),len(set(ids)),p.name)
        packs=json.loads((REG_DIR/"OBJECT_PACK_REGISTRY_v0_2.json").read_text(encoding="utf-8"))
        self.assertIsNone(packs["active_object_pack_id"])
        self.assertEqual(len(packs["entries"]),2)
        self.assertTrue(all(not e["activation_eligible"] and e["real_source_forbidden"] for e in packs["entries"]))
        self.assertTrue(all(len(e["object_pack_hash"]) == 64 for e in packs["entries"]))

    def test_synthetic_packs_are_concrete_distinct_and_hash_pinned(self):
        a=json.loads((FIX_DIR/"C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json").read_text(encoding="utf-8"))
        b=json.loads((FIX_DIR/"C2P_SYNTH_OBJECTPACK_MINIMAL_B_v1.json").read_text(encoding="utf-8"))
        self.assertNotEqual(a["object_pack_id"],b["object_pack_id"])
        self.assertNotEqual(a["object_pack_hash"],b["object_pack_hash"])
        for p in (a,b):
            self.assertEqual(p["status"],"SYNTHETIC_ONLY_NONEMPIRICAL")
            self.assertFalse(p["activation_eligible"])
            self.assertTrue(p["real_source_forbidden"])
            self.assertEqual(p["confirmation_contract"]["successive_member_candidates"],3)
            self.assertFalse(p["retirement_contract"]["censoring_is_retirement"])
            self.assertFalse(p["retirement_contract"]["missingness_is_retirement"])
            for key in ("candidate_contract","tracklet_contract","confirmation_contract","matching_contract","retrieval_contract","continuity_contract","retirement_contract","split_merge_contract","chronology_contract","serialization_contract","operations_contract"):
                self.assertIn(key,p)
                self.assertIsInstance(p[key],dict)
            unhashed=dict(p); expected=unhashed.pop("object_pack_hash")
            raw=json.dumps(unhashed,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
            self.assertEqual(expected,hashlib.sha256(raw).hexdigest())

    def test_design_field_families_are_explicit(self):
        candidate=json.loads((SCHEMA_DIR/"c2p_candidate_v0_2.json").read_text())
        tracklet=json.loads((SCHEMA_DIR/"c2p_tracklet_v0_2.json").read_text())
        assertion=json.loads((SCHEMA_DIR/"c2p_object_assertion_v0_2.json").read_text())
        snapshot=json.loads((SCHEMA_DIR/"c2p_object_snapshot_v0_2.json").read_text())
        checkpoint=json.loads((SCHEMA_DIR/"c2p_checkpoint_v0_2.json").read_text())
        self.assertTrue({"source_refs","evidence_status"}.issubset(candidate["required"]))
        self.assertTrue({"decision_frontier","observability_state","evaluation_state"}.issubset(tracklet["required"]))
        self.assertIn("CONFIRMED",tracklet["properties"]["state"]["enum"])
        self.assertNotIn("PROMOTED",tracklet["properties"]["state"]["enum"])
        self.assertTrue({"genesis_event_id","lifecycle_state"}.issubset(assertion["required"]))
        self.assertTrue({"geometry","state_payload","evaluation_cutoff"}.issubset(snapshot["required"]))
        self.assertTrue({"run_manifest_id","object_pack_hashes","open_tracklet_ids","assertion_map_digest","index_digest","projection_digest"}.issubset(checkpoint["required"]))
        edges=json.loads((REG_DIR/"C2P_LINEAGE_EDGE.json").read_text())
        edge_ids={e["id"] for e in edges["entries"]}
        self.assertTrue({"SPLIT_FROM","MERGED_FROM","RECURRENCE_OF"}.issubset(edge_ids))
        self.assertEqual(edges["forbidden"],["SAME_OBJECT_AS"])

    def test_canonical_profile_goldens_and_rejections(self):
        x={"b":Decimal("1.2300"),"a":None,"c":["é",Decimal("2.000")]}
        self.assertEqual(canonical_bytes(x),'{"a":null,"b":"1.23","c":["é","2"]}'.encode('utf-8'))
        self.assertEqual(canonical_bytes({"z":1,"a":2}),canonical_bytes({"a":2,"z":1}))
        for bad in [1.0,float("nan"),float("inf"),-0.0]:
            with self.assertRaises(CanonicalizationError):
                canonical_bytes({"x":bad})
        with self.assertRaises(CanonicalizationError):
            canonical_bytes({"x":"e\u0301"})

    def test_geometry_role_and_missingness_remain_distinct(self):
        roles=json.loads((REG_DIR/"STRUCTURAL_ROLE.json").read_text(encoding="utf-8"))
        by={e["id"]:e for e in roles["entries"]}
        self.assertIn("POINT_REFERENCE",by["LEVEL"]["allowed_geometry"])
        self.assertIn("POINT_REFERENCE",by["BOUNDARY"]["allowed_geometry"])
        self.assertNotEqual("LEVEL","BOUNDARY")
        ev=json.loads((REG_DIR/"EVALUATION_EVIDENCE_STATE.json").read_text(encoding="utf-8"))
        values={e["id"] for e in ev["entries"]}
        self.assertTrue({"ABSENT","MISSING","NOT_EVALUABLE","AMBIGUOUS","CONFLICT"}.issubset(values))
        obs=json.loads((REG_DIR/"OBSERVABILITY_STATE.json").read_text(encoding="utf-8"))
        self.assertIn("CENSORED",{e["id"] for e in obs["entries"]})

    def test_core_qa_fixture_scope_and_no_validation(self):
        q=json.loads((QA_DIR/"assertions.json").read_text(encoding="utf-8"))
        f=json.loads((QA_DIR/"fixtures.json").read_text(encoding="utf-8"))
        self.assertEqual(len(q["core_blocking"]),37)
        self.assertEqual(q["deferred_future"],["C2P2-QA-024","C2P2-QA-025","C2P2-QA-026","C2P2-QA-027"])
        self.assertTrue(all(x.startswith("C2P2-QA-") for x in q["core_blocking"]+q["deferred_future"]))
        self.assertEqual(len(f["core_blocking"]),39)
        self.assertEqual(len(f["deferred_reconciliation"]),9)
        self.assertTrue(all(x.startswith("C2P2-F") for x in f["core_blocking"]+f["deferred_reconciliation"]))
        all_text="".join(p.read_text(encoding="utf-8") for p in FIX_DIR.glob("*.json"))
        self.assertNotIn("ACTIVE_VALIDATION",all_text)
        self.assertNotIn("2025",all_text)

if __name__=="__main__":
    unittest.main()
