"""LSIAC research-only, non-authoritative classification support.

This namespace performs deterministic source-census and inheritance-adjudication
conformance mechanics only. It creates no active market truth, selector or
candidate promotion, scientific or semantic-promotion authority, Validation or
publication authority, probability, risk, exposure, trading, execution authority,
or agent-write authority. Source-blocked and invalid states fail closed.
"""

from .pass1 import (
    build_pass1_classification_view,
    build_shared_locator_dependence_graph,
    load_source_passports,
)

__all__ = [
    "build_pass1_classification_view",
    "build_shared_locator_dependence_graph",
    "load_source_passports",
]
