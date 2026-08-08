import json
from pathlib import Path
import pytest

from ovc.opt_b.c2e_v2.handoff import C2EHandoffError, build_input_frame

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"


def test_forbidden_downstream_field_fails_closed():
    payload = json.loads(FIXTURE.read_text())
    payload["evidence"]["family_id"] = "FAMILY.SHOULD.NOT.ENTER"
    with pytest.raises(C2EHandoffError, match="DEP_FORBIDDEN_FIELD_CONSUMED"):
        build_input_frame(payload)
