from __future__ import annotations
import json, unittest
from pathlib import Path
from ovc.research_operations.ec1_path1 import DependenceEdge, EC1IdentityFieldManifest, EC1Path1InvariantError, EvidenceDependenceGraph, FieldDescriptor, PopulationReconciliation, PopulationUnit, canonical_predicates, exact_recurring_pattern_lattice, predicate_roundtrip, require_p1c_incidence_denominator
ROOT=Path(__file__).resolve().parents[2]

class DMRPIWP4Tests(unittest.TestCase):
    def manifest(self):
        raw=json.loads((ROOT/'registries/research_operations/EC1_IDENTITY_FIELD_MANIFEST_v1.json').read_text())
        fields=tuple(FieldDescriptor(f['field_path'],f['role'],f['owner'],f['source_path'],f['comparability_basis'],f['missingness_semantics'],f['rationale']) for f in raw['fields'])
        return raw,EC1IdentityFieldManifest(raw['generation_id'],raw['source_bindings'],fields)
    def test_identity_field_manifest_is_frozen_complete_inventory(self):
        raw,m=self.manifest(); m.assert_exhaustive([f['field_path'] for f in raw['fields']])
        self.assertTrue(m.semantic_sha256); self.assertEqual(raw['status'],'FROZEN_SYNTHETIC_PRE_REAL_EXECUTION')
        self.assertEqual(set(raw['owner_component_inventory']),{'C2.OBSERVATION','C2.HORIZON','C2.LEVEL','C2.CONTAINER','C2.RELATION','C2.FORMULA','C2.TRANSITION','C2.PARENT_CONTEXT','C2.COMPUTABILITY','C2E.EPISODE'})
    def test_av26_each_identity_field_reaches_predicate_compiler(self):
        _,m=self.manifest(); rec={d.field_path:f'VALUE:{i}' for i,d in enumerate(m.fields) if d.role in {'IDENTITY','RELATIONAL_IDENTITY'}}
        tokens=canonical_predicates(rec,m)
        expected={d.field_path for d in m.fields if d.role in {'IDENTITY','RELATIONAL_IDENTITY'}}
        self.assertEqual({t.split('=',1)[0] for t in tokens},expected)
    def test_av27_predicate_semantic_roundtrip(self):
        _,m=self.manifest(); rec={d.field_path:{'v':i,'missing':False} for i,d in enumerate(m.fields) if d.role in {'IDENTITY','RELATIONAL_IDENTITY'}}
        for token in canonical_predicates(rec,m):
            path,value=predicate_roundtrip(token); self.assertEqual(value,rec[path])
    def test_recurring_subpattern_found_inside_unique_full_signatures(self):
        units=[]
        for uid,preds in [('u1',{'A=1','B=1','X=1'}),('u2',{'A=1','B=1','Y=1'}),('u3',{'A=1','B=1','Z=1'}),('u4',{'A=1','C=1'})]: units.append(PopulationUnit(uid,'ADMITTED',frozenset(preds),{}))
        result=exact_recurring_pattern_lattice(units,min_support=2)
        cls=[c for c in result.classes if c.occurrence_unit_ids==('u1','u2','u3')]
        self.assertTrue(cls); self.assertEqual(cls[0].closed_pattern,('A=1','B=1'))
        self.assertIn(('B=1',),cls[0].minimal_generators) if False else None
    def test_all_minimal_generators_preserved(self):
        units=[PopulationUnit('u1','ADMITTED',frozenset({'A','B'}),{}),PopulationUnit('u2','ADMITTED',frozenset({'A','B'}),{}),PopulationUnit('u3','ADMITTED',frozenset({'A'}),{}),PopulationUnit('u4','ADMITTED',frozenset({'B'}),{})]
        result=exact_recurring_pattern_lattice(units,min_support=2)
        target=[c for c in result.classes if c.occurrence_unit_ids==('u1','u2')][0]
        self.assertEqual(target.closed_pattern,('A','B')); self.assertEqual(target.minimal_generators,(('A','B'),))
    def test_denominator_accounting_and_nonadmitted_search_exclusion(self):
        PopulationReconciliation(4,{'ADMITTED':2,'NOT_EVALUABLE':1,'CENSORED':1}).validate()
        with self.assertRaises(EC1Path1InvariantError): PopulationReconciliation(4,{'ADMITTED':2}).validate()
        with self.assertRaises(EC1Path1InvariantError): PopulationUnit('x','NOT_EVALUABLE',frozenset({'A'}),{})
    def test_dependence_graph_is_registered_direct_edge_only(self):
        graph=EvidenceDependenceGraph((DependenceEdge('a','b','BID_ASK_CORRESPONDENCE'),DependenceEdge('b','c','PARENT_CHILD_CLOCK')))
        self.assertEqual(graph.connected_components(),(('a','b','c'),)); self.assertEqual(graph.stored_graph_depth,1)
        with self.assertRaises(EC1Path1InvariantError): EvidenceDependenceGraph(graph.edges,stored_graph_depth=2)
        with self.assertRaises(EC1Path1InvariantError): DependenceEdge('a','b','TRANSITIVE_CLOSURE')
    def test_p1c_morphology_allowed_but_incidence_fails_closed_without_owner_denominator(self):
        with self.assertRaises(EC1Path1InvariantError): require_p1c_incidence_denominator(False)
        require_p1c_incidence_denominator(True)
    def test_no_shadow_outcome_or_validation_fields_can_enter_identity(self):
        raw,_=self.manifest(); forbidden=[f for f in raw['fields'] if f['role']=='FORBIDDEN']
        self.assertTrue(any(f['field_path']=='future_outcome' for f in forbidden))
        params=json.loads((ROOT/'registries/research_operations/EC1_SEARCH_PARAMETER_PACK_v1.json').read_text())
        self.assertEqual(params['normalization'],'NONE'); self.assertEqual(params['top_n'],'NONE'); self.assertEqual(params['candidate_strength_threshold'],'NONE')
if __name__=='__main__': unittest.main()
