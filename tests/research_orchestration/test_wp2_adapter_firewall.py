from __future__ import annotations

import pytest

from ovc.research_orchestration.adapters import AdapterError, AdapterRegistry, assert_no_scientific_mutation


class DummyAdapter:
    def __init__(self, stage_id: str) -> None:
        self.stage_id = stage_id


def test_adapter_registry_rejects_duplicate_stage() -> None:
    registry = AdapterRegistry()
    registry.register(DummyAdapter("A"))
    with pytest.raises(AdapterError, match="IROF_DUPLICATE_ADAPTER"):
        registry.register(DummyAdapter("A"))


def test_wrapper_may_change_execution_envelope_only() -> None:
    before = {"value": 7, "status": "NULL_RESULT", "run_id": "r1", "physical_path": "/a"}
    after = {"value": 7, "status": "NULL_RESULT", "run_id": "r2", "physical_path": "/b", "telemetry": {"wall": 1.0}}
    assert_no_scientific_mutation(before, after)


def test_wrapper_scientific_mutation_fails_closed() -> None:
    before = {"value": 7, "status": "NULL_RESULT", "run_id": "r1"}
    after = {"value": 8, "status": "NULL_RESULT", "run_id": "r1"}
    with pytest.raises(AdapterError, match="IROF_WRAPPER_SCIENTIFIC_MUTATION"):
        assert_no_scientific_mutation(before, after)


def test_scientific_result_status_is_not_execution_envelope() -> None:
    before = {"value": 7, "status": "NO_STABLE_FAMILY", "execution_status": "RUNNING"}
    after = {"value": 7, "status": "COMPLETE", "execution_status": "COMPLETE"}
    with pytest.raises(AdapterError, match="IROF_WRAPPER_SCIENTIFIC_MUTATION"):
        assert_no_scientific_mutation(before, after)
