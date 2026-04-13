from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from blotto import STRATEGIES, MatchResult, simulate_match

@dataclass(frozen=True)
class Scenario:
    name: str
    troops: int
    battlefield_values: list[int]
    matches_per_pairing: int

    @property
    def battlefields(self) -> int:
        return len(self.battlefield_values)

    @property
    def total_battlefield_value(self) -> int:
        return sum(self.battlefield_values)


DEFAULT_SCENARIOS = [
    Scenario(name="small", troops=15, battlefield_values=[1, 2, 3, 4], matches_per_pairing=150),
    Scenario(name="baseline", troops=20, battlefield_values=[1, 2, 3, 4, 5], matches_per_pairing=250),
    Scenario(name="medium", troops=30, battlefield_values=[1, 2, 3, 4, 5, 6], matches_per_pairing=300),
    Scenario(name="large", troops=45, battlefield_values=[1, 2, 3, 4, 5, 6, 7, 8], matches_per_pairing=350),
    Scenario(name="wide", troops=60, battlefield_values=[2, 2, 3, 3, 4, 5, 6, 7, 8, 9], matches_per_pairing=400),
    Scenario(name="high_value", troops=40, battlefield_values=[2, 4, 6, 8, 10, 12], matches_per_pairing=300),
]


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def allocation_hhi(allocation: list[int]) -> float:
    total = sum(allocation)
    if total == 0:
        return 0.0
    return sum((troops / total) ** 2 for troops in allocation)


def allocation_entropy(allocation: list[int]) -> float:
    total = sum(allocation)
    if total == 0:
        return 0.0

    entropy = 0.0
    for troops in allocation:
        if troops == 0:
            continue
        probability = troops / total
        entropy -= probability * math.log2(probability)
    return entropy


def battlefield_breakdown(
    allocation_1: list[int],
    allocation_2: list[int],
) -> tuple[int, int, int]:
    player_1_wins = 0
    player_2_wins = 0
    tied_battlefields = 0

    for troops_1, troops_2 in zip(allocation_1, allocation_2, strict=True):
        if troops_1 > troops_2:
            player_1_wins += 1
        elif troops_2 > troops_1:
            player_2_wins += 1
        else:
            tied_battlefields += 1

    return player_1_wins, player_2_wins, tied_battlefields


def result_to_row(
    match_id: int,
    scenario: Scenario,
    result: MatchResult,
    runtime_ms: float,
) -> dict[str, object]:
    player_1_battlefield_wins, player_2_battlefield_wins, tied_battlefields = battlefield_breakdown(
        result.player_1_allocation,
        result.player_2_allocation,
    )

    return {
        "match_id": match_id,
        "scenario": scenario.name,
        "troops_per_player": scenario.troops,
        "battlefields": scenario.battlefields,
        "total_battlefield_value": scenario.total_battlefield_value,
        "battlefield_values": json.dumps(result.battlefield_values),
        "player_1_strategy": result.player_1_strategy,
        "player_2_strategy": result.player_2_strategy,
        "player_1_allocation": json.dumps(result.player_1_allocation),
        "player_2_allocation": json.dumps(result.player_2_allocation),
        "player_1_score": result.player_1_score,
        "player_2_score": result.player_2_score,
        "score_margin": result.score_margin,
        "winner": result.winner,
        "runtime_ms": runtime_ms,
        "player_1_battlefield_wins": player_1_battlefield_wins,
        "player_2_battlefield_wins": player_2_battlefield_wins,
        "tied_battlefields": tied_battlefields,
        "player_1_score_share": result.player_1_score / scenario.total_battlefield_value,
        "player_2_score_share": result.player_2_score / scenario.total_battlefield_value,
        "player_1_allocation_hhi": allocation_hhi(result.player_1_allocation),
        "player_2_allocation_hhi": allocation_hhi(result.player_2_allocation),
        "player_1_allocation_entropy": allocation_entropy(result.player_1_allocation),
        "player_2_allocation_entropy": allocation_entropy(result.player_2_allocation),
        "player_1_unused_battlefields": sum(1 for troops in result.player_1_allocation if troops == 0),
        "player_2_unused_battlefields": sum(1 for troops in result.player_2_allocation if troops == 0),
    }


