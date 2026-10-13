"""Scaling-law analysis helpers shared by the workshop notebooks.

Ported from bpsw-mt-scaling/hackathon/figures/data_utils.py and generalized
to accept any results dataframe (not just the bundled CSV), so the same
functions work on the default dataset (Path A) and on a participant's own
data (Path B) or a live Aurora run appended via the bonus notebook.
"""
from pathlib import Path

import numpy as np
import pandas as pd

VOCAB_SIZE = 32768
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "results.csv"


def compute_effective_params(df: pd.DataFrame, vocab_size: int = VOCAB_SIZE) -> pd.DataFrame:
    """Add effective_params and total_flops columns in place.

    effective_params = transformer params + the embedding/lm_head contribution
    (model_dim * vocab_size), matching the convention used to produce
    results.csv. total_flops uses the standard C = 6ND approximation.
    """
    df["effective_params"] = (df["params_transformer"] + df["model_dim"] * vocab_size).astype(float)
    df["total_flops"] = 6.0 * df["effective_params"] * df["tokens_trained"].astype(float)
    return df


def load_raw(path: "str | Path | None" = None) -> pd.DataFrame:
    """Load a results CSV and compute derived columns.

    Defaults to the bundled data/results.csv (24 runs x 4 FLOPs budgets).
    Pass a different path to load your own data (Path B exercise) as long
    as it has the same columns: flops_budget, depth, model_dim,
    params_transformer, tokens_trained, val_bpb.
    """
    df = pd.read_csv(path or DEFAULT_DATA_PATH)
    return compute_effective_params(df)


def best_per_budget(df: pd.DataFrame) -> pd.DataFrame:
    """Lowest val_bpb run within each FLOPs budget (the 'best observed' frontier)."""
    idx = df.groupby("flops_budget")["val_bpb"].idxmin()
    return df.loc[idx].sort_values("flops_budget").reset_index(drop=True)


def fit_power_law(x: np.ndarray, y: np.ndarray):
    """Fit y = a * x^b in log-log space. Returns (b, a)."""
    log_x, log_y = np.log10(x), np.log10(y)
    slope, intercept = np.polyfit(log_x, log_y, 1)
    return slope, 10 ** intercept


def quad_fit_min(log_x: np.ndarray, y: np.ndarray):
    """Fit a quadratic in log-x space, return (coeffs, x_min, y_min) if it has an
    interior minimum (positive curvature, vertex inside the observed range)."""
    a, b, c = np.polyfit(log_x, y, 2)
    if a <= 0:
        return (a, b, c), None, None
    log_x_min = -b / (2 * a)
    if not (log_x.min() <= log_x_min <= log_x.max()):
        return (a, b, c), None, None
    x_min = 10 ** log_x_min
    y_min = a * log_x_min ** 2 + b * log_x_min + c
    return (a, b, c), x_min, y_min


def allocation_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per-budget 'what should we train next' table.

    For each FLOPs budget, reports the best-observed effective parameter
    count, tokens trained, val_bpb, how many model sizes were tested at
    that budget, and whether the winner sits at the edge of the tested
    size range (a signal that the sweep should be widened before trusting
    any size-vs-budget trend).
    """
    winners = best_per_budget(df)
    stats = df.groupby("flops_budget")["effective_params"].agg(["min", "max", "count"])

    rows = []
    for _, row in winners.iterrows():
        budget_stats = stats.loc[row["flops_budget"]]
        n_tested = int(budget_stats["count"])
        if row["effective_params"] <= budget_stats["min"]:
            range_position = f"min of {n_tested}"
        elif row["effective_params"] >= budget_stats["max"]:
            range_position = f"max of {n_tested}"
        else:
            range_position = "interior"
        rows.append(
            {
                "flops_budget": row["flops_budget"],
                "effective_params": row["effective_params"],
                "tokens_trained": row["tokens_trained"],
                "val_bpb": row["val_bpb"],
                "n_tested": n_tested,
                "range_position": range_position,
            }
        )
    return pd.DataFrame(rows)
