"""Thin client for the DOE IRI Facility API, as an alternative to the PBS/qsub
path in aurora_job_helpers.py for the optional Aurora live-training bonus.

Used by notebooks/01_scaling_analysis.ipynb's live-training section. Targets
ALCF's IRI API (https://docs.alcf.anl.gov/services/iri-api/) against Aurora,
following the request/response shapes in
github.com/doe-iri/iri-facility-api-examples (genesis_hackathon/). The point
of this path is that it works from anywhere with network access (a laptop,
not just an Aurora login node) -- the tradeoff is it needs an ALCF IRI token
instead of an interactive Aurora session.

Requires `requests` and `python-dotenv` (pip install -e .[iri]), and an
IRI_TOKEN_ALCF in the environment or a .env file at the repo root -- see
https://github.com/doe-iri/iri-facility-api-examples/tree/main/genesis_hackathon
for how to mint one with `alcf-tokens login iri`. Callers should check
`iri_available()` first and fall back to stored data (or the PBS path)
otherwise.
"""
import os
import re
import time

BASE_URL = "https://api.alcf.anl.gov/api/v1"

# Resource IDs are fixed for the hackathon (Aurora / Flare); see config_alcf.py
# in the iri-facility-api-examples repo for the full list across facilities.
AURORA_COMPUTE_RESOURCE_ID = "0325fc07-6fb7-4453-b772-3d5030b2df72"
AURORA_FILESYSTEM_RESOURCE_ID = "154bb3be-5d12-4a76-a16b-898b8e310a4b"  # Flare

# Same hackathon reservation/allocation as aurora_submit_isoflop.sh.
RESERVATION_QUEUE = "R8914313"
ALLOCATION = "GenesisHackathonOct26"
WALLTIME_SEC = 3300  # 55 min, matches aurora_submit_isoflop.sh


def _load_token():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    return os.environ.get("IRI_TOKEN_ALCF")


def iri_available() -> bool:
    """True if `requests` is installed and an ALCF IRI token is configured."""
    try:
        import requests  # noqa: F401
    except ImportError:
        return False
    return bool(_load_token())


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def submit_job(alcf_username: str, depth: int = 10, target_flops: str = "5e16",
               nanochat_dir: "str | None" = None,
               queue: str = RESERVATION_QUEUE, account: str = ALLOCATION,
               flare_project: "str | None" = None):
    """Submit one IsoFLOP sweep point to Aurora via the IRI API.

    Runs the same training command as aurora_submit_isoflop.sh through the
    IRI API's job-submission endpoint instead of a local qsub call. queue/
    account default to the hackathon reservation/allocation but can be
    overridden (e.g. for personal testing against a different queue/
    project). flare_project controls the stdout/stderr directory on the
    Flare filesystem and defaults to `account` -- override it separately if
    your Flare project directory differs from your billing account. Returns
    (job_id, stdout_path) -- stdout_path is needed later to fetch the result
    via the filesystem API.
    """
    import requests

    token = _load_token()
    if not token:
        raise RuntimeError("IRI_TOKEN_ALCF not set -- see the IRI repo's README to mint one.")
    if not alcf_username:
        raise ValueError("alcf_username is required (used for stdout/stderr paths).")

    flare_project = flare_project or account
    tag = f"bonus_{target_flops}_d{depth}"
    nanochat_dir = nanochat_dir or f"/home/{alcf_username}/proj/nanochat"
    stdout_path = f"/flare/{flare_project}/{alcf_username}_{tag}.out"
    stderr_path = f"/flare/{flare_project}/{alcf_username}_{tag}.err"

    commands = f"""
module load frameworks
export OMP_NUM_THREADS=1
export NANOCHAT_BASE_DIR="${{NANOCHAT_BASE_DIR:-/flare/AuroraGPT/ngetty/data/nanochat}}"
cd {nanochat_dir}
python -m scripts.base_train \\
    --device-type=xpu \\
    --depth={depth} \\
    --device-batch-size=8 \\
    --target-flops={target_flops} \\
    --target-param-data-ratio=-1 \\
    --run=dummy \\
    --model-tag={tag} \\
    --core-metric-every=-1 \\
    --sample-every=-1 \\
    --save-every=-1
"""

    payload = {
        "executable": "/bin/bash",
        "arguments": ["-lc", commands],
        "name": f"a5-isoflop-{tag}",
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "resources": {"node_count": 1},
        "attributes": {
            "duration": WALLTIME_SEC,
            "queue_name": queue,
            "account": account,
            "custom_attributes": {"filesystems": "flare"},
        },
    }
    response = requests.post(
        f"{BASE_URL}/compute/job/{AURORA_COMPUTE_RESOURCE_ID}",
        json=payload, headers=_headers(token),
    )
    response.raise_for_status()
    body = response.json()
    job_id = body.get("id")
    if not job_id:
        raise RuntimeError(f"Submission did not return a job id: {body}")
    return job_id, stdout_path


def job_status(job_id: str) -> str:
    """One of the IRI API's job states ('queued', 'running', 'completed', 'failed', ...)."""
    import requests
    token = _load_token()
    response = requests.get(
        f"{BASE_URL}/compute/status/{AURORA_COMPUTE_RESOURCE_ID}/{job_id}",
        headers=_headers(token),
    )
    response.raise_for_status()
    return response.json().get("status", {}).get("state", "unknown")


def wait_for_job(job_id: str, poll_seconds: int = 30, max_polls: int = 6) -> bool:
    """Poll a bounded number of times (default: up to 3 minutes). Returns True if finished."""
    for _ in range(max_polls):
        state = job_status(job_id)
        if state in ("completed", "failed", "canceled"):
            return True
        time.sleep(poll_seconds)
    return False


def _view_file(file_path: str) -> str:
    """Fetch a remote file's contents via the IRI filesystem API.

    Filesystem operations are async: submitting a view returns a task_id,
    which we poll until it leaves the pending/active states.
    """
    import requests
    token = _load_token()
    response = requests.get(
        f"{BASE_URL}/filesystem/view/{AURORA_FILESYSTEM_RESOURCE_ID}",
        params={"path": file_path, "size": 1_000_000, "offset": 0},
        headers=_headers(token),
    )
    response.raise_for_status()
    task_id = response.json().get("task_id")
    if not task_id:
        return ""

    for _ in range(30):
        time.sleep(2)
        task = requests.get(f"{BASE_URL}/task/{task_id}", headers=_headers(token)).json()
        if task.get("status") not in ("pending", "active"):
            result = task.get("result")
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return result.get("content") or result.get("data") or ""
            return ""
    return ""


def parse_result_row(stdout_path: str, target_flops: str, depth: int) -> "dict | None":
    """Fetch the remote stdout log via the IRI filesystem API and parse it into a
    results.csv-shaped row. Mirrors aurora_job_helpers.parse_result_row's regexes
    since both run the exact same base_train.py invocation."""
    text = _view_file(stdout_path)
    if not text:
        return None

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
