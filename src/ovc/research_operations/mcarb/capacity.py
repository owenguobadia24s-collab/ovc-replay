from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import platform
import time
import tracemalloc
from .models import PriceBar
from .activity import raw_activity, side_activity, activity_acceleration
from .intrinsic_time import directional_change, threshold_crossings, variation_clock
from .volatility import abs_return_variation, squared_return_variation, high_low_range
from .pack import PackDefinition, compile_pack
from .dependence import pearson, rank_correlation

PACKS=("R0","R1","R2","R3","R4","R4X","R5","R6")

def _bars(n: int, side: str) -> list[PriceBar]:
    start=datetime(2024,1,1,tzinfo=timezone.utc)
    out=[]
    price=Decimal("1.25000")
    for index in range(n):
        price += Decimal("0.0001") if index % 3 else Decimal("-0.00005")
        s=start+timedelta(hours=2*index); e=s+timedelta(hours=2)
        out.append(PriceBar(
            object_id=f"SYN.{side}.{index}", side=side,
            start_utc=s.isoformat().replace("+00:00","Z"), end_utc=e.isoformat().replace("+00:00","Z"),
            open=price-Decimal("0.00003"), high=price+Decimal("0.00020"), low=price-Decimal("0.00020"), close=price,
            volume=Decimal(1000+index%97),
        ))
    return out

def _profile_one(n_per_side: int) -> dict[str, object]:
    tracemalloc.start()
    t0=time.perf_counter()
    transform_count=0; pack_count=0; dependence_count=0; event_count=0
    for side in ("BID","ASK"):
        bars=_bars(n_per_side,side)
        al=[]; vs=[]
        for index,bar in enumerate(bars):
            al.append(raw_activity(bar)); transform_count += 1
            side_activity(bar); transform_count += 1
            high_low_range(bar); transform_count += 1
            if index:
                activity_acceleration(bars[index-1],bar); transform_count += 1
                vs.append(abs_return_variation(bars[index-1],bar)); transform_count += 1
                squared_return_variation(bars[index-1],bar); transform_count += 1
        dc=directional_change(bars,Decimal("0.0002")); x=threshold_crossings(bars,Decimal("1.251")); var=variation_clock(bars,Decimal("0.0005"))
        event_count += len(dc)+len(x)+len(var); transform_count += len(dc)+len(x)+len(var)
        fields=(("P.close","PRICE"),("AL-01","AL"),("ET-VAR","ET"),("VS-01","VS"))
        available={"P.close":"1.25","AL-01":"1000","ET-VAR":"1","VS-01":"0.001"}
        for pack_id in PACKS:
            allowed={"R0":{"PRICE"},"R1":{"PRICE","AL"},"R2":{"PRICE","ET"},"R3":{"PRICE","VS"},"R4":{"PRICE","AL","VS"},"R4X":{"PRICE","AL","ET"},"R5":{"PRICE","ET","VS"},"R6":{"PRICE","AL","ET","VS"}}[pack_id]
            use=tuple((field,domain) for field,domain in fields if domain in allowed)
            definition=PackDefinition(pack_id,tuple(field for field,_ in use),use)
            for _ in bars:
                compile_pack(definition,{key:value for key,value in available.items() if key in definition.field_ids}); pack_count += 1
        left=[m.value for m in al]; right=[Decimal(index+1) for index in range(len(al))]
        pearson(left,right); rank_correlation(left,right); dependence_count += 2
    wall=time.perf_counter()-t0
    current,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    return {
        "n_per_side":n_per_side,"input_bar_count":n_per_side*2,"transform_count":transform_count,
        "event_count":event_count,"pack_compile_count":pack_count,"dependence_vector_count":dependence_count,
        "wall_seconds":wall,"peak_python_tracemalloc_bytes":peak,
        "measurement_class":"MEASURED_SYNTHETIC_LOCAL_PROCESS",
    }

def capacity_profile(c0_n: int = 64, c1_n: int = 449) -> dict[str, object]:
    return {
        "schema":"ovc-mcarbi-capacity-profile/v1",
        "environment":{
            "python":platform.python_version(),"platform":platform.platform(),"cpu_count":os.cpu_count(),
            "github_actions":os.environ.get("GITHUB_ACTIONS","false"),"runner_os":os.environ.get("RUNNER_OS"),
        },
        "C0":_profile_one(c0_n),"C1":_profile_one(c1_n),
        "notes":["Synthetic capacity only; no market values are consumed.","C1 n_per_side equals proposed paired 2H Stage-A cardinality 449."],
    }
