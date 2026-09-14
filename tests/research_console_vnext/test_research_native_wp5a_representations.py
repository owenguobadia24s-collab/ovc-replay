from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ovc.console_vnext.application.errors import AuthorityDenied, ContractError, SourceConflict
from ovc.console_vnext.application.research_wp5a import (
    build_wp5a_representation_snapshot,
    git_blob_sha,
)

ROOT = Path(__file__).resolve().parents[2]
BINDINGS = (
    ROOT
    / "registries"
    / "research_console_vnext"
    / "research_native"
    / "wp5a_representation_source_bindings_v1.json"
)
PRESENTATION = (
    ROOT
    / "fixtures"
    / "research_console_vnext"
    / "console_pack_v0_1"
    / "research_wp5a.json"
)
SCHEMA = ROOT / "schemas" / "research_console_vnext" / "wp5a_representation_snapshot_v1.schema.json"
ROUTES = ROOT / "registries" / "research_console_vnext" / "research_native" / "route_registry_v2.json"
STATE = ROOT / "registries" / "implementation" / "research_console_vnext" / "OVC_RCN_RN_STATE_v0_2.json"
PREFLIGHT = ROOT / "artifacts" / "research_console_vnext" / "pvs3" / "RCN_RN_WP5A_SOURCE_AUTHORITY_PREFLIGHT.json"
MERGE_RECEIPT = ROOT / "artifacts" / "research_console_vnext" / "pvs3" / "RCN_RN_WP5A_MERGE_RECEIPT.json"
COMPONENT = ROOT / "apps" / "research_console_vnext" / "src" / "production" / "RepresentationWorkbench.tsx"
ROUTER = ROOT / "apps" / "research_console_vnext" / "src" / "app" / "router.tsx"
CLIENT = ROOT / "apps" / "research_console_vnext" / "src" / "api" / "client.ts"
CONTRACTS = ROOT / "apps" / "research_console_vnext" / "src" / "production" / "pvsContracts.ts"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class WP5ARepresentationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bindings = load(BINDINGS)
        self.presentation = load(PRESENTATION)

    def build(self, *, bindings=None, presentation=None):
        return build_wp5a_representation_snapshot(
            repository_root=ROOT,
            bindings=bindings or self.bindings,
            presentation=presentation or self.presentation,
        )

    def test_source_preflight_binds_exact_fixture_only_repository_objects(self) -> None:
        self.assertEqual("PASS_NO_FIRST_NEW_REAL_RESEARCH_SOURCE", self.bindings["source_preflight_status"])
        self.assertFalse(self.bindings["first_new_real_research_source"])
        self.assertEqual("RCN-RN-WP5A-CLOSEOUT", self.bindings["gate_branch"])
        self.assertEqual("RCN-RN-G5-FIRST-NEW-SOURCE", self.bindings["operator_escalation_gate"])
        self.assertEqual("LOCKED_UNCONSUMED", self.bindings["validation_consumption"])
        self.assertEqual("NONE", self.bindings["authority_effect"])
        self.assertTrue(self.bindings["sources"])
        for source in self.bindings["sources"]:
            self.assertEqual("SYNTHETIC_FIXTURE", source["source_class"])
            self.assertFalse(source["first_new_real_research_source"])
            source_path = ROOT / source["path"]
            self.assertTrue(source_path.is_file())
            self.assertEqual(source["git_blob_sha"], git_blob_sha(source_path))
            payload = load(source_path)
            self.assertEqual(source["schema"], payload["schema"])
            self.assertEqual(source["authority_value"], payload[source["authority_field"]])

    def test_valid_snapshot_is_method_first_null_winner_and_equal_status(self) -> None:
        value = self.build()
        self.assertEqual("FIXTURE_ONLY", value["mode"])
        self.assertEqual("NON_EVIDENTIARY", value["evidence_status"])
        self.assertTrue(value["presentation_guardrails"]["method_first"])
        self.assertFalse(value["presentation_guardrails"]["family_first"])
        self.assertIsNone(value["presentation_guardrails"]["default_winner"])
        self.assertEqual("NONE", value["presentation_guardrails"]["selector_authority"])
        self.assertEqual("PROHIBITED", value["presentation_guardrails"]["frontend_scientific_calculation"])
        self.assertTrue(all(row["winner"] is None for row in value["methods"]))
        self.assertTrue(all(row["winner"] is None for row in value["comparability"]))
        self.assertEqual(
            {"RESIDUAL", "AMBIGUOUS", "NO_STABLE_FAMILY"},
            {row["outcome"] for row in value["family_outcomes"]},
        )
        self.assertTrue(all(row["status"] == "LAWFUL_EQUAL_STATUS" for row in value["family_outcomes"]))

    def test_real_source_class_requires_operator_g5(self) -> None:
        bad = copy.deepcopy(self.bindings)
        bad["sources"][0]["source_class"] = "REAL_RESEARCH"
        with self.assertRaises(AuthorityDenied):
            self.build(bindings=bad)

    def test_first_new_real_source_requires_operator_g5(self) -> None:
        bad = copy.deepcopy(self.bindings)
        bad["first_new_real_research_source"] = True
        with self.assertRaises(AuthorityDenied):
            self.build(bindings=bad)

    def test_source_blob_mismatch_fails_closed(self) -> None:
        bad = copy.deepcopy(self.bindings)
        bad["sources"][0]["git_blob_sha"] = "0" * 40
        with self.assertRaises(SourceConflict):
            self.build(bindings=bad)

    def test_winner_and_selector_invention_fail_closed(self) -> None:
        bad = copy.deepcopy(self.presentation)
        bad["methods"][0]["winner"] = "SRI.MISSING_DIMENSION"
        with self.assertRaises(ContractError):
            self.build(presentation=bad)
        bad = copy.deepcopy(self.presentation)
        bad["methods"][0]["selection_authority"] = "ACTIVE"
        with self.assertRaises(AuthorityDenied):
            self.build(presentation=bad)

    def test_denominator_or_equal_status_drift_fails_closed(self) -> None:
        bad = copy.deepcopy(self.presentation)
        bad["population"]["denominator"] += 1
        with self.assertRaises(ContractError):
            self.build(presentation=bad)
        bad = copy.deepcopy(self.presentation)
        bad["family_outcomes"] = bad["family_outcomes"][:-1]
        with self.assertRaises(ContractError):
            self.build(presentation=bad)
        bad = copy.deepcopy(self.presentation)
        bad["outcome_denominator"]["denominator"] += 1
        with self.assertRaises(ContractError):
            self.build(presentation=bad)

    def test_source_fixture_expectation_drift_fails_closed(self) -> None:
        bad = copy.deepcopy(self.presentation)
        bad["source_fixture_refs"][0]["expected"] = "INVENTED_EXPECTATION"
        with self.assertRaises(SourceConflict):
            self.build(presentation=bad)

    def test_not_comparable_never_calls_distance_engine(self) -> None:
        bad = copy.deepcopy(self.presentation)
        bad["comparability"][0]["distance_engine_called"] = True
        with self.assertRaises(ContractError):
            self.build(presentation=bad)


