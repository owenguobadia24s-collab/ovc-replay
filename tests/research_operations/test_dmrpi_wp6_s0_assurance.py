from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.research_operations.dmrp_s0 import (
    S0AuthorityBlock, S0AuthoritySnapshot, S0ProtocolBlock, S0ReproductionMismatch,
    assert_boundary_pack_explicit, assert_cache_reuse, assert_context_is_stratifier,
    assert_corrupt_cache_handling, assert_dependency_reachability, assert_f0_not_e1_evidence,
    assert_f0_parameter_change, assert_f0_projection_safe, assert_fvt_monotone,
    assert_no_hidden_top_n, assert_no_illegal_representation, assert_no_posthoc_applicability,
    assert_no_shadow_rewrite, assert_not_independent_replication, assert_reproduction,
    assert_source_policy, cache_key, capacity_complete, classify_upper_layer_need,
    revalidate_authority, shard_semantic_hash, s0_feasibility_assessment,
)
from ovc.research_operations.ec1_path1 import DependenceEdge, EC1CapacityError, EC1Path1InvariantError, EvidenceDependenceGraph, FieldDescriptor, EC1IdentityFieldManifest, PopulationReconciliation, PopulationUnit, canonical_predicates, exact_recurring_pattern_lattice, predicate_roundtrip, require_p1c_incidence_denominator
from ovc.research_operations.dmrp_candidate import assess_candidate_change
from ovc.research_operations.dmrp_execution import F0BlindedProjection

ROOT=Path(__file__).resolve().parents[2]

