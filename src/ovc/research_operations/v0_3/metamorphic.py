from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal, localcontext
from typing import Any, Callable, Mapping

ASSURANCE_DECIMAL_PRECISION = 34
PRIOR_NULL_REASONS = {
    "NO_PRIOR_BAR",
    "NO_CONTIGUOUS_PRIOR_BAR",
    "PRIOR_IDENTITY_MISMATCH",
    "PRIOR_NOT_FIRST_VALID",
}


class MetamorphicContractError(ValueError):
    """Raised when the frozen independent invariant canon is malformed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _s(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _q(numerator: Decimal, denominator: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = ASSURANCE_DECIMAL_PRECISION
        return numerator / denominator


def _result_dict(result: Any) -> dict[str, Any]:
    if is_dataclass(result):
        return asdict(result)
    if isinstance(result, Mapping):
        return dict(result)
    raise MetamorphicContractError("engine result must be a dataclass or mapping")


def load_invariant_registry(registry_text: str) -> dict[str, Any]:
    try:
        registry = json.loads(registry_text)
    except json.JSONDecodeError as exc:
        raise MetamorphicContractError("invariant registry must remain canonical JSON") from exc
    if registry.get("registry_id") != "C1.METAMORPHIC.INVARIANTS.v0.1":
        raise MetamorphicContractError("unknown invariant registry identity")
    if registry.get("status") != "FROZEN_AT_RO3_G0":
        raise MetamorphicContractError("invariant registry is not frozen at RO3-G0")
    if registry.get("source_of_expectations") != "INDEPENDENT_CONTRACT_CANON_NOT_IMPLEMENTATION":
        raise MetamorphicContractError("invariant expectations are not independent")
    invariants = registry.get("invariants")
    if registry.get("formula_count") != 18 or not isinstance(invariants, list) or len(invariants) != 18:
        raise MetamorphicContractError("invariant registry must cover exactly 18 formulas")
    primitive_ids = [str(item.get("primitive_id")) for item in invariants]
    if len(set(primitive_ids)) != 18:
        raise MetamorphicContractError("invariant primitive IDs must be unique")
    if any(not item.get("relations") for item in invariants):
        raise MetamorphicContractError("every primitive requires at least one relation")
    logical = dict(registry)
    return {**logical, "registry_logical_sha256": _digest(logical)}


def _transform_bar(
    current: Mapping[str, Any],
    prior: Mapping[str, Any] | None,
    transform_id: str,
    parameter: Decimal | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    transformed = dict(current)
    transformed_prior = None if prior is None else dict(prior)

    def apply_prices(payload: dict[str, Any], operation: Callable[[Decimal], Decimal]) -> None:
        for field in ("open", "high", "low", "close"):
            payload[field] = _s(operation(Decimal(str(payload[field]))))

    if transform_id == "PRICE_TRANSLATION":
        offset = parameter if parameter is not None else Decimal("0.125")
        apply_prices(transformed, lambda value: value + offset)
        if transformed_prior is not None:
            apply_prices(transformed_prior, lambda value: value + offset)
    elif transform_id in {"PRICE_REFLECTION", "WICK_SWAP_REFLECTION"}:
        centre = parameter if parameter is not None else Decimal("2")
        for payload in (transformed, transformed_prior):
            if payload is None:
                continue
            old = {field: Decimal(str(payload[field])) for field in ("open", "high", "low", "close")}
            payload["open"] = _s(centre * 2 - old["open"])
            payload["close"] = _s(centre * 2 - old["close"])
            payload["high"] = _s(centre * 2 - old["low"])
            payload["low"] = _s(centre * 2 - old["high"])
    elif transform_id == "UP_DOWN_REVERSAL":
        transformed["open"], transformed["close"] = transformed["close"], transformed["open"]
    elif transform_id == "POSITIVE_SCALE":
        factor = parameter if parameter is not None else Decimal("10")
        if factor <= 0:
            raise MetamorphicContractError("scale factor must be positive")
        for payload in (transformed, transformed_prior):
            if payload is None:
                continue
            apply_prices(payload, lambda value: value * factor)
            if payload.get("price_increment") is not None:
                payload["price_increment"] = _s(Decimal(str(payload["price_increment"])) * factor)
    elif transform_id == "ZERO_RANGE":
        anchor = transformed["open"]
        for field in ("open", "high", "low", "close"):
            transformed[field] = anchor
    elif transform_id == "REMOVE_CONTIGUOUS_PRIOR":
        transformed_prior = None
    elif transform_id == "CANONICAL_REORDER":
        transformed = dict(reversed(list(transformed.items())))
        if transformed_prior is not None:
            transformed_prior = dict(reversed(list(transformed_prior.items())))
    else:
        raise MetamorphicContractError(f"unknown transform: {transform_id}")
    return transformed, transformed_prior


def contract_oracle(current: Mapping[str, Any], prior: Mapping[str, Any] | None) -> dict[str, Any]:
    """Independent fixture-only oracle derived from the frozen formula registry."""

    o = Decimal(str(current["open"]))
    h = Decimal(str(current["high"]))
    l = Decimal(str(current["low"]))
    c = Decimal(str(current["close"]))
    increment = None if current.get("price_increment") is None else Decimal(str(current["price_increment"]))
    r = h - l
    body = c - o
    upper = h - max(o, c)
    lower = min(o, c) - l
    measurements: dict[str, str | None] = {
        "range_abs": _s(r),
        "range_ticks": _s(_q(r, increment)) if increment else None,
        "body_signed": _s(body),
        "body_abs": _s(abs(body)),
        "body_utilisation": _s(_q(abs(body), r)) if r else None,
        "upper_wick_abs": _s(upper),
        "lower_wick_abs": _s(lower),
        "upper_wick_share": _s(_q(upper, r)) if r else None,
        "lower_wick_share": _s(_q(lower, r)) if r else None,
        "wick_balance": _s(_q(upper - lower, r)) if r else None,
        "open_location": _s(_q(o - l, r)) if r else None,
        "close_location": _s(_q(c - l, r)) if r else None,
        "signed_efficiency": _s(_q(body, r)) if r else None,
        "true_range_abs": None,
        "true_range_ticks": None,
        "close_change": None,
        "open_gap": None,
    }
    null_reasons: dict[str, str] = {}
    if increment is None:
        null_reasons["range_ticks"] = "PRICE_INCREMENT_UNAVAILABLE"
    if not r:
        for field in (
            "body_utilisation", "upper_wick_share", "lower_wick_share", "wick_balance",
            "open_location", "close_location", "signed_efficiency",
        ):
            null_reasons[field] = "ZERO_RANGE"
    if prior is None:
        for field in ("true_range_abs", "true_range_ticks", "close_change", "open_gap"):
            null_reasons[field] = "NO_PRIOR_BAR"
    else:
        prior_close = Decimal(str(prior["close"]))
        true_range = max(r, abs(h - prior_close), abs(l - prior_close))
        measurements["true_range_abs"] = _s(true_range)
        measurements["true_range_ticks"] = _s(_q(true_range, increment)) if increment else None
        measurements["close_change"] = _s(c - prior_close)
        measurements["open_gap"] = _s(o - prior_close)
        if increment is None:
            null_reasons["true_range_ticks"] = "PRICE_INCREMENT_UNAVAILABLE"
    return {
        "measurements": measurements,
        "categorical": {"direction": "UP" if body > 0 else "DOWN" if body < 0 else "FLAT"},
        "null_reasons": null_reasons,
    }


def _field_value(result: Mapping[str, Any], field_name: str) -> Any:
    if field_name == "direction":
        return result["categorical"].get(field_name)
    return result["measurements"].get(field_name)


def _relation_assertion(
    primitive_id: str,
    field_name: str,
    relation: str,
    base: Mapping[str, Any],
    transformed: Mapping[str, Any],
    factor: Decimal,
    primitive_to_field: Mapping[str, str],
) -> dict[str, Any]:
    transform_id, expectation = relation.split(":", 1)
    base_value = _field_value(base, field_name)
    transformed_value = _field_value(transformed, field_name)
    status = "PASS"
    detail = ""

    if expectation == "EQUAL":
        status = "PASS" if transformed_value == base_value else "FAIL"
    elif expectation == "SCALE":
        expected = None if base_value is None else _s(Decimal(base_value) * factor)
        status = "PASS" if transformed_value == expected else "FAIL"
    elif expectation == "SIGN_REVERSE":
        expected = None if base_value is None else _s(-Decimal(base_value))
        status = "PASS" if transformed_value == expected else "FAIL"
    elif expectation == "COMPLEMENT":
        expected = None if base_value is None else _s(Decimal("1") - Decimal(base_value))
        status = "PASS" if transformed_value == expected else "FAIL"
    elif expectation == "SWAP_WITH_LOWER":
        counterpart = "lower_wick_abs" if field_name == "upper_wick_abs" else "lower_wick_share"
        status = "PASS" if transformed_value == _field_value(base, counterpart) else "FAIL"
    elif expectation == "SWAP_WITH_UPPER":
        counterpart = "upper_wick_abs" if field_name == "lower_wick_abs" else "upper_wick_share"
        status = "PASS" if transformed_value == _field_value(base, counterpart) else "FAIL"
    elif expectation in {"UP_DOWN_SWAP_FLAT_INVARIANT", "UP_DOWN_ENUM_SWAP_FLAT_INVARIANT"}:
        expected = {"UP": "DOWN", "DOWN": "UP", "FLAT": "FLAT"}.get(base_value)
        status = "PASS" if transformed_value == expected else "FAIL"
    elif expectation == "ZERO":
        status = "PASS" if transformed_value == "0" else "FAIL"
    elif expectation == "ZERO_IF_INCREMENT_AVAILABLE":
        status = "PASS" if transformed_value == "0" else "FAIL"
    elif expectation == "FLAT":
        status = "PASS" if transformed_value == "FLAT" else "FAIL"
    elif expectation == "NULL_ZERO_RANGE":
        reason = transformed["null_reasons"].get(field_name)
        status = "PASS" if transformed_value is None and reason == "ZERO_RANGE" else "FAIL"
    elif expectation in {"NULL_PRIOR_CLOSE_REQUIRED", "NULL_PRIOR_CLOSE_AND_PRICE_INCREMENT_REQUIRED"}:
        reason = transformed["null_reasons"].get(field_name)
        status = "PASS" if transformed_value is None and reason in PRIOR_NULL_REASONS else "FAIL"
    else:
        raise MetamorphicContractError(f"unknown relation expectation: {expectation}")

    if status == "FAIL":
        detail = f"base={base_value!r}; transformed={transformed_value!r}; expectation={expectation}"
    assertion = {
        "primitive_id": primitive_id,
        "field_name": field_name,
        "transform_id": transform_id,
        "expectation": expectation,
        "status": status,
        "detail": detail,
    }
    return {**assertion, "assertion_id": f"ro3-c1-metamorphic-assertion:{_digest(assertion)}"}


def run_metamorphic_assurance(
    registry: Mapping[str, Any],
    formula_registry: Mapping[str, Any],
    engine: Callable[[dict[str, Any], dict[str, Any] | None], Any],
    current: Mapping[str, Any],
    prior: Mapping[str, Any] | None,
    serializer: Callable[[Any], str] | None = None,
) -> dict[str, Any]:
    formulas = {str(item["primitive_id"]): dict(item) for item in formula_registry["formulas"]}
    invariants = {str(item["primitive_id"]): list(item["relations"]) for item in registry["invariants"]}
    if set(formulas) != set(invariants):
        raise MetamorphicContractError("formula and invariant primitive sets differ")
    primitive_to_field = {primitive_id: str(item["field_name"]) for primitive_id, item in formulas.items()}

    base_result_object = engine(dict(current), None if prior is None else dict(prior))
    base = _result_dict(base_result_object)
    transform_cache: dict[str, dict[str, Any]] = {}
    scale_factor = Decimal("10")
    for transform_id in registry["transforms"]:
        parameter = scale_factor if transform_id == "POSITIVE_SCALE" else None
        changed_current, changed_prior = _transform_bar(current, prior, transform_id, parameter)
        transform_cache[transform_id] = _result_dict(engine(changed_current, changed_prior))

    assertions: list[dict[str, Any]] = []
    for primitive_id in sorted(invariants):
        field_name = primitive_to_field[primitive_id]
        for relation in invariants[primitive_id]:
            transform_id = relation.split(":", 1)[0]
            assertions.append(
                _relation_assertion(
                    primitive_id, field_name, relation, base, transform_cache[transform_id],
                    scale_factor, primitive_to_field,
                )
            )

    oracle = contract_oracle(current, prior)
    oracle_assertions: list[dict[str, Any]] = []
    for primitive_id in sorted(formulas):
        field_name = primitive_to_field[primitive_id]
        actual = _field_value(base, field_name)
        expected = _field_value(oracle, field_name)
        status = "PASS" if actual == expected else "FAIL"
        item = {
            "primitive_id": primitive_id,
            "field_name": field_name,
            "actual": actual,
            "expected": expected,
            "status": status,
        }
        oracle_assertions.append({**item, "assertion_id": f"ro3-c1-golden-assertion:{_digest(item)}"})

    reorder_current, reorder_prior = _transform_bar(current, prior, "CANONICAL_REORDER")
    reordered_object = engine(reorder_current, reorder_prior)
    if serializer is None:
        serialization_pass = _canonical(_result_dict(base_result_object)) == _canonical(_result_dict(reordered_object))
        base_bytes = _canonical(_result_dict(base_result_object))
        rerun_bytes = _canonical(_result_dict(engine(dict(current), None if prior is None else dict(prior))))
    else:
        base_bytes = serializer(base_result_object).encode("utf-8")
        serialization_pass = serializer(reordered_object).encode("utf-8") == base_bytes
        rerun_bytes = serializer(engine(dict(current), None if prior is None else dict(prior))).encode("utf-8")

    determinism_receipt = {
        "schema": "ovc-ro3-c1-determinism-receipt/v1",
        "base_sha256": hashlib.sha256(base_bytes).hexdigest(),
        "rerun_sha256": hashlib.sha256(rerun_bytes).hexdigest(),
        "same_input_same_output_bytes": base_bytes == rerun_bytes,
        "canonical_reorder_identical": serialization_pass,
        "writes": "NONE",
    }
    determinism_receipt["receipt_id"] = f"ro3-c1-determinism:{_digest(determinism_receipt)}"

    failed = [item for item in assertions + oracle_assertions if item["status"] != "PASS"]
    if not determinism_receipt["same_input_same_output_bytes"] or not determinism_receipt["canonical_reorder_identical"]:
        failed.append({"status": "FAIL", "primitive_id": "GLOBAL", "field_name": "serialization", "detail": "determinism or canonical reorder failure"})
    result = {
        "schema": "ovc-ro3-c1-metamorphic-run/v1",
        "registry_id": registry["registry_id"],
        "registry_logical_sha256": registry["registry_logical_sha256"],
        "formula_registry_id": formula_registry["registry_id"],
        "formula_registry_logical_sha256": formula_registry["registry_logical_sha256"],
        "primitive_count": len(formulas),
        "metamorphic_assertion_count": len(assertions),
        "golden_assertion_count": len(oracle_assertions),
        "metamorphic_assertions": assertions,
        "golden_assertions": oracle_assertions,
        "determinism_receipt": determinism_receipt,
        "failed_assertion_count": len(failed),
        "failed_assertions": failed,
        "status": "PASS" if not failed else "BLOCK",
        "authority_effect": "QA_EVIDENCE_ONLY",
        "writes": "NONE",
    }
    return {**result, "run_id": f"ro3-c1-metamorphic-run:{_digest(result)}"}
