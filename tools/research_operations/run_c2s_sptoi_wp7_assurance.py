from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.spto.factorised_assurance import build_algorithmic_assurance_receipt


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(build_algorithmic_assurance_receipt(root), sort_keys=True, separators=(",", ":")))
