from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/governance/materialize_pgn_wp2e_bundle.py"


def load_module():
    spec = importlib.util.spec_from_file_location("materialize_pgn_wp2e_bundle", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PGNWP2ERegenerationEvidenceTests(unittest.TestCase):
    def test_emit_changed_bundle_records(self) -> None:
        module = load_module()
        manifest, _ = module.build_bundle(ROOT)
        print("PGN_REGEN_MANIFEST=" + json.dumps(manifest, sort_keys=True, separators=(",", ":")))
        directory = ROOT / "registries/governance/programme_genesis/pgn_census"
        for name in (
            "PGN_REPOSITORY_GENESIS_OBJECTS_v0_2_01.jsonc",
            "PGN_REPOSITORY_GENESIS_OBJECTS_v0_2_04.jsonc",
            "PGN_REPOSITORY_GENESIS_OBJECTS_v0_2_05.jsonc",
            "PGN_REPOSITORY_GENESIS_COVERAGE_UNRESOLVED_v0_2.jsonc",
        ):
            value = json.loads((directory / name).read_text(encoding="utf-8"))
            print("PGN_REGEN_FILE=" + name + ":" + json.dumps(value, sort_keys=True, separators=(",", ":")))
        self.assertEqual(108, manifest["object_count"])


if __name__ == "__main__":
    unittest.main()