def aggregate_metrics(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row["scenario"]),
            str(row["player_1_strategy"]),
            str(row["player_2_strategy"]),
        )
        grouped[key].append(row)

    metrics = []
    for (scenario_name, strategy_1, strategy_2), matches in sorted(grouped.items()):
        total_matches = len(matches)
        player_1_wins = sum(1 for match in matches if int(match["winner"]) == 1)
        player_2_wins = sum(1 for match in matches if int(match["winner"]) == 2)
        draws = sum(1 for match in matches if int(match["winner"]) == 0)

        avg_player_1_score = sum(float(match["player_1_score"]) for match in matches) / total_matches
        avg_player_2_score = sum(float(match["player_2_score"]) for match in matches) / total_matches
        avg_margin = sum(float(match["score_margin"]) for match in matches) / total_matches
        avg_runtime_ms = sum(float(match["runtime_ms"]) for match in matches) / total_matches
        max_runtime_ms = max(float(match["runtime_ms"]) for match in matches)
        avg_player_1_score_share = sum(float(match["player_1_score_share"]) for match in matches) / total_matches
        avg_player_2_score_share = sum(float(match["player_2_score_share"]) for match in matches) / total_matches
        avg_player_1_battlefield_wins = (
            sum(float(match["player_1_battlefield_wins"]) for match in matches) / total_matches
        )
        avg_player_2_battlefield_wins = (
            sum(float(match["player_2_battlefield_wins"]) for match in matches) / total_matches
        )
        avg_tied_battlefields = sum(float(match["tied_battlefields"]) for match in matches) / total_matches
        avg_player_1_hhi = sum(float(match["player_1_allocation_hhi"]) for match in matches) / total_matches
        avg_player_2_hhi = sum(float(match["player_2_allocation_hhi"]) for match in matches) / total_matches
        avg_player_1_entropy = (
            sum(float(match["player_1_allocation_entropy"]) for match in matches) / total_matches
        )
        avg_player_2_entropy = (
            sum(float(match["player_2_allocation_entropy"]) for match in matches) / total_matches
        )
        avg_player_1_unused = (
            sum(float(match["player_1_unused_battlefields"]) for match in matches) / total_matches
        )
        avg_player_2_unused = (
            sum(float(match["player_2_unused_battlefields"]) for match in matches) / total_matches
        )
        close_game_rate = (
            sum(1 for match in matches if abs(float(match["score_margin"])) <= 1.0) / total_matches
        )
        decisive_game_rate = (
            sum(1 for match in matches if abs(float(match["score_margin"])) >= 0.25 * float(match["total_battlefield_value"]))
            / total_matches
        )

        metrics.append(
            {
                "scenario": scenario_name,
                "player_1_strategy": strategy_1,
                "player_2_strategy": strategy_2,
                "matches": total_matches,
                "troops_per_player": int(matches[0]["troops_per_player"]),
                "battlefields": int(matches[0]["battlefields"]),
                "total_battlefield_value": int(matches[0]["total_battlefield_value"]),
                "player_1_win_rate": player_1_wins / total_matches,
                "player_2_win_rate": player_2_wins / total_matches,
                "draw_rate": draws / total_matches,
                "avg_player_1_score": avg_player_1_score,
                "avg_player_2_score": avg_player_2_score,
                "avg_margin": avg_margin,
                "avg_runtime_ms": avg_runtime_ms,
                "max_runtime_ms": max_runtime_ms,
                "avg_player_1_score_share": avg_player_1_score_share,
                "avg_player_2_score_share": avg_player_2_score_share,
                "avg_player_1_battlefield_wins": avg_player_1_battlefield_wins,
                "avg_player_2_battlefield_wins": avg_player_2_battlefield_wins,
                "avg_tied_battlefields": avg_tied_battlefields,
                "avg_player_1_hhi": avg_player_1_hhi,
                "avg_player_2_hhi": avg_player_2_hhi,
                "avg_player_1_entropy": avg_player_1_entropy,
                "avg_player_2_entropy": avg_player_2_entropy,
                "avg_player_1_unused_battlefields": avg_player_1_unused,
                "avg_player_2_unused_battlefields": avg_player_2_unused,
                "close_game_rate": close_game_rate,
                "decisive_game_rate": decisive_game_rate,
            }
        )

    return metrics


