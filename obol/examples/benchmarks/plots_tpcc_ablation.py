#!/usr/bin/env python3
"""TPC-C ablation study figures.

Reads the result files produced by run_tpcc_all_systems.sh and renders:

  1. ablation_saturation.png — latency-vs-offered-throughput curves for every
     system (hand-written, full Obol, and one curve per ablated optimization),
     one panel per warehouse count, p50 solid / p99 dashed.
  2. ablation_summary.png — per system, the highest offered throughput it
     sustains while keeping p50 below the SLO (default 100 ms), one panel per
     warehouse count.

It also prints a per-system summary table (and writes it as CSV next to the
figures) so the numbers behind the bars are inspectable.

Result files are named  tpcc_<system>_W<warehouses>_<tput>_ALL.json  and are
looked up in every results* directory next to this script; points present in
several directories are averaged (same convention as plots_tpcc.py).
"""

import argparse
import csv
import glob
import json
import os
import re

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

sns.set_theme(
    context="paper",
    style="whitegrid",
    font_scale=1.05,
    rc={
        "figure.dpi": 120,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "axes.edgecolor": "0.25",
        "grid.linewidth": 0.6,
        "grid.linestyle": "--",
        "lines.linewidth": 1.9,
        "lines.markersize": 6,
    },
)

# System token -> display name + style. Colors are the first six slots of a
# CVD-validated categorical palette, assigned in fixed order (identity is
# stable across every figure in this directory); markers act as the secondary
# encoding so no series is identified by color alone.
SYS = {
    "handwritten":   dict(label="Hand-written Styx", short="hand-written",
                          color="#2a78d6", marker="o"),
    "obol_gather":   dict(label="Obol (full)", short="Obol full",
                          color="#008300", marker="s"),
    "obol_nogather": dict(label="Obol − gather", short="− gather",
                          color="#e87ba4", marker="^"),
    "obol_no_tco":   dict(label="Obol − tail-call", short="− tail-call",
                          color="#eda100", marker="D"),
    "obol_ctx_net":  dict(label="Obol − ctx-in-state (ctx over network)", short="− ctx-in-state",
                          color="#1baf7a", marker="v"),
    "obol_no_live":  dict(label="Obol − liveness (full ctx capture)", short="− liveness",
                          color="#eb6834", marker="P"),
}
DRAW_ORDER = ["handwritten", "obol_gather", "obol_nogather",
              "obol_no_tco", "obol_ctx_net", "obol_no_live"]

FNAME_RE = re.compile(r"^tpcc_(?P<sys>.+)_W(?P<wh>\d+)_(?P<tput>\d+)_ALL\.json$")


def result_dirs():
    return sorted(d for d in glob.glob(os.path.join(HERE, "results*")) if os.path.isdir(d))


def load_results(dirs):
    """{warehouses: {system: [(tput, p50, p99), ...]}} averaged across dirs."""
    samples = {}
    for d in dirs:
        for path in glob.glob(os.path.join(d, "tpcc_*_ALL.json")):
            m = FNAME_RE.match(os.path.basename(path))
            if not m or m.group("sys") not in SYS:
                continue
            try:
                with open(path) as f:
                    lat = json.load(f)["latency (ms)"]
                point = (float(lat["50"]), float(lat["99"]))
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                continue
            key = (int(m.group("wh")), m.group("sys"), int(m.group("tput")))
            samples.setdefault(key, []).append(point)

    data = {}
    for (wh, sysname, tput), runs in samples.items():
        p50 = sum(r[0] for r in runs) / len(runs)
        p99 = sum(r[1] for r in runs) / len(runs)
        data.setdefault(wh, {}).setdefault(sysname, []).append((tput, p50, p99))
    for wh in data:
        for sysname in data[wh]:
            data[wh][sysname].sort(key=lambda r: r[0])
    return data


def system_legend_handles(present):
    return [
        Line2D([0], [0], color=SYS[s]["color"], marker=SYS[s]["marker"],
               linestyle="-", label=SYS[s]["label"])
        for s in DRAW_ORDER if s in present
    ]


def style_legend_handles():
    return [
        Line2D([0], [0], color="0.3", linestyle="-", marker="o",
               markersize=4.5, label=r"$p_{50}$"),
        Line2D([0], [0], color="0.3", linestyle="--", marker="o",
               markerfacecolor="white", markersize=4.5, label=r"$p_{99}$"),
    ]


# ── Figure 1: saturation curves ────────────────────────────────────────


