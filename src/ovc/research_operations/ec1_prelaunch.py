from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import os
import platform
import shutil
import sys
import tempfile

from .canonical import canonical_sha256
from .dmrp_execution import F0BlindedProjection, StageSemanticDependencyMatrix


EC1_GENERATION = "OVC-EC1-DISCOVERY-2021_2023-G1"
EXPECTED_C2_PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
EXPECTED_C2_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
EXPECTED_C2E_PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
EXPECTED_C2E_PACK_SHA256 = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
EXPECTED_INTERVAL = "[2021-01-01T00:00:00Z,2024-01-01T00:00:00Z)"
EXPECTED_ACTIVE_SPINE = ("OPT-A", "OPT-B.C1.v2", "OPT-B.C2.vNext", "OPT-B.C2E.v0.2")

COURT_RECORD_PATHS = {
    "ec1_current": "registries/implementation/ec1_dmrp_v0_1/CURRENT_STATE_POINTER.json",
    "f0_hold": "docs/releases/ec1-dmrp-conformance-v0-1/f0-a/EC1_F0_A_OPERATOR_HOLD_20260816_v0_1.json",
    "active_stack": "registries/governance/active_stack/OVC_ACTIVE_STACK_STATE_v0_1.json",
    "c2_authority": "registries/opt_b/c2/vnext/C2_VNEXT_ACTIVE_RUNTIME_AUTHORITY_v0_1.json",
    "c2e_authority": "registries/authority/C2E_ACTIVE_ENGINE_AUTHORITY_v0_1.json",
    "identity_manifest": "registries/research_operations/EC1_IDENTITY_FIELD_MANIFEST_v1.json",
    "search_pack": "registries/research_operations/EC1_SEARCH_PARAMETER_PACK_v1.json",
    "f0_policy": "registries/research_operations/EC1_F0_SELECTOR_AND_SCALE_POLICY_v1.json",
    "source_materialisation": "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_CURRENT_SOURCE_MATERIALISATION_CLOSEOUT_v0_1.json",
    "prsc_prereg": "docs/programmes/ec1-prsc-v0-1/wp9/PRSCI_G_PREREG_GATE_PACKET_v0_1.json",
    "c2p_interlock": "registries/research_operations/EC1_C2P_PARALLEL_ROUTE_EXECUTION_INTERLOCK_v0_1.json",
}

STAGES = (
    "SOURCE_HYDRATION",
    "C2_VNEXT",
    "C2E",
    "P1_DENOMINATOR_CONSTRUCTION",
    "PREDICATE_COMPILATION",
    "PATTERN_LATTICE",
    "CORE_CLOSURE_EXTRACTION",
    "ADVERSARIAL_REVIEW",
    "REVIEW_PACKET",
)


class EC1PrelaunchError(RuntimeError):
    pass


class EC1PrelaunchInjectedFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class RepositoryPrelaunchReport:
    checks: Mapping[str, str]
    warnings: tuple[str, ...]
    source_bindings: Mapping[str, str]

    @property
    def semantic_sha256(self) -> str:
        return canonical_sha256(
            {
                "checks": dict(sorted(self.checks.items())),
                "warnings": list(self.warnings),
                "source_bindings": dict(sorted(self.source_bindings.items())),
            }
        )


@dataclass(frozen=True)
class EnvironmentProbe:
    python: str
    implementation: str
    platform: str
    machine: str
    free_disk_bytes: int
    temp_write: str

    @property
    def semantic_sha256(self) -> str:
        return canonical_sha256(self.__dict__)


@dataclass(frozen=True)
class RehearsalResult:
    stage_hashes: Mapping[str, str]
    terminal_hash: str
    resumed_from_checkpoint: bool

    @property
    def semantic_sha256(self) -> str:
        return canonical_sha256(
            {
                "stage_hashes": dict(self.stage_hashes),
                "terminal_hash": self.terminal_hash,
                "resumed_from_checkpoint": self.resumed_from_checkpoint,
            }
        )


def _load(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EC1PrelaunchError(f"COURT_RECORD_UNREADABLE:{relative}") from exc
    if not isinstance(value, dict):
        raise EC1PrelaunchError(f"COURT_RECORD_NOT_OBJECT:{relative}")
    return value


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise EC1PrelaunchError(code)


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, Mapping) or key not in value:
            raise EC1PrelaunchError(f"MISSING_FIELD:{'.'.join(keys)}")
        value = value[key]
    return value


