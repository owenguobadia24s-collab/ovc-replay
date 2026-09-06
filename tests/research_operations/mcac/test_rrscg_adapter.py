from __future__ import annotations

import pytest

from ovc.research_operations.mcac.contracts import MCACContractError
from ovc.research_operations.mcac.rrscg_adapter import adapt_rrscg_public_record

from .conftest import context, occurrence


def payload():
    ctx = context()
    return occurrence(ctx.left_coordinate, ctx.left_registry, "o", "2020-01-01T00:00:00Z", "2020-01-01T01:00:00Z").semantic_dict()


def test_public_rrscg_reference_adapts_without_authority_gain():
    result = adapt_rrscg_public_record(payload())
    assert result.authority_effect == "NONE"
    assert result.occurrence.owner_payload_ref == "OPAQUE_NOT_DEREFERENCEABLE"


@pytest.mark.parametrize("key", ["private_payload", "phase", "probability", "risk", "children"])
def test_private_or_semantic_fields_rejected(key):
    value = payload(); value[key] = "forbidden"
    with pytest.raises(MCACContractError, match="MCAC_RRSCG_PRIVATE_OR_SEMANTIC_FIELD_REJECTED"):
        adapt_rrscg_public_record(value)


def test_owner_payload_dereference_rejected():
    value = payload(); value["owner_payload_ref"] = "private/path"
    with pytest.raises(MCACContractError, match="MCAC_OWNER_PAYLOAD_DEREFERENCE_FORBIDDEN"):
        adapt_rrscg_public_record(value)
