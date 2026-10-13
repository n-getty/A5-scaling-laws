#!/bin/bash
#PBS -N a5_isoflop_bonus
#PBS -q debug
#PBS -A ModCon
#PBS -l select=1
#PBS -l walltime=00:55:00
#PBS -l filesystems=home:flare
#PBS -j oe
#PBS -o aurora_bonus_job.log

# Single IsoFLOP sweep point for the A5 Scaling Laws hands-on bonus notebook.
# Targets Aurora's `debug` queue (1 node, <=1hr walltime), billed to the
# ModCon allocation. Run depth/budget are kept small so the run plausibly
# finishes inside the debug queue's walltime cap on XPU.
#
# Submit with: qsub -v DEPTH=10,TARGET_FLOPS=5e16 aurora_submit_isoflop.sh
# (02_live_training_bonus.ipynb does this for you via aurora_job_helpers.py)

# NB: no `set -u` -- Lmod's init trips it at `module load` (unbound
# ZSH_EVAL_CONTEXT), same gotcha documented in the vjepa2 reference scripts.
set -eo pipefail

DEPTH="${DEPTH:-10}"
TARGET_FLOPS="${TARGET_FLOPS:-5e16}"
TAG="bonus_${TARGET_FLOPS}_d${DEPTH}"

cd "${NANOCHAT_REPO:-$PBS_O_WORKDIR/../nanochat}"

# Aurora's `module load frameworks` provides a patched torch build with native
# XPU dispatch keys and xccl distributed support already compiled in -- no
# separate venv/IPEX install needed. See nanochat's pyproject.toml `xpu` extra.
module load frameworks

export OMP_NUM_THREADS=1
# Default to the shared Aurora data dir (tokenizer + base_data already staged there) --
# $HOME/.cache/nanochat has no tokenizer.pkl and fails fast with FileNotFoundError
# (confirmed on job 8925861) before ever reaching the training loop.
export NANOCHAT_BASE_DIR="${NANOCHAT_BASE_DIR:-/flare/AuroraGPT/ngetty/data/nanochat}"
RESULTS_DIR="$PBS_O_WORKDIR/../data/aurora_bonus_runs"
mkdir -p "$RESULTS_DIR"
LOG_FILE="$RESULTS_DIR/${TAG}_train.log"

# base_train.py has no --no-compile flag: it skips torch.compile automatically
# when --device-type=xpu (inductor's Triton backend isn't reliable there yet).
#
# --device-batch-size=8: the default of 32 OOMs on a single Max 1550 tile (64GB) --
# logits are computed in fp32 for the softcap+loss (gpt.py), so at seq_len=2048 and
# vocab_size=65536 the activation memory for backward blows past capacity. Confirmed
# via a live OOM trace on job 8925823/8925845: "Tried to allocate 16.00 GiB ... 54.07
# GiB is allocated by PyTorch" right at loss.backward() on step 0.
python -m scripts.base_train \
    --device-type=xpu \
    --depth="$DEPTH" \
    --device-batch-size=8 \
    --target-flops="$TARGET_FLOPS" \
    --target-param-data-ratio=-1 \
    --run=dummy \
    --model-tag="$TAG" \
    --core-metric-every=-1 \
    --sample-every=-1 \
    --save-every=-1 \
    2>&1 | tee "$LOG_FILE"

echo "DONE: log at $LOG_FILE"
