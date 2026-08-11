from __future__ import annotations

from typing import Any, Mapping

from ovc.development.identity import canonical_sha256


class EnvironmentManifestError(ValueError):
    pass


_ALLOWED_REPRO = {"EXACT_LOCKED", "REPRODUCIBLE_LOCAL", "PARTIAL", "NON_REPRODUCIBLE"}


def build_execution_environment_manifest(
    *,
    os_name: str,
    architecture: str,
    python_version: str,
    toolchain: Mapping[str, str],
    lockfile_sha256: str | None,
    base_environment_id: str | None,
    reproducibility_class: str,
) -> dict[str, Any]:
    if reproducibility_class not in _ALLOWED_REPRO:
        raise EnvironmentManifestError("reproducibility_class must be explicit and supported")
    payload = {
        "os_name": os_name,
        "architecture": architecture,
        "python_version": python_version,
        "toolchain": {key: toolchain[key] for key in sorted(toolchain)},
        "lockfile_sha256": lockfile_sha256,
        "base_environment_id": base_environment_id,
        "reproducibility_class": reproducibility_class,
    }
    if not all([os_name, architecture, python_version]):
        raise EnvironmentManifestError("os_name, architecture and python_version are required")
    return {
        "schema": "ovc-dsai-execution-environment-manifest/v1",
        "environment_id": canonical_sha256(payload, role="EXECUTION_ENVIRONMENT"),
        **payload,
        "authority_effect": "NONE",
    }
