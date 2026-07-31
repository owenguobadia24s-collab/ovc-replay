from __future__ import annotations

import sys
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "ro4":
        from ovc.research_operations.v0_4.record_cli import main as ro4_main
        return ro4_main(args[1:])
    from ovc.research_operations.cli import main as research_main
    return research_main(args)
