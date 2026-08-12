from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import runpy
import unittest

ESL_TESTS = Path(__file__).resolve().parent / "opt_b" / "esl"


def _load(filename: str):
    return runpy.run_path(str(ESL_TESTS / filename))


WP1 = _load("test_esli_wp1_common_contracts.py")
WP2 = _load("test_esli_wp2_canonical_serialization.py")
WP3 = _load("test_esli_wp3_occurrence_compiler.py")
WP4 = _load("test_esli_wp4_c3_reference.py")
WP4_PERF = _load("test_esli_wp4_performance_calibration_probe.py")


class TestESLICanonicalUnittestBridge(unittest.TestCase):
    """Make every ESLI WP1-WP4 assertion visible to canonical unittest discovery."""

    def test_wp1_01_valid_partial_occurrence(self): WP1["test_valid_partial_occurrence_is_lawful"]()
    def test_wp1_02_required_missing_dependency(self): WP1["test_required_missing_dependency_fails_closed"]()
    def test_wp1_03_reverse_dependency(self): WP1["test_reverse_dependency_to_c3_fails_closed"]()
    def test_wp1_04_backdated_fvt(self): WP1["test_backdated_first_valid_time_fails"]()
    def test_wp1_05_comparability_mismatch(self): WP1["test_comparability_mismatch_fails"]()
    def test_wp1_06_nonavailable_zero_smuggling(self): WP1["test_nonavailable_facet_cannot_smuggle_zero_equivalent"]()
    def test_wp1_07_registry_schema_fixture(self): WP1["test_frozen_registries_and_schema_fixture_are_materialized"]()

    def test_wp2_01_normative_trace_bytes(self): WP2["test_five_normative_traces_are_byte_identical_across_independent_implementations"]()
    def test_wp2_02_g1_identity(self): WP2["test_ratified_g1_occurrence_identity_is_exact"]()
    def test_wp2_03_key_unicode_number_normalization(self): WP2["test_object_key_order_whitespace_unicode_and_number_normalization"]()
    def test_wp2_04_nonfinite_negative_zero(self):
        for value in (-0.0, Decimal("-0"), float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=repr(value)): WP2["test_nonfinite_and_negative_zero_fail_closed"](value)
    def test_wp2_05_null_empty_omission(self): WP2["test_null_empty_and_omission_have_distinct_identity"]()
    def test_wp2_06_schema_array_order(self): WP2["test_schema_declared_arrays_are_deterministically_ordered"]()
    def test_wp2_07_identity_projection(self): WP2["test_identity_projection_excludes_only_own_top_level_id_and_hash"]()
    def test_wp2_08_frontier_hash(self): WP2["test_evidence_frontier_uses_same_hash_discipline"]()
    def test_wp2_09_independent_reference(self): WP2["test_reference_implementation_does_not_import_production_serializer"]()
    def test_wp2_10_adversarial_catalogues(self): WP2["test_adversarial_catalogues_are_complete_and_permanently_routed"]()
    def test_wp2_11_serialization_registry(self): WP2["test_serialization_registry_is_frozen_and_matches_contract"]()

    def test_wp3_01_field_missingness(self): WP3["test_bootstrap_reference_compiler_preserves_field_level_missingness"]()
    def test_wp3_02_reordering_determinism(self): WP3["test_compiler_is_deterministic_under_profile_input_reordering"]()
    def test_wp3_03_optional_c2e(self): WP3["test_optional_missing_c2e_does_not_invalidate_base_occurrence"]()
    def test_wp3_04_ineligible_c2(self): WP3["test_ineligible_required_c2_observation_fails_closed"]()
    def test_wp3_05_hindsight_quality(self): WP3["test_hindsight_and_global_quality_inputs_fail_closed"]()
    def test_wp3_06_after_cutoff(self): WP3["test_profile_after_cutoff_fails_closed"]()
    def test_wp3_07_axis_absence(self): WP3["test_all_axis_absence_is_explicit_not_zero_or_synthetic_family"]()
    def test_wp3_08_measurement_authority(self): WP3["test_reference_measurement_has_no_budget_or_scientific_authority"]()
    def test_wp3_09_bootstrap_pack(self): WP3["test_bootstrap_pack_is_exact_and_family_independent"]()

    def test_wp4_01_normative_renderings(self): WP4["test_all_five_ratified_normative_renderings_are_reproduced"]()
    def test_wp4_02_vertical_determinism(self): WP4["test_base_vertical_reference_path_is_deterministic_and_source_immutable"]()
    def test_wp4_03_optional_enrichments(self): WP4["test_family_organisation_constraint_are_optional_and_do_not_invalidate_base_statement"]()
    def test_wp4_04_maturity_fail_closed(self): WP4["test_shadow_and_production_maturity_fail_closed_without_activation_record"]()
    def test_wp4_05_activation_registry(self): WP4["test_activation_registry_is_empty_and_maturity_registry_is_reference_only"]()
    def test_wp4_06_explanation_sidecar(self): WP4["test_llm_explanation_is_separate_noncanonical_sidecar"]()
    def test_wp4_07_performance_calibration_probe(self): WP4_PERF["test_wp4_reference_performance_calibration_probe"]()
