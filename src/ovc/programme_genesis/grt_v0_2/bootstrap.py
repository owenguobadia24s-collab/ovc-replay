from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DIALECT = "https://json-schema.org/draft/2020-12/schema"
PROFILE_ID = "ovc-grt-bootstrap-subset-v1"
VALIDATOR_RELEASE = "ovc-grt-bootstrap-validator/1.0.0"

_ALLOWED_SCHEMA_KEYS = frozenset(
    {
        "$schema",
        "$id",
        "title",
        "description",
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "format",
    }
)
_PRIMITIVE_TYPES = frozenset(
    {"object", "array", "string", "integer", "number", "boolean", "null"}
)
_FORMAT_PATTERNS = {
    "sha256": re.compile(r"^[0-9a-f]{64}$"),
    "git-sha1": re.compile(r"^[0-9a-f]{40}$"),
    "date-time-z": re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
    ),
}


class BootstrapValidationError(ValueError):
    """Finite bootstrap schema or instance validation failure."""


@dataclass(frozen=True)
class ValidationReceipt:
    schema_id: str
    instance_id: str
    result: str
    validator_release: str = VALIDATOR_RELEASE


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _types(schema: Mapping[str, Any]) -> tuple[str, ...]:
    raw = schema.get("type")
    if raw is None:
        return ()
    if isinstance(raw, str):
        values = (raw,)
    elif isinstance(raw, list) and raw and all(isinstance(item, str) for item in raw):
        values = tuple(raw)
    else:
        raise BootstrapValidationError("GRT_BOOTSTRAP_SCHEMA_TYPE_INVALID")
    unknown = sorted(set(values) - _PRIMITIVE_TYPES)
    if unknown:
        raise BootstrapValidationError(
            "GRT_BOOTSTRAP_SCHEMA_TYPE_UNKNOWN:" + ",".join(unknown)
        )
    if len(set(values)) != len(values):
        raise BootstrapValidationError("GRT_BOOTSTRAP_SCHEMA_TYPE_DUPLICATE")
    return values