class WP5ARepositoryContractTests(unittest.TestCase):
    def test_schema_route_preflight_and_programme_state_are_bound(self) -> None:
        schema = load(SCHEMA)
        routes = load(ROUTES)
        state = load(STATE)
        preflight = load(PREFLIGHT)
        receipt = load(MERGE_RECEIPT)
        self.assertEqual("ovc-rcn-rn-wp5a-representation-snapshot/v1", schema["$id"])
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("/research/representations/snapshot", routes["domains"]["RESEARCH"])
        self.assertEqual("COMPLETED", routes["wp5a_representations"]["binding_state"])
        self.assertEqual("PASS_NO_FIRST_NEW_REAL_RESEARCH_SOURCE", preflight["status"])
        self.assertFalse(preflight["gate_classification"]["operator_escalation_triggered"])
        self.assertEqual("RCN-RN-WP5A", receipt["packet_id"])
        self.assertEqual("COMPLETED", receipt["status"])
        self.assertEqual("PASS_DELEGATED_AUTO_RATIFICATION", receipt["decision"])
        self.assertEqual("NONE", receipt["authority_delta"])
        self.assertFalse(receipt["source_authority"]["first_new_real_research_source"])
        self.assertEqual("RCN-RN-WP5B", receipt["next_packet_named"])
        self.assertEqual("READY", receipt["next_packet_status"])

        # WP5A's historical closeout remains immutable while the current programme
        # pointer lawfully advances into source-scoped WP5B1 execution.
        self.assertEqual("RCN-RN-WP5B1", state["packet_id"])
        self.assertEqual("RCN-RN-WP5B1", state["current_packet"])
        self.assertEqual("QA_REVIEW", state["status"])
        self.assertEqual("NONE", state["authority_delta"])
        self.assertEqual("PASS", state["wp5b1"]["source_gate_decision"])
        self.assertEqual("RCN-RN-WP5B2", state["next_packet"])
        self.assertEqual(
            ["RCN-RN-WP5B1", "RCN-RN-WP5B2"],
            state["architecture_reconciliation"]["legacy_packet_mapping"]["RCN-RN-WP5B"],
        )
        self.assertFalse(state["architecture_reconciliation"]["source_plan_semantics_changed"])
        self.assertEqual("COMPLETED", state["wp5a"]["status"])
        self.assertFalse(state["wp5a"]["first_new_real_research_source"])

    def test_react_surface_inherits_workbenchframe_and_has_no_scientific_write_surface(self) -> None:
        component = COMPONENT.read_text(encoding="utf-8")
        router = ROUTER.read_text(encoding="utf-8")
        client = CLIENT.read_text(encoding="utf-8")
        contracts = CONTRACTS.read_text(encoding="utf-8")
        for inherited in [
            "GlobalDomainRail",
            "ApplicationHeader",
            "ContextAuthorityStrip",
            "WorkbenchNavigator",
            "EvidenceInspector",
            "EvidenceDock",
            "StatusBar",
        ]:
            self.assertIn(inherited, component)
        for marker in [
            "METHOD-FIRST SOURCE EVIDENCE",
            "NO DEFAULT WINNER",
            "NO METHOD SELECTOR AUTHORITY",
            "RESIDUAL / AMBIGUITY / NO_STABLE_FAMILY",
            "frontend scientific calculation PROHIBITED",
            'data-first-new-real-research-source="false"',
        ]:
            self.assertIn(marker, component)
        self.assertNotIn("fetch(", component)
        self.assertNotIn("Math.random", component)
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            self.assertNotIn(f'method: "{method}"', component)
        self.assertIn('{path:"/research/representations",element:<RepresentationWorkbench/>}', router)
        self.assertIn('"/research/representations"', contracts)
        self.assertIn('method: "GET"', client)
        self.assertIn('"/research/representations/snapshot"', client)


