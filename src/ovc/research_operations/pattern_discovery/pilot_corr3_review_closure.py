from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.research_operations.prospective_source import operator_replay_acceptance as replay

from . import pilot_corrective_review_v2 as review_v2
from . import pilot_discovery as pilot
from . import pilot_corr2_review_closure as corr2
from .corr3_evidence import (
    PACKET_ID,
    RETURN_GATE,
    TARGET_CANDIDATE_ID,
    TARGET_FINDING_CODE,
    Corr3EvidenceError,
    build_structural_comparison_context,
    exact_corr3_references,
    validate_exact_corr3_references,
)


INPUT_SCHEMA = "ovc-c1c-g5-corr3-review-input/v1"
RECEIPT_SCHEMA = "ovc-c1c-g5-corr3-review-receipt/v1"
LEDGER_SCHEMA = "ovc-c1c-g5-corr3-closure-ledger/v1"
INVENTORY_SCHEMA = "ovc-c1c-g5-corr3-evidence-inventory/v1"
GATE_INPUT_SCHEMA = "ovc-c1c-g5-corrective-pilot-review-final-gate-input/v2"
PREPARE_DIR = "corr3-prepared"
FINAL_DIR = "operator-review-corr3"
TEMPLATE_NAME = "c1c-g5-corr3-review.template.json"
CONTEXT_NAME = "c1c-g5-corr3-structural-comparison.json"
CONSOLE_NAME = "c1c-g5-corr3-console-bundle.json"
EXPECTED_RUN_ID = review_v2.EXPECTED_RUN_ID
EXPECTED_NAMESPACE = review_v2.EXPECTED_NAMESPACE
ALLOWED_FINAL_DISPOSITIONS = {
    "WORKFLOW_ACCEPTED",
    "DEFER_PILOT_OBJECT",
    "REJECT_PILOT_OBJECT",
}
_SIGNATURE_FIELDS = {
    "signature_algorithm",
    "signature_format",
    "signature_namespace",
    "signed_payload_sha256",
    "signature_sha256",
    "signature",
}


