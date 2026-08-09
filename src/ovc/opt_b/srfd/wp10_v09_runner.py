from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .segmentation_prereg import validate_boundary_pack_registry
from .serialization import logical_sha256
from .stability_metrics_v04 import validate_metric_registry
from .wp10_execution_resilience import RunAuthorityStore
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
    compile_frozen_domains,
    verify_and_load_frozen_source,
    verify_durable_workspace,
)
from .wp10_v07_family import frozen_configuration_plan
from .wp10_v07_runner import _run_from_start, planned_work_units
from .wp10_v09_interface import (
    EXECUTION_BINDING_SHA256,
    PACKET_ID,
    PROGRAMME_ID,
    RunBindingV09,
    WP10V09InterfaceError,
    binding_from_manifest,
    interface_preflight,
    start_after_exact_preflight,
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def preflight_wp10_v09(
    *,
    binding: RunBindingV09,
    source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any],
    segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any],
    durable_root: Path,
) -> dict[str, Any]:
    workspace = verify_durable_workspace(durable_root)
    if logical_sha256(pack_registry) != FROZEN_REPRESENTATION_PACK_SHA256:
        raise WP10V09InterfaceError("V09_REPRESENTATION_PACK_HASH_MISMATCH", logical_sha256(pack_registry))
    if validate_boundary_pack_registry(segmentation_registry) != FROZEN_SEGMENTATION_PACK_SHA256:
        raise WP10V09InterfaceError("V09_SEGMENTATION_PACK_HASH_MISMATCH", "registry drift")
    if validate_metric_registry(stability_registry) != FROZEN_STABILITY_PACK_SHA256:
        raise WP10V09InterfaceError("V09_STABILITY_PACK_HASH_MISMATCH", "registry drift")
    rows, source_receipts = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    pair_count = sum(len(records) * (len(records) - 1) // 2 for records in domains.values())
    family_count = sum(len(frozen_configuration_plan(domain_id)) for domain_id in domains)
    plan = planned_work_units(tuple(domains))
    if len(rows) != 9420 or len(domains) != FROZEN_DOMAIN_COUNT or pair_count != FROZEN_PAIR_COUNT:
        raise WP10V09InterfaceError(
            "V09_FROZEN_POPULATION_DRIFT",
            f"rows={len(rows)} domains={len(domains)} pairs={pair_count}",
        )
    if family_count != FROZEN_FAMILY_CONFIGURATION_COUNT:
        raise WP10V09InterfaceError("V09_FROZEN_GRID_INCOMPLETE", str(family_count))
    receipt = {
        "schema": "ovc-srfdi-wp10-v09-full-preflight/v1",
        "status": "PASS",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "run_binding_sha256": binding.logical_hash,
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
        "frozen_science_status": "PASS",
        "source_binding_status": "PASS",
        "capacity_contract_status": "PASS",
        "execution_binding_status": "PASS",
        "execution_binding_sha256": EXECUTION_BINDING_SHA256,
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "token_consumed": False,
        "scientific_delta": "NONE",
    }
    return {**receipt, "logical_hash": logical_sha256(receipt)}


def start_wp10_v09(
    *,
    repo_root: Path,
    manifest: Mapping[str, Any],
    raw_token: Mapping[str, Any],
    authority_effect: Mapping[str, Any],
    execution_freeze: Mapping[str, Any],
    source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any],
    segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any],
    durable_root: Path,
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    def full_preflight(binding: RunBindingV09) -> Mapping[str, Any]:
        return preflight_wp10_v09(
            binding=binding,
            source_paths=source_paths,
            pack_registry=pack_registry,
            segmentation_registry=segmentation_registry,
            stability_registry=stability_registry,
            durable_root=durable_root,
        )

    authority_store = RunAuthorityStore(Path(durable_root))
    start, interface_receipt, full_receipt, binding = start_after_exact_preflight(
        store=authority_store,
        repo_root=repo_root,
        manifest=manifest,
        raw_token=raw_token,
        authority_effect=authority_effect,
        execution_freeze=execution_freeze,
        full_preflight=full_preflight,
    )
    rows, _ = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    engine_result = _run_from_start(
        start=start,
        binding=binding,
        rows=rows,
        domains=domains,
        preflight=full_receipt,
        durable_root=durable_root,
        stop_after_new_units=stop_after_new_units,
    )
    envelope = {
        "schema": "ovc-srfdi-wp10-v09-execution-envelope/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "run_id": start.run_id,
        "token_id": start.token_id,
        "run_binding_sha256": binding.logical_hash,
        "interface_preflight_logical_hash": interface_receipt["logical_hash"],
        "full_preflight_logical_hash": full_receipt["logical_hash"],
        "frozen_engine_packet_id": "SRFDI-WP10-v0.7",
        "frozen_engine_provenance": "PRESERVED_NOT_RELABELED",
        "engine_result": engine_result,
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_delta": "NONE",
    }
    return {**envelope, "logical_hash": logical_sha256(envelope)}


