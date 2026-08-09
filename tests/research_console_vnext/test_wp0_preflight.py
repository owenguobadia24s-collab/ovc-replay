from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "research_console_vnext"
STATE = ROOT / "registries" / "implementation" / "research_console_vnext" / "OVC_RCN_STATE_v0_1.json"

def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_wp0_preflight_is_authority_neutral_and_stops_before_real_sources():
    value = _load(ART / "RCN_WP0_PREFLIGHT.json")
    assert value["status"] == "PASS"
    assert value["authority"]["authority_effect"] == "NONE"
    assert value["authority"]["real_source_route_exposure"] == "DENIED_UNTIL_RCN_G4"
    assert value["stop_boundary"] == "RCN-G3V"

def test_reuse_census_is_complete_for_frozen_console_tree():
    value = _load(ART / "RCN_REUSE_CENSUS_v0_1.json")
    paths = {row["path"] for row in value["entries"]}
    assert len(paths) == 24
    assert "Home.py" in paths and "shell.py" in paths and "repository_topology_surface.py" in paths
    assert all(row["disposition"] in {"REUSE_AS_DOMAIN_OR_APPLICATION_LOGIC", "EXTRACT_AND_REFACTOR", "SUPERSEDE", "HISTORICAL_ONLY"} for row in value["entries"])

def test_visual_target_hash_and_primary_canvas_contract():
    value = _load(ART / "RCN_VISUAL_TARGET_MANIFEST_v0_1.json")
    assert value["sha256"] == "6f2bbfcdbed1ebf6090b78f25e2f3d14bf7da334719864eb4f1f8a0be47e3257"
    assert [v["min_primary_canvas_height"] for v in value["supported_viewports"]] == [420, 300, 260]

def test_toolchain_lock_is_exact_and_self_identifying():
    value = _load(ART / "RCN_TOOLCHAIN_LOCK_v0_1.json")
    canonical = json.dumps(value["tools"], sort_keys=True, separators=(",", ":"))
    assert value["canonical_selection_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()

def test_programme_state_records_g0_pass_without_scientific_authority():
    value = _load(STATE)
    assert value["status"] == "APPROVED"
    assert value["packet_id"] == "RCN-WP0"
    assert value["next_packet"] == "RCN-WP1"
