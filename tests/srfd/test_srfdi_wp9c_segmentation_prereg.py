from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd.segmentation_prereg import (
    null_boundary_control_from_c2_ledger,
    run_change_from_c2_ledger,
    state_change_indicator,
    validate_boundary_pack_registry,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registries/research/srfd/segmentation_boundary_packs_v0_3.json"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_3.json"
MANIFEST = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9c/SRFD_JUNE_RUN_MANIFEST_v0_3_CANDIDATE.json"
PACKET = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9c/SRFDI_G9C_FREEZE_OPERATOR_PACKET.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_4.json"
CURRENT_POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


def row(record_id: str, when: str, state_key: str, *, reset: str | None = None) -> dict[str, object]:
    return {
        "record_id": record_id,
        "source_release_id": "SRC",
        "instrument_id": "GBPUSD",
        "side": "BID",
        "scope_id": "15M-LOCAL",
        "clock_id": "15M",
        "first_valid_time": when,
        "state_key": state_key,
        "reset_reason": reset,
    }


class SRFDIWP9CCorrectivePreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY.read_text())
        cls.prereg = json.loads(PREREG.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.packet = json.loads(PACKET.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.current_pointer = json.loads(CURRENT_POINTER.read_text())

    def test_registry_materialises_exact_declared_segmentation_set(self) -> None:
        digest = validate_boundary_pack_registry(self.registry)
        self.assertEqual(self.prereg["segmentation_supersession"]["registry_logical_sha256"], digest)
        self.assertEqual(
            [
                "C2E_CAUSAL_ADAPTER",
                "RUN_CHANGE_SEGMENTATION",
                "DIRECTIONAL_CHANGE",
                "PELT_REFERENCE",
                "NULL_BOUNDARY_CONTROL",
            ],
            self.prereg["segmentation_supersession"]["declared_method_ids"],
        )

    def test_v02_is_immutable_base_and_only_segmentation_is_superseded(self) -> None:
        self.assertEqual(
            "13c17cf64c576b35e53047de753a5fd1a49bbdc7205c387bbcedb5a34441b804",
            self.prereg["supersession"]["base_preregistration_sha256"],
        )
        self.assertEqual("SEGMENTATION_EXECUTION_SPECIFICATION_ONLY", self.prereg["supersession"]["supersession_scope"])
        for key in ("representation_grid", "distance_grid", "family_method_grid", "sensitivity_family_parameter_ladders"):
            self.assertEqual("UNCHANGED", self.prereg["inherited_frozen_surfaces"][key])

    def test_run_change_is_causal_and_resets_split_streams(self) -> None:
        rows = [
            row("R1", "2026-06-01T00:15:00Z", "A"),
            row("R2", "2026-06-01T00:30:00Z", "A"),
            row("R3", "2026-06-01T00:45:00Z", "B"),
            row("R4", "2026-06-01T01:00:00Z", "B", reset="C2_SCOPE_RESET"),
            row("R5", "2026-06-01T01:15:00Z", "C"),
        ]
        result = run_change_from_c2_ledger(reversed(rows))
        self.assertEqual(2, result["stream_count"])
        self.assertEqual(2, len(result["boundaries"]))
        self.assertEqual("2026-06-01T00:45:00Z", result["boundaries"][0]["first_valid_time"])
        self.assertEqual("2026-06-01T01:15:00Z", result["boundaries"][1]["first_valid_time"])

    def test_null_control_has_no_structural_boundaries(self) -> None:
        rows = [
            row("R1", "2026-06-01T00:15:00Z", "A"),
            row("R2", "2026-06-01T00:30:00Z", "B"),
            row("R3", "2026-06-01T00:45:00Z", "C", reset="C2_SCOPE_RESET"),
        ]
        result = null_boundary_control_from_c2_ledger(rows)
        self.assertEqual([], result["boundaries"])
        self.assertEqual(2, len(result["segments"]))
        self.assertTrue(all(item["structural_boundary_count"] == 0 for item in result["segments"]))

    def test_pelt_signal_is_exact_bounded_transition_indicator(self) -> None:
        rows = [
            row("R1", "2026-06-01T00:15:00Z", "A"),
            row("R2", "2026-06-01T00:30:00Z", "A"),
            row("R3", "2026-06-01T00:45:00Z", "B"),
            row("R4", "2026-06-01T01:00:00Z", "B"),
        ]
        self.assertEqual([[0, 0, 1, 0]], state_change_indicator(rows))

    def test_manifest_has_no_hidden_segmentation_default_or_method_drop(self) -> None:
        self.assertEqual(
            self.prereg["segmentation_supersession"]["declared_method_ids"],
            self.manifest["candidate_sets"]["segmentation"],
        )
        self.assertEqual(
            ["RUN_CHANGE_SEGMENTATION", "NULL_BOUNDARY_CONTROL"],
            self.manifest["candidate_sets"]["segmentation_execute"],
        )
        self.assertEqual(
            ["C2E_CAUSAL_ADAPTER", "DIRECTIONAL_CHANGE", "PELT_REFERENCE"],
            self.manifest["candidate_sets"]["segmentation_visible_nonexecuted"],
        )

    def test_old_authority_is_unconsumed_and_candidate_freeze_does_not_authorize_june(self) -> None:
        self.assertFalse(self.prereg["authority_transition"]["current_v0_2_token_consumed"])
        self.assertEqual("SRFDI-G9C-FREEZE", self.packet["gate_id"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.packet["recommended_decision"])
        self.assertEqual("DENIED_PENDING_NEW_EXACT_AUTHORIZATION", self.packet["authority_after_recommended_decision"]["june_execution"])
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("SRFDI-G9C-FREEZE", self.state["current_gate"])
        self.assertTrue(self.state["operator_decision_required"])

    def test_candidate_does_not_mutate_authoritative_pointer_before_operator_freeze(self) -> None:
        self.assertEqual(
            "registries/implementation/srfd/OVC_SRFDI_STATE_v0_3.json",
            self.current_pointer["authoritative_state"],
        )
        self.assertEqual("SRFDI-G10", self.current_pointer["current_gate"])
        self.assertFalse(self.current_pointer["operator_decision_required"])
        self.assertEqual("AUTHORIZED_BOUNDED_JUNE_BENCHMARK_UNCONSUMED", self.current_pointer["june_execution"])


if __name__ == "__main__":
    unittest.main()
