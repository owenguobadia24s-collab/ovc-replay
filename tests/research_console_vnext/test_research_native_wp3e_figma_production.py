from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "research_console_vnext" / "src"


class ProductionFigmaConformance(unittest.TestCase):
    def test_production_routes_are_research_native_and_market_is_legacy_only(self):
        router = (APP / "app" / "router.tsx").read_text()
        self.assertIn('Navigate to="/structure"', router)
        self.assertIn('{path:"/market",element:<AppShell/>', router)
        for route in ["/structure", "/research", "/evidence", "/control"]:
            self.assertIn(f'{{path:"{route}",element:<ProductionConsole/>}}', router)

    def test_production_console_preserves_source_authority_and_fail_honest_semantics(self):
        source = (APP / "production" / "ProductionConsole.tsx").read_text()
        for marker in [
            "SYNTHETIC_FIXTURE", "NON-EVIDENTIARY", "AUTHORITY EFFECT", "AVAILABLE", "AUTHORISED", "ACTIVE",
            "FVT", "MISSINGNESS", "DENOMINATOR", "C2 STATE MATRIX", "C2E EPISODE / CHRONOLOGY RAIL",
            "REPRESENTATION × METHOD COMPARISON", "NO METHOD SELECTOR AUTHORITY", "NO_STABLE_FAMILY",
            "Object lineage / dependencies / QA projection", "display_projection non-canonical",
            "PROGRAMME / PACKET / GATE LEDGER", "G3V · OPERATOR REQUIRED", "NO WRITE SURFACE", "REAL SOURCE", "DENIED",
        ]:
            self.assertIn(marker, source)
        self.assertNotIn("Math.random", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("localStorage", source)
        self.assertNotIn("sessionStorage", source)

    def test_production_tokens_are_semantic_not_legacy_colour_aliases(self):
        tokens = (APP / "design" / "productionTokens.css").read_text()
        for token in [
            "--ovc-surface-canvas", "--ovc-border-focus", "--ovc-text-primary",
            "--ovc-domain-investigate", "--ovc-domain-research", "--ovc-domain-evidence", "--ovc-domain-control",
            "--ovc-state-pass", "--ovc-state-warn", "--ovc-state-error", "--ovc-state-residual", "--ovc-state-null",
            "--ovc-rail:56px", "--ovc-header:56px", "--ovc-context:48px", "--ovc-navigator:236px",
            "--ovc-inspector:320px", "--ovc-dock:144px", "--ovc-status:48px",
        ]:
            self.assertIn(token, tokens)
        self.assertNotIn("--rcn-green", tokens)
        self.assertNotIn("--rcn-amber", tokens)

    def test_responsive_contract_encodes_figma_geometry_and_drawer_non_equivalence(self):
        responsive = (APP / "production" / "productionResponsive.css").read_text()
        for marker in [
            "@media (max-width:1550px)", ".pc-header{left:48px;height:48px}",
            ".pc-navigator{left:48px;top:90px;width:200px;bottom:140px", ".pc-primary{left:248px;right:280px;top:90px;bottom:140px",
            ".pc-inspector{right:0;top:90px;width:280px;bottom:140px", ".pc-dock{left:48px;bottom:40px;height:100px",
            "@media (max-width:1320px)", ".pc-navigator{left:48px;top:90px;width:176px;bottom:130px",
            ".pc-primary{left:224px;right:0;top:90px;bottom:130px", ".pc-inspector{right:16px;top:108px;width:268px;height:428px",
            'content:"INSPECTOR DRAWER · OPEN"', "drawer changes placement only — source identity, authority and scientific meaning are unchanged",
        ]:
            self.assertIn(marker, responsive)

    def test_visual_acceptance_adds_production_masters_without_weakening_legacy_fixture_evidence(self):
        legacy = (ROOT / "apps" / "research_console_vnext" / "tests" / "e2e" / "fixture-visual.spec.ts").read_text()
        production = (ROOT / "apps" / "research_console_vnext" / "tests" / "e2e" / "production-visual.spec.ts").read_text()
        self.assertIn("WP3G measures central-scene pixel distance", legacy)
        self.assertIn('test(`production ${domain} master is exact at 1920x1080`', production)
        for domain in ["Investigate", "Research", "Evidence", "Control"]:
            self.assertIn(f'"{domain}"', production)
        for marker in [
            "Investigate responsive master is exact at 1440x810",
            "Investigate responsive master uses controlled inspector drawer at 1280x720",
            "production-domain-rail", "production-primary-canvas", "production-evidence-inspector", "production-evidence-dock",
        ]:
            self.assertIn(marker, production)


if __name__ == "__main__":
    unittest.main()
