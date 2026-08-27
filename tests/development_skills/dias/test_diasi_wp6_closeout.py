import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WP6 = ROOT / "docs/programmes/dias-v0-1/wp6"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_id(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def test_live_pilot_is_physically_complete_under_full_reference_assurance() -> None:
    result = load(WP6 / "DIASI_WP6_LIVE_PILOT_PASS.json")
    assert result["decision"] == "PASS"
    assert result["selected_class"] == "DSAI_VIT_RECEIPT_ONLY_V0_1"
    assert result["qualification_writer"] == "VIT_QUALIFICATION_OWNER_LOCAL"
    assert result["writer_generation"] == 2
    assert result["post_merge_completion"]["exact_tree_equal"] is True
    assert result["post_merge_completion"]["four_content_addressed_receipts_present"] is True
    assert result["reference_assurance"]["all_required_checks_passed"] is True
    assert result["reference_assurance"]["canonical_shards_passed"] == result["reference_assurance"]["canonical_shards_denominator"] == 4
    assert result["reference_assurance"]["proof_substitution"] is False
    assert result["unsafe_count"] == 0 and result["blockers"] == []


def test_closeout_bindings_and_current_state() -> None:
    for name in ("DIASI_WP6_CLOSEOUT_VIT_AUTHORITY_MANIFEST.json", "DIASI_WP6_CLOSEOUT_VIT_DEPENDENCY_FRONTIER.json"):
        binding = load(WP6 / name)
        assert binding["logical_id"] == canonical_id(binding["payload"])
    state = load(ROOT / "registries/implementation/dias_v0_1/DIASI_CURRENT_v0_10.json")
    assert state["decision"] == "PASS" and state["next_packet"] == "DIASI-WP7A"
    assert state["old_route"] == "DISABLED_RETAINED_EXACT_SELECTED_CLASS"
    assert state["global_cers_state_changed"] is False
    assert state["non_selected_classes_changed"] is False
    assert state["retirement"] is False and state["proof_substitution"] is False
    assert state["blockers"] == []
