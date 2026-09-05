"""Compatibility surface for the canonical GEN0002 Pass-1 implementation.

The decision-bearing algorithm is ``pass1_gen0002.py`` and is bound by the
GEN0002 Pass-1 classification-view manifest.  This module intentionally adds no
second implementation or scientific authority; it only re-exports that frozen
surface for callers using the shorter historical module name.
"""

from .pass1_gen0002 import (
    EXPECTED_FRONTIER_RECEIPT_ID,
    EXPECTED_PASSPORT_COUNT,
    EXPECTED_POST_DELTA_SHA256,
    EXPECTED_PROTOCOL_BINDING_ID,
    EXPECTED_SOURCE_PASSPORT_SET_SHA256,
    EXPECTED_SOURCE_UNIVERSE_ID,
    EXPECTED_SUBJECT_COUNT,
    GENERATION_ID,
    PACKET_ID,
    PROJECTION,
    PROTOCOL_ID,
    build_pass1_classification_view,
    build_shared_locator_dependence_graph,
    build_virtual_view_identity,
    load_source_passports,
)

__all__ = [
    "EXPECTED_FRONTIER_RECEIPT_ID",
    "EXPECTED_PASSPORT_COUNT",
    "EXPECTED_POST_DELTA_SHA256",
    "EXPECTED_PROTOCOL_BINDING_ID",
    "EXPECTED_SOURCE_PASSPORT_SET_SHA256",
    "EXPECTED_SOURCE_UNIVERSE_ID",
    "EXPECTED_SUBJECT_COUNT",
    "GENERATION_ID",
    "PACKET_ID",
    "PROJECTION",
    "PROTOCOL_ID",
    "build_pass1_classification_view",
    "build_shared_locator_dependence_graph",
    "build_virtual_view_identity",
    "load_source_passports",
]