def verify_repository_prelaunch(root: str | Path) -> RepositoryPrelaunchReport:
    root = Path(root).resolve()
    records = {name: _load(root, rel) for name, rel in COURT_RECORD_PATHS.items()}
    current = records["ec1_current"]
    hold = records["f0_hold"]
    active = records["active_stack"]
    c2 = records["c2_authority"]
    c2e = records["c2e_authority"]
    identity = records["identity_manifest"]
    search = records["search_pack"]
    f0 = records["f0_policy"]
    source = records["source_materialisation"]
    prsc = records["prsc_prereg"]
    c2p_interlock = records["c2p_interlock"]

    checks: dict[str, str] = {}

    _require(current.get("real_source_authority") == "AUTHORISED_BOUNDED", "EC1_GREAL_AUTHORITY_NOT_CURRENT")
    _require(current.get("research_operations_real_append") == "AUTHORISED_BOUNDED", "EC1_RO_APPEND_NOT_CURRENT")
    _require(current.get("next_packet") == "F0-A", "EC1_FRONTIER_NOT_F0_A")
    _require(current.get("validation") == "LOCKED_UNCONSUMED", "VALIDATION_NOT_LOCKED")
    _require(_nested(current, "execution_hold", "status") == "HOLD", "F0_A_HOLD_NOT_ACTIVE")
    checks["ec1_authority"] = "PASS"

    _require(hold.get("status") == "HOLD", "F0_A_HOLD_RECORD_NOT_ACTIVE")
    _require(hold.get("f0_a_execution") == "DENIED_WHILE_HOLD_ACTIVE", "F0_A_HOLD_NOT_FAIL_CLOSED")
    _require(hold.get("dmrpi_greal_ec1_authority") == "PRESERVED_AUTHORISED_BOUNDED_NOT_REVOKED", "GREAL_NOT_PRESERVED")
    _require(hold.get("release_condition") == "EXPLICIT_OPERATOR_RESUME_OR_SUPERSEDING_INSTRUCTION", "F0_RELEASE_CONDITION_DRIFT")
    checks["f0_hold"] = "PASS"

    _require(tuple(active.get("active_spine", ())) == EXPECTED_ACTIVE_SPINE, "ACTIVE_SPINE_DRIFT")
    _require(active.get("market_envelope", {}).get("validation") == "LOCKED_UNCONSUMED", "ACTIVE_STACK_VALIDATION_DRIFT")
    checks["active_spine"] = "PASS"

    _require(c2.get("package_id") == EXPECTED_C2_PACKAGE_ID, "C2_PACKAGE_ID_DRIFT")
    _require(c2.get("package_sha256") == EXPECTED_C2_PACKAGE_SHA256, "C2_PACKAGE_HASH_DRIFT")
    _require(c2.get("state") == "ACTIVE_STRUCTURAL_DESCRIPTION_DISCOVERY_DEVELOPMENT", "C2_NOT_ACTIVE")
    checks["c2_binding"] = "PASS"

    _require(c2e.get("active_boundary_pack_id") == EXPECTED_C2E_PACK_ID, "C2E_PACK_ID_DRIFT")
    _require(c2e.get("active_boundary_pack_logical_sha256") == EXPECTED_C2E_PACK_SHA256, "C2E_PACK_HASH_DRIFT")
    _require(c2e.get("state") == "ACTIVE_ENGINE_CURRENT_OPERATOR_SELECTED_PACK_MARKET_ENVELOPE_BOUND", "C2E_NOT_ACTIVE")
    checks["c2e_binding"] = "PASS"

    bindings = identity.get("source_bindings", {})
    _require(identity.get("generation_id") == EC1_GENERATION, "EC1_IDENTITY_GENERATION_DRIFT")
    _require(bindings.get("c2_package") == EXPECTED_C2_PACKAGE_ID, "IDENTITY_C2_PACKAGE_DRIFT")
    _require(bindings.get("c2_package_sha256") == EXPECTED_C2_PACKAGE_SHA256, "IDENTITY_C2_HASH_DRIFT")
    _require(bindings.get("c2e_boundary_pack") == EXPECTED_C2E_PACK_ID, "IDENTITY_C2E_PACK_DRIFT")
    _require(bindings.get("c2e_boundary_pack_sha256") == EXPECTED_C2E_PACK_SHA256, "IDENTITY_C2E_HASH_DRIFT")
    for item in identity.get("fields", []):
        if not isinstance(item, Mapping):
            raise EC1PrelaunchError("IDENTITY_FIELD_NOT_OBJECT")
        source_path = str(item.get("source_path", ""))
        _require(bool(source_path), "IDENTITY_FIELD_SOURCE_PATH_MISSING")
        _require((root / source_path).is_file(), f"IDENTITY_FIELD_SOURCE_UNREACHABLE:{source_path}")
    checks["semantic_source_reachability"] = "PASS"

    _require(search.get("cycle_id") == EC1_GENERATION, "SEARCH_GENERATION_DRIFT")
    _require(search.get("representation") == "DIRECT_STRUCTURAL_CANONICAL_v1", "SEARCH_REPRESENTATION_DRIFT")
    _require(search.get("search") == "DIRECT_STRUCTURAL_PATTERN_LATTICE_v1", "SEARCH_METHOD_DRIFT")
    for field in ("normalization", "distance", "learned_similarity", "top_n", "candidate_strength_threshold"):
        _require(search.get(field) == "NONE", f"SEARCH_FORBIDDEN_CONTROL:{field}")
    _require(search.get("transition_sequence_lengths") == [1, 2, 3, 4], "SEARCH_SEQUENCE_LENGTH_DRIFT")
    checks["search_freeze"] = "PASS"

    _require(f0.get("effective_only_after") == "DMRPI-GREAL-EC1_PASS", "F0_POLICY_AUTHORITY_DRIFT")
    _require(_nested(f0, "f0a", "selector_id") == "EC1.F0A.THREE_7DAY_WINDOWS.ONE_PER_YEAR.v1", "F0_A_SELECTOR_DRIFT")
    _require(f0.get("scientific_parameter_tuning") == "FORBIDDEN", "F0_PARAMETER_TUNING_NOT_FORBIDDEN")
    checks["f0_selection_blinding"] = "PASS"

    materialisation = source.get("materialisation", {})
    _require(source.get("status") == "COMPLETED", "SOURCE_MATERIALISATION_NOT_COMPLETED")
    _require(materialisation.get("status") == "PASS", "SOURCE_MATERIALISATION_NOT_PASS")
    population = materialisation.get("population", {})
    _require(population.get("instrument") == "GBPUSD", "SOURCE_INSTRUMENT_DRIFT")
    _require(population.get("sides") == ["BID", "ASK"], "SOURCE_SIDES_DRIFT")
    _require(population.get("clocks") == ["15M", "2H_A_L"], "SOURCE_CLOCKS_DRIFT")
    _require(population.get("interval") == EXPECTED_INTERVAL, "SOURCE_INTERVAL_DRIFT")
    source_binding = materialisation.get("source_binding", {})
    _require(source_binding.get("c2_package_sha256") == EXPECTED_C2_PACKAGE_SHA256, "MATERIALISED_C2_HASH_DRIFT")
    _require(source_binding.get("c2e_boundary_pack_sha256") == EXPECTED_C2E_PACK_SHA256, "MATERIALISED_C2E_HASH_DRIFT")
    _require(source.get("qa", {}).get("all_projected_rows_verified") is True, "SOURCE_ROWS_NOT_VERIFIED")
    _require(source.get("qa", {}).get("resolver_conflicts_per_side") == 0, "SOURCE_RESOLVER_CONFLICT")
    _require(source.get("qa", {}).get("sampling") is False, "SOURCE_SAMPLING_FORBIDDEN")
    _require(source.get("qa", {}).get("reduced_precision") is False, "SOURCE_REDUCED_PRECISION_FORBIDDEN")
    checks["source_chain"] = "PASS"

    _require(prsc.get("status") == "APPROVED" and prsc.get("decision") == "PASS", "PRSC_PREREG_NOT_APPROVED")
    _require(_nested(prsc, "current_authority", "preregistration") == "FROZEN", "PRSC_PROTOCOL_NOT_FROZEN")
    _require(_nested(prsc, "current_authority", "f0_a") == "HOLD", "PRSC_F0_HOLD_DRIFT")
    _require(_nested(prsc, "acceptance_conditions", "e1_decision_bearing_inspection") == "ABSENT", "PRE_E1_FIREWALL_NOT_CLEAN")
    checks["prsc_pre_e1_freeze"] = "PASS"

    firewall = c2p_interlock.get("path1_firewall", {})
    for field in ("c2p_as_seed", "c2p_as_filter", "c2p_as_repair_input", "c2p_as_promotion_criterion", "post_disclosure_g1_repair"):
        _require(firewall.get(field) == "DENIED", f"C2P_PATH1_FIREWALL_DRIFT:{field}")
    _require(
        c2p_interlock.get("disclosure_firewall", {}).get("scientific_c2p_outputs")
        == "SEALED_FROM_PATH1_REVIEWERS_UNTIL_E1_CONTENT_ADDRESSED_AND_R1_PASS",
        "C2P_DISCLOSURE_FIREWALL_DRIFT",
    )
    checks["c2p_non_influence"] = "PASS"

    StageSemanticDependencyMatrix().validate_complete()
    checks["stage_dependency_matrix"] = "PASS"

    return RepositoryPrelaunchReport(
        checks=checks,
        warnings=("EC1-DEP-C2E-DENOMINATOR-001 blocks episode incidence/prevalence only; morphology remains lawful.",),
        source_bindings={
            "c2_package_sha256": EXPECTED_C2_PACKAGE_SHA256,
            "c2e_boundary_pack_sha256": EXPECTED_C2E_PACK_SHA256,
            "source_materialisation_logical_sha256": str(materialisation.get("logical_sha256", "")),
        },
    )


