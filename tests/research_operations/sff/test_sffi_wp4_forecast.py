import pytest

from ovc.research_operations.sff.core import SFFContractError
from ovc.research_operations.sff.forecast import ForecastModelGeneration, UncertaintyRecord, build_forecast_snapshot
from ovc.research_operations.sff.risk import DistributionRecord


def _generation():
    return ForecastModelGeneration.freeze("method-v1", {"alpha": 0.25}, "calibration:synthetic:train-only")


def _uncertainty(**overrides):
    values = {"epistemic": "BOUNDED", "aleatoric": "ESTIMATED", "support": "IN_ENVELOPE", "evidence_identity": "evidence-1"}
    values.update(overrides)
    return UncertaintyRecord(**values)


def test_static_generation_identity_and_same_generation_no_update() -> None:
    first = _generation()
    assert first == _generation()
    assert first.mode == "STATIC"
    assert first.adaptive_state == "DEFERRED_NON_EXECUTABLE"
    with pytest.raises(SFFContractError, match="OUTCOME_UPDATE"):
        first.update_from_outcomes({"realised": 1})


def test_earned_uncertainty_and_support_emit_synthetic_snapshot() -> None:
    snapshot = build_forecast_snapshot(
        target_id="target-1",
        generation=_generation(),
        distribution=DistributionRecord({"A": 0.6, "B": 0.4}, "COMPLETE", "KNOWN"),
        uncertainty=_uncertainty(),
        support_currentness="CURRENT_SUPPORTED",
    )
    assert snapshot.status == "ISSUED"
    assert snapshot.research_effect == "SYNTHETIC_REFERENCE_ONLY"


def test_unsupported_or_unknown_uncertainty_abstains_without_probability() -> None:
    distribution = DistributionRecord({"A": 0.6, "B": 0.4}, "COMPLETE", "KNOWN")
    unsupported = build_forecast_snapshot(target_id="t", generation=_generation(), distribution=distribution, uncertainty=_uncertainty(), support_currentness="STALE")
    assert unsupported.status == "ABSTAINED" and unsupported.distribution is None
    unknown = build_forecast_snapshot(target_id="t", generation=_generation(), distribution=distribution, uncertainty=_uncertainty(epistemic="UNKNOWN"), support_currentness="CURRENT_SUPPORTED")
    assert unknown.status == "ABSTAINED" and unknown.distribution is None


def test_partial_probability_remains_partial() -> None:
    snapshot = build_forecast_snapshot(
        target_id="t",
        generation=_generation(),
        distribution=DistributionRecord({"A": 0.4}, "PARTIAL", "UNKNOWN"),
        uncertainty=_uncertainty(),
        support_currentness="CURRENT_SUPPORTED",
    )
    assert snapshot.status == "PARTIAL"
    assert snapshot.distribution is not None and sum(snapshot.distribution.probabilities.values()) == 0.4
