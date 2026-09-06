from __future__ import annotations

from ovc.research_operations.mcac.contracts import ClockCoordinateIdentity, ClockIndexedOccurrenceRef, ClockRegistryEntry, ComparabilityContext
from ovc.research_operations.mcac.doctrine import DOCTRINE_HASH, DOCTRINE_ID


def coordinate(clock_id: str, duration: int, *, generation: str = "GEN-A", owner: str = "OWNER") -> ClockCoordinateIdentity:
    return ClockCoordinateIdentity(owner, clock_id, generation, "FIXED", duration, "UTC_INTERVAL_END", "OWNER_FVT", "UTC", "24X7", "GREGORIAN", ("fixture",))


def registry(clock: ClockCoordinateIdentity) -> ClockRegistryEntry:
    return ClockRegistryEntry(clock, "AUTH.READ", "PAIRWISE_ALLOWED", "r1", "2020-01-01T00:00:00Z", ("fixture",))


def context(left=None, right=None, *, cutoff="2020-01-02T00:00:00Z") -> ComparabilityContext:
    left = left or coordinate("15M", 900)
    right = right or coordinate("2H_A_L", 7200)
    return ComparabilityContext(left, right, registry(left), registry(right), left.generation_id, right.generation_id, "2020-01-01T00:00:00Z", "2020-01-02T00:00:00Z", cutoff, ("GEOM", "GEOM"), ("OWNER.PUBLIC", "OWNER.PUBLIC"), "RULE-1", "NO_STITCH", DOCTRINE_ID, DOCTRINE_HASH, {"left": "2020-01-01T00:00:00Z", "right": "2020-01-01T00:00:00Z", "rule": "2020-01-01T00:00:00Z", "doctrine": "2020-01-01T00:00:00Z"}, "OVC.MCAC.CAPACITY.SYNTHETIC.v0.1")


def occurrence(clock: ClockCoordinateIdentity, reg: ClockRegistryEntry, oid: str, start: str, end: str, *, kind="CLOSED_INTERVAL", generation=None, gap="NONE", missing="NONE", segment="S1", censor="NONE") -> ClockIndexedOccurrenceRef:
    gen = generation or clock.generation_id
    return ClockIndexedOccurrenceRef(oid, "owner-" + oid, clock.coordinate_id, reg.registry_entry_id, gen, "AUTH.READ", "BINDING", "rep:" + oid, "GEOM", gen, "2020-01-01T00:00:00Z", "OWNER.PUBLIC", kind, start, end, end, end, "2020-01-02T00:00:00Z", segment, gap, censor, missing)