def resume_wp10_v09(
    *,
    manifest: Mapping[str, Any],
    source_paths: Mapping[str, str | Path],
    pack_registry: Mapping[str, Any],
    segmentation_registry: Mapping[str, Any],
    stability_registry: Mapping[str, Any],
    durable_root: Path,
    token_id: str,
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    binding = binding_from_manifest(manifest)
    full_receipt = preflight_wp10_v09(
        binding=binding,
        source_paths=source_paths,
        pack_registry=pack_registry,
        segmentation_registry=segmentation_registry,
        stability_registry=stability_registry,
        durable_root=durable_root,
    )
    authority_store = RunAuthorityStore(Path(durable_root))
    start = authority_store.load(token_id)
    if start.run_binding_sha256 != binding.logical_hash:
        raise WP10V09InterfaceError("V09_RESUME_BINDING_MISMATCH", start.run_binding_sha256)
    rows, _ = verify_and_load_frozen_source(source_paths)
    domains = compile_frozen_domains(rows, pack_registry)
    engine_result = _run_from_start(
        start=start,
        binding=binding,
        rows=rows,
        domains=domains,
        preflight=full_receipt,
        durable_root=durable_root,
        stop_after_new_units=stop_after_new_units,
    )
    envelope = {
        "schema": "ovc-srfdi-wp10-v09-execution-envelope/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "run_id": start.run_id,
        "token_id": start.token_id,
        "run_binding_sha256": binding.logical_hash,
        "full_preflight_logical_hash": full_receipt["logical_hash"],
        "frozen_engine_packet_id": "SRFDI-WP10-v0.7",
        "frozen_engine_provenance": "PRESERVED_NOT_RELABELED",
        "engine_result": engine_result,
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_delta": "NONE",
    }
    return {**envelope, "logical_hash": logical_sha256(envelope)}


def _cli() -> int:
    parser = argparse.ArgumentParser(description="OVC SRFDI WP10 v0.9 versioned execution-interface wrapper")
    parser.add_argument("mode", choices=("interface-preflight",))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", default="docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_9.json")
    parser.add_argument("--token", default="docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFD_JUNE_AUTHORITY_TOKEN_v0_9.json")
    parser.add_argument("--authority-effect", default="docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9/SRFD_JUNE_AUTHORITY_EFFECT_v0_9.json")
    parser.add_argument("--execution-freeze", default="registries/research/srfd/wp10b_segmentation_execution_binding_freeze_v0_1.json")
    args = parser.parse_args()
    receipt = interface_preflight(
        repo_root=Path(args.repo_root).resolve(),
        manifest=_load_json(Path(args.manifest)),
        raw_token=_load_json(Path(args.token)),
        authority_effect=_load_json(Path(args.authority_effect)),
        execution_freeze=_load_json(Path(args.execution_freeze)),
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
