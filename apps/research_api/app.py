from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ovc.console_vnext.application.errors import AuthorityDenied, ConsoleBoundaryError, SourceConflict, SourceGap

from .fixture_store import FixtureStore
from .routers.domains import build_domain_router
from .routers.system import build_system_router

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_ROOT = ROOT / "fixtures" / "research_console_vnext" / "console_pack_v0_1"
_MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app(*, fixture_root: Path | None = None) -> FastAPI:
    store = FixtureStore(fixture_root or DEFAULT_FIXTURE_ROOT)
    app = FastAPI(
        title="OVC Research Console vNext API",
        version="0.1.0-fixture",
        description="Loopback-only, read-only, fixture-first API. Authority effect NONE.",
    )
    app.state.fixture_store = store
    app.state.network_scope = "LOOPBACK_ONLY"
    app.state.cache_enabled = False

    @app.middleware("http")
    async def read_only_transport(request: Request, call_next):
        if request.method.upper() in _MUTATION_METHODS:
            return JSONResponse(
                status_code=405,
                content={
                    "reason_code": "MUTATION_METHOD_DENIED",
                    "detail": "Research Console vNext v0.1 transport is GET/read-only.",
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
    app.include_router(build_domain_router(store), prefix="/api/v1")
    return app
