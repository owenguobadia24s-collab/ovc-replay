from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .models import canonical_hash


ACTIVE_C2_RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
RESEARCH_LINE = "RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1"


@dataclass(frozen=True)
class ProspectiveSourceBinding:
    binding_id: str
    research_line_id: str
    status: str
    active_c2_model_release_id: str
    source_slice_id: str
    source_manifest_sha256: str
    compute_run_id: str
    eligible_data_through_utc: str
    active_triage_started_at_utc: str | None
    qa: Mapping[str, Any]
    release_eligibility: str = "NONE"
    selector_eligibility: str = "NONE"
    r2_publication: str = "DENIED"
    validation_consumption: str = "DENIED"
    exposure_authority: str = "NONE"

    def as_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "research_line_id": self.research_line_id,
            "status": self.status,
            "active_c2_model_release_id": self.active_c2_model_release_id,
            "source_slice_id": self.source_slice_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "compute_run_id": self.compute_run_id,
            "eligible_data_through_utc": self.eligible_data_through_utc,
            "active_triage_started_at_utc": self.active_triage_started_at_utc,
            "qa": dict(self.qa),
            "release_eligibility": self.release_eligibility,
            "selector_eligibility": self.selector_eligibility,
            "r2_publication": self.r2_publication,
            "validation_consumption": self.validation_consumption,
            "exposure_authority": self.exposure_authority,
        }


def build_replay_binding(
    *,
    source_slice_id: str,
    source_manifest_sha256: str,
    compute_run_id: str,
    eligible_data_through_utc: str,
    deterministic_replay: bool,
    lineage_complete: bool,
    gap_state: str,
) -> ProspectiveSourceBinding:
    body = {
        "research_line_id": RESEARCH_LINE,
        "active_c2_model_release_id": ACTIVE_C2_RELEASE,
        "source_slice_id": source_slice_id,
        "source_manifest_sha256": source_manifest_sha256,
        "compute_run_id": compute_run_id,
        "eligible_data_through_utc": eligible_data_through_utc,
    }
    binding_id = f"RPS.BINDING.{canonical_hash(body)[:24]}"
    return ProspectiveSourceBinding(
        binding_id=binding_id,
        research_line_id=RESEARCH_LINE,
        status="ACCEPTED_FOR_REPLAY",
        active_c2_model_release_id=ACTIVE_C2_RELEASE,
        source_slice_id=source_slice_id,
        source_manifest_sha256=source_manifest_sha256,
        compute_run_id=compute_run_id,
        eligible_data_through_utc=eligible_data_through_utc,
        active_triage_started_at_utc=None,
        qa={
            "gap_state": gap_state,
            "deterministic_replay": deterministic_replay,
            "lineage_complete": lineage_complete,
        },
    )


def validate_non_activating(binding: ProspectiveSourceBinding) -> None:
    if binding.status == "ACTIVE_RESEARCH_TRIAGE":
        raise ValueError("RPS-WP1 cannot activate research triage")
    if binding.active_triage_started_at_utc is not None:
        raise ValueError("fixture binding cannot pin a live start")
    if binding.release_eligibility != "NONE" or binding.selector_eligibility != "NONE":
        raise ValueError("prospective binding cannot mutate release or selector authority")
    if binding.r2_publication != "DENIED" or binding.validation_consumption != "DENIED":
        raise ValueError("R2 and Validation remain denied")
