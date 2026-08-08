"""C2E v0.2 conformance shadow-only package.

This namespace has no active market/C2E authority.  It is inactive and
noncanonical build/test machinery only.  Importing it cannot change a selector,
run real-source replay, publish, consume Validation, promote family/semantic
state, or create probability, risk, exposure, trading or execution authority.
"""

from .handoff import C2EHandoffError, build_input_frame

__all__ = ["C2EHandoffError", "build_input_frame"]
