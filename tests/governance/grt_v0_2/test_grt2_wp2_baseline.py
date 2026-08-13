from __future__ import annotations

import unittest

from ovc.programme_genesis.grt_v0_2.bootstrap import BootstrapValidationError
from ovc.programme_genesis.grt_v0_2.protocols import (
    B0_MEMBER_COUNT,
    B0_MEMBERSHIP_SHA256,
    SCANNER_IDENTITY,
    baseline_member_id,
    baseline_membership_sha256,
    validate_baseline_members,
    validate_debt_baseline,
)


class GRT2WP2BaselineTests(unittest.TestCase):
    def _synthetic_members(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for ordinal in range(1, B0_MEMBER_COUNT + 1):
            anomaly_id = f"GRT.ANOM.{ordinal:024x}"
            payload_hash = f"{ordinal:064x}"
            rows.append(
                {
                    "schema": "grt-baseline-member-record/v0.2",
                    "baseline_member_id": baseline_member_id(anomaly_id, payload_hash),
                    "ordinal": ordinal,
                    "original_GRT_anomaly": anomaly_id,
                    "original_anomaly_code": "SYNTHETIC_WP2_TEST_ONLY",
                    "original_subject_locator": "LEGACY:" + anomaly_id,
                    "payload_hash": payload_hash,
                    "original_scanner_identity": SCANNER_IDENTITY,
                    "mapped_finding_id": None,
                    "mapping_status": "PENDING_WP3_ARTIFACT_GRAPH",
                    "disposition": None,
                    "lineage_refs": [],
                }
            )
        return rows

    def test_exact_569_shape_is_required_but_does_not_substitute_for_b0(self) -> None:
        rows = self._synthetic_members()
        validate_baseline_members(rows)
        self.assertEqual(len(rows), 569)
        self.assertNotEqual(baseline_membership_sha256(rows), B0_MEMBERSHIP_SHA256)
        baseline = {
            "baseline_id": "B0",
            "source_commit": "100b3fa342c5dee7c96a7a4e5af9e80dac3ddfe4",
            "source_tree_hash": "91374c54bde0e0b61ac51705f6434d4f2b0d8417",
            "source_topology_sha256": "4120468ecb1c1f484ab073c851287706f4fb45ad0e99fc355b4624094bb795f2",
            "raw_warning_count": 569,
            "baseline_member_ids": [row["baseline_member_id"] for row in rows],
        }
        with self.assertRaisesRegex(BootstrapValidationError, "MEMBERSHIP_HASH_MISMATCH"):
            validate_debt_baseline(baseline, rows)

    def test_duplicate_original_payload_hash_fails_closed(self) -> None:
        rows = self._synthetic_members()
        rows[1]["payload_hash"] = rows[0]["payload_hash"]
        rows[1]["baseline_member_id"] = baseline_member_id(
            str(rows[1]["original_GRT_anomaly"]), str(rows[1]["payload_hash"])
        )
        with self.assertRaisesRegex(BootstrapValidationError, "PAYLOAD_HASH_COLLISION"):
            validate_baseline_members(rows)

    def test_ordinal_substitution_fails_closed(self) -> None:
        rows = self._synthetic_members()
        rows[0]["ordinal"] = 2
        with self.assertRaisesRegex(BootstrapValidationError, "ORDINAL_SEQUENCE_INVALID"):
            validate_baseline_members(rows)


if __name__ == "__main__":
    unittest.main()
