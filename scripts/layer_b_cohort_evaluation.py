#!/usr/bin/env python3
"""Chronological cohort robustness report with bootstrap AUC intervals."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from layer_b_audit_utils import RESULTS_DIR, classification_metrics, ensure_output_dirs, load_original_gold
from layer_b_leakage_diagnostics import BASE_CATEGORICAL, BASE_NUMERIC, model_for


def bootstrap_auc(y: np.ndarray, p: np.ndarray, seed: int = 17, draws: int = 300) -> tuple[float, float]:
    if len(y) < 30 or len(np.unique(y)) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        ix = rng.integers(0, len(y), len(y))
        if len(np.unique(y[ix])) == 2:
            values.append(roc_auc_score(y[ix], p[ix]))
    return tuple(np.quantile(values, [0.025, 0.975])) if values else (float("nan"), float("nan"))


def main() -> None:
    ensure_output_dirs()
    df = load_original_gold()
    train, test = df.index_year < 2024, df.index_year >= 2024
    features = BASE_NUMERIC + BASE_CATEGORICAL
    model = model_for("random_forest", BASE_NUMERIC, BASE_CATEGORICAL)
    model.fit(df.loc[train, features], df.loc[train, "is_unicorn"])
    scored = df.loc[test].copy()
    scored["probability"] = model.predict_proba(scored[features])[:, 1]
    scored["founding_year_cohort"] = pd.cut(
        scored.founded_year.where(scored.has_founded_year == 1),
        bins=[1900, 2009, 2014, 2018, 2021, 2100], labels=["≤2009", "2010-14", "2015-18", "2019-21", "2022+"],
    ).astype(str).replace("nan", "missing")
    scored["funding_stage_proxy"] = pd.cut(
        scored.pre_round_count, bins=[-1, 0, 1, 2, 999], labels=["0", "1", "2", "3+"]
    ).astype(str)
    scored["total_funding_bucket"] = pd.qcut(
        scored.pre_funding_total_usd.rank(method="first"), q=4, labels=["Q1", "Q2", "Q3", "Q4"]
    ).astype(str)
    scored["company_age_proxy"] = pd.cut(
        scored.years_of_history_pre, bins=[-0.01, 0, 1, 3, 7, np.inf], labels=["0", "0-1", "1-3", "3-7", "7+"]
    ).astype(str)
    scored["data_completeness"] = np.select(
        [
            (scored.has_pre_round == 1) & (scored.has_founded_year == 1) & (scored.master_match_status == "exact_unique"),
            (scored.has_pre_round == 1),
        ], ["round+founding+master", "round_history_only"], default="limited_source_metadata",
    )
    scored["economic_period"] = np.where(scored.index_year <= 2024, "2024", "2025-2026")
    mapping = {
        "prediction_year": "index_year", "founding_year_cohort": "founding_year_cohort", "industry": "industry_group",
        "geography": "continent", "funding_stage_proxy": "funding_stage_proxy", "company_age_proxy": "company_age_proxy",
        "prior_round_count": "funding_stage_proxy", "total_funding_bucket": "total_funding_bucket",
        "data_completeness": "data_completeness", "economic_period": "economic_period",
    }
    rows = []
    for dimension, column in mapping.items():
        for cohort, subset in scored.groupby(column, dropna=False):
            y, p = subset.is_unicorn.to_numpy(int), subset.probability.to_numpy(float)
            if len(y) < 20 or len(np.unique(y)) < 2:
                rows.append({"dimension": dimension, "cohort": str(cohort), "rows": len(y), "status": "too_small_or_single_class"})
                continue
            low, high = bootstrap_auc(y, p, seed=17 + len(rows))
            rows.append({
                "dimension": dimension, "cohort": str(cohort), "rows": len(y),
                "positive_rows": int(y.sum()), "negative_rows": int((y == 0).sum()), "status": "evaluated",
                **classification_metrics(y, p), "roc_auc_ci_95_low": low, "roc_auc_ci_95_high": high,
            })
    results = pd.DataFrame(rows)
    results.to_csv(RESULTS_DIR / "forward_cohort_robustness.csv", index=False)
    scored.to_csv(RESULTS_DIR / "forward_scored_rows_for_cohort_analysis.csv", index=False)
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
