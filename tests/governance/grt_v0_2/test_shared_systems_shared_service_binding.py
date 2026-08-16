from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bindings import resolve_claims
from ovc.programme_genesis.grt_v0_2.serialization import canonical_json_v1_bytes


ROOT = Path(__file__).resolve().parents[3]
BINDING = ROOT / "registries/governance/grt_v0_2/shared_service_bindings/OVC_SHARED_SYSTEMS_V0_1_BINDING_REGISTRY.json"
DECISION = ROOT / "docs/programmes/grt-v0-2/shared-service-bindings/OVC_SHARED_SYSTEMS_V0_1_OPERATOR_DECISION.json"


def test_shared_systems_binding_is_single_owner_non_authoritative_projection() -> None:
    registry = json.loads(BINDING.read_text(encoding="utf-8"))
    decision = json.loads(DECISION.read_text(encoding="utf-8"))

    assert registry["schema"] == "grt-governance-binding-registry/v0.2"
    assert registry["authority_effect"] == "NONE_GOVERNANCE_PROJECTION"
    assert registry["active_enforcement"] == "NONE"
    assert registry["conflicts"] == []
    assert len(registry["shared_service_bindings"]) == 1

    binding = registry["shared_service_bindings"][0]
    assert binding["service_id"] == "OVC-SHARED-SYSTEMS-v0.1"
    assert binding["owner_programme_id"] == "OVC-SHARED-SYSTEMS-v0.1"
    assert binding["binding_status"] == "RESOLVED"
    assert binding["consumer_programmes"] == []
    assert binding["service_state"] == "INACTIVE_NOT_IMPLEMENTED"
    assert binding["authority_effect"] == "NONE_GOVERNANCE_PROJECTION"

    resolution = resolve_claims(
        [{
            "evidence_class": binding["evidence_class"],
            "source_id": binding["source_id"],
            "value": binding["owner_programme_id"],
        }],
        binding_kind="PROGRAMME_OWNER",
    )
    assert resolution["status"] == "RESOLVED"
    assert resolution["value"] == "OVC-SHARED-SYSTEMS-v0.1"

    assert decision["decision"] == "PASS"
    assert decision["authority_delta"] == "GOVERNANCE_OWNER_BINDING_ONLY"
    assert decision["implementation_authority"] == "NONE"
    assert decision["service_activation"] == "NONE"
    assert decision["genesis_crosswalk_effect"] == "NONE"


def test_shared_systems_binding_canonical_hash_is_exact() -> None:
    registry = json.loads(BINDING.read_text(encoding="utf-8"))
    claimed = registry.pop("canonical_hash")
    assert hashlib.sha256(canonical_json_v1_bytes(registry)).hexdigest() == claimed
