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
from .corr2_evidence import (
    DEFERRED_OBJECTS,
    PACKET_ID,
    RETURN_GATE,
    Corr2EvidenceError,
    build_exact_evidence_context,
    exact_evidence_references,
    validate_exact_evidence_references,
)

INPUT_SCHEMA = "ovc-c1c-g5-corr2-deferred-review-input/v1"
RECEIPT_SCHEMA = "ovc-c1c-g5-corr2-deferred-review-receipt/v1"
LEDGER_SCHEMA = "ovc-c1c-g5-corr2-closure-ledger/v1"
INVENTORY_SCHEMA = "ovc-c1c-g5-corr2-evidence-inventory/v1"
GATE_INPUT_SCHEMA = "ovc-c1c-g5-corrective-pilot-review-final-gate-input/v1"
FINAL_DIR = "operator-review-corr2"
TEMPLATE_NAME = "c1c-g5-corr2-deferred-review.template.json"
EXPECTED_RUN_ID = review_v2.EXPECTED_RUN_ID
EXPECTED_NAMESPACE = review_v2.EXPECTED_NAMESPACE
ALLOWED_FINAL_DISPOSITIONS = {
    "WORKFLOW_ACCEPTED",
    "DEFER_PILOT_OBJECT",
    "REJECT_PILOT_OBJECT",
}


