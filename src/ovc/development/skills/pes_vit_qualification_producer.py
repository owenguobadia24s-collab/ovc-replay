from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from ovc.development.skills.vit_routing import validate_vit_lineage_record


PRODUCER_REQUEST_SCHEMA = "ovc-pes-vit-qualification-publication-request/v0.1"
PRODUCER_ACTIVATION_SCHEMA = "ovc-pes-vit-qualification-producer-runtime-activation/v0.1"
PRODUCER_DISPATCH_SCHEMA = "ovc-pes-vit-qualification-producer-dispatch/v0.1"
PRODUCER_ACTIVATION_GATE = "DSAI3V-PES-VIT-G-PRODUCER-ACTIVATION"
PRODUCER_ACTIVATION_PHRASE = "OVC APPROVE PES-VIT-QUALIFICATION-PRODUCER ACTIVATION PASS"
PRODUCER_TARGET_LEDGER_BRANCH = "ovc/vit-qualification-ledger-v1"
PRODUCER_TARGET_LEDGER_ROOT = ".ovc/vit-qualifications"
PRODUCER_WRITE_SCOPE = "ENVELOPE_AND_EXACT_HEAD_POINTER_ONLY"
PRODUCER_DISPATCH_ACTION = "PUBLISH_DETACHED_VIT_QUALIFICATION"
PRODUCER_DISPATCH_WRITE_DOMAIN = (
    f"{PRODUCER_TARGET_LEDGER_BRANCH}:{PRODUCER_TARGET_LEDGER_ROOT}"
)
PRODUCER_SEMANTIC_OWNER = "DSAI_VIT_PHYSICAL_CONTROLLER"
OWNER_AUTHORITY_SOURCE_KIND = "DURABLE_OWNER_AUTHORITY_RECORD"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")

_REQUIRED_CAPABILITIES = {
    "ledger_write": True,
    "persistent_dispatch": True,
    "event_subscription": False,
    "polling": False,
    "direct_main_write": False,
    "merge": False,
    "force_push": False,
    "history_rewrite": False,
    "programme_authority": False,
    "vit_authority": False,
    "siq_authority": False,
    "grt_authority": False,
}


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


@dataclass(frozen=True)
class ValidatedProducerActivation:
    activation_id: str
    gate_id: str
    ledger_branch: str
    ledger_root: str
    write_scope: str


@dataclass(frozen=True)
class ValidatedProducerDispatch:
    dispatch_id: str
    activation_id: str
    request_id: str
    executor_identity: str
    fencing_generation: int


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
    issuer_identity = _required_text(
        issuer_identity,
        "PES_VIT_PRODUCER_ISSUER_MISSING",
    )
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
    identity_payload = {
        key: value
        for key, value in request.items()
        if key != "request_id"
    }
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
    issuer_identity = _required_text(
        issuance.get("issuer_identity"),
        "PES_VIT_PRODUCER_ISSUER_MISSING",
    )
    expected_issuer_identity = _required_text(
        expected_issuer_identity,
        "PES_VIT_PRODUCER_EXPECTED_ISSUER_MISSING",
    )
    if issuer_identity != expected_issuer_identity:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ISSUER_NOT_AUTHORISED")
    if issuance.get("owner_authority_source_kind") != OWNER_AUTHORITY_SOURCE_KIND:
        raise PesVitQualificationProducerError(
            "PES_VIT_PRODUCER_OWNER_AUTHORITY_SOURCE_KIND_INVALID"
        )
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


