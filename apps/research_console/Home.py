from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from apps.research_console.ro2_projection_source import load_ro2_projection, projection_identity
from apps.research_console.shell import run_console


def load_represented_identity() -> dict[str, Any]:
    """Load the authorised read-model identity and accepted RO2-G3 projection identity.

    Missing or malformed sources fail to NOT_EVALUATED. Only bounded, local,
    read-only projection identity is admitted to the persistent shell context.
    """
    model_path = Path(os.environ.get("OVC_RESEARCH_READ_MODEL", "var/research_operations/read_model/current.json"))
    identity: dict[str, Any] = {
        "repository": "owenguobadia24s-collab/ovc-replay",
        "branch": os.environ.get("OVC_REPOSITORY_BRANCH", "main"),
        "source_commit": os.environ.get("OVC_SOURCE_COMMIT", "NOT_EVALUATED"),
        "read_model_sha256": "NOT_EVALUATED",
        "freshness": "READ_MODEL_IDENTITY_UNAVAILABLE",
    }
    if model_path.is_file():
        try:
            raw = json.loads(model_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            identity["freshness"] = "READ_MODEL_IDENTITY_INVALID"
        else:
            identity["source_commit"] = str(raw.get("source_commit") or identity["source_commit"])
            identity["read_model_sha256"] = str(raw.get("logical_sha256") or "NOT_EVALUATED")
            identity["freshness"] = "IDENTITY_ONLY_PRESENTATION"

    ro2_projection = load_ro2_projection()
    ro2_identity = projection_identity(ro2_projection)
    identity.update({f"ro2_{key}": value for key, value in ro2_identity.items()})
    if ro2_identity["availability"] == "AVAILABLE":
        identity["freshness"] = "RO2_G3_ACCEPTED_LOCAL_READ_ONLY_PRESENTATION"
    return identity


run_console(load_represented_identity())
