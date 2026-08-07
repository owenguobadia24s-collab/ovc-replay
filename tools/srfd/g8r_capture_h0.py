from __future__ import annotations

import json
import os
from pathlib import Path

from ovc.opt_b.srfd.capacity_v2 import capture_h0_environment, reference_component_profile


def main() -> int:
    output_root = Path(os.environ.get("G8R_H0_OUTPUT", "g8r-h0-evidence"))
    output_root.mkdir(parents=True, exist_ok=True)
    io_root = os.environ.get("RUNNER_TEMP") or os.environ.get("OVC_EXTERNAL_ARTIFACT_ROOT")
    h0 = capture_h0_environment(artifact_root=io_root)
    reference = reference_component_profile()
    (output_root / "H0_ENVIRONMENT_RECEIPT.json").write_text(
        json.dumps(h0, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (output_root / "REFERENCE_COMPONENT_PROFILE.json").write_text(
        json.dumps(reference, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(f"H0_ENVIRONMENT_FINGERPRINT={h0['environment_fingerprint']}")
    print(f"H0_LOGICAL_HASH={h0['logical_hash']}")
    print(f"REFERENCE_COMPONENT_LOGICAL_HASH={reference['logical_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
