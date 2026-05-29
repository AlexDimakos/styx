
# nohup ./scripts/run_tpcc_all_systems.sh > tpcc_logs.log 2>&1 &

set -u

SAVING_DIR=${1:-results}
PARTITIONS=${2:-4}
EXP_TIME=${3:-60}
WARMUP=${4:-30}
STYX_THREADS_PER_WORKER=${5:-1}

CONFIG_CSV="scripts/styx_experiments_config.csv"
N_KEYS=10  # ignored for tpcc (warehouses come from create_config.py), kept for the positional API

mkdir -p "$SAVING_DIR"

run_system() {
    local system=$1 variant=$2
    echo
    echo "############################################################"
    echo "# SYSTEM: $system   (compiled variant: $variant)"
    echo "############################################################"
    export TPCC_SYSTEM="$system"
    export TPCC_COMPILED_VARIANT="$variant"

    ./scripts/run_batch_experiments.sh \
        "$CONFIG_CSV" \
        "$SAVING_DIR" \
        "$STYX_THREADS_PER_WORKER" \
        "$PARTITIONS" \
        "$N_KEYS" \
        "$EXP_TIME" \
        "$WARMUP" \
        tpcc
}

# 1) hand-written Styx baseline
run_system handwritten   gather
# 2) Obol, compiled functions WITH gather
run_system obol_gather   gather
# 3) Obol, compiled functions WITHOUT gather
run_system obol_nogather no_gather

echo
echo "ALL TPC-C SYSTEMS DONE -> $SAVING_DIR"
