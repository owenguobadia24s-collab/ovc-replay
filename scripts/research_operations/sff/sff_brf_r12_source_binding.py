#!/usr/bin/env python3
import argparse,csv,datetime as dt,gzip,hashlib,io,json,os,time,urllib.error,urllib.request
from collections import defaultdict
from pathlib import Path

YEARS=(2014,2016,2018,2019)
BASE="https://candledata.fxcorporate.com/m1/GBPUSD/{year}/{week}.csv.gz"

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def parse_dt(s):
    s=s.strip()
    for fmt in ("%m/%d/%Y %H:%M:%S.%f","%m/%d/%Y %H:%M:%S","%Y-%m-%d %H:%M:%S.%f","%Y-%m-%d %H:%M:%S"):
        try: return dt.datetime.strptime(s,fmt).replace(tzinfo=dt.timezone.utc)
        except ValueError: pass
    x=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    return x.replace(tzinfo=x.tzinfo or dt.timezone.utc).astimezone(dt.timezone.utc)

def fetch(url,retries=4):
    last=None
    for attempt in range(retries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"ovc-replay-sff-brf-r12/0.1"})
            with urllib.request.urlopen(req,timeout=60) as r:
                return r.status,r.read()
        except urllib.error.HTTPError as e:
            if e.code==404: return 404,b""
            last=e
            if e.code<500: raise
        except Exception as e:
            last=e
        time.sleep(2**attempt)
    raise RuntimeError(f"fetch failed after {retries} attempts: {url}: {last}")

def choose(headers,names):
    low={h.strip().lower():h for h in headers}
    for n in names:
        if n.lower() in low:return low[n.lower()]
    raise KeyError(f"missing required column {names}; headers={headers}")

def read_rows(raw):
    txt=gzip.decompress(raw).decode("utf-8-sig")
    rd=csv.DictReader(io.StringIO(txt))
    h=rd.fieldnames or []
    kdt=choose(h,["DateTime","datetime","timestamp","date"])
    ko=choose(h,["BidOpen","bidopen"])
    kh=choose(h,["BidHigh","bidhigh"])
    kl=choose(h,["BidLow","bidlow"])
    kc=choose(h,["BidClose","bidclose"])
    out=[]
    for row in rd:
        t=parse_dt(row[kdt])
        out.append((t,float(row[ko]),float(row[kh]),float(row[kl]),float(row[kc])))
    return out,h

def aggregate_15m(rows,year):
    uniq={}
    duplicate_same=0
    duplicate_conflict=0
    for r in rows:
        t=r[0]
        if t in uniq:
            if uniq[t]==r: duplicate_same+=1
            else: duplicate_conflict+=1
        uniq[t]=r
    if duplicate_conflict:
        raise RuntimeError(f"{year}: conflicting duplicate minute rows={duplicate_conflict}")
    rows=sorted(uniq.values(),key=lambda x:x[0])
    bybin=defaultdict(list)
    for r in rows:
        t=r[0]
        b=t.replace(minute=(t.minute//15)*15,second=0,microsecond=0)
        bybin[b].append(r)
    bars=[]
    incomplete=0
    for b,rs in sorted(bybin.items()):
        rs=sorted(rs,key=lambda x:x[0])
        expected=[b+dt.timedelta(minutes=i) for i in range(15)]
        if len(rs)!=15 or [x[0] for x in rs]!=expected:
            incomplete+=1
            continue
        bars.append((b,rs[0][1],max(x[2] for x in rs),min(x[3] for x in rs),rs[-1][4]))
    gaps=0
    prev=None
    for b,*_ in bars:
        if prev is not None and b-prev!=dt.timedelta(minutes=15):gaps+=1
        prev=b
    return bars,{"minute_rows_unique":len(rows),"duplicate_same":duplicate_same,"duplicate_conflict":duplicate_conflict,"complete_15m_bars":len(bars),"incomplete_15m_bins_dropped":incomplete,"15m_discontinuities":gaps}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=Path(a.out); rawdir=root/"raw"; aggdir=root/"aggregated"
    rawdir.mkdir(parents=True,exist_ok=True); aggdir.mkdir(parents=True,exist_ok=True)
    manifest={"schema":"sff-brf-r12-source-binding/v0.1","provider":"FXCM_PUBLIC_CANDLEDATA","instrument":"GBPUSD","side":"BID","raw_periodicity":"m1","target_clock":"15M","years":{},"source_url_template":BASE,"brf_outcomes_inspected":False}
    for year in YEARS:
        yrraw=rawdir/str(year); yrraw.mkdir()
        allrows=[]; weeks=[]; header_sets=[]
        for week in range(1,54):
            url=BASE.format(year=year,week=week)
            status,b=fetch(url)
            if status==404:
                weeks.append({"week":week,"url":url,"status":"SOURCE_ABSENT_404","bytes":0,"sha256":None,"rows":0})
                continue
            path=yrraw/f"{week}.csv.gz"; path.write_bytes(b)
            rows,headers=read_rows(b); allrows.extend(rows); header_sets.append(headers)
            weeks.append({"week":week,"url":url,"status":"PRESENT","bytes":len(b),"sha256":sha256_bytes(b),"rows":len(rows)})
        if not allrows: raise RuntimeError(f"{year}: no source rows fetched")
        bars,stats=aggregate_15m(allrows,year)
        if not bars: raise RuntimeError(f"{year}: no complete 15m bars")
        outp=aggdir/f"GBPUSD_BID_15M_{year}.csv.gz"
        payload=io.StringIO(); w=csv.writer(payload,lineterminator="\n")
        w.writerow(["DateTime","BidOpen","BidHigh","BidLow","BidClose"])
        for b,o,h,l,c in bars:w.writerow([b.isoformat().replace("+00:00","Z"),repr(o),repr(h),repr(l),repr(c)])
        outbytes=gzip.compress(payload.getvalue().encode("utf-8"),compresslevel=9,mtime=0); outp.write_bytes(outbytes)
        manifest["years"][str(year)]={"weeks":weeks,"present_weeks":sum(x["status"]=="PRESENT" for x in weeks),"absent_weeks":sum(x["status"]!="PRESENT" for x in weeks),"headers_seen":header_sets[:3],"aggregated_file":outp.name,"aggregated_bytes":len(outbytes),"aggregated_sha256":sha256_bytes(outbytes),**stats}
    mp=root/"SFF_BRF_R12_SOURCE_BINDING_MANIFEST_v0_1.json"
    mp.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    sums=[]
    for p in sorted(root.rglob("*")):
        if p.is_file():sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}")
    (root/"SHA256SUMS.txt").write_text("\n".join(sums)+"\n",encoding="utf-8")
    print(json.dumps(manifest,sort_keys=True,indent=2))

if __name__=="__main__":main()
