#!/usr/bin/env python3
"""Combine compatible raw benchmark CSV files without changing rows."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("Usage: combine_raw_results.py OUTPUT_CSV INPUT_CSV [INPUT_CSV ...]")
    output = Path(sys.argv[1])
    inputs = [Path(value) for value in sys.argv[2:]]
    fieldnames: list[str] | None = None
    rows: list[dict[str, str]] = []
    for path in inputs:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if fieldnames is None:
                fieldnames = list(reader.fieldnames or [])
            elif reader.fieldnames != fieldnames:
                raise SystemExit(f"CSV schema mismatch in {path}")
            rows.extend(reader)
    if not fieldnames or not rows:
        raise SystemExit("No raw benchmark rows to combine")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
