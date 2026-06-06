import argparse
import os

import pandas as pd

# -----------------------------
# Parse command-line arguments
# -----------------------------
parser = argparse.ArgumentParser(description="Generate Styx experiment config CSV")
parser.add_argument("--partitions", type=int, required=True, help="Number of partitions")
parser.add_argument("--n_keys", type=int, required=True, help="Number of keys")
parser.add_argument("--experiment_time", type=int, required=True, help="Total experiment time (seconds)")
parser.add_argument("--warmup_time", type=int, required=True, help="Warmup time (seconds)")
parser.add_argument(
    "--scenarios",
    nargs="+",
    default=["ycsbt_uni", "ycsbt_zipf", "dmr", "dhr", "tpcc"],
    help="Which scenarios to generate (default: all)"
)

args = parser.parse_args()
partitions = args.partitions
n_keys = args.n_keys
experiment_time = args.experiment_time
warmup_time = args.warmup_time
scenarios = set(args.scenarios)

script_path = os.path.dirname(os.path.realpath(__file__))

results_path = "results"

file_names = [f for f in os.listdir(results_path) if os.path.isfile(os.path.join(results_path, f))]

ycsbt_results = [file_name for file_name in file_names if file_name.startswith("ycsbt")]
d_movie_results = [file_name for file_name in file_names if file_name.startswith("d_movie")]
d_hotel_results = [file_name for file_name in file_names if file_name.startswith("d_hotel")]
tpcc_results = [file_name for file_name in file_names if file_name.startswith("tpcc_")]

lines = []

# UNIFORM
zipf_const = 0.0
input_throughput = [(100, 1),
                    (200, 1),
                    (300, 1),
                    (500, 1),
                    (700, 1),
                    (1000, 1),
                    (1500, 1),
                    (2000, 1),
                    (3000, 1),
                    (3000, 2),
                    (4000, 2),
                    (5000, 2),
                    (4000, 3),
                    (5000, 3),
                    (4000, 4),
                    (5000, 4),
                    (4400, 5),
                    (4800, 5),
                    (5200, 5),
                    (5600, 5),
                    (5000, 6),
                    (5500, 6),
                    (3400, 10),
                    (3500, 10),
                    (3600, 10),
                    (3700, 10),
                    (3800, 10),
                    (3900, 10),
                    (4000, 10),
                    (4100, 10),
                    (4200, 10),
                    (4300, 10),
                    (4400, 10),
                    (4500, 10),
                    (4600, 10),
                    (4700, 10),
                    (4800, 10),
                    (4900, 10),
                    (5000, 10),
                    (5100, 10),
                    (5200, 10),
                    (5300, 10),
                    (5400, 10),
                    (5500, 10),
                    (5600, 10),
                    (5700, 10),
                    (5800, 10),
                    (5900, 10),
                    (6000, 10),
                    (10000, 10),
                    (10000, 11),
                    (10000, 12),
                    (10000, 13),
                    (10000, 14),
                    (10000, 15),
                    (6400, 25),
                    (6800, 25),
                    (7200, 25),
                    (8000, 25),
                    (8400, 25),
                    (8600, 25),
                    (9200, 25),
                    (9600, 25)
                    ]

if "ycsbt_uni" in scenarios:
    for input_rate, n_threads in input_throughput:
        file_name = f"ycsbt_uni_{input_rate * n_threads}.json"
        if file_name not in ycsbt_results:
            lines.append(("ycsbt", input_rate, n_keys, partitions, zipf_const, n_threads,
                          experiment_time, warmup_time, 1_000, True, True, True))

# ZIPF

input_throughput = [(200, 1),
                    (700, 1),
                    (1000, 1),
                    (2000, 1),
                    (3000, 1),
                    (3000, 2),
                    (3500, 2),
                    (4000, 2)]
zipf_const_list = [0.1,
                   0.2,
                   0.3,
                   0.4,
                   0.5,
                   0.6,
                   0.7,
                   0.8,
                   0.9,
                   0.99,
                   0.999]

if "ycsbt_zipf" in scenarios:
    for input_rate, n_threads in input_throughput:
        for zipf_const in zipf_const_list:
            file_name = f"ycsbt_zipf_{zipf_const}_{input_rate * n_threads}.json"
            if file_name not in ycsbt_results:
                lines.append(("ycsbt", input_rate, n_keys, partitions,
                              zipf_const, n_threads, experiment_time, warmup_time, 100, True, True, True))


# deathstar hotel reservation
input_throughput = [(100, 1),
                    (300, 1),
                    (500, 1),
                    (700, 1),
                    (1000, 1),
                    (1500, 1),
                    (2000, 1),
                    (3000, 1),
                    (3000, 2),
                    (4000, 2),
                    (5000, 2),
                    (4000, 3),
                    (5000, 3),
                    (6000, 3),
                    (7000, 3),
                    (5000, 5),
                    (6000, 5),
                    (7000, 5),
                    (8000, 5),
                    (9000, 5),
                    (10000, 5),
                    (5500, 10),
                    (6000, 10)]

if "dhr" in scenarios:
    for input_rate, n_threads in input_throughput:
        file_name = f"d_hotel_reservation_{input_rate * n_threads}.json"
        if file_name not in d_hotel_results:
            lines.append(("dhr", input_rate, -1, partitions, 0.0, n_threads, experiment_time, warmup_time, 1_000, True, True, True))


# deathstar movie review

