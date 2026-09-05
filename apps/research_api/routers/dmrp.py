from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query

from ovc.console_vnext.application.errors import AuthorityDenied
from ovc.console_vnext.application.research_wp5b1 import build_wp5b1_dmrp_snapshot
from ovc.console_vnext.application.research_wp5b1_real import build_wp5b1_dmrp_real_envelope

from ..fixture_store import FixtureStore

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_FIXTURE_BINDINGS = (
    _REPOSITORY_ROOT
    / "registries"
    / "research_console_vnext"
    / "research_native"
    / "wp5b1_dmrp_source_bindings_v1.json"
)
_DEFAULT_REAL_BINDINGS = (
    _REPOSITORY_ROOT
    / "registries"
    / "research_console_vnext"
    / "research_native"
    / "wp5b1_dmrp_real_source_bindings_v1.json"
)


def build_dmrp_router(
    store: FixtureStore,
    *,
    source_mode: str,
    repository_root: Path | None = None,
    fixture_bindings: Path | None = None,
    real_bindings: Path | None = None,
) -> APIRouter:
    router = APIRouter()
    repo_root = Path(repository_root or _REPOSITORY_ROOT)
    fixture_binding_path = Path(fixture_bindings or _DEFAULT_FIXTURE_BINDINGS)
    real_binding_path = Path(real_bindings or _DEFAULT_REAL_BINDINGS)

    @router.get("/research/dmrp/snapshot", tags=["research"])
    def dmrp_snapshot(role: str | None = Query(default=None)):
        if role is not None and role.upper() == "VALIDATION":
            raise AuthorityDenied("VALIDATION_DENIED_BEFORE_OBJECT_RESOLUTION")
        if source_mode == "REAL":
            return build_wp5b1_dmrp_real_envelope(
                repository_root=repo_root,
                bindings=real_binding_path,
            )
        payload = build_wp5b1_dmrp_snapshot(
            repository_root=repo_root,
            presentation=store.resource("research_wp5b1"),
            bindings=fixture_binding_path,
        )
        return store.envelope(
            "research.dmrp.snapshot",
            payload,
            schema_id="ovc-rcn-rn-wp5b1-dmrp-snapshot/v1",
            capability_id="RESEARCH",
        )

    return router
