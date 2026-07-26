from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "opt_b" / "freeze_c2_g5_candidate.py"
spec = importlib.util.spec_from_file_location("freeze_c2_g5_candidate", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class C2G5CandidateFreezeTests(unittest.TestCase):
    def test_exact_source_identity_is_pinned(self):
        self.assertEqual(module.SOURCE["artifact_id"], 8634383302)
        self.assertEqual(module.SOURCE["workflow_run_id"], 30210057332)
        self.assertEqual(module.SOURCE["artifact_archive_sha256"], "b8f993f733aed75e488aa60883f00a53596c15e5cd6c14edb787fc3bc12df62f")
        self.assertEqual(module.EXPECTED, {"files": 24, "bytes": 872_839_722, "states": 404_434, "transitions": 323_910})

    def test_candidate_identities_are_role_aware(self):
        self.assertEqual(module.ROLES["discovery"]["release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")
        self.assertEqual(module.ROLES["development"]["release_id"], "OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1")
        self.assertIn("DISCOVERY.2021_2023", module.ROLES["discovery"]["manifest_id"])
        self.assertIn("DEVELOPMENT.2024", module.ROLES["development"]["manifest_id"])

    def test_canonical_json_and_hashing_are_deterministic(self):
        left = {"b": 2, "a": 1}
        right = json.loads('{"a":1,"b":2}')
        self.assertEqual(module.cbytes(left), module.cbytes(right))
        self.assertEqual(module.hfile(self._write_temp("same\n")), module.hfile(self._write_temp("same\n")))

    def test_scope_conversion(self):
        self.assertEqual(module.scope_from_name("GBPUSD-15M-WITH-2H-PARENT-v0_1.jsonl"), "GBPUSD-15M-WITH-2H-PARENT-v0.1")
        self.assertEqual(module.scope_from_name("GBPUSD-2H-A-L-LOCAL-v0_1.jsonl"), "GBPUSD-2H-A-L-LOCAL-v0.1")

    def test_tree_inventory_is_stably_sorted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "z").mkdir()
            (root / "z/b.txt").write_text("b\n")
            (root / "a.txt").write_text("a\n")
            inv = module.inventory(root)
            self.assertEqual([x["path"] for x in inv], ["a.txt", "z/b.txt"])
            self.assertTrue(all(len(x["sha256"]) == 64 for x in inv))

    def _write_temp(self, value: str) -> Path:
        td = tempfile.mkdtemp()
        p = Path(td) / "value.txt"
        p.write_text(value)
        self.addCleanup(lambda: __import__("shutil").rmtree(td, ignore_errors=True))
        return p


if __name__ == "__main__":
    unittest.main()
