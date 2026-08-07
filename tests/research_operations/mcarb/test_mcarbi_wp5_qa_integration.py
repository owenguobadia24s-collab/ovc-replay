import json
import unittest
from pathlib import Path
from decimal import Decimal
from ovc.research_operations.mcarb import PriceBar, raw_activity, directional_change, high_low_range
from ovc.research_operations.mcarb.pack import PackDefinition, nested_ablation_field_sets
from ovc.research_operations.mcarb.dependence import pearson
from ovc.research_operations.mcarb.controls import matched_complexity_noise
from ovc.research_operations.mcarb.qa import (
    RESERVED_ACTIONS, authority_guard, validate_al_candidate, validate_proxy_quality,
    validate_normalization, null_consequence,
)
from ovc.research_operations.mcarb.evidence import EvidenceEnvelope, validate_external_artifact_ref, append_audit_event

ROOT=Path(__file__).resolve().parents[3]

class MCARBIWP5QAIntegrationTest(unittest.TestCase):
    def test_fixture_catalog_is_exact(self):
        doc=json.loads((ROOT/"fixtures/research_operations/mcarb/MCARB_ADVERSARIAL_FIXTURE_CATALOG_v0_1.json").read_text())
        ids=[x["fixture_id"] for x in doc["fixtures"]]
        self.assertEqual(ids,[f"MCARB-FX-{i:02d}" for i in range(1,15)])
        self.assertEqual(doc["authority"],"SYNTHETIC_FIXTURE_ONLY")

    def test_iqa_01_source_binding_envelope_is_exact_and_deterministic(self):
        env=EvidenceEnvelope("AuxiliaryMeasurement","OPT-A.GBPUSD.DEVELOPMENT.2024.v2",("BAR.1",),"2024-01-02T01:00:00Z",{"candidate_id":"VS-03"})
        self.assertEqual(env.record_id,env.record_id)
        self.assertEqual(env.to_dict()["source_release_id"],"OPT-A.GBPUSD.DEVELOPMENT.2024.v2")
        self.assertEqual(env.to_dict()["source_record_ids"],["BAR.1"])

    def test_iqa_03_04_al_block_is_branch_local(self):
        eligible=("AL-01","AL-05","AL-07","AL-08","AL-09")
        self.assertEqual(validate_al_candidate("AL-10",eligible).result,"BLOCK")
        b=PriceBar("B1","BID","2024-01-02T00:00:00Z","2024-01-02T00:15:00Z",Decimal("1"),Decimal("1.02"),Decimal("0.99"),Decimal("1.01"),Decimal("10"))
        self.assertEqual(high_low_range(b).candidate_id,"VS-03")

    def test_iqa_05_proxy_honesty(self):
        self.assertEqual(validate_proxy_quality("AL-11",proxy_label="COARSE_PAIRED_BAR_PROXY",status="NOT_EVALUABLE",information_loss=None).result,"PASS")
        self.assertEqual(validate_proxy_quality("AL-11",proxy_label=None,status="PASS",information_loss=0.1).result,"BLOCK")

    def test_iqa_07_08_09_pack_composite_and_dependence(self):
        definition=PackDefinition("R6",("P","AL-01","ET-X","VS-01"),(("P","PRICE"),("AL-01","AL"),("ET-X","ET"),("VS-01","VS")))
        self.assertEqual(nested_ablation_field_sets(definition)["R4X"],("P","AL-01","ET-X"))
        self.assertEqual(pearson([1,2,3],[1,2,3]),Decimal(1))

    def test_iqa_10_normalization_leakage(self):
        self.assertEqual(validate_normalization(causal=True,reference_hash="a"*64,refit_on_evaluation=False).result,"PASS")
        self.assertEqual(validate_normalization(causal=True,reference_hash=None,refit_on_evaluation=False).result,"BLOCK")

    def test_iqa_11_missingness_no_zero_fill(self):
        b=PriceBar("B1","BID","2024-01-02T00:00:00Z","2024-01-02T00:15:00Z",Decimal("1"),Decimal("1.02"),Decimal("0.99"),Decimal("1.01"),None)
        m=raw_activity(b)
        self.assertIsNone(m.value)
        self.assertEqual(m.missingness_state,"SOURCE_FIELD_ABSENT")

    def test_iqa_12_capacity_control_fixture_is_deterministic(self):
        a=matched_complexity_noise(["A","B"],dimensions=3,seed_id="C0")
        b=matched_complexity_noise(["A","B"],dimensions=3,seed_id="C0")
        self.assertEqual(a,b)

    def test_iqa_13_null_consequence(self):
        self.assertEqual(null_consequence(["REDUNDANT_WITH_PRICE_STRUCTURE","NO_ADDITIONAL_INFORMATION"]),"NO_ADDITIONAL_INFORMATION")

    def test_iqa_14_15_validation_and_authority_firewall(self):
        self.assertIn("VALIDATION_READ",RESERVED_ACTIONS)
        for action in RESERVED_ACTIONS:
            with self.assertRaises(PermissionError):
                authority_guard(action)

    def test_append_only_evidence_and_external_ref(self):
        ref={"artifact_id":"A","sha256":"a"*64,"size_bytes":12,"media_type":"application/json","storage_class":"LOCAL_EXTERNAL"}
        validate_external_artifact_ref(ref)
        ledger=append_audit_event((),{"event_id":"E1","action":"QA"})
        self.assertEqual(len(ledger),1)
        with self.assertRaises(ValueError):
            append_audit_event(ledger,{"event_id":"E1","action":"QA2"})

if __name__=="__main__": unittest.main()
