from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import dukascopy_intake as intake


PLAN_ID = "OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1"
AUTHORITY_GATE = "RPS-G3"
SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1"
SOURCE_MANIFEST_SHA256 = "429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41"
RUN_ID = "RPS.RUN.7aeb551335d766ee3bf503e6"
BINDING_ID = "RPS.BINDING.32fb3003efa072916c11e907"
OUTPUT_MANIFEST_SHA256 = "3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff"
RPS_G3_MERGE = "c8429ebdf8774a876d5a33e495cb313e31c8d034"
OPERATION_MODE = "TIME_GATED_REPLAY"
SIGNATURE_NAMESPACE = "ovc-rps"
ALGORITHM = "ED25519"
SIGNATURE_FORMAT = "SSHSIG_OPENSSH_V1"
_OPERATOR_ID = re.compile(r"^OVC\.OPERATOR\.[A-Z0-9][A-Z0-9_.-]*\.v[0-9]+$")


class ReplayAcceptanceError(RuntimeError):
    """Raised when RPS-WP4 cannot complete lawfully."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ReplayAcceptanceError(f"refusing to overwrite evidence: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplayAcceptanceError(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise ReplayAcceptanceError(f"{code}:{path}")
    return value


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def validate_operator_id(operator_id: str) -> str:
    value = operator_id.strip().upper()
    if not _OPERATOR_ID.fullmatch(value):
        raise ReplayAcceptanceError(
            "operator ID must match OVC.OPERATOR.<UPPERCASE_ID>.v<NUMBER>"
        )
    return value


def operator_slug(operator_id: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", operator_id).strip("-").lower()


def repository_state(repository_root: Path) -> tuple[str, str]:
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        changes = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReplayAcceptanceError("unable to resolve repository state") from exc
    if branch != "main":
        raise ReplayAcceptanceError("RPS-WP4 local execution requires the main branch")
    if changes:
        raise ReplayAcceptanceError("RPS-WP4 requires a clean tracked worktree")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ReplayAcceptanceError("invalid repository commit identity")
    return branch, commit


def external_root(repository_root: Path, environ: Mapping[str, str]) -> Path:
    try:
        return intake._resolve_root(repository_root, environ)
    except intake.IntakeError as exc:
        raise ReplayAcceptanceError(str(exc)) from exc


def safe_file(root: Path, relative: str) -> Path:
    path = root / Path(relative)
    if path.is_symlink() or not path.is_file():
        raise ReplayAcceptanceError(f"required regular file unavailable: {relative}")
    resolved_root = root.resolve(strict=True)
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ReplayAcceptanceError(f"file escapes governed root: {relative}") from exc
    return resolved


def evidence_index_path(repository_root: Path) -> Path:
    return (
        repository_root
        / "docs"
        / "releases"
        / "prospective-source-v0-1"
        / "rps-wp3"
        / "RPS_WP3_COMPACT_COMPUTE_EVIDENCE_INDEX.json"
    )


def acceptance_state_path(repository_root: Path) -> Path:
    return (
        repository_root
        / "registries"
        / "research_operations"
        / "prospective_source"
        / "RPS_G3_ACCEPTANCE_STATE_v0_1.json"
    )


def load_governed_acceptance(repository_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    index = load_json(evidence_index_path(repository_root), "INVALID_RPS_G3_EVIDENCE_INDEX")
    state = load_json(acceptance_state_path(repository_root), "INVALID_RPS_G3_STATE")
    expected = {
        "gate_id": "RPS-G3",
        "run_id": RUN_ID,
        "binding_id": BINDING_ID,
        "slice_id": SLICE_ID,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "output_manifest_sha256": OUTPUT_MANIFEST_SHA256,
        "operation_mode": OPERATION_MODE,
    }
    for key, value in expected.items():
        if index.get(key) != value:
            raise ReplayAcceptanceError(f"RPS-G3 evidence mismatch:{key}")
    if state.get("gate_status") != "APPROVED":
        raise ReplayAcceptanceError("RPS-G3 is not approved")
    if state.get("packet_status") != "COMPLETED":
        raise ReplayAcceptanceError("RPS-WP3 is not complete")
    if state.get("active_binding_id") is not None:
        raise ReplayAcceptanceError("RPS-G3 state unexpectedly contains an active binding")
    if state.get("active_research_triage") is not False:
        raise ReplayAcceptanceError("active research triage must remain false")
    if state.get("write_authority") is not False:
        raise ReplayAcceptanceError("write authority must remain false")
    return index, state


def verify_compute_run(
    repository_root: Path,
    environ: Mapping[str, str],
) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    index, _ = load_governed_acceptance(repository_root)
    root = (
        external_root(repository_root, environ)
        / "prospective-source"
        / "compute"
        / RUN_ID
    )
    if not root.is_dir():
        raise ReplayAcceptanceError(f"accepted compute run unavailable: {root}")

    compact_paths = {
        "coverage.json": "qa/coverage.json",
        "compute-receipt.json": "compute-receipt.json",
        "output-manifest.json": "output-manifest.json",
        "prospective-compute-run.json": "prospective-compute-run.json",
        "prospective-source-binding.json": "prospective-source-binding.json",
    }
    compact = {item["name"]: item for item in index["compact_files"]}
    if set(compact) != set(compact_paths):
        raise ReplayAcceptanceError("compact compute inventory mismatch")
    for name, relative in compact_paths.items():
        path = safe_file(root, relative)
        expected = compact[name]
        if path.stat().st_size != int(expected["size_bytes"]):
            raise ReplayAcceptanceError(f"compact size mismatch:{name}")
        if sha_file(path) != expected["sha256"]:
            raise ReplayAcceptanceError(f"compact SHA-256 mismatch:{name}")

    manifest_path = safe_file(root, "output-manifest.json")
    manifest = load_json(manifest_path, "INVALID_OUTPUT_MANIFEST")
    logical = dict(manifest)
    claimed = logical.pop("output_manifest_sha256", None)
    if claimed != canonical_sha256(logical) or claimed != OUTPUT_MANIFEST_SHA256:
        raise ReplayAcceptanceError("output manifest logical SHA-256 mismatch")
    if sha_file(manifest_path) != index["output_manifest_file_sha256"]:
        raise ReplayAcceptanceError("output manifest file SHA-256 mismatch")

    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != 21 or manifest.get("file_count") != 21:
        raise ReplayAcceptanceError("output payload inventory count mismatch")
    declared: set[str] = set()
    payload_bytes = 0
    for item in files:
        if not isinstance(item, dict):
            raise ReplayAcceptanceError("invalid output manifest file entry")
        relative = str(item.get("path", ""))
        if not relative or relative in declared or "\\" in relative or relative.startswith("/"):
            raise ReplayAcceptanceError(f"unsafe or duplicate output path:{relative}")
        if ".." in Path(relative).parts:
            raise ReplayAcceptanceError(f"unsafe output path:{relative}")
        declared.add(relative)
        path = safe_file(root, relative)
        if path.stat().st_size != int(item.get("size_bytes", -1)):
            raise ReplayAcceptanceError(f"derived payload size mismatch:{relative}")
        if sha_file(path) != item.get("sha256"):
            raise ReplayAcceptanceError(f"derived payload SHA-256 mismatch:{relative}")
        payload_bytes += path.stat().st_size
    if payload_bytes != 5_557_327:
        raise ReplayAcceptanceError("derived payload byte count mismatch")

    run = load_json(
        safe_file(root, "prospective-compute-run.json"),
        "INVALID_COMPUTE_RUN",
    )
    binding = load_json(
        safe_file(root, "prospective-source-binding.json"),
        "INVALID_SOURCE_BINDING",
    )
    receipt = load_json(
        safe_file(root, "compute-receipt.json"),
        "INVALID_COMPUTE_RECEIPT",
    )
    coverage = load_json(
        safe_file(root, "qa/coverage.json"),
        "INVALID_COVERAGE",
    )
    if run.get("run_id") != RUN_ID or run.get("status") != "COMPLETE":
        raise ReplayAcceptanceError("compute run identity or status mismatch")
    if binding.get("binding_id") != BINDING_ID:
        raise ReplayAcceptanceError("source binding identity mismatch")
    if binding.get("status") != "ACCEPTED_FOR_REPLAY_CANDIDATE":
        raise ReplayAcceptanceError("source binding status mismatch")
    if binding.get("active_research_triage") is not False:
        raise ReplayAcceptanceError("binding must remain non-activating")
    if binding.get("write_authority") is not False:
        raise ReplayAcceptanceError("binding must not grant write authority")
    if receipt.get("status") != "COMPLETE_LOCAL_CANDIDATE":
        raise ReplayAcceptanceError("compute receipt status mismatch")
    if coverage.get("qa_state") != "PASS_GAPPED_EXCLUSION":
        raise ReplayAcceptanceError("coverage QA is not accepted")
    for value in (manifest, run, binding, receipt):
        if value.get("operation_mode") != OPERATION_MODE:
            raise ReplayAcceptanceError("operation mode mismatch")
    return root, manifest, run, binding, receipt


def ssh_keygen() -> str:
    path = shutil.which("ssh-keygen")
    if not path:
        raise ReplayAcceptanceError("OpenSSH ssh-keygen is required")
    return path


def key_root(repository_root: Path, environ: Mapping[str, str], operator_id: str) -> Path:
    return (
        external_root(repository_root, environ)
        / "prospective-source"
        / "operator-signing"
        / operator_slug(operator_id)
    )


def key_paths(repository_root: Path, environ: Mapping[str, str], operator_id: str) -> tuple[Path, Path]:
    root = key_root(repository_root, environ, operator_id)
    private = root / "id_ed25519"
    return private, private.with_suffix(".pub")


def public_key_details(public_key_path: Path, operator_id: str) -> dict[str, Any]:
    line = public_key_path.read_text(encoding="utf-8").strip()
    parts = line.split()
    if len(parts) < 2 or parts[0] != "ssh-ed25519":
        raise ReplayAcceptanceError("operator public key is not Ed25519")
    result = subprocess.run(
        [ssh_keygen(), "-lf", str(public_key_path), "-E", "sha256"],
        check=True,
        capture_output=True,
        text=True,
    )
    fingerprint_line = result.stdout.strip()
    fields = fingerprint_line.split()
    if len(fields) < 2 or not fields[1].startswith("SHA256:"):
        raise ReplayAcceptanceError("unable to resolve Ed25519 public-key fingerprint")
    return {
        "operator_id": operator_id,
        "algorithm": ALGORITHM,
        "signature_format": SIGNATURE_FORMAT,
        "signature_namespace": SIGNATURE_NAMESPACE,
        "public_key": " ".join(parts[:2]),
        "public_key_sha256": hashlib.sha256((line + "\n").encode("utf-8")).hexdigest(),
        "public_key_fingerprint": fields[1],
        "private_key_in_git": False,
        "private_key_alias": (
            f"OVC_EXTERNAL_ARTIFACT_ROOT/prospective-source/operator-signing/"
            f"{operator_slug(operator_id)}/id_ed25519"
        ),
    }


def setup_key(
    repository_root: Path,
    *,
    operator_id: str,
    authority_gate: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if authority_gate != AUTHORITY_GATE:
        raise ReplayAcceptanceError(f"exact delegated authority required: --gate {AUTHORITY_GATE}")
    if truthy(values.get("CI")) or truthy(values.get("GITHUB_ACTIONS")):
        raise ReplayAcceptanceError("operator key generation is prohibited in CI")
    operator = validate_operator_id(operator_id)
    repository_state(repository_root)
    verify_compute_run(repository_root, values)
    private, public = key_paths(repository_root, values, operator)
    private.parent.mkdir(parents=True, exist_ok=True)
    if private.exists() or public.exists():
        raise ReplayAcceptanceError("refusing to overwrite existing operator key")
    try:
        subprocess.run(
            [
                ssh_keygen(),
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                operator,
                "-f",
                str(private),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ReplayAcceptanceError(
            f"ssh-keygen failed:{exc.stderr.strip() or exc.stdout.strip()}"
        ) from exc
    details = public_key_details(public, operator)
    return {
        "status": "KEY_CREATED_AWAITING_PRIVATE_KEY_PROTECTION_CONFIRMATION",
        "operator_id": operator,
        "algorithm": ALGORITHM,
        "public_key_fingerprint": details["public_key_fingerprint"],
        "public_key_sha256": details["public_key_sha256"],
        "private_key_alias": details["private_key_alias"],
        "private_key_in_git": False,
        "next_command": "accept-replay with --confirm-private-key-protected",
    }


def sign_and_verify(
    *,
    private_key: Path,
    public_key: str,
    operator_id: str,
    payload: bytes,
) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="rps-wp4-sign-") as temporary:
        root = Path(temporary)
        payload_path = root / "payload.json"
        signature_path = root / "payload.json.sig"
        allowed_path = root / "allowed_signers"
        payload_path.write_bytes(payload)
        allowed_path.write_text(
            f'{operator_id} namespaces="{SIGNATURE_NAMESPACE}" {public_key}\n',
            encoding="utf-8",
        )
        try:
            subprocess.run(
                [
                    ssh_keygen(),
                    "-Y",
                    "sign",
                    "-f",
                    str(private_key),
                    "-n",
                    SIGNATURE_NAMESPACE,
                    str(payload_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise ReplayAcceptanceError(
                f"Ed25519 signing failed:{exc.stderr.strip() or exc.stdout.strip()}"
            ) from exc
        if not signature_path.is_file():
            raise ReplayAcceptanceError("ssh-keygen did not create a signature")
        signature = signature_path.read_text(encoding="utf-8")
        verify = subprocess.run(
            [
                ssh_keygen(),
                "-Y",
                "verify",
                "-f",
                str(allowed_path),
                "-I",
                operator_id,
                "-n",
                SIGNATURE_NAMESPACE,
                "-s",
                str(signature_path),
            ],
            input=payload,
            capture_output=True,
        )
        if verify.returncode != 0:
            raise ReplayAcceptanceError(
                "Ed25519 signature verification failed:"
                + verify.stderr.decode("utf-8", errors="replace").strip()
            )
        return signature, hashlib.sha256(signature.encode("utf-8")).hexdigest()


def quarantine_staging(staging: Path, reason: str) -> Path | None:
    if not staging.exists():
        return None
    quarantine = staging.parent / "quarantine"
    quarantine.mkdir(parents=True, exist_ok=True)
    target = quarantine / (
        f"RPS-WP4.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}."
        f"{uuid.uuid4().hex[:8]}"
    )
    try:
        write_json(
            staging / "failure-receipt.json",
            {
                "schema": "ovc-rps-wp4-failure/v1",
                "reason": reason,
                "private_key_in_git": False,
                "provider_network_access_performed": False,
                "active_research_triage": False,
                "write_authority": False,
            },
        )
    except Exception:
        pass
    staging.rename(target)
    return target


def preflight(
    repository_root: Path,
    *,
    operator_id: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    operator = validate_operator_id(operator_id)
    branch, commit = repository_state(repository_root)
    verify_compute_run(repository_root, values)
    private, public = key_paths(repository_root, values, operator)
    return {
        "status": "READY_FOR_OPERATOR_SIGNING_AND_TIME_GATED_REPLAY_ACCEPTANCE",
        "authority_gate": AUTHORITY_GATE,
        "repository_branch": branch,
        "repository_commit": commit,
        "operator_id": operator,
        "ssh_keygen_available": bool(ssh_keygen()),
        "private_key_exists": private.is_file(),
        "public_key_exists": public.is_file(),
        "run_id": RUN_ID,
        "binding_id": BINDING_ID,
        "operation_mode": OPERATION_MODE,
        "active_research_triage": False,
        "write_authority": False,
        "live_prospective_append": "DENIED",
    }


def accept_replay(
    repository_root: Path,
    *,
    operator_id: str,
    authority_gate: str,
    confirm_private_key_protected: bool,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if authority_gate != AUTHORITY_GATE:
        raise ReplayAcceptanceError(f"exact delegated authority required: --gate {AUTHORITY_GATE}")
    if truthy(values.get("CI")) or truthy(values.get("GITHUB_ACTIONS")):
        raise ReplayAcceptanceError("operator replay acceptance is prohibited in CI")
    if not confirm_private_key_protected:
        raise ReplayAcceptanceError("explicit private-key protection confirmation is required")
    operator = validate_operator_id(operator_id)
    _, repository_commit = repository_state(repository_root)
    _, manifest, run, source_binding, _ = verify_compute_run(repository_root, values)
    private, public = key_paths(repository_root, values, operator)
    if private.is_symlink() or not private.is_file():
        raise ReplayAcceptanceError("operator private key is unavailable or unsafe")
    if public.is_symlink() or not public.is_file():
        raise ReplayAcceptanceError("operator public key is unavailable or unsafe")
    key = public_key_details(public, operator)

    signing_identity = {
        "operator_id": operator,
        "algorithm": ALGORITHM,
        "signature_format": SIGNATURE_FORMAT,
        "signature_namespace": SIGNATURE_NAMESPACE,
        "public_key_sha256": key["public_key_sha256"],
        "public_key_fingerprint": key["public_key_fingerprint"],
        "run_id": RUN_ID,
        "binding_id": BINDING_ID,
    }
    signing_binding_id = f"RPS.SIGNING.{canonical_sha256(signing_identity)[:24]}"
    signing_binding = {
        "schema": "ovc-rps-operator-signing-binding/v1",
        "signing_binding_id": signing_binding_id,
        **key,
        "run_id": RUN_ID,
        "binding_id": BINDING_ID,
        "source_slice_id": SLICE_ID,
        "private_key_protection_confirmed": True,
        "active_research_triage": False,
        "write_authority": False,
        "status": "REGISTERED_REPLAY_ONLY_CANDIDATE",
    }

    acceptance_body = {
        "schema": "ovc-rps-time-gated-replay-acceptance/v1",
        "plan_id": PLAN_ID,
        "authority_gate": AUTHORITY_GATE,
        "operator_id": operator,
        "signing_binding_id": signing_binding_id,
        "source_slice_id": SLICE_ID,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "run_id": RUN_ID,
        "binding_id": BINDING_ID,
        "output_manifest_sha256": OUTPUT_MANIFEST_SHA256,
        "compute_code_commit": run["code_commit"],
        "rps_g3_merge": RPS_G3_MERGE,
        "operator_execution_commit": repository_commit,
        "operation_mode": OPERATION_MODE,
        "admissible_cutoff_utc": run["admissible_cutoff_utc"],
        "eligible_data_through_utc": source_binding["eligible_data_through_utc"],
        "coverage_state": source_binding["source_coverage_state"],
        "deterministic_replay": True,
        "lineage_complete": True,
        "payload_file_count": manifest["file_count"],
        "payload_bytes": 5_557_327,
        "acceptance": "ACCEPTED_FOR_TIME_GATED_REPLAY_ONLY",
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "validation_consumption": "DENIED",
        "live_prospective_append": "DENIED",
        "active_research_triage": False,
        "write_authority": False,
        "probability_authority": "NONE",
        "exposure_authority": "NONE",
        "trading_authority": "NONE",
        "execution_authority": "NONE",
        "agent_write_authority": "NONE",
    }
    acceptance_id = f"RPS.REPLAY-ACCEPT.{canonical_sha256(acceptance_body)[:24]}"
    signed_payload = {**acceptance_body, "acceptance_id": acceptance_id}
    signature, signature_sha = sign_and_verify(
        private_key=private,
        public_key=key["public_key"],
        operator_id=operator,
        payload=canonical_bytes(signed_payload),
    )
    acceptance = {
        **signed_payload,
        "signature_algorithm": ALGORITHM,
        "signature_format": SIGNATURE_FORMAT,
        "signature_namespace": SIGNATURE_NAMESPACE,
        "signed_payload_sha256": canonical_sha256(signed_payload),
        "signature_sha256": signature_sha,
        "signature": signature,
        "status": "SIGNED_REPLAY_ACCEPTANCE_CANDIDATE",
    }

    root = (
        external_root(repository_root, values)
        / "prospective-source"
        / "replay-acceptance"
    )
    root.mkdir(parents=True, exist_ok=True)
    final = root / acceptance_id
    if final.exists():
        raise ReplayAcceptanceError(f"refusing to overwrite replay acceptance: {final}")
    staging = root / f".RPS-WP4.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        signing_path = staging / "operator-signing-binding.json"
        acceptance_path = staging / "time-gated-replay-acceptance.json"
        write_json(signing_path, signing_binding)
        write_json(acceptance_path, acceptance)
        verification = {
            "schema": "ovc-rps-signature-verification-receipt/v1",
            "acceptance_id": acceptance_id,
            "operator_id": operator,
            "signing_binding_id": signing_binding_id,
            "algorithm": ALGORITHM,
            "signature_format": SIGNATURE_FORMAT,
            "signature_namespace": SIGNATURE_NAMESPACE,
            "public_key_fingerprint": key["public_key_fingerprint"],
            "signed_payload_sha256": acceptance["signed_payload_sha256"],
            "signature_sha256": signature_sha,
            "signature_verified": True,
            "operator_signing_binding_file_sha256": sha_file(signing_path),
            "time_gated_replay_acceptance_file_sha256": sha_file(acceptance_path),
            "private_key_in_git": False,
            "private_key_material_in_receipt": False,
            "active_research_triage": False,
            "write_authority": False,
            "status": "PASS",
        }
        verification_path = staging / "signature-verification-receipt.json"
        write_json(verification_path, verification)
        gate_input = {
            "schema": "ovc-rps-g4-operator-gate-input/v1",
            "gate_id": "RPS-G4",
            "plan_id": PLAN_ID,
            "source_slice_id": SLICE_ID,
            "run_id": RUN_ID,
            "binding_id": BINDING_ID,
            "acceptance_id": acceptance_id,
            "signing_binding_id": signing_binding_id,
            "operator_id": operator,
            "operator_signing_binding_file_sha256": verification[
                "operator_signing_binding_file_sha256"
            ],
            "time_gated_replay_acceptance_file_sha256": verification[
                "time_gated_replay_acceptance_file_sha256"
            ],
            "signature_verification_receipt_file_sha256": sha_file(verification_path),
            "current_authority": "TIME_GATED_REPLAY_ACCEPTED_NON_ACTIVATING",
            "proposed_delta": (
                "ACTIVATE_EXACT_BINDING_FOR_ACTIVE_RESEARCH_TRIAGE_AND_ENABLE_"
                "PD_WP5_FIRST_LIVE_PROSPECTIVE_OPERATION"
            ),
            "operator_approval_required": True,
            "active_binding_id": None,
            "active_research_triage": False,
            "live_prospective_append": "DENIED",
            "write_authority": False,
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "status": "RPS_G4_EVIDENCE_CANDIDATE",
        }
        gate_path = staging / "rps-g4-operator-gate-input.json"
        write_json(gate_path, gate_input)
        staging.rename(final)
    except Exception as exc:
        quarantine_staging(staging, str(exc))
        if isinstance(exc, ReplayAcceptanceError):
            raise
        raise ReplayAcceptanceError(str(exc)) from exc

    return {
        "status": "COMPLETE_LOCAL_SIGNING_AND_REPLAY_ACCEPTANCE_CANDIDATE",
        "acceptance_id": acceptance_id,
        "signing_binding_id": signing_binding_id,
        "operator_id": operator,
        "run_id": RUN_ID,
        "binding_id": BINDING_ID,
        "public_key_fingerprint": key["public_key_fingerprint"],
        "active_research_triage": False,
        "write_authority": False,
        "live_prospective_append": "DENIED",
        "compact_files": [
            "operator-signing-binding.json",
            "time-gated-replay-acceptance.json",
            "signature-verification-receipt.json",
            "rps-g4-operator-gate-input.json",
        ],
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description=(
            "Operator-local RPS-WP4 Ed25519 signing binding and "
            "TIME_GATED_REPLAY acceptance preparation."
        )
    )
    value.add_argument("command", choices=("preflight", "setup-key", "accept-replay"))
    value.add_argument("--repository-root", type=Path, default=Path.cwd())
    value.add_argument("--operator-id", required=True)
    value.add_argument("--gate", default=None)
    value.add_argument("--confirm-private-key-protected", action="store_true")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "preflight":
            result = preflight(
                repository_root,
                operator_id=arguments.operator_id,
            )
        elif arguments.command == "setup-key":
            result = setup_key(
                repository_root,
                operator_id=arguments.operator_id,
                authority_gate=arguments.gate or "",
            )
        else:
            result = accept_replay(
                repository_root,
                operator_id=arguments.operator_id,
                authority_gate=arguments.gate or "",
                confirm_private_key_protected=arguments.confirm_private_key_protected,
            )
    except ReplayAcceptanceError as exc:
        print(f"RPS-WP4 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
