from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from .serialization import logical_sha256, stable_id
from .wp10_durable_execution import RunCapacityStore, execute_durable_resumable_units
from .wp10_execution_resilience import (
    ExecutionResilienceError, RunAuthorityStore, RunBinding, RunCheckpointStore
)
from .wp10_v10_storage import ContentAddressedArtifactStoreV10


PROGRAMME_ID = "OVC-SRFD-BENCHMARK-v0.1"
PACKET_ID = "SRFDI-WP10-v1.1-HARDENING"
SYNTHETIC_DOMAIN_COUNT = 36
SYNTHETIC_CONFIGURATIONS_PER_DOMAIN = 54
SYNTHETIC_WORK_UNIT_COUNT = 2020
SYNTHETIC_TOKEN_ID = "SRFD.HARDENING.SYNTHETIC.AUTH.v1"
SYNTHETIC_EXTERNAL_LIMIT_BYTES = 2 * 1024**3


class CachedRunCheckpointStoreV11(RunCheckpointStore):
    """Cache only the latest validated checkpoint inside one process.

    A fresh process still performs the parent store's complete contiguous-chain
    validation once. Checkpoint payloads, identities and files remain exactly the
    parent RunCheckpointStore format; only repeated O(n) rescans during one
    uninterrupted process are avoided.
    """

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self._latest_cache: dict[tuple[str, str], Any] = {}
        self._latest_seen: set[tuple[str, str]] = set()

    def _cache_key(self, start, binding) -> tuple[str, str]:
        return (start.run_id, binding.logical_hash)

    def latest(self, start, binding, *, allow_missing: bool = False):
        key = self._cache_key(start, binding)
        if key in self._latest_seen:
            receipt = self._latest_cache.get(key)
            if receipt is None and not allow_missing:
                raise ExecutionResilienceError("CHECKPOINT_MISSING", "no committed checkpoint exists")
            return receipt
        receipt = super().latest(start, binding, allow_missing=allow_missing)
        self._latest_seen.add(key)
        self._latest_cache[key] = receipt
        return receipt

    def commit(self, start, binding, completed):
        receipt = super().commit(start, binding, completed)
        key = self._cache_key(start, binding)
        self._latest_seen.add(key)
        self._latest_cache[key] = receipt
        return receipt


class WorkUnitContractError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class WorkUnitContract:
    kind: str
    schema: str
    required_fields: tuple[str, ...]


CONTRACTS = {
    "POPULATION": WorkUnitContract(
        "POPULATION",
        "ovc-srfdi-wp10-v07-population-unit/v1",
        (
            "source_record_count", "eligible_record_count", "population_id",
            "comparability_domain_count", "exact_pair_opportunity_count",
            "family_configuration_count", "work_unit_count",
        ),
    ),
    "SEGMENTATION": WorkUnitContract(
        "SEGMENTATION",
        "ovc-srfdi-wp10-v07-segmentation-output/v1",
        ("method_id", "counts", "result"),
    ),
    "DOMAIN_PREPARE": WorkUnitContract(
        "DOMAIN_PREPARE",
        "ovc-srfdi-wp10-v07-domain-preparation/v1",
        ("domain_id", "configuration_plan", "preparation", "population_count", "pair_count"),
    ),
    "DOMAIN_CONFIGURATION": WorkUnitContract(
        "DOMAIN_CONFIGURATION",
        "ovc-srfdi-wp10-v07-family-configuration/v1",
        ("domain_id", "configuration", "catalog"),
    ),
    "DOMAIN_ANALYSIS": WorkUnitContract(
        "DOMAIN_ANALYSIS",
        "ovc-srfdi-wp10-v07-domain-analysis/v1",
        ("domain_id", "configuration_count", "method_disagreement", "invariant_core_support"),
    ),
    "PACKET": WorkUnitContract(
        "PACKET",
        "ovc-srfdi-wp10-v07-production-evidence-packet/v1",
        ("run_id", "run_binding_sha256", "completed_work_unit_manifest_before_packet"),
    ),
}


