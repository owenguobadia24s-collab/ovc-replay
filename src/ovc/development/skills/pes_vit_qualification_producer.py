from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from ovc.development.skills.vit_routing import validate_vit_lineage_record


PRODUCER_REQUEST_SCHEMA = "ovc-pes-vit-qualification-publication-request/v0.1"
PRODUCER_TARGET_LEDGER_BRANCH = "ovc/vit-qualification-ledger-v1"
PRODUCER_TARGET_LEDGER_ROOT = ".ovc/vit-qualifications"
PRODUCER_WRITE_SCOPE = "ENVELOPE_AND_EXACT_HEAD_POINTER_ONLY"
OWNER_AUTHORITY_SOURCE_KIND = "DURABLE_OWNER_AUTHORITY_RECORD"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


class PesVitQualificationProducerError(RuntimeError):
    pass


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _required_text(value: object, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise PesVitQualificationProducerError(code)
    return text


@dataclass(frozen=True)
class ValidatedQualificationPublicationRequest:
    request_id: str
    candidate_head_sha: str
    lineage_record: Mapping[str, Any]
    pip_id: str
    authority_manifest_id: str
    dependency_frontier_id: str
    issuer_identity: str
    owner_authority_source: str


def build_qualification_publication_request(
    *,
    candidate_head_sha: str,
    lineage_record: Mapping[str, Any],
    issuer_identity: str,
    owner_authority_source: str,
) -> Mapping[str, Any]:
    if not SHA40.fullmatch(candidate_head_sha):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_HEAD_SHA_INVALID")
    validated = validate_vit_lineage_record(lineage_record)
    if not validated.late_binding:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_LATE_BINDING_REQUIRED")
    pip = lineage_record.get("pip")
    if not isinstance(pip, Mapping):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_PIP_INVALID")
    authority_manifest_id = str(pip.get("authority_manifest_id", "")).strip()
    dependency_frontier_id = str(pip.get("dependency_frontier_id", "")).strip()
    if not SHA64.fullmatch(authority_manifest_id) or not SHA64.fullmatch(dependency_frontier_id):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_FRONTIER_INVALID")
    issuer_identity = _required_text(issuer_identity, "PES_VIT_PRODUCER_ISSUER_MISSING")
    owner_authority_source = _required_text(
        owner_authority_source,
        "PES_VIT_PRODUCER_OWNER_AUTHORITY_SOURCE_MISSING",
    )
    payload = {
        "schema_version": PRODUCER_REQUEST_SCHEMA,
        "candidate_head_sha": candidate_head_sha,
        "pip_id": validated.pip_id,
        "authority_manifest_id": authority_manifest_id,
        "dependency_frontier_id": dependency_frontier_id,
        "lineage": dict(lineage_record),
        "issuance": {
            "issuer_identity": issuer_identity,
            "owner_authority_source_kind": OWNER_AUTHORITY_SOURCE_KIND,
            "owner_authority_source": owner_authority_source,
        },
        "target": {
            "ledger_branch": PRODUCER_TARGET_LEDGER_BRANCH,
            "ledger_root": PRODUCER_TARGET_LEDGER_ROOT,
            "write_scope": PRODUCER_WRITE_SCOPE,
        },
        "authority_effect": "NONE_REQUEST_ONLY",
    }
    return {**payload, "request_id": _canonical_sha256(payload)}


def validate_qualification_publication_request(
    request: Mapping[str, Any],
    *,
    expected_issuer_identity: str,
) -> ValidatedQualificationPublicationRequest:
    if str(request.get("schema_version", "")) != PRODUCER_REQUEST_SCHEMA:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_REQUEST_SCHEMA_INVALID")
    request_id = str(request.get("request_id", "")).strip()
    if not SHA64.fullmatch(request_id):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_REQUEST_ID_INVALID")
    identity_payload = {key: value for key, value in request.items() if key != "request_id"}
    if _canonical_sha256(identity_payload) != request_id:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_REQUEST_ID_MISMATCH")

    head_sha = str(request.get("candidate_head_sha", "")).strip()
    if not SHA40.fullmatch(head_sha):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_HEAD_SHA_INVALID")

    lineage_record = request.get("lineage")
    if not isinstance(lineage_record, Mapping):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_LINEAGE_INVALID")
    lineage = validate_vit_lineage_record(lineage_record)
    if not lineage.late_binding:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_LATE_BINDING_REQUIRED")
    pip = lineage_record.get("pip")
    if not isinstance(pip, Mapping):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_PIP_INVALID")

    pip_id = str(request.get("pip_id", "")).strip()
    authority_manifest_id = str(request.get("authority_manifest_id", "")).strip()
    dependency_frontier_id = str(request.get("dependency_frontier_id", "")).strip()
    if pip_id != lineage.pip_id:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_PIP_ID_MISMATCH")
    if authority_manifest_id != str(pip.get("authority_manifest_id", "")):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_AUTHORITY_ID_MISMATCH")
    if dependency_frontier_id != str(pip.get("dependency_frontier_id", "")):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_FRONTIER_ID_MISMATCH")
    if not SHA64.fullmatch(authority_manifest_id) or not SHA64.fullmatch(dependency_frontier_id):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_FRONTIER_INVALID")

    issuance = request.get("issuance")
    if not isinstance(issuance, Mapping):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ISSUANCE_INVALID")
    issuer_identity = _required_text(issuance.get("issuer_identity"), "PES_VIT_PRODUCER_ISSUER_MISSING")
    expected_issuer_identity = _required_text(
        expected_issuer_identity,
        "PES_VIT_PRODUCER_EXPECTED_ISSUER_MISSING",
    )
    if issuer_identity != expected_issuer_identity:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ISSUER_NOT_AUTHORISED")
    if issuance.get("owner_authority_source_kind") != OWNER_AUTHORITY_SOURCE_KIND:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_OWNER_AUTHORITY_SOURCE_KIND_INVALID")
    owner_authority_source = _required_text(
        issuance.get("owner_authority_source"),
        "PES_VIT_PRODUCER_OWNER_AUTHORITY_SOURCE_MISSING",
    )

    target = request.get("target")
    if not isinstance(target, Mapping):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_TARGET_INVALID")
    if target.get("ledger_branch") != PRODUCER_TARGET_LEDGER_BRANCH:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_LEDGER_BRANCH_INVALID")
    if target.get("ledger_root") != PRODUCER_TARGET_LEDGER_ROOT:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_LEDGER_ROOT_INVALID")
    if target.get("write_scope") != PRODUCER_WRITE_SCOPE:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_WRITE_SCOPE_INVALID")
    if request.get("authority_effect") != "NONE_REQUEST_ONLY":
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_AUTHORITY_EFFECT_INVALID")

    return ValidatedQualificationPublicationRequest(
        request_id=request_id,
        candidate_head_sha=head_sha,
        lineage_record=dict(lineage_record),
        pip_id=pip_id,
        authority_manifest_id=authority_manifest_id,
        dependency_frontier_id=dependency_frontier_id,
        issuer_identity=issuer_identity,
        owner_authority_source=owner_authority_source,
    )
