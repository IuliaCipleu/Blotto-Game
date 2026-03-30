from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from blotto import STRATEGIES, MatchResult, simulate_match


DEFAULT_BATTLEFIELD_VALUES = [1, 2, 3, 4, 5]


def result_to_row(match_id: int, result: MatchResult, troops: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "troops_per_player": troops,
        "battlefield_values": json.dumps(result.battlefield_values),
        "player_1_strategy": result.player_1_strategy,
        "player_2_strategy": result.player_2_strategy,
        "player_1_allocation": json.dumps(result.player_1_allocation),
        "player_2_allocation": json.dumps(result.player_2_allocation),
        "player_1_score": result.player_1_score,
        "player_2_score": result.player_2_score,
        "score_margin": result.score_margin,
        "winner": result.winner,
    }


def aggregate_metrics(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["player_1_strategy"]), str(row["player_2_strategy"]))].append(row)

    metrics = []
    for (strategy_1, strategy_2), matches in sorted(grouped.items()):
        total_matches = len(matches)
        player_1_wins = sum(1 for match in matches if int(match["winner"]) == 1)
        player_2_wins = sum(1 for match in matches if int(match["winner"]) == 2)
        draws = sum(1 for match in matches if int(match["winner"]) == 0)
        avg_player_1_score = sum(float(match["player_1_score"]) for match in matches) / total_matches
        avg_player_2_score = sum(float(match["player_2_score"]) for match in matches) / total_matches
        avg_margin = sum(float(match["score_margin"]) for match in matches) / total_matches

        metrics.append(
            {
                "player_1_strategy": strategy_1,
                "player_2_strategy": strategy_2,
                "matches": total_matches,
                "player_1_win_rate": player_1_wins / total_matches,
                "player_2_win_rate": player_2_wins / total_matches,
                "draw_rate": draws / total_matches,
                "avg_player_1_score": avg_player_1_score,
                "avg_player_2_score": avg_player_2_score,
                "avg_margin": avg_margin,
            }
        )

    return metrics


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


def generate_dataset(
    output_dir: Path,
    matches_per_pairing: int,
    troops: int,
    battlefield_values: list[int],
    seed: int,
) -> tuple[Path, Path, Path]:
    rng = random.Random(seed)
    rows: list[dict[str, object]] = []
    match_id = 1

    strategy_names = list(STRATEGIES.keys())
    for strategy_1 in strategy_names:
        for strategy_2 in strategy_names:
            for _ in range(matches_per_pairing):
                result = simulate_match(
                    player_1_strategy=strategy_1,
                    player_2_strategy=strategy_2,
                    troops=troops,
                    battlefield_values=battlefield_values,
                    rng=rng,
                )
                rows.append(result_to_row(match_id=match_id, result=result, troops=troops))
                match_id += 1

    metrics = aggregate_metrics(rows)

    dataset_path = output_dir / "blotto_dataset.csv"
    metrics_csv_path = output_dir / "blotto_metrics.csv"
    metrics_json_path = output_dir / "blotto_metrics.json"

    write_csv(dataset_path, rows)
    write_csv(metrics_csv_path, metrics)
    write_json(metrics_json_path, metrics)

    return dataset_path, metrics_csv_path, metrics_json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Colonel Blotto dataset and summary metrics.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--matches-per-pairing", type=int, default=250)
    parser.add_argument("--troops", type=int, default=20)
    parser.add_argument("--battlefield-values", type=int, nargs="+", default=DEFAULT_BATTLEFIELD_VALUES)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path, metrics_csv_path, metrics_json_path = generate_dataset(
        output_dir=args.output_dir,
        matches_per_pairing=args.matches_per_pairing,
        troops=args.troops,
        battlefield_values=args.battlefield_values,
        seed=args.seed,
    )

    print(f"Dataset saved to {dataset_path}")
    print(f"Metrics CSV saved to {metrics_csv_path}")
    print(f"Metrics JSON saved to {metrics_json_path}")


if __name__ == "__main__":
    main()
