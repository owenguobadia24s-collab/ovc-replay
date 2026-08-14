import pytest

from ovc.opt_b.esl.research_bridge import ResearchBridgeError, assert_no_runtime_fabrication, bind_research_candidate_generation, build_research_evidence_handoff


def test_wp11_interface_only_handoff_stops_when_runtime_absent():
    handoff = build_research_evidence_handoff(mode="PATH_1", evidence_refs=["ev:1"], evidence_frontier_ref="ef:1")
    assert handoff["bridge_maturity"] == "INTERFACE_ONLY"
    assert handoff["runtime_state"] == "DOWNSTREAM_RUNTIME_NOT_MATERIALIZED"
    assert handoff["execution_boundary"] == "FULL_RESEARCH_HANDOFF"
    assert_no_runtime_fabrication(handoff)


def test_wp11_path_identity_and_term_identity_remain_distinct():
    handoff = build_research_evidence_handoff(mode="PATH_2", evidence_refs=["ev:2"], evidence_frontier_ref="ef:2")
    binding = bind_research_candidate_generation(handoff=handoff, research_candidate_generation_id="rcg:1", structural_term_candidate_id="stc1:2")
    assert binding["identity_merge"] == "FORBIDDEN"
    assert binding["language_candidate_binding"]["research_candidate_generation_id"] != binding["language_candidate_binding"]["structural_term_candidate_id"]
    assert binding["candidate_freeze"] == "OPERATOR_RESERVED"
    assert binding["semantic_admission"] == "OPERATOR_RESERVED"


def test_wp11_mechanism_remains_research_operations_owned():
    with pytest.raises(ResearchBridgeError, match="MECHANISM_OWNER"):
        build_research_evidence_handoff(mode="PATH_1", evidence_refs=["ev:1"], evidence_frontier_ref="ef:1", mechanism_refs=["theory:1"], research_operations_owner="ESL")
