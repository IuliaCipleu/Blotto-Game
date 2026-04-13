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


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("cannot write an empty CSV")

    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=list(rows[0].keys()))
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
) -> tuple[Path, Path, Path, Path, Path]:
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

    dataset_path = output_dir / "blotto_dataset.csv"
    metrics_csv_path = output_dir / "blotto_metrics.csv"
    metrics_json_path = output_dir / "blotto_metrics.json"
    scenario_csv_path = output_dir / "scenario_summary.csv"
    scenario_json_path = output_dir / "scenario_summary.json"

    write_csv(dataset_path, rows)
    write_csv(metrics_csv_path, metrics)
    write_json(metrics_json_path, metrics)
    write_csv(scenario_csv_path, scenario_summary)
    write_json(scenario_json_path, scenario_summary)

    return dataset_path, metrics_csv_path, metrics_json_path, scenario_csv_path, scenario_json_path


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
    dataset_path, metrics_csv_path, metrics_json_path, scenario_csv_path, scenario_json_path = generate_dataset(
        output_dir=args.output_dir,
        scenarios=scenarios,
        seed=args.seed,
    )

    print(f"Dataset saved to {dataset_path}")
    print(f"Metrics CSV saved to {metrics_csv_path}")
    print(f"Metrics JSON saved to {metrics_json_path}")
    print(f"Scenario summary CSV saved to {scenario_csv_path}")
    print(f"Scenario summary JSON saved to {scenario_json_path}")


if __name__ == "__main__":
    main()
