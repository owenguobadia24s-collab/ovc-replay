import pytest

from ovc.research_operations.sff.core import SFFContractError, canonical_bytes
from ovc.research_operations.sff.preregistration import REQUIRED_FIELDS, amend_frozen_bundle, compile_preregistration


def valid_fields():
    fields = {name: {"identity": f"{name}-v1"} for name in REQUIRED_FIELDS}
    fields["outcome_access_embargo_manifest"] = {"identity": "embargo-v1", "protected_outcomes_accessed": False, "embargo_state": "LOCKED"}
    fields["static_model_generation"] = {"identity": "generation-v1", "mode": "STATIC"}
    fields["feasibility_evidence"] = {"identity": "feasibility-v1", "scope": "SUPPORT_ONLY_PRE_OUTCOME"}
    return fields


def test_complete_prereg_compiles_atomically_and_reproduces_exact_bytes() -> None:
    first = compile_preregistration(valid_fields())
    second = compile_preregistration(valid_fields())
    assert first == second
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first.freeze_receipt.atomic
    assert not first.freeze_receipt.real_study_frozen
    assert not first.freeze_receipt.protected_outcomes_accessed


@pytest.mark.parametrize("bad", [None, "UNKNOWN", "DEFAULT", "TBD", "AMBIGUOUS", "CONTAMINATED", "AUTHORITY_BLOCKED"])
def test_decision_bearing_unknown_default_or_blocked_values_fail_closed(bad) -> None:
    fields = valid_fields(); fields["materiality_rule"] = bad
    with pytest.raises(SFFContractError, match="UNRESOLVED"):
        compile_preregistration(fields)


def test_missing_field_outcome_access_and_adaptive_model_fail_closed() -> None:
    fields = valid_fields(); del fields["dependence_plan"]
    with pytest.raises(SFFContractError, match="MISSING"):
        compile_preregistration(fields)
    fields = valid_fields(); fields["outcome_access_embargo_manifest"]["protected_outcomes_accessed"] = True
    with pytest.raises(SFFContractError, match="EMBARGO"):
        compile_preregistration(fields)
    fields = valid_fields(); fields["static_model_generation"]["mode"] = "ADAPTIVE"
    with pytest.raises(SFFContractError, match="NOT_STATIC"):
        compile_preregistration(fields)


def test_frozen_bundle_amendment_requires_explicit_successor_generation() -> None:
    compiled = compile_preregistration(valid_fields())
    with pytest.raises(SFFContractError, match="SUCCESSOR"):
        amend_frozen_bundle(compiled, successor_generation_id=None)
    assert amend_frozen_bundle(compiled, successor_generation_id="generation-v2").startswith("SUCCESSOR_REQUIRED")


def test_contaminated_feasibility_and_nested_protected_access_fail_closed() -> None:
    fields = valid_fields()
    fields["feasibility_evidence"]["scope"] = "OUTCOME_EXPOSED_NONCONFIRMATORY"
    with pytest.raises(SFFContractError, match="FEASIBILITY_OUTCOME_CONTAMINATED"):
        compile_preregistration(fields)
    fields = valid_fields()
    fields["scientific_endpoint_manifest"]["protected_outcomes_accessed"] = True
    with pytest.raises(SFFContractError, match="PROTECTED_OUTCOME_ACCESS_PRESENT"):
        compile_preregistration(fields)
