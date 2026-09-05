"""Laboratory Scientific Inheritance & Accession governance-only helpers.

This namespace is research-only and non-authoritative. It does not grant active market,
selector, scientific-promotion, candidate/family/model/theory promotion, validation,
publication, probability, risk, exposure, trading, execution, or agent-write authority.
GEN0002 performs exact-source accounting and deterministic Pass-1 source-state
classification only; both fail closed on identity drift.
"""

from .gen0002 import audit_frozen_passport_subject_identity
from .pass1 import (
    build_pass1_classification_view,
    build_shared_locator_dependence_graph,
    build_virtual_view_identity,
    load_source_passports,
)

__all__ = [
    "audit_frozen_passport_subject_identity",
    "build_pass1_classification_view",
    "build_shared_locator_dependence_graph",
    "build_virtual_view_identity",
    "load_source_passports",
]
