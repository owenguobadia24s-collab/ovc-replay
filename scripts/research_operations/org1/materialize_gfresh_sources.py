#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,math,urllib.error,urllib.request
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path

YEARS=(2012,2013)
URL='https://candledata.fxcorporate.com/m1/GBPUSD/{year}/{week}.csv.gz'
MINTICK=0.00001
FP_MOD=2147483629; FP_MULT=1000003

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def canon(obj)->bytes:return (json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n').encode()
def norm(s):return ''.join(ch for ch in s.lower() if ch.isalnum())

def parse_dt(s:str)->datetime:
    s=s.strip()
    fmts=('%m/%d/%Y %H:%M:%S.%f','%m/%d/%Y %H:%M:%S','%Y-%m-%d %H:%M:%S.%f','%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S.%fZ','%Y-%m-%dT%H:%M:%SZ')
    for f in fmts:
        try:return datetime.strptime(s,f).replace(tzinfo=timezone.utc)
        except ValueError:pass
    raise ValueError('UNSUPPORTED_DATETIME:'+s)

def parse_week(raw:bytes):
    text=gzip.decompress(raw).decode('utf-8-sig').replace('\x00','')
    reader=csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:raise ValueError('MISSING_HEADER')
    keys={norm(x):x for x in reader.fieldnames}
    def key(*cands):
        for c in cands:
            if norm(c) in keys:return keys[norm(c)]
        raise ValueError('MISSING_COLUMN:'+','.join(cands)+':'+repr(reader.fieldnames))
    kd=key('DateTime','Date','Timestamp'); ko=key('BidOpen'); kh=key('BidHigh'); kl=key('BidLow'); kc=key('BidClose')
    out=[]
    for r in reader:
        if not r.get(kd):continue
        out.append((parse_dt(r[kd]),float(r[ko]),float(r[kh]),float(r[kl]),float(r[kc])))
    return out,reader.fieldnames

def pine_round_positive(x):return int(math.floor(x+0.5))
def fp_update(prior,seq,t_s,o,h,l,c):
    ot=pine_round_positive(o/MINTICK);ht=pine_round_positive(h/MINTICK);lt=pine_round_positive(l/MINTICK);ct=pine_round_positive(c/MINTICK)
    tm=int(math.floor((t_s*1000)/60000))%10000000
    mix=ot*31+ht*37+lt*41+ct*43+seq*47+tm*53
    nxt=int((prior*FP_MULT+mix)%FP_MOD)
    return nxt+FP_MOD if nxt<0 else nxt

def aggregate_15m(rows,year):
    begin=datetime(year,1,1,tzinfo=timezone.utc); end=datetime(year+1,1,1,tzinfo=timezone.utc)
    chosen={};duplicates=0
    for rec in rows:
        t=rec[0]
        if not(begin<=t<end):continue
        prior=chosen.get(t)
        if prior is None:chosen[t]=rec
        elif prior==rec:duplicates+=1
        else:raise ValueError('CONFLICTING_DUPLICATE_TIMESTAMP:'+t.isoformat())
    ordered=[chosen[t] for t in sorted(chosen)];bins=defaultdict(list)
    for rec in ordered:
        t=rec[0];floor=t.replace(minute=(t.minute//15)*15,second=0,microsecond=0);bins[floor].append(rec)
    bars=[];incomplete=[]
    for b in sorted(bins):
        rr=sorted(bins[b]);expected=[b+timedelta(minutes=i) for i in range(15)];actual=[x[0] for x in rr]
        if actual!=expected:
            incomplete.append({'start_utc':b.isoformat().replace('+00:00','Z'),'minutes_present':len(rr)});continue
        bars.append((b,rr[0][1],max(x[2] for x in rr),min(x[3] for x in rr),rr[-1][4]))
    fp=17;raw_gaps=weekends=source_gaps=0;gap_ledger=[];prev=None
    for seq,b in enumerate(bars,1):
        if prev:
            missing=max(int(round((b[0]-prev[0]).total_seconds()/900))-1,0)
            if missing:
                raw_gaps+=1;scheduled=prev[0].weekday()==4 and b[0].weekday()==6
                weekends+=int(scheduled);source_gaps+=int(not scheduled)
                gap_ledger.append({'after_utc':prev[0].isoformat().replace('+00:00','Z'),'before_utc':b[0].isoformat().replace('+00:00','Z'),'missing_15m_slots':missing,'class':'SCHEDULED_WEEKEND_CLOSURE' if scheduled else 'SOURCE_GAP_BREAK'})
        fp=fp_update(fp,seq,int(b[0].timestamp()),b[1],b[2],b[3],b[4]);prev=b
    receipt={'year':year,'provider':'FXCM_PUBLIC_CANDLEDATA','instrument':'GBPUSD','side':'BID','clock':'15M','raw_m1_rows_in_calendar_year':len(ordered),'duplicate_m1_rows_identical':duplicates,'incomplete_15m_bins_dropped':len(incomplete),'bars_15m':len(bars),'first_15m_utc':bars[0][0].isoformat().replace('+00:00','Z') if bars else None,'last_15m_utc':bars[-1][0].isoformat().replace('+00:00','Z') if bars else None,'raw_gap_events':raw_gaps,'scheduled_weekend_closures':weekends,'source_gap_breaks':source_gaps,'stream_segments':1+source_gaps if bars else 0,'scc_source_fingerprint':fp,'mintick':MINTICK,'target_firewall':'CLOSED_NO_D_L_O_COMPUTED'}
    return bars,receipt,incomplete,gap_ledger

def download_year(year,out):
    rawdir=out/'raw'/str(year);rawdir.mkdir(parents=True,exist_ok=True);manifest=[];rows=[];headers=None
    for week in range(1,54):
        url=URL.format(year=year,week=week);req=urllib.request.Request(url,headers={'User-Agent':'OVC-ORG1-GFRESH/0.1 source-binding-only'})
        try:
            with urllib.request.urlopen(req,timeout=45) as r:data=r.read()
        except urllib.error.HTTPError as e:
            if e.code==404:continue
            raise
        p=rawdir/f'{week}.csv.gz';p.write_bytes(data);parsed,h=parse_week(data)
        if headers is None:headers=h
        elif [norm(x) for x in headers]!=[norm(x) for x in h]:raise ValueError('WEEK_HEADER_DRIFT')
        rows.extend(parsed);manifest.append({'week':week,'url':url,'sha256':sha(data),'bytes':len(data),'rows':len(parsed)})
    if len(manifest)<50:raise ValueError(f'INSUFFICIENT_WEEK_FILES:{year}:{len(manifest)}')
    bars,receipt,incomplete,gaps=aggregate_15m(rows,year)
    if len(bars)<5000:raise ValueError(f'INSUFFICIENT_15M_BARS:{year}:{len(bars)}')
    csvp=out/f'FXCM_GBPUSD_BID_15M_{year}.csv'
    with csvp.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['time_utc','open','high','low','close'])
        for b in bars:w.writerow([b[0].isoformat().replace('+00:00','Z'),*(format(x,'.10g') for x in b[1:])])
    receipt['derived_15m_sha256']=sha(csvp.read_bytes());receipt['weekly_source_file_count']=len(manifest)
    (out/f'FXCM_GBPUSD_BID_M1_{year}_WEEKLY_MANIFEST.json').write_bytes(canon({'year':year,'files':manifest}))
    (out/f'FXCM_GBPUSD_BID_15M_{year}_SOURCE_RECEIPT.json').write_bytes(canon(receipt))
    (out/f'FXCM_GBPUSD_BID_15M_{year}_GAP_LEDGER.json').write_bytes(canon({'year':year,'gaps':gaps,'incomplete_bins':incomplete}))
    return receipt

def selftest():
    b=datetime(2012,1,2,0,0,tzinfo=timezone.utc);rows=[]
    for i in range(30):
        x=1.2+i/100000;rows.append((b+timedelta(minutes=i),x,x+.0001,x-.0001,x+.00001))
    bars,r,inc,g=aggregate_15m(rows,2012)
    assert len(bars)==2 and not inc and not g and r['bars_15m']==2 and r['source_gap_breaks']==0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='org1_gfresh_source_binding');ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
    if a.self_test:selftest();print('ORG1_GFRESH_SOURCE_BINDING_SELF_TEST_PASS');return
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);receipts=[download_year(y,out) for y in YEARS]
    binding={'schema':'ovc-org1-gfresh-source-binding-candidate/v1','programme_id':'OVC-SFF-AOSC-ORG1-v0.1','roles':[{'role':'EVAL-A-CANDIDATE','year':2012,'receipt':receipts[0]},{'role':'EVAL-B-CANDIDATE','year':2013,'receipt':receipts[1]}],'mutually_disjoint':True,'selection_basis':'PRE_OUTCOME_CHRONOLOGY_ADMISSIBILITY_EXPOSURE_ONLY','target_firewall':'CLOSED_NO_ORG1_D_L_O_COMPUTED','next':'AOSC_REPLAY_FEASIBILITY_AND_EXPOSURE_BINDING'}
    (out/'ORG1_GFRESH_SOURCE_BINDING_CANDIDATE_v0_1.json').write_bytes(canon(binding));print(json.dumps(binding,sort_keys=True))
if __name__=='__main__':main()
