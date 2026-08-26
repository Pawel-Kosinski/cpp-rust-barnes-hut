#!/usr/bin/env python3
"""Generate the three manuscript figures from raw v1.1.2 benchmark data."""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


COLORS = {"cpp": "#176B87", "rust": "#D97706"}
VARIANT_COLORS = {"v2": "#7A9E9F", "v3": "#176B87", "v4": "#C8553D", "v5": "#2A9D6F"}
VARIANT_LABELS = {"v2": "V2 pointer", "v3": "V3 arena", "v4": "V4 threaded", "v5": "V5 parallel"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def aggregate(
    rows: list[dict[str, str]], keys: tuple[str, ...], field: str
) -> dict[tuple[str, ...], tuple[float, float]]:
    groups: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(float(row[field]))
    return {
        key: (statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0)
        for key, values in groups.items()
    }


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linestyle": "--",
        }
    )


def plot_figure_1(root: Path, output: Path) -> None:
    timing = read_csv(root / "fig1" / "raw_runs.csv")
    accuracy = read_csv(root / "fig1" / "accuracy.csv")
    timing_stats = aggregate(timing, ("language", "theta"), "total_ms_per_frame")

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for language in ("cpp", "rust"):
        theta_values = sorted(float(key[1]) for key in timing_stats if key[0] == language)
        means = [timing_stats[(language, f"{theta:g}")][0] for theta in theta_values]
        errors = [timing_stats[(language, f"{theta:g}")][1] for theta in theta_values]
        axes[0].errorbar(
            theta_values,
            means,
            yerr=errors,
            marker="o",
            capsize=3,
            linewidth=2,
            color=COLORS[language],
            label="C++ V3" if language == "cpp" else "Rust V3",
        )
    axes[0].set_xlabel(r"Opening threshold $\theta$")
    axes[0].set_ylabel("Measured time (ms/frame)")
    axes[0].set_title("Runtime and opening threshold")
    axes[0].legend(frameon=False)

    line_styles = {"rms_relative": "-", "p95_relative": "--"}
    metric_labels = {"rms_relative": "RMS", "p95_relative": "p95"}
    for language in ("cpp", "rust"):
        language_rows = sorted(
            (row for row in accuracy if row["language"] == language),
            key=lambda row: float(row["theta"]),
        )
        theta_values = [float(row["theta"]) for row in language_rows]
        for metric in ("rms_relative", "p95_relative"):
            is_cpp = language == "cpp"
            axes[1].plot(
                theta_values,
                [100.0 * float(row[metric]) for row in language_rows],
                line_styles[metric],
                marker="o",
                markersize=7 if is_cpp else 5,
                linewidth=4 if is_cpp else 2,
                color=COLORS[language],
                zorder=2 if is_cpp else 3,
                label=f"{'C++' if language == 'cpp' else 'Rust'} {metric_labels[metric]}",
            )
    axes[1].set_xlabel(r"Opening threshold $\theta$")
    axes[1].set_ylabel("Relative force error (%)")
    axes[1].set_title("Accuracy against direct summation")
    axes[1].legend(frameon=False, ncol=2)
    axes[1].text(
        0.54,
        0.04,
        "C++ and Rust curves overlap",
        transform=axes[1].transAxes,
        fontsize=9,
        color="#525252",
        ha="center",
    )

    figure.tight_layout()
    figure.savefig(output / "fig1_theta_accuracy.png", dpi=220, bbox_inches="tight")
    plt.close(figure)


