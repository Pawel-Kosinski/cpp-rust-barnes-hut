#!/usr/bin/env python3
"""Reproduce cross-host summaries without pooling runs from different hosts."""
import argparse
import csv
import json
import math
from pathlib import Path
import platform
import statistics as st

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from audit_laptop import read_csv, read_json, require, sha

COLORS = {'cpp': '#156082', 'rust': '#bd5b24'}
HOSTS = ('Ryzen 7 5800X3D', 'Core i7-11370H')


def numeric(rows):
    for row in rows:
        for key, value in row.items():
            try:
                row[key] = float(value)
            except ValueError:
                pass
    return rows


def subset(rows, **keys):
    return [r for r in rows if all(r[k] == v for k, v in keys.items())]


def mean(rows, field):
    return st.mean(r[field] for r in rows)


def spread(rows, field):
    return st.stdev(r[field] for r in rows)


def speedup(rows, language, n, threads, field):
    one = {r['repeat']: r[field] for r in subset(rows, solver=language+'_v5', n=n, threads=1)}
    many = subset(rows, solver=language+'_v5', n=n, threads=threads)
    require(len(one) == len(many) == 5, 'Scaling needs five repetition blocks')
    ratios = [one[r['repeat']] / r[field] for r in many]
    return st.mean(ratios), 2.776445 * st.stdev(ratios) / math.sqrt(5)


def pm(value, half):
    return f'{value:.2f} $\\pm$ {half:.2f}'


