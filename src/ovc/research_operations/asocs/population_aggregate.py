"""15M and 2H_A_L source-literal aggregation for ASOCS G1."""
from datetime import timedelta
from decimal import Decimal
from .population_core import *

def build_15m(rows,source_sha):
    by={}
    for r in rows: by.setdefault(floor15(r.source_time),[]).append(r)
    surface=[]; complete={}; cur=floor15(rows[0].source_time); end=floor15(rows[-1].source_time)
    while cur<=end:
        exp=[cur+timedelta(minutes=i) for i in range(15)]; obs={r.source_time:r for r in by.get(cur,[])}; miss=[t for t in exp if t not in obs]
        base={"schema":"ovc-asocs-audit-bar/v0_1","clock":"15M","lattice_id":LATTICE_15M_ID,"interval_start":literal(cur),"interval_end":literal(cur+timedelta(minutes=15)),"effective_time":literal(cur+timedelta(minutes=15)),"first_valid_time":literal(cur+timedelta(minutes=15)),"source_clock_state":SOURCE_CLOCK_STATE,"price_side":SOURCE_SIDE_STATE,"region":region(cur),"expected_parent_count":15,"observed_parent_count":len(obs),"missing_parent_slots":[literal(t) for t in miss],"repair_applied":False,"authority_class":AUTHORITY_CLASS,"active":False,"canonical":False,"publication":False}
        ids=[obs[t].source_row_id for t in exp if t in obs]
        if not miss and len(obs)==15:
            ps=[obs[t] for t in exp]; p={"clock":"15M","lattice_id":LATTICE_15M_ID,"interval_start":base["interval_start"],"parent_source_row_ids":ids,"source_sha256":source_sha}
            rec={**base,"bar_id":f"asocs:15m:{canonical_sha256(p)}","status":"COMPLETE","parent_source_row_ids":ids,"open":ps[0].open,"high":str(max(Decimal(x.high) for x in ps)),"low":str(min(Decimal(x.low) for x in ps)),"close":ps[-1].close}; complete[cur]=rec
        else:
            st="INCOMPLETE" if obs else "ABSENT"; p={"clock":"15M","lattice_id":LATTICE_15M_ID,"interval_start":base["interval_start"],"status":st,"observed_source_row_ids":ids,"missing_parent_slots":base["missing_parent_slots"],"source_sha256":source_sha}; rec={**base,"bar_id":f"asocs:15m-status:{canonical_sha256(p)}","status":st,"parent_source_row_ids":ids}
        surface.append(rec); cur+=timedelta(minutes=15)
    return surface,complete

def build_2h(rows,complete15,source_sha):
    surface=[]; cur=floor2(rows[0].source_time); end=floor2(rows[-1].source_time)
    while cur<=end:
        starts=[cur+timedelta(minutes=15*i) for i in range(8)]; parents=[complete15.get(t) for t in starts]; miss=[t for t,p in zip(starts,parents) if p is None]
        base={"schema":"ovc-asocs-audit-bar/v0_1","clock":"2H_A_L","lattice_id":LATTICE_2H_ID,"lattice_coordinate":chr(ord("A")+cur.hour//2),"interval_start":literal(cur),"interval_end":literal(cur+timedelta(hours=2)),"effective_time":literal(cur+timedelta(hours=2)),"first_valid_time":literal(cur+timedelta(hours=2)),"source_clock_state":SOURCE_CLOCK_STATE,"price_side":SOURCE_SIDE_STATE,"region":region(cur),"expected_parent_count":8,"observed_complete_parent_count":8-len(miss),"missing_parent_starts":[literal(t) for t in miss],"repair_applied":False,"authority_class":AUTHORITY_CLASS,"active":False,"canonical":False,"publication":False}
        ids=[str(p["bar_id"]) for p in parents if p]
        if not miss:
            ps=[p for p in parents if p]; q={"clock":"2H_A_L","lattice_id":LATTICE_2H_ID,"interval_start":base["interval_start"],"parent_15m_bar_ids":ids,"source_sha256":source_sha}; rec={**base,"bar_id":f"asocs:2h:{canonical_sha256(q)}","status":"COMPLETE","parent_15m_bar_ids":ids,"open":str(ps[0]["open"]),"high":str(max(Decimal(str(x["high"])) for x in ps)),"low":str(min(Decimal(str(x["low"])) for x in ps)),"close":str(ps[-1]["close"])}
        else:
            q={"clock":"2H_A_L","lattice_id":LATTICE_2H_ID,"interval_start":base["interval_start"],"missing_parent_starts":base["missing_parent_starts"],"source_sha256":source_sha}; rec={**base,"bar_id":f"asocs:2h-status:{canonical_sha256(q)}","status":"UNAVAILABLE","parent_15m_bar_ids":ids}
        surface.append(rec); cur+=timedelta(hours=2)
    return surface
