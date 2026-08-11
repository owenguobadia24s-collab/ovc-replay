from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

from .segmentation_prereg import validate_boundary_pack_registry
from .serialization import logical_sha256
from .stability_metrics_v04 import validate_metric_registry
from .wp10_durable_execution import RunCapacityStore
from .wp10_execution_resilience import RunAuthorityStore, RunStartReceipt
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
    T0_MAX_WALL_SECONDS,
    compile_frozen_domains,
    verify_and_load_frozen_source,
    verify_durable_workspace,
)
from .wp10_v07_family import frozen_configuration_plan, materialize_prepared_configuration, prepare_domain
from .wp10_v07_runner import _descriptor_by_config, execute_segmentation, planned_work_units
from .wp10_v10_interface import T1_EXTERNAL_ARTIFACT_LIMIT_BYTES
from .wp10_v11_environment import (
    capture_execution_environment,
    load_frozen_profile,
    verify_frozen_execution_environment,
)
from .wp10_v11_execution import ContentAddressedArtifactStoreV11, execute_durable_resumable_units_v11
from .wp10_v11_hardening import CachedRunCheckpointStoreV11
from .wp10_v11_interface import (
    FROZEN_ENVIRONMENT_PROFILE_SHA256,
    HARDENING_REHEARSAL_SHA256,
    PACKET_ID,
    PROGRAMME_ID,
    RunBindingV11,
    verify_science_unchanged,
)
from .wp10_v11_streaming_analysis import stream_analyse_domain_to_file


PROFILE_REPOSITORY_PATH = Path(
    "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1-hardening/SRFDI_EXECUTION_ENVIRONMENT_PROFILE_v2.json"
)
HARD_MEMORY_CEILING_BYTES = 4 * 1024**3


