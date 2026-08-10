from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .segmentation_prereg import validate_boundary_pack_registry
from .serialization import logical_sha256
from .stability_metrics_v04 import validate_metric_registry
from .wp10_durable_execution import RunCapacityStore, execute_durable_resumable_units
from .wp10_execution_resilience import RunAuthorityStore, RunCheckpointStore, RunStartReceipt, WorkUnitReceipt
from .wp10_v07_contract import (
    FROZEN_DOMAIN_COUNT, FROZEN_ELIGIBLE_COUNT, FROZEN_ELIGIBLE_IDS_SHA256,
    FROZEN_FAMILY_CONFIGURATION_COUNT, FROZEN_PAIR_COUNT, FROZEN_POPULATION_ID,
    FROZEN_REPRESENTATION_PACK_SHA256, FROZEN_SEGMENTATION_PACK_SHA256,
    FROZEN_STABILITY_PACK_SHA256, T0_MAX_PEAK_RSS_BYTES, T0_MAX_WALL_SECONDS,
    compile_frozen_domains, verify_and_load_frozen_source, verify_durable_workspace,
)
from .wp10_v07_family import frozen_configuration_plan, materialize_prepared_configuration, prepare_domain
from .wp10_v07_analysis import analyse_domain
from .wp10_v07_runner import execute_segmentation, planned_work_units, _descriptor_by_config
from .wp10_v10_interface import (
    PACKET_ID, PROGRAMME_ID, SCIENCE_IDENTITY_SHA256, T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,
    V09_RUN_BINDING_SHA256, V09_RUN_ID, V09_TOKEN_ID, RunBindingV10, verify_science_unchanged,
)
from .wp10_v10_storage import ContentAddressedArtifactStoreV10, ReuseSource


