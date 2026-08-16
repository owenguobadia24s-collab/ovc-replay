from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.rccr.core import RCCRValidationError
from ovc.research_operations.rccr.scaleout import compile_bounded_scaleout

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = "docs/releases/rccr-v0-1/rccri-wp6b/RCCRI_WP6B_SOURCE_ADMISSION_MANIFEST.json"
BOOTSTRAP = "docs/releases/rccr-v0-1/rccri-wp6b/RCCRBootstrapManifest.BROAD_WAVE_1.json"


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_wp6b_wave_is_exact_allowlist_and_non_authoritative():
    m = load(MANIFEST)
    assert m["admission_mode"] == "EXACT_ID_ALLOWLIST_ONLY"
    assert m["interesting_file_ingestion"] == "FORBIDDEN"
    assert {x["stratum"] for x in m["admitted_sources"]} == {
        "PATH2_IN_HOUSE", "PATH2_EXTERNAL", "EXTERNAL_FINDING", "ARCHITECTURE_CONTROL"
    }
    assert all(x["authority_effect"] == "NONE" for x in m["admitted_sources"])
    assert m["owner_authority_frontier"]["ec1"]["state"] == "AUTHORISED_BOUNDED"
    assert m["owner_authority_frontier"]["path2_external"]["state"] == "AUTHORISED_BOUNDED"
    assert m["rccr_consumption_boundary"]["real_source_ec1_consumption"] == "DENIED_BY_RCCRI_WP6B_SCOPE"
    assert m["rccr_consumption_boundary"]["path2_real_source_consumption"] == "DENIED_BY_RCCRI_WP6B_SCOPE"
    assert m["rccr_consumption_boundary"]["owner_capability_activation"] == "DENIED"
    assert m["owner_authority_frontier"]["validation"]["state"] == "LOCKED_UNCONSUMED"


def test_wp6b_excludes_unadmitted_real_source_and_protected_sources():
    m = load(MANIFEST)
    excluded = {x["source_id"]: x["reason"] for x in m["explicit_exclusions"]}
    assert excluded["P2-EXT-EXPERIMENTRECORD-SHELLS-v0.1"] == "PREREGISTRATION_SHELL_NOT_EFFECTIVE_IN_BOUND_WAVE"
    assert excluded["VALIDATION_PROTECTED_CONTENT"] == "PROTECTED_SOURCE_DENIED"
    assert excluded["REAL_SOURCE_EC1_RESULTS"] == "OWNER_AUTHORISED_BUT_RCCRI_WP6B_CONSUMPTION_NOT_ADMITTED"
    assert excluded["PATH2_REAL_SOURCE_RESULTS"] == "OWNER_AUTHORISED_BUT_RCCRI_WP6B_CONSUMPTION_NOT_ADMITTED"
    assert excluded["ARBITRARY_INTERESTING_FILES"] == "NO_EXACT_GOVERNED_ADMISSION"


def test_wp6b_pre_post_freeze_visibility_does_not_rewrite_state():
    m = load(MANIFEST)
    assert m["visibility_firewall"]["pre_freeze_objects_preserve_pre_freeze_state"] is True
    assert m["visibility_firewall"]["post_freeze_control_state_does_not_rewrite_pre_freeze_objects"] is True
    theory = next(x for x in m["admitted_sources"] if x["source_id"] == "P2-EXT-THEORYRECORD-DRAFT-REGISTER-v0.1")
    freeze = next(x for x in m["admitted_sources"] if x["source_id"] == "P2-EXT-METHOD-PARAMETER-FREEZE-STATE-v0.1")
    assert theory["state"] == "UNTESTED"
    assert theory["visibility"] == "PRE_FREEZE_VISIBLE"
    assert freeze["visibility"] == "POST_FREEZE_VISIBLE"


def test_scaleout_compiler_rejects_protected_or_unlisted_source_and_preserves_owner_frontier():
    base = {
        "source_id": "A", "stratum": "PATH2_EXTERNAL", "object_type": "TheoryRecord",
        "owner": "owner", "source_ref": "ref", "source_hash": "abc", "state": "UNTESTED",
        "visibility": "PRE_FREEZE_VISIBLE", "research_mode": "PATH_2_THEORY_FORMALISATION",
        "authority_effect": "NONE",
    }
    owner_frontier = {"ec1": {"state": "AUTHORISED_BOUNDED"}}
    out = compile_bounded_scaleout(
        [base, {**base, "source_id": "B"}],
        admitted_ids=["A"],
        owner_authority_frontier=owner_frontier,
    )
    assert [x["source_id"] for x in out["admitted"]] == ["A"]
    assert out["excluded"] == [{"source_id": "B", "reason": "NOT_EXACTLY_ADMITTED"}]
    assert out["owner_authority_frontier"] == owner_frontier
    assert out["rccr_consumption_boundary"]["real_source_ec1_consumption"] == "DENIED_BY_RCCRI_WP6B_SCOPE"
    with pytest.raises(RCCRValidationError):
        compile_bounded_scaleout([{**base, "protected": True}], admitted_ids=["A"])


def test_bootstrap_wave_counts_and_boundaries_match_manifest():
    m = load(MANIFEST)
    b = load(BOOTSTRAP)
    assert b["admitted_source_count"] == len(m["admitted_sources"]) == 6
    assert b["excluded_source_count"] == len(m["explicit_exclusions"]) == 6
    assert b["mode_visibility_preserved"] is True
    assert b["negative_controls_preserved"] is True
    assert b["owner_authority_frontier"] == m["owner_authority_frontier"]
    assert b["rccr_consumption_boundary"] == m["rccr_consumption_boundary"]
    assert b["authority_effect"] == "NONE"
