"""RRSCG StageSpec pack and read-only C2 owner adapter for IROF v0.1.

This module reuses IROF's existing models, planner, authority preflight, cache,
and checkpoint surfaces.  It creates no runner, scheduler, cache, or checkpoint
plane and grants no execution authority.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from ovc.opt_b.c2_vnext.owner_read_surface import (
    HANDOFF_ID,
    INSTRUMENT,
    LOCAL_CLOCK,
    OWNER_AUTHORITY_ID,
    OWNER_GENERATION_ID,
    OWNER_PACKAGE_ID,
    OWNER_PACKAGE_SHA256,
    PARENT_CLOCK,
    SIDES,
    SNAPSHOT_SCHEMA,
    canonical_sha256,
    validate_source_binding,
)
from ovc.research_orchestration.adapters import (
    AdapterEstimate,
    AdapterExecution,
    AdapterPreflight,
    AdapterVerification,
)
from ovc.research_orchestration.authority import (
    AuthorityRequirementRegistry,
    AuthorityRequirementSpec,
)
from ovc.research_orchestration.models import (
    AuthorityBinding,
    PipelineProfile,
    PopulationSpec,
    ResearchRunSpec,
    StageDependency,
    StageInvocation,
    StageSpec,
)

from .d10 import D10_PACKAGE_SHA256
from .d9 import D9_PACKAGE_SHA256
from .kernel import SOURCE_ARCHIVE_SHA256

RRSCG_OWNER_ADAPTER_ID = "RRSCG.C2.OWNER.STRUCTURAL.SNAPSHOT.ADAPTER.v0.1"
RRSCG_OWNER_INPUT_SCHEMA = "ovc-rrscg-owner-input/v0.1"
RRSCG_PROFILE_ID = "RRSCG_CORE_INACTIVE_SINGLE_CLOCK"
RRSCG_C2_READ_REQUIREMENT = "RRSCG_C2_OWNER_SNAPSHOT_READ"
RRSCG_CORE_REQUIREMENT = "RRSCG_CORE_INACTIVE_CONSTRUCTION"


class RRSCGIROFError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class RRSCGOwnerInput:
    snapshot_id: str
    owner_generation_id: str
    owner_snapshot: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema": RRSCG_OWNER_INPUT_SCHEMA,
            "adapter_id": RRSCG_OWNER_ADAPTER_ID,
            "snapshot_id": self.snapshot_id,
            "owner_generation_id": self.owner_generation_id,
            "owner_snapshot": copy.deepcopy(dict(self.owner_snapshot)),
            "flattening": "NONE_OWNER_RECORDS_PRESERVED",
            "scientific_inference": "NONE",
        }
        return {**body, "content_id": canonical_sha256(body)}


def adapt_owner_snapshot(snapshot: Mapping[str, Any]) -> RRSCGOwnerInput:
    """Validate and wrap one exact current-owner snapshot without flattening it."""
    value = copy.deepcopy(dict(snapshot))
    required = {
        "schema", "snapshot_id", "handoff_id", "owner_authority_id",
        "owner_generation_id", "owner_package_id", "owner_package_sha256",
        "source_binding", "instrument", "side", "clocks", "observation_id",
        "interval_start", "interval_end", "effective_time", "first_valid_time",
        "target_eligible", "continuity", "projection_eligibility",
        "component_refs", "owner_records", "component_availability", "authority",
    }
    missing = sorted(required.difference(value))
    if missing:
        raise RRSCGIROFError("RRSCG_OWNER_SNAPSHOT_FIELDS_MISSING", ",".join(missing))
    exact = {
        "schema": SNAPSHOT_SCHEMA,
        "handoff_id": HANDOFF_ID,
        "owner_authority_id": OWNER_AUTHORITY_ID,
        "owner_generation_id": OWNER_GENERATION_ID,
        "owner_package_id": OWNER_PACKAGE_ID,
        "owner_package_sha256": OWNER_PACKAGE_SHA256,
        "instrument": INSTRUMENT,
    }
    for field, expected in exact.items():
        if value.get(field) != expected:
            raise RRSCGIROFError("RRSCG_OWNER_SNAPSHOT_BINDING_MISMATCH", field)
    if value["side"] not in SIDES:
        raise RRSCGIROFError("RRSCG_OWNER_SNAPSHOT_SIDE_DENIED", str(value["side"]))
    if value["clocks"] != {"local": LOCAL_CLOCK, "parent": PARENT_CLOCK}:
        raise RRSCGIROFError("RRSCG_OWNER_SNAPSHOT_CLOCK_BINDING_MISMATCH", str(value["clocks"]))

    binding = validate_source_binding(value["source_binding"])
    if (
        binding["instrument"] != value["instrument"]
        or binding["side"] != value["side"]
        or binding["local_clock"] != value["clocks"]["local"]
        or binding["parent_clock"] != value["clocks"]["parent"]
    ):
        raise RRSCGIROFError("RRSCG_OWNER_SOURCE_SCOPE_MISMATCH", str(value["snapshot_id"]))
    if value["effective_time"] != value["interval_end"]:
        raise RRSCGIROFError("RRSCG_OWNER_EFFECTIVE_TIME_MISMATCH", str(value["observation_id"]))
    if value["first_valid_time"] != value["interval_end"]:
        raise RRSCGIROFError("RRSCG_OWNER_FVT_MISMATCH", str(value["observation_id"]))

    authority = value["authority"]
    expected_authority = {
        "read_only": True,
        "owner_state_write": "DENIED",
        "new_source_authority": "DENIED",
        "validation": "LOCKED_UNCONSUMED",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
        "agent_write": "NONE",
    }
    if authority != expected_authority:
        raise RRSCGIROFError("RRSCG_OWNER_AUTHORITY_ENVELOPE_MISMATCH", str(value["snapshot_id"]))

    declared_id = str(value.pop("snapshot_id"))
    if canonical_sha256(value) != declared_id:
        raise RRSCGIROFError("RRSCG_OWNER_SNAPSHOT_ID_MISMATCH", declared_id)
    value["snapshot_id"] = declared_id
    return RRSCGOwnerInput(declared_id, OWNER_GENERATION_ID, value)


def rrscg_stage_specs() -> tuple[StageSpec, ...]:
    owner = StageSpec(
        stage_id="RRSCG_C2_OWNER_ADAPTER",
        stage_version="0.1",
        stage_kind="CURRENT_OWNER_READ_ADAPTER",
        implementation_identity="ovc.research_operations.rrscg.irof:adapt_owner_snapshot",
        contract_identity="RRSCG.C2.OWNER.IROF.TRANSPORT.v0.1",
        schema_identity=RRSCG_OWNER_INPUT_SCHEMA,
        input_types=("C2_OWNER_STRUCTURAL_SNAPSHOT_READ_V0_1",),
        output_types=("RRSCG_OWNER_INPUT_V0_1",),
        authority_requirements=(RRSCG_C2_READ_REQUIREMENT, RRSCG_CORE_REQUIREMENT),
        deterministic_mode="EXACT",
        checkpoint_capability="STAGE",
        cache_capability="SEMANTIC",
        qa_requirements=("OWNER_SNAPSHOT_ID_VERIFIED", "NO_FLATTENING", "FVT_PRESERVED"),
        adapter_identity=RRSCG_OWNER_ADAPTER_ID,
    )
    r2 = StageSpec(
        stage_id="RRSCG_R2_KERNEL",
        stage_version="0.1",
        stage_kind="INACTIVE_SCIENTIFIC_KERNEL",
        implementation_identity="ovc.research_operations.rrscg.kernel",
        contract_identity="OVC-EML-GRAMMAR-0003-RRSCG-ALGORITHM-0.1-R2",
        schema_identity="RRSCG_R2_CONSTRAINT_EVENT_REPOSITORY_NATIVE_v1",
        input_types=("RRSCG_OWNER_INPUT_V0_1",),
        output_types=("RRSCG_R2_EVENT_WITH_OWNER_EVIDENCE_V0_1",),
        dependencies=(StageDependency("RRSCG_C2_OWNER_ADAPTER", "REQUIRED", ("RRSCG_OWNER_INPUT_V0_1",)),),
        authority_requirements=(RRSCG_CORE_REQUIREMENT,),
        pack_requirements=(SOURCE_ARCHIVE_SHA256,),
        checkpoint_capability="STAGE",
        cache_capability="SEMANTIC",
        qa_requirements=("R2_EXACT_SOURCE_BINDING", "R2_ABSTENTION_PRESERVED"),
        adapter_identity="RRSCG.IROF.R2.v0.1",
    )
    d9 = StageSpec(
        stage_id="RRSCG_D9_OBSERVER",
        stage_version="0.1",
        stage_kind="INACTIVE_OBSERVER_FACULTY",
        implementation_identity="ovc.research_operations.rrscg.d9",
        contract_identity="OVC-EML-GRAMMAR-0003-RRSCG-DYNAMICS-ALGORITHM-0.2-D9",
        schema_identity="RRSCG_D9_STATE_MOTION_REPOSITORY_NATIVE_v1",
        input_types=("RRSCG_R2_EVENT_WITH_OWNER_EVIDENCE_V0_1",),
        output_types=("RRSCG_D9_OBSERVER_STATE_V0_1",),
        dependencies=(StageDependency("RRSCG_R2_KERNEL", "REQUIRED", ("RRSCG_R2_EVENT_WITH_OWNER_EVIDENCE_V0_1",)),),
        authority_requirements=(RRSCG_CORE_REQUIREMENT,),
        pack_requirements=(D9_PACKAGE_SHA256,),
        checkpoint_capability="STAGE",
        cache_capability="SEMANTIC",
        qa_requirements=("D9_REFERENCE_FACULTY_PRESERVED", "CROSS_SEGMENT_MOTION_DENIED"),
        adapter_identity="RRSCG.IROF.D9.v0.1",
    )
    d10 = StageSpec(
        stage_id="RRSCG_D10_REDUCER",
        stage_version="0.1",
        stage_kind="INACTIVE_REDUCER_SUBCOMPONENT",
        implementation_identity="ovc.research_operations.rrscg.d10:reduce_d9_state",
        contract_identity="OVC-EML-GRAMMAR-0003-RRSCG-DYNAMICS-ALGORITHM-0.2-D10",
        schema_identity="RRSCG_D10_REDUCER_RECORD_v0.1",
        input_types=("RRSCG_D9_OBSERVER_STATE_V0_1",),
        output_types=("RRSCG_D10_REDUCER_RECORD_V0_1",),
        dependencies=(StageDependency("RRSCG_D9_OBSERVER", "REQUIRED", ("RRSCG_D9_OBSERVER_STATE_V0_1",)),),
        authority_requirements=(RRSCG_CORE_REQUIREMENT,),
        pack_requirements=(D10_PACKAGE_SHA256,),
        checkpoint_capability="STAGE",
        cache_capability="SEMANTIC",
        qa_requirements=("D10_REDUCER_INTERFACE_ONLY", "D9_CONTROL_RECONCILED"),
        adapter_identity="RRSCG.IROF.D10.v0.1",
    )
    return owner, r2, d9, d10


def rrscg_pipeline_profile() -> PipelineProfile:
    return PipelineProfile(
        RRSCG_PROFILE_ID,
        "0.1",
        tuple(stage.stage_id for stage in rrscg_stage_specs()),
        ("RRSCG_D9_OBSERVER_STATE_V0_1", "RRSCG_D10_REDUCER_RECORD_V0_1"),
        prerequisites=("RRSCG-CORE-G3-D10-CONFORMANCE:PASS_AND_INTEGRATED",),
        authority_policy_ref="RRSCG_EXISTING_OWNER_AND_INACTIVE_CONSTRUCTION_AUTHORITY_ONLY",
        observability_requirements=("CONTENT_ID", "CHECKPOINT_CONTENT_HASH", "SOURCE_FVT"),
    )


def rrscg_authority_registry() -> AuthorityRequirementRegistry:
    return AuthorityRequirementRegistry((
        AuthorityRequirementSpec(
            RRSCG_C2_READ_REQUIREMENT,
            "OVC-ACTIVE-STACK-RECLASSIFICATION-v0.1",
            "C2-OWNER-READ-HANDOFF-G1",
            "CURRENT_OWNER_STRUCTURAL_SNAPSHOT_READ",
            OWNER_GENERATION_ID,
            required_scope={"instrument": "GBPUSD", "local_clock": "15M", "parent_clock": "2H_A_L"},
        ),
        AuthorityRequirementSpec(
            RRSCG_CORE_REQUIREMENT,
            "OVC-LSIAC-v0.1",
            "LSIAC-G-RRSCG-CORE-ACCESSION-AUTHORITY_AFTER_WP0_SOURCE_BINDING",
            "INACTIVE_CAPABILITY_CONSTRUCTION",
            "OVC-RRSCG-CORE-ACCESSION-CONFORMANCE-PLAN-0.1",
            required_scope={"capability_state": "INACTIVE", "validation": "LOCKED_UNCONSUMED"},
        ),
    ))


def rrscg_authority_bindings() -> tuple[AuthorityBinding, ...]:
    return (
        AuthorityBinding(
            "RRSCG.BINDING.C2_OWNER_READ.v0.1",
            "OVC-ACTIVE-STACK-RECLASSIFICATION-v0.1",
            "C2-OWNER-READ-HANDOFF-G1",
            "CURRENT_OWNER_STRUCTURAL_SNAPSHOT_READ",
            OWNER_GENERATION_ID,
            {"instrument": "GBPUSD", "local_clock": "15M", "parent_clock": "2H_A_L"},
            "ALLOW",
            "ACTIVE",
            "registries/opt_b/c2/vnext/C2_OWNER_STRUCTURAL_SNAPSHOT_READ_AUTHORITY_v0_1.json",
            source_decision_hash="2269494d7871ce34fbe67a0fc826c1f7ad15d8872a94cbbb492726ef130113c4",
        ),
        AuthorityBinding(
            "RRSCG.BINDING.INACTIVE_CONSTRUCTION.v0.1",
            "OVC-LSIAC-v0.1",
            "LSIAC-G-RRSCG-CORE-ACCESSION-AUTHORITY_AFTER_WP0_SOURCE_BINDING",
            "INACTIVE_CAPABILITY_CONSTRUCTION",
            "OVC-RRSCG-CORE-ACCESSION-CONFORMANCE-PLAN-0.1",
            {"capability_state": "INACTIVE", "validation": "LOCKED_UNCONSUMED"},
            "ALLOW",
            "APPROVED",
            "docs/programmes/lsiac-v0-1/rrscg-core-accession-authority/LSIAC_G_RRSCG_CORE_ACCESSION_AUTHORITY_OPERATOR_DECISION_v0_1.json",
            source_decision_hash="6f230474b52af69eb117ab1f25e327d814622d37349bbb9078cb4d70ec9b1239",
        ),
    )


class RRSCGOwnerStageAdapter:
    stage_id = "RRSCG_C2_OWNER_ADAPTER"

    def preflight(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterPreflight:
        reasons = []
        if stage_spec.stage_id != self.stage_id or invocation.stage_id != self.stage_id:
            reasons.append("RRSCG_IROF_STAGE_ID_MISMATCH")
        if envelope.get("population_mode", "SYNTHETIC_FIXTURE") not in {"SYNTHETIC_FIXTURE", "SYNTHETIC_GENERATED"}:
            reasons.append("RRSCG_REAL_SOURCE_RUN_NOT_AUTHORISED")
        try:
            adapt_owner_snapshot(envelope.get("owner_snapshot", {}))
        except Exception:
            reasons.append("RRSCG_OWNER_SNAPSHOT_INVALID")
        return AdapterPreflight(self.stage_id, not reasons, tuple(sorted(set(reasons))))

    def estimate(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterEstimate:
        return AdapterEstimate(self.stage_id, work_units=1, estimated_bytes=None, estimator_id="RRSCG_OWNER_SNAPSHOT_COUNT_v0.1")

    def execute(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any]) -> AdapterExecution:
        preflight = self.preflight(stage_spec, invocation, envelope)
        if not preflight.allowed:
            raise RRSCGIROFError(preflight.reason_codes[0], self.stage_id)
        adapted = adapt_owner_snapshot(envelope["owner_snapshot"]).to_dict()
        return AdapterExecution(
            self.stage_id,
            (adapted["content_id"],),
            scientific_payload_hash=adapted["snapshot_id"],
            checkpoint_ref=envelope.get("checkpoint_ref"),
        )

    def resume(self, stage_spec: StageSpec, invocation: StageInvocation, envelope: Mapping[str, Any], checkpoint_ref: str) -> AdapterExecution:
        merged = dict(envelope)
        merged["checkpoint_ref"] = checkpoint_ref
        return self.execute(stage_spec, invocation, merged)

    def verify(self, stage_spec: StageSpec, invocation: StageInvocation, result: AdapterExecution) -> AdapterVerification:
        reasons = []
        if result.stage_id != self.stage_id:
            reasons.append("RRSCG_IROF_STAGE_ID_MISMATCH")
        if len(result.output_refs) != 1 or not result.scientific_payload_hash:
            reasons.append("RRSCG_OWNER_ADAPTER_IDENTITY_MISSING")
        return AdapterVerification(self.stage_id, not reasons, tuple(reasons))


def build_rrscg_run_spec(population: PopulationSpec) -> ResearchRunSpec:
    if population.population_mode not in {"SYNTHETIC_FIXTURE", "SYNTHETIC_GENERATED"}:
        raise RRSCGIROFError("RRSCG_REAL_SOURCE_RUN_NOT_AUTHORISED", population.population_id)
    if population.instrument != "GBPUSD" or population.price_side not in SIDES or population.clock_lattice != "15M":
        raise RRSCGIROFError("RRSCG_POPULATION_SCOPE_OUTSIDE_CURRENT_OWNER", population.population_id)
    if population.validation_access_state != "LOCKED_UNCONSUMED" or population.role == "VALIDATION":
        raise RRSCGIROFError("RRSCG_VALIDATION_CONSUMPTION_DENIED", population.population_id)
    profile = rrscg_pipeline_profile()
    return ResearchRunSpec(
        population,
        profile,
        rrscg_stage_specs(),
        rrscg_authority_bindings(),
        pack_bindings={
            "RRSCG_R2": SOURCE_ARCHIVE_SHA256,
            "RRSCG_D9": D9_PACKAGE_SHA256,
            "RRSCG_D10": D10_PACKAGE_SHA256,
        },
        chronology_policy_id="C2_OWNER_EFFECTIVE_AND_FIRST_VALID_TIME_DISTINCT_v0.1",
        comparability_domain_id="GBPUSD_BID_ASK_15M_WITH_2H_A_L_PARENT_CURRENT_OWNER_ONLY",
        context_role_identity="RRSCG_DESCRIPTIVE_DEVELOPMENT_ONLY",
    )
