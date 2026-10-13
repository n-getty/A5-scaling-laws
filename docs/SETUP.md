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

## Aurora (optional — only needed for the bonus notebook)

The bonus notebook (`02_live_training_bonus.ipynb`) submits a real training
job to Aurora's `debug` PBS queue. You need:

- An Aurora (ALCF) account with access to the **ModCon** project allocation
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

Then open `notebooks/02_live_training_bonus.ipynb` from a Jupyter session
running on the Aurora login node (or a compute node) and run all cells. The
notebook submits to the `debug` queue (1 node, ≤55 min walltime, billed to
`ModCon`), polls for a bounded time, and falls back to a stored example
point if the job hasn't finished yet — it will not hang indefinitely.

**If you don't have Aurora access:** skip this notebook entirely. Nothing
in the core exercise depends on it.
