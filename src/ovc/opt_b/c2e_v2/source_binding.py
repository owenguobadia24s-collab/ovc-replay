"""Exact revised-C2 package/source binding for C2E2-WP1."""
from __future__ import annotations

import copy
from typing import Any, Mapping

C2AR_PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
C2AR_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
C2AR_PERMISSION = "READ_ONLY_SHADOW_RESEARCH_ONLY"


class SourceBindingError(ValueError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise SourceBindingError(marker)


def validate_source_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(binding))
    _require(result.get("c2ar_package_id") == C2AR_PACKAGE_ID, "C2AR_PACKAGE_ID_MISMATCH")
    _require(result.get("c2ar_package_sha256") == C2AR_PACKAGE_SHA256, "C2AR_PACKAGE_HASH_MISMATCH")
    _require(result.get("research_consumer_permission") == C2AR_PERMISSION, "C2AR_PERMISSION_MISMATCH")
    _require(result.get("active") is False, "ACTIVE_C2_SOURCE_DENIED")
    _require(result.get("canonical") is False, "CANONICAL_C2_SOURCE_DENIED")
    for key in (
        "source_release_id", "source_manifest_id", "c2_release_id",
        "c2_contract_id", "source_build_commit",
    ):
        _require(bool(result.get(key)), f"SOURCE_BINDING_REQUIRED:{key}")
    result["binding_status"] = "EXACT_READ_ONLY_SHADOW"
    return result
