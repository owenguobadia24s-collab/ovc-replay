from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.orch345 import (
    PARALLEL_BUILD_CLASS,
    SERIAL_CLASS,
    analyze_repository_empirical_corpus,
    build_activation_readiness,
    build_conflict_matrix,
    build_packet_descriptor,
    build_packet_train_plan,
    build_portfolio_schedule,
    classify_packet_pair,
    resolve_orch345_authority,
)


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "docs/releases/development-skills-architecture-v0-2/dsai2-wp0/DSAI2_EMPIRICAL_REPOSITORY_CORPUS_v0_1.json"


class DsaiV02Orch345ConformanceTests(unittest.TestCase):
    def test_empirical_corpus_justifies_all_three_conformance_stages_without_self_activation(self) -> None:
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        analysis = analyze_repository_empirical_corpus(corpus["events"])

        self.assertEqual(analysis["event_count"], 28)
        self.assertEqual(analysis["distinct_pr_count"], 26)
        self.assertEqual(analysis["distinct_programme_count"], 8)
        self.assertEqual(analysis["main_head_churn_pressure_events"], 18)
        self.assertEqual(analysis["event_type_counts"]["MAIN_SYNC_RECONCILIATION"], 8)
        self.assertEqual(analysis["event_type_counts"]["STALE_BASE_SUPERSESSION"], 5)
        self.assertEqual(analysis["event_type_counts"]["GREEN_ASSURANCE_DISCARDED"], 3)
        self.assertEqual(analysis["event_type_counts"]["CROSS_PROGRAM_DEPENDENCY"], 2)
        self.assertEqual(analysis["implementation_justification"], {"orch3": True, "orch4": True, "orch5": True})
        self.assertEqual(analysis["authority_conclusion"], "JUSTIFIES_CONFORMANCE_IMPLEMENTATION_NOT_SELF_ACTIVATION")
        self.assertEqual(analysis["authority_effect"], "NONE")

    def test_orch3_packet_train_advances_auto_packets_and_stops_at_operator_boundary(self) -> None:
        p1 = build_packet_descriptor(programme_id="P", packet_id="P-WP1")
        p2 = build_packet_descriptor(programme_id="P", packet_id="P-WP2", prerequisites=["P-WP1"])
        p3 = build_packet_descriptor(
            programme_id="P",
            packet_id="P-G3",
            prerequisites=["P-WP2"],
            gate_class="OPERATOR_REQUIRED",
        )

        plan = build_packet_train_plan(programme_id="P", packets=[p3, p2, p1])

        self.assertEqual(plan["selected_packet_ids"], ["P-WP1", "P-WP2"])
        self.assertEqual(plan["operator_boundaries"], ["P-G3"])
        self.assertEqual(plan["orchestrator_stage"], "ORCH-3")
        self.assertEqual(plan["execution_mode"], "SHADOW_ONLY")
        self.assertEqual(plan["integration_policy"], "PDC_SERIAL_FINAL_INTEGRATION_WINDOW_REQUIRED")
        self.assertEqual(plan["authority_effect"], "NONE")

    def test_orch4_allows_only_disjoint_low_risk_parallel_build_and_never_parallel_merge(self) -> None:
        c2p = build_packet_descriptor(
            programme_id="C2P",
            packet_id="C2P-WP2",
            write_paths=["src/ovc/opt_b/c2p_v0_2", "tests/opt_b/c2p/v0_2"],
            semantic_owners=["C2P"],
        )
        rcn = build_packet_descriptor(
            programme_id="RCN",
            packet_id="RCN-WP5",
            write_paths=["apps/research_console", "apps/research_api"],
            semantic_owners=["RCN"],
        )
        overlapping = build_packet_descriptor(
            programme_id="C2P",
            packet_id="C2P-WP3",
            write_paths=["src/ovc/opt_b/c2p_v0_2/objects"],
            semantic_owners=["C2P"],
        )

        safe = classify_packet_pair(c2p, rcn)
        conflict = classify_packet_pair(c2p, overlapping)
        matrix = build_conflict_matrix([c2p, rcn, overlapping])

        self.assertEqual(safe["classification"], PARALLEL_BUILD_CLASS)
        self.assertFalse(safe["parallel_merge"])
        self.assertEqual(conflict["classification"], SERIAL_CLASS)
        self.assertIn("WRITE_SET_OVERLAP", conflict["reason_codes"])
        self.assertIn("SEMANTIC_OWNER_OVERLAP", conflict["reason_codes"])
        self.assertEqual(matrix["parallel_build_pair_count"], 2)
        self.assertEqual(matrix["serial_required_pair_count"], 1)
        self.assertEqual(matrix["ambiguity_policy"], "SERIAL_REQUIRED")
        self.assertFalse(matrix["parallel_merge"])

    def test_orch4_dependency_edge_forces_serial_even_when_paths_are_disjoint(self) -> None:
        upstream = build_packet_descriptor(
            programme_id="EI",
            packet_id="EI-WP1",
            write_paths=["contracts/ei"],
            semantic_owners=["EI"],
        )
        downstream = build_packet_descriptor(
            programme_id="PYT",
            packet_id="PYT-WP2",
            cross_programme_dependencies=["EI-WP1"],
            write_paths=[".github/workflows/tests.yml"],
            semantic_owners=["TEST_INFRA"],
        )

        result = classify_packet_pair(upstream, downstream)

        self.assertEqual(result["classification"], SERIAL_CLASS)
        self.assertIn("ORDERED_DEPENDENCY", result["reason_codes"])

    def test_orch5_selects_independent_work_while_conflicting_and_operator_packets_wait(self) -> None:
        c2p = build_packet_descriptor(
            programme_id="C2P",
            packet_id="C2P-WP2",
            write_paths=["src/ovc/opt_b/c2p_v0_2"],
            semantic_owners=["C2P"],
            priority=10,
        )
        c2p_conflict = build_packet_descriptor(
            programme_id="C2P",
            packet_id="C2P-WP3",
            write_paths=["src/ovc/opt_b/c2p_v0_2/objects"],
            semantic_owners=["C2P"],
            priority=15,
        )
        rcn = build_packet_descriptor(
            programme_id="RCN",
            packet_id="RCN-WP5",
            write_paths=["apps/research_console"],
            semantic_owners=["RCN"],
            priority=20,
        )
        operator_gate = build_packet_descriptor(
            programme_id="RCN",
            packet_id="RCN-G4",
            gate_class="OPERATOR_REQUIRED",
            write_paths=[],
            semantic_owners=["RCN"],
            priority=5,
        )

        schedule = build_portfolio_schedule(
            packets=[c2p_conflict, operator_gate, rcn, c2p],
            max_parallel=2,
        )

        self.assertEqual(schedule["selected_packet_ids"], ["C2P-WP2", "RCN-WP5"])
        self.assertEqual(schedule["operator_wait"], ["RCN-G4"])
        self.assertEqual(schedule["waiting"][0]["packet_id"], "C2P-WP3")
        self.assertEqual(schedule["waiting"][0]["reason"], "SERIAL_FALLBACK")
        self.assertEqual(schedule["integration_policy"], "PDC_SERIAL_FINAL_INTEGRATION_WINDOW_REQUIRED")
        self.assertFalse(schedule["parallel_merge"])
        self.assertEqual(schedule["dispatch_authority"], "NONE")

    def test_activation_readiness_can_recommend_gate_ready_but_cannot_activate(self) -> None:
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        analysis = analyze_repository_empirical_corpus(corpus["events"])

        readiness = build_activation_readiness(
            corpus_analysis=analysis,
            conflict_detector_qualified=True,
            portfolio_scheduler_qualified=True,
            pdc_terminal_state="COMPLETED / PARALLEL_BUILD_SERIALIZED_FINAL_INTEGRATION_WINDOW_ACTIVE",
            unresolved_s3_s4=0,
        )

        self.assertEqual(readiness["status"], "GATE_READY_OPERATOR_REQUIRED")
        self.assertFalse(readiness["activation_performed"])
        self.assertTrue(readiness["self_grant_prohibited"])
        self.assertEqual(readiness["proposed_authority_delta"]["operator_required_gate"], "DSAI2-G3")
        self.assertEqual(readiness["authority_effect"], "NONE")

    def test_future_authority_resolver_fails_closed_until_exact_operator_record_is_on_main(self) -> None:
        candidate = {
            "schema": "ovc-dsai-orch345-authority/v1",
            "programme_id": "OVC-DSAI-v0.2",
            "plan_id": "OVC-DSAI-ORCH345-IMPLEMENTATION-PLAN-0.2",
            "gate_id": "DSAI2-G3",
            "approved": True,
            "effective": True,
            "enabled_orchestrators": ["ORCH-3", "ORCH-4", "ORCH-5"],
            "enabled_packet_classes": ["LOW_RISK_IMPLEMENTATION"],
            "modes": {
                "ORCH-3": "SERIAL_PACKET_TRAIN",
                "ORCH-4": "PARALLEL_BUILD_SERIAL_INTEGRATION",
                "ORCH-5": "PORTFOLIO_DISPATCH_ONLY",
            },
            "integration_policy": {
                "serialized_final_integration_window": True,
                "parallel_merge": False,
                "target_branch": "main",
                "merge_method": "squash",
                "direct_main_mutation": False,
                "force_push": False,
                "history_rewrite": False,
            },
            "validation": "DENIED",
            "reserved_scientific_execution_authority": "NONE",
        }

        blocked = resolve_orch345_authority(authority=candidate, record_present_on_main=False)
        active = resolve_orch345_authority(authority=candidate, record_present_on_main=True)

        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("AUTHORITY_RECORD_NOT_PRESENT_ON_MAIN", blocked["reason_codes"])
        self.assertEqual(active["status"], "ACTIVE_AUTHORIZED")
        self.assertEqual(active["authority_effect"], "READ_ONLY_RESOLUTION")


if __name__ == "__main__":
    unittest.main()
