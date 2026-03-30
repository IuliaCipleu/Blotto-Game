from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file_handle:
        return list(csv.DictReader(file_handle))


def save_svg_bar_chart(
    title: str,
    labels: list[str],
    series: list[tuple[str, list[float], str]],
    output_path: Path,
    y_max: float,
) -> Path:
    width = 1500
    height = 820
    margin_left = 90
    margin_right = 40
    margin_top = 90
    margin_bottom = 240
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    output_path.parent.mkdir(parents=True, exist_ok=True)
    group_width = chart_width / max(len(labels), 1)
    bar_width = max((group_width * 0.75) / max(len(series), 1), 8)

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
            x = margin_left + (group_width * label_index) + (group_width * 0.12) + (series_index * bar_width)
            y = margin_top + chart_height - bar_height
            svg_parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}"/>'
            )

        for line_index, line in enumerate(label.split("\n")):
            svg_parts.append(
                f'<text x="{label_x:.2f}" y="{margin_top + chart_height + 24 + (line_index * 16)}" text-anchor="middle" font-size="12" font-family="Arial">{html.escape(line)}</text>'
            )

    legend_y = height - 40
    for series_index, (name, _, color) in enumerate(series):
        x = margin_left + (series_index * 260)
        svg_parts.append(f'<rect x="{x}" y="{legend_y - 12}" width="18" height="18" fill="{color}"/>')
        svg_parts.append(
            f'<text x="{x + 28}" y="{legend_y + 2}" font-size="15" font-family="Arial">{html.escape(name)}</text>'
        )

    svg_parts.append("</svg>")
    output_path.write_text("\n".join(svg_parts), encoding="utf-8")
    return output_path


def bar_chart(
    title: str,
    labels: list[str],
    series: list[tuple[str, list[float], str]],
    output_path_png: Path,
    output_path_svg: Path,
    y_label: str,
    y_max: float,
) -> Path:
    output_path_png.parent.mkdir(parents=True, exist_ok=True)

    if plt is not None:
        fig, ax = plt.subplots(figsize=(15, 8))
        x_positions = list(range(len(labels)))
        width = 0.8 / max(len(series), 1)

        for index, (name, values, _) in enumerate(series):
            offsets = [position - 0.4 + (width / 2) + index * width for position in x_positions]
            ax.bar(offsets, values, width=width, label=name)

        ax.set_title(title)
        ax.set_ylabel(y_label)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.legend()
        if y_max > 0:
            ax.set_ylim(0, y_max)
        fig.tight_layout()
        fig.savefig(output_path_png, dpi=200)
        plt.close(fig)
        return output_path_png

    return save_svg_bar_chart(
        title=title,
        labels=labels,
        series=series,
        output_path=output_path_svg,
        y_max=y_max if y_max > 0 else 1.0,
    )


def plot_runtime_by_scenario(scenarios: list[dict[str, str]], output_dir: Path) -> Path:
    labels = [
        f'{row["scenario"]}\n{row["battlefields"]} bf\n{row["troops_per_player"]} troops'
        for row in scenarios
    ]
    avg_runtime = [float(row["avg_runtime_ms"]) for row in scenarios]
    max_runtime = [float(row["max_runtime_ms"]) for row in scenarios]
    y_max = max(avg_runtime + max_runtime) * 1.15 if scenarios else 1.0

    return bar_chart(
        title="Scenario Runtime Comparison",
        labels=labels,
        series=[
            ("Average runtime (ms)", avg_runtime, "#2563eb"),
            ("Max runtime (ms)", max_runtime, "#f97316"),
        ],
        output_path_png=output_dir / "runtime_by_scenario.png",
        output_path_svg=output_dir / "runtime_by_scenario.svg",
        y_label="Runtime (ms)",
        y_max=y_max,
    )


