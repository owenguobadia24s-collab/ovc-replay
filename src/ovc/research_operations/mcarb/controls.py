from __future__ import annotations
from decimal import Decimal
import hashlib

def _key(seed: str, index: int, value) -> str:
    return hashlib.sha256(f"{seed}|{index}|{value}".encode("utf-8")).hexdigest()

def stratified_shuffle(values: list, strata: list[str], *, seed_id: str) -> list:
    if len(values) != len(strata):
        raise ValueError("values/strata length mismatch")
    output=list(values)
    groups={}
    for index,(value,stratum) in enumerate(zip(values,strata)):
        groups.setdefault(stratum,[]).append((index,value))
    for stratum,members in sorted(groups.items()):
        targets=[i for i,_ in members]
        permuted=sorted(members,key=lambda iv:_key(seed_id+"|"+stratum,iv[0],iv[1]))
        for target,(_,value) in zip(targets,permuted):
            output[target]=value
    return output

def matched_complexity_noise(row_ids: list[str], *, dimensions: int, seed_id: str) -> dict[str, tuple[Decimal,...]]:
    if dimensions < 0:
        raise ValueError("dimensions cannot be negative")
    result={}
    scale=Decimal(16**16-1)
    for row_id in row_ids:
        values=[]
        for dim in range(dimensions):
            digest=hashlib.sha256(f"{seed_id}|{row_id}|{dim}".encode("utf-8")).hexdigest()[:16]
            values.append(Decimal(int(digest,16))/scale)
        result[row_id]=tuple(values)
    return result

def preserve_stratum_multisets(original: list, shuffled: list, strata: list[str]) -> bool:
    groups={}
    for a,b,s in zip(original,shuffled,strata):
        groups.setdefault(s,[[],[]])
        groups[s][0].append(a); groups[s][1].append(b)
    return all(sorted(map(str,x)) == sorted(map(str,y)) for x,y in groups.values())
