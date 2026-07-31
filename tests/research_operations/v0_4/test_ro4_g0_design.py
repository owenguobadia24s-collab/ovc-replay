from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class RO4G0DesignTests(unittest.TestCase):
    def setUp(self) -> None:
        path = ROOT / "scripts" / "research_operations" / "validate_ro4_g0_design.py"
        spec = importlib.util.spec_from_file_location("validate_ro4_g0_design", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.validator = module

    def test_design_validator_passes(self) -> None:
        self.assertEqual(self.validator.main(), 0)

    def test_programme_stops_at_operator_gate(self) -> None:
        state = json.loads(
            (ROOT / "registries/research_operations/v0_4/RO4_PROGRAMME_STATE_v0_1.json").read_text()
        )
        self.assertEqual(state["programme_status"], "GATE_READY")
        self.assertEqual(state["current_gate"], "RO4-G0")
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual(state["packets"][0]["authority_required"], "OPERATOR_REQUIRED")
        self.assertEqual(state["packets"][1]["status"], "PLANNED")
        self.assertIn("C2E_EPISODE_AUTHORITY", state["retained_prohibitions"])

    def test_signature_diversity_is_frozen_and_count_only(self) -> None:
        policy = (
            ROOT
            / "registries/research_operations/v0_4/RO4_SIGNATURE_DIVERSITY_POLICY_v0_1.yaml"
        ).read_text()
        self.assertIn("minimum_candidate_count_for_pass: 100", policy)
        self.assertIn("normalized_shannon_entropy_warning_below: '0.55'", policy)
        self.assertIn("top_1_warning_above_share: '0.12'", policy)
        self.assertIn("top_5_warning_above_share: '0.30'", policy)
        self.assertIn("top_10_warning_above_share: '0.45'", policy)
        self.assertIn("operator_batch_signature_cap_share: '0.20'", policy)
        self.assertIn("derived_share_values: DENIED", policy)
        schema = json.loads(
            (
                ROOT
                / "schemas/research_operations/v0_4/signature_diversity_audit_v0_1.schema.json"
            ).read_text()
        )
        self.assertIn("SIGNATURE_CONCENTRATION_WARNING", schema["properties"]["status"]["enum"])
        self.assertEqual(schema["properties"]["review_batch_signature_cap"]["const"], 0.2)

    def test_pattern_discovery_is_trace_only(self) -> None:
        policy = (
            ROOT / "registries/research_operations/v0_4/RO4_PD_TRACE_ALLOWLIST_v0_1.yaml"
        ).read_text()
        for allowed in ("pd_trigger_id", "pd_run_id", "trigger_first_valid_at", "trace_authority"):
            self.assertIn(allowed, policy)
        for denied in ("fingerprint", "novelty", "medoid", "cluster", "answer_key", "promotion"):
            self.assertIn(denied, policy)
        self.assertIn("joint_review_batch: DENIED", policy)
        self.assertIn("ro4_to_pd_evidence_bridge: DENIED", policy)
        schema = json.loads(
            (
                ROOT
                / "schemas/research_operations/v0_4/pd_trigger_trace_ref_v0_1.schema.json"
            ).read_text()
        )
        denied_fields = {item["required"][0] for item in schema["not"]["anyOf"]}
        self.assertIn("pd_candidate_id", denied_fields)
        self.assertIn("fingerprint", denied_fields)
        self.assertIn("promotion", denied_fields)

    def test_axis_ablation_cannot_reach_operator_surface(self) -> None:
        policy = (
            ROOT
            / "registries/research_operations/v0_4/RO4_AXIS_ABLATION_ASSURANCE_POLICY_v0_1.yaml"
        ).read_text()
        self.assertIn("artifact_class: MACHINE_QA_ONLY", policy)
        self.assertIn("operator_facing_schemas: DENY", policy)
        self.assertIn("blinded_review_batches: DENY", policy)
        self.assertIn("importance_language: PROHIBITED", policy)
        projection = json.loads(
            (
                ROOT
                / "schemas/research_operations/v0_4/ro4_console_projection_v0_1.schema.json"
            ).read_text()
        )
        denied = {item["required"][0] for item in projection["not"]["anyOf"]}
        self.assertIn("synthetic_control", denied)

    def test_performance_and_sample_contract_is_explicit(self) -> None:
        policy = (
            ROOT
            / "registries/research_operations/v0_4/RO4_PERFORMANCE_AND_SAMPLE_POLICY_v0_1.yaml"
        ).read_text()
        self.assertIn("full_discovery_index_seconds: 600", policy)
        self.assertIn("peak_rss_bytes: 8589934592", policy)
        self.assertIn("window_cardinality_cap_per_role_clock_side_calendar_partition: 100000", policy)
        self.assertIn("selection: LOWEST_HASH_WITHIN_FROZEN_STRATA", policy)
        self.assertIn("silent_substitution: PROHIBITED", policy)
        schema = json.loads(
            (
                ROOT
                / "schemas/research_operations/v0_4/declared_sample_manifest_v0_1.schema.json"
            ).read_text()
        )
        self.assertEqual(schema["properties"]["banner"]["const"], "SAMPLED_NON_CANONICAL_EXPLORATORY")
        self.assertEqual(
            schema["properties"]["hash_expression"]["const"],
            "SHA256(sequence_id + sampling_policy_id + sampling_version)",
        )

    def test_operator_presentation_denies_distribution_shapes(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "schemas/research_operations/v0_4/count_denominator_cell_v0_1.schema.json"
            ).read_text()
        )
        denied = {item["required"][0] for item in schema["not"]["anyOf"]}
        self.assertTrue(
            {"percentage", "ratio", "normalized_frequency", "probability", "rank", "colour_intensity", "bar_length"}.issubset(denied)
        )
        self.assertEqual(
            schema["properties"]["display_style"]["const"],
            "UNIFORM_NON_DATA_DRIVEN_IDENTITY_ORDERED",
        )
        route = (
            ROOT / "registries/research_operations/v0_4/RO4_ROUTE_REGISTRY_v0_1.yaml"
        ).read_text()
        self.assertIn("state: DISABLED_PENDING_RC_G5", route)
        self.assertIn("writes: NONE", route)
        self.assertIn("buttons: NONE", route)

    def test_c2e_opening_only_allows_a_separate_plan(self) -> None:
        threshold = (
            ROOT
            / "registries/research_operations/v0_4/RO4_C2E_DESIGN_OPENING_THRESHOLD_v0_1.yaml"
        ).read_text()
        self.assertIn("minimum_strata: 3", threshold)
        self.assertIn("minimum_accepted_annotations: 10", threshold)
        self.assertIn("minimum_distinct_real_sequences: 5", threshold)
        self.assertIn("multi_operator_kappa_minimum: '0.70'", threshold)
        self.assertIn("minimum_counterexample_sets_where_per_bar_c2_is_sufficient: 5", threshold)
        self.assertIn("DRAFT_SEPARATE_C2E_IMPLEMENTATION_PLAN_ONLY", threshold)
        schema = json.loads(
            (
                ROOT
                / "schemas/research_operations/v0_4/c2e_design_opening_assessment_v0_1.schema.json"
            ).read_text()
        )
        self.assertEqual(
            schema["properties"]["decision_effect"]["const"],
            "DRAFT_SEPARATE_PLAN_ONLY_NO_C2E_AUTHORITY",
        )
        denied = {item["required"][0] for item in schema["not"]["anyOf"]}
        self.assertIn("episode_records", denied)
        self.assertIn("selector_change", denied)
        self.assertIn("activation", denied)

    def test_gate_packet_is_operator_owned_and_unapproved(self) -> None:
        gate = json.loads(
            (
                ROOT
                / "docs/releases/research-operations-foundation-v0-4/ro4-g0/RO4_G0_GATE_PACKET.json"
            ).read_text()
        )
        self.assertEqual(gate["status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertEqual(gate["candidate_commit"], None)
        self.assertEqual(gate["next_packet"], "RO4-WP1")
        self.assertIn("OPERATOR_DECISION_RO4_G0_REQUIRED", gate["unresolved_issues"])
        self.assertEqual(
            set(gate["allowed_decisions"]),
            {"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"},
        )


if __name__ == "__main__":
    unittest.main()