def classify_work_unit(unit_id: str) -> str:
    unit = str(unit_id)
    if unit == "population":
        return "POPULATION"
    if unit.startswith("segmentation/") and unit.count("/") == 1:
        return "SEGMENTATION"
    if unit == "packet":
        return "PACKET"
    parts = unit.split("/")
    if len(parts) == 3 and parts[0] == "domain" and parts[2] == "prepare":
        return "DOMAIN_PREPARE"
    if len(parts) == 4 and parts[0] == "domain" and parts[2] == "configuration":
        return "DOMAIN_CONFIGURATION"
    if len(parts) == 3 and parts[0] == "domain" and parts[2] == "analysis":
        return "DOMAIN_ANALYSIS"
    raise WorkUnitContractError("WORK_UNIT_KIND_UNKNOWN", unit)


def validate_work_unit_output(unit_id: str, output: Mapping[str, Any]) -> None:
    if not isinstance(output, Mapping):
        raise WorkUnitContractError("WORK_UNIT_INVALID_OUTPUT", f"{unit_id}:mapping required")
    kind = classify_work_unit(unit_id)
    contract = CONTRACTS[kind]
    if output.get("schema") != contract.schema:
        raise WorkUnitContractError(
            "WORK_UNIT_OUTPUT_SCHEMA_MISMATCH",
            f"{unit_id}:expected={contract.schema}:actual={output.get('schema')}",
        )
    missing = [field for field in contract.required_fields if field not in output]
    if missing:
        raise WorkUnitContractError(
            "WORK_UNIT_OUTPUT_CONTRACT_MISSING_FIELD",
            f"{unit_id}:{','.join(missing)}",
        )
    claimed = output.get("logical_hash")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise WorkUnitContractError("WORK_UNIT_OUTPUT_LOGICAL_HASH_MISSING", unit_id)
    payload = dict(output)
    payload.pop("logical_hash", None)
    if logical_sha256(payload) != claimed:
        raise WorkUnitContractError("WORK_UNIT_OUTPUT_LOGICAL_HASH_MISMATCH", unit_id)

    if kind in {"DOMAIN_PREPARE", "DOMAIN_CONFIGURATION", "DOMAIN_ANALYSIS"}:
        expected_domain = unit_id.split("/")[1]
        if str(output.get("domain_id")) != expected_domain:
            raise WorkUnitContractError(
                "WORK_UNIT_OUTPUT_DOMAIN_MISMATCH",
                f"{unit_id}:{output.get('domain_id')}",
            )
    if kind == "DOMAIN_CONFIGURATION":
        expected_config = unit_id.split("/")[3]
        configuration = output.get("configuration")
        if not isinstance(configuration, Mapping) or str(configuration.get("configuration_id")) != expected_config:
            raise WorkUnitContractError(
                "WORK_UNIT_OUTPUT_CONFIGURATION_MISMATCH", unit_id
            )
        catalog = output.get("catalog")
        if not isinstance(catalog, Mapping):
            raise WorkUnitContractError("WORK_UNIT_OUTPUT_CATALOG_MISSING", unit_id)
    if kind == "DOMAIN_ANALYSIS":
        if not isinstance(output.get("method_disagreement"), Mapping):
            raise WorkUnitContractError("WORK_UNIT_OUTPUT_ANALYSIS_SHAPE_INVALID", unit_id)
        if not isinstance(output.get("invariant_core_support"), Mapping):
            raise WorkUnitContractError("WORK_UNIT_OUTPUT_ANALYSIS_SHAPE_INVALID", unit_id)


def validated_worker(worker: Callable[[str], Mapping[str, Any]]) -> Callable[[str], Mapping[str, Any]]:
    def wrapped(unit_id: str) -> Mapping[str, Any]:
        output = worker(unit_id)
        validate_work_unit_output(unit_id, output)
        return output
    return wrapped


def synthetic_work_units(
    *,
    domain_count: int = SYNTHETIC_DOMAIN_COUNT,
    configurations_per_domain: int = SYNTHETIC_CONFIGURATIONS_PER_DOMAIN,
) -> tuple[str, ...]:
    units = [
        "population",
        "segmentation/RUN_CHANGE_SEGMENTATION",
        "segmentation/NULL_BOUNDARY_CONTROL",
    ]
    for domain_index in range(domain_count):
        domain_id = f"SYNTH.DOMAIN.{domain_index:02d}"
        units.append(f"domain/{domain_id}/prepare")
        for config_index in range(configurations_per_domain):
            units.append(f"domain/{domain_id}/configuration/SYNTH.CONFIG.{config_index:02d}")
        units.append(f"domain/{domain_id}/analysis")
    units.append("packet")
    return tuple(units)


