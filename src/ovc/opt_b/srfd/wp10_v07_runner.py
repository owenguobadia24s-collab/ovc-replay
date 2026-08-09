from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .segmentation_prereg import (
    null_boundary_control_from_c2_ledger,
    run_change_from_c2_ledger,
    validate_boundary_pack_registry,
)
from .serialization import canonical_json_bytes, logical_sha256
from .source_adapter import adapt_c2_to_c2e_input
from .stability_metrics_v04 import validate_metric_registry
from .wp10_durable_execution import (
    RunArtifactStore,
    RunCapacityStore,
    execute_durable_resumable_units,
)
from .wp10_execution_resilience import RunAuthorityStore, RunBinding, RunCheckpointStore
from .wp10_v07_contract import (
    FROZEN_DOMAIN_COUNT,
    FROZEN_ELIGIBLE_COUNT,
    FROZEN_ELIGIBLE_IDS_SHA256,
    FROZEN_FAMILY_CONFIGURATION_COUNT,
    FROZEN_PAIR_COUNT,
    FROZEN_POPULATION_ID,
    FROZEN_REPRESENTATION_PACK_SHA256,
    FROZEN_SEGMENTATION_PACK_SHA256,
    FROZEN_STABILITY_PACK_SHA256,
    PACKET_ID,
    PROGRAMME_ID,
    T0_MAX_EXTERNAL_BYTES,
    T0_MAX_PEAK_RSS_BYTES,
    T0_MAX_WALL_SECONDS,
    EXPECTED_SEGMENTATION_COUNTS,
    ConfigurationDescriptor,
    WP10RunnerError,
    adapted_capacity_record,
    compile_frozen_domains,
    verify_and_load_frozen_source,
    verify_durable_workspace,
    verify_frozen_run_binding,
)
from .wp10_v07_family import (
    frozen_configuration_plan,
    gower_pattern_surface,
    materialize_prepared_configuration,
    prepare_domain,
)
from .wp10_v07_analysis import (
    analyse_domain,
    build_invariant_core_support_exact,
    method_disagreement_exact,
)

def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _segmentation_inputs(rows: Sequence[Mapping[str, Any]]) -> list[Any]:
    values = [
        adapt_c2_to_c2e_input(adapted_capacity_record(row))
        for row in rows
        if bool(row.get("target_eligible"))
    ]
    if len(values) != FROZEN_ELIGIBLE_COUNT:
        raise WP10RunnerError("POPULATION_BINDING_MISMATCH", f"segmentation={len(values)}")
    return values


def execute_segmentation(rows: Sequence[Mapping[str, Any]], method_id: str) -> dict[str, Any]:
    ledger = _segmentation_inputs(rows)
    if method_id == "RUN_CHANGE_SEGMENTATION":
        result = run_change_from_c2_ledger(ledger)
        counts = {
            "stream_count": int(result["stream_count"]),
            "segment_count": len(result["segments"]),
            "boundary_count": len(result["boundaries"]),
        }
    elif method_id == "NULL_BOUNDARY_CONTROL":
        result = null_boundary_control_from_c2_ledger(ledger)
        counts = {
            "stream_count": int(result["stream_count"]),
            "segment_count": len(result["segments"]),
            "boundary_count": len(result["boundaries"]),
        }
    else:
        raise WP10RunnerError("UNDECLARED_METHOD_OR_DEPENDENCY", method_id)
    if counts != EXPECTED_SEGMENTATION_COUNTS[method_id]:
        raise WP10RunnerError(
            "SEGMENTATION_BINDING_MISMATCH", f"{method_id}:{counts}"
        )
    payload = {
        "schema": "ovc-srfdi-wp10-v07-segmentation-output/v1",
        "method_id": method_id,
        "counts": counts,
        "result": result,
        "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
    }
    return {**payload, "logical_hash": logical_sha256(payload)}


