import json
import tempfile
from pathlib import Path

import pytest

from ovc.research_operations.bcwt import (
    compile_ledger,
    compile_mechanical_origins,
    make_consequence_pack,
    make_join_manifest,
    make_run_receipt,
)
from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.storage import DraftStore, FrozenRecordStore, ResearchWriteService

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "research_operations" / "bcwt" / "v0_1"
EVENTS = json.loads((FIXTURES / "synthetic_events.json").read_text(encoding="utf-8"))
BARS = json.loads((FIXTURES / "synthetic_bars.json").read_text(encoding="utf-8"))
SOURCE = {
    "release_id": "SYNTH-R2",
    "instrument": "GBPUSD",
    "side": "BID",
    "clock": "15M",
    "provider": "SYNTHETIC",
    "role": "MECHANICAL_ASSURANCE",
}


def _build():
    origins = compile_mechanical_origins(EVENTS, reference_id="OVC-BCWT-BREF-0.1")
    pack = make_consequence_pack(source_binding=SOURCE, horizons=[1, 2, 3])
    join = make_join_manifest(
        reference_id="OVC-BCWT-BREF-0.1",
        origin_set_hash=canonical_sha256(origins),
        consequence_pack_id=pack["consequence_pack_id"],
        source_binding=SOURCE,
    )
    ledger = compile_ledger(origins=origins, bars=BARS, pack=pack, join=join)
    receipt = make_run_receipt(reference_id="OVC-BCWT-BREF-0.1", origins=origins, pack=pack, join=join, ledger=ledger)
    return origins, pack, join, ledger, receipt


def _draft(writes, record_type, payload):
    return writes.base_record(
        record_type=record_type,
        created_at="2026-09-13T12:00:00Z",
        cutoff="2026-09-13T12:00:00Z",
        operator_id="bcwt-r2-fixture",
        source_release_refs=[],
        payload=payload,
    )


def test_bcwt_records_use_existing_frozen_record_store_append_only():
    origins, pack, join, ledger, receipt = _build()
    records = [
        ("BCWT_B_TO_C_ORIGIN.v0.1", origins[0]),
        ("BCWT_CONSEQUENCE_MEASUREMENT_PACK.v0.1", pack),
        ("BCWT_OUTCOME_JOIN_MANIFEST.v0.1", join),
        ("BCWT_OUTCOME_RECORD.v0.1", ledger["records"][0]),
        ("BCWT_OUTCOME_LEDGER.v0.1", ledger),
        ("BCWT_MECHANICAL_RUN_RECEIPT.v0.1", receipt),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = FrozenRecordStore(root / "records")
        writes = ResearchWriteService(
            drafts=DraftStore(root / "drafts"), records=store, operator_id="bcwt-r2-fixture"
        )
        frozen = []
        for record_type, payload in records:
            item = writes.freeze_new(
                _draft(writes, record_type, payload),
                frozen_at="2026-09-13T12:00:01Z",
                action="bcwt.r2.fixture.freeze",
            )
            frozen.append(item)
            assert store.read(item["record_id"])["record_id"] == item["record_id"]
        with pytest.raises(FileExistsError):
            store.write(frozen[0])


def test_candidate_evaluation_admission_cannot_be_persisted_as_bcwt_origin():
    origins, _, _, _, _ = _build()
    origin = dict(origins[0])
    origin["candidate_generation_id_or_none"] = "cg"
    origin["candidate_occurrence_id_or_none"] = "occ"
    origin["candidate_evaluation_admission_id_or_none"] = "admit"
    origin["origin_role"] = "C_ADMITTED_SCIENTIFIC_ORIGIN"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        writes = ResearchWriteService(
            drafts=DraftStore(root / "drafts"),
            records=FrozenRecordStore(root / "records"),
            operator_id="bcwt-r2-fixture",
        )
        with pytest.raises(Exception):
            writes.freeze_new(
                _draft(writes, "BCWT_B_TO_C_ORIGIN.v0.1", origin),
                frozen_at="2026-09-13T12:00:01Z",
                action="bcwt.r2.fixture.forbidden",
            )


def test_scientific_join_role_cannot_be_persisted():
    _, _, join, _, _ = _build()
    bad = dict(join)
    bad["execution_role"] = "C_ADMITTED_SCIENTIFIC"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        writes = ResearchWriteService(
            drafts=DraftStore(root / "drafts"),
            records=FrozenRecordStore(root / "records"),
            operator_id="bcwt-r2-fixture",
        )
        with pytest.raises(Exception):
            writes.freeze_new(
                _draft(writes, "BCWT_OUTCOME_JOIN_MANIFEST.v0.1", bad),
                frozen_at="2026-09-13T12:00:01Z",
                action="bcwt.r2.fixture.forbidden",
            )
