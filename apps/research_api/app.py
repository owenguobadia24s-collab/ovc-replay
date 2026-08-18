from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ovc.console_vnext.application.errors import AuthorityDenied, ConsoleBoundaryError, SourceConflict, SourceGap

from .fixture_store import FixtureStore
from .real_source_store import RealSourceStore
from .routers.dmrp import build_dmrp_router
from .routers.domains import build_domain_router
from .routers.system import build_system_router

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_ROOT = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1"
DEFAULT_REAL_SOURCE_ROOT = ROOT / "var" / "research_console_vnext" / "owner_read_projections"
DEFAULT_REAL_SOURCE_BINDINGS = ROOT / "registries" / "research_console_vnext" / "research_native" / "owner_read_projection_bindings_v1.json"
_MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app(*, fixture_root: Path | None = None, source_mode: str | None = None, real_source_root: Path | None = None, real_source_bindings: Path | None = None) -> FastAPI:
    store = FixtureStore(fixture_root or DEFAULT_FIXTURE_ROOT)
    resolved_mode = (source_mode or os.environ.get("OVC_RCN_INVESTIGATE_SOURCE_MODE", "FIXTURE")).strip().upper()
    if resolved_mode not in {"FIXTURE", "REAL"}:
        raise ValueError("INVESTIGATE_SOURCE_MODE_MUST_BE_FIXTURE_OR_REAL")
    real_store = RealSourceStore(real_source_root or DEFAULT_REAL_SOURCE_ROOT, real_source_bindings or DEFAULT_REAL_SOURCE_BINDINGS) if resolved_mode == "REAL" else None
    app = FastAPI(
        title="OVC Research Console vNext API",
        version="0.1.0-g5-dmrp",
        description="Loopback-only GET/read-only API. Fixture mode is explicit; G4 market/structure and independently admitted G5 DMRP real-source routes are owner-source-bound and fail closed without fixture fallback.",
    )
    app.state.fixture_store = store
    app.state.real_source_store = real_store
    app.state.investigate_source_mode = resolved_mode
    app.state.network_scope = "LOOPBACK_ONLY"
    app.state.cache_enabled = False

    @app.middleware("http")
    async def read_only_transport(request: Request, call_next):
        if request.method.upper() in _MUTATION_METHODS:
            return JSONResponse(
                status_code=405,
                content={
                    "reason_code": "MUTATION_METHOD_DENIED",
                    "detail": "Research Console vNext transport is GET/read-only.",
                    "authority_effect": "NONE",
                },
            )
        return await call_next(request)

    @app.exception_handler(ConsoleBoundaryError)
    async def console_boundary_handler(_request: Request, exc: ConsoleBoundaryError):
        status = 403 if isinstance(exc, AuthorityDenied) else 409 if isinstance(exc, (SourceConflict, SourceGap)) else 422
        return JSONResponse(
            status_code=status,
            content={"reason_code": exc.reason_code, "detail": str(exc), "authority_effect": "NONE"},
        )

    app.include_router(build_system_router(store), prefix="/api/v1")
    app.include_router(build_domain_router(store, real_store=real_store, source_mode=resolved_mode), prefix="/api/v1")
    app.include_router(build_dmrp_router(store, source_mode=resolved_mode), prefix="/api/v1")
    return app