def validate_producer_activation(
    activation: Mapping[str, Any],
) -> ValidatedProducerActivation:
    if str(activation.get("schema_version", "")) != PRODUCER_ACTIVATION_SCHEMA:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ACTIVATION_SCHEMA_INVALID")
    activation_id = str(activation.get("activation_id", "")).strip()
    if not SHA64.fullmatch(activation_id):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ACTIVATION_ID_INVALID")
    identity_payload = {
        key: value
        for key, value in activation.items()
        if key != "activation_id"
    }
    if _canonical_sha256(identity_payload) != activation_id:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ACTIVATION_ID_MISMATCH")
    if activation.get("gate_id") != PRODUCER_ACTIVATION_GATE:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ACTIVATION_GATE_INVALID")
    if activation.get("decision") != "PASS" or activation.get("status") != "ACTIVE":
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ACTIVATION_NOT_ACTIVE")
    if activation.get("operator_phrase") != PRODUCER_ACTIVATION_PHRASE:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_OPERATOR_GRANT_MISMATCH")
    if activation.get("authority_effect") != "BOUNDED_INFRASTRUCTURE_ACTIVATION":
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ACTIVATION_EFFECT_INVALID")
    if activation.get("executor_scope") != "TRUSTED_OWNER_ISSUED_REQUEST_ONLY":
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_EXECUTOR_SCOPE_INVALID")

    target = activation.get("target")
    if not isinstance(target, Mapping):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ACTIVATION_TARGET_INVALID")
    expected_target = {
        "ledger_branch": PRODUCER_TARGET_LEDGER_BRANCH,
        "ledger_root": PRODUCER_TARGET_LEDGER_ROOT,
        "write_scope": PRODUCER_WRITE_SCOPE,
    }
    if dict(target) != expected_target:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_ACTIVATION_TARGET_DRIFT")

    capabilities = activation.get("capabilities")
    if not isinstance(capabilities, Mapping) or dict(capabilities) != _REQUIRED_CAPABILITIES:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_CAPABILITY_DRIFT")

    return ValidatedProducerActivation(
        activation_id=activation_id,
        gate_id=PRODUCER_ACTIVATION_GATE,
        ledger_branch=PRODUCER_TARGET_LEDGER_BRANCH,
        ledger_root=PRODUCER_TARGET_LEDGER_ROOT,
        write_scope=PRODUCER_WRITE_SCOPE,
    )


def build_producer_dispatch(
    *,
    request: Mapping[str, Any],
    activation: Mapping[str, Any],
    expected_issuer_identity: str,
    fencing_generation: int,
) -> Mapping[str, Any]:
    validated_request = validate_qualification_publication_request(
        request,
        expected_issuer_identity=expected_issuer_identity,
    )
    validated_activation = validate_producer_activation(activation)
    if fencing_generation < 1:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_FENCE_INVALID")
    payload = {
        "schema_version": PRODUCER_DISPATCH_SCHEMA,
        "activation_id": validated_activation.activation_id,
        "request_id": validated_request.request_id,
        "executor_identity": validated_request.issuer_identity,
        "action": PRODUCER_DISPATCH_ACTION,
        "write_domain": PRODUCER_DISPATCH_WRITE_DOMAIN,
        "semantic_owner": PRODUCER_SEMANTIC_OWNER,
        "fencing_generation": int(fencing_generation),
        "authority_effect": "NONE_EXECUTE_AUTHORISED_OWNER_REQUEST",
    }
    return {**payload, "dispatch_id": _canonical_sha256(payload)}


def validate_producer_dispatch(
    dispatch: Mapping[str, Any],
    *,
    request: ValidatedQualificationPublicationRequest,
    activation: ValidatedProducerActivation,
    expected_fencing_generation: int,
) -> ValidatedProducerDispatch:
    if str(dispatch.get("schema_version", "")) != PRODUCER_DISPATCH_SCHEMA:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_SCHEMA_INVALID")
    dispatch_id = str(dispatch.get("dispatch_id", "")).strip()
    if not SHA64.fullmatch(dispatch_id):
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_ID_INVALID")
    identity_payload = {
        key: value
        for key, value in dispatch.items()
        if key != "dispatch_id"
    }
    if _canonical_sha256(identity_payload) != dispatch_id:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_ID_MISMATCH")
    if dispatch.get("activation_id") != activation.activation_id:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_ACTIVATION_MISMATCH")
    if dispatch.get("request_id") != request.request_id:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_REQUEST_MISMATCH")
    if dispatch.get("executor_identity") != request.issuer_identity:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_EXECUTOR_MISMATCH")
    if dispatch.get("action") != PRODUCER_DISPATCH_ACTION:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_ACTION_INVALID")
    if dispatch.get("write_domain") != PRODUCER_DISPATCH_WRITE_DOMAIN:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_WRITE_DOMAIN_INVALID")
    if dispatch.get("semantic_owner") != PRODUCER_SEMANTIC_OWNER:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_SEMANTIC_OWNER_INVALID")
    try:
        fencing_generation = int(dispatch.get("fencing_generation"))
    except (TypeError, ValueError) as exc:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_FENCE_INVALID") from exc
    if expected_fencing_generation < 1 or fencing_generation != expected_fencing_generation:
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_STALE_FENCE")
    if dispatch.get("authority_effect") != "NONE_EXECUTE_AUTHORISED_OWNER_REQUEST":
        raise PesVitQualificationProducerError("PES_VIT_PRODUCER_DISPATCH_EFFECT_INVALID")

    return ValidatedProducerDispatch(
        dispatch_id=dispatch_id,
        activation_id=activation.activation_id,
        request_id=request.request_id,
        executor_identity=request.issuer_identity,
        fencing_generation=fencing_generation,
    )
