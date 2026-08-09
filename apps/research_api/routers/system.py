from __future__ import annotations

from fastapi import APIRouter, Query

from ovc.console_vnext.application.errors import AuthorityDenied

from ..fixture_store import FixtureStore


def _deny_validation(role: str | None) -> None:
    if role is not None and role.upper() == "VALIDATION":
        raise AuthorityDenied("VALIDATION_DENIED_BEFORE_OBJECT_RESOLUTION")


def build_system_router(store: FixtureStore) -> APIRouter:
    router = APIRouter()

    @router.get("/status", tags=["system"])
    def status():
        return store.envelope(
            "status",
            {"service": "research-console-vnext", "read_only": True, "network_scope": "LOOPBACK_ONLY", "cache_enabled": False},
            schema_id="ovc-rcn-status/v1",
            capability_id="SYSTEM",
        )

    @router.get("/identity", tags=["system"])
    def identity():
        return store.envelope("identity", store.identity(), schema_id="ovc-rcn-identity/v1", capability_id="SYSTEM")

    @router.get("/capabilities", tags=["system"])
    def capabilities():
        rows = sorted(store.resource("capabilities").get("items", []), key=lambda row: row["capability_id"])
        return store.envelope(
            "capabilities", rows, schema_id="ovc-rcn-capability-dependency-status-list/v1", capability_id="SYSTEM"
        )

    @router.get("/context/options", tags=["context"])
    def context_options(role: str | None = Query(default=None)):
        _deny_validation(role)
        return store.envelope(
            "context", store.resource("context"), schema_id="ovc-rcn-context-options/v1", capability_id="CONTEXT"
        )

    return router
