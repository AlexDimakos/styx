"""Generate scripts/styx_experiments_config.csv for run_batch_experiments.sh.

Each emitted row is one experiment:

    workload,input_rate,n_keys,n_part,zipf_const,n_threads,total_time,warmup,epoch_size,enable_compression,use_composite_keys

Rows whose result file already exists in --results_dir are skipped, so an
interrupted sweep can be resumed by simply re-running the orchestrator: only
the missing points are generated again.

The TPC-C and YCSB sweeps encode the system under test (handwritten vs the
Obol-compiled variants) in the result filename via the TPCC_SYSTEM /
YCSB_SYSTEM environment variables, mirroring how demo/*/calculate_metrics.py
names its output files.
"""

import argparse
import os

import pandas as pd

parser = argparse.ArgumentParser(description="Generate Styx experiment config CSV")
parser.add_argument("--partitions", type=int, required=True, help="Number of partitions")
parser.add_argument("--n_keys", type=int, required=True, help="Number of keys")
parser.add_argument("--experiment_time", type=int, required=True, help="Total experiment time (seconds)")
parser.add_argument("--warmup_time", type=int, required=True, help="Warmup time (seconds)")
parser.add_argument(
    "--scenarios",
    nargs="+",
    default=["ycsbt_uni", "ycsbt_zipf", "dmr", "dhr", "tpcc"],
    help="Which scenarios to generate (default: all)",
)
parser.add_argument(
    "--results_dir",
    default="results",
    help="Directory scanned for already-completed result files (default: results)",
)

args = parser.parse_args()
partitions = args.partitions
n_keys = args.n_keys
experiment_time = args.experiment_time
warmup_time = args.warmup_time
scenarios = set(args.scenarios)

script_path = os.path.dirname(os.path.realpath(__file__))

if os.path.isdir(args.results_dir):
    existing_results = {
        f for f in os.listdir(args.results_dir) if os.path.isfile(os.path.join(args.results_dir, f))
    }
else:
    existing_results = set()

lines = []


def add(workload, input_rate, keys, zipf_const, n_threads, epoch_size, file_name):
    if file_name not in existing_results:
        lines.append((workload, input_rate, keys, partitions, zipf_const, n_threads,
                      experiment_time, warmup_time, epoch_size, True, True))


# ============================================================================
# YCSB-T uniform / zipfian and DeathStar sweeps (legacy Styx experiments)
# ============================================================================

YCSBT_UNI_SWEEP = [
    (100, 1), (200, 1), (300, 1), (500, 1), (700, 1), (1000, 1), (1500, 1),
    (2000, 1), (3000, 1), (3000, 2), (4000, 2), (5000, 2), (4000, 3),
    (5000, 3), (4000, 4), (5000, 4), (4400, 5), (4800, 5), (5200, 5),
    (5600, 5), (5000, 6), (5500, 6),
    (3400, 10), (3500, 10), (3600, 10), (3700, 10), (3800, 10), (3900, 10),
    (4000, 10), (4100, 10), (4200, 10), (4300, 10), (4400, 10), (4500, 10),
    (4600, 10), (4700, 10), (4800, 10), (4900, 10), (5000, 10), (5100, 10),
    (5200, 10), (5300, 10), (5400, 10), (5500, 10), (5600, 10), (5700, 10),
    (5800, 10), (5900, 10), (6000, 10), (10000, 10), (10000, 11),
    (10000, 12), (10000, 13), (10000, 14), (10000, 15), (6400, 25),
    (6800, 25), (7200, 25), (8000, 25), (8400, 25), (8600, 25), (9200, 25),
    (9600, 25),
]

if "ycsbt_uni" in scenarios:
    for input_rate, n_threads in YCSBT_UNI_SWEEP:
        add("ycsbt", input_rate, n_keys, 0.0, n_threads, 1_000,
            f"ycsbt_uni_{input_rate * n_threads}.json")

YCSBT_ZIPF_SWEEP = [(200, 1), (700, 1), (1000, 1), (2000, 1), (3000, 1),
                    (3000, 2), (3500, 2), (4000, 2)]
ZIPF_CONSTANTS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99, 0.999]

if "ycsbt_zipf" in scenarios:
    for input_rate, n_threads in YCSBT_ZIPF_SWEEP:
        for zipf_const in ZIPF_CONSTANTS:
            add("ycsbt", input_rate, n_keys, zipf_const, n_threads, 100,
                f"ycsbt_zipf_{zipf_const}_{input_rate * n_threads}.json")

DHR_SWEEP = [
    (100, 1), (300, 1), (500, 1), (700, 1), (1000, 1), (1500, 1), (2000, 1),
    (3000, 1), (3000, 2), (4000, 2), (5000, 2), (4000, 3), (5000, 3),
    (6000, 3), (7000, 3), (5000, 5), (6000, 5), (7000, 5), (8000, 5),
    (9000, 5), (10000, 5), (5500, 10), (6000, 10),
]

