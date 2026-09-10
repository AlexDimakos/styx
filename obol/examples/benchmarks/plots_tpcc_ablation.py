#!/usr/bin/env python3
"""TPC-C cumulative optimization-ladder figures.

Reads the result files produced by run_tpcc_all_systems.sh for the four Obol
ladder configurations -- naive (gather only), then one optimization added per
rung -- and renders one overview figure with three stacked views, one column
per warehouse count:

  row 1  saturation curves: latency vs offered throughput, p50 solid /
         p99 dashed (same style as plots_tpcc.py)
  row 2  latency distribution: one box per configuration at a single offered
         rate (by default the heaviest load the full system holds within the
         SLO), reconstructed from the stored percentiles
  row 3  sustained throughput: highest offered rate each configuration holds
         while keeping p50 within the SLO (default 100 ms)

Because consecutive rungs differ by exactly one optimization, the step between
two neighbouring series/boxes/bars is that optimization's contribution.

Hand-written Styx is drawn in every row as a muted reference (the performance
ceiling); pass --no-reference to plot the four Obol rungs alone.

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
from typing import NamedTuple

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

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

# System token -> display name + style. The ladder runs warm -> cool and ends
# on the green that identifies the full Obol system in every other figure;
# markers are the secondary encoding so nothing is identified by color alone.
SYS = {
    "handwritten":  dict(label="Hand-written Styx (reference)", short="hand-written",
                         color="#2a78d6", marker="o"),
    "obol_naive":   dict(label="Obol naive (gather only)", short="naive",
                         color="#eb6834", marker="P"),
    "obol_opt_tco": dict(label="+ tail-call opt.", short="+ tail-call",
                         color="#eda100", marker="D"),
    "obol_opt_ctx": dict(label="+ context-in-state", short="+ ctx-in-state",
                         color="#1baf7a", marker="v"),
    "obol_gather":  dict(label="+ liveness (full Obol)", short="+ liveness\n(full)",
                         color="#008300", marker="s"),
}

# The ladder itself, in the order optimizations are switched on.
LADDER = ["obol_naive", "obol_opt_tco", "obol_opt_ctx", "obol_gather"]
REFERENCE = "handwritten"

REF_ALPHA = 0.55
REF_LINEWIDTH = 1.2

# Percentiles kept from each result file, used for the box plots.
PERCENTILES = (10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99)

FNAME_RE = re.compile(r"^tpcc_(?P<sys>.+)_W(?P<wh>\d+)_(?P<tput>\d+)_ALL\.json$")


class Point(NamedTuple):
    """One (system, warehouses, offered-rate) measurement.

    The first three fields keep the historical ``(tput, p50, p99)`` tuple
    layout, so positional unpacking in the other plot scripts still works.
    """

    tput: int
    p50: float
    p99: float
    pcts: dict
    mean: float


def result_dirs():
    return sorted(d for d in glob.glob(os.path.join(HERE, "results*")) if os.path.isdir(d))


def load_results(dirs, systems=None):
    """{warehouses: {system: [Point, ...]}} averaged across ``dirs``."""
    wanted = set(systems) if systems is not None else set(SYS)
    samples = {}
    for d in dirs:
        for path in glob.glob(os.path.join(d, "tpcc_*_ALL.json")):
            m = FNAME_RE.match(os.path.basename(path))
            if not m or m.group("sys") not in wanted:
                continue
            try:
                with open(path) as f:
                    lat = json.load(f)["latency (ms)"]
                sample = {p: float(lat[str(p)]) for p in PERCENTILES}
                sample["mean"] = float(lat["mean"])
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                continue
            key = (int(m.group("wh")), m.group("sys"), int(m.group("tput")))
            samples.setdefault(key, []).append(sample)

    data = {}
    for (wh, sysname, tput), runs in samples.items():
        avg = {k: sum(r[k] for r in runs) / len(runs) for k in runs[0]}
        point = Point(tput, avg[50], avg[99],
                      {p: avg[p] for p in PERCENTILES}, avg["mean"])
        data.setdefault(wh, {}).setdefault(sysname, []).append(point)
    for wh in data:
        for sysname in data[wh]:
            data[wh][sysname].sort(key=lambda r: r.tput)
    return data


def plotted_systems(with_reference):
    return ([REFERENCE] if with_reference else []) + LADDER


# -- Legends -----------------------------------------------------------


def system_legend_handles(present, order):
    """One handle per system, each drawn the way that system is drawn."""
    handles = []
    for s in order:
        if s not in present:
            continue
        st = SYS[s]
        if s == REFERENCE:
            handles.append(Line2D([0], [0], color=st["color"], linestyle="-",
                                  linewidth=REF_LINEWIDTH, alpha=REF_ALPHA,
                                  label=st["label"]))
        else:
            handles.append(Line2D([0], [0], color=st["color"], marker=st["marker"],
                                  linestyle="-", label=st["label"]))
    return handles


def style_legend_handles():
    return [
        Line2D([0], [0], color="0.3", linestyle="-", marker="o",
               markersize=4.5, label=r"$p_{50}$"),
        Line2D([0], [0], color="0.3", linestyle="--", marker="o",
               markerfacecolor="white", markersize=4.5, label=r"$p_{99}$"),
        Patch(facecolor="0.85", edgecolor="0.3",
              label=r"box $p_{25}$-$p_{75}$, whiskers $p_{10}$/$p_{99}$"),
    ]


# -- Row 1: saturation curves ------------------------------------------


def draw_saturation(ax, panel, order):
    for sysname in order:
        rows = panel.get(sysname)
        if not rows:
            continue
        st = SYS[sysname]
        is_ref = sysname == REFERENCE
        tput = [r.tput for r in rows]
        ax.plot(tput, [r.p50 for r in rows], color=st["color"],
                marker=None if is_ref else st["marker"], linestyle="-",
                linewidth=REF_LINEWIDTH if is_ref else 1.9,
                alpha=REF_ALPHA if is_ref else 1.0, zorder=1 if is_ref else 3)
        if not is_ref:
            ax.plot(tput, [r.p99 for r in rows], color=st["color"],
                    marker=st["marker"], linestyle="--", markerfacecolor="white",
                    markersize=4.5, linewidth=1.3, zorder=2)
    ax.set_yscale("log")
    ax.set_xlim(left=0)
    ax.set_xlabel("Input throughput (txn/s)", labelpad=6)
    if not panel:
        ax.text(0.5, 0.5, "no data yet", transform=ax.transAxes,
                ha="center", va="center", color="0.5", fontsize=10)
    sns.despine(ax=ax)


# -- Row 2: latency distribution box plots -----------------------------


def box_tput_for(panel, order, slo_ms, requested=None):
    """Offered rate to draw boxes at, snapped to a rate every config measured.

    Defaults to the heaviest load the *full* system still serves within the
    SLO -- the operating point it is built for. Anchoring there keeps the
    comparison informative: at the top of the sweep every configuration is
    deep in saturation and the boxes only show how badly each one queues.
    """
    present = [s for s in order if panel.get(s)]
    if not present:
        return None
    common = set.intersection(*({r.tput for r in panel[s]} for s in present))
    if not common:
        return None
    anchor = requested
    if anchor is None:
        anchor = sustained_throughput(panel.get(LADDER[-1], []), slo_ms)
    if anchor is None:
        return max(common)
    return min(common, key=lambda t: abs(t - anchor))


def box_stats(point, label):
    """matplotlib bxp stats from the stored percentiles.

    p25/p75 are not recorded, so the box edges interpolate the neighbouring
    deciles; the median and the whiskers are measured values.
    """
    p = point.pcts
    return {
        "label": label,
        "med": p[50],
        "q1": (p[20] + p[30]) / 2,
        "q3": (p[70] + p[80]) / 2,
        "whislo": p[10],
        "whishi": p[99],
        "mean": point.mean,
        "fliers": [],
    }


def draw_boxes(ax, panel, order, slo_ms, requested_tput):
    tput = box_tput_for(panel, order, slo_ms, requested_tput)
    if tput is None:
        ax.text(0.5, 0.5, "no data yet", transform=ax.transAxes,
                ha="center", va="center", color="0.5", fontsize=10)
        sns.despine(ax=ax)
        return None, []

    systems, stats = [], []
    for sysname in order:
        point = next((r for r in panel.get(sysname, []) if r.tput == tput), None)
        if point is None:
            continue
        systems.append(sysname)
        stats.append(box_stats(point, SYS[sysname]["short"]))

    artists = ax.bxp(stats, positions=list(range(len(stats))), widths=0.55,
                     showfliers=False, showmeans=False, patch_artist=True)
    for sysname, box, median in zip(systems, artists["boxes"], artists["medians"]):
        st = SYS[sysname]
        is_ref = sysname == REFERENCE
        box.set(facecolor=st["color"], alpha=0.35 if is_ref else 0.55,
                edgecolor=st["color"], linewidth=1.2)
        median.set(color="0.15", linewidth=1.6)
    for part in ("whiskers", "caps"):
        for artist in artists[part]:
            artist.set(color="0.35", linewidth=1.1)

    ax.set_yscale("log")
    ax.set_xticks(list(range(len(systems))))
    ax.set_xticklabels([SYS[s]["short"] for s in systems], fontsize=7.5,
                       rotation=20, ha="right")
    ax.set_xlabel(f"offered load: {tput:,} txn/s", labelpad=6, fontsize=8.5)
    sns.despine(ax=ax)
    return tput, list(zip(systems, stats))


# -- Row 3: sustained-throughput bars ----------------------------------


def sustained_throughput(rows, slo_ms):
    """Highest offered tput whose p50 stays within the SLO (None if none does)."""
    ok = [r.tput for r in rows if r.p50 <= slo_ms]
    return max(ok) if ok else None


def draw_bars(ax, panel, order, slo_ms):
    systems = [s for s in order if s in panel]
    if not systems:
        ax.text(0.5, 0.5, "no data yet", transform=ax.transAxes,
                ha="center", va="center", color="0.5", fontsize=10)
        sns.despine(ax=ax)
        return []

    values = [sustained_throughput(panel[s], slo_ms) or 0 for s in systems]
    # bar() takes a single alpha, so fade the reference through its RGBA color.
    colors = [to_rgba(SYS[s]["color"], REF_ALPHA if s == REFERENCE else 1.0)
              for s in systems]
    bars = ax.bar(list(range(len(systems))), values, color=colors,
                  width=0.62, edgecolor="white", linewidth=1)
    for bar, value in zip(bars, values):
        if value:
            ax.annotate(f"{value:,}", (bar.get_x() + bar.get_width() / 2, value),
                        textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=7.5, color="0.2")
    ax.set_xticks(list(range(len(systems))))
    ax.set_xticklabels([SYS[s]["short"] for s in systems], fontsize=7.5,
                       rotation=20, ha="right")
    ax.set_xlabel("")
    sns.despine(ax=ax)
    return list(zip(systems, values))


# -- The overview figure -----------------------------------------------


def make_overview_figure(data, slo_ms, dpi, out_path, csv_path,
                         with_reference=True, requested_tput=None):
    warehouses = sorted(data)
    order = plotted_systems(with_reference)
    n = len(warehouses)

    fig, axes = plt.subplots(3, n, figsize=(4.6 * n, 9.3), squeeze=False,
                             sharey="row",
                             gridspec_kw={"height_ratios": [1.15, 1.0, 1.0]})

    letters = "abcdefghijklmnopqrstuvwxyz"
    table_rows = []
    for col, wh in enumerate(warehouses):
        panel = data[wh]
        draw_saturation(axes[0][col], panel, order)
        axes[0][col].set_title(f"({letters[col]}) {wh} warehouses", pad=8)

        box_tput, box_rows = draw_boxes(axes[1][col], panel, order, slo_ms,
                                        requested_tput)
        bar_rows = draw_bars(axes[2][col], panel, order, slo_ms)

        sustained = dict(bar_rows)
        boxes = dict(box_rows)
        for sysname in order:
            if sysname not in panel:
                continue
            stats = boxes.get(sysname)
            table_rows.append({
                "warehouses": wh,
                "system": sysname,
                "sustained_tput_txn_s": sustained.get(sysname) or "n/a",
                "slo_ms": slo_ms,
                "box_tput_txn_s": box_tput if stats else "n/a",
                "p10_ms": round(stats["whislo"], 2) if stats else "n/a",
                "p25_ms": round(stats["q1"], 2) if stats else "n/a",
                "p50_ms": round(stats["med"], 2) if stats else "n/a",
                "p75_ms": round(stats["q3"], 2) if stats else "n/a",
                "p99_ms": round(stats["whishi"], 2) if stats else "n/a",
                "min_p50_ms": round(min(r.p50 for r in panel[sysname]), 2),
            })

    axes[0][0].set_ylabel("Latency (ms)")
    axes[1][0].set_ylabel("Latency distribution (ms)")
    axes[2][0].set_ylabel(f"Sustained throughput\n(txn/s, p50 <= {slo_ms:g} ms)")

    present = {s for wh in warehouses for s in data[wh]}
    leg1 = fig.legend(handles=system_legend_handles(present, order), ncol=3,
                      frameon=False, fontsize=8, loc="upper center",
                      bbox_to_anchor=(0.5, 1.06), columnspacing=1.4,
                      handletextpad=0.5)
    fig.add_artist(leg1)
    fig.legend(handles=style_legend_handles(), ncol=3, frameon=False, fontsize=8,
               loc="upper center", bbox_to_anchor=(0.5, 1.018),
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
        header = (f"{'wh':>4} {'system':<14} {'sustained':>10} "
                  f"{'p50@box':>9} {'p99@box':>9}")
        print("\n" + header)
        print("-" * len(header))
        for row in table_rows:
            print(f"{row['warehouses']:>4} {row['system']:<14} "
                  f"{row['sustained_tput_txn_s']!s:>10} "
                  f"{row['p50_ms']!s:>9} {row['p99_ms']!s:>9}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hi-res", action="store_true")
    ap.add_argument("--slo-ms", type=float, default=100.0,
                    help="p50 SLO used for the sustained-throughput bars (default: 100)")
    ap.add_argument("--box-tput", type=int, default=None,
                    help="offered rate for the box plots; snapped to the nearest "
                         "rate all configurations share (default: the full system's "
                         "sustained rate under --slo-ms)")
    ap.add_argument("--no-reference", action="store_true",
                    help="omit the hand-written Styx reference series")
    args = ap.parse_args()
    dpi = 300 if args.hi_res else 200

    dirs = result_dirs()
    if not dirs:
        print("no results* directories found in", HERE)
        return
    data = load_results(dirs, plotted_systems(not args.no_reference))
    if not data:
        print("no TPC-C ladder results found across",
              ", ".join(os.path.basename(d) for d in dirs))
        return

    make_overview_figure(data, args.slo_ms, dpi,
                         os.path.join(OUT, "optimization_ladder.png"),
                         os.path.join(OUT, "optimization_ladder.csv"),
                         with_reference=not args.no_reference,
                         requested_tput=args.box_tput)


if __name__ == "__main__":
    main()
