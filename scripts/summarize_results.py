#!/usr/bin/env python3
"""Aggregate one-row-per-process benchmark data using sample standard deviation."""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


GROUP_FIELDS = (
    "language",
    "variant",
    "particles",
    "measured_frames",
    "warmup_frames",
    "theta",
    "seed",
    "effective_threads",
)
METRICS = (
    "tree_ms_per_frame",
    "force_update_ms_per_frame",
    "cleanup_ms_per_frame",
    "total_ms_per_frame",
    "total_run_ms",
)
LANGUAGE_ORDER = {"cpp": 0, "rust": 1}
VARIANT_ORDER = {f"v{index}": index for index in range(1, 6)}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: summarize_results.py RAW_CSV SUMMARY_CSV")

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    with input_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise SystemExit(f"No benchmark rows found in {input_path}")

    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in GROUP_FIELDS)].append(row)

    fieldnames = [*GROUP_FIELDS, "runs"]
    for metric in METRICS:
        fieldnames.extend((f"{metric}_mean", f"{metric}_sd"))

    def sort_key(item: tuple[tuple[str, ...], list[dict[str, str]]]) -> tuple[object, ...]:
        values = dict(zip(GROUP_FIELDS, item[0]))
        return (
            int(values["particles"]),
            float(values["theta"]),
            LANGUAGE_ORDER.get(values["language"], 99),
            VARIANT_ORDER.get(values["variant"], 99),
            int(values["effective_threads"]),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for key, group in sorted(groups.items(), key=sort_key):
            output = dict(zip(GROUP_FIELDS, key))
            output["runs"] = len(group)
            for metric in METRICS:
                values = [float(row[metric]) for row in group]
                output[f"{metric}_mean"] = f"{statistics.mean(values):.9f}"
                output[f"{metric}_sd"] = f"{statistics.stdev(values):.9f}" if len(values) > 1 else "0.000000000"
            writer.writerow(output)


if __name__ == "__main__":
    main()
