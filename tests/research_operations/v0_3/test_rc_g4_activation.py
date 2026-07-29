from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from apps.research_console.c1_fact_assurance import build_c1_fact_assurance_view
from apps.research_console.c1_projection_source import (
    DOWNSTREAM_AUTHORITY_BANNER,
    SCHEMA_BINDINGS,
    load_c1_projection,
    projection_identity,
    validate_c1_projection_payload,
)
from ovc.research_operations.v0_3 import (
    build_c1_console_projection,
    build_c1_fact_projection,
    build_c1_lineage_trace,
    build_downstream_trace_projection,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/v0_3/wp4_c1_lineage_projection_fixture.json"
HOME = ROOT / "apps/research_console/Home.py"
WRAPPER = ROOT / "apps/research_console/rc_g4_console.py"
DECISION = ROOT / "docs/releases/research-console-v0-3/rc-g4/RC_G4_OPERATOR_DECISION.md"


def build_candidate() -> dict:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    lineage = build_c1_lineage_trace(
        release_context=fixture["release_context"],
        c1_record=fixture["c1_record"],
    )
    fact = build_c1_fact_projection(
        release_context=fixture["release_context"],
        c1_record=fixture["c1_record"],
        formula_evidence=fixture["formula_evidence"],
        lineage_trace=lineage,
    )
    downstream = build_downstream_trace_projection(
        c1_record_id=fixture["c1_record"]["record_id"],
        child_references=fixture["child_references"],
    )
    return build_c1_console_projection(
        release_context=fixture["release_context"],
        fact_projection=fact,
        computability_projection=fixture["computability_projection"],
        assurance_projection=fixture["assurance_projection"],
        lineage_trace=lineage,
        downstream_trace=downstream,
    )


class RCG4ActivationTests(unittest.TestCase):
    def test_valid_projection_activates_local_read_only_consumption(self) -> None:
        activated = validate_c1_projection_payload(build_candidate(), schema_root=ROOT)
        self.assertEqual(activated["route_state"], "ENABLED_LOCAL_READ_ONLY")
        self.assertTrue(activated["route_enabled"])
        self.assertEqual(activated["availability"], "AVAILABLE")
        self.assertEqual(activated["authority"], "LOCAL_READ_ONLY_C1_PRESENTATION")
        self.assertEqual(activated["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(activated["c2_authority"], "UNCHANGED")
        self.assertEqual(activated["pattern_discovery_authority"], "UNCHANGED")
        self.assertTrue(activated["read_only"])
        self.assertEqual(activated["writes"], "NONE")
        self.assertEqual(len(activated["schema_bindings"]), 4)

    def test_loader_is_deterministic_and_identity_only(self) -> None:
        candidate = build_candidate()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "projection.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            first = load_c1_projection(path, schema_root=ROOT)
            second = load_c1_projection(path, schema_root=ROOT)
        self.assertEqual(first, second)
        identity = projection_identity(first)
        self.assertEqual(identity["availability"], "AVAILABLE")
        self.assertEqual(identity["authority"], "LOCAL_READ_ONLY_C1_PRESENTATION")
        self.assertEqual(identity["writes"], "NONE")

    def test_view_model_keeps_fact_and_downstream_trace_structurally_separate(self) -> None:
        activated = validate_c1_projection_payload(build_candidate(), schema_root=ROOT)
        view = build_c1_fact_assurance_view(activated)
        self.assertEqual(view["status"], "READY")
        self.assertEqual(view["fact"]["panel_id"], "RO3-C1-FACT-INSPECTOR")
        self.assertEqual(view["downstream_trace"]["panel_id"], "RO3-C1-DOWNSTREAM-TRACE")
        self.assertNotIn("child_references", view["fact"])
        self.assertNotIn("null_reason", view["downstream_trace"])
        self.assertEqual(view["downstream_trace"]["banner"], DOWNSTREAM_AUTHORITY_BANNER)
        for row in view["downstream_trace"]["child_references"]:
            self.assertNotIn("null_reason", row)
            self.assertNotIn("confidence", row)
            self.assertNotIn("score", row)

    def test_missing_projection_is_explicit_not_evaluated_on_enabled_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = load_c1_projection(Path(tmp) / "missing.json", schema_root=ROOT)
        self.assertTrue(result["route_enabled"])
        self.assertEqual(result["route_state"], "ENABLED_LOCAL_READ_ONLY")
        self.assertEqual(result["availability"], "NOT_EVALUATED")
        self.assertEqual(result["reason"], "C1_PROJECTION_UNAVAILABLE")
        self.assertEqual(result["panels"], {})

    def test_validation_is_denied_before_nested_panel_capability_is_inspected(self) -> None:
        candidate = copy.deepcopy(build_candidate())
        candidate["source_context"]["role"] = "VALIDATION"
        candidate["panels"]["fact"]["path"] = "/forbidden/validation/content"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "projection.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            result = load_c1_projection(path, schema_root=ROOT)
        self.assertEqual(result["availability"], "NOT_EVALUATED")
        self.assertEqual(result["reason"], "VALIDATION_DENIED_BEFORE_PANEL_OR_RECORD_RESOLUTION")
        self.assertEqual(result["validation_consumption"], "LOCKED_UNCONSUMED")

    def test_stale_projection_fails_closed(self) -> None:
        candidate = copy.deepcopy(build_candidate())
        candidate["source_context"]["represented_commit"] = "1111111111111111111111111111111111111111"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "projection.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            result = load_c1_projection(path, schema_root=ROOT)
        self.assertEqual(result["reason"], "C1_STALE_PROJECTION_DENIED")
        self.assertEqual(result["panels"], {})

    def test_recursive_write_capability_is_denied(self) -> None:
        candidate = copy.deepcopy(build_candidate())
        candidate["panels"]["assurance"]["git_write"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "projection.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            result = load_c1_projection(path, schema_root=ROOT)
        self.assertIn("C1_PROJECTION_CAPABILITY_DENIED:git_write", result["reason"])
        self.assertEqual(result["writes"], "NONE")

    def test_fact_panel_cannot_embed_c2_transition(self) -> None:
        candidate = copy.deepcopy(build_candidate())
        candidate["panels"]["fact"]["c2_transition"] = {"child_id": "forbidden"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "projection.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            result = load_c1_projection(path, schema_root=ROOT)
        self.assertIn("C1_FACT_PANEL_MIXED_AUTHORITY", result["reason"])

    def test_downstream_scoring_vocabulary_is_denied(self) -> None:
        candidate = copy.deepcopy(build_candidate())
        candidate["panels"]["downstream_trace"]["child_references"][0]["confidence"] = "0.9"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "projection.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            result = load_c1_projection(path, schema_root=ROOT)
        self.assertIn("C1_DOWNSTREAM_PRESENTATION_DENIED", result["reason"])

    def test_permanent_downstream_banner_is_required(self) -> None:
        candidate = copy.deepcopy(build_candidate())
        candidate["panels"]["downstream_trace"]["banner"] = "read only"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "projection.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            result = load_c1_projection(path, schema_root=ROOT)
        self.assertEqual(result["reason"], "C1_DOWNSTREAM_AUTHORITY_BANNER_REQUIRED")

    def test_exact_schema_blob_binding_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for binding in SCHEMA_BINDINGS:
                source = ROOT / binding["path"]
                target = root / binding["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            first = root / SCHEMA_BINDINGS[0]["path"]
            first.write_text(first.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            result = load_c1_projection(Path(tmp) / "missing.json", schema_root=root)
        self.assertIn("C1_SCHEMA_BLOB_MISMATCH", result["reason"])
        self.assertEqual(result["availability"], "NOT_EVALUATED")

    def test_console_entry_point_and_wrapper_record_exact_activation_boundary(self) -> None:
        home = HOME.read_text(encoding="utf-8")
        wrapper = WRAPPER.read_text(encoding="utf-8")
        decision = DECISION.read_text(encoding="utf-8")
        self.assertIn("load_c1_projection", home)
        self.assertIn("c1_projection=_c1_projection", home)
        self.assertIn("render_c1_fact_assurance", wrapper)
        self.assertIn("ENABLED_LOCAL_READ_ONLY", wrapper)
        self.assertIn("LOCKED_UNCONSUMED", wrapper)
        self.assertIn("LOCAL_READ_ONLY_C1_PRESENTATION", decision)
        for denied in ("research_write", "selector_mutation", "threshold_mutation", "execution", "agent"):
            self.assertIn(f'"{denied}"', wrapper)


if __name__ == "__main__":
    unittest.main()
