from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any, Callable

from .serialization import logical_sha256
from .wp10_execution_resilience import RunAuthorityStore, RunStartReceipt


PROGRAMME_ID = "OVC-SRFD-BENCHMARK-v0.1"
PACKET_ID = "SRFDI-WP10-v0.9"
RUN_BINDING_SHA256 = "ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"
EXECUTION_BINDING_SHA256 = "2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1"
EXECUTION_BINDING_MERGE = "eefd860af86aea38e80ec211dd5ea34160171b6f"
AUTHORITY_EFFECT_MAIN = "63f084c04796121357db15259467b91e7065929d"
FRESH_TOKEN_ID = "SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"
FROZEN_POPULATION_ID = "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd"

_EXPECTED_BINDING = {
    "programme_id": PROGRAMME_ID,
    "packet_id": PACKET_ID,
    "population_id": FROZEN_POPULATION_ID,
    "eligible_ids_sha256": "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e",
    "scientific_manifest_sha256": "6ba46d446d799d7686ee038c80fb21fa899e8dbe0875ddd12779068b38e30cbb",
    "preregistration_sha256": "f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3",
    "representation_pack_sha256": "7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0",
    "segmentation_pack_sha256": "6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0",
    "stability_pack_sha256": "371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b",
    "source_binding_sha256": "4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7",
    "capacity_grid_sha256": "68317db2ddb5608d0dd13bad67be78f70263dee5c2dc59790c1c995098c00866",
    "execution_binding_sha256": EXECUTION_BINDING_SHA256,
    "execution_binding_merge": EXECUTION_BINDING_MERGE,
}


