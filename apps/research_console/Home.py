from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from apps.research_console.shell import run_console


def load_represented_identity() -> dict[str, Any]:
    """Read only the already-authorised read-model identity for persistent shell context.

    RC-WP1-v0.3 does not consume nodes, health rows or other live projections.
    Missing or malformed identity fails to NOT_EVALUATED rather than stopping the fixture shell.
    """

    model_path = Path(os.environ.get("OVC_RESEARCH_READ_MODEL", "var/research_operations/read_model/current.json"))
    identity: dict[str, Any] = {
        "repository": "owenguobadia24s-collab/ovc-replay",
        "branch": os.environ.get("OVC_REPOSITORY_BRANCH", "main"),
        "source_commit": os.environ.get("OVC_SOURCE_COMMIT", "NOT_EVALUATED"),
        "read_model_sha256": "NOT_EVALUATED",
        "freshness": "READ_MODEL_IDENTITY_UNAVAILABLE",
    }
    if not model_path.is_file():
        return identity
    try:
        raw = json.loads(model_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        identity["freshness"] = "READ_MODEL_IDENTITY_INVALID"
        return identity
    identity["source_commit"] = str(raw.get("source_commit") or identity["source_commit"])
    identity["read_model_sha256"] = str(raw.get("logical_sha256") or "NOT_EVALUATED")
    identity["freshness"] = "IDENTITY_ONLY_FIXTURE_PRESENTATION"
    return identity


run_console(load_represented_identity())
