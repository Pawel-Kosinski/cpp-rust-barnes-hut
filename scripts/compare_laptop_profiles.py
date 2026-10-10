#!/usr/bin/env python3
"""Compare two audited, sequential laptop series without pooling or filtering."""
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

from analyze_two_hosts import numeric, pm, speedup, subset, table
from audit_laptop import read_csv, read_json, require, sha, within

KEYS = ('group', 'n', 'distribution', 'seed', 'solver', 'threads')
FIELDS = ('total_ms', 'tree_ms', 'kernel_ms')
LABELS = ('First series (Turbo-labelled plan)', 'Performance repetition')
COLORS = ('#156082', '#bd5b24')


def configuration_statistics(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(tuple(row[k] for k in KEYS), []).append(row)
    result = {}
    for key, selected in sorted(grouped.items()):
        expected = 5 if key[0] == 'scaling' else 3
        require(len(selected) == len({r['repeat'] for r in selected}) == expected,
                f'Missing or duplicate repetitions: {key}')
        values = dict(zip(KEYS, key), repeats=len(selected))
        for field in FIELDS:
            samples = [r[field] for r in selected]
            require(all(math.isfinite(x) and x >= 0 for x in samples), f'Invalid timing: {key}')
            avg, sd = st.mean(samples), st.stdev(samples)
            require(field != 'total_ms' or avg > 0, f'Nonpositive frame time: {key}')
            values[field] = dict(mean=avg, sd=sd, median=st.median(samples),
                                 cv_percent=100*sd/avg if avg else None)
        result[key] = values
    return result


def variability(configs):
    values = [c['total_ms']['cv_percent'] for c in configs]
    return dict(configurations=len(values), median_cv_percent=st.median(values),
                max_cv_percent=max(values), above_10_percent=sum(x > 10 for x in values),
                above_20_percent=sum(x > 20 for x in values),
                maximum_configuration=max(configs, key=lambda c: c['total_ms']['cv_percent']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first', type=Path, required=True)
    parser.add_argument('--performance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--figures', type=Path, required=True)
    parser.add_argument('--tables', type=Path, required=True)
    args = parser.parse_args()
    archives = (args.first, args.performance)
    reports = [read_json(p/'analysis/audit.json') for p in archives]
    require(all(r['status'] == 'passed' and r['process_records'] == 430 for r in reports), 'Audit both series first')
    plans = [read_json(p/'raw/plan.json') for p in archives]
    require(plans[0] == plans[1], 'Plans/order differ')
    critical = []
    for root in archives:
        manifest = read_json(root/'payload/kit-manifest.json')
        entries = {item['path'].replace('\\', '/'): item['sha256'] for item in manifest['files']}
        # The second kit adds a profile declaration, not a computational asset.
        identities = {k: v for k, v in entries.items()
                      if k.startswith(('bin/', 'inputs/', 'references/', 'provenance/'))
                      and k != 'provenance/comparison-profile.json'}
        require(all(sha(within(root/'payload', k)) == v for k, v in identities.items()), 'Payload changed')
        critical.append(identities)
    require(critical[0] == critical[1], 'Computational payloads differ')
    force_pairs = []
    for case in plans[0]['Full']:
        if case['group'] != 'correctness':
            continue
        hashes = []
        for root in archives:
            record = read_json(root/'raw/records'/(case['id']+'.json'))
            files = [k for k in record['artifacts'] if k.endswith('forces.csv')]
            require(len(files) == 1, 'Missing or ambiguous force dump')
            hashes.append(sha(within(root/'raw', files[0])))
        require(hashes[0] == hashes[1], f'Force results changed: {case["id"]}')
        force_pairs.append(dict(case_id=case['id'], sha256=hashes[0]))
    require(len(force_pairs) == 54, 'Expected 54 paired force files')
    rows = [numeric(read_csv(p/'raw/timings.csv')) for p in archives]
    require(all(len(r) == len({x['case_id'] for x in r}) == 376 for r in rows), 'Timing coverage mismatch')
    require({r['case_id'] for r in rows[0]} == {r['case_id'] for r in rows[1]}, 'Unmatched timing cases')
    configurations = [configuration_statistics(r) for r in rows]
    require(configurations[0].keys() == configurations[1].keys() and len(configurations[0]) == 112,
            'Unmatched timing configurations')
    environments = [read_json(p/'raw/environment.json') for p in archives]
    summary = dict(status='passed', campaigns=[], byte_identical_force_pairs=force_pairs,
                   identical_computational_files=len(critical[0]), configurations=[], scaling=[], workloads=[],
                   limitations='Sequential series, not randomized power-mode crossover; no clock/temperature/load telemetry. No observations removed or pooled.',
                   analysis_environment=dict(python=platform.python_version(), numpy=np.__version__, matplotlib=matplotlib.__version__))
    for label, root, env, config in zip(LABELS, archives, environments, configurations):
        summary['campaigns'].append(dict(label=label, environment=env,
            timings_sha256=sha(root/'raw/timings.csv'), accuracy_sha256=sha(root/'raw/accuracy.csv'),
            kit_manifest_sha256=sha(root/'payload/kit-manifest.json'),
            overall=variability(list(config.values())),
            groups={g: variability([c for c in config.values() if c['group'] == g]) for g in ('baseline', 'workload', 'scaling')}))
    for key, first in configurations[0].items():
        second = configurations[1][key]
        summary['configurations'].append(dict(**dict(zip(KEYS, key)), first=first, performance=second,
            frame_time_change_percent=100*(second['total_ms']['mean']/first['total_ms']['mean']-1)))
    for index, series in enumerate(rows):
        scaling = subset(series, group='scaling')
        for n in (100000, 1000000):
            for language in ('cpp', 'rust'):
                for threads in (1, 2, 4, 8):
                    config = configurations[index][('scaling', n, 'plummer', 1337, language+'_v5', threads)]
                    item = dict(series=index, n=n, language=language, threads=threads, times=config)
                    for field in ('total_ms', 'kernel_ms'):
                        value, half = speedup(scaling, language, n, threads, field)
                        item[field] = dict(speedup=value, ci95_half=half)
                    summary['scaling'].append(item)
        for distribution in ('plummer', 'uniform', 'clustered'):
            for seed in (1337, 42, 2026):
                for language in ('cpp', 'rust'):
                    means = [configurations[index][('workload', 100000, distribution, seed, f'{language}_v{v}', 8 if v == 5 else 1)]['total_ms']['mean'] for v in range(2, 6)]
                    summary['workloads'].append(dict(series=index, distribution=distribution, seed=seed, language=language,
                        means_ms=means, decreasing_mean_order=all(a > b for a, b in zip(means, means[1:])),
                        ratios={f'V{v}/V{v+1}': means[v-2]/means[v-1] for v in (2, 3, 4)}))
    changes = [c['frame_time_change_percent'] for c in summary['configurations']]
    summary['matched_configuration_changes'] = dict(median_percent=st.median(changes), min_percent=min(changes), max_percent=max(changes),
        lower_frame_mean=sum(x < 0 for x in changes), lower_cv=sum(c['performance']['total_ms']['cv_percent'] < c['first']['total_ms']['cv_percent'] for c in summary['configurations']))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'profile_comparison.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    with (args.output/'matched_configurations.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = list(KEYS) + ['repeats', 'first_mean_ms', 'performance_mean_ms', 'first_cv_percent', 'performance_cv_percent', 'frame_time_change_percent']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for c in summary['configurations']:
            writer.writerow(dict(**{k: c[k] for k in KEYS}, repeats=c['first']['repeats'],
                first_mean_ms=c['first']['total_ms']['mean'], performance_mean_ms=c['performance']['total_ms']['mean'],
                first_cv_percent=c['first']['total_ms']['cv_percent'], performance_cv_percent=c['performance']['total_ms']['cv_percent'],
                frame_time_change_percent=c['frame_time_change_percent']))

    args.figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.2))
    for group, marker in (('baseline', 'o'), ('workload', 's'), ('scaling', '^')):
        pairs = [c for c in summary['configurations'] if c['group'] == group]
        axes[0, 0].scatter([c['first']['total_ms']['mean'] for c in pairs], [c['performance']['total_ms']['mean'] for c in pairs], label=group, marker=marker, s=20, alpha=.7)
        axes[0, 1].scatter([c['first']['total_ms']['cv_percent'] for c in pairs], [c['performance']['total_ms']['cv_percent'] for c in pairs], label=group, marker=marker, s=20, alpha=.7)
    axes[0, 0].plot([.01, 30000], [.01, 30000], ':', color='.5')
    axes[0, 0].set(xscale='log', yscale='log', xlabel='First series: mean frame time (ms)', ylabel='Performance: mean frame time (ms)', title='All 112 matched configurations')
    axes[0, 1].plot([0, 35], [0, 35], ':', color='.5')
    axes[0, 1].set(xlabel='First series: frame-time CV (%)', ylabel='Performance: frame-time CV (%)', title='Within-configuration variability')
    axes[0, 0].legend(fontsize=8)
    for ax, field, label in zip(axes[1], ('total_ms', 'kernel_ms'), ('Complete frame', 'Force kernel')):
        for index, color in enumerate(COLORS):
            for language, marker in (('cpp', 'o'), ('rust', 's')):
                points = subset(summary['scaling'], series=index, language=language, n=1000000)
                ax.errorbar([p['threads'] for p in points], [p[field]['speedup'] for p in points], yerr=[p[field]['ci95_half'] for p in points],
                            color=color, marker=marker, ls='-' if language == 'cpp' else '--', capsize=2,
                            label=('First' if index == 0 else 'Performance')+' / '+('C++' if language == 'cpp' else 'Rust'))
        ax.axvline(4, color='.7', ls=':')
        ax.set(xlabel='Workers (4 physical / 8 logical)', ylabel='Speedup relative to V5 / 1 worker', xticks=[1, 2, 4, 8], title=label+' / N = 1,000,000', ylim=(0, 5.5))
        ax.grid(alpha=.2)
    axes[1, 0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(args.figures/'laptop_profile_comparison.png', dpi=240, bbox_inches='tight')
    plt.close(fig)
    table_rows = []
    for group in ('baseline', 'workload', 'scaling'):
        a, b = [c['groups'][group] for c in summary['campaigns']]
        table_rows.append(f"{group} & {a['configurations']} & {a['median_cv_percent']:.2f} & {a['max_cv_percent']:.2f} & {b['median_cv_percent']:.2f} & {b['max_cv_percent']:.2f}")
    tables = table('Group & Count & First median & First max & Perf. median & Perf. max', table_rows,
        'Frame-time CV (percent) across matched configurations. Each CV uses three processes for baseline/workload or five for scaling. All observations are retained; the two sequential series are not pooled.', 'tab:profile_cv', 'lrrrrr')
    for n in (100000, 1000000):
        table_rows = []
        for language in ('cpp', 'rust'):
            for p in subset(summary['scaling'], series=1, n=n, language=language):
                table_rows.append(('C++' if language == 'cpp' else 'Rust') + f" & {p['threads']} & " +
                    ' & '.join(pm(p['times'][f]['mean'], p['times'][f]['sd']) for f in ('tree_ms', 'kernel_ms', 'total_ms')) + ' & ' +
                    ' & '.join(pm(p[f]['speedup'], p[f]['ci95_half']) for f in ('kernel_ms', 'total_ms')))
        tables += table('Language & $p$ & Tree (ms) & Kernel (ms) & Frame (ms) & $S_F$ & $S_T$', table_rows,
            f'Performance repetition: V5 at $N={n:,}$. Times are means $\\pm$ sample SD; speedups are means of five within-block ratios $\\pm$ 95\\% CI half-width. First-series results remain separate.',
            f'tab:performance_scaling{n}', 'lrrrrrr').replace(r'\centering\small', r'\centering\footnotesize\setlength{\tabcolsep}{3pt}')
    table_rows = []
    for distribution in ('plummer', 'uniform', 'clustered'):
        for seed in (1337, 42, 2026):
            points = subset(summary['workloads'], series=1, distribution=distribution, seed=seed)
            values = [p['ratios'][transition] for p in points for transition in ('V2/V3', 'V3/V4', 'V4/V5')]
            table_rows.append(f'{distribution} & {seed} & '+' & '.join(f'{v:.2f}' for v in values))
    tables += table('Input & Seed & C++ 2/3 & C++ 3/4 & C++ 4/5 & Rust 2/3 & Rust 3/4 & Rust 4/5', table_rows,
        'Performance workload ratios at $N=10^5$, based on three-process means. V5 uses eight workers; other variants are serial. Ratios are not significance tests.', 'tab:performance_workloads', 'lrrrrrrr')
    args.tables.write_text(tables, encoding='utf-8')
    print(json.dumps(dict(campaigns=[{k: c[k] for k in ('label', 'overall', 'groups')} for c in summary['campaigns']],
        changes=summary['matched_configuration_changes'], all_mean_orders_preserved=all(p['decreasing_mean_order'] for p in summary['workloads']),
        scaling_1m_8workers=subset(summary['scaling'], n=1000000, threads=8)), indent=2))


if __name__ == '__main__':
    main()