def aggregate_scenarios(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["scenario"])].append(row)

    summary = []
    for scenario_name, matches in sorted(grouped.items()):
        total_matches = len(matches)
        summary.append(
            {
                "scenario": scenario_name,
                "matches": total_matches,
                "troops_per_player": int(matches[0]["troops_per_player"]),
                "battlefields": int(matches[0]["battlefields"]),
                "total_battlefield_value": int(matches[0]["total_battlefield_value"]),
                "avg_runtime_ms": sum(float(match["runtime_ms"]) for match in matches) / total_matches,
                "max_runtime_ms": max(float(match["runtime_ms"]) for match in matches),
                "avg_score_margin_abs": sum(abs(float(match["score_margin"])) for match in matches) / total_matches,
                "draw_rate": sum(1 for match in matches if int(match["winner"]) == 0) / total_matches,
                "avg_tied_battlefields": sum(float(match["tied_battlefields"]) for match in matches) / total_matches,
            }
        )

    return summary


def battlefield_value_hhi(values: list[int]) -> float:
    total = sum(values)
    if total == 0:
        return 0.0
    return sum((value / total) ** 2 for value in values)


def pearson_correlation(x_values: list[float], y_values: list[float]) -> float:
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return 0.0

    mean_x = average(x_values)
    mean_y = average(y_values)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values, strict=True))
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in x_values))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_values))
    if denominator_x == 0 or denominator_y == 0:
        return 0.0
    return numerator / (denominator_x * denominator_y)


