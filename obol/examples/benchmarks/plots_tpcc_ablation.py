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
  row 3  saturation point: one grouped bar chart spanning the figure, one
         group per warehouse count, one bar per configuration. The saturation
         point is the last offered rate before p50 rises above the knee
         (default 1000 ms) and stays there at the next rate, so a single
         transient stall does not count. Curves that never cross are drawn
         hatched as a lower bound.

The rungs are naive -> + context-in-state -> + tail-call -> + liveness.
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
    "obol_opt_ctx": dict(label="+ context-in-state", short="+ ctx-in-state",
                         color="#eda100", marker="D"),
    "obol_opt_tco": dict(label="+ tail-call opt.", short="+ tail-call",
                         color="#1baf7a", marker="v"),
    "obol_gather":  dict(label="+ liveness (full Obol)", short="+ liveness\n(full)",
                         color="#008300", marker="s"),
}

# The ladder itself, in the order optimizations are switched on. Context-in-
# state comes before the tail-call optimization: every continuation site in
# TPC-C is a tail call, so enabling tail-call first would leave context-in-
# state with nothing to transport and the two rungs would be identical.
LADDER = ["obol_naive", "obol_opt_ctx", "obol_opt_tco", "obol_gather"]
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


# -- Row 3: saturation points ------------------------------------------


def sustained_throughput(rows, slo_ms):
    """Highest offered tput whose p50 stays within the SLO (None if none does)."""
    ok = [r.tput for r in rows if r.p50 <= slo_ms]
    return max(ok) if ok else None


def saturation_point(rows, knee_ms):
    """Offered rate at which a system saturates, as ``(rate, reached)``.

    The saturation point is the last offered rate before p50 rises above
    ``knee_ms`` and stays above it at the next measured rate as well. Requiring
    two in a row keeps a transient stall -- p50 spikes at one rate and recovers
    at the next -- from being read as saturation. A crossing at the last
    measured rate counts, since there is no later point to recover at.

    If p50 never crosses, the system has not saturated within the measured
    range; the highest measured rate is returned with ``reached=False`` so it
    can be drawn as a lower bound.
    """
    for i, r in enumerate(rows):
        if r.p50 <= knee_ms:
            continue
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        if nxt is None or nxt.p50 > knee_ms:
            return (rows[i - 1].tput if i > 0 else 0), True
    return rows[-1].tput, False


def draw_saturation_bars(ax, data, warehouses, order, knee_ms):
    """One group per warehouse count, one bar per system, height = saturation point."""
    systems = [s for s in order if any(s in data[wh] for wh in warehouses)]
    if not systems:
        ax.text(0.5, 0.5, "no data yet", transform=ax.transAxes,
                ha="center", va="center", color="0.5", fontsize=10)
        sns.despine(ax=ax)
        return {}

    width = 0.8 / len(systems)
    points = {}
    for group, wh in enumerate(warehouses):
        for idx, sysname in enumerate(systems):
            rows = data[wh].get(sysname)
            if not rows:
                continue
            rate, reached = saturation_point(rows, knee_ms)
            points[(wh, sysname)] = (rate, reached)
            color = SYS[sysname]["color"]
            alpha = REF_ALPHA if sysname == REFERENCE else 1.0
            x = group + (idx - (len(systems) - 1) / 2) * width
            if reached:
                ax.bar(x, rate, width=width * 0.9, color=to_rgba(color, alpha),
                       edgecolor="white", linewidth=1)
            else:
                # Not saturated yet: hatched outline, labelled as a lower bound.
                ax.bar(x, rate, width=width * 0.9, facecolor=to_rgba(color, 0.15),
                       edgecolor=color, hatch="///", linewidth=1)
            if rate:
                ax.annotate(f"{rate:,}" if reached else f"≥{rate:,}", (x, rate),
                            textcoords="offset points", xytext=(0, 3),
                            ha="center", fontsize=7, color="0.2")

    ax.set_xticks(list(range(len(warehouses))))
    ax.set_xticklabels([f"{wh} warehouses" for wh in warehouses], fontsize=9)
    ax.set_xlim(-0.5, len(warehouses) - 0.5)
    ax.set_ylabel(f"Saturation point\n(offered txn/s, p50 > {knee_ms:g} ms)")
    if not all(reached for _rate, reached in points.values()):
        ax.legend(handles=[Patch(facecolor="white", edgecolor="0.4", hatch="///",
                                 label="not saturated yet (lower bound)")],
                  loc="upper left", frameon=False, fontsize=7.5)
    sns.despine(ax=ax)
    return points


