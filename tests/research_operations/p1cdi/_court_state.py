from __future__ import annotations


_POST_REVIEW5_PACKET_ORDER = (
    "P1CDII-WP5",
    "P1CDII-WP6",
    "P1CDII-WP7",
    "P1CDII-WP8",
    "P1CDII-WP9",
    "P1CDII-WP10",
    "P1CDII-WP11",
)


def assert_post_review5_current_state(state: dict) -> None:
    """Assert immutable Review-5 PASS while allowing lawful successor progress.

    Historical review/remediation tests verify immutable packet evidence. They must
    not pin the mutable programme pointer to WP5 after later delegated packets
    complete. Forward progress is accepted only across the declared post-Review-5
    packet order, while all Review-5/G4 facts and reserved denials remain fixed.
    """
    current = state["current_packet"]
    assert current in _POST_REVIEW5_PACKET_ORDER
    assert state["status"] in {
        "READY",
        "RUNNING",
        "IMPLEMENTED",
        "QA_REVIEW",
        "GATE_READY",
        "APPROVED",
        "COMPLETED",
    }
    assert state["packets"]["P1CDII-WP4"]["status"] == "COMPLETED"
    assert state["packets"]["P1CDII-G4-ALG"]["status"] == "COMPLETED"
    review5 = state["packets"]["P1CDII-G4-ALG-FRESH-INDEPENDENT-REVIEW-5"]
    assert review5["status"] == "COMPLETED"
    assert review5["authority_required"] == "INDEPENDENT_BLOCKING"
    assert review5["authority_delta"] == "NONE"
    assert review5["blockers"] == []
    assert review5["next_packet"] == "P1CDII-WP5"
    wp5 = state["packets"]["P1CDII-WP5"]
    assert wp5["authority_required"] == "AUTO_EXECUTABLE"
    assert wp5["authority_delta"] == "NONE"
    if current == "P1CDII-WP5":
        assert wp5["status"] in {"READY", "RUNNING", "IMPLEMENTED", "QA_REVIEW", "GATE_READY", "APPROVED"}
    else:
        assert wp5["status"] == "COMPLETED"
    assert state["blockers"] == []
    assert state["authority"]["operational_read_only"] == "DENIED"
    assert state["authority"]["continuous_intake"] == "DENIED"
