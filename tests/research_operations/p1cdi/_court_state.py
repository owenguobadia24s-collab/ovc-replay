from __future__ import annotations


def assert_post_review5_current_state(state: dict) -> None:
    """Assert the lawful current pointer after immutable Review-5 PASS.

    Historical review/remediation tests must continue to verify their immutable
    packet evidence, but they must not require the mutable programme pointer to
    remain parked at an earlier G4 boundary after a later lawful PASS.
    """
    assert state["status"] == "READY"
    assert state["current_packet"] == "P1CDII-WP5"
    assert state["packets"]["P1CDII-WP4"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG"]["status"] == "COMPLETED"
    review5 = state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"]
    assert review5["status"] == "COMPLETED"
    assert review5["authority_required"] == "INDEPENDENT_BLOCKING"
    assert review5["authority_delta"] == "NONE"
    assert review5["blockers"] == []
    assert review5["next_packet"] == "P1CDII-WP5"
    wp5 = state["packets"]["P1CDII-WP5"]
    assert wp5["status"] == "READY"
    assert wp5["authority_required"] == "AUTO_EXECUTABLE"
    assert wp5["authority_delta"] == "NONE"
    assert state["blockers"] == []
    assert state["next_packet"] == "P1CDII-WP5"
    assert state["authority"]["operational_read_only"] == "DENIED"
    assert state["authority"]["continuous_intake"] == "DENIED"
