"""C2E v0.2 conformance package.

Inactive, noncanonical build/test machinery only.  No source replay, selector,
publication, Validation, semantic, family, probability, risk, exposure or
execution authority is created by importing this package.
"""

from .handoff import C2EHandoffError, build_input_frame

__all__ = ["C2EHandoffError", "build_input_frame"]
