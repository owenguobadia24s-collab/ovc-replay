from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ovc.research_operations.cbs.comparators.common import build_estimate
from ovc.research_operations.cbs.correspondence import correspondence_tolerance_surface, directional_correspondence
from ovc.research_operations.cbs.estimands import (
    assert_estimand_separation, build_consensus_boundary_discovery, build_estimand_denominator,
    build_reference_boundary_audit,
)
from ovc.research_operations.cbs.identity import CBSContractError
from ovc.research_operations.cbs.multiplicity import (
    build_specification_opportunity_ledger, family_factorised_support, semantic_configuration_key,
)
from ovc.research_operations.cbs.regions import build_consensus_regions, build_reference_regions, build_tolerance_grid

ROOT=Path(__file__).resolve().parents[3]
CUTOFF="2020-01-01T02:00:00Z"


def estimate(method: str, time: str, ordinal: int = 0) -> dict:
    temporal={"B0":"OWNER_DEFINED_ONLINE_CAUSAL","B1":"ONLINE_CAUSAL","B2":"CONFIRMATION_DELAYED","B3":"RETROSPECTIVE"}[method]
    return build_estimate(method_id=method,family_id=f"FAMILY_{method}",config_id=f"{method}-{ordinal}",temporal_class=temporal,
        state="ESTIMATED",candidate_onset_time=time,effective_time=time,confirmation_time=time,first_valid_time=time,
        evaluation_cutoff=CUTOFF,causal_admissibility=method not in {"B3"})


def test_tolerance_grid_preserves_duplicates_without_extra_weight() -> None:
    grid=build_tolerance_grid([{"configuration_id":"t60-a","seconds":60},{"configuration_id":"t60-b","seconds":60.0},{"configuration_id":"t300","seconds":300}])
    assert grid["declared_configuration_count"] == 3 and grid["semantic_tolerance_count"] == 2
    assert grid["entries"][0]["provenance_configuration_ids"] == ["t60-a","t60-b"]
    assert all(row["family_weight"] == 1 for row in grid["entries"])


def test_reference_and_consensus_regions_are_separate_and_non_ground_truth() -> None:
    audit_den=build_estimand_denominator(estimand="REFERENCE_BOUNDARY_AUDIT",universe_id="universe")
    discovery_den=build_estimand_denominator(estimand="CONSENSUS_BOUNDARY_DISCOVERY",universe_id="universe")
    refs=[estimate("B0","2020-01-01T00:15:00Z")]
    all_estimates=refs+[estimate("B1","2020-01-01T00:16:00Z"),estimate("B2","2020-01-01T00:17:00Z")]
    reference_regions=build_reference_regions(reference_estimates=refs,tolerance_seconds=300,estimand_denominator_id=audit_den["denominator_id"])
    consensus_regions=build_consensus_regions(estimates=all_estimates,tolerance_seconds=300,estimand_denominator_id=discovery_den["denominator_id"])
    assert reference_regions["region_set_id"] != consensus_regions["region_set_id"]
    assert reference_regions["estimand_denominator_id"] != consensus_regions["estimand_denominator_id"]
    assert consensus_regions["regions"][0]["representative_rule"] == "EARLIEST_MEMBER_NOT_AVERAGE"
    audit=build_reference_boundary_audit(b0_projection_id="b0",region_set=reference_regions,denominator=audit_den,ledger_ids=["audit-ledger"])
    discovery=build_consensus_boundary_discovery(region_set=consensus_regions,denominator=discovery_den,ledger_ids=["discovery-ledger"])
    assert_estimand_separation(audit,discovery)
    with pytest.raises(CBSContractError,match="ESTIMAND_CROSSING"):
        build_reference_boundary_audit(b0_projection_id="b0",region_set=consensus_regions,denominator=audit_den,ledger_ids=[])


def test_directional_one_to_one_retains_split_merge_unmatched_and_typed_gaps() -> None:
    den=build_estimand_denominator(estimand="REFERENCE_BOUNDARY_AUDIT",universe_id="u")
    refs=build_reference_regions(reference_estimates=[estimate("B0","2020-01-01T00:15:00Z",1),estimate("B0","2020-01-01T00:20:00Z",2)],
        tolerance_seconds=300,estimand_denominator_id=den["denominator_id"])["regions"]
    challengers=[estimate("B1","2020-01-01T00:16:00Z",1),estimate("B1","2020-01-01T00:17:00Z",2),estimate("B1","2020-01-01T00:40:00Z",3)]
    ledger=directional_correspondence(references=refs,challengers=challengers,tolerance_seconds=300,estimand="REFERENCE_BOUNDARY_AUDIT",
        source_events=[{"event_id":"gap","classification":"SOURCE_GAP"},{"event_id":"end","classification":"CENSOR"}])
    assert ledger["one_to_one_first"] is True and len(ledger["matches"]) == 2
    assert ledger["splits"] and ledger["merges"]
    assert ledger["unmatched_estimate_ids"] == [challengers[2]["estimate_id"]]
    assert {row["classification"] for row in ledger["typed_source_events"]} == {"SOURCE_GAP","CENSOR"}
    assert ledger["comparator_identity_rewrite"] == "NONE"