def build_strategy_behavior_summary(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in metrics:
        grouped[str(row["player_1_strategy"])].append(row)

    summary = []
    for strategy, rows in sorted(grouped.items()):
        summary.append(
            {
                "strategy": strategy,
                "avg_win_rate": average([float(row["player_1_win_rate"]) for row in rows]),
                "avg_score_share": average([float(row["avg_player_1_score_share"]) for row in rows]),
                "avg_margin": average([float(row["avg_margin"]) for row in rows]),
                "avg_entropy": average([float(row["avg_player_1_entropy"]) for row in rows]),
                "avg_hhi": average([float(row["avg_player_1_hhi"]) for row in rows]),
                "avg_unused_battlefields": average([float(row["avg_player_1_unused_battlefields"]) for row in rows]),
            }
        )

    return summary


def build_strategy_sensitivity(metrics: list[dict[str, object]], scenarios: list[Scenario]) -> list[dict[str, object]]:
    scenario_lookup = {
        scenario.name: {
            "troops": float(scenario.troops),
            "battlefields": float(scenario.battlefields),
            "value_hhi": battlefield_value_hhi(scenario.battlefield_values),
        }
        for scenario in scenarios
    }
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in metrics:
        grouped[str(row["player_1_strategy"])].append(row)

    sensitivity_rows = []
    for strategy, rows in sorted(grouped.items()):
        scenario_scores: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            scenario_scores[str(row["scenario"])].append(float(row["player_1_win_rate"]))

        ordered = sorted(
            (
                {
                    "scenario": scenario_name,
                    "avg_win_rate": average(values),
                    "troops": scenario_lookup[scenario_name]["troops"],
                    "battlefields": scenario_lookup[scenario_name]["battlefields"],
                    "value_hhi": scenario_lookup[scenario_name]["value_hhi"],
                }
                for scenario_name, values in scenario_scores.items()
                if scenario_name in scenario_lookup
            ),
            key=lambda row: str(row["scenario"]),
        )
        if not ordered:
            continue

        win_rates = [float(row["avg_win_rate"]) for row in ordered]
        troops = [float(row["troops"]) for row in ordered]
        battlefields = [float(row["battlefields"]) for row in ordered]
        value_hhis = [float(row["value_hhi"]) for row in ordered]
        best_scenario = max(ordered, key=lambda row: float(row["avg_win_rate"]))
        worst_scenario = min(ordered, key=lambda row: float(row["avg_win_rate"]))

        sensitivity_rows.append(
            {
                "strategy": strategy,
                "best_scenario": str(best_scenario["scenario"]),
                "best_scenario_win_rate": float(best_scenario["avg_win_rate"]),
                "worst_scenario": str(worst_scenario["scenario"]),
                "worst_scenario_win_rate": float(worst_scenario["avg_win_rate"]),
                "troop_count_sensitivity": pearson_correlation(troops, win_rates),
                "battlefield_count_sensitivity": pearson_correlation(battlefields, win_rates),
                "value_concentration_sensitivity": pearson_correlation(value_hhis, win_rates),
                "win_rate_range": max(win_rates) - min(win_rates),
            }
        )

    return sensitivity_rows


def build_pairwise_payoff_matrix(
    metrics: list[dict[str, object]],
) -> tuple[list[str], dict[str, dict[str, float]]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    strategies = sorted({str(row["player_1_strategy"]) for row in metrics} | {str(row["player_2_strategy"]) for row in metrics})

    for row in metrics:
        payoff = float(row["player_1_win_rate"]) - float(row["player_2_win_rate"])
        grouped[(str(row["player_1_strategy"]), str(row["player_2_strategy"]))].append(payoff)

    matrix: dict[str, dict[str, float]] = {}
    for strategy_1 in strategies:
        matrix[strategy_1] = {}
        for strategy_2 in strategies:
            values = grouped.get((strategy_1, strategy_2), [])
            matrix[strategy_1][strategy_2] = average(values)

    return strategies, matrix


def build_payoff_matrix_rows(
    strategy_names: list[str],
    payoff_matrix: dict[str, dict[str, float]],
) -> list[dict[str, object]]:
    rows = []
    for strategy in strategy_names:
        row: dict[str, object] = {"strategy": strategy}
        for opponent in strategy_names:
            row[opponent] = payoff_matrix[strategy][opponent]
        rows.append(row)
    return rows


def build_dominance_rows(
    strategy_names: list[str],
    payoff_matrix: dict[str, dict[str, float]],
    epsilon: float = 1e-9,
) -> list[dict[str, object]]:
    rows = []
    for candidate in strategy_names:
        for comparison in strategy_names:
            if candidate == comparison:
                continue

            candidate_values = [payoff_matrix[candidate][opponent] for opponent in strategy_names]
            comparison_values = [payoff_matrix[comparison][opponent] for opponent in strategy_names]

            if all(left > right + epsilon for left, right in zip(candidate_values, comparison_values, strict=True)):
                relation = "strongly_dominates"
            elif all(left >= right - epsilon for left, right in zip(candidate_values, comparison_values, strict=True)) and any(
                left > right + epsilon for left, right in zip(candidate_values, comparison_values, strict=True)
            ):
                relation = "weakly_dominates"
            else:
                continue

            rows.append(
                {
                    "strategy": candidate,
                    "compared_to": comparison,
                    "relation": relation,
                }
            )

    return rows


def standardize_feature_matrix(feature_rows: list[list[float]]) -> list[list[float]]:
    if not feature_rows:
        return []

    columns = list(zip(*feature_rows, strict=True))
    means = [average(list(column)) for column in columns]
    standard_deviations = []
    for column, mean in zip(columns, means, strict=True):
        variance = average([(value - mean) ** 2 for value in column])
        standard_deviations.append(math.sqrt(variance))

    standardized = []
    for row in feature_rows:
        standardized.append(
            [
                0.0 if std_dev == 0 else (value - mean) / std_dev
                for value, mean, std_dev in zip(row, means, standard_deviations, strict=True)
            ]
        )

    return standardized


def squared_distance(left: list[float], right: list[float]) -> float:
    return sum((left_value - right_value) ** 2 for left_value, right_value in zip(left, right, strict=True))


def run_kmeans(points: list[list[float]], cluster_count: int, iterations: int = 30) -> list[int]:
    if not points:
        return []
    if cluster_count <= 1:
        return [0] * len(points)

    initial_indexes = [
        round(index * (len(points) - 1) / (cluster_count - 1))
        for index in range(cluster_count)
    ]
    centroids = [points[index][:] for index in initial_indexes]
    assignments = [0] * len(points)

    for _ in range(iterations):
        new_assignments = [
            min(range(cluster_count), key=lambda cluster_index: squared_distance(point, centroids[cluster_index]))
            for point in points
        ]
        if new_assignments == assignments:
            break
        assignments = new_assignments

        for cluster_index in range(cluster_count):
            cluster_points = [point for point, assignment in zip(points, assignments, strict=True) if assignment == cluster_index]
            if not cluster_points:
                continue
            centroids[cluster_index] = [
                average([point[feature_index] for point in cluster_points])
                for feature_index in range(len(points[0]))
            ]

    return assignments


def cluster_profile_label(cluster_rows: list[dict[str, object]], all_rows: list[dict[str, object]]) -> str:
    cluster_win_rate = average([float(row["avg_win_rate"]) for row in cluster_rows])
    cluster_entropy = average([float(row["avg_entropy"]) for row in cluster_rows])
    cluster_hhi = average([float(row["avg_hhi"]) for row in cluster_rows])
    cluster_unused = average([float(row["avg_unused_battlefields"]) for row in cluster_rows])

    overall_win_rate = average([float(row["avg_win_rate"]) for row in all_rows])
    overall_entropy = average([float(row["avg_entropy"]) for row in all_rows])
    overall_hhi = average([float(row["avg_hhi"]) for row in all_rows])
    overall_unused = average([float(row["avg_unused_battlefields"]) for row in all_rows])

    if cluster_win_rate >= overall_win_rate and cluster_entropy >= overall_entropy and cluster_hhi <= overall_hhi:
        return "balanced_high_performers"
    if cluster_hhi > overall_hhi or cluster_unused > overall_unused:
        return "concentrated_specialists"
    return "spread_or_mixed_profiles"


def build_strategy_clusters(metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    behavior_rows = build_strategy_behavior_summary(metrics)
    if not behavior_rows:
        return []

    feature_rows = [
        [
            float(row["avg_win_rate"]),
            float(row["avg_score_share"]),
            float(row["avg_margin"]),
            float(row["avg_entropy"]),
            float(row["avg_hhi"]),
            float(row["avg_unused_battlefields"]),
        ]
        for row in behavior_rows
    ]
    standardized = standardize_feature_matrix(feature_rows)
    cluster_count = min(3, len(behavior_rows))
    assignments = run_kmeans(standardized, cluster_count=cluster_count)

    rows_by_cluster: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row, assignment in zip(behavior_rows, assignments, strict=True):
        rows_by_cluster[assignment].append(row)

    labels_by_cluster = {
        cluster_index: cluster_profile_label(cluster_rows, behavior_rows)
        for cluster_index, cluster_rows in rows_by_cluster.items()
    }

    clustered_rows = []
    for row, assignment in zip(behavior_rows, assignments, strict=True):
        clustered_rows.append(
            {
                **row,
                "cluster_id": assignment + 1,
                "cluster_label": labels_by_cluster[assignment],
            }
        )

    return clustered_rows


def approximate_mixed_equilibrium(
    strategy_names: list[str],
    payoff_matrix: dict[str, dict[str, float]],
    iterations: int = 4000,
    learning_rate: float = 0.18,
) -> dict[str, object]:
    if not strategy_names:
        return {"strategy_weights": []}

    weights = [1.0 / len(strategy_names)] * len(strategy_names)
    cumulative_weights = [0.0] * len(strategy_names)

    for _ in range(iterations):
        expected_payoffs = [
            sum(payoff_matrix[strategy_names[row_index]][strategy_names[column_index]] * weights[column_index] for column_index in range(len(strategy_names)))
            for row_index in range(len(strategy_names))
        ]
        baseline = sum(weight * payoff for weight, payoff in zip(weights, expected_payoffs, strict=True))
        updated = [
            weight * math.exp(learning_rate * (payoff - baseline))
            for weight, payoff in zip(weights, expected_payoffs, strict=True)
        ]
        normalizer = sum(updated)
        weights = [value / normalizer for value in updated]
        cumulative_weights = [total + weight for total, weight in zip(cumulative_weights, weights, strict=True)]

    average_weights = [value / iterations for value in cumulative_weights]
    against_mixture = [
        sum(payoff_matrix[strategy_names[row_index]][strategy_names[column_index]] * average_weights[column_index] for column_index in range(len(strategy_names)))
        for row_index in range(len(strategy_names))
    ]
    expected_self_play_payoff = sum(
        average_weights[row_index] * against_mixture[row_index]
        for row_index in range(len(strategy_names))
    )

    strategy_weights = sorted(
        (
            {
                "strategy": strategy,
                "weight": weight,
                "payoff_against_mixture": payoff,
            }
            for strategy, weight, payoff in zip(strategy_names, average_weights, against_mixture, strict=True)
        ),
        key=lambda row: float(row["weight"]),
        reverse=True,
    )

    return {
        "iterations": iterations,
        "learning_rate": learning_rate,
        "expected_self_play_payoff": expected_self_play_payoff,
        "best_response_payoff": max(against_mixture),
        "approximate_exploitability": max(against_mixture) - expected_self_play_payoff,
        "strategy_weights": strategy_weights,
    }


def simulate_adaptive_matchups(
    scenarios: list[Scenario],
    rng: random.Random,
    rounds_per_opponent: int = 120,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    strategy_names = sorted(STRATEGIES.keys())
    history_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for scenario in scenarios:
        for opponent_strategy in strategy_names:
            selection_counts = {strategy: 0 for strategy in strategy_names}
            reward_sums = {strategy: 0.0 for strategy in strategy_names}
            adaptive_wins = 0
            strategy_switches = 0
            previous_strategy: str | None = None

            for round_number in range(1, rounds_per_opponent + 1):
                unexplored = [strategy for strategy in strategy_names if selection_counts[strategy] == 0]
                if unexplored:
                    selected_strategy = unexplored[0]
                else:
                    total_rounds = round_number - 1
                    selected_strategy = max(
                        strategy_names,
                        key=lambda strategy: (
                            (reward_sums[strategy] / selection_counts[strategy])
                            + math.sqrt((2.0 * math.log(total_rounds)) / selection_counts[strategy])
                        ),
                    )

                if previous_strategy is not None and selected_strategy != previous_strategy:
                    strategy_switches += 1

                result = simulate_match(
                    player_1_strategy=selected_strategy,
                    player_2_strategy=opponent_strategy,
                    troops=scenario.troops,
                    battlefield_values=scenario.battlefield_values,
                    rng=rng,
                )
                reward = result.score_margin / scenario.total_battlefield_value
                selection_counts[selected_strategy] += 1
                reward_sums[selected_strategy] += reward
                adaptive_wins += 1 if result.winner == 1 else 0
                previous_strategy = selected_strategy

                history_rows.append(
                    {
                        "scenario": scenario.name,
                        "opponent_strategy": opponent_strategy,
                        "round": round_number,
                        "selected_strategy": selected_strategy,
                        "reward": reward,
                        "winner": result.winner,
                        "player_1_score": result.player_1_score,
                        "player_2_score": result.player_2_score,
                    }
                )

            best_empirical_strategy = max(
                strategy_names,
                key=lambda strategy: (
                    float("-inf")
                    if selection_counts[strategy] == 0
                    else reward_sums[strategy] / selection_counts[strategy]
                ),
            )
            summary_rows.append(
                {
                    "scenario": scenario.name,
                    "opponent_strategy": opponent_strategy,
                    "adaptive_agent": "adaptive_ucb_meta",
                    "rounds_played": rounds_per_opponent,
                    "win_rate": adaptive_wins / rounds_per_opponent,
                    "avg_reward": sum(reward_sums.values()) / rounds_per_opponent,
                    "most_selected_strategy": max(selection_counts, key=selection_counts.get),
                    "best_empirical_strategy": best_empirical_strategy,
                    "explored_strategies": sum(1 for count in selection_counts.values() if count > 0),
                    "strategy_switches": strategy_switches,
                }
            )

    return history_rows, summary_rows


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and fieldnames is None:
        raise ValueError("cannot write an empty CSV")

    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames or list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2)


def select_scenarios(
    scenario_names: list[str] | None,
    matches_override: int | None,
) -> list[Scenario]:
    scenarios = DEFAULT_SCENARIOS
    if scenario_names:
        requested = set(scenario_names)
        scenarios = [scenario for scenario in DEFAULT_SCENARIOS if scenario.name in requested]
        if len(scenarios) != len(requested):
            missing = sorted(requested - {scenario.name for scenario in scenarios})
            raise ValueError(f"Unknown scenarios requested: {', '.join(missing)}")

    if matches_override is not None:
        scenarios = [
            Scenario(
                name=scenario.name,
                troops=scenario.troops,
                battlefield_values=scenario.battlefield_values,
                matches_per_pairing=matches_override,
            )
            for scenario in scenarios
        ]

    return scenarios


def generate_dataset(
    output_dir: Path,
    scenarios: list[Scenario],
    seed: int,
) -> dict[str, Path]:
    rng = random.Random(seed)
    rows: list[dict[str, object]] = []
    match_id = 1

    strategy_names = list(STRATEGIES.keys())
    for scenario in scenarios:
        for strategy_1 in strategy_names:
            for strategy_2 in strategy_names:
                for _ in range(scenario.matches_per_pairing):
                    start_time = time.perf_counter()
                    result = simulate_match(
                        player_1_strategy=strategy_1,
                        player_2_strategy=strategy_2,
                        troops=scenario.troops,
                        battlefield_values=scenario.battlefield_values,
                        rng=rng,
                    )
                    runtime_ms = (time.perf_counter() - start_time) * 1000
                    rows.append(
                        result_to_row(
                            match_id=match_id,
                            scenario=scenario,
                            result=result,
                            runtime_ms=runtime_ms,
                        )
                    )
                    match_id += 1

    metrics = aggregate_metrics(rows)
    scenario_summary = aggregate_scenarios(rows)
    strategy_sensitivity = build_strategy_sensitivity(metrics, scenarios)
    payoff_strategy_names, payoff_matrix = build_pairwise_payoff_matrix(metrics)
    payoff_matrix_rows = build_payoff_matrix_rows(payoff_strategy_names, payoff_matrix)
    dominance_rows = build_dominance_rows(payoff_strategy_names, payoff_matrix)
    strategy_clusters = build_strategy_clusters(metrics)
    approximate_equilibrium = approximate_mixed_equilibrium(payoff_strategy_names, payoff_matrix)
    adaptive_history, adaptive_summary = simulate_adaptive_matchups(scenarios=scenarios, rng=rng)

    output_paths = {
        "dataset_csv": output_dir / "blotto_dataset.csv",
        "metrics_csv": output_dir / "blotto_metrics.csv",
        "metrics_json": output_dir / "blotto_metrics.json",
        "scenario_csv": output_dir / "scenario_summary.csv",
        "scenario_json": output_dir / "scenario_summary.json",
        "sensitivity_csv": output_dir / "strategy_sensitivity.csv",
        "sensitivity_json": output_dir / "strategy_sensitivity.json",
        "payoff_matrix_csv": output_dir / "strategy_payoff_matrix.csv",
        "payoff_matrix_json": output_dir / "strategy_payoff_matrix.json",
        "dominance_csv": output_dir / "strategy_dominance.csv",
        "dominance_json": output_dir / "strategy_dominance.json",
        "clusters_csv": output_dir / "strategy_clusters.csv",
        "clusters_json": output_dir / "strategy_clusters.json",
        "equilibrium_json": output_dir / "approximate_equilibrium.json",
        "adaptive_history_csv": output_dir / "adaptive_match_history.csv",
        "adaptive_history_json": output_dir / "adaptive_match_history.json",
        "adaptive_summary_csv": output_dir / "adaptive_summary.csv",
        "adaptive_summary_json": output_dir / "adaptive_summary.json",
    }

    write_csv(output_paths["dataset_csv"], rows)
    write_csv(output_paths["metrics_csv"], metrics)
    write_json(output_paths["metrics_json"], metrics)
    write_csv(output_paths["scenario_csv"], scenario_summary)
    write_json(output_paths["scenario_json"], scenario_summary)
    write_csv(output_paths["sensitivity_csv"], strategy_sensitivity)
    write_json(output_paths["sensitivity_json"], strategy_sensitivity)
    write_csv(output_paths["payoff_matrix_csv"], payoff_matrix_rows)
    write_json(
        output_paths["payoff_matrix_json"],
        {
            "strategies": payoff_strategy_names,
            "matrix": payoff_matrix,
        },
    )
    write_csv(
        output_paths["dominance_csv"],
        dominance_rows,
        fieldnames=["strategy", "compared_to", "relation"],
    )
    write_json(output_paths["dominance_json"], dominance_rows)
    write_csv(output_paths["clusters_csv"], strategy_clusters)
    write_json(output_paths["clusters_json"], strategy_clusters)
    write_json(output_paths["equilibrium_json"], approximate_equilibrium)
    write_csv(output_paths["adaptive_history_csv"], adaptive_history)
    write_json(output_paths["adaptive_history_json"], adaptive_history)
    write_csv(output_paths["adaptive_summary_csv"], adaptive_summary)
    write_json(output_paths["adaptive_summary_json"], adaptive_summary)

    return output_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a scalable Colonel Blotto dataset and summary metrics.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=[scenario.name for scenario in DEFAULT_SCENARIOS],
        help="Optional subset of named scenarios to run.",
    )
    parser.add_argument(
        "--matches-per-pairing",
        type=int,
        help="Override the configured number of matches per strategy pairing for every selected scenario.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenarios = select_scenarios(
        scenario_names=args.scenarios,
        matches_override=args.matches_per_pairing,
    )
    output_paths = generate_dataset(
        output_dir=args.output_dir,
        scenarios=scenarios,
        seed=args.seed,
    )

    print(f"Dataset saved to {output_paths['dataset_csv']}")
    print(f"Metrics CSV saved to {output_paths['metrics_csv']}")
    print(f"Metrics JSON saved to {output_paths['metrics_json']}")
    print(f"Scenario summary CSV saved to {output_paths['scenario_csv']}")
    print(f"Scenario summary JSON saved to {output_paths['scenario_json']}")
    print(f"Strategy sensitivity CSV saved to {output_paths['sensitivity_csv']}")
    print(f"Strategy payoff matrix CSV saved to {output_paths['payoff_matrix_csv']}")
    print(f"Strategy dominance CSV saved to {output_paths['dominance_csv']}")
    print(f"Strategy clusters CSV saved to {output_paths['clusters_csv']}")
    print(f"Approximate equilibrium JSON saved to {output_paths['equilibrium_json']}")
    print(f"Adaptive history CSV saved to {output_paths['adaptive_history_csv']}")
    print(f"Adaptive summary CSV saved to {output_paths['adaptive_summary_csv']}")


if __name__ == "__main__":
    main()