class Corr3ReviewError(RuntimeError):
    pass


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Corr3ReviewError(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise Corr3ReviewError(f"{code}:{path}")
    return value


def _load_jsonl(path: Path, code: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise Corr3ReviewError(f"{code}:{path}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Corr3ReviewError(f"{code}:{path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise Corr3ReviewError(f"{code}:{path}:{line_number}")
        rows.append(value)
    return rows


def _required_text(source: Mapping[str, Any], field: str, code: str) -> str:
    value = str(source.get(field) or "").strip()
    if not value or "REPLACE_WITH" in value:
        raise Corr3ReviewError(f"{code}:{field}")
    return value


def _required_strings(source: Mapping[str, Any], field: str, code: str) -> list[str]:
    value = source.get(field)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise Corr3ReviewError(f"{code}:{field}")
    normalized = sorted({str(item).strip() for item in value if str(item).strip()})
    if not normalized or any("REPLACE_WITH" in item for item in normalized):
        raise Corr3ReviewError(f"{code}:{field}")
    return normalized


def _signature_body(record: Mapping[str, Any], *, inventory: bool = False) -> dict[str, Any]:
    excluded = set(_SIGNATURE_FIELDS)
    if inventory:
        excluded.update({"inventory_id", "status"})
    return {key: value for key, value in record.items() if key not in excluded}


def load_corr3_authority(repository_root: Path) -> dict[str, Any]:
    decision_path = repository_root / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/final-gate/C1C_G5_CORR2_OPERATOR_DEFER_DECISION.json"
    state_path = repository_root / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/final-gate/C1C_G5_CORR3_PROGRAMME_STATE.json"
    binding_path = repository_root / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr3/C1C_G5_CORR3_AUTHORITY_BINDING.json"
    decision = _load_json(decision_path, "CORR3_OPERATOR_DECISION_UNAVAILABLE")
    state = _load_json(state_path, "CORR3_PROGRAMME_STATE_UNAVAILABLE")
    binding = _load_json(binding_path, "CORR3_AUTHORITY_BINDING_UNAVAILABLE")
    if decision.get("gate_id") != RETURN_GATE or decision.get("decision") != "DEFER":
        raise Corr3ReviewError("CORR3_OPERATOR_DEFER_NOT_RECORDED")
    packet = decision.get("authorised_next_packet")
    if not isinstance(packet, Mapping) or packet.get("packet_id") != PACKET_ID:
        raise Corr3ReviewError("CORR3_PACKET_AUTHORITY_NOT_RECORDED")
    if packet.get("machine_replay") != "DENIED_NOT_REQUIRED":
        raise Corr3ReviewError("CORR3_MACHINE_REPLAY_BOUNDARY_INVALID")
    if state.get("packet_id") != PACKET_ID or state.get("status") not in {"READY", "RUNNING", "IMPLEMENTED", "QA_REVIEW", "GATE_READY", "COMPLETED"}:
        raise Corr3ReviewError(f"CORR3_STATE_NOT_EXECUTABLE:{state.get('status')}")
    if binding.get("packet_id") != PACKET_ID or binding.get("target_candidate_window_id") != TARGET_CANDIDATE_ID:
        raise Corr3ReviewError("CORR3_AUTHORITY_BINDING_MISMATCH")
    return {
        "decision": decision,
        "decision_path": decision_path,
        "state": state,
        "state_path": state_path,
        "binding": binding,
        "binding_path": binding_path,
    }


def load_verified_corr3_source(
    repository_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    authority = load_corr3_authority(repository_root)
    base = corr2.load_verified_corr2_source(repository_root, environ=environ)
    root = Path(base["root"])
    corr2_root = root / corr2.FINAL_DIR
    paths = {
        "c1c-g5-corr2-review-receipt.json": corr2_root / "c1c-g5-corr2-review-receipt.json",
        "c1c-g5-corr2-closure-ledger.json": corr2_root / "c1c-g5-corr2-closure-ledger.json",
        "signed-c1c-g5-corr2-evidence-inventory.json": corr2_root / "signed-c1c-g5-corr2-evidence-inventory.json",
        "c1c-g5-corrective-pilot-review-final-gate-input.json": corr2_root / "c1c-g5-corrective-pilot-review-final-gate-input.json",
    }
    expected_hashes = authority["binding"].get("corr2_returned_evidence_sha256")
    if not isinstance(expected_hashes, Mapping):
        raise Corr3ReviewError("CORR3_CORR2_HASH_BINDING_MISSING")
    for name, path in paths.items():
        if path.is_symlink() or not path.is_file():
            raise Corr3ReviewError(f"CORR3_CORR2_RETURNED_FILE_UNAVAILABLE_OR_UNSAFE:{path}")
        if pilot.sha_file(path) != expected_hashes.get(name):
            raise Corr3ReviewError(f"CORR3_CORR2_RETURNED_FILE_HASH_MISMATCH:{name}")

    receipt = _load_json(paths["c1c-g5-corr2-review-receipt.json"], "CORR3_CORR2_RECEIPT_INVALID")
    ledger = _load_json(paths["c1c-g5-corr2-closure-ledger.json"], "CORR3_CORR2_LEDGER_INVALID")
    inventory = _load_json(paths["signed-c1c-g5-corr2-evidence-inventory.json"], "CORR3_CORR2_INVENTORY_INVALID")
    gate = _load_json(paths["c1c-g5-corrective-pilot-review-final-gate-input.json"], "CORR3_CORR2_GATE_INVALID")

    if receipt.get("schema") != corr2.RECEIPT_SCHEMA or receipt.get("status") != "C1C_G5_CORR2_OPERATOR_REREVIEW_COMPLETE":
        raise Corr3ReviewError("CORR3_CORR2_RECEIPT_STATUS_MISMATCH")
    if ledger.get("remaining_deferred_object_count") != 1 or ledger.get("status") != "CORR2_REVIEW_COMPLETE_REMAINS_DEFERRED":
        raise Corr3ReviewError("CORR3_CORR2_LEDGER_STATUS_MISMATCH")
    if gate.get("recommended_decision") != "DEFER" or gate.get("remaining_deferred_object_count") != 1:
        raise Corr3ReviewError("CORR3_CORR2_GATE_STATUS_MISMATCH")
    if inventory.get("status") != "SIGNED_C1C_G5_CORR2_EVIDENCE_COMPLETE":
        raise Corr3ReviewError("CORR3_CORR2_INVENTORY_STATUS_MISMATCH")

    logical_ledger = dict(ledger)
    claimed_ledger = logical_ledger.pop("ledger_sha256", None)
    if claimed_ledger != pilot.logical_sha(logical_ledger):
        raise Corr3ReviewError("CORR3_CORR2_LEDGER_LOGICAL_HASH_MISMATCH")
    links = {
        "ledger_receipt": ledger.get("source_corr2_review_receipt_file_sha256") == pilot.sha_file(paths["c1c-g5-corr2-review-receipt.json"]),
        "inventory_receipt": inventory.get("corr2_review_receipt_file_sha256") == pilot.sha_file(paths["c1c-g5-corr2-review-receipt.json"]),
        "inventory_ledger": inventory.get("corr2_closure_ledger_file_sha256") == pilot.sha_file(paths["c1c-g5-corr2-closure-ledger.json"]),
        "gate_receipt": gate.get("corr2_review_receipt_file_sha256") == pilot.sha_file(paths["c1c-g5-corr2-review-receipt.json"]),
        "gate_ledger": gate.get("corr2_closure_ledger_file_sha256") == pilot.sha_file(paths["c1c-g5-corr2-closure-ledger.json"]),
        "gate_inventory": gate.get("signed_corr2_inventory_file_sha256") == pilot.sha_file(paths["signed-c1c-g5-corr2-evidence-inventory.json"]),
    }
    if not all(links.values()):
        raise Corr3ReviewError(f"CORR3_CORR2_HASH_LINK_MISMATCH:{sorted(key for key, value in links.items() if not value)}")

    public_key = str(base["authority"]["signing"]["public_key"])
    review_v2._verify_signature(receipt, _signature_body(receipt), public_key=public_key)
    review_v2._verify_signature(inventory, _signature_body(inventory, inventory=True), public_key=public_key)

    decisions = receipt.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 2:
        raise Corr3ReviewError("CORR3_CORR2_DECISION_COUNT_MISMATCH")
    decision_by_id = {
        str(item.get("candidate_window_id")): dict(item)
        for item in decisions
        if isinstance(item, Mapping)
    }
    target = decision_by_id.get(TARGET_CANDIDATE_ID)
    if not target or target.get("final_disposition") != "DEFER_PILOT_OBJECT" or target.get("finding_code") != TARGET_FINDING_CODE:
        raise Corr3ReviewError("CORR3_TARGET_DEFER_DECISION_MISMATCH")
    rejected_id = "PDPILOT-CANDIDATE-4f41e21b6cd075e0fdbc40e4"
    rejected = decision_by_id.get(rejected_id)
    if not rejected or rejected.get("final_disposition") != "REJECT_PILOT_OBJECT":
        raise Corr3ReviewError("CORR3_REJECTED_OBJECT_PRESERVATION_MISMATCH")

    candidates = _load_jsonl(root / "derived/candidates.jsonl", "CORR3_CANDIDATES_INVALID")
    cluster_versions = _load_jsonl(root / "derived/cluster-versions.jsonl", "CORR3_CLUSTER_VERSIONS_INVALID")
    trigger_events = _load_jsonl(root / "derived/trigger-events.jsonl", "CORR3_TRIGGER_EVENTS_INVALID")
    try:
        context = build_structural_comparison_context(
            candidates=candidates,
            fingerprints=base["fingerprints"],
            cluster_versions=cluster_versions,
            trigger_events=trigger_events,
        )
    except Corr3EvidenceError as exc:
        raise Corr3ReviewError(str(exc)) from exc

    return {
        **base,
        "corr3_authority": authority,
        "corr2_receipt": receipt,
        "corr2_ledger": ledger,
        "corr2_inventory": inventory,
        "corr2_gate": gate,
        "corr2_paths": paths,
        "candidates": candidates,
        "cluster_versions": cluster_versions,
        "trigger_events": trigger_events,
        "corr3_context": context,
        "preserved_rejected_decision": rejected,
    }


def build_review_template(source: Mapping[str, Any]) -> dict[str, Any]:
    context = source["corr3_context"]
    return {
        "schema": INPUT_SCHEMA,
        "packet_id": PACKET_ID,
        "gate_id": RETURN_GATE,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "operator_id": pilot.OPERATOR_ID,
        "reviewed_at_utc": "REPLACE_WITH_UTC_TIMESTAMP_ENDING_Z",
        "source_corr2_review_receipt_file_sha256": pilot.sha_file(source["corr2_paths"]["c1c-g5-corr2-review-receipt.json"]),
        "decision": {
            "candidate_window_id": TARGET_CANDIDATE_ID,
            "prior_disposition": "DEFER_PILOT_OBJECT",
            "prior_finding_code": TARGET_FINDING_CODE,
            "final_disposition": "REPLACE_WITH_WORKFLOW_ACCEPTED_DEFER_PILOT_OBJECT_OR_REJECT_PILOT_OBJECT",
            "notes": "REPLACE_WITH_NONEMPTY_REVIEW_NOTES",
            "evidence_references": list(exact_corr3_references()),
            "evidence_context_sha256": pilot.logical_sha(context),
        },
        "required_fields_by_final_disposition": {
            "WORKFLOW_ACCEPTED": ["closure_basis", "acceptance_criteria"],
            "DEFER_PILOT_OBJECT": ["finding_code", "resolution_criteria", "next_review_condition"],
            "REJECT_PILOT_OBJECT": ["finding_code", "structural_basis"],
        },
        "second_machine_replay_required": False,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_append": "DENIED",
    }


def validate_review_input(review: Mapping[str, Any], *, source: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema": INPUT_SCHEMA,
        "packet_id": PACKET_ID,
        "gate_id": RETURN_GATE,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "operator_id": pilot.OPERATOR_ID,
    }
    for key, value in expected.items():
        if review.get(key) != value:
            raise Corr3ReviewError(f"CORR3_REVIEW_INPUT_MISMATCH:{key}")
    pilot.parse_utc(_required_text(review, "reviewed_at_utc", "CORR3_REVIEW_INPUT_MISSING"))
    receipt_sha = pilot.sha_file(source["corr2_paths"]["c1c-g5-corr2-review-receipt.json"])
    if review.get("source_corr2_review_receipt_file_sha256") != receipt_sha:
        raise Corr3ReviewError("CORR3_REVIEW_SOURCE_RECEIPT_HASH_MISMATCH")
    item = review.get("decision")
    if not isinstance(item, Mapping):
        raise Corr3ReviewError("CORR3_REVIEW_REQUIRES_EXACTLY_ONE_DECISION")
    if item.get("candidate_window_id") != TARGET_CANDIDATE_ID:
        raise Corr3ReviewError("CORR3_REVIEW_UNAUTHORISED_CANDIDATE")
    if item.get("prior_disposition") != "DEFER_PILOT_OBJECT" or item.get("prior_finding_code") != TARGET_FINDING_CODE:
        raise Corr3ReviewError("CORR3_REVIEW_PRIOR_DECISION_MISMATCH")
    context_sha = pilot.logical_sha(source["corr3_context"])
    if item.get("evidence_context_sha256") != context_sha:
        raise Corr3ReviewError("CORR3_EVIDENCE_CONTEXT_HASH_MISMATCH")
    try:
        references = validate_exact_corr3_references(
            _required_strings(item, "evidence_references", "CORR3_REVIEW_DECISION_MISSING")
        )
    except Corr3EvidenceError as exc:
        raise Corr3ReviewError(str(exc)) from exc
    disposition = _required_text(item, "final_disposition", "CORR3_REVIEW_DECISION_MISSING")
    if disposition not in ALLOWED_FINAL_DISPOSITIONS:
        raise Corr3ReviewError(f"CORR3_FINAL_DISPOSITION_INVALID:{disposition}")
    normalized: dict[str, Any] = {
        "candidate_window_id": TARGET_CANDIDATE_ID,
        "prior_disposition": "DEFER_PILOT_OBJECT",
        "prior_finding_code": TARGET_FINDING_CODE,
        "final_disposition": disposition,
        "notes": _required_text(item, "notes", "CORR3_REVIEW_DECISION_MISSING"),
        "evidence_references": references,
        "evidence_context_sha256": context_sha,
    }
    if disposition == "WORKFLOW_ACCEPTED":
        normalized["closure_basis"] = _required_text(item, "closure_basis", "CORR3_ACCEPTANCE_INCOMPLETE")
        normalized["acceptance_criteria"] = _required_strings(item, "acceptance_criteria", "CORR3_ACCEPTANCE_INCOMPLETE")
    elif disposition == "DEFER_PILOT_OBJECT":
        finding_code = _required_text(item, "finding_code", "CORR3_DEFER_INCOMPLETE")
        if not finding_code.startswith("PD-DEFER-"):
            raise Corr3ReviewError(f"CORR3_DEFER_CODE_INVALID:{finding_code}")
        normalized.update({
            "finding_code": finding_code,
            "resolution_criteria": _required_strings(item, "resolution_criteria", "CORR3_DEFER_INCOMPLETE"),
            "next_review_condition": _required_text(item, "next_review_condition", "CORR3_DEFER_INCOMPLETE"),
        })
    else:
        finding_code = _required_text(item, "finding_code", "CORR3_REJECTION_INCOMPLETE")
        if not finding_code.startswith("PD-REJECT-"):
            raise Corr3ReviewError(f"CORR3_REJECTION_CODE_INVALID:{finding_code}")
        normalized.update({
            "finding_code": finding_code,
            "structural_basis": _required_text(item, "structural_basis", "CORR3_REJECTION_INCOMPLETE"),
        })
    return normalized


def preflight(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    source = load_verified_corr3_source(repository_root, environ=environ)
    values = os.environ if environ is None else environ
    private_key, public_key = replay.key_paths(repository_root, values, pilot.OPERATOR_ID)
    return {
        "status": "READY_FOR_C1C_G5_CORR3_ONE_OBJECT_REREVIEW",
        "packet_id": PACKET_ID,
        "return_gate": RETURN_GATE,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "candidate_window_id": TARGET_CANDIDATE_ID,
        "evidence_context_sha256": pilot.logical_sha(source["corr3_context"]),
        "comparison_status": source["corr3_context"]["comparison_availability"]["status"],
        "private_key_exists": private_key.is_file() and not private_key.is_symlink(),
        "public_key_exists": public_key.is_file() and not public_key.is_symlink(),
        "second_machine_replay_required": False,
        "canonical_append": "DENIED",
    }


def prepare(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if pilot.truthy(values.get("CI")) or pilot.truthy(values.get("GITHUB_ACTIONS")):
        raise Corr3ReviewError("CORR3_OPERATOR_REVIEW_PREPARATION_PROHIBITED_IN_CI")
    source = load_verified_corr3_source(repository_root, environ=values)
    root = Path(source["root"])
    final = root / "review" / PREPARE_DIR
    if final.exists():
        raise Corr3ReviewError(f"CORR3_REFUSING_TO_OVERWRITE_PREPARED_REVIEW:{final}")
    staging = root / "review" / f".{PREPARE_DIR}.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        context_path = staging / CONTEXT_NAME
        pilot.write_json(context_path, source["corr3_context"])
        console = json.loads(json.dumps(source["console_bundle"]))
        details = console.get("candidate_details")
        if not isinstance(details, dict) or TARGET_CANDIDATE_ID not in details:
            raise Corr3ReviewError("CORR3_CONSOLE_TARGET_DETAIL_MISSING")
        details[TARGET_CANDIDATE_ID]["corr3_structural_comparison"] = source["corr3_context"]
        console_path = staging / CONSOLE_NAME
        pilot.write_json(console_path, console)
        template_path = staging / TEMPLATE_NAME
        pilot.write_json(template_path, build_review_template(source))
        staging.rename(final)
    except Exception:
        if staging.exists():
            for path in sorted(staging.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            staging.rmdir()
        raise
    return {
        "status": "C1C_G5_CORR3_ONE_OBJECT_REVIEW_READY",
        "candidate_window_id": TARGET_CANDIDATE_ID,
        "comparison_context": str(final / CONTEXT_NAME),
        "console_bundle": str(final / CONSOLE_NAME),
        "review_template": str(final / TEMPLATE_NAME),
        "next_command": "finalize --review-file <completed-corr3-review.json>",
        "second_machine_replay_required": False,
        "canonical_append": "DENIED",
    }


def finalize(
    repository_root: Path,
    *,
    review_file: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if pilot.truthy(values.get("CI")) or pilot.truthy(values.get("GITHUB_ACTIONS")):
        raise Corr3ReviewError("CORR3_OPERATOR_REVIEW_FINALIZATION_PROHIBITED_IN_CI")
    source = load_verified_corr3_source(repository_root, environ=values)
    review = _load_json(review_file.resolve(strict=True), "CORR3_REVIEW_INPUT_INVALID")
    decision = validate_review_input(review, source=source)

    private_key, public_key_path = replay.key_paths(repository_root, values, pilot.OPERATOR_ID)
    if private_key.is_symlink() or not private_key.is_file() or public_key_path.is_symlink() or not public_key_path.is_file():
        raise Corr3ReviewError("CORR3_OPERATOR_ED25519_KEY_UNAVAILABLE_OR_UNSAFE")
    public = replay.public_key_details(public_key_path, pilot.OPERATOR_ID)
    if public["public_key_sha256"] != source["authority"]["signing"]["public_key_sha256"]:
        raise Corr3ReviewError("CORR3_OPERATOR_KEY_BINDING_MISMATCH")

    root = Path(source["root"])
    final_root = root / FINAL_DIR
    if final_root.exists():
        raise Corr3ReviewError(f"CORR3_REFUSING_TO_OVERWRITE_FINAL_REVIEW:{final_root}")
    staging = root / f".{FINAL_DIR}.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        rejected_hash = pilot.logical_sha(source["preserved_rejected_decision"])
        context_hash = pilot.logical_sha(source["corr3_context"])
        receipt_body = {
            "schema": RECEIPT_SCHEMA,
            "packet_id": PACKET_ID,
            "gate_id": RETURN_GATE,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "operator_id": pilot.OPERATOR_ID,
            "reviewed_at_utc": str(review["reviewed_at_utc"]),
            "source_corr2_review_receipt_file_sha256": pilot.sha_file(source["corr2_paths"]["c1c-g5-corr2-review-receipt.json"]),
            "source_corr3_comparison_context_sha256": context_hash,
            "preserved_rejected_object_decision_sha256": rejected_hash,
            "preserved_non_deferred_decision_count": source["corr2_receipt"]["preserved_non_deferred_decision_count"],
            "preserved_non_deferred_decisions_sha256": source["corr2_receipt"]["preserved_non_deferred_decisions_sha256"],
            "decision": decision,
            "second_machine_replay_performed": False,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "status": "C1C_G5_CORR3_OPERATOR_REREVIEW_COMPLETE",
        }
        signature, signature_sha = replay.sign_and_verify(
            private_key=private_key,
            public_key=public["public_key"],
            operator_id=pilot.OPERATOR_ID,
            payload=pilot.canonical_bytes(receipt_body),
        )
        receipt = {
            **receipt_body,
            "signature_algorithm": "ED25519",
            "signature_format": replay.SIGNATURE_FORMAT,
            "signature_namespace": replay.SIGNATURE_NAMESPACE,
            "signed_payload_sha256": pilot.logical_sha(receipt_body),
            "signature_sha256": signature_sha,
            "signature": signature,
        }
        receipt_path = staging / "c1c-g5-corr3-review-receipt.json"
        pilot.write_json(receipt_path, receipt)

        remaining = 1 if decision["final_disposition"] == "DEFER_PILOT_OBJECT" else 0
        ledger_body = {
            "schema": LEDGER_SCHEMA,
            "packet_id": PACKET_ID,
            "gate_id": RETURN_GATE,
            "pilot_run_id": EXPECTED_RUN_ID,
            "source_corr3_review_receipt_file_sha256": pilot.sha_file(receipt_path),
            "candidate_window_id": TARGET_CANDIDATE_ID,
            "prior_finding_code": TARGET_FINDING_CODE,
            "final_disposition": decision["final_disposition"],
            "resolution_status": "OPEN_DEFERRED" if remaining else "CLOSED_BY_OPERATOR_REREVIEW",
            "remaining_deferred_object_count": remaining,
            "preserved_rejected_object_decision_sha256": rejected_hash,
            "preserved_non_deferred_decisions_sha256": receipt_body["preserved_non_deferred_decisions_sha256"],
            "second_machine_replay_performed": False,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "status": "CORR3_REVIEW_COMPLETE_REMAINS_DEFERRED" if remaining else "CORR3_REVIEW_COMPLETE_NO_DEFERRED_OBJECTS",
        }
        ledger = {**ledger_body, "ledger_sha256": pilot.logical_sha(ledger_body)}
        ledger_path = staging / "c1c-g5-corr3-closure-ledger.json"
        pilot.write_json(ledger_path, ledger)

        inventory_body = {
            "schema": INVENTORY_SCHEMA,
            "packet_id": PACKET_ID,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "operator_id": pilot.OPERATOR_ID,
            "signing_binding_id": source["authority"]["signing"]["signing_binding_id"],
            "source_corr2_review_receipt_file_sha256": receipt_body["source_corr2_review_receipt_file_sha256"],
            "corr3_review_receipt_file_sha256": pilot.sha_file(receipt_path),
            "corr3_closure_ledger_file_sha256": pilot.sha_file(ledger_path),
            "corr3_comparison_context_sha256": context_hash,
            "preserved_rejected_object_decision_sha256": rejected_hash,
            "preserved_non_deferred_decisions_sha256": receipt_body["preserved_non_deferred_decisions_sha256"],
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
        }
        inventory_id = f"PD.PILOT.CORR3.EVIDENCE.{pilot.logical_sha(inventory_body)[:24]}"
        inventory_signature, inventory_signature_sha = replay.sign_and_verify(
            private_key=private_key,
            public_key=public["public_key"],
            operator_id=pilot.OPERATOR_ID,
            payload=pilot.canonical_bytes(inventory_body),
        )
        inventory = {
            **inventory_body,
            "inventory_id": inventory_id,
            "signature_algorithm": "ED25519",
            "signature_format": replay.SIGNATURE_FORMAT,
            "signature_namespace": replay.SIGNATURE_NAMESPACE,
            "signed_payload_sha256": pilot.logical_sha(inventory_body),
            "signature_sha256": inventory_signature_sha,
            "signature": inventory_signature,
            "status": "SIGNED_C1C_G5_CORR3_EVIDENCE_COMPLETE",
        }
        inventory_path = staging / "signed-c1c-g5-corr3-evidence-inventory.json"
        pilot.write_json(inventory_path, inventory)

        recommended = "DEFER" if remaining else "PASS"
        gate = {
            "schema": GATE_INPUT_SCHEMA,
            "packet_id": PACKET_ID,
            "gate_id": RETURN_GATE,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "active_c2_release_id": source["corr2_gate"]["active_c2_release_id"],
            "active_c2_manifest_id": source["corr2_gate"]["active_c2_manifest_id"],
            "selector_id": source["corr2_gate"]["selector_id"],
            "corr3_operator_rereview_complete": True,
            "corr3_review_receipt_file_sha256": pilot.sha_file(receipt_path),
            "corr3_closure_ledger_file_sha256": pilot.sha_file(ledger_path),
            "signed_corr3_inventory_file_sha256": pilot.sha_file(inventory_path),
            "structural_comparison_context_sha256": context_hash,
            "structured_review_v2_preserved": True,
            "corr2_rejected_object_preserved": True,
            "second_machine_replay_performed": False,
            "remaining_deferred_object_count": remaining,
            "recommended_decision": recommended,
            "operator_approval_required": True,
            "allowed_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "status": "C1C_G5_CORRECTIVE_PILOT_REVIEW_FINAL_GATE_INPUT_READY",
        }
        gate_path = staging / "c1c-g5-corrective-pilot-review-final-gate-input.json"
        pilot.write_json(gate_path, gate)
        staging.rename(final_root)
    except Exception:
        if staging.exists():
            for path in sorted(staging.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            staging.rmdir()
        raise
    return {
        "status": "C1C_G5_CORR3_OPERATOR_REREVIEW_COMPLETE",
        "candidate_window_id": TARGET_CANDIDATE_ID,
        "final_disposition": decision["final_disposition"],
        "remaining_deferred_object_count": remaining,
        "recommended_decision": recommended,
        "final_root": str(final_root),
        "second_machine_replay_performed": False,
        "canonical_append": "DENIED",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run bounded C1C-G5-CORR3 one-object review closure")
    parser.add_argument("command", choices=("preflight", "prepare", "finalize"))
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--review-file", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "preflight":
            result = preflight(arguments.repository_root)
        elif arguments.command == "prepare":
            result = prepare(arguments.repository_root)
        else:
            if arguments.review_file is None:
                raise Corr3ReviewError("CORR3_FINALIZE_REQUIRES_REVIEW_FILE")
            result = finalize(arguments.repository_root, review_file=arguments.review_file)
    except Exception as exc:
        print(f"C1C-G5-CORR3 blocked: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