def plot_figure_2(root: Path, output: Path) -> None:
    rows = read_csv(root / "fig2" / "raw_runs.csv")
    total_stats = aggregate(rows, ("language", "variant"), "total_ms_per_frame")
    phase_stats = {
        field: aggregate(rows, ("language", "variant"), field)
        for field in ("tree_ms_per_frame", "force_update_ms_per_frame", "cleanup_ms_per_frame")
    }
    variants = ("v2", "v3", "v4", "v5")
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    positions = list(range(len(variants)))
    width = 0.36
    for language, offset in (("cpp", -width / 2), ("rust", width / 2)):
        means = [total_stats[(language, variant)][0] for variant in variants]
        errors = [total_stats[(language, variant)][1] for variant in variants]
        axes[0].bar(
            [position + offset for position in positions],
            means,
            width,
            yerr=errors,
            capsize=3,
            color=COLORS[language],
            label="C++" if language == "cpp" else "Rust",
        )
    axes[0].set_xticks(positions, [VARIANT_LABELS[variant] for variant in variants], rotation=15)
    axes[0].set_ylabel("Measured time (ms/frame)")
    axes[0].set_title("End-to-end variant comparison")
    axes[0].legend(frameon=False)

    labels = [f"{language.upper()} {variant.upper()}" for language in ("cpp", "rust") for variant in variants]
    keys = [(language, variant) for language in ("cpp", "rust") for variant in variants]
    bottoms = [0.0] * len(keys)
    phase_definitions = (
        ("tree_ms_per_frame", "Tree construction", "#4C78A8"),
        ("force_update_ms_per_frame", "Force and update", "#F2A541"),
        ("cleanup_ms_per_frame", "Tree cleanup", "#8C6D62"),
    )
    for field, label, color in phase_definitions:
        values = [phase_stats[field][key][0] for key in keys]
        axes[1].bar(range(len(keys)), values, bottom=bottoms, color=color, label=label)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
    axes[1].set_xticks(range(len(keys)), labels, rotation=35, ha="right")
    axes[1].set_ylabel("Measured time (ms/frame)")
    axes[1].set_title("Measured phase composition")
    axes[1].legend(frameon=False)

    figure.tight_layout()
    figure.savefig(output / "fig2_variants_100k.png", dpi=220, bbox_inches="tight")
    plt.close(figure)


def plot_figure_3(root: Path, output: Path) -> None:
    rows = read_csv(root / "fig3" / "raw_runs.csv")
    stats = aggregate(rows, ("language", "variant", "particles"), "total_ms_per_frame")
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    line_styles = {"cpp": "-", "rust": "--"}
    markers = {"v3": "o", "v4": "s", "v5": "^"}

    for language in ("cpp", "rust"):
        for variant in ("v3", "v4", "v5"):
            particle_counts = sorted(
                int(key[2]) for key in stats if key[0] == language and key[1] == variant
            )
            means = [stats[(language, variant, str(count))][0] / 1000.0 for count in particle_counts]
            errors = [stats[(language, variant, str(count))][1] / 1000.0 for count in particle_counts]
            axes[0].errorbar(
                [count / 1_000_000 for count in particle_counts],
                means,
                yerr=errors,
                linestyle=line_styles[language],
                marker=markers[variant],
                linewidth=2,
                capsize=3,
                color=VARIANT_COLORS[variant],
                label=f"{'C++' if language == 'cpp' else 'Rust'} {variant.upper()}",
            )
    axes[0].set_xlabel("Particles (millions)")
    axes[0].set_ylabel("Measured time (s/frame)")
    axes[0].set_title("Large-scale runtime")
    axes[0].legend(frameon=False, ncol=2)

    for language in ("cpp", "rust"):
        particle_counts = sorted(
            int(key[2]) for key in stats if key[0] == language and key[1] == "v3"
        )
        speedups = [
            stats[(language, "v3", str(count))][0] / stats[(language, "v5", str(count))][0]
            for count in particle_counts
        ]
        axes[1].plot(
            [count / 1_000_000 for count in particle_counts],
            speedups,
            marker="o",
            linewidth=2,
            color=COLORS[language],
            label="C++ V3/V5" if language == "cpp" else "Rust V3/V5",
        )
    axes[1].axhline(1.0, color="#666666", linewidth=1)
    axes[1].set_xlabel("Particles (millions)")
    axes[1].set_ylabel("V5 speedup over V3")
    axes[1].set_title("Parallel force-evaluation speedup")
    axes[1].legend(frameon=False)

    figure.tight_layout()
    figure.savefig(output / "fig3_scaling.png", dpi=220, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: plot_manuscript_figures.py RESULTS_ROOT OUTPUT_DIR")
    root = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    apply_style()
    plot_figure_1(root, output)
    plot_figure_2(root, output)
    plot_figure_3(root, output)


if __name__ == "__main__":
    main()