def planned_work_units(domain_ids: Sequence[str]) -> tuple[str, ...]:
    units: list[str] = [
        "population",
        "segmentation/RUN_CHANGE_SEGMENTATION",
        "segmentation/NULL_BOUNDARY_CONTROL",
    ]
    for domain_id in sorted(str(value) for value in domain_ids):
        units.append(f"domain/{domain_id}/prepare")
        units.extend(
            f"domain/{domain_id}/configuration/{item.configuration_id}"
            for item in frozen_configuration_plan(domain_id)
        )
        units.append(f"domain/{domain_id}/analysis")
    units.append("packet")
    if len(units) != 1 + 2 + len(domain_ids) * 56 + 1:
        raise WP10RunnerError("QA_NON_REPRODUCIBLE", "work-unit plan count drift")
    return tuple(units)


def _commit_preflight(root: Path, binding: RunBinding, payload: Mapping[str, Any]) -> dict[str, Any]:
    directory = Path(root) / "preflight"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{binding.logical_hash}.json"
    data = canonical_json_bytes(payload) + b"\n"
    if path.exists():
        if path.read_bytes() != data:
            raise WP10RunnerError(
                "PREFLIGHT_HISTORY_REWRITE", "existing preflight differs for same RunBinding"
            )
    else:
        tmp = path.with_name(path.name + ".tmp")
        with tmp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    return {"preflight_sha256": sha256(data).hexdigest(), "path": path}


def preflight_wp10(
    *,
    binding: RunBinding,
    source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any],
    segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any],
    durable_root: Path,
) -> dict[str, Any]:
    verify_frozen_run_binding(binding)
    workspace = verify_durable_workspace(durable_root)
    if logical_sha256(pack_registry) != FROZEN_REPRESENTATION_PACK_SHA256:
        raise WP10RunnerError("REPRESENTATION_PACK_HASH_MISMATCH", logical_sha256(pack_registry))
    if validate_boundary_pack_registry(segmentation_registry) != FROZEN_SEGMENTATION_PACK_SHA256:
        raise WP10RunnerError("SEGMENTATION_PACK_HASH_MISMATCH", "registry drift")
    if validate_metric_registry(stability_registry) != FROZEN_STABILITY_PACK_SHA256:
        raise WP10RunnerError("STABILITY_PACK_HASH_MISMATCH", "registry drift")
    rows, source_receipts = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    plan = planned_work_units(tuple(domains))
    if sum(len(frozen_configuration_plan(domain_id)) for domain_id in domains) != FROZEN_FAMILY_CONFIGURATION_COUNT:
        raise WP10RunnerError("FROZEN_GRID_INCOMPLETE", "configuration total drift")
    payload = {
        "schema": "ovc-srfdi-wp10-v07-production-preflight/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "run_binding_sha256": binding.logical_hash,
        "workspace": workspace,
        "source_files": source_receipts,
        "source_record_count": len(rows),
        "eligible_record_count": FROZEN_ELIGIBLE_COUNT,
        "eligible_record_ids_sha256": FROZEN_ELIGIBLE_IDS_SHA256,
        "population_id": FROZEN_POPULATION_ID,
        "comparability_domain_count": len(domains),
        "exact_pair_opportunity_count": sum(
            len(records) * (len(records) - 1) // 2 for records in domains.values()
        ),
        "family_configuration_count": FROZEN_FAMILY_CONFIGURATION_COUNT,
        "work_unit_count": len(plan),
        "minimum_family_grid_restart_unit": "ONE_FAMILY_CONFIGURATION_WITHIN_ONE_COMPARABILITY_DOMAIN",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_promotion": "NONE",
        "token_consumed": False,
    }
    payload = {**payload, "logical_hash": logical_sha256(payload)}
    receipt = _commit_preflight(durable_root, binding, payload)
    return {**payload, "preflight_file_sha256": receipt["preflight_sha256"]}


def _descriptor_by_config(domain_id: str) -> dict[str, ConfigurationDescriptor]:
    return {item.configuration_id: item for item in frozen_configuration_plan(domain_id)}


