from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.research_operations.prospective_source import operator_replay_acceptance as replay

from . import pilot_corrective_rerun as corrective
from . import pilot_discovery as pilot
from .review_corrections import REVIEW_SCHEMA_V2, ReviewCorrectionError, validate_review_input_v2


EXPECTED_RUN_ID = "PD.PILOT.RUN.96c16f11717e787f971851ee"
EXPECTED_NAMESPACE = corrective.CORRECTIVE_PILOT_NAMESPACE
EXPECTED_CODE_COMMIT = "0c687101e031b404b3994c8bb96d65b177f97743"
NEXT_GATE = corrective.CORRECTIVE_NEXT_GATE
RECEIPT_SCHEMA_V2 = "ovc-pd-wp5-pilot-review-receipt/v2"
LEDGER_SCHEMA_V2 = "ovc-c1c-g5-corrective-review-defect-ledger/v2"
INVENTORY_SCHEMA_V2 = "ovc-c1c-g5-corrective-review-evidence-inventory/v2"
GATE_INPUT_SCHEMA_V2 = "ovc-c1c-g5-corrective-pilot-review-gate-input/v2"
TEMPLATE_NAME = "pilot-review-input.v2.template.json"
FINAL_DIR = "operator-review-v2"

_SIGNATURE_FIELDS = {
    "signature_algorithm",
    "signature_format",
    "signature_namespace",
    "signed_payload_sha256",
    "signature_sha256",
    "signature",
}


