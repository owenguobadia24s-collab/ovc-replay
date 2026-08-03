from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
EXPECTED_TOP_LEVEL = {"ovc", "ovc_evidence_store"}
EXPECTED_OVC_PACKAGES = {
    "ovc",
    "ovc.development",
    "ovc.opt_a",
    "ovc.opt_b",
    "ovc.opt_b.c1",
    "ovc.opt_b.c2",
    "ovc.programme_genesis",
    "ovc.research_operations",
    "ovc.research_operations.v0_2",
    "ovc.research_operations.v0_3",
    "ovc.research_operations.v0_4",
    "ovc.research_operations.pattern_discovery",
    "ovc.research_operations.mta",
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

    def test_mta_namespace_is_audit_only(self) -> None:
        init_text = (SRC / "ovc" / "research_operations" / "mta" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("semantic-promotion", init_text)
        self.assertIn("execution authority", init_text)

    def test_programme_genesis_namespace_is_governance_only(self) -> None:
        init_text = (SRC / "ovc" / "programme_genesis" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("governance-only", init_text)
        self.assertIn("no market", init_text)
        self.assertIn("selector", init_text)
        self.assertIn("execution authority", init_text)


if __name__ == "__main__":
    unittest.main()
