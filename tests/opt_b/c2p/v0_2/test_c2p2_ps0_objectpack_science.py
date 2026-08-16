import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CANDIDATES = ROOT / "registries/opt_b/c2p/v0_2/C2P2_PS0_OBJECTPACK_CANDIDATES_v0_1.json"
FIXTURES = ROOT / "fixtures/opt_b/c2p/v0_2/research/C2P2_PS0_OBJECTPACK_DISCRIMINATION_FIXTURES_v0_1.json"
PREREG = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-ps0/C2P2_PS0_RS0_PREREGISTRATION_v0_1.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _logical_hash(candidate):
    payload = dict(candidate)
    expected = payload.pop("candidate_logical_hash")
    actual = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return expected, actual


def test_ps0_candidates_are_immutable_activation_ineligible_and_unselected():
    registry = _load(CANDIDATES)
    assert registry["selection_state"] == "NONE_SELECTED"
    assert registry["active_object_pack_id"] is None
    assert registry["real_source_evaluated"] is False
    assert registry["validation_consumed"] is False
    assert registry["non_authority"]["preferred_candidate"] is None
    assert registry["non_authority"]["winner"] is None
    assert registry["non_authority"]["selector"] is None
    assert len(registry["candidates"]) >= 3
    for candidate in registry["candidates"]:
        assert candidate["status"] == "UNSELECTED_RESEARCH_CANDIDATE"
        assert candidate["activation_eligible"] is False
        expected, actual = _logical_hash(candidate)
        assert actual == expected
        forbidden = set(candidate["forbidden"])
        assert {"family", "C3_semantics", "OPT_C", "OPT_D", "Validation", "outcomes", "future_information"} <= forbidden


def test_ps0_discrimination_corpus_has_required_adversarial_surfaces_and_no_outcomes():
    fixture = _load(FIXTURES)
    assert fixture["evidence_class"] == "SYNTHETIC_ADVERSARIAL_NON_EVIDENTIARY"
    assert fixture["real_source"] is False
    assert fixture["outcomes_present"] is False
    ids = {case["case_id"] for case in fixture["cases"]}
    required = {
        "PS0-F02-BOUNDED-GEOMETRY-EVOLUTION",
        "PS0-F03-C2E-LINEAGE-CONFLICT",
        "PS0-F04-GAP-CENSOR",
        "PS0-F05-DORMANT-REAPPEARANCE",
        "PS0-F06-RETIRED-RECURRENCE",
        "PS0-F07-EQUAL-COMPETITORS",
        "PS0-F08-SPLIT",
        "PS0-F09-MERGE",
        "PS0-F10-CROSS-SCALE-SIMILARITY",
        "PS0-F11-FAMILY-LABEL-MATCH",
        "PS0-F12-DOWNSTREAM-SEMANTIC-MATCH",
    }
    assert required <= ids
    assert fixture["selection_rule"].startswith("NO_SCALAR_RANKING_NO_WINNER")


def test_ps0_rs0_preregistration_preserves_run_and_selection_authority_boundaries():
    prereg = _load(PREREG)
    assert prereg["status"] == "PREPARED_NOT_AUTHORISED"
    assert prereg["source_population"]["validation"] == "LOCKED_UNCONSUMED"
    assert prereg["comparison_design"]["no_winner_metric"] is True
    assert prereg["real_source_run_authority"] == "DENIED_UNTIL_SEPARATE_C2P2_RS0_OPERATOR_TOKEN"
    assert prereg["selection_after_rs0"].startswith("OPERATOR_REQUIRED")
    assert "FAILS_CLOSED" in prereg["capacity_policy"]
