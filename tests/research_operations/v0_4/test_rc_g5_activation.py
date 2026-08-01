from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from apps.research_console.c2_sequence_evidence import (
    PANEL_ORDER,
    build_c2_sequence_evidence_view,
)
from apps.research_console.ro4_active_projection_source import (
    DECISION_ID,
    RO4ActiveProjectionError,
    load_active_projection,
    projection_identity,
    route_registration,
)
from ovc.research_operations.v0_4.console_projection import build_console_projection

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/v0_4/RO4_WP5_CONSOLE_PROJECTION_FIXTURE_v0_1.json"
AUTHORITY = ROOT / "registries/research_console/RC_G5_C2_SEQUENCE_EVIDENCE_AUTHORITY_v0_1.json"
HOME = ROOT / "apps/research_console/Home.py"
WRAPPER = ROOT / "apps/research_console/rc_g5_console.py"
SOURCE = ROOT / "apps/research_console/ro4_active_projection_source.py"


def build_candidate(fixture: dict | None = None) -> dict:
    source = copy.deepcopy(fixture or json.loads(FIXTURE.read_text(encoding="utf-8")))
    return build_console_projection(
        source_commit=source["source_commit"],
        source_release_refs=source["source_release_refs"],
        panels=source["panels"],
        schema_root=ROOT,
    )


