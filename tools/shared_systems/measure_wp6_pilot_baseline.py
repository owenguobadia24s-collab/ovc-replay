#!/usr/bin/env python3
"""Measure and print the immutable SHSI-WP6 pilot baseline; never writes files."""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from typing import Callable

from ovc.development.identity import canonical_json_bytes, canonical_sha256, sha256_file
from ovc.shared_systems.envelopes import AdapterDescriptor, CompatibilityContract
from ovc.shared_systems.execution import RunExecutionManifest, RunSpecification, SemanticGenerationRef, run_reference
from ovc.shared_systems.foundation import (
    DurableArtifactDescriptor,
    PILOT_HARD_FLOOR_DIMENSIONS,
    PILOT_NUMERIC_CAP_DIMENSIONS,
    PilotAcceptanceBudget,
    PilotBaselineMeasurement,
    inspect_reachability,
)
from ovc.shared_systems.resolution import (
    AdapterRegistry,
    CompatibilityRegistry,
    RegistryDirectory,
    RegistryDirectoryEntry,
    ResolutionRequest,
    ServiceConsumptionBinding,
    SharedServiceDescriptor,
    resolve_exact,
)


PROCEDURE_REF = "tools/shared_systems/measure_wp6_pilot_baseline.py"
INPUT_REF = "fixtures/shared_systems/foundation/SHSI_WP6_MEASUREMENT_INPUTS_v0_1.json"
CORE_ARTIFACTS = (
    "contracts/shared_systems/OVC_SHARED_SYSTEMS_PERSISTENCE_SECURITY_OBSERVABILITY_CONTRACT_v0_1.md",
    "fixtures/shared_systems/foundation/SHSI_WP6_FOUNDATION_NEGATIVE_FIXTURES_v0_1.json",
    "schemas/shared_systems/persistence_security_observability_v0_1.schema.json",
    "src/ovc/shared_systems/foundation.py",
)


def _elapsed_us(operation: Callable[[], object], samples: int) -> tuple[float, ...]:
    values = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        operation()
        values.append((time.perf_counter_ns() - started) / 1_000.0)
    return tuple(values)


