from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None
ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1"


@unittest.skipUnless(FASTAPI_AVAILABLE, "WP2 FastAPI dependency installed only in dedicated console workflow")
class RCNWP2FastAPIContractTests(unittest.TestCase):
    def setUp(self):
        from apps.research_api.app import create_app
        self.app = create_app(fixture_root=PACK)

    def test_openapi_contract_is_get_only_and_exact_paths(self):
        spec = self.app.openapi()
        expected = json.loads((PACK / "openapi_contract.json").read_text(encoding="utf-8"))
        actual = {path: sorted(k for k in value if k in {"get","post","put","patch","delete"}) for path, value in spec["paths"].items()}
        self.assertEqual(expected["expected_paths"], actual)
        for methods in actual.values():
            self.assertFalse(set(expected["forbidden_methods"]).intersection(methods))

    def test_fixture_store_requires_non_evidentiary_authority_neutral_banner(self):
        from apps.research_api.fixture_store import FixtureStore
        banner = FixtureStore(PACK).banner()
        self.assertEqual(banner, {"mode":"FIXTURE_ONLY","data_classification":"SYNTHETIC_FIXTURE","evidence_status":"NON_EVIDENTIARY","authority_effect":"NONE"})

    def test_all_api_routes_are_read_only(self):
        methods = set()
        for route in self.app.routes:
            if route.path.startswith("/api/v1"):
                methods.update(route.methods or ())
        self.assertEqual(methods, {"GET"})

    def test_evidence_cursor_is_backend_owned_and_deterministic(self):
        endpoint = next(r.endpoint for r in self.app.routes if r.path == "/api/v1/evidence")
        page = endpoint(cursor=1, limit=2)
        self.assertEqual([x["evidence_id"] for x in page["payload"]["items"]], ["EV-SYNTH-002","EV-SYNTH-003"])
        self.assertEqual(page["payload"]["next_cursor"], 3)

    def test_capability_triad_remains_separate(self):
        endpoint = next(r.endpoint for r in self.app.routes if r.path == "/api/v1/capabilities")
        rows = endpoint()["payload"]
        c2e = next(row for row in rows if row["capability_id"] == "C2E")
        self.assertFalse(c2e["available"]); self.assertFalse(c2e["authorised"]); self.assertFalse(c2e["active"])
        self.assertEqual(c2e["source_status"], "NOT_MATERIALIZED")


if __name__ == "__main__":
    unittest.main()
