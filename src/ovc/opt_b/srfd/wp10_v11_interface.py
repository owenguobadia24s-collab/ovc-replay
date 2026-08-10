from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .serialization import logical_sha256, stable_id
from .wp10_v10_interface import (
    FROZEN_POPULATION_ID,
    PROGRAMME_ID,
    SCIENCE_BINDING,
    SCIENCE_IDENTITY_SHA256,
    T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,
)

PACKET_ID = "SRFDI-WP10-v1.1"
FROZEN_ENVIRONMENT_PROFILE_SHA256 = "d921fb6b7bf8632b705851c07a85d09218571780201050fde5d6f31dc04df6df"
HARDENING_REHEARSAL_SHA256 = "b44052db7f4f30a701d157bafaee463ff30cf4e66ad5a2f2715708241498422a"
# packet_id is execution/governance generation identity, not a scientific input.
# It is separately frozen by RunBindingV11.to_dict() and must differ from v1.0.
NON_SCIENCE_BINDING_FIELDS = frozenset({"packet_id"})


class WP10V11InterfaceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _hex64(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise WP10V11InterfaceError("V11_BINDING_INVALID", field)
    return text


def _hex40(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise WP10V11InterfaceError("V11_BINDING_INVALID", field)
    return text


@dataclass(frozen=True)
class RunBindingV11:
    programme_id: str
    packet_id: str
    population_id: str
    eligible_ids_sha256: str
    scientific_manifest_sha256: str
    preregistration_sha256: str
    representation_pack_sha256: str
    segmentation_pack_sha256: str
    stability_pack_sha256: str
    source_binding_sha256: str
    capacity_grid_sha256: str
    science_identity_sha256: str
    capacity_envelope_sha256: str
    storage_binding_sha256: str
    execution_binding_sha256: str
    execution_environment_profile_sha256: str
    hardening_rehearsal_sha256: str
    implementation_commit: str

    def to_dict(self) -> dict[str, str]:
        out = {name: str(getattr(self, name)).strip() for name in self.__dataclass_fields__}
        for name in (
            "eligible_ids_sha256", "scientific_manifest_sha256", "preregistration_sha256",
            "representation_pack_sha256", "segmentation_pack_sha256", "stability_pack_sha256",
            "source_binding_sha256", "capacity_grid_sha256", "science_identity_sha256",
            "capacity_envelope_sha256", "storage_binding_sha256", "execution_binding_sha256",
            "execution_environment_profile_sha256", "hardening_rehearsal_sha256",
        ):
            out[name] = _hex64(out[name], name)
        out["implementation_commit"] = _hex40(out["implementation_commit"], "implementation_commit")
        if out["programme_id"] != PROGRAMME_ID or out["packet_id"] != PACKET_ID or out["population_id"] != FROZEN_POPULATION_ID:
            raise WP10V11InterfaceError(
                "V11_IDENTITY_DRIFT",
                f"{out['programme_id']}:{out['packet_id']}:{out['population_id']}",
            )
        return out

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.to_dict())


def verify_science_unchanged(binding: RunBindingV11) -> None:
    actual = binding.to_dict()
    for key, expected in SCIENCE_BINDING.items():
        if key in NON_SCIENCE_BINDING_FIELDS:
            continue
        if actual[key] != expected:
            raise WP10V11InterfaceError("V11_SCIENCE_BINDING_DRIFT", f"{key}:{actual[key]}")
    if actual["science_identity_sha256"] != SCIENCE_IDENTITY_SHA256:
        raise WP10V11InterfaceError("V11_SCIENCE_IDENTITY_DRIFT", actual["science_identity_sha256"])
    if actual["execution_environment_profile_sha256"] != FROZEN_ENVIRONMENT_PROFILE_SHA256:
        raise WP10V11InterfaceError("V11_ENVIRONMENT_PROFILE_DRIFT", actual["execution_environment_profile_sha256"])
    if actual["hardening_rehearsal_sha256"] != HARDENING_REHEARSAL_SHA256:
        raise WP10V11InterfaceError("V11_HARDENING_REHEARSAL_DRIFT", actual["hardening_rehearsal_sha256"])


def binding_from_manifest(manifest: Mapping[str, Any]) -> RunBindingV11:
    raw = manifest.get("run_binding")
    if not isinstance(raw, Mapping):
        raise WP10V11InterfaceError("V11_MANIFEST_INVALID", "run_binding mapping required")
    keys = tuple(RunBindingV11.__dataclass_fields__)
    if set(raw) != set(keys):
        raise WP10V11InterfaceError("V11_BINDING_SHAPE_MISMATCH", f"keys={sorted(raw)}")
    binding = RunBindingV11(**{key: str(raw[key]) for key in keys})
    verify_science_unchanged(binding)
    if str(manifest.get("run_binding_sha256", "")) != binding.logical_hash:
        raise WP10V11InterfaceError("V11_MANIFEST_BINDING_HASH_MISMATCH", str(manifest.get("run_binding_sha256", "")))
    return binding


def mint_single_use_token(binding: RunBindingV11, *, operator_decision_id: str) -> dict[str, Any]:
    verify_science_unchanged(binding)
    core = {
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "run_binding_sha256": binding.logical_hash,
        "operator_decision_id": str(operator_decision_id),
        "cardinality": "ONE_EXACT_BOUND_RUN",
    }
    token_id = stable_id("SRFD.JUNE.AUTH.", core)
    return {
        "schema": "ovc-srfd-june-authority-token/v11",
        "token_id": token_id,
        "state": "AUTHORIZED_UNCONSUMED",
        "single_use": True,
        "run_cardinality": "ONE_EXACT_BOUND_RUN",
        "run_binding_sha256": binding.logical_hash,
        "operator_decision_id": str(operator_decision_id),
        "science_identity_sha256": SCIENCE_IDENTITY_SHA256,
        "execution_environment_profile_sha256": FROZEN_ENVIRONMENT_PROFILE_SHA256,
        "hardening_rehearsal_sha256": HARDENING_REHEARSAL_SHA256,
        "capacity_tier": "T1_EXTERNAL_ARTIFACT",
        "max_external_bytes": T1_EXTERNAL_ARTIFACT_LIMIT_BYTES,
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_promotion": "NONE",
        "selector_family_semantic_publication": "NONE",
        "probability_risk_exposure_execution": "NONE",
    }
