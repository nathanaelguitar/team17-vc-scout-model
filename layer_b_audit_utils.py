"""Shared, reproducible utilities for the Layer B audit.

The existing classifier table is intentionally retained as the *historical
construction* being audited.  These helpers do not alter it.  They expose the
source-round history and consistent metrics for the separate audit scripts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from capitaliq_time_etl import (
    CONTROL_RAW_PATH,
    CONTROL_SLICE_GLOB,
    ONE_BILLION_USD,
    POSITIVE_PATH,
    RAW_DIR,
    canonical_name,
    read_capitaliq,
)


ROOT = Path(__file__).resolve().parent
AUDIT_DIR = ROOT / "analysis" / "layer_b_audit"
RESULTS_DIR = AUDIT_DIR / "results"
FIGURES_DIR = AUDIT_DIR / "figures"
GOLD_PATH = ROOT / "data" / "gold" / "capitaliq_classifier_time_safe.csv"
RNG = 17


def ensure_output_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def load_original_gold() -> pd.DataFrame:
    """Load the unmodified historical matched-pair classifier table."""

    return pd.read_csv(
        GOLD_PATH,
        parse_dates=["index_date", "outcome_date", "max_feature_round_date"],
        low_memory=False,
    )


def load_source_rounds() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load raw Capital IQ exports, preserving their extraction limitations.

    Returns all normalized sub-$1B transaction rows, all >=$1B outcome rows,
    and a company-level first-outcome table.  A company in the low-valuation
    extract is *not* automatically a known non-event company; callers must
    explicitly choose and report a follow-up proxy.
    """

    positive_raw = read_capitaliq(POSITIVE_PATH, "positive_export")
    control_paths = [CONTROL_RAW_PATH] + sorted(RAW_DIR.glob(CONTROL_SLICE_GLOB))
    control_raw = pd.concat(
        [
            read_capitaliq(
                path,
                "control_export_raw" if path == CONTROL_RAW_PATH else "control_date_slice",
            )
            for path in control_paths
        ],
        ignore_index=True,
        sort=False,
    ).drop_duplicates(subset=["transaction_id"], keep="first")

    outcomes = positive_raw[positive_raw["post_money_usd"] >= ONE_BILLION_USD].copy()
    outcomes = outcomes.sort_values(["company_key", "event_date", "transaction_id"])
    first_events = (
        outcomes.groupby("company_key", as_index=False)
        .agg(
            company=("company_name", "first"),
            outcome_date=("event_date", "first"),
            outcome_transaction_id=("transaction_id", "first"),
        )
    )
    sub_billion = control_raw[
        control_raw["post_money_usd"].notna()
        & (control_raw["post_money_usd"] < ONE_BILLION_USD)
    ].copy()
    # CIQ transaction IDs are stable within the supplied extracts.  Retain one
    # row if a date partition overlaps the original capped extract.
    sub_billion = sub_billion.drop_duplicates(subset=["transaction_id"], keep="first")
    return sub_billion.reset_index(drop=True), outcomes.reset_index(drop=True), first_events


def history_features(rounds: pd.DataFrame, company_key: str, as_of: pd.Timestamp) -> dict[str, float]:
    """Features using only rows strictly before ``as_of``."""

    history = rounds[
        (rounds["company_key"] == company_key) & (rounds["event_date"] < as_of)
    ].sort_values("event_date")
    if history.empty:
        return {
            "pre_round_count": 0,
            "pre_rounds_with_amount": 0,
            "pre_funding_total_usd": 0.0,
            "pre_funding_max_usd": 0.0,
            "pre_unique_investor_count": 0,
            "pre_investor_count_max": 0,
            "years_of_history_pre": 0.0,
            "days_since_last_pre_round": -1.0,
            "max_feature_round_date": pd.NaT,
        }
    amounts = pd.to_numeric(history["round_value_usd"], errors="coerce")
    positive_amounts = amounts[amounts > 0]
    investors: set[str] = set()
    for value in history["Buyers/Investors"].fillna(""):
        investors.update(
            key for key in (canonical_name(item) for item in str(value).split(";")) if key
        )
    first_date, last_date = history["event_date"].iloc[0], history["event_date"].iloc[-1]
    return {
        "pre_round_count": float(len(history)),
        "pre_rounds_with_amount": float((amounts > 0).sum()),
        "pre_funding_total_usd": float(positive_amounts.sum()) if len(positive_amounts) else 0.0,
        "pre_funding_max_usd": float(positive_amounts.max()) if len(positive_amounts) else 0.0,
        "pre_unique_investor_count": float(len(investors)),
        "pre_investor_count_max": float(history["investor_count"].max()),
        "years_of_history_pre": max((as_of - first_date).days / 365.25, 0.0),
        "days_since_last_pre_round": max(float((as_of - last_date).days), 0.0),
        "max_feature_round_date": last_date,
    }


def classification_metrics(y_true: Iterable[int], probability: Iterable[float]) -> dict[str, float]:
    """A common metric contract used across all audit outputs."""

    y = np.asarray(list(y_true), dtype=int)
    p = np.clip(np.asarray(list(probability), dtype=float), 1e-6, 1 - 1e-6)
    predicted = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    # Fit y ~ logit(p) on evaluation predictions.  These are descriptive
    # calibration diagnostics, not a calibration model fitted to this split.
    x = logit(p).reshape(-1, 1)
    try:
        calibration = LogisticRegression(C=1e6, max_iter=2000).fit(x, y)
        calibration_intercept = float(calibration.intercept_[0])
        calibration_slope = float(calibration.coef_[0, 0])
    except ValueError:
        calibration_intercept = float("nan")
        calibration_slope = float("nan")
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else float("nan"),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "brier_score": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "calibration_intercept": calibration_intercept,
        "calibration_slope": calibration_slope,
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def screening_metrics(y_true: Iterable[int], probability: Iterable[float], buckets=(0.01, 0.05, 0.10, 0.20)) -> pd.DataFrame:
    y = np.asarray(list(y_true), dtype=int)
    p = np.asarray(list(probability), dtype=float)
    order = np.argsort(-p, kind="stable")
    base_rate = y.mean()
    rows = []
    for bucket in buckets:
        n = max(1, int(np.ceil(len(y) * bucket)))
        selected = y[order[:n]]
        precision = selected.mean()
        rows.append(
            {
                "screening_bucket": bucket,
                "companies_screened": n,
                "positives_found": int(selected.sum()),
                "precision": float(precision),
                "recall_captured": float(selected.sum() / y.sum()) if y.sum() else float("nan"),
                "lift_over_base_rate": float(precision / base_rate) if base_rate else float("nan"),
                "number_needed_to_screen": float(1 / precision) if precision else float("inf"),
            }
        )
    return pd.DataFrame(rows)
