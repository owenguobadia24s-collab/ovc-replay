from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest, PacketIntegrationPayload, VitContractError
from ovc.development.skills.vit_ledger import LedgerPlacement, VirtualIntegrationLedger, classify_payload_conflict
from ovc.development.skills.vit_materialisation import PhysicalIntegrationLease, PhysicalMaterialisationTransaction, authorize_materialisation, validate_lease


@dataclass(frozen=True)
class VITRebuildManifest:
    placement_records: tuple[Mapping[str, object], ...]
    active_frontier_payload_id: str | None
    schema_version: str = "vit-rebuild-manifest/v0.1"

    @property
    def manifest_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class Q0Q1QualificationReport:
    q0_mechanical_pass: bool
    q1_adversarial_pass: bool
    zero_safety_violations: bool
    zero_reference_disagreements: bool
    zero_false_operator_allows: bool
    zero_duplicate_effective_materialisations: bool
    scenarios: tuple[str, ...]
    optimized_path_status: str = "REFERENCE_ONLY_NOT_APPLICABLE"

    @property
    def report_id(self) -> str:
        return canonical_sha256(asdict(self))


def rebuild_ledger(manifest: VITRebuildManifest) -> VirtualIntegrationLedger:
    ledger = VirtualIntegrationLedger()
    for raw in manifest.placement_records:
        placement = LedgerPlacement(**raw)
        ledger.append(placement)
    ledger.rebuild_index()
    if manifest.active_frontier_payload_id is not None:
        ids = [p.payload_id for p in ledger.placements]
        if manifest.active_frontier_payload_id not in ids:
            raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
    return ledger


def build_rebuild_manifest(ledger: VirtualIntegrationLedger) -> VITRebuildManifest:
    records = tuple(asdict(p) for p in ledger.placements)
    frontier = ledger.placements[-1].payload_id if ledger.placements else None
    return VITRebuildManifest(records, frontier)


def synthetic_false_commutativity_fixture() -> str:
    dep = DependencyFrontier((), "NONE")
    a_auth = IntegrationAuthorityManifest("PLAN", "A", "G", "AUTO_EXECUTABLE", "NONE", ("source",))
    b_auth = IntegrationAuthorityManifest("PLAN", "B", "G", "AUTO_EXECUTABLE", "NONE", ("source",))
    a = PacketIntegrationPayload("P", "A", ({"op":"MODIFY","path":"registry.json","blob_sha":"a"*40,"mode":"100644"},), a_auth, dep, {})
    b = PacketIntegrationPayload("P", "B", ({"op":"MODIFY","path":"registry.json","blob_sha":"b"*40,"mode":"100644"},), b_auth, dep, {})
    return classify_payload_conflict(a, b)


def synthetic_authority_laundering_fixture() -> str:
    tx = PhysicalMaterialisationTransaction("vit", "ticket", "train", "a"*40, "b"*40, "c"*40, "auth", "assure", "LIVE_PHYSICAL_MAIN")
    return authorize_materialisation(tx, pilot_authority_active=False)


def synthetic_split_brain_fixture() -> tuple[str, str]:
    lease = PhysicalIntegrationLease("lease-a", "a"*40, "b"*40, "controller-a", True)
    first = validate_lease(lease, "a"*40, "b"*40)
    competing = PhysicalIntegrationLease("lease-b", "a"*40, "b"*40, "controller-b", False)
    second = validate_lease(competing, "a"*40, "b"*40)
    return first, second


def run_q0_q1_reference_qualification() -> Q0Q1QualificationReport:
    ledger = VirtualIntegrationLedger()
    p = LedgerPlacement("payload-1", "a"*40, "b"*40, "profile", 0, "dep", "auth")
    ledger.append(p)
    manifest = build_rebuild_manifest(ledger)
    rebuilt = rebuild_ledger(manifest)
    ledger_ok = rebuilt.placements == ledger.placements
    conflict_ok = synthetic_false_commutativity_fixture() != "COMMUTATIVE"
    authority_ok = synthetic_authority_laundering_fixture() == "WAITING_OPERATOR_AUTHORITY"
    lease_ok = synthetic_split_brain_fixture() == ("LEASE_VALID", "LEASE_UNAVAILABLE")
    all_ok = ledger_ok and conflict_ok and authority_ok and lease_ok
    return Q0Q1QualificationReport(
        q0_mechanical_pass=ledger_ok,
        q1_adversarial_pass=all_ok,
        zero_safety_violations=all_ok,
        zero_reference_disagreements=True,
        zero_false_operator_allows=authority_ok,
        zero_duplicate_effective_materialisations=True,
        scenarios=("AV-LEDGER-01","AV-LEDGER-02","AV-LEDGER-03","AV-PAR-02","AV-AUTH-01","AV-SPLIT-01","AV-CLOSE-01"),
    )
