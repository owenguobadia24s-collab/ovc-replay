from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from ovc.research_operations.prospective_source import operator_replay_acceptance as replay

from . import pilot_discovery as pilot

CORRECTIVE_AUTHORITY_GATE = "C1C-G5"
CORRECTIVE_NEXT_GATE = "C1C-G5-CORRECTIVE-PILOT-REVIEW"
CORRECTIVE_PILOT_NAMESPACE = "PD.PILOT.GBPUSD.20260622_20260625.v2"
CORRECTIVE_ACTIVE_C2_RELEASE = "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2"
CORRECTIVE_C2_MANIFEST_ID = "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1"
CORRECTIVE_SELECTOR_ID = "SELECTOR.OPT-B.C2.GBPUSD.v2"
CORRECTIVE_BANNER = "PILOT_ONLY · NON_PROMOTABLE · TIME_GATED_REPLAY · GAPPED_SOURCE · C1C_CORRECTIVE_RERUN"

_ORIGINAL_LOAD_AUTHORITY = pilot.load_governed_authority
_ORIGINAL_VALUES = {
    "AUTHORITY_GATE": pilot.AUTHORITY_GATE,
    "NEXT_GATE": pilot.NEXT_GATE,
    "PILOT_NAMESPACE": pilot.PILOT_NAMESPACE,
    "ACTIVE_C2_RELEASE": pilot.ACTIVE_C2_RELEASE,
    "C2_MANIFEST_ID": pilot.C2_MANIFEST_ID,
    "SELECTOR_ID": pilot.SELECTOR_ID,
    "PILOT_BANNER": pilot.PILOT_BANNER,
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise pilot.PilotDiscoveryError(f"C1C_G5_CORRECTIVE_AUTHORITY_UNAVAILABLE:{path}") from exc
    if not isinstance(value, dict):
        raise pilot.PilotDiscoveryError(f"C1C_G5_CORRECTIVE_AUTHORITY_INVALID:{path}")
    return value


def apply_corrective_identity() -> None:
    pilot.AUTHORITY_GATE = CORRECTIVE_AUTHORITY_GATE
    pilot.NEXT_GATE = CORRECTIVE_NEXT_GATE
    pilot.PILOT_NAMESPACE = CORRECTIVE_PILOT_NAMESPACE
    pilot.ACTIVE_C2_RELEASE = CORRECTIVE_ACTIVE_C2_RELEASE
    pilot.C2_MANIFEST_ID = CORRECTIVE_C2_MANIFEST_ID
    pilot.SELECTOR_ID = CORRECTIVE_SELECTOR_ID
    pilot.PILOT_BANNER = CORRECTIVE_BANNER


def _require_fields(source: dict[str, Any], expected: dict[str, Any], code: str) -> None:
    for key, value in expected.items():
        if source.get(key) != value:
            raise pilot.PilotDiscoveryError(f"{code}:{key}")


def load_corrective_authority(repository_root: Path) -> dict[str, Any]:
    # C1C-G5 is a later, narrower authority that preserves the already approved
    # June source/replay/signing bindings while superseding only the downstream
    # C1/C2 lineage and isolated noncanonical pilot identity. Historical PD-WP5
    # packet status is deliberately not reopened or rewritten.
    historical_gate = _load_json(
        repository_root
        / "registries/research_operations/pattern_discovery/PD_G4B_PILOT_DISCOVERY_GATE_STATE_v0_1.json"
    )
    signing = _load_json(
        repository_root / "docs/releases/prospective-source-v0-1/rps-wp4/evidence/operator-signing-binding.json"
    )
    acceptance = _load_json(
        repository_root / "docs/releases/prospective-source-v0-1/rps-wp4/evidence/time-gated-replay-acceptance.json"
    )
    decision = _load_json(
        repository_root / "docs/releases/opt-b-c1-v2/corrective/C1C_G3_G4_G5_OPERATOR_DECISION.json"
    )
    transaction = _load_json(
        repository_root
        / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/C1C_G4_G5_COORDINATED_SELECTOR_TRANSACTION.json"
    )
    receipt = _load_json(
        repository_root
        / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/C1C_G5_C2_V2_REMOTE_VERIFICATION_RECEIPT.json"
    )
    c1_selectors = (
        repository_root / "registries/opt_b/c1/C1_ACTIVE_SELECTORS.yaml"
    ).read_text(encoding="utf-8")
    c2_selectors = (
        repository_root / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml"
    ).read_text(encoding="utf-8")

    _require_fields(
        historical_gate,
        {
            "gate_id": "PD-G4B",
            "gate_status": "APPROVED",
            "decision": "PASS",
            "research_role": pilot.RESEARCH_ROLE,
            "operation_mode": pilot.OPERATION_MODE,
            "source_slice_id": pilot.SLICE_ID,
            "source_manifest_sha256": pilot.SOURCE_MANIFEST_SHA256,
            "compute_run_id": pilot.RUN_ID,
            "output_manifest_sha256": pilot.OUTPUT_MANIFEST_SHA256,
            "source_binding_id": pilot.BINDING_ID,
            "signed_replay_acceptance_id": pilot.ACCEPTANCE_ID,
            "signing_binding_id": pilot.SIGNING_BINDING_ID,
            "operator_id": pilot.OPERATOR_ID,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
        },
        "HISTORICAL_PD_G4B_BINDING_MISMATCH",
    )
    _require_fields(
        signing,
        {
            "signing_binding_id": pilot.SIGNING_BINDING_ID,
            "binding_id": pilot.BINDING_ID,
            "run_id": pilot.RUN_ID,
            "source_slice_id": pilot.SLICE_ID,
            "operator_id": pilot.OPERATOR_ID,
            "algorithm": "ED25519",
            "signature_namespace": replay.SIGNATURE_NAMESPACE,
        },
        "SIGNING_BINDING_MISMATCH",
    )
    _require_fields(
        acceptance,
        {
            "acceptance_id": pilot.ACCEPTANCE_ID,
            "binding_id": pilot.BINDING_ID,
            "run_id": pilot.RUN_ID,
            "source_slice_id": pilot.SLICE_ID,
            "source_manifest_sha256": pilot.SOURCE_MANIFEST_SHA256,
            "output_manifest_sha256": pilot.OUTPUT_MANIFEST_SHA256,
            "operation_mode": pilot.OPERATION_MODE,
            "operator_id": pilot.OPERATOR_ID,
            "signing_binding_id": pilot.SIGNING_BINDING_ID,
            "acceptance": "ACCEPTED_FOR_TIME_GATED_REPLAY_ONLY",
        },
        "REPLAY_ACCEPTANCE_MISMATCH",
    )

    gates = {
        str(item.get("gate_id")): item
        for item in decision.get("approved_gates", ())
        if isinstance(item, dict)
    }
    gate = gates.get("C1C-G5")
    if decision.get("decision") != "PASS" or not gate:
        raise pilot.PilotDiscoveryError("C1C_G5_OPERATOR_PASS_UNAVAILABLE")
    if gate.get("authority_delta") != (
        "DETERMINISTIC_C2_V2_IDENTITY_REPLAY_PUBLICATION_COORDINATED_SELECTOR_REPLACEMENT_"
        "AND_NONCANONICAL_PILOT_SUPERSESSION_RERUN"
    ):
        raise pilot.PilotDiscoveryError("C1C_G5_OPERATOR_SCOPE_MISMATCH")
    if transaction.get("status") != "APPROVED_MATERIALISED_EFFECTIVE_ON_MAIN_MERGE":
        raise pilot.PilotDiscoveryError("C1C_G5_SELECTOR_TRANSACTION_NOT_MATERIALISED")
    if receipt.get("status") != "PASS_C2_V2_IDENTITY_REPLAY_PUBLICATION_FULL_REMOTE_BYTE_VERIFICATION":
        raise pilot.PilotDiscoveryError("C1C_G5_C2_V2_REMOTE_VERIFICATION_NOT_PASS")
    if receipt.get("semantic_state_drift_count") != 0 or receipt.get("semantic_transition_drift_count") != 0:
        raise pilot.PilotDiscoveryError("C1C_G5_C2_V2_SEMANTIC_DRIFT")
    if CORRECTIVE_ACTIVE_C2_RELEASE not in c2_selectors or CORRECTIVE_C2_MANIFEST_ID not in c2_selectors:
        raise pilot.PilotDiscoveryError("C1C_G5_C2_V2_SELECTOR_NOT_EFFECTIVE")
    for required in (
        "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2",
        "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2",
        "C1.IMPLEMENTATION.v0.2",
    ):
        if required not in c1_selectors:
            raise pilot.PilotDiscoveryError(f"C1C_G5_C1_V2_SELECTOR_MISMATCH:{required}")

    return {
        "gate": historical_gate,
        "signing": signing,
        "acceptance": acceptance,
        "corrective": {
            "gate_id": CORRECTIVE_AUTHORITY_GATE,
            "next_gate": CORRECTIVE_NEXT_GATE,
            "pilot_namespace": CORRECTIVE_PILOT_NAMESPACE,
            "active_c2_release": CORRECTIVE_ACTIVE_C2_RELEASE,
            "c2_manifest_id": CORRECTIVE_C2_MANIFEST_ID,
            "selector_id": CORRECTIVE_SELECTOR_ID,
            "source_binding_preserved": pilot.BINDING_ID,
            "source_compute_run_preserved": pilot.RUN_ID,
            "canonical_append": "DENIED",
            "promotion_eligibility": "NON_PROMOTABLE",
        },
    }


def configure() -> None:
    apply_corrective_identity()
    pilot.load_governed_authority = load_corrective_authority


def main(argv: Sequence[str] | None = None) -> int:
    configure()
    return pilot.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
