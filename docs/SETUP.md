# Setup

## Laptop (everyone — required for the core exercise)

Any machine with Python 3.10+. No GPU, no network access needed once the
repo is cloned (the dataset is bundled in `data/results.csv`).

```bash
git clone <this-repo-url>
cd A5-scaling-laws
pip install -e .          # or: uv sync
jupyter notebook notebooks/01_scaling_analysis.ipynb
```

Run all cells top to bottom. If anything errors, check your Python version
(`python3 --version`, need 3.10+) and that `pip install -e .` completed
without errors.

## Aurora (optional — only needed for section 8's bonus run)

Section 8 of `01_scaling_analysis.ipynb` submits one real training job
targeting Aurora's `GenesisHackathonOct26` hackathon reservation (queue
`R8914313`). There are two ways to do this — pick whichever matches your
setup.

### Option A: PBS (`qsub`), from an Aurora login node

- An Aurora (ALCF) account authorized for the `GenesisHackathonOct26`
  reservation and allocation.
- This repo cloned on an Aurora login node, alongside the vendored
  `nanochat` fork:

```bash
ssh <your-aurora-login>
cd ~/proj
git clone --recurse-submodules <this-repo-url> A5-scaling-laws
cd A5-scaling-laws
git submodule update --init   # if you skipped --recurse-submodules above
```

- `nanochat`'s dependencies installed in a `.venv` under the `nanochat/`
  submodule directory (see that project's own README for `uv sync --extra
  xpu`, or whichever extra matches your environment).

Open `01_scaling_analysis.ipynb` from a Jupyter session running on the
Aurora login node (or a compute node), set `METHOD = "pbs"` in section 8,
and run those cells. It submits to the hackathon reservation (1 node, ≤55
min walltime), polls for a bounded time, and falls back to a stored
example point if the job hasn't finished yet — it will not hang
indefinitely.

### Option B: IRI API, from anywhere (including your laptop)

The [DOE IRI Facility API](https://github.com/doe-iri/iri-facility-api-examples/tree/main/genesis_hackathon)
lets you submit the same job over HTTPS, without needing an interactive
Aurora session.

- Install the optional extra: `pip install -e .[iri]` (or `uv sync --extra
  iri`).
- Mint an ALCF IRI token:

```bash
pip install alcf-tokens
alcf-tokens login iri
alcf-tokens get-token iri
```

- Set `IRI_TOKEN_ALCF` to that token, either in your shell environment or
  in a `.env` file at the repo root (never commit this file — it's
  gitignored).

In section 8, set `METHOD = "iri"` and `ALCF_USERNAME` to your ALCF
username, then run those cells. Same polling/fallback behavior as the PBS
path.

**If you don't have Aurora access or an IRI token:** skip section 8
entirely. Nothing in the core exercise (sections 1–7) depends on it.
