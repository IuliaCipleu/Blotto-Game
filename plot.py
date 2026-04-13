from __future__ import annotations

import argparse
import csv
import html
import math
from collections import defaultdict
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

PALETTE = ["#f4f1de","#eab69f","#e07a5f","#8f5d5d","#3d405b","#5f797b","#81b29a","#f2cc8f"]

def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file_handle:
        return list(csv.DictReader(file_handle))


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def min_positive(values: list[float]) -> float:
    positive_values = [value for value in values if value > 0]
    if not positive_values:
        return 1.0
    return min(positive_values)


def split_in_half[T](items: list[T]) -> tuple[list[T], list[T]]:
    midpoint = (len(items) + 1) // 2
    return items[:midpoint], items[midpoint:]


def save_svg_bar_chart(
    title: str,
    labels: list[str],
    series: list[tuple[str, list[float], str]],
    output_path: Path,
    y_label: str,
    y_max: float,
    log_scale: bool = False,
) -> Path:
    width = 1500
    height = 820
    margin_left = 90
    margin_right = 40
    margin_top = 90
    margin_bottom = 240
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom
    title_font_size = 34
    axis_font_size = 20
    tick_font_size = 18
    label_font_size = 18
    legend_font_size = 20

    output_path.parent.mkdir(parents=True, exist_ok=True)
    group_width = chart_width / max(len(labels), 1)
    bar_width = max((group_width * 0.75) / max(len(series), 1), 8)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        f'<text x="{width / 2}" y="50" text-anchor="middle" font-size="{title_font_size}" font-family="Arial">{html.escape(title)}</text>',
        f'<text x="28" y="{margin_top + chart_height / 2}" text-anchor="middle" font-size="{axis_font_size}" font-family="Arial" transform="rotate(-90 28 {margin_top + chart_height / 2})">{html.escape(y_label)}</text>',
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" stroke="#222" stroke-width="2"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" stroke="#222" stroke-width="2"/>',
    ]

    all_values = [value for _, values, _ in series for value in values]
    log_min = min_positive(all_values) * 0.8 if log_scale else 0.0
    if log_scale and log_min <= 0:
        log_min = min_positive(all_values)
    log_range = 1.0
    if log_scale:
        log_range = max((y_max / log_min), 1.000001)

    if log_scale:
        tick = log_min
        tick_values: list[float] = []
        while tick <= y_max * 1.000001:
            tick_values.append(tick)
            tick *= 10
        if y_max not in tick_values:
            tick_values.append(y_max)

        for value in tick_values:
            progress = 0.0 if value <= 0 else (math.log10(value / log_min) / math.log10(log_range))
            y = margin_top + chart_height - (chart_height * progress)
            svg_parts.append(
                f'<line x1="{margin_left - 6}" y1="{y}" x2="{margin_left + chart_width}" y2="{y}" stroke="#d8d8d8" stroke-width="1"/>'
            )
            svg_parts.append(
                f'<text x="{margin_left - 12}" y="{y + 6}" text-anchor="end" font-size="{tick_font_size}" font-family="Arial">{value:.3f}</text>'
            )
    else:
        for tick in range(6):
            value = y_max * tick / 5
            y = margin_top + chart_height - (chart_height * tick / 5)
            svg_parts.append(
                f'<line x1="{margin_left - 6}" y1="{y}" x2="{margin_left + chart_width}" y2="{y}" stroke="#d8d8d8" stroke-width="1"/>'
            )
            svg_parts.append(
                f'<text x="{margin_left - 12}" y="{y + 6}" text-anchor="end" font-size="{tick_font_size}" font-family="Arial">{value:.2f}</text>'
            )

    for label_index, label in enumerate(labels):
        label_x = margin_left + (group_width * label_index) + group_width / 2
        for series_index, (_, values, color) in enumerate(series):
            value = values[label_index]
            if log_scale:
                if value <= 0:
                    bar_height = 0
                else:
                    bar_height = (math.log10(value / log_min) / math.log10(log_range)) * chart_height
            else:
                bar_height = 0 if y_max == 0 else (value / y_max) * chart_height
            x = margin_left + (group_width * label_index) + (group_width * 0.12) + (series_index * bar_width)
            y = margin_top + chart_height - bar_height
            svg_parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}"/>'
            )

        for line_index, line in enumerate(label.split("\n")):
            svg_parts.append(
                f'<text x="{label_x:.2f}" y="{margin_top + chart_height + 32 + (line_index * 22)}" text-anchor="middle" font-size="{label_font_size}" font-family="Arial">{html.escape(line)}</text>'
            )

    legend_y = height - 40
    for series_index, (name, _, color) in enumerate(series):
        x = margin_left + (series_index * 260)
        svg_parts.append(f'<rect x="{x}" y="{legend_y - 12}" width="18" height="18" fill="{color}"/>')
        svg_parts.append(
            f'<text x="{x + 28}" y="{legend_y + 4}" font-size="{legend_font_size}" font-family="Arial">{html.escape(name)}</text>'
        )

    svg_parts.append("</svg>")
    output_path.write_text("\n".join(svg_parts), encoding="utf-8")
    return output_path


