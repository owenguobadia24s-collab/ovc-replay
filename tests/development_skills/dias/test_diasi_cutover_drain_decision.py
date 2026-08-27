import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/programmes/dias-v0-1/cutover-drain"
STATE_ROOT = ROOT / "registries/implementation/dias_v0_1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_id(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_exact_operator_pass_and_scope() -> None:
    decision = load(BASE / "DIASI_G_DGS_CUTOVER_DRAIN_OPERATOR_DECISION.json")
    assert decision["operator_phrase"] == "OVC APPROVE DIASI-G-DGS-CUTOVER-DRAIN PASS"
    assert decision["decision"] == "PASS"
    assert decision["selected_class"] == "DSAI_VIT_RECEIPT_ONLY_V0_1"
    assert decision["authority_after_materialisation"]["implementation_packets"] == ["DIASI-WP6", "DIASI-WP7A"]
    assert "CERS_OR_PES_DELETION_OR_REMOVAL" in decision["authority_after_materialisation"]["denied"]
    assert decision["next_reserved_operator_gate"] == "DIASI-G-DGS-RETIRE-REMOVE"


def test_currentness_is_exact_and_fail_closed() -> None:
    current = load(BASE / "DIASI_G_DGS_CUTOVER_DRAIN_CURRENTNESS_PREFLIGHT.json")
    assert current["repository"]["main_commit"] == "9e357bab97f8dd82be4bb71b51182658696a927b"
    assert current["repository"]["main_tree"] == "51f1b29488b32b896f42df73560c42dd5e3d8364"
    assert current["repository"]["required_check"] == "OVC merge readiness"
    assert current["repository"]["bypass_actors"] == []
    assert current["grt"]["revalidate_immediately_before_physical_write"] is True
    assert current["cers"]["selected_class_is_programme_admission"] is False
    assert current["cers"]["global_state_change_authorised"] is False
    assert current["qualification_ledger"]["unknown_in_flight_count"] == 0
    assert current["open_pull_request_census"]["selected_class_matches"] == []
    assert current["physical_route"]["one_writer"] is True
    assert current["result"] == "PASS_CURRENT_NO_SCOPE_CONFLICT"


def test_vit_bindings_are_canonical() -> None:
    for name in (
        "DIASI_G_DGS_CUTOVER_DRAIN_VIT_AUTHORITY_MANIFEST.json",
        "DIASI_G_DGS_CUTOVER_DRAIN_VIT_DEPENDENCY_FRONTIER.json",
    ):
        binding = load(BASE / name)
        assert binding["logical_id"] == canonical_id(binding["payload"])


def test_state_advances_without_removal_or_proof_substitution() -> None:
    state = load(STATE_ROOT / "DIASI_CURRENT_v0_8.json")
    assert state["next_packet"] == "DIASI-WP6"
    assert state["decision"] == "PASS"
    assert state["authority_scope"] == "WP6_WP7A_EXACT_SELECTED_CLASS_ONLY"
    assert state["retirement"] is False
    assert state["proof_substitution"] is False
    assert state["blockers"] == []
