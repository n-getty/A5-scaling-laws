# Facilitator guide — 75-minute run of show

Target: a large, mixed-experience audience, mostly on their own laptops.

| Time | Segment | Notes |
|---|---|---|
| 0:00–0:10 | Intro & framing | Recap the talk's motivation: fixed compute budget, model size vs. training duration trade-off. Point out `01_scaling_analysis.ipynb` needs no GPU and runs on any laptop. |
| 0:10–0:45 | Guided walkthrough (sections 1–4) | Walk through Load→Check→Select→Plot, the four-budget fit, the held-out-budget check, and the allocation table together. Pause after the holdout check (section 3) — the real result is a ~0.06% relative error, a good moment to ask "would this change what you'd train next?" |
| 0:45–1:05 | Exercise, Path A or B | Let people choose: Path A (reproduce with a different holdout) is more guided; Path B (apply the same functions to new/toy data) is more open-ended. Facilitators circulate; solution cells are provided for Path A. |
| 1:05–1:15 | Optional bonus kickoff | For anyone with Aurora access or an IRI token: point them at section 8 of `01_scaling_analysis.ipynb` and `docs/SETUP.md`. Submitting is a single cell (`METHOD = "pbs"` or `"iri"`); don't wait on it live — it polls in the background and falls back gracefully if it's not done by the time the session ends. |
| 1:15–1:25 | Wrap-up & Q&A | Revisit the summary table at the end of notebook 1. Emphasize the caveats: small number of budgets, no run-to-run variance estimate, no loss-floor term. |

## Common issues

- **`pip install -e .` fails / wrong Python version:** need 3.10+. `uv sync`
  is the more reliable fallback if participants have `uv` installed.
- **Notebook kernel can't find `scaling_lib`:** the notebooks add `..` to
  `sys.path` assuming they're run from `notebooks/` with the repo as the
  working directory root — if a participant moved the notebook file, this
  breaks. Re-clone instead of copying the single file.
- **Bonus submission fails:** for the PBS path, almost always missing
  access to the `GenesisHackathonOct26` reservation/allocation or the
  `nanochat` submodule not being initialized. For the IRI path, almost
  always a missing/expired `IRI_TOKEN_ALCF` or unset `ALCF_USERNAME`.
  Point them at `docs/SETUP.md`'s Aurora section, or just have them skip
  section 8 entirely.
