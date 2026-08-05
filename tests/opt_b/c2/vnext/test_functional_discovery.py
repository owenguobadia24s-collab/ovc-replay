from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.functional_discovery import (
    AUTHORITY,
    FunctionalDiscoveryError,
    build_fingerprint_inventory,
    build_legacy_benchmark_comparison,
    build_matched_controls,
    build_opportunity_population,
    build_provisional_families,
    build_synthetic_discovery_bundle,
    compile_rule_candidate,
    evaluate_rule_candidate,
    extract_functional_cores,
    extract_motifs,
    fingerprint_opportunity,
    validate_discovery_view,
    validate_rule_ast,
)

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2/vnext/C2_FUNCTIONAL_DISCOVERY_SYNTHETIC_FIXTURE_v0_1.json"
REGISTRY = ROOT / "registries/opt_b/c2/vnext/C2_FUNCTIONAL_DISCOVERY_METHOD_CANDIDATE_v0_1.jsonc"
SCHEMA = ROOT / "schemas/opt_b/c2/vnext/C2_FUNCTIONAL_DISCOVERY_SCHEMA_BUNDLE_vNext_r1.json"
CONTRACT = ROOT / "contracts/opt_b/c2/C2_FUNCTIONAL_DISCOVERY_AND_RULE_CANDIDATE_CONTRACT_vNext.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FunctionalDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load(FIXTURE)
        cls.view = cls.fixture["discovery_view"]
        cls.method = cls.fixture["method_pack"]

    def population(self) -> dict:
        return build_opportunity_population(
            self.fixture["requests"],
            self.view,
            registered_scope_id=self.fixture["registered_scope_id"],
            input_manifest_sha256=self.fixture["input_manifest_sha256"],
        )

    def test_discovery_view_is_inactive_closed_and_prohibition_complete(self) -> None:
        view = validate_discovery_view(self.view)
        self.assertFalse(view["active"])
        self.assertFalse(view["canonical"])
        self.assertEqual(AUTHORITY, view["authority"])
        self.assertEqual("CANDIDATE_METHOD_NOT_ADMITTED_PENDING_CEAR_G10", view["method_status"])
        self.assertIn("outcome", view["prohibited_input_fields"])
        self.assertIn("validation", view["prohibited_input_fields"])
        self.assertIn("legacy_trigger", view["prohibited_input_fields"])
        self.assertIn("candidatewindow", view["prohibited_input_fields"])
        self.assertNotIn("outcome", view["permitted_input_fields"])

    def test_complete_opportunity_population_has_one_outcome_per_request(self) -> None:
        population = self.population()
        expected = self.fixture["expected"]
        self.assertEqual(expected["requested_count"], population["requested_count"])
        self.assertEqual(expected["requested_count"], population["record_count"])
        self.assertTrue(population["complete_accounting"])
        self.assertEqual(expected["computable_count"], population["outcome_counts"]["COMPUTABLE"])
        self.assertEqual(expected["not_applicable_count"], population["outcome_counts"]["NOT_APPLICABLE"])
        self.assertEqual(expected["not_evaluable_count"], population["outcome_counts"]["NOT_EVALUABLE"])
        self.assertEqual(expected["censored_count"], population["outcome_counts"]["CENSORED"])
        self.assertEqual(expected["conflict_count"], population["outcome_counts"]["CONFLICT"])
        self.assertEqual(expected["policy_unresolved_count"], population["outcome_counts"]["POLICY_UNRESOLVED"])
        self.assertEqual(expected["authority_blocked_count"], population["outcome_counts"]["AUTHORITY_BLOCKED"])
        self.assertEqual(0, population["legacy_seed_count"])
        self.assertEqual(0, population["outcome_dependency_count"])
        self.assertEqual(len(population["records"]), len({item["source_unit_id"] for item in population["records"]}))
        self.assertTrue(all(item["active"] is False and item["canonical"] is False for item in population["records"]))

    def test_duplicate_or_unregistered_opportunity_fails_closed(self) -> None:
        duplicate = [copy.deepcopy(self.fixture["requests"][0]), copy.deepcopy(self.fixture["requests"][0])]
        with self.assertRaisesRegex(FunctionalDiscoveryError, "DUPLICATE_SOURCE_UNIT_ID"):
            build_opportunity_population(
                duplicate,
                self.view,
                registered_scope_id="S",
                input_manifest_sha256="0" * 64,
            )
        invalid = copy.deepcopy(self.fixture["requests"][0])
        invalid["side"] = "MID"
        with self.assertRaisesRegex(FunctionalDiscoveryError, "OPPORTUNITY_SIDE_NOT_ADMITTED"):
            build_opportunity_population(
                [invalid],
                self.view,
                registered_scope_id="S",
                input_manifest_sha256="0" * 64,
            )

    def test_outcome_validation_profitability_and_legacy_seed_fields_are_technically_blocked(self) -> None:
        for forbidden_field in ("outcome", "validation", "profitability", "legacy_trigger", "candidate_window"):
            request = copy.deepcopy(self.fixture["requests"][0])
            request[forbidden_field] = "FORBIDDEN"
            with self.assertRaisesRegex(FunctionalDiscoveryError, "PROHIBITED_DISCOVERY_FIELD"):
                build_opportunity_population(
                    [request],
                    self.view,
                    registered_scope_id="S",
                    input_manifest_sha256="0" * 64,
                )

    def test_fingerprints_are_neutral_complete_and_deterministic(self) -> None:
        population = self.population()
        inventory = build_fingerprint_inventory(population, self.method)
        again = build_fingerprint_inventory(copy.deepcopy(population), copy.deepcopy(self.method))
        self.assertEqual(inventory, again)
        self.assertEqual(self.fixture["expected"]["fingerprint_count"], inventory["fingerprint_count"])
        self.assertTrue(inventory["complete_accounting"])
        prohibited_fragments = ("outcome", "profit", "validation", "legacy", "candidatewindow")
        for fingerprint in inventory["fingerprints"]:
            joined = " ".join(fingerprint["tokens"]).lower()
            self.assertFalse(any(fragment in joined for fragment in prohibited_fragments))
            self.assertEqual(AUTHORITY, fingerprint["authority"])
            self.assertFalse(fingerprint["active"])
            self.assertFalse(fingerprint["canonical"])

    def test_noncomputable_opportunity_cannot_be_fingerprinted(self) -> None:
        population = self.population()
        item = next(value for value in population["records"] if value["opportunity_outcome"] == "CENSORED")
        with self.assertRaisesRegex(FunctionalDiscoveryError, "FINGERPRINT_REQUIRES_COMPUTABLE_OPPORTUNITY"):
            fingerprint_opportunity(item, self.method)

    def test_motifs_retain_supported_groups_and_negative_singletons(self) -> None:
        population = self.population()
        fingerprints = build_fingerprint_inventory(population, self.method)
        motifs = extract_motifs(fingerprints, self.method)
        expected = self.fixture["expected"]
        self.assertEqual(expected["retained_motif_count"], len(motifs["motifs"]))
        self.assertEqual(expected["insufficient_support_negative_count"], len(motifs["negative_candidates"]))
        self.assertTrue(motifs["complete_accounting"])
        self.assertEqual(fingerprints["fingerprint_count"], motifs["accounted_member_count"])
        self.assertTrue(all(item["provisional"] for item in motifs["motifs"]))
        self.assertTrue(all(item["semantic_authority"] == "NONE" for item in motifs["motifs"]))
        self.assertTrue(all(item["medoid_selection_rule"] == "LEXICOGRAPHIC_FIRST_WITHIN_EXACT_SIGNATURE" for item in motifs["motifs"]))

    def test_provisional_families_are_complete_deterministic_and_semantically_neutral(self) -> None:
        population = self.population()
        fingerprints = build_fingerprint_inventory(population, self.method)
        motifs = extract_motifs(fingerprints, self.method)
        families = build_provisional_families(motifs, self.method)
        again = build_provisional_families(copy.deepcopy(motifs), copy.deepcopy(self.method))
        self.assertEqual(families, again)
        self.assertEqual(self.fixture["expected"]["provisional_family_count"], len(families["families"]))
        self.assertTrue(families["complete_accounting"])
        self.assertEqual(families["motif_count"], families["assigned_motif_count"])
        self.assertTrue(all(item["semantic_authority"] == "NONE" for item in families["families"]))
        self.assertTrue(all(item["assignment_order"] == "LEXICOGRAPHIC_MEDOID_THEN_THRESHOLD" for item in families["families"]))

    def test_functional_core_matrix_uses_exact_five_class_vocabulary(self) -> None:
        population = self.population()
        fingerprints = build_fingerprint_inventory(population, self.method)
        motifs = extract_motifs(fingerprints, self.method)
        families = build_provisional_families(motifs, self.method)
        cores = extract_functional_cores(families, motifs, fingerprints, self.method)
        self.assertEqual(self.fixture["expected"]["functional_core_count"], cores["functional_core_count"])
        self.assertTrue(cores["complete_accounting"])
        allowed = {"INVARIANT", "COMMON", "OPTIONAL", "RARE", "CONTRADICTORY"}
        for core in cores["functional_cores"]:
            self.assertIsNone(core["semantic_name"])
            self.assertTrue(core["provisional"])
            self.assertGreater(core["member_count"], 0)
            self.assertTrue({item["classification"] for item in core["component_matrix"]}.issubset(allowed))
            self.assertIn("INVARIANT", core["classification_counts"])

    def test_rules_compile_only_from_functional_cores_into_restricted_ast(self) -> None:
        population = self.population()
        fingerprints = build_fingerprint_inventory(population, self.method)
        motifs = extract_motifs(fingerprints, self.method)
        families = build_provisional_families(motifs, self.method)
        cores = extract_functional_cores(families, motifs, fingerprints, self.method)
        candidates = [compile_rule_candidate(item, self.method) for item in cores["functional_cores"]]
        self.assertEqual(self.fixture["expected"]["rule_candidate_count"], len(candidates))
        for candidate in candidates:
            validate_rule_ast(candidate["ast"])
            self.assertEqual("ALL_OF", candidate["ast"]["operator"])
            self.assertTrue(all(item["operator"] == "MEASUREMENT_COMPARISON" for item in candidate["ast"]["clauses"]))
            self.assertEqual("NONE", candidate["selector_authority"])
            self.assertEqual("NONE", candidate["event_authority"])
            self.assertEqual("NONE", candidate["episode_authority"])
            self.assertEqual("NONE", candidate["semantic_authority"])
            self.assertEqual("NONE", candidate["outcome_authority"])
            self.assertFalse(candidate["active"])
            self.assertFalse(candidate["canonical"])

    def test_rule_ast_rejects_unknown_or_prohibited_operators_and_fields(self) -> None:
        with self.assertRaisesRegex(FunctionalDiscoveryError, "RULE_AST_OPERATOR_NOT_ALLOWED"):
            validate_rule_ast({"operator": "BEST_MATCH", "clauses": []})
        with self.assertRaisesRegex(FunctionalDiscoveryError, "PROHIBITED_DISCOVERY_FIELD"):
            validate_rule_ast({
                "operator": "MEASUREMENT_COMPARISON",
                "feature_key": "x",
                "comparison": "EQUALS",
                "value": "y",
                "outcome": "UP",
            })

    def test_rule_evaluation_accounts_for_complete_population_and_all_negative_outcomes(self) -> None:
        bundle = build_synthetic_discovery_bundle(
            self.fixture["requests"],
            self.view,
            self.method,
            registered_scope_id=self.fixture["registered_scope_id"],
            input_manifest_sha256=self.fixture["input_manifest_sha256"],
        )
        self.assertEqual(self.fixture["expected"]["rule_candidate_count"], len(bundle["rule_candidates"]))
        for evaluation in bundle["rule_evaluations"]:
            self.assertTrue(evaluation["complete_accounting"])
            self.assertEqual(self.fixture["expected"]["requested_count"], evaluation["result_count"])
            self.assertEqual(1, evaluation["outcome_counts"]["NOT_APPLICABLE"])
            self.assertEqual(1, evaluation["outcome_counts"]["NOT_EVALUABLE"])
            self.assertEqual(1, evaluation["outcome_counts"]["CENSORED"])
            self.assertEqual(1, evaluation["outcome_counts"]["CONFLICT"])
            self.assertEqual(1, evaluation["outcome_counts"]["POLICY_UNRESOLVED"])
            self.assertEqual(1, evaluation["outcome_counts"]["AUTHORITY_BLOCKED"])
            self.assertEqual(
                evaluation,
                evaluate_rule_candidate(
                    next(item for item in bundle["rule_candidates"] if item["rule_candidate_id"] == evaluation["rule_candidate_id"]),
                    bundle["population"],
                    bundle["fingerprint_inventory"],
                ),
            )

    def test_matched_controls_use_exact_strata_and_duration_bins_without_nearest_fallback(self) -> None:
        bundle = build_synthetic_discovery_bundle(
            self.fixture["requests"],
            self.view,
            self.method,
            registered_scope_id=self.fixture["registered_scope_id"],
            input_manifest_sha256=self.fixture["input_manifest_sha256"],
        )
        self.assertEqual(2, len(bundle["matched_control_sets"]))
        self.assertEqual(self.fixture["expected"]["matched_control_count"], sum(item["matched_count"] for item in bundle["matched_control_sets"]))
        self.assertEqual(self.fixture["expected"]["unmatched_control_count"], sum(item["unmatched_count"] for item in bundle["matched_control_sets"]))
        for controls in bundle["matched_control_sets"]:
            self.assertFalse(controls["hidden_nearest_or_best_selection"])
            self.assertTrue(all(item["selection_rule"] == "LEXICOGRAPHIC_FIRST_WITHIN_EXACT_REGISTERED_STRATUM_AND_DURATION_BIN" for item in controls["matches"]))

        population = bundle["population"]
        one_member = [bundle["rule_candidates"][0]["source_opportunity_ids"][0]]
        no_control_population = copy.deepcopy(population)
        no_control_population["records"] = [
            item for item in population["records"] if item["opportunity_id"] in one_member or item["opportunity_outcome"] != "COMPUTABLE"
        ]
        no_control_population["record_count"] = len(no_control_population["records"])
        controls = build_matched_controls(one_member, no_control_population, duration_bin_size=2)
        self.assertEqual(0, controls["matched_count"])
        self.assertEqual(1, controls["unmatched_count"])
        self.assertEqual("NO_CONTROL_IN_EXACT_REGISTERED_STRATUM_AND_DURATION_BIN", controls["unmatched_requests"][0]["reason_code"])

    def test_legacy_benchmarks_are_post_discovery_comparators_with_zero_upstream_effect(self) -> None:
        bundle = build_synthetic_discovery_bundle(
            self.fixture["requests"],
            self.view,
            self.method,
            registered_scope_id=self.fixture["registered_scope_id"],
            input_manifest_sha256=self.fixture["input_manifest_sha256"],
        )
        benchmarks = copy.deepcopy(self.fixture["legacy_benchmark_fixture"])
        benchmarks[0]["matched_opportunity_ids"] = [
            item["opportunity_id"]
            for item in bundle["population"]["records"]
            if item["source_unit_id"] in {"A-001", "A-002"}
        ]
        comparison = build_legacy_benchmark_comparison(bundle["rule_evaluations"], benchmarks)
        self.assertEqual(2, comparison["legacy_rule_count"])
        self.assertEqual(2, comparison["candidate_rule_count"])
        self.assertEqual(0, comparison["legacy_seed_count"])
        self.assertEqual(0, comparison["legacy_filter_count"])
        self.assertEqual(0, comparison["legacy_score_count"])
        self.assertEqual(0, comparison["legacy_stop_count"])
        self.assertEqual(0, comparison["legacy_promotion_count"])
        self.assertTrue(all(item["benchmark_only"] for item in comparison["mappings"]))
        self.assertTrue(all(item["operator_disposition"] is None for item in comparison["mappings"]))
        invalid = copy.deepcopy(benchmarks)
        invalid[0]["benchmark_only"] = False
        with self.assertRaisesRegex(FunctionalDiscoveryError, "LEGACY_RULE_MUST_BE_BENCHMARK_ONLY"):
            build_legacy_benchmark_comparison(bundle["rule_evaluations"], invalid)

    def test_two_clean_synthetic_runs_are_logically_identical_but_not_gate_eligible(self) -> None:
        first = build_synthetic_discovery_bundle(
            self.fixture["requests"],
            self.view,
            self.method,
            registered_scope_id=self.fixture["registered_scope_id"],
            input_manifest_sha256=self.fixture["input_manifest_sha256"],
        )
        second = build_synthetic_discovery_bundle(
            copy.deepcopy(self.fixture["requests"]),
            copy.deepcopy(self.view),
            copy.deepcopy(self.method),
            registered_scope_id=self.fixture["registered_scope_id"],
            input_manifest_sha256=self.fixture["input_manifest_sha256"],
        )
        self.assertEqual(first, second)
        self.assertTrue(first["synthetic_only"])
        self.assertFalse(first["market_population"])
        self.assertFalse(first["cear_g10_disposition_eligible"])
        self.assertFalse(first["active"])
        self.assertFalse(first["canonical"])

    def test_registry_schema_and_contract_preserve_operator_gate_and_real_population_requirement(self) -> None:
        registry = load(REGISTRY)
        schema = load(SCHEMA)
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertEqual("CANDIDATE_METHOD_NOT_ADMITTED_PENDING_CEAR_G10", registry["status"])
        self.assertFalse(registry["effective"])
        self.assertFalse(registry["active"])
        self.assertFalse(registry["canonical"])
        self.assertTrue(registry["real_population_requirement"]["required_for_cear_g10"])
        self.assertFalse(registry["real_population_requirement"]["legacy_active_c2_substitution"])
        self.assertFalse(registry["real_population_requirement"]["manifest_without_payload_substitution"])
        self.assertFalse(registry["real_population_requirement"]["synthetic_substitution"])
        self.assertEqual("PROHIBITED", registry["legacy_isolation"]["seed"])
        self.assertEqual("PROHIBITED", registry["outcome_isolation"]["validation_dependencies"])
        self.assertEqual("NONE", registry["candidate_authority"]["selector_event_episode_semantic_outcome"])
        self.assertFalse(schema["active"])
        self.assertFalse(schema["canonical"])
        self.assertIn("Synthetic fixtures prove contracts and determinism only", contract)
        self.assertIn("CEAR-G10 remains operator-required", contract)


if __name__ == "__main__":
    unittest.main()
