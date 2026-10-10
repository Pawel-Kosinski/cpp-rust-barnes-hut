#!/usr/bin/env python3
"""Regression checks for descriptive laptop-profile comparison statistics."""
import unittest

from analyze_two_hosts import speedup
from compare_laptop_profiles import configuration_statistics, variability


class ProfileStatisticsTests(unittest.TestCase):
    def rows(self, values):
        return [dict(group='workload', n=100000, distribution='plummer', seed=1337,
                     solver='cpp_v4', threads=1, repeat=i, total_ms=x, tree_ms=0, kernel_ms=x)
                for i, x in enumerate(values)]

    def test_keeps_slow_observation(self):
        config = list(configuration_statistics(self.rows([10, 10, 100])).values())[0]
        self.assertEqual(config['total_ms']['mean'], 40)
        self.assertEqual(config['total_ms']['median'], 10)
        self.assertEqual(config['repeats'], 3)
        self.assertGreater(variability([config])['max_cv_percent'], 100)

    def test_duplicate_repeat_rejected(self):
        rows = self.rows([10, 11, 12])
        rows[2]['repeat'] = rows[0]['repeat']
        with self.assertRaises(ValueError):
            configuration_statistics(rows)

    def test_missing_repeat_rejected(self):
        with self.assertRaises(ValueError):
            configuration_statistics(self.rows([10, 11]))

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            configuration_statistics(self.rows([10, float('nan'), 12]))

    def test_scaling_uses_within_block_ratios(self):
        rows = [dict(solver='cpp_v5', n=100000, threads=t, repeat=i, total_ms=x)
                for t, values in ((1, [2, 4, 8, 16, 32]), (8, [1, 1, 2, 2, 4]))
                for i, x in enumerate(values)]
        value, half = speedup(rows, 'cpp', 100000, 8, 'total_ms')
        self.assertAlmostEqual(value, 5.2)
        self.assertGreater(half, 0)
        self.assertEqual(speedup(rows, 'cpp', 100000, 1, 'total_ms'), (1, 0))


if __name__ == '__main__':
    unittest.main()
