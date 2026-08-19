from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.asocs.blind_review import (
    ASOCSBlindFirewallError,
    BLIND_RESOURCE_ROOT,
    REVEAL_RESOURCE_ROOT,
    freeze_blind_record,
    lint_neutral_prompt,
    successor_annotation,
    validate_blind_index,
)

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_blind_and_reveal_resources_are_separate() -> None:
    assert BLIND_RESOURCE_ROOT != REVEAL_RESOURCE_ROOT
    assert not BLIND_RESOURCE_ROOT.startswith(REVEAL_RESOURCE_ROOT)
    assert not REVEAL_RESOURCE_ROOT.startswith(BLIND_RESOURCE_ROOT)


def test_blind_index_allows_only_case_navigation_and_source_native_visual() -> None:
    allowed = {
        "case_id": "ASOCS.BLIND.abc",
        "navigation_window": {"start": "2026-01-01", "end": "2026-01-02"},
        "source_native_visual_ref": "sha256:abc",
    }
    assert validate_blind_index(allowed) == allowed
    leaking = {**allowed, "stratum": "LEVEL", "c2": {"machine": "x"}}
    with pytest.raises(ASOCSBlindFirewallError, match="BLIND_METADATA_LEAK"):
        validate_blind_index(leaking)


def test_neutral_prompt_lint_rejects_leading_ovc_vocabulary() -> None:
    assert lint_neutral_prompt("Describe visible price movement, range width and change in character.") == []
    hits = lint_neutral_prompt("Is this a C2 level or breakout episode?")
    assert "c2" in hits
    assert "level" in hits
    assert "breakout" in hits
    assert "episode" in hits


def test_blind_record_is_append_only_via_successor_annotation() -> None:
    base = freeze_blind_record({"case_id": "A", "neutral_description": "Price moved up then paused."})
    successor = successor_annotation(base, {"clarification": "Approximate visible high corrected."})
    assert base["frozen_before_reveal"] is True
    assert successor["predecessor_blind_record_sha256"] == base["blind_record_sha256"]
    assert successor["mutates_predecessor"] is False


def test_wp7_infra_stops_before_human_review_and_g5() -> None:
    state = _json("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_9_WP7_INFRA_PREBUILD.json")
    assert state["status"] == "IMPLEMENTED"
    assert state["human_review_started"] is False
    assert state["g5_status"] == "NOT_STARTED"
    assert state["stop_boundary"] == "STOP_BEFORE_WP7_HUMAN_REVIEW"
