from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Iterable, Mapping

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .generation import PARTITIONS, GenerationBundle
from .query import AtlasQueryError, AtlasQueryIndex, execute_optimized_query


class AtlasQueryRequest(BaseModel):
    family: str
    term: str | None = None
    start_id: str | None = None
    entity_id: str | None = None
    object_id: str | None = None
    changed_entity_ids: list[str] | None = None
    max_depth: int | None = None
    direction: str | None = None
    predicates: list[str] | None = None
    relationship_families: list[str] | None = None


class AtlasViewRequest(BaseModel):
    entity_ids: list[str] | None = None
    maximum_entities: int = 200


PermissionResolver = Callable[[Request], Iterable[str]]


def build_openapi_document() -> dict[str, Any]:
    """Return the version-independent public API contract.

    FastAPI's generated component details vary across Pydantic releases. The Atlas
    contract is frozen independently so runtime dependency upgrades cannot change
    the committed OpenAPI bytes.
    """
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    nullable_strings = {"anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]}
    envelope = {"$ref": "#/components/schemas/AtlasEnvelope"}
    query_properties = {
        "family": {"type": "string"},
        "term": deepcopy(nullable_string),
        "start_id": deepcopy(nullable_string),
        "entity_id": deepcopy(nullable_string),
        "object_id": deepcopy(nullable_string),
        "changed_entity_ids": deepcopy(nullable_strings),
        "max_depth": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "direction": deepcopy(nullable_string),
        "predicates": deepcopy(nullable_strings),
        "relationship_families": deepcopy(nullable_strings),
    }

    def operation(operation_id: str, *, request_schema: str | None = None) -> dict[str, Any]:
        value: dict[str, Any] = {
            "operationId": operation_id,
            "responses": {
                "200": {"description": "Successful Response", "content": {"application/json": {"schema": envelope}}},
                "422": {"description": "Query Rejected", "content": {"application/json": {"schema": envelope}}},
            },
        }
        if request_schema is not None:
            value["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{request_schema}"}}},
            }
        return value

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "OVC System Atlas Read-Only API",
            "version": "0.1.0",
            "description": "Generation-bound read-only Atlas API. POST routes are query semantics with write_effect=NONE.",
        },
        "paths": {
            "/api/v1/atlas/meta": {"get": operation("atlasMeta")},
            "/api/v1/atlas/query": {"post": operation("atlasQuery", request_schema="AtlasQueryRequest")},
            "/api/v1/atlas/view": {"post": operation("atlasView", request_schema="AtlasViewRequest")},
        },
        "components": {
            "schemas": {
                "AtlasEnvelope": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["schema", "graph_generation", "repository_tree", "query_policy_version", "completeness_profile", "security_visibility", "warnings", "write_effect", "data"],
                    "properties": {
                        "schema": {"const": "ovc-atlas-api-envelope/v1"},
                        "graph_generation": {"type": "string"},
                        "repository_tree": {"type": "string"},
                        "query_policy_version": {"type": "string"},
                        "completeness_profile": {"type": "string"},
                        "security_visibility": {"type": "array", "items": {"type": "string"}},
                        "warnings": {"type": "array", "items": {"type": "string"}},
                        "write_effect": {"const": "NONE"},
                        "data": {},
                    },
                },
                "AtlasQueryRequest": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["family"],
                    "properties": query_properties,
                },
                "AtlasViewRequest": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "entity_ids": deepcopy(nullable_strings),
                        "maximum_entities": {"type": "integer", "default": 200, "minimum": 1, "maximum": 500},
                    },
                },
            }
        },
    }


def _model_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)


