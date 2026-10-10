#!/usr/bin/env python3
"""Export numerical LaTeX tables from completed extended-validation records."""
import argparse
from pathlib import Path
import statistics as stats

from plot_extended_results import read, select, mean


def latex_table(headers, rows, caption, align=None):
    align = align or 'l' + 'r' * (len(headers)-1)
    return '\n'.join([r'\begin{table}[H]\centering\small',
        r'\begin{tabular}{'+align+'}', r'\toprule', ' & '.join(headers)+r' \\', r'\midrule',
        *[' & '.join(map(str, row))+r' \\' for row in rows], r'\bottomrule',
        r'\end{tabular}', r'\caption{'+caption+'}', r'\end{table}', ''])


def number(value):
    return f'{value:.2e}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    workload = read(args.data / 'workload.csv')
    scaling = read(args.data / 'scaling.csv')
    accuracy = read(args.data / 'accuracy.csv')
    memory = read(args.data / 'memory.csv')
    dynamics = read(args.data / 'dynamics.csv')
    probe = read(args.data / 'wait_policy.csv')
    text, rows = [], []
    for distribution in ('plummer', 'uniform', 'clustered'):
        for seed in (1337, 42, 2026):
            ratios = []
            for language in ('cpp', 'rust'):
                for a, b in ((2, 3), (3, 4), (4, 5)):
                    ratios.append(mean(select(workload, distribution=distribution, seed=seed, solver=f'{language}_v{a}'), 'total_ms') / mean(select(workload, distribution=distribution, seed=seed, solver=f'{language}_v{b}'), 'total_ms'))
            rows.append([distribution, seed, *[f'{v:.2f}' for v in ratios]])
    text.append(latex_table(['Input', 'Seed', 'C++ 2/3', 'C++ 3/4', 'C++ 4/5', 'Rust 2/3', 'Rust 3/4', 'Rust 4/5'], rows,
        'End-to-end ratios of three-process means at $N=10^5$. Column labels identify the V2/V3, V3/V4 and V4/V5 transitions.', 'lrrrrrrr'))
    rows = []
    for solver, threads, policy in (('cpp_v4', 1, 'default'), ('cpp_v5', 1, 'default'), ('cpp_v5', 16, 'default'), ('cpp_v5', 16, 'ACTIVE'), ('cpp_v5', 16, 'PASSIVE')):
        items = select(probe, solver=solver, threads=threads, policy=policy)
        row = [solver.replace('cpp_', '').upper(), threads, policy]
        for field in ('tree_ms', 'kernel_ms', 'total_ms'):
            row.append(f"{mean(items, field):.2f} $\\pm$ {stats.stdev(r[field] for r in items):.2f}")
        rows.append(row)
    text.append(latex_table(['Variant', 'Workers', 'Policy', 'Tree (ms)', 'Kernel (ms)', 'Total (ms)'], rows,
        'Controlled waiting-policy probe: means and sample standard deviations of five processes, with one warm-up and five measured frames. This does not identify the cause of every historical V4/V5 difference.', 'lrllrr'))
    rows = []
    for language in ('cpp', 'rust'):
        for n in (100000, 1000000):
            for t in (1, 2, 4, 8, 16):
                items = select(scaling, solver=language+'_v5', n=n, threads=t)
                baseline = {r['repeat']: r for r in select(scaling, solver=language+'_v5', n=n, threads=1)}
                row = [language, f'{n//1000}k', t]
                for field in ('total_ms', 'kernel_ms'):
                    values = [baseline[r['repeat']][field]/r[field] for r in items]
                    ci = 2.776445*stats.stdev(values)/len(values)**0.5
                    row.append(f'{stats.mean(values):.2f} $\\pm$ {ci:.2f}')
                row.append(f"{mean(items, 'tree_ms'):.2f}")
                rows.append(row)
    text.append(latex_table(['Language', '$N$', 'Workers', '$S_T$ (95\\% CI)', '$S_F$ (95\\% CI)', 'Tree (ms)'], rows,
        'Mean within-block V5 self-speedups with confidence-interval half-widths. Tree time is the five-process mean.', 'lrrrrr'))
    rows = []
    for distribution in ('plummer', 'uniform', 'clustered'):
        for theta in (0.1, 0.3, 0.7):
            items = select(accuracy, n=10000, distribution=distribution, theta=theta)
            row = [distribution, theta]
            for field in ('rms_relative', 'p95_particle_relative'):
                values = [100*r[field] for r in items]
                row.append(f'{min(values):.3f}--{max(values):.3f}')
            rows.append(row)
    for n in (1000000, 5000000):
        items = select(accuracy, n=n)
        row = [f'{n//1000000}M (sample)', 0.3]
        for field in ('rms_relative', 'p95_particle_relative'):
            values = [100*r[field] for r in items]
            row.append(f'{min(values):.3f}--{max(values):.3f}')
        rows.append(row)
    text.append(latex_table(['Input', '$\\theta$', 'RMS (\\%)', 'Local p95 (\\%)'], rows,
        'Ranges across all checked approximate implementations and, at $N=10^4$, three seeds. Large-system rows describe only 256 selected targets; ranges are not statistical confidence intervals.', 'lrrr'))
    rows = []
    for solver in [f'{lang}_v{v}' for lang in ('cpp', 'rust') for v in range(2, 6)]:
        r = select(memory, solver=solver, distribution='plummer')[0]
        rows.append([solver.replace('_', ' '), int(r['node_bytes']), int(r['tree_nodes']), int(r['tree_capacity']),
                     int(r['tree_heap_blocks']), f"{r['structural_bytes']/2**20:.2f}"])
    text.append(latex_table(['Solver', 'Node B', 'Live nodes', 'Capacity', 'Heap blocks', 'Total MiB'], rows,
        'Structural memory at $N=10^5$, Plummer seed 1337. Total includes particle capacity and any force buffer, not runtime/allocator overhead. The Rust V2 root is stack-resident.', 'lrrrrr'))
    text += [r'\begingroup\scriptsize\setlength{\tabcolsep}{3pt}',
             r'\begin{longtable}{llrrrrrrr}',
             r'\caption{Complete dynamics results. $d_P,d_L,d_E$ are maximum normalized drifts. $e_x,e_v$ compare the final state to RK4; $b_v$ compares velocity to same-step V1. Scientific notation is dimensionless.}\\',
             r'\toprule Solver & $\Delta t$ & $\theta$ & $d_P$ & $d_L$ & $d_E$ & $e_x$ & $e_v$ & $b_v$ \\ \midrule\endfirsthead',
             r'\toprule Solver & $\Delta t$ & $\theta$ & $d_P$ & $d_L$ & $d_E$ & $e_x$ & $e_v$ & $b_v$ \\ \midrule\endhead']
    for r in sorted(dynamics, key=lambda r: (r['solver'], -r['dt'], r['theta'])):
        fields = ['max_momentum_drift', 'max_angular_drift', 'max_energy_drift', 'position_error_rk4', 'velocity_error_rk4', 'velocity_difference_direct']
        text.append(' & '.join([r['solver'].replace('_', ' '), str(r['dt']), '-' if r['solver'].endswith('v1') else str(r['theta']), *[number(r[k]) for k in fields]])+r' \\')
    text += [r'\bottomrule\end{longtable}\endgroup']
    args.output.write_text('\n'.join(text)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
