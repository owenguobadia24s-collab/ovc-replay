from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any, Iterable, Mapping


_ALLOWED_RELEASES: dict[str, dict[str, Any]] = {
    "DISCOVERY": {
        "release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "manifest_sha256": "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        "record_count": 159_892,
        "record_file_count": 144,
    },
    "DEVELOPMENT": {
        "release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1",
        "manifest_sha256": "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        "record_count": 52_872,
        "record_file_count": 48,
    },
}
_ALLOWED_CLOCKS = {"15M", "2H_A_L"}
_ALLOWED_SIDES = {"BID", "ASK"}
_FORMULA_REQUIRED = {
    "primitive_id",
    "field_name",
    "definition",
    "formula",
    "required_inputs",
    "unit",
    "domain",
    "null_rule",
    "lookback_bars",
    "first_valid_rule",
    "symmetry_rule",
    "authority",
}
_VALIDATION_FORBIDDEN = {
    "path",
    "paths",
    "local_path",
    "remote_key",
    "record_path",
    "record_paths",
    "objects",
    "records",
    "rows",
    "timestamps",
    "source_object_id",
    "source_bar_id",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AccessDenied(ValueError):
    """Raised before forbidden role content or source location is resolved."""


class IndexContractError(ValueError):
    """Raised when an index input violates the frozen RO3 contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        return [] if not body else [_parse_scalar(item) for item in body.split(",")]
    if value.startswith("{") and value.endswith("}"):
        body = value[1:-1].strip()
        result: dict[str, Any] = {}
        if body:
            for item in body.split(","):
                if ":" not in item:
                    raise IndexContractError(f"invalid inline mapping item: {item}")
                key, raw = item.split(":", 1)
                result[_unquote(key)] = _parse_scalar(raw)
        return result
    if re.fullmatch(r"-?[0-9]+", value):
        return int(value)
    return _unquote(value)


def parse_formula_registry(registry_text: str) -> dict[str, Any]:
    """Parse the frozen, deliberately simple C1 formula registry without a YAML dependency."""

    header: dict[str, Any] = {}
    formulas: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_formulas = False

    for raw_line in registry_text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        stripped = raw_line.strip()
        if stripped == "formulas:":
            in_formulas = True
            continue
        if stripped.startswith("versioning:"):
            if current is not None:
                formulas.append(current)
                current = None
            break
        if in_formulas and stripped.startswith("- primitive_id:"):
            if current is not None:
                formulas.append(current)
            current = {"primitive_id": _parse_scalar(stripped.split(":", 1)[1])}
            continue
        if in_formulas and current is not None:
            if ":" not in stripped:
                raise IndexContractError(f"invalid formula registry line: {raw_line}")
            key, value = stripped.split(":", 1)
            current[key] = _parse_scalar(value)
            continue
        if not in_formulas and ":" in stripped:
            key, value = stripped.split(":", 1)
            if key in {
                "schema",
                "registry_id",
                "status",
                "layer_id",
                "contract_id",
                "record_schema_id",
                "arithmetic",
                "canonical_serialization",
                "clock_neutral",
                "side_separate",
                "formula_count",
            }:
                header[key] = _parse_scalar(value)

    if current is not None:
        formulas.append(current)

    if header.get("registry_id") != "C1.FORMULAS.v0.1":
        raise IndexContractError("unknown formula registry identity")
    if header.get("status") != "FROZEN_AFTER_WP2":
        raise IndexContractError("formula registry is not frozen")
    if header.get("arithmetic") != "DECIMAL_EXACT":
        raise IndexContractError("formula registry arithmetic must be DECIMAL_EXACT")
    if header.get("formula_count") != 18 or len(formulas) != 18:
        raise IndexContractError("formula registry must contain exactly 18 formulas")

    seen: set[str] = set()
    for formula in formulas:
        missing = sorted(_FORMULA_REQUIRED - formula.keys())
        if missing:
            raise IndexContractError(f"formula {formula.get('primitive_id')} missing {missing}")
        primitive_id = str(formula["primitive_id"])
        if primitive_id in seen:
            raise IndexContractError(f"duplicate primitive_id: {primitive_id}")
        if not re.fullmatch(r"C1-[A-Z0-9-]+\.v0\.1", primitive_id):
            raise IndexContractError(f"invalid primitive_id: {primitive_id}")
        if formula["authority"] != "DERIVED_ATOMIC_FACT":
            raise IndexContractError(f"unknown primitive authority: {primitive_id}")
        seen.add(primitive_id)

    formulas.sort(key=lambda item: item["primitive_id"])
    registry_logical = {**header, "formulas": formulas}
    return {**registry_logical, "registry_logical_sha256": _digest(registry_logical)}


def validation_metadata_only(metadata: Mapping[str, Any]) -> dict[str, Any]:
    if metadata.get("role") != "VALIDATION":
        raise IndexContractError("Validation metadata role must be explicit")
    forbidden = sorted(_VALIDATION_FORBIDDEN.intersection(metadata))
    if forbidden:
        raise AccessDenied(f"VALIDATION_DENY_BEFORE_RESOLUTION: {forbidden}")
    required = {"release_id", "manifest_sha256"}
    missing = sorted(required - metadata.keys())
    if missing:
        raise IndexContractError(f"Validation metadata missing fields: {missing}")
    manifest = str(metadata["manifest_sha256"])
    if not _SHA256_RE.fullmatch(manifest):
        raise IndexContractError("Validation manifest hash is invalid")
    return {
        "role": "VALIDATION",
        "release_id": str(metadata["release_id"]),
        "manifest_sha256": manifest,
        "coverage_start": metadata.get("coverage_start"),
        "coverage_end": metadata.get("coverage_end"),
        "aggregate_record_count": int(metadata.get("aggregate_record_count", 0)),
        "build_state": "NOT_BUILT",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "availability": "METADATA_ONLY",
    }


def _validate_release(release: Mapping[str, Any]) -> dict[str, Any]:
    role = str(release.get("role", ""))
    if role == "VALIDATION":
        raise AccessDenied("VALIDATION_DENY_BEFORE_RELEASE_CONTENT_RESOLUTION")
    if role not in _ALLOWED_RELEASES:
        raise AccessDenied(f"content resolution denied for role {role or 'UNKNOWN'}")

    required = {
        "release_id",
        "manifest_sha256",
        "instrument",
        "coverage_start",
        "coverage_end",
        "record_count",
        "record_file_count",
        "schema_version",
        "formula_registry_id",
        "formula_registry_sha256",
        "clocks",
        "sides",
        "selector_state",
        "availability",
    }
    missing = sorted(required - release.keys())
    if missing:
        raise IndexContractError(f"{role} release missing fields: {missing}")

    expected = _ALLOWED_RELEASES[role]
    if release["release_id"] != expected["release_id"]:
        raise IndexContractError(f"unexpected {role} release_id")
    if release["manifest_sha256"] != expected["manifest_sha256"]:
        raise IndexContractError(f"unexpected {role} manifest_sha256")
    if int(release["record_count"]) != expected["record_count"]:
        raise IndexContractError(f"unexpected {role} record_count")
    if int(release["record_file_count"]) != expected["record_file_count"]:
        raise IndexContractError(f"unexpected {role} record_file_count")
    if release["instrument"] != "GBPUSD":
        raise IndexContractError("instrument must remain GBPUSD")
    if release["formula_registry_id"] != "C1.FORMULAS.v0.1":
        raise IndexContractError("unknown formula registry")
    if not _SHA256_RE.fullmatch(str(release["formula_registry_sha256"])):
        raise IndexContractError("invalid formula registry SHA-256")
    clocks = sorted(set(release["clocks"]))
    sides = sorted(set(release["sides"]))
    if set(clocks) != _ALLOWED_CLOCKS:
        raise IndexContractError(f"unknown or incomplete clocks: {clocks}")
    if set(sides) != _ALLOWED_SIDES:
        raise IndexContractError(f"unknown or incomplete sides: {sides}")
    if release["selector_state"] != "SHADOW":
        raise IndexContractError("RO3 source release must remain SHADOW")
    if release["availability"] != "REMOTE_VERIFIED":
        raise IndexContractError("RO3 source release must be REMOTE_VERIFIED")

    return {
        "role": role,
        "release_id": release["release_id"],
        "manifest_sha256": release["manifest_sha256"],
        "instrument": release["instrument"],
        "coverage_start": release["coverage_start"],
        "coverage_end": release["coverage_end"],
        "record_count": int(release["record_count"]),
        "record_file_count": int(release["record_file_count"]),
        "schema_version": str(release["schema_version"]),
        "formula_registry_id": release["formula_registry_id"],
        "formula_registry_sha256": release["formula_registry_sha256"],
        "clocks": clocks,
        "sides": sides,
        "selector_state": "SHADOW",
        "lifecycle_state": str(release.get("lifecycle_state", "REMOTE_VERIFIED")),
        "availability": "REMOTE_VERIFIED",
        "eligible_source_bar_count": int(release.get("eligible_source_bar_count", release["record_count"])),
        "source_rejections": dict(sorted((release.get("source_rejections") or {}).items())),
    }


def _release_index_id(release: Mapping[str, Any]) -> str:
    return f"RO3-C1-REL-{_digest({'role': release['role'], 'release_id': release['release_id'], 'manifest_sha256': release['manifest_sha256']})[:20]}"


def _primitive_index_id(primitive: Mapping[str, Any], registry_hash: str) -> str:
    return f"RO3-C1-PRIM-{_digest({'primitive_id': primitive['primitive_id'], 'registry_hash': registry_hash, 'definition': primitive})[:20]}"


def _family_id(key: tuple[str, str, str, str, str, str]) -> str:
    return f"RO3-C1-FAM-{_digest(key)[:20]}"


def build_c1_indexes(
    *,
    releases: Iterable[Mapping[str, Any]],
    formula_registry_text: str,
    record_headers: Iterable[Mapping[str, Any]] | None = None,
    validation_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build source-bound, order-independent C1 index projections."""

    parsed_registry = parse_formula_registry(formula_registry_text)
    normalized_releases = [_validate_release(release) for release in releases]
    normalized_releases.sort(key=lambda item: item["role"])
    roles = [release["role"] for release in normalized_releases]
    if roles != ["DEVELOPMENT", "DISCOVERY"]:
        raise IndexContractError("exact Discovery and Development releases are both required once")

    release_by_id = {release["release_id"]: release for release in normalized_releases}
    release_index = [
        {
            "release_index_id": _release_index_id(release),
            **release,
            "writes": "NONE",
        }
        for release in normalized_releases
    ]

    registry_hash = parsed_registry["registry_logical_sha256"]
    primitive_index = [
        {
            "primitive_index_id": _primitive_index_id(primitive, registry_hash),
            "formula_registry_id": "C1.FORMULAS.v0.1",
            "formula_registry_logical_sha256": registry_hash,
            **primitive,
            "writes": "NONE",
        }
        for primitive in parsed_registry["formulas"]
    ]

    family_counts: Counter[tuple[str, str, str, str, str, str]] = Counter()
    null_field_counts: Counter[str] = Counter()
    population_digests: list[str] = []
    seen_record_ids: set[str] = set()

    if record_headers is None:
        for release in normalized_releases:
            declared = release.get("family_counts")
            if declared is not None:
                raise IndexContractError("family_counts must be supplied on original release input, not normalized release")
        raise IndexContractError("record_headers are required for source-bound family and coverage indexes")

    for raw in record_headers:
        required = {
            "record_id",
            "role",
            "release_id",
            "manifest_sha256",
            "clock",
            "side",
            "schema_version",
            "formula_registry_id",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise IndexContractError(f"record header missing fields: {missing}")
        role = str(raw["role"])
        if role == "VALIDATION":
            raise AccessDenied("VALIDATION_DENY_BEFORE_RECORD_RESOLUTION")
        release_id = str(raw["release_id"])
        if release_id not in release_by_id:
            raise IndexContractError(f"record references unknown release: {release_id}")
        release = release_by_id[release_id]
        if role != release["role"] or raw["manifest_sha256"] != release["manifest_sha256"]:
            raise IndexContractError("record role/release/manifest identity mismatch")
        clock = str(raw["clock"])
        side = str(raw["side"])
        if clock not in _ALLOWED_CLOCKS or side not in _ALLOWED_SIDES:
            raise IndexContractError("record uses unknown clock or side")
        if raw["formula_registry_id"] != "C1.FORMULAS.v0.1":
            raise IndexContractError("record uses unknown formula registry")
        record_id = str(raw["record_id"])
        if record_id in seen_record_ids:
            raise IndexContractError(f"duplicate record_id: {record_id}")
        seen_record_ids.add(record_id)

        null_reasons = raw.get("null_reasons") or {}
        if not isinstance(null_reasons, Mapping):
            raise IndexContractError("null_reasons must be an object")
        for field, reason in null_reasons.items():
            if not field or not reason:
                raise IndexContractError("null reason field and reason must be non-empty")
            null_field_counts[str(field)] += 1

        key = (
            role,
            release_id,
            clock,
            side,
            str(raw["schema_version"]),
            str(raw["formula_registry_id"]),
        )
        family_counts[key] += 1
        logical_header = {
            "record_id": record_id,
            "role": role,
            "release_id": release_id,
            "manifest_sha256": raw["manifest_sha256"],
            "clock": clock,
            "side": side,
            "schema_version": str(raw["schema_version"]),
            "formula_registry_id": str(raw["formula_registry_id"]),
            "null_reasons": dict(sorted((str(k), str(v)) for k, v in null_reasons.items())),
            "source_hash": raw.get("source_hash"),
        }
        population_digests.append(_digest(logical_header))

    expected_total = sum(release["record_count"] for release in normalized_releases)
    if len(seen_record_ids) != expected_total:
        raise IndexContractError(f"record corpus count mismatch: {len(seen_record_ids)} != {expected_total}")

    for release in normalized_releases:
        actual = sum(count for key, count in family_counts.items() if key[1] == release["release_id"])
        if actual != release["record_count"]:
            raise IndexContractError(f"{release['role']} family count mismatch: {actual} != {release['record_count']}")

    family_index = [
        {
            "family_id": _family_id(key),
            "role": key[0],
            "release_id": key[1],
            "clock": key[2],
            "side": key[3],
            "schema_version": key[4],
            "formula_registry_id": key[5],
            "record_count": count,
            "writes": "NONE",
        }
        for key, count in sorted(family_counts.items())
    ]

    role_coverage = {
        release["role"]: {
            "release_id": release["release_id"],
            "manifest_sha256": release["manifest_sha256"],
            "eligible_source_bar_count": release["eligible_source_bar_count"],
            "c1_record_count": release["record_count"],
            "record_file_count": release["record_file_count"],
            "source_rejections": release["source_rejections"],
            "coverage_status": "RECONCILED"
            if release["eligible_source_bar_count"] == release["record_count"]
            else "RECONCILIATION_REQUIRED",
        }
        for release in normalized_releases
    }
    coverage_profile = {
        "profile_id": "",
        "roles": role_coverage,
        "total_eligible_source_bar_count": sum(item["eligible_source_bar_count"] for item in normalized_releases),
        "total_c1_record_count": expected_total,
        "total_record_file_count": sum(item["record_file_count"] for item in normalized_releases),
        "null_bearing_field_counts": dict(sorted(null_field_counts.items())),
        "record_population_sha256": _digest(sorted(population_digests)),
        "writes": "NONE",
    }
    coverage_profile["profile_id"] = f"RO3-C1-COV-{_digest(coverage_profile)[:20]}"

    validation = validation_metadata_only(validation_metadata) if validation_metadata is not None else None
    logical = {
        "schema": "ovc-ro3-c1-index-bundle/v1",
        "release_index": release_index,
        "primitive_index": primitive_index,
        "family_index": family_index,
        "coverage_profile": coverage_profile,
        "validation": validation,
        "read_only": True,
        "writes": "NONE",
    }
    return {**logical, "logical_index_sha256": _digest(logical)}


def build_incremental_index_receipt(
    *,
    prior_logical_index_sha256: str,
    added_source_identities: Iterable[str],
    final_index: Mapping[str, Any],
) -> dict[str, Any]:
    if not _SHA256_RE.fullmatch(prior_logical_index_sha256):
        raise IndexContractError("invalid prior logical index hash")
    final_hash = str(final_index.get("logical_index_sha256", ""))
    if not _SHA256_RE.fullmatch(final_hash):
        raise IndexContractError("final index lacks a valid logical hash")
    added = sorted(set(str(item) for item in added_source_identities))
    if not added:
        raise IndexContractError("incremental receipt requires at least one exact added source identity")
    logical = {
        "schema": "ovc-ro3-c1-incremental-index-receipt/v1",
        "prior_logical_index_sha256": prior_logical_index_sha256,
        "added_source_identities": added,
        "final_logical_index_sha256": final_hash,
        "equivalence_requirement": "FINAL_HASH_MUST_EQUAL_FULL_REBUILD",
        "writes": "NONE",
    }
    return {**logical, "receipt_id": f"RO3-C1-INCR-{_digest(logical)[:20]}"}
