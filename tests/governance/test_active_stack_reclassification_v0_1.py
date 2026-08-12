from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.active_stack import ActiveStackError, classification, load_active_stack, require_new_evidence_route
from ovc.programme_genesis.migration import discover_programme_state_paths


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "registries/governance/active_stack/OVC_ACTIVE_STACK_STATE_v0_1.json"
POINTER_PATH = ROOT / "registries/governance/active_stack/CURRENT_ACTIVE_STACK_POINTER.json"
PRE_CI_STATE_CANDIDATE = ROOT / "registries/governance/active_stack/PROGRAMME_STATE_v0_1.json"
C1_SELECTORS = ROOT / "registries/opt_b/c1/C1_ACTIVE_SELECTORS.yaml"
C2_HISTORICAL_SELECTORS = ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml"
C2_VNEXT_AUTH = ROOT / "registries/opt_b/c2/vnext/C2_VNEXT_ACTIVE_RUNTIME_AUTHORITY_v0_1.json"
C2_VNEXT_PACKAGE = ROOT / "registries/opt_b/c2/vnext/C2_INTEGRATED_SHADOW_PACKAGE_APPROVED_v1.jsonc"
C2_LEGACY = ROOT / "registries/opt_b/c2/C2_V2_LEGACY_SUPERSESSION_v0_1.json"
C2E_AUTH = ROOT / "registries/authority/C2E_ACTIVE_ENGINE_AUTHORITY_v0_1.json"
OC_AUTH = ROOT / "registries/implementation/occurrence_context/OCCURRENCE_CONTEXT_ACTIVE_FOUNDATION_AUTHORITY_v0_1.json"
RO_AUTH = ROOT / "registries/research_operations/ACTIVE_FOUNDATION_AUTHORITY_v0_1.json"
OPERATOR_DECISION = ROOT / "docs/releases/active-stack-reclassification-v0-1/asr-00/ASR_00_OPERATOR_DECISION.json"
IMPLEMENTATION_REGISTRY = ROOT / "registries/implementation/IMPLEMENTATION_REGISTRY.yaml"


class ActiveStackReclassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    def test_pointer_resolves_exact_current_state(self) -> None:
        pointer = json.loads(POINTER_PATH.read_text(encoding="utf-8"))
        self.assertEqual(pointer["programme_id"], "OVC-ACTIVE-STACK-RECLASSIFICATION-v0.1")
        self.assertEqual(
            pointer["authoritative_state"],
            "registries/governance/active_stack/OVC_ACTIVE_STACK_STATE_v0_1.json",
        )
        resolved = load_active_stack(ROOT)
        self.assertEqual(
            resolved["active_spine"],
            ["OPT-A", "OPT-B.C1.v2", "OPT-B.C2.vNext", "OPT-B.C2E.v0.2"],
        )

    def test_machine_programme_state_fields_are_materialised_in_canonical_state(self) -> None:
        for field in (
            "packet_id", "prerequisites", "authority_required", "authority_delta", "baseline_commit",
            "branch", "candidate_commit", "tests", "qa_packet", "decision_record", "merge_commit",
            "blockers", "next_packet", "gate",
        ):
            self.assertIn(field, self.state)
        self.assertEqual(self.state["packet_id"], "ASR-WP1")
        self.assertEqual(self.state["gate"]["gate_id"], "ASR-G1")
        self.assertTrue(self.state["gate"]["auto_ratifiable"])

    def test_post_snapshot_asr_does_not_mutate_frozen_pg_pgn_migration_population(self) -> None:
        candidate = json.loads(PRE_CI_STATE_CANDIDATE.read_text(encoding="utf-8"))
        self.assertNotIn("programme_id", candidate)
        self.assertEqual(candidate["authority_effect"], "NONE")
        self.assertEqual(candidate["status"], "SUPERSEDED_PRE_CI_CANDIDATE")
        discovered = discover_programme_state_paths(ROOT)
        discovered_documents = [json.loads(path.read_text(encoding="utf-8")) for path in discovered]
        discovered_ids = {doc["programme_id"] for doc in discovered_documents}
        self.assertNotIn("OVC-ACTIVE-STACK-RECLASSIFICATION-v0.1", discovered_ids)

    def test_operator_decision_is_exact_and_reserved_delta_is_materialised(self) -> None:
        decision = json.loads(OPERATOR_DECISION.read_text(encoding="utf-8"))
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["decision_authority"], "OPERATOR")
        self.assertEqual(decision["operator_command"], "OVC APPROVE OVC ACTIVE STACK RECLASSIFICATION v0.1")
        approved = decision["approved_authority_delta"]
        self.assertEqual(
            approved["legacy_c2_v2"],
            "RETIRE_FROM_NEW_EVIDENCE_RUNTIME_AND_CLASSIFY_LEGACY_INACTIVE",
        )
        self.assertEqual(
            approved["c2_vnext_core"],
            "ACTIVATE_EXACT_NINE_COMPONENT_CORE_DISCOVERY_AND_DEVELOPMENT",
        )
        self.assertIn("REMOVE_EXACT_JUNE_POPULATION_RUN_DATE_SCOPE_BINDING", approved["c2e_v0_2"])

    def test_c1_v2_remains_active_and_validation_locked(self) -> None:
        text = C1_SELECTORS.read_text(encoding="utf-8")
        self.assertIn("OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2", text)
        self.assertIn("OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2", text)
        self.assertIn("active_activation_role: ACTIVE_DISCOVERY_AND_DEVELOPMENT", text)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", text)
        self.assertEqual(classification(self.state, "OPT-B.C1.v2"), "ACTIVE")

    def test_historical_c2_selector_record_is_preserved_but_superseded(self) -> None:
        text = C2_HISTORICAL_SELECTORS.read_text(encoding="utf-8")
        self.assertIn("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2", text)
        legacy = json.loads(C2_LEGACY.read_text(encoding="utf-8"))
        self.assertEqual(legacy["current_state"], "LEGACY_INACTIVE")
        self.assertEqual(legacy["new_evidence_runtime_import"], "DENIED")
        self.assertEqual(legacy["new_evidence_parent_eligibility"], "DENIED")
        self.assertEqual(legacy["historical_lineage_read"], "PERMITTED_READ_ONLY")
        self.assertEqual(classification(self.state, "OPT-B.C2.v2"), "LEGACY_INACTIVE")

    def test_c2_vnext_core_is_active_without_promoting_research_candidates(self) -> None:
        historical_package = json.loads(C2_VNEXT_PACKAGE.read_text(encoding="utf-8"))
        self.assertFalse(historical_package["active"])
        self.assertEqual(historical_package["status"], "IMPLEMENTED_SHADOW_COMPLETE")
        authority = json.loads(C2_VNEXT_AUTH.read_text(encoding="utf-8"))
        self.assertEqual(authority["package_id"], "C2AR.INTEGRATED.SHADOW.PACKAGE.v1")
        self.assertEqual(
            authority["package_sha256"],
            "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3",
        )
        self.assertEqual(
            authority["active_components"],
            [
                "OBSERVATION", "HORIZON", "LEVEL", "CONTAINER", "RELATION",
                "FORMULA", "TRANSITION", "PARENT_CONTEXT", "COMPUTABILITY",
            ],
        )
        self.assertEqual(
            authority["shadow_components"],
            ["FUNCTIONAL_DISCOVERY", "CANDIDATE_DISPOSITIONS"],
        )
        self.assertEqual(authority["candidate_family_rule_promotion"], "NONE")
        self.assertEqual(classification(self.state, "OPT-B.C2.vNext"), "ACTIVE")
        self.assertEqual(
            classification(self.state, "OPT-B.C2.vNext.FUNCTIONAL_DISCOVERY"),
            "SHADOW",
        )

    def test_c2e_is_active_engine_without_exact_population_or_date_binding(self) -> None:
        authority = json.loads(C2E_AUTH.read_text(encoding="utf-8"))
        self.assertEqual(
            authority["active_boundary_pack_id"],
            "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8",
        )
        general = authority["scope_generalization"]
        self.assertEqual(general["exact_population_identity_binding"], "NONE")
        self.assertEqual(general["exact_run_token_binding"], "NONE_FOR_ACTIVATION_IDENTITY")
        self.assertEqual(general["exact_date_window_binding"], "NONE")
        self.assertEqual(general["boundary_pack_binding"], "RETAIN_EXACT_CURRENT_OPERATOR_SELECTED_PACK")
        self.assertIn("BOUNDARY_PACK_SELECTION_OR_REPLACEMENT", authority["operator_required_for"])
        self.assertEqual(classification(self.state, "OPT-B.C2E.v0.2"), "ACTIVE")

    def test_occurrence_context_is_active_foundation_but_not_representation_input(self) -> None:
        authority = json.loads(OC_AUTH.read_text(encoding="utf-8"))
        self.assertEqual(authority["state"], "ACTIVE_FOUNDATION_NONSTRUCTURAL_ENRICHMENT")
        self.assertEqual(authority["representation_input"], "DENIED_BY_DEFAULT")
        self.assertEqual(authority["structural_identity_mutation"], "DENIED")
        self.assertEqual(
            classification(self.state, "OCCURRENCE_CONTEXT.v0.1"),
            "ACTIVE_FOUNDATION",
        )

    def test_research_operations_is_active_foundation_without_authority_escalation(self) -> None:
        authority = json.loads(RO_AUTH.read_text(encoding="utf-8"))
        self.assertEqual(
            authority["state"],
            "ACTIVE_FOUNDATION_WITHIN_EXISTING_READ_ONLY_AND_BOUNDED_APPEND_AUTHORITY",
        )
        self.assertIn("NEW_RESEARCH_WRITE_AUTHORITY", authority["not_granted_by_this_reclassification"])
        self.assertEqual(
            authority["ro4_g6_evidence_blocker"],
            "UNCHANGED_MUST_BE_RESOLVED_BY_ACTUAL_EVIDENCE_ACCUMULATION",
        )
        self.assertEqual(
            classification(self.state, "RESEARCH_OPERATIONS_FOUNDATION"),
            "ACTIVE_FOUNDATION",
        )

    def test_current_implementation_registry_points_to_current_authority(self) -> None:
        text = IMPLEMENTATION_REGISTRY.read_text(encoding="utf-8")
        self.assertIn("schema: ovc-implementation-registry/v2", text)
        self.assertIn(
            "current_authority_pointer: registries/governance/active_stack/CURRENT_ACTIVE_STACK_POINTER.json",
            text,
        )
        self.assertIn("state: LEGACY_INACTIVE", text)
        self.assertIn("ACTIVE_EXACT_NINE_COMPONENT_CORE_DISCOVERY_DEVELOPMENT", text)
        self.assertIn("ACTIVE_ENGINE_CURRENT_OPERATOR_SELECTED_PACK_MARKET_ENVELOPE_BOUND", text)

    def test_shadow_non_evaluable_legacy_and_locked_classes_are_disjoint(self) -> None:
        seen: set[str] = set()
        for class_name, members in self.state["classifications"].items():
            for member in members:
                self.assertNotIn(member, seen, f"duplicate classification for {member}")
                seen.add(member)
        self.assertEqual(classification(self.state, "FDI_C2G_FAMILY_DISCOVERY"), "SHADOW")
        self.assertEqual(
            classification(self.state, "OPT-B.C2P.v0.2.PERSISTENT_STRUCTURAL_OBJECTS"),
            "NON_EVALUABLE",
        )
        self.assertEqual(classification(self.state, "VALIDATION_2025_CURRENT_STACK"), "LOCKED")

    def test_new_evidence_route_allows_only_existing_market_envelope(self) -> None:
        resolved = require_new_evidence_route(
            ROOT, instrument="GBPUSD", side="BID", clock="15M", research_role="DISCOVERY"
        )
        self.assertEqual(resolved["market_envelope"]["validation"], "LOCKED_UNCONSUMED")
        with self.assertRaises(ActiveStackError):
            require_new_evidence_route(
                ROOT, instrument="EURUSD", side="BID", clock="15M", research_role="DISCOVERY"
            )
        with self.assertRaises(ActiveStackError):
            require_new_evidence_route(
                ROOT, instrument="GBPUSD", side="BID", clock="15M", research_role="VALIDATION"
            )

    def test_exposure_authorities_remain_denied(self) -> None:
        denials = set(self.state["retained_denials"])
        self.assertIn("PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION_AGENT_WRITE", denials)
        self.assertIn("CANONICAL_OR_R2_PUBLICATION", denials)
        self.assertIn("VALIDATION_CONSUMPTION", denials)


if __name__ == "__main__":
    unittest.main()