def validate_schema(schema: Any, *, require_dialect: bool = True) -> None:
    seen: set[int] = set()

    def walk(node: Any, path: str) -> None:
        if not isinstance(node, dict):
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_SCHEMA_NODE_NOT_OBJECT:{path}"
            )
        identity = id(node)
        if identity in seen:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_SCHEMA_SELF_REFERENCE:{path}"
            )
        seen.add(identity)
        try:
            unknown = sorted(set(node) - _ALLOWED_SCHEMA_KEYS)
            if unknown:
                raise BootstrapValidationError(
                    f"GRT_BOOTSTRAP_SCHEMA_UNKNOWN_KEYWORD:{path}:{unknown[0]}"
                )
            _types(node)
            if "properties" in node:
                properties = node["properties"]
                if not isinstance(properties, dict):
                    raise BootstrapValidationError(
                        f"GRT_BOOTSTRAP_SCHEMA_PROPERTIES_INVALID:{path}"
                    )
                for name, child in properties.items():
                    if not isinstance(name, str) or not name:
                        raise BootstrapValidationError(
                            f"GRT_BOOTSTRAP_SCHEMA_PROPERTY_NAME_INVALID:{path}"
                        )
                    walk(child, f"{path}.properties.{name}")
            required = node.get("required", [])
            if not isinstance(required, list) or not all(
                isinstance(item, str) and item for item in required
            ):
                raise BootstrapValidationError(
                    f"GRT_BOOTSTRAP_SCHEMA_REQUIRED_INVALID:{path}"
                )
            if len(set(required)) != len(required):
                raise BootstrapValidationError(
                    f"GRT_BOOTSTRAP_SCHEMA_REQUIRED_DUPLICATE:{path}"
                )
            if required:
                properties = node.get("properties", {})
                missing = sorted(set(required) - set(properties))
                if missing:
                    raise BootstrapValidationError(
                        f"GRT_BOOTSTRAP_SCHEMA_REQUIRED_UNDECLARED:{path}:{missing[0]}"
                    )
            if "additionalProperties" in node and not isinstance(
                node["additionalProperties"], bool
            ):
                raise BootstrapValidationError(
                    f"GRT_BOOTSTRAP_SCHEMA_ADDITIONAL_PROPERTIES_INVALID:{path}"
                )
            if "items" in node:
                walk(node["items"], f"{path}.items")
            if "pattern" in node:
                try:
                    re.compile(node["pattern"])
                except (TypeError, re.error) as exc:
                    raise BootstrapValidationError(
                        f"GRT_BOOTSTRAP_SCHEMA_PATTERN_INVALID:{path}"
                    ) from exc
            if "enum" in node:
                enum = node["enum"]
                if not isinstance(enum, list) or not enum:
                    raise BootstrapValidationError(
                        f"GRT_BOOTSTRAP_SCHEMA_ENUM_INVALID:{path}"
                    )
                fingerprints = [json.dumps(item, sort_keys=True) for item in enum]
                if len(set(fingerprints)) != len(fingerprints):
                    raise BootstrapValidationError(
                        f"GRT_BOOTSTRAP_SCHEMA_ENUM_DUPLICATE:{path}"
                    )
            for key in (
                "minLength",
                "maxLength",
                "minItems",
                "maxItems",
                "minProperties",
                "maxProperties",
            ):
                if key in node and (
                    not isinstance(node[key], int)
                    or isinstance(node[key], bool)
                    or node[key] < 0
                ):
                    raise BootstrapValidationError(
                        f"GRT_BOOTSTRAP_SCHEMA_BOUND_INVALID:{path}:{key}"
                    )
            if "uniqueItems" in node and not isinstance(node["uniqueItems"], bool):
                raise BootstrapValidationError(
                    f"GRT_BOOTSTRAP_SCHEMA_UNIQUE_ITEMS_INVALID:{path}"
                )
            if "format" in node and node["format"] not in _FORMAT_PATTERNS:
                raise BootstrapValidationError(
                    f"GRT_BOOTSTRAP_SCHEMA_FORMAT_UNKNOWN:{path}:{node['format']}"
                )
        finally:
            seen.remove(identity)

    if not isinstance(schema, dict):
        raise BootstrapValidationError("GRT_BOOTSTRAP_SCHEMA_ROOT_NOT_OBJECT")
    if require_dialect and schema.get("$schema") != DIALECT:
        raise BootstrapValidationError("GRT_BOOTSTRAP_SCHEMA_DIALECT_UNSUPPORTED")
    walk(schema, "$")


