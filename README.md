# A5 Scaling Laws — Hands-On Materials

Hands-on companion to the "A5: Scaling Laws" talk. Analyze 24 real IsoFLOP
training runs, fit and test a scaling-law prediction, and turn it into a
concrete recommendation for what to train next — all on a laptop, no GPU
required.

## Quickstart

```bash
pip install -e .
jupyter notebook notebooks/01_scaling_analysis.ipynb
```

or with `uv`:

```bash
uv sync
uv run jupyter notebook notebooks/01_scaling_analysis.ipynb
```

That's it — `01_scaling_analysis.ipynb` loads the bundled dataset and runs
entirely offline.

## Repo map

```
data/
  results.csv                — 24 real training runs, 4 FLOPs budgets (the core dataset)
  bonus_fallback_point.csv   — stored example used by the optional bonus section
scaling_lib/core.py          — the scaling-law analysis functions (load, select, fit, recommend)
notebooks/
  01_scaling_analysis.ipynb    — the hands-on exercise, including an optional live-run section
scripts/                     — Aurora PBS script + IRI API client + job-polling helpers (bonus-only)
nanochat/                    — git submodule, only needed for the bonus section
docs/
  SETUP.md       — laptop and Aurora setup instructions
  FACILITATOR.md — 75-minute run-of-show for facilitators
```

## Two paths through this repo

**Everyone:** sections 1–7 of `notebooks/01_scaling_analysis.ipynb`.
Self-contained, no dependencies beyond the Python packages in
`pyproject.toml`, runs on any laptop.

**Optional, Aurora-access only:** section 8 of the same notebook. Submits
one real training run targeting the `GenesisHackathonOct26` hackathon
reservation on Aurora — either via `qsub` from an Aurora login node, or via
the [DOE IRI Facility API](https://github.com/doe-iri/iri-facility-api-examples/tree/main/genesis_hackathon)
from anywhere with network access — and folds the result into the same
analysis. If you don't have Aurora access, or your job doesn't finish in
time, it falls back to a stored example point automatically — it never
blocks the core exercise.

To use the PBS path, first pull in the vendored nanochat fork:

```bash
git submodule update --init
```

To use the IRI API path instead, install the optional `iri` extra
(`pip install -e .[iri]` or `uv sync --extra iri`) and set up an ALCF IRI
token as described in the IRI repo's README.

See `docs/SETUP.md` for details on both paths.

## Where this data comes from

`data/results.csv` is real training data: 24 runs of a small transformer
(nanochat) at various depths, swept across 4 FLOPs budgets
(1e17/2e17/4e17/6e17), trained on Aurora (ALCF). `scaling_lib/core.py`
reproduces the exact analysis shown in the talk — fitting a power law to
the best run at each budget, testing it against a held-out budget, and
building a per-budget "what should we train next" table.
