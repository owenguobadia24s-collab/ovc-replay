from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..identity import CBSContractError, seal_object


def adapt_annotations(annotations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    for annotation in annotations:
        if annotation.get("role") != "REFERENCE_ONLY" or annotation.get("ground_truth") is not False:
            raise CBSContractError("CBS_OPERATOR_ANNOTATION_GROUND_TRUTH_FORBIDDEN")
    return seal_object({"schema":"ovc-cbs-operator-annotation-reference/v0.1",
        "annotations":[dict(item) for item in annotations],"fitted_target":False,"ground_truth":False,
        "authority_effect":"NONE"},id_field="annotation_reference_id")
