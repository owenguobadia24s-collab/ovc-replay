from __future__ import annotations

import copy

import pytest

from ovc.research_operations.rccr.capability_frontier import (
    CapabilityBindingResolver,
    CapabilityFrontierCompiler,
    binding_state_digest,
)
from ovc.research_operations.rccr.core import RCCRValidationError


def capability(
    capability_id: str,
    *,
    implementation: str = "YES",
    availability: str = "YES",
    qualification: str = "QUALIFIED_FOR_DECLARED_USE",
    authority: str = "AUTHORISED_FOR_DECLARED_USE",
    activation: str = "ACTIVE_FOR_DECLARED_USE",
    active_stack_classification: str | None = "ACTIVE",
):
    item = {
        "capability_id": capability_id,
        "owner_programme": f"OWNER:{capability_id}",
        "responsibility": f"RESPONSIBILITY:{capability_id}",
        "design": "YES",
        "implementation": implementation,
        "availability": availability,
        "qualification": qualification,
        "authority": authority,
        "activation": activation,
        "first_valid_time": "2026-08-15T18:00:00+01:00",
        "source_refs": [f"repo:{capability_id.lower()}"],
        "active_stack_classification": active_stack_classification,
    }
    item["owner_state_digest"] = binding_state_digest(item)
    return item


def compile_frontier(catalog, relevant, **kwargs):
    resolver = CapabilityBindingResolver(catalog)
    resolved = [resolver.resolve(item) for item in relevant if any(row["capability_id"] == item for row in catalog)]
    return CapabilityFrontierCompiler().compile(
        resolved_bindings=resolved,
        relevant_capability_ids=relevant,
        evaluation_cutoff="2026-08-15T20:00:00+01:00",
        scope=["EC1-Q01-Q10-PRE_EVIDENTIARY"],
        authority_bindings=[
            {
                "authority_id": "DMRPI-GREAL-EC1",
                "state": "NONE",
                "authority_effect": "NONE",
            }
        ],
        **kwargs,
    )


def test_six_maturity_planes_remain_orthogonal_and_not_collapsed():
    item = capability(
        "C2P",
        implementation="YES",
        availability="YES",
        qualification="QUALIFIED_FOR_DECLARED_USE",
        authority="NOT_AUTHORISED",
        activation="INACTIVE",
        active_stack_classification="NON_EVALUABLE",
    )
    frontier = compile_frontier([item], ["C2P"])
    row = frontier["capability_bindings"][0]
    assert row["design"] == "YES"
    assert row["implementation"] == "YES"
    assert row["availability"] == "YES"
    assert row["qualification"] == "QUALIFIED_FOR_DECLARED_USE"
    assert row["authority"] == "NOT_AUTHORISED"
    assert row["activation"] == "INACTIVE"
    assert row["active_stack_classification"] == "NON_EVALUABLE"
    assert row["authority_effect"] == "NONE"


def test_c2p_implementation_yes_and_non_evaluable_stack_classification_are_preserved_together():
    item = capability(
        "C2P",
        implementation="YES",
        authority="NOT_AUTHORISED",
        activation="INACTIVE",
        active_stack_classification="NON_EVALUABLE",
    )
    frontier = compile_frontier([item], ["C2P"])
    row = frontier["capability_bindings"][0]
    assert row["implementation"] == "YES"
    assert row["active_stack_classification"] == "NON_EVALUABLE"
    assert not any(x["kind"] == "OWNER_STACK_PROJECTION_DISCREPANCY" for x in frontier["unresolved_bindings"])


def test_irrelevant_main_movement_does_not_change_frontier_identity():
    item = capability("C2")
    left = compile_frontier([item], ["C2"], unrelated_main_sha="a" * 40)
    right = compile_frontier([item], ["C2"], unrelated_main_sha="b" * 40)
    assert left == right


def test_irrelevant_capability_does_not_change_requirement_relevant_frontier():
    relevant = capability("C2")
    unrelated = capability("UNRELATED-C3")
    left = compile_frontier([relevant], ["C2"])
    right = compile_frontier([relevant, unrelated], ["C2"])
    assert left == right


def test_owner_projection_discrepancy_is_recorded_without_reconciliation():
    item = capability("C2P", active_stack_classification="NON_EVALUABLE", authority="NOT_AUTHORISED", activation="INACTIVE")
    frontier = compile_frontier(
        [item],
        ["C2P"],
        stack_projections={
            "C2P": {
                "active_stack_classification": "ACTIVE",
                "projection_ref": "active-stack:current",
            }
        },
    )
    row = frontier["capability_bindings"][0]
    assert row["active_stack_classification"] == "NON_EVALUABLE"
    discrepancy = next(x for x in frontier["unresolved_bindings"] if x["kind"] == "OWNER_STACK_PROJECTION_DISCREPANCY")
    assert discrepancy["owner_active_stack_classification"] == "NON_EVALUABLE"
    assert discrepancy["projected_active_stack_classification"] == "ACTIVE"
    assert discrepancy["resolution"] == "PRESERVE_BOTH_STOP_INFERENCE"


def test_missing_relevant_capability_is_explicit_unresolved_not_inferred():
    frontier = compile_frontier([], ["C2P"])
    assert frontier["capability_bindings"] == []
    assert frontier["unresolved_bindings"] == [
        {"kind": "MISSING_RELEVANT_CAPABILITY", "capability_id": "C2P", "authority_effect": "NONE"}
    ]


def test_unknown_plane_state_fails_closed():
    item = capability("C2")
    item["activation"] = "MAYBE_ACTIVE"
    item["owner_state_digest"] = binding_state_digest(item)
    with pytest.raises(RCCRValidationError) as exc:
        CapabilityBindingResolver([item]).resolve("C2")
    assert exc.value.code == "UNKNOWN_CAPABILITY_PLANE_STATE"


def test_protected_validation_capability_source_is_denied():
    item = capability("VALIDATION")
    item["protected"] = True
    item["protection_class"] = "VALIDATION"
    item["owner_state_digest"] = binding_state_digest(item)
    with pytest.raises(RCCRValidationError) as exc:
        CapabilityBindingResolver([item]).resolve("VALIDATION")
    assert exc.value.code == "PROTECTED_CAPABILITY_SOURCE_DENIED"


def test_real_source_ec1_authority_remains_none_in_frontier():
    frontier = compile_frontier([capability("C2")], ["C2"])
    assert frontier["authority_effect"] == "NONE"
    assert frontier["authority_bindings"] == [
        {"authority_id": "DMRPI-GREAL-EC1", "state": "NONE", "authority_effect": "NONE"}
    ]


def test_binding_digest_changes_only_when_owner_state_material_changes():
    item = capability("C2")
    same = copy.deepcopy(item)
    assert binding_state_digest(item) == binding_state_digest(same)
    changed = copy.deepcopy(item)
    changed["activation"] = "INACTIVE"
    assert binding_state_digest(changed) != binding_state_digest(item)