def probe_environment(root: str | Path, *, minimum_free_disk_bytes: int = 0) -> EnvironmentProbe:
    root = Path(root).resolve()
    usage = shutil.disk_usage(root)
    _require(usage.free >= minimum_free_disk_bytes, "PRELAUNCH_DISK_HEADROOM_INSUFFICIENT")
    with tempfile.NamedTemporaryFile(prefix="ec1-prelaunch-", dir=root, delete=True) as handle:
        handle.write(b"ec1-prelaunch")
        handle.flush()
        temp_write = "PASS"
    return EnvironmentProbe(
        python=sys.version.split()[0],
        implementation=platform.python_implementation(),
        platform=platform.system(),
        machine=platform.machine(),
        free_disk_bytes=usage.free,
        temp_write=temp_write,
    )


def validate_source_probe(
    *,
    expected_sha256: str,
    observed_sha256: str,
    available: bool,
    fallback_requested: bool = False,
) -> str:
    if fallback_requested:
        raise EC1PrelaunchError("SOURCE_FALLBACK_FORBIDDEN")
    if not available:
        raise EC1PrelaunchError("SOURCE_UNAVAILABLE")
    if observed_sha256 != expected_sha256:
        raise EC1PrelaunchError("SOURCE_HASH_MISMATCH")
    return "PASS"