def make_saturation_figure(data, dpi, out_path):
    warehouses = sorted(data)
    fig, axes = plt.subplots(1, len(warehouses), figsize=(4.6 * len(warehouses), 3.4),
                             sharey=True, squeeze=False)
    axes = axes[0]

    letters = "abcdefghijklmnopqrstuvwxyz"
    for idx, (ax, wh) in enumerate(zip(axes, warehouses)):
        panel = data[wh]
        for sysname in DRAW_ORDER:
            rows = panel.get(sysname)
            if not rows:
                continue
            st = SYS[sysname]
            tput = [r[0] for r in rows]
            ax.plot(tput, [r[1] for r in rows], color=st["color"],
                    marker=st["marker"], linestyle="-")
            ax.plot(tput, [r[2] for r in rows], color=st["color"],
                    marker=st["marker"], linestyle="--",
                    markerfacecolor="white", markersize=4.5, linewidth=1.3)
        ax.set_yscale("log")
        ax.set_xlim(left=0)
        ax.set_xlabel("Input throughput (txn/s)", labelpad=8)
        ax.set_title(f"({letters[idx]}) {wh} warehouses")
        if not panel:
            ax.text(0.5, 0.5, "no data yet", transform=ax.transAxes,
                    ha="center", va="center", color="0.5", fontsize=10)
        sns.despine(ax=ax)
    axes[0].set_ylabel("Latency (ms)")

    present = {s for wh in warehouses for s in data[wh]}
    leg1 = fig.legend(handles=system_legend_handles(present), ncol=3, frameon=False,
                      fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.14),
                      columnspacing=1.4, handletextpad=0.5)
    fig.add_artist(leg1)
    fig.legend(handles=style_legend_handles(), ncol=2, frameon=False, fontsize=8,
               loc="upper center", bbox_to_anchor=(0.5, 1.005),
               columnspacing=1.4, handletextpad=0.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print("wrote", out_path)


# ── Figure 2: sustained-throughput summary ─────────────────────────────


def sustained_throughput(rows, slo_ms):
    """Highest offered tput whose p50 stays within the SLO (None if none does)."""
    ok = [tput for tput, p50, _p99 in rows if p50 <= slo_ms]
    return max(ok) if ok else None


def make_summary_figure(data, slo_ms, dpi, out_path, csv_path):
    warehouses = sorted(data)
    fig, axes = plt.subplots(1, len(warehouses), figsize=(4.6 * len(warehouses), 3.2),
                             sharey=True, squeeze=False)
    axes = axes[0]

    table_rows = []
    letters = "abcdefghijklmnopqrstuvwxyz"
    for idx, (ax, wh) in enumerate(zip(axes, warehouses)):
        panel = data[wh]
        systems = [s for s in DRAW_ORDER if s in panel]
        values = []
        for s in systems:
            sustained = sustained_throughput(panel[s], slo_ms)
            values.append(sustained or 0)
            best_p50 = min(p50 for _t, p50, _p in panel[s])
            table_rows.append({
                "warehouses": wh,
                "system": s,
                "sustained_tput_txn_s": sustained if sustained is not None else "n/a",
                "min_p50_ms": round(best_p50, 2),
                "slo_ms": slo_ms,
            })

        xs = range(len(systems))
        bars = ax.bar(xs, values,
                      color=[SYS[s]["color"] for s in systems],
                      width=0.62, edgecolor="white", linewidth=1)
        for bar, value in zip(bars, values):
            if value:
                ax.annotate(f"{value:,}", (bar.get_x() + bar.get_width() / 2, value),
                            textcoords="offset points", xytext=(0, 3),
                            ha="center", fontsize=7.5, color="0.2")
        ax.set_xticks(list(xs))
        ax.set_xticklabels([SYS[s]["short"] for s in systems],
                           fontsize=7.5, rotation=30, ha="right")
        ax.set_title(f"({letters[idx]}) {wh} warehouses")
        ax.set_xlabel("")
        if not systems:
            ax.text(0.5, 0.5, "no data yet", transform=ax.transAxes,
                    ha="center", va="center", color="0.5", fontsize=10)
        sns.despine(ax=ax)
    axes[0].set_ylabel(f"Sustained throughput (txn/s, p50 ≤ {slo_ms:g} ms)")

    present = {s for wh in warehouses for s in data[wh]}
    fig.legend(handles=system_legend_handles(present), ncol=3, frameon=False,
               fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.12),
               columnspacing=1.4, handletextpad=0.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    print("wrote", out_path)

    if table_rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(table_rows[0]))
            writer.writeheader()
            writer.writerows(table_rows)
        print("wrote", csv_path)
        header = f"{'wh':>4} {'system':<15} {'sustained':>10} {'min p50 (ms)':>13}"
        print("\n" + header)
        print("-" * len(header))
        for row in table_rows:
            print(f"{row['warehouses']:>4} {row['system']:<15} "
                  f"{row['sustained_tput_txn_s']!s:>10} {row['min_p50_ms']:>13}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hi-res", action="store_true")
    ap.add_argument("--slo-ms", type=float, default=100.0,
                    help="p50 SLO used for the sustained-throughput summary (default: 100)")
    args = ap.parse_args()
    dpi = 300 if args.hi_res else 200

    dirs = result_dirs()
    if not dirs:
        print("no results* directories found in", HERE)
        return
    data = load_results(dirs)
    if not data:
        print("no TPC-C ablation results found across",
              ", ".join(os.path.basename(d) for d in dirs))
        return

    make_saturation_figure(data, dpi, os.path.join(OUT, "ablation_saturation.png"))
    make_summary_figure(data, args.slo_ms, dpi,
                        os.path.join(OUT, "ablation_summary.png"),
                        os.path.join(OUT, "ablation_summary.csv"))


if __name__ == "__main__":
    main()
