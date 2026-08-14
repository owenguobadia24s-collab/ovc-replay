from __future__ import annotations
import json, unittest
from pathlib import Path
from ovc.research_operations.dmrp_execution import DMRPExecutionBinding, F0BlindedProjection, F0InformationLeakError, OperatorTouch, OperatorTouchLedger, StageSemanticDependencyMatrix, leak_scan, research_operations_real_append_authorised
ROOT=Path(__file__).resolve().parents[2]
class DMRPIWP5Tests(unittest.TestCase):
    def test_dmrp_execution_binding_hash_enters_pack_bindings(self):
        b=DMRPExecutionBinding('b','study','cycle',('obj',),'IROF.RUN.synthetic',{'PATTERN_LATTICE':('PatternLatticeResult',)},('AUTH.SYNTH',),('ro:synthetic',),('FRESH_REPEAT_EQUAL',))
        self.assertEqual(b.pack_bindings(),{'dmrp_execution_binding':b.semantic_sha256}); self.assertEqual(b.authority_effect,'NONE')
    def test_stage_semantic_dependency_matrix_complete(self): StageSemanticDependencyMatrix().validate_complete()
    def test_f0_allowlist_projection(self):
        raw=json.loads((ROOT/'fixtures/research_operations/dmrp_wp5/F0_BLINDING_SYNTHETIC.json').read_text())
        p=F0BlindedProjection(raw['allowed_projection']); self.assertTrue(p.semantic_sha256)
    def test_f0_structural_content_leak_fails_closed(self):
        for payload in ({'pattern_id':'p1'},{'nested':{'minimal_generators':[['A']]}},{'candidate_dossier':{'id':'c'}}):
            with self.assertRaises(F0InformationLeakError): leak_scan(payload)
        with self.assertRaises(F0InformationLeakError): F0BlindedProjection({'run_id':'x','pattern_id':'p'})
    def test_operator_touch_records_only_blinded_fields(self):
        ledger=OperatorTouchLedger(); ledger.add(OperatorTouch('CLI','PASS',('run_id','stage_id','runtime_seconds','qa_state')))
        self.assertTrue(ledger.semantic_sha256)
        with self.assertRaises(F0InformationLeakError): OperatorTouch('CLI','PASS',('candidate_id',))
    def test_real_ro_append_not_self_granted(self):
        self.assertFalse(research_operations_real_append_authorised([])); self.assertTrue(research_operations_real_append_authorised(['RESEARCH_OPERATIONS_DMRP_EC1_BOUNDED_APPEND']))
    def test_irof_reuse_register_has_required_primitives(self):
        reg=json.loads((ROOT/'registries/research_operations/DMRP_IROF_REUSE_REGISTER_v0_1.json').read_text())
        for name in ['PopulationSpec','ResearchRunSpec','IntegratedRunManifest','SemanticCacheKey','CheckpointRecord','RestartLedger','CapacityBudget','StageExecutionReceipt','RunComparisonRecord']: self.assertIn(name,reg['reuse'])
        self.assertEqual(reg['real_source_append'],'DENIED_UNTIL_DMRPI_GREAL_EC1')
if __name__=='__main__': unittest.main()