def validate_artifact_probe(*, writable: bool, durable: bool, partial_write_detected: bool = False) -> str:
    if partial_write_detected:
        raise EC1PrelaunchError("PARTIAL_ARTIFACT_WRITE_QUARANTINE_REQUIRED")
    if not writable or not durable:
        raise EC1PrelaunchError("ARTIFACT_ROOT_NOT_READY")
    return "PASS"


def validate_shards(expected_units: Sequence[str], shards: Sequence[Sequence[str]]) -> str:
    expected = set(expected_units)
    assigned = [unit for shard in shards for unit in shard]
    if len(assigned) != len(set(assigned)):
        raise EC1PrelaunchError("DUPLICATE_SHARD_OWNERSHIP")
    if set(assigned) != expected:
        raise EC1PrelaunchError("INCOMPLETE_SHARD_OWNERSHIP")
    return "PASS"


def blinded_heartbeat(values: Mapping[str, Any]) -> F0BlindedProjection:
    return F0BlindedProjection(values)


def launch_guard(report: RepositoryPrelaunchReport, *, operator_release_present: bool) -> str:
    if report.checks.get("f0_hold") != "PASS":
        raise EC1PrelaunchError("F0_HOLD_EVIDENCE_INVALID")
    if not operator_release_present:
        return "BLOCKED_BY_F0_A_HOLD"
    return "READY_FOR_FINAL_LAUNCH_SEAL_ONLY"


