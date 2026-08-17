from ovc.research_operations.prsc.rv_adapters import (
    bind_candidate_review_card,
    bind_evidence_cycle_review_packet,
    build_q08_bundle,
    preserve_review_disagreement,
)


def test_card_adapter_is_reference_only():
    out = bind_candidate_review_card(card_ref="CARD", candidate_ref="C", challenge_vector_ref="V", disposition_ref="D", review_refs=["R1"])
    assert out["candidate_semantics_changed"] is False
    assert out["authority_effect"] == "NONE"


def test_disagreement_is_preserved_without_majority():
    out = preserve_review_disagreement(candidate_ref="C", review_refs=["R1","R2"], dispositions=["RESTRICT","ANNOTATE"])
    assert out is not None
    assert out["resolution"] == "PRESERVE_DISAGREEMENT_NO_MAJORITY"


def test_q08_freeze_is_recommendation_only():
    out = build_q08_bundle(candidate_ref="C", challenge_vector_ref="V", review_refs=["R1"], disagreement_ref=None, disposition_ref="D", freeze_recommendation_ref="F")
    assert out["candidate_freeze_effect"] == "NONE"
    assert out["candidate_freeze_gate"] == "EC1-GSCI"


def test_limitation_routes_do_not_activate_authority():
    out = bind_evidence_cycle_review_packet(packet_ref="P", candidate_adapter_refs=["A"], q08_bundle_refs=["Q"], limitation_routes=[{"limitation_type":"METHOD_LIMITATION","target":"RCCR/Q09","authority_effect":"NONE"}])
    assert out["authority_effect"] == "NONE"
