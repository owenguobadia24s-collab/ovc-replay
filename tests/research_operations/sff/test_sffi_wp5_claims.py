import pytest

from ovc.research_operations.sff.claims import (
    ChallengerComparison,
    FailureRecord,
    ForecastSearchExposureManifest,
    SFFFalsificationContract,
    decide_claim,
    reentry_generation,
)
from ovc.research_operations.sff.core import SFFContractError


def _contract():
    return SFFFalsificationContract("falsification-v1", ("FULL_POPULATION", "MATCHED_SUPPORT", "CALIBRATION", "UNCERTAINTY"))


def _challenger():
    return ChallengerComparison("empirical-frequency", True, "PASS", "PASS")


def test_search_exposure_is_complete_content_addressed_and_order_sensitive() -> None:
    first = ForecastSearchExposureManifest.freeze("g1", ("t1", "t2"), "holm-v1", "cal:train")
    assert first == ForecastSearchExposureManifest.freeze("g1", ("t1", "t2"), "holm-v1", "cal:train")
    assert first.manifest_id != ForecastSearchExposureManifest.freeze("g1", ("t2", "t1"), "holm-v1", "cal:train").manifest_id


def test_non_compensation_blocks_on_any_dimension() -> None:
    results = {dimension: "PASS" for dimension in _contract().blocking_dimensions}
    results["UNCERTAINTY"] = "BLOCK"
    decision = decide_claim(generation_id="g1", dimension_results=results, falsification=_contract(), challengers=(_challenger(),))
    assert decision.decision == "FAIL"
    assert decision.blocking_failures == ("UNCERTAINTY",)
    assert decision.scientific_authority_effect == "NONE"


def test_missing_dimension_or_challenger_fails_closed() -> None:
    with pytest.raises(SFFContractError, match="MISSING"):
        decide_claim(generation_id="g1", dimension_results={"FULL_POPULATION": "PASS"}, falsification=_contract(), challengers=(_challenger(),))
    results = {dimension: "PASS" for dimension in _contract().blocking_dimensions}
    with pytest.raises(SFFContractError, match="CHALLENGER"):
        decide_claim(generation_id="g1", dimension_results=results, falsification=_contract(), challengers=())


def test_failure_is_append_only_and_same_generation_rescue_is_forbidden() -> None:
    failure = FailureRecord.create("g1", "semantics-v1", "ENDPOINT_FAILED", "FAILED_CONFIRMATORY")
    assert failure.append_only
    with pytest.raises(SFFContractError, match="SAME_GENERATION"):
        reentry_generation(failure, proposed_generation_id="g1", proposed_target_semantics_id="narrowed-after-result")
    assert reentry_generation(failure, proposed_generation_id="g2", proposed_target_semantics_id="semantics-v2") == "SUCCESSOR_GENERATION_NEW_SEMANTICS_REQUIRED"


@pytest.mark.parametrize(
    ("challenger", "blocker"),
    [
        (ChallengerComparison("c", True, "FAIL", "PASS"), "CHALLENGER_MATCHED_SUPPORT"),
        (ChallengerComparison("c", True, "PASS", "FAIL"), "CHALLENGER_FULL_POPULATION"),
    ],
)
def test_nonpassing_credible_challenger_is_noncompensating(challenger, blocker) -> None:
    results = {dimension: "PASS" for dimension in _contract().blocking_dimensions}
    decision = decide_claim(
        generation_id="g1",
        dimension_results=results,
        falsification=_contract(),
        challengers=(challenger,),
    )
    assert decision.decision == "FAIL"
    assert decision.blocking_failures == (blocker,)
