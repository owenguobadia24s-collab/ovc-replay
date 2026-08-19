"""Core deterministic contracts for ASOCS G1 audit population construction."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping, Sequence
import gzip, hashlib, json
from .source import ASOCSSourceQualificationError, iter_source_rows

TARGET_START=datetime(2026,1,1); TARGET_END=datetime(2026,7,1)
SOURCE_CLOCK_STATE="SOURCE_TIMEZONE_UNRESOLVED"; SOURCE_SIDE_STATE="UNRESOLVED_SINGLE_STREAM"
CLAIM_CLASS="ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE"; AUTHORITY_CLASS="ASOCS_AUDIT_ONLY"
LATTICE_15M_ID="ASOCS.LATTICE.15M.SOURCE_LITERAL_0000.v0.1"
LATTICE_2H_ID="ASOCS.LATTICE.2H_A_L.SOURCE_LITERAL_0000.v0.1"
RENDERER_CONTRACT={"schema":"ovc-asocs-source-native-renderer-contract/v0_1","renderer_id":"ASOCS.SOURCE_NATIVE.SVG.CANDLE.v0.1","input":"COMPLETE_ASOCS_15M_AUDIT_BARS_ONLY","format":"SVG_1_1_UTF8","network_dependency":False,"source_clock_annotation":SOURCE_CLOCK_STATE,"semantic_effect":"EVIDENCE_PRESENTATION_ONLY","fixed_width":1200,"fixed_height":600,"padding":40,"coordinate_precision":3}

class ASOCSPopulationError(ValueError): pass

def canonical_json_bytes(v:object)->bytes: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def canonical_sha256(v:object)->str: return hashlib.sha256(canonical_json_bytes(v)).hexdigest()
def literal(t:datetime)->str: return t.strftime("%Y-%m-%dT%H:%M:%S")
def region(t:datetime)->str: return "PRE_CONTEXT" if t<TARGET_START else "POST_CONTEXT" if t>=TARGET_END else "TARGET"
def floor15(t:datetime)->datetime: return t.replace(minute=t.minute//15*15,second=0,microsecond=0)
def floor2(t:datetime)->datetime: return t.replace(hour=t.hour//2*2,minute=0,second=0,microsecond=0)

@dataclass(frozen=True)
class SourceRow:
    row_number:int; source_time:datetime; literal_timestamp:str; open:str; high:str; low:str; close:str; volume:str; source_row_id:str
@dataclass(frozen=True)
class MaterializationResult:
    manifest:Mapping[str,object]; external_root:Path

def read_source(path:Path,expected_sha:str)->tuple[list[SourceRow],int]:
    raw=path.read_bytes(); actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected_sha: raise ASOCSPopulationError(f"SOURCE_HASH_MISMATCH:{actual}")
    try: raw.decode("utf-8",errors="strict")
    except UnicodeDecodeError as e: raise ASOCSPopulationError("SOURCE_NOT_STRICT_UTF8") from e
    out=[]; seen=set(); prev=None
    try:
        with path.open("r",encoding="utf-8",errors="strict",newline="") as h:
            for r in iter_source_rows(h):
                t=r.source_time
                if t in seen: raise ASOCSPopulationError(f"DUPLICATE_TIMESTAMP:{literal(t)}")
                if prev is not None and t<=prev: raise ASOCSPopulationError(f"NON_MONOTONIC_TIMESTAMP:{literal(t)}")
                seen.add(t); prev=t
                p={"source_sha256":expected_sha,"row_number":r.row_number,"literal_timestamp":r.literal_timestamp,"open":str(r.open),"high":str(r.high),"low":str(r.low),"close":str(r.close),"volume":str(r.volume)}
                out.append(SourceRow(r.row_number,t,r.literal_timestamp,str(r.open),str(r.high),str(r.low),str(r.close),str(r.volume),f"asocs:m1:{canonical_sha256(p)}"))
    except ASOCSSourceQualificationError as e: raise ASOCSPopulationError(str(e)) from e
    if not out: raise ASOCSPopulationError("SOURCE_HAS_NO_DATA_ROWS")
    return out,len(raw)

def write_gzip_jsonl(path:Path,records:Iterable[Mapping[str,object]])->dict[str,object]:
    path.parent.mkdir(parents=True,exist_ok=True); n=0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="",mode="wb",fileobj=raw,mtime=0) as z:
            for r in records: z.write(canonical_json_bytes(r)+b"\n"); n+=1
    b=path.read_bytes(); return {"sha256":hashlib.sha256(b).hexdigest(),"byte_size":len(b),"record_count":n,"compression":"gzip-mtime-0-jsonl"}

def render_source_native_svg(bars:Sequence[Mapping[str,object]])->str:
    if not bars: raise ASOCSPopulationError("RENDERER_REQUIRES_BARS")
    w,h,p,prec=(int(RENDERER_CONTRACT[k]) for k in ("fixed_width","fixed_height","padding","coordinate_precision"))
    hi=max(Decimal(str(b["high"])) for b in bars); lo=min(Decimal(str(b["low"])) for b in bars)
    if hi<=lo: raise ASOCSPopulationError("RENDERER_ZERO_PRICE_RANGE")
    step=Decimal(w-2*p)/Decimal(len(bars)); bw=max(Decimal("1"),step*Decimal("0.55")); ph=Decimal(h-2*p)
    def y(v:Decimal)->str: return f"{Decimal(p)+(hi-v)/(hi-lo)*ph:.{prec}f}"
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<metadata>{json.dumps(RENDERER_CONTRACT,sort_keys=True,separators=(",",":"))}</metadata>','<rect x="0" y="0" width="1200" height="600" fill="white"/>']
    for i,b in enumerate(bars):
        x=Decimal(p)+(Decimal(i)+Decimal("0.5"))*step; o,c,hh,ll=(Decimal(str(b[k])) for k in ("open","close","high","low")); top=max(o,c); bottom=min(o,c); by=y(top); bh=abs(Decimal(y(bottom))-Decimal(by)); fill="black" if c<o else "white"
        parts += [f'<line x1="{x:.{prec}f}" y1="{y(hh)}" x2="{x:.{prec}f}" y2="{y(ll)}" stroke="black" stroke-width="1"/>',f'<rect x="{x-bw/2:.{prec}f}" y="{by}" width="{bw:.{prec}f}" height="{max(bh,Decimal("1")):.{prec}f}" fill="{fill}" stroke="black" stroke-width="1"/>']
    return "\n".join(parts+["</svg>"])+"\n"
