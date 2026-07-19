from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence


def descriptive_support_band(count: int) -> str:
    if count < 0:
        raise ValueError("support count cannot be negative")
    if count == 0:
        return "EMPTY"
    if count < 30:
        return "SPARSE_NO_COMPARISON"
    if count < 100:
        return "LIMITED_DESCRIPTIVE_SUPPORT"
    return "ADEQUATE_DESCRIPTIVE_SUPPORT"


def overlap_stratum(overlap: Mapping[str, object]) -> str:
    if not overlap["overlap_present"]:
        return "NO_OVERLAP"
    if int(overlap["subsequent_overlap_anchor_count_same_clock"]) > 0:
        return "SUBSEQUENT_SAME_CLOCK"
    if int(overlap["subsequent_overlap_anchor_count_all_clocks"]) > 0:
        return "SUBSEQUENT_CROSS_CLOCK_ONLY"
    return "SAME_TIME_ONLY"


def measurement_semantic_violations(record: Mapping[str, object]) -> list[str]:
    m = record["measurements"]
    pip = Decimal(str(record["pip_size"]))
    anchor = Decimal(str(record["anchor_price"]))
    endpoint = Decimal(str(m["endpoint_price"]))
    raw = Decimal(str(m["raw_return_price"]))
    upward = Decimal(str(m["maximum_upward_excursion_price"]))
    downward = Decimal(str(m["maximum_downward_excursion_price"]))
    maximum = Decimal(str(m["forward_maximum_price"]))
    minimum = Decimal(str(m["forward_minimum_price"]))
    forward_range = Decimal(str(m["forward_range_price"]))
    horizon_minutes = int(record["horizon_hours"]) * 60
    violations: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            violations.append(code)

    require(endpoint - anchor == raw, "RAW_RETURN_IDENTITY")
    require(Decimal(str(m["raw_return_pips"])) == raw / pip, "RAW_RETURN_PIPS_IDENTITY")
    require(upward >= 0 and downward >= 0, "NEGATIVE_EXCURSION")
    require(maximum - minimum == forward_range and forward_range >= 0, "FORWARD_RANGE_IDENTITY")
    require(maximum - anchor == upward or (maximum < anchor and upward == 0), "UPWARD_EXCURSION_IDENTITY")
    require(anchor - minimum == downward or (minimum > anchor and downward == 0), "DOWNWARD_EXCURSION_IDENTITY")
    require(minimum <= endpoint <= maximum, "ENDPOINT_OUTSIDE_RANGE")
    position = m["endpoint_close_position_in_forward_range"]
    if forward_range == 0:
        require(position is None, "ZERO_RANGE_POSITION_PRESENT")
    else:
        require(position is not None and Decimal(str(position)) == (endpoint - minimum) / forward_range,
                "ENDPOINT_POSITION_IDENTITY")
        require(position is not None and Decimal("0") <= Decimal(str(position)) <= Decimal("1"),
                "ENDPOINT_POSITION_BOUNDS")
    for field in ("maximum_time_elapsed_minutes", "minimum_time_elapsed_minutes"):
        value = int(m[field])
        require(15 <= value <= horizon_minutes and value % 15 == 0, f"{field.upper()}_BOUNDS")

    direction = record["event_direction"]
    normalized_fields = (
        "direction_normalized_endpoint_return_pips",
        "direction_normalized_favorable_excursion_pips",
        "direction_normalized_adverse_excursion_pips",
    )
    if direction in ("UP", "DOWN"):
        require(m["direction_normalization_status"] == "DIRECTIONAL", "DIRECTIONAL_STATUS")
        require(all(m[field] is not None for field in normalized_fields), "DIRECTIONAL_VALUES_MISSING")
        sign = Decimal("1") if direction == "UP" else Decimal("-1")
        favorable = upward if direction == "UP" else downward
        adverse = downward if direction == "UP" else upward
        require(Decimal(str(m[normalized_fields[0]])) == sign * raw / pip, "NORMALIZED_RETURN_IDENTITY")
        require(Decimal(str(m[normalized_fields[1]])) == favorable / pip, "FAVORABLE_IDENTITY")
        require(Decimal(str(m[normalized_fields[2]])) == adverse / pip, "ADVERSE_IDENTITY")
        continued = m["continued_beyond_event_extreme"]
        continuation_time = m["first_continuation_elapsed_minutes"]
        require((continued is True) == (continuation_time is not None), "CONTINUATION_TIME_PRESENCE")
        if continuation_time is not None:
            require(15 <= int(continuation_time) <= horizon_minutes, "CONTINUATION_TIME_BOUNDS")
    else:
        require(m["direction_normalization_status"] == "NOT_DIRECTIONAL", "NON_DIRECTIONAL_STATUS")
        require(all(m[field] is None for field in normalized_fields), "NON_DIRECTIONAL_VALUES_PRESENT")
        require(m["continued_beyond_event_extreme"] is None, "NON_DIRECTIONAL_CONTINUATION_PRESENT")
        require(m["first_continuation_elapsed_minutes"] is None, "NON_DIRECTIONAL_CONTINUATION_TIME_PRESENT")
        require(m["primary_frontier_type"] is None, "NON_DIRECTIONAL_PRIMARY_FRONTIER")

    tests = {item["frontier_type"]: item for item in m["frontier_tests"]}
    require(len(tests) == len(m["frontier_tests"]), "DUPLICATE_FRONTIER_TEST")
    for frontier_type, item in tests.items():
        price = Decimal(str(item["frontier_price"]))
        expected_relation = "ABOVE" if endpoint > price else "BELOW" if endpoint < price else "AT"
        expected_hold = endpoint >= price if frontier_type == "FLOOR" else endpoint <= price
        require(item["endpoint_relation"] == expected_relation, "FRONTIER_ENDPOINT_RELATION")
        require(item["held_at_endpoint"] == expected_hold, "FRONTIER_ENDPOINT_HOLD")
        require((item["retested"] is True) == (item["first_retest_elapsed_minutes"] is not None),
                "FRONTIER_RETEST_TIME_PRESENCE")
        require((item["lost_on_close"] is True) == (item["first_loss_elapsed_minutes"] is not None),
                "FRONTIER_LOSS_TIME_PRESENCE")
        for field in ("first_retest_elapsed_minutes", "first_loss_elapsed_minutes"):
            if item[field] is not None:
                require(15 <= int(item[field]) <= horizon_minutes, f"{field.upper()}_BOUNDS")
    primary_type = m["primary_frontier_type"]
    if primary_type is not None:
        primary = tests.get(primary_type)
        require(primary is not None, "PRIMARY_FRONTIER_TEST_MISSING")
        if primary is not None:
            require(m["primary_frontier_retested"] == primary["retested"], "PRIMARY_RETEST_IDENTITY")
            require(m["primary_frontier_lost_on_close"] == primary["lost_on_close"], "PRIMARY_LOSS_IDENTITY")
            require(m["primary_frontier_held_at_endpoint"] == primary["held_at_endpoint"], "PRIMARY_HOLD_IDENTITY")
            require(m["directional_reversal_through_frontier"] == primary["lost_on_close"],
                    "DIRECTIONAL_REVERSAL_IDENTITY")
    return violations


