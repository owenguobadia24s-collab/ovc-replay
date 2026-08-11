from __future__ import annotations
from fastapi import APIRouter, Query
from ovc.console_vnext.application.errors import AuthorityDenied, ContractError
from ovc.console_vnext.application.investigate_preparation import build_fixture_investigate_snapshot
from ..fixture_store import FixtureStore
from ..query import bounded_time_window, stable_page

def _deny_validation(role: str | None) -> None:
    if role is not None and role.upper() == "VALIDATION": raise AuthorityDenied("VALIDATION_DENIED_BEFORE_OBJECT_RESOLUTION")

def build_domain_router(store: FixtureStore) -> APIRouter:
    router=APIRouter()
    @router.get('/market/window',tags=['market'])
    def market_window(start:str|None=Query(default=None),end:str|None=Query(default=None),limit:int=Query(default=500,ge=1,le=5000),role:str|None=Query(default=None)):
        _deny_validation(role)
        try: payload=bounded_time_window(store.resource('market').get('bars',[]),start=start,end=end,limit=limit)
        except ValueError as exc: raise ContractError(str(exc)) from exc
        return store.envelope('market',payload,schema_id='ovc-rcn-market-window/v1',capability_id='MARKET')
    @router.get('/c1/state',tags=['structure'])
    def c1_state(role:str|None=Query(default=None)):
        _deny_validation(role); return store.envelope('c1',store.resource('structure').get('c1',{}),schema_id='ovc-rcn-c1-view/v1',capability_id='C1')
    @router.get('/c2/state',tags=['structure'])
    def c2_state(role:str|None=Query(default=None)):
        _deny_validation(role); return store.envelope('c2',store.resource('structure').get('c2',{}),schema_id='ovc-rcn-c2-view/v1',capability_id='C2')
    @router.get('/c2e/episodes',tags=['structure'])
    def c2e_episodes(role:str|None=Query(default=None)):
        _deny_validation(role); return store.envelope('c2e',store.resource('structure').get('c2e',{}),schema_id='ovc-rcn-c2e-view/v1',capability_id='C2E')
    @router.get('/c2p/objects',tags=['structure','preparation'])
    def c2p_objects(role:str|None=Query(default=None)):
        _deny_validation(role); return store.envelope('c2p_preparation',dict(store.resource('c2p_preparation')),schema_id='ovc-rcn-c2p-preparation/v1',capability_id='C2P')
    @router.get('/c2-5/events',tags=['structure','preparation'])
    def c2_5_events(role:str|None=Query(default=None)):
        _deny_validation(role); return store.envelope('c2_5_preparation',dict(store.resource('c2_5_preparation')),schema_id='ovc-rcn-c2-5-preparation/v1',capability_id='C2_5')
    @router.get('/investigate/snapshot',tags=['structure','preparation'])
    def investigate_snapshot(role:str|None=Query(default=None)):
        _deny_validation(role); p=build_fixture_investigate_snapshot(market=store.resource('market'),structure=store.resource('structure'),preparation=store.resource('investigate_preparation')); return store.envelope('investigate_snapshot',p,schema_id='ovc-rcn-investigate-snapshot/v1',capability_id='C2')
    @router.get('/occurrences/{occurrence_id}/context',tags=['context'])
    def occurrence_context(occurrence_id:str,role:str|None=Query(default=None)):
        _deny_validation(role); p=dict(store.resource('context'))
        if p.get('occurrence_id')!=occurrence_id: p={'availability':'NOT_MATERIALIZED','occurrence_id':occurrence_id,'reason_code':'UPSTREAM_READ_MODEL_GAP'}
        return store.envelope('occurrence_context',p,schema_id='ovc-rcn-occurrence-context-view/v1',capability_id='CONTEXT')
    @router.get('/research/representations',tags=['research'])
    def representations(): return store.envelope('representations',store.resource('research').get('representations',[]),schema_id='ovc-rcn-representation-list/v1',capability_id='RESEARCH')
    @router.get('/research/comparability',tags=['research'])
    def comparability(): return store.envelope('comparability',store.resource('research').get('comparability',[]),schema_id='ovc-rcn-comparability-list/v1',capability_id='RESEARCH')
    @router.get('/research/families',tags=['research'])
    def families(): return store.envelope('families',store.resource('research').get('families',[]),schema_id='ovc-rcn-family-list/v1',capability_id='FAMILY_EVIDENCE')
    @router.get('/research/benchmarks',tags=['research'])
    def benchmarks(): return store.envelope('benchmarks',store.resource('research').get('benchmarks',[]),schema_id='ovc-rcn-benchmark-list/v1',capability_id='RESEARCH')
    @router.get('/evidence/objects',tags=['evidence'])
    def evidence_objects(cursor:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=200)):
        p=stable_page(store.resource('evidence').get('items',[]),key='evidence_id',cursor=cursor,limit=limit); return store.envelope('evidence',p,schema_id='ovc-rcn-evidence-page/v1',capability_id='EVIDENCE')
    @router.get('/fixture/investigations',tags=['fixture'])
    def fixture_investigations(): return store.envelope('investigations',store.resource('investigations'),schema_id='ovc-rcn-investigation-fixtures/v1',capability_id='SYSTEM')
    return router
