from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .models import canonical_hash

PACK_DOMAINS = {
    "R0": ("PRICE",), "R1": ("PRICE","AL"), "R2": ("PRICE","ET"), "R3": ("PRICE","VS"),
    "R4": ("PRICE","AL","VS"), "R4X": ("PRICE","AL","ET"), "R5": ("PRICE","ET","VS"),
    "R6": ("PRICE","AL","ET","VS"), "D-AL": ("AL",), "D-ET": ("ET",), "D-VS": ("VS",),
}

@dataclass(frozen=True)
class PackDefinition:
    pack_id: str
    field_ids: tuple[str, ...]
    field_domains: tuple[tuple[str, str], ...]
    variant_ids: tuple[str, ...] = ()
    normalization_ids: tuple[str, ...] = ()
    comparability_domain_id: str = "MCARB.DEFAULT"
    free_parameter_count: int = 0
    lookback_burden: int = 0
    categorical_cardinality: int = 0
    diagnostic_only: bool = False

    def __post_init__(self):
        if self.pack_id not in PACK_DOMAINS:
            raise ValueError("unknown pack")
        if len(set(self.field_ids)) != len(self.field_ids):
            raise ValueError("duplicate field id")
        mapping=dict(self.field_domains)
        if set(mapping) != set(self.field_ids):
            raise ValueError("every field must have exactly one domain declaration")
        allowed=set(PACK_DOMAINS[self.pack_id])
        if any(domain not in allowed for domain in mapping.values()):
            raise ValueError("field domain outside pack contract")
        if self.diagnostic_only != self.pack_id.startswith("D-"):
            raise ValueError("diagnostic-only flag must match D-* pack identity")
        if self.pack_id == "R0" and any(domain != "PRICE" for domain in mapping.values()):
            raise ValueError("R0 is price-only")

    @property
    def pack_spec_id(self) -> str:
        return "MCARB.PACK." + canonical_hash({
            "pack_id":self.pack_id,"field_ids":self.field_ids,"field_domains":self.field_domains,
            "variant_ids":self.variant_ids,"normalization_ids":self.normalization_ids,
            "comparability_domain_id":self.comparability_domain_id,
        })[:24]

    def complexity(self, missing_count: int = 0) -> dict[str, int | None]:
        return {
            "feature_count": len(self.field_ids),
            "free_parameter_count": self.free_parameter_count,
            "lookback_burden": self.lookback_burden,
            "missingness_burden": missing_count,
            "categorical_cardinality": self.categorical_cardinality,
            "effective_information": None,
        }

def compile_pack(definition: PackDefinition, available: dict[str, Any]) -> dict[str, Any]:
    hidden = set(available) - set(definition.field_ids)
    fields=[]
    missing=[]
    for field_id in definition.field_ids:
        value=available.get(field_id)
        if value is None:
            missing.append(field_id)
        fields.append({"field_id":field_id,"value":value})
    return {
        "pack_spec_id":definition.pack_spec_id,
        "pack_id":definition.pack_id,
        "fields":fields,
        "missing_field_ids":missing,
        "ignored_available_field_ids":sorted(hidden),
        "complexity":definition.complexity(len(missing)),
        "diagnostic_only":definition.diagnostic_only,
        "authority":"RESEARCH_PACK_ONLY_NO_PROMOTION",
    }

def nested_ablation_field_sets(definition: PackDefinition) -> dict[str, tuple[str,...]]:
    by_domain={}
    mapping=dict(definition.field_domains)
    for domain in PACK_DOMAINS[definition.pack_id]:
        by_domain[domain]=tuple(f for f in definition.field_ids if mapping[f] != domain)
    if definition.pack_id == "R6":
        by_domain["R4X"]=tuple(f for f in definition.field_ids if mapping[f] in {"PRICE","AL","ET"})
    return by_domain
