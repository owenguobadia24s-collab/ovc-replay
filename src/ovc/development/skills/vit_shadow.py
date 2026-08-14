from __future__ import annotations

from dataclasses import asdict, dataclass

from ovc.development.identity import canonical_sha256


@dataclass(frozen=True)
class ShadowPrediction:
    programme_id: str
    packet_id: str
    candidate_ref: str
    predecessor_commit: str
    predecessor_tree: str
    predicted_result_tree: str
    predicted_receipt_id: str
    physical_write_performed_by_vit: bool = False

    @property
    def prediction_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class ShadowComparison:
    prediction_id: str
    actual_result_commit: str
    actual_result_tree: str
    tree_equal: bool
    mismatch_attributable_to_vit: bool
    complete_receipt_chain: bool
    physical_write_performed_by_vit: bool

    @property
    def comparison_id(self) -> str:
        return canonical_sha256(asdict(self))


def compare_shadow_prediction(prediction: ShadowPrediction, actual_result_commit: str, actual_result_tree: str, *, complete_receipt_chain: bool) -> ShadowComparison:
    equal = prediction.predicted_result_tree == actual_result_tree
    return ShadowComparison(prediction.prediction_id, actual_result_commit, actual_result_tree, equal, not equal, complete_receipt_chain, prediction.physical_write_performed_by_vit)


def q3_shadow_pass(comparisons: tuple[ShadowComparison, ...]) -> bool:
    return bool(comparisons) and all(c.tree_equal and not c.mismatch_attributable_to_vit and c.complete_receipt_chain and not c.physical_write_performed_by_vit for c in comparisons)