def nested_horizon_violations(records: Sequence[Mapping[str, object]]) -> list[str]:
    ordered = sorted(records, key=lambda row: int(row["horizon_hours"]))
    violations: list[str] = []
    previous = None
    for row in ordered:
        m = row["measurements"]
        if int(row["path_bar_count"]) != int(row["horizon_hours"]) * 4:
            violations.append("PATH_BAR_COUNT")
        if previous is not None:
            pm = previous["measurements"]
            if Decimal(str(m["maximum_upward_excursion_price"])) < Decimal(
                str(pm["maximum_upward_excursion_price"])
            ):
                violations.append("UPWARD_EXCURSION_NOT_MONOTONE")
            if Decimal(str(m["maximum_downward_excursion_price"])) < Decimal(
                str(pm["maximum_downward_excursion_price"])
            ):
                violations.append("DOWNWARD_EXCURSION_NOT_MONOTONE")
            if int(row["transition_lineage"]["transition_count"]) < int(
                previous["transition_lineage"]["transition_count"]
            ):
                violations.append("TRANSITION_COUNT_NOT_MONOTONE")
            for boolean_field, time_field in (
                ("continued_beyond_event_extreme", "first_continuation_elapsed_minutes"),
                ("primary_frontier_retested", None),
                ("primary_frontier_lost_on_close", None),
            ):
                if pm[boolean_field] is True and m[boolean_field] is not True:
                    violations.append(f"{boolean_field.upper()}_NOT_MONOTONE")
                if time_field and pm[time_field] is not None and m[time_field] != pm[time_field]:
                    violations.append(f"{time_field.upper()}_CHANGED")
            previous_tests = {item["frontier_type"]: item for item in pm["frontier_tests"]}
            current_tests = {item["frontier_type"]: item for item in m["frontier_tests"]}
            for frontier_type, prior_test in previous_tests.items():
                current = current_tests.get(frontier_type)
                if current is None:
                    violations.append("FRONTIER_DISAPPEARED")
                    continue
                for flag, time_field in (
                    ("retested", "first_retest_elapsed_minutes"),
                    ("lost_on_close", "first_loss_elapsed_minutes"),
                ):
                    if prior_test[flag] is True and current[flag] is not True:
                        violations.append(f"FRONTIER_{flag.upper()}_NOT_MONOTONE")
                    if prior_test[time_field] is not None and current[time_field] != prior_test[time_field]:
                        violations.append(f"FRONTIER_{time_field.upper()}_CHANGED")
        previous = row
    return violations