def save_svg_two_panel_bar_chart(
    title: str,
    labels_top: list[str],
    series_top: list[tuple[str, list[float], str]],
    labels_bottom: list[str],
    series_bottom: list[tuple[str, list[float], str]],
    output_path: Path,
    y_label: str,
    y_max: float,
) -> Path:
    width = 2200
    height = 1500
    margin_left = 110
    margin_right = 40
    margin_top = 90
    margin_bottom = 110
    panel_gap = 150
    panel_height = (height - margin_top - margin_bottom - panel_gap) / 2
    chart_width = width - margin_left - margin_right
    title_font_size = 34
    axis_font_size = 20
    tick_font_size = 18
    label_font_size = 18
    legend_font_size = 20

    output_path.parent.mkdir(parents=True, exist_ok=True)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        f'<text x="{width / 2}" y="50" text-anchor="middle" font-size="{title_font_size}" font-family="Arial">{html.escape(title)}</text>',
        f'<text x="28" y="{margin_top + panel_height}" text-anchor="middle" font-size="{axis_font_size}" font-family="Arial" transform="rotate(-90 28 {margin_top + panel_height})">{html.escape(y_label)}</text>',
    ]

    panels = [
        (labels_top, series_top, margin_top),
        (labels_bottom, series_bottom, margin_top + panel_height + panel_gap),
    ]

    for labels, series, panel_top in panels:
        if not labels:
            continue

        group_width = chart_width / max(len(labels), 1)
        bar_width = max((group_width * 0.75) / max(len(series), 1), 8)

        svg_parts.append(
            f'<line x1="{margin_left}" y1="{panel_top + panel_height}" x2="{margin_left + chart_width}" y2="{panel_top + panel_height}" stroke="#222" stroke-width="2"/>'
        )
        svg_parts.append(
            f'<line x1="{margin_left}" y1="{panel_top}" x2="{margin_left}" y2="{panel_top + panel_height}" stroke="#222" stroke-width="2"/>'
        )

        for tick in range(6):
            value = y_max * tick / 5
            y = panel_top + panel_height - (panel_height * tick / 5)
            svg_parts.append(
                f'<line x1="{margin_left - 6}" y1="{y}" x2="{margin_left + chart_width}" y2="{y}" stroke="#d8d8d8" stroke-width="1"/>'
            )
            svg_parts.append(
                f'<text x="{margin_left - 12}" y="{y + 6}" text-anchor="end" font-size="{tick_font_size}" font-family="Arial">{value:.2f}</text>'
            )

        for label_index, label in enumerate(labels):
            label_x = margin_left + (group_width * label_index) + group_width / 2
            for series_index, (_, values, color) in enumerate(series):
                value = values[label_index]
                bar_height = 0 if y_max == 0 else (value / y_max) * panel_height
                x = margin_left + (group_width * label_index) + (group_width * 0.12) + (series_index * bar_width)
                y = panel_top + panel_height - bar_height
                svg_parts.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}"/>'
                )

            for line_index, line in enumerate(label.split("\n")):
                svg_parts.append(
                    f'<text x="{label_x:.2f}" y="{panel_top + panel_height + 32 + (line_index * 22)}" text-anchor="middle" font-size="{label_font_size}" font-family="Arial">{html.escape(line)}</text>'
                )

    legend_y = height - 40
    for series_index, (name, _, color) in enumerate(series_top):
        x = margin_left + (series_index * 320)
        svg_parts.append(f'<rect x="{x}" y="{legend_y - 12}" width="18" height="18" fill="{color}"/>')
        svg_parts.append(
            f'<text x="{x + 28}" y="{legend_y + 4}" font-size="{legend_font_size}" font-family="Arial">{html.escape(name)}</text>'
        )

    svg_parts.append("</svg>")
    output_path.write_text("\n".join(svg_parts), encoding="utf-8")
    return output_path


