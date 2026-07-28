from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from . import pilot_corrective_review_v2 as structured
from . import pilot_discovery as pilot
from .review_findings_corr2_model import (
    PACKET_ID,
    RETURN_GATE,
    EXPECTED_RUN_ID,
    EXPECTED_NAMESPACE,
    TEMPLATE_NAME,
    CONTEXT_NAME,
    DEFERRED_FINDINGS,
    Corr2Error,
    build_exact_evidence_context,
)
from .review_findings_corr2_review import build_rereview_template

def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Corr2Error(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise Corr2Error(f"{code}:{path}")
    return value


def _load_jsonl(path: Path, code: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise Corr2Error(f"{code}:{path}:{number}")
                rows.append(value)
    except Corr2Error:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Corr2Error(f"{code}:{path}") from exc
    return rows


def _load_verified_review_v2(root: Path, evidence: Mapping[str, Any]) -> dict[str, Any]:
    review_root = root / "operator-review-v2"
    receipt_path = pilot.safe_file(review_root, "pilot-review-receipt-v2.json")
    ledger_path = pilot.safe_file(review_root, "pilot-defect-ledger-v2.json")
    inventory_path = pilot.safe_file(review_root, "signed-structured-review-evidence-inventory.json")
    gate_path = pilot.safe_file(review_root, "c1c-g5-corrective-pilot-review-gate-input.json")
    receipt = _load_json(receipt_path, "INVALID_STRUCTURED_REVIEW_RECEIPT_V2")
    ledger = _load_json(ledger_path, "INVALID_STRUCTURED_REVIEW_LEDGER_V2")
    inventory = _load_json(inventory_path, "INVALID_STRUCTURED_REVIEW_INVENTORY_V2")
    gate = _load_json(gate_path, "INVALID_STRUCTURED_REVIEW_GATE_INPUT_V2")
    common = {
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_append": "DENIED",
    }
    for name, record in (("receipt", receipt), ("ledger", ledger), ("inventory", inventory), ("gate", gate)):
        for key, expected in common.items():
            if record.get(key) != expected:
                raise Corr2Error(f"STRUCTURED_REVIEW_V2_IDENTITY_MISMATCH:{name}:{key}")
    if gate.get("structured_review_receipt_file_sha256") != pilot.sha_file(receipt_path):
        raise Corr2Error("STRUCTURED_REVIEW_RECEIPT_HASH_MISMATCH")
    if gate.get("structured_defect_ledger_file_sha256") != pilot.sha_file(ledger_path):
        raise Corr2Error("STRUCTURED_REVIEW_LEDGER_HASH_MISMATCH")
    if gate.get("signed_structured_inventory_file_sha256") != pilot.sha_file(inventory_path):
        raise Corr2Error("STRUCTURED_REVIEW_INVENTORY_HASH_MISMATCH")
    if inventory.get("structured_review_v2_file_sha256") != pilot.sha_file(receipt_path):
        raise Corr2Error("INVENTORY_RECEIPT_HASH_MISMATCH")
    if inventory.get("structured_defect_ledger_v2_file_sha256") != pilot.sha_file(ledger_path):
        raise Corr2Error("INVENTORY_LEDGER_HASH_MISMATCH")
    public_key = str(evidence["authority"]["signing"]["public_key"])
    structured._verify_signature(receipt, structured._signature_body(receipt), public_key=public_key)
    structured._verify_signature(inventory, structured._signature_body(inventory, inventory=True), public_key=public_key)
    decisions = receipt.get("decisions")
    if not isinstance(decisions, list):
        raise Corr2Error("STRUCTURED_REVIEW_V2_DECISIONS_INVALID")
    deferred = {
        str(item.get("candidate_window_id")): str(item.get("finding_code"))
        for item in decisions
        if isinstance(item, Mapping) and item.get("review_disposition") == "DEFER_PILOT_OBJECT"
    }
    if deferred != DEFERRED_FINDINGS:
        raise Corr2Error(f"EXACT_DEFERRED_OBJECT_SET_REQUIRED:{sorted(deferred)}")
    return {
        "root": review_root,
        "receipt": receipt,
        "ledger": ledger,
        "inventory": inventory,
        "gate": gate,
        "paths": {
            "receipt": receipt_path,
            "ledger": ledger_path,
            "inventory": inventory_path,
            "gate": gate_path,
        },
    }


def load_context(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    evidence = structured.load_and_verify_evidence(repository_root, environ=values)
    root = Path(evidence["root"])
    review_v2 = _load_verified_review_v2(root, evidence)
    queue_items = _load_jsonl(pilot.safe_file(root, "review/queue-items.jsonl"), "INVALID_QUEUE_ITEMS")
    console_bundle = _load_json(pilot.safe_file(root, "review/console-bundle.json"), "INVALID_CONSOLE_BUNDLE")
    candidate_details = console_bundle.get("candidate_details")
    if not isinstance(candidate_details, Mapping):
        raise Corr2Error("CONSOLE_BUNDLE_CANDIDATE_DETAILS_INVALID")
    fingerprints = _load_jsonl(pilot.safe_file(root, "derived/fingerprints.jsonl"), "INVALID_FINGERPRINTS")
    cluster_versions = _load_jsonl(pilot.safe_file(root, "derived/cluster-versions.jsonl"), "INVALID_CLUSTER_VERSIONS")
    contexts = [
        build_exact_evidence_context(
            queue_items=queue_items,
            candidate_details=candidate_details,
            fingerprints=fingerprints,
            cluster_versions=cluster_versions,
            candidate_id=candidate_id,
        )
        for candidate_id in sorted(DEFERRED_FINDINGS)
    ]
    return {
        "evidence": evidence,
        "review_v2": review_v2,
        "contexts": contexts,
        "root": root,
    }



def preflight(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    context = load_context(repository_root, environ=environ)
    return {
        "status": "READY_FOR_C1C_G5_CORR2_DEFERRED_OBJECT_REREVIEW",
        "packet_id": PACKET_ID,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "deferred_candidate_ids": sorted(DEFERRED_FINDINGS),
        "context_statuses": {
            item["candidate_window_id"]: item["structural_comparison_status"]
            for item in context["contexts"]
        },
        "second_machine_replay_required": False,
        "canonical_append": "DENIED",
        "next_gate": RETURN_GATE,
    }


def prepare(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if pilot.truthy(values.get("CI")) or pilot.truthy(values.get("GITHUB_ACTIONS")):
        raise Corr2Error("CORR2_OPERATOR_REREVIEW_PREPARATION_PROHIBITED_IN_CI")
    context = load_context(repository_root, environ=values)
    review_root = Path(context["root"]) / "review"
    template_path = pilot.safe_file(review_root, TEMPLATE_NAME)
    context_path = pilot.safe_file(review_root, CONTEXT_NAME)
    if template_path.exists() or context_path.exists():
        raise Corr2Error(f"REFUSING_TO_OVERWRITE_CORR2_REVIEW_PREPARATION:{review_root}")
    context_record = {
        "schema": "ovc-c1c-g5-corr2-evidence-context-bundle/v1",
        "packet_id": PACKET_ID,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "contexts": list(context["contexts"]),
        "context_count": len(context["contexts"]),
        "read_only": True,
        "source_artifacts_mutated": False,
        "second_machine_replay_required": False,
        "canonical_append": "DENIED",
    }
    pilot.write_json(context_path, context_record)
    pilot.write_json(template_path, build_rereview_template(context["contexts"]))
    return {
        "status": "C1C_G5_CORR2_REREVIEW_TEMPLATE_READY",
        "packet_id": PACKET_ID,
        "pilot_run_id": EXPECTED_RUN_ID,
        "context_file": str(context_path),
        "review_template": str(template_path),
        "next_command": f"finalize --pilot-run-id {EXPECTED_RUN_ID} --review-file <completed-corr2-review.json>",
        "second_machine_replay_required": False,
        "canonical_append": "DENIED",
    }


