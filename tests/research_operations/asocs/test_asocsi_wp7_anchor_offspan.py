from __future__ import annotations

from ovc.research_operations.asocs.blind_review import overlay_visible_review_anchor, review_anchor_partition
from ovc.research_operations.asocs.population_core import render_source_native_svg


def _bars(starts: list[str]):
    return [
        {
            "interval_start": start,
            "open": str(1.00 + i * 0.01),
            "high": str(1.03 + i * 0.01),
            "low": str(0.99 + i * 0.01),
            "close": str(1.02 + i * 0.01),
        }
        for i, start in enumerate(starts)
    ]


def test_exact_midpoint_before_first_rendered_complete_bar_uses_truthful_edge_callout():
    bars = _bars([
        "2026-04-05T22:00:00",
        "2026-04-05T22:15:00",
        "2026-04-05T22:30:00",
    ])
    window = {"start": "2026-04-05T13:32:00", "end": "2026-04-06T05:35:00"}
    anchor, split = review_anchor_partition(bars, window)
    assert anchor.isoformat() == "2026-04-05T21:33:30"
    assert split == 0
    marked = overlay_visible_review_anchor(render_source_native_svg(bars), bars, window)
    assert marked.count('data-asocs-review-anchor="visible-neutral-reference"') == 1
    assert 'data-anchor-time="2026-04-05T21:33:30"' in marked
    assert 'data-anchor-placement="BEFORE_FIRST_RENDERED_COMPLETE_BAR"' in marked
    assert "BEFORE FIRST RENDERED COMPLETE 15M BAR" in marked
    assert "stroke-dasharray=\"8 6\"" not in marked


def test_exact_midpoint_after_last_rendered_complete_bar_uses_truthful_edge_callout():
    bars = _bars([
        "2026-04-05T13:30:00",
        "2026-04-05T13:45:00",
        "2026-04-05T14:00:00",
    ])
    window = {"start": "2026-04-05T13:00:00", "end": "2026-04-06T05:00:00"}
    anchor, split = review_anchor_partition(bars, window)
    assert anchor.isoformat() == "2026-04-05T21:00:00"
    assert split == len(bars)
    marked = overlay_visible_review_anchor(render_source_native_svg(bars), bars, window)
    assert marked.count('data-asocs-review-anchor="visible-neutral-reference"') == 1
    assert 'data-anchor-time="2026-04-05T21:00:00"' in marked
    assert 'data-anchor-placement="AFTER_LAST_RENDERED_COMPLETE_BAR"' in marked
    assert "AFTER LAST RENDERED COMPLETE 15M BAR" in marked
    assert "stroke-dasharray=\"8 6\"" not in marked


def test_bracketed_anchor_preserves_existing_gap_safe_vertical_marker():
    bars = _bars([
        "2026-01-01T00:00:00",
        "2026-01-01T00:15:00",
        "2026-01-01T00:30:00",
        "2026-01-01T01:45:00",
    ])
    window = {"start": "2026-01-01T00:00:00", "end": "2026-01-01T02:00:00"}
    anchor, split = review_anchor_partition(bars, window)
    assert anchor.isoformat() == "2026-01-01T01:00:00"
    assert split == 3
    marked = overlay_visible_review_anchor(render_source_native_svg(bars), bars, window)
    assert 'data-anchor-placement="BETWEEN_RENDERED_BARS"' in marked
    assert 'x1="880.000"' in marked and 'x2="880.000"' in marked
    assert marked.count("REVIEW ANCHOR") == 1
