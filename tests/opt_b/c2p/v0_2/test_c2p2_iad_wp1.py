from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONTRACT = ROOT / "contracts/opt_b/c2p/v0_2/C2P2_IAD_IDENTITY_ANCHOR_EVIDENCE_CONTRACT_v0_1.md"
SCHEMA = ROOT / "schemas/opt_b/c2p/v0_2/c2p2_iad_identity_anchor_evidence_v0_1.schema.json"
REGISTRY = ROOT / "registries/opt_b/c2p/v0_2/research/C2P2_IAD_ANCHOR_ADMISSIBILITY_REGISTRY_v0_1.json"


def test_anchor_contract_denies_absence_as_positive_same() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "absence of invalidation" in text
    assert "never sufficient" in text
    assert "C2P2-IAD-GOWNER" in text
    assert "Candidate outputs are joined only after the anchor ledger has been frozen" in text


def test_anchor_schema_has_exact_scientific_label_domain_and_firewalls() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    props = schema["properties"]
    assert props["label"]["enum"] == ["POSITIVE_SAME", "POSITIVE_DIFFERENT", "AMBIGUOUS", "NOT_EVALUABLE"]
    assert props["candidate_independent"]["const"] is True
    assert props["future_information_used"]["const"] is False
    assert props["owner_contract"]["properties"]["identity_semantics_explicit"]["type"] == "boolean"


def test_admissibility_registry_requires_owner_semantics_and_reserves_owner_change() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert "EXPLICIT_OWNER_PERSISTENT_IDENTITY_SEMANTICS" in registry["positive_same"]["requires"]
    assert "NO_HARD_BREAK_OBSERVED" in registry["positive_same"]["forbidden_as_sufficient"]
    assert registry["candidate_outputs_may_define_anchor"] is False
    assert registry["c2p_durable_identity_may_be_owner_ground_truth"] is False
    assert registry["owner_contract_extension_if_needed"] == "OPERATOR_REQUIRED_C2P2_IAD_GOWNER"
    assert registry["fresh_real_source_execution"] == "FORBIDDEN_UNTIL_C2P2_IAD_GREAL"