class CorrectiveReviewV2Error(RuntimeError):
    pass


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorrectiveReviewV2Error(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise CorrectiveReviewV2Error(f"{code}:{path}")
    return value


def _require(source: Mapping[str, Any], expected: Mapping[str, Any], code: str) -> None:
    for key, value in expected.items():
        if source.get(key) != value:
            raise CorrectiveReviewV2Error(f"{code}:{key}")


def _signature_body(record: Mapping[str, Any], *, inventory: bool = False) -> dict[str, Any]:
    excluded = set(_SIGNATURE_FIELDS)
    if inventory:
        excluded.update({"inventory_id", "operator_id", "signing_binding_id", "status"})
    return {key: value for key, value in record.items() if key not in excluded}


def _verify_signature(record: Mapping[str, Any], body: Mapping[str, Any], *, public_key: str) -> None:
    payload = pilot.canonical_bytes(body)
    if pilot.logical_sha(body) != record.get("signed_payload_sha256"):
        raise CorrectiveReviewV2Error("SIGNED_PAYLOAD_SHA256_MISMATCH")
    signature = str(record.get("signature") or "")
    if hashlib.sha256(signature.encode("utf-8")).hexdigest() != record.get("signature_sha256"):
        raise CorrectiveReviewV2Error("SIGNATURE_FILE_SHA256_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="c1c-g5-review-v2-verify-") as temporary:
        root = Path(temporary)
        signature_path = root / "payload.sig"
        allowed = root / "allowed_signers"
        signature_path.write_text(signature, encoding="utf-8")
        allowed.write_text(
            f'{pilot.OPERATOR_ID} namespaces="{replay.SIGNATURE_NAMESPACE}" {public_key}\n',
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                replay.ssh_keygen(),
                "-Y",
                "verify",
                "-f",
                str(allowed),
                "-I",
                pilot.OPERATOR_ID,
                "-n",
                replay.SIGNATURE_NAMESPACE,
                "-s",
                str(signature_path),
            ],
            input=payload,
            capture_output=True,
        )
        if result.returncode != 0:
            raise CorrectiveReviewV2Error(
                "ED25519_SIGNATURE_INVALID:"
                + result.stderr.decode("utf-8", errors="replace").strip()
            )


def _run_root(repository_root: Path, values: Mapping[str, str]) -> tuple[Path, dict[str, Any]]:
    corrective.configure()
    pilot.repository_state(repository_root)
    authority = corrective.load_corrective_authority(repository_root)
    replay.verify_compute_run(repository_root, values)
    root = (
        pilot.external_root(repository_root, values)
        / "pattern-discovery"
        / "pilot"
        / EXPECTED_NAMESPACE
        / EXPECTED_RUN_ID
    )
    if not root.is_dir():
        raise CorrectiveReviewV2Error(f"CORRECTIVE_PILOT_RUN_UNAVAILABLE:{root}")
    return root, authority


def load_and_verify_evidence(
    repository_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    root, authority = _run_root(repository_root, values)
    run_path = pilot.safe_file(root, "pilot-run.json")
    manifest_path = pilot.safe_file(root, "output-manifest.json")
    review_path = pilot.safe_file(root, "operator-review/pilot-review-receipt.json")
    ledger_path = pilot.safe_file(root, "operator-review/pilot-defect-ledger.json")
    inventory_path = pilot.safe_file(root, "operator-review/signed-pilot-evidence-inventory.json")
    gate_path = pilot.safe_file(root, "operator-review/pd-g5p-gate-input.json")

    run = _load_json(run_path, "INVALID_CORRECTIVE_PILOT_RUN")
    manifest = _load_json(manifest_path, "INVALID_CORRECTIVE_OUTPUT_MANIFEST")
    review = _load_json(review_path, "INVALID_CORRECTIVE_REVIEW_V1")
    ledger = _load_json(ledger_path, "INVALID_CORRECTIVE_LEDGER_V1")
    inventory = _load_json(inventory_path, "INVALID_CORRECTIVE_INVENTORY_V1")
    gate = _load_json(gate_path, "INVALID_CORRECTIVE_GATE_INPUT_V1")

    common = {
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_append": "DENIED",
    }
    _require(run, {**common, "authority_gate": "C1C-G5", "next_gate": NEXT_GATE, "code_commit": EXPECTED_CODE_COMMIT}, "RUN_IDENTITY_MISMATCH")
    _require(manifest, common, "MANIFEST_IDENTITY_MISMATCH")
    _require(review, {**common, "status": "OPERATOR_REVIEW_COMPLETE"}, "REVIEW_IDENTITY_MISMATCH")
    _require(inventory, {**common, "status": "SIGNED_PILOT_EVIDENCE_COMPLETE"}, "INVENTORY_IDENTITY_MISMATCH")
    _require(gate, {**common, "gate_id": NEXT_GATE, "operator_review_complete": True}, "GATE_INPUT_IDENTITY_MISMATCH")

    logical_manifest = dict(manifest)
    claimed_manifest = logical_manifest.pop("output_manifest_sha256", None)
    if claimed_manifest != pilot.logical_sha(logical_manifest):
        raise CorrectiveReviewV2Error("OUTPUT_MANIFEST_LOGICAL_SHA256_MISMATCH")
    if gate.get("pilot_output_manifest_sha256") != claimed_manifest:
        raise CorrectiveReviewV2Error("GATE_OUTPUT_MANIFEST_MISMATCH")
    if run.get("derived_bundle_sha256") != run.get("deterministic_rerun_sha256") or not run.get("deterministic_rerun_match"):
        raise CorrectiveReviewV2Error("CORRECTIVE_RERUN_NOT_DETERMINISTIC")

    expected_hashes = {
        "pilot_run_file_sha256": pilot.sha_file(run_path),
        "pilot_output_manifest_file_sha256": pilot.sha_file(manifest_path),
        "pilot_review_receipt_file_sha256": pilot.sha_file(review_path),
        "pilot_defect_ledger_file_sha256": pilot.sha_file(ledger_path),
    }
    _require(inventory, expected_hashes, "SIGNED_INVENTORY_FILE_HASH_MISMATCH")
    if gate.get("signed_pilot_evidence_inventory_file_sha256") != pilot.sha_file(inventory_path):
        raise CorrectiveReviewV2Error("GATE_INVENTORY_FILE_HASH_MISMATCH")

    public_key = str(authority["signing"]["public_key"])
    _verify_signature(run, _signature_body(run), public_key=public_key)
    _verify_signature(review, _signature_body(review), public_key=public_key)
    _verify_signature(inventory, _signature_body(inventory, inventory=True), public_key=public_key)

    decisions = review.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 6:
        raise CorrectiveReviewV2Error("CORRECTIVE_REVIEW_DECISION_COUNT_MISMATCH")
    candidate_ids = [str(item.get("candidate_window_id") or "") for item in decisions if isinstance(item, Mapping)]
    if len(set(candidate_ids)) != 6 or any(not item.startswith("PDPILOT-CANDIDATE-") for item in candidate_ids):
        raise CorrectiveReviewV2Error("CORRECTIVE_REVIEW_CANDIDATE_IDENTITY_INVALID")

    return {
        "root": root,
        "authority": authority,
        "run": run,
        "manifest": manifest,
        "review_v1": review,
        "ledger_v1": ledger,
        "inventory_v1": inventory,
        "gate_v1": gate,
        "paths": {
            "run": run_path,
            "manifest": manifest_path,
            "review_v1": review_path,
            "ledger_v1": ledger_path,
            "inventory_v1": inventory_path,
            "gate_v1": gate_path,
        },
    }


def _decision_template(source: Mapping[str, Any]) -> dict[str, Any]:
    disposition = str(source.get("review_disposition") or "")
    common: dict[str, Any] = {
        "candidate_window_id": str(source.get("candidate_window_id") or ""),
        "review_disposition": disposition,
        "notes": "REPLACE_WITH_NONEMPTY_REVIEW_NOTES",
        "evidence_references": ["REPLACE_WITH_EXACT_EVIDENCE_REFERENCE"],
        "ui_friction_codes": [],
    }
    if disposition == "WORKFLOW_ACCEPTED":
        common.update({
            "acceptance_basis": "REPLACE_WITH_NONEMPTY_ACCEPTANCE_BASIS",
            "acceptance_criteria": ["REPLACE_WITH_ACCEPTANCE_CRITERION"],
        })
    elif disposition == "FLAG_WORKFLOW_DEFECT":
        common.update({
            "finding_code": "PD-WF-REPLACE-WITH-CODE",
            "affected_component": "REPLACE_WITH_AFFECTED_COMPONENT",
            "actual_behavior": "REPLACE_WITH_ACTUAL_BEHAVIOR",
            "expected_behavior": "REPLACE_WITH_EXPECTED_BEHAVIOR",
            "reproduction_steps": ["REPLACE_WITH_REPRODUCTION_STEP"],
            "acceptance_criteria": ["REPLACE_WITH_ACCEPTANCE_CRITERION"],
        })
    elif disposition == "FLAG_UI_FRICTION":
        common.update({
            "finding_code": "PD-UI-REPLACE-WITH-CODE",
            "ui_friction_codes": ["PD-UI-REPLACE-WITH-CODE"],
            "affected_component": "REPLACE_WITH_AFFECTED_COMPONENT",
            "affected_console_surface": "REPLACE_WITH_CONSOLE_SURFACE",
            "actual_behavior": "REPLACE_WITH_ACTUAL_BEHAVIOR",
            "expected_behavior": "REPLACE_WITH_EXPECTED_BEHAVIOR",
            "reproduction_steps": ["REPLACE_WITH_REPRODUCTION_STEP"],
            "acceptance_criteria": ["REPLACE_WITH_ACCEPTANCE_CRITERION"],
        })
    elif disposition == "DEFER_PILOT_OBJECT":
        common.update({
            "finding_code": "PD-DEFER-REPLACE-WITH-CODE",
            "resolution_criteria": ["REPLACE_WITH_RESOLUTION_CRITERION"],
            "next_review_condition": "REPLACE_WITH_NEXT_REVIEW_CONDITION",
        })
    elif disposition == "REJECT_PILOT_OBJECT":
        common.update({
            "finding_code": "PD-REJECT-REPLACE-WITH-CODE",
            "structural_basis": "REPLACE_WITH_NONSEMANTIC_STRUCTURAL_BASIS",
        })
    else:
        raise CorrectiveReviewV2Error(f"UNSUPPORTED_REVIEW_DISPOSITION:{disposition}")
    return common


def build_review_template_v2(review_v1: Mapping[str, Any]) -> dict[str, Any]:
    decisions = review_v1.get("decisions")
    if not isinstance(decisions, list):
        raise CorrectiveReviewV2Error("V1_REVIEW_DECISIONS_INVALID")
    return {
        "schema": REVIEW_SCHEMA_V2,
        "pilot_run_id": EXPECTED_RUN_ID,
        "operator_id": pilot.OPERATOR_ID,
        "reviewed_at_utc": "REPLACE_WITH_UTC_TIMESTAMP_ENDING_Z",
        "decisions": [_decision_template(item) for item in decisions if isinstance(item, Mapping)],
    }


def _reject_placeholders(value: Any, path: str = "review") -> None:
    if isinstance(value, str):
        if not value.strip() or "REPLACE_WITH" in value:
            raise CorrectiveReviewV2Error(f"STRUCTURED_REVIEW_PLACEHOLDER_OR_EMPTY:{path}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_placeholders(item, f"{path}[{index}]")
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _reject_placeholders(item, f"{path}.{key}")


def preflight(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    evidence = load_and_verify_evidence(repository_root, environ=environ)
    review = evidence["review_v1"]
    incomplete = [
        str(item.get("candidate_window_id"))
        for item in review["decisions"]
        if item.get("review_disposition") != "WORKFLOW_ACCEPTED" and (
            not str(item.get("notes") or "").strip()
            or (item.get("review_disposition") == "FLAG_UI_FRICTION" and not item.get("ui_friction_codes"))
        )
    ]
    return {
        "status": "READY_FOR_C1C_G5_STRUCTURED_V2_REREVIEW",
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "machine_rerun_valid": True,
        "signed_v1_review_preserved": True,
        "v1_review_incomplete_candidate_ids": incomplete,
        "second_machine_replay_required": False,
        "next_gate": NEXT_GATE,
        "canonical_append": "DENIED",
    }


def prepare(repository_root: Path, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if pilot.truthy(values.get("CI")) or pilot.truthy(values.get("GITHUB_ACTIONS")):
        raise CorrectiveReviewV2Error("STRUCTURED_OPERATOR_REVIEW_PREPARATION_PROHIBITED_IN_CI")
    evidence = load_and_verify_evidence(repository_root, environ=values)
    path = evidence["root"] / "review" / TEMPLATE_NAME
    pilot.write_json(path, build_review_template_v2(evidence["review_v1"]))
    return {
        "status": "STRUCTURED_V2_REVIEW_TEMPLATE_READY",
        "pilot_run_id": EXPECTED_RUN_ID,
        "review_template": str(path),
        "next_command": f"finalize --pilot-run-id {EXPECTED_RUN_ID} --review-file <completed-v2-review.json>",
        "second_machine_replay_required": False,
        "canonical_append": "DENIED",
    }


def _build_defect_ledger(decisions: Sequence[Mapping[str, Any]], *, receipt_sha256: str) -> dict[str, Any]:
    defects = [dict(item) for item in decisions if item.get("review_disposition") != "WORKFLOW_ACCEPTED" or item.get("ui_friction_codes")]
    body = {
        "schema": LEDGER_SCHEMA_V2,
        "gate_id": NEXT_GATE,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "source_review_receipt_v2_file_sha256": receipt_sha256,
        "defects": defects,
        "defect_count": len(defects),
        "contract_changes_required": bool(defects),
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_append": "DENIED",
        "status": "STRUCTURED_V2_REVIEW_COMPLETE_WITH_FINDINGS" if defects else "STRUCTURED_V2_REVIEW_COMPLETE_NO_FINDINGS",
    }
    return {**body, "ledger_sha256": pilot.logical_sha(body)}


def finalize(
    repository_root: Path,
    *,
    review_file: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if pilot.truthy(values.get("CI")) or pilot.truthy(values.get("GITHUB_ACTIONS")):
        raise CorrectiveReviewV2Error("STRUCTURED_OPERATOR_REVIEW_FINALIZATION_PROHIBITED_IN_CI")
    evidence = load_and_verify_evidence(repository_root, environ=values)
    root = evidence["root"]
    final_root = root / FINAL_DIR
    if final_root.exists():
        raise CorrectiveReviewV2Error(f"REFUSING_TO_OVERWRITE_STRUCTURED_REVIEW:{final_root}")
    review = _load_json(review_file.resolve(strict=True), "INVALID_STRUCTURED_REVIEW_V2")
    _reject_placeholders(review)
    expected_ids = [str(item["candidate_window_id"]) for item in evidence["review_v1"]["decisions"]]
    markings = {
        "research_role": pilot.RESEARCH_ROLE,
        "operation_mode": pilot.OPERATION_MODE,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_discovery_population": False,
        "live_prospective": False,
        "identity_namespace": EXPECTED_NAMESPACE,
    }
    try:
        decisions = validate_review_input_v2(
            review,
            expected_candidate_ids=expected_ids,
            pilot_run_id=EXPECTED_RUN_ID,
            pilot_markings=markings,
        )
    except ReviewCorrectionError as exc:
        raise CorrectiveReviewV2Error(str(exc)) from exc

    private_key, public_key_path = replay.key_paths(repository_root, values, pilot.OPERATOR_ID)
    if private_key.is_symlink() or not private_key.is_file() or public_key_path.is_symlink() or not public_key_path.is_file():
        raise CorrectiveReviewV2Error("EXACT_OPERATOR_ED25519_KEY_UNAVAILABLE_OR_UNSAFE")
    public = replay.public_key_details(public_key_path, pilot.OPERATOR_ID)
    if public["public_key_sha256"] != evidence["authority"]["signing"]["public_key_sha256"]:
        raise CorrectiveReviewV2Error("OPERATOR_KEY_DOES_NOT_MATCH_SIGNING_BINDING")

    staging = root / f".{FINAL_DIR}.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        receipt_body = {
            "schema": RECEIPT_SCHEMA_V2,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "operator_id": pilot.OPERATOR_ID,
            "reviewed_at_utc": str(review["reviewed_at_utc"]),
            "decisions": decisions,
            "decision_count": len(decisions),
            "source_review_contract": REVIEW_SCHEMA_V2,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "status": "OPERATOR_REVIEW_COMPLETE_STRUCTURED_V2",
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
        receipt_path = staging / "pilot-review-receipt-v2.json"
        pilot.write_json(receipt_path, receipt)

        ledger = _build_defect_ledger(decisions, receipt_sha256=pilot.sha_file(receipt_path))
        ledger_path = staging / "pilot-defect-ledger-v2.json"
        pilot.write_json(ledger_path, ledger)

        inventory_body = {
            "schema": INVENTORY_SCHEMA_V2,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "source_pilot_run_file_sha256": pilot.sha_file(evidence["paths"]["run"]),
            "source_output_manifest_file_sha256": pilot.sha_file(evidence["paths"]["manifest"]),
            "preserved_review_v1_file_sha256": pilot.sha_file(evidence["paths"]["review_v1"]),
            "structured_review_v2_file_sha256": pilot.sha_file(receipt_path),
            "structured_defect_ledger_v2_file_sha256": pilot.sha_file(ledger_path),
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
            "inventory_id": f"PD.PILOT.REVIEW-V2.EVIDENCE.{pilot.logical_sha(inventory_body)[:24]}",
            "signature_algorithm": "ED25519",
            "signature_format": replay.SIGNATURE_FORMAT,
            "signature_namespace": replay.SIGNATURE_NAMESPACE,
            "signed_payload_sha256": pilot.logical_sha(inventory_body),
            "signature_sha256": inventory_signature_sha,
            "signature": inventory_signature,
            "status": "SIGNED_STRUCTURED_V2_REVIEW_EVIDENCE_COMPLETE",
        }
        inventory_path = staging / "signed-structured-review-evidence-inventory.json"
        pilot.write_json(inventory_path, inventory)

        gate_input = {
            "schema": GATE_INPUT_SCHEMA_V2,
            "gate_id": NEXT_GATE,
            "pilot_run_id": EXPECTED_RUN_ID,
            "pilot_namespace": EXPECTED_NAMESPACE,
            "active_c2_release_id": corrective.CORRECTIVE_ACTIVE_C2_RELEASE,
            "active_c2_manifest_id": corrective.CORRECTIVE_C2_MANIFEST_ID,
            "selector_id": corrective.CORRECTIVE_SELECTOR_ID,
            "machine_rerun_valid": True,
            "structured_review_v2_complete": True,
            "structured_review_receipt_file_sha256": pilot.sha_file(receipt_path),
            "structured_defect_ledger_file_sha256": pilot.sha_file(ledger_path),
            "signed_structured_inventory_file_sha256": pilot.sha_file(inventory_path),
            "defect_count": ledger["defect_count"],
            "contract_changes_required": ledger["contract_changes_required"],
            "second_machine_replay_required": False,
            "operator_approval_required": True,
            "allowed_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
            "status": "C1C_G5_CORRECTIVE_PILOT_REVIEW_GATE_INPUT_READY",
        }
        gate_path = staging / "c1c-g5-corrective-pilot-review-gate-input.json"
        pilot.write_json(gate_path, gate_input)
        staging.rename(final_root)
        return {
            "status": "C1C_G5_STRUCTURED_V2_REVIEW_COMPLETE_GATE_INPUT_READY",
            "pilot_run_id": EXPECTED_RUN_ID,
            "operator_review_root": str(final_root),
            "defect_count": ledger["defect_count"],
            "next_gate": NEXT_GATE,
            "second_machine_replay_required": False,
            "canonical_append": "DENIED",
        }
    except Exception as exc:
        if staging.exists():
            quarantine = root / "quarantine" / f"C1C-G5-REVIEW-V2.{uuid.uuid4().hex[:8]}"
            quarantine.parent.mkdir(parents=True, exist_ok=True)
            staging.rename(quarantine)
        if isinstance(exc, CorrectiveReviewV2Error):
            raise
        raise CorrectiveReviewV2Error(f"UNEXPECTED_STRUCTURED_REVIEW_FAILURE:{exc}") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="C1C-G5 structured v2 re-review over the immutable corrective pilot run.")
    result.add_argument("command", choices=("preflight", "prepare", "finalize"))
    result.add_argument("--repository-root", type=Path, default=Path.cwd())
    result.add_argument("--pilot-run-id", default=EXPECTED_RUN_ID)
    result.add_argument("--review-file", type=Path, default=None)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.pilot_run_id != EXPECTED_RUN_ID:
        raise CorrectiveReviewV2Error(f"EXACT_CORRECTIVE_RUN_REQUIRED:{EXPECTED_RUN_ID}")
    if args.command == "preflight":
        result = preflight(args.repository_root)
    elif args.command == "prepare":
        result = prepare(args.repository_root)
    else:
        if args.review_file is None:
            raise CorrectiveReviewV2Error("--review-file is required for finalize")
        result = finalize(args.repository_root, review_file=args.review_file)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