if "dhr" in scenarios:
    for input_rate, n_threads in DHR_SWEEP:
        add("dhr", input_rate, -1, 0.0, n_threads, 1_000,
            f"d_hotel_reservation_{input_rate * n_threads}.json")

DMR_SWEEP = [
    (100, 1), (300, 1), (500, 1), (700, 1), (1000, 1), (1500, 1), (2000, 1),
    (3000, 1), (3000, 2), (4000, 2), (5000, 2), (4000, 3), (5000, 3),
    (6000, 3), (4000, 5), (6000, 4), (5000, 5),
]

if "dmr" in scenarios:
    for input_rate, n_threads in DMR_SWEEP:
        add("dmr", input_rate, -1, 0.0, n_threads, 1_000,
            f"d_movie_review_{input_rate * n_threads}.json")


# ============================================================================
# TPC-C saturation sweep (hand-written Styx vs Obol-compiled variants)
#
# The system token comes from $TPCC_SYSTEM (handwritten | obol_gather |
# obol_nogather | obol_no_tco | obol_ctx_net | obol_no_live) so every system
# writes distinct result files and reruns skip already-completed points.
# ============================================================================

tpcc_system = os.environ.get("TPCC_SYSTEM", "handwritten")

# Warehouse counts place TPC-C in opposite contention regimes:
# 10 warehouses -> high contention, 100 warehouses -> low contention.
TPCC_WAREHOUSES = [int(w) for w in os.environ.get("TPCC_WAREHOUSES", "10 100").split()]

# Offered-rate sweep with a per-warehouse-count cap. Each pair is
# (per-thread rate, client threads); offered throughput is their product.
TPCC_MAX_RATE = {10: 4000, 100: 7000}
TPCC_RATES = [(v, 1) for v in range(100, 4001, 200)]

# Low contention (100 wh) does not saturate by 4k, so extend its sweep to 7k
# at the same 200 txn/s granularity. A single client thread cannot offer much
# beyond ~3-4k txn/s of TPC-C input, so the extension uses 2 client threads
# at half the per-thread rate (like the YCSB sweep).
TPCC_EXTRA_RATES = {
    100: [(tput // 2, 2) for tput in range(4200, 7001, 200)],
}

if "tpcc" in scenarios:
    for n_w in TPCC_WAREHOUSES:
        for input_rate, n_threads in TPCC_RATES + TPCC_EXTRA_RATES.get(n_w, []):
            tput = input_rate * n_threads
            if tput > TPCC_MAX_RATE.get(n_w, 4000):
                continue
            add("tpcc", input_rate, n_w, 0.0, n_threads, 100,
                f"tpcc_{tpcc_system}_W{n_w}_{tput}_ALL.json")


# ============================================================================
# Obol YCSB saturation sweep (hand-written Styx vs Obol-compiled)
#
# Two key-space sizes put the `transfer` workload in opposite contention
# regimes: 1_000 keys -> high contention, 100_000 keys -> low contention.
# The system token comes from $YCSB_SYSTEM (handwritten | obol).
# ============================================================================

ycsb_system = os.environ.get("YCSB_SYSTEM", "handwritten")

YCSB_KEYSPACES = [1_000, 100_000]

# Shared base sweep (~100 .. 50k txn/s, log-spaced). Each pair is
# (per-thread rate, n_threads); the offered throughput is their product.
# A single client thread tops out around 3k txn/s, hence the thread scaling.
_YCSB_BASE = [
    (100, 1), (200, 1), (300, 1), (500, 1), (700, 1),
    (1000, 1), (1500, 1), (2000, 1), (3000, 1),
    (2000, 2), (2500, 2), (3000, 2), (4000, 2), (5000, 2),
    (4000, 3), (5000, 3),
    (5000, 4), (5000, 5), (5000, 6),
    (5000, 8), (5000, 9), (5000, 10),
]

# Per-key-space extras: each contention regime saturates at a different load.
YCSB_RATES_BY_KEYSPACE = {
    # High contention: flat until ~30k; extra points define the knee.
    1_000: [*_YCSB_BASE, (3300, 10), (3700, 10)],
    # Low contention: saturates an order of magnitude later, so push to ~320k.
    100_000: [
        *_YCSB_BASE,
        (6000, 10), (7500, 10), (9000, 10),
        (10000, 10), (10000, 13), (10000, 16),
        (10000, 20), (10000, 24), (10000, 28),
        (10000, 32),
    ],
}

if "ycsb" in scenarios:
    for keyspace in YCSB_KEYSPACES:
        for input_rate, n_threads in YCSB_RATES_BY_KEYSPACE[keyspace]:
            add("ycsbt", input_rate, keyspace, 0.0, n_threads, 1_000,
                f"ycsbt_{ycsb_system}_K{keyspace}_{input_rate * n_threads}.json")


df = pd.DataFrame(lines)
df.to_csv(os.path.join(script_path, "styx_experiments_config.csv"), index=False, header=False)
print(f"styx_experiments_config.csv: {len(lines)} experiments to run "
      f"({len(existing_results)} existing result files found in '{args.results_dir}')")
