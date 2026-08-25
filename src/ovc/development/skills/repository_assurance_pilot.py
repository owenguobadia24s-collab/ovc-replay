from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path
from ovc.development.skills.vit_routing import validate_vit_lineage_record

PILOT_POLICY_SCHEMA = "ovc-rac-delta-assurance-pilot-policy/v1"
PILOT_BASELINE_SCHEMA = "ovc-rac-delta-assurance-pilot-baseline/v1"
PILOT_CERTIFICATE_SCHEMA = "ovc-rac-delta-assurance-pilot-certificate/v1"
PILOT_CLASS = "DSAI_VIT_RECEIPT_ONLY_V0_1"
ACTIVE_STATUS = "ACTIVE_BOUNDED_PILOT"
PASS = "PASS"


class RepositoryAssurancePilotError(ValueError):
    """Raised when a pilot object or candidate cannot be trusted."""


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RepositoryAssurancePilotError(
            proc.stderr.strip() or f"RAC_PILOT_GIT_FAILED:{' '.join(args)}"
        )
    return proc.stdout


def _hex(value: object, length: int, reason: str) -> str:
    text = str(value or "")
    if len(text) != length or any(ch not in "0123456789abcdef" for ch in text):
        raise RepositoryAssurancePilotError(reason)
    return text


def _canonical_id(value: Mapping[str, Any], *, field: str, role: str) -> str:
    logical = {key: item for key, item in value.items() if key != field}
    return canonical_sha256(logical, role=role)


def validate_pilot_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if policy.get("schema") != PILOT_POLICY_SCHEMA:
        raise RepositoryAssurancePilotError("RAC_PILOT_POLICY_SCHEMA_INVALID")
    if policy.get("pilot_class") != PILOT_CLASS:
        raise RepositoryAssurancePilotError("RAC_PILOT_CLASS_INVALID")
    required = (
        "policy_id",
        "programme_id",
        "operator_decision_id",
        "status",
        "receipt_prefixes",
        "control_prefixes",
        "allowed_ops",
        "baseline_certificate_path",
    )
    if any(key not in policy for key in required):
        raise RepositoryAssurancePilotError("RAC_PILOT_POLICY_FIELD_MISSING")
    _hex(policy["operator_decision_id"], 64, "RAC_PILOT_DECISION_ID_INVALID")
    prefixes = sorted({normalize_relative_path(str(x)).rstrip("/") + "/" for x in policy["receipt_prefixes"]})
    controls = sorted({normalize_relative_path(str(x)).rstrip("/") + "/" for x in policy["control_prefixes"]})
    ops = sorted({str(x) for x in policy["allowed_ops"]})
    if not prefixes or not controls or ops != ["ADD", "MODIFY"]:
        raise RepositoryAssurancePilotError("RAC_PILOT_POLICY_SCOPE_INVALID")
    baseline = str(policy.get("baseline_certificate_path") or "")
    if baseline:
        normalize_relative_path(baseline)
    result = dict(policy)
    result["receipt_prefixes"] = prefixes
    result["control_prefixes"] = controls
    result["allowed_ops"] = ops
    return result


def pilot_active(policy: Mapping[str, Any]) -> bool:
    return validate_pilot_policy(policy)["status"] == ACTIVE_STATUS


def is_pilot_receipt_path(path: str, policy: Mapping[str, Any]) -> bool:
    normalized = normalize_relative_path(path)
    configured = validate_pilot_policy(policy)
    if not any(normalized.startswith(prefix) for prefix in configured["receipt_prefixes"]):
        return False
    name = normalized.rsplit("/", 1)[-1]
    return name.endswith(".json") and "RECEIPT" in name.upper()


def _surface_excluded(path: str, policy: Mapping[str, Any]) -> bool:
    normalized = normalize_relative_path(path)
    configured = validate_pilot_policy(policy)
    if is_pilot_receipt_path(normalized, configured):
        return True
    return any(normalized.startswith(prefix) for prefix in configured["control_prefixes"])


