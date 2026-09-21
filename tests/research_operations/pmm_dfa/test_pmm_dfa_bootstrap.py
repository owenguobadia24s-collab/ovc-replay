import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

STATE = ROOT / "records/research_operations/pmm_dfa/PMM_DFA_PROGRAMME_STATE_v0_1.json"
CANDIDATES = ROOT / "registries/research/pmm_dfa/PMM_DFA_R1T_CANDIDATE_PROPOSALS_v0_1.json"
CHALLENGE = ROOT / "docs/programmes/pmm-dfa-v0-1/r1t/PMM_DFA_R1T_CHALLENGE_PACK_PROPOSAL_v0_1.json"
AUTHORITY = ROOT / "docs/programmes/pmm-dfa-v0-1/r1t/PMM_DFA_R1T_G0_AUTHORITY_MANIFEST_v0_1.json"
SOURCES = ROOT / "docs/programmes/pmm-dfa-v0-1/bootstrap/PMM_DFA_SOURCE_BINDINGS_v0_1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_bootstrap_fail_closed_authority():
    state = load(STATE)
    assert state["programme_id"] == "OVC-PMM-0001"
    assert state["current_gate"] == "PMM-DFA-R1T-G0"
    assert state["gate_status"] == "OPERATOR_REQUIRED_NOT_APPROVED"
    assert state["candidate_freeze"] == "NONE"
    assert state["development_access"] == "LOCKED_UNCONSUMED"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["probability_risk_exposure_trading_execution"] == "NONE"


def test_candidate_set_is_exactly_six_unique_proposals():
    doc = load(CANDIDATES)
    ids = [c["candidate_id"] for c in doc["candidates"]]
    assert doc["status"] == "PROPOSAL_ONLY_NOT_FROZEN"
    assert doc["freeze_state"] == "NONE"
    assert doc["candidate_count"] == 6 == len(ids)
    assert len(set(ids)) == 6
    assert ids == ["R1T-N01", "R1T-C01", "R1T-C02", "R1T-C03", "R1T-C04", "R1T-C05"]


def test_gate_and_challenge_pack_do_not_self_authorise():
    challenge = load(CHALLENGE)
    authority = load(AUTHORITY)
    assert challenge["status"] == "PROPOSAL_ONLY_NOT_FROZEN"
    assert "CANDIDATE_FREEZE" in challenge["explicit_non_grants"]
    assert "DEVELOPMENT_ACCESS" in challenge["explicit_non_grants"]
    assert authority["gate_class"] == "OPERATOR_REQUIRED"
    assert authority["status"] == "NOT_APPROVED"
    assert authority["exact_operator_command_for_reserved_delta"] == "OVC APPROVE PMM-DFA-R1T-G0"


def test_source_hashes_are_exact_sha256_strings():
    sources = load(SOURCES)
    hashes = []
    for item in sources["controlling_external_artifacts"]:
        hashes.append(item["sha256"])
    for item in sources["primary_source_identities"].values():
        if "sha256" in item:
            hashes.append(item["sha256"])
    assert hashes
    assert all(len(h) == 64 and all(ch in "0123456789abcdef" for ch in h) for h in hashes)