def _pip_freeze() -> bytes:
    return subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--all"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def preflight_wp10_v11(
    *,
    binding: RunBindingV11,
    source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any],
    segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any],
    durable_root: Path,
    repository_root: Path,
) -> dict[str, Any]:
    verify_science_unchanged(binding)
    if binding.execution_environment_profile_sha256 != FROZEN_ENVIRONMENT_PROFILE_SHA256:
        raise ValueError("V11_ENVIRONMENT_PROFILE_BINDING_MISMATCH")
    if binding.hardening_rehearsal_sha256 != HARDENING_REHEARSAL_SHA256:
        raise ValueError("V11_HARDENING_REHEARSAL_BINDING_MISMATCH")
    workspace = verify_durable_workspace(durable_root)
    profile_path = Path(repository_root) / PROFILE_REPOSITORY_PATH
    frozen_profile = load_frozen_profile(profile_path)
    observed_profile = capture_execution_environment(
        profile_id=str(frozen_profile["profile_id"]),
        working_root=durable_root,
        captured_at="RUNTIME_PRE_SCIENCE_NON_IDENTITY",
        pip_freeze_bytes=_pip_freeze(),
        required_min_free_bytes_before_run=int(
            frozen_profile["execution_constraints"]["required_min_free_bytes_before_run"]
        ),
        t1_external_artifact_limit_bytes=T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,
        minimum_temp_reserve_bytes=int(
            frozen_profile["execution_constraints"]["minimum_temp_reserve_bytes"]
        ),
    )
    environment = verify_frozen_execution_environment(observed_profile, frozen_profile)
    if int(frozen_profile["execution_constraints"]["hard_memory_ceiling_bytes"]) != HARD_MEMORY_CEILING_BYTES:
        raise ValueError("V11_HARD_MEMORY_CEILING_DRIFT")
    if logical_sha256(pack_registry) != FROZEN_REPRESENTATION_PACK_SHA256:
        raise ValueError("V11_REPRESENTATION_PACK_HASH_MISMATCH")
    if validate_boundary_pack_registry(segmentation_registry) != FROZEN_SEGMENTATION_PACK_SHA256:
        raise ValueError("V11_SEGMENTATION_PACK_HASH_MISMATCH")
    if validate_metric_registry(stability_registry) != FROZEN_STABILITY_PACK_SHA256:
        raise ValueError("V11_STABILITY_PACK_HASH_MISMATCH")
    rows, source_receipts = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    plan = planned_work_units(tuple(domains))
    pair_count = sum(len(records) * (len(records) - 1) // 2 for records in domains.values())
    family_count = sum(len(frozen_configuration_plan(domain_id)) for domain_id in domains)
    if (
        len(rows) != 9420
        or len(domains) != FROZEN_DOMAIN_COUNT
        or pair_count != FROZEN_PAIR_COUNT
        or family_count != FROZEN_FAMILY_CONFIGURATION_COUNT
        or len(plan) != 2020
    ):
        raise ValueError("V11_FROZEN_POPULATION_DRIFT")
    body = {
        "schema": "ovc-srfdi-wp10-v11-full-preflight/v1",
        "status": "PASS",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "run_binding_sha256": binding.logical_hash,
        "science_identity_sha256": binding.science_identity_sha256,
        "population_id": FROZEN_POPULATION_ID,
        "source_record_count": len(rows),
        "eligible_record_count": FROZEN_ELIGIBLE_COUNT,
        "eligible_record_ids_sha256": FROZEN_ELIGIBLE_IDS_SHA256,
        "comparability_domain_count": len(domains),
        "exact_pair_opportunity_count": pair_count,
        "family_configuration_count": family_count,
        "work_unit_count": len(plan),
        "source_files": source_receipts,
        "workspace": workspace,
        "environment": environment,
        "capacity_tier": "T1_EXTERNAL_ARTIFACT",
        "max_external_bytes": T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,
        "max_process_rss_bytes": HARD_MEMORY_CEILING_BYTES,
        "storage_layout": "CONTENT_ADDRESSED_CHUNKED_COMPRESSED_FILE_BACKED_ANALYSIS",
        "checkpoint_store": "CachedRunCheckpointStoreV11_WIRE_IDENTICAL_RUN_CHECKPOINT_STORE",
        "strict_work_unit_output_contracts": "ENFORCED_BEFORE_COMMIT",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_delta": "NONE",
    }
    return {**body, "logical_hash": logical_sha256(body)}


def _run_from_start_v11(
    *,
    start: RunStartReceipt,
    binding: RunBindingV11,
    rows: Sequence[Mapping[str, Any]],
    domains: Mapping[str, Sequence[Mapping[str, Any]]],
    preflight: Mapping[str, Any],
    durable_root: Path,
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    root = Path(durable_root)
    checkpoints = CachedRunCheckpointStoreV11(root)
    artifacts = ContentAddressedArtifactStoreV11(
        root, max_external_bytes=T1_EXTERNAL_ARTIFACT_LIMIT_BYTES
    )
    capacity = RunCapacityStore(
        root,
        max_committed_active_wall_seconds=T0_MAX_WALL_SECONDS,
        max_peak_rss_bytes=HARD_MEMORY_CEILING_BYTES,
    )
    unit_ids = planned_work_units(tuple(domains))
    staging = root / "runs" / start.run_id / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    def load(unit_id: str) -> dict[str, Any]:
        return artifacts.load_output(start, binding, unit_id)

    def worker(unit_id: str):
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
            analysis_hashes = {
                item.unit_id.split("/")[1]: item.output_logical_hash
                for item in checkpoint.unit_receipts
                if item.unit_id.startswith("domain/") and item.unit_id.endswith("/analysis")
            }
            expected_domains = set(domains)
            if set(analysis_hashes) != expected_domains:
                raise ValueError("V11_PACKET_ANALYSIS_MANIFEST_INCOMPLETE")
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
                "domain_analysis_hashes": analysis_hashes,
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
            raise ValueError(f"V11_UNKNOWN_UNIT:{unit_id}")
        domain_id = parts[1]
        records = domains[domain_id]
        preparation_unit = f"domain/{domain_id}/prepare"
        if parts[2] == "prepare":
            return prepare_domain(records, domain_id)
        preparation = load(preparation_unit)
        if parts[2] == "configuration" and len(parts) == 4:
            descriptor = _descriptor_by_config(domain_id).get(parts[3])
            if descriptor is None:
                raise ValueError(f"V11_UNKNOWN_CONFIGURATION:{parts[3]}")
            return materialize_prepared_configuration(records, preparation, descriptor)
        if parts[2] == "analysis":
            catalogs = {
                descriptor.configuration_id: load(
                    f"domain/{domain_id}/configuration/{descriptor.configuration_id}"
                )["catalog"]
                for descriptor in frozen_configuration_plan(domain_id)
            }
            return stream_analyse_domain_to_file(
                records,
                preparation,
                catalogs,
                staging / f"{domain_id}.analysis.json",
            )
        raise ValueError(f"V11_UNKNOWN_UNIT:{unit_id}")

    result = execute_durable_resumable_units_v11(
        start=start,
        binding=binding,
        checkpoint_store=checkpoints,
        artifact_store=artifacts,
        capacity_store=capacity,
        unit_ids=unit_ids,
        worker=worker,
        stop_after_new_units=stop_after_new_units,
    )
    return {
        **result,
        "capacity_tier": "T1_EXTERNAL_ARTIFACT",
        "max_external_bytes": T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,
        "max_process_rss_bytes": HARD_MEMORY_CEILING_BYTES,
        "reuse_seed_receipt": None,
        "reuse_disposition": "RECOMPUTE_FROM_FROZEN_PARENTS_NO_UNVERIFIED_HISTORICAL_REUSE",
        "scientific_delta": "NONE",
    }


def start_wp10_v11(
    *,
    binding: RunBindingV11,
    token: Mapping[str, Any],
    source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any],
    segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any],
    durable_root: Path,
    repository_root: Path,
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    preflight = preflight_wp10_v11(
        binding=binding,
        source_paths=source_paths,
        pack_registry=pack_registry,
        segmentation_registry=segmentation_registry,
        stability_registry=stability_registry,
        durable_root=durable_root,
        repository_root=repository_root,
    )
    rows, _ = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    authority = RunAuthorityStore(Path(durable_root))
    start = authority.consume(token, binding)
    return _run_from_start_v11(
        start=start,
        binding=binding,
        rows=rows,
        domains=domains,
        preflight=preflight,
        durable_root=durable_root,
        stop_after_new_units=stop_after_new_units,
    )
