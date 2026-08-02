from __future__ import annotations

import copy
import json
from pathlib import Path

from ovc.research_operations.mta.registry import (
    RegistryValidationError,
    classify_attempt,
    load_registry_bundle,
    validate_amendment,
    validate_registry_bundle,
)

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    "contracts/research_operations/mta/OVC_MTA_CURRENT_FLOW_REGISTRY_CONTRACT_v0_1.md",
    "schemas/research_operations/mta/mta_registry_entry_v0_1.schema.json",
    "schemas/research_operations/mta/mta_registry_amendment_v0_1.schema.json",
    "registries/research_operations/mta/MTA_FLOW_OBJECT_REGISTRY_v0_1.json",
    "registries/research_operations/mta/MTA_METRIC_REGISTRY_v0_1.json",
    "registries/research_operations/mta/MTA_COMPUTABILITY_STATUS_REGISTRY_v0_1.json",
    "registries/research_operations/mta/MTA_REASON_CODE_REGISTRY_v0_1.json",
    "registries/research_operations/mta/MTA_MARKER_FUNCTION_REGISTRY_v0_1.json",
    "fixtures/research_operations/mta/MTA_WP1_REGISTRY_FIXTURES_v0_1.json",
]


def load(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object:{relative}")
    return value


def expect_error(action, marker: str) -> None:
    try:
        action()
    except RegistryValidationError as exc:
        assert marker in str(exc), (marker, str(exc))
    else:
        raise AssertionError(f"expected RegistryValidationError containing {marker}")


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    assert not missing, missing

    bundle = load_registry_bundle(ROOT)
    result = validate_registry_bundle(bundle)
    assert result["status"] == "PASS"
    assert result["authority_delta"] == "AUDIT_CLASSIFICATION_ONLY"
    assert result["entry_counts"] == {
        "FLOW_OBJECT": 16,
        "METRIC": 13,
        "COMPUTABILITY_STATUS": 11,
        "REASON_CODE": 21,
        "MARKER_FUNCTION": 8,
    }
    assert len(result["logical_sha256"]) == 64

    fixtures = load("fixtures/research_operations/mta/MTA_WP1_REGISTRY_FIXTURES_v0_1.json")
    for attempt in fixtures["valid_attempts"]:
        classified = classify_attempt(bundle, status=attempt["status"], reason_code=attempt["reason_code"])
        assert classified["status"] == attempt["status"]
    for attempt in fixtures["invalid_attempts"]:
        expect_error(
            lambda attempt=attempt: classify_attempt(
                bundle,
                status=attempt["status"],
                reason_code=attempt["reason_code"],
            ),
            attempt["expected_error"],
        )

    valid_amendment = fixtures["valid_amendment"]
    amendment_result = validate_amendment(valid_amendment)
    assert amendment_result["status"] == "PASS"
    assert amendment_result["material"] is True
    for invalid in fixtures["invalid_amendments"]:
        candidate = copy.deepcopy(valid_amendment)
        candidate.update(invalid["overrides"])
        expect_error(lambda candidate=candidate: validate_amendment(candidate), invalid["expected_error"])

    marker_registry = bundle["MARKER_FUNCTION"]
    assert marker_registry["authority_note"].endswith("every entry.")
    for entry in marker_registry["entries"]:
        assert entry["authority"]["semantic_promotion"] == "DENIED"
        assert entry["authority"]["selector_or_release_mutation"] == "DENIED"
        assert entry["source_lineage"][0]["path"].startswith("pull_request:202/")

    flow = {entry["name"]: entry for entry in bundle["FLOW_OBJECT"]["entries"]}
    assert flow["RO4 sequence window"]["status"] == "REFERENCE_ONLY"
    assert flow["OPT-B.C2E episode"]["status"] == "DEFERRED"
    assert flow["OPT-B.C2.5 event"]["status"] == "PROHIBITED"
    assert flow["OPT-B.C3 structural meaning"]["status"] == "PROHIBITED"

    contract = (ROOT / REQUIRED[0]).read_text(encoding="utf-8")
    for phrase in (
        "No missing or ambiguous result may be converted to `NOT_FIRED`",
        "c2_5_authority: DENIED",
        "A registry version is immutable",
        "RO4 objects remain separate references",
    ):
        assert phrase in contract

    entry_schema = load("schemas/research_operations/mta/mta_registry_entry_v0_1.schema.json")
    amendment_schema = load("schemas/research_operations/mta/mta_registry_amendment_v0_1.schema.json")
    assert entry_schema["additionalProperties"] is False
    assert amendment_schema["additionalProperties"] is False
    assert amendment_schema["allOf"][0]["then"]["properties"]["rerun_required"]["const"] is True

    print(json.dumps(result, sort_keys=True))
    print("MTA-WP1 registry validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