def _matches_type(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return False


def validate_instance(instance: Any, schema: Mapping[str, Any], *, path: str = "$") -> None:
    validate_schema(schema)
    _validate_instance(instance, schema, path)


def _validate_instance(instance: Any, schema: Mapping[str, Any], path: str) -> None:
    expected = _types(schema)
    if expected and not any(_matches_type(instance, item) for item in expected):
        raise BootstrapValidationError(
            f"GRT_BOOTSTRAP_INSTANCE_TYPE:{path}:{'|'.join(expected)}"
        )
    if "const" in schema and instance != schema["const"]:
        raise BootstrapValidationError(f"GRT_BOOTSTRAP_INSTANCE_CONST:{path}")
    if "enum" in schema and instance not in schema["enum"]:
        raise BootstrapValidationError(f"GRT_BOOTSTRAP_INSTANCE_ENUM:{path}")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for name in required:
            if name not in instance:
                raise BootstrapValidationError(
                    f"GRT_BOOTSTRAP_INSTANCE_REQUIRED:{path}.{name}"
                )
        properties = schema.get("properties", {})
        unknown = sorted(set(instance) - set(properties))
        if unknown and schema.get("additionalProperties", True) is False:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_ADDITIONAL:{path}.{unknown[0]}"
            )
        for name, child_schema in properties.items():
            if name in instance:
                _validate_instance(instance[name], child_schema, f"{path}.{name}")
        if len(instance) < schema.get("minProperties", 0):
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_MIN_PROPERTIES:{path}"
            )
        maximum = schema.get("maxProperties")
        if maximum is not None and len(instance) > maximum:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_MAX_PROPERTIES:{path}"
            )

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise BootstrapValidationError(f"GRT_BOOTSTRAP_INSTANCE_MIN_ITEMS:{path}")
        maximum = schema.get("maxItems")
        if maximum is not None and len(instance) > maximum:
            raise BootstrapValidationError(f"GRT_BOOTSTRAP_INSTANCE_MAX_ITEMS:{path}")
        if schema.get("uniqueItems", False):
            fingerprints = [
                json.dumps(item, sort_keys=True, separators=(",", ":"))
                for item in instance
            ]
            if len(set(fingerprints)) != len(fingerprints):
                raise BootstrapValidationError(
                    f"GRT_BOOTSTRAP_INSTANCE_DUPLICATE_ITEM:{path}"
                )
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(instance):
                _validate_instance(item, item_schema, f"{path}[{index}]")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_MIN_LENGTH:{path}"
            )
        maximum = schema.get("maxLength")
        if maximum is not None and len(instance) > maximum:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_MAX_LENGTH:{path}"
            )
        pattern = schema.get("pattern")
        if pattern is not None and re.fullmatch(pattern, instance) is None:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_PATTERN:{path}"
            )
        format_name = schema.get("format")
        if format_name is not None and _FORMAT_PATTERNS[format_name].fullmatch(
            instance
        ) is None:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_FORMAT:{path}:{format_name}"
            )

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and instance < minimum:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_MINIMUM:{path}"
            )
        if maximum is not None and instance > maximum:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_INSTANCE_MAXIMUM:{path}"
            )


def validate_manifest_dag(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    nodes = manifest.get("schemas")
    if not isinstance(nodes, list) or not nodes:
        raise BootstrapValidationError("GRT_BOOTSTRAP_MANIFEST_SCHEMAS_INVALID")
    graph: dict[str, tuple[str, ...]] = {}
    for item in nodes:
        if not isinstance(item, dict):
            raise BootstrapValidationError("GRT_BOOTSTRAP_MANIFEST_NODE_INVALID")
        schema_id = item.get("schema_id")
        dependencies = item.get("dependencies", [])
        if (
            not isinstance(schema_id, str)
            or not schema_id
            or not isinstance(dependencies, list)
            or not all(isinstance(dep, str) and dep for dep in dependencies)
        ):
            raise BootstrapValidationError("GRT_BOOTSTRAP_MANIFEST_NODE_INVALID")
        if schema_id in graph:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_MANIFEST_DUPLICATE:{schema_id}"
            )
        graph[schema_id] = tuple(dependencies)
    unknown = sorted(
        {dependency for dependencies in graph.values() for dependency in dependencies}
        - set(graph)
    )
    if unknown:
        raise BootstrapValidationError(
            f"GRT_BOOTSTRAP_MANIFEST_UNKNOWN_DEPENDENCY:{unknown[0]}"
        )

    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(node: str) -> None:
        if node in visiting:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_MANIFEST_CYCLE:{node}"
            )
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)
        order.append(node)

    for node in sorted(graph):
        visit(node)
    return tuple(order)


def validate_registry_unique(
    registry: Mapping[str, Any],
    *,
    collection_field: str,
    identity_field: str,
) -> None:
    entries = registry.get(collection_field)
    if not isinstance(entries, list):
        raise BootstrapValidationError(
            f"GRT_BOOTSTRAP_REGISTRY_COLLECTION_INVALID:{collection_field}"
        )
    identities: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_REGISTRY_ENTRY_INVALID:{collection_field}"
            )
        identity = entry.get(identity_field)
        if not isinstance(identity, str) or not identity:
            raise BootstrapValidationError(
                f"GRT_BOOTSTRAP_REGISTRY_ID_INVALID:{identity_field}"
            )
        identities.append(identity)
    if len(set(identities)) != len(identities):
        raise BootstrapValidationError(
            f"GRT_BOOTSTRAP_REGISTRY_DUPLICATE_ID:{identity_field}"
        )
