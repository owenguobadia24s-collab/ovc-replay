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


def test_wp0_census_and_sealed_recovery_manifest_have_exact_locator_parity():
    root = Path(__file__).resolve().parents[3]
    source_root = root / "docs/programmes/lsiac-v0-1/mcac-v0-1"
    census = json.loads(
        (source_root / "wp0/MCAC_WP0_SOURCE_CENSUS_v0_1.json").read_text()
    )
    manifest = json.loads(
        (source_root / "source-census/MCAC_RECOVERED_ARTIFACT_MANIFEST_v0_1.json").read_text()
    )

    census_entries = {
        (entry["title"], entry["size"], entry["sha256"]): entry["drive_file_id"]
        for entry in census["google_drive_search"]["recovered_artifacts"]
    }
    manifest_entries = {
        (entry["title"], entry["size"], entry["sha256"]): entry["drive_id"]
        for entry in manifest["artifacts"]
    }
    assert census_entries == manifest_entries
    assert (
        census["google_drive_search"]["journal"]["sha256"]
        == manifest["journal_locator"]["exact_sha256"]
        == "NOT_RECORDED_WITHOUT_EXACT_BYTES"
    )
