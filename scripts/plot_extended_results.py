#!/usr/bin/env python3
"""Build supplementary figures and numerical summaries from raw campaign CSVs."""
import argparse
import csv
import json
import math
from pathlib import Path
import platform
import statistics as stats

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

COLORS = {'cpp': '#156082', 'rust': '#bd5b24'}


def read(path):
    with path.open() as stream:
        result = list(csv.DictReader(stream))
    for row in result:
        for key, value in row.items():
            try:
                row[key] = float(value)
            except ValueError:
                pass
    return result


def select(rows, **criteria):
    return [r for r in rows if all(r[k] == v for k, v in criteria.items())]


def mean(rows, field):
    return stats.mean(r[field] for r in rows)


def save(fig, path):
    fig.savefig(path, dpi=220, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.2})
    data = {name: read(args.data / f'{name}.csv') for name in ('baseline', 'workload', 'scaling', 'accuracy', 'memory', 'dynamics')}
    expected = dict(baseline=60, workload=216, scaling=120, accuracy=232, memory=24, dynamics=78)
    for name, count in expected.items():
        if len(data[name]) != count:
            raise ValueError(f'Incomplete {name}: {len(data[name])} instead of {count}')
    report = {'rows': {k: len(v) for k, v in data.items()}, 'scaling': [], 'workload_ratios': [], 'accuracy': [], 'memory': data['memory'], 'dynamics': data['dynamics']}

    fig, axes = plt.subplots(2, 2, figsize=(10, 7.4), sharex=True)
    for i, n in enumerate((100000, 1000000)):
        for j, (field, label) in enumerate((('total_ms', 'End-to-end'), ('kernel_ms', 'Force kernel only'))):
            ax = axes[i, j]
            upper = 18.0
            for language in ('cpp', 'rust'):
                one = select(data['scaling'], n=n, solver=language+'_v5', threads=1)
                baseline = {r['repeat']: r[field] for r in one}
                points, errors = [], []
                for t in (1, 2, 4, 8, 16):
                    rows = select(data['scaling'], n=n, solver=language+'_v5', threads=t)
                    ratios = [baseline[r['repeat']] / r[field] for r in rows]
                    average = stats.mean(ratios)
                    ci = 2.776445 * stats.stdev(ratios) / math.sqrt(len(ratios))
                    points.append(average)
                    errors.append(ci)
                    report['scaling'].append(dict(n=n, language=language, metric=field, threads=t, speedup=average, ci95_half=ci,
                        tree_ms=mean(rows, 'tree_ms'), kernel_ms=mean(rows, 'kernel_ms'), total_ms=mean(rows, 'total_ms')))
                ax.errorbar([1, 2, 4, 8, 16], points, yerr=errors, marker='o', capsize=3, color=COLORS[language], label='C++' if language == 'cpp' else 'Rust')
                upper = max(upper, max(v + e for v, e in zip(points, errors)) * 1.05)
            ax.plot([1, 16], [1, 16], ':', color='0.6', label='Ideal linear')
            ax.axvline(8, ls='--', color='0.75', lw=1)
            ax.set(title=f'N = {n:,}: {label}', ylabel='V5 speedup relative to V5 / 1 thread', xticks=[1, 2, 4, 8, 16], ylim=(0, upper))
            if i == 1:
                ax.set_xlabel('Worker threads (8 physical cores; 16 logical CPUs)')
            if i == 0 and j == 0:
                ax.legend(fontsize=9)
    fig.tight_layout()
    save(fig, args.output / 'extended_scaling.png')

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, n in zip(axes, (1000, 10000)):
        for offset, language in ((-0.18, 'cpp'), (0.18, 'rust')):
            series = [select(data['baseline'], n=n, solver=f'{language}_v{v}') for v in range(1, 6)]
            ax.bar(np.arange(1, 6)+offset, [mean(r, 'total_ms') for r in series], 0.34,
                   yerr=[stats.stdev(x['total_ms'] for x in r) for r in series], capsize=3,
                   color=COLORS[language], label='C++' if language == 'cpp' else 'Rust')
        ax.set(yscale='log', xticks=range(1, 6), xticklabels=['V1', 'V2', 'V3', 'V4', 'V5'],
               title=f'N = {n:,}', ylabel='End-to-end time per frame (ms)')
        ax.legend()
    fig.tight_layout()
    save(fig, args.output / 'extended_baseline.png')

    matrix, labels = [], []
    for distribution in ('plummer', 'uniform', 'clustered'):
        for seed in (1337, 42, 2026):
            row = []
            labels.append(f'{distribution} / {seed}')
            for language in ('cpp', 'rust'):
                for a, b in ((2, 3), (3, 4), (4, 5)):
                    ratio = mean(select(data['workload'], distribution=distribution, seed=seed, solver=f'{language}_v{a}'), 'total_ms') / mean(select(data['workload'], distribution=distribution, seed=seed, solver=f'{language}_v{b}'), 'total_ms')
                    row.append(ratio)
                    report['workload_ratios'].append(dict(distribution=distribution, seed=seed, language=language, transition=f'V{a}/V{b}', speedup=ratio))
            matrix.append(row)
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.imshow(np.log2(matrix), cmap='YlGnBu', vmin=0, vmax=4, aspect='auto')
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            ax.text(j, i, f'{value:.2f}', ha='center', va='center', color='white' if value > 4 else '#142b38')
    ax.set(xticks=range(6), xticklabels=['C++\nV2/V3', 'C++\nV3/V4', 'C++\nV4/V5', 'Rust\nV2/V3', 'Rust\nV3/V4', 'Rust\nV4/V5'], yticks=range(9), yticklabels=labels,
           title='End-to-end speedup: ratio of three-process means per input')
    ax.grid(False)
    fig.tight_layout()
    save(fig, args.output / 'extended_workloads.png')

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for distribution, marker in zip(('plummer', 'uniform', 'clustered'), ('o', 's', '^')):
        for language in ('cpp', 'rust'):
            rows = [select(data['memory'], distribution=distribution, solver=f'{language}_v{v}')[0] for v in range(2, 6)]
            offset = -0.03 if language == 'cpp' else 0.03
            for ax, field, divisor in ((axes[0], 'structural_bytes', 2**20), (axes[1], 'tree_heap_blocks', 1)):
                ax.plot(np.arange(2, 6)+offset, [r[field]/divisor for r in rows], marker=marker, color=COLORS[language], ls='-' if language == 'cpp' else '--', label=f'{language} / {distribution}')
    axes[0].set(ylabel='Reserved structural storage (MiB)', title='Not process RSS or allocator overhead')
    axes[1].set(ylabel='Live tree heap blocks', yscale='log', title='Not cumulative allocation-event counts')
    for ax in axes:
        ax.set(xticks=range(2, 6), xticklabels=['V2', 'V3', 'V4', 'V5'])
    axes[0].legend(fontsize=8, ncol=2)
    fig.tight_layout()
    save(fig, args.output / 'extended_memory.png')

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for distribution, color in zip(('plummer', 'uniform', 'clustered'), ('#156082', '#bd5b24', '#547b35')):
        vals, low, high = [], [], []
        for theta in (0.1, 0.3, 0.7):
            rows = select(data['accuracy'], n=10000, distribution=distribution, theta=theta)
            errors = [r['rms_relative']*100 for r in rows]
            vals.append(stats.mean(errors)); low.append(min(errors)); high.append(max(errors))
            report['accuracy'].append(dict(n=10000, distribution=distribution, theta=theta, min_rms_pct=min(errors), max_rms_pct=max(errors), max_p95_pct=max(r['p95_particle_relative']*100 for r in rows)))
        axes[0].plot([0.1, 0.3, 0.7], vals, 'o-', color=color, label=distribution)
        axes[0].fill_between([0.1, 0.3, 0.7], low, high, color=color, alpha=0.15)
    axes[0].set(yscale='log', xlabel='Opening threshold', ylabel='Global RMS force error (%)', title='10,000 particles: all V2-V5, both languages')
    axes[0].legend()
    for language, offset in (('cpp', -0.025), ('rust', 0.025)):
        for variant, marker in zip(range(2, 6), ('o', 's', '^', 'x')):
            rows = [select(data['accuracy'], n=n, solver=f'{language}_v{variant}')[0] for n in (1000000, 5000000)]
            axes[1].plot(np.array([1, 5])+offset, [r['rms_relative']*100 for r in rows], marker=marker, color=COLORS[language], ls='-' if language == 'cpp' else '--', label=f'{language} V{variant}')
    axes[1].set(xlabel='Particle count (millions)', ylabel='Sampled RMS force error (%)', title='256 fixed target indices; theta = 0.3', xticks=[1, 5])
    axes[1].legend(fontsize=8, ncol=2)
    fig.tight_layout()
    save(fig, args.output / 'extended_accuracy.png')

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for language in ('cpp', 'rust'):
        rows = select(data['dynamics'], solver=language+'_v1')
        for field, marker in (('position_error_rk4', 'o'), ('velocity_error_rk4', 's')):
            axes[0].loglog([r['dt'] for r in rows], [r[field] for r in rows], marker=marker,
                           color=COLORS[language], ls='-' if 'position' in field else '--', label=f'{language}: '+field.split('_')[0])
    axes[0].set(xlabel='Timestep', ylabel='Relative final-state error vs double RK4', title='V1: temporal discretization and rounding')
    axes[0].legend(fontsize=8)
    for theta, color in zip((0.1, 0.3, 0.7), ('#156082', '#bd5b24', '#547b35')):
        rows = select(data['dynamics'], solver='cpp_v3', theta=theta)
        axes[1].loglog([r['dt'] for r in rows], [r['velocity_difference_direct'] for r in rows], 'o-', color=color, label=f'theta = {theta}')
    axes[1].set(xlabel='Timestep', ylabel='Relative velocity difference vs V1 / same step', title='V3: approximation is not removed by step refinement')
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    save(fig, args.output / 'extended_dynamics.png')
    (args.output / 'extended_summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    environment = dict(python=platform.python_version(), numpy=np.__version__,
                       matplotlib=matplotlib.__version__, system=platform.platform(),
                       purpose='Derived figures and descriptive summaries; not the solver execution environment')
    (args.data / 'analysis_environment.json').write_text(json.dumps(environment, indent=2), encoding='utf-8')
    print('Verified row counts and created six supplementary figures.')


if __name__ == '__main__':
    main()
