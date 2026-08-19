from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.asocs.sampling import (
    blind_case_id,
    deduplicate_frames,
    freeze_case_order,
    select_frame,
    select_hidden_repeats,
    selection_score,
)

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


POP = "f" * 64
NONCE = "31aa07a7de93f1f70fa5b500eeae5159040965079e9bc11ab4ed1c43d93ea158"


def test_score_is_exact_concatenated_sha256_and_reproducible() -> None:
    import hashlib
    expected = hashlib.sha256((POP + NONCE + "S" + "A").encode("utf-8")).hexdigest()
    assert selection_score(POP, NONCE, "S", "A") == expected
    assert selection_score(POP, NONCE, "S", "A") == expected


def test_stratum_exhaustion_is_full_census_and_dedup_preserves_memberships() -> None:
    objects = [{"object_id": "A"}, {"object_id": "B"}]
    a = select_frame(objects, population_hash=POP, nonce_hex=NONCE, stratum_id="LEVEL", target_size=5)
    b = select_frame(objects, population_hash=POP, nonce_hex=NONCE, stratum_id="NULL", target_size=1)
    assert a["exhaustion"] == "STRATUM_EXHAUSTED_FULL_CENSUS"
    units = deduplicate_frames([a, b])
    assert len(units) == 2
    assert any(len(x["stratum_memberships"]) == 2 for x in units)


def test_blind_ids_and_order_do_not_encode_stratum() -> None:
    frames = [
        {"stratum_id": "LEVEL", "object_ids": ["A"], "target_size": 1},
        {"stratum_id": "GAP", "object_ids": ["B"], "target_size": 1},
    ]
    units = deduplicate_frames(frames)
    ordered = freeze_case_order(units, POP, NONCE)
    assert all(x["blind_case_id"].startswith("ASOCS.BLIND.") for x in ordered)
    assert all("LEVEL" not in x["blind_case_id"] and "GAP" not in x["blind_case_id"] for x in ordered)
    assert blind_case_id(POP, NONCE, "A") == blind_case_id(POP, NONCE, "A")


def test_hidden_repeat_and_session_choices_are_frozen_inside_plan_range() -> None:
    config = _json("registries/research_operations/asocs/ASOCSI_WP6_PREBUILD_SAMPLING_CONFIG_v0_1.json")
    units = freeze_case_order(
        [{"review_unit_id": str(i), "stratum_memberships": ["BASE"]} for i in range(40)],
        POP, NONCE,
    )
    repeats = select_hidden_repeats(
        units, POP, NONCE, fraction=config["hidden_repeat_fraction"]
    )
    assert len(repeats) == 2
    assert config["hidden_repeat_fraction"] == 0.05
    assert config["default_session_cap_primary_anchor_equivalents"] == 25
    assert config["census_outcome_used_to_choose_operational_values"] is False


def test_prebuild_does_not_freeze_g4_without_g3_census() -> None:
    state = _json("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_8_WP6_PREBUILD.json")
    assert state["status"] == "IMPLEMENTED"
    assert state["gate_status"] == "NOT_EVALUATED"
    assert "ASOCSI_G3_CENSUS_FREEZE_REQUIRED" in state["blockers"]
    assert state["human_review_started"] is False
