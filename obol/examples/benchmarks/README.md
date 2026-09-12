# Obol benchmarks: YCSB, TPC-C, and the optimization ladder

This directory contains everything needed to (re)run the Obol vs hand-written
Styx experiments and to render the figures: the annotated benchmark sources,
the compiled outputs for every system variant, the sweep orchestrators, and
the plotting scripts.

## Layout

| Path | What it is |
|---|---|
| `original/` | Annotated OOP sources fed to the Obol compiler |
| `compiled/` | Reference compiler outputs, one file per system variant |
| `compile_variants.py` | Regenerates every compiled variant (see below) |
| `run_tpcc_all_systems.sh` | TPC-C sweep over all systems + ladder rungs |
| `run_ycsb_all_systems.sh` | YCSB sweep over hand-written and Obol |
| `plots_tpcc.py` / `plots_ycsb.py` | Main comparison figures |
| `plots_tpcc_ablation.py` | Optimization-ladder overview figure (curves + boxes + bars) + summary table |
| `plots_tpcc_ablation_grid.py` | Same ladder data as small multiples, one panel per rung |
| `results*/` | Result JSONs, one directory per run (not committed) |
| `figures/` | Rendered PNGs |

## Systems and the optimization ladder

The TPC-C sweep runs six systems. Four of them form a **cumulative ladder**:
a naive baseline with every optimization off, then one optimization switched
on per rung, up to the full system. Consecutive rungs differ by exactly one
optimization, so the step from one rung to the next is that optimization's
contribution. Every rung keeps the `gather` fan-out on.

| System token | Compiled variant | Ctx-in-state | Tail-call | Liveness |
|---|---|:--:|:--:|:--:|
| `obol_naive` | `naive` | — | — | — |
| `obol_opt_ctx` | `opt_ctx` | on | — | — |
| `obol_opt_tco` | `opt_tco` | on | on | — |
| `obol_gather` | `gather` | on | on | on |

**Why context-in-state comes first.** Every continuation site in TPC-C is a
tail call, so enabling the tail-call optimization removes all four of them. If
tail-call came first, context-in-state would have nothing left to transport and
the two variants would compile to byte-identical programs — the rung would
measure nothing. In this order each rung changes something real: `opt_ctx`
keeps the four continuation sites but ships a context id instead of the whole
dict, and `opt_tco` then deletes the sites outright.

Two systems sit outside the ladder:

| System token | Compiled variant | What it is |
|---|---|---|
| `handwritten` | — | Baseline: hand-written Styx operators (the performance ceiling) |
| `obol_nogather` | `no_gather` | Full Obol compiled from a source written without `gather`, so every cross-entity call is dispatched sequentially |

The three optimizations, in the order the ladder adds them:

- **Context-in-state** — save the live continuation context in the operator's
  function-context store and put only a small integer id in `reply_to`. Off,
  the whole context dict travels the network on every hop, forward and back.
- **Distributed tail-call optimization** — when a step ends in
  `return other.method(...)`, forward the caller's reply-to address instead of
  routing the reply back through the intermediate entity. Off, the compiler
  emits a `*_step_2` trampoline per delegated return whose only job is to
  forward the reply. TPC-C has four such sites: `Item.get_item` (hit once per
  order line, so 5–15 times per New-Order), `CustomerIndex.pay`, and both
  branches of `PaymentTxn.get_customer_data`.
- **Live-variable analysis** — serialize only the variables still live past
  the split. Off, every variable defined so far is captured at each split.
  With tail-call on, what this actually shrinks is the `gather` barrier's
  saved-variable dict: the item fan-out in `District.get_district` drops from
  9 saved variables (including three 5–15 element lists) to none.

Ladder rungs are produced by compiler flags (see `obol --help`:
`--no-tail-call`, `--context-over-network`, `--no-liveness`), wired through
the `OBOL_DISABLE_TAIL_CALL`, `OBOL_CONTEXT_OVER_NETWORK`, and
`OBOL_DISABLE_LIVENESS` environment variables. `no_gather` is a source-level
variant (`original/tpcc_no_gather.py`). Everything is client-side: every
variant ships a different compiled dataflow graph to the *same* cluster
image, so no rebuild is needed between systems.

Regenerate all compiled outputs (also refreshes the copies under
`demo/demo-tpc-c/functions/` and `demo/demo-ycsb/ycsb_compiled.py`):

```bash
cd obol && python examples/benchmarks/compile_variants.py
```

## Running the sweeps

Both orchestrators live here but can be invoked from anywhere; they cd to the
repo root themselves. Positional API (all optional):
`SAVING_DIR PARTITIONS EXP_TIME WARMUP STYX_THREADS_PER_WORKER [SYSTEM ...]`.

```bash
# full TPC-C sweep, all six systems (cluster example):
nohup bash obol/examples/benchmarks/run_tpcc_all_systems.sh results 80 60 30 10 > tpcc_logs.log 2>&1 &

# only the ladder rungs you still need:
bash obol/examples/benchmarks/run_tpcc_all_systems.sh results 80 60 30 10 obol_naive obol_opt_ctx obol_opt_tco

# YCSB, both systems:
nohup bash obol/examples/benchmarks/run_ycsb_all_systems.sh results 80 60 30 10 > ycsb_logs.log 2>&1 &
```

Deployment mode is inherited from the environment exactly as in
`scripts/run_batch_experiments.sh` (`DEPLOY_MODE=docker-compose |
k8s-minikube | k8s-cluster`, plus `RELEASE_NAME`/`NAMESPACE` for k8s).

Result filenames encode the system, so sweeps are **resumable**: re-running
an orchestrator only executes the points whose result file is missing from
`SAVING_DIR`. TPC-C files are `tpcc_<system>_W<warehouses>_<tput>_ALL.json`,
YCSB files are `ycsbt_<system>_K<keys>_<tput>.json`. The sweep grids live in
`scripts/create_config.py` (`TPCC_RATES`, `YCSB_RATES_BY_KEYSPACE`); extend a
grid and re-run to add points.

To average several complete runs, keep each run in its own directory named
`results*` next to this file (`results`, `results_run2`, ...): the plot
scripts average every directory and additionally render a figure for
`results/` alone.

## Plotting

```bash
python plots_tpcc.py                # figures/saturation_wh[_avg].png
                                    #   3 systems: hand-written, Obol (gather),
                                    #   Obol (no gather)
python plots_ycsb.py                # figures/ycsb_results[_avg].png
python plots_tpcc_ablation.py       # figures/optimization_ladder.png + .csv
python plots_tpcc_ablation_grid.py  # figures/optimization_ladder_grid.png
```

`optimization_ladder.png` is one figure with three rows, one column per
warehouse count:

1. **saturation curves** — latency vs offered throughput, p50 solid / p99
   dashed, same style as `plots_tpcc.py`;
2. **latency distribution** — one box per configuration at a single offered
   rate, reconstructed from the percentiles in the result files (box spans
   p25–p75, interpolated from the recorded deciles; the median line and the
   p10/p99 whiskers are measured values);
3. **sustained throughput** — the highest offered rate each configuration
   holds while keeping p50 within the SLO.

Options: `--slo-ms 200` changes the p50 SLO used by rows 2 and 3 (default
100 ms); `--box-tput 2000` picks the offered rate for the boxes, snapped to
the nearest rate every configuration measured (default: the rate the full
system sustains under the SLO); `--no-reference` drops the hand-written Styx
reference and plots the four Obol rungs alone. All scripts accept `--hi-res`
for 300 dpi output.
