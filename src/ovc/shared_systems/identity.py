"""Shared Systems v0.1 deterministic identity/profile reference core.

The module is intentionally standard-library-only. Hash algorithms, serialization
profiles, identity projections and legacy bindings remain separate registry objects;
none of their identifiers may substitute for another.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping
import unicodedata


class SharedIdentityError(ValueError):
    """Base class for fail-closed Shared Systems identity errors."""


class UnknownIdentityBinding(SharedIdentityError):
    """Raised when an exact registered profile, projection or legacy binding is absent."""


class AmbiguousIdentityBinding(SharedIdentityError):
    """Raised when context resolves more than one lawful identity binding."""


class ProfileCollisionError(SharedIdentityError):
    """Raised when one profile identifier is attached to different semantics."""


class NonCanonicalIdentityPayload(SharedIdentityError):
    """Raised when input violates the selected profile or projection."""


_PROFILE_FIELDS = (
    "serialization_profile_id", "profile_version", "character_encoding",
    "unicode_policy", "object_key_order", "numeric_policy", "negative_zero_policy",
    "collection_policy", "null_policy", "timestamp_policy", "string_policy",
    "identity_projection_ref", "self_identity_exclusion_policy",
    "storage_framing_policy", "hash_algorithm_ref", "conformance_vector_set_ref",
)
_PROJECTION_FIELDS = (
    "projection_id", "owner_namespace", "included_fields", "excluded_fields",
    "conditional_fields", "self_id_fields", "descriptive_only_fields",
    "projection_version",
)
_LEGACY_FIELDS = (
    "binding_id", "legacy_identifier", "owner_namespace", "pack_id", "generation_id",
    "serialization_profile_id", "identity_projection_id", "hash_algorithm_id",
    "historical_digest", "status",
)


def _strict_fields(value: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    expected_set = set(expected)
    observed = set(value)
    if observed != expected_set:
        missing = sorted(expected_set - observed)
        unknown = sorted(observed - expected_set)
        raise SharedIdentityError(f"{label}_FIELDS_INVALID:missing={missing}:unknown={unknown}")


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SharedIdentityError(f"{field}_INVALID")
    return value


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise SharedIdentityError(f"{field}_INVALID")
    result = tuple(value)
    if len(result) != len(set(result)):
        raise SharedIdentityError(f"{field}_DUPLICATE")
    return result


@dataclass(frozen=True)
class HashAlgorithmDescriptor:
    hash_algorithm_id: str
    hashlib_name: str
    digest_hex_length: int
    usage: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "HashAlgorithmDescriptor":
        _strict_fields(
            value,
            ("hash_algorithm_id", "hashlib_name", "digest_hex_length", "usage"),
            "HASH_ALGORITHM",
        )
        length = value["digest_hex_length"]
        if not isinstance(length, int) or length < 32:
            raise SharedIdentityError("HASH_DIGEST_LENGTH_INVALID")
        descriptor = cls(
            _nonempty(value["hash_algorithm_id"], "hash_algorithm_id"),
            _nonempty(value["hashlib_name"], "hashlib_name"),
            length,
            _nonempty(value["usage"], "usage"),
        )
        try:
            observed = hashlib.new(descriptor.hashlib_name).digest_size * 2
        except ValueError as exc:
            raise SharedIdentityError("HASH_ALGORITHM_UNAVAILABLE") from exc
        if observed != descriptor.digest_hex_length:
            raise SharedIdentityError("HASH_DIGEST_LENGTH_MISMATCH")
        return descriptor

    def digest(self, payload: bytes) -> str:
        return hashlib.new(self.hashlib_name, payload).hexdigest()


@dataclass(frozen=True)
class SerializationProfile:
    serialization_profile_id: str
    profile_version: str
    character_encoding: str
    unicode_policy: str
    object_key_order: str
    numeric_policy: str
    negative_zero_policy: str
    collection_policy: str
    null_policy: str
    timestamp_policy: str
    string_policy: str
    identity_projection_ref: str
    self_identity_exclusion_policy: str
    storage_framing_policy: str
    hash_algorithm_ref: str
    conformance_vector_set_ref: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SerializationProfile":
        _strict_fields(value, _PROFILE_FIELDS, "SERIALIZATION_PROFILE")
        profile = cls(*(_nonempty(value[field], field) for field in _PROFILE_FIELDS))
        allowed = {
            "character_encoding": {"UTF-8"},
            "unicode_policy": {"PRESERVE", "REQUIRE_NFC"},
            "object_key_order": {"LEXICOGRAPHIC_CODEPOINT"},
            "numeric_policy": {"JSON_NUMBER", "CANONICAL_DECIMAL_STRING", "PRECISION_PRESERVING_DECIMAL_STRING"},
            "negative_zero_policy": {"REJECT", "NORMALIZE_TO_ZERO", "PRESERVE"},
            "collection_policy": {"ORDERED_SEQUENCE", "SEMANTIC_SET", "OWNER_DECLARED_ORDER"},
            "null_policy": {"EXPLICIT_ALLOW", "REJECT"},
            "timestamp_policy": {"OWNER_TYPED_STRING", "RFC3339_UTC_REQUIRE_Z"},
            "string_policy": {"JSON_STRING"},
            "self_identity_exclusion_policy": {"EXCLUDE_DECLARED_SELF_ID_FIELDS"},
            "storage_framing_policy": {"NONE", "TRAILING_LF"},
        }
        for field, values in allowed.items():
            if getattr(profile, field) not in values:
                raise SharedIdentityError(f"SERIALIZATION_PROFILE_{field.upper()}_INVALID")
        return profile

    def semantic_mapping(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in _PROFILE_FIELDS}


@dataclass(frozen=True)
class IdentityProjection:
    projection_id: str
    owner_namespace: str
    included_fields: tuple[str, ...]
    excluded_fields: tuple[str, ...]
    conditional_fields: tuple[str, ...]
    self_id_fields: tuple[str, ...]
    descriptive_only_fields: tuple[str, ...]
    projection_version: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "IdentityProjection":
        _strict_fields(value, _PROJECTION_FIELDS, "IDENTITY_PROJECTION")
        projection = cls(
            _nonempty(value["projection_id"], "projection_id"),
            _nonempty(value["owner_namespace"], "owner_namespace"),
            _string_tuple(value["included_fields"], "included_fields"),
            _string_tuple(value["excluded_fields"], "excluded_fields"),
            _string_tuple(value["conditional_fields"], "conditional_fields"),
            _string_tuple(value["self_id_fields"], "self_id_fields"),
            _string_tuple(value["descriptive_only_fields"], "descriptive_only_fields"),
            _nonempty(value["projection_version"], "projection_version"),
        )
        groups = {
            "included": set(projection.included_fields),
            "excluded": set(projection.excluded_fields),
            "self": set(projection.self_id_fields),
            "descriptive": set(projection.descriptive_only_fields),
        }
        if groups["included"] & (groups["excluded"] | groups["self"] | groups["descriptive"]):
            raise SharedIdentityError("IDENTITY_PROJECTION_FIELD_ROLE_CONFLICT")
        if set(projection.conditional_fields) & (groups["included"] | groups["excluded"] | groups["self"] | groups["descriptive"]):
            raise SharedIdentityError("IDENTITY_PROJECTION_CONDITIONAL_ROLE_CONFLICT")
        return projection

    def project(self, value: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
            raise NonCanonicalIdentityPayload("IDENTITY_PAYLOAD_OBJECT_REQUIRED")
        declared = (
            set(self.included_fields) | set(self.conditional_fields) | set(self.excluded_fields)
            | set(self.self_id_fields) | set(self.descriptive_only_fields)
        )
        undeclared = sorted(set(value) - declared)
        if undeclared:
            raise NonCanonicalIdentityPayload(f"IDENTITY_FIELD_ROLE_UNDECLARED:{undeclared}")
        missing = [field for field in self.included_fields if field not in value]
        if missing:
            raise NonCanonicalIdentityPayload(f"IDENTITY_REQUIRED_FIELDS_MISSING:{missing}")
        selected = set(self.included_fields)
        selected.update(field for field in self.conditional_fields if field in value)
        denied = set(self.excluded_fields) | set(self.self_id_fields) | set(self.descriptive_only_fields)
        if selected & denied:
            raise NonCanonicalIdentityPayload("IDENTITY_PROJECTION_DENIED_FIELD_SELECTED")
        return {field: value[field] for field in selected}


@dataclass(frozen=True)
class LegacySerializationBinding:
    binding_id: str
    legacy_identifier: str
    owner_namespace: str
    pack_id: str
    generation_id: str
    serialization_profile_id: str
    identity_projection_id: str
    hash_algorithm_id: str
    historical_digest: str
    status: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LegacySerializationBinding":
        _strict_fields(value, _LEGACY_FIELDS, "LEGACY_SERIALIZATION_BINDING")
        binding = cls(*(_nonempty(value[field], field) for field in _LEGACY_FIELDS))
        if binding.status != "HISTORICAL_IMMUTABLE_READ_ONLY":
            raise SharedIdentityError("LEGACY_BINDING_STATUS_INVALID")
        if any(ch not in "0123456789abcdef" for ch in binding.historical_digest):
            raise SharedIdentityError("LEGACY_HISTORICAL_DIGEST_INVALID")
        return binding


class IdentityRegistry:
    """Exact registries with collision detection and context-complete legacy lookup."""

    def __init__(self, *, algorithms: Iterable[HashAlgorithmDescriptor], profiles: Iterable[SerializationProfile], projections: Iterable[IdentityProjection], legacy_bindings: Iterable[LegacySerializationBinding] = ()) -> None:
        self.algorithms = self._unique(algorithms, "hash_algorithm_id", "HASH_ALGORITHM")
        self.profiles = self._profiles(profiles)
        self.projections = self._unique(projections, "projection_id", "IDENTITY_PROJECTION")
        self.legacy_bindings = tuple(legacy_bindings)
        binding_ids: set[str] = set()
        for binding in self.legacy_bindings:
            if binding.binding_id in binding_ids:
                raise AmbiguousIdentityBinding("LEGACY_BINDING_ID_DUPLICATE")
            binding_ids.add(binding.binding_id)
            algorithm = self.algorithm(binding.hash_algorithm_id)
            self.profile(binding.serialization_profile_id)
            self.projection(binding.identity_projection_id)
            if len(binding.historical_digest) != algorithm.digest_hex_length:
                raise SharedIdentityError("LEGACY_HISTORICAL_DIGEST_LENGTH_MISMATCH")
        for profile in self.profiles.values():
            self.algorithm(profile.hash_algorithm_ref)
            self.projection(profile.identity_projection_ref)
            if profile.serialization_profile_id in {profile.hash_algorithm_ref, profile.identity_projection_ref}:
                raise SharedIdentityError("IDENTITY_NAMESPACE_SUBSTITUTION_FORBIDDEN")

    @staticmethod
    def _unique(values: Iterable[Any], attribute: str, label: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for value in values:
            identifier = getattr(value, attribute)
            if identifier in result:
                raise AmbiguousIdentityBinding(f"{label}_DUPLICATE:{identifier}")
            result[identifier] = value
        return result

    @staticmethod
    def _profiles(values: Iterable[SerializationProfile]) -> dict[str, SerializationProfile]:
        result: dict[str, SerializationProfile] = {}
        for value in values:
            current = result.get(value.serialization_profile_id)
            if current is not None:
                if current.semantic_mapping() != value.semantic_mapping():
                    raise ProfileCollisionError(f"SERIALIZATION_PROFILE_COLLISION:{value.serialization_profile_id}")
                raise AmbiguousIdentityBinding(f"SERIALIZATION_PROFILE_DUPLICATE:{value.serialization_profile_id}")
            result[value.serialization_profile_id] = value
        return result

    def algorithm(self, identifier: str) -> HashAlgorithmDescriptor:
        try:
            return self.algorithms[identifier]
        except KeyError as exc:
            raise UnknownIdentityBinding(f"HASH_ALGORITHM_UNKNOWN:{identifier}") from exc

    def profile(self, identifier: str) -> SerializationProfile:
        try:
            return self.profiles[identifier]
        except KeyError as exc:
            raise UnknownIdentityBinding(f"SERIALIZATION_PROFILE_UNKNOWN:{identifier}") from exc

    def projection(self, identifier: str) -> IdentityProjection:
        try:
            return self.projections[identifier]
        except KeyError as exc:
            raise UnknownIdentityBinding(f"IDENTITY_PROJECTION_UNKNOWN:{identifier}") from exc

    def resolve_legacy(self, legacy_identifier: str, *, owner_namespace: str, pack_id: str, generation_id: str) -> LegacySerializationBinding:
        matches = [
            row for row in self.legacy_bindings
            if row.legacy_identifier == legacy_identifier
            and row.owner_namespace == owner_namespace
            and row.pack_id == pack_id
            and row.generation_id == generation_id
        ]
        if not matches:
            raise UnknownIdentityBinding("LEGACY_IDENTITY_BINDING_UNKNOWN")
        if len(matches) != 1:
            raise AmbiguousIdentityBinding("LEGACY_IDENTITY_BINDING_AMBIGUOUS")
        return matches[0]


def _validated_text(value: str, profile: SerializationProfile) -> str:
    if profile.unicode_policy == "REQUIRE_NFC" and unicodedata.normalize("NFC", value) != value:
        raise NonCanonicalIdentityPayload("UNICODE_NOT_NFC")
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _decimal(value: int | float | Decimal) -> Decimal:
    if isinstance(value, bool):
        raise NonCanonicalIdentityPayload("BOOLEAN_IS_NOT_NUMERIC")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise NonCanonicalIdentityPayload("NON_FINITE_NUMBER")
        return Decimal(repr(value))
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise NonCanonicalIdentityPayload("NUMBER_INVALID") from exc
    if not result.is_finite():
        raise NonCanonicalIdentityPayload("NON_FINITE_NUMBER")
    return result


def _number_text(value: int | float | Decimal, profile: SerializationProfile) -> str:
    decimal = _decimal(value)
    negative_zero = decimal.is_zero() and decimal.is_signed()
    if negative_zero and profile.negative_zero_policy == "REJECT":
        raise NonCanonicalIdentityPayload("NEGATIVE_ZERO_REJECTED")
    if negative_zero and profile.negative_zero_policy == "NORMALIZE_TO_ZERO":
        decimal = Decimal(0)
    if decimal.is_zero():
        text = "-0" if decimal.is_signed() else "0"
    else:
        text = format(decimal, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
    if profile.numeric_policy == "JSON_NUMBER":
        return text
    if profile.numeric_policy == "CANONICAL_DECIMAL_STRING":
        return _validated_text(text, profile)
    if profile.numeric_policy == "PRECISION_PRESERVING_DECIMAL_STRING":
        return _validated_text(format(decimal, "f"), profile)
    raise NonCanonicalIdentityPayload("NUMERIC_POLICY_UNSUPPORTED")


def _canonical_text(value: Any, profile: SerializationProfile) -> str:
    if value is None:
        if profile.null_policy == "REJECT":
            raise NonCanonicalIdentityPayload("NULL_REJECTED")
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _validated_text(value, profile)
    if isinstance(value, (int, float, Decimal)):
        return _number_text(value, profile)
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise NonCanonicalIdentityPayload("OBJECT_KEY_NOT_STRING")
        pairs = [(key, _validated_text(key, profile), _canonical_text(item, profile)) for key, item in value.items()]
        pairs.sort(key=lambda row: row[0])
        return "{" + ",".join(f"{key}:{item}" for _, key, item in pairs) + "}"
    if isinstance(value, (list, tuple)):
        items = [_canonical_text(item, profile) for item in value]
        if profile.collection_policy == "SEMANTIC_SET":
            items.sort(key=lambda item: item.encode("utf-8"))
            if len(items) != len(set(items)):
                raise NonCanonicalIdentityPayload("SEMANTIC_SET_DUPLICATE")
        return "[" + ",".join(items) + "]"
    raise NonCanonicalIdentityPayload(f"UNSUPPORTED_IDENTITY_TYPE:{type(value).__name__}")


def canonicalize(value: Any, profile: SerializationProfile) -> bytes:
    """Return logical canonical bytes; physical storage framing is never included."""
    if profile.character_encoding != "UTF-8":
        raise NonCanonicalIdentityPayload("CHARACTER_ENCODING_UNSUPPORTED")
    return _canonical_text(value, profile).encode("utf-8")


def storage_bytes(logical_bytes: bytes, profile: SerializationProfile) -> bytes:
    if profile.storage_framing_policy == "NONE":
        return logical_bytes
    if profile.storage_framing_policy == "TRAILING_LF":
        return logical_bytes + b"\n"
    raise NonCanonicalIdentityPayload("STORAGE_FRAMING_POLICY_UNSUPPORTED")


def logical_identity(value: Mapping[str, Any], *, serialization_profile_id: str, identity_projection_id: str, registry: IdentityRegistry) -> dict[str, Any]:
    profile = registry.profile(serialization_profile_id)
    projection = registry.projection(identity_projection_id)
    if profile.identity_projection_ref != projection.projection_id:
        raise SharedIdentityError("PROFILE_PROJECTION_BINDING_MISMATCH")
    projected = projection.project(value)
    logical_bytes = canonicalize(projected, profile)
    algorithm = registry.algorithm(profile.hash_algorithm_ref)
    identity_material = (
        b"OVC-SHARED-IDENTITY-v1\x00"
        + profile.serialization_profile_id.encode("utf-8")
        + b"\x00"
        + projection.projection_id.encode("utf-8")
        + b"\x00"
        + logical_bytes
    )
    return {
        "serialization_profile_id": profile.serialization_profile_id,
        "identity_projection_id": projection.projection_id,
        "hash_algorithm_id": algorithm.hash_algorithm_id,
        "logical_digest": algorithm.digest(identity_material),
        "canonical_content_digest": algorithm.digest(logical_bytes),
        "logical_bytes": logical_bytes,
        "physical_blob_digest": algorithm.digest(storage_bytes(logical_bytes, profile)),
    }


def load_registry(root: Path) -> IdentityRegistry:
    """Load the four strict WP1 registries from a directory."""
    def read(name: str, schema: str, fields: set[str]) -> Mapping[str, Any]:
        try:
            value = json.loads((root / name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SharedIdentityError(f"IDENTITY_REGISTRY_READ_FAILED:{name}") from exc
        if not isinstance(value, Mapping):
            raise SharedIdentityError(f"IDENTITY_REGISTRY_OBJECT_REQUIRED:{name}")
        if set(value) != fields or value.get("schema") != schema or not isinstance(value.get("entries"), list):
            raise SharedIdentityError(f"IDENTITY_REGISTRY_ENVELOPE_INVALID:{name}")
        return value

    algorithms = read("HASH_ALGORITHM_REGISTRY_v0_1.json", "ovc-shared-systems-hash-algorithm-registry/v0.1", {"schema", "registry_id", "entries", "authority_effect"})
    profiles = read("SERIALIZATION_PROFILE_REGISTRY_v0_1.json", "ovc-shared-systems-serialization-profile-registry/v0.1", {"schema", "registry_id", "entries", "authority_effect"})
    projections = read("IDENTITY_PROJECTION_REGISTRY_v0_1.json", "ovc-shared-systems-identity-projection-registry/v0.1", {"schema", "registry_id", "entries", "authority_effect"})
    legacy = read("LEGACY_SERIALIZATION_BINDING_REGISTRY_v0_1.json", "ovc-shared-systems-legacy-serialization-binding-registry/v0.1", {"schema", "registry_id", "entries", "resolution_rule", "authority_effect"})
    return IdentityRegistry(
        algorithms=(HashAlgorithmDescriptor.from_mapping(row) for row in algorithms["entries"]),
        profiles=(SerializationProfile.from_mapping(row) for row in profiles["entries"]),
        projections=(IdentityProjection.from_mapping(row) for row in projections["entries"]),
        legacy_bindings=(LegacySerializationBinding.from_mapping(row) for row in legacy["entries"]),
    )
