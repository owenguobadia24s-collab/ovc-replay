from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import PacketIntegrationPayload, ProspectiveTreeState, VitContractError


@dataclass(frozen=True)
class IntegrationTicket:
    programme_id: str
    packet_id: str
    payload_id: str
    admitted_sequence: int
    dependencies: tuple[str, ...] = ()
    blocked: bool = False

    @property
    def ticket_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class LedgerPlacement:
    payload_id: str
    predecessor_tree: str
    result_tree: str
    apply_profile: str
    ordinal: int
    dependency_frontier_id: str
    authority_manifest_id: str

    @property
    def placement_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class IntegrationTrainGeneration:
    physical_anchor_tree: str
    generation_ids: tuple[str, ...]
    scheduling_policy: str
    reason: str
    supersedes: str | None = None
    active_materialisation_path: bool = False

    @property
    def train_generation_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class InvalidationDecision:
    affected_payload_id: str
    severity: str
    reason_code: str


class VirtualIntegrationLedger:
    """Append-only prospective placement ledger. No physical write operations live here."""

    def __init__(self) -> None:
        self._placements: list[LedgerPlacement] = []
        self._by_key: dict[tuple[str, str, str], LedgerPlacement] = {}

    @property
    def placements(self) -> tuple[LedgerPlacement, ...]:
        return tuple(self._placements)

    def append(self, placement: LedgerPlacement) -> LedgerPlacement:
        key = (placement.payload_id, placement.predecessor_tree, placement.apply_profile)
        existing = self._by_key.get(key)
        if existing is not None:
            if existing != placement:
                raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
            return existing
        if placement.ordinal < 0:
            raise VitContractError("INPUT_PRECONDITION_MISMATCH")
        self._placements.append(placement)
        self._by_key[key] = placement
        return placement

    def rebuild_index(self) -> None:
        rebuilt: dict[tuple[str, str, str], LedgerPlacement] = {}
        for placement in self._placements:
            key = (placement.payload_id, placement.predecessor_tree, placement.apply_profile)
            if key in rebuilt and rebuilt[key] != placement:
                raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
            rebuilt[key] = placement
        self._by_key = rebuilt


def _paths(payload: PacketIntegrationPayload) -> dict[str, Mapping[str, object]]:
    return {str(change.get("path", "")): change for change in payload.logical_changes}


def classify_payload_conflict(left: PacketIntegrationPayload, right: PacketIntegrationPayload) -> str:
    if left.payload_id == right.payload_id:
        return "COMMUTATIVE"
    lpaths = _paths(left)
    rpaths = _paths(right)
    overlap = set(lpaths).intersection(rpaths)
    if not overlap:
        return "COMMUTATIVE"
    for path in overlap:
        if lpaths[path] != rpaths[path]:
            lop = lpaths[path].get("op")
            rop = rpaths[path].get("op")
            if "DELETE" in {lop, rop}:
                return "MUTUALLY_EXCLUSIVE"
            return "ORDER_SENSITIVE"
    return "SERIAL_REQUIRED"


def safe_bypass(blocked: IntegrationTicket, candidate: IntegrationTicket, payloads: Mapping[str, PacketIntegrationPayload]) -> bool:
    if not blocked.blocked or candidate.blocked:
        return False
    if blocked.packet_id in candidate.dependencies or candidate.packet_id in blocked.dependencies:
        return False
    left = payloads.get(blocked.payload_id)
    right = payloads.get(candidate.payload_id)
    if left is None or right is None:
        return False
    return classify_payload_conflict(left, right) == "COMMUTATIVE"


def schedule_ready(tickets: Sequence[IntegrationTicket], completed_packets: Iterable[str], payloads: Mapping[str, PacketIntegrationPayload]) -> tuple[IntegrationTicket, ...]:
    completed = set(completed_packets)
    ordered = sorted(tickets, key=lambda ticket: ticket.admitted_sequence)
    selected: list[IntegrationTicket] = []
    for ticket in ordered:
        if ticket.blocked:
            continue
        if not set(ticket.dependencies).issubset(completed):
            continue
        prior_blocked = [t for t in ordered if t.admitted_sequence < ticket.admitted_sequence and t.blocked]
        if prior_blocked and not all(safe_bypass(blocked, ticket, payloads) for blocked in prior_blocked):
            continue
        selected.append(ticket)
    return tuple(selected)


def selective_invalidation(*, payload_id: str, predecessor_only: bool = False, assurance_base_changed: bool = False, dependency_changed: bool = False, authority_changed: bool = False) -> InvalidationDecision:
    flags = sum((predecessor_only, assurance_base_changed, dependency_changed, authority_changed))
    if flags != 1:
        raise VitContractError("INPUT_PRECONDITION_MISMATCH")
    if authority_changed:
        return InvalidationDecision(payload_id, "AUTHORITY_REVIEW_REQUIRED", "AUTHORITY_INVALIDATED")
    if dependency_changed:
        return InvalidationDecision(payload_id, "PAYLOAD_REBUILD_REQUIRED", "DEPENDENCY_INVALIDATED")
    if assurance_base_changed:
        return InvalidationDecision(payload_id, "ASSURANCE_RENEWAL_REQUIRED", "ASSURANCE_RENEWAL_REQUIRED")
    return InvalidationDecision(payload_id, "PLACEMENT_RECOMPUTE_ONLY", "PREDECESSOR_MOVED")


def prospective_state(tree_sha: str) -> ProspectiveTreeState:
    return ProspectiveTreeState(tree_sha)
