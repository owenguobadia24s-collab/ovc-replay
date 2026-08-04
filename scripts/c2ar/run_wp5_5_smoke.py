#!/usr/bin/env python3
"""Emit the deterministic C2AR-WP5.5 canonical smoke manifest."""
from __future__ import annotations

import json
from pathlib import Path

from ovc.opt_b.c2_vnext.smoke_pipeline import run_canonical_smoke

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/opt_b/c2/vnext/c2ar_wp5_5_canonical_smoke_v0_1.json"


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    manifest = run_canonical_smoke(fixture)
    print("C2AR_WP5_5_SMOKE_MANIFEST=" + json.dumps(manifest, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
