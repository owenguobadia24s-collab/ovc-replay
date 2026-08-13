from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .models import PipelineProfile, StageDependency, StageSpec
from .planner import CanonicalPlan, build_plan
from .registry import build_registry_snapshot
from .serialization import logical_sha256


@dataclass(frozen=True)
class MetadataOnlyExtensionAdapter:
    adapter_id: str = "IROF.WP11.METADATA_ONLY_EXTENSION.v0_1"

    def execute(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        result = {
            "extension_stage_id": "FUTURE_METADATA_ONLY",
            "source_refs": sorted(str(item) for item in payload.get("source_refs", ())),
            "metadata": dict(payload.get("metadata", {})),
            "scientific_effect": "NONE",
            "authority_effect": "NONE",
        }
        result["logical_hash"] = logical_sha256(result)
        return result


def build_extension_plan() -> CanonicalPlan:
    base = StageSpec(
        stage_id="RESEARCH_OPERATIONS",
        stage_version="0.1",
        stage_kind="READ_ONLY_EVIDENCE",
        implementation_identity="irof-existing:research-operations",
        contract_identity="irof-existing:research-operations-contract",
        schema_identity="irof-existing:research-operations-schema",
        input_types=(),
        output_types=("RESEARCH_OPERATIONS_EVIDENCE",),
        adapter_identity="IROF.CURRENT.RESEARCH_OPERATIONS",
    )
    extension = StageSpec(
        stage_id="FUTURE_METADATA_ONLY",
        stage_version="0.1",
        stage_kind="SYNTHETIC_EXTENSION_PROOF",
        implementation_identity="irof-wp11:metadata-only-extension",
        contract_identity="irof-wp11:metadata-only-contract",
        schema_identity="irof-wp11:metadata-only-schema",
        input_types=(),
        output_types=("FUTURE_METADATA_ONLY_EVIDENCE",),
        dependencies=(StageDependency("RESEARCH_OPERATIONS", "REQUIRED", ("RESEARCH_OPERATIONS_EVIDENCE",)),),
        adapter_identity="IROF.WP11.METADATA_ONLY_EXTENSION.v0_1",
    )
    profile = PipelineProfile(
        "IROF_WP11_EXTENSION_PROOF",
        "0.1",
        ("RESEARCH_OPERATIONS", "FUTURE_METADATA_ONLY"),
        required_terminal_outputs=("FUTURE_METADATA_ONLY_EVIDENCE",),
    )
    snapshot = build_registry_snapshot(stage_specs=(base, extension), profiles=(profile,))
    return build_plan(snapshot=snapshot, profile_id=profile.profile_id)


def preflight_real_population(*, main_sha: str, c2e_state: Mapping[str, Any], plan: CanonicalPlan) -> dict[str, Any]:
    authority = dict(c2e_state.get("authority", {}))
    warnings = set(str(item) for item in c2e_state.get("warnings", ()))
    population_frozen = "REPLACEMENT_REAL_SOURCE_FRAME_POPULATION_NOT_YET_FROZEN" not in warnings
    run_authorised = authority.get("real_source_replay") not in {None, "DENIED_PENDING_FRESH_RUN_AUTH"}
    active_boundary = authority.get("active_boundary_pack") not in {None, "NONE"}

    blocked_stage = "C2E_V0_2"
    descendants = plan.blocked_descendants((blocked_stage,))
    blockers: list[str] = []
    if not population_frozen:
        blockers.append("C2E_REPLACEMENT_REAL_SOURCE_FRAME_POPULATION_NOT_FROZEN")
    if not active_boundary:
        blockers.append("C2E_ACTIVE_BOUNDARY_PACK_NONE")
    if not run_authorised:
        blockers.append("C2E2_G6_FRESH_RUN_AUTH_REQUIRED")
    if authority.get("replacement_resource_envelope_manifest_token") == "AUTHORIZED_CANDIDATE_PREPARATION_AFTER_EXACT_FRAME_POPULATION_FREEZE":
        blockers.append("C2E_REPLACEMENT_RESOURCE_ENVELOPE_AND_RUN_TOKEN_NOT_YET_MATERIALIZED")

    readiness = "REAL_RUN_READY_BUT_NOT_AUTHORISED" if population_frozen and active_boundary and not run_authorised else "REAL_RUN_NOT_READY_AND_NOT_AUTHORISED"
    payload = {
        "schema": "ovc-irof-real-preflight/v0.1",
        "main_sha": main_sha,
        "requested_population": "GBPUSD_JUNE_2026_C2E_REPLACEMENT_REAL_SOURCE_FRAME_POPULATION",
        "population_binding": "UNRESOLVED_UNTIL_C2E_REPLACEMENT_FRAME_POPULATION_FREEZE" if not population_frozen else "FROZEN_BY_OWNER",
        "source_release_binding": "OWNER_C2E_REPLACEMENT_RUN_OBJECTS_REQUIRED",
        "profile": plan.profile_id,
        "ordered_stage_ids": list(plan.ordered_stage_ids),
        "execution_status": "NOT_AUTHORISED",
        "readiness_disposition": readiness,
        "blocked_stage_id": blocked_stage,
        "blocked_descendants": list(descendants),
        "blockers": sorted(blockers),
        "cache_preflight": "IROF_SEMANTIC_CACHE_INFRASTRUCTURE_AVAILABLE_NO_REAL_LOOKUP_PERFORMED",
        "workload_preflight": "PAIR_AND_CONFIGURATION_ESTIMATE_DEFERRED_UNTIL_EXACT_OWNER_POPULATION_FREEZE",
        "space_preflight": "RESOURCE_ENVELOPE_NOT_MATERIALIZED_BY_C2E_OWNER",
        "protected_data_accessed": False,
        "owner_gate": "C2E2-G6-RUN-AUTH",
        "authority_effect": "NONE",
    }
    payload["logical_hash"] = logical_sha256(payload)
    return payload
