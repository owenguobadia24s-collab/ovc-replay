from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "c2e_v2" / "run_c2e_ag1_restart_equivalence.py"


def _load():
    spec = importlib.util.spec_from_file_location("c2e_ag1_restart_harness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class _EpisodeState:
    episode_id: str
    status: str
    member_ids: list[str]
    phase_ids: list[str]
    boundary_ids: list[str]
    phase_start_time: str
    phase_source_ids: list[str]


class _ReplayEngine:
    def __init__(self, pack_id: str, source_release_id: str) -> None:
        self.pack_id = pack_id
        self.source_release_id = source_release_id
        self.records = []
        self.episodes = {}
        self.active_by_side = {}


class _FakeExecutor:
    EpisodeState = _EpisodeState
    ReplayEngine = _ReplayEngine


def test_constants_pin_exact_gap_and_executor():
    m = _load()
    assert m.RESTART_CUT == "PARTITION_END:ASK"
    assert m.EXPECTED_EXECUTOR_SHA256 == "98e87b229ad82475970b72da169b115aa99eb736926b97ce2c1b339c9028fe6a"
    assert m.EXPECTED_BASELINE_LOGICAL_OUTPUT_SHA256 == "18519e37a16bc1f73148f3764ec1444d1fcd36fce82e9a1d585f712fb02d6988"


def test_restore_closed_ask_partition_from_persisted_prefix():
    m = _load()
    records = [
        {"schema": "c2e_episode_genesis/v0_2", "episode_id": "E1", "side": "ASK"},
        {"schema": "c2e_boundary_event/v0_2", "boundary_event_id": "B1", "episode_ids": ["E1"], "lifecycle_action": "BIRTH"},
        {"schema": "c2e_membership_delta/v0_2", "episode_id": "E1", "frame_id": "F1", "operation": "ADD"},
        {"schema": "c2e_phase_segment/v0_2", "episode_id": "E1", "phase_segment_id": "P1"},
        {"schema": "c2e_boundary_event/v0_2", "boundary_event_id": "B2", "episode_ids": ["E1"], "lifecycle_action": "CENSOR_RELEASE_END"},
    ]
    engine = m.restore_closed_partition_engine(_FakeExecutor, records, pack_id="PACK", source_release_id="SOURCE")
    assert engine.active_by_side == {}
    assert engine.records == records
    assert engine.episodes["E1"].status == "CENSORED"
    assert engine.episodes["E1"].member_ids == ["F1"]
    assert engine.episodes["E1"].phase_ids == ["P1"]
    assert engine.episodes["E1"].boundary_ids == ["B1", "B2"]


def test_partition_boundary_requires_ask_release_end_before_bid():
    m = _load()
    records = [
        {"schema": "c2e_episode_genesis/v0_2", "episode_id": "EA", "side": "ASK"},
        {"schema": "c2e_boundary_event/v0_2", "boundary_event_id": "BA", "episode_ids": ["EA"], "lifecycle_action": "CENSOR_RELEASE_END"},
        {"schema": "c2e_episode_genesis/v0_2", "episode_id": "EB", "side": "BID"},
    ]
    assert m.baseline_partition_boundary(records) == 2
