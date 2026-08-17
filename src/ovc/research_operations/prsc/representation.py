from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256
from .contracts import PRSCContractError

CROSSWALK_STATES = frozenset({
    "MATCH", "SPLIT", "MERGE", "AMBIGUOUS", "NOT_COMPARABLE", "NOT_EVALUABLE", "FAILED"
})
FORBIDDEN_SELECTION_KEYS = frozenset({"winner", "selected", "promoted", "rank", "score"})


def _strings(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def build_invariance_contract(
    *,
    contract_id: str,
    invariant_dimensions: Sequence[str],
    nuisance_dimensions: Sequence[str] = (),
    non_invariant_dimensions: Sequence[str] = (),
) -> dict:
    cid = str(contract_id).strip()
    invariant = _strings(invariant_dimensions)
    nuisance = _strings(nuisance_dimensions)
    non_invariant = _strings(non_invariant_dimensions)
    if not cid or not invariant:
        raise PRSCContractError("PRSC_INVARIANCE_CONTRACT_INVALID")
    if (set(invariant) & set(nuisance)) or (set(invariant) & set(non_invariant)) or (set(nuisance) & set(non_invariant)):
        raise PRSCContractError("PRSC_INVARIANCE_DIMENSION_COLLISION")
    payload = {
        "schema": "ovc-prsc-invariance-contract/v0.1",
        "contract_id": cid,
        "invariant_dimensions": list(invariant),
        "nuisance_dimensions": list(nuisance),
        "non_invariant_dimensions": list(non_invariant),
        "selection_effect": "NONE",
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def build_representation_challenge_pack(
    *,
    pack_id: str,
    base_representation_ref: str,
    invariance_contract_ref: str,
    challengers: Sequence[Mapping[str, object]],
) -> dict:
    pid = str(pack_id).strip()
    base = str(base_representation_ref).strip()
    contract = str(invariance_contract_ref).strip()
    if not pid or not base or not contract or not challengers:
        raise PRSCContractError("PRSC_REPRESENTATION_PACK_INVALID")
    normalized: list[dict] = []
    seen: set[str] = set()
    for row in challengers:
        bad = FORBIDDEN_SELECTION_KEYS & {str(key).lower() for key in row}
        if bad:
            raise PRSCContractError(f"PRSC_REPRESENTATION_HIDDEN_SELECTION:{','.join(sorted(bad))}")
        challenger_id = str(row.get("challenger_id", "")).strip()
        representation_ref = str(row.get("representation_ref", "")).strip()
        method_pack_ref = str(row.get("method_pack_ref", "")).strip()
        if not challenger_id or not representation_ref or not method_pack_ref or challenger_id in seen:
            raise PRSCContractError("PRSC_REPRESENTATION_CHALLENGER_INVALID")
        seen.add(challenger_id)
        normalized.append({
            "challenger_id": challenger_id,
            "representation_ref": representation_ref,
            "method_pack_ref": method_pack_ref,
            "authority_effect": "NONE",
        })
    payload = {
        "schema": "ovc-prsc-representation-challenge-pack/v0.1",
        "pack_id": pid,
        "base_representation_ref": base,
        "invariance_contract_ref": contract,
        "challengers": normalized,
        "declared_challenger_count": len(normalized),
        "selection_policy": "NO_WINNER",
        "base_representation_immutable": True,
        "sri_scientific_authority": "NONE",
        "authority_effect": "NONE",
    }
    payload["semantic_sha256"] = canonical_sha256(payload)
    return payload


def build_population_crosswalk(*, base_unit_ids: Iterable[str], challenger_rows: Sequence[Mapping[str, object]]) -> dict:
    base_ids = _strings(base_unit_ids)
    if not base_ids:
        raise PRSCContractError("PRSC_CROSSWALK_EMPTY_BASE")
    rows: dict[str, dict] = {}
    for row in challenger_rows:
        base_id = str(row.get("base_unit_id", "")).strip()
        state = str(row.get("status", "")).strip().upper()
        targets = _strings(row.get("challenger_unit_ids", ()))
        if base_id not in set(base_ids) or base_id in rows or state not in CROSSWALK_STATES:
            raise PRSCContractError("PRSC_CROSSWALK_ROW_INVALID")
        if state in {"MATCH", "SPLIT", "MERGE"} and not targets:
            raise PRSCContractError("PRSC_CROSSWALK_TARGET_REQUIRED")
        if state in {"NOT_COMPARABLE", "NOT_EVALUABLE", "FAILED"} and targets:
            raise PRSCContractError("PRSC_CROSSWALK_NON_EVALUABLE_TARGET_FORBIDDEN")
        rows[base_id] = {
            "base_unit_id": base_id,
            "challenger_unit_ids": list(targets),
            "status": state,
        }
    missing = sorted(set(base_ids) - set(rows))
    if missing:
        raise PRSCContractError(f"PRSC_CROSSWALK_ACCOUNTING_MISSING:{','.join(missing)}")
    payload = {
        "schema": "ovc-prsc-population-crosswalk/v0.1",
        "base_unit_ids": list(base_ids),
        "rows": [rows[base_id] for base_id in base_ids],
        "complete_accounting": True,
        "identity_claim": False,
        "silent_drop": False,
        "authority_effect": "NONE",
    }
    payload["crosswalk_id"] = canonical_sha256(payload)
    return payload


def directional_correspondence(
    source_memberships: Mapping[str, Sequence[str]],
    target_memberships: Mapping[str, Sequence[str]],
    *,
    direction: str = "SOURCE_TO_TARGET",
) -> dict:
    if not source_memberships or not target_memberships:
        raise PRSCContractError("PRSC_CORRESPONDENCE_MEMBERSHIPS_REQUIRED")
    targets = {str(key): set(map(str, values)) for key, values in target_memberships.items()}
    records: list[dict] = []
    for source_id in sorted(source_memberships):
        source = set(map(str, source_memberships[source_id]))
        overlaps = [(len(source & members), target_id) for target_id, members in targets.items()]
        best = max((count for count, _ in overlaps), default=0)
        best_ids = sorted(target_id for count, target_id in overlaps if count == best and count > 0)
        if not best_ids:
            records.append({"source_id": str(source_id), "status": "UNMATCHED", "target_ids": [], "overlap_count": 0})
            continue
        if len(best_ids) > 1:
            records.append({"source_id": str(source_id), "status": "AMBIGUOUS", "target_ids": best_ids, "overlap_count": best})
            continue
        target_id = best_ids[0]
        target = targets[target_id]
        if source == target:
            status = "EXACT_CORRESPONDENCE"
        elif source < target:
            status = "SOURCE_MERGES_INTO_TARGET"
        elif target < source:
            status = "SOURCE_SPLITS_ACROSS_TARGET_VIEW"
        else:
            status = "PARTIAL_OVERLAP"
        records.append({"source_id": str(source_id), "status": status, "target_ids": [target_id], "overlap_count": best})
    payload = {
        "schema": "ovc-prsc-representation-correspondence/v0.1",
        "direction": str(direction),
        "records": records,
        "identity_claim": False,
        "directional": True,
        "authority_effect": "NONE",
    }
    payload["correspondence_id"] = canonical_sha256(payload)
    return payload


def build_candidate_invariant_core(representations: Mapping[str, object]) -> dict:
    if not representations:
        raise PRSCContractError("PRSC_INVARIANT_CORE_REPRESENTATIONS_REQUIRED")
    evaluable: list[set[str]] = []
    accounting: list[dict] = []
    all_features: set[str] = set()
    incomplete = False
    for representation_id in sorted(representations):
        value = representations[representation_id]
        if isinstance(value, Mapping):
            status = str(value.get("status", "EVALUABLE")).upper()
            features = _strings(value.get("features", ()))
        else:
            status = "EVALUABLE"
            features = _strings(value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ())
        if status == "EVALUABLE":
            feature_set = set(features)
            evaluable.append(feature_set)
            all_features.update(feature_set)
        else:
            incomplete = True
        accounting.append({"representation_id": str(representation_id), "status": status, "feature_count": len(features)})
    if not evaluable:
        core: set[str] = set()
        state = "NOT_EVALUABLE"
        universal = False
    else:
        core = set.intersection(*evaluable)
        state = "PARTIAL_NOT_UNIVERSAL" if incomplete else "COMPLETE_UNIVERSAL_CORE"
        universal = not incomplete
    payload = {
        "schema": "ovc-prsc-candidate-invariant-core/v0.1",
        "state": state,
        "core": sorted(core),
        "shell": sorted(all_features - core),
        "representation_accounting": accounting,
        "universal_claim": universal,
        "selection_effect": "NONE",
        "authority_effect": "NONE",
    }
    payload["invariant_core_id"] = canonical_sha256(payload)
    return payload
