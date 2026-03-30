from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable


StrategyFn = Callable[[int, list[int], random.Random], list[int]]


@dataclass(frozen=True)
class MatchResult:
    player_1_strategy: str
    player_2_strategy: str
    player_1_allocation: list[int]
    player_2_allocation: list[int]
    battlefield_values: list[int]
    player_1_score: float
    player_2_score: float
    winner: int

    @property
    def score_margin(self) -> float:
        return self.player_1_score - self.player_2_score


def allocate_weighted_budget(
    troops: int,
    weights: list[float],
    rng: random.Random,
) -> list[int]:
    total_weight = sum(weights)
    if troops < 0:
        raise ValueError("troops must be non-negative")
    if not weights:
        raise ValueError("weights must not be empty")
    if total_weight <= 0:
        raise ValueError("weights must sum to a positive value")

    raw_allocations = [(troops * weight) / total_weight for weight in weights]
    allocations = [int(value) for value in raw_allocations]
    remainder = troops - sum(allocations)

    ranked_indices = sorted(
        range(len(weights)),
        key=lambda idx: (raw_allocations[idx] - allocations[idx], rng.random()),
        reverse=True,
    )

    for idx in ranked_indices[:remainder]:
        allocations[idx] += 1

    return allocations


def random_partition_strategy(
    troops: int,
    battlefield_values: list[int],
    rng: random.Random,
) -> list[int]:
    if len(battlefield_values) == 1:
        return [troops]

    cuts = sorted(rng.randint(0, troops) for _ in range(len(battlefield_values) - 1))
    points = [0, *cuts, troops]
    return [points[i + 1] - points[i] for i in range(len(points) - 1)]


def uniform_strategy(
    troops: int,
    battlefield_values: list[int],
    rng: random.Random,
) -> list[int]:
    battlefields = len(battlefield_values)
    base = troops // battlefields
    remainder = troops % battlefields
    allocations = [base] * battlefields

    for idx in rng.sample(range(battlefields), remainder):
        allocations[idx] += 1

    return allocations


def weighted_value_strategy(
    troops: int,
    battlefield_values: list[int],
    rng: random.Random,
) -> list[int]:
    return allocate_weighted_budget(
        troops=troops,
        weights=[float(value) for value in battlefield_values],
        rng=rng,
    )


def top_heavy_strategy(
    troops: int,
    battlefield_values: list[int],
    rng: random.Random,
) -> list[int]:
    max_value = max(battlefield_values)
    boosted_weights = []

    for value in battlefield_values:
        if value == max_value:
            boosted_weights.append(float(value) * 2.5)
        else:
            boosted_weights.append(max(float(value) * 0.5, 0.1))

    return allocate_weighted_budget(troops=troops, weights=boosted_weights, rng=rng)


STRATEGIES: dict[str, StrategyFn] = {
    "uniform": uniform_strategy,
    "weighted_value": weighted_value_strategy,
    "top_heavy": top_heavy_strategy,
    "random_partition": random_partition_strategy,
}


def score_allocations(
    allocation_1: list[int],
    allocation_2: list[int],
    battlefield_values: list[int],
) -> tuple[float, float]:
    player_1_score = 0.0
    player_2_score = 0.0

    for troops_1, troops_2, value in zip(
        allocation_1,
        allocation_2,
        battlefield_values,
        strict=True,
    ):
        if troops_1 > troops_2:
            player_1_score += value
        elif troops_2 > troops_1:
            player_2_score += value
        else:
            player_1_score += value / 2
            player_2_score += value / 2

    return player_1_score, player_2_score


def simulate_match(
    player_1_strategy: str,
    player_2_strategy: str,
    troops: int,
    battlefield_values: list[int],
    rng: random.Random | None = None,
) -> MatchResult:
    if troops <= 0:
        raise ValueError("troops must be positive")
    if not battlefield_values:
        raise ValueError("battlefield_values must not be empty")
    if player_1_strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy: {player_1_strategy}")
    if player_2_strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy: {player_2_strategy}")

    rng = rng or random.Random()

    allocation_1 = STRATEGIES[player_1_strategy](troops, battlefield_values, rng)
    allocation_2 = STRATEGIES[player_2_strategy](troops, battlefield_values, rng)

    if sum(allocation_1) != troops or sum(allocation_2) != troops:
        raise ValueError("strategy produced an invalid allocation")

    player_1_score, player_2_score = score_allocations(
        allocation_1=allocation_1,
        allocation_2=allocation_2,
        battlefield_values=battlefield_values,
    )

    if player_1_score > player_2_score:
        winner = 1
    elif player_2_score > player_1_score:
        winner = 2
    else:
        winner = 0

    return MatchResult(
        player_1_strategy=player_1_strategy,
        player_2_strategy=player_2_strategy,
        player_1_allocation=allocation_1,
        player_2_allocation=allocation_2,
        battlefield_values=battlefield_values[:],
        player_1_score=player_1_score,
        player_2_score=player_2_score,
        winner=winner,
    )
