from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .canonical import sha256_canonical


class ESLReadModelError(ValueError):
    pass


PROJECTION_KEYS = (
    "occurrence",
    "evidence_frontier",
    "states",
    "sri",
    "organisation",
    "constraint",
    "qualification",
    "ast",
    "render",
)

FORBIDDEN_COMPUTATION_KEYS = frozenset({
    "score",
    "candidate_strength",
    "probability",
    "forecast",
    "expected_return",
    "risk",
    "exposure",
    "trade_direction",
    "derived_metric",
})


def _scan_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in FORBIDDEN_COMPUTATION_KEYS:
                raise ESLReadModelError(f"FRONTEND_SCIENTIFIC_CALCULATION_FORBIDDEN:{path}.{key_text}")
            _scan_forbidden(child, f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _scan_forbidden(child, f"{path}[{index}]")


def build_esl_read_model(
    *,
    source_refs: Sequence[str],
    projections: Mapping[str, Any],
    authority: Mapping[str, Any],
    lineage_refs: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a deterministic GET-only ESL projection without deriving scientific truth."""
    refs = sorted({str(ref) for ref in source_refs if str(ref)})
    if not refs:
        raise ESLReadModelError("READ_MODEL_SOURCE_REF_REQUIRED")
    unknown = sorted(set(map(str, projections.keys())) - set(PROJECTION_KEYS))
    if unknown:
        raise ESLReadModelError("READ_MODEL_UNKNOWN_PROJECTION:" + ",".join(unknown))
    if not authority:
        raise ESLReadModelError("READ_MODEL_AUTHORITY_PROJECTION_REQUIRED")
    if authority.get("authority_effect") not in (None, "NONE"):
        raise ESLReadModelError("READ_MODEL_CANNOT_GRANT_AUTHORITY")

    copied: dict[str, Any] = {key: deepcopy(projections.get(key)) for key in PROJECTION_KEYS}
    _scan_forbidden(copied)
    payload = {
        "schema": "ovc-esl-read-model/v1",
        "projection_mode": "READ_ONLY",
        "source_refs": refs,
        "projections": copied,
        "authority": deepcopy(dict(authority)),
        "lineage_refs": sorted({str(ref) for ref in lineage_refs if str(ref)}),
        "calculation_policy": "NO_FRONTEND_SCIENTIFIC_CALCULATION",
        "authority_effect": "NONE",
    }
    payload["read_model_id"] = "eslrm1:" + sha256_canonical(payload)
    return payload


def assert_projection_fidelity(*, read_model: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    if read_model.get("projection_mode") != "READ_ONLY":
        raise ESLReadModelError("READ_MODEL_NOT_READ_ONLY")
    actual = read_model.get("projections")
    if not isinstance(actual, Mapping):
        raise ESLReadModelError("READ_MODEL_PROJECTIONS_INVALID")
    for key in PROJECTION_KEYS:
        if actual.get(key) != expected.get(key):
            raise ESLReadModelError(f"READ_MODEL_FIDELITY_MISMATCH:{key}")
    _scan_forbidden(actual)