def load_candidate(candidate: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "projection.json"
        path.write_text(json.dumps(candidate), encoding="utf-8")
        return load_active_projection(path, schema_root=ROOT)


class RCG5ActivationTests(unittest.TestCase):
    def test_authority_registry_is_exactly_enabled_local_read_only(self) -> None:
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        self.assertTrue(authority["enabled"])
        self.assertEqual(authority["status"], "ENABLED_LOCAL_READ_ONLY")
        self.assertEqual(authority["current_route_state"], "ENABLED_LOCAL_READ_ONLY")
        self.assertEqual(authority["operator_decision_id"], DECISION_ID)
        self.assertEqual(authority["writes"], "NONE")
        self.assertEqual(authority["annotation_actions"], "NONE")
        self.assertEqual(authority["remote_deployment"], "DENIED")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")

    def test_valid_projection_is_consumed_under_active_route_without_mutation(self) -> None:
        candidate = build_candidate()
        activated = load_candidate(candidate)
        self.assertEqual(activated["availability"], "AVAILABLE")
        self.assertEqual(activated["route_state"], "ENABLED_LOCAL_READ_ONLY")
        self.assertTrue(activated["route_enabled"])
        self.assertEqual(activated["source_projection_id"], candidate["projection_id"])
        self.assertEqual(activated["source_logical_hash"], candidate["logical_hash"])
        self.assertEqual(activated["writes"], "NONE")
        self.assertEqual(activated["annotation_actions"], "NONE")

    def test_loader_is_deterministic_and_identity_only(self) -> None:
        candidate = build_candidate()
        first = load_candidate(candidate)
        second = load_candidate(candidate)
        self.assertEqual(first, second)
        identity = projection_identity(first)
        self.assertEqual(identity["availability"], "AVAILABLE")
        self.assertEqual(identity["route_state"], "ENABLED_LOCAL_READ_ONLY")
        self.assertEqual(identity["writes"], "NONE")

    def test_missing_projection_is_explicit_not_evaluated_on_enabled_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = load_active_projection(Path(tmp) / "missing.json", schema_root=ROOT)
        self.assertEqual(result["route_state"], "ENABLED_LOCAL_READ_ONLY")
        self.assertTrue(result["route_enabled"])
        self.assertEqual(result["availability"], "NOT_EVALUATED")
        self.assertEqual(result["reason"], "RO4_PROJECTION_UNAVAILABLE")
        self.assertEqual(result["panels"], [])

    def test_validation_is_denied_before_panel_resolution(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        fixture["source_release_refs"][0]["role"] = "VALIDATION"
        fixture["source_release_refs"][0]["release_id"] = "SYNTHETIC.VALIDATION.DENIED"
        candidate = {
            "projection_id": "RO4.CONSOLE.PROJECTION.invalid",
            "route_id": "RESEARCH.C2_SEQUENCE_EVIDENCE",
            "route_state": "DISABLED_PENDING_RC_G5",
            "source_commit": fixture["source_commit"],
            "source_release_refs": fixture["source_release_refs"],
            "panels": fixture["panels"],
            "authority_banners": [
                "LOCAL READ ONLY — ROUTE DISABLED PENDING RC-G5.",
                "NO ANNOTATION OR WRITE ACTIONS ARE AVAILABLE.",
                "VALIDATION IS LOCKED_UNCONSUMED.",
                "C2 AND PATTERN DISCOVERY AUTHORITY IS UNCHANGED.",
            ],
            "writes": "NONE",
            "remote_deployment": "DENIED",
            "logical_hash": "0" * 64,
        }
        result = load_candidate(candidate)
        self.assertEqual(result["availability"], "NOT_EVALUATED")
        self.assertIn("RO4_VALIDATION_DENIED_BEFORE_PANEL_RESOLUTION", result["reason"])
        self.assertEqual(result["validation_consumption"], "LOCKED_UNCONSUMED")

    def test_view_keeps_all_eight_panel_classes_separate(self) -> None:
        view = build_c2_sequence_evidence_view(load_candidate(build_candidate()))
        self.assertEqual(view["status"], "READY")
        self.assertEqual(tuple(view["panel_order"]), PANEL_ORDER)
        self.assertEqual(set(view["panels"]), set(PANEL_ORDER))
        for panel_class, rows in view["panels"].items():
            for row in rows:
                self.assertEqual(row["panel_class"], panel_class)

    def test_pattern_discovery_remains_trigger_trace_only(self) -> None:
        view = build_c2_sequence_evidence_view(load_candidate(build_candidate()))
        rows = view["panels"]["PD_TRIGGER_TRACE_ONLY"]
        self.assertEqual(len(rows), 1)
        payload = rows[0]["payload"]
        self.assertIn("trigger_trace_ids", payload)
        for denied in ("candidate_ids", "ranking", "novelty", "review_decision"):
            self.assertNotIn(denied, payload)

    def test_permanent_banners_and_no_write_boundary_are_visible(self) -> None:
        view = build_c2_sequence_evidence_view(load_candidate(build_candidate()))
        self.assertEqual(len(view["authority_banners"]), 4)
        self.assertEqual(view["writes"], "NONE")
        self.assertEqual(view["annotation_actions"], "NONE")
        self.assertEqual(view["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(view["remote_deployment"], "DENIED")

    def test_tampered_operator_authority_fails_closed(self) -> None:
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        authority["operator_decision_id"] = "RC-G5.OPERATOR.INVALID"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "authority.json"
            path.write_text(json.dumps(authority), encoding="utf-8")
            with self.assertRaisesRegex(RO4ActiveProjectionError, "RC_G5_OPERATOR_DECISION_BINDING_FAILURE"):
                load_active_projection(Path(tmp) / "missing.json", schema_root=ROOT, authority_path=path)

    def test_route_registration_contains_no_action_or_remote_authority(self) -> None:
        registration = route_registration()
        self.assertEqual(registration["route_state"], "ENABLED_LOCAL_READ_ONLY")
        self.assertEqual(registration["writes"], "NONE")
        self.assertEqual(registration["annotation_actions"], "NONE")
        self.assertEqual(registration["remote_deployment"], "DENIED")
        self.assertEqual(registration["operator_decision_id"], DECISION_ID)

    def test_console_entry_point_records_exact_activation_boundary(self) -> None:
        home = HOME.read_text(encoding="utf-8")
        wrapper = WRAPPER.read_text(encoding="utf-8")
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("load_active_projection", home)
        self.assertIn("c2_sequence_projection=_c2_sequence_projection", home)
        self.assertIn("render_c2_sequence_evidence", wrapper)
        self.assertIn("LOCAL_READ_ONLY_C2_SEQUENCE_EVIDENCE_PRESENTATION", wrapper)
        self.assertIn("ANNOTATION_ACTIONS", source.upper())
        for denied in ("research_write", "selector_mutation", "threshold_mutation", "execution", "agent", "r2_write"):
            self.assertIn(f'"{denied}"', wrapper)


if __name__ == "__main__":
    unittest.main()
