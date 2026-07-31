from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/research-operations-foundation-v0-4"
REQUIRED = [
    ROOT / "contracts/research_operations/v0_4/RO4_BOUNDARY_ANNOTATION_AND_FRICTION_CONTRACT_v0_1.md",
    ROOT / "contracts/research_operations/v0_4/RO4_APPEND_ONLY_SERVICE_BINDING_v0_1.md",
    ROOT / "src/ovc/research_operations/v0_4/annotation_friction_service.py",
    ROOT / "src/ovc/research_operations/v0_4/record_cli.py",
    ROOT / "src/ovc/cli.py",
    ROOT / "tests/research_operations/v0_4/test_ro4_g4_annotation_friction.py",
    ROOT / "fixtures/research_operations/v0_4/RO4_G4_SYNTHETIC_ASSURANCE_FIXTURE_v0_1.json",
    ROOT / "schemas/research_operations/v0_4/sequence_boundary_annotation_v0_1.schema.json",
    ROOT / "schemas/research_operations/v0_4/c2e_friction_record_v0_1.schema.json",
    ROOT / "schemas/research_operations/v0_4/prospective_sequence_review_v0_1.schema.json",
    ROOT / "schemas/research_operations/v0_4/ro4_append_only_record_envelope_v0_1.schema.json",
    ROOT / "schemas/research_operations/v0_4/signature_concentration_acknowledgement_v0_1.schema.json",
    ROOT / "registries/research_operations/v0_4/RO4_APPEND_AUTHORITY_v0_1.json",
    ROOT / "registries/research_operations/v0_4/RO4_G4_COMMAND_REGISTRY_v0_1.json",
    BASE / "ro4-wp4/RO4_WP4_IMPLEMENTATION_PACKET.json",
    BASE / "ro4-g4/RO4_G4_QA_PACKET.json",
    BASE / "ro4-g4/RO4_G4_GATE_PACKET.json",
    BASE / "ro4-g4/RO4_G4_CHANGED_FILE_INVENTORY.json",
]
EXPECTED_TYPES = {
    "RO4_SEQUENCE_BOUNDARY_ANNOTATION.v0.1",
    "RO4_C2E_FRICTION_RECORD.v0.1",
    "RO4_PROSPECTIVE_SEQUENCE_REVIEW.v0.1",
    "RO4_SIGNATURE_CONCENTRATION_ACKNOWLEDGEMENT.v0.1",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    if missing:
        raise SystemExit("MISSING_RO4_G4_FILES:" + ",".join(missing))

    authority = load(ROOT / "registries/research_operations/v0_4/RO4_APPEND_AUTHORITY_v0_1.json")
    if authority.get("enabled") is not False or authority.get("status") != "DISABLED_PENDING_RO4_G4":
        raise SystemExit("RO4_G4_PREAPPROVAL_APPEND_MUST_BE_DISABLED")
    if set(authority.get("accepted_record_types", [])) != EXPECTED_TYPES:
        raise SystemExit("RO4_G4_RECORD_ALLOWLIST_MISMATCH")
    if authority.get("console_write_state") != "PROHIBITED":
        raise SystemExit("RO4_G4_CONSOLE_WRITE_NOT_PROHIBITED")
    if authority.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise SystemExit("RO4_G4_VALIDATION_LOCK_NOT_PRESERVED")

    diversity = load(BASE / "ro4-wp3/RO4_G3_SIGNATURE_DIVERSITY_AUDIT.json")
    if diversity.get("full_population", {}).get("status") != "PASS":
        raise SystemExit("RO4_G4_DIVERSITY_NOT_PASS")
    if diversity.get("ro4_g4_acknowledgement_required") is not False:
        raise SystemExit("RO4_G4_UNRESOLVED_CONCENTRATION_ACKNOWLEDGEMENT")

    gate = load(BASE / "ro4-g4/RO4_G4_GATE_PACKET.json")
    if gate.get("operator_decision_required") is not True or gate.get("auto_ratifiable") is not False:
        raise SystemExit("RO4_G4_OPERATOR_BOUNDARY_FAILURE")
    if gate.get("proposed_authority_delta") != "BOUNDED_LOCAL_APPEND_ONLY_RESEARCH_EVIDENCE":
        raise SystemExit("RO4_G4_AUTHORITY_DELTA_FAILURE")
    if gate.get("status") not in {"GATE_READY_PENDING_FINAL_HEAD_CI", "GATE_READY"}:
        raise SystemExit("RO4_G4_GATE_STATUS_FAILURE")
    candidate = str(gate.get("candidate_commit"))
    if candidate != "PENDING_FINAL_HEAD_PIN" and not re.fullmatch(r"[0-9a-f]{40}", candidate):
        raise SystemExit("RO4_G4_CANDIDATE_PIN_INVALID")
    if gate.get("external_artifacts", {}).get("canonical_records_appended") != 0:
        raise SystemExit("RO4_G4_CANONICAL_RECORD_APPENDED_PREAPPROVAL")

    qa = load(BASE / "ro4-g4/RO4_G4_QA_PACKET.json")
    if qa.get("blocking_issues") or qa.get("recommendation") != "PASS":
        raise SystemExit("RO4_G4_QA_FAILURE")
    fixture = load(ROOT / "fixtures/research_operations/v0_4/RO4_G4_SYNTHETIC_ASSURANCE_FIXTURE_v0_1.json")
    if fixture.get("synthetic") is not True or fixture.get("operator_evidence") is not False:
        raise SystemExit("RO4_G4_FIXTURE_AUTHORITY_FAILURE")

    records_root = ROOT / "records/research_operations/ro4"
    if records_root.exists() and any(path.is_file() for path in records_root.rglob("*")):
        raise SystemExit("RO4_G4_CANONICAL_RECORD_BYTES_COMMITTED")
    forbidden = list(ROOT.rglob("*.sqlite")) + list(ROOT.rglob("*.db")) + list(ROOT.rglob("*.jsonl.gz"))
    forbidden = [path for path in forbidden if ".git" not in path.parts and "legacy" not in path.parts]
    if forbidden:
        raise SystemExit("RO4_G4_EXTERNAL_BYTES_COMMITTED:" + ",".join(str(p.relative_to(ROOT)) for p in forbidden))

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'ovc = "ovc.cli:main"' not in pyproject:
        raise SystemExit("RO4_G4_CLI_DISPATCH_NOT_BOUND")
    print("PASS: RO4-G4 packet is gate-ready, append-disabled, cutoff-safe, audited and operator-reserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
