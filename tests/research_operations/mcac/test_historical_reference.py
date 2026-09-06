from __future__ import annotations

import hashlib
import json
from pathlib import Path


def test_recovered_historical_bytes_match_manifest_and_do_not_claim_parity():
    root = Path(__file__).resolve().parents[3]
    base = root / "docs/programmes/lsiac-v0-1/mcac-v0-1/source-census"
    manifest = json.loads((base / "MCAC_RECOVERED_ARTIFACT_MANIFEST_v0_1.json").read_text())
    recovered = base / "recovered/google-drive"
    for entry in manifest["artifacts"]:
        raw = (recovered / entry["title"]).read_bytes()
        assert len(raw) == entry["size"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    assert manifest["historical_result_artifacts"] == "NOT_RECOVERED"
    assert manifest["computational_parity_authority"] == "NONE_FROM_SOURCE_CODE"
    assert manifest["journal_locator"]["use_class"] == "LOCATOR_ONLY"
