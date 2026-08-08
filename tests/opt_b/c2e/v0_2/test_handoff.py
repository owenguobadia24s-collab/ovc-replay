import json
from pathlib import Path
import copy

from ovc.opt_b.c2e_v2.handoff import build_input_frame

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"


def test_handoff_is_deterministic_and_identity_rich():
    payload = json.loads(FIXTURE.read_text())
    first = build_input_frame(payload)
    second = build_input_frame(copy.deepcopy(payload))
    assert first == second
    assert first["frame_id"].startswith("C2E.FRAME.")
    assert first["logical_hash"] == second["logical_hash"]
    assert first["identity"]["observation_id"] == first["identity"]["c2_record_id"]
    assert first["source_binding"]["binding_status"] == "EXACT_READ_ONLY_SHADOW"
    assert first["authority"] == "INACTIVE_NONCANONICAL_BUILD_TEST_ONLY"
