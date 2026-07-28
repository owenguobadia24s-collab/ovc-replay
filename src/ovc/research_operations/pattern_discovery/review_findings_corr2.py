from __future__ import annotations

import argparse
import json
import os
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.research_operations.prospective_source import operator_replay_acceptance as replay

from . import pilot_discovery as pilot
from .review_findings_corr2_model import (
    PACKET_ID,
    RETURN_GATE,
    EXPECTED_RUN_ID,
    EXPECTED_NAMESPACE,
    REVIEW_INPUT_SCHEMA,
    REVIEW_RECEIPT_SCHEMA,
    INVENTORY_SCHEMA,
    RETURN_GATE_SCHEMA,
    FINAL_DIR,
    Corr2Error,
    build_corr2_console_rows,
    DEFERRED_FINDINGS,
    parse_evidence_reference,
    build_exact_evidence_context,
)
from .review_findings_corr2_review import build_rereview_template, validate_rereview_input, build_closure_ledger
from .review_findings_corr2_evidence import load_context, preflight, prepare, _load_json

def finalize(
    repository_root: Path,
    *,
    review_file: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if pilot.truthy(values.get("CI")) or pilot.truthy(values.get("GITHUB_ACTIONS")):
        raise Corr2Error("CORR2_OPERATOR_REREVIEW_FINALIZATION_PROHIBITED_IN_CI")
    context = load_context(repository_root, environ=values)
    root = Path(context["root"])
    final_root = root / FINAL_DIR
    if final_root.exists():
        raise Corr2Error(f"REFUSING_TO_OVERWRITE_CORR2_REREVIEW:{final_root}")
    review = _load_json(review_file.resolve(strict=True), "INVALID_CORR2_REREVIEW")
    decisions = validate_rereview_input(review, context["contexts"])

    private_key, public_key_path = replay.key_paths(repository_root, values, pilot.OPERATOR_ID)
    if private_key.is_symlink() or not private_key.is_file() or public_key_path.is_symlink() or not public_key_path.is_file():
        raise Corr2Error("EXACT_OPERATOR_ED25519_KEY_UNAVAILABLE_OR_UNSAFE")
    public = replay.public_key_details(public_key_path, pilot.OPERATOR_ID)
    if public["public_key_sha256"] != context["evidence"]["authority"]["signing"]["public_key_sha256"]:
        raise Corr2Error("OPERATOR_KEY_DOES_NOT_MATCH_SIGNING_BINDING")

    staging = root / f".{FINAL_DIR}.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        receipt_body = {
            "schema": REVIEW_RECEIPT_SCHEMA,
            "packet_id": PACKET_ID,
            "gate_id": RETURN_GATE,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "operator_id": pilot.OPERATOR_ID,
            "reviewed_at_utc": str(review["reviewed_at_utc"]),
            "decisions": decisions,
            "decision_count": len(decisions),
            "source_review_contract": REVIEW_INPUT_SCHEMA,
            "source_structured_review_inventory_file_sha256": pilot.sha_file(context["review_v2"]["paths"]["inventory"]),
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
        receipt_path = staging / "deferred-rereview-receipt-corr2.json"
        pilot.write_json(receipt_path, receipt)

        ledger = build_closure_ledger(decisions, receipt_sha256=pilot.sha_file(receipt_path))
        ledger_path = staging / "c1c-g5-corr2-closure-ledger.json"
        pilot.write_json(ledger_path, ledger)

        inventory_body = {
            "schema": INVENTORY_SCHEMA,
            "packet_id": PACKET_ID,
            "gate_id": RETURN_GATE,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "source_pilot_run_file_sha256": pilot.sha_file(context["evidence"]["paths"]["run"]),
            "source_output_manifest_file_sha256": pilot.sha_file(context["evidence"]["paths"]["manifest"]),
            "source_structured_review_v2_file_sha256": pilot.sha_file(context["review_v2"]["paths"]["receipt"]),
            "source_structured_review_inventory_file_sha256": pilot.sha_file(context["review_v2"]["paths"]["inventory"]),
            "corr2_review_receipt_file_sha256": pilot.sha_file(receipt_path),
            "corr2_closure_ledger_file_sha256": pilot.sha_file(ledger_path),
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

        gate_input = {
            "schema": RETURN_GATE_SCHEMA,
            "gate_id": RETURN_GATE,
            "packet_id": PACKET_ID,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "active_c2_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",
            "active_c2_manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1",
            "selector_id": "SELECTOR.OPT-B.C2.GBPUSD.v2",
            "machine_rerun_valid": True,
            "structured_review_v2_complete": True,
            "corr2_rereview_complete": True,
            "corr2_rereview_receipt_file_sha256": pilot.sha_file(receipt_path),
            "corr2_closure_ledger_file_sha256": pilot.sha_file(ledger_path),
            "signed_corr2_inventory_file_sha256": pilot.sha_file(inventory_path),
            "unresolved_finding_count": 0,
            "contract_changes_required": False,
            "second_machine_replay_required": False,
            "operator_approval_required": True,
            "allowed_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
            "recommended_decision": "PASS",
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_discovery_processing": "DENIED",
            "canonical_append": "DENIED",
            "status": "C1C_G5_CORRECTIVE_PILOT_REVIEW_RETURN_GATE_INPUT_READY",
        }
        gate_path = staging / "c1c-g5-corrective-pilot-review-return-gate-input.json"
        pilot.write_json(gate_path, gate_input)
        staging.rename(final_root)
        return {
            "status": "C1C_G5_CORR2_COMPLETE_RETURN_GATE_INPUT_READY",
            "packet_id": PACKET_ID,
            "pilot_run_id": EXPECTED_RUN_ID,
            "operator_review_root": str(final_root),
            "unresolved_finding_count": 0,
            "next_gate": RETURN_GATE,
            "second_machine_replay_required": False,
            "canonical_append": "DENIED",
        }
    except Exception as exc:
        if staging.exists():
            quarantine = root / "quarantine" / f"C1C-G5-CORR2.{uuid.uuid4().hex[:8]}"
            quarantine.parent.mkdir(parents=True, exist_ok=True)
            staging.rename(quarantine)
        if isinstance(exc, Corr2Error):
            raise
        raise Corr2Error(f"UNEXPECTED_CORR2_FAILURE:{exc}") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="C1C-G5 CORR2 exact-context review of the two deferred Pilot Discovery objects.")
    result.add_argument("command", choices=("preflight", "prepare", "finalize"))
    result.add_argument("--repository-root", type=Path, default=Path.cwd())
    result.add_argument("--pilot-run-id", default=EXPECTED_RUN_ID)
    result.add_argument("--review-file", type=Path, default=None)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.pilot_run_id != EXPECTED_RUN_ID:
        raise Corr2Error(f"EXPACT_CORRECTIVE_RUN_REQUIRED:{EXPECTED_RUN_ID}")
    if args.command == "preflight":
        result = preflight(args.repository_root)
    elif args.command == "prepare":
        result = prepare(args.repository_root)
    else:
        if args.review_file is None:
            raise Corr2Error("--review-file is required for finalize")
        result = finalize(args.repository_root, review_file=args.review_file)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
