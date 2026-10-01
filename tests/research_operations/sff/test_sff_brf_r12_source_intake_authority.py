import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R12 = ROOT / "docs/programmes/sff-v0-1/brf/r12"
STATE = ROOT / "records/research_operations/sff/SFF_BRF_PROGRAMME_STATE_v0_1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_operator_pass_is_exact_and_bounded():
    decision = read(R12 / "SFF_BRF_GNEW_SOURCE_INTAKE_OPERATOR_DECISION_v0_1.json")
    assert decision["gate_id"] == "SFF-BRF-GNEW-SOURCE-INTAKE"
    assert decision["decision"] == "PASS"
    assert decision["operator_command"] == "OVC APPROVE SFF-BRF-GNEW-SOURCE-INTAKE"
    assert decision["repository_effective_on_main_merge"] is True
    for denied in ("SEMANTIC_PROMOTION", "MODEL_PROMOTION", "ACTIVE_VALIDATION", "RISK", "EXPOSURE", "TRADING", "EXECUTION", "AGENT_WRITE"):
        assert denied in decision["denies"]


def test_source_selection_is_frozen_before_bytes_and_nonadaptive():
    freeze = read(R12 / "SFF_BRF_R12_SOURCE_SELECTION_FREEZE_v0_1.json")
    assert freeze["status"] == "FROZEN_BEFORE_NEW_SOURCE_BYTES_OPEN"
    assert freeze["provider"] == "FXCM_PUBLIC_CANDLEDATA"
    assert freeze["instrument"] == "GBPUSD"
    assert freeze["side"] == "BID"
    assert freeze["target_clock"] == "15M"
    assert freeze["raw_periodicity"] == "m1"
    assert freeze["selected_calendar_years"] == [2014, 2016, 2018, 2019]
    assert "no adaptive stopping" in freeze["selection_rule"]
    assert "NO_BRF_EXACT_JOINT_OUTCOME_INSPECTION" in freeze["event_firewall"]


def test_authority_and_dependency_frontier_identities_are_exact():
    authority = read(R12 / "SFF_BRF_R12_AUTHORITY_MANIFEST_v0_1.json")
    frontier = read(R12 / "SFF_BRF_R12_DEPENDENCY_FRONTIER_v0_1.json")
    state = read(STATE)
    assert state["authority_manifest_id"] == canonical_sha256(authority)
    assert state["dependency_frontier_id"] == canonical_sha256(frontier)
    assert frontier["blockers"] == []
    assert frontier["next_packet"] == "SFF-BRF-R12-SOURCE-BINDING"


def test_programme_state_stops_short_of_reserved_authority():
    state = read(STATE)
    assert state["packet_id"] == "SFF-BRF-R12"
    assert state["status"] == "APPROVED_SOURCE_SELECTION_FROZEN_PENDING_SOURCE_BINDING"
    assert state["authority_required"] == "SATISFIED_BY_DIRECT_OPERATOR_COMMAND"
    assert state["support_baseline"] == {"uncensored_opportunities": 5, "exact_joint_events": 3}
    assert state["next_packet"] == "SFF-BRF-R12-SOURCE-BINDING"
    assert "CALIBRATED_PROBABILITY_BEFORE_100_20_SUPPORT" in state["explicit_non_grants"]
