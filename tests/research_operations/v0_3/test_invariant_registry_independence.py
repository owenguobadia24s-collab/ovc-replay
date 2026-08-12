from __future__ import annotations

import ast
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "registries/research_operations/v0_3/C1_METAMORPHIC_INVARIANT_REGISTRY_v0_1.yaml"
METAMORPHIC_PATH = ROOT / "src/ovc/research_operations/v0_3/metamorphic.py"
C1_SOURCE_ROOT = ROOT / "src/ovc/opt_b/c1"
G0_MERGE_COMMIT = "4d701ad78af8597e182565eb301739501b51dff6"
G0_BLOB_SHA = "568309747bbf4e9d368c704893f4a9d0b8af406b"
G3_RETEST_EVIDENCE_PATH = ROOT / "docs/releases/research-operations-foundation-v0-3/ro3-g3-retest/RO3_G3_RETEST_ASSURANCE_EVIDENCE.json"


class InvariantRegistryIndependenceTests(unittest.TestCase):
    def test_registry_is_independent_frozen_and_implementation_free(self) -> None:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(registry["status"], "FROZEN_AT_RO3_G0")
        self.assertEqual(
            registry["source_of_expectations"],
            "INDEPENDENT_CONTRACT_CANON_NOT_IMPLEMENTATION",
        )
        self.assertEqual(registry["formula_count"], 18)
        self.assertEqual(len(registry["invariants"]), 18)
        self.assertIn("ovc.opt_b.c1.formulas", registry["implementation_imports_prohibited"])

    def test_assurance_module_has_no_c1_implementation_import(self) -> None:
        tree = ast.parse(METAMORPHIC_PATH.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertFalse(any(name.startswith("ovc.opt_b.c1") for name in imported))
        self.assertFalse(any(name.endswith(".formulas") for name in imported))

    def test_c1_implementation_cannot_import_assurance_module(self) -> None:
        prohibited = "ovc.research_operations.v0_3.metamorphic"
        for path in sorted(C1_SOURCE_ROOT.glob("*.py")):
            self.assertNotIn(prohibited, path.read_text(encoding="utf-8"), path.as_posix())

    def test_registry_git_blob_is_unchanged_from_ro3_g0(self) -> None:
        relative = REGISTRY_PATH.relative_to(ROOT).as_posix()
        evidence = json.loads(G3_RETEST_EVIDENCE_PATH.read_text(encoding="utf-8"))
        frozen = evidence["frozen_canon"]
        self.assertEqual(G0_MERGE_COMMIT, frozen["invariant_registry_g0_merge_commit"])
        self.assertEqual(G0_BLOB_SHA, frozen["invariant_registry_g0_blob_sha"])
        self.assertTrue(frozen["unchanged_since_ro3_g0"])

        current_blob = subprocess.check_output(
            ["git", "hash-object", relative],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(G0_BLOB_SHA, current_blob)
        self.assertEqual(frozen["invariant_registry_current_blob_sha"], current_blob)


if __name__ == "__main__":
    unittest.main()
