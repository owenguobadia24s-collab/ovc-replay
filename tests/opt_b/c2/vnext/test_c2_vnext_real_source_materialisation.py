import json
from pathlib import Path
from tests.historical_court_record import json_at
import unittest

from ovc.opt_b.c2_vnext.horizons import evaluate_horizon
from ovc.opt_b.c2_vnext.observation import build_population, default_gbpusd_calendar, baseline_lattices
from ovc.opt_b.c2_vnext.real_source_materialisation import (
    c1_to_evidence, fast_horizon, horizon_definition, formula_membership, PARTITION_ID,
)

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2-vnext-real-observation-materialisation-v0-1"
RECEIPT = BASE / "C2VNEXT_RM1_EXECUTION_RECEIPT.json"
DECISION = BASE / "C2VNEXT_RM1_OPERATOR_DECISION.json"
QA = BASE / "C2VNEXT_RM1_QA_PACKET.json"
STATE = ROOT / "registries/implementation/c2_vnext_real_materialisation/OVC_C2VNEXT_RM_STATE_v0_1.json"


def synthetic_rows():
    rows=[]
    for i in range(20):
        start_minutes=i*15; end_minutes=(i+1)*15
        rows.append({
            "open_time":f"2026-06-01T{start_minutes//60:02d}:{start_minutes%60:02d}:00Z",
            "close_time":f"2026-06-01T{end_minutes//60:02d}:{end_minutes%60:02d}:00Z",
            "side":"BID","c1_record_id":f"C1.{i}","opt_a_release_id":"OPTA.TEST","source_bar_id":f"BAR.{i}",
            "c1_release_id":"C1.TEST","quality_state":"COMPLETE",
            "prices":{"open":"1.0","high":"1.1","low":"0.9","close":"1.0"}
        })
    return rows


class C2VNextRealMaterialisationTests(unittest.TestCase):
    def population(self):
        rows=synthetic_rows()
        return build_population(
            "2026-06-01T00:00:00Z","2026-06-01T05:00:00Z",instrument="GBPUSD",
            calendar=default_gbpusd_calendar(),evidence_rows=[c1_to_evidence(row) for row in rows],
            sides=("BID",),lattices=(baseline_lattices()[0],),partition_id=PARTITION_ID,
        )["observations"]

    def test_fast_trailing_horizon_adapter_is_exact_frozen_evaluator(self):
        items=self.population()
        for count in (4,8,16):
            definition=horizon_definition(count)
            for index in (0,3,7,15,19):
                expected=evaluate_horizon(definition,items,as_of_observation_id=items[index]["observation_id"],consumer_class="C2_MEASUREMENT")
                self.assertEqual(expected,fast_horizon(definition,items,index))

    def test_formula_membership_crosswalk_changes_vocabulary_not_semantics(self):
        items=self.population(); definition=horizon_definition(4)
        complete=fast_horizon(definition,items,3)
        adapted=formula_membership(complete,items[3]["first_valid_time"])
        self.assertEqual("COMPLETE",adapted["status"])
        self.assertEqual(complete["membership_id"],adapted["membership_id"])
        early=fast_horizon(definition,items,0)
        self.assertEqual(early["reason"],formula_membership(early,items[0]["first_valid_time"])["status"])

    def test_real_execution_receipt_is_exact_and_authority_safe(self):
        receipt=json.loads(RECEIPT.read_text())
        self.assertEqual(2,receipt["execution"]["clean_run_count"])
        self.assertEqual("PASS",receipt["execution"]["byte_equivalence"])
        self.assertEqual(4072,receipt["counts"]["15m_target_eligible"])
        self.assertEqual(3556,receipt["counts"]["target_parent_linked"])
        self.assertEqual(516,receipt["counts"]["target_parent_not_computable"])
        self.assertEqual("NONE",receipt["execution"]["provider_intake"])
        self.assertEqual("NONE",receipt["execution"]["validation_consumption"])
        self.assertEqual("NONE",receipt["authority_after"]["selector"])
        self.assertEqual("DENIED_PENDING_FRESH_EXACT_C2E2_G6_RUN_AUTH",receipt["authority_after"]["c2e_wp6"])

    def test_operator_decision_and_qa_preserve_reserved_boundaries(self):
        decision=json.loads(DECISION.read_text()); qa=json.loads(QA.read_text()); state=json_at("f4ef2c104f0e812cac3ed08215e6d81671352e57",STATE)
        self.assertEqual("PASS",decision["decision"])
        self.assertEqual("AUTHORIZED_INACTIVE_SHADOW_ONLY",decision["authority_delta"]["bounded_real_source_c2_vnext_materialisation"])
        self.assertEqual("DENIED",decision["authority_delta"]["outcome_validation_publication"])
        self.assertEqual([],qa["blocking_warnings"]); self.assertEqual([],qa["unresolved_issues"])
        self.assertEqual("QA_REVIEW",state["status"])
        self.assertEqual("UNCHANGED_READ_ONLY",state["authority"]["active_c2"])


if __name__ == "__main__":
    unittest.main()
