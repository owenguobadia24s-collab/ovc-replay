from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ovc.console_vnext.application.errors import AuthorityDenied, ContractError, SourceConflict
from ovc.console_vnext.application.research_wp5a import git_blob_sha
from ovc.console_vnext.application.research_wp5b1 import build_wp5b1_dmrp_snapshot

ROOT = Path(__file__).resolve().parents[2]
BINDINGS = ROOT / "registries" / "research_console_vnext" / "research_native" / "wp5b1_dmrp_source_bindings_v1.json"
PRESENTATION = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1" / "research_wp5b1.json"
SCHEMA = ROOT / "schemas" / "research_console_vnext" / "wp5b1_dmrp_snapshot_v1.schema.json"
ROUTES = ROOT / "registries" / "research_console_vnext" / "research_native" / "route_registry_v2.json"
COMPONENT = ROOT / "apps" / "research_console_vnext" / "src" / "production" / "DMRPWorkbench.tsx"
ROUTER = ROOT / "apps" / "research_console_vnext" / "src" / "app" / "router.tsx"
CLIENT = ROOT / "apps" / "research_console_vnext" / "src" / "api" / "client.ts"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class WP5B1DMRPServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bindings = load(BINDINGS)
        self.presentation = load(PRESENTATION)

    def build(self, *, bindings=None, presentation=None):
        return build_wp5b1_dmrp_snapshot(
            repository_root=ROOT,
            bindings=bindings or self.bindings,
            presentation=presentation or self.presentation,
        )

    def test_exact_fixture_only_owner_bindings(self) -> None:
        self.assertEqual("GET_ONLY", self.bindings["transport"])
        self.assertEqual("FIXTURE_ONLY", self.bindings["presentation_mode"])
        self.assertEqual("NON_EVIDENTIARY", self.bindings["evidence_status"])
        self.assertEqual("NONE", self.bindings["authority_effect"])
        self.assertEqual("LOCKED_UNCONSUMED", self.bindings["validation_consumption"])
        self.assertFalse(self.bindings["first_new_real_research_source"])
        self.assertEqual("RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]", self.bindings["operator_escalation_gate"])
        self.assertEqual(3, len(self.bindings["sources"]))
        for source in self.bindings["sources"]:
            self.assertEqual("SYNTHETIC_FIXTURE", source["source_class"])
            self.assertFalse(source["first_new_real_research_source"])
            path = ROOT / source["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(source["git_blob_sha"], git_blob_sha(path))
            owner = load(path)
            self.assertEqual(source["schema"], owner["schema"])
            self.assertEqual(source["authority_value"], owner[source["authority_field"]])

    def test_valid_snapshot_preserves_candidate_and_mode_identity(self) -> None:
        value = self.build()
        self.assertEqual("PATH_1_EMPIRICAL", value["path1"]["research_mode"])
        self.assertEqual("SYNTH.SERIES.P1.1", value["candidate_generation"]["series_id"])
        self.assertEqual(1, value["candidate_generation"]["generation"])
        self.assertEqual({"MATCH": 1, "NON_MATCH": 1, "NOT_EVALUABLE": 1}, value["candidate_generation"]["membership"])
        self.assertEqual("NONE", value["path2"]["real_source_authority"])
        self.assertEqual("UNFORMALISABLE", value["path2"]["divergent_disposition"])
        self.assertEqual("LOCKED_UNCONSUMED", value["path1"]["validation_access_state"])

    def test_cross_mode_correspondence_never_becomes_independence_or_identity_merge(self) -> None:
        value = self.build()
        relation = value["cross_mode"][0]
        self.assertEqual("POSSIBLE_CORRESPONDENCE", relation["correspondence"])
        self.assertEqual("NOT_ESTABLISHED", relation["independence"])
        self.assertFalse(relation["identity_merge"])
        self.assertIsNone(relation["winner"])
        self.assertIsNone(relation["ranking"])

        bad = copy.deepcopy(self.presentation)
        bad["cross_mode"][0]["independence"] = "ESTABLISHED"
        with self.assertRaises(ContractError):
            self.build(presentation=bad)

        bad = copy.deepcopy(self.presentation)
        bad["cross_mode"][0]["identity_merge"] = True
        with self.assertRaises(ContractError):
            self.build(presentation=bad)

    def test_negative_and_divergent_evidence_are_mandatory(self) -> None:
        value = self.build()
        self.assertEqual(
            {"NOT_EVALUABLE", "UNFORMALISABLE"},
            {row["status"] for row in value["negative_divergent_evidence"]},
        )
        bad = copy.deepcopy(self.presentation)
        bad["negative_divergent_evidence"] = [bad["negative_divergent_evidence"][0]]
        with self.assertRaises(ContractError):
            self.build(presentation=bad)

    def test_real_source_or_authority_drift_requires_reserved_gate(self) -> None:
        bad = copy.deepcopy(self.bindings)
        bad["sources"][0]["source_class"] = "REAL_RESEARCH_SOURCE"
        with self.assertRaises(AuthorityDenied):
            self.build(bindings=bad)

        bad = copy.deepcopy(self.bindings)
        bad["first_new_real_research_source"] = True
        with self.assertRaises(AuthorityDenied):
            self.build(bindings=bad)

        bad = copy.deepcopy(self.bindings)
        bad["validation_consumption"] = "AVAILABLE"
        with self.assertRaises(AuthorityDenied):
            self.build(bindings=bad)

    def test_blob_or_identity_drift_fails_closed(self) -> None:
        bad = copy.deepcopy(self.bindings)
        bad["sources"][0]["git_blob_sha"] = "0" * 40
        with self.assertRaises(SourceConflict):
            self.build(bindings=bad)

        bad = copy.deepcopy(self.presentation)
        bad["candidate_generation"]["series_id"] = "SYNTH.INVENTED"
        with self.assertRaises(SourceConflict):
            self.build(presentation=bad)

    def test_path_escape_is_rejected(self) -> None:
        bad = copy.deepcopy(self.bindings)
        bad["sources"][0]["path"] = "../outside.json"
        with self.assertRaises(ContractError):
            self.build(bindings=bad)

    def test_guardrails_reject_rank_or_candidate_action(self) -> None:
        bad = copy.deepcopy(self.presentation)
        bad["presentation_guardrails"]["ranking"] = "SCORE"
        with self.assertRaises(ContractError):
            self.build(presentation=bad)
        bad = copy.deepcopy(self.presentation)
        bad["presentation_guardrails"]["candidate_repair"] = "ENABLED"
        with self.assertRaises(ContractError):
            self.build(presentation=bad)


class WP5B1RepositoryContractTests(unittest.TestCase):
    def test_schema_route_and_frontend_are_fixture_only_and_read_only(self) -> None:
        schema = load(SCHEMA)
        routes = load(ROUTES)
        component = COMPONENT.read_text(encoding="utf-8")
        router = ROUTER.read_text(encoding="utf-8")
        client = CLIENT.read_text(encoding="utf-8")
        self.assertEqual("ovc-rcn-rn-wp5b1-dmrp-snapshot/v1", schema["$id"])
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("/research/dmrp/snapshot", routes["domains"]["RESEARCH"])
        route = routes["wp5b1_dmrp"]
        self.assertEqual("FIXTURE_ONLY", route["mode"])
        self.assertFalse(route["first_new_real_research_source"])
        self.assertEqual("NONE", route["authority_effect"])
        self.assertEqual("RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]", route["operator_escalation_gate"])
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
            "PATH 1 / EMPIRICAL DISCOVERY",
            "PATH 2 / THEORY FORMALISATION",
            "RESEARCH CANDIDATE GENERATION",
            "CROSS-MODE CORRESPONDENCE",
            "NEGATIVE / DIVERGENT EVIDENCE",
            "correspondence is not independence",
            'data-first-new-real-research-source="false"',
        ]:
            self.assertIn(marker, component)
        self.assertNotIn("fetch(", component)
        self.assertNotIn("Math.random", component)
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            self.assertNotIn(f'method: "{method}"', component)
        self.assertIn('{path:"/research/dmrp",element:<DMRPWorkbench/>}', router)
        self.assertIn('"/research/dmrp/snapshot"', client)
        self.assertIn('method: "GET"', client)


