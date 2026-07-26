from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.research_console.shell import (
    configure_page,
    render_active_route,
    render_footer,
    render_header,
    render_navigation,
)


def load_runtime_context() -> dict[str, Any]:
    """Read only the already-authorised v0.1 model identity for shell context.

    RC-WP1 route contents remain fixtures. This function does not traverse source
    files, build v0.2 projections, or interpret research objects.
    """

    model_path = Path(
        os.environ.get(
            "OVC_RESEARCH_READ_MODEL",
            "var/research_operations/read_model/current.json",
        )
    )
    context: dict[str, Any] = {
        "source_commit": os.environ.get("OVC_SOURCE_COMMIT", "NOT_EVALUATED"),
        "read_model_sha256": "NOT_EVALUATED",
        "built_at_utc": "NOT_RECORDED",
        "model_status": "MISSING",
        "model_path": str(model_path),
    }
    if not model_path.is_file():
        return context

    try:
        raw = json.loads(model_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        context["model_status"] = "BLOCK"
        return context

    context.update(
        {
            "source_commit": raw.get("source_commit", context["source_commit"]),
            "read_model_sha256": raw.get("logical_sha256", "NOT_EVALUATED"),
            "built_at_utc": raw.get("built_at_utc", "NOT_RECORDED"),
            "model_status": "PASS"
            if raw.get("source_commit") and raw.get("logical_sha256")
            else "INCOMPLETE",
        }
    )
    return context


def main() -> None:
    configure_page()
    route_id, fixture_mode = render_navigation()
    context = load_runtime_context()
    render_header(context)
    render_active_route(route_id, fixture_mode)
    render_footer()


if __name__ == "__main__":
    main()
