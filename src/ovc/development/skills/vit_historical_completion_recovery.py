from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from ovc.development.dsai3v_completion_observability import (
    build_canonical_completion_latency_receipt,
    validate_completion_attachment,
)
from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_completion_runtime import (
    SIQ_PHYSICAL_GATEWAY,
    VIT_PHYSICAL_CONTROLLER,
)
from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_materialisation import ReceiptStore


DECISION_SCHEMA = "ovc-vit-historical-completion-recovery-decision/v1"
ATTEMPT_SCHEMA = "ovc-vit-historical-completion-recovery-attempt/v1"
EFFECTIVE_WRITE_SCHEMA = "ovc-vit-historical-effective-write-receipt/v1"
COMPLETION_SCHEMA = "ovc-vit-historical-packet-completion-receipt/v1"
PROOF_SCHEMA = "ovc-vit-historical-completion-recovery-proof/v1"

RECOVERY_CLASS = "HISTORICAL_EFFECTIVE_WRITE_COMPLETION_WITH_MISSING_PREWRITE_FREEZE"
PREWRITE_FREEZE_STATUS = "ABSENT_NOT_EMITTED"
AUTHORITY_DELTA = "NONE_COMPLETION_RECOVERY_ONLY"
PRECEDENT_EFFECT = "NONE_SINGLE_USE"

AUTHORIZED_PR = 1047
AUTHORIZED_HEAD = "3e86c67eb6d8891acda2b2de8f930542fcd750ab"
AUTHORIZED_MERGE = "911cac359aa0d23b981be15edae473b7d2b7d55b"
AUTHORIZED_PIP = "f88dd554f12639e2cc0b3a5d4296663fc8161654ca1c6b9ff0eec1d2c46852cf"
AUTHORIZED_GENERATION = "ef7fb341f6b442ddf638a65e688a7c69d535fc866bf186d035a147e560655a7f"
AUTHORIZED_PREDECESSOR_TREE = "0c631bcb656f0e82a926a371b8307e82b74b0298"
AUTHORIZED_RESULT_TREE = "ce04f93eedf5f9c8c55914cb00ba66a6f8b17ee3"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_PROHIBITED_ORIGINAL_FIELDS = {
    "materialisation_transaction_id",
    "transaction_id",
    "ticket_id",
    "assurance_frontier_id",
    "original_attempt",
    "original_timing",
    "original_retry",
    "original_telemetry",
}


def _record(logical: Mapping[str, Any], *, id_field: str, role: str) -> dict[str, Any]:
    value = dict(logical)
    value[id_field] = canonical_sha256(value, role=role)
    return value


