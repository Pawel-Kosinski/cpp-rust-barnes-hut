#!/usr/bin/env python3
"""Compare a solver force snapshot with a direct-summation reference."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def read_forces(path: Path) -> list[tuple[float, float]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"Force snapshot is empty: {path}")
    forces: list[tuple[float, float]] = []
    for expected_index, row in enumerate(rows):
        if int(row["index"]) != expected_index:
            raise ValueError(f"Non-contiguous force index in {path}: {row['index']}")
        force = (float(row["acc_x"]), float(row["acc_y"]))
        if not all(math.isfinite(component) for component in force):
            raise ValueError(f"Non-finite force at index {expected_index} in {path}")
        forces.append(force)
    return forces


def percentile_nearest_rank(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(quantile * len(ordered)))
    return ordered[rank - 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--language", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--theta", default="")
    parser.add_argument("--rms-threshold", type=float, default=0.05)
    parser.add_argument("--p95-threshold", type=float, default=0.15)
    arguments = parser.parse_args()

    reference = read_forces(arguments.reference)
    candidate = read_forces(arguments.candidate)
    if len(reference) != len(candidate):
        raise SystemExit(
            f"Force snapshot length mismatch: {len(reference)} != {len(candidate)}"
        )

    difference_squared = 0.0
    reference_squared = 0.0
    local_errors: list[float] = []
    for (reference_x, reference_y), (candidate_x, candidate_y) in zip(reference, candidate):
        difference = math.hypot(candidate_x - reference_x, candidate_y - reference_y)
        reference_norm = math.hypot(reference_x, reference_y)
        difference_squared += difference * difference
        reference_squared += reference_norm * reference_norm
        if reference_norm > 1e-6:
            local_errors.append(difference / reference_norm)

    rms = math.sqrt(difference_squared / reference_squared) if reference_squared else 0.0
    p95 = percentile_nearest_rank(local_errors, 0.95)
    passed = rms <= arguments.rms_threshold and p95 <= arguments.p95_threshold
    print(
        f"{arguments.language},{arguments.variant},{len(reference)},{arguments.theta},"
        f"{rms:.9g},{p95:.9g},{arguments.rms_threshold:.9g},"
        f"{arguments.p95_threshold:.9g},{str(passed).lower()}"
    )
    if not passed:
        raise SystemExit(
            f"Force regression failed for {arguments.language} {arguments.variant}: "
            f"RMS={rms:.6g}, p95={p95:.6g}"
        )


if __name__ == "__main__":
    main()
