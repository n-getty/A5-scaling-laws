#!/bin/bash
#PBS -N a5_isoflop_bonus
#PBS -q debug
#PBS -A ModCon
#PBS -l select=1
#PBS -l walltime=00:55:00
#PBS -j oe
#PBS -o aurora_bonus_job.log

# Single IsoFLOP sweep point for the A5 Scaling Laws hands-on bonus notebook.
# Targets Aurora's `debug` queue (1 node, <=1hr walltime), billed to the
# ModCon allocation. Run depth/budget are kept small so the run plausibly
# finishes inside the debug queue's walltime cap on XPU.
#
# Submit with: qsub -v DEPTH=10,TARGET_FLOPS=5e16 aurora_submit_isoflop.sh
# (02_live_training_bonus.ipynb does this for you via aurora_job_helpers.py)

set -euo pipefail

DEPTH="${DEPTH:-10}"
TARGET_FLOPS="${TARGET_FLOPS:-5e16}"
TAG="bonus_${TARGET_FLOPS}_d${DEPTH}"

cd "${NANOCHAT_REPO:-$PBS_O_WORKDIR/../nanochat}"

# Aurora's `module load frameworks` provides a patched torch build with native
# XPU dispatch keys and xccl distributed support already compiled in -- no
# separate venv/IPEX install needed. See nanochat's pyproject.toml `xpu` extra.
module load frameworks

export OMP_NUM_THREADS=1
export NANOCHAT_BASE_DIR="${NANOCHAT_BASE_DIR:-$HOME/.cache/nanochat}"
RESULTS_DIR="$PBS_O_WORKDIR/../data/aurora_bonus_runs"
mkdir -p "$RESULTS_DIR"
LOG_FILE="$RESULTS_DIR/${TAG}_train.log"

# base_train.py has no --no-compile flag: it skips torch.compile automatically
# when --device-type=xpu (inductor's Triton backend isn't reliable there yet).
python -m scripts.base_train \
    --device-type=xpu \
    --depth="$DEPTH" \
    --target-flops="$TARGET_FLOPS" \
    --target-param-data-ratio=-1 \
    --run=dummy \
    --model-tag="$TAG" \
    --core-metric-every=-1 \
    --sample-every=-1 \
    --save-every=-1 \
    2>&1 | tee "$LOG_FILE"

echo "DONE: log at $LOG_FILE"
