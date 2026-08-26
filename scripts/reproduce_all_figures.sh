#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

output_root="${1:-results/manuscript/$(date -u +%Y%m%dT%H%M%SZ)}"
if [ -e "$output_root" ]; then
    echo "Output directory already exists: $output_root" >&2
    exit 1
fi
mkdir -p "$output_root"

SKIP_BUILD="${SKIP_BUILD:-0}" bash scripts/reproduce_fig1.sh "$output_root/fig1"
SKIP_BUILD=1 bash scripts/reproduce_fig2.sh "$output_root/fig2"
SKIP_BUILD=1 bash scripts/reproduce_fig3.sh "$output_root/fig3"

if [ -n "${PYTHON:-}" ]; then python_cmd="$PYTHON"; elif command -v python3 >/dev/null 2>&1; then python_cmd=python3; else python_cmd=python; fi
"$python_cmd" scripts/plot_manuscript_figures.py "$output_root" "$output_root/figures"
echo "Manuscript data and figures written to $output_root"
