from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_cers_ps_wp0_binds_exact_completed_pilot_and_plan_materialisation():
    b = load("docs/releases/development-skills-v0-3/cers-persistent-supervisor/wp0/CERS_PS_WP0_BASELINE_PACKET_v0_1.json")
    assert b["packet_id"] == "CERS-PS-WP0"
    assert b["gate_id"] == "CERS-PS-G0"
    p = b["completed_predecessor"]
    assert p["terminal_status"] == "CERS_IMPLEMENTED_QUALIFIED_LIVE_PILOT_PASS"
    assert p["merge_commit"] == "81faa31be2e59e47bc9784174f971c93a5a3a41c"
    assert p["physical_tree"] == "5faa522134abfae1749a13bb9b53ae51e8054ee7"
    assert p["transaction_id"] == "8e306f0506d1a2199777e267c5321425e97ff3b72a07ca9605a9ef04c47516f9"
    assert p["post_merge_completion_proof_id"] == "112fcfcec02c73b1b19d56d90c5965e45da9d2a7cc26d19706f8cd0816fde860"
    m = b["plan_ratification_materialisation"]
    assert m["merge_commit"] == "9fb87de746df6450f703dd0c2d0ac3be66947885"
    assert m["physical_tree"] == "5d97d40e559f0a20f57fcd8df59e8bc7ee4cb056"
    assert m["materialisation_receipt_id"] == "7f5cfc66652982f9019786994fdd9f48c2351bd8c3a1f2db4c4cedce20aa563d"
    assert m["packet_completion_receipt_id"] == "addf8a2f8e4af0dd10f5f95cfd83ce0ff382e260e61208e9c9247310959acb75"


def test_cers_ps_g0_pass_does_not_activate_persistent_dispatch():
    d = load("docs/releases/development-skills-v0-3/cers-persistent-supervisor/wp0/CERS_PS_G0_DECISION_v0_1.json")
    assert d["gate_class"] == "AUTO_RATIFIABLE"
    assert d["decision"] == "PASS_DELEGATED"
    assert d["authority_delta"] == "NONE"
    assert d["persistent_general_dispatch"] == "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION"
    assert d["post_pilot_dispatch_state"] == "DISABLE_NEW_DISPATCH"


def test_cers_ps_wp0_remains_preserved_as_preactivation_state_advances():
    state10 = load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_10.json")
    assert state10["supersedes_state"] == "OVC_DSAI3V_CERS_STATE_v0_9.json"
    assert state10["current_gate"] == "CERS-PS-G1"
    wp0 = next(row for row in state10["packet_register"] if row["packet_id"] == "CERS-PS-WP0")
    wp1 = next(row for row in state10["packet_register"] if row["packet_id"] == "CERS-PS-WP1")
    activation = next(row for row in state10["packet_register"] if row["packet_id"] == "CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION")
    assert wp0["status"] == "COMPLETED" and wp0["decision"] == "PASS_DELEGATED"
    assert wp1["status"] == "READY"
    assert activation["status"] == "PLANNED"
    assert activation["authority_required"] == "OPERATOR_REQUIRED"

    pointer = load("registries/implementation/dsai3v_cers_v0_1/CURRENT_STATE_POINTER.json")
    assert pointer["persistent_general_dispatch"] == "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION"
    assert pointer["post_pilot_dispatch_state"] == "DISABLE_NEW_DISPATCH"
    current = load(pointer["current_state"])
    assert current["plan_id"] == "OVC-DSAI3V-CERS-PERSISTENT-SUPERVISOR-ACTIVATION-PLAN-0.1-RATIFIED"
    assert current["persistent_general_dispatch"] == "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION"
    assert current["post_pilot_dispatch_state"] == "DISABLE_NEW_DISPATCH"
    assert current["packet_id"] in {
        "CERS-PS-WP1",
        "CERS-PS-WP2",
        "CERS-PS-WP3",
        "CERS-PS-WP4",
        "CERS-PS-WP5",
        "CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION",
    }