def plot_draw_and_ties(scenarios: list[dict[str, str]], output_dir: Path) -> Path:
    labels = [
        f'{row["scenario"]}\n{row["battlefields"]} bf'
        for row in scenarios
    ]
    draw_rates = [float(row["draw_rate"]) for row in scenarios]
    avg_tied_battlefields = [float(row["avg_tied_battlefields"]) for row in scenarios]
    y_max = max(draw_rates + avg_tied_battlefields) * 1.15 if scenarios else 1.0

    return bar_chart(
        title="Draw Frequency and Tied Battlefields by Scenario",
        labels=labels,
        series=[
            ("Draw rate", draw_rates, "#16a34a"),
            ("Avg tied battlefields", avg_tied_battlefields, "#dc2626"),
        ],
        output_path_png=output_dir / "draws_and_ties.png",
        output_path_svg=output_dir / "draws_and_ties.svg",
        y_label="Rate / Count",
        y_max=y_max,
    )


def plot_best_strategy_by_scenario(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    best_rows: dict[str, dict[str, str]] = {}
    for row in metrics:
        current = best_rows.get(row["scenario"])
        current_score = float(current["avg_margin"]) if current else float("-inf")
        candidate_score = float(row["avg_margin"])
        if candidate_score > current_score:
            best_rows[row["scenario"]] = row

    labels = [
        f'{scenario}\n{row["player_1_strategy"]}\nvs {row["player_2_strategy"]}'
        for scenario, row in sorted(best_rows.items())
    ]
    win_rates = [float(row["player_1_win_rate"]) for _, row in sorted(best_rows.items())]
    margins = [float(row["avg_margin"]) for _, row in sorted(best_rows.items())]
    y_max = max(win_rates + margins) * 1.15 if best_rows else 1.0

    return bar_chart(
        title="Best Player 1 Matchup per Scenario",
        labels=labels,
        series=[
            ("Player 1 win rate", win_rates, "#3b82f6"),
            ("Average margin", margins, "#7c3aed"),
        ],
        output_path_png=output_dir / "best_matchups.png",
        output_path_svg=output_dir / "best_matchups.svg",
        y_label="Value",
        y_max=y_max,
    )


def plot_efficiency_metrics(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    best_rows: dict[str, dict[str, str]] = {}
    for row in metrics:
        current = best_rows.get(row["scenario"])
        current_score = float(current["avg_player_1_score_share"]) if current else float("-inf")
        candidate_score = float(row["avg_player_1_score_share"])
        if candidate_score > current_score:
            best_rows[row["scenario"]] = row

    labels = [
        f'{scenario}\n{row["player_1_strategy"]}'
        for scenario, row in sorted(best_rows.items())
    ]
    score_share = [float(row["avg_player_1_score_share"]) for _, row in sorted(best_rows.items())]
    entropy = [float(row["avg_player_1_entropy"]) for _, row in sorted(best_rows.items())]
    y_max = max(score_share + entropy) * 1.15 if best_rows else 1.0

    return bar_chart(
        title="Best Strategy Efficiency Snapshot",
        labels=labels,
        series=[
            ("Avg score share", score_share, "#0891b2"),
            ("Avg allocation entropy", entropy, "#ea580c"),
        ],
        output_path_png=output_dir / "efficiency_metrics.png",
        output_path_svg=output_dir / "efficiency_metrics.svg",
        y_label="Value",
        y_max=y_max,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot saved Blotto metrics and scenario summaries.")
    parser.add_argument("--metrics-path", type=Path, default=Path("outputs/blotto_metrics.csv"))
    parser.add_argument("--scenario-path", type=Path, default=Path("outputs/scenario_summary.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/plots"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = read_csv_rows(args.metrics_path)
    scenarios = read_csv_rows(args.scenario_path)

    if not metrics:
        raise ValueError(f"No metrics found in {args.metrics_path}")
    if not scenarios:
        raise ValueError(f"No scenario summary found in {args.scenario_path}")

    runtime_plot = plot_runtime_by_scenario(scenarios=scenarios, output_dir=args.output_dir)
    draws_plot = plot_draw_and_ties(scenarios=scenarios, output_dir=args.output_dir)
    best_matchups_plot = plot_best_strategy_by_scenario(metrics=metrics, output_dir=args.output_dir)
    efficiency_plot = plot_efficiency_metrics(metrics=metrics, output_dir=args.output_dir)

    print(f"Runtime plot saved to {runtime_plot}")
    print(f"Draw/tie plot saved to {draws_plot}")
    print(f"Best matchup plot saved to {best_matchups_plot}")
    print(f"Efficiency plot saved to {efficiency_plot}")


if __name__ == "__main__":
    main()