def _percentile(values: tuple[float, ...], percentile: int) -> float:
    ordered = sorted(values)
    index = max(0, ((len(ordered) * percentile + 99) // 100) - 1)
    return round(ordered[index], 3)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _resolver_fixture() -> tuple[Callable[[], object], AdapterDescriptor]:
    descriptor = SharedServiceDescriptor(
        "SVC.1", "SVC.1.RELEASE.1", "OWNER.1", "REGISTRY.1",
        ("CAP.1",), ("CONTRACT.PRODUCER.1",), "QUAL.1", "CURRENT", True,
    )
    request = ResolutionRequest(
        "REQUEST.1", "CONSUMER.1", "CONSUMER.1.GEN.1", "SVC.1", "CAP.1",
        "SVC.1.RELEASE.1", "CONTRACT.CONSUMER.1", "SCOPE.1", "AUTH.1", "ENV.1", "CUTOFF.1",
    )
    compatibility = CompatibilityContract(
        "COMPAT.1", "CONTRACT.PRODUCER.1", "CONTRACT.CONSUMER.1",
        "ADAPTER_REQUIRED", "SCOPE.1", ("EXACT_FIELDS",),
    )
    adapter = AdapterDescriptor(
        "ADAPTER.1", "OWNER.1", "CONTRACT.PRODUCER.1", "CONTRACT.CONSUMER.1",
        (("value", "value"),), (),
    )
    arguments = {
        "directory": RegistryDirectory(
            (RegistryDirectoryEntry("SVC.1", "OWNER.1", "REGISTRY.1", "STAGE0.1"),),
            stage0_owner_bindings={"SVC.1": "OWNER.1"},
        ),
        "owner_descriptors": {"REGISTRY.1": (descriptor,)},
        "consumption_bindings": (
            ServiceConsumptionBinding(
                "CONSUME.1", "CONSUMER.1", "SVC.1", "CAP.1",
                ("SVC.1.RELEASE.1",), ("AUTH.1",),
            ),
        ),
        "qualification_currentness": {"QUAL.1": "CURRENT"},
        "compatibility_registry": CompatibilityRegistry((compatibility,)),
        "adapter_registry": AdapterRegistry((adapter,)),
    }
    return lambda: resolve_exact(request, **arguments), adapter


def _execution_fixture() -> tuple[RunSpecification, RunExecutionManifest, dict[str, int]]:
    generation = SemanticGenerationRef("FIXTURE_OWNER", "FIXTURE.GEN.v1", ("FIXTURE.CONTRACT.v1",))
    spec = RunSpecification(
        generation.logical_id, ("R1", "R2", "R3", "R4"), "FIXTURE.SCOPE.v1",
        "2026-08-01T12:00:00Z", {"precision": "EXACT"}, "FIXTURE.OUTPUT.v1",
        ("SOURCE:FVT<=2026-08-01T12:00:00Z",),
    )
    manifest = RunExecutionManifest(spec.logical_id, "ENV.WP6", "ATTEMPT.WP6", 1, 1, "LOCAL_REFERENCE", "<NON_SEMANTIC>")
    return spec, manifest, {"R1": 1, "R2": 2, "R3": 3, "R4": 4}


def _checkpoint_overhead_samples(samples: int) -> tuple[float, ...]:
    spec, manifest, records = _execution_fixture()
    transform = lambda value: {"exact": value * 7}
    values = []
    for _ in range(samples):
        start = time.perf_counter_ns()
        run_reference(spec, manifest, records, transform)
        fresh = time.perf_counter_ns() - start
        start = time.perf_counter_ns()
        interrupted = run_reference(spec, manifest, records, transform, stop_after=1)
        run_reference(spec, manifest, records, transform, checkpoint=interrupted.checkpoint)
        resumed = time.perf_counter_ns() - start
        values.append(max(0.0, (resumed - fresh) / 1_000.0))
    return tuple(values)


def _adapter_surface_lines(root: Path) -> int:
    targets = (
        (root / "src/ovc/shared_systems/envelopes.py", "AdapterDescriptor"),
        (root / "src/ovc/shared_systems/resolution.py", "AdapterRegistry"),
    )
    total = 0
    for path, class_name in targets:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        node = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == class_name)
        total += node.end_lineno - node.lineno + 1
    return total


def _measurement(dimension: str, unit: str, values: tuple[float, ...], evidence: tuple[str, ...], environment: str, procedure_sha: str) -> PilotBaselineMeasurement:
    rounded = tuple(round(float(value), 3) for value in values)
    identity_payload = {
        "dimension": dimension, "unit": unit, "environment_ref": environment,
        "procedure_ref": f"sha256:{procedure_sha}", "sample_values": rounded,
        "evidence_refs": evidence, "authority_effect": "NONE",
    }
    return PilotBaselineMeasurement(
        "SHSI-WP6-MEAS-" + canonical_sha256(identity_payload), dimension, unit,
        environment, f"sha256:{procedure_sha}", rounded, evidence,
    )


def measure(root: Path, source_commit: str, samples: int) -> dict[str, object]:
    resolved = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()
    if resolved != source_commit:
        raise SystemExit("MEASUREMENT_SOURCE_COMMIT_MUST_EQUAL_HEAD")
    inputs = json.loads((root / INPUT_REF).read_text(encoding="utf-8"))
    procedure_sha = sha256_file(root / PROCEDURE_REF)
    input_sha = sha256_file(root / INPUT_REF)
    environment = f"{platform.system()}-{platform.machine()}-python-{platform.python_version()}"
    resolve_operation, adapter = _resolver_fixture()
    canonical_payload = {
        "packet": "SHSI-WP6", "service": "SVC.1", "release": "SVC.1.RELEASE.1",
        "population": ["R1", "R2", "R3", "R4"], "authority_effect": "NONE",
    }
    for _ in range(50):
        resolve_operation()
        canonical_json_bytes(canonical_payload)
    resolver_samples = _elapsed_us(resolve_operation, samples)
    canonical_samples = _elapsed_us(lambda: canonical_json_bytes(canonical_payload), samples)

    tracemalloc.start()
    before_current, _ = tracemalloc.get_traced_memory()
    for _ in range(100):
        resolve_operation()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_delta = max(0, peak - before_current)

    raw = b"durable evidence"
    descriptor = DurableArtifactDescriptor(
        "ARTIFACT.1", "LOGICAL.ARTIFACT.1", __import__("hashlib").sha256(raw).hexdigest(),
        len(raw), "application/octet-stream", "LOCAL_REBUILDABLE", "OWNER.1", "REPRODUCIBILITY_REQUIRED",
    )
    reachability_samples = _elapsed_us(
        lambda: inspect_reachability("REACH.1", (descriptor,), {"ARTIFACT.1": raw}), samples,
    )
    checkpoint_samples = _checkpoint_overhead_samples(max(31, samples // 5))

    created = _parse_timestamp(inputs["ci_observation"]["created_at"])
    queue_samples = tuple(
        (_parse_timestamp(job["started_at"]) - created).total_seconds()
        for job in inputs["ci_observation"]["jobs"]
    )
    wasted = tuple(
        (_parse_timestamp(job["completed_at"]) - _parse_timestamp(job["started_at"])).total_seconds()
        for job in inputs["ci_observation"]["jobs"]
        if job["conclusion"] in {"failure", "cancelled", "timed_out"}
    ) or (0.0,)
    artifact_bytes = sum((root / path).stat().st_size for path in CORE_ARTIFACTS)
    operator = inputs["operator_observation"]
    incidents = inputs["incident_observation"]
    evidence = (f"git:{source_commit}", f"sha256:{input_sha}")
    values = {
        "RESOLVER_P50_LATENCY_US": (_percentile(resolver_samples, 50),),
        "RESOLVER_P95_LATENCY_US": (_percentile(resolver_samples, 95),),
        "CANONICALIZATION_P50_LATENCY_US": (_percentile(canonical_samples, 50),),
        "CANONICALIZATION_P95_LATENCY_US": (_percentile(canonical_samples, 95),),
        "PEAK_MEMORY_DELTA_BYTES": (float(peak_delta),),
        "ARTIFACT_BYTE_DELTA_BYTES": (float(artifact_bytes),),
        "CHECKPOINT_RESTART_OVERHEAD_US": (_percentile(checkpoint_samples, 95),),
        "EVIDENCE_REACHABILITY_LATENCY_US": (_percentile(reachability_samples, 95),),
        "CI_QUEUE_TIME_SECONDS": queue_samples,
        "WASTED_ASSURANCE_TIME_SECONDS": wasted,
        "OPERATOR_TIME_SECONDS": (float(operator["operator_elapsed_seconds"]),),
        "MAINTENANCE_TIME_SECONDS": (float(operator["maintenance_elapsed_seconds"]),),
        "ACTIVE_ADAPTER_COUNT": (0.0,),
        "ADAPTER_CODE_SURFACE_LINES": (float(_adapter_surface_lines(root)),),
        "ADAPTER_MAPPING_COUNT": (float(len(adapter.field_mapping)),),
        "ADAPTER_INCIDENT_CONTRIBUTION_COUNT": (float(incidents["adapter_attributed_incident_count"]),),
        "DEPENDENCY_FAN_OUT_COUNT": (1.0,),
        "INVALIDATION_VOLUME_COUNT": (1.0,),
    }
    if set(values) != set(PILOT_NUMERIC_CAP_DIMENSIONS):
        raise SystemExit("MEASUREMENT_DIMENSION_SET_INCOMPLETE")
    baselines = tuple(
        _measurement(
            dimension, PILOT_NUMERIC_CAP_DIMENSIONS[dimension], values[dimension],
            evidence, environment, procedure_sha,
        )
        for dimension in sorted(values)
    )
    derivation_ref = f"{PROCEDURE_REF}#NO_SLACK_MAX_OF_PINNED_BASELINE"
    identity_seed = {
        "baseline_measurement_refs": [item.measurement_id for item in baselines],
        "zero_tolerance_floor": [[item, 0] for item in sorted(PILOT_HARD_FLOOR_DIMENSIONS)],
        "derivation_procedure_ref": derivation_ref,
    }
    budget = PilotAcceptanceBudget.freeze_from_baselines(
        "SHSI-WP6-BUDGET-" + canonical_sha256(identity_seed), baselines,
        derivation_procedure_ref=derivation_ref,
    )
    payload = {
        "schema": "ovc-shsi-pilot-baseline-and-acceptance-budget/v0.1",
        "programme_id": "OVC-SHARED-SYSTEMS-v0.1",
        "packet_id": "SHSI-WP6",
        "measurement_source_commit": source_commit,
        "measurement_source_tree": subprocess.run(
            ["git", "show", "-s", "--format=%T", source_commit], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip(),
        "environment_ref": environment,
        "procedure": {"path": PROCEDURE_REF, "sha256": procedure_sha, "sample_count": samples, "percentile_rule": "NEAREST_RANK", "cap_rule": "NO_SLACK_MAX_OF_PINNED_BASELINE"},
        "input_evidence": {"path": INPUT_REF, "sha256": input_sha},
        "raw_observation_summary": {
            "resolver_samples": len(resolver_samples), "canonicalization_samples": len(canonical_samples),
            "checkpoint_samples": len(checkpoint_samples), "reachability_samples": len(reachability_samples),
            "ci_job_samples": len(queue_samples), "core_artifact_paths": list(CORE_ARTIFACTS),
        },
        "baseline_measurements": [asdict(item) for item in baselines],
        "pilot_acceptance_budget": {**asdict(budget), "logical_id": budget.logical_id},
        "hard_floor_observed_values": {item: 0 for item in sorted(PILOT_HARD_FLOOR_DIMENSIONS)},
        "budget_relaxable_within_pilot": False,
        "authority_effect": "NONE",
    }
    return {**payload, "logical_id": canonical_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--measurement-source-commit", required=True)
    parser.add_argument("--samples", type=int, default=501)
    args = parser.parse_args()
    if args.samples < 101:
        raise SystemExit("SAMPLE_COUNT_MUST_BE_AT_LEAST_101")
    result = measure(args.repo_root.resolve(), args.measurement_source_commit, args.samples)
    json.dump(result, sys.stdout, sort_keys=True, indent=2, allow_nan=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
