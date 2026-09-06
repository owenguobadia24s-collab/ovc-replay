from __future__ import annotations

from ovc.research_operations.mcac.correspondence import CandidateEdge
from ovc.research_operations.mcac.qualification import qualify_candidate_transport


def edges(count):
    return tuple(CandidateEdge(f"l{i:05d}", f"r{i:05d}", f"h{i:05d}", 1_000_000, "GEOM") for i in range(count))


def test_clean_chunked_restart_and_order_equivalence_at_bound_population():
    values = edges(20_000)
    full = qualify_candidate_transport((values,), left_count=20_000, right_count=20_000, chunk_size=512)
    chunked = qualify_candidate_transport((values[i:i+512] for i in range(0, len(values), 512)), left_count=20_000, right_count=20_000, chunk_size=512)
    restarted = qualify_candidate_transport((reversed(values[10000:]), reversed(values[:10000])), left_count=20_000, right_count=20_000, chunk_size=512)
    assert full.status == chunked.status == restarted.status == "PASS"
    assert full.canonical_hash == chunked.canonical_hash == restarted.canonical_hash


def test_each_capacity_boundary_fails_closed_without_result():
    values = edges(2)
    cases = [
        dict(left_count=20001, right_count=1, chunk_size=1),
        dict(left_count=20000, right_count=20001, chunk_size=1),
        dict(left_count=1, right_count=1, chunk_size=513),
    ]
    for kwargs in cases:
        receipt = qualify_candidate_transport((values,), **kwargs)
        assert receipt.status == "CAPACITY_EXCEEDED" and not receipt.complete and receipt.canonical_hash is None