def test_equidistant_candidate_is_preserved_as_ambiguous() -> None:
    den=build_estimand_denominator(estimand="REFERENCE_BOUNDARY_AUDIT",universe_id="u")
    refs=build_reference_regions(reference_estimates=[estimate("B0","2020-01-01T00:15:00Z")],tolerance_seconds=120,
        estimand_denominator_id=den["denominator_id"])["regions"]
    challengers=[estimate("B1","2020-01-01T00:14:00Z",1),estimate("B1","2020-01-01T00:16:00Z",2)]
    ledger=directional_correspondence(references=refs,challengers=challengers,tolerance_seconds=120,estimand="REFERENCE_BOUNDARY_AUDIT")
    assert any(row["kind"] == "REFERENCE_EQUIDISTANT" for row in ledger["ambiguities"])
    assert len(ledger["matches"]) == 1 and len(ledger["unmatched_estimate_ids"]) == 1


def test_one_to_one_matching_maximises_cardinality_before_displacement() -> None:
    den=build_estimand_denominator(estimand="REFERENCE_BOUNDARY_AUDIT",universe_id="u")
    refs=build_reference_regions(reference_estimates=[estimate("B0","2020-01-01T00:10:00Z",1),estimate("B0","2020-01-01T00:13:00Z",2)],
        tolerance_seconds=180,estimand_denominator_id=den["denominator_id"])["regions"]
    # c1 can match either reference; c2 can match only the first. A nearest-edge
    # greedy pass can strand one reference, while the ordered optimum matches both.
    challengers=[estimate("B1","2020-01-01T00:09:00Z",1),estimate("B1","2020-01-01T00:11:00Z",2)]
    ledger=directional_correspondence(references=refs,challengers=challengers,tolerance_seconds=180,estimand="REFERENCE_BOUNDARY_AUDIT")
    assert len(ledger["matches"]) == 2
    assert ledger["unmatched_region_ids"] == [] and ledger["unmatched_estimate_ids"] == []


def test_correspondence_surface_emits_every_semantic_tolerance_without_selection() -> None:
    den=build_estimand_denominator(estimand="REFERENCE_BOUNDARY_AUDIT",universe_id="u")
    refs=build_reference_regions(reference_estimates=[estimate("B0","2020-01-01T00:15:00Z")],tolerance_seconds=300,
        estimand_denominator_id=den["denominator_id"])["regions"]
    grid=build_tolerance_grid([{"configuration_id":"a","seconds":60},{"configuration_id":"b","seconds":300}])
    surface=correspondence_tolerance_surface(references=refs,challengers=[estimate("B1","2020-01-01T00:17:00Z")],tolerance_grid=grid,
        estimand="REFERENCE_BOUNDARY_AUDIT")
    assert len(surface["ledgers"]) == 2 and surface["selected_best_tolerance"] is None and surface["complete_grid"] is True


def configuration(configuration_id: str) -> dict:
    return {"configuration_id":configuration_id,"method_family_id":"B2_FAMILY","projection_id":"p","parameters":{"threshold":5},
            "representation_id":"C2_RAW_TYPED","context_id":"ALL","state":"DECLARED"}


def test_semantic_duplicate_configurations_do_not_boost_family_support() -> None:
    ledger=build_specification_opportunity_ledger([configuration("a"),configuration("b")])
    assert ledger["declared_configuration_count"] == 2 and ledger["semantic_configuration_count"] == 1
    semantic=semantic_configuration_key(configuration("a"))
    one=family_factorised_support(region_id="r",evidence=[{"method_family_id":"B2_FAMILY","dependence_cluster":"B2_DEP","estimate_id":"e1","configuration_id":"a","semantic_configuration_key":semantic}])
    duplicated=family_factorised_support(region_id="r",evidence=[{"method_family_id":"B2_FAMILY","dependence_cluster":"B2_DEP","estimate_id":"e1","configuration_id":"a","semantic_configuration_key":semantic},{"method_family_id":"B2_FAMILY","dependence_cluster":"B2_DEP","estimate_id":"e2","configuration_id":"b","semantic_configuration_key":semantic}])
    assert one["supporting_family_count"] == duplicated["supporting_family_count"] == 1
    assert one["supporting_dependence_cluster_count"] == duplicated["supporting_dependence_cluster_count"] == 1
    assert duplicated["independent_vote_count"] is None and duplicated["aggregation"] == "NO_VOTE_NO_AVERAGE"


def test_prsci_reuse_assessment_is_blob_exact_and_owner_neutral() -> None:
    assessment=json.loads((ROOT/"records/research_operations/cbs/CBSI_WP4_PRSCI_REUSE_ASSESSMENT_v0_1.json").read_text())
    for row in assessment["assessed"]:
        blob=subprocess.check_output(["git","hash-object",row["path"]],cwd=ROOT,text=True).strip()
        assert blob == row["blob_sha"]
    assert assessment["owner_semantics_changed"] is False and assessment["implementation"] == "CBS_OWNED_THIN_REFERENCE_ENGINE"
