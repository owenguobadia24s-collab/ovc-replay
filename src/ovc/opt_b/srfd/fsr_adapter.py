"""Fresh synthetic SRFD rehearsal over actual revised-C2/C2E outputs.

This adapter is intentionally fixture-only and DOES NOT resolve the separately governed
real-source representation-pack mapping blocker. It exposes transparent arithmetic views
of existing revised-C2 evidence solely to exercise the already-implemented SRFD engines.
No representation, normalization, distance, sensitivity or family output is promotable.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .distance import DistanceSpec, compute_distance
from .families import DistanceMatrix, FamilyMethodSpec, bounded_pam, hierarchical, medoid_star, pair_key
from .representation import RepresentationPack, compile_population, compile_representation, fit_minmax_normalization
from .sensitivity import build_correspondence, build_invariant_cores, method_disagreement, sensitivity_metrics

PROGRAMME_ID = "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1"
AUTHORITY = "FIXTURE_ONLY_NON_PROMOTABLE"
STATIC_FIELDS = (
    "motion_price_delta",
    "measurement_container_width",
    "location_relation_count",
    "interaction_crossing_count",
    "quality_issue_count",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _axis(snapshot: Mapping[str, Any], axis: str) -> Mapping[str, Any]:
    return next(item for item in snapshot["formula_outputs"] if item["axis"] == axis)


def _measurement_container(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    return next(
        item
        for item in snapshot["containers"]
        if item.get("family") == "TRAILING_RANGE_SNAPSHOT" and item.get("kind") == "MEASUREMENT"
    )


def _static_structural(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    motion = _axis(snapshot, "MOTION")
    location = _axis(snapshot, "LOCATION")
    interaction = _axis(snapshot, "INTERACTION")
    quality = _axis(snapshot, "QUALITY")
    container = _measurement_container(snapshot)
    interaction_value: int | None = len(interaction.get("facts", {}).get("crossings", []))
    if interaction.get("computability") != "COMPUTABLE":
        interaction_value = None
    quality_issues = sum(
        1
        for item in quality.get("facts", {}).get("components", [])
        if item.get("status") != "COMPUTABLE"
        or item.get("censored")
        or item.get("ambiguous")
        or item.get("conflict")
    )
    return {
        "motion_price_delta": motion.get("facts", {}).get("price_delta"),
        "measurement_container_width": container.get("width"),
        "location_relation_count": len(location.get("facts", {}).get("relations", [])),
        "interaction_crossing_count": interaction_value,
        "quality_issue_count": quality_issues,
    }


def static_source_records(c2_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for snapshot in sorted(c2_manifest["snapshots"], key=lambda item: (item["side"], item["as_of_time"], item["snapshot_id"])):
        structural = _static_structural(snapshot)
        missing = sorted(key for key, value in structural.items() if value is None)
        records.append(
            {
                "record_id": snapshot["snapshot_id"],
                "first_valid_time": snapshot["as_of_time"],
                "computability_status": "NOT_EVALUABLE" if missing else "EVALUABLE",
                "not_evaluable_reason": "REP_REQUIRED_DIMENSION_MISSING:" + ",".join(missing) if missing else None,
                "structural": structural,
                "parent_context": snapshot.get("parent_context"),
                "instrument": "GBPUSD",
                "side": snapshot["side"],
                "units": "MIXED_TYPED_ARITHMETIC",
                "clock": "15M",
                "representation_schema": "FSR_REVISED_C2_STATIC_V1",
                "source_quality": "SYNTHETIC_FIXTURE",
                "source_snapshot_sha256": _sha(snapshot),
            }
        )
    return records


def _episode_member_map(c2_manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(item["snapshot_id"]): item for item in c2_manifest["snapshots"]}


def episode_source_records(c2_manifest: Mapping[str, Any], c2e_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_snapshot = _episode_member_map(c2_manifest)
    records: list[dict[str, Any]] = []
    for ledger in c2e_manifest["ledgers"]:
        for episode in ledger["episodes"]:
            sequence: list[dict[str, Any]] = []
            for member_id in episode["member_record_ids"]:
                snapshot = by_snapshot.get(str(member_id))
                if snapshot is None:
                    continue
                structural = _static_structural(snapshot)
                sequence.append({"motion_price_delta": structural["motion_price_delta"]})
            if not sequence:
                continue
            records.append(
                {
                    "record_id": episode["episode_id"],
                    "first_valid_time": episode["first_valid_time"],
                    "computability_status": "EVALUABLE",
                    "not_evaluable_reason": None,
                    "sequence": sequence,
                    "structural": {"duration_count": len(sequence), "censored": 1 if episode["status"] == "CENSORED" else 0},
                    "parent_context": None,
                    "instrument": "GBPUSD",
                    "side": ledger["side"],
                    "units": "PRICE_DELTA",
                    "clock": "15M",
                    "representation_schema": "FSR_C2E_SEQUENCE_V1",
                    "source_quality": "SYNTHETIC_FIXTURE",
                    "episode_status": episode["status"],
                }
            )
    return sorted(records, key=lambda item: (item["side"], item["first_valid_time"], item["record_id"]))


def _decorate(representation: Mapping[str, Any], source: Mapping[str, Any], schema: str) -> dict[str, Any]:
    return {
        **dict(representation),
        "instrument": source["instrument"],
        "side": source["side"],
        "units": source["units"],
        "clock": source["clock"],
        "representation_schema": schema,
        "source_quality": source["source_quality"],
    }


def _representation_sets(c2_manifest: Mapping[str, Any], c2e_manifest: Mapping[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    static_records = static_source_records(c2_manifest)
    episode_records = episode_source_records(c2_manifest, c2e_manifest)
    eligible_static = [item for item in static_records if item["computability_status"] == "EVALUABLE"]
    static_population = compile_population(static_records, population_name="FSR_REVISED_C2_STATIC")
    episode_population = compile_population(episode_records, population_name="FSR_C2E_EPISODES")
    fit_records = eligible_static[: max(2, len(eligible_static) // 2)]
    fit_cutoff = max(item["first_valid_time"] for item in fit_records)
    normalization = fit_minmax_normalization(fit_records, STATIC_FIELDS, fit_population_id=static_population["population_id"], fit_cutoff=fit_cutoff)

    packs = {
        "R1": RepresentationPack("FSR.SRFD.R1.RAW_C2.v1", "SRFDI-R1", "R0", STATIC_FIELDS, "FSR.STATIC", "STATIC_VECTOR"),
        "R2": RepresentationPack("FSR.SRFD.R2.C2E_AGG.v1", "SRFDI-R2", "R3", ("motion_price_delta",), "FSR.EPISODE_AGG", "STATIC_VECTOR"),
        "R3": RepresentationPack("FSR.SRFD.R3.ORDERED_MOTION.v1", "SRFDI-R3", "R4", (), "FSR.SEQUENCE", "ORDERED_SEQUENCE"),
        "R4": RepresentationPack("FSR.SRFD.R4.NORMALIZED_C2.v1", "SRFDI-R4", "R1_R2_R5_TRANSFORM_CLASS", STATIC_FIELDS, "FSR.STATIC_NORM", "STATIC_VECTOR"),
        "R5": RepresentationPack("FSR.SRFD.R5.HYBRID_SEQUENCE.v1", "SRFDI-R5", "R6", (), "FSR.SEQUENCE_HYBRID", "HYBRID"),
        "R6": RepresentationPack("FSR.SRFD.R6.ABLATE_LOCATION.v1", "SRFDI-R6", "DERIVED_BENCHMARK_VARIANT", STATIC_FIELDS, "FSR.STATIC_ABLATION", "STATIC_VECTOR", ("location_relation_count",)),
        "R7": RepresentationPack("FSR.SRFD.R7.PARENT_CONTEXT.v1", "SRFDI-R7", "R7", STATIC_FIELDS, "FSR.STATIC_CONTEXT", "STATIC_VECTOR"),
        "R8": RepresentationPack("FSR.SRFD.R8.MISSINGNESS.v1", "SRFDI-R8", "R8", STATIC_FIELDS, "FSR.STATIC_MISSING", "STATIC_VECTOR"),
        "R9": RepresentationPack("FSR.SRFD.R9.NULL.v1", "SRFDI-R9", "NULL_CONTROL", (), "FSR.NULL", "STATIC_VECTOR"),
    }
    sets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in static_records:
        for key in ("R8", "R9"):
            sets[key].append(_decorate(compile_representation(source, packs[key], source_population_id=static_population["population_id"]), source, f"FSR_{key}_V1"))
        if source["computability_status"] != "EVALUABLE":
            continue
        for key in ("R1", "R6", "R7"):
            sets[key].append(_decorate(compile_representation(source, packs[key], source_population_id=static_population["population_id"]), source, f"FSR_{key}_V1"))
        sets["R4"].append(_decorate(compile_representation(source, packs["R4"], source_population_id=static_population["population_id"], normalization_pack=normalization), source, "FSR_R4_V1"))
    for source in episode_records:
        for key in ("R2", "R3", "R5"):
            sets[key].append(_decorate(compile_representation(source, packs[key], source_population_id=episode_population["population_id"]), source, f"FSR_{key}_V1"))

    return {key: sorted(value, key=lambda item: item["representation_id"]) for key, value in sets.items()}, {
        "static_population": static_population,
        "episode_population": episode_population,
        "normalization_pack": normalization.to_dict(),
        "fit_record_count": len(fit_records),
        "fit_cutoff": fit_cutoff,
        "pack_ids": {key: value.representation_pack_id for key, value in packs.items()},
        "real_source_mapping_blocker_resolved": False,
        "mapping_authority": "FSR_FIXTURE_ADAPTER_ONLY",
    }


def _distance_results(representations: Sequence[Mapping[str, Any]], spec: DistanceSpec) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in representations:
        grouped[str(item["side"])].append(item)
    for side in sorted(grouped):
        group = sorted(grouped[side], key=lambda item: item["representation_id"])
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                values.append(compute_distance(left, right, spec))
    return values


def _matrix(representations: Sequence[Mapping[str, Any]], distance_results: Sequence[Mapping[str, Any]], *, side: str) -> DistanceMatrix:
    group = [item for item in representations if item["side"] == side]
    ids = [str(item["representation_id"]) for item in group]
    by_pair_id = {str(item["pair_id"]): item for item in distance_results if item["status"] == "COMPUTED"}
    pairs: dict[str, str] = {}
    spec = DistanceSpec("FSR.DIST.L1.NORMALIZED.v1", "L1_TYPED", STATIC_FIELDS)
    for i, left in enumerate(group):
        for right in group[i + 1 :]:
            pair_id = compute_distance(left, right, spec)["pair_id"]
            result = by_pair_id[pair_id]
            pairs[pair_key(str(left["representation_id"]), str(right["representation_id"]))] = str(result["distance"])
    return DistanceMatrix.from_pairs(ids, pairs)


def _family_benchmark(normalized_representations: Sequence[Mapping[str, Any]], normalized_distances: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    catalogs: list[dict[str, Any]] = []
    by_side: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in normalized_representations:
        by_side[str(item["side"])].append(item)
    for side in sorted(by_side):
        matrix = _matrix(normalized_representations, normalized_distances, side=side)
        n = len(matrix.ids)
        if n < 2:
            continue
        for radius in ("0.15", "0.30"):
            star = FamilyMethodSpec("GREEDY_LEXICOGRAPHIC_MEDOID_STAR", f"FSR.{side}.STAR.R{radius}", radius=radius, minimum_support=2)
            complete = FamilyMethodSpec("COMPLETE_LINKAGE", f"FSR.{side}.COMPLETE.R{radius}", radius=radius, minimum_support=2, linkage="complete")
            average = FamilyMethodSpec("AVERAGE_LINKAGE", f"FSR.{side}.AVERAGE.R{radius}", radius=radius, minimum_support=2, linkage="average")
            catalogs.extend((medoid_star(matrix, star), hierarchical(matrix, complete), hierarchical(matrix, average)))
        pam_k = min(3, max(1, n // 3))
        catalogs.append(bounded_pam(matrix, FamilyMethodSpec("BOUNDED_PAM", f"FSR.{side}.PAM.K{pam_k}", k=pam_k, minimum_support=2, max_iterations=20, max_assignment_distance="0.30")))

    correspondences: list[dict[str, Any]] = []
    grouped_catalogs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for catalog in catalogs:
        pieces = str(catalog["configuration_id"]).split(".")
        grouped_catalogs[pieces[1] if len(pieces) > 1 else "UNKNOWN"].append(catalog)
    for side in sorted(grouped_catalogs):
        ordered = sorted(grouped_catalogs[side], key=lambda item: (item["method_id"], item["configuration_id"]))
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                correspondences.append(build_correspondence(left, right))
    return {
        "catalogs": catalogs,
        "sensitivity_metrics": sensitivity_metrics(catalogs),
        "correspondences": correspondences,
        "invariant_cores": build_invariant_cores(catalogs, minimum_catalog_support=2),
        "method_disagreement": method_disagreement(catalogs),
        "evidence_status_counts": dict(sorted(Counter(item["evidence_status"] for item in catalogs).items())),
        "residual_count": sum(len(item["residual_ids"]) for item in catalogs),
    }


def run_fsr_srfd(c2_manifest: Mapping[str, Any], c2e_manifest: Mapping[str, Any]) -> dict[str, Any]:
    sets, metadata = _representation_sets(c2_manifest, c2e_manifest)
    specs = {
        "R1_L1": DistanceSpec("FSR.DIST.R1.L1.v1", "L1_TYPED", STATIC_FIELDS),
        "R1_L2": DistanceSpec("FSR.DIST.R1.L2.v1", "L2_TYPED", STATIC_FIELDS),
        "R1_GOWER": DistanceSpec("FSR.DIST.R1.GOWER.v1", "GOWER_MIXED", STATIC_FIELDS),
        "R2_L1": DistanceSpec("FSR.DIST.R2.L1.v1", "L1_TYPED", ("motion_price_delta_mean", "duration_count")),
        "R3_DTW": DistanceSpec("FSR.DIST.R3.DTW.v1", "DTW_SEQUENCE", ()),
        "R4_L1": DistanceSpec("FSR.DIST.L1.NORMALIZED.v1", "L1_TYPED", STATIC_FIELDS),
        "R5_DTW": DistanceSpec("FSR.DIST.R5.DTW.v1", "DTW_SEQUENCE", ()),
        "R6_L1": DistanceSpec("FSR.DIST.R6.L1.v1", "L1_TYPED", tuple(field for field in STATIC_FIELDS if field != "location_relation_count")),
        "R7_L1": DistanceSpec("FSR.DIST.R7.L1.v1", "L1_TYPED", STATIC_FIELDS),
        "R9_GOWER": DistanceSpec("FSR.DIST.R9.NULL_GOWER.v1", "GOWER_MIXED", ("null_control_token",)),
    }
    distances: dict[str, list[dict[str, Any]]] = {}
    mapping = {"R1_L1":"R1","R1_L2":"R1","R1_GOWER":"R1","R2_L1":"R2","R3_DTW":"R3","R4_L1":"R4","R5_DTW":"R5","R6_L1":"R6","R7_L1":"R7","R9_GOWER":"R9"}
    for name, spec in specs.items():
        distances[name] = _distance_results(sets[mapping[name]], spec)
    family = _family_benchmark(sets["R4"], distances["R4_L1"])
    body = {
        "schema": "ovc-fsr-srfd-rehearsal/v1",
        "programme_id": PROGRAMME_ID,
        "fixture_id": c2_manifest["fixture_id"],
        "source_c2_sha256": c2_manifest["logical_sha256"],
        "source_c2e_sha256": c2e_manifest["logical_sha256"],
        "representation_metadata": metadata,
        "representation_counts": {key: len(value) for key, value in sorted(sets.items())},
        "representation_hashes": {key: _sha(value) for key, value in sorted(sets.items())},
        "distance_counts": {key: len(value) for key, value in sorted(distances.items())},
        "distance_status_counts": {key: dict(sorted(Counter(item["status"] for item in value).items())) for key, value in sorted(distances.items())},
        "family_benchmark": family,
        "lawful_null_outcomes": ["NO_STABLE_FAMILY", "METHOD_DEPENDENT_STRUCTURE_ONLY", "UNRESOLVED"],
        "hidden_construction_consumed": False,
        "authority": {
            "mode": AUTHORITY,
            "real_source_field_mapping": "UNRESOLVED_NOT_CHANGED",
            "canonical_representation": "NONE",
            "canonical_normalization": "NONE",
            "canonical_distance": "NONE",
            "canonical_sensitivity": "NONE",
            "canonical_family_method": "NONE",
            "canonical_family": "NONE",
            "selector": "NONE",
            "publication": "NONE",
            "validation_consumption": "DENIED",
            "semantic_probability_risk_exposure_execution": "NONE"
        },
    }
    body["logical_sha256"] = _sha(body)
    return body
