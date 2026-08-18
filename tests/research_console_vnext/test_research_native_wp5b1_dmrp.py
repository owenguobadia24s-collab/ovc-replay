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
from ovc.console_vnext.application.research_wp5b1_real import build_wp5b1_dmrp_real_envelope

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_BINDINGS = ROOT / "registries" / "research_console_vnext" / "research_native" / "wp5b1_dmrp_source_bindings_v1.json"
REAL_BINDINGS = ROOT / "registries" / "research_console_vnext" / "research_native" / "wp5b1_dmrp_real_source_bindings_v1.json"
PRESENTATION = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1" / "research_wp5b1.json"
FIXTURE_SCHEMA = ROOT / "schemas" / "research_console_vnext" / "wp5b1_dmrp_snapshot_v1.schema.json"
REAL_SCHEMA = ROOT / "schemas" / "research_console_vnext" / "wp5b1_dmrp_real_snapshot_v1.schema.json"
ROUTES = ROOT / "registries" / "research_console_vnext" / "research_native" / "route_registry_v2.json"
COMPONENT = ROOT / "apps" / "research_console_vnext" / "src" / "production" / "DMRPWorkbench.tsx"
ROUTER = ROOT / "apps" / "research_console_vnext" / "src" / "app" / "router.tsx"
CLIENT = ROOT / "apps" / "research_console_vnext" / "src" / "api" / "client.ts"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class WP5B1FixtureServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bindings = load(FIXTURE_BINDINGS)
        self.presentation = load(PRESENTATION)

    def build(self, *, bindings=None, presentation=None):
        return build_wp5b1_dmrp_snapshot(
            repository_root=ROOT,
            bindings=bindings or self.bindings,
            presentation=presentation or self.presentation,
        )

    def test_fixture_route_remains_non_evidentiary(self) -> None:
        value = self.build()
        self.assertEqual("FIXTURE_ONLY", value["mode"])
        self.assertEqual("PATH_1_EMPIRICAL", value["path1"]["research_mode"])
        self.assertFalse(value["source_preflight"]["first_new_real_research_source"])
        self.assertEqual("NOT_ESTABLISHED", value["cross_mode"][0]["independence"])
        self.assertFalse(value["cross_mode"][0]["identity_merge"])

    def test_fixture_authority_and_blob_drift_fail_closed(self) -> None:
        bad = copy.deepcopy(self.bindings)
        bad["first_new_real_research_source"] = True
        with self.assertRaises(AuthorityDenied):
            self.build(bindings=bad)
        bad = copy.deepcopy(self.bindings)
        bad["sources"][0]["git_blob_sha"] = "0" * 40
        with self.assertRaises(SourceConflict):
            self.build(bindings=bad)


class WP5B1RealSourceTests(unittest.TestCase):
    def build(self, *, bindings=None):
        return build_wp5b1_dmrp_real_envelope(
            repository_root=ROOT,
            bindings=bindings or REAL_BINDINGS,
        )

    def test_exact_operator_gate_and_owner_sources_are_bound(self) -> None:
        registry = load(REAL_BINDINGS)
        self.assertEqual("DMRP", registry["owner"])
        self.assertEqual("GET_ONLY", registry["transport"])
        self.assertEqual("NONE", registry["writes"])
        self.assertTrue(registry["first_new_real_research_source"])
        self.assertEqual("PROHIBITED", registry["source_admission_transitivity"])
        self.assertEqual("PROHIBITED_IN_REAL_MODE", registry["fixture_fallback"])
        decision = registry["gate_decision"]
        self.assertEqual(decision["git_blob_sha"], git_blob_sha(ROOT / decision["path"]))
        self.assertEqual("PASS", load(ROOT / decision["path"])["decision"])
        for source in registry["sources"]:
            self.assertEqual(source["git_blob_sha"], git_blob_sha(ROOT / source["path"]))
            self.assertEqual(source["schema"], load(ROOT / source["path"])["schema"])

    def test_real_snapshot_preserves_owner_state_without_fabricating_candidate(self) -> None:
        envelope = self.build()
        self.assertEqual("REAL_SOURCE_READ_ONLY", envelope["real_source_banner"]["mode"])
        self.assertEqual("RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]", envelope["real_source_banner"]["presentation_authority"])
        self.assertEqual("PROHIBITED", envelope["real_source_banner"]["source_admission_transitivity"])
        value = envelope["payload"]
        self.assertEqual("OWNER_SOURCE_BOUND", value["evidence_status"])
        self.assertEqual("PATH_1_EMPIRICAL", value["path1"]["research_mode"])
        self.assertEqual("DISCOVERY", value["path1"]["research_role"])
        self.assertEqual("LOCKED_UNCONSUMED", value["path1"]["validation_access_state"])
        self.assertEqual("NONE", value["candidate_generation"]["candidate_freeze"])
        self.assertIsNone(value["candidate_generation"]["series_id"])
        self.assertIsNone(value["candidate_generation"]["generation"])
        self.assertEqual({}, value["candidate_generation"]["membership"])

    def test_missing_exposure_does_not_become_independence(self) -> None:
        value = self.build()["payload"]
        self.assertEqual([], value["cross_mode"])
        self.assertEqual("UNKNOWN", value["cross_mode_state"]["independence"])
        self.assertFalse(value["cross_mode_state"]["missing_exposure_implies_independence"])
        self.assertFalse(value["presentation_guardrails"]["missing_exposure_implies_independence"])

    def test_no_transitive_source_or_scientific_authority(self) -> None:
        value = self.build()["payload"]
        guard = value["presentation_guardrails"]
        self.assertEqual("PROHIBITED", guard["source_admission_transitivity"])
        self.assertEqual("PROHIBITED", guard["candidate_construction"])
        self.assertEqual("PROHIBITED", guard["candidate_repair"])
        self.assertEqual("NONE", guard["candidate_promotion"])
        self.assertEqual("NONE", guard["ranking"])
        self.assertEqual("LOCKED_UNCONSUMED", guard["validation_consumption"])
        self.assertEqual("NONE", guard["writes"])

    def test_gate_or_owner_blob_drift_fails_closed(self) -> None:
        registry = load(REAL_BINDINGS)
        bad = copy.deepcopy(registry)
        bad["gate_decision"]["git_blob_sha"] = "0" * 40
        with self.assertRaises(SourceConflict):
            self.build(bindings=bad)
        bad = copy.deepcopy(registry)
        bad["source_admission_transitivity"] = "ALLOWED"
        with self.assertRaises(AuthorityDenied):
            self.build(bindings=bad)


