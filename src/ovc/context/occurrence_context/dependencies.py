from __future__ import annotations

from typing import Iterable

from .models import ContextDependencyRef
from .serialization import canonical_json, sha256_payload


def dependency_set_hash(dependencies: Iterable[ContextDependencyRef]) -> str:
    values = [dependency.to_dict() for dependency in dependencies]
    values.sort(key=canonical_json)
    return sha256_payload("OVC.OCCURRENCE_CONTEXT.DEPENDENCIES", values)


def dependency_first_valid_times(dependencies: Iterable[ContextDependencyRef]) -> tuple[str, ...]:
    return tuple(dependency.first_valid_time for dependency in dependencies)
