import pytest

from ovc.research_operations.prsc.execution import (
    ExecutionPrerequisites,
    PRSCExecutionError,
    assert_real_execution_authorized,
    build_completion_receipt,
    build_review_population_manifest,
    execute_candidate_synthetic,
)


def test_population_reconciliation_preserves_nulls():
    manifest = build_review_population_manifest(
        [{"candidate_ref":"A"},{"candidate_ref":"B"}],
        {"A":"COMPLETE","B":"NOT_EVALUABLE"},
    )
    assert manifest["n_admitted"] == 2
    assert manifest["counts"]["NOT_EVALUABLE"] == 1
    assert manifest["reconciled"] is True


def test_population_reconciliation_fails_closed():
    with pytest.raises(PRSCExecutionError):
        build_review_population_manifest([{"candidate_ref":"A"}], {})


def test_real_execution_is_denied_without_all_reserved_prerequisites():
    with pytest.raises(PRSCExecutionError):
        assert_real_execution_authorized(ExecutionPrerequisites(True, True, True, False, True, "FROZEN"))


def test_synthetic_dispatch_keeps_not_evaluable_visible():
    record = execute_candidate_synthetic(
        candidate_ref="A",
        protocol_generation_ref="P",
        dimensions=["dependence","reference"],
        handlers={"dependence": lambda _: {"status":"PASS"}},
    )
    assert record["execution_mode"] == "SYNTHETIC_BUILD_AHEAD"
    assert record["dimension_results"][1]["status"] == "NOT_EVALUABLE"


def test_completion_receipt_requires_reconciliation_and_qa():
    receipt = build_completion_receipt(manifest_ref="M", execution_refs=["E"], population_reconciled=True, qa_pass=True)
    assert receipt["status"] == "PASS_CANDIDATE"