class WP5B1RepositoryContractTests(unittest.TestCase):
    def test_fixture_and_real_contracts_are_explicit(self) -> None:
        fixture_schema = load(FIXTURE_SCHEMA)
        real_schema = load(REAL_SCHEMA)
        routes = load(ROUTES)
        component = COMPONENT.read_text(encoding="utf-8")
        router = ROUTER.read_text(encoding="utf-8")
        client = CLIENT.read_text(encoding="utf-8")
        self.assertEqual("ovc-rcn-rn-wp5b1-dmrp-snapshot/v1", fixture_schema["$id"])
        self.assertEqual("ovc-rcn-rn-wp5b1-dmrp-real-snapshot/v1", real_schema["$id"])
        route = routes["wp5b1_dmrp"]
        self.assertTrue(route["first_new_real_research_source"])
        self.assertEqual("RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]", route["gate_id"])
        self.assertEqual("PROHIBITED", route["source_admission_transitivity"])
        self.assertFalse(route["missing_exposure_implies_independence"])
        self.assertIn('{path:"/research/dmrp",element:<DMRPWorkbench/>}', router)
        self.assertIn('"/research/dmrp/snapshot"', client)
        self.assertIn('method: "GET"', client)
        self.assertIn("DMRP_REAL_SOURCE_AUTHORITY_VIOLATION", client)
        self.assertIn("missing exposure does not imply independence", component)
        self.assertNotIn("Math.random", component)


@unittest.skipIf(
    importlib.util.find_spec("fastapi") is None,
    "FastAPI dependency not installed in generic repository environment",
)
class WP5B1ApiTests(unittest.TestCase):
    def test_fixture_mode_stays_fixture_and_get_only(self) -> None:
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app

        client = TestClient(create_app())
        response = client.get("/api/v1/research/dmrp/snapshot")
        self.assertEqual(200, response.status_code)
        self.assertEqual("FIXTURE_ONLY", response.json()["fixture_banner"]["mode"])
        self.assertEqual(405, client.post("/api/v1/research/dmrp/snapshot").status_code)

    def test_real_mode_is_dmrp_owner_bound_with_no_fixture_fallback(self) -> None:
        from fastapi.testclient import TestClient
        from apps.research_api.app import create_app

        owner_bindings = ROOT / "registries" / "research_console_vnext" / "research_native" / "owner_read_projection_bindings_v1.json"
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(
                source_mode="REAL",
                real_source_root=Path(temporary),
                real_source_bindings=owner_bindings,
            )
            client = TestClient(app)
            denied = client.get("/api/v1/research/dmrp/snapshot?role=VALIDATION")
            self.assertEqual(403, denied.status_code)
            response = client.get("/api/v1/research/dmrp/snapshot")
            self.assertEqual(200, response.status_code)
            body = response.json()
            self.assertNotIn("fixture_banner", body)
            self.assertEqual("REAL_SOURCE_READ_ONLY", body["real_source_banner"]["mode"])
            self.assertEqual("PROHIBITED", body["real_source_banner"]["fixture_fallback"])
            self.assertEqual("DMRP_OWNER_COURT_RECORD", body["real_source_banner"]["data_classification"])
            self.assertEqual("UNKNOWN", body["payload"]["cross_mode_state"]["independence"])
            self.assertIsNone(body["payload"]["candidate_generation"]["series_id"])
            self.assertEqual(405, client.post("/api/v1/research/dmrp/snapshot").status_code)
