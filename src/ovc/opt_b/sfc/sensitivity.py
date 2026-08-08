from __future__ import annotations

from typing import Any, Mapping, Sequence

from .serialization import logical_hash


class SFCSensitivityError(ValueError):
    pass


def configuration_identity(config: Mapping[str, Any]) -> str:
    return "SFC.CFG." + logical_hash(dict(config))[:24]


def declared_delta(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    keys=sorted(set(left)|set(right))
    changed=[key for key in keys if left.get(key)!=right.get(key)]
    return {"left_configuration_id":configuration_identity(left),"right_configuration_id":configuration_identity(right),"changed_fields":changed,"changed_count":len(changed),"fixed_fields":{key:left.get(key) for key in keys if key not in changed},"logical_hash":logical_hash({"left":dict(left),"right":dict(right),"changed":changed})}


def qualify_adjacent_sensitivity(left: Mapping[str, Any], right: Mapping[str, Any], *, sensitivity_field: str, ladder: Sequence[Any]) -> dict[str, Any]:
    delta=declared_delta(left,right)
    qualified=False; reason="NONQUALIFYING_PAIR"
    if delta["changed_fields"]==[sensitivity_field]:
        try:
            li=ladder.index(left[sensitivity_field]); ri=ladder.index(right[sensitivity_field])
            qualified=abs(li-ri)==1
            reason="QUALIFYING_ADJACENT_RUNG" if qualified else "NONADJACENT_RUNG"
        except (ValueError, KeyError):
            reason="RUNG_NOT_DECLARED"
    return {**delta,"qualified":qualified,"reason_code":reason,"sensitivity_field":sensitivity_field}


def qualify_cross_method(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    required=("representation_pack_id","comparison_spec_id","minimum_support")
    shared=all(left.get(key)==right.get(key) for key in required)
    different=left.get("family_method_id")!=right.get("family_method_id")
    payload={"left_configuration_id":configuration_identity(left),"right_configuration_id":configuration_identity(right),"qualified":bool(shared and different),"reason_code":"QUALIFYING_CROSS_METHOD" if shared and different else "NONQUALIFYING_CROSS_METHOD","shared_required_fields":list(required)}
    return {**payload,"logical_hash":logical_hash(payload)}