input_throughput = [(100, 1),
                    (300, 1),
                    (500, 1),
                    (700, 1),
                    (1000, 1),
                    (1500, 1),
                    (2000, 1),
                    (3000, 1),
                    (3000, 2),
                    (4000, 2),
                    (5000, 2),
                    (4000, 3),
                    (5000, 3),
                    (6000, 3),
                    (4000, 5),
                    (6000, 4),
                    (5000, 5)]

if "dmr" in scenarios:
    for input_rate, n_threads in input_throughput:
        file_name = f"d_movie_review_{input_rate * n_threads}.json"
        if file_name not in d_movie_results:
            lines.append(("dmr", input_rate, -1, partitions, 0.0, n_threads, experiment_time, warmup_time, 1_000, True, True, True))


# tpcc
n_workers = [10, 100]

# per-worker caps
max_rate = {
    10: 4000,
    100: 10000,
}


min_val = 100
max_val = 4000
step = 200

input_throughput = [
    (v, 1)
    for v in range(min_val, max_val + 1, step)
]

# # Comment these two lines out to run the full sweep above.
# n_workers = [10]
# input_throughput = [(350, 1)]
# ============================================================================


# define the three configurations
configs = [
    # (enable_compression, use_composite_keys, suffix)
    (True,  True,  "ALL"),
    # (False, True,  "NO_COMP"),
    # (True,  False, "NO_CK"),
]

tpcc_system = os.environ.get("TPCC_SYSTEM", "handwritten")

if "tpcc" in scenarios:
    for input_rate, n_threads in input_throughput:
        for n_w in n_workers:
            # skip rates above the per-worker cap
            if input_rate > max_rate[n_w]:
                continue
            for enable_compression, use_composite_keys, tag in configs:
                # file name now encodes the variant tag
                file_name = f"tpcc_{tpcc_system}_W{n_w}_{input_rate * n_threads}_{tag}.json"

                if file_name not in tpcc_results:
                    lines.append((
                        "tpcc",
                        input_rate,
                        n_w,
                        partitions,
                        0.0,
                        n_threads,
                        experiment_time,
                        warmup_time,
                        100,
                        enable_compression,
                        use_composite_keys,
                    ))

# ============================================================================
# Obol YCSB saturation sweep (hand-written Styx vs Obol-compiled)
#
# Mirrors the TPC-C sweep: a 100..4000 txn/s offered-rate sweep, single client
# thread, run under two key-space sizes that place the `transfer` workload in
# opposite contention regimes:
#   - small key space (1_000 keys)   -> high contention (hot keys, like 10 wh)
#   - large key space (100_000 keys) -> low contention  (like 100 warehouses)
# The system token (handwritten | obol) comes from $YCSB_SYSTEM so the two
# systems write distinct result files and reruns skip already-completed points.
# To push past single-thread saturation, raise the n_threads field below.
# ============================================================================
ycsb_system = os.environ.get("YCSB_SYSTEM", "handwritten")

ycsb_keyspaces = [1_000, 100_000]          # high-contention, low-contention
ycsb_zipf = 0.0

# The transfer txn is far lighter than TPC-C New-Order (a single remote call,
# no fan-out/aggregation), so it sustains an order of magnitude more load. Each
# pair is (per-thread input_rate, n_threads); offered throughput is the product.
# Above ~3k a single client thread cannot offer the rate, so we add threads.
#
# Shared base sweep both key-spaces already ran (~100 .. 50k txn/s, log-spaced):
_ycsb_base = [
    (100, 1), (200, 1), (300, 1), (500, 1), (700, 1),
    (1000, 1), (1500, 1), (2000, 1), (3000, 1),     # single-thread, up to 3k
    (2000, 2), (2500, 2), (3000, 2), (4000, 2), (5000, 2),   # 4k .. 10k
    (4000, 3), (5000, 3),                            # 12k, 15k
    (5000, 4), (5000, 5), (5000, 6),                 # 20k, 25k, 30k
    (5000, 8), (5000, 9), (5000, 10),                           # 40k, 50k
]

# Per-key-space sweeps. Each regime saturates at a different load, so they get
# different extra points. Re-running only adds points whose result file is
# missing, so extending these lists and re-running is cheap.
ycsb_rates_by_keyspace = {
    # High contention: flat until ~30k, only 40k/50k saturate -> two points in
    # the 30k-40k gap to define the knee.
    1_000:   _ycsb_base + [(3300, 10), (3700, 10)],              # 33k, 37k
    # Low contention: still climbing at 90k (only ~150ms p50), so push much
    # higher to find the knee. Per thread tops out ~10k txn/s, so we scale
    # threads (load-gen has 96 cores). The original Styx YCSB sweep saturated
    # this regime by ~240k, so we sweep up to 320k to bracket it.
    100_000: _ycsb_base + [
        (6000, 10), (7500, 10), (9000, 10),          # 60k, 75k, 90k (already run)
        (10000, 10), (10000, 13), (10000, 16),       # 100k, 130k, 160k
        (10000, 20), (10000, 24), (10000, 28),       # 200k, 240k, 280k
        (10000, 32),                                 # 320k
    ],
}

if "ycsb" in scenarios:
    for ks in ycsb_keyspaces:
        for input_rate, n_threads in ycsb_rates_by_keyspace[ks]:
            file_name = f"ycsbt_{ycsb_system}_K{ks}_{input_rate * n_threads}.json"
            if file_name not in ycsbt_results:
                lines.append(("ycsbt", input_rate, ks, partitions, ycsb_zipf,
                              n_threads, experiment_time, warmup_time,
                              1_000, True, True, True))

df = pd.DataFrame(lines)
df.to_csv(os.path.join(script_path, "styx_experiments_config.csv"), index=False, header=False)
