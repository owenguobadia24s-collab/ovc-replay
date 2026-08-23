from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess

import pytest

from ovc.shared_systems.dsai_active import (
    DSAI_ADOPTION_AUTHORITY,
    DSAI_ADOPTION_SURFACES,
    DSAIActiveConsumptionBinding,
    DSAIAdoptionError,
    compare_active_candidate,
    consume_dsai_surface,
    prove_rollback,
    unwrap_dsai_active_surface,
)


ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_REF = "9f2cae3ac70dca4baacbd52d597ba25d7428b14f945c91c4fdedd92e3d9770ba"
SOURCE_PATHS = {
    "CURRENTNESS": "registries/implementation/dsai/CURRENT_STATE_POINTER.json",
    "ASSURANCE": "registries/implementation/dsai/OVC_DSAI_STATE_v0_31.json",
    "RUN": "docs/releases/development-skills-architecture-v0-1/dsai-wp7/DSAI_G7_E5_HISTORICAL_REFERENCE_EXECUTION_PACKET.json",
    "ENVIRONMENT": "docs/releases/development-skills-architecture-v0-1/dsai-wp6/DSAI_WP6_COMPLETION_PACKET.json",
    "RECEIPT": "docs/releases/development-skills-architecture-v0-1/dsai-wp11/DSAI_WP11_G11_TERMINAL_SQUASH_MERGE_RECEIPT.json",
}


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def binding() -> DSAIActiveConsumptionBinding:
    return DSAIActiveConsumptionBinding(
        "SHSI-DSAI-ACTIVE-CANDIDATE-v0.1",
        "OVC-DSAI-v0.1",
        "OVC_DSAI_STATE_v0_31",
        "OVC-SHARED-SYSTEMS-v0.1",
        "SHSI-WP10-TERMINAL-v0.1",
        tuple(sorted(DSAI_ADOPTION_SURFACES)),
        AUTHORITY_REF,
    )


def test_active_candidate_is_dsai_only_and_not_current() -> None:
    candidate = binding()
    assert candidate.status == "ACTIVE_CANDIDATE"
    assert candidate.current_binding_changed is False
    assert candidate.authority_effect == DSAI_ADOPTION_AUTHORITY
    with pytest.raises(DSAIAdoptionError, match="NON_DSAI_CONSUMER"):
        replace(candidate, consumer_programme_id="OVC-OPTB-ESL-CONFORMANCE-v0.1")
    with pytest.raises(DSAIAdoptionError, match="PREMATURE_DSAI_CURRENT_BINDING_SWITCH"):
        replace(candidate, current_binding_changed=True)


def test_all_five_active_candidate_surfaces_round_trip_exactly() -> None:
    candidate = binding()
    assert set(SOURCE_PATHS) == DSAI_ADOPTION_SURFACES
    for surface, path in SOURCE_PATHS.items():
        source = load(path)
        envelope = consume_dsai_surface(candidate, surface, source)
        assert envelope.status == "ACTIVE_CANDIDATE"
        assert envelope.writes_performed == ()
        assert envelope.semantic_inventions == ()
        assert unwrap_dsai_active_surface(envelope) == source
        receipt = compare_active_candidate(f"SHSI-DSAI-EQUIV-{surface}-v0.1", surface, source, envelope)
        assert receipt.status == "PASS"
        assert receipt.divergent_paths == ()


def test_unknown_or_unbound_surface_fails_closed() -> None:
    candidate = binding()
    source = load(SOURCE_PATHS["CURRENTNESS"])
    with pytest.raises(DSAIAdoptionError, match="SURFACE_NOT_BOUND"):
        consume_dsai_surface(candidate, "SECURITY", source)


def test_rollback_restores_exact_pre_adoption_binding() -> None:
    candidate = binding()
    receipt = prove_rollback(
        "SHSI-DSAI-ROLLBACK-v0.1",
        pre_adoption_current_binding_ref="OVC-DSAI-v0.1@OVC_DSAI_STATE_v0_31",
        candidate_binding_ref=candidate.logical_id,
        restored_binding_ref="OVC-DSAI-v0.1@OVC_DSAI_STATE_v0_31",
        active_route_disabled=True,
        historical_shadow_preserved=True,
        requalification_required=True,
    )
    assert receipt.status == "PASS"
    blocked = prove_rollback(
        "SHSI-DSAI-ROLLBACK-BAD-v0.1",
        pre_adoption_current_binding_ref="OVC-DSAI-v0.1@OVC_DSAI_STATE_v0_31",
        candidate_binding_ref=candidate.logical_id,
        restored_binding_ref="OTHER",
        active_route_disabled=True,
        historical_shadow_preserved=True,
        requalification_required=True,
    )
    assert blocked.status == "BLOCK"


def test_historical_wp7_shadow_and_dsai_current_pointer_are_immutable() -> None:
    expected = {
        "src/ovc/shared_systems/dsai_shadow.py": "44b0e882c0bd4b536ffbbaaf8ae98cbc3503b373",
        "registries/implementation/dsai/CURRENT_STATE_POINTER.json": "f2ddbf70db95a57946bec76084be775ca2329fd9",
    }
    for path, blob_sha in expected.items():
        actual = subprocess.run(
            ["git", "hash-object", "--", path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert actual == blob_sha, path


def test_operator_authority_and_boundary_are_present() -> None:
    decision = load(
        "docs/programmes/shared-systems-v0-1/adoption/dsai/SHSI_DSAI_ONLY_ADOPTION_OPERATOR_DECISION_v0_1.json"
    )
    boundary = load(
        "docs/programmes/shared-systems-v0-1/adoption/dsai/SHSI_DSAI_ADOPTION_IMPLEMENTATION_BOUNDARY_v0_1.json"
    )
    assert decision["decision"] == "PASS"
    assert decision["consumer_programme_id"] == "OVC-DSAI-v0.1"
    assert decision["approved_authority_delta"] == DSAI_ADOPTION_AUTHORITY
    assert boundary["status"] == "AUTHORIZED_READY_NOT_YET_CUT_OVER"
    assert boundary["consumer_scope"] == ["OVC-DSAI-v0.1"]
    assert boundary["esl_binding"] == boundary["dmrp_binding"] == "UNCHANGED_NOT_AUTHORIZED"
