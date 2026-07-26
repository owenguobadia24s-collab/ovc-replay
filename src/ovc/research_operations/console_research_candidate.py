from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .console_research import ResearchContext, ResearchWorkspaceProjection, ResearchWorkspaceProjectionBuilder

SOURCE_SCHEMA = "ovc-research-console-research-source/v0.3"


def load_source_bundle(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != SOURCE_SCHEMA:
        raise ValueError(f"Unsupported Research source schema: {raw.get('schema')}")
    if not str(raw.get("source_commit") or "").strip():
        raise ValueError("Research source bundle requires source_commit")
    if not isinstance(raw.get("records"), list):
        raise ValueError("Research source bundle requires a records list")
    return raw


def build_candidate(path: Path, *, cutoff_mode: str | None = None) -> ResearchWorkspaceProjection:
    raw = load_source_bundle(path)
    context_raw = dict(raw.get("context", {}))
    if cutoff_mode is not None:
        context_raw["cutoff_mode"] = cutoff_mode
    context = ResearchContext(
        instrument=str(context_raw["instrument"]),
        release_id=str(context_raw["release_id"]),
        clock=str(context_raw["clock"]),
        price_side=str(context_raw["price_side"]),
        selected_time=str(context_raw["selected_time"]),
        cutoff_mode=str(context_raw.get("cutoff_mode", "PROSPECTIVE")),
    )
    return ResearchWorkspaceProjectionBuilder().build(
        source_commit=str(raw["source_commit"]),
        records=raw["records"],
        context=context,
    )
