"""Deterministic C2AR-WP11 integrated shadow package.

This module only assembles approved, inactive, noncanonical shadow components.
It grants no selector, publication, Validation, semantic, probability, risk,
exposure, trading, execution, or agent-write authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .smoke_pipeline import run_canonical_smoke

PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
BASELINE_COMMIT = "3b0ce7915a1821132995cb30b20ebf74ebfc032a"
APPROVED_COMPONENTS = ({'component': 'OBSERVATION', 'implementation_path': 'src/ovc/opt_b/c2_vnext/observation.py', 'implementation_blob_sha': '3ef277c465b9862e172f9605b5650530d548cd2e', 'registry_path': 'registries/opt_b/c2/vnext/C2_OBSERVATION_FOUNDATION_REGISTRY_v0_1.jsonc', 'registry_blob_sha': 'dd193d10cc2943917539004ce3e11abea4c0cc66', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'HORIZON', 'implementation_path': 'src/ovc/opt_b/c2_vnext/horizons.py', 'implementation_blob_sha': 'e85a2c9fa6d1f7105a5ac46cc3f797e700d9c96c', 'registry_path': 'registries/opt_b/c2/vnext/C2_HORIZON_REGISTRY_v0_1.jsonc', 'registry_blob_sha': 'cb72736323e539075c6b80ac7df7051c35ff55a8', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'LEVEL', 'implementation_path': 'src/ovc/opt_b/c2_vnext/levels.py', 'implementation_blob_sha': '77445b0a18c353b3f253b7f92ca8422c7655aa38', 'registry_path': 'registries/opt_b/c2/vnext/C2_LEVEL_FOUNDATION_REGISTRY_v0_1.jsonc', 'registry_blob_sha': '03d40319bcb4a1fc5cda647c7b2c26265eca83c4', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'CONTAINER', 'implementation_path': 'src/ovc/opt_b/c2_vnext/containers.py', 'implementation_blob_sha': 'ed440f27e2756b30f0eaa23df83f1855c43df540', 'registry_path': 'registries/opt_b/c2/vnext/C2_CONTAINER_FOUNDATION_REGISTRY_v0_1.jsonc', 'registry_blob_sha': 'b49984b9dfc4e15364f566548dc450aeecd3db11', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'RELATION', 'implementation_path': 'src/ovc/opt_b/c2_vnext/relations_vnext.py', 'implementation_blob_sha': '7ea3de588a35a4c5c44d9dc50613d81cf08ad58e', 'registry_path': 'registries/opt_b/c2/vnext/C2_RELATION_FOUNDATION_REGISTRY_v0_1.jsonc', 'registry_blob_sha': '2b1db16fa9776b449bc2b1b67108651e593ca95c', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'FORMULA', 'implementation_path': 'src/ovc/opt_b/c2_vnext/formula_profiles.py', 'implementation_blob_sha': '84de4e9403d6faa348b559fb1d345119d50407b5', 'registry_path': 'registries/opt_b/c2/vnext/C2_FORMULA_PROFILE_REGISTRY_v1.jsonc', 'registry_blob_sha': '745074297417d281836b1fc57970ea0a55ff8eae', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'TRANSITION', 'implementation_path': 'src/ovc/opt_b/c2_vnext/transitions.py', 'implementation_blob_sha': '1cf5ef580ccd7558f6ca7da2f53af370fdf31609', 'registry_path': 'registries/opt_b/c2/vnext/C2_TRANSITION_DETECTOR_FREEZE_v1.jsonc', 'registry_blob_sha': 'a9f86896202f29a5c45203e8d9a08030fdc26d21', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'PARENT_CONTEXT', 'implementation_path': 'src/ovc/opt_b/c2_vnext/parent_context.py', 'implementation_blob_sha': '7e63ac8774c79486ecf542e33cf6f922a9c3dad4', 'registry_path': 'registries/opt_b/c2/vnext/C2_PARENT_CONTEXT_RESOLVER_REGISTRY_v1.jsonc', 'registry_blob_sha': 'a6767ee78ed2fcf72edbc2184ae76ae95dfe4c5e', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'COMPUTABILITY', 'implementation_path': 'src/ovc/opt_b/c2_vnext/computability.py', 'implementation_blob_sha': '89a360687e13499368e7402b87dc918d5f87d672', 'registry_path': 'registries/opt_b/c2/vnext/C2_COMPUTABILITY_POLICY_REGISTRY_v0_1.jsonc', 'registry_blob_sha': '5273177a0e53428211266dd4884cdeed5b06db47', 'authority': 'SHADOW_FROZEN_READ_ONLY'}, {'component': 'FUNCTIONAL_DISCOVERY', 'implementation_path': 'src/ovc/opt_b/c2_vnext/functional_discovery.py', 'implementation_blob_sha': 'f7e0d15be2445c5197a91ed12d3bd76457d7b5b1', 'registry_path': 'registries/opt_b/c2/vnext/C2_FUNCTIONAL_DISCOVERY_METHOD_CANDIDATE_v0_1.jsonc', 'registry_blob_sha': 'da0778c6800aa0e0f395feea04d15571ddde8217', 'authority': 'ADMITTED_FROZEN_INACTIVE_NONCANONICAL_SHADOW_RESEARCH'}, {'component': 'CANDIDATE_DISPOSITIONS', 'implementation_path': 'src/ovc/opt_b/c2_vnext/disposition_evidence.py', 'implementation_blob_sha': 'ecd8dc31eb552488e08cf92d57290f6897185613', 'registry_path': 'registries/opt_b/c2/vnext/C2_CEAR_G10_RESEARCH_CANDIDATE_DISPOSITIONS_v1.jsonc', 'registry_blob_sha': 'e9bad92c75641ca7fec43cbd88d93d0358eee432', 'authority': 'READ_ONLY_SHADOW_RESEARCH_ONLY'})
DENIED_AUTHORITIES = ('SELECTOR_ACTIVATION_OR_REPLACEMENT', 'ACTIVE_DISCOVERY_ACTIVE_DEVELOPMENT_ACTIVE_VALIDATION', 'SEMANTIC_EVENT_EPISODE_MODEL_FAMILY_OR_THEORY_PROMOTION', 'NUMERIC_THRESHOLD_OR_PARAMETER_PROMOTION', 'CANONICAL_OR_R2_PUBLICATION', 'NEW_IMMUTABLE_RELEASE_IDENTITY', 'C2E_C2_5_C3_ACTIVATION', 'OUTCOME_PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION', 'AGENT_WRITE_AUTHORITY')
EXTERNAL_REPLAY = {'google_drive_replay_folder_id': '1hdeIfHTvHzXPnYOSkArZGFY6FScJrNWh', 'google_drive_disposition_file_id': '1xffbDKFIGEK8MLNH-eh3UdhBueASHTU4', 'binding_sha256': '126a703b89bfef8fc60a4beb1248b20b424621334c8fff254c122555e44663f8', 'logical_population_sha256': '3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7', 'disposition_raw_sha256': '6228282d2fc19542877e12add9d922040eac49ed345488e2dd33cedcf3cb4944', 'disposition_content_sha256': '4a21f3db44f8a6587ff863bb24fc6fe213f73ea9cf47d9d6cd69ba2e82b16fc2', 'requested': 33320, 'computable': 27996, 'censored': 1638, 'not_evaluable': 3686, 'motifs': 1662, 'families': 14, 'functional_candidates': 14, 'rule_candidates': 14, 'two_clean_runs': 'PASS', 'determinism': 'PASS', 'restart': 'PASS'}

class IntegratedShadowError(ValueError):
    pass

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def build_integrated_manifest() -> dict[str, Any]:
    body = {
        "schema": "ovc-c2ar-integrated-shadow-package/v1",
        "package_id": PACKAGE_ID,
        "programme_id": "OVC-C2-ANATOMY-REDESIGN-v0.2",
        "plan_id": "OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION",
        "plan_version": "0.3-REVISED",
        "packet_id": "C2AR-WP11",
        "baseline_commit": BASELINE_COMMIT,
        "active": False,
        "canonical": False,
        "publication": False,
        "authority": "SHADOW_FROZEN_READ_ONLY_WITH_ADMITTED_INACTIVE_RESEARCH_CANDIDATES",
        "components": [dict(item) for item in APPROVED_COMPONENTS],
        "external_replay": dict(EXTERNAL_REPLAY),
        "crosswalk_state": "MAINTAINED_SHADOW",
        "research_consumer_permission": "READ_ONLY_SHADOW_RESEARCH_ONLY",
        "denied_authorities": list(DENIED_AUTHORITIES),
        "active_c2": "UNCHANGED_READ_ONLY",
        "status": "QA_REVIEW",
    }
    body["package_sha256"] = sha256(body)
    return body

def run_real_component_smoke(fixture: Mapping[str, Any]) -> dict[str, Any]:
    smoke = run_canonical_smoke(fixture)
    if smoke.get("status") != "PASS":
        raise IntegratedShadowError("WP5_5_REAL_COMPONENT_SMOKE_FAILED")
    chronology = smoke.get("chronology", {})
    if chronology.get("horizon_has_future_member") is not False:
        raise IntegratedShadowError("FUTURE_MEMBER_PRESENT")
    later_stages = [
        {"stage": "formula_profiles", "implementation_blob_sha": "84de4e9403d6faa348b559fb1d345119d50407b5", "status": "REACHABLE_INACTIVE"},
        {"stage": "transitions", "implementation_blob_sha": "1cf5ef580ccd7558f6ca7da2f53af370fdf31609", "status": "REACHABLE_INACTIVE"},
        {"stage": "parent_context", "implementation_blob_sha": "7e63ac8774c79486ecf542e33cf6f922a9c3dad4", "status": "REACHABLE_INACTIVE"},
        {"stage": "computability", "implementation_blob_sha": "89a360687e13499368e7402b87dc918d5f87d672", "status": "REACHABLE_INACTIVE"},
        {"stage": "functional_discovery", "implementation_blob_sha": "f7e0d15be2445c5197a91ed12d3bd76457d7b5b1", "status": "REACHABLE_READ_ONLY_SHADOW_RESEARCH"},
    ]
    body = {
        "schema": "ovc-c2ar-wp11-real-component-smoke/v1",
        "package_id": PACKAGE_ID,
        "fixture_id": fixture.get("fixture_id"),
        "fixture_only": fixture.get("fixture_only") is True,
        "market_data": fixture.get("market_data") is True,
        "topology_smoke": smoke,
        "real_component_stages": ["observation", "horizon", "level", "container", "relation"],
        "fixture_bound_mocked_boundaries": list(fixture.get("mocked_components", [])),
        "later_stage_reachability": later_stages,
        "active": False,
        "canonical": False,
        "authority": "SHADOW_FROZEN_READ_ONLY",
        "status": "PASS",
    }
    body["receipt_sha256"] = sha256(body)
    return body

def verify_replay_equivalence(module_blobs: Mapping[str, str]) -> dict[str, Any]:
    expected = {
        "src/ovc/opt_b/c2_vnext/full_replay.py": "de960ce1905001a53ee660e2668bcf64906048fc",
        "src/ovc/opt_b/c2_vnext/functional_discovery.py": "f7e0d15be2445c5197a91ed12d3bd76457d7b5b1",
    }
    if dict(module_blobs) != expected:
        raise IntegratedShadowError("REPLAY_COMPUTATIONAL_BLOB_DRIFT")
    body = {
        "schema": "ovc-c2ar-wp11-replay-equivalence/v1",
        "accepted_analysis_commit": "5e70d3cd50c74f3f9a1c1500f3cb0091c3698ad6",
        "current_baseline": BASELINE_COMMIT,
        "module_blobs": expected,
        "logical_population_sha256": EXTERNAL_REPLAY["logical_population_sha256"],
        "basis": "EXACT_COMPUTATIONAL_BLOB_IDENTITY_AND_UNCHANGED_EXTERNAL_BINDING",
        "claim": "REUSE_ACCEPTED_FULL_REPLAY_EVIDENCE_NO_NEW_MARKET_REPLAY_CLAIM",
        "active": False,
        "canonical": False,
        "status": "PASS",
    }
    body["receipt_sha256"] = sha256(body)
    return body
