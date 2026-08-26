from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
HISTORICAL_STATE = "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_27_WP8_S01_STAGE1_C1_CASE_NARRATIVE_FIDELITY_SUPERSESSION_COMPLETED.json"
EFFECTIVE_STATE = "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_28_WP8_S01_STAGE1_C1_CASE_NARRATIVE_FIDELITY_SUPERSESSION_REPOSITORY_EFFECTIVE.json"
RECEIPT = "records/research_operations/asocs/wp8/ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_POST_MERGE_COMPLETION_RECEIPT_v0_1.json"
SOURCE_PACKET = "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-FIDELITY-SUPERSESSION"
NEXT_PACKET = "ASOCSI-WP8-S01-STAGE1-C1-CASE-NARRATIVE-HUMAN-ADJUDICATION"
SOURCE_CANDIDATE = "afa76a77766cbd580e439b2a99c078e276c43aaf"
SOURCE_MERGE = "6986acc3caf92c2fd3cdf32ed8460fe1bd858c06"
SOURCE_TREE = "720fb751634b5216438e030837aadbe244966a87"

def load(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return json.loads(path.read_text(encoding="utf-8"))

def test_case_narrative_supersession_is_repository_effective_without_starting_human_adjudication():
    historical = load(HISTORICAL_STATE)
    effective = load(EFFECTIVE_STATE)
    receipt = load(RECEIPT)
    pointer = load("registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    current = load(pointer["current_state"])
    closeout = load(WP8 / "ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_POST_MERGE_PACKET_v0_1.json")
    closeout_decision = load(WP8 / "ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_POST_MERGE_DECISION_v0_1.json")
    closeout_qa = load(WP8 / "ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_POST_MERGE_QA_v0_1.json")
    source_decision = load(WP8 / "ASOCSI_WP8_S01_STAGE1_C1_CASE_NARRATIVE_DECISION_v0_1.json")

    assert historical["packet_id"] == SOURCE_PACKET
    assert historical["status"] == "COMPLETED"
    assert historical["candidate_commit"] == "RESOLVE_AT_PACKET_HEAD"
    assert historical["merge_commit"] is None
    assert historical["merge_commit_resolution"] == "RESOLVE_FROM_PACKET_PR_SQUASH_MERGE"

    assert source_decision["decision"] == "PASS"
    assert source_decision["authority_delta"] == "NONE"
    assert source_decision["next_boundary"] == "HUMAN_SCIENTIFIC_INPUT"

    assert effective["packet_id"] == SOURCE_PACKET
    assert effective["status"] == "COMPLETED_REPOSITORY_EFFECTIVE"
    assert effective["candidate_commit"] == SOURCE_CANDIDATE
    assert effective["merge_commit"] == SOURCE_MERGE
    assert effective["repository_effective"]["repository_effective"] is True
    assert effective["repository_effective"]["pr_number"] == 1353
    assert effective["repository_effective"]["merge_tree"] == SOURCE_TREE
    assert effective["human_scientific_input_boundary"] is True
    assert effective["required_human_input_started"] is False
    assert effective["human_adjudication_started"] is False
    assert effective["stage2_reveal_started"] is False
    assert effective["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
    assert effective["next_boundary"] == "HUMAN_SCIENTIFIC_INPUT"
    assert effective["next_packet"] == NEXT_PACKET

    assert receipt["completed_packet"] == SOURCE_PACKET
    assert receipt["status"] == "COMPLETED_REPOSITORY_EFFECTIVE"
    assert receipt["repository_effective"] is True
    assert receipt["merge"]["candidate_head_sha"] == SOURCE_CANDIDATE
    assert receipt["merge"]["commit_sha"] == SOURCE_MERGE
    assert receipt["merge"]["merged_tree_sha"] == SOURCE_TREE
    assert receipt["exact_assurance"]["qualification_id"] == "e860c2b733f8d5f476beb451f1448781e07b5a94664553ad378a3879a473e340"
    assert receipt["exact_assurance"]["pip_id"] == "9aefbf2eb7f26b5a74477302065cd3159b52b2edab617c71da99a81b9404c1a2"
    assert receipt["exact_assurance"]["assurance_generation_id"] == "a6b40837ba67be3d7f31fd2c5805482bec1890aa0cc2a6f94b42561ea65b451c"
    assert receipt["exact_assurance"]["integration_admission_receipt_id"] == "745b47deadbfa13f15a3e6faf8fbdb311a7b396aff5977d619f34483081630c2"
    assert receipt["authority_delta"] == "NONE"
    assert receipt["evidence"]["human_adjudication_started"] is False
    assert receipt["evidence"]["required_human_input_started"] is False
    assert receipt["evidence"]["stage2_reveal_started"] is False

    assert closeout["completed_source_packet"] == SOURCE_PACKET
    assert closeout["authority_delta"] == "NONE"
    assert closeout["next_boundary"] == "HUMAN_SCIENTIFIC_INPUT"
    assert closeout_decision["decision"] == "PASS"
    assert closeout_decision["authority_delta"] == "NONE"
    assert closeout_qa["blocking_findings"] == []
    assert closeout_qa["qa_recommendation"] == "PASS_SUBJECT_TO_EXACT_HEAD_REPOSITORY_ASSURANCE"

    assert pointer["current_state"] == EFFECTIVE_STATE
    assert pointer["programme_id"] == current["programme_id"] == effective["programme_id"]
    assert pointer["packet_id"] == current["packet_id"] == SOURCE_PACKET
    assert pointer["status"] == current["status"] == "COMPLETED_REPOSITORY_EFFECTIVE"
    assert pointer["next_packet"] == current["next_packet"] == NEXT_PACKET