def _write_content_addressed(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
        return
    path.write_text(encoded, encoding="utf-8")


def _assert_no_original_pmt_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        prohibited = _PROHIBITED_ORIGINAL_FIELDS.intersection(value)
        if prohibited:
            raise VitContractError(
                "HISTORICAL_RECOVERY_ORIGINAL_PMT_INFERENCE_PROHIBITED:"
                + ",".join(sorted(prohibited))
            )
        for nested in value.values():
            _assert_no_original_pmt_fields(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _assert_no_original_pmt_fields(nested)


def validate_historical_recovery_decision(record: Mapping[str, Any]) -> Mapping[str, Any]:
    _assert_no_original_pmt_fields(record)
    expected = {
        "schema": DECISION_SCHEMA,
        "operator_decision": "PASS_SINGLE_USE_FORWARD_ONLY_EXCEPTION",
        "pr_number": AUTHORIZED_PR,
        "head_sha": AUTHORIZED_HEAD,
        "physical_merge_sha": AUTHORIZED_MERGE,
        "pip_id": AUTHORIZED_PIP,
        "vit_generation_id": AUTHORIZED_GENERATION,
        "predecessor_tree": AUTHORIZED_PREDECESSOR_TREE,
        "admitted_result_tree": AUTHORIZED_RESULT_TREE,
        "observed_physical_tree": AUTHORIZED_RESULT_TREE,
        "prewrite_freeze_status": PREWRITE_FREEZE_STATUS,
        "recovery_class": RECOVERY_CLASS,
        "authority_delta": AUTHORITY_DELTA,
        "precedent_effect": PRECEDENT_EFFECT,
    }
    for field, value in expected.items():
        if record.get(field) != value:
            raise VitContractError(f"HISTORICAL_RECOVERY_DECISION_{field.upper()}_INVALID")
    if record.get("normal_prospective_requirement") != "PMT_AND_PREWRITE_FREEZE_REQUIRED_UNCHANGED":
        raise VitContractError("HISTORICAL_RECOVERY_PROSPECTIVE_REQUIREMENT_WEAKENED")
    if record.get("authority_effect") != "NONE":
        raise VitContractError("HISTORICAL_RECOVERY_AUTHORITY_EFFECT_INVALID")
    if not _SHA64.fullmatch(str(record.get("source_census_id", ""))):
        raise VitContractError("HISTORICAL_RECOVERY_SOURCE_CENSUS_INVALID")
    decision_id = str(record.get("recovery_decision_id", ""))
    logical = {key: value for key, value in record.items() if key != "recovery_decision_id"}
    expected_id = canonical_sha256(logical, role="DSAI3V_HISTORICAL_COMPLETION_RECOVERY_DECISION")
    if decision_id != expected_id:
        raise VitContractError("HISTORICAL_RECOVERY_DECISION_ID_INVALID")
    return record


@dataclass(frozen=True)
class HistoricalRecoveryBundle:
    recovery_decision_id: str
    recovery_attempt_id: str
    effective_write_receipt_id: str
    completion_receipt_id: str
    development_latency_receipt_id: str
    attachment_id: str
    proof_id: str


def _assert_single_effective_completion(
    store: ReceiptStore, *, physical_merge_sha: str, completion_receipt_id: str
) -> None:
    matches: list[str] = []
    for path in sorted(store.root.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL") from exc
        if (
            isinstance(value, Mapping)
            and value.get("schema") == COMPLETION_SCHEMA
            and value.get("physical_merge_sha") == physical_merge_sha
        ):
            matches.append(str(value.get("completion_receipt_id", "")))
    if any(value != completion_receipt_id for value in matches) or len(matches) > 1:
        raise VitContractError("HISTORICAL_RECOVERY_DUPLICATE_EFFECTIVE_COMPLETION")


def recover_historical_effective_write_completion(
    *,
    decision: Mapping[str, Any],
    receipt_store: ReceiptStore,
    current_main_before: str,
    current_main_after: str,
    implementation_ref: str,
    qa_ref: str,
    gate_decision_ref: str,
    next_packet: str | None,
    siq_receipts: Sequence[Mapping[str, Any]],
) -> HistoricalRecoveryBundle:
    """Persist the one authorised historical completion without constructing a PMT."""
    validate_historical_recovery_decision(decision)
    if not _SHA40.fullmatch(current_main_before) or current_main_before != current_main_after:
        raise VitContractError("HISTORICAL_RECOVERY_MAIN_REF_CHANGED")

    decision_id = str(decision["recovery_decision_id"])
    attempt = _record(
        {
            "schema": ATTEMPT_SCHEMA,
            "recovery_decision_id": decision_id,
            "source_census_id": str(decision["source_census_id"]),
            "pr_number": AUTHORIZED_PR,
            "head_sha": AUTHORIZED_HEAD,
            "physical_merge_sha": AUTHORIZED_MERGE,
            "observed_physical_tree": AUTHORIZED_RESULT_TREE,
            "recovery_class": RECOVERY_CLASS,
            "prewrite_freeze_status": PREWRITE_FREEZE_STATUS,
            "identity_class": "NEW_RECOVERY_ATTEMPT_NOT_ORIGINAL_PMT",
            "authority_delta": AUTHORITY_DELTA,
            "precedent_effect": PRECEDENT_EFFECT,
            "authority_effect": "NONE",
        },
        id_field="recovery_attempt_id",
        role="DSAI3V_HISTORICAL_COMPLETION_RECOVERY_ATTEMPT",
    )
    attempt_id = str(attempt["recovery_attempt_id"])
    effective = _record(
        {
            "schema": EFFECTIVE_WRITE_SCHEMA,
            "recovery_decision_id": decision_id,
            "recovery_attempt_id": attempt_id,
            "pr_number": AUTHORIZED_PR,
            "head_sha": AUTHORIZED_HEAD,
            "physical_merge_sha": AUTHORIZED_MERGE,
            "predecessor_tree": AUTHORIZED_PREDECESSOR_TREE,
            "expected_result_tree": AUTHORIZED_RESULT_TREE,
            "observed_physical_tree": AUTHORIZED_RESULT_TREE,
            "exact_tree_equal": True,
            "prewrite_freeze_status": PREWRITE_FREEZE_STATUS,
            "controller": VIT_PHYSICAL_CONTROLLER,
            "physical_gateway": SIQ_PHYSICAL_GATEWAY,
            "git_write_performed": False,
            "outcome": "HISTORICAL_EFFECTIVE_WRITE_COMPLETION_RECOVERED",
            "recovery_class": RECOVERY_CLASS,
            "authority_delta": AUTHORITY_DELTA,
            "precedent_effect": PRECEDENT_EFFECT,
            "authority_effect": "NONE",
        },
        id_field="effective_write_receipt_id",
        role="DSAI3V_HISTORICAL_EFFECTIVE_WRITE_RECEIPT",
    )
    effective_id = str(effective["effective_write_receipt_id"])
    completion = _record(
        {
            "schema": COMPLETION_SCHEMA,
            "programme_id": "OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1",
            "packet_id": "ATLAS-WP10",
            "implementation_ref": implementation_ref,
            "qa_ref": qa_ref,
            "gate_decision_ref": gate_decision_ref,
            "payload_id": AUTHORIZED_PIP,
            "vit_generation_id": AUTHORIZED_GENERATION,
            "historical_effective_write_receipt_id": effective_id,
            "recovery_decision_id": decision_id,
            "recovery_attempt_id": attempt_id,
            "physical_merge_sha": AUTHORIZED_MERGE,
            "next_packet": next_packet,
            "result": "PACKET_COMPLETION_RECOVERED_HISTORICAL_EXCEPTION",
            "authority_delta": AUTHORITY_DELTA,
            "precedent_effect": PRECEDENT_EFFECT,
            "authority_effect": "NONE",
        },
        id_field="completion_receipt_id",
        role="DSAI3V_HISTORICAL_PACKET_COMPLETION_RECEIPT",
    )
    completion_id = str(completion["completion_receipt_id"])
    _assert_single_effective_completion(
        receipt_store,
        physical_merge_sha=AUTHORIZED_MERGE,
        completion_receipt_id=completion_id,
    )

    devobs = build_canonical_completion_latency_receipt(
        programme_id=str(completion["programme_id"]),
        packet_id=str(completion["packet_id"]),
        completion_receipt_id=completion_id,
        vit_receipts=(effective,),
        siq_receipts=siq_receipts,
    )
    attachment = validate_completion_attachment(
        programme_id=str(completion["programme_id"]),
        packet_id=str(completion["packet_id"]),
        completion_receipt_id=completion_id,
        development_latency_receipt=devobs,
    ).to_record()

    records = (
        (decision, decision_id),
        (attempt, attempt_id),
        (effective, effective_id),
        (completion, completion_id),
        (devobs, str(devobs["record_id"])),
        (attachment, str(attachment["attachment_id"])),
    )
    for value, record_id in records:
        receipt_store.put_record(value, record_id)

    proof = _record(
        {
            "schema": PROOF_SCHEMA,
            "recovery_decision_id": decision_id,
            "recovery_attempt_id": attempt_id,
            "physical_merge_sha": AUTHORIZED_MERGE,
            "predecessor_tree": AUTHORIZED_PREDECESSOR_TREE,
            "expected_result_tree": AUTHORIZED_RESULT_TREE,
            "observed_physical_tree": AUTHORIZED_RESULT_TREE,
            "exact_tree_equal": True,
            "current_main_before": current_main_before,
            "current_main_after": current_main_after,
            "git_main_write_performed": False,
            "packet_completion_result_count": 1,
            "reconstruction_source": "REPOSITORY_MAIN_PLUS_RECEIPTSTORE",
            "repeated_recovery": "IDEMPOTENT_NO_DUPLICATE_EFFECTIVE_COMPLETION",
            "normal_prospective_requirement": "PMT_AND_PREWRITE_FREEZE_REQUIRED_UNCHANGED",
            "receipt_ids": {
                "effective_write_receipt_id": effective_id,
                "completion_receipt_id": completion_id,
                "development_latency_receipt_id": str(devobs["record_id"]),
                "attachment_id": str(attachment["attachment_id"]),
            },
            "telemetry_status": "UNAVAILABLE",
            "controller": VIT_PHYSICAL_CONTROLLER,
            "physical_gateway": SIQ_PHYSICAL_GATEWAY,
            "authority_delta": AUTHORITY_DELTA,
            "precedent_effect": PRECEDENT_EFFECT,
            "authority_effect": "NONE",
        },
        id_field="proof_id",
        role="DSAI3V_HISTORICAL_COMPLETION_RECOVERY_PROOF",
    )
    proof_id = str(proof["proof_id"])
    _write_content_addressed(receipt_store.root / "proofs" / f"{proof_id}.json", proof)
    reconstruct_historical_completion(receipt_store=receipt_store, decision=decision)
    return HistoricalRecoveryBundle(
        recovery_decision_id=decision_id,
        recovery_attempt_id=attempt_id,
        effective_write_receipt_id=effective_id,
        completion_receipt_id=completion_id,
        development_latency_receipt_id=str(devobs["record_id"]),
        attachment_id=str(attachment["attachment_id"]),
        proof_id=proof_id,
    )


def reconstruct_historical_completion(
    *, receipt_store: ReceiptStore, decision: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Reconstruct the single effective completion from repository decision + store."""
    validate_historical_recovery_decision(decision)
    decision_id = str(decision["recovery_decision_id"])
    completions: list[Mapping[str, Any]] = []
    for path in sorted(receipt_store.root.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            isinstance(value, Mapping)
            and value.get("schema") == COMPLETION_SCHEMA
            and value.get("physical_merge_sha") == AUTHORIZED_MERGE
        ):
            completions.append(value)
    if len(completions) != 1:
        raise VitContractError(
            f"HISTORICAL_RECOVERY_EXPECTED_ONE_COMPLETION_FOUND_{len(completions)}"
        )
    completion = completions[0]
    if completion.get("recovery_decision_id") != decision_id:
        raise VitContractError("HISTORICAL_RECOVERY_COMPLETION_DECISION_MISMATCH")
    required_ids = (
        decision_id,
        str(completion["recovery_attempt_id"]),
        str(completion["historical_effective_write_receipt_id"]),
        str(completion["completion_receipt_id"]),
    )
    if any(not (receipt_store.root / f"{record_id}.json").is_file() for record_id in required_ids):
        raise VitContractError("HISTORICAL_RECOVERY_BUNDLE_INCOMPLETE")
    return {
        "status": "RECONSTRUCTED_EXACTLY_ONE_HISTORICAL_COMPLETION",
        "physical_merge_sha": AUTHORIZED_MERGE,
        "completion_receipt_id": completion["completion_receipt_id"],
        "recovery_decision_id": decision_id,
        "authority_effect": "NONE",
    }