def _receipt_admission(receipts: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    admitted = {}
    for family, receipt in receipts.items():
        if (
            receipt.get("family") == family
            and receipt.get("result") == "PASS"
            and receipt.get("optimized_conformance") == "ADMITTED"
        ):
            admitted[family] = str(receipt.get("receipt_hash", ""))
    return admitted


def _envelope(bundle: GenerationBundle, partitions: Iterable[str], data: Any, *, warnings: Iterable[str] = ()) -> dict[str, Any]:
    allowed = sorted(set(partitions), key=PARTITIONS.index)
    manifest = bundle.root_manifest
    return {
        "schema": "ovc-atlas-api-envelope/v1",
        "graph_generation": bundle.root_hash,
        "repository_tree": manifest["repository_tree"],
        "query_policy_version": "0.1",
        "completeness_profile": manifest["completeness_profile"],
        "security_visibility": allowed,
        "warnings": sorted(set(warnings)),
        "write_effect": "NONE",
        "data": data,
    }


def build_view_projection(
    index: AtlasQueryIndex,
    *,
    allowed_partitions: Iterable[str],
    entity_ids: Iterable[str] | None = None,
    maximum_entities: int = 200,
) -> dict[str, Any]:
    if not isinstance(maximum_entities, int) or not 1 <= maximum_entities <= 500:
        raise AtlasQueryError("ATLAS_VIEW_ENTITY_LIMIT_INVALID")
    view = index.view(allowed_partitions)
    visible = view.entities
    selected_ids = sorted(set(entity_ids or visible))
    if not set(selected_ids) <= set(visible):
        raise AtlasQueryError("ATLAS_VIEW_ENTITY_NOT_VISIBLE")
    if len(selected_ids) > maximum_entities:
        return {
            "status": "INCOMPLETE_CAPACITY",
            "required_entity_count": len(selected_ids),
            "nodes": [],
            "edges": [],
            "groups": [],
        }
    selected = set(selected_ids)
    nodes = [
        {
            "entity_id": entity_id,
            "entity_type": visible[entity_id]["entity_type"],
            "label": visible[entity_id]["label"],
            "state_planes": deepcopy(visible[entity_id]["state_planes"]),
        }
        for entity_id in selected_ids
    ]
    edges = [
        {
            "relationship_id": edge["relationship_id"],
            "subject_id": edge["subject_id"],
            "object_id": edge["object_id"],
            "predicate": edge["predicate"],
            "family": edge["family"],
            "resolution_status": edge["resolution_status"],
        }
        for edge in view.relationships
        if edge["subject_id"] in selected and edge["object_id"] in selected
    ]
    edges.sort(key=lambda row: row["relationship_id"])
    grouped: dict[str, list[str]] = {}
    for node in nodes:
        grouped.setdefault(node["entity_type"], []).append(node["entity_id"])
    groups = [
        {"entity_type": entity_type, "entity_ids": sorted(ids), "count": len(ids)}
        for entity_type, ids in sorted(grouped.items())
    ]
    return {"status": "PASS", "nodes": nodes, "edges": edges, "groups": groups}


def create_atlas_app(
    *,
    bundle: GenerationBundle,
    admitted_receipts: Mapping[str, Mapping[str, Any]],
    comparison_bundle: GenerationBundle | None = None,
    permission_resolver: PermissionResolver | None = None,
) -> FastAPI:
    index = AtlasQueryIndex(bundle)
    comparison_index = None if comparison_bundle is None else AtlasQueryIndex(comparison_bundle)
    admissions = _receipt_admission(admitted_receipts)
    resolve_permissions = permission_resolver or (lambda _request: ("ATLAS_PUBLIC_METADATA",))
    app = FastAPI(
        title="OVC System Atlas Read-Only API",
        version="0.1.0",
        description="Generation-bound read-only Atlas API. POST routes are query semantics with write_effect=NONE.",
    )
    app.state.write_effect = "NONE"
    app.state.operational_status = "QUALIFIED_SHADOW_NOT_ACTIVATED"

    def partitions(request: Request) -> tuple[str, ...]:
        values = tuple(resolve_permissions(request))
        if not values or any(value not in PARTITIONS for value in values):
            raise AtlasQueryError("ATLAS_API_CALLER_PERMISSION_INVALID")
        return values

    @app.middleware("http")
    async def read_only_transport(request: Request, call_next):
        method = request.method.upper()
        query_posts = {"/api/v1/atlas/query", "/api/v1/atlas/view"}
        if method in {"PUT", "PATCH", "DELETE"} or method == "POST" and request.url.path not in query_posts:
            try:
                allowed = partitions(request)
            except AtlasQueryError:
                allowed = ("ATLAS_PUBLIC_METADATA",)
            return JSONResponse(
                status_code=405,
                content=_envelope(
                    bundle,
                    allowed,
                    {"reason_code": "ATLAS_MUTATION_METHOD_DENIED"},
                    warnings=("READ_ONLY_API",),
                ),
            )
        return await call_next(request)

    @app.exception_handler(AtlasQueryError)
    async def query_error(request: Request, exc: AtlasQueryError):
        try:
            allowed = partitions(request)
        except AtlasQueryError:
            allowed = ("ATLAS_PUBLIC_METADATA",)
        return JSONResponse(
            status_code=422,
            content=_envelope(bundle, allowed, {"reason_code": str(exc)}, warnings=("QUERY_REJECTED",)),
        )

    @app.get("/api/v1/atlas/meta", operation_id="atlasMeta")
    async def atlas_meta(request: Request):
        allowed = partitions(request)
        return _envelope(
            bundle,
            allowed,
            {
                "programme_id": bundle.root_manifest["programme_id"],
                "admitted_query_families": sorted(admissions),
                "receipt_hashes": dict(sorted(admissions.items())),
                "operational_status": app.state.operational_status,
            },
            warnings=("NOT_ACTIVATED",),
        )

    @app.post("/api/v1/atlas/query", operation_id="atlasQuery")
    async def atlas_query(payload: AtlasQueryRequest, request: Request):
        query = _model_dict(payload)
        family = query["family"]
        if family not in admissions:
            raise AtlasQueryError(f"ATLAS_QUERY_FAMILY_RECEIPT_REQUIRED:{family}")
        allowed = partitions(request)
        result = execute_optimized_query(
            index,
            query,
            allowed_partitions=allowed,
            comparison_index=comparison_index,
        )
        return _envelope(bundle, allowed, result, warnings=result["warnings"])

    @app.post("/api/v1/atlas/view", operation_id="atlasView")
    async def atlas_view(payload: AtlasViewRequest, request: Request):
        allowed = partitions(request)
        request_body = _model_dict(payload)
        projection = build_view_projection(
            index,
            allowed_partitions=allowed,
            entity_ids=request_body.get("entity_ids"),
            maximum_entities=request_body.get("maximum_entities", 200),
        )
        warnings = ("INCOMPLETE_CAPACITY",) if projection["status"] != "PASS" else ()
        return _envelope(bundle, allowed, projection, warnings=warnings)

    app.openapi = build_openapi_document
    return app


def generate_typescript_client(openapi: Mapping[str, Any]) -> str:
    operations = {
        operation["operationId"]: (method.upper(), path)
        for path, methods in openapi["paths"].items()
        for method, operation in methods.items()
        if method.lower() in {"get", "post"}
    }
    required = {"atlasMeta", "atlasQuery", "atlasView"}
    if set(operations) != required:
        raise AtlasQueryError("ATLAS_TYPESCRIPT_OPERATION_SET_MISMATCH")
    return """// Generated from src/ovc/system_atlas/generated/atlas_openapi_v0_1.json. Do not edit manually.
export type AtlasVisibility = "ATLAS_PUBLIC_METADATA" | "ATLAS_INTERNAL" | "ATLAS_RESTRICTED";
export type AtlasQueryFamily = "SEARCH" | "TRACE" | "DEPENDENCY" | "IMPACT" | "EXPLAIN" | "AUTHORITY" | "OWNERSHIP" | "WHY_BLOCKED" | "HISTORY" | "DIFF";
export interface AtlasEnvelope<T> { schema: "ovc-atlas-api-envelope/v1"; graph_generation: string; repository_tree: string; query_policy_version: string; completeness_profile: string; security_visibility: AtlasVisibility[]; warnings: string[]; write_effect: "NONE"; data: T; }
export interface AtlasQueryRequest { family: AtlasQueryFamily; term?: string; start_id?: string; entity_id?: string; object_id?: string; changed_entity_ids?: string[]; max_depth?: number; direction?: "OUTBOUND" | "INBOUND" | "BOTH"; predicates?: string[]; relationship_families?: string[]; }
export interface AtlasViewRequest { entity_ids?: string[]; maximum_entities?: number; }
export class AtlasClient {
  constructor(private readonly baseUrl: string, private readonly fetcher: typeof fetch = fetch) {}
  private async call<T>(path: string, init?: RequestInit): Promise<AtlasEnvelope<T>> { const response = await this.fetcher(`${this.baseUrl}${path}`, init); const body = await response.json() as AtlasEnvelope<T>; if (!response.ok) throw Object.assign(new Error(`Atlas API ${response.status}`), { response: body }); return body; }
  meta<T = unknown>(): Promise<AtlasEnvelope<T>> { return this.call<T>("/api/v1/atlas/meta"); }
  query<T = unknown>(request: AtlasQueryRequest): Promise<AtlasEnvelope<T>> { return this.call<T>("/api/v1/atlas/query", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(request) }); }
  view<T = unknown>(request: AtlasViewRequest): Promise<AtlasEnvelope<T>> { return this.call<T>("/api/v1/atlas/view", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(request) }); }
}
"""
