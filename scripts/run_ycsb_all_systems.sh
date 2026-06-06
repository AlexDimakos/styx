
# nohup ./scripts/run_ycsb_all_systems.sh > ycsb_logs.log 2>&1 &
#
# Runs the YCSB `transfer` saturation sweep for every system on the Styx
# runtime and stores one result file per (system, key-space, throughput) point.
#
# Usage (mirrors run_tpcc_all_systems.sh):
#   bash scripts/run_ycsb_all_systems.sh <SAVING_DIR> <PARTITIONS> <EXP_TIME> <WARMUP> <STYX_THREADS_PER_WORKER>
#   e.g.  bash scripts/run_ycsb_all_systems.sh results 80 60 30 10
#
# Deployment mode (docker-compose | k8s-minikube | k8s-cluster) is inherited
# from the environment exactly as in run_batch_experiments.sh / run_experiment.sh.

set -u

SAVING_DIR=${1:-results}
PARTITIONS=${2:-4}
EXP_TIME=${3:-60}
WARMUP=${4:-30}
STYX_THREADS_PER_WORKER=${5:-1}

CONFIG_CSV="scripts/styx_experiments_config.csv"
N_KEYS=10  # ignored for ycsb (key-spaces come from create_config.py), kept for the positional API

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

# 1) hand-written Styx baseline
run_system handwritten
# 2) Obol, compiled functions
run_system obol

echo
echo "ALL YCSB SYSTEMS DONE -> $SAVING_DIR"
