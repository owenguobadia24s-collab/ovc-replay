from __future__ import annotations
import json
from pathlib import Path
from ovc.opt_b.srfd.serialization import logical_sha256
from ovc.opt_b.srfd.wp10_v11_interface import binding_from_manifest, mint_single_use_token, verify_science_unchanged
from srfd._current_pointer_compat import assert_lawful_v10_pointer
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-1-r3'
MANIFEST=BASE/'SRFD_JUNE_AUTHORITY_MANIFEST_R3.json'; DECISION=BASE/'SRFD_JUNE_AUTHORITY_OPERATOR_CONTINUATION_R3.json'; TOKEN=BASE/'SRFD_JUNE_AUTHORITY_TOKEN_R3.json'; QA=BASE/'SRFD_JUNE_AUTHORITY_R3_QA.json'; EXEC=ROOT/'registries/research/srfd/wp10_v11_execution_binding_v0_2.json'; STORE=ROOT/'registries/research/srfd/wp10_v11_storage_binding_v0_2.json'; STATE=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_51_WP10_V11_R3_AUTHORIZED.json'; POINTER=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'
def load(p): return json.loads(p.read_text())
def assert_hash(doc):
 saved=doc['logical_sha256']; body=dict(doc); body.pop('logical_sha256'); assert logical_sha256(body)==saved
def test_r3_authority_exact_and_single_use():
 m,d,t,e,s,q=map(load,[MANIFEST,DECISION,TOKEN,EXEC,STORE,QA]); [assert_hash(x) for x in (m,d,t,e,s,q)]; b=binding_from_manifest(m); verify_science_unchanged(b); assert b.logical_hash==m['run_binding_sha256']==t['run_binding_sha256']; assert b.execution_environment_profile_sha256=='e08aaf02871d23979b47f2ce928b2098d775eab3e483ff3602db2794afa13eef'; expected=mint_single_use_token(b,operator_decision_id=d['decision_id']); assert t['token_id']==expected['token_id']; assert t['state']=='AUTHORIZED_UNCONSUMED'; assert q['checks']['accepted_source_hashes_retrieved_and_verified']=='PASS_6_OF_6'
def test_r3_historical_authority_and_current_pointer_are_both_lawful():
 state,p=map(load,[STATE,POINTER]); assert_hash(state); assert state['status']=='READY'; assert state['science_execution_started'] is False; assert assert_lawful_v10_pointer(__import__('unittest').TestCase(),p); assert p['provider_fetch']=='DENIED'; assert p['validation_2025']=='LOCKED_UNCONSUMED'; assert p['scientific_promotion']=='NONE'