def save_svg_stacked_bar_chart(
    title: str,
    labels: list[str],
    series: list[tuple[str, list[float], str]],
    output_path: Path,
    y_label: str,
    y_max: float,
    width: int = 1600,
    height: int = 900,
) -> Path:
    margin_left = 90
    margin_right = 40
    margin_top = 90
    margin_bottom = 260
    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom
    title_font_size = 34
    axis_font_size = 20
    tick_font_size = 18
    label_font_size = 18
    legend_font_size = 20

    output_path.parent.mkdir(parents=True, exist_ok=True)
    group_width = chart_width / max(len(labels), 1)
    bar_width = max(group_width * 0.75, 16)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        f'<text x="{width / 2}" y="50" text-anchor="middle" font-size="{title_font_size}" font-family="Arial">{html.escape(title)}</text>',
        f'<text x="28" y="{margin_top + chart_height / 2}" text-anchor="middle" font-size="{axis_font_size}" font-family="Arial" transform="rotate(-90 28 {margin_top + chart_height / 2})">{html.escape(y_label)}</text>',
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
            f'<text x="{margin_left - 12}" y="{y + 6}" text-anchor="end" font-size="{tick_font_size}" font-family="Arial">{value:.2f}</text>'
        )

    for label_index, label in enumerate(labels):
        label_x = margin_left + (group_width * label_index) + group_width / 2
        x = label_x - bar_width / 2
        cumulative_height = 0.0

        for _, values, color in series:
            value = values[label_index]
            bar_height = 0 if y_max == 0 else (value / y_max) * chart_height
            y = margin_top + chart_height - cumulative_height - bar_height
            svg_parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}"/>'
            )
            cumulative_height += bar_height

        for line_index, line in enumerate(label.split("\n")):
            svg_parts.append(
                f'<text x="{label_x:.2f}" y="{margin_top + chart_height + 32 + (line_index * 22)}" text-anchor="middle" font-size="{label_font_size}" font-family="Arial">{html.escape(line)}</text>'
            )

    legend_y = height - 40
    for series_index, (name, _, color) in enumerate(series):
        x = margin_left + (series_index * 260)
        svg_parts.append(f'<rect x="{x}" y="{legend_y - 12}" width="18" height="18" fill="{color}"/>')
        svg_parts.append(
            f'<text x="{x + 28}" y="{legend_y + 4}" font-size="{legend_font_size}" font-family="Arial">{html.escape(name)}</text>'
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
    log_scale: bool = False,
) -> Path:
    output_path_png.parent.mkdir(parents=True, exist_ok=True)

    if plt is not None:
        fig, ax = plt.subplots(figsize=(15, 8))
        x_positions = list(range(len(labels)))
        width = 0.8 / max(len(series), 1)

        for index, (name, values, color) in enumerate(series):
            offsets = [position - 0.4 + (width / 2) + index * width for position in x_positions]
            ax.bar(offsets, values, width=width, label=name, color=color)

        ax.set_title(title, fontsize=22, pad=16)
        ax.set_ylabel(y_label, fontsize=18)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=15)
        ax.tick_params(axis="y", labelsize=15)
        ax.legend(fontsize=15)
        if log_scale:
            all_values = [value for _, values, _ in series for value in values]
            lower_bound = min_positive(all_values) * 0.8
            ax.set_yscale("log")
            ax.set_ylim(lower_bound, y_max)
        elif y_max > 0:
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
        y_label=y_label,
        y_max=y_max if y_max > 0 else 1.0,
        log_scale=log_scale,
    )