def assurance_surface_id(root: Path, commit_sha: str, policy: Mapping[str, Any]) -> str:
    """Hash all tracked repository objects that the pilot is not allowed to ignore."""
    _hex(commit_sha, 40, "RAC_PILOT_COMMIT_INVALID")
    raw = _git(root, "ls-tree", "-r", "--full-tree", commit_sha)
    rows: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line:
            continue
        try:
            left, path = line.split("\t", 1)
            mode, kind, sha = left.split(" ", 2)
        except ValueError as exc:
            raise RepositoryAssurancePilotError("RAC_PILOT_TREE_ROW_INVALID") from exc
        if _surface_excluded(path, policy):
            continue
        rows.append({"mode": mode, "type": kind, "sha": sha, "path": normalize_relative_path(path)})
    return canonical_sha256(rows, role="OVC_RAC_PILOT_ASSURANCE_SURFACE")


def validate_pilot_baseline(baseline: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    configured = validate_pilot_policy(policy)
    if baseline.get("schema") != PILOT_BASELINE_SCHEMA:
        raise RepositoryAssurancePilotError("RAC_PILOT_BASELINE_SCHEMA_INVALID")
    if baseline.get("policy_id") != configured["policy_id"]:
        raise RepositoryAssurancePilotError("RAC_PILOT_BASELINE_POLICY_MISMATCH")
    if baseline.get("operator_decision_id") != configured["operator_decision_id"]:
        raise RepositoryAssurancePilotError("RAC_PILOT_BASELINE_DECISION_MISMATCH")
    _hex(baseline.get("source_commit_sha"), 40, "RAC_PILOT_BASELINE_COMMIT_INVALID")
    _hex(baseline.get("source_tree_sha"), 40, "RAC_PILOT_BASELINE_TREE_INVALID")
    _hex(baseline.get("assurance_surface_id"), 64, "RAC_PILOT_BASELINE_SURFACE_INVALID")
    expected = _canonical_id(baseline, field="baseline_id", role="OVC_RAC_PILOT_BASELINE")
    if baseline.get("baseline_id") != expected:
        raise RepositoryAssurancePilotError("RAC_PILOT_BASELINE_IDENTITY_INVALID")
    if baseline.get("reference_status") != PASS:
        raise RepositoryAssurancePilotError("RAC_PILOT_BASELINE_REFERENCE_NOT_PASS")
    return dict(baseline)


def classify_candidate(
    *,
    root: Path,
    candidate_head_sha: str,
    lineage_record: Mapping[str, Any],
    policy: Mapping[str, Any],
    baseline: Mapping[str, Any] | None,
) -> dict[str, Any]:
    configured = validate_pilot_policy(policy)
    _hex(candidate_head_sha, 40, "RAC_PILOT_HEAD_INVALID")
    if configured["status"] != ACTIVE_STATUS:
        return {"eligible": False, "reason": "POLICY_INACTIVE", "pilot_class": PILOT_CLASS}
    if baseline is None:
        return {"eligible": False, "reason": "BASELINE_MISSING", "pilot_class": PILOT_CLASS}
    certified = validate_pilot_baseline(baseline, configured)
    lineage = validate_vit_lineage_record(lineage_record)
    if not lineage.late_binding:
        return {"eligible": False, "reason": "LATE_BINDING_REQUIRED", "pilot_class": PILOT_CLASS}
    pip = lineage_record.get("pip")
    if not isinstance(pip, Mapping):
        raise RepositoryAssurancePilotError("RAC_PILOT_PIP_INVALID")
    logical_changes = pip.get("logical_changes")
    if not isinstance(logical_changes, Sequence) or isinstance(logical_changes, (str, bytes)) or not logical_changes:
        raise RepositoryAssurancePilotError("RAC_PILOT_LOGICAL_CHANGES_INVALID")
    receipt_paths: list[str] = []
    for change in logical_changes:
        if not isinstance(change, Mapping):
            raise RepositoryAssurancePilotError("RAC_PILOT_LOGICAL_CHANGE_INVALID")
        op = str(change.get("op", ""))
        path = normalize_relative_path(str(change.get("path", "")))
        if op not in configured["allowed_ops"]:
            return {"eligible": False, "reason": f"OP_NOT_ALLOWED:{op}", "pilot_class": PILOT_CLASS}
        if not is_pilot_receipt_path(path, configured):
            return {"eligible": False, "reason": f"PATH_NOT_RECEIPT_ONLY:{path}", "pilot_class": PILOT_CLASS}
        receipt_paths.append(path)
    surface = assurance_surface_id(root, candidate_head_sha, configured)
    if surface != certified["assurance_surface_id"]:
        return {
            "eligible": False,
            "reason": "ASSURANCE_SURFACE_DRIFT",
            "pilot_class": PILOT_CLASS,
            "candidate_assurance_surface_id": surface,
            "baseline_assurance_surface_id": certified["assurance_surface_id"],
        }
    return {
        "eligible": True,
        "reason": "EXACT_RECEIPT_ONLY_SURFACE_MATCH",
        "pilot_class": PILOT_CLASS,
        "pip_id": lineage.pip_id,
        "candidate_assurance_surface_id": surface,
        "baseline_id": certified["baseline_id"],
        "receipt_paths": sorted(receipt_paths),
    }


def build_pilot_certificate(
    *,
    candidate_head_sha: str,
    candidate_tree_sha: str,
    classification: Mapping[str, Any],
    policy: Mapping[str, Any],
    verified_receipt_paths: Sequence[str],
) -> dict[str, Any]:
    configured = validate_pilot_policy(policy)
    if classification.get("eligible") is not True:
        raise RepositoryAssurancePilotError("RAC_PILOT_CERTIFICATE_INELIGIBLE")
    _hex(candidate_head_sha, 40, "RAC_PILOT_CERTIFICATE_HEAD_INVALID")
    _hex(candidate_tree_sha, 40, "RAC_PILOT_CERTIFICATE_TREE_INVALID")
    expected_paths = sorted(str(x) for x in classification.get("receipt_paths", []))
    actual_paths = sorted(str(x) for x in verified_receipt_paths)
    if expected_paths != actual_paths:
        raise RepositoryAssurancePilotError("RAC_PILOT_RECEIPT_VERIFICATION_INCOMPLETE")
    certificate: dict[str, Any] = {
        "schema": PILOT_CERTIFICATE_SCHEMA,
        "status": PASS,
        "authority_effect": "NONE_ASSURANCE_ONLY",
        "pilot_class": PILOT_CLASS,
        "policy_id": configured["policy_id"],
        "operator_decision_id": configured["operator_decision_id"],
        "candidate_head_sha": candidate_head_sha,
        "candidate_tree_sha": candidate_tree_sha,
        "pip_id": _hex(classification.get("pip_id"), 64, "RAC_PILOT_CERTIFICATE_PIP_INVALID"),
        "baseline_id": _hex(classification.get("baseline_id"), 64, "RAC_PILOT_CERTIFICATE_BASELINE_INVALID"),
        "assurance_surface_id": _hex(
            classification.get("candidate_assurance_surface_id"),
            64,
            "RAC_PILOT_CERTIFICATE_SURFACE_INVALID",
        ),
        "verified_receipt_paths": actual_paths,
        "inherited_assurance": [
            "CANONICAL_REPOSITORY_SUITE",
            "PYTEST_UNITTEST_PARITY",
            "RUNNER_PARITY",
        ],
        "fresh_assurance_required": [
            "VIT_ROUTING_PREFLIGHT",
            "OVC_PROFILE_ASSURANCE",
            "SIQ_READY",
            "SIQ_PDC_EXACT_FINAL",
            "GRT_EXACT_FINAL",
            "POST_WRITE_TREE_EQUALITY",
        ],
    }
    certificate["certificate_id"] = _canonical_id(
        certificate,
        field="certificate_id",
        role="OVC_RAC_PILOT_CANDIDATE_CERTIFICATE",
    )
    return certificate


def validate_pilot_certificate(certificate: Mapping[str, Any]) -> str:
    if certificate.get("schema") != PILOT_CERTIFICATE_SCHEMA:
        raise RepositoryAssurancePilotError("RAC_PILOT_CERTIFICATE_SCHEMA_INVALID")
    if certificate.get("status") != PASS or certificate.get("authority_effect") != "NONE_ASSURANCE_ONLY":
        raise RepositoryAssurancePilotError("RAC_PILOT_CERTIFICATE_STATE_INVALID")
    expected = _canonical_id(
        certificate,
        field="certificate_id",
        role="OVC_RAC_PILOT_CANDIDATE_CERTIFICATE",
    )
    if certificate.get("certificate_id") != expected:
        raise RepositoryAssurancePilotError("RAC_PILOT_CERTIFICATE_IDENTITY_INVALID")
    return expected


def load_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RepositoryAssurancePilotError(f"RAC_PILOT_JSON_INVALID:{path}") from exc
    if not isinstance(value, Mapping):
        raise RepositoryAssurancePilotError(f"RAC_PILOT_JSON_OBJECT_REQUIRED:{path}")
    return value
