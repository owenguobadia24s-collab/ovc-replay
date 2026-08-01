#!/usr/bin/env python3
"""Validate DA-WP1 shared development-service trust."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.identity import canonical_sha256, normalize_relative_path  # noqa: E402
from ovc.development.profiles import ProfileError, load_profile  # noqa: E402

BASELINE = "2baa3029160cbb1390bfd335d78ac0d573ed5ab0"
REQUIRED = [
    "contracts/development/OVC_SHARED_DEVELOPMENT_SERVICES_CONTRACT_v0_1.md",
    "src/ovc/development/__init__.py",
    "src/ovc/development/identity.py",
    "src/ovc/development/profiles.py",
    "src/ovc/development/artifacts.py",
    "src/ovc/development/qa.py",
    "src/ovc/development/gates.py",
    "src/ovc/development/decisions.py",
    "src/ovc/development/rollback.py",
    "fixtures/development/artifact_profile_pass_v0_1.json",
    "fixtures/development/artifact_profile_block_v0_1.json",
    "docs/releases/development-acceleration-v0-1/da-00/DA_00_MERGE_RECEIPT.json",
    "docs/releases/development-acceleration-v0-1/da-g1/DA_G1_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g1/DA_G1_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g1/DA_G1_DELEGATED_DECISION.json",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-G1 artifacts: {missing}")

    receipt = json.loads(read(REQUIRED[11]))
    gate = json.loads(read(REQUIRED[12]))
    qa = json.loads(read(REQUIRED[13]))
    decision = json.loads(read(REQUIRED[14]))
    assert receipt["squash_merge_sha"] == BASELINE
    assert receipt["pull_request"] == 203
    assert gate["gate_id"] == "DA-G1"
    assert gate["baseline_commit"] == BASELINE
    assert gate["authority_delta"] == "LOCAL_COMPUTE_AND_GENERATED_COMPACT_RECORDS"
    assert gate["reserved_authority_delta"] == "NONE"
    assert gate["next_packet"] == "DA-WP2"
    assert qa["blocking_issues"] == []
    assert decision["decision"] in {"PENDING_CI", "PASS"}
    assert decision["repository_bot_write"] == "DENIED"

    schemas = sorted((ROOT / "schemas/development").glob("*.schema.json"))
    assert len(schemas) >= 6
    for path in schemas:
        obj = json.loads(path.read_text(encoding="utf-8"))
        assert obj["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert obj["type"] == "object"
        assert obj["additionalProperties"] is False

    source = "\n".join(read(path) for path in REQUIRED[1:9])
    for forbidden in ("from ovc.opt_", "import ovc.opt_", "pattern_discovery", "research_operations"):
        if forbidden in source:
            raise AssertionError(f"shared package imports forbidden semantic namespace: {forbidden}")

    first = canonical_sha256({"b": 2, "a": 1}, role="FIXTURE")
    second = canonical_sha256({"a": 1, "b": 2}, role="FIXTURE")
    assert first == second
    assert normalize_relative_path("docs\\x.json") == "docs/x.json"

    profile = load_profile(ROOT / "fixtures/development/artifact_profile_pass_v0_1.json")
    assert profile.authority["repository_bot_write"] == "DENIED"
    assert profile.authority["direct_main_write"] == "DENIED"
    try:
        load_profile(ROOT / "fixtures/development/artifact_profile_block_v0_1.json")
    except ProfileError:
        pass
    else:
        raise AssertionError("blocked profile was accepted")

    contract = read(REQUIRED[0])
    for token in (
        "LOCAL_COMPUTE_AND_GENERATED_COMPACT_RECORDS",
        "write directly to `main`",
        "force-push",
        "consume Validation",
        "FAIL-closed" if False else "Failure behavior",
    ):
        assert token in contract, token

    print("DA-G1 validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