@unittest.skipIf(
    importlib.util.find_spec("fastapi") is None,
    "FastAPI dependency not installed in generic repository environment",
)
class WP5AApiTests(unittest.TestCase):
    def test_fixture_snapshot_is_get_only_and_validation_denies_before_reads(self) -> None:
        from fastapi.testclient import TestClient

        from apps.research_api.app import create_app

        app = create_app()
        client = TestClient(app)
        store = app.state.fixture_store
        before = store.resource_reads
        denied = client.get("/api/v1/research/representations/snapshot?role=VALIDATION")
        self.assertEqual(403, denied.status_code)
        self.assertEqual("AUTHORITY_DENIED", denied.json()["reason_code"])
        self.assertEqual(before, store.resource_reads)

        response = client.get("/api/v1/research/representations/snapshot")
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual("FIXTURE_ONLY", body["fixture_banner"]["mode"])
        self.assertEqual("NON_EVIDENTIARY", body["fixture_banner"]["evidence_status"])
        self.assertEqual("NONE", body["capability"]["authority_effect"])
        self.assertFalse(body["capability"]["authorised"])
        self.assertFalse(body["capability"]["active"])
        self.assertNotIn("real_source_banner", body)
        self.assertTrue(all(row["winner"] is None for row in body["payload"]["methods"]))
        self.assertEqual(
            ["RESIDUAL", "AMBIGUOUS", "NO_STABLE_FAMILY"],
            body["payload"]["presentation_guardrails"]["equal_status_outcomes"],
        )

        mutation = client.post("/api/v1/research/representations/snapshot")
        self.assertEqual(405, mutation.status_code)
        self.assertEqual("MUTATION_METHOD_DENIED", mutation.json()["reason_code"])

    def test_investigate_real_mode_does_not_turn_wp5a_into_a_real_research_source(self) -> None:
        from fastapi.testclient import TestClient

        from apps.research_api.app import create_app

        owner_bindings = (
            ROOT
            / "registries"
            / "research_console_vnext"
            / "research_native"
            / "owner_read_projection_bindings_v1.json"
        )
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(
                source_mode="REAL",
                real_source_root=Path(temporary),
                real_source_bindings=owner_bindings,
            )
            body = TestClient(app).get("/api/v1/research/representations/snapshot").json()
            self.assertEqual("FIXTURE_ONLY", body["fixture_banner"]["mode"])
            self.assertEqual("SYNTHETIC_FIXTURE", body["fixture_banner"]["data_classification"])
            self.assertNotIn("real_source_banner", body)
            self.assertFalse(body["payload"]["source_preflight"]["first_new_real_research_source"])
