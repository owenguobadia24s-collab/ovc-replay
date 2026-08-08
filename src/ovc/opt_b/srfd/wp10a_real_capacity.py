from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import resource
import time
from typing import Any, Iterable, Mapping, Sequence

from .distance import DistanceSpec, compute_distance
from .families import DistanceMatrix
from .pattern_family_capacity import PatternDistanceSurface, materialize_pattern_full_grid
from .real_source_packs import compile_real_source_representation
from .serialization import logical_sha256


FROZEN_POPULATION_ID = "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd"
FROZEN_ELIGIBLE_COUNT = 8598
FROZEN_ELIGIBLE_IDS_SHA256 = "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e"
FROZEN_DOMAIN_COUNT = 36
FROZEN_PAIR_COUNT = 35380668
FROZEN_FAMILY_CONFIGURATION_COUNT = 1944
T0_MAX_WALL_SECONDS = 14400
T0_MAX_PEAK_RSS_BYTES = 17179869184
T0_MAX_EXTERNAL_BYTES = 10737418240

FROZEN_SOURCE_RELEASE_ID = "PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9"
FROZEN_SOURCE_COMMIT = "837c9a3e1cbfc18bf01d577896a8f2e01d12f7d2"
FROZEN_SOURCE_SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
FROZEN_SOURCE_MANIFEST_SHA256 = "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3"
FROZEN_OUTPUT_MANIFEST_SHA256 = "e805eaa0f8603da644d23d83297fdc5e62142f8051d8583c9c28c9469a3b704b"
FROZEN_ACTIVE_C2_RELEASE_ID = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
FROZEN_OPERATION_MODE = "TIME_GATED_REPLAY"
FROZEN_ROLE = "DISCOVERY"
NON_EVALUATED_PRECEDENCE = ("QUARANTINED", "CONFLICT", "CENSORED", "NOT_EVALUABLE", "NOT_EVALUATED")

FROZEN_C2_FILE_SHA256 = {
    "C2_15M_ASK_LOCAL": "f0df9558afc5740aabd2dd9f75e958880efd5343b70982d77f4c1e3252ba4e8a",
    "C2_15M_ASK_PARENT": "4b67517f54d02b1f601c451b4f4ed9eb5a1dee05712ef44c1463b06f8500f879",
    "C2_15M_BID_LOCAL": "63a1d24836d3cd0aaad9e5a11e9b9ec51724bfd335fab47f538ed23f36e8c58b",
    "C2_15M_BID_PARENT": "15e487cede1bd8a2ccdbfe4c515c72d10b6e5bea9c54f1c7212a368a146e1b88",
    "C2_2H_ASK_LOCAL": "f671c18b01d840d3cca8a058f905104146f77254b7ca400378818697242170cb",
    "C2_2H_BID_LOCAL": "ce7704f1a29dde6e22e0083fbcfda67fef2929875304c2eb9a0874e63d3d27f5",
}


class WP10ACapacityError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class CapacitySourceFile:
    source_key: str
    path: Path
    sha256: str
    record_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "file_name": self.path.name,
            "sha256": self.sha256,
            "record_count": self.record_count,
        }


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise WP10ACapacityError(
                    "QA_SCHEMA_FAILURE",
                    f"{path.name}:{line_number}:{exc}",
                ) from exc
            if not isinstance(row, Mapping):
                raise WP10ACapacityError("QA_SCHEMA_FAILURE", f"{path.name}:{line_number}")
            rows.append(dict(row))
    return rows


