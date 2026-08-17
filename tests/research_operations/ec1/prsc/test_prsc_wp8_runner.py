from ovc.research_operations.prsc.assurance import CapacityMeasurement, PRSCAssuranceError
from ovc.research_operations.prsc.wp8_runner import (
    EXPECTED_AV_FIXTURES,
    execute_registered_fixtures,
    execute_wp8_assurance,
    freeze_operational_budget,
    freeze_review_budget,
)


def _measurement(tier: str, n: int) -> CapacityMeasurement:
    return CapacityMeasurement(
        tier_id=tier,
        candidate_count=n,
        surrogate_count=n * 2,
        representation_count=2,
        time_partition_count=2,
        context_partition_count=2,
        boundary_count=n,
        artifact_bytes=n * 100,
        peak_memory_bytes=n * 200,
        review_units=n * 3,
    )


def test_budget_freeze_is_measured_non_scientific_and_non_reductive():
    measurements = [_measurement("TINY", 8), _measurement("SMALL", 32)]
    op = freeze_operational_budget(measurements)
    review = freeze_review_budget(measurements)
    assert op["source"] == "MEASURED_NON_SCIENTIFIC_SYNTHETIC_EVIDENCE"
    assert op["scope_reduction_permitted"] is False
    assert op["sampling_permitted"] is False
    assert review["top_n_permitted"] is False
    assert review["deterministic_batching_required"] is True


def test_fixture_catalogue_requires_all_15_registered_attacks():
    handlers = {fixture_id: (lambda fid=fixture_id: {"fixture_id": fid, "status": "PASS"}) for fixture_id in EXPECTED_AV_FIXTURES}
    assert len(execute_registered_fixtures(handlers)) == 15
    handlers.pop("AV-PRSC-15")
    try:
        execute_registered_fixtures(handlers)
    except PRSCAssuranceError:
        pass
    else:
        raise AssertionError("missing fixture must block")


def test_wp8_bundle_quarantines_protected_source_survivor_and_preserves_reference_oracle():
    handlers = {fixture_id: (lambda fid=fixture_id: {"fixture_id": fid, "status": "PASS"}) for fixture_id in EXPECTED_AV_FIXTURES}
    bundle = execute_wp8_assurance(
        bundle_id="WP8.TEST",
        fixture_handlers=handlers,
        equivalence_families={"multiplicity": ([1, 2], lambda x: x, lambda x: x)},
        measurements=[_measurement("TINY", 8)],
        protected_source_survivors=1,
    )
    assert bundle["status"] == "QUARANTINED"
    assert bundle["protected_source_reachability"] == "BLOCKING_SURVIVORS"


def test_wp8_bundle_is_pass_candidate_only_with_complete_fixtures_equivalence_and_zero_survivors():
    handlers = {fixture_id: (lambda fid=fixture_id: {"fixture_id": fid, "status": "PASS"}) for fixture_id in EXPECTED_AV_FIXTURES}
    bundle = execute_wp8_assurance(
        bundle_id="WP8.TEST.PASS",
        fixture_handlers=handlers,
        equivalence_families={"multiplicity": ([1, 2, 3], lambda x: x * 2, lambda x: x * 2)},
        measurements=[_measurement("TINY", 8), _measurement("SMALL", 32)],
        protected_source_survivors=0,
    )
    assert bundle["status"] == "PASS_CANDIDATE"
    assert bundle["authority_effect"] == "NONE"
    assert bundle["operational_budget"]["scope_reduction_permitted"] is False