def preflight_wp10_v10(
    *, binding: RunBindingV10, source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any], segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any], durable_root: Path,
) -> dict[str, Any]:
    verify_science_unchanged(binding)
    workspace = verify_durable_workspace(durable_root)
    if logical_sha256(pack_registry) != FROZEN_REPRESENTATION_PACK_SHA256:
        raise ValueError("V10_REPRESENTATION_PACK_HASH_MISMATCH")
    if validate_boundary_pack_registry(segmentation_registry) != FROZEN_SEGMENTATION_PACK_SHA256:
        raise ValueError("V10_SEGMENTATION_PACK_HASH_MISMATCH")
    if validate_metric_registry(stability_registry) != FROZEN_STABILITY_PACK_SHA256:
        raise ValueError("V10_STABILITY_PACK_HASH_MISMATCH")
    rows, source_receipts = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    plan = planned_work_units(tuple(domains))
    pair_count = sum(len(records) * (len(records) - 1) // 2 for records in domains.values())
    family_count = sum(len(frozen_configuration_plan(domain_id)) for domain_id in domains)
    if len(rows) != 9420 or len(domains) != FROZEN_DOMAIN_COUNT or pair_count != FROZEN_PAIR_COUNT or family_count != FROZEN_FAMILY_CONFIGURATION_COUNT:
        raise ValueError("V10_FROZEN_POPULATION_DRIFT")
    body = {
        "schema": "ovc-srfdi-wp10-v10-full-preflight/v1", "status": "PASS",
        "programme_id": PROGRAMME_ID, "packet_id": PACKET_ID, "run_binding_sha256": binding.logical_hash,
        "science_identity_sha256": SCIENCE_IDENTITY_SHA256, "population_id": FROZEN_POPULATION_ID,
        "source_record_count": len(rows), "eligible_record_count": FROZEN_ELIGIBLE_COUNT,
        "eligible_record_ids_sha256": FROZEN_ELIGIBLE_IDS_SHA256, "comparability_domain_count": len(domains),
        "exact_pair_opportunity_count": pair_count, "family_configuration_count": family_count,
        "work_unit_count": len(plan), "source_files": source_receipts, "workspace": workspace,
        "capacity_tier": "T1_EXTERNAL_ARTIFACT", "max_external_bytes": T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,
        "storage_layout": "CONTENT_ADDRESSED_CHUNKED_COMPRESSED", "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED", "scientific_delta": "NONE",
    }
    return {**body, "logical_hash": logical_sha256(body)}


def _seed_verified_v09_prefix(
    *, new_start: RunStartReceipt, binding: RunBindingV10, v09_root: Path,
    checkpoint_store: RunCheckpointStore, artifact_store: ContentAddressedArtifactStoreV10,
    ordered_units: Sequence[str], max_units: int = 1626,
) -> dict[str, Any]:
    """Import only a contiguous, hash-verified v0.9 prefix as new-run dependencies.

    This function reads the historical checkpoint ledger, verifies its exact identity and every
    old artifact hash, re-materialises unchanged outputs in the v1.0 CAS, then writes a NEW v1.0
    checkpoint. It never copies or relabels an old checkpoint.
    """
    old_authority = RunAuthorityStore(Path(v09_root))
    old_start = old_authority.load(V09_TOKEN_ID)
    if old_start.run_id != V09_RUN_ID or old_start.run_binding_sha256 != V09_RUN_BINDING_SHA256:
        raise ValueError("V10_REUSE_V09_RUN_IDENTITY_MISMATCH")

    class OldBinding:
        logical_hash = V09_RUN_BINDING_SHA256
    old_checkpoints = RunCheckpointStore(Path(v09_root))
    old_latest = old_checkpoints.latest(old_start, OldBinding())
    if old_latest is None:
        raise ValueError("V10_REUSE_V09_CHECKPOINT_MISSING")
    if old_latest.sequence < 1 or len(old_latest.unit_receipts) < 1:
        raise ValueError("V10_REUSE_V09_CHECKPOINT_EMPTY")
    prefix = min(int(max_units), len(old_latest.unit_receipts), len(ordered_units))
    if list(old_latest.completed_units[:prefix]) != list(ordered_units[:prefix]):
        raise ValueError("V10_REUSE_V09_PREFIX_ORDER_MISMATCH")
    source = ReuseSource(
        run_id=old_start.run_id, token_id=old_start.token_id,
        run_binding_sha256=old_start.run_binding_sha256,
        checkpoint_id=old_latest.checkpoint_id, checkpoint_sequence=old_latest.sequence,
    )
    imported: list[WorkUnitReceipt] = []
    for old_receipt in old_latest.unit_receipts[:prefix]:
        imported.append(artifact_store.import_v09_output(
            start=new_start, binding=binding, v09_root=Path(v09_reuse_root), source=source,
            source_receipt=old_receipt, expected_v09_binding_sha256=V09_RUN_BINDING_SHA256,
        ))
    new_checkpoint = checkpoint_store.commit(new_start, binding, imported)
    return {
        "schema": "ovc-srfdi-wp10-v10-reuse-seed-receipt/v1", "status": "PASS",
        "source_run_id": old_start.run_id, "source_checkpoint_id": old_latest.checkpoint_id,
        "source_checkpoint_sequence": old_latest.sequence, "source_completed_unit_count": len(old_latest.unit_receipts),
        "verified_reused_prefix_count": len(imported), "new_run_id": new_start.run_id,
        "new_checkpoint_id": new_checkpoint.checkpoint_id, "new_checkpoint_sequence": new_checkpoint.sequence,
        "old_checkpoint_relabelled": False, "verification": "EXACT_SOURCE_ARTIFACT_SHA256_PLUS_OUTPUT_LOGICAL_HASH",
    }


def _run_from_start_v10(
    *, start: RunStartReceipt, binding: RunBindingV10, rows: Sequence[Mapping[str, Any]],
    domains: Mapping[str, Sequence[Mapping[str, Any]]], preflight: Mapping[str, Any], durable_root: Path,
    v09_reuse_root: Path | None = None, stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    checkpoints = RunCheckpointStore(Path(durable_root))
    artifacts = ContentAddressedArtifactStoreV10(Path(durable_root), max_external_bytes=T1_EXTERNAL_ARTIFACT_LIMIT_BYTES)
    capacity = RunCapacityStore(Path(durable_root), max_committed_active_wall_seconds=T0_MAX_WALL_SECONDS, max_peak_rss_bytes=T0_MAX_PEAK_RSS_BYTES)
    unit_ids = planned_work_units(tuple(domains))
    reuse_receipt = None
    if checkpoints.latest(start, binding, allow_missing=True) is None and v09_reuse_root is not None:
        reuse_receipt = _seed_verified_v09_prefix(
            new_start=start, binding=binding, v09_root=Path(v09_reuse_root), checkpoint_store=checkpoints,
            artifact_store=artifacts, ordered_units=unit_ids, max_units=1626,
        )

    def load(unit_id: str) -> dict[str, Any]:
        return artifacts.load_output(start, binding, unit_id)

    def worker(unit_id: str) -> Mapping[str, Any]:
        if unit_id == "population":
            keys = ("source_record_count", "eligible_record_count", "eligible_record_ids_sha256", "population_id", "comparability_domain_count", "exact_pair_opportunity_count", "family_configuration_count", "work_unit_count")
            body = {key: preflight[key] for key in keys}
            body.update({"schema":"ovc-srfdi-wp10-v07-population-unit/v1","provider_fetch":"DENIED","validation_2025":"LOCKED_UNCONSUMED"})
            return {**body, "logical_hash": logical_sha256(body)}
        if unit_id.startswith("segmentation/"):
            return execute_segmentation(rows, unit_id.split("/", 1)[1])
        if unit_id == "packet":
            checkpoint = checkpoints.latest(start, binding)
            manifest = [item.to_dict() for item in checkpoint.unit_receipts]
            analyses = [load(f"domain/{domain_id}/analysis") for domain_id in sorted(domains)]
            segmentation = {method:load(f"segmentation/{method}")["counts"] for method in ("RUN_CHANGE_SEGMENTATION","NULL_BOUNDARY_CONTROL")}
            body = {
                "schema":"ovc-srfdi-wp10-v07-production-evidence-packet/v1","programme_id":PROGRAMME_ID,"packet_id":PACKET_ID,
                "run_id":start.run_id,"run_binding_sha256":binding.logical_hash,"population_id":FROZEN_POPULATION_ID,
                "eligible_record_count":FROZEN_ELIGIBLE_COUNT,"comparability_domain_count":FROZEN_DOMAIN_COUNT,
                "exact_pair_opportunity_count":FROZEN_PAIR_COUNT,"family_configuration_count":FROZEN_FAMILY_CONFIGURATION_COUNT,
                "segmentation_counts":segmentation,"visible_nonexecuted_segmentation":{"C2E_CAUSAL_ADAPTER":"NOT_EXECUTED_DEPENDENCY_UNAVAILABLE","DIRECTIONAL_CHANGE":"NOT_EXECUTED_DEPENDENCY_UNAVAILABLE","PELT_REFERENCE":"NOT_EXECUTED_CAPACITY_UNRESOLVED_AT_T0"},
                "domain_analysis_hashes":{str(item["domain_id"]):str(item["logical_hash"]) for item in analyses},
                "completed_work_unit_manifest_before_packet":manifest,"provider_fetch":"DENIED","validation_2025":"LOCKED_UNCONSUMED",
                "scientific_disposition":"NOT_PERFORMED_PENDING_SRFDI_G10","selector_family_semantic_publication":"NONE","probability_risk_exposure_execution":"NONE",
            }
            return {**body,"logical_hash":logical_sha256(body)}
        parts=unit_id.split("/")
        if len(parts)<3 or parts[0]!="domain": raise ValueError(f"V10_UNKNOWN_UNIT:{unit_id}")
        domain_id=parts[1]; records=domains[domain_id]; preparation_unit=f"domain/{domain_id}/prepare"
        if parts[2]=="prepare": return prepare_domain(records,domain_id)
        preparation=load(preparation_unit)
        if parts[2]=="configuration" and len(parts)==4:
            descriptor=_descriptor_by_config(domain_id).get(parts[3])
            if descriptor is None: raise ValueError(f"V10_UNKNOWN_CONFIGURATION:{parts[3]}")
            return materialize_prepared_configuration(records,preparation,descriptor)
        if parts[2]=="analysis":
            catalogs={descriptor.configuration_id:load(f"domain/{domain_id}/configuration/{descriptor.configuration_id}")["catalog"] for descriptor in frozen_configuration_plan(domain_id)}
            return analyse_domain(records,preparation,catalogs)
        raise ValueError(f"V10_UNKNOWN_UNIT:{unit_id}")

    result=execute_durable_resumable_units(start=start,binding=binding,checkpoint_store=checkpoints,artifact_store=artifacts,capacity_store=capacity,unit_ids=unit_ids,worker=worker,stop_after_new_units=stop_after_new_units)
    return {**result,"capacity_tier":"T1_EXTERNAL_ARTIFACT","max_external_bytes":T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,"reuse_seed_receipt":reuse_receipt}


def start_wp10_v10(
    *, binding: RunBindingV10, token: Mapping[str, Any], source_paths: Mapping[str,str|Path],
    pack_registry: Mapping[str,Any], segmentation_registry: Mapping[str,Any], stability_registry: Mapping[str,Any],
    durable_root: Path, v09_reuse_root: Path|None=None, stop_after_new_units: int|None=None,
) -> dict[str,Any]:
    preflight=preflight_wp10_v10(binding=binding,source_paths=source_paths,pack_registry=pack_registry,segmentation_registry=segmentation_registry,stability_registry=stability_registry,durable_root=durable_root)
    rows,_=verify_and_load_frozen_source(source_paths); domains=compile_frozen_domains(rows,pack_registry)
    authority=RunAuthorityStore(Path(durable_root)); start=authority.consume(token,binding)
    return _run_from_start_v10(start=start,binding=binding,rows=rows,domains=domains,preflight=preflight,durable_root=durable_root,v09_reuse_root=v09_reuse_root,stop_after_new_units=stop_after_new_units)
