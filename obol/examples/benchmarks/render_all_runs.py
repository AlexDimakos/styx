#!/usr/bin/env python3
"""Render every plot for every individual results* run, one output folder per run.

Each run's figures are built from that run's data alone (no averaging across
runs), unlike plots_tpcc.py/plots_tpcc_ablation.py, which average every
results* directory.
Runs are numbered by directory mtime (oldest first) and written to
figures_run<N>_<dirname>/ so nothing collides with the main figures/ folder.

    python render_all_runs.py [--slo-ms 1000]
"""

import argparse
import glob
import os

from plots_tpcc import make_figure as make_main_figure
from plots_tpcc import load_results as load_main_results
from plots_tpcc_ablation import load_results as load_ladder_results
from plots_tpcc_ablation import make_overview_figure, plotted_systems
from plots_tpcc_ablation_grid import make_grid_figure

HERE = os.path.dirname(__file__)


def find_runs() -> list[str]:
    dirs = [d for d in glob.glob(os.path.join(HERE, "results*")) if os.path.isdir(d)]
    return sorted(dirs, key=os.path.getmtime)


def render_run(index: int, run_dir: str, slo_ms: float, dpi: int) -> None:
    name = os.path.basename(run_dir)
    out_dir = os.path.join(HERE, f"figures_run{index}_{name}")
    os.makedirs(out_dir, exist_ok=True)
    print(f"\n=== run {index}: {name} -> {os.path.relpath(out_dir, HERE)} ===")

    main_data = load_main_results([run_dir])
    if main_data:
        make_main_figure(main_data, dpi, os.path.join(out_dir, "saturation_wh.png"))
    else:
        print("  (no tpcc_*_ALL.json results in this run)")

    ladder_data = load_ladder_results([run_dir], plotted_systems(True))
    if ladder_data:
        make_overview_figure(ladder_data, slo_ms, dpi,
                             os.path.join(out_dir, "optimization_ladder.png"),
                             os.path.join(out_dir, "optimization_ladder.csv"))
        make_grid_figure(ladder_data, dpi,
                         os.path.join(out_dir, "optimization_ladder_grid.png"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hi-res", action="store_true")
    ap.add_argument("--slo-ms", type=float, default=1000.0,
                    help="p50 SLO used for the sustained-throughput summary (default: 1000)")
    args = ap.parse_args()
    dpi = 300 if args.hi_res else 200

    runs = find_runs()
    if not runs:
        print("no results* directories found in", HERE)
        return

    for index, run_dir in enumerate(runs, start=1):
        render_run(index, run_dir, args.slo_ms, dpi)

    print(f"\n{len(runs)} run(s) rendered.")


if __name__ == "__main__":
    main()
