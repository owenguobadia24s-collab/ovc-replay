from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from apps.research_console.c1_projection_source import (
    load_c1_projection,
    projection_identity as c1_projection_identity,
)
from apps.research_console.rc_g5_console import run_console
from apps.research_console.ro2_projection_source import load_ro2_projection, projection_identity
from apps.research_console.ro4_active_projection_source import (
    load_active_projection,
    projection_identity as c2_sequence_projection_identity,
)


def load_represented_identity(
    c1_projection: Mapping[str, Any] | None = None,
    c2_sequence_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load authorised local read-model, RO2, C1 and RC-G5 C2 sequence identities."""

    model_path = Path(os.environ.get("OVC_RESEARCH_READ_MODEL", "var/research_operations/read_model/current.json"))
    identity: dict[str, Any] = {
        "repository": "owenguobadia24s-collab/ovc-replay",
        "branch": os.environ.get("OVC_REPOSITORY_BRANCH", "main"),
        "source_commit": os.environ.get("OVC_SOURCE_COMMIT", "NOT_EVALUATED"),
        "read_model_sha256": "NOT_EVALUATED",
        "freshness": "READ_MODEL_IDENTITY_UNAVAILABLE",
        "c1_route_state": "ENABLED_LOCAL_READ_ONLY",
        "c1_availability": "NOT_EVALUATED",
        "c2_sequence_route_state": "ENABLED_LOCAL_READ_ONLY",
        "c2_sequence_availability": "NOT_EVALUATED",
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

    c2_source = dict(c2_sequence_projection or load_active_projection())
    c2_identity = c2_sequence_projection_identity(c2_source)
    identity.update({f"c2_sequence_{key}": value for key, value in c2_identity.items()})
    identity["c2_sequence_route_state"] = str(c2_identity["route_state"])
    identity["c2_sequence_availability"] = str(c2_identity["availability"])
    if c2_identity["availability"] == "AVAILABLE":
        identity["freshness"] = "RC_G5_C2_SEQUENCE_ACCEPTED_LOCAL_READ_ONLY_PRESENTATION"
    return identity


_c1_projection = load_c1_projection()
_c2_sequence_projection = load_active_projection()
run_console(
    load_represented_identity(_c1_projection, _c2_sequence_projection),
    c1_projection=_c1_projection,
    c2_sequence_projection=_c2_sequence_projection,
)
