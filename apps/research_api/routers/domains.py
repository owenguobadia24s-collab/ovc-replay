from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query

from ovc.console_vnext.application.errors import AuthorityDenied, ContractError, SourceGap
from ovc.console_vnext.application.investigate_preparation import build_fixture_investigate_snapshot
from ovc.console_vnext.application.research_wp5a import build_wp5a_representation_snapshot
from ovc.console_vnext.application.research_wp5b1 import build_wp5b1_dmrp_snapshot

from ..fixture_store import FixtureStore
from ..query import bounded_time_window, stable_page
from ..real_source_store import RealSourceStore

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_WP5A_BINDINGS = (
    _REPOSITORY_ROOT
    / "registries"
    / "research_console_vnext"
    / "research_native"
    / "wp5a_representation_source_bindings_v1.json"
)
_DEFAULT_WP5B1_BINDINGS = (
    _REPOSITORY_ROOT
    / "registries"
    / "research_console_vnext"
    / "research_native"
    / "wp5b1_dmrp_source_bindings_v1.json"
)


def _deny_validation(role: str | None) -> None:
    if role is not None and role.upper() == "VALIDATION":
        raise AuthorityDenied("VALIDATION_DENIED_BEFORE_OBJECT_RESOLUTION")


def build_domain_router(
    store: FixtureStore,
    *,
    real_store: RealSourceStore | None = None,
    source_mode: str = "FIXTURE",
    repository_root: Path | None = None,
    wp5a_bindings: Path | None = None,
    wp5b1_bindings: Path | None = None,
) -> APIRouter:
    router = APIRouter()
    repo_root = Path(repository_root or _REPOSITORY_ROOT)
    representation_bindings = Path(wp5a_bindings or _DEFAULT_WP5A_BINDINGS)
    dmrp_bindings = Path(wp5b1_bindings or _DEFAULT_WP5B1_BINDINGS)

    def real_projection(capability_id: str, resource: str, schema_id: str):
        if source_mode != "REAL" or real_store is None:
            raise SourceGap("REAL_SOURCE_STORE_NOT_ACTIVE")
        return real_store.envelope(
            resource,
            real_store.projection(capability_id),
            schema_id=schema_id,
        )

    @router.get("/market/window", tags=["market"])
    def market_window(
        start: str | None = Query(default=None),
        end: str | None = Query(default=None),
        limit: int = Query(default=500, ge=1, le=5000),
        role: str | None = Query(default=None),
    ):
        _deny_validation(role)
        if source_mode == "REAL":
            envelope = real_projection("MARKET", "market", "ovc-rcn-market-window/v1")
            if not envelope["capability"]["available"]:
                return envelope
            bars = envelope["payload"].get("bars")
            if not isinstance(bars, list):
                raise ContractError("MARKET_OWNER_PROJECTION_BARS_LIST_REQUIRED")
            try:
                envelope["payload"] = bounded_time_window(
                    bars, start=start, end=end, limit=limit
                )
            except (ValueError, KeyError, TypeError) as exc:
                raise ContractError(f"MARKET_OWNER_PROJECTION_BAR_CONTRACT:{exc}") from exc
            return envelope
        try:
            payload = bounded_time_window(
                store.resource("market").get("bars", []),
                start=start,
                end=end,
                limit=limit,
            )
        except ValueError as exc:
            raise ContractError(str(exc)) from exc
        return store.envelope(
            "market",
            payload,
            schema_id="ovc-rcn-market-window/v1",
            capability_id="MARKET",
        )

    @router.get("/c1/state", tags=["structure"])
    def c1_state(role: str | None = Query(default=None)):
        _deny_validation(role)
        if source_mode == "REAL":
            return real_projection("C1", "c1", "ovc-rcn-c1-view/v1")
        return store.envelope(
            "c1",
            store.resource("structure").get("c1", {}),
            schema_id="ovc-rcn-c1-view/v1",
            capability_id="C1",
        )

    @router.get("/c2/state", tags=["structure"])
    def c2_state(role: str | None = Query(default=None)):
        _deny_validation(role)
        if source_mode == "REAL":
            return real_projection("C2", "c2", "ovc-rcn-c2-view/v1")
        return store.envelope(
            "c2",
            store.resource("structure").get("c2", {}),
            schema_id="ovc-rcn-c2-view/v1",
            capability_id="C2",
        )

    @router.get("/c2e/episodes", tags=["structure"])
    def c2e_episodes(role: str | None = Query(default=None)):
        _deny_validation(role)
        if source_mode == "REAL":
            return real_projection("C2E", "c2e", "ovc-rcn-c2e-view/v1")
        return store.envelope(
            "c2e",
            store.resource("structure").get("c2e", {}),
            schema_id="ovc-rcn-c2e-view/v1",
            capability_id="C2E",
        )

    @router.get("/c2p/objects", tags=["structure", "preparation"])
    def c2p_objects(role: str | None = Query(default=None)):
        _deny_validation(role)
        return store.envelope(
            "c2p_preparation",
            dict(store.resource("c2p_preparation")),
            schema_id="ovc-rcn-c2p-preparation/v1",
            capability_id="C2P",
        )

    @router.get("/c2-5/events", tags=["structure", "preparation"])
    def c2_5_events(role: str | None = Query(default=None)):
        _deny_validation(role)
        return store.envelope(
            "c2_5_preparation",
            dict(store.resource("c2_5_preparation")),
            schema_id="ovc-rcn-c2-5-preparation/v1",
            capability_id="C2_5",
        )

    @router.get("/c3/graph", tags=["structure", "preparation"])
    def c3_graph(role: str | None = Query(default=None)):
        _deny_validation(role)
        return store.envelope(
            "c3_preparation",
            dict(store.resource("c3_preparation")),
            schema_id="ovc-rcn-c3-preparation/v1",
            capability_id="C3",
        )

    @router.get("/investigate/snapshot", tags=["structure", "preparation"])
    def investigate_snapshot(role: str | None = Query(default=None)):
        _deny_validation(role)
        if source_mode == "REAL":
            if real_store is None:
                raise SourceGap("REAL_SOURCE_STORE_NOT_ACTIVE")
            return real_store.investigate_snapshot()
        payload = build_fixture_investigate_snapshot(
            market=store.resource("market"),
            structure=store.resource("structure"),
            preparation=store.resource("investigate_preparation"),
        )
        return store.envelope(
            "investigate_snapshot",
            payload,
            schema_id="ovc-rcn-investigate-snapshot/v1",
            capability_id="C2",
        )

    @router.get("/occurrences/{occurrence_id}/context", tags=["context"])
    def occurrence_context(
        occurrence_id: str,
        role: str | None = Query(default=None),
    ):
        _deny_validation(role)
        payload = dict(store.resource("context"))
        if payload.get("occurrence_id") != occurrence_id:
            payload = {
                "availability": "NOT_MATERIALIZED",
                "occurrence_id": occurrence_id,
                "reason_code": "UPSTREAM_READ_MODEL_GAP",
            }
        return store.envelope(
            "occurrence_context",
            payload,
            schema_id="ovc-rcn-occurrence-context-view/v1",
            capability_id="CONTEXT",
        )

    @router.get("/research/representations", tags=["research"])
    def representations(role: str | None = Query(default=None)):
        _deny_validation(role)
        return store.envelope(
            "representations",
            store.resource("research").get("representations", []),
            schema_id="ovc-rcn-representation-list/v1",
            capability_id="RESEARCH",
        )

    @router.get("/research/representations/snapshot", tags=["research"])
    def representation_snapshot(role: str | None = Query(default=None)):
        _deny_validation(role)
        payload = build_wp5a_representation_snapshot(
            repository_root=repo_root,
            presentation=store.resource("research_wp5a"),
            bindings=representation_bindings,
        )
        return store.envelope(
            "research.representations.snapshot",
            payload,
            schema_id="ovc-rcn-rn-wp5a-representation-snapshot/v1",
            capability_id="RESEARCH",
        )

    @router.get("/research/dmrp/snapshot", tags=["research"])
    def dmrp_snapshot(role: str | None = Query(default=None)):
        _deny_validation(role)
        payload = build_wp5b1_dmrp_snapshot(
            repository_root=repo_root,
            presentation=store.resource("research_wp5b1"),
            bindings=dmrp_bindings,
        )
        return store.envelope(
            "research.dmrp.snapshot",
            payload,
            schema_id="ovc-rcn-rn-wp5b1-dmrp-snapshot/v1",
            capability_id="RESEARCH",
        )

    @router.get("/research/comparability", tags=["research"])
    def comparability(role: str | None = Query(default=None)):
        _deny_validation(role)
        return store.envelope(
            "comparability",
            store.resource("research").get("comparability", []),
            schema_id="ovc-rcn-comparability-list/v1",
            capability_id="RESEARCH",
        )

    @router.get("/research/families", tags=["research"])
    def families(role: str | None = Query(default=None)):
        _deny_validation(role)
        return store.envelope(
            "families",
            store.resource("research").get("families", []),
            schema_id="ovc-rcn-family-list/v1",
            capability_id="FAMILY_EVIDENCE",
        )

    @router.get("/research/benchmarks", tags=["research"])
    def benchmarks(role: str | None = Query(default=None)):
        _deny_validation(role)
        return store.envelope(
            "benchmarks",
            store.resource("research").get("benchmarks", []),
            schema_id="ovc-rcn-benchmark-list/v1",
            capability_id="RESEARCH",
        )

    @router.get("/evidence/objects", tags=["evidence"])
    def evidence_objects(
        cursor: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
    ):
        payload = stable_page(
            store.resource("evidence").get("items", []),
            key="evidence_id",
            cursor=cursor,
            limit=limit,
        )
        return store.envelope(
            "evidence",
            payload,
            schema_id="ovc-rcn-evidence-page/v1",
            capability_id="EVIDENCE",
        )

    @router.get("/fixture/investigations", tags=["fixture"])
    def fixture_investigations():
        return store.envelope(
            "investigations",
            store.resource("investigations"),
            schema_id="ovc-rcn-investigation-fixtures/v1",
            capability_id="SYSTEM",
        )

    return router
