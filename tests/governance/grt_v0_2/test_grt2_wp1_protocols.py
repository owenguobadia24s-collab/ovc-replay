from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import (
    BootstrapValidationError,
    load_json,
)
from ovc.programme_genesis.grt_v0_2.protocols import (
    validate_amendment_record,
    validate_historical_disposition_record,
    validate_override_record,
)


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "schemas/governance/grt_v0_2"
FIXTURES = ROOT / "fixtures/governance/grt_v0_2/wp1"


class GRT2WP1ProtocolTests(unittest.TestCase):
    def test_approved_amendment_requires_shadow_migration_and_operator_decision(self) -> None:
        schema = load_json(SCHEMAS / "constitution_amendment.schema.json")
        validate_amendment_record(
            load_json(FIXTURES / "valid_constitution_amendment.json"), schema
        )
        with self.assertRaisesRegex(
            BootstrapValidationError, "OPERATOR_DECISION_REQUIRED"
        ):
            validate_amendment_record(
                load_json(
                    FIXTURES
                    / "invalid_constitution_amendment_missing_operator.json"
                ),
                schema,
            )

    def test_override_is_exact_context_single_use_and_time_bounded(self) -> None:
        schema = load_json(SCHEMAS / "conformance_override.schema.json")
        validate_override_record(
            load_json(FIXTURES / "valid_conformance_override.json"), schema
        )
        with self.assertRaisesRegex(BootstrapValidationError, "EXPIRY_NOT_AFTER"):
            validate_override_record(
                load_json(
                    FIXTURES
                    / "invalid_conformance_override_expired_before_issue.json"
                ),
                schema,
            )

    def test_historical_disposition_over_five_percent_requires_independent_qa(self) -> None:
        schema = load_json(SCHEMAS / "historical_disposition.schema.json")
        validate_historical_disposition_record(
            load_json(
                FIXTURES / "valid_historical_disposition_enhanced_qa.json"
            ),
            schema,
        )
        with self.assertRaisesRegex(BootstrapValidationError, "ENHANCED_QA_REQUIRED"):
            validate_historical_disposition_record(
                load_json(
                    FIXTURES
                    / "invalid_historical_disposition_missing_enhanced_qa.json"
                ),
                schema,
            )

    def test_protocol_records_reject_unknown_fields(self) -> None:
        schema = load_json(SCHEMAS / "conformance_override.schema.json")
        record = load_json(FIXTURES / "valid_conformance_override.json")
        record["silent_waiver"] = True
        with self.assertRaisesRegex(BootstrapValidationError, "INSTANCE_ADDITIONAL"):
            validate_override_record(record, schema)


if __name__ == "__main__":
    unittest.main()
