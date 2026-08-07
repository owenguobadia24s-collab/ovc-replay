from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence


class PairIndexError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def exact_pair_count(population_count: int) -> int:
    if population_count < 0:
        raise PairIndexError("G8R_PAIR_INVALID_POPULATION", "population_count must be non-negative")
    return population_count * (population_count - 1) // 2


def row_start(i: int, n: int) -> int:
    if n < 0 or i < 0 or i > n:
        raise PairIndexError("G8R_PAIR_INVALID_INDEX", f"row {i} outside n={n}")
    if i == n:
        return exact_pair_count(n)
    return i * (2 * n - i - 1) // 2


def pair_to_index(i: int, j: int, n: int) -> int:
    if n < 0 or not (0 <= i < j < n):
        raise PairIndexError("G8R_PAIR_INVALID_INDEX", f"require 0 <= i < j < n, got i={i}, j={j}, n={n}")
    return row_start(i, n) + (j - i - 1)


def index_to_pair(k: int, n: int) -> tuple[int, int]:
    total = exact_pair_count(n)
    if k < 0 or k >= total:
        raise PairIndexError("G8R_PAIR_INVALID_INDEX", f"pair index {k} outside [0,{total})")
    low, high = 0, n - 1
    while low < high:
        mid = (low + high + 1) // 2
        if row_start(mid, n) <= k:
            low = mid
        else:
            high = mid - 1
    i = low
    offset = k - row_start(i, n)
    j = i + 1 + offset
    if not (0 <= i < j < n):
        raise PairIndexError("G8R_PAIR_BIJECTION_FAILURE", f"reconstructed invalid pair for k={k}, n={n}")
    return i, j


@dataclass(frozen=True, order=True)
class PairRange:
    k_start: int
    k_end: int

    @property
    def count(self) -> int:
        return self.k_end - self.k_start

    def validate(self, total_pairs: int) -> None:
        if self.k_start < 0 or self.k_end < self.k_start or self.k_end > total_pairs:
            raise PairIndexError("G8R_PAIR_INVALID_RANGE", f"invalid [{self.k_start},{self.k_end}) for {total_pairs}")


def pair_ranges(population_count: int, *, tile_pair_count: int) -> tuple[PairRange, ...]:
    if tile_pair_count < 1:
        raise PairIndexError("G8R_PAIR_INVALID_TILE_SIZE", "tile_pair_count must be positive")
    total = exact_pair_count(population_count)
    return tuple(
        PairRange(start, min(total, start + tile_pair_count))
        for start in range(0, total, tile_pair_count)
    )


def iter_pairs(population_count: int, pair_range: PairRange | None = None) -> Iterator[tuple[int, int, int]]:
    total = exact_pair_count(population_count)
    active = pair_range or PairRange(0, total)
    active.validate(total)
    for k in range(active.k_start, active.k_end):
        i, j = index_to_pair(k, population_count)
        yield k, i, j


def canonical_ids(values: Iterable[str]) -> tuple[str, ...]:
    ids = tuple(sorted(str(value) for value in values))
    if any(not value for value in ids):
        raise PairIndexError("G8R_PAIR_INVALID_ID", "empty object identifier")
    if len(ids) != len(set(ids)):
        raise PairIndexError("G8R_PAIR_DUPLICATE_ID", "duplicate object identifier")
    return ids


def pair_endpoints(ids: Sequence[str], k: int) -> tuple[str, str]:
    i, j = index_to_pair(k, len(ids))
    return str(ids[i]), str(ids[j])
