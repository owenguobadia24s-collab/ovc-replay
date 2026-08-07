from __future__ import annotations
import copy,hashlib,json,unittest
from pathlib import Path
from ovc.opt_b.market_grammar.candidate_migration import classify_legacy_feature,migrate_candidate

ROOT=Path(__file__).resolve().parents[2]
LEDGER=ROOT/"registries/opt_b/market_grammar/MG_CEAR_G10_MIGRATION_LEDGER_v0_1.json"
FEATURES=ROOT/"registries/opt_b/market_grammar/MG_CEAR_G10_TYPED_FEATURE_MIGRATION_REGISTRY_v0_1.json"

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def canon_hash(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()

def synthetic_candidate():
    return {"rule_candidate_id":"R","functional_core_id":"F","family_id":"X","source_rule_content_sha256":"0"*64,"ast_operator":"ALL_OF","functional_core_classification_counts":{"INVARIANT":2},"evaluation":{"counterexample_count":0},"clauses":[{"operator":"MEASUREMENT_COMPARISON","comparison":"EQUALS","feature_key":"ordered_development[0].position","value":"0","legacy_classification":"INVARIANT","legacy_count":1,"legacy_frequency":"1"},{"operator":"MEASUREMENT_COMPARISON","comparison":"EQUALS","feature_key":"assurance.binding_sha256","value":"abc","legacy_classification":"INVARIANT","legacy_count":1,"legacy_frequency":"1"}]}

class CandidateMigrationTests(unittest.TestCase):
    def test_domain_adapter_excludes_identity_and_computability_from_structure(self):
        self.assertEqual("PROVENANCE",classify_legacy_feature("assurance.binding_sha256")); self.assertEqual("CONTEXT",classify_legacy_feature("context_ids[1]")); self.assertEqual("PROVENANCE",classify_legacy_feature("object_ids[4]")); self.assertEqual("COMPUTABILITY",classify_legacy_feature("ordered_development[2].availability")); self.assertEqual("TEMPORAL",classify_legacy_feature("ordered_development[2].position")); self.assertEqual("STRUCTURAL",classify_legacy_feature("ordered_development[2].close_vs_open"))

    def test_clause_order_does_not_change_migration_identity_or_mapping_hash(self):
        first=synthetic_candidate(); second=copy.deepcopy(first); second["clauses"].reverse(); a=migrate_candidate(first); b=migrate_candidate(second); self.assertEqual(a.migration_id,b.migration_id); self.assertEqual(a.source_clause_inventory_sha256,b.source_clause_inventory_sha256); self.assertEqual(a.typed_mapping_sha256,b.typed_mapping_sha256)

    def test_committed_ledger_accounts_for_all_fourteen_without_promotion(self):
        ledger=load(LEDGER); features=load(FEATURES); dictionary=features["feature_dictionary"]; keys=sorted(dictionary)
        self.assertEqual(14,ledger["candidate_count"]); self.assertEqual(14,len(ledger["migration_records"])); self.assertEqual({"MAPPED":14},ledger["migration_status_counts"]); self.assertEqual({"COMPUTABILITY":172,"CONTEXT":45,"PROVENANCE":140,"STRUCTURAL":228,"TEMPORAL":74},ledger["domain_totals"]); self.assertEqual({"COMMON":122,"INVARIANT":537},ledger["selected_clause_classification_totals"]); self.assertEqual(30954,ledger["legacy_core_classification_totals"]["CONTRADICTORY"]); self.assertFalse(ledger["canonical"]); self.assertEqual("NONE",ledger["promotion_authority"]); self.assertFalse(features["canonical"]); self.assertEqual("NONE",features["promotion_authority"]); self.assertEqual(features["registry_sha256"],ledger["feature_registry_sha256"]); self.assertEqual("NOT_EVALUATED_IN_WP7",ledger["migration_policy"]["exact_empirical_parity"]); self.assertEqual("DIAGNOSTIC_ONLY_PROVENANCE",ledger["migration_policy"]["provenance_structural_usage"])
        seen=set()
        for ref in ledger["migration_records"]:
            path=ROOT/ref["path"]; item=load(path); self.assertEqual(ref["record_sha256"],canon_hash(item)); self.assertEqual(ref["rule_candidate_id"],item["rule_candidate_id"]); self.assertEqual(ref["migration_id"],item["migration_id"]); self.assertEqual("MAPPED",item["migration_status"]); self.assertNotIn(item["rule_candidate_id"],seen); seen.add(item["rule_candidate_id"]); self.assertRegex(item["source_clause_inventory_sha256"],r"^[0-9a-f]{64}$"); self.assertRegex(item["typed_mapping_sha256"],r"^[0-9a-f]{64}$"); self.assertGreaterEqual(item["evaluation"]["counterexample_count"],0)
            for domain,indices in item["typed_feature_indices_by_domain"].items():
                self.assertEqual(len(indices),item["domain_counts"][domain])
                for index in indices: self.assertEqual(domain,dictionary[keys[index]][0])
        self.assertEqual(14,len(seen))

    def test_source_artifact_bindings_are_frozen(self):
        source=load(LEDGER)["source_artifacts"]; self.assertEqual("6228282d2fc19542877e12add9d922040eac49ed345488e2dd33cedcf3cb4944",source["cear_g10_disposition_evidence"]["raw_sha256"]); self.assertEqual("db9966224abd75619971bbdbff40e078e955ee5b933fa82416ceab2048521230",source["rule_candidates"]["raw_sha256"]); self.assertEqual("77f9ee2a58d5d8b9fcf0eb43cf20a9cef4c69ba8c2fe8750a6a04d123a2f1bae",source["functional_cores"]["raw_sha256"])

    def test_invalid_source_operator_and_duplicate_clause_fail_closed(self):
        wrong=synthetic_candidate(); wrong["ast_operator"]="ANY_OF"
        with self.assertRaises(ValueError): migrate_candidate(wrong)
        duplicate=synthetic_candidate(); duplicate["clauses"].append(copy.deepcopy(duplicate["clauses"][0]))
        with self.assertRaises(ValueError): migrate_candidate(duplicate)

if __name__=="__main__": unittest.main()