def table(header, rows, caption, label, columns):
    return '\n'.join([r'\begin{table}[H]\centering\small', r'\begin{tabular}{'+columns+'}',
                      r'\toprule', header + r' \\', r'\midrule', *[r + r' \\' for r in rows],
                      r'\bottomrule', r'\end{tabular}', r'\caption{'+caption+'}',
                      r'\label{'+label+'}', r'\end{table}', ''])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ryzen', type=Path, required=True)
    parser.add_argument('--laptop', type=Path, required=True, help='Curated archive containing raw/ and analysis/')
    parser.add_argument('--figures', type=Path, required=True)
    parser.add_argument('--tables', type=Path, required=True)
    args = parser.parse_args()
    audit = read_json(args.laptop/'analysis/audit.json')
    require(audit['status'] == 'passed' and audit['process_records'] == 430, 'Audit must pass first')
    laptop = numeric(read_csv(args.laptop/'raw/timings.csv'))
    data = {HOSTS[0]: {k: numeric(read_csv(args.ryzen/(k+'.csv'))) for k in ('baseline', 'workload', 'scaling')},
            HOSTS[1]: {k: subset(laptop, group=k) for k in ('baseline', 'workload', 'scaling')}}
    thread_counts = {HOSTS[0]: [1, 2, 4, 8, 16], HOSTS[1]: [1, 2, 4, 8]}
    physical = {HOSTS[0]: 8, HOSTS[1]: 4}
    summary = {'source_timings_sha256': sha(args.laptop/'raw/timings.csv'),
               'scaling': [], 'workload_ratios': [], 'process_variability': [],
               'analysis_environment': dict(python=platform.python_version(), numpy=np.__version__, matplotlib=matplotlib.__version__)}
    args.figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': .2})
    for host in HOSTS:
        for n in (100000, 1000000):
            for language in COLORS:
                for threads in thread_counts[host]:
                    rows = subset(data[host]['scaling'], n=n, solver=language+'_v5', threads=threads)
                    point = dict(host=host, n=n, language=language, threads=threads)
                    for field in ('total_ms', 'kernel_ms'):
                        value, half = speedup(data[host]['scaling'], language, n, threads, field)
                        point[field+'_speedup'], point[field+'_ci95_half'] = value, half
                    for field in ('tree_ms', 'kernel_ms', 'total_ms'):
                        point[field+'_mean'], point[field+'_sd'] = mean(rows, field), spread(rows, field)
                    summary['scaling'].append(point)
        for distribution in ('plummer', 'uniform', 'clustered'):
            for seed in (1337, 42, 2026):
                for language in COLORS:
                    for a, b in ((2, 3), (3, 4), (4, 5)):
                        left = subset(data[host]['workload'], distribution=distribution, seed=seed, solver=f'{language}_v{a}')
                        right = subset(data[host]['workload'], distribution=distribution, seed=seed, solver=f'{language}_v{b}')
                        ratio = mean(left, 'total_ms')/mean(right, 'total_ms')
                        summary['workload_ratios'].append(dict(host=host, distribution=distribution, seed=seed,
                                                             language=language, transition=f'V{a}/V{b}', speedup=ratio))
        for group, rows in data[host].items():
            keys = sorted({(r['n'], r.get('distribution', 'plummer'), r.get('seed', 1337), r['solver'], r['threads']) for r in rows})
            for n, distribution, seed, solver, threads in keys:
                selected = [r for r in rows if r['n'] == n and r['solver'] == solver and r['threads'] == threads
                            and r.get('distribution', 'plummer') == distribution and r.get('seed', 1337) == seed]
                summary['process_variability'].append(dict(host=host, group=group, n=n, distribution=distribution,
                    seed=seed, solver=solver, threads=threads, repeats=len(selected),
                    mean_ms=mean(selected, 'total_ms'), sd_ms=spread(selected, 'total_ms'),
                    cv_percent=100*spread(selected, 'total_ms')/mean(selected, 'total_ms')))

    fig, axes = plt.subplots(2, 2, figsize=(10, 6.8))
    for i, host in enumerate(HOSTS):
        for j, (field, title) in enumerate((('total_ms', 'Complete frame'), ('kernel_ms', 'Force kernel'))):
            ax = axes[i, j]
            ts = thread_counts[host]
            for language, color in COLORS.items():
                points = subset(summary['scaling'], host=host, language=language, n=1000000)
                ax.errorbar(ts, [p[field+'_speedup'] for p in points],
                            yerr=[p[field+'_ci95_half'] for p in points], marker='o', capsize=3, color=color,
                            label='C++' if language == 'cpp' else 'Rust')
            ax.plot([1, ts[-1]], [1, ts[-1]], ':', color='.65', label='Ideal linear')
            ax.axvline(physical[host], ls='--', color='.7', lw=1)
            ax.set(title=host+' / '+title, xlabel=f'Workers ({physical[host]} physical / {ts[-1]} logical)',
                   ylabel='Speedup relative to V5 / 1 worker', xticks=ts, ylim=(0, ts[-1]*1.08))
            if i == j == 0:
                ax.legend(fontsize=8, loc='upper left')
    fig.tight_layout()
    fig.savefig(args.figures/'two_host_scaling.png', dpi=240, bbox_inches='tight')
    plt.close(fig)

    labels, matrix, rows_tex = [], [], []
    for distribution in ('plummer', 'uniform', 'clustered'):
        for seed in (1337, 42, 2026):
            cells = []
            for language in COLORS:
                for transition in ('V2/V3', 'V3/V4', 'V4/V5'):
                    cells.append(subset(summary['workload_ratios'], host=HOSTS[1], language=language,
                                        transition=transition, distribution=distribution, seed=seed)[0]['speedup'])
            labels.append(f'{distribution} / {seed}')
            matrix.append(cells)
            rows_tex.append(f'{distribution} & {seed} & '+' & '.join(f'{v:.2f}' for v in cells))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.imshow(np.log2(matrix), cmap='YlGnBu', vmin=0, vmax=4, aspect='auto')
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            ax.text(j, i, f'{value:.2f}', ha='center', va='center', color='white' if value > 4 else '#142b38')
    ax.set(xticks=range(6), xticklabels=['C++\nV2/V3', 'C++\nV3/V4', 'C++\nV4/V5', 'Rust\nV2/V3', 'Rust\nV3/V4', 'Rust\nV4/V5'],
           yticks=range(9), yticklabels=labels, title='Core i7-11370H: ratio of three-process mean frame times')
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(args.figures/'laptop_workloads.png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    tables = table('Input & Seed & C++ 2/3 & C++ 3/4 & C++ 4/5 & Rust 2/3 & Rust 3/4 & Rust 4/5', rows_tex,
                   'Laptop workload ratios, $N=10^5$. V5 uses eight workers; other variants are serial. These are ratios of means, not confidence bounds.',
                   'tab:laptop_workloads', 'lrrrrrrr')

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, n in zip(axes, (1000, 10000)):
        for offset, (language, color) in zip((-.18, .18), COLORS.items()):
            series = [subset(data[HOSTS[1]]['baseline'], n=n, solver=f'{language}_v{v}') for v in range(1, 6)]
            ax.bar(np.arange(1, 6)+offset, [mean(r, 'total_ms') for r in series], .34,
                   yerr=[spread(r, 'total_ms') for r in series], capsize=3, color=color,
                   label='C++' if language == 'cpp' else 'Rust')
        ax.set(yscale='log', xticks=range(1, 6), xticklabels=['V1', 'V2', 'V3', 'V4', 'V5'],
               title=f'Core i7-11370H / N = {n:,}', ylabel='Complete frame time (ms)')
        ax.legend()
    fig.tight_layout()
    fig.savefig(args.figures/'laptop_baseline.png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    for n in (100000, 1000000):
        rows_tex = []
        for language in COLORS:
            for p in subset(summary['scaling'], host=HOSTS[1], n=n, language=language):
                rows_tex.append(('C++' if language == 'cpp' else 'Rust') + f" & {p['threads']} & " +
                    ' & '.join(pm(p[f+'_mean'], p[f+'_sd']) for f in ('tree_ms', 'kernel_ms', 'total_ms')) + ' & ' +
                    ' & '.join(pm(p[f+'_speedup'], p[f+'_ci95_half']) for f in ('kernel_ms', 'total_ms')))
        # A full-width table remains legible at the supplementary document's 11 pt base size.
        tables += table('Language & $p$ & Tree (ms) & Kernel (ms) & Frame (ms) & $S_F$ & $S_T$', rows_tex,
                        f'Laptop V5 scaling at $N={n:,}$. Times are means $\\pm$ sample SD; speedups are means of five within-block ratios $\\pm$ 95\\% CI half-width. The one-worker ratio is one by definition.',
                        f'tab:laptop_scaling{n}', 'lrrrrrr').replace(r'\centering\small', r'\centering\footnotesize\setlength{\tabcolsep}{3pt}')
    args.tables.write_text(tables, encoding='utf-8')
    (args.laptop/'analysis/two_host_summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    for host in HOSTS:
        for language in COLORS:
            last = subset(summary['scaling'], host=host, language=language, n=1000000, threads=thread_counts[host][-1])[0]
            print(host, language, 'frame', pm(last['total_ms_speedup'], last['total_ms_ci95_half']),
                  'kernel', pm(last['kernel_ms_speedup'], last['kernel_ms_ci95_half']))
            for transition in ('V2/V3', 'V3/V4', 'V4/V5'):
                ratios = [r['speedup'] for r in subset(summary['workload_ratios'], host=host, language=language, transition=transition)]
                print(' ', transition, f'{min(ratios):.3f}--{max(ratios):.3f}')
    print('Largest process CV:', max(summary['process_variability'], key=lambda r: r['cv_percent']))


if __name__ == '__main__':
    main()
