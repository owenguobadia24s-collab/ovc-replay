from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from ovc.console_vnext.application.errors import AuthorityDenied, ConsoleBoundaryError, SourceConflict, SourceGap
from .fixture_store import FixtureStore

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_ROOT = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1"


def _envelope(store: FixtureStore, resource: str, payload: Any) -> dict[str, Any]:
    return {"fixture_banner": store.banner(), "resource": resource, "payload": payload}


def create_app(*, fixture_root: Path | None = None) -> FastAPI:
    store = FixtureStore(fixture_root or DEFAULT_FIXTURE_ROOT)
    app = FastAPI(
        title="OVC Research Console vNext API",
        version="0.1.0-fixture",
        description="Loopback-only, read-only, fixture-first API. Authority effect NONE.",
    )
    app.state.fixture_store = store

    @app.exception_handler(ConsoleBoundaryError)
    async def console_boundary_handler(_request: Request, exc: ConsoleBoundaryError):
        status = 403 if isinstance(exc, AuthorityDenied) else 409 if isinstance(exc, (SourceConflict, SourceGap)) else 422
        return JSONResponse(status_code=status, content={"reason_code": exc.reason_code, "detail": str(exc), "authority_effect": "NONE"})

    @app.get("/api/v1/status", tags=["system"])
    def status():
        return _envelope(store, "status", {"service": "research-console-vnext", "read_only": True, "network_scope": "LOOPBACK_ONLY"})

    @app.get("/api/v1/capabilities", tags=["system"])
    def capabilities():
        rows = store.resource("capabilities").get("items", [])
        return _envelope(store, "capabilities", sorted(rows, key=lambda x: x["capability_id"]))

    @app.get("/api/v1/context", tags=["market"])
    def context():
        return _envelope(store, "context", store.resource("context"))

    @app.get("/api/v1/market", tags=["market"])
    def market():
        return _envelope(store, "market", store.resource("market"))

    @app.get("/api/v1/structure", tags=["structure"])
    def structure():
        return _envelope(store, "structure", store.resource("structure"))

    @app.get("/api/v1/research", tags=["research"])
    def research():
        return _envelope(store, "research", store.resource("research"))

    @app.get("/api/v1/evidence", tags=["evidence"])
    def evidence(cursor: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
        items = sorted(store.resource("evidence").get("items", []), key=lambda x: x["evidence_id"])
        page = items[cursor : cursor + limit]
        next_cursor = cursor + len(page) if cursor + len(page) < len(items) else None
        return _envelope(store, "evidence", {"items": page, "next_cursor": next_cursor, "total": len(items)})

    @app.get("/api/v1/governance", tags=["governance"])
    def governance():
        return _envelope(store, "governance", store.resource("governance"))

    return app
