from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
EXPECTED_TOP_LEVEL = {"ovc", "ovc_evidence_store"}
EXPECTED_OVC_PACKAGES = {
    "ovc",
    "ovc.context",
    "ovc.context.occurrence_context",
    "ovc.development",
    "ovc.opt_a",
    "ovc.opt_b",
    "ovc.opt_b.c1",
    "ovc.opt_b.c2",
    "ovc.opt_b.c2_vnext",
    "ovc.opt_b.c2e_v2",
    "ovc.opt_b.market_grammar",
    "ovc.opt_b.sfc",
    "ovc.opt_b.srfd",
    "ovc.programme_genesis",
    "ovc.research_operations",
    "ovc.research_operations.v0_2",
    "ovc.research_operations.v0_3",
    "ovc.research_operations.v0_4",
    "ovc.research_operations.pattern_discovery",
    "ovc.research_operations.mta",
    "ovc.research_operations.mcarb",
}


class ActiveNamespaceAllowlistTests(unittest.TestCase):
    def test_top_level_source_namespaces_match_allowlist(self) -> None:
        actual = {
            path.name
            for path in SRC.iterdir()
            if path.is_dir() and (path / "__init__.py").is_file()
        }
        self.assertEqual(EXPECTED_TOP_LEVEL, actual)

    def test_ovc_package_names_match_foundation_allowlist(self) -> None:
        package_root = SRC / "ovc"
        actual = {
            ".".join(path.parent.relative_to(SRC).parts)
            for path in package_root.rglob("__init__.py")
        }
        self.assertEqual(EXPECTED_OVC_PACKAGES, actual)

    def test_occurrence_context_namespace_is_inactive_nonstructural_only(self) -> None:
        context_init = (SRC / "ovc" / "context" / "__init__.py").read_text(encoding="utf-8").lower()
        occurrence_init = (SRC / "ovc" / "context" / "occurrence_context" / "__init__.py").read_text(encoding="utf-8").lower()
        combined = context_init + occurrence_init
        self.assertIn("inactive", combined)
        self.assertIn("non-structural", combined)
        self.assertIn("no active market", combined)
        self.assertIn("representation-input", combined)
        self.assertIn("validation", combined)
        self.assertIn("c2p", combined)
        self.assertIn("execution authority", combined)

    def test_c2_vnext_namespace_is_shadow_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "c2_vnext" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("shadow-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("execution authority", init_text)

    def test_c2e_v2_namespace_is_shadow_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "c2e_v2" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("shadow-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("execution authority", init_text)
        self.assertIn("no", init_text)
        self.assertIn("real-source replay", init_text)

    def test_market_grammar_namespace_is_shadow_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "market_grammar" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("shadow-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("canonical grammar", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_sfc_namespace_is_inactive_shadow_conformance_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "sfc" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("inactive", init_text)
        self.assertIn("shadow-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("canonical representation", init_text)
        self.assertIn("family", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_srfd_namespace_is_fixture_shadow_only(self) -> None:
        init_text = (SRC / "ovc" / "opt_b" / "srfd" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("shadow-only", init_text)
        self.assertIn("no active market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("canonical representation", init_text)
        self.assertIn("family", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_mta_namespace_is_audit_only(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "mta" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_mcarb_namespace_is_research_only(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "mcarb" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("research-only", init_text)
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("validation", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_programme_genesis_namespace_is_governance_only(self) -> None:
        init_text = (SRC / "ovc" / "programme_genesis" / "__init__.py").read_text(encoding="utf-8").lower()
        self.assertIn("governance-only", init_text)
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("execution authority", init_text)


if __name__ == "__main__":
    unittest.main()