class Corr2ReviewError(RuntimeError):
    pass


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Corr2ReviewError(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise Corr2ReviewError(f"{code}:{path}")
    return value


def _load_jsonl(path: Path, code: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise Corr2ReviewError(f"{code}:{path}") from exc
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Corr2ReviewError(f"{code}:{path}:{index}") from exc
        if not isinstance(value, dict):
            raise Corr2ReviewError(f"{code}:{path}:{index}")
        rows.append(value)
    return rows


def _required_text(source: Mapping[str, Any], field: str, code: str) -> str:
    value = str(source.get(field) or "").strip()
    if not value or "REPLACE_WITH" in value:
        raise Corr2ReviewError(f"{code}:{field}")
    return value


def _required_strings(source: Mapping[str, Any], field: str, code: str) -> list[str]:
    value = source.get(field)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise Corr2ReviewError(f"{code}:{field}")
    normalized = sorted({str(item).strip() for item in value if str(item).strip()})
    if not normalized or any("REPLACE_WITH" in item for item in normalized):
        raise Corr2ReviewError(f"{code}:{field}")
    return normalized


def _repo_json(repository_root: Path, relative: str, code: str) -> dict[str, Any]:
    return _load_json(repository_root / relative, code)


def load_corr2_authority(repository_root: Path) -> dict[str, Any]:
    decision = _repo_json(
        repository_root,
        "docs/releases/opt-b-c1-v2/corrective/c1c-g5/operator-gate/C1C_G5_CORRECTIVE_PILOT_REVIEW_OPERATOR_DECISION.json",
        "CORR2_OPERATOR_DECISION_UNAVAILABLE",
    )
    state = _repo_json(
        repository_root,
        "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json",
        "CORR2_PROGRAMME_STATE_UNAVAILABLE",
    )
    bundle = _repo_json(
        repository_root,
        "docs/releases/opt-b-c1-v2/corrective/c1c-g5/operator-gate/C1C_G5_CORRECTIVE_PILOT_REVIEW_GATE_READY_BUNDLE.json",
        "CORR2_GATE_READY_BUNDLE_UNAVAILABLE",
    )
    if decision.get("gate_id") != RETURN_GATE or decision.get("decision") != "DEFER":
        raise Corr2ReviewError("CORR2_OPERATOR_DEFER_NOT_RECORDED")
    packet = decision.get("authorised_next_packet")
    if not isinstance(packet, Mapping) or packet.get("packet_id") != PACKET_ID:
        raise Corr2ReviewError("CORR2_PACKET_AUTHORITY_NOT_RECORDED")
    if packet.get("machine_replay") != "DENIED_NOT_REQUIRED":
        raise Corr2ReviewError("CORR2_MACHINE_REPLAY_BOUNDARY_INVALID")
    corr2 = state.get("corr2")
    if not isinstance(corr2, Mapping) or corr2.get("packet_id") != PACKET_ID:
        raise Corr2ReviewError("CORR2_STATE_PACKET_MISMATCH")
    if corr2.get("status") not in {"READY", "RUNNING", "IMPLEMENTED", "GATE_READY", "COMPLETED_IN_MAIN"}:
        raise Corr2ReviewError(f"CORR2_STATE_NOT_EXECUTABLE:{corr2.get('status')}")
    if bundle.get("gate_id") != RETURN_GATE or bundle.get("recommended_decision", {}).get("decision") != "DEFER":
        raise Corr2ReviewError("CORR2_GATE_READY_SOURCE_MISMATCH")
    return {"decision": decision, "state": state, "bundle": bundle}


def _verify_returned_file_hashes(bundle: Mapping[str, Any], paths: Mapping[str, Path]) -> None:
    expected = {
        str(item.get("name")): str(item.get("sha256"))
        for item in bundle.get("evidence_files", ())
        if isinstance(item, Mapping)
    }
    for name, path in paths.items():
        if name not in expected:
            raise Corr2ReviewError(f"CORR2_GATE_BUNDLE_HASH_MISSING:{name}")
        if not path.is_file() or path.is_symlink():
            raise Corr2ReviewError(f"CORR2_RETURNED_FILE_UNAVAILABLE_OR_UNSAFE:{path}")
        if pilot.sha_file(path) != expected[name]:
            raise Corr2ReviewError(f"CORR2_RETURNED_FILE_HASH_MISMATCH:{name}")


def load_verified_corr2_source(
    repository_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    authority = load_corr2_authority(repository_root)
    base = review_v2.load_and_verify_evidence(repository_root, environ=environ)
    root = Path(base["root"])
    review_root = root / "operator-review-v2"
    paths = {
        "pilot-review-receipt-v2.json": review_root / "pilot-review-receipt-v2.json",
        "pilot-defect-ledger-v2.json": review_root / "pilot-defect-ledger-v2.json",
        "signed-structured-review-evidence-inventory.json": review_root / "signed-structured-review-evidence-inventory.json",
        "c1c-g5-corrective-pilot-review-gate-input.json": review_root / "c1c-g5-corrective-pilot-review-gate-input.json",
    }
    _verify_returned_file_hashes(authority["bundle"], paths)

    receipt = _load_json(paths["pilot-review-receipt-v2.json"], "CORR2_REVIEW_V2_RECEIPT_INVALID")
    ledger = _load_json(paths["pilot-defect-ledger-v2.json"], "CORR2_REVIEW_V2_LEDGER_INVALID")
    inventory = _load_json(paths["signed-structured-review-evidence-inventory.json"], "CORR2_REVIEW_V2_INVENTORY_INVALID")
    gate = _load_json(paths["c1c-g5-corrective-pilot-review-gate-input.json"], "CORR2_REVIEW_V2_GATE_INVALID")

    common = {
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_append": "DENIED",
    }
    for key, expected in {**common, "status": "OPERATOR_REVIEW_COMPLETE_STRUCTURED_V2"}.items():
        if receipt.get(key) != expected:
            raise Corr2ReviewError(f"CORR2_REVIEW_V2_RECEIPT_MISMATCH:{key}")
    for key, expected in {**common, "gate_id": RETURN_GATE}.items():
        if ledger.get(key) != expected:
            raise Corr2ReviewError(f"CORR2_REVIEW_V2_LEDGER_MISMATCH:{key}")
    if gate.get("gate_id") != RETURN_GATE or gate.get("structured_review_v2_complete") is not True:
        raise Corr2ReviewError("CORR2_REVIEW_V2_GATE_MISMATCH")

    logical_ledger = dict(ledger)
    claimed_ledger = logical_ledger.pop("ledger_sha256", None)
    if claimed_ledger != pilot.logical_sha(logical_ledger):
        raise Corr2ReviewError("CORR2_REVIEW_V2_LEDGER_LOGICAL_HASH_MISMATCH")
    links = {
        "ledger_receipt": ledger.get("source_review_receipt_v2_file_sha256") == pilot.sha_file(paths["pilot-review-receipt-v2.json"]),
        "inventory_receipt": inventory.get("structured_review_v2_file_sha256") == pilot.sha_file(paths["pilot-review-receipt-v2.json"]),
        "inventory_ledger": inventory.get("structured_defect_ledger_v2_file_sha256") == pilot.sha_file(paths["pilot-defect-ledger-v2.json"]),
        "gate_receipt": gate.get("structured_review_receipt_file_sha256") == pilot.sha_file(paths["pilot-review-receipt-v2.json"]),
        "gate_ledger": gate.get("structured_defect_ledger_file_sha256") == pilot.sha_file(paths["pilot-defect-ledger-v2.json"]),
        "gate_inventory": gate.get("signed_structured_inventory_file_sha256") == pilot.sha_file(paths["signed-structured-review-evidence-inventory.json"]),
    }
    if not all(links.values()):
        raise Corr2ReviewError(f"CORR2_REVIEW_V2_HASH_LINK_MISMATCH:{sorted(key for key, value in links.items() if not value)}")

    public_key = str(base["authority"]["signing"]["public_key"])
    review_v2._verify_signature(receipt, review_v2._signature_body(receipt), public_key=public_key)
    review_v2._verify_signature(inventory, review_v2._signature_body(inventory, inventory=True), public_key=public_key)

    decisions = receipt.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 6:
        raise Corr2ReviewError("CORR2_REVIEW_V2_DECISION_COUNT_MISMATCH")
    by_id = {
        str(item.get("candidate_window_id")): dict(item)
        for item in decisions
        if isinstance(item, Mapping)
    }
    for candidate_id, finding_code in DEFERRED_OBJECTS.items():
        item = by_id.get(candidate_id)
        if not item:
            raise Corr2ReviewError(f"CORR2_DEFERRED_SOURCE_OBJECT_MISSING:{candidate_id}")
        if item.get("review_disposition") != "DEFER_PILOT_OBJECT" or item.get("finding_code") != finding_code:
            raise Corr2ReviewError(f"CORR2_DEFERRED_SOURCE_DECISION_MISMATCH:{candidate_id}")

    console_path = root / "review/console-bundle.json"
    queue_path = root / "review/queue-items.jsonl"
    fingerprints_path = root / "derived/fingerprints.jsonl"
    return {
        **base,
        "corr2_authority": authority,
        "review_v2": receipt,
        "ledger_v2": ledger,
        "inventory_v2": inventory,
        "gate_v2": gate,
        "review_v2_paths": paths,
        "console_bundle": _load_json(console_path, "CORR2_CONSOLE_BUNDLE_INVALID"),
        "queue_rows": _load_jsonl(queue_path, "CORR2_QUEUE_ROWS_INVALID"),
        "fingerprints": _load_jsonl(fingerprints_path, "CORR2_FINGERPRINT_ROWS_INVALID"),
    }


def _contexts(source: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    console = source["console_bundle"]
    details = console.get("candidate_details") if isinstance(console, Mapping) else None
    if not isinstance(details, Mapping):
        raise Corr2ReviewError("CORR2_CANDIDATE_DETAILS_UNAVAILABLE")
    queue_by_id = {
        str(item.get("candidate_window_id")): item
        for item in source["queue_rows"]
        if isinstance(item, Mapping)
    }
    fingerprint_by_id = {
        str(item.get("candidate_window_id")): item
        for item in source["fingerprints"]
        if isinstance(item, Mapping)
    }
    result: dict[str, dict[str, Any]] = {}
    for candidate_id in DEFERRED_OBJECTS:
        detail = details.get(candidate_id)
        queue = queue_by_id.get(candidate_id)
        fingerprint = fingerprint_by_id.get(candidate_id)
        if not isinstance(detail, Mapping):
            raise Corr2ReviewError(f"CORR2_CANDIDATE_DETAIL_MISSING:{candidate_id}")
        if not isinstance(queue, Mapping):
            raise Corr2ReviewError(f"CORR2_QUEUE_ITEM_MISSING:{candidate_id}")
        if not isinstance(fingerprint, Mapping):
            raise Corr2ReviewError(f"CORR2_FINGERPRINT_MISSING:{candidate_id}")
        merged_detail = dict(detail)
        merged_detail["fingerprint"] = dict(fingerprint)
        try:
            result[candidate_id] = build_exact_evidence_context(merged_detail, queue_item=queue)
        except Corr2EvidenceError as exc:
            raise Corr2ReviewError(str(exc)) from exc
    return result


def build_deferred_review_template(source: Mapping[str, Any]) -> dict[str, Any]:
    contexts = _contexts(source)
    return {
        "schema": INPUT_SCHEMA,
        "packet_id": PACKET_ID,
        "gate_id": RETURN_GATE,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "operator_id": pilot.OPERATOR_ID,
        "reviewed_at_utc": "REPLACE_WITH_UTC_TIMESTAMP_ENDING_Z",
        "source_structured_review_v2_file_sha256": pilot.sha_file(
            source["review_v2_paths"]["pilot-review-receipt-v2.json"]
        ),
        "decisions": [
            {
                "candidate_window_id": candidate_id,
                "prior_disposition": "DEFER_PILOT_OBJECT",
                "prior_finding_code": finding_code,
                "final_disposition": "REPLACE_WITH_WORKFLOW_ACCEPTED_DEFER_PILOT_OBJECT_OR_REJECT_PILOT_OBJECT",
                "notes": "REPLACE_WITH_NONEMPTY_REVIEW_NOTES",
                "evidence_references": list(exact_evidence_references(candidate_id)),
                "evidence_context_sha256": pilot.logical_sha(contexts[candidate_id]),
            }
            for candidate_id, finding_code in sorted(DEFERRED_OBJECTS.items())
        ],
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


def validate_corr2_review_input(
    review: Mapping[str, Any],
    *,
    source: Mapping[str, Any],
) -> list[dict[str, Any]]:
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
            raise Corr2ReviewError(f"CORR2_REVIEW_INPUT_MISMATCH:{key}")
    pilot.parse_utc(_required_text(review, "reviewed_at_utc", "CORR2_REVIEW_INPUT_MISSING"))
    expected_receipt_sha = pilot.sha_file(source["review_v2_paths"]["pilot-review-receipt-v2.json"])
    if review.get("source_structured_review_v2_file_sha256") != expected_receipt_sha:
        raise Corr2ReviewError("CORR2_REVIEW_INPUT_SOURCE_RECEIPT_HASH_MISMATCH")

    decisions = review.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 2:
        raise Corr2ReviewError("CORR2_REVIEW_INPUT_REQUIRES_EXACTLY_TWO_DECISIONS")
    contexts = _contexts(source)
    observed: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for item in decisions:
        if not isinstance(item, Mapping):
            raise Corr2ReviewError("CORR2_REVIEW_DECISION_INVALID")
        candidate_id = _required_text(item, "candidate_window_id", "CORR2_REVIEW_DECISION_MISSING")
        if candidate_id not in DEFERRED_OBJECTS or candidate_id in observed:
            raise Corr2ReviewError(f"CORR2_REVIEW_UNEXPECTED_OR_DUPLICATE_CANDIDATE:{candidate_id}")
        observed.add(candidate_id)
        if item.get("prior_disposition") != "DEFER_PILOT_OBJECT":
            raise Corr2ReviewError(f"CORR2_PRIOR_DISPOSITION_MISMATCH:{candidate_id}")
        if item.get("prior_finding_code") != DEFERRED_OBJECTS[candidate_id]:
            raise Corr2ReviewError(f"CORR2_PRIOR_FINDING_CODE_MISMATCH:{candidate_id}")
        context_sha = pilot.logical_sha(contexts[candidate_id])
        if item.get("evidence_context_sha256") != context_sha:
            raise Corr2ReviewError(f"CORR2_EVIDENCE_CONTEXT_HASH_MISMATCH:{candidate_id}")
        try:
            references = validate_exact_evidence_references(
                candidate_id,
                _required_strings(item, "evidence_references", "CORR2_REVIEW_DECISION_MISSING"),
            )
        except Corr2EvidenceError as exc:
            raise Corr2ReviewError(str(exc)) from exc

        disposition = _required_text(item, "final_disposition", "CORR2_REVIEW_DECISION_MISSING")
        if disposition not in ALLOWED_FINAL_DISPOSITIONS:
            raise Corr2ReviewError(f"CORR2_FINAL_DISPOSITION_INVALID:{disposition}")
        row: dict[str, Any] = {
            "candidate_window_id": candidate_id,
            "prior_disposition": "DEFER_PILOT_OBJECT",
            "prior_finding_code": DEFERRED_OBJECTS[candidate_id],
            "final_disposition": disposition,
            "notes": _required_text(item, "notes", "CORR2_REVIEW_DECISION_MISSING"),
            "evidence_references": references,
            "evidence_context_sha256": context_sha,
        }
        if disposition == "WORKFLOW_ACCEPTED":
            row["closure_basis"] = _required_text(item, "closure_basis", "CORR2_ACCEPTANCE_INCOMPLETE")
            row["acceptance_criteria"] = _required_strings(item, "acceptance_criteria", "CORR2_ACCEPTANCE_INCOMPLETE")
        elif disposition == "DEFER_PILOT_OBJECT":
            finding_code = _required_text(item, "finding_code", "CORR2_DEFER_INCOMPLETE")
            if not finding_code.startswith("PD-DEFER-"):
                raise Corr2ReviewError(f"CORR2_DEFER_CODE_INVALID:{finding_code}")
            row.update({
                "finding_code": finding_code,
                "resolution_criteria": _required_strings(item, "resolution_criteria", "CORR2_DEFER_INCOMPLETE"),
                "next_review_condition": _required_text(item, "next_review_condition", "CORR2_DEFER_INCOMPLETE"),
            })
        else:
            finding_code = _required_text(item, "finding_code", "CORR2_REJECTION_INCOMPLETE")
            if not finding_code.startswith("PD-REJECT-"):
                raise Corr2ReviewError(f"CORR2_REJECTION_CODE_INVALID:{finding_code}")
            row.update({
                "finding_code": finding_code,
                "structural_basis": _required_text(item, "structural_basis", "CORR2_REJECTION_INCOMPLETE"),
            })
        normalized.append(row)
    if observed != set(DEFERRED_OBJECTS):
        raise Corr2ReviewError(f"CORR2_REVIEW_INPUT_MISSING_OBJECTS:{sorted(set(DEFERRED_OBJECTS) - observed)}")
    return sorted(normalized, key=lambda item: item["candidate_window_id"])


def _implementation_receipt(repository_root: Path) -> tuple[Path, dict[str, Any]]:
    path = repository_root / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/corr2/C1C_G5_CORR2_IMPLEMENTATION_RECEIPT.json"
    receipt = _load_json(path, "CORR2_IMPLEMENTATION_RECEIPT_UNAVAILABLE")
    required = {
        "packet_id": PACKET_ID,
        "decision": "PASS",
        "workflow_evidence_finding": "CLOSED_BY_IMPLEMENTATION_AND_TESTS",
        "console_context_finding": "CLOSED_BY_IMPLEMENTATION_AND_TESTS",
        "second_machine_replay": "DENIED_NOT_REQUIRED",
    }
    for key, value in required.items():
        if receipt.get(key) != value:
            raise Corr2ReviewError(f"CORR2_IMPLEMENTATION_RECEIPT_MISMATCH:{key}")
    return path, receipt


def preflight(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    source = load_verified_corr2_source(repository_root, environ=environ)
    contexts = _contexts(source)
    implementation_path, _ = _implementation_receipt(repository_root)
    values = os.environ if environ is None else environ
    private_key, public_key = replay.key_paths(repository_root, values, pilot.OPERATOR_ID)
    return {
        "status": "READY_FOR_C1C_G5_CORR2_DEFERRED_OBJECT_REREVIEW",
        "packet_id": PACKET_ID,
        "return_gate": RETURN_GATE,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "deferred_candidate_ids": sorted(DEFERRED_OBJECTS),
        "exact_context_hashes": {key: pilot.logical_sha(value) for key, value in sorted(contexts.items())},
        "implementation_receipt": str(implementation_path),
        "private_key_exists": private_key.is_file() and not private_key.is_symlink(),
        "public_key_exists": public_key.is_file() and not public_key.is_symlink(),
        "second_machine_replay_required": False,
        "canonical_append": "DENIED",
    }


def prepare(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if pilot.truthy(values.get("CI")) or pilot.truthy(values.get("GITHUB_ACTIONS")):
        raise Corr2ReviewError("CORR2_OPERATOR_REVIEW_PREPARATION_PROHIBITED_IN_CI")
    source = load_verified_corr2_source(repository_root, environ=values)
    _implementation_receipt(repository_root)
    path = Path(source["root"]) / "review" / TEMPLATE_NAME
    pilot.write_json(path, build_deferred_review_template(source))
    return {
        "status": "C1C_G5_CORR2_DEFERRED_REVIEW_TEMPLATE_READY",
        "review_template": str(path),
        "deferred_candidate_ids": sorted(DEFERRED_OBJECTS),
        "next_command": "finalize --review-file <completed-corr2-review.json>",
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
        raise Corr2ReviewError("CORR2_OPERATOR_REVIEW_FINALIZATION_PROHIBITED_IN_CI")
    source = load_verified_corr2_source(repository_root, environ=values)
    implementation_path, implementation = _implementation_receipt(repository_root)
    review = _load_json(review_file.resolve(strict=True), "CORR2_REVIEW_INPUT_INVALID")
    decisions = validate_corr2_review_input(review, source=source)

    private_key, public_key_path = replay.key_paths(repository_root, values, pilot.OPERATOR_ID)
    if private_key.is_symlink() or not private_key.is_file() or public_key_path.is_symlink() or not public_key_path.is_file():
        raise Corr2ReviewError("CORR2_OPERATOR_ED25519_KEY_UNAVAILABLE_OR_UNSAFE")
    public = replay.public_key_details(public_key_path, pilot.OPERATOR_ID)
    if public["public_key_sha256"] != source["authority"]["signing"]["public_key_sha256"]:
        raise Corr2ReviewError("CORR2_OPERATOR_KEY_BINDING_MISMATCH")

    root = Path(source["root"])
    final_root = root / FINAL_DIR
    if final_root.exists():
        raise Corr2ReviewError(f"CORR2_REFUSING_TO_OVERWRITE_FINAL_REVIEW:{final_root}")
    staging = root / f".{FINAL_DIR}.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        preserved = sorted(
            [
                dict(item)
                for item in source["review_v2"]["decisions"]
                if item.get("candidate_window_id") not in DEFERRED_OBJECTS
            ],
            key=lambda item: str(item.get("candidate_window_id")),
        )
        preserved_hash = pilot.logical_sha(preserved)
        receipt_body = {
            "schema": RECEIPT_SCHEMA,
            "packet_id": PACKET_ID,
            "gate_id": RETURN_GATE,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "operator_id": pilot.OPERATOR_ID,
            "reviewed_at_utc": str(review["reviewed_at_utc"]),
            "source_structured_review_v2_file_sha256": pilot.sha_file(source["review_v2_paths"]["pilot-review-receipt-v2.json"]),
            "implementation_receipt_file_sha256": pilot.sha_file(implementation_path),
            "preserved_non_deferred_decision_count": len(preserved),
            "preserved_non_deferred_decisions_sha256": preserved_hash,
            "decisions": decisions,
            "decision_count": len(decisions),
            "second_machine_replay_performed": False,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "status": "C1C_G5_CORR2_OPERATOR_REREVIEW_COMPLETE",
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
        receipt_path = staging / "c1c-g5-corr2-review-receipt.json"
        pilot.write_json(receipt_path, receipt)

        remaining = [item for item in decisions if item["final_disposition"] == "DEFER_PILOT_OBJECT"]
        ledger_body = {
            "schema": LEDGER_SCHEMA,
            "packet_id": PACKET_ID,
            "gate_id": RETURN_GATE,
            "pilot_run_id": EXPECTED_RUN_ID,
            "source_corr2_review_receipt_file_sha256": pilot.sha_file(receipt_path),
            "workflow_evidence_finding": implementation["workflow_evidence_finding"],
            "console_context_finding": implementation["console_context_finding"],
            "deferred_object_resolutions": [
                {
                    "candidate_window_id": item["candidate_window_id"],
                    "prior_finding_code": item["prior_finding_code"],
                    "final_disposition": item["final_disposition"],
                    "status": "OPEN_DEFERRED" if item["final_disposition"] == "DEFER_PILOT_OBJECT" else "CLOSED_BY_OPERATOR_REREVIEW",
                }
                for item in decisions
            ],
            "remaining_deferred_object_count": len(remaining),
            "contract_changes_required": bool(remaining),
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "status": "CORR2_CLOSURE_READY" if not remaining else "CORR2_REVIEW_COMPLETE_REMAINS_DEFERRED",
        }
        ledger = {**ledger_body, "ledger_sha256": pilot.logical_sha(ledger_body)}
        ledger_path = staging / "c1c-g5-corr2-closure-ledger.json"
        pilot.write_json(ledger_path, ledger)

        inventory_body = {
            "schema": INVENTORY_SCHEMA,
            "packet_id": PACKET_ID,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "source_structured_review_v2_file_sha256": pilot.sha_file(source["review_v2_paths"]["pilot-review-receipt-v2.json"]),
            "corr2_review_receipt_file_sha256": pilot.sha_file(receipt_path),
            "corr2_closure_ledger_file_sha256": pilot.sha_file(ledger_path),
            "implementation_receipt_file_sha256": pilot.sha_file(implementation_path),
            "preserved_non_deferred_decisions_sha256": preserved_hash,
            "operator_id": pilot.OPERATOR_ID,
            "signing_binding_id": pilot.SIGNING_BINDING_ID,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
        }
        inventory_signature, inventory_signature_sha = replay.sign_and_verify(
            private_key=private_key,
            public_key=public["public_key"],
            operator_id=pilot.OPERATOR_ID,
            payload=pilot.canonical_bytes(inventory_body),
        )
        inventory = {
            **inventory_body,
            "inventory_id": f"PD.PILOT.CORR2.EVIDENCE.{pilot.logical_sha(inventory_body)[:24]}",
            "signature_algorithm": "ED25519",
            "signature_format": replay.SIGNATURE_FORMAT,
            "signature_namespace": replay.SIGNATURE_NAMESPACE,
            "signed_payload_sha256": pilot.logical_sha(inventory_body),
            "signature_sha256": inventory_signature_sha,
            "signature": inventory_signature,
            "status": "SIGNED_C1C_G5_CORR2_EVIDENCE_COMPLETE",
        }
        inventory_path = staging / "signed-c1c-g5-corr2-evidence-inventory.json"
        pilot.write_json(inventory_path, inventory)

        recommendation = "PASS" if not remaining else "DEFER"
        gate_input = {
            "schema": GATE_INPUT_SCHEMA,
            "gate_id": RETURN_GATE,
            "packet_id": PACKET_ID,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "active_c2_release_id": source["corr2_authority"]["bundle"]["current_authority"]["active_c2_release_id"],
            "active_c2_manifest_id": source["corr2_authority"]["bundle"]["current_authority"]["active_c2_manifest_id"],
            "selector_id": source["corr2_authority"]["bundle"]["current_authority"]["selector_id"],
            "machine_rerun_valid": True,
            "second_machine_replay_performed": False,
            "structured_review_v2_preserved": True,
            "corr2_operator_rereview_complete": True,
            "workflow_evidence_finding": implementation["workflow_evidence_finding"],
            "console_context_finding": implementation["console_context_finding"],
            "remaining_deferred_object_count": len(remaining),
            "corr2_review_receipt_file_sha256": pilot.sha_file(receipt_path),
            "corr2_closure_ledger_file_sha256": pilot.sha_file(ledger_path),
            "signed_corr2_inventory_file_sha256": pilot.sha_file(inventory_path),
            "recommended_decision": recommendation,
            "operator_approval_required": True,
            "allowed_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "status": "C1C_G5_CORRECTIVE_PILOT_REVIEW_FINAL_GATE_INPUT_READY",
        }
        gate_path = staging / "c1c-g5-corrective-pilot-review-final-gate-input.json"
        pilot.write_json(gate_path, gate_input)
        staging.rename(final_root)
        return {
            "status": "C1C_G5_CORR2_OPERATOR_REREVIEW_COMPLETE_FINAL_GATE_READY",
            "operator_review_root": str(final_root),
            "recommended_decision": recommendation,
            "remaining_deferred_object_count": len(remaining),
            "next_gate": RETURN_GATE,
            "second_machine_replay_performed": False,
            "canonical_append": "DENIED",
        }
    except Exception as exc:
        if staging.exists():
            quarantine = root / "quarantine" / f"C1C-G5-CORR2.{uuid.uuid4().hex[:8]}"
            quarantine.parent.mkdir(parents=True, exist_ok=True)
            staging.rename(quarantine)
        if isinstance(exc, Corr2ReviewError):
            raise
        raise Corr2ReviewError(f"CORR2_FINALIZATION_FAILURE:{exc}") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="C1C-G5 CORR2 deferred-object operator re-review.")
    result.add_argument("command", choices=("preflight", "prepare", "finalize"))
    result.add_argument("--repository-root", type=Path, default=Path.cwd())
    result.add_argument("--review-file", type=Path, default=None)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "preflight":
            result = preflight(repository_root)
        elif arguments.command == "prepare":
            result = prepare(repository_root)
        else:
            if arguments.review_file is None:
                raise Corr2ReviewError("CORR2_FINALIZE_REQUIRES_REVIEW_FILE")
            result = finalize(repository_root, review_file=arguments.review_file)
    except (Corr2ReviewError, review_v2.CorrectiveReviewV2Error, pilot.PilotDiscoveryError, replay.ReplayAcceptanceError) as exc:
        print(f"C1C-G5-CORR2 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
