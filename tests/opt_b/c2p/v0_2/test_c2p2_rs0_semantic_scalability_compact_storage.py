from __future__ import annotations

from pathlib import Path
import sqlite3

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime import _hash
from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_indexed import (
    EVIDENCE_CONTRACT_ID,
    NEGATIVE_COVERAGE_STORAGE_SCHEMA,
    materialize_outcome_result,
    run_indexed_empirical_runtime,
)


SPEC = {
    "candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
    "semantic_candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
    "activation_eligible": False,
}
DEPENDENCIES = {"entries": []}


def row(ordinal: int) -> dict:
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "source_record_id": f"COMPACT-{ordinal:04d}",
        "source_record_kind": "C2_LEVEL",
        "instrument": "GBPUSD",
        "side": "ASK",
        "clock": "15M",
        "first_valid_time": f"2024-01-01T00:{ordinal:02d}:00Z",
        "evaluation_cutoff": f"2024-01-01T00:{ordinal:02d}:00Z",
        "geometry_signature": {
            "horizon_id": "H15",
            "level_type": "SWING_HIGH",
            "value": f"1.25{ordinal:02d}",
            "origin": "COMPACT_STORAGE_TEST",
            "structural_depth": 1,
        },
        "relation_topology": ["REL-A"],
    }


def test_negative_coverage_is_physically_compact_and_public_certificate_is_reconstructed_exactly(tmp_path: Path) -> None:
    work = tmp_path / "compact"
    manifest = run_indexed_empirical_runtime(
        [row(i) for i in range(8)],
        SPEC,
        DEPENDENCIES,
        work_dir=work,
        checkpoint_cadence=2,
    )
    assert manifest["negative_coverage_storage_schema"] == NEGATIVE_COVERAGE_STORAGE_SCHEMA

    with sqlite3.connect(work / "runtime-indexed.sqlite3") as connection:
        columns = [record[1] for record in connection.execute("PRAGMA table_info(negative_coverage)")]
        assert columns == [
            "ordinal",
            "match_key",
            "assertion_total",
            "assertion_examined",
            "tracklet_total",
            "tracklet_examined",
            "global_blocker",
        ]
        assert "value_json" not in columns
        assert connection.execute("SELECT COUNT(*) FROM negative_coverage").fetchone()[0] == 8

    result = materialize_outcome_result(work)
    certificates = result["negative_coverage_certificates"]
    assert len(certificates) == 8
    for certificate in certificates:
        assert certificate["evidence_contract_id"] == EVIDENCE_CONTRACT_ID
        digest = certificate["coverage_certificate_sha256"]
        body = {key: value for key, value in certificate.items() if key != "coverage_certificate_sha256"}
        assert digest == _hash(body)
        assert certificate["claim"] == "ALL_OMITTED_COMPETITORS_FAIL_A_FROZEN_NECESSARY_PREDICATE_OR_CURRENT_GLOBAL_BLOCKER"
        assert certificate["audit_mode"] == "DETERMINISTIC_REPLAY_VERIFIABLE_NO_IMPOSSIBLE_PAIR_MATERIALISATION"

    last = certificates[-1]
    assert last["open_tracklets"]["scope_total"] == 7
    assert last["open_tracklets"]["examined"] == 0
    assert last["open_tracklets"]["pruned_by_necessary_key_or_global_blocker"] == 7
