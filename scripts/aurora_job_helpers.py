"""Thin wrappers around qsub/qstat for the optional Aurora live-training bonus.

Used by the live-training section of notebooks/01_scaling_analysis.ipynb. Not
required for the rest of that notebook, and does nothing useful off of a
system with `qsub`/`qstat` and access to the GenesisHackathonOct26
reservation/allocation (see aurora_submit_isoflop.sh) — callers should check
`on_pbs_system()` first and fall back to stored data, or to
iri_job_helpers.py's IRI API path, otherwise.
"""
import re
import shutil
import subprocess
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SUBMIT_SCRIPT = SCRIPT_DIR / "aurora_submit_isoflop.sh"
RESULTS_DIR = SCRIPT_DIR.parent / "data" / "aurora_bonus_runs"

# Defaults match the #PBS directives baked into aurora_submit_isoflop.sh (the
# hackathon reservation/allocation). Pass queue/account to submit_job() to
# override them per-call -- qsub's -q/-A flags take precedence over the
# script's own #PBS directives, so this needs no change to the .sh file.
DEFAULT_QUEUE = "R8914313"
DEFAULT_ACCOUNT = "GenesisHackathonOct26"


def on_pbs_system() -> bool:
    """True if qsub/qstat are available on this machine."""
    return shutil.which("qsub") is not None and shutil.which("qstat") is not None


def submit_job(depth: int = 10, target_flops: str = "5e16",
                queue: str = DEFAULT_QUEUE, account: str = DEFAULT_ACCOUNT) -> str:
    """Submit one IsoFLOP sweep point. Returns the PBS job id.

    queue/account default to the hackathon reservation/allocation but can be
    overridden (e.g. for personal testing against a different queue/project).
    """
    result = subprocess.run(
        ["qsub", "-q", queue, "-A", account,
         "-v", f"DEPTH={depth},TARGET_FLOPS={target_flops}", str(SUBMIT_SCRIPT)],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def job_status(job_id: str) -> str:
    """One of 'Q' (queued), 'R' (running), 'F'/'done' (finished or not found)."""
    result = subprocess.run(["qstat", "-x", job_id], capture_output=True, text=True)
    if result.returncode != 0:
        return "done"
    lines = [l for l in result.stdout.splitlines() if job_id.split(".")[0] in l]
    if not lines:
        return "done"
    fields = lines[0].split()
    return fields[-2] if len(fields) >= 2 else "unknown"


def wait_for_job(job_id: str, poll_seconds: int = 30, max_polls: int = 6) -> bool:
    """Poll a bounded number of times (default: up to 3 minutes). Returns True if finished."""
    for _ in range(max_polls):
        status = job_status(job_id)
        if status in ("done", "F"):
            return True
        time.sleep(poll_seconds)
    return False


def parse_result_row(target_flops: str, depth: int) -> dict | None:
    """Parse a completed run's training log into a results.csv-shaped row.

    Mirrors the extraction pattern in nanochat's runs/scaling_laws.sh.
    Returns None if the log doesn't exist or doesn't contain a final val_bpb.
    """
    tag = f"bonus_{target_flops}_d{depth}"
    log_file = RESULTS_DIR / f"{tag}_train.log"
    if not log_file.exists():
        return None

    text = log_file.read_text()

    def last_match(pattern):
        matches = re.findall(pattern, text)
        return matches[-1] if matches else None

    val_bpb = last_match(r"Validation bpb:\s*([\d.]+)")
    params_transformer = last_match(r"transformer_matrices:\s*([\d,]+)")
    num_iters = last_match(r"Calculated number of iterations[^\d]*(\d+)")
    if val_bpb is None or params_transformer is None or num_iters is None:
        return None

    model_dim = depth * 64
    tokens_trained = int(num_iters) * 524288
    return {
        "flops_budget": target_flops,
        "depth": depth,
        "model_dim": model_dim,
        "params_transformer": int(params_transformer.replace(",", "")),
        "params_total": None,
        "num_iterations": int(num_iters),
        "tokens_trained": tokens_trained,
        "val_bpb": float(val_bpb),
        "core_score": None,
        "train_time_sec": None,
    }
