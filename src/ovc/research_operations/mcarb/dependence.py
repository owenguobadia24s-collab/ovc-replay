from __future__ import annotations
from decimal import Decimal, getcontext

getcontext().prec = 40

def _paired(left, right):
    if len(left) != len(right):
        raise ValueError("paired vectors require equal length")
    pairs=[(Decimal(str(a)),Decimal(str(b))) for a,b in zip(left,right) if a is not None and b is not None]
    return pairs

def pearson(left, right) -> Decimal | None:
    pairs=_paired(left,right)
    n=len(pairs)
    if n < 2:
        return None
    xs=[p[0] for p in pairs]; ys=[p[1] for p in pairs]
    mx=sum(xs,Decimal(0))/Decimal(n); my=sum(ys,Decimal(0))/Decimal(n)
    dx=[x-mx for x in xs]; dy=[y-my for y in ys]
    num=sum((a*b for a,b in zip(dx,dy)),Decimal(0))
    sx=sum((a*a for a in dx),Decimal(0)); sy=sum((b*b for b in dy),Decimal(0))
    if sx == 0 or sy == 0:
        return None
    return num/(sx*sy).sqrt()

def _average_ranks(values: list[Decimal]) -> list[Decimal]:
    indexed=sorted(enumerate(values), key=lambda x:(x[1],x[0]))
    ranks=[Decimal(0)]*len(values)
    i=0
    while i < len(indexed):
        j=i+1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg=(Decimal(i+1)+Decimal(j))/Decimal(2)
        for k in range(i,j):
            ranks[indexed[k][0]]=avg
        i=j
    return ranks

def rank_correlation(left, right) -> Decimal | None:
    pairs=_paired(left,right)
    if len(pairs)<2:
        return None
    return pearson(_average_ranks([x for x,_ in pairs]),_average_ranks([y for _,y in pairs]))

def dependence_result(*, result_id: str, left_field_id: str, right_field_id: str,
                      left, right, method: str, comparability_left: str, comparability_right: str,
                      control_ids: tuple[str,...]=()):
    if comparability_left != comparability_right:
        return {"result_id":result_id,"left_field_id":left_field_id,"right_field_id":right_field_id,
                "method":method,"method_status":"ENABLED","comparability_domain_id":"NOT_COMPARABLE",
                "n_comparable":0,"value":None,"control_ids":list(control_ids),"authority":"DESCRIPTIVE_ONLY",
                "reason_codes":["NOT_COMPARABLE"]}
    if method == "MUTUAL_INFORMATION":
        raise ValueError("mutual information disabled until preregistered")
    pairs=_paired(left,right)
    value=pearson(left,right) if method=="PEARSON" else rank_correlation(left,right) if method=="RANK" else None
    if method not in {"PEARSON","RANK"}:
        raise ValueError("unsupported dependence method")
    return {"result_id":result_id,"left_field_id":left_field_id,"right_field_id":right_field_id,
            "method":method,"method_status":"ENABLED","comparability_domain_id":comparability_left,
            "n_comparable":len(pairs),"value":None if value is None else str(value),
            "control_ids":list(control_ids),"authority":"DESCRIPTIVE_ONLY","reason_codes":[]}