@unittest.skipIf(
    importlib.util.find_spec("fastapi") is None,
    "FastAPI dependency not installed in generic repository environment",
)
class WP5B1ApiTests(unittest.TestCase):
    def test_fixture_endpoint_is_get_only_and_validation_denies_before_reads(self) -> None:
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app

        app = create_app()
        client = TestClient(app)
        store = app.state.fixture_store
        before = store.resource_reads
        denied = client.get("/api/v1/research/dmrp/snapshot?role=VALIDATION")
        self.assertEqual(403, denied.status_code)
        self.assertEqual("AUTHORITY_DENIED", denied.json()["reason_code"])
        self.assertEqual(before, store.resource_reads)

        response = client.get("/api/v1/research/dmrp/snapshot")
        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual("FIXTURE_ONLY", body["fixture_banner"]["mode"])
        self.assertEqual("NON_EVIDENTIARY", body["fixture_banner"]["evidence_status"])
        self.assertEqual("NONE", body["capability"]["authority_effect"])
        self.assertFalse(body["payload"]["source_preflight"]["first_new_real_research_source"])
        self.assertEqual("NOT_ESTABLISHED", body["payload"]["cross_mode"][0]["independence"])

        mutation = client.post("/api/v1/research/dmrp/snapshot")
        self.assertEqual(405, mutation.status_code)
        self.assertEqual("MUTATION_METHOD_DENIED", mutation.json()["reason_code"])

    def test_investigate_real_mode_does_not_promote_wp5b1_to_real_dmrp(self) -> None:
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app

        owner_bindings = ROOT / "registries" / "research_console_vnext" / "research_native" / "owner_read_projection_bindings_v1.json"
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(
                source_mode="REAL",
                real_source_root=Path(temporary),
                real_source_bindings=owner_bindings,
            )
            body = TestClient(app).get("/api/v1/research/dmrp/snapshot").json()
            self.assertEqual("FIXTURE_ONLY", body["fixture_banner"]["mode"])
            self.assertEqual("SYNTHETIC_FIXTURE", body["fixture_banner"]["data_classification"])
            self.assertFalse(body["payload"]["source_preflight"]["first_new_real_research_source"])
            self.assertEqual("NONE", body["payload"]["path2"]["real_source_authority"])