class S0AVTests(unittest.TestCase):
    def test_av00_dependency_reachability(self):
        assert_dependency_reachability(['C2_VNEXT','C2E'])
        with self.assertRaises(S0ProtocolBlock): assert_dependency_reachability(['C2_VNEXT','VALIDATION'])
    def test_av01_replay_equality(self):
        units=[PopulationUnit('u1','ADMITTED',frozenset({'A','B'}),{}),PopulationUnit('u2','ADMITTED',frozenset({'A','B'}),{})]
        a=exact_recurring_pattern_lattice(units); b=exact_recurring_pattern_lattice(list(reversed(units)))
        self.assertEqual(a.semantic_sha256,b.semantic_sha256)
    def test_av02_denominator_reconciliation(self): PopulationReconciliation(3,{'ADMITTED':1,'NOT_EVALUABLE':1,'CENSORED':1}).validate()
    def test_av03_fvt_monotone(self):
        assert_fvt_monotone(['2026-01-01T00:00:00Z'],'2026-01-01T00:00:01Z')
        with self.assertRaises(S0ProtocolBlock): assert_fvt_monotone(['2026-01-02T00:00:00Z'],'2026-01-01T00:00:00Z')
    def test_av04_recurring_subpattern(self):
        units=[PopulationUnit('u1','ADMITTED',frozenset({'A','B','X'}),{}),PopulationUnit('u2','ADMITTED',frozenset({'A','B','Y'}),{}),PopulationUnit('u3','ADMITTED',frozenset({'A','B','Z'}),{})]
        r=exact_recurring_pattern_lattice(units); self.assertTrue(any(c.closed_pattern==('A','B') for c in r.classes))
    def test_av05_multiple_minimal_generator_visibility(self):
        units=[PopulationUnit('1','ADMITTED',frozenset({'A','B'}),{}),PopulationUnit('2','ADMITTED',frozenset({'A','B'}),{})]
        r=exact_recurring_pattern_lattice(units); c=[x for x in r.classes if x.occurrence_unit_ids==('1','2')][0]
        self.assertEqual(c.closed_pattern,('A','B')); self.assertEqual(c.minimal_generators,(('A',),('B',)))
    def test_av06_hidden_identity_field_requires_new_generation(self): self.assertTrue(assess_candidate_change({'definition'}).successor_generation_required)
    def test_av07_no_normalization_bucketing_weighting(self):
        assert_no_illegal_representation({'normalization':'NONE','distance':'NONE','learned_similarity':'NONE'})
        with self.assertRaises(S0ProtocolBlock): assert_no_illegal_representation({'normalization':'ZSCORE'})
    def test_av08_context_is_stratifier(self):
        assert_context_is_stratifier(base_membership_hash='a',context_enriched_membership_hash='a')
        with self.assertRaises(S0ProtocolBlock): assert_context_is_stratifier(base_membership_hash='a',context_enriched_membership_hash='b')
    def test_av09_no_posthoc_applicability(self):
        with self.assertRaises(S0ProtocolBlock): assert_no_posthoc_applicability(preregistered_scope_hash='a',reviewed_scope_hash='b')
    def test_av10_bidask_not_independent(self):
        with self.assertRaises(S0ProtocolBlock): assert_not_independent_replication('BID_ASK',True)
    def test_av11_parent_child_not_independent(self):
        with self.assertRaises(S0ProtocolBlock): assert_not_independent_replication('PARENT_CHILD_15M_2H',True)
    def test_av12_overlap_dependence_edge(self):
        g=EvidenceDependenceGraph((DependenceEdge('a','b','TRANSITION_SEQUENCE_OVERLAP'),)); self.assertEqual(g.connected_components(),(('a','b'),))
    def test_av13_incidence_without_denominator(self):
        with self.assertRaises(EC1Path1InvariantError): require_p1c_incidence_denominator(False)
    def test_av14_boundary_pack_explicit(self):
        assert_boundary_pack_explicit({'c2e_boundary_pack_id':'p','c2e_boundary_pack_sha256':'h'})
        with self.assertRaises(S0ProtocolBlock): assert_boundary_pack_explicit({})
    def test_av15_corrupt_cache_checkpoint(self):
        assert_corrupt_cache_handling('CORRUPT','QUARANTINE_AND_RECOMPUTE')
        with self.assertRaises(S0ProtocolBlock): assert_corrupt_cache_handling('CORRUPT','USE_ANYWAY')
    def test_av16_cache_changed_search_universe_miss(self):
        a=cache_key('u1','p','s'); b=cache_key('u2','p','s'); self.assertEqual(assert_cache_reuse(a,b),'MISS')
    def test_av17_f0_leak_block(self):
        F0BlindedProjection({'run_id':'r','stage_id':'s','runtime_seconds':1,'qa_state':'PASS'})
        with self.assertRaises(S0ProtocolBlock): assert_f0_projection_safe({'candidate_id':'c'})
    def test_av18_f0_scientific_parameter_change_successor(self): assert_f0_parameter_change({'parameter_pack'})
    def test_av19_source_unavailable_no_fallback(self):
        with self.assertRaises(S0AuthorityBlock): assert_source_policy(exact_source_available=False,fallback_requested=True)
    def test_av20_no_hidden_topn(self):
        assert_no_hidden_top_n({'top_n':'NONE'})
        with self.assertRaises(S0ProtocolBlock): assert_no_hidden_top_n({'top_n':10})
    def test_av21_capacity_truncation(self):
        with self.assertRaises(EC1CapacityError): capacity_complete(enumerated=9,expected_complete=10)
    def test_av22_self_induced_need_no_activation(self): self.assertEqual(classify_upper_layer_need('EC1_METHOD_LIMITATION')['activation_recommendation'],'NONE')
    def test_av23_shadow_rewrite_block(self):
        with self.assertRaises(S0ProtocolBlock): assert_no_shadow_rewrite('original','rewritten')
    def test_av24_authority_superseded_midrun(self):
        a=S0AuthoritySnapshot(('AUTH.1',)); a.assert_synthetic_only()
        with self.assertRaises(S0AuthorityBlock): revalidate_authority(a,S0AuthoritySnapshot(('AUTH.2',)))
    def test_av25_f0_not_e1_evidence(self):
        with self.assertRaises(S0ProtocolBlock): assert_f0_not_e1_evidence('F0A.OPERATIONAL','E1_SCIENTIFIC_EVIDENCE')
    def test_av26_identity_field_coverage(self):
        raw=json.loads((ROOT/'registries/research_operations/EC1_IDENTITY_FIELD_MANIFEST_v1.json').read_text())
        fields=tuple(FieldDescriptor(f['field_path'],f['role'],f['owner'],f['source_path'],f['comparability_basis'],f['missingness_semantics'],f['rationale']) for f in raw['fields'])
        m=EC1IdentityFieldManifest(raw['generation_id'],raw['source_bindings'],fields)
        expected=tuple(d.field_path for d in m.fields if d.role in {'IDENTITY','RELATIONAL_IDENTITY'})
        rec={field_path:f'v{i}' for i,field_path in enumerate(expected)}
        tokens=canonical_predicates(rec,m)
        self.assertEqual(len(tokens),len(expected))
        self.assertEqual({predicate_roundtrip(token)[0] for token in tokens},set(expected))
    def test_av27_predicate_roundtrip(self):
        path,value=predicate_roundtrip('x={"a":1}'); self.assertEqual((path,value),('x',{'a':1}))
    def test_av28_dependence_direct_only(self):
        with self.assertRaises(EC1Path1InvariantError): EvidenceDependenceGraph((DependenceEdge('a','b','COMMON_C2E_EPISODE'),),2)
    def test_av29_sharding_preserves_hash_and_ownership(self):
        pairs=[('u1','h1'),('u2','h2'),('u3','h3')]; self.assertEqual(shard_semantic_hash(pairs,[['u1'],['u2','u3']]),shard_semantic_hash(pairs,[['u1','u2'],['u3']]))
        with self.assertRaises(S0ProtocolBlock): shard_semantic_hash(pairs,[['u1'],['u2']])
    def test_av30_reproduction_mismatch_blocks(self):
        assert_reproduction('h','h')
        with self.assertRaises(S0ReproductionMismatch): assert_reproduction('h','x')
    def test_feasibility_and_greal_stay_non_authoritative(self):
        a=s0_feasibility_assessment(identity_dimension_count=11,max_predicate_cardinality=11,synthetic_unit_count=16,enumerated_conjunctions=2047,closure_count=10,minimal_generator_count=14); self.assertEqual(a['status'],'PASS'); self.assertEqual(a['authority_effect'],'NONE')
        policy=json.loads((ROOT/'registries/research_operations/EC1_F0_SELECTOR_AND_SCALE_POLICY_v1.json').read_text()); self.assertEqual(policy['effective_only_after'],'DMRPI-GREAL-EC1_PASS')
if __name__=='__main__': unittest.main()
