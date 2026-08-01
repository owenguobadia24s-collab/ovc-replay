"""Deterministic shared development mechanics for governed OVC packets.

This package contains tooling administration only. It has no market, selector,
release, provider, validation, probability, risk, exposure or execution authority.
"""

from .artifacts import ArtifactRef, verify_artifact
from .decisions import DecisionRecord
from .gates import GatePacket
from .identity import canonical_json_bytes, canonical_sha256, normalize_relative_path
from .preflight import DestinationCheck, PreflightRequest, run_preflight
from .profiles import ArtifactProfile, ProfileError, load_profile
from .qa import QAAssertion, aggregate_assertions
from .rollback import RollbackRecord
from .test_selection import (
    TestProfileRegistry,
    TestSelectionError,
    load_test_profile_registry,
    select_test_manifest,
)

__all__ = [
    "ArtifactProfile",
    "ArtifactRef",
    "DecisionRecord",
    "DestinationCheck",
    "GatePacket",
    "PreflightRequest",
    "ProfileError",
    "QAAssertion",
    "RollbackRecord",
    "TestProfileRegistry",
    "TestSelectionError",
    "aggregate_assertions",
    "canonical_json_bytes",
    "canonical_sha256",
    "load_profile",
    "load_test_profile_registry",
    "normalize_relative_path",
    "run_preflight",
    "select_test_manifest",
    "verify_artifact",
]
