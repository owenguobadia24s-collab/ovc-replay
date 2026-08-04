from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.smoke_pipeline import run_canonical_smoke

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2/vnext/c2ar_wp5_5_canonical_smoke_v0_1.json"


class SmokeManifestEmissionTests(unittest.TestCase):
    def test_emit_canonical_manifest_for_gate_evidence(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        manifest = run_canonical_smoke(fixture)
        self.assertEqual("PASS", manifest["status"])
        print("C2AR_WP5_5_SMOKE_MANIFEST=" + json.dumps(manifest, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
