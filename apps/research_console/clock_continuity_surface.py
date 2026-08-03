from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from ovc.research_operations.clock_continuity.review import build_read_model

REFERENCE=Path(__file__).resolve().parents[2]/"docs/releases/clock-continuity-review-v0-1/ccr-wp1/CCR_FULL_AUDIT_REFERENCE.json"

def load_clock_continuity_review() -> dict[str,Any]:
    return build_read_model(json.loads(REFERENCE.read_text(encoding="utf-8")))