def _sealed(payload: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    return {**body, "logical_hash": logical_sha256(body)}


def synthetic_worker(unit_id: str) -> Mapping[str, Any]:
    kind = classify_work_unit(unit_id)
    if kind == "POPULATION":
        return _sealed({
            "schema": CONTRACTS[kind].schema,
            "source_record_count": 9420,
            "eligible_record_count": 8598,
            "eligible_record_ids_sha256": "ab" * 32,
            "population_id": "SRFD.SYNTHETIC.REHEARSAL.POPULATION.v1",
            "comparability_domain_count": 36,
            "exact_pair_opportunity_count": 35380668,
            "family_configuration_count": 1944,
            "work_unit_count": SYNTHETIC_WORK_UNIT_COUNT,
            "provider_fetch": "DENIED",
            "validation_2025": "LOCKED_UNCONSUMED",
        })
    if kind == "SEGMENTATION":
        method = unit_id.split("/", 1)[1]
        return _sealed({
            "schema": CONTRACTS[kind].schema,
            "method_id": method,
            "counts": {"stream_count": 1, "segment_count": 1, "boundary_count": 0},
            "result": {"synthetic": True, "method_id": method},
            "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
        })
    if kind == "DOMAIN_PREPARE":
        domain_id = unit_id.split("/")[1]
        return _sealed({
            "schema": CONTRACTS[kind].schema,
            "domain_id": domain_id,
            "population_count": 2,
            "pair_count": 1,
            "unique_pattern_count": 2,
            "representation_id": "SYNTH.REPRESENTATION",
            "distance_id": "GOWER_MIXED",
            "null_control_fast_path": False,
            "gower_equivalence": {"checked_pairs": 1, "result": "PASS"},
            "configuration_plan": [
                {"configuration_id": f"SYNTH.CONFIG.{index:02d}"}
                for index in range(SYNTHETIC_CONFIGURATIONS_PER_DOMAIN)
            ],
            "preparation": {"hierarchical": {}, "medoid": {}, "pam": {}},
            "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
        })
    if kind == "DOMAIN_CONFIGURATION":
        _, domain_id, _, configuration_id = unit_id.split("/")
        return _sealed({
            "schema": CONTRACTS[kind].schema,
            "domain_id": domain_id,
            "configuration": {"configuration_id": configuration_id, "synthetic": True},
            "catalog": {
                "family_catalog_id": f"SYNTH.CATALOG.{domain_id}.{configuration_id}",
                "configuration_id": configuration_id,
                "families": [],
                "residual_ids": ["SYNTH.1", "SYNTH.2"],
            },
            "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
        })
    if kind == "DOMAIN_ANALYSIS":
        domain_id = unit_id.split("/")[1]
        return _sealed({
            "schema": CONTRACTS[kind].schema,
            "domain_id": domain_id,
            "configuration_count": SYNTHETIC_CONFIGURATIONS_PER_DOMAIN,
            "sensitivity_metrics": {"synthetic": True},
            "per_configuration_stability": [],
            "pair_qualification_ledger": [],
            "ordered_pair_stability": [],
            "family_correspondence_split_merge": [],
            "invariant_core_support": {"cores": [], "catalog_denominator": SYNTHETIC_CONFIGURATIONS_PER_DOMAIN},
            "method_disagreement": {"method_count": SYNTHETIC_CONFIGURATIONS_PER_DOMAIN, "record_denominator": 2, "disagreement_count": 0, "disagreements": []},
            "scientific_disposition": "NOT_PERFORMED_SYNTHETIC_REHEARSAL",
            "authority_effect": "NONE_EXECUTION_ROUTE_ONLY",
        })
    if kind == "PACKET":
        binding = synthetic_binding()
        run_id = stable_id(
            "SRFD.RUN.",
            {"token_id": SYNTHETIC_TOKEN_ID, "run_binding_sha256": binding.logical_hash},
        )
        return _sealed({
            "schema": CONTRACTS[kind].schema,
            "programme_id": PROGRAMME_ID,
            "packet_id": PACKET_ID,
            "run_id": run_id,
            "run_binding_sha256": binding.logical_hash,
            "population_id": "SRFD.SYNTHETIC.REHEARSAL.POPULATION.v1",
            "completed_work_unit_manifest_before_packet": [],
            "provider_fetch": "DENIED",
            "validation_2025": "LOCKED_UNCONSUMED",
            "scientific_disposition": "NOT_PERFORMED_SYNTHETIC_REHEARSAL",
            "selector_family_semantic_publication": "NONE",
            "probability_risk_exposure_execution": "NONE",
        })
    raise AssertionError(kind)


def synthetic_binding() -> RunBinding:
    return RunBinding(
        programme_id=PROGRAMME_ID,
        packet_id=PACKET_ID,
        population_id="SRFD.SYNTHETIC.REHEARSAL.POPULATION.v1",
        eligible_ids_sha256="01" * 32,
        scientific_manifest_sha256="02" * 32,
        preregistration_sha256="03" * 32,
        representation_pack_sha256="04" * 32,
        segmentation_pack_sha256="05" * 32,
        stability_pack_sha256="06" * 32,
        source_binding_sha256="07" * 32,
        capacity_grid_sha256="08" * 32,
        implementation_commit="09" * 32,
    )


def synthetic_token(binding: RunBinding) -> dict[str, Any]:
    return {
        "schema": "ovc-srfd-synthetic-rehearsal-authority/v1",
        "token_id": SYNTHETIC_TOKEN_ID,
        "state": "AUTHORIZED_UNCONSUMED",
        "run_binding_sha256": binding.logical_hash,
        "authority_effect": "SYNTHETIC_EXECUTION_ONLY_NO_SCIENTIFIC_AUTHORITY",
    }


def _run_plan(
    root: Path,
    *,
    unit_ids: Sequence[str],
    stop_after_new_units: int | None = None,
) -> dict[str, Any]:
    root = Path(root)
    binding = synthetic_binding()
    authority = RunAuthorityStore(root)
    try:
        start = authority.load(SYNTHETIC_TOKEN_ID)
    except ExecutionResilienceError as exc:
        if exc.reason_code != "TOKEN_NOT_CONSUMED":
            raise
        start = authority.consume(synthetic_token(binding), binding)
    checkpoints = CachedRunCheckpointStoreV11(root)
    artifacts = ContentAddressedArtifactStoreV10(
        root,
        max_external_bytes=SYNTHETIC_EXTERNAL_LIMIT_BYTES,
    )
    capacity = RunCapacityStore(
        root,
        max_committed_active_wall_seconds=4 * 60 * 60,
        max_peak_rss_bytes=4 * 1024**3,
    )
    return execute_durable_resumable_units(
        start=start,
        binding=binding,
        checkpoint_store=checkpoints,
        artifact_store=artifacts,
        capacity_store=capacity,
        unit_ids=unit_ids,
        worker=validated_worker(synthetic_worker),
        stop_after_new_units=stop_after_new_units,
    )


def run_restart_torture(root: Path) -> dict[str, Any]:
    root = Path(root)
    reference_root = root / "reference"
    torture_root = root / "torture"
    plan = synthetic_work_units(domain_count=2, configurations_per_domain=2)
    reference = _run_plan(reference_root, unit_ids=plan)
    targets = tuple(range(1, len(plan) + 1))
    current = 0
    result = None
    for target in targets:
        if target <= current:
            continue
        result = _run_plan(
            torture_root,
            unit_ids=plan,
            stop_after_new_units=target - current,
        )
        current = int(result["completed_unit_count"])
        if current != target:
            raise WorkUnitContractError(
                "RESTART_TORTURE_PROGRESS_MISMATCH", f"expected={target}:actual={current}"
            )
    if result is None or not result["complete"]:
        raise WorkUnitContractError("RESTART_TORTURE_INCOMPLETE", str(current))
    if result["unit_output_hashes"] != reference["unit_output_hashes"]:
        raise WorkUnitContractError("RESTART_TORTURE_OUTPUT_DIVERGENCE", "hash maps differ")
    if result["result_logical_hash"] != reference["result_logical_hash"]:
        raise WorkUnitContractError("RESTART_TORTURE_RESULT_DIVERGENCE", "result hash differs")
    payload = {
        "schema": "ovc-srfdi-wp10-v11-restart-torture-receipt/v1",
        "status": "PASS",
        "work_unit_count": len(plan),
        "restart_targets": list(targets),
        "transition_classes": [
            "POPULATION_TO_SEGMENTATION",
            "SEGMENTATION_TO_DOMAIN_PREPARE",
            "DOMAIN_PREPARE_TO_CONFIGURATION",
            "CONFIGURATION_TO_CONFIGURATION",
            "CONFIGURATION_TO_ANALYSIS",
            "ANALYSIS_TO_NEXT_DOMAIN_PREPARE",
            "FINAL_ANALYSIS_TO_PACKET",
        ],
        "reference_result_logical_hash": reference["result_logical_hash"],
        "torture_result_logical_hash": result["result_logical_hash"],
        "scientific_delta": "NONE_SYNTHETIC_ONLY",
    }
    return {**payload, "logical_sha256": logical_sha256(payload)}


def run_full_synthetic_rehearsal(root: Path) -> dict[str, Any]:
    root = Path(root)
    plan = synthetic_work_units()
    if len(plan) != SYNTHETIC_WORK_UNIT_COUNT:
        raise WorkUnitContractError(
            "SYNTHETIC_PLAN_COUNT_MISMATCH", f"{len(plan)}"
        )
    started = time.perf_counter()
    result = _run_plan(root, unit_ids=plan)
    elapsed = time.perf_counter() - started
    if not result["complete"] or result["completed_unit_count"] != SYNTHETIC_WORK_UNIT_COUNT:
        raise WorkUnitContractError("SYNTHETIC_REHEARSAL_INCOMPLETE", str(result["completed_unit_count"]))
    binding = synthetic_binding()
    start = RunAuthorityStore(root).load(SYNTHETIC_TOKEN_ID)
    checkpoint = RunCheckpointStore(root).latest(start, binding)
    artifact_store = ContentAddressedArtifactStoreV10(root, max_external_bytes=SYNTHETIC_EXTERNAL_LIMIT_BYTES)
    capacity_path = root / "runs" / start.run_id / "capacity_telemetry.json"
    capacity = json.loads(capacity_path.read_text(encoding="utf-8"))
    payload = {
        "schema": "ovc-srfdi-wp10-v11-full-synthetic-rehearsal-receipt/v1",
        "status": "PASS",
        "work_unit_count": SYNTHETIC_WORK_UNIT_COUNT,
        "completed_unit_count": int(result["completed_unit_count"]),
        "checkpoint_sequence": int(checkpoint.sequence),
        "last_checkpoint_id": checkpoint.checkpoint_id,
        "result_logical_hash": result["result_logical_hash"],
        "artifact_store_bytes": int(artifact_store.total_bytes(start.run_id)),
        "capacity_accounted_unit_count": int(capacity["accounted_unit_count"]),
        "capacity_peak_rss_bytes": int(capacity["peak_rss_bytes"]),
        "capacity_status": capacity["capacity_status"],
        "elapsed_wall_seconds_non_identity": elapsed,
        "scheduler": "execute_durable_resumable_units",
        "checkpoint_store": "CachedRunCheckpointStoreV11_WIRE_IDENTICAL_RUN_CHECKPOINT_STORE",
        "artifact_store": "ContentAddressedArtifactStoreV10/ContentAddressedArtifactStore",
        "work_unit_output_contract_validation": "ENFORCED_BEFORE_CAPACITY_ARTIFACT_CHECKPOINT_COMMIT",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_delta": "NONE_SYNTHETIC_MINIMAL_PAYLOAD",
        "authority_effect": "NONE_EXECUTION_REHEARSAL_ONLY",
    }
    identity_payload = dict(payload)
    identity_payload.pop("elapsed_wall_seconds_non_identity", None)
    payload["logical_sha256"] = logical_sha256(identity_payload)
    return payload
