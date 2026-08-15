from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "registries/authority/DEFAULT_EXECUTION_SUBSTRATE.json"
GENERAL = ROOT / "registries/authority/DSAI3V_VIT_GENERAL_AUTHORITY_v0_1.json"


def test_default_substrate_uses_existing_general_authority_without_broadening() -> None:
    default = json.loads(DEFAULT.read_text(encoding="utf-8"))
    general = json.loads(GENERAL.read_text(encoding="utf-8"))

    assert default["status"] == "ACTIVE"
    assert default["substrate_id"] == general["authority_id"]
    assert default["routing_scope"]["required_authority_delta"] == "NONE"
    assert default["routing_scope"]["required_owner_authority"] == "ALREADY_AUTHORISED_BY_GOVERNING_PROGRAMME"
    assert default["execution_policy"]["physical_gateway"] == general["physical_gateway"]
    assert default["execution_policy"]["parallel_physical_merge"] is False
    assert default["execution_policy"]["stop_at_programme_owned_operator_required_boundary"] is True
    assert default["execution_policy"]["infer_or_expand_authority"] is False
    assert set(default["routing_scope"]["eligible_gate_classes"]) == set(general["allowed_gate_classes"])


def test_default_substrate_preserves_hard_non_authority_boundaries() -> None:
    default = json.loads(DEFAULT.read_text(encoding="utf-8"))
    joined = "\n".join(default["explicit_non_authority"])
    for marker in [
        "no scope expansion",
        "no GRT2-G3 activation",
        "no parallel physical merge",
        "no force-push or history rewrite",
    ]:
        assert marker in joined
