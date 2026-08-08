from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .serialization import logical_sha256, stable_id

GATE_ID = "SRFDI-G-JUNE-AUTH"
AUTHORIZED_DECISION = "AUTHORIZE_JUNE"
AUTHORIZED_RUN_STATE = "AUTHORIZED_BY_SRFDI_G_JUNE_AUTH"
PREREG_BYTE_SHA256 = "76a18f79596772343f398256582dab9c37e219d01345c606204230c554599792"
PREREG_LOGICAL_SHA256 = "a832daad99b6df49199eced0c35632b15974f86b58a8e6481350294a87d3d32e"


class JuneAuthorityError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _text(value: object, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", f"{field} must be non-empty")
    return text


def _hex64(value: object, field: str) -> str:
    text = _text(value, field).lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise JuneAuthorityError("QA_SCHEMA_FAILURE", f"{field} must be lowercase SHA-256 hex")
    return text


def _required_mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", f"{field} mapping required")
    return value


def _bound_hashes(values: object, field: str) -> list[str]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence) or not values:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", f"{field} must contain at least one SHA-256")
    return [_hex64(item, field) for item in values]


def manifest_binding_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload.pop("authority_binding", None)
    payload["run_authority"] = "PENDING_SRFDI_G_JUNE_AUTH"
    return payload


def manifest_binding_sha256(manifest: Mapping[str, Any]) -> str:
    return logical_sha256(manifest_binding_payload(manifest))


@dataclass(frozen=True)
class JuneRunAuthorityToken:
    token_id: str
    decision_id: str
    decision_logical_sha256: str
    manifest_logical_sha256: str
    authorized_manifest_sha256: str
    implementation_commit: str
    population_id: str
    source_release_id: str
    authority_state: str = AUTHORIZED_RUN_STATE

    def to_dict(self) -> dict[str, str]:
        return {
            "token_id": self.token_id,
            "decision_id": self.decision_id,
            "decision_logical_sha256": self.decision_logical_sha256,
            "manifest_logical_sha256": self.manifest_logical_sha256,
            "authorized_manifest_sha256": self.authorized_manifest_sha256,
            "implementation_commit": self.implementation_commit,
            "population_id": self.population_id,
            "source_release_id": self.source_release_id,
            "authority_state": self.authority_state,
        }


