import json
from pathlib import Path

from ovc.research_operations.dmrp_candidate import ResearchCandidateGeneration
from ovc.research_operations.pmm_dfa import classify_corridor, classify_node

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "docs/programmes/pmm-dfa-v0-1/r1t/generation-1/PMM_DFA_R1T_GENERATION_1_FREEZE_MANIFEST_v0_1.json"
CENSUS = ROOT / "docs/programmes/pmm-dfa-v0-1/r1t/wp1/PMM_DFA_R1T_PROTECTED_DEVELOPMENT_SOURCE_CENSUS_v0_1.json"
FIXTURE = ROOT / "tests/fixtures/research_operations/pmm_dfa_r1t_generation_1_truth_v0_1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def candidates_by_id(freeze):
    return {row["candidate_id"]: row for row in freeze["research_candidate_generation"]["definition"]["candidate_set"]}


def test_generation_1_identity_is_exact_and_canonical():
    freeze = load(FREEZE)
    record = freeze["research_candidate_generation"]
    generation = ResearchCandidateGeneration(**record)
    assert generation.semantic_sha256 == freeze["semantic_sha256"] == "2ff95fa8e4cbd1038b11edd12b38cc993b23c09569a691b5fd162a478b1066d4"
    assert generation.candidate_generation_id == freeze["candidate_generation_id"] == "rcg:2ff95fa8e4cbd1038b11edd12b38cc993b23c09569a691b5fd162a478b1066d4"
    assert [row["candidate_id"] for row in record["definition"]["candidate_set"]] == [
        "R1T-N01", "R1T-C01", "R1T-C02", "R1T-C03", "R1T-C04", "R1T-C05"
    ]
    assert record["population_binding"]["status"] == "UNBOUND_PENDING_EXACT_SOURCE_ADMISSION"
    assert record["population_binding"]["protected_payload_accessed"] is False


def test_synthetic_truth_worlds_and_outcome_blindness():
    freeze = load(FREEZE)
    fixture = load(FIXTURE)
    candidates = candidates_by_id(freeze)
    for case in fixture["cases"]:
        candidate = candidates[case["candidate_id"]]
        if candidate["type"] == "NODE":
            result = classify_node(case["observed"], candidate, case["projection"])
            assert result.state == case["expected_state"], case["case_id"]
            if "alternate_projection" in case:
                alternate = classify_node(case["observed"], candidate, case["alternate_projection"])
                assert alternate.state == case["alternate_expected_state"], case["case_id"]
        else:
            result = classify_corridor(
                case["previous"], case["current"], candidate,
                same_live_hypothesis=case["same_live_hypothesis"],
                projection=case["projection"],
            )
            assert result.state == case["expected_state"], case["case_id"]


def test_metadata_only_source_census_fails_closed_without_source_access():
    census = load(CENSUS)
    assert census["census_mode"] == "METADATA_ONLY"
    assert census["selected_source"] is None
    assert census["protected_payload_read"] is False
    assert census["candidate_bearing_payload_read"] is False
    assert census["result"] == "BLOCKED_NO_ELIGIBLE_FILED_UNTOUCHED_SAME_LINEAGE_PROTECTED_DEVELOPMENT_SOURCE"
    assert any(row["population"].startswith("2026") and row["eligibility"] == "OUT_OF_SCOPE" for row in census["known_population_dispositions"])
