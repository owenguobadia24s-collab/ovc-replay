from ovc.research_operations.prsc.assurance import (
    CapacityMeasurement,
    PRSCAssuranceError,
    assert_fixture_catalogue_complete,
    build_mechanical_conformance_bundle,
    capacity_status,
    evaluate_reference_equivalence,
)


def test_reference_equivalence_pass_and_mismatch():
    passed = evaluate_reference_equivalence("multiplicity", [1, 2], lambda x: x * 2, lambda x: x + x)
    assert all(item.status == "PASS" for item in passed)

    failed = evaluate_reference_equivalence("multiplicity", [1], lambda x: x * 2, lambda x: x * 3)
    assert failed[0].status == "MISMATCH_QUARANTINE_OPTIMIZED"


def test_fixture_catalogue_must_be_exact():
    assert_fixture_catalogue_complete(["A", "B"], ["B", "A"])
    try:
        assert_fixture_catalogue_complete(["A", "B"], ["A"])
    except PRSCAssuranceError:
        pass
    else:
        raise AssertionError("missing fixture must fail closed")


def test_capacity_exceeded_does_not_mutate_scope():
    measurement = CapacityMeasurement("T", 10, 20, 2, 2, 2, 10, 100, 1000, 10)
    assert capacity_status(measurement, {"peak_memory_bytes": 999}) == "CAPACITY_EXCEEDED"


def test_bundle_quarantines_protected_source_survivor():
    bundle = build_mechanical_conformance_bundle(
        bundle_id="B1",
        fixture_results=[{"fixture_id": "AV-PRSC-01", "status": "PASS"}],
        equivalence_results=[],
        capacity_results=[{"tier_id": "TINY", "status": "PASS"}],
        protected_source_survivors=1,
    )
    assert bundle["status"] == "QUARANTINED"
    assert bundle["protected_source_reachability"] == "BLOCKING_SURVIVORS"


def test_bundle_capacity_incomplete_is_not_pass():
    bundle = build_mechanical_conformance_bundle(
        bundle_id="B2",
        fixture_results=[],
        equivalence_results=[],
        capacity_results=[{"tier_id": "MEDIUM", "status": "CAPACITY_EXCEEDED"}],
        protected_source_survivors=0,
    )
    assert bundle["status"] == "CAPACITY_INCOMPLETE"
    assert bundle["authority_effect"] == "NONE"
