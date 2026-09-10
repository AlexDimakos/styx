#!/usr/bin/env python3
"""TPC-C optimization ladder, small-multiples layout.

`plots_tpcc_ablation.py`'s saturation row stacks every ladder rung x 2
percentiles into one axes, which gets hard to read once curves cross near the
saturation knee. This renders the same data as a grid instead: one small panel
per (warehouse count, ladder rung), each showing that rung's own p50/p99 in
full color against the two things you actually care about comparing it to --
hand-written Styx and full Obol -- drawn thin and muted as reference lines.
Position in the grid carries identity instead of one more color, so nothing
needs to be visually disentangled from the other rungs at once.

Does not modify plots_tpcc_ablation.py or its output files.
"""

import argparse
import os

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D

from plots_tpcc_ablation import LADDER, OUT, SYS, load_results, result_dirs

REFERENCE_SYSTEMS = ("handwritten", "obol_gather")
# Every rung gets its own panel, including the full system (whose panel then
# shows it against the hand-written ceiling alone).
VARIANT_ORDER = list(LADDER)

REF_ALPHA = 0.55
REF_LINEWIDTH = 1.1


def draw_panel(ax, panel, variant):
    drawn_any = False

    for ref in REFERENCE_SYSTEMS:
        rows = panel.get(ref)
        if not rows:
            continue
        st = SYS[ref]
        ax.plot([r[0] for r in rows], [r[1] for r in rows], color=st["color"],
                linestyle="-", linewidth=REF_LINEWIDTH, alpha=REF_ALPHA, zorder=1)
        drawn_any = True

    rows = panel.get(variant)
    if rows:
        st = SYS[variant]
        tput = [r[0] for r in rows]
        ax.plot(tput, [r[1] for r in rows], color=st["color"], marker=st["marker"],
                linestyle="-", zorder=3)
        ax.plot(tput, [r[2] for r in rows], color=st["color"], marker=st["marker"],
                linestyle="--", markerfacecolor="white", markersize=4.5,
                linewidth=1.3, zorder=2)
        drawn_any = True

    ax.set_yscale("log")
    ax.set_xlim(left=0)
    if not drawn_any:
        ax.text(0.5, 0.5, "no data yet", transform=ax.transAxes,
                ha="center", va="center", color="0.5", fontsize=9)
    sns.despine(ax=ax)


def make_grid_figure(data, dpi, out_path):
    warehouses = sorted(data)
    variants = [v for v in VARIANT_ORDER if any(v in data[wh] for wh in warehouses)]
    if not variants:
        print("no ablation variants found (only baseline/full present)")
        return

    n_rows, n_cols = len(warehouses), len(variants)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(2.9 * n_cols, 2.7 * n_rows),
                             sharey="row", squeeze=False)

    for row, wh in enumerate(warehouses):
        panel_data = data[wh]
        for col, variant in enumerate(variants):
            ax = axes[row][col]
            draw_panel(ax, panel_data, variant)
            if row == 0:
                ax.set_title(SYS[variant]["label"], fontsize=10)
            if row == n_rows - 1:
                ax.set_xlabel("Input throughput (txn/s)", fontsize=8.5, labelpad=6)
            if col == 0:
                ax.set_ylabel(f"{wh} warehouses\nLatency (ms)", fontsize=8.5)
            ax.tick_params(labelsize=7.5)

    legend_handles = [
        Line2D([0], [0], color=SYS["handwritten"]["color"], linewidth=REF_LINEWIDTH,
               alpha=REF_ALPHA, label="hand-written Styx (ref., p50)"),
        Line2D([0], [0], color=SYS["obol_gather"]["color"], linewidth=REF_LINEWIDTH,
               alpha=REF_ALPHA, label="Obol full (ref., p50)"),
        Line2D([0], [0], color="0.25", linestyle="-", marker="o", markersize=4.5,
               label="column's variant, p50"),
        Line2D([0], [0], color="0.25", linestyle="--", marker="o", markerfacecolor="white",
               markersize=4.5, label="column's variant, p99"),
    ]
    fig.legend(handles=legend_handles, ncol=4, frameon=False, fontsize=8,
               loc="upper center", bbox_to_anchor=(0.5, 1.06 if n_rows > 1 else 1.14),
               columnspacing=1.3, handletextpad=0.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print("wrote", out_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hi-res", action="store_true")
    args = ap.parse_args()
    dpi = 300 if args.hi_res else 200

    dirs = result_dirs()
    if not dirs:
        print("no results* directories found")
        return
    data = load_results(dirs, list(REFERENCE_SYSTEMS) + VARIANT_ORDER)
    if not data:
        print("no TPC-C ladder results found across",
              ", ".join(os.path.basename(d) for d in dirs))
        return

    make_grid_figure(data, dpi, os.path.join(OUT, "optimization_ladder_grid.png"))


if __name__ == "__main__":
    main()
