from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


def read_metrics(metrics_path: Path) -> list[dict[str, str]]:
    with metrics_path.open("r", newline="", encoding="utf-8") as file_handle:
        return list(csv.DictReader(file_handle))


def save_svg_bar_chart(
    title: str,
    labels: list[str],
    series: list[tuple[str, list[float], str]],
    output_path: Path,
    y_max: float,
) -> Path:
    width = 1400
    height = 800
    margin_left = 90
    margin_right = 40
    margin_top = 90
    margin_bottom = 220
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not labels:
        raise ValueError("labels must not be empty")

    group_width = chart_width / len(labels)
    series_count = len(series)
    bar_width = max((group_width * 0.72) / max(series_count, 1), 8)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        f'<text x="{width / 2}" y="42" text-anchor="middle" font-size="26" font-family="Arial">{html.escape(title)}</text>',
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" stroke="#222" stroke-width="2"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" stroke="#222" stroke-width="2"/>',
    ]

    for tick in range(6):
        value = y_max * tick / 5
        y = margin_top + chart_height - (chart_height * tick / 5)
        svg_parts.append(
            f'<line x1="{margin_left - 6}" y1="{y}" x2="{margin_left + chart_width}" y2="{y}" stroke="#d8d8d8" stroke-width="1"/>'
        )
        svg_parts.append(
            f'<text x="{margin_left - 12}" y="{y + 5}" text-anchor="end" font-size="14" font-family="Arial">{value:.2f}</text>'
        )

    for label_index, label in enumerate(labels):
        label_x = margin_left + (group_width * label_index) + group_width / 2

        for series_index, (_, values, color) in enumerate(series):
            value = values[label_index]
            bar_height = 0 if y_max == 0 else (value / y_max) * chart_height
            x = margin_left + (group_width * label_index) + (group_width * 0.14) + (series_index * bar_width)
            y = margin_top + chart_height - bar_height
            svg_parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}"/>'
            )

        for line_index, line in enumerate(label.split("\n")):
            svg_parts.append(
                f'<text x="{label_x:.2f}" y="{margin_top + chart_height + 24 + (line_index * 16)}" text-anchor="middle" font-size="12" font-family="Arial">{html.escape(line)}</text>'
            )

    legend_x = margin_left
    legend_y = height - 40
    for series_index, (name, _, color) in enumerate(series):
        x = legend_x + (series_index * 260)
        svg_parts.append(f'<rect x="{x}" y="{legend_y - 12}" width="18" height="18" fill="{color}"/>')
        svg_parts.append(
            f'<text x="{x + 28}" y="{legend_y + 2}" font-size="15" font-family="Arial">{html.escape(name)}</text>'
        )

    svg_parts.append("</svg>")
    output_path.write_text("\n".join(svg_parts), encoding="utf-8")
    return output_path


def plot_win_rates(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    labels = [
        f'{row["player_1_strategy"]}\nvs\n{row["player_2_strategy"]}'
        for row in metrics
    ]
    player_1_win_rates = [float(row["player_1_win_rate"]) for row in metrics]
    player_2_win_rates = [float(row["player_2_win_rate"]) for row in metrics]
    draw_rates = [float(row["draw_rate"]) for row in metrics]

    output_dir.mkdir(parents=True, exist_ok=True)

    if plt is not None:
        fig, ax = plt.subplots(figsize=(14, 7))
        x_positions = range(len(labels))

        ax.bar(x_positions, player_1_win_rates, label="Player 1 win rate")
        ax.bar(x_positions, player_2_win_rates, bottom=player_1_win_rates, label="Player 2 win rate")
        stacked_bottom = [
            player_1_win_rates[index] + player_2_win_rates[index]
            for index in range(len(player_1_win_rates))
        ]
        ax.bar(x_positions, draw_rates, bottom=stacked_bottom, label="Draw rate")

        ax.set_title("Blotto Strategy Matchup Outcomes")
        ax.set_ylabel("Rate")
        ax.set_xlabel("Strategy matchup")
        ax.set_ylim(0, 1)
        ax.set_xticks(list(x_positions))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.legend()
        fig.tight_layout()

        output_path = output_dir / "win_rates.png"
        fig.savefig(output_path, dpi=200)
        plt.close(fig)
        return output_path

    return save_svg_bar_chart(
        title="Blotto Strategy Matchup Outcomes",
        labels=labels,
        series=[
            ("Player 1 win rate", player_1_win_rates, "#3b82f6"),
            ("Player 2 win rate", player_2_win_rates, "#ef4444"),
            ("Draw rate", draw_rates, "#10b981"),
        ],
        output_path=output_dir / "win_rates.svg",
        y_max=1.0,
    )


def plot_average_scores(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    labels = [
        f'{row["player_1_strategy"]}\nvs\n{row["player_2_strategy"]}'
        for row in metrics
    ]
    avg_player_1_scores = [float(row["avg_player_1_score"]) for row in metrics]
    avg_player_2_scores = [float(row["avg_player_2_score"]) for row in metrics]
    max_score = max(avg_player_1_scores + avg_player_2_scores)

    output_dir.mkdir(parents=True, exist_ok=True)

    if plt is not None:
        fig, ax = plt.subplots(figsize=(14, 7))
        x_positions = list(range(len(labels)))
        width = 0.4

        ax.bar(
            [position - width / 2 for position in x_positions],
            avg_player_1_scores,
            width=width,
            label="Player 1 average score",
        )
        ax.bar(
            [position + width / 2 for position in x_positions],
            avg_player_2_scores,
            width=width,
            label="Player 2 average score",
        )

        ax.set_title("Average Score by Blotto Strategy Matchup")
        ax.set_ylabel("Average score")
        ax.set_xlabel("Strategy matchup")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.legend()
        fig.tight_layout()

        output_path = output_dir / "average_scores.png"
        fig.savefig(output_path, dpi=200)
        plt.close(fig)
        return output_path

    return save_svg_bar_chart(
        title="Average Score by Blotto Strategy Matchup",
        labels=labels,
        series=[
            ("Player 1 average score", avg_player_1_scores, "#2563eb"),
            ("Player 2 average score", avg_player_2_scores, "#f97316"),
        ],
        output_path=output_dir / "average_scores.svg",
        y_max=max_score if max_score > 0 else 1.0,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot saved Blotto metrics.")
    parser.add_argument("--metrics-path", type=Path, default=Path("outputs/blotto_metrics.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/plots"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = read_metrics(args.metrics_path)

    if not metrics:
        raise ValueError(f"No metrics found in {args.metrics_path}")

    win_rate_plot = plot_win_rates(metrics=metrics, output_dir=args.output_dir)
    average_score_plot = plot_average_scores(metrics=metrics, output_dir=args.output_dir)

    print(f"Win rate plot saved to {win_rate_plot}")
    print(f"Average score plot saved to {average_score_plot}")


if __name__ == "__main__":
    main()
