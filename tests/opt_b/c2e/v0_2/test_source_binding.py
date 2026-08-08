import json
from pathlib import Path
import pytest

from ovc.opt_b.c2e_v2.handoff import C2EHandoffError, build_input_frame

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"


def test_source_binding_hash_is_exact():
    payload = json.loads(FIXTURE.read_text())
    payload["source_binding"]["c2ar_package_sha256"] = "0" * 64
    with pytest.raises(C2EHandoffError, match="C2AR_PACKAGE_HASH_MISMATCH"):
        build_input_frame(payload)
