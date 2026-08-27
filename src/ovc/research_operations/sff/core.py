from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Mapping


class SFFContractError(ValueError):
    """A deterministic SFF contract was violated."""


class ChronologyError(SFFContractError):
    pass


class AuthorityError(SFFContractError):
    pass


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise SFFContractError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, float) and not math.isfinite(value):
        raise SFFContractError("non-finite values are not canonical")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise SFFContractError(f"unsupported canonical value: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Return the sole identity-bearing JSON representation."""

    return json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_identity(namespace: str, value: Any) -> str:
    if not namespace or namespace.strip() != namespace:
        raise SFFContractError("identity namespace must be explicit and normalized")
    digest = hashlib.sha256(canonical_bytes(value)).hexdigest()
    return f"{namespace}:{digest}"


def require_first_valid_chronology(*, antecedent_at: datetime, cutoff_at: datetime) -> None:
    if antecedent_at.tzinfo is None or cutoff_at.tzinfo is None:
        raise ChronologyError("timestamps must be timezone-aware")
    if antecedent_at >= cutoff_at:
        raise ChronologyError("antecedent must be strictly earlier than cutoff")


@dataclass(frozen=True)
class ResearchFreezeFrontier:
    frontier_id: str
    cutoff_at: datetime
    source_frontier_id: str
    owner_authority_id: str
    validation_state: str = "LOCKED_UNCONSUMED"

    def __post_init__(self) -> None:
        if self.validation_state != "LOCKED_UNCONSUMED":
            raise AuthorityError("Validation must remain locked and unconsumed")
        if self.cutoff_at.tzinfo is None or self.cutoff_at.utcoffset() is None:
            raise ChronologyError("freeze cutoff must be timezone-aware")
        for name in ("frontier_id", "source_frontier_id", "owner_authority_id"):
            if not getattr(self, name):
                raise SFFContractError(f"{name} is required")


@dataclass(frozen=True)
class TargetGrammarExposureManifest:
    manifest_id: str
    exposure_class: str
    grammar_identity: str
    selected_before_outcomes: bool
    activation_state: str = "CANDIDATE_ONLY_NOT_ACTIVE"

    def __post_init__(self) -> None:
        if self.activation_state != "CANDIDATE_ONLY_NOT_ACTIVE":
            raise AuthorityError("target vocabulary activation is not granted")
        if not self.selected_before_outcomes:
            raise ChronologyError("target grammar must be selected before outcomes")
        if not all((self.manifest_id, self.exposure_class, self.grammar_identity)):
            raise SFFContractError("target exposure fields are required")


@dataclass(frozen=True)
class TargetComplexityBudget:
    budget_id: str
    maximum_targets: int
    maximum_depth: int
    maximum_branching: int
    deep_tree_state: str = "DEFERRED_NON_EXECUTABLE"

    def __post_init__(self) -> None:
        if min(self.maximum_targets, self.maximum_depth, self.maximum_branching) < 1:
            raise SFFContractError("complexity limits must be positive")
        if self.maximum_depth != 1:
            raise AuthorityError("v0.1 permits one-step targets only")
        if self.deep_tree_state != "DEFERRED_NON_EXECUTABLE":
            raise AuthorityError("deep-tree activation is not granted")
