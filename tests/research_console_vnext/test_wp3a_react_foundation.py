from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "research_console_vnext"


class RCNWP3AFoundationTests(unittest.TestCase):
    def test_toolchain_is_exactly_pinned_and_matches_lock(self) -> None:
        package = json.loads((APP / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "artifacts" / "research_console_vnext" / "RCN_TOOLCHAIN_LOCK_v0_1.json").read_text(encoding="utf-8"))["tools"]
        direct = {**package["dependencies"], **package["devDependencies"]}
        for name, version in direct.items():
            self.assertFalse(version.startswith(("^", "~", ">", "<", "*")), (name, version))
            self.assertEqual(lock[name], version)
        self.assertEqual(package["dependencies"]["@tanstack/react-query"], lock["@tanstack/react-query"])

    def test_fixture_only_shell_and_route_foundation(self) -> None:
        shell = (APP / "src" / "app" / "AppShell.tsx").read_text(encoding="utf-8")
        router = (APP / "src" / "app" / "router.tsx").read_text(encoding="utf-8")
        self.assertIn("SYNTHETIC FIXTURE", shell)
        self.assertIn("NON-EVIDENTIARY", shell)
        self.assertIn("AUTHORITY EFFECT NONE", shell)
        self.assertIn("Real-source routes: DENIED UNTIL RCN-G4", shell)
        for route in ("market", "structure", "research", "evidence", "control"):
            self.assertIn(route, router)

    def test_investigation_state_is_browser_local_non_evidentiary_and_revalidates(self) -> None:
        state = (APP / "src" / "features" / "investigations" / "state.ts").read_text(encoding="utf-8")
        tabs = (APP / "src" / "features" / "investigations" / "InvestigationTabs.tsx").read_text(encoding="utf-8")
        combined = state + tabs
        self.assertIn("localStorage", combined)
        self.assertIn("NON_EVIDENTIARY", combined)
        self.assertIn("useSearchParams", combined)
        self.assertIn("invalidateQueries", combined)

    def test_no_streamlit_or_real_source_shortcut_in_executable_frontend(self) -> None:
        paths = [path for path in (APP / "src").rglob("*.ts*") if "generated" not in path.parts]
        source = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
        self.assertNotIn("streamlit", source)
        self.assertNotIn("dukascopy", source)
        self.assertNotIn('"/validation', source)
        self.assertNotIn("r2://", source)

    def test_openapi_generation_inputs_expose_expected_read_only_paths(self) -> None:
        openapi = (APP / "openapi.console-vnext.v1.json").read_text(encoding="utf-8")
        self.assertIn('"/api/v1/identity"', openapi)
        self.assertIn('"/api/v1/capabilities"', openapi)
        self.assertIn('"/api/v1/fixture/investigations"', openapi)
        self.assertIn("CapabilityDependencyStatus", openapi)


if __name__ == "__main__":
    unittest.main()
