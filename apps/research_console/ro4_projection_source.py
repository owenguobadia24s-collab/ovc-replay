from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ovc.research_operations.v0_4.console_projection import (
    ROUTE_STATE,
    RO4ProjectionDenied,
    validate_console_projection,
)


class RO4ProjectionSourceError(ValueError):
    pass


def load_disabled_projection(path: str | Path, *, schema_root: str | Path | None = None) -> dict[str, Any]:
    """Load one local projection without registering or enabling a Console route."""
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RO4ProjectionSourceError("RO4_DISABLED_PROJECTION_SOURCE_UNAVAILABLE") from exc
    validate_console_projection(payload, schema_root=schema_root)
    if payload.get("route_state") != ROUTE_STATE:
        raise RO4ProjectionDenied("RO4_ROUTE_ACTIVATION_DENIED_PENDING_RC_G5")
    return payload


def route_registration() -> None:
    """RO4-WP5 deliberately provides no route registration."""
    return None
