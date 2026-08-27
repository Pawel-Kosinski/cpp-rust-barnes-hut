#!/usr/bin/env python3
"""Produce a version-independent deterministic shuffle for one benchmark block."""

from __future__ import annotations

import argparse


MASK_64 = (1 << 64) - 1
GOLDEN_GAMMA = 0x9E3779B97F4A7C15


class SplitMix64:
    def __init__(self, seed: int) -> None:
        self.state = seed & MASK_64

    def next(self) -> int:
        self.state = (self.state + GOLDEN_GAMMA) & MASK_64
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK_64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK_64
        return value ^ (value >> 31)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--repeat", type=int, required=True)
    parser.add_argument("configurations", nargs="+")
    arguments = parser.parse_args()

    configurations = list(arguments.configurations)
    random = SplitMix64(arguments.seed + arguments.repeat * GOLDEN_GAMMA)
    for index in range(len(configurations) - 1, 0, -1):
        swap_index = random.next() % (index + 1)
        configurations[index], configurations[swap_index] = (
            configurations[swap_index],
            configurations[index],
        )
    print("\n".join(configurations))


if __name__ == "__main__":
    main()