# -- The overview figure -----------------------------------------------


def make_overview_figure(data, slo_ms, dpi, out_path, csv_path,
                         with_reference=True, requested_tput=None, knee_ms=1000.0):
    warehouses = sorted(data)
    order = plotted_systems(with_reference)
    n = len(warehouses)

    fig = plt.figure(figsize=(4.6 * n, 9.3))
    grid = fig.add_gridspec(3, n, height_ratios=[1.15, 1.0, 1.0])
    curve_axes, box_axes = [], []
    for col in range(n):
        curve_axes.append(fig.add_subplot(grid[0, col], sharey=curve_axes[0] if col else None))
        box_axes.append(fig.add_subplot(grid[1, col], sharey=box_axes[0] if col else None))
        if col:
            curve_axes[col].tick_params(labelleft=False)
            box_axes[col].tick_params(labelleft=False)
    bar_ax = fig.add_subplot(grid[2, :])

    letters = "abcdefghijklmnopqrstuvwxyz"
    boxes_by_wh = {}
    for col, wh in enumerate(warehouses):
        panel = data[wh]
        draw_saturation(curve_axes[col], panel, order)
        curve_axes[col].set_title(f"({letters[col]}) {wh} warehouses", pad=8)
        boxes_by_wh[wh] = draw_boxes(box_axes[col], panel, order, slo_ms, requested_tput)

    saturation = draw_saturation_bars(bar_ax, data, warehouses, order, knee_ms)
    bar_ax.set_title(f"({letters[n]}) saturation point", pad=8)

    table_rows = []
    for wh in warehouses:
        panel = data[wh]
        box_tput, box_rows = boxes_by_wh[wh]
        boxes = dict(box_rows)
        for sysname in order:
            if sysname not in panel:
                continue
            stats = boxes.get(sysname)
            rate, reached = saturation[(wh, sysname)]
            table_rows.append({
                "warehouses": wh,
                "system": sysname,
                "saturation_point_txn_s": rate,
                "saturated": reached,
                "knee_ms": knee_ms,
                "sustained_tput_txn_s": sustained_throughput(panel[sysname], slo_ms) or "n/a",
                "slo_ms": slo_ms,
                "box_tput_txn_s": box_tput if stats else "n/a",
                "p10_ms": round(stats["whislo"], 2) if stats else "n/a",
                "p25_ms": round(stats["q1"], 2) if stats else "n/a",
                "p50_ms": round(stats["med"], 2) if stats else "n/a",
                "p75_ms": round(stats["q3"], 2) if stats else "n/a",
                "p99_ms": round(stats["whishi"], 2) if stats else "n/a",
                "min_p50_ms": round(min(r.p50 for r in panel[sysname]), 2),
            })

    curve_axes[0].set_ylabel("Latency (ms)")
    box_axes[0].set_ylabel("Latency distribution (ms)")

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
        header = (f"{'wh':>4} {'system':<14} {'saturation':>11} "
                  f"{'p50@box':>9} {'p99@box':>9}")
        print("\n" + header)
        print("-" * len(header))
        for row in table_rows:
            sat = f"{row['saturation_point_txn_s']}" + ("" if row["saturated"] else "+")
            print(f"{row['warehouses']:>4} {row['system']:<14} {sat:>11} "
                  f"{row['p50_ms']!s:>9} {row['p99_ms']!s:>9}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hi-res", action="store_true")
    ap.add_argument("--slo-ms", type=float, default=100.0,
                    help="p50 SLO that picks the box-plot operating point (default: 100)")
    ap.add_argument("--knee-ms", type=float, default=1000.0,
                    help="p50 above which a system counts as saturated (default: 1000)")
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
                         requested_tput=args.box_tput,
                         knee_ms=args.knee_ms)


if __name__ == "__main__":
    main()
