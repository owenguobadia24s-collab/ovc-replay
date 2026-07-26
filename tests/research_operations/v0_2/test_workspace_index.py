from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.v0_2.workspace_index import AccessDenied, build_indexes, validation_metadata_only

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/v0_2/wp1_workspace_index_cases.json"


def _fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_deterministic_index_hash_and_counts():
    fixture = _fixture()
    first = build_indexes(fixture["approved_releases"], fixture["validation_metadata"])
    second = build_indexes(list(reversed(fixture["approved_releases"])), fixture["validation_metadata"])
    assert first["logical_index_hash"] == second["logical_index_hash"]
    assert len(first["workspaces"]) == 2
    assert len(first["observations"]) == 3
    assert first["validation"]["availability"] == "METADATA_ONLY"
    assert first["validation"]["validation_consumption"] == "LOCKED_UNCONSUMED"


def test_validation_denied_before_path_resolution():
    metadata = _fixture()["validation_metadata"] | {"local_path": "C:/forbidden"}
    with pytest.raises(AccessDenied, match="before path resolution"):
        validation_metadata_only(metadata)


def test_validation_cannot_enter_content_build():
    release = _fixture()["validation_metadata"] | {"observations": []}
    with pytest.raises(AccessDenied):
        build_indexes([release])


def test_unknown_role_fails_closed():
    release = _fixture()["approved_releases"][0] | {"role": "UNKNOWN"}
    with pytest.raises(AccessDenied):
        build_indexes([release])


def test_conflicting_duplicate_observation_is_blocked():
    release = _fixture()["approved_releases"][0]
    duplicate = dict(release["observations"][0])
    duplicate["observation_id"] = "FIXED-ID"
    first = dict(duplicate)
    first["clock"] = "15M"
    second = dict(duplicate)
    second["clock"] = "2H_A_L"
    bad = release | {"observations": [first, second]}
    with pytest.raises(ValueError, match="conflicting duplicate"):
        build_indexes([bad])