def _run_from_start(
    *,
    start: Any,
    binding: RunBinding,
    rows: Sequence[Mapping[str, Any]],
    domains: Mapping[str, Sequence[Mapping[str, Any]]],
    preflight: Mapping[str, Any],
    durable_root: Path,
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    checkpoints = RunCheckpointStore(Path(durable_root))
    artifacts = RunArtifactStore(Path(durable_root), max_external_bytes=T0_MAX_EXTERNAL_BYTES)
    capacity = RunCapacityStore(
        Path(durable_root),
        max_committed_active_wall_seconds=T0_MAX_WALL_SECONDS,
        max_peak_rss_bytes=T0_MAX_PEAK_RSS_BYTES,
    )
    unit_ids = planned_work_units(tuple(domains))

    def load(unit_id: str) -> dict[str, Any]:
        return artifacts.load_output(start, binding, unit_id)

    def worker(unit_id: str) -> Mapping[str, Any]:
        if unit_id == "population":
            keys = (
                "source_record_count", "eligible_record_count", "eligible_record_ids_sha256",
                "population_id", "comparability_domain_count", "exact_pair_opportunity_count",
                "family_configuration_count", "work_unit_count",
            )
            body = {key: preflight[key] for key in keys}
            body.update(
                {
                    "schema": "ovc-srfdi-wp10-v07-population-unit/v1",
                    "provider_fetch": "DENIED",
                    "validation_2025": "LOCKED_UNCONSUMED",
                }
            )
            return {**body, "logical_hash": logical_sha256(body)}
        if unit_id.startswith("segmentation/"):
            return execute_segmentation(rows, unit_id.split("/", 1)[1])
        if unit_id == "packet":
            checkpoint = checkpoints.latest(start, binding)
            manifest = [item.to_dict() for item in checkpoint.unit_receipts]
            analyses = [
                load(f"domain/{domain_id}/analysis") for domain_id in sorted(domains)
            ]
            segmentation = {
                method: load(f"segmentation/{method}")["counts"]
                for method in ("RUN_CHANGE_SEGMENTATION", "NULL_BOUNDARY_CONTROL")
            }
            body = {
                "schema": "ovc-srfdi-wp10-v07-production-evidence-packet/v1",
                "programme_id": PROGRAMME_ID,
                "packet_id": PACKET_ID,
                "run_id": start.run_id,
                "run_binding_sha256": binding.logical_hash,
                "population_id": FROZEN_POPULATION_ID,
                "eligible_record_count": FROZEN_ELIGIBLE_COUNT,
                "comparability_domain_count": FROZEN_DOMAIN_COUNT,
                "exact_pair_opportunity_count": FROZEN_PAIR_COUNT,
                "family_configuration_count": FROZEN_FAMILY_CONFIGURATION_COUNT,
                "segmentation_counts": segmentation,
                "visible_nonexecuted_segmentation": {
                    "C2E_CAUSAL_ADAPTER": "NOT_EXECUTED_DEPENDENCY_UNAVAILABLE",
                    "DIRECTIONAL_CHANGE": "NOT_EXECUTED_DEPENDENCY_UNAVAILABLE",
                    "PELT_REFERENCE": "NOT_EXECUTED_CAPACITY_UNRESOLVED_AT_T0",
                },
                "domain_analysis_hashes": {
                    str(item["domain_id"]): str(item["logical_hash"])
                    for item in analyses
                },
                "completed_work_unit_manifest_before_packet": manifest,
                "provider_fetch": "DENIED",
                "validation_2025": "LOCKED_UNCONSUMED",
                "scientific_disposition": "NOT_PERFORMED_PENDING_SRFDI_G10",
                "selector_family_semantic_publication": "NONE",
                "probability_risk_exposure_execution": "NONE",
            }
            return {**body, "logical_hash": logical_sha256(body)}

        parts = unit_id.split("/")
        if len(parts) < 3 or parts[0] != "domain":
            raise WP10RunnerError("QA_NON_REPRODUCIBLE", f"unknown unit:{unit_id}")
        domain_id = parts[1]
        records = domains[domain_id]
        prepare_unit = f"domain/{domain_id}/prepare"
        if parts[2] == "prepare":
            return prepare_domain(records, domain_id)
        preparation = load(prepare_unit)
        if parts[2] == "configuration" and len(parts) == 4:
            descriptor = _descriptor_by_config(domain_id).get(parts[3])
            if descriptor is None:
                raise WP10RunnerError("FROZEN_GRID_INCOMPLETE", parts[3])
            return materialize_prepared_configuration(records, preparation, descriptor)
        if parts[2] == "analysis":
            catalogs = {
                descriptor.configuration_id: load(
                    f"domain/{domain_id}/configuration/{descriptor.configuration_id}"
                )["catalog"]
                for descriptor in frozen_configuration_plan(domain_id)
            }
            return analyse_domain(records, preparation, catalogs)
        raise WP10RunnerError("QA_NON_REPRODUCIBLE", f"unknown unit:{unit_id}")

    return execute_durable_resumable_units(
        start=start,
        binding=binding,
        checkpoint_store=checkpoints,
        artifact_store=artifacts,
        capacity_store=capacity,
        unit_ids=unit_ids,
        worker=worker,
        stop_after_new_units=stop_after_new_units,
    )


def start_wp10(
    *,
    token: Mapping[str, Any],
    binding: RunBinding,
    source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any],
    segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any],
    durable_root: Path,
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    preflight = preflight_wp10(
        binding=binding,
        source_paths=source_paths,
        pack_registry=pack_registry,
        segmentation_registry=segmentation_registry,
        stability_registry=stability_registry,
        durable_root=durable_root,
    )
    rows, _ = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    authority = RunAuthorityStore(Path(durable_root))
    start = authority.consume(token, binding)
    return _run_from_start(
        start=start,
        binding=binding,
        rows=rows,
        domains=domains,
        preflight=preflight,
        durable_root=durable_root,
        stop_after_new_units=stop_after_new_units,
    )


