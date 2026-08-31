from __future__ import annotations

import json
import sys
from typing import Any

from ovc.research_operations.canonical import canonical_json_bytes

from .engine import C2CSMReferenceEngine, ReferenceEngineError
from .models import ReferenceBar


def replay_payload(payload: dict[str, Any]) -> dict[str, Any]:
    checkpoint = payload.get("checkpoint")
    engine = (
        C2CSMReferenceEngine.from_checkpoint(checkpoint)
        if checkpoint is not None
        else C2CSMReferenceEngine()
    )
    bars = payload.get("bars")
    if not isinstance(bars, list):
        raise ReferenceEngineError("bars must be a list")
    for row in bars:
        if not isinstance(row, dict):
            raise ReferenceEngineError("each bar must be an object")
        engine.step(ReferenceBar(**row))
    return engine.typed_output()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ReferenceEngineError("input must be an object")
        sys.stdout.buffer.write(canonical_json_bytes(replay_payload(payload)))
    except (ReferenceEngineError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"C2CSM_REFERENCE_REPLAY_ERROR: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
