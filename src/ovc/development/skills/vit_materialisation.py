from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Mapping

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError, assert_tree_equivalent


@dataclass(frozen=True)
class PhysicalMaterialisationTransaction:
    vit_generation_id: str
    ticket_id: str
    train_generation_id: str
    expected_predecessor_commit: str
    expected_predecessor_tree: str
    expected_result_tree: str
    authority_frontier_id: str
    assurance_frontier_id: str
    materialisation_profile: str
    attempt: int = 1

    def __post_init__(self) -> None:
        if self.materialisation_profile not in {"ISOLATED_REHEARSAL", "LIVE_PHYSICAL_MAIN"}:
            raise VitContractError("unknown materialisation profile")
        if self.attempt < 1:
            raise VitContractError("invalid attempt")

    @property
    def transaction_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class PhysicalIntegrationLease:
    lease_id: str
    expected_predecessor_commit: str
    expected_predecessor_tree: str
    holder: str
    active: bool = True


@dataclass(frozen=True)
class PhysicalMaterialisationReceipt:
    transaction_id: str
    observed_commit: str
    observed_tree: str
    expected_result_tree: str
    equality: bool
    outcome: str

    @property
    def receipt_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class PacketCompletionReceipt:
    programme_id: str
    packet_id: str
    implementation_ref: str
    qa_ref: str
    gate_decision_ref: str
    payload_id: str
    vit_generation_id: str
    materialisation_receipt_id: str
    next_packet: str | None

    @property
    def receipt_id(self) -> str:
        return canonical_sha256(asdict(self))


class ReceiptStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _put_payload(self, payload: Mapping[str, object], receipt_id: str) -> Path:
        path = self.root / f"{receipt_id}.json"
        encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
        if path.exists():
            if path.read_text(encoding="utf-8") != encoded:
                raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
            return path
        path.write_text(encoded, encoding="utf-8")
        return path

    def put(self, receipt: object, receipt_id: str) -> Path:
        if isinstance(receipt, Mapping):
            return self.put_record(receipt, receipt_id)
        if isinstance(receipt, PacketCompletionReceipt) and receipt.programme_id == "OVC-DSAI-VIT-v0.3":
            raise VitContractError("DEVOBS_COMPLETION_ATTACHMENT_REQUIRED")
        return self._put_payload(asdict(receipt), receipt_id)

    def put_record(self, receipt: Mapping[str, object], receipt_id: str) -> Path:
        """Persist an already-canonical mapping without changing its logical identity."""
        return self._put_payload(receipt, receipt_id)

    def put_completion_with_devobs(
        self,
        completion: PacketCompletionReceipt,
        development_latency_receipt: Mapping[str, object],
    ) -> Mapping[str, str]:
        """Persist completion + canonical DEVOBS receipt + binding as one required bundle."""
        from ovc.development.dsai3v_completion_observability import validate_completion_attachment

        attachment = validate_completion_attachment(
            programme_id=completion.programme_id,
            packet_id=completion.packet_id,
            completion_receipt_id=completion.receipt_id,
            development_latency_receipt=development_latency_receipt,
        )
        devobs_id = str(development_latency_receipt["record_id"])
        self._put_payload(asdict(completion), completion.receipt_id)
        self.put_record(development_latency_receipt, devobs_id)
        attachment_record = attachment.to_record()
        self.put_record(attachment_record, attachment.attachment_id)
        return {
            "completion_receipt_id": completion.receipt_id,
            "development_latency_receipt_id": devobs_id,
            "attachment_id": attachment.attachment_id,
        }

    @staticmethod
    def packet_completion_generation_index_key(
        *, programme_id: str, packet_id: str, vit_generation_id: str
    ) -> str:
        """Return the unambiguous generation-qualified completion lookup key."""
        identity = json.dumps(
            [programme_id, packet_id, vit_generation_id],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return f"packet_completion_generation:{identity}"

    def rebuild_index(self) -> Mapping[str, str]:
        index: dict[str, str] = {}
        for path in sorted(self.root.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            keys: list[str] = []
            if raw.get("transaction_id"):
                keys.append(f"transaction_id:{raw['transaction_id']}")
            if raw.get("gate_decision_ref") and raw.get("payload_id") and raw.get("packet_id"):
                keys.append(
                    self.packet_completion_generation_index_key(
                        programme_id=str(raw.get("programme_id", "")),
                        packet_id=str(raw["packet_id"]),
                        vit_generation_id=str(raw.get("vit_generation_id", "")),
                    )
                )
            if raw.get("schema") == "ovc-dsai3v-completion-observability-attachment/v1":
                for field in ("completion_receipt_id", "development_latency_receipt_id"):
                    if raw.get(field):
                        keys.append(f"{field}:{raw[field]}")
            for key in keys:
                if key in index and index[key] != path.name:
                    raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
                index[key] = path.name
        return index


def authorize_materialisation(transaction: PhysicalMaterialisationTransaction, *, pilot_authority_active: bool) -> str:
    if transaction.materialisation_profile == "LIVE_PHYSICAL_MAIN" and not pilot_authority_active:
        return "WAITING_OPERATOR_AUTHORITY"
    if transaction.materialisation_profile == "ISOLATED_REHEARSAL":
        return "ALLOW_ISOLATED_REHEARSAL"
    return "ALLOW_LIVE_SERIALIZED_GATEWAY"


def validate_lease(lease: PhysicalIntegrationLease, actual_commit: str, actual_tree: str) -> str:
    if not lease.active:
        return "LEASE_UNAVAILABLE"
    if lease.expected_predecessor_commit != actual_commit or lease.expected_predecessor_tree != actual_tree:
        return "PREDECESSOR_MOVED"
    return "LEASE_VALID"


def materialisation_receipt(transaction: PhysicalMaterialisationTransaction, observed_commit: str, observed_tree: str) -> PhysicalMaterialisationReceipt:
    try:
        assert_tree_equivalent(transaction.expected_result_tree, observed_tree)
    except VitContractError:
        return PhysicalMaterialisationReceipt(transaction.transaction_id, observed_commit, observed_tree, transaction.expected_result_tree, False, "POST_WRITE_TREE_MISMATCH")
    return PhysicalMaterialisationReceipt(transaction.transaction_id, observed_commit, observed_tree, transaction.expected_result_tree, True, "MATERIALISED_EQUIVALENT")


def recover_unknown_write(transaction: PhysicalMaterialisationTransaction, observed_commit: str, observed_tree: str) -> str:
    if observed_tree == transaction.expected_predecessor_tree and observed_commit == transaction.expected_predecessor_commit:
        return "WRITE_NOT_EFFECTIVE_RETRYABLE"
    if observed_tree == transaction.expected_result_tree:
        return "WRITE_EFFECTIVE_RECEIPT_RECOVERY_REQUIRED"
    return "POST_WRITE_STATE_UNKNOWN"