def resume_wp10(
    *,
    token_id: str,
    binding: RunBinding,
    source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any],
    segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any],
    durable_root: Path,
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    preflight = preflight_wp10(
        binding=binding,
        source_paths=source_paths,
        pack_registry=pack_registry,
        segmentation_registry=segmentation_registry,
        stability_registry=stability_registry,
        durable_root=durable_root,
    )
    rows, _ = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    authority = RunAuthorityStore(Path(durable_root))
    start = authority.load(token_id)
    if start.run_binding_sha256 != binding.logical_hash:
        raise WP10RunnerError("RESUME_BINDING_MISMATCH", "run start binding differs")
    return _run_from_start(
        start=start,
        binding=binding,
        rows=rows,
        domains=domains,
        preflight=preflight,
        durable_root=durable_root,
        stop_after_new_units=stop_after_new_units,
    )


def _binding_from_json(value: Mapping[str, Any]) -> RunBinding:
    return RunBinding(**{key: value[key] for key in RunBinding.__dataclass_fields__})


def _cli() -> int:
    parser = argparse.ArgumentParser(description="OVC SRFDI WP10 v0.7 production resumable runner")
    parser.add_argument("mode", choices=("preflight", "start", "resume"))
    parser.add_argument("--durable-root", required=True)
    parser.add_argument("--binding-json", required=True)
    parser.add_argument("--source-map-json", required=True)
    parser.add_argument("--pack-registry", default="registries/research/srfd/real_source_representation_packs_v0_2.json")
    parser.add_argument("--segmentation-registry", default="registries/research/srfd/segmentation_boundary_packs_v0_3.json")
    parser.add_argument("--stability-registry", default="registries/research/srfd/stability_metric_specs_v0_4.json")
    parser.add_argument("--token-json")
    parser.add_argument("--token-id")
    args = parser.parse_args()

    binding = _binding_from_json(_load_json(Path(args.binding_json)))
    source_paths = _load_json(Path(args.source_map_json))
    pack_registry = _load_json(Path(args.pack_registry))
    segmentation_registry = _load_json(Path(args.segmentation_registry))
    stability_registry = _load_json(Path(args.stability_registry))
    common = {
        "binding": binding,
        "source_paths": source_paths,
        "pack_registry": pack_registry,
        "segmentation_registry": segmentation_registry,
        "stability_registry": stability_registry,
        "durable_root": Path(args.durable_root),
    }
    if args.mode == "preflight":
        result = preflight_wp10(**common)
    elif args.mode == "start":
        if not args.token_json:
            parser.error("--token-json is required for start")
        result = start_wp10(token=_load_json(Path(args.token_json)), **common)
    else:
        if not args.token_id:
            parser.error("--token-id is required for resume")
        result = resume_wp10(token_id=args.token_id, **common)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
