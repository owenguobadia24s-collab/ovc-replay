from __future__ import annotations

from typing import Sequence

# Install the historical structured-v2 inventory compatibility verifier before
# importing the CORR3 runner, which reuses the governed CORR2 source verifier.
from . import pilot_corr2_review_closure_entry as _corr2_compat  # noqa: F401

# CORR2's original authority loader predates the exact court-record status written
# after the signed local re-review. Install the narrowly scoped CORR3 compatibility
# adapter before importing the runner; no direct CORR2 command behaviour changes.
from . import corr3_corr2_state_compat as _corr2_state_compat  # noqa: F401
from .pilot_corr3_review_closure import main as _corr3_main


def main(argv: Sequence[str] | None = None) -> int:
    return _corr3_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
