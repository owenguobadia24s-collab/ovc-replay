from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.mta.c2_translation_audit import validate_reference, validate_sequence_fixture

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = "docs/releases/market-translation-audit-v0-2/mta-g3/MTA_WP3_C2_TRANSLATION_AUDIT_REFERENCE.json"
FIXTURE = "fixtures/research_operations/mta/MTA_WP3_C2_TRANSLATION_FIXTURE_v0_1.json"


def load(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(relative)
    return value


def main() -> int:
    required = [
        "contracts/research_operations/mta/OVC_MTA_C2_TRANSLATION_AUDIT_CONTRACT_v0_1.md",
        "schemas/research_operations/mta/mta_c2_translation_audit_v0_1.schema.json",
        REFERENCE,
        FIXTURE,
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, missing

    result = validate_reference(load(REFERENCE))
    assert result["status"] == "PASS"
    assert result["c2_states_total"] == 9420
    assert result["c2_transitions_total"] == 7345
    assert result["accepted_c2_ids_reconstructed"] == 16765
    assert result["external_artifact_sha256"] == "77474a18ccec38e5a3495cbf6af89542d32ea891229a0df208f75f4b124e2158"

    fixture_result = validate_sequence_fixture(load(FIXTURE))
    assert fixture_result == {"status": "PASS", "states": 2, "transitions": 1}

    contract = (ROOT / required[0]).read_text(encoding="utf-8")
    for phrase in (
        "Every accepted C2 state ID",
        "Every accepted C2 transition ID",
        "PARENT_RANGE",
        "MTA-G3 passes only when",
        "MTA-A3",
    ):
        assert phrase in contract

    print(json.dumps(result, sort_keys=True))
    print("MTA-WP3 C2 translation audit validation PASS_WITH_MATERIAL_FINDINGS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
