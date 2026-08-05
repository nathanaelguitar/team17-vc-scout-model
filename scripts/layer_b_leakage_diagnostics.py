#!/usr/bin/env python3
"""Run leakage, artifact, ablation, baseline, and pair-balance diagnostics.

This script deliberately evaluates the historical matched-pair target as it
was constructed.  It does not claim that this target is a forward-looking
unicorn probability.  Results are written under ``analysis/layer_b_audit``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from layer_b_audit_utils import (
    FIGURES_DIR,
    RESULTS_DIR,
    RNG,
    classification_metrics,
    ensure_output_dirs,
    load_original_gold,
    load_source_rounds,
)


TARGET = "is_unicorn"
GROUP = "matched_positive_company"
BASE_NUMERIC = [
    "index_year", "pre_round_count", "has_pre_round", "pre_rounds_with_amount",
    "ln_pre_funding", "ln_pre_funding_max", "pre_last_post_money_usd",
    "pre_max_post_money_usd", "pre_unique_investor_count", "pre_investor_count_max",
    "years_of_history_pre", "days_since_last_pre_round", "founded_year", "has_founded_year",
]
BASE_CATEGORICAL = ["industry_group", "continent", "country"]
TIMING_AND_MOMENTUM = [
    "index_year", "pre_round_count", "has_pre_round", "pre_rounds_with_amount",
    "ln_pre_funding", "ln_pre_funding_max", "pre_last_post_money_usd",
    "pre_max_post_money_usd", "pre_unique_investor_count", "pre_investor_count_max",
    "years_of_history_pre", "days_since_last_pre_round",
]
COMPANY_CHARACTERISTICS = ["founded_year", "has_founded_year", "industry_group", "continent", "country"]
FUNDING_HISTORY = [field for field in TIMING_AND_MOMENTUM if field != "index_year"]


def _preprocess(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    transformers = []
    if numeric:
        transformers.append(("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric))
    if categorical:
        transformers.append(("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical))
    return ColumnTransformer(transformers)


def model_for(kind: str, numeric: list[str], categorical: list[str]) -> Pipeline:
    if kind == "random_forest":
        estimator = RandomForestClassifier(
            n_estimators=500, max_depth=7, min_samples_leaf=5, max_features=0.7,
            class_weight="balanced", random_state=RNG, n_jobs=-1,
        )
    elif kind == "logistic":
        estimator = LogisticRegression(max_iter=4000, class_weight="balanced", C=1e6, random_state=RNG)
    elif kind == "regularized_logistic":
        estimator = LogisticRegression(max_iter=4000, class_weight="balanced", C=0.5, random_state=RNG)
    elif kind == "shallow_tree":
        estimator = DecisionTreeClassifier(max_depth=2, min_samples_leaf=25, class_weight="balanced", random_state=RNG)
    else:
        raise ValueError(kind)
    return Pipeline([("preprocess", _preprocess(numeric, categorical)), ("model", estimator)])


def split_forward(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    train = df["index_year"] < 2024
    test = ~train
    if not train.any() or not test.any():
        raise ValueError("Expected 2024+ chronological test rows")
    return train, test


def evaluate(
    df: pd.DataFrame, name: str, numeric: list[str], categorical: list[str], kind: str = "random_forest",
    training_labels: pd.Series | None = None,
) -> tuple[dict, np.ndarray]:
    train, test = split_forward(df)
    features = numeric + categorical
    pipeline = model_for(kind, numeric, categorical)
    y_train = df.loc[train, TARGET] if training_labels is None else training_labels.loc[train]
    pipeline.fit(df.loc[train, features], y_train)
    probability = pipeline.predict_proba(df.loc[test, features])[:, 1]
    row = {
        "diagnostic": name,
        "model": kind,
        "feature_count": len(features),
        "features": "|".join(features),
        "train_rows": int(train.sum()),
        "test_rows": int(test.sum()),
        **classification_metrics(df.loc[test, TARGET], probability),
    }
    return row, probability


def make_diagnostic_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # These use only fields already present in the historical construction.
    # ``no_observed_pre_round`` is a source-history absence proxy, not evidence
    # that the company had no financing before its index date.
    out["missing_max_feature_round_date"] = out["max_feature_round_date"].isna().astype(int)
    out["missing_founding_date"] = (out["has_founded_year"] == 0).astype(int)
    out["unmatched_master_record"] = (out["master_match_status"] == "unmatched").astype(int)
    out["ambiguous_master_record"] = (out["master_match_status"] == "ambiguous").astype(int)
    out["no_observed_pre_round"] = (out["has_pre_round"] == 0).astype(int)
    return out


def permute_within_pairs(df: pd.DataFrame, field: str) -> pd.DataFrame:
    out = df.copy()
    rng = np.random.default_rng(RNG)
    for _, index in out.groupby(GROUP).groups.items():
        values = out.loc[index, field].to_numpy(copy=True)
        out.loc[index, field] = rng.permutation(values)
    return out


def smd(a: pd.Series, b: pd.Series) -> float:
    a, b = pd.to_numeric(a, errors="coerce").dropna(), pd.to_numeric(b, errors="coerce").dropna()
    if not len(a) or not len(b):
        return float("nan")
    denominator = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return float((a.mean() - b.mean()) / denominator) if denominator else 0.0


def balance_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    positives, controls = df[df[TARGET] == 1], df[df[TARGET] == 0]
    numeric = [
        "index_year", "founded_year", "pre_round_count", "years_of_history_pre",
        "days_since_last_pre_round", "pre_funding_total_usd", "pre_funding_max_usd",
        "pre_unique_investor_count", "pre_investor_count_max", "has_founded_year",
    ]
    table = []
    for column in numeric:
        table.append({
            "variable": column,
            "positive_n": int(positives[column].notna().sum()),
            "control_n": int(controls[column].notna().sum()),
            "positive_mean": float(positives[column].mean()),
            "control_mean": float(controls[column].mean()),
            "positive_median": float(positives[column].median()),
            "control_median": float(controls[column].median()),
            "standardized_mean_difference": smd(positives[column], controls[column]),
        })
    categories = []
    for column in ["industry_group", "continent", "country", "master_match_status"]:
        levels = sorted(set(positives[column].fillna("<missing>")) | set(controls[column].fillna("<missing>")))
        for level in levels:
            p = (positives[column].fillna("<missing>") == level).mean()
            c = (controls[column].fillna("<missing>") == level).mean()
            denom = np.sqrt((p * (1 - p) + c * (1 - c)) / 2)
            categories.append({
                "variable": column,
                "level": level,
                "positive_fraction": float(p),
                "control_fraction": float(c),
                "standardized_difference": float((p - c) / denom) if denom else 0.0,
            })
    return pd.DataFrame(table), pd.DataFrame(categories)


def pre_match_pool_balance(df: pd.DataFrame) -> pd.DataFrame:
    """Describe the available, unmatched control pool before selection.

    The pool has only each company's own last supplied sub-$1B date, whereas
    positives are indexed at their event date.  This is deliberately labelled
    as non-time-aligned: it is a source-pool audit, not causal balance proof.
    """
    rounds, _, first_events = load_source_rounds()
    event_keys = set(first_events.company_key)
    pool = rounds[~rounds.company_key.isin(event_keys)].copy()
    summary = pool.groupby("company_key").agg(
        index_year=("event_date", lambda x: x.max().year),
        pre_round_count=("event_date", "size"),
        years_of_history_pre=("event_date", lambda x: (x.max() - x.min()).days / 365.25),
        days_since_last_pre_round=("event_date", lambda x: 0.0),
        pre_funding_total_usd=("round_value_usd", lambda x: pd.to_numeric(x, errors="coerce").clip(lower=0).sum()),
        pre_funding_max_usd=("round_value_usd", lambda x: pd.to_numeric(x, errors="coerce").clip(lower=0).max()),
        pre_unique_investor_count=("investor_count", "max"),
        pre_investor_count_max=("investor_count", "max"),
    ).reset_index()
    positives = df[df.is_unicorn == 1]
    columns = [
        "index_year", "pre_round_count", "years_of_history_pre", "days_since_last_pre_round",
        "pre_funding_total_usd", "pre_funding_max_usd", "pre_unique_investor_count", "pre_investor_count_max",
    ]
    rows = []
    for column in columns:
        rows.append({
            "comparison_scope": "before_matching_available_pool_not_time_aligned",
            "variable": column, "positive_n": int(positives[column].notna().sum()),
            "control_pool_n": int(summary[column].notna().sum()), "positive_mean": float(positives[column].mean()),
            "control_pool_mean": float(summary[column].mean()), "positive_median": float(positives[column].median()),
            "control_pool_median": float(summary[column].median()),
            "standardized_mean_difference": smd(positives[column], summary[column]),
        })
    return pd.DataFrame(rows)


def source_audit(df: pd.DataFrame) -> dict:
    sub_billion, outcomes, first_events = load_source_rounds()
    overlap = set(sub_billion.company_key) & set(first_events.company_key)
    return {
        "historical_gold_rows": int(len(df)),
        "historical_positive_rows": int(df[TARGET].sum()),
        "historical_control_rows": int((df[TARGET] == 0).sum()),
        "historical_pair_groups": int(df[GROUP].nunique()),
        "gold_duplicate_company_keys": int(df.company_key.duplicated().sum()),
        "raw_sub_billion_round_rows": int(len(sub_billion)),
        "raw_sub_billion_companies": int(sub_billion.company_key.nunique()),
        "raw_ge_1b_round_rows": int(len(outcomes)),
        "raw_ge_1b_companies": int(first_events.company_key.nunique()),
        "companies_in_both_low_round_and_event_exports": int(len(overlap)),
        "latest_supplied_round_date": str(max(sub_billion.event_date.max(), outcomes.event_date.max()).date()),
        "control_index_uses_matched_positive_outcome_date": True,
        "note": (
            "The low-valuation extract does not supply operating status, closure, coverage dates, "
            "or a complete valuation history; absence of a >=$1B row is not a verified non-event."
        ),
    }


def plot_ablation(results: pd.DataFrame) -> None:
    plot = results[results["model"] == "random_forest"].sort_values("roc_auc")
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(plot["diagnostic"], plot["roc_auc"], color="#2f6f9f")
    ax.set_xlim(0, 1.03)
    ax.set_xlabel("Forward-test ROC-AUC (index year ≥ 2024)")
    ax.set_title("Layer B historical-target leakage and ablation diagnostics")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "forward_ablation_roc_auc.png", dpi=220)
    plt.close(fig)


def main() -> None:
    ensure_output_dirs()
    original = load_original_gold()
    df = make_diagnostic_frame(original)
    missingness = [
        "missing_max_feature_round_date", "missing_founding_date", "unmatched_master_record",
        "ambiguous_master_record", "no_observed_pre_round",
    ]
    all_features = BASE_NUMERIC + BASE_CATEGORICAL
    specs = [
        ("all_current_features", BASE_NUMERIC, BASE_CATEGORICAL, "random_forest"),
        ("remove_days_since_last_pre_round", [x for x in BASE_NUMERIC if x != "days_since_last_pre_round"], BASE_CATEGORICAL, "random_forest"),
        ("remove_timing_and_funding_momentum", [x for x in BASE_NUMERIC if x not in TIMING_AND_MOMENTUM], BASE_CATEGORICAL, "random_forest"),
        ("company_characteristics_only", ["founded_year", "has_founded_year"], BASE_CATEGORICAL, "random_forest"),
        ("funding_history_only", FUNDING_HISTORY, [], "random_forest"),
        ("matching_variables_only_DIAGNOSTIC", ["match_gap_days"], ["match_method"], "random_forest"),
        ("missingness_indicators_only", missingness, [], "random_forest"),
        ("remove_company_metadata_family", [x for x in BASE_NUMERIC if x not in {"founded_year", "has_founded_year"}], [], "random_forest"),
        ("remove_funding_history_family", [x for x in BASE_NUMERIC if x not in FUNDING_HISTORY], BASE_CATEGORICAL, "random_forest"),
        ("logistic_regression", BASE_NUMERIC, BASE_CATEGORICAL, "logistic"),
        ("regularized_logistic_regression", BASE_NUMERIC, BASE_CATEGORICAL, "regularized_logistic"),
        ("shallow_decision_tree", BASE_NUMERIC, BASE_CATEGORICAL, "shallow_tree"),
        ("single_strongest_feature_days_since_last_pre_round", ["days_since_last_pre_round"], [], "random_forest"),
    ]
    rows = []
    predictions = []
    for name, numeric, categorical, kind in specs:
        row, probability = evaluate(df, name, numeric, categorical, kind)
        rows.append(row)
        test = df.index_year >= 2024
        predictions.append(pd.DataFrame({
            "diagnostic": name, "company_key": df.loc[test, "company_key"],
            "is_unicorn": df.loc[test, TARGET], "probability": probability,
        }))

    # A transparent, non-fitted rule: no observed pre-index low-valuation
    # round scores highest; otherwise recency decays over one year.  This is
    # intentionally included because it tests the extraction artifact itself.
    train, test = split_forward(df)
    days = df.loc[test, "days_since_last_pre_round"].to_numpy(float)
    simple_rule = np.where(days < 0, 0.95, 0.50 * np.exp(-days / 365.25))
    rows.append({
        "diagnostic": "simple_observed_funding_recency_rule", "model": "fixed_rule",
        "feature_count": 1, "features": "days_since_last_pre_round + no_observed_pre_round",
        "train_rows": int(train.sum()), "test_rows": int(test.sum()),
        **classification_metrics(df.loc[test, TARGET], simple_rule),
    })
    prevalence_probability = np.repeat(float(df.loc[train, TARGET].mean()), int(test.sum()))
    rows.append({
        "diagnostic": "training_prevalence_only_baseline", "model": "fixed_prevalence",
        "feature_count": 0, "features": "none",
        "train_rows": int(train.sum()), "test_rows": int(test.sum()),
        **classification_metrics(df.loc[test, TARGET], prevalence_probability),
    })

    permuted = permute_within_pairs(df, "days_since_last_pre_round")
    row, probability = evaluate(permuted, "permute_top_feature_within_matched_pair", BASE_NUMERIC, BASE_CATEGORICAL)
    rows.append(row)
    rng = np.random.default_rng(RNG)
    labels = df[TARGET].copy()
    labels.loc[train] = rng.permutation(labels.loc[train].to_numpy())
    row, probability = evaluate(df, "permuted_training_labels_negative_control", BASE_NUMERIC, BASE_CATEGORICAL, training_labels=labels)
    rows.append(row)

    results = pd.DataFrame(rows)
    results.to_csv(RESULTS_DIR / "leakage_ablation_baseline_metrics.csv", index=False)
    pd.concat(predictions, ignore_index=True).to_csv(RESULTS_DIR / "diagnostic_forward_predictions.csv", index=False)
    balance_numeric, balance_categorical = balance_tables(df)
    balance_numeric.to_csv(RESULTS_DIR / "matched_pair_balance_numeric.csv", index=False)
    balance_categorical.to_csv(RESULTS_DIR / "matched_pair_balance_categorical.csv", index=False)
    pre_match_pool_balance(df).to_csv(RESULTS_DIR / "pre_match_available_pool_balance_numeric.csv", index=False)
    missing_summary = df.groupby(TARGET)[missingness + ["has_pre_round", "days_since_last_pre_round"]].agg(["mean", "sum", "count"])
    missing_summary.to_csv(RESULTS_DIR / "missingness_by_label.csv")
    (RESULTS_DIR / "source_and_construction_audit.json").write_text(json.dumps(source_audit(df), indent=2) + "\n")
    plot_ablation(results)
    print(results[["diagnostic", "model", "roc_auc", "pr_auc", "precision", "recall", "specificity", "f1", "brier_score", "log_loss", "calibration_slope"]].to_string(index=False))


if __name__ == "__main__":
    main()