def verify_and_load_frozen_c2_files(
    paths: Mapping[str, str | Path],
) -> tuple[list[dict[str, Any]], list[CapacitySourceFile]]:
    if set(paths) != set(FROZEN_C2_FILE_SHA256):
        raise WP10ACapacityError(
            "SOURCE_BINDING_MISMATCH",
            f"required={sorted(FROZEN_C2_FILE_SHA256)} actual={sorted(paths)}",
        )
    all_rows: list[dict[str, Any]] = []
    receipts: list[CapacitySourceFile] = []
    for source_key in sorted(paths):
        path = Path(paths[source_key])
        if not path.is_file():
            raise WP10ACapacityError("ARTIFACT_UNAVAILABLE", f"{source_key}:{path}")
        actual_sha = _file_sha256(path)
        if actual_sha != FROZEN_C2_FILE_SHA256[source_key]:
            raise WP10ACapacityError(
                "SOURCE_BINDING_MISMATCH",
                f"{source_key}:{actual_sha}",
            )
        rows = _load_jsonl(path)
        receipts.append(CapacitySourceFile(source_key, path, actual_sha, len(rows)))
        all_rows.extend(rows)
    if len(all_rows) != 9420:
        raise WP10ACapacityError("SOURCE_BINDING_MISMATCH", f"record_count={len(all_rows)}")
    eligible_ids = sorted(
        str(row["c2_state_id"]) for row in all_rows if bool(row.get("target_eligible"))
    )
    if len(eligible_ids) != FROZEN_ELIGIBLE_COUNT:
        raise WP10ACapacityError("POPULATION_BINDING_MISMATCH", f"eligible={len(eligible_ids)}")
    eligible_hash = sha256(
        json.dumps(
            eligible_ids,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    if eligible_hash != FROZEN_ELIGIBLE_IDS_SHA256:
        raise WP10ACapacityError("POPULATION_BINDING_MISMATCH", eligible_hash)
    return all_rows, receipts


def _computability(axes: Mapping[str, Mapping[str, Any]]) -> tuple[str, str | None]:
    for status in NON_EVALUATED_PRECEDENCE:
        if any(str(item["status"]) == status for item in axes.values()):
            reasons = [
                f"{name}:{item['status']}:{item.get('reason_code') or 'UNSPECIFIED'}"
                for name, item in axes.items()
                if item["status"] != "EVALUATED"
            ]
            return status, "|".join(reasons)
    return "EVALUABLE", None


def _capacity_adapted_record(row: Mapping[str, Any]) -> dict[str, Any]:
    if str(row.get("active_c2_model_release_id")) != FROZEN_ACTIVE_C2_RELEASE_ID:
        raise WP10ACapacityError("SOURCE_BINDING_MISMATCH", "active C2 release")
    if str(row.get("source_slice_id")) != FROZEN_SOURCE_SLICE_ID:
        raise WP10ACapacityError("SOURCE_BINDING_MISMATCH", "source slice")
    if str(row.get("operation_mode")) != FROZEN_OPERATION_MODE or str(row.get("role")) != FROZEN_ROLE:
        raise WP10ACapacityError("AUTH_SCOPE_EXPANSION", "operation mode/role")
    if bool(row.get("release_membership")):
        raise WP10ACapacityError("AUTH_SCOPE_EXPANSION", "release membership")
    if str(row.get("live_prospective_append", "DENIED")) != "DENIED":
        raise WP10ACapacityError("AUTH_SCOPE_EXPANSION", "live prospective append")

    raw_axes = row.get("axes")
    if not isinstance(raw_axes, Mapping):
        raise WP10ACapacityError("QA_SCHEMA_FAILURE", "native C2 axes required")
    axis_payload: dict[str, dict[str, Any]] = {}
    for axis_name in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY"):
        axis = raw_axes.get(axis_name)
        if not isinstance(axis, Mapping):
            raise WP10ACapacityError("QA_SCHEMA_FAILURE", f"axis={axis_name}")
        status = str(axis.get("status") or "").upper()
        if not status:
            raise WP10ACapacityError("QA_SCHEMA_FAILURE", f"axis status={axis_name}")
        value = axis.get("value")
        reason = axis.get("reason_code")
        measurement = axis.get("measurement")
        axis_payload[axis_name] = {
            "status": status,
            "value": str(value) if value is not None else None,
            "reason_code": str(reason) if reason is not None else None,
            "measurement": str(measurement) if measurement is not None else None,
        }
    computability_status, computability_reason = _computability(axis_payload)
    scope = str(row.get("evaluation_scope_id") or "")
    record_id = str(row.get("c2_state_id") or "")
    parent_c1 = str(row.get("parent_c1_record_id") or "")
    source_lineage = {
        "source_release_id": FROZEN_SOURCE_RELEASE_ID,
        "source_commit": FROZEN_SOURCE_COMMIT,
        "source_slice_id": FROZEN_SOURCE_SLICE_ID,
        "source_manifest_sha256": FROZEN_SOURCE_MANIFEST_SHA256,
        "output_manifest_sha256": FROZEN_OUTPUT_MANIFEST_SHA256,
        "active_c2_model_release_id": FROZEN_ACTIVE_C2_RELEASE_ID,
        "c1_record_id": parent_c1,
        "c1_release_id": str(row.get("c1_release_id") or ""),
        "c1_manifest_id": str(row.get("c1_manifest_id") or ""),
        "opt_a_release_id": str(row.get("opt_a_release_id") or ""),
        "opt_a_manifest_id": str(row.get("opt_a_manifest_id") or ""),
        "parent_opt_a_bar_id": str(row.get("parent_opt_a_bar_id") or ""),
    }
    return {
        "record_id": record_id,
        "first_valid_time": str(row.get("first_valid_time") or ""),
        "instrument": "GBPUSD",
        "side": str(row.get("side") or "").upper(),
        "clock": str(row.get("clock") or ""),
        "units": "MIXED_TYPED_C2",
        "representation_schema": f"C2_TYPED_AXES:{FROZEN_ACTIVE_C2_RELEASE_ID}:{scope}",
        "source_quality": "ACCEPTED_FROZEN_C2",
        "evaluation_scope_id": scope,
        "eligibility_class": str(row.get("eligibility_class") or ""),
        "target_eligible": bool(row.get("target_eligible")),
        "computability_status": computability_status,
        "not_evaluable_reason": computability_reason,
        "native_c2": {
            "axes": axis_payload,
            "level_ids": sorted(str(item) for item in row.get("level_ids", ())),
            "container_ids": sorted(str(item) for item in row.get("container_ids", ())),
            "relation_set_id": str(row.get("relation_set_id") or ""),
            "persistence": dict(row["persistence"]) if isinstance(row.get("persistence"), Mapping) else row.get("persistence"),
            "continuity": str(row.get("continuity") or ""),
            "parameter_pack_id": str(row.get("parameter_pack_id") or ""),
        },
        "source_lineage": source_lineage,
        "source_logical_sha256": logical_sha256(dict(row)),
        "adapter_semantics": "SCHEMA_PRESERVING_NO_REPRESENTATION_FIELD_SELECTION",
        "adapter_id": "SRFDI-SOURCE-ADAPTER-v0.2",
        "evaluated_reason_policy": "PRESERVE_OPTIONAL_DESCRIPTIVE_REASON_CODE",
    }


def compile_capacity_domains(
    rows: Iterable[Mapping[str, Any]],
    registry: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    domains: dict[str, list[dict[str, Any]]] = {}
    representation_counts: dict[str, int] = {}
    for row in rows:
        if not bool(row.get("target_eligible")):
            continue
        source = _capacity_adapted_record(row)
        evaluable = source["computability_status"] == "EVALUABLE"
        requests: list[tuple[str, str | None]] = []
        if evaluable:
            requests.append(("SRFDI-R1", None))
            requests.extend(
                ("SRFDI-R6", variant)
                for variant in (
                    "SRFDI-R6-DROP-LOCATION",
                    "SRFDI-R6-DROP-MOTION",
                    "SRFDI-R6-DROP-ORGANISATION",
                    "SRFDI-R6-DROP-INTERACTION",
                    "SRFDI-R6-DROP-QUALITY",
                )
            )
        requests.extend((("SRFDI-R8", None), ("SRFDI-R9", None)))
        for implementation_class_id, variant_id in requests:
            compiled = compile_real_source_representation(
                source,
                registry,
                implementation_class_id,
                source_population_id=FROZEN_POPULATION_ID,
                variant_id=variant_id,
            )
            domain_id = str(compiled["comparability_domain_id"])
            domains.setdefault(domain_id, []).append(compiled)
            counter_key = variant_id or implementation_class_id
            representation_counts[counter_key] = representation_counts.get(counter_key, 0) + 1
    for records in domains.values():
        records.sort(key=lambda item: str(item["representation_id"]))
    expected_counts = {
        "SRFDI-R1": 4996,
        "SRFDI-R6-DROP-LOCATION": 4996,
        "SRFDI-R6-DROP-MOTION": 4996,
        "SRFDI-R6-DROP-ORGANISATION": 4996,
        "SRFDI-R6-DROP-INTERACTION": 4996,
        "SRFDI-R6-DROP-QUALITY": 4996,
        "SRFDI-R8": 8598,
        "SRFDI-R9": 8598,
    }
    if representation_counts != expected_counts:
        raise WP10ACapacityError(
            "REPRESENTATION_BINDING_MISMATCH",
            f"counts={representation_counts}",
        )
    if len(domains) != FROZEN_DOMAIN_COUNT:
        raise WP10ACapacityError("COMPARABILITY_DOMAIN_MISMATCH", f"domains={len(domains)}")
    pair_count = sum(len(records) * (len(records) - 1) // 2 for records in domains.values())
    if pair_count != FROZEN_PAIR_COUNT:
        raise WP10ACapacityError("DISTANCE_PAIR_COUNT_MISMATCH", f"pairs={pair_count}")
    return dict(sorted(domains.items()))


def _gower_fields(record: Mapping[str, Any]) -> tuple[str, ...]:
    raw = record.get("structural_raw")
    if isinstance(raw, Mapping) and raw:
        return tuple(sorted(str(key) for key in raw))
    comparison = record.get("comparison_only")
    if isinstance(comparison, Mapping) and "null_control_token" in comparison:
        return ("null_control_token",)
    raise WP10ACapacityError("DISTANCE_BINDING_MISMATCH", "no frozen Gower fields")


def _combined_value(record: Mapping[str, Any], field: str) -> Any:
    for namespace in (
        "structural_raw",
        "structural_derived",
        "structural_normalized",
        "comparison_only",
    ):
        values = record.get(namespace)
        if isinstance(values, Mapping) and field in values:
            return values[field]
    raise WP10ACapacityError("DISTANCE_BINDING_MISMATCH", field)


def gower_pattern_surface(records: Sequence[Mapping[str, Any]]) -> PatternDistanceSurface:
    if len(records) < 2:
        raise WP10ACapacityError("DISTANCE_BINDING_MISMATCH", "domain requires >=2 records")
    fields = _gower_fields(records[0])
    for record in records:
        if _gower_fields(record) != fields:
            raise WP10ACapacityError("DISTANCE_BINDING_MISMATCH", "field set changed within domain")
    return PatternDistanceSurface.from_records(
        records,
        fields=fields,
        value_getter=_combined_value,
    )


def gower_distance_matrix(records: Sequence[Mapping[str, Any]]) -> DistanceMatrix:
    """Small-fixture semantic oracle; real capacity execution uses pattern compression."""
    surface = gower_pattern_surface(records)
    pair_values = {
        f"{left}|{right}": format(surface.distance(left, right), "f")
        for left, right in combinations(surface.ids, 2)
    }
    return DistanceMatrix.from_pairs(surface.ids, pair_values)


def verify_gower_batch_against_reference(
    records: Sequence[Mapping[str, Any]],
    surface: Any,
    *,
    sample_pairs: int = 64,
) -> dict[str, Any]:
    by_id = {str(record["representation_id"]): record for record in records}
    fields = _gower_fields(records[0])
    spec = DistanceSpec("SRFDI-WP10A-GOWER-CHECK", "GOWER_MIXED", fields)
    pairs = list(combinations(surface.ids, 2))
    if len(pairs) > sample_pairs:
        stride = max(1, len(pairs) // sample_pairs)
        pairs = pairs[::stride][:sample_pairs]
    for left, right in pairs:
        expected = compute_distance(by_id[left], by_id[right], spec)
        actual = format(surface.distance(left, right), "f")
        if expected["distance"] != actual:
            raise WP10ACapacityError(
                "G10A_DISTANCE_EQUIVALENCE_FAILURE",
                f"{left}|{right}:{expected['distance']}!={actual}",
            )
    payload = {
        "schema": "ovc-srfdi-wp10a-gower-equivalence/v1",
        "checked_pairs": len(pairs),
        "fields": list(fields),
        "result": "PASS",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value * 1024


def _is_exact_null_control(surface: PatternDistanceSurface) -> bool:
    if surface.fields != ("null_control_token",):
        return False
    if surface.unique_pattern_count != len(surface.ids):
        return False
    return all(
        surface.distance(left, right) == Decimal("1.000000000000")
        for left, right in zip(surface.ids, surface.ids[1:])
    )


def execute_domain_family_grid(
    domain_id: str,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    start = time.perf_counter()
    surface_start = time.perf_counter()
    surface = gower_pattern_surface(records)
    surface_seconds = time.perf_counter() - surface_start
    gower_equivalence = verify_gower_batch_against_reference(records, surface)
    null_fast_path = _is_exact_null_control(surface)

    grid_start = time.perf_counter()
    grid = materialize_pattern_full_grid(
        surface,
        domain_id=domain_id,
        null_control_all_off_diagonal_one=null_fast_path,
    )
    grid_seconds = time.perf_counter() - grid_start
    if int(grid["configuration_count"]) != 54:
        raise WP10ACapacityError(
            "FROZEN_GRID_INCOMPLETE",
            f"domain={domain_id}:configs={grid['configuration_count']}",
        )
    payload = {
        "domain_id": domain_id,
        "population_count": len(surface.ids),
        "unique_pattern_count": surface.unique_pattern_count,
        "pair_count": len(surface.ids) * (len(surface.ids) - 1) // 2,
        "configuration_count": int(grid["configuration_count"]),
        "catalog_hashes_sha256": str(grid["catalog_hashes_sha256"]),
        "gower_equivalence": gower_equivalence,
        "null_control_fast_path": null_fast_path,
        "stage_seconds": {
            "pattern_surface": round(surface_seconds, 9),
            "full_grid_materialization": round(grid_seconds, 9),
        },
        "wall_seconds": round(time.perf_counter() - start, 9),
        "peak_rss_bytes_after_domain": _peak_rss_bytes(),
        "scientific_effect": "NONE_CAPACITY_ONLY",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}


def execute_full_real_capacity_grid(
    source_paths: Mapping[str, str | Path],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    rows, source_receipts = verify_and_load_frozen_c2_files(source_paths)
    domains = compile_capacity_domains(rows, registry)
    domain_receipts: list[dict[str, Any]] = []
    for domain_id, records in domains.items():
        domain_receipts.append(execute_domain_family_grid(domain_id, records))
    wall_seconds = time.perf_counter() - started
    config_count = sum(int(item["configuration_count"]) for item in domain_receipts)
    pair_count = sum(int(item["pair_count"]) for item in domain_receipts)
    peak_rss = _peak_rss_bytes()
    if config_count != FROZEN_FAMILY_CONFIGURATION_COUNT:
        raise WP10ACapacityError("FROZEN_GRID_INCOMPLETE", f"configs={config_count}")
    if pair_count != FROZEN_PAIR_COUNT:
        raise WP10ACapacityError("DISTANCE_PAIR_COUNT_MISMATCH", f"pairs={pair_count}")
    catalog_grid_hash = logical_sha256(
        {
            item["domain_id"]: item["catalog_hashes_sha256"]
            for item in sorted(domain_receipts, key=lambda row: str(row["domain_id"]))
        }
    )
    status = (
        "PASS_FULL_GRID_T0"
        if wall_seconds <= T0_MAX_WALL_SECONDS and peak_rss <= T0_MAX_PEAK_RSS_BYTES
        else "CAPACITY_EXCEEDED"
    )
    payload = {
        "schema": "ovc-srfdi-wp10a-real-family-grid-capacity/v2",
        "measurement_class": "MEASURED_REAL_DATA_CAPACITY_ONLY",
        "status": status,
        "source_files": [item.to_dict() for item in source_receipts],
        "source_record_count": len(rows),
        "eligible_record_count": FROZEN_ELIGIBLE_COUNT,
        "eligible_record_ids_sha256": FROZEN_ELIGIBLE_IDS_SHA256,
        "population_id": FROZEN_POPULATION_ID,
        "comparability_domain_count": len(domain_receipts),
        "exact_pair_opportunity_count": pair_count,
        "family_configuration_count": config_count,
        "catalog_grid_hash": catalog_grid_hash,
        "domain_receipts": domain_receipts,
        "wall_seconds": round(wall_seconds, 9),
        "peak_rss_bytes": peak_rss,
        "new_external_artifact_bytes": 0,
        "t0": {
            "max_wall_seconds": T0_MAX_WALL_SECONDS,
            "max_peak_rss_bytes": T0_MAX_PEAK_RSS_BYTES,
            "max_external_bytes": T0_MAX_EXTERNAL_BYTES,
        },
        "backend_identities": [
            "AVERAGE_LINKAGE_EXACT_SUM_COUNT_HEAP_v1",
            "HIERARCHICAL_EXACT_TRACE_REUSE_v1",
            "MEDOID_STAR_EXACT_PREFIX_REUSE_v1",
            "BOUNDED_PAM_EXACT_SUPPORT_MATERIALIZATION_v1",
            "CATEGORICAL_GOWER_EXACT_PATTERN_COMPRESSION_v1",
            "NULL_CONTROL_ALL_RESIDUAL_ANALYTIC_v1",
        ],
        "sampling": "NONE_FULL_FROZEN_GRID",
        "method_or_configuration_drop": False,
        "provider_fetch": False,
        "validation_consumed": False,
        "scientific_effect": "NONE_CAPACITY_ONLY",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}