def stacked_bar_chart(
    title: str,
    labels: list[str],
    series: list[tuple[str, list[float], str]],
    output_path_png: Path,
    output_path_svg: Path,
    y_label: str,
    y_max: float,
    figure_size: tuple[float, float] = (13.33, 7.5),
    svg_size: tuple[int, int] = (1600, 900),
) -> Path:
    output_path_png.parent.mkdir(parents=True, exist_ok=True)

    if plt is not None:
        fig, ax = plt.subplots(figsize=figure_size)
        x_positions = list(range(len(labels)))
        cumulative = [0.0] * len(labels)

        for name, values, color in series:
            ax.bar(x_positions, values, bottom=cumulative, label=name, color=color)
            cumulative = [base + value for base, value in zip(cumulative, values, strict=True)]

        ax.set_title(title, fontsize=22, pad=16)
        ax.set_ylabel(y_label, fontsize=18)
        ax.set_xlabel("Strategy matchup", fontsize=18)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=14)
        ax.tick_params(axis="y", labelsize=15)
        ax.legend(fontsize=15)
        if y_max > 0:
            ax.set_ylim(0, y_max)
        fig.tight_layout()
        fig.savefig(output_path_png, dpi=200)
        plt.close(fig)
        return output_path_png

    return save_svg_stacked_bar_chart(
        title=title,
        labels=labels,
        series=series,
        output_path=output_path_svg,
        y_label=y_label,
        y_max=y_max if y_max > 0 else 1.0,
        width=svg_size[0],
        height=svg_size[1],
    )


def two_panel_bar_chart(
    title: str,
    labels: list[str],
    series: list[tuple[str, list[float], str]],
    output_path_png: Path,
    output_path_svg: Path,
    y_label: str,
    y_max: float,
) -> Path:
    output_path_png.parent.mkdir(parents=True, exist_ok=True)
    labels_top, labels_bottom = split_in_half(labels)
    series_top = [(name, values[: len(labels_top)], color) for name, values, color in series]
    series_bottom = [(name, values[len(labels_top):], color) for name, values, color in series]

    if plt is not None:
        fig, axes = plt.subplots(2, 1, figsize=(22, 14), sharey=True)

        for ax, panel_labels, panel_series in zip(
            axes,
            [labels_top, labels_bottom],
            [series_top, series_bottom],
            strict=True,
        ):
            x_positions = list(range(len(panel_labels)))
            width = 0.8 / max(len(panel_series), 1)

            for index, (name, values, color) in enumerate(panel_series):
                offsets = [position - 0.4 + (width / 2) + index * width for position in x_positions]
                ax.bar(offsets, values, width=width, label=name, color=color)

            ax.set_ylabel(y_label, fontsize=18)
            ax.set_xticks(x_positions)
            ax.set_xticklabels(panel_labels, rotation=45, ha="right", fontsize=14)
            ax.tick_params(axis="y", labelsize=15)
            if y_max > 0:
                ax.set_ylim(0, y_max)

        axes[0].set_title(title, fontsize=22, pad=16)
        axes[0].legend(fontsize=15)
        fig.tight_layout()
        fig.savefig(output_path_png, dpi=200)
        plt.close(fig)
        return output_path_png

    return save_svg_two_panel_bar_chart(
        title=title,
        labels_top=labels_top,
        series_top=series_top,
        labels_bottom=labels_bottom,
        series_bottom=series_bottom,
        output_path=output_path_svg,
        y_label=y_label,
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
            ("Average runtime (ms)", avg_runtime, PALETTE[2]),
            ("Max runtime (ms)", max_runtime, PALETTE[4]),
        ],
        output_path_png=output_dir / "runtime_by_scenario.png",
        output_path_svg=output_dir / "runtime_by_scenario.svg",
        y_label="Runtime (ms)",
        y_max=y_max,
        log_scale=True,
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
            ("Draw rate", draw_rates, PALETTE[3]),
            ("Avg tied battlefields", avg_tied_battlefields, PALETTE[6]),
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
            ("Player 1 win rate", win_rates, PALETTE[2]),
            ("Average margin", margins, PALETTE[4]),
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
            ("Avg score share", score_share, PALETTE[5]),
            ("Avg allocation entropy", entropy, PALETTE[7]),
        ],
        output_path_png=output_dir / "efficiency_metrics.png",
        output_path_svg=output_dir / "efficiency_metrics.svg",
        y_label="Value",
        y_max=y_max,
    )


