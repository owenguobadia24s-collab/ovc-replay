"""Exact RRSCG-D10 reducer fragment from the bound freeze candidate.

Only the reducer hierarchy and reducer function are transported here.  The
full D9 state, geometry, motion, and trajectory faculty remains in ``d9``.
"""

_D9_CONTROL_HIERARCHY=(
    ("FULL_CONSENSUS",("C_LAST_EXACT","C_LAST_HI","C_LAST_MID","CARRIER_BAG_HI","CARRIER_BAG_MID")),
    ("COARSE_CONSENSUS",("C_LAST_HI","C_LAST_MID","CARRIER_BAG_MID")),
    ("MINIMAL_CONSTRAINT",("C_LAST_MID",)),
)
_D10_SUCCESSOR_HIERARCHY=(
    ("FULL_CONSENSUS",("C_LAST_EXACT","C_LAST_HI","C_LAST_MID","CARRIER_BAG_HI","CARRIER_BAG_MID")),
    ("COARSE_CONSENSUS",("C_LAST_HI","C_LAST_MID","CARRIER_BAG_MID")),
    ("C_LAST_FAMILY_CONSENSUS",("C_LAST_EXACT","C_LAST_HI","C_LAST_MID")),
    ("MINIMAL_CONSTRAINT",("C_LAST_MID",)),
)

def _select_reducer(views,hierarchy):
    by={v["view_id"]:v for v in views}
    for tier,ids in hierarchy:
        xs=[by[i] for i in ids]
        if not all(v["antecedent_supported"] for v in xs):
            continue
        sets=[set(v["qualified_frontier_target_ids"]) for v in xs]
        q=set.intersection(*sets) if sets else set()
        if q:
            return sorted(q),tier
    return [],"NONE"
