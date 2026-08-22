"""Inactive, library-first exact service resolution and migration governance.

The directory is a non-authoritative projection over owner registries. Resolution
is exact and fail-closed; this module cannot select a live consumer binding.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable, Mapping

from .envelopes import AdapterDescriptor, CompatibilityContract


class SharedResolutionError(ValueError):
    """A fail-closed Shared Systems WP5 contract violation."""


def _text(value: str, field: str, *, exact: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise SharedResolutionError(f"{field.upper()}_REQUIRED")
    if exact and "latest" in value.casefold():
        raise SharedResolutionError("NORMATIVE_LATEST_RESOLUTION_FORBIDDEN")
    return value


def _refs(values: tuple[str, ...], field: str, *, allow_empty: bool = False) -> None:
    if not isinstance(values, tuple) or (not values and not allow_empty):
        raise SharedResolutionError(f"{field.upper()}_REQUIRED")
    if any(not isinstance(value, str) or not value for value in values):
        raise SharedResolutionError(f"{field.upper()}_INVALID")
    if len(values) != len(set(values)):
        raise SharedResolutionError(f"{field.upper()}_DUPLICATE")


def _hash(value: object) -> str:
    try:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SharedResolutionError("NON_CANONICAL_RESOLUTION_VALUE") from exc
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SharedServiceDescriptor:
    service_id: str
    release_id: str
    owner_programme_id: str
    registry_id: str
    capability_ids: tuple[str, ...]
    contract_refs: tuple[str, ...]
    qualification_ref: str
    lifecycle: str
    materialized: bool
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "service_id",
            "release_id",
            "owner_programme_id",
            "registry_id",
            "qualification_ref",
        ):
            _text(getattr(self, field), field, exact=field in {"release_id", "qualification_ref"})
        _refs(self.capability_ids, "capability_ids")
        _refs(self.contract_refs, "contract_refs")
        for ref in self.contract_refs:
            _text(ref, "contract_ref", exact=True)
        if self.lifecycle not in {
            "PROPOSED",
            "ADMITTED",
            "CURRENT",
            "SUPERSEDED",
            "RETIRED",
            "QUARANTINED",
        }:
            raise SharedResolutionError("SERVICE_LIFECYCLE_UNKNOWN")
        if self.authority_effect != "NONE":
            raise SharedResolutionError("SERVICE_DESCRIPTOR_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class RegistryDirectoryEntry:
    service_id: str
    owner_programme_id: str
    registry_id: str
    stage0_binding_id: str

    def __post_init__(self) -> None:
        for field in (
            "service_id",
            "owner_programme_id",
            "registry_id",
            "stage0_binding_id",
        ):
            _text(getattr(self, field), field)


class RegistryDirectory:
    """A deterministic locator that cannot override a Stage-0 owner binding."""

    def __init__(
        self,
        entries: Iterable[RegistryDirectoryEntry],
        *,
        stage0_owner_bindings: Mapping[str, str],
    ) -> None:
        self._stage0 = dict(stage0_owner_bindings)
        grouped: dict[str, list[RegistryDirectoryEntry]] = {}
        for entry in entries:
            expected = self._stage0.get(entry.service_id)
            if expected is None:
                raise SharedResolutionError("STAGE0_OWNER_BINDING_MISSING")
            if expected != entry.owner_programme_id:
                raise SharedResolutionError("SERVICE_GOVERNANCE_CONFLICT")
            grouped.setdefault(entry.service_id, []).append(entry)
        if any(len(items) != 1 for items in grouped.values()):
            raise SharedResolutionError("REGISTRY_DIRECTORY_AMBIGUOUS")
        self._entries = {key: items[0] for key, items in grouped.items()}

    def locate(self, service_id: str) -> RegistryDirectoryEntry | None:
        return self._entries.get(service_id)

    def projection(self) -> dict[str, object]:
        rows = [asdict(self._entries[key]) for key in sorted(self._entries)]
        payload = {"entries": rows, "authoritative": False}
        return {**payload, "logical_id": _hash(payload), "authority_effect": "NONE"}


@dataclass(frozen=True)
class ServiceConsumptionBinding:
    binding_id: str
    consumer_programme_id: str
    service_id: str
    capability_id: str
    allowed_release_ids: tuple[str, ...]
    authority_refs: tuple[str, ...]
    status: str = "INACTIVE_REFERENCE"
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("binding_id", "consumer_programme_id", "service_id", "capability_id"):
            _text(getattr(self, field), field)
        _refs(self.allowed_release_ids, "allowed_release_ids")
        _refs(self.authority_refs, "authority_refs")
        for release_id in self.allowed_release_ids:
            _text(release_id, "allowed_release_id", exact=True)
        if self.status not in {"INACTIVE_REFERENCE", "SHADOW_ONLY"}:
            raise SharedResolutionError("ACTIVE_CONSUMER_BINDING_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise SharedResolutionError("CONSUMPTION_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class ResolutionRequest:
    request_id: str
    requester_programme_id: str
    requester_generation: str
    service_id: str
    capability_id: str
    required_release_id: str
    required_contract_ref: str
    semantic_scope: str
    authority_ref: str
    environment_ref: str
    cutoff_ref: str | None = None

    def __post_init__(self) -> None:
        for field in (
            "request_id",
            "requester_programme_id",
            "requester_generation",
            "service_id",
            "capability_id",
            "required_release_id",
            "required_contract_ref",
            "semantic_scope",
            "authority_ref",
            "environment_ref",
        ):
            _text(
                getattr(self, field),
                field,
                exact=field in {"requester_generation", "required_release_id", "required_contract_ref"},
            )
        if self.cutoff_ref is not None:
            _text(self.cutoff_ref, "cutoff_ref", exact=True)


@dataclass(frozen=True)
class ResolutionManifest:
    request_id: str
    status: str
    reason_codes: tuple[str, ...]
    service_id: str
    release_id: str | None
    owner_programme_id: str | None
    registry_id: str | None
    contract_ref: str | None
    compatibility_ref: str | None
    adapter_chain: tuple[str, ...]
    qualification_ref: str | None
    consumption_binding_ref: str | None
    authority_ref: str
    environment_ref: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.status not in {
            "RESOLVED",
            "MISSING",
            "AMBIGUOUS",
            "STALE_QUALIFICATION",
            "INCOMPATIBLE",
            "UNAUTHORIZED",
            "OWNER_CONFLICT",
            "NOT_MATERIALIZED",
            "QUARANTINED",
        }:
            raise SharedResolutionError("RESOLUTION_STATUS_UNKNOWN")
        if self.status == "RESOLVED" and self.reason_codes:
            raise SharedResolutionError("RESOLVED_REASON_CODES_FORBIDDEN")
        if self.status != "RESOLVED" and not self.reason_codes:
            raise SharedResolutionError("FAILED_RESOLUTION_REASON_REQUIRED")
        if self.authority_effect != "NONE":
            raise SharedResolutionError("RESOLUTION_AUTHORITY_EFFECT_FORBIDDEN")

    @property
    def logical_id(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class CompatibilityRegistry:
    contracts: tuple[CompatibilityContract, ...]

    def resolve(self, producer_ref: str, consumer_ref: str) -> CompatibilityContract | None:
        matches = [
            item
            for item in self.contracts
            if item.producer_contract_ref == producer_ref
            and item.consumer_contract_ref == consumer_ref
        ]
        if len(matches) > 1:
            raise SharedResolutionError("COMPATIBILITY_AMBIGUOUS")
        return matches[0] if matches else None


@dataclass(frozen=True)
class AdapterRegistry:
    adapters: tuple[AdapterDescriptor, ...]

    def resolve(self, source_ref: str, target_ref: str) -> AdapterDescriptor | None:
        matches = [
            item
            for item in self.adapters
            if item.source_contract_ref == source_ref and item.target_contract_ref == target_ref
        ]
        if len(matches) > 1:
            raise SharedResolutionError("ADAPTER_AMBIGUOUS")
        return matches[0] if matches else None


def _failed(request: ResolutionRequest, status: str, reason: str) -> ResolutionManifest:
    return ResolutionManifest(
        request.request_id,
        status,
        (reason,),
        request.service_id,
        None,
        None,
        None,
        None,
        None,
        (),
        None,
        None,
        request.authority_ref,
        request.environment_ref,
    )


def resolve_exact(
    request: ResolutionRequest,
    *,
    directory: RegistryDirectory,
    owner_descriptors: Mapping[str, tuple[SharedServiceDescriptor, ...]],
    consumption_bindings: Iterable[ServiceConsumptionBinding],
    qualification_currentness: Mapping[str, str],
    compatibility_registry: CompatibilityRegistry,
    adapter_registry: AdapterRegistry,
) -> ResolutionManifest:
    entry = directory.locate(request.service_id)
    if entry is None:
        return _failed(request, "MISSING", "DIRECTORY_ENTRY_MISSING")
    descriptors = owner_descriptors.get(entry.registry_id)
    if descriptors is None:
        return _failed(request, "MISSING", "OWNER_REGISTRY_MISSING")
    matches = [
        item
        for item in descriptors
        if item.service_id == request.service_id
        and item.release_id == request.required_release_id
    ]
    if not matches:
        return _failed(request, "MISSING", "EXACT_RELEASE_MISSING")
    if len(matches) > 1:
        return _failed(request, "AMBIGUOUS", "EXACT_RELEASE_AMBIGUOUS")
    descriptor = matches[0]
    if (
        descriptor.owner_programme_id != entry.owner_programme_id
        or descriptor.registry_id != entry.registry_id
    ):
        return _failed(request, "OWNER_CONFLICT", "OWNER_REGISTRY_DISAGREEMENT")
    if descriptor.lifecycle == "QUARANTINED":
        return _failed(request, "QUARANTINED", "SERVICE_RELEASE_QUARANTINED")
    if descriptor.lifecycle != "CURRENT":
        return _failed(request, "MISSING", "SERVICE_RELEASE_NOT_CURRENT")
    if not descriptor.materialized:
        return _failed(request, "NOT_MATERIALIZED", "SERVICE_RELEASE_NOT_MATERIALIZED")
    if request.capability_id not in descriptor.capability_ids:
        return _failed(request, "INCOMPATIBLE", "CAPABILITY_UNAVAILABLE")

    bindings = [
        item
        for item in consumption_bindings
        if item.consumer_programme_id == request.requester_programme_id
        and item.service_id == request.service_id
        and item.capability_id == request.capability_id
        and request.required_release_id in item.allowed_release_ids
    ]
    if len(bindings) != 1:
        return _failed(
            request,
            "AMBIGUOUS" if len(bindings) > 1 else "UNAUTHORIZED",
            "CONSUMPTION_BINDING_AMBIGUOUS" if len(bindings) > 1 else "CONSUMPTION_BINDING_MISSING",
        )
    binding = bindings[0]
    if request.authority_ref not in binding.authority_refs:
        return _failed(request, "UNAUTHORIZED", "AUTHORITY_REF_NOT_BOUND")
    if qualification_currentness.get(descriptor.qualification_ref) != "CURRENT":
        return _failed(request, "STALE_QUALIFICATION", "QUALIFICATION_NOT_CURRENT")

    producer_ref: str
    compatibility_ref: str | None = None
    adapter_chain: tuple[str, ...] = ()
    if request.required_contract_ref in descriptor.contract_refs:
        producer_ref = request.required_contract_ref
    else:
        paths: list[tuple[str, str, tuple[str, ...]]] = []
        missing_required_adapter = False
        for candidate_ref in sorted(descriptor.contract_refs):
            try:
                compatibility = compatibility_registry.resolve(
                    candidate_ref, request.required_contract_ref
                )
            except SharedResolutionError:
                return _failed(request, "AMBIGUOUS", "COMPATIBILITY_AMBIGUOUS")
            if compatibility is None or compatibility.compatibility_class in {
                "INCOMPATIBLE",
                "UNKNOWN",
                "HISTORICAL_REPLAY_ONLY",
            }:
                continue
            chain: tuple[str, ...] = ()
            if compatibility.compatibility_class in {
                "ADAPTER_REQUIRED",
                "LOSSY_ADAPTER_ALLOWED",
            }:
                try:
                    adapter = adapter_registry.resolve(
                        candidate_ref, request.required_contract_ref
                    )
                except SharedResolutionError:
                    return _failed(request, "AMBIGUOUS", "ADAPTER_AMBIGUOUS")
                if adapter is None:
                    missing_required_adapter = True
                    continue
                chain = (adapter.adapter_id,)
            paths.append(
                (candidate_ref, compatibility.compatibility_contract_id, chain)
            )
        if len(paths) > 1:
            return _failed(request, "AMBIGUOUS", "CONTRACT_PATH_AMBIGUOUS")
        if not paths:
            return _failed(
                request,
                "INCOMPATIBLE",
                "REQUIRED_ADAPTER_MISSING"
                if missing_required_adapter
                else "CONTRACT_INCOMPATIBLE",
            )
        producer_ref, compatibility_ref, adapter_chain = paths[0]

    return ResolutionManifest(
        request.request_id,
        "RESOLVED",
        (),
        descriptor.service_id,
        descriptor.release_id,
        descriptor.owner_programme_id,
        descriptor.registry_id,
        producer_ref,
        compatibility_ref,
        adapter_chain,
        descriptor.qualification_ref,
        binding.binding_id,
        request.authority_ref,
        request.environment_ref,
    )


@dataclass(frozen=True)
class SharedExecutionContext:
    context_id: str
    request_ref: str
    resolution_manifest_id: str
    service_id: str
    release_id: str
    contract_ref: str
    adapter_chain: tuple[str, ...]
    authority_ref: str
    environment_ref: str
    reresolution_barrier_ref: str | None = None

    @classmethod
    def freeze(cls, context_id: str, manifest: ResolutionManifest) -> "SharedExecutionContext":
        if manifest.status != "RESOLVED":
            raise SharedResolutionError("FAILED_RESOLUTION_CONTEXT_FORBIDDEN")
        assert manifest.release_id and manifest.contract_ref
        return cls(
            context_id,
            manifest.request_id,
            manifest.logical_id,
            manifest.service_id,
            manifest.release_id,
            manifest.contract_ref,
            manifest.adapter_chain,
            manifest.authority_ref,
            manifest.environment_ref,
        )

    def reresolve(
        self, manifest: ResolutionManifest, *, barrier_ref: str
    ) -> "SharedExecutionContext":
        _text(barrier_ref, "reresolution_barrier_ref")
        replacement = self.freeze(self.context_id, manifest)
        return SharedExecutionContext(
            **{**asdict(replacement), "reresolution_barrier_ref": barrier_ref}
        )


@dataclass(frozen=True)
class ServiceCurrentBinding:
    binding_id: str
    service_id: str
    release_id: str
    status: str = "INACTIVE_REFERENCE"
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("binding_id", "service_id", "release_id"):
            _text(getattr(self, field), field, exact=field == "release_id")
        if self.status not in {"INACTIVE_REFERENCE", "SHADOW_ONLY"}:
            raise SharedResolutionError("ACTIVE_SERVICE_CURRENT_BINDING_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise SharedResolutionError("SERVICE_CURRENT_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class MigrationInventory:
    inventory_id: str
    consumer_programme_id: str
    current_binding_ref: str
    proposed_service_id: str
    disposition: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "inventory_id",
            "consumer_programme_id",
            "current_binding_ref",
            "proposed_service_id",
        ):
            _text(getattr(self, field), field)
        if self.disposition not in {"CANDIDATE", "DO_NOT_MIGRATE", "DEFERRED"}:
            raise SharedResolutionError("MIGRATION_DISPOSITION_UNKNOWN")
        if self.authority_effect != "NONE":
            raise SharedResolutionError("MIGRATION_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class NonMigrationDecision:
    decision_id: str
    consumer_programme_id: str
    subject_ref: str
    reason_codes: tuple[str, ...]
    trigger_refs: tuple[str, ...]
    review_barrier_ref: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "decision_id",
            "consumer_programme_id",
            "subject_ref",
            "review_barrier_ref",
        ):
            _text(getattr(self, field), field)
        _refs(self.reason_codes, "reason_codes")
        _refs(self.trigger_refs, "trigger_refs")
        if self.authority_effect != "NONE":
            raise SharedResolutionError("NON_MIGRATION_AUTHORITY_EFFECT_FORBIDDEN")


class NonMigrationDecisionRegistry:
    def __init__(self, decisions: Iterable[NonMigrationDecision]) -> None:
        rows = tuple(decisions)
        ids = [item.decision_id for item in rows]
        subjects = [
            (item.consumer_programme_id, item.subject_ref) for item in rows
        ]
        if len(ids) != len(set(ids)) or len(subjects) != len(set(subjects)):
            raise SharedResolutionError("NON_MIGRATION_DECISION_AMBIGUOUS")
        self._decisions = rows

    def triggered(self, changed_refs: Iterable[str]) -> tuple[str, ...]:
        changed = set(changed_refs)
        return tuple(
            sorted(
                item.decision_id
                for item in self._decisions
                if changed & set(item.trigger_refs)
            )
        )

    def projection(self) -> dict[str, object]:
        rows = sorted(
            (asdict(item) for item in self._decisions),
            key=lambda row: (row["consumer_programme_id"], row["subject_ref"]),
        )
        payload = {"decisions": rows}
        return {**payload, "logical_id": _hash(payload), "authority_effect": "NONE"}