class WP10V09InterfaceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _sha256_hex(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise WP10V09InterfaceError("V09_BINDING_INVALID", f"{field} must be lowercase sha256")
    return text


def _git_commit_hex(value: str, field: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 40 or any(ch not in "0123456789abcdef" for ch in text):
        raise WP10V09InterfaceError("V09_BINDING_INVALID", f"{field} must be lowercase git commit sha")
    return text


@dataclass(frozen=True)
class RunBindingV09:
    programme_id: str
    packet_id: str
    population_id: str
    eligible_ids_sha256: str
    scientific_manifest_sha256: str
    preregistration_sha256: str
    representation_pack_sha256: str
    segmentation_pack_sha256: str
    stability_pack_sha256: str
    source_binding_sha256: str
    capacity_grid_sha256: str
    execution_binding_sha256: str
    execution_binding_merge: str

    def to_dict(self) -> dict[str, str]:
        output = {
            "programme_id": str(self.programme_id).strip(),
            "packet_id": str(self.packet_id).strip(),
            "population_id": str(self.population_id).strip(),
            "eligible_ids_sha256": _sha256_hex(self.eligible_ids_sha256, "eligible_ids_sha256"),
            "scientific_manifest_sha256": _sha256_hex(self.scientific_manifest_sha256, "scientific_manifest_sha256"),
            "preregistration_sha256": _sha256_hex(self.preregistration_sha256, "preregistration_sha256"),
            "representation_pack_sha256": _sha256_hex(self.representation_pack_sha256, "representation_pack_sha256"),
            "segmentation_pack_sha256": _sha256_hex(self.segmentation_pack_sha256, "segmentation_pack_sha256"),
            "stability_pack_sha256": _sha256_hex(self.stability_pack_sha256, "stability_pack_sha256"),
            "source_binding_sha256": _sha256_hex(self.source_binding_sha256, "source_binding_sha256"),
            "capacity_grid_sha256": _sha256_hex(self.capacity_grid_sha256, "capacity_grid_sha256"),
            "execution_binding_sha256": _sha256_hex(self.execution_binding_sha256, "execution_binding_sha256"),
            "execution_binding_merge": _git_commit_hex(self.execution_binding_merge, "execution_binding_merge"),
        }
        if not all(output[key] for key in ("programme_id", "packet_id", "population_id")):
            raise WP10V09InterfaceError("V09_BINDING_INVALID", "programme, packet and population IDs are required")
        return output

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.to_dict())


def binding_from_manifest(manifest: Mapping[str, Any]) -> RunBindingV09:
    raw = manifest.get("run_binding")
    if not isinstance(raw, Mapping):
        raise WP10V09InterfaceError("V09_MANIFEST_INVALID", "run_binding mapping required")
    keys = tuple(RunBindingV09.__dataclass_fields__)
    missing = [key for key in keys if key not in raw]
    extras = sorted(set(raw) - set(keys))
    if missing or extras:
        raise WP10V09InterfaceError("V09_BINDING_SHAPE_MISMATCH", f"missing={missing} extras={extras}")
    binding = RunBindingV09(**{key: str(raw[key]) for key in keys})
    verify_v09_binding(binding)
    if str(manifest.get("run_binding_sha256", "")) != binding.logical_hash:
        raise WP10V09InterfaceError("V09_MANIFEST_BINDING_HASH_MISMATCH", str(manifest.get("run_binding_sha256")))
    return binding


def verify_v09_binding(binding: RunBindingV09) -> None:
    actual = binding.to_dict()
    for key, expected in _EXPECTED_BINDING.items():
        if actual.get(key) != expected:
            raise WP10V09InterfaceError("V09_BINDING_DRIFT", f"{key}:{actual.get(key)}")
    if binding.logical_hash != RUN_BINDING_SHA256:
        raise WP10V09InterfaceError("V09_BINDING_HASH_MISMATCH", binding.logical_hash)


class AuthorityEffectTokenView(Mapping[str, Any]):
    """Read-only effective start view over the immutable v0.9 token artifact.

    The raw token mapping is copied and never mutated. Only ``state`` is overlaid from the
    separately immutable authority-effect receipt. Token identity and the raw token payload
    hash therefore remain court-record values while RunAuthorityStore sees the post-merge
    effective start state.
    """

    def __init__(self, raw_token: Mapping[str, Any], effective_state: str) -> None:
        self._raw = dict(raw_token)
        self._effective_state = str(effective_state)

    def __getitem__(self, key: str) -> Any:
        if key == "state":
            return self._effective_state
        return self._raw[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._raw)

    def __len__(self) -> int:
        return len(self._raw)

    @property
    def raw_payload_logical_sha256(self) -> str:
        return logical_sha256(self._raw)

    @property
    def raw_token(self) -> dict[str, Any]:
        return dict(self._raw)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def verify_frozen_execution_runtime(repo_root: Path, execution_freeze: Mapping[str, Any]) -> None:
    if str(execution_freeze.get("candidate_logical_sha256", "")) != EXECUTION_BINDING_SHA256:
        raise WP10V09InterfaceError(
            "V09_EXECUTION_BINDING_MISMATCH",
            str(execution_freeze.get("candidate_logical_sha256", "")),
        )
    paths = execution_freeze.get("runtime_paths")
    blobs = execution_freeze.get("runtime_blobs")
    if not isinstance(paths, Mapping) or not isinstance(blobs, Mapping) or set(paths) != set(blobs):
        raise WP10V09InterfaceError("V09_EXECUTION_BINDING_INVALID", "runtime path/blob maps must match")
    for name in sorted(paths):
        path = Path(repo_root) / str(paths[name])
        if not path.is_file():
            raise WP10V09InterfaceError("V09_RUNTIME_ARTIFACT_UNAVAILABLE", f"{name}:{path}")
        actual = _git_blob_sha(path)
        if actual != str(blobs[name]):
            raise WP10V09InterfaceError("V09_RUNTIME_BINDING_DRIFT", f"{name}:{actual}")


def effective_token_view(
    raw_token: Mapping[str, Any],
    authority_effect: Mapping[str, Any],
    binding: RunBindingV09,
) -> AuthorityEffectTokenView:
    verify_v09_binding(binding)
    if str(raw_token.get("token_id", "")) != FRESH_TOKEN_ID:
        raise WP10V09InterfaceError("V09_TOKEN_ID_MISMATCH", str(raw_token.get("token_id", "")))
    if str(raw_token.get("state", "")) != "AUTHORIZED_UNCONSUMED_PENDING_MAIN_MERGE":
        raise WP10V09InterfaceError("V09_RAW_TOKEN_STATE_MISMATCH", str(raw_token.get("state", "")))
    if str(raw_token.get("run_binding_sha256", "")) != RUN_BINDING_SHA256:
        raise WP10V09InterfaceError("V09_TOKEN_BINDING_MISMATCH", str(raw_token.get("run_binding_sha256", "")))
    if str(raw_token.get("execution_binding_logical_sha256", "")) != EXECUTION_BINDING_SHA256:
        raise WP10V09InterfaceError("V09_TOKEN_EXECUTION_BINDING_MISMATCH", str(raw_token.get("execution_binding_logical_sha256", "")))
    if str(raw_token.get("execution_binding_effective_merge", "")) != EXECUTION_BINDING_MERGE:
        raise WP10V09InterfaceError("V09_TOKEN_EXECUTION_MERGE_MISMATCH", str(raw_token.get("execution_binding_effective_merge", "")))
    if raw_token.get("single_use") is not True or str(raw_token.get("run_cardinality", "")) != "ONE_EXACT_BOUND_RUN":
        raise WP10V09InterfaceError("V09_TOKEN_CARDINALITY_MISMATCH", "single-use exact run required")
    if str(raw_token.get("provider_fetch", "")) != "DENIED" or str(raw_token.get("validation_2025", "")) != "LOCKED_UNCONSUMED":
        raise WP10V09InterfaceError("V09_TOKEN_FIREWALL_DRIFT", "provider/Validation firewall mismatch")
    if str(raw_token.get("reserved_authority", "")) != "NONE":
        raise WP10V09InterfaceError("V09_TOKEN_AUTHORITY_EXPANSION", str(raw_token.get("reserved_authority", "")))

    if str(authority_effect.get("effective_main_commit", "")) != AUTHORITY_EFFECT_MAIN:
        raise WP10V09InterfaceError("V09_AUTHORITY_EFFECT_COMMIT_MISMATCH", str(authority_effect.get("effective_main_commit", "")))
    if str(authority_effect.get("run_binding_sha256", "")) != RUN_BINDING_SHA256:
        raise WP10V09InterfaceError("V09_AUTHORITY_EFFECT_BINDING_MISMATCH", str(authority_effect.get("run_binding_sha256", "")))
    if str(authority_effect.get("execution_binding_logical_sha256", "")) != EXECUTION_BINDING_SHA256:
        raise WP10V09InterfaceError("V09_AUTHORITY_EFFECT_EXECUTION_MISMATCH", str(authority_effect.get("execution_binding_logical_sha256", "")))
    fresh = authority_effect.get("fresh_token")
    if not isinstance(fresh, Mapping):
        raise WP10V09InterfaceError("V09_AUTHORITY_EFFECT_INVALID", "fresh_token mapping required")
    if str(fresh.get("token_id", "")) != FRESH_TOKEN_ID or str(fresh.get("state", "")) != "AUTHORIZED_UNCONSUMED":
        raise WP10V09InterfaceError("V09_AUTHORITY_EFFECT_TOKEN_MISMATCH", f"{fresh.get('token_id')}:{fresh.get('state')}")
    if fresh.get("consumed") is not False:
        raise WP10V09InterfaceError("V09_AUTHORITY_EFFECT_ALREADY_CONSUMED", str(fresh.get("consumed")))
    if str(authority_effect.get("provider_fetch", "")) != "DENIED" or str(authority_effect.get("validation_2025", "")) != "LOCKED_UNCONSUMED":
        raise WP10V09InterfaceError("V09_AUTHORITY_EFFECT_FIREWALL_DRIFT", "provider/Validation firewall mismatch")
    reserved = authority_effect.get("reserved_authority")
    if not isinstance(reserved, Mapping) or any(str(value) != "NONE" for value in reserved.values()):
        raise WP10V09InterfaceError("V09_AUTHORITY_EFFECT_EXPANSION", str(reserved))
    return AuthorityEffectTokenView(raw_token, str(fresh["state"]))


def interface_preflight(
    *,
    repo_root: Path,
    manifest: Mapping[str, Any],
    raw_token: Mapping[str, Any],
    authority_effect: Mapping[str, Any],
    execution_freeze: Mapping[str, Any],
) -> dict[str, Any]:
    binding = binding_from_manifest(manifest)
    verify_frozen_execution_runtime(repo_root, execution_freeze)
    view = effective_token_view(raw_token, authority_effect, binding)
    receipt = {
        "schema": "ovc-srfdi-wp10-v09-interface-preflight/v1",
        "status": "PASS",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "run_binding_sha256": binding.logical_hash,
        "execution_binding_sha256": EXECUTION_BINDING_SHA256,
        "execution_binding_merge": EXECUTION_BINDING_MERGE,
        "fresh_token_id": FRESH_TOKEN_ID,
        "effective_token_state": view["state"],
        "raw_token_payload_logical_sha256": view.raw_payload_logical_sha256,
        "token_consumed": False,
        "market_records_read": False,
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "scientific_delta": "NONE",
        "authority_delta": "NONE_USE_EXISTING_OPERATOR_AUTHORIZED_SINGLE_RUN",
    }
    return {**receipt, "logical_hash": logical_sha256(receipt)}


def _verify_full_preflight_receipt(receipt: Mapping[str, Any], binding: RunBindingV09) -> None:
    required = {
        "status": "PASS",
        "run_binding_sha256": binding.logical_hash,
        "frozen_science_status": "PASS",
        "source_binding_status": "PASS",
        "capacity_contract_status": "PASS",
        "execution_binding_status": "PASS",
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise WP10V09InterfaceError("V09_FULL_PREFLIGHT_NOT_PASS", f"{key}:{receipt.get(key)}")
    if receipt.get("token_consumed") is not False:
        raise WP10V09InterfaceError("V09_PREFLIGHT_CONSUMED_TOKEN", str(receipt.get("token_consumed")))


def start_after_exact_preflight(
    *,
    store: RunAuthorityStore,
    repo_root: Path,
    manifest: Mapping[str, Any],
    raw_token: Mapping[str, Any],
    authority_effect: Mapping[str, Any],
    execution_freeze: Mapping[str, Any],
    full_preflight: Callable[[RunBindingV09], Mapping[str, Any]],
) -> tuple[RunStartReceipt, dict[str, Any], dict[str, Any], RunBindingV09]:
    interface_receipt = interface_preflight(
        repo_root=repo_root,
        manifest=manifest,
        raw_token=raw_token,
        authority_effect=authority_effect,
        execution_freeze=execution_freeze,
    )
    binding = binding_from_manifest(manifest)
    full_receipt = dict(full_preflight(binding))
    _verify_full_preflight_receipt(full_receipt, binding)
    view = effective_token_view(raw_token, authority_effect, binding)
    start = store.consume(view, binding)  # type: ignore[arg-type]
    return start, interface_receipt, full_receipt, binding
