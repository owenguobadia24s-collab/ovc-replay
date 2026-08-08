"""Event-sourced synthetic/shadow lifecycle engine for C2E v0.2."""
from __future__ import annotations

from typing import Any, Mapping

from .models import build_record
from .projection import project_episode
from .stream import AppendOnlyStream
from .topology import EpisodeTopology


class LifecycleError(ValueError):
    pass


class EpisodeEngine:
    def __init__(self, boundary_pack_id: str) -> None:
        self.boundary_pack_id = boundary_pack_id
        self.stream = AppendOnlyStream()
        self.topology = EpisodeTopology()
        self.genesis: dict[str, dict[str, Any]] = {}
        self.status_by_episode: dict[str, str] = {}
        self.owner_by_frame: dict[tuple[str, str, str], str] = {}

    def _require_open(self, episode_id: str) -> None:
        if self.status_by_episode.get(episode_id) != "OPEN":
            raise LifecycleError("EPISODE_NOT_OPEN")

    def _build_event(self, *, episode_ids: list[str], candidate_ids: list[str], action: str, priority: int, effective_time: str, first_valid_time: str, compatibility: str = "ORDERED_BY_PRIORITY", collision: str = "NONE", reason_codes: list[str] | None = None) -> dict[str, Any]:
        return build_record("boundary_event", {"episode_ids":episode_ids,"candidate_ids":candidate_ids,"lifecycle_action":action,"priority_class":priority,"compatibility_disposition":compatibility,"effective_time":effective_time,"confirmation_time":first_valid_time,"first_valid_time":first_valid_time,"collision_disposition":collision,"reason_codes":reason_codes or [],"authority":"INACTIVE_NONCANONICAL_SHADOW"})

    def _event(self, **kwargs: Any) -> dict[str, Any]:
        event = self._build_event(**kwargs)
        self.stream.append(event)
        return event

    def birth(self, *, frame: Mapping[str, Any], boundary_rule_id: str, candidate_id: str, effective_time: str, first_valid_time: str) -> dict[str, Any]:
        identity = frame["identity"]
        owner_key = (str(identity["scope_id"]), str(identity["scale_id"]), str(frame["frame_id"]))
        if owner_key in self.owner_by_frame:
            raise LifecycleError("C2E_OWNER_MULTIPLE_PEER_OWNERS")
        genesis = build_record("episode_genesis", {"boundary_pack_id":self.boundary_pack_id,"source_release_id":frame["source_binding"]["source_release_id"],"instrument_id":identity["instrument_id"],"side":identity["side"],"scope_id":identity["scope_id"],"scale_id":identity["scale_id"],"birth_frame_id":frame["frame_id"],"birth_boundary_rule_id":boundary_rule_id,"birth_effective_time":effective_time,"first_valid_time":first_valid_time,"authority":"INACTIVE_NONCANONICAL_SHADOW"})
        self.stream.append(genesis)
        self.genesis[genesis["episode_id"]] = genesis
        self.status_by_episode[genesis["episode_id"]] = "OPEN"
        self.owner_by_frame[owner_key] = genesis["episode_id"]
        event = self._event(episode_ids=[genesis["episode_id"]], candidate_ids=[candidate_id], action="BIRTH", priority=8, effective_time=effective_time, first_valid_time=first_valid_time)
        membership = build_record("membership_delta", {"episode_id":genesis["episode_id"],"frame_id":frame["frame_id"],"operation":"ADD","boundary_event_id":event["boundary_event_id"],"effective_time":effective_time,"first_valid_time":first_valid_time,"authority":"INACTIVE_NONCANONICAL_SHADOW"})
        self.stream.append(membership)
        return genesis

    def continue_episode(self, *, episode_id: str, frame: Mapping[str, Any], candidate_id: str, effective_time: str, first_valid_time: str) -> dict[str, Any]:
        self._require_open(episode_id)
        identity = frame["identity"]
        owner_key = (str(identity["scope_id"]), str(identity["scale_id"]), str(frame["frame_id"]))
        existing = self.owner_by_frame.get(owner_key)
        if existing is not None and existing != episode_id:
            raise LifecycleError("C2E_OWNER_MULTIPLE_PEER_OWNERS")
        event = self._event(episode_ids=[episode_id], candidate_ids=[candidate_id], action="CONTINUATION", priority=7, effective_time=effective_time, first_valid_time=first_valid_time)
        membership = build_record("membership_delta", {"episode_id":episode_id,"frame_id":frame["frame_id"],"operation":"ADD","boundary_event_id":event["boundary_event_id"],"effective_time":effective_time,"first_valid_time":first_valid_time,"authority":"INACTIVE_NONCANONICAL_SHADOW"})
        self.stream.append(membership)
        self.owner_by_frame[owner_key] = episode_id
        return membership

    def phase_mutation(self, *, episode_id: str, candidate_id: str, phase_type: str, start_time: str, end_time: str | None, source_record_ids: list[str], effective_time: str, first_valid_time: str) -> dict[str, Any]:
        self._require_open(episode_id)
        self._event(episode_ids=[episode_id], candidate_ids=[candidate_id], action="PHASE_MUTATION", priority=6, effective_time=effective_time, first_valid_time=first_valid_time)
        phase = build_record("phase_segment", {"episode_id":episode_id,"phase_type":phase_type,"start_time":start_time,"end_time":end_time,"first_valid_time":first_valid_time,"source_record_ids":source_record_ids,"authority":"INACTIVE_NONCANONICAL_SHADOW"})
        self.stream.append(phase)
        return phase

    def censor(self, *, episode_id: str, candidate_id: str, reason: str, effective_time: str, first_valid_time: str) -> dict[str, Any]:
        self._require_open(episode_id)
        if reason not in {"CENSOR_GAP","CENSOR_RELEASE_END"}:
            raise LifecycleError("CENSOR_REASON_INVALID")
        event = self._event(episode_ids=[episode_id], candidate_ids=[candidate_id], action=reason, priority=2, effective_time=effective_time, first_valid_time=first_valid_time, reason_codes=["C2E_SOURCE_GAP" if reason == "CENSOR_GAP" else "C2E_RELEASE_END_CENSORED"])
        self.status_by_episode[episode_id] = "CENSORED"
        return event

    def terminate(self, *, episode_id: str, candidate_id: str, conflict: bool, effective_time: str, first_valid_time: str) -> dict[str, Any]:
        self._require_open(episode_id)
        action = "TERMINATE_CONFLICT" if conflict else "TERMINATE"
        event = self._event(episode_ids=[episode_id], candidate_ids=[candidate_id], action=action, priority=3 if conflict else 5, effective_time=effective_time, first_valid_time=first_valid_time, reason_codes=["C2E_CONFLICT"] if conflict else [])
        self.status_by_episode[episode_id] = "CONFLICTED" if conflict else "TERMINATED"
        return event

    def link(self, *, edge_type: str, parent_episode_id: str, child_episode_id: str, candidate_id: str, effective_time: str, first_valid_time: str) -> dict[str, Any]:
        if parent_episode_id not in self.genesis or child_episode_id not in self.genesis:
            raise LifecycleError("TOPOLOGY_EPISODE_NOT_FOUND")
        event = self._build_event(episode_ids=sorted({parent_episode_id, child_episode_id}), candidate_ids=[candidate_id], action=edge_type, priority=4, effective_time=effective_time, first_valid_time=first_valid_time)
        edge = self.topology.add_edge(edge_type=edge_type, parent_episode_id=parent_episode_id, child_episode_id=child_episode_id, boundary_event_id=event["boundary_event_id"], effective_time=effective_time, first_valid_time=first_valid_time)
        self.stream.append(event)
        self.stream.append(edge)
        return edge

    def snapshot(self, episode_id: str, *, as_of_time: str, first_valid_time: str) -> dict[str, Any]:
        return project_episode(episode_id, self.stream.records, as_of_time=as_of_time, first_valid_time=first_valid_time)
