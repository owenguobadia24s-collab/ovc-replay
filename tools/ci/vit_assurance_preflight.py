from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from ovc.development.skills.vit_assurance_decoupling import validate_aa0_reuse_authorization
from ovc.development.skills.vit_routing import validate_vit_lineage_record

LINEAGE = re.compile(r"(?im)^VIT-Lineage-B64:\s*([A-Za-z0-9_\-=]+)\s*$")
REUSE = re.compile(r"(?im)^VIT-AA0-Reuse-B64:\s*([A-Za-z0-9_\-=]+)\s*$")


def _decode(marker: re.Pattern[str], body: str, label: str) -> Mapping[str, Any] | None:
    match = marker.search(body)
    if not match:
        return None
    token = match.group(1)
    token += "=" * ((4 - len(token) % 4) % 4)
    try:
        value = json.loads(base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{label}_INVALID_ENCODING:{exc}") from exc
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label}_INVALID_OBJECT")
    return value


def _write_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    print(f"OVC_VIT_ASSURANCE_{name.upper()}={value}")


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name != "pull_request":
        sha = os.environ.get("GITHUB_SHA", "NON_PR")
        _write_output("aa0_identity", sha)
        _write_output("generation_id", sha)
        _write_output("pip_id", sha)
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "NON_PULL_REQUEST")
        return 0

    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    pr = event.get("pull_request") or {}
    body = str(pr.get("body") or "")
    head_sha = str((pr.get("head") or {}).get("sha") or "")

    lineage_record = _decode(LINEAGE, body, "VIT_LINEAGE")
    reuse_record = _decode(REUSE, body, "VIT_AA0_REUSE")

    # Registered routing exceptions are handled by the preceding canonical routing
    # preflight. They never receive cross-generation AA0 reuse here.
    if lineage_record is None:
        if reuse_record is not None:
            raise RuntimeError("AA0_REUSE_WITHOUT_VIT_LINEAGE")
        _write_output("aa0_identity", head_sha)
        _write_output("generation_id", head_sha)
        _write_output("pip_id", head_sha)
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "REGISTERED_EXCEPTION_OR_NO_LINEAGE")
        return 0

    lineage = validate_vit_lineage_record(lineage_record)
    _write_output("aa0_identity", lineage.pip_id)
    _write_output("generation_id", lineage.generation_id)
    _write_output("pip_id", lineage.pip_id)

    if reuse_record is None:
        _write_output("aa0_reuse_authorized", "false")
        _write_output("aa0_reuse_reason", "NO_REUSE_AUTHORIZATION")
        return 0

    validate_aa0_reuse_authorization(reuse_record, current_lineage=lineage_record)
    _write_output("aa0_reuse_authorized", "true")
    _write_output("aa0_reuse_reason", "PLACEMENT_ONLY_PIP_REUSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
