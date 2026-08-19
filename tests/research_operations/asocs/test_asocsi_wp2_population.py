from datetime import datetime
from pathlib import Path
import hashlib, json
import gzip
import pytest

from ovc.research_operations.asocs.population import (
    ASOCSPopulationError,
    LATTICE_15M_ID,
    LATTICE_2H_ID,
    SOURCE_CLOCK_STATE,
    SOURCE_SIDE_STATE,
    materialize_population,
    render_source_native_svg,
)

HEADER = "Date,Time,Open,High,Low,Close,Volume\n"

def write(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "s.csv"
    p.write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return p

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def minute_rows(start: datetime, count: int, skip: set[int] | None = None) -> list[str]:
    from datetime import timedelta
    skip = skip or set()
    rows=[]
    for i in range(count):
        if i in skip: continue
        t=start+timedelta(minutes=i)
        rows.append(f"{t:%Y%m%d},{t:%H:%M:%S},1.1000,1.2000,1.0000,1.1500,{100+i}")
    return rows

def test_complete_15m_and_2h_require_exact_parent_membership(tmp_path: Path) -> None:
    p=write(tmp_path, minute_rows(datetime(2026,1,2), 120))
    result=materialize_population(p,tmp_path/'out',expected_sha256=sha(p),source_logical_name='audit.csv')
    root=result.external_root
    s15=load_gz(root/'audit_15m_surface.jsonl.gz')
    s2=load_gz(root/'audit_2h_a_l_surface.jsonl.gz')
    assert len(s15)==8 and all(x['status']=='COMPLETE' for x in s15)
    assert len(s2)==1 and s2[0]['status']=='COMPLETE'
    assert s2[0]['lattice_coordinate']=='A'
    assert s15[0]['first_valid_time']=='2026-01-02T00:15:00'
    assert s2[0]['first_valid_time']=='2026-01-02T02:00:00'
    assert s15[0]['lattice_id']==LATTICE_15M_ID
    assert s2[0]['lattice_id']==LATTICE_2H_ID


def test_missing_m1_is_never_repaired_and_censors_parent(tmp_path: Path) -> None:
    p=write(tmp_path, minute_rows(datetime(2026,1,2), 120, skip={7}))
    result=materialize_population(p,tmp_path/'out',expected_sha256=sha(p),source_logical_name='audit.csv')
    s15=load_gz(result.external_root/'audit_15m_surface.jsonl.gz')
    s2=load_gz(result.external_root/'audit_2h_a_l_surface.jsonl.gz')
    gaps=load_gz(result.external_root/'source_gap_ledger.jsonl.gz')
    assert s15[0]['status']=='INCOMPLETE'
    assert s15[0]['observed_parent_count']==14
    assert s15[0]['repair_applied'] is False
    assert s2[0]['status']=='UNAVAILABLE'
    assert gaps[0]['cause_classification']=='UNKNOWN_SOURCE_ABSENCE'
    assert gaps[0]['proven_market_closure'] is False
    assert gaps[0]['repair_applied'] is False


def test_population_preserves_unresolved_side_clock_and_audit_only_authority(tmp_path: Path) -> None:
    p=write(tmp_path, minute_rows(datetime(2026,1,2), 1440))
    result=materialize_population(p,tmp_path/'out',expected_sha256=sha(p),source_logical_name='audit.csv')
    m=result.manifest
    assert m['generation_contract']['source_clock_state']==SOURCE_CLOCK_STATE
    assert m['generation_contract']['source_side_state']==SOURCE_SIDE_STATE
    assert m['authority_class']=='ASOCS_AUDIT_ONLY'
    assert m['active_provider'] is False
    assert m['selector_eligible'] is False
    assert m['ec1_eligible'] is False
    assert m['canonical'] is False
    assert m['publication'] is False
    assert m['structural_computation_started'] is False
    assert m['review_sampling_started'] is False


def test_deterministic_materialisation_and_renderer(tmp_path: Path) -> None:
    p=write(tmp_path, minute_rows(datetime(2026,1,2), 1440))
    a=materialize_population(p,tmp_path/'a',expected_sha256=sha(p),source_logical_name='audit.csv')
    b=materialize_population(p,tmp_path/'b',expected_sha256=sha(p),source_logical_name='audit.csv')
    assert a.manifest['population_manifest_id']==b.manifest['population_manifest_id']
    assert a.manifest['external_artifacts']==b.manifest['external_artifacts']
    bars=load_gz(a.external_root/'audit_15m_surface.jsonl.gz')[:4]
    assert render_source_native_svg(bars)==render_source_native_svg(bars)
    assert '<metadata>' in render_source_native_svg(bars)


def test_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    p=write(tmp_path, minute_rows(datetime(2026,1,2), 120))
    with pytest.raises(ASOCSPopulationError, match='SOURCE_HASH_MISMATCH'):
        materialize_population(p,tmp_path/'out',expected_sha256='0'*64,source_logical_name='audit.csv')


def test_wp2_court_record_freezes_exact_population_and_no_authority() -> None:
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads((root / "docs/programmes/asocs-v0-1/implementation/wp2/ASOCS_POPULATION_G1_MANIFEST_v0_1.json").read_text(encoding="utf-8"))
    freeze = json.loads((root / "docs/programmes/asocs-v0-1/implementation/wp2/ASOCSI_G1_POPULATION_FREEZE_v0_1.json").read_text(encoding="utf-8"))
    pointer = json.loads((root / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json").read_text(encoding="utf-8"))
    assert manifest["source"]["sha256"] == "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
    assert manifest["source"]["row_count"] == 186145
    assert manifest["source"]["region_row_counts"] == {"PRE_CONTEXT": 1319, "TARGET": 183408, "POST_CONTEXT": 1418}
    assert manifest["surface_15m"]["target_complete"] == 11930
    assert manifest["surface_15m"]["target_incomplete"] == 370
    assert manifest["surface_15m"]["target_absent"] == 5076
    assert manifest["surface_2h_a_l"]["target_complete"] == 1330
    assert manifest["surface_2h_a_l"]["target_unavailable"] == 842
    assert manifest["gap_ledger"]["closure_assertions"] == 0
    assert manifest["gap_ledger"]["repair_count"] == 0
    assert manifest["renderer"]["reference_bar_count"] == 95
    assert manifest["renderer"]["network_dependency"] is False
    assert freeze["population_manifest_id"] == manifest["population_manifest_id"]
    assert freeze["structural_computation_started"] is False
    assert freeze["review_sampling_started"] is False
    assert pointer["packet_id"] == "ASOCSI-WP2"
    assert pointer["next_packet"] == "ASOCSI-WP3"
    assert manifest["active_provider"] is False
    assert manifest["selector_eligible"] is False
    assert manifest["ec1_eligible"] is False
    assert manifest["canonical"] is False
    assert manifest["publication"] is False


def test_external_artifact_identity_has_no_absolute_paths() -> None:
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads((root / "docs/programmes/asocs-v0-1/implementation/wp2/ASOCS_POPULATION_G1_MANIFEST_v0_1.json").read_text(encoding="utf-8"))
    assert len(manifest["external_artifacts"]) == 5
    assert all(str(item["logical_name"]).startswith("asocs/g1/") for item in manifest["external_artifacts"])
    assert all(not str(item["logical_name"]).startswith(("/", "C:", "D:")) for item in manifest["external_artifacts"])
