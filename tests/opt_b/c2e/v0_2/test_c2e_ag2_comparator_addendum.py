from copy import deepcopy
import unittest

from ovc.opt_b.c2e_v2.ag2_comparator import (
    AG2ComparatorError,
    compare_structural_boundaries,
    null_control_counts,
)


def _axis(value: str) -> dict[str, object]:
    return {"status": "EVALUATED", "value": value, "reason_code": None}


def _srfd(time: str, state: str, *, reset: bool = False) -> dict[str, object]:
    axes = {
        "LOCATION": _axis(state),
        "MOTION": _axis("M"),
        "ORGANISATION": _axis("O"),
        "INTERACTION": _axis("I"),
        "QUALITY": _axis("Q"),
    }
    return {
        "c2_state_id": f"srfd-{time}",
        "first_valid_time": time,
        "side": "ASK",
        "clock": "15M",
        "evaluation_scope_id": "LOCAL",
        "target_eligible": True,
        "continuity": "RESET" if reset else "CONTIGUOUS",
        "axes": axes,
    }


def _frame(time: str, observation: str, predecessor: str | None, signature: str) -> dict[str, object]:
    return {
        "side": "ASK",
        "first_valid_time": time,
        "observation_id": observation,
        "predecessor_observation_id": predecessor,
        "structural_signature_sha256": signature,
    }


def _event(action: str, time: str, episode: str = "ep") -> dict[str, object]:
    return {
        "schema": "c2e_boundary_event/v0_2",
        "boundary_event_id": f"b-{action}-{time}",
        "lifecycle_action": action,
        "episode_ids": [episode],
        "effective_time": time,
    }


class C2EAG2ComparatorAddendumTests(unittest.TestCase):
    def test_classifies_common_transition_surface_and_excludes_stream_start(self):
        frames = [
            _frame("2026-06-01T00:15:00Z", "o1", None, "s1"),
            _frame("2026-06-01T00:30:00Z", "o2", "o1", "s2"),
            _frame("2026-06-01T00:45:00Z", "o3", "o2", "s3"),
        ]
        events = [
            {"schema": "c2e_episode_genesis/v0_2", "episode_id": "ep", "side": "ASK"},
            _event("BIRTH", "2026-06-01T00:15:00Z"),
            _event("PHASE_MUTATION", "2026-06-01T00:30:00Z"),
            _event("PHASE_MUTATION", "2026-06-01T00:45:00Z"),
        ]
        srfd = [
            _srfd("2026-06-01T00:15:00Z", "A", reset=True),
            _srfd("2026-06-01T00:30:00Z", "B"),
            _srfd("2026-06-01T00:45:00Z", "B"),
        ]
        result = compare_structural_boundaries(frames, events, srfd)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(
            result["counts"],
            {
                "BOTH_BOUNDARY": 1,
                "C2E_ONLY": 1,
                "SRFD_ONLY": 0,
                "NEITHER_BOUNDARY": 0,
            },
        )
        self.assertEqual(
            null_control_counts(result["rows"]),
            {
                "BOTH_BOUNDARY": 0,
                "C2E_ONLY": 2,
                "SRFD_ONLY": 0,
                "NEITHER_BOUNDARY": 0,
            },
        )

    def test_input_order_does_not_change_comparison(self):
        frames = [
            _frame("2026-06-01T00:15:00Z", "o1", None, "s1"),
            _frame("2026-06-01T00:30:00Z", "o2", "o1", "s2"),
        ]
        events = [
            {"schema": "c2e_episode_genesis/v0_2", "episode_id": "ep", "side": "ASK"},
            _event("BIRTH", "2026-06-01T00:15:00Z"),
            _event("PHASE_MUTATION", "2026-06-01T00:30:00Z"),
        ]
        srfd = [
            _srfd("2026-06-01T00:15:00Z", "A", reset=True),
            _srfd("2026-06-01T00:30:00Z", "B"),
        ]
        first = compare_structural_boundaries(frames, events, srfd)
        second = compare_structural_boundaries(
            list(reversed(frames)), list(reversed(events)), list(reversed(srfd))
        )
        self.assertEqual(first["rows"], second["rows"])
        self.assertEqual(first["counts"], second["counts"])

    def test_family_or_outcome_fields_fail_closed(self):
        frames = [
            _frame("2026-06-01T00:15:00Z", "o1", None, "s1"),
            _frame("2026-06-01T00:30:00Z", "o2", "o1", "s2"),
        ]
        frames[1]["family_id"] = "forbidden"
        events = [
            {"schema": "c2e_episode_genesis/v0_2", "episode_id": "ep", "side": "ASK"},
            _event("BIRTH", "2026-06-01T00:15:00Z"),
        ]
        srfd = [
            _srfd("2026-06-01T00:15:00Z", "A", reset=True),
            _srfd("2026-06-01T00:30:00Z", "A"),
        ]
        with self.assertRaisesRegex(AG2ComparatorError, "AG2_FORBIDDEN_COMPARATOR_FIELD"):
            compare_structural_boundaries(frames, events, srfd)


if __name__ == "__main__":
    unittest.main()
