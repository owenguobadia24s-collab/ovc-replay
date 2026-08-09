from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs" / "releases" / "irof-v0-1" / "irof-wp0"


def load(name: str):
    return json.loads((PACKET / name).read_text(encoding="utf-8"))


def test_wp0_court_record_baseline_and_primitive_paths_exist():
    record = load("IROF_WP0_COURT_RECORD.json")
    assert record["baseline_commit"] == "07d078101daf9645dafa2dea23999f9d1d688133"
    assert record["preexisting_irof_package_conflict"] is False
    for primitive in record["reusable_primitive_git_blobs"].values():
        assert (ROOT / primitive["path"]).exists(), primitive["path"]
        assert len(primitive["git_blob_sha"]) == 40


def test_wp0_inventory_has_unique_stage_ids_and_authority_owners():
    inventory = load("IROF_WP0_CONFORMANCE_INVENTORY.json")
    components = inventory["components"]
    ids = [item["stage_id"] for item in components]
    assert len(ids) == len(set(ids))
    assert all(item["authority_owner"] for item in components)
    assert inventory["no_synonym_policy"] is True


def test_wp0_future_targets_fail_closed_and_validation_stays_locked():
    inventory = load("IROF_WP0_CONFORMANCE_INVENTORY.json")
    future = [item for item in inventory["components"] if item["classification"] == "FUTURE_TARGET_RESERVED"]
    assert future
    assert all(item["register_now"] is False for item in future)
    assert all("NOT_AUTHORISED" in item["real_execution_state"] or "VALIDATION_LOCKED" in item["real_execution_state"] for item in future)
    record = load("IROF_WP0_COURT_RECORD.json")
    assert record["authority_snapshot"]["validation"] == "LOCKED_UNCONSUMED"
    assert record["authority_snapshot"]["srfd_v0_6_token"] == "CONSUMED_NOT_REUSABLE"


def test_wp0_open_prs_are_not_promoted_to_authority():
    record = load("IROF_WP0_COURT_RECORD.json")
    dispositions = record["open_pr_dispositions"]
    assert dispositions["418"] == "HISTORICAL_FIXTURE_ONLY_DRAFT_DO_NOT_IMPORT"
    assert "NO_IROF_AUTHORITY" in dispositions["487"]
    assert "NO_IROF_AUTHORITY" in dispositions["485"]
    assert dispositions["479"] == "C2E_BLOCKER_EVIDENCE_DO_NOT_TREAT_AS_PASS"
