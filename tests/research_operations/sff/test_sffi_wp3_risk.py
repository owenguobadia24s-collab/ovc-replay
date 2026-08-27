import pytest

from ovc.research_operations.sff.core import SFFContractError
from ovc.research_operations.sff.risk import (
    DistributionRecord,
    ForecastRiskSetManifest,
    RiskSetEntry,
    RiskStatus,
    evaluate_with_opt_c,
)


def _entry(target: str, status: RiskStatus, *, origin: str = "o1", owner: str = "RESOLVED_CURRENT_AUTHORIZED"):
    return RiskSetEntry(target, origin, 0, status, f"dependence:{origin}", owner)


def test_full_population_denominator_preserves_all_partitions() -> None:
    rows = [_entry("t1", RiskStatus.RESOLVED), _entry("t2", RiskStatus.PREEMPTED), _entry("t3", RiskStatus.STILL_AT_RISK)]
    manifest = ForecastRiskSetManifest.build("declared-population", rows)
    assert manifest.denominator == 3
    assert sum(manifest.counts().values()) == 3
    assert manifest.counts()["PREEMPTED"] == 1


def test_survivor_convenience_subset_changes_identity_and_cannot_claim_original_denominator() -> None:
    full = ForecastRiskSetManifest.build("declared-population", [_entry("t1", RiskStatus.RESOLVED), _entry("t2", RiskStatus.CENSORED)])
    survivor = ForecastRiskSetManifest.build("declared-population", [_entry("t1", RiskStatus.RESOLVED)])
    assert survivor.denominator != full.denominator
    assert survivor.risk_set_id != full.risk_set_id


def test_missing_owner_dependency_becomes_not_evaluable_and_opt_c_abstains() -> None:
    manifest = ForecastRiskSetManifest.build("p", [_entry("t1", RiskStatus.RESOLVED, owner="MISSING")])
    assert manifest.entries[0].status is RiskStatus.NOT_EVALUABLE
    assert evaluate_with_opt_c(None, "t1")["status"] == "ABSTAINED"


def test_partial_distribution_never_renormalizes_and_unknown_support_is_not_zero() -> None:
    partial = DistributionRecord({"A": 0.4}, "PARTIAL", "UNKNOWN")
    assert partial.probabilities["A"] == 0.4
    assert partial.probability("UNOBSERVED") is None
    with pytest.raises(SFFContractError):
        DistributionRecord({"A": 0.4}, "COMPLETE", "KNOWN")


def test_repeated_snapshots_share_explicit_dependence_group() -> None:
    rows = (
        RiskSetEntry("t1", "origin", 0, RiskStatus.STILL_AT_RISK, "dependence:origin"),
        RiskSetEntry("t1", "origin", 1, RiskStatus.RESOLVED, "dependence:origin"),
    )
    manifest = ForecastRiskSetManifest.build("p", rows)
    assert len({row.dependence_group_id for row in manifest.entries}) == 1
    assert manifest.repeated_snapshot_policy == "DEPENDENT_WITHIN_ORIGIN"


def test_nonfinite_probability_and_repeated_origin_pseudo_independence_fail_closed() -> None:
    with pytest.raises(SFFContractError, match="finite"):
        DistributionRecord({"A": float("nan")}, "COMPLETE", "KNOWN")
    rows = (
        RiskSetEntry("t1", "origin", 0, RiskStatus.STILL_AT_RISK, "dependence:one"),
        RiskSetEntry("t1", "origin", 1, RiskStatus.RESOLVED, "dependence:two"),
    )
    with pytest.raises(SFFContractError, match="PSEUDO_INDEPENDENCE"):
        ForecastRiskSetManifest.build("p", rows)