def build_strategy_overview(metrics: list[dict[str, str]]) -> list[dict[str, float | str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in metrics:
        grouped[row["player_1_strategy"]].append(row)

    overview = []
    for strategy, rows in sorted(grouped.items()):
        overview.append(
            {
                "strategy": strategy,
                "win_rate": average([float(row["player_1_win_rate"]) for row in rows]),
                "score_share": average([float(row["avg_player_1_score_share"]) for row in rows]),
                "margin": average([float(row["avg_margin"]) for row in rows]),
                "entropy": average([float(row["avg_player_1_entropy"]) for row in rows]),
                "hhi": average([float(row["avg_player_1_hhi"]) for row in rows]),
                "unused": average([float(row["avg_player_1_unused_battlefields"]) for row in rows]),
            }
        )

    return overview


def build_strategy_scenario_overview(metrics: list[dict[str, str]]) -> list[dict[str, float | str]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in metrics:
        grouped[(row["player_1_strategy"], row["scenario"])].append(row)

    overview = []
    for (strategy, scenario), rows in sorted(grouped.items()):
        overview.append(
            {
                "scenario": scenario,
                "strategy": strategy,
                "win_rate": average([float(row["player_1_win_rate"]) for row in rows]),
                "score_share": average([float(row["avg_player_1_score_share"]) for row in rows]),
            }
        )

    return overview


def build_competitiveness_overview(metrics: list[dict[str, str]]) -> list[dict[str, float | str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in metrics:
        grouped[row["scenario"]].append(row)

    overview = []
    for scenario, rows in sorted(grouped.items()):
        overview.append(
            {
                "scenario": scenario,
                "close_game_rate": average([float(row["close_game_rate"]) for row in rows]),
                "decisive_game_rate": average([float(row["decisive_game_rate"]) for row in rows]),
                "avg_margin": average([abs(float(row["avg_margin"])) for row in rows]),
            }
        )

    return overview


def build_matchup_outcome_overview(
    metrics: list[dict[str, str]],
    scenario: str,
) -> list[dict[str, float | str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in metrics:
        if row["scenario"] == scenario:
            grouped[row["player_1_strategy"]].append(row)

    overview = []
    for strategy, rows in sorted(grouped.items()):
        overview.append(
            {
                "label": strategy,
                "player_1_win_rate": average([float(row["player_1_win_rate"]) for row in rows]),
                "player_2_win_rate": average([float(row["player_2_win_rate"]) for row in rows]),
                "draw_rate": average([float(row["draw_rate"]) for row in rows]),
            }
        )

    return overview


def plot_strategy_win_rates(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    overview = build_strategy_overview(metrics)
    labels = [str(row["strategy"]) for row in overview]
    win_rates = [float(row["win_rate"]) for row in overview]
    score_share = [float(row["score_share"]) for row in overview]
    y_max = max(win_rates + score_share) * 1.15 if overview else 1.0

    return bar_chart(
        title="Overall Strategy Performance",
        labels=labels,
        series=[
            ("Average win rate", win_rates, PALETTE[5]),
            ("Average score share", score_share, PALETTE[7]),
        ],
        output_path_png=output_dir / "strategy_performance.png",
        output_path_svg=output_dir / "strategy_performance.svg",
        y_label="Rate",
        y_max=y_max,
    )


def plot_matchup_outcomes(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    scenario_names = sorted({row["scenario"] for row in metrics})
    scenario_name = "baseline" if "baseline" in scenario_names else scenario_names[0]
    overview = build_matchup_outcome_overview(metrics, scenario=scenario_name)
    labels = [str(row["label"]) for row in overview]
    player_1_win_rates = [float(row["player_1_win_rate"]) for row in overview]
    player_2_win_rates = [float(row["player_2_win_rate"]) for row in overview]
    draw_rates = [float(row["draw_rate"]) for row in overview]

    return stacked_bar_chart(
        title=f"Blotto Strategy Outcomes ({scenario_name} scenario)",
        labels=labels,
        series=[
            ("Player 1 win rate", player_1_win_rates, PALETTE[4]),
            ("Player 2 win rate", player_2_win_rates, PALETTE[2]),
            ("Draw rate", draw_rates, PALETTE[6]),
        ],
        output_path_png=output_dir / "win_rates.png",
        output_path_svg=output_dir / "win_rates.svg",
        y_label="Rate",
        y_max=1.0,
        figure_size=(13.33, 7.5),
        svg_size=(1600, 900),
    )


def plot_strategy_style(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    overview = build_strategy_overview(metrics)
    labels = [str(row["strategy"]) for row in overview]
    entropy = [float(row["entropy"]) for row in overview]
    hhi = [float(row["hhi"]) for row in overview]
    y_max = max(entropy + hhi) * 1.15 if overview else 1.0

    return bar_chart(
        title="Allocation Style by Strategy",
        labels=labels,
        series=[
            ("Average entropy", entropy, PALETTE[2]),
            ("Average HHI", hhi, PALETTE[4]),
        ],
        output_path_png=output_dir / "strategy_style.png",
        output_path_svg=output_dir / "strategy_style.svg",
        y_label="Value",
        y_max=y_max,
    )


def plot_strategy_unused_battlefields(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    overview = build_strategy_overview(metrics)
    labels = [str(row["strategy"]) for row in overview]
    unused = [float(row["unused"]) for row in overview]
    y_max = max(unused) * 1.15 if overview else 1.0

    return bar_chart(
        title="Unused Battlefields by Strategy",
        labels=labels,
        series=[
            ("Average unused battlefields", unused, PALETTE[4]),
        ],
        output_path_png=output_dir / "strategy_unused_battlefields.png",
        output_path_svg=output_dir / "strategy_unused_battlefields.svg",
        y_label="Battlefields",
        y_max=y_max,
    )


def plot_match_competitiveness(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    overview = build_competitiveness_overview(metrics)
    labels = [str(row["scenario"]) for row in overview]
    close_rates = [float(row["close_game_rate"]) for row in overview]
    decisive_rates = [float(row["decisive_game_rate"]) for row in overview]
    y_max = max(close_rates + decisive_rates) * 1.15 if overview else 1.0

    return bar_chart(
        title="Match Competitiveness by Scenario",
        labels=labels,
        series=[
            ("Close game rate", close_rates, PALETTE[6]),
            ("Decisive game rate", decisive_rates, PALETTE[7]),
        ],
        output_path_png=output_dir / "match_competitiveness.png",
        output_path_svg=output_dir / "match_competitiveness.svg",
        y_label="Rate",
        y_max=y_max,
    )


def plot_average_score_margin(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    overview = build_competitiveness_overview(metrics)
    labels = [str(row["scenario"]) for row in overview]
    margins = [float(row["avg_margin"]) for row in overview]
    y_max = max(margins) * 1.15 if overview else 1.0

    return bar_chart(
        title="Average Score Margin by Scenario",
        labels=labels,
        series=[
            ("Average absolute margin", margins, PALETTE[3]),
        ],
        output_path_png=output_dir / "average_score_margin.png",
        output_path_svg=output_dir / "average_score_margin.svg",
        y_label="Score margin",
        y_max=y_max,
    )


def plot_ranked_strategy_performance(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    overview = sorted(
        build_strategy_overview(metrics),
        key=lambda row: (float(row["win_rate"]), float(row["score_share"])),
        reverse=True,
    )
    labels = [str(row["strategy"]) for row in overview]
    win_rates = [float(row["win_rate"]) for row in overview]
    score_share = [float(row["score_share"]) for row in overview]
    y_max = max(win_rates + score_share) * 1.15 if overview else 1.0

    return bar_chart(
        title="Ranked Strategy Performance",
        labels=labels,
        series=[
            ("Average win rate", win_rates, PALETTE[2]),
            ("Average score share", score_share, PALETTE[4]),
        ],
        output_path_png=output_dir / "ranked_strategy_performance.png",
        output_path_svg=output_dir / "ranked_strategy_performance.svg",
        y_label="Rate",
        y_max=y_max,
    )


def plot_strategy_margin_overview(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    overview = sorted(
        build_strategy_overview(metrics),
        key=lambda row: float(row["margin"]),
        reverse=True,
    )
    labels = [str(row["strategy"]) for row in overview]
    win_rates = [float(row["win_rate"]) for row in overview]
    margins = [float(row["margin"]) for row in overview]
    y_max = max(win_rates + margins) * 1.15 if overview else 1.0

    return bar_chart(
        title="Strategy Margin Overview",
        labels=labels,
        series=[
            ("Average win rate", win_rates, PALETTE[2]),
            ("Average margin", margins, PALETTE[4]),
        ],
        output_path_png=output_dir / "strategy_margin_overview.png",
        output_path_svg=output_dir / "strategy_margin_overview.svg",
        y_label="Value",
        y_max=y_max,
    )


def plot_strategy_by_scenario(metrics: list[dict[str, str]], output_dir: Path) -> Path:
    overview = build_strategy_scenario_overview(metrics)
    labels = [f'{row["scenario"]}\n{row["strategy"]}' for row in overview]
    win_rates = [float(row["win_rate"]) for row in overview]
    score_share = [float(row["score_share"]) for row in overview]
    y_max = max(win_rates + score_share) * 1.15 if overview else 1.0

    return two_panel_bar_chart(
        title="Strategy Performance by Scenario",
        labels=labels,
        series=[
            ("Average win rate", win_rates, PALETTE[6]),
            ("Average score share", score_share, PALETTE[7]),
        ],
        output_path_png=output_dir / "strategy_by_scenario.png",
        output_path_svg=output_dir / "strategy_by_scenario.svg",
        y_label="Rate",
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
    strategy_performance_plot = plot_strategy_win_rates(metrics=metrics, output_dir=args.output_dir)
    matchup_outcomes_plot = plot_matchup_outcomes(metrics=metrics, output_dir=args.output_dir)
    strategy_style_plot = plot_strategy_style(metrics=metrics, output_dir=args.output_dir)
    unused_battlefields_plot = plot_strategy_unused_battlefields(metrics=metrics, output_dir=args.output_dir)
    competitiveness_plot = plot_match_competitiveness(metrics=metrics, output_dir=args.output_dir)
    score_margin_plot = plot_average_score_margin(metrics=metrics, output_dir=args.output_dir)
    ranked_strategy_performance_plot = plot_ranked_strategy_performance(metrics=metrics, output_dir=args.output_dir)
    strategy_margin_overview_plot = plot_strategy_margin_overview(metrics=metrics, output_dir=args.output_dir)
    strategy_by_scenario_plot = plot_strategy_by_scenario(metrics=metrics, output_dir=args.output_dir)

    print(f"Runtime plot saved to {runtime_plot}")
    print(f"Draw/tie plot saved to {draws_plot}")
    print(f"Best matchup plot saved to {best_matchups_plot}")
    print(f"Efficiency plot saved to {efficiency_plot}")
    print(f"Strategy performance plot saved to {strategy_performance_plot}")
    print(f"Matchup outcomes plot saved to {matchup_outcomes_plot}")
    print(f"Strategy style plot saved to {strategy_style_plot}")
    print(f"Unused battlefields plot saved to {unused_battlefields_plot}")
    print(f"Competitiveness plot saved to {competitiveness_plot}")
    print(f"Score margin plot saved to {score_margin_plot}")
    print(f"Ranked strategy performance plot saved to {ranked_strategy_performance_plot}")
    print(f"Strategy margin overview plot saved to {strategy_margin_overview_plot}")
    print(f"Strategy by scenario plot saved to {strategy_by_scenario_plot}")


if __name__ == "__main__":
    main()
