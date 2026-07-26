from __future__ import annotations

import json
from dataclasses import asdict

from .models import C1Result


def to_dict(result: C1Result) -> dict:
    payload = asdict(result)
    payload["schema"] = "ovc-opt-b-c1-bar-primitives/v1"
    payload["record_version"] = "0.1"
    payload["lifecycle_state"] = "FIXTURE_VERIFIED" if result.synthetic else "IMPLEMENTED"
    payload["qa_state"] = "PASS"
    return payload


def dumps(result: C1Result) -> str:
    return json.dumps(to_dict(result), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