def _load_checkpoint(path: Path) -> tuple[dict[str, str], str | None]:
    if not path.exists():
        return {}, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EC1PrelaunchError("CORRUPT_CHECKPOINT_QUARANTINE_REQUIRED") from exc
    if not isinstance(raw, dict) or raw.get("schema") != "ec1-prelaunch-stage-checkpoint/v1":
        raise EC1PrelaunchError("CORRUPT_CHECKPOINT_QUARANTINE_REQUIRED")
    stage_hashes = raw.get("stage_hashes")
    if not isinstance(stage_hashes, dict):
        raise EC1PrelaunchError("CORRUPT_CHECKPOINT_QUARANTINE_REQUIRED")
    for stage, digest in stage_hashes.items():
        if stage not in STAGES or not isinstance(digest, str) or len(digest) != 64:
            raise EC1PrelaunchError("CORRUPT_CHECKPOINT_QUARANTINE_REQUIRED")
    return dict(stage_hashes), raw.get("terminal_hash")


def run_stage_rehearsal(
    stage_payloads: Mapping[str, Any],
    *,
    checkpoint_path: str | Path | None = None,
    inject_failure_after: str | None = None,
) -> RehearsalResult:
    if set(stage_payloads) != set(STAGES):
        raise EC1PrelaunchError("REHEARSAL_STAGE_SET_INCOMPLETE")
    checkpoint = Path(checkpoint_path).resolve() if checkpoint_path is not None else None
    stage_hashes: dict[str, str] = {}
    resumed = False
    if checkpoint is not None and checkpoint.exists():
        stage_hashes, terminal = _load_checkpoint(checkpoint)
        resumed = bool(stage_hashes)
        if terminal is not None and len(stage_hashes) != len(STAGES):
            raise EC1PrelaunchError("CORRUPT_CHECKPOINT_QUARANTINE_REQUIRED")

    previous = "GENESIS"
    for stage in STAGES:
        expected = canonical_sha256({"stage": stage, "payload": stage_payloads[stage], "previous": previous})
        if stage in stage_hashes:
            if stage_hashes[stage] != expected:
                raise EC1PrelaunchError(f"CHECKPOINT_STAGE_HASH_MISMATCH:{stage}")
        else:
            stage_hashes[stage] = expected
            if checkpoint is not None:
                checkpoint.write_text(
                    json.dumps(
                        {
                            "schema": "ec1-prelaunch-stage-checkpoint/v1",
                            "stage_hashes": stage_hashes,
                            "terminal_hash": None,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n",
                    encoding="utf-8",
                )
            if inject_failure_after == stage:
                raise EC1PrelaunchInjectedFailure(f"INJECTED_FAILURE_AFTER:{stage}")
        previous = expected

    terminal_hash = canonical_sha256({"stages": [(stage, stage_hashes[stage]) for stage in STAGES]})
    if checkpoint is not None:
        checkpoint.write_text(
            json.dumps(
                {
                    "schema": "ec1-prelaunch-stage-checkpoint/v1",
                    "stage_hashes": stage_hashes,
                    "terminal_hash": terminal_hash,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
    return RehearsalResult(stage_hashes=dict(stage_hashes), terminal_hash=terminal_hash, resumed_from_checkpoint=resumed)


def build_execution_capsule(
    *,
    report: RepositoryPrelaunchReport,
    environment: EnvironmentProbe,
    code_commit: str,
    artifact_root_binding: str,
    checkpoint_policy_id: str,
) -> dict[str, Any]:
    for value, field in (
        (code_commit, "code_commit"),
        (artifact_root_binding, "artifact_root_binding"),
        (checkpoint_policy_id, "checkpoint_policy_id"),
    ):
        if not value:
            raise EC1PrelaunchError(f"EXECUTION_CAPSULE_FIELD_MISSING:{field}")
    payload = {
        "schema": "ec1-f0-execution-capsule/v1",
        "generation_id": EC1_GENERATION,
        "prelaunch_report_sha256": report.semantic_sha256,
        "environment_sha256": environment.semantic_sha256,
        "code_commit": code_commit,
        "artifact_root_binding": artifact_root_binding,
        "checkpoint_policy_id": checkpoint_policy_id,
        "authority_effect": "NONE",
    }
    return {**payload, "capsule_sha256": canonical_sha256(payload)}
