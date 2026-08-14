from __future__ import annotations
import unittest
from ovc.research_operations.dmrp_exploration import ExplorationAuthorityError, NonEvidentiaryExploration, OperatorTouch, Path2IntakeDisposition, Path2OperationalHealthLedger, Path2OperatorReadinessPack

class DMRPIWP3Tests(unittest.TestCase):
    def test_non_evidentiary_exploration_cannot_promote(self):
        item=NonEvidentiaryExploration("x","PATH_1_EMPIRICAL",{"idea":"synthetic"})
        self.assertEqual(item.authority_effect,"NONE")
        with self.assertRaises(ExplorationAuthorityError): item.freeze_candidate()

    def test_path2_readiness_is_synthetic_only(self):
        d=Path2IntakeDisposition("i","READY_FOR_GUIDED_FORMALISATION")
        pack=Path2OperatorReadinessPack("p",("train",),("guide",),(d,))
        self.assertFalse(pack.real_source_ready)
        with self.assertRaises(ExplorationAuthorityError): Path2IntakeDisposition("i2","DEFERRED",source_class="REAL")
        with self.assertRaises(ExplorationAuthorityError): Path2OperatorReadinessPack("p2",("t",),("g",),(d,),real_source_ready=True)

    def test_operator_touch_queue_abandonment_metrics(self):
        ledger=Path2OperationalHealthLedger()
        ledger.add(OperatorTouch("FORMALISE",20,1,False)); ledger.add(OperatorTouch("FORMALISE",40,2,True))
        self.assertEqual(ledger.summary(),{"touches":2,"abandoned":1,"interventions":3,"max_queue_age_seconds":40,"authority_effect":"NONE"})

    def test_no_real_source_candidate_generation_authority(self):
        with self.assertRaises(ExplorationAuthorityError): NonEvidentiaryExploration("x","PATH_2_THEORY_FORMALISATION",{},source_class="REAL")

if __name__=="__main__": unittest.main()
