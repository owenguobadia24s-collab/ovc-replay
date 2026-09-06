from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..identity import CBSContractError, canonical_id, seal_object


def build_method_pack(*, comparator_id: str, projection_id: str, support_manifest_id: str,
                      parameters: Mapping[str, Any], temporal_class: str, dependence_cluster: str,
                      exposure_classification: str) -> dict[str, Any]:
    if not comparator_id or not projection_id or not support_manifest_id or not dependence_cluster:
        raise CBSContractError("CBS_METHOD_PACK_INCOMPLETE")
    return seal_object({"schema":"ovc-cbs-method-pack/v0.1","comparator_id":comparator_id,
        "projection_id":projection_id,"support_manifest_id":support_manifest_id,
        "parameters":dict(parameters),"temporal_class":temporal_class,"dependence_cluster":dependence_cluster,
        "exposure_classification":exposure_classification,"authority_effect":"NONE"},id_field="method_pack_id")


def build_run_manifest(*, method_pack: Mapping[str, Any], source_population_id: str,
                       code_blobs: Mapping[str, str], capacity_receipt_id: str,
                       outputs: Sequence[Mapping[str, Any]], qa_state: str) -> dict[str, Any]:
    if qa_state not in {"PASS","FAIL","QUARANTINE","NOT_EVALUABLE"}:
        raise CBSContractError("CBS_RUN_QA_STATE_INVALID")
    output_ids=[str(item.get("output_id") or item.get("estimate_id") or canonical_id(item)) for item in outputs]
    return seal_object({"schema":"ovc-cbs-comparator-run-manifest/v0.1",
        "method_pack_id":method_pack["method_pack_id"],"source_population_id":source_population_id,
        "code_blobs":dict(sorted(code_blobs.items())),"capacity_receipt_id":capacity_receipt_id,
        "output_ids":output_ids,"output_logical_sha256":canonical_id({"output_ids":output_ids}),
        "qa_state":qa_state,"authority_effect":"NONE"},id_field="run_manifest_id")
