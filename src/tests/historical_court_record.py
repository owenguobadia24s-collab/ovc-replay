"""Compatibility re-export for the repository test helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_HELPER = Path(__file__).resolve().parents[2] / "tests" / "historical_court_record.py"
_SPEC = importlib.util.spec_from_file_location("ovc_historical_court_record_helper", _HELPER)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load historical court-record helper: {_HELPER}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

text_at = _MODULE.text_at
json_at = _MODULE.json_at
names_at = _MODULE.names_at

__all__ = ["text_at", "json_at", "names_at"]