def verify_june_run_authority(
    decision: Mapping[str, Any] | None,
    manifest: Mapping[str, Any],
    *,
    expected_implementation_commit: str,
) -> JuneRunAuthorityToken:
    if decision is None:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "operator decision is required")
    if _text(decision.get("gate_id"), "decision.gate_id") != GATE_ID:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "wrong authority gate")
    if _text(decision.get("decision"), "decision.decision") != AUTHORIZED_DECISION:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "decision does not authorize June")
    decision_id = _text(decision.get("decision_id"), "decision.decision_id")

    authority_effect = _required_mapping(decision.get("authority_effect"), "decision.authority_effect")
    required_effect = {
        "june_execution": "AUTHORIZED_BOUNDED_JUNE_BENCHMARK",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_promotion": "NONE",
        "selector_change": "NONE",
        "publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }
    for field, expected in required_effect.items():
        if authority_effect.get(field) != expected:
            raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", f"decision authority effect mismatch:{field}")

    if manifest.get("run_authority_gate") != GATE_ID or manifest.get("run_authority") != AUTHORIZED_RUN_STATE:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest run authority is not exact")
    prereg = _required_mapping(manifest.get("preregistration"), "manifest.preregistration")
    if prereg.get("byte_sha256") != PREREG_BYTE_SHA256 or prereg.get("logical_sha256") != PREREG_LOGICAL_SHA256:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "preregistration hash mismatch")
    if prereg.get("freeze_gate") != "SRFDI-G9":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "preregistration freeze gate mismatch")
    if manifest.get("validation_2025") != "LOCKED_UNCONSUMED":
        raise JuneAuthorityError("AUTH_VALIDATION_DENIED", "Validation must remain locked")
    if manifest.get("selector_change") != "NONE" or manifest.get("scientific_promotion") != "NONE" or manifest.get("publication") != "NONE":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "reserved scientific authority changed")
    if manifest.get("probability_risk_exposure_execution") != "NONE":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "probability/risk/exposure/execution authority changed")

    required = _required_mapping(manifest.get("required_before_run_authority"), "manifest.required_before_run_authority")
    source = _required_mapping(required.get("source"), "manifest.source")
    population = _required_mapping(required.get("population"), "manifest.population")
    code = _required_mapping(required.get("code"), "manifest.code")
    rollback = _required_mapping(required.get("rollback"), "manifest.rollback")
    qa = _required_mapping(required.get("qa"), "manifest.qa")

    if source.get("provider_fetch") != "FORBIDDEN" or source.get("upstream_mutation") != "FORBIDDEN":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "source firewalls changed")
    source_release_id = _text(source.get("source_release_id"), "source_release_id")
    _text(source.get("source_commit"), "source_commit")
    _bound_hashes(source.get("source_hashes"), "source_hashes")

    population_id = _text(population.get("population_id"), "population_id")
    count = population.get("eligible_record_count")
    exclusion_count = population.get("exclusion_count")
    if not isinstance(count, int) or count < 1 or not isinstance(exclusion_count, int) or exclusion_count < 0:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "population counts must be bound")
    _hex64(population.get("eligible_record_ids_sha256"), "eligible_record_ids_sha256")
    _hex64(population.get("exclusion_ledger_sha256"), "exclusion_ledger_sha256")

    implementation_commit = _text(code.get("implementation_commit"), "implementation_commit")
    if implementation_commit != _text(expected_implementation_commit, "expected_implementation_commit"):
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "implementation commit mismatch")
    _hex64(code.get("dependency_manifest_sha256"), "dependency_manifest_sha256")
    if qa.get("exact_preregistration_hash") != "REQUIRED_MATCH" or qa.get("pre_run_checks") != "REQUIRED_PASS" or qa.get("retrospective_isolation") != "REQUIRED_PASS":
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "QA preconditions changed")
    if rollback.get("upstream_mutation") != "FORBIDDEN" or rollback.get("safe_cancellation") != "REQUIRED":
        raise JuneAuthorityError("AUTH_SCOPE_EXPANSION", "rollback firewalls changed")

    binding_hash = manifest_binding_sha256(manifest)
    decision_binding_hash = _hex64(decision.get("authorized_manifest_sha256"), "decision.authorized_manifest_sha256")
    if decision_binding_hash != binding_hash:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "operator decision does not bind this manifest")
    decision_hash = logical_sha256(decision)
    authority_binding = _required_mapping(manifest.get("authority_binding"), "manifest.authority_binding")
    if authority_binding.get("gate_id") != GATE_ID or authority_binding.get("decision_id") != decision_id:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest authority decision identity mismatch")
    if _hex64(authority_binding.get("decision_logical_sha256"), "authority_binding.decision_logical_sha256") != decision_hash:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest decision hash mismatch")
    if _hex64(authority_binding.get("authorized_manifest_sha256"), "authority_binding.authorized_manifest_sha256") != binding_hash:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest binding hash mismatch")

    manifest_hash = logical_sha256(manifest)
    token_payload = {
        "decision_id": decision_id,
        "decision_logical_sha256": decision_hash,
        "manifest_logical_sha256": manifest_hash,
        "authorized_manifest_sha256": binding_hash,
        "implementation_commit": implementation_commit,
        "population_id": population_id,
        "source_release_id": source_release_id,
    }
    return JuneRunAuthorityToken(
        token_id=stable_id("SRFD.JUNE.AUTH.", token_payload),
        decision_id=decision_id,
        decision_logical_sha256=decision_hash,
        manifest_logical_sha256=manifest_hash,
        authorized_manifest_sha256=binding_hash,
        implementation_commit=implementation_commit,
        population_id=population_id,
        source_release_id=source_release_id,
    )


def guard_bounded_june_run(token: JuneRunAuthorityToken | None, manifest: Mapping[str, Any]) -> None:
    if token is None:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "bounded June authority token required")
    if token.authority_state != AUTHORIZED_RUN_STATE:
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "authority token is not active for bounded June")
    if token.manifest_logical_sha256 != logical_sha256(manifest):
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest differs from authorized token")
    if token.authorized_manifest_sha256 != manifest_binding_sha256(manifest):
        raise JuneAuthorityError("AUTH_JUNE_NOT_AUTHORISED", "manifest binding differs from authorized token")
