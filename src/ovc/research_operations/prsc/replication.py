from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


PROTECTED_SOURCE_ROLES = frozenset({"DEVELOPMENT", "VALIDATION"})
EXPOSURE_CHANNELS = frozenset({"HUMAN", "ALGORITHM", "SUMMARY"})


class ReplicationFirewallError(ValueError):
    """Raised when WP7 replication/exposure rules fail closed."""


@dataclass(frozen=True)
class DisjointnessDecision:
    state: str
    overlap_refs: tuple[str, ...]


@dataclass(frozen=True)
class ExposureState:
    human_exposed: bool = False
    algorithm_exposed: bool = False
    summary_exposed: bool = False

    @property
    def contaminated(self) -> bool:
        return self.human_exposed or self.algorithm_exposed or self.summary_exposed


def evaluate_disjointness(reference_refs: Iterable[str], replication_refs: Iterable[str]) -> DisjointnessDecision:
    reference = {str(x) for x in reference_refs}
    replication = {str(x) for x in replication_refs}
    if not reference or not replication:
        return DisjointnessDecision("NOT_EVALUABLE", tuple())
    overlap = tuple(sorted(reference.intersection(replication)))
    return DisjointnessDecision("DISJOINT" if not overlap else "OVERLAP_BLOCKED", overlap)


def apply_exposure(state: ExposureState, channel: str) -> ExposureState:
    channel = str(channel).upper()
    if channel not in EXPOSURE_CHANNELS:
        raise ReplicationFirewallError(f"unknown exposure channel: {channel}")
    return ExposureState(
        human_exposed=state.human_exposed or channel == "HUMAN",
        algorithm_exposed=state.algorithm_exposed or channel == "ALGORITHM",
        summary_exposed=state.summary_exposed or channel == "SUMMARY",
    )


def assert_exposure_monotone(previous: ExposureState, current: ExposureState) -> None:
    fields = ("human_exposed", "algorithm_exposed", "summary_exposed")
    rolled_back = [name for name in fields if getattr(previous, name) and not getattr(current, name)]
    if rolled_back:
        raise ReplicationFirewallError(f"irreversible exposure rollback: {','.join(rolled_back)}")


def validate_replication_protocol_pack(record: Mapping[str, object]) -> None:
    required = {
        "replication_protocol_id",
        "candidate_ref",
        "protocol_generation_ref",
        "source_role",
        "identity_unit",
        "disjointness_manifest_ref",
        "method_transport_manifest_ref",
        "population_exposure_ledger_ref",
        "real_execution_allowed",
        "authority_effect",
    }
    missing = sorted(required.difference(record))
    if missing:
        raise ReplicationFirewallError(f"replication protocol missing fields: {missing}")
    if record["real_execution_allowed"] is not False:
        raise ReplicationFirewallError("WP7 does not authorize real replication execution")
    if record["authority_effect"] != "NONE":
        raise ReplicationFirewallError("WP7 authority effect must remain NONE")
    if str(record["source_role"]).upper() in PROTECTED_SOURCE_ROLES:
        raise ReplicationFirewallError("protected source role cannot be consumed by WP7")


def validate_method_transport(record: Mapping[str, object]) -> None:
    state = str(record.get("transport_state", ""))
    refit_allowed = record.get("refit_allowed")
    allowed = {
        "TRANSPORTED_UNCHANGED",
        "TRANSPORTED_WITH_DECLARED_RESTRICTION",
        "REFIT_REQUIRED",
        "NOT_TRANSPORTABLE",
        "NOT_EVALUABLE",
    }
    if state not in allowed:
        raise ReplicationFirewallError(f"invalid transport state: {state}")
    if state == "REFIT_REQUIRED" and refit_allowed is not True:
        raise ReplicationFirewallError("REFIT_REQUIRED must be explicitly declared")
    if state != "REFIT_REQUIRED" and refit_allowed is True:
        raise ReplicationFirewallError("hidden method refit is prohibited")


def validate_validation_reservation(record: Mapping[str, object]) -> None:
    if record.get("validation_role") != "VALIDATION":
        raise ReplicationFirewallError("reservation must be scoped to Validation")
    if record.get("reservation_state") != "RESERVED_UNCONSUMED":
        raise ReplicationFirewallError("Validation must remain reserved and unconsumed")
    for field in ("read_path_present", "source_locator_present", "credential_present", "query_present"):
        if record.get(field) is not False:
            raise ReplicationFirewallError(f"Validation read surface present: {field}")
    if record.get("authority_effect") != "NONE":
        raise ReplicationFirewallError("reservation creates no authority")


def protected_source_reachability_survivors(edges: Sequence[Mapping[str, str]], protected_roles: Iterable[str] = PROTECTED_SOURCE_ROLES) -> tuple[str, ...]:
    protected = {str(x).upper() for x in protected_roles}
    survivors = []
    for edge in edges:
        role = str(edge.get("source_role", "")).upper()
        reachable = str(edge.get("reachable", "false")).lower() == "true"
        if role in protected and reachable:
            survivors.append(str(edge.get("edge_id", "UNNAMED_EDGE")))
    return tuple(sorted(survivors))


def assert_zero_protected_source_reachability(edges: Sequence[Mapping[str, str]]) -> None:
    survivors = protected_source_reachability_survivors(edges)
    if survivors:
        raise ReplicationFirewallError(f"protected-source reachability survivors: {survivors}")
