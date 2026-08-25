#!/usr/bin/env python3
"""Create timing plots from scripts/run_benchmarks.sh summary output."""
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/plot_results.py SUMMARY_CSV OUTPUT_DIR")
    rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="")))
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    for field, label in (("tree_ms_mean", "Tree construction (ms/frame)"), ("force_ms_mean", "Force evaluation (ms/frame)"), ("total_ms_mean", "Total time (ms)")):
        labels = [f"{row['language']} {row['variant']}" for row in rows]
        values = [float(row[field]) for row in rows]
        errors = [float(row[field.replace('mean', 'std')]) for row in rows]
        plt.figure(figsize=(9, 4.5))
        plt.bar(labels, values, yerr=errors, capsize=4)
        plt.ylabel(label)
        plt.xticks(rotation=35, ha="right")
        plt.tight_layout()
        plt.savefig(output / f"{field}.png", dpi=180)
        plt.close()


if __name__ == "__main__":
    main()
