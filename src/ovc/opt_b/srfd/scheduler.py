from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_sha256, stable_id


CAPACITY_STATUSES = frozenset({
    "SUPPORTED_T0",
    "SUPPORTED_T1",
    "METHOD_CAPACITY_UNSUPPORTED_AT_T0",
    "REQUIRES_SEPARATE_CAPACITY_TIER",
    "CAPACITY_UNRESOLVED",
    "CAPACITY_EXCEEDED_AT_MEASUREMENT",
})
MEASUREMENT_CLASSES = frozenset({
    "MEASURED",
    "INTERPOLATED",
    "EXTRAPOLATED",
    "THEORETICAL_BOUND",
    "UNRESOLVED",
})


class CapacityScheduleError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class CapacityBudget:
    tier_id: str
    max_wall_seconds: Decimal
    max_rss_bytes: int
    max_external_bytes: int

    @classmethod
    def from_values(
        cls,
        tier_id: str,
        *,
        max_wall_seconds: str | Decimal,
        max_rss_bytes: int,
        max_external_bytes: int,
    ) -> "CapacityBudget":
        tier = str(tier_id).strip().upper()
        if not tier:
            raise CapacityScheduleError("CAP_INVALID_BUDGET", "tier_id required")
        wall = Decimal(str(max_wall_seconds))
        if wall <= 0 or max_rss_bytes <= 0 or max_external_bytes <= 0:
            raise CapacityScheduleError("CAP_INVALID_BUDGET", tier)
        return cls(tier, wall, int(max_rss_bytes), int(max_external_bytes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier_id": self.tier_id,
            "max_wall_seconds": format(self.max_wall_seconds, "f"),
            "max_rss_bytes": self.max_rss_bytes,
            "max_external_bytes": self.max_external_bytes,
        }


@dataclass(frozen=True)
class ResourceContract:
    node_id: str
    node_type: str
    method_id: str | None
    configuration_id: str | None
    dependency_ids: tuple[str, ...]
    wall_seconds: Decimal | None
    peak_rss_bytes: int | None
    external_bytes: int | None
    measurement_class: str
    reusable: bool = False
    required: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ResourceContract":
        node_id = str(value.get("node_id", "")).strip()
        node_type = str(value.get("node_type", "")).strip().upper()
        if not node_id or not node_type:
            raise CapacityScheduleError("CAP_INVALID_RESOURCE_CONTRACT", "node identity required")
        measurement_class = str(value.get("measurement_class", "UNRESOLVED")).strip().upper()
        if measurement_class not in MEASUREMENT_CLASSES:
            raise CapacityScheduleError("CAP_INVALID_RESOURCE_CONTRACT", f"invalid measurement class {measurement_class}")
        dependencies = tuple(str(item).strip() for item in value.get("dependency_ids", ()))
        if any(not item for item in dependencies) or len(dependencies) != len(set(dependencies)):
            raise CapacityScheduleError("CAP_INVALID_RESOURCE_CONTRACT", f"invalid dependencies for {node_id}")

        def decimal_or_none(raw: Any) -> Decimal | None:
            if raw is None:
                return None
            number = Decimal(str(raw))
            if number < 0:
                raise CapacityScheduleError("CAP_INVALID_RESOURCE_CONTRACT", f"negative resource value for {node_id}")
            return number

        def int_or_none(raw: Any) -> int | None:
            if raw is None:
                return None
            number = int(raw)
            if number < 0:
                raise CapacityScheduleError("CAP_INVALID_RESOURCE_CONTRACT", f"negative resource value for {node_id}")
            return number

        return cls(
            node_id=node_id,
            node_type=node_type,
            method_id=str(value["method_id"]).strip() if value.get("method_id") is not None else None,
            configuration_id=str(value["configuration_id"]).strip() if value.get("configuration_id") is not None else None,
            dependency_ids=dependencies,
            wall_seconds=decimal_or_none(value.get("wall_seconds")),
            peak_rss_bytes=int_or_none(value.get("peak_rss_bytes")),
            external_bytes=int_or_none(value.get("external_bytes")),
            measurement_class=measurement_class,
            reusable=bool(value.get("reusable", False)),
            required=bool(value.get("required", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "method_id": self.method_id,
            "configuration_id": self.configuration_id,
            "dependency_ids": list(self.dependency_ids),
            "wall_seconds": format(self.wall_seconds, "f") if self.wall_seconds is not None else None,
            "peak_rss_bytes": self.peak_rss_bytes,
            "external_bytes": self.external_bytes,
            "measurement_class": self.measurement_class,
            "reusable": self.reusable,
            "required": self.required,
        }


@dataclass(frozen=True)
class CapacityStatus:
    node_id: str
    status: str
    reason: str
    measurement_class: str
    tier_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "reason": self.reason,
            "measurement_class": self.measurement_class,
            "tier_id": self.tier_id,
            "scientific_effect": "NONE",
        }


def _fits(contract: ResourceContract, budget: CapacityBudget) -> bool | None:
    values = (contract.wall_seconds, contract.peak_rss_bytes, contract.external_bytes)
    if any(value is None for value in values):
        return None
    assert contract.wall_seconds is not None
    assert contract.peak_rss_bytes is not None
    assert contract.external_bytes is not None
    return (
        contract.wall_seconds <= budget.max_wall_seconds
        and contract.peak_rss_bytes <= budget.max_rss_bytes
        and contract.external_bytes <= budget.max_external_bytes
    )


def classify_capacity_status(
    contract: ResourceContract,
    *,
    t0: CapacityBudget,
    t1: CapacityBudget,
    measured_exceeded: bool = False,
) -> CapacityStatus:
    if measured_exceeded:
        return CapacityStatus(
            contract.node_id,
            "CAPACITY_EXCEEDED_AT_MEASUREMENT",
            "MEASURED_RUN_CROSSED_DECLARED_RESOURCE_BOUND",
            contract.measurement_class,
            None,
        )
    fit_t0 = _fits(contract, t0)
    fit_t1 = _fits(contract, t1)
    if fit_t0 is None:
        return CapacityStatus(
            contract.node_id,
            "CAPACITY_UNRESOLVED",
            "RESOURCE_EVIDENCE_INCOMPLETE",
            contract.measurement_class,
            None,
        )
    if fit_t0:
        return CapacityStatus(
            contract.node_id,
            "SUPPORTED_T0",
            "WITHIN_T0_RESOURCE_CONTRACT",
            contract.measurement_class,
            t0.tier_id,
        )
    if fit_t1:
        status = (
            "METHOD_CAPACITY_UNSUPPORTED_AT_T0"
            if contract.node_type == "FAMILY_METHOD"
            else "SUPPORTED_T1"
        )
        return CapacityStatus(
            contract.node_id,
            status,
            "OUTSIDE_T0_WITHIN_T1_RESOURCE_CONTRACT",
            contract.measurement_class,
            t1.tier_id,
        )
    return CapacityStatus(
        contract.node_id,
        "REQUIRES_SEPARATE_CAPACITY_TIER",
        "OUTSIDE_T0_AND_T1_RESOURCE_CONTRACT",
        contract.measurement_class,
        None,
    )


def _topological_order(contracts: Mapping[str, ResourceContract]) -> tuple[str, ...]:
    for contract in contracts.values():
        missing = sorted(set(contract.dependency_ids) - set(contracts))
        if missing:
            raise CapacityScheduleError(
                "CAP_DEPENDENCY_MISSING",
                f"{contract.node_id}:{','.join(missing)}",
            )
    incoming = {node_id: set(item.dependency_ids) for node_id, item in contracts.items()}
    ready = sorted(node_id for node_id, deps in incoming.items() if not deps)
    output: list[str] = []
    while ready:
        node_id = ready.pop(0)
        output.append(node_id)
        for candidate in sorted(incoming):
            if node_id in incoming[candidate]:
                incoming[candidate].remove(node_id)
                if not incoming[candidate] and candidate not in output and candidate not in ready:
                    ready.append(candidate)
                    ready.sort()
    if len(output) != len(contracts):
        unresolved = sorted(set(contracts) - set(output))
        raise CapacityScheduleError("CAP_DEPENDENCY_CYCLE", ",".join(unresolved))
    return tuple(output)


def build_capacity_plan(
    resource_contracts: Iterable[Mapping[str, Any] | ResourceContract],
    *,
    required_method_configurations: Sequence[tuple[str, str]],
    t0: CapacityBudget,
    t1: CapacityBudget,
    measured_exceeded_nodes: Sequence[str] = (),
) -> dict[str, Any]:
    parsed: list[ResourceContract] = []
    for item in resource_contracts:
        parsed.append(item if isinstance(item, ResourceContract) else ResourceContract.from_mapping(item))
    by_id = {item.node_id: item for item in parsed}
    if len(by_id) != len(parsed):
        raise CapacityScheduleError("CAP_DUPLICATE_NODE", "node_id must be unique")

    expected = {(str(method), str(config)) for method, config in required_method_configurations}
    present = {
        (item.method_id, item.configuration_id)
        for item in parsed
        if item.node_type == "FAMILY_METHOD" and item.required
    }
    missing_method_configs = sorted(expected - present)
    unexpected_method_configs = sorted(present - expected)
    if missing_method_configs or unexpected_method_configs:
        raise CapacityScheduleError(
            "CAP_METHOD_CONFIG_INCOMPLETE",
            f"missing={missing_method_configs};unexpected={unexpected_method_configs}",
        )

    order = _topological_order(by_id)
    exceeded = set(measured_exceeded_nodes)
    unknown_exceeded = sorted(exceeded - set(by_id))
    if unknown_exceeded:
        raise CapacityScheduleError("CAP_UNKNOWN_MEASUREMENT_NODE", ",".join(unknown_exceeded))

    statuses = {
        node_id: classify_capacity_status(
            by_id[node_id],
            t0=t0,
            t1=t1,
            measured_exceeded=node_id in exceeded,
        )
        for node_id in order
    }

    blocked_nodes: dict[str, str] = {}
    for node_id in order:
        dependency_blockers = [
            dependency
            for dependency in by_id[node_id].dependency_ids
            if statuses[dependency].status
            in {
                "REQUIRES_SEPARATE_CAPACITY_TIER",
                "CAPACITY_UNRESOLVED",
                "CAPACITY_EXCEEDED_AT_MEASUREMENT",
            }
        ]
        if dependency_blockers:
            blocked_nodes[node_id] = "DEPENDENCY_CAPACITY_UNRESOLVED:" + ",".join(dependency_blockers)

    total_core_proxy_seconds = sum(
        (item.wall_seconds for item in parsed if item.wall_seconds is not None),
        Decimal("0"),
    )
    max_peak_rss = max((item.peak_rss_bytes or 0 for item in parsed), default=0)
    unique_external_bytes = sum(
        item.external_bytes or 0 for item in parsed if not item.reusable
    ) + sum(
        item.external_bytes or 0
        for item in parsed
        if item.reusable
    )

    payload: dict[str, Any] = {
        "schema": "ovc-srfdi-g8r-capacity-plan/v1",
        "authority_state": "FIXTURE_LOCAL_CAPACITY_REMEDIATION_ONLY",
        "scientific_effect": "NONE",
        "required_method_configurations": [
            {"method_id": method, "configuration_id": config}
            for method, config in sorted(expected)
        ],
        "execution_order": list(order),
        "resource_contracts": [by_id[node_id].to_dict() for node_id in order],
        "capacity_statuses": [statuses[node_id].to_dict() for node_id in order],
        "blocked_nodes": blocked_nodes,
        "diagnostic_resource_sums": {
            "wall_seconds_sum_not_makespan": format(total_core_proxy_seconds, "f"),
            "max_node_peak_rss_bytes": max_peak_rss,
            "declared_external_bytes_sum": unique_external_bytes,
        },
        "budget_tiers": [t0.to_dict(), t1.to_dict()],
        "partial_benchmark_escape_hatch": "PROHIBITED",
        "scientific_scope_change_on_capacity_failure": "PROHIBITED",
        "june_market_records_read": False,
        "validation_consumed": False,
    }
    return {
        **payload,
        "plan_id": stable_id("SRFD.G8R.CAPACITY.PLAN.", payload),
        "logical_hash": logical_sha256(payload),
    }


def controlled_capacity_failure(
    *,
    node_id: str,
    status: str,
    measured: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = str(status).strip().upper()
    if normalized not in CAPACITY_STATUSES:
        raise CapacityScheduleError("CAP_INVALID_STATUS", normalized)
    if normalized in {"SUPPORTED_T0", "SUPPORTED_T1"}:
        raise CapacityScheduleError("CAP_INVALID_FAILURE", "supported status cannot be emitted as failure")
    payload = {
        "schema": "ovc-srfdi-g8r-controlled-capacity-failure/v1",
        "node_id": str(node_id),
        "status": normalized,
        "measured": dict(measured or {}),
        "action": "STOP_NODE_PRESERVE_EVIDENCE_DO_NOT_DROP_METHOD",
        "scientific_effect": "NONE",
        "partial_benchmark_escape_hatch": "PROHIBITED",
        "authority_effect": "NONE",
    }
    return {**payload, "failure_id": stable_id("SRFD.G8R.CAP.FAIL.", payload)}
