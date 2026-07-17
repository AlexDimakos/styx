#!/bin/bash
# Runs the YCSB `transfer` saturation sweep for the hand-written Styx
# operator and the Obol-compiled operator, storing one result file per
# (system, key-space, offered-throughput) point.
#
# Typical cluster invocation (from anywhere):
#   nohup bash obol/examples/benchmarks/run_ycsb_all_systems.sh results 80 60 30 10 > ycsb_logs.log 2>&1 &
#
# Usage (mirrors run_tpcc_all_systems.sh):
#   bash run_ycsb_all_systems.sh [SAVING_DIR] [PARTITIONS] [EXP_TIME] [WARMUP] [STYX_THREADS_PER_WORKER] [SYSTEM ...]
#
# SYSTEM (optional, defaults to both):
#   handwritten   hand-written Styx operator (demo/demo-ycsb/ycsb.py)
#   obol          Obol-compiled operator     (demo/demo-ycsb/ycsb_compiled.py)
#
# Result files land in SAVING_DIR as ycsbt_<system>_K<keys>_<tput>.json;
# already-existing points are skipped, so the sweep is resumable.
#
# Deployment mode (docker-compose | k8s-minikube | k8s-cluster) is inherited
# from the environment exactly as in scripts/run_batch_experiments.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

SAVING_DIR=${1:-results}
PARTITIONS=${2:-4}
EXP_TIME=${3:-60}
WARMUP=${4:-30}
STYX_THREADS_PER_WORKER=${5:-1}
shift $(( $# < 5 ? $# : 5 ))

DEFAULT_SYSTEMS=(handwritten obol)
if [ $# -gt 0 ]; then
    SYSTEMS=("$@")
else
    SYSTEMS=("${DEFAULT_SYSTEMS[@]}")
fi

CONFIG_CSV="scripts/styx_experiments_config.csv"
N_KEYS=10  # ignored for ycsb (key-space sizes come from create_config.py)

for system in "${SYSTEMS[@]}"; do
    case "$system" in
        handwritten|obol) ;;
        *) echo "ERROR: unknown system '$system' (expected: ${DEFAULT_SYSTEMS[*]})" >&2; exit 1 ;;
    esac
done

mkdir -p "$SAVING_DIR"

run_system() {
    local system=$1
    echo
    echo "############################################################"
    echo "# SYSTEM: $system"
    echo "############################################################"
    export YCSB_SYSTEM="$system"

    ./scripts/run_batch_experiments.sh \
        "$CONFIG_CSV" \
        "$SAVING_DIR" \
        "$STYX_THREADS_PER_WORKER" \
        "$PARTITIONS" \
        "$N_KEYS" \
        "$EXP_TIME" \
        "$WARMUP" \
        ycsb
}

for system in "${SYSTEMS[@]}"; do
    run_system "$system"
done

echo
echo "ALL YCSB SYSTEMS DONE (${SYSTEMS[*]}) -> $SAVING_DIR"
