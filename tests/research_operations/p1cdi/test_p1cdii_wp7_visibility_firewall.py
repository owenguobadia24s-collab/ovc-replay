from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.p1cdi.visibility import (
    LEAK_SURFACES,
    PATH1_SAFE_REDACTED_FIELDS,
    build_visibility_decision,
    build_visibility_safe_index_entry,
    deny_validation_before_resolution,
    project_independence_state,
    project_visible_record,
    validate_visibility_decision,
)


FIXTURE = Path("fixtures/research_operations/p1cdi/P1CDII_WP7_VISIBILITY_LEAK_FIXTURE_v0_1.json")


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_visibility_classification_fails_closed_before_indexing() -> None:
    for case in _fixture()["classification_cases"]:
        decision = build_visibility_decision(
            source_ref=case["source_ref"],
            classification=case["classification"],
            classification_complete=case["classification_complete"],
            permission_refs=case.get("permission_refs", []),
            cross_mode_freeze_ref=case.get("cross_mode_freeze_ref"),
        )
        validate_visibility_decision(decision)
        assert decision["classification"] == case["expected"]
        assert decision["classified_before_indexing"] is True
        assert decision["validation_access"] == "DENIED"
        assert decision["authority_effect"] == "NONE"


def test_protected_leak_corpus_has_zero_survivors() -> None:
    decision = build_visibility_decision(
        source_ref="source:protected",
        classification="PROTECTED",
        classification_complete=True,
    )
    assert set(decision["denied_surfaces"]) == set(LEAK_SURFACES)
    for case in _fixture()["leak_cases"]:
        record = {case["field"]: case["secret"], "safe": "visible-if-lawful"}
        projection = project_visible_record(
            decision=decision,
            record=record,
            surface=case["surface"],
        )
        assert projection["visibility"] == "DENIED"
        assert case["secret"] not in json.dumps(projection, sort_keys=True)
        assert "source:protected" not in json.dumps(projection, sort_keys=True)


def test_path1_safe_removes_candidate_defining_content() -> None:
    decision = build_visibility_decision(
        source_ref="source:path1-safe",
        classification="PATH1_SAFE",
        classification_complete=True,
    )
    projection = project_visible_record(
        decision=decision,
        record=_fixture()["path1_safe_record"],
        surface="FIELDS",
    )
    assert projection["visibility"] == "VISIBLE"
    assert projection["record"]["safe_summary"] == "lawful-path1-summary"
    for field in PATH1_SAFE_REDACTED_FIELDS:
        assert field not in projection["record"]
    encoded = json.dumps(projection, sort_keys=True)
    assert "SECRET_PATH2_" not in encoded


def test_path1_full_requires_exact_permission_intersection() -> None:
    decision = build_visibility_decision(
        source_ref="source:path1-full",
        classification="PATH1_FULL",
        classification_complete=True,
        permission_refs=["perm:path1:eligible"],
    )
    denied = project_visible_record(
        decision=decision,
        record={"payload": "allowed-only-to-eligible"},
        surface="FIELDS",
        caller_permission_refs=["perm:wrong"],
    )
    allowed = project_visible_record(
        decision=decision,
        record={"payload": "allowed-only-to-eligible"},
        surface="FIELDS",
        caller_permission_refs=["perm:path1:eligible"],
    )
    assert denied["visibility"] == "DENIED"
    assert "allowed-only-to-eligible" not in json.dumps(denied)
    assert allowed["visibility"] == "VISIBLE"


def test_cross_mode_requires_exact_freeze_and_visibility_permission() -> None:
    missing = build_visibility_decision(
        source_ref="source:cross-mode",
        classification="CROSS_MODE_POST_FREEZE",
        classification_complete=True,
        permission_refs=["perm:cross-mode"],
    )
    assert missing["classification"] == "PROTECTED"

    frozen = build_visibility_decision(
        source_ref="source:cross-mode",
        classification="CROSS_MODE_POST_FREEZE",
        classification_complete=True,
        permission_refs=["perm:cross-mode"],
        cross_mode_freeze_ref="dmrp:freeze:exact-1",
    )
    assert frozen["classification"] == "CROSS_MODE_POST_FREEZE"
    assert "dmrp:freeze:exact-1" in frozen["permission_refs"]
    allowed = project_visible_record(
        decision=frozen,
        record={"correspondence": "post-freeze-only"},
        surface="FIELDS",
        caller_permission_refs=["perm:cross-mode"],
    )
    assert allowed["visibility"] == "VISIBLE"


def test_validation_is_denied_before_sensitive_resolution() -> None:
    decision = build_visibility_decision(
        source_ref="source:protected-validation",
        classification="PROTECTED",
        classification_complete=True,
    )
    calls: list[str] = []

    def resolver() -> str:
        calls.append("CALLED")
        return "SECRET_VALIDATION_PAYLOAD"

    with pytest.raises(PermissionError, match="VALIDATION_NEGATIVE_REACHABILITY"):
        deny_validation_before_resolution(decision=decision, sensitive_resolver=resolver)
    assert calls == []


def test_index_materialization_occurs_only_after_visibility_filter() -> None:
    protected = build_visibility_decision(
        source_ref="source:index-protected",
        classification=None,
        classification_complete=False,
    )
    assert build_visibility_safe_index_entry(
        decision=protected,
        record={"title": "SECRET_INDEX_TITLE"},
    ) is None

    safe = build_visibility_decision(
        source_ref="source:index-safe",
        classification="PATH1_SAFE",
        classification_complete=True,
        redacted_fields=["secret"],
    )
    entry = build_visibility_safe_index_entry(
        decision=safe,
        record={"summary": "safe", "secret": "SECRET_INDEX_PAYLOAD"},
    )
    assert entry is not None
    assert entry["classified_before_indexing"] is True
    assert entry["record"] == {"summary": "safe"}
    assert entry["authority_effect"] == "NONE"


def test_no_exposure_record_never_becomes_independence() -> None:
    for case in _fixture()["independence_cases"]:
        projection = project_independence_state(exposure_refs=case["exposure_refs"])
        assert projection["result"] == case["expected"]
        assert projection["authority_effect"] == "NONE"


def test_only_owner_evidence_can_project_stronger_independence_class() -> None:
    projection = project_independence_state(
        exposure_refs=[],
        owner_independence_evidence={
            "record_id": "dmrp:independence:owner-1",
            "result": "INDEPENDENCE_SUPPORTED",
        },
    )
    assert projection["result"] == "INDEPENDENCE_SUPPORTED"
    assert projection["owner_evidence_ref"] == "dmrp:independence:owner-1"
    assert projection["authority_effect"] == "NONE"


def test_visibility_records_cannot_smuggle_authority() -> None:
    decision = build_visibility_decision(
        source_ref="source:safe",
        classification="PATH1_SAFE",
        classification_complete=True,
    )
    tampered = dict(decision)
    tampered["authority_effect"] = "OPERATIONAL_READ_ONLY"
    with pytest.raises(PermissionError):
        validate_visibility_decision(tampered)
