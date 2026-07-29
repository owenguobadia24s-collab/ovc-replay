from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from apps.research_console.c1_projection_source import (
    load_c1_projection,
    projection_identity as c1_projection_identity,
)
from apps.research_console.ro2_projection_source import load_ro2_projection, projection_identity
from apps.research_console.shell import run_console


def load_represented_identity(c1_projection: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Load authorised local read-model, RO2 and RC-G4 C1 presentation identities.

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
        "c1_route_state": "ENABLED_LOCAL_READ_ONLY",
        "c1_availability": "NOT_EVALUATED",
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

    c1_source = dict(c1_projection or load_c1_projection())
    c1_identity = c1_projection_identity(c1_source)
    identity.update({f"c1_{key}": value for key, value in c1_identity.items()})
    identity["c1_route_state"] = str(c1_identity["route_state"])
    identity["c1_availability"] = str(c1_identity["availability"])
    if c1_identity["availability"] == "AVAILABLE":
        identity["freshness"] = "RC_G4_C1_ACCEPTED_LOCAL_READ_ONLY_PRESENTATION"
    return identity


_c1_projection = load_c1_projection()
run_console(load_represented_identity(_c1_projection), c1_projection=_c1_projection)
