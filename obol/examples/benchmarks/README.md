# Obol benchmarks: YCSB, TPC-C, and the optimization ablation study

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
| `run_tpcc_all_systems.sh` | TPC-C sweep over all systems + ablation variants |
| `run_ycsb_all_systems.sh` | YCSB sweep over hand-written and Obol |
| `plots_tpcc.py` / `plots_ycsb.py` | Main comparison figures |
| `plots_tpcc_ablation.py` | Ablation figures + summary table |
| `results*/` | Result JSONs, one directory per run (not committed) |
| `figures/` | Rendered PNGs |

## Systems and ablation variants

The TPC-C sweep runs six systems. Each Obol ablation variant disables exactly
one optimization relative to the full system, so the gap between
`obol_gather` and a variant isolates that optimization's contribution:

| System token | Compiled variant | What is ablated |
|---|---|---|
| `handwritten` | — | Baseline: hand-written Styx operators |
| `obol_gather` | `gather` | Nothing — the full system |
| `obol_nogather` | `no_gather` | `gather` fan-out: independent remote calls are dispatched sequentially |
| `obol_no_tco` | `no_tco` | Distributed tail-call optimization: replies route back through every intermediate entity |
| `obol_ctx_net` | `ctx_net` | Context-in-state: the live context dict travels inside `reply_to` over the network instead of being saved in the operator's function-context store |
| `obol_no_live` | `no_live` | Live-variable analysis: every defined variable is serialized at each split, not just the live set |

The variants are produced by compiler flags (see `obol --help`:
`--no-tail-call`, `--context-over-network`, `--no-liveness`), wired through
the `OBOL_DISABLE_TAIL_CALL`, `OBOL_CONTEXT_OVER_NETWORK`, and
`OBOL_DISABLE_LIVENESS` environment variables. `no_gather` is a source-level
variant (`original/tpcc_no_gather.py`). All ablation is client-side: every
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

# only the ablation variants you still need:
bash obol/examples/benchmarks/run_tpcc_all_systems.sh results 80 60 30 10 obol_no_tco obol_ctx_net

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
python plots_tpcc.py           # figures/saturation_wh[_avg].png (3 main systems)
python plots_ycsb.py           # figures/ycsb_results[_avg].png
python plots_tpcc_ablation.py  # figures/ablation_saturation.png,
                               # figures/ablation_summary.png + .csv
```

`plots_tpcc_ablation.py --slo-ms 200` changes the p50 SLO used for the
sustained-throughput summary bars (default 100 ms). All scripts accept
`--hi-res` for 300 dpi output.
