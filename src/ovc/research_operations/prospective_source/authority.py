from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AuthoritySnapshot:
    pd_g4_approved: bool = True
    rps_g4_approved: bool = False
    operator_key_bound: bool = False
    bridge_healthy: bool = False
    write_authority: bool = False
    operation_mode: str = "TIME_GATED_REPLAY"
    source_binding_id: str | None = None
    signing_binding_id: str | None = None
    operator_id: str | None = None
    candidate_source_resolved: bool = False
    active_model_release_id: str = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1"
    eligible_data_through_utc: str | None = None
    evidence_sequence: int = 0

    @property
    def triage_enabled(self) -> bool:
        return all(
            (
                self.pd_g4_approved,
                self.rps_g4_approved,
                self.operator_key_bound,
                self.bridge_healthy,
                self.write_authority,
                self.operation_mode == "LIVE_PROSPECTIVE",
                bool(self.source_binding_id),
                bool(self.signing_binding_id),
                bool(self.operator_id),
            )
        )

    @property
    def live_append_enabled(self) -> bool:
        return self.triage_enabled and self.candidate_source_resolved

    @property
    def authority_label(self) -> str:
        if self.live_append_enabled:
            return "ACTIVE_RESEARCH_TRIAGE_APPEND_ENABLED"
        if self.triage_enabled:
            return "ACTIVE_RESEARCH_TRIAGE"
        if self.operation_mode == "TIME_GATED_REPLAY":
            return "TIME_GATED_REPLAY_NON_EVIDENTIARY"
        if self.rps_g4_approved:
            return "ACTIVE_RESEARCH_TRIAGE_ACTIVATION_INCOMPLETE"
        return "LIVE_APPEND_DISABLED_PENDING_RPS_G4"

    def as_dict(self) -> dict[str, Any]:
        return {
            "authority": self.authority_label,
            "operation_mode": self.operation_mode,
            "pd_g4_approved": self.pd_g4_approved,
            "rps_g4_approved": self.rps_g4_approved,
            "operator_key_bound": self.operator_key_bound,
            "bridge_healthy": self.bridge_healthy,
            "write_authority": self.write_authority,
            "source_binding_id": self.source_binding_id,
            "signing_binding_id": self.signing_binding_id,
            "operator_id": self.operator_id,
            "active_model_release_id": self.active_model_release_id,
            "eligible_data_through_utc": self.eligible_data_through_utc,
            "evidence_sequence": self.evidence_sequence,
            "candidate_source_resolved": self.candidate_source_resolved,
            "triage_enabled": self.triage_enabled,
            "live_append_enabled": self.live_append_enabled,
        }


def authority_from_mapping(value: Mapping[str, Any] | None) -> AuthoritySnapshot:
    if not isinstance(value, Mapping):
        value = {}
    return AuthoritySnapshot(
        pd_g4_approved=bool(value.get("pd_g4_approved", True)),
        rps_g4_approved=bool(value.get("rps_g4_approved", False)),
        operator_key_bound=bool(value.get("operator_key_bound", False)),
        bridge_healthy=bool(value.get("bridge_healthy", False)),
        write_authority=bool(value.get("write_authority", False)),
        operation_mode=str(value.get("operation_mode", "TIME_GATED_REPLAY")),
        source_binding_id=value.get("source_binding_id"),
        signing_binding_id=value.get("signing_binding_id"),
        operator_id=value.get("operator_id"),
        candidate_source_resolved=bool(value.get("candidate_source_resolved", False)),
        active_model_release_id=str(value.get("active_model_release_id", "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")),
        eligible_data_through_utc=value.get("eligible_data_through_utc"),
        evidence_sequence=int(value.get("evidence_sequence", 0)),
    )
