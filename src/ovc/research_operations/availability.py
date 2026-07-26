from __future__ import annotations

from typing import Any


def derive_reproducibility_state(artifact_refs: list[dict[str, Any]]) -> str:
    required = [ref for ref in artifact_refs if ref.get("required", True)]
    if not required:
        return "REPRODUCIBLE"
    verified = sum(1 for ref in required if ref.get("availability") == "VERIFIED")
    if verified == len(required):
        return "REPRODUCIBLE"
    if verified == 0:
        return "NOT_REPRODUCIBLE"
    return "PARTIALLY_AVAILABLE"
