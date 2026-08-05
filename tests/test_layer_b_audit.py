"""Regression tests for Layer B audit invariants and generated redesign data."""

from pathlib import Path

import pandas as pd

from layer_b_audit_utils import GOLD_PATH, RESULTS_DIR, history_features


def test_historical_pairs_are_complete_and_entity_separated():
    df = pd.read_csv(GOLD_PATH, parse_dates=["index_date", "outcome_date"])
    assert not df.company_key.duplicated().any()
    pairs = df.groupby("matched_positive_company").is_unicorn.agg(["count", "sum"])
    assert (pairs["count"] == 2).all()
    assert (pairs["sum"] == 1).all()
    controls = df[df.is_unicorn == 0]
    matched_outcomes = df[df.is_unicorn == 1].set_index("company").outcome_date
    assert (controls.index_date.to_numpy() == controls.matched_positive_company.map(matched_outcomes).to_numpy()).all()


def test_history_features_never_use_as_of_or_future_rounds():
    as_of = pd.Timestamp("2020-01-15")
    rounds = pd.DataFrame({
        "company_key": ["a", "a", "a"],
        "event_date": pd.to_datetime(["2020-01-01", "2020-01-15", "2020-02-01"]),
        "round_value_usd": [1_000_000, 9_000_000, 20_000_000],
        "Buyers/Investors": ["One LP", "Two LP", "Three LP"],
        "investor_count": [1, 1, 1],
    })
    features = history_features(rounds, "a", as_of)
    assert features["pre_round_count"] == 1
    assert features["pre_funding_total_usd"] == 1_000_000
    assert features["max_feature_round_date"] < as_of


def test_fixed_horizon_labels_have_strict_feature_cutoff_and_explicit_proxy():
    snapshots = pd.read_csv(
        RESULTS_DIR / "fixed_horizon_2y_snapshots.csv",
        parse_dates=["landmark_date", "max_feature_round_date", "horizon_end_date"],
    )
    used = snapshots.max_feature_round_date.notna()
    assert (snapshots.loc[used, "max_feature_round_date"] < snapshots.loc[used, "landmark_date"]).all()
    negatives = snapshots[snapshots.is_unicorn_within_horizon == 0]
    assert (negatives.label_basis == "no_known_event_plus_later_sub_1b_round_proxy").all()


def test_generated_audit_outputs_include_required_result_families():
    required = [
        "leakage_ablation_baseline_metrics.csv",
        "matched_pair_balance_numeric.csv",
        "fixed_horizon_evaluation.csv",
        "strict_negative_cohort_sensitivity.csv",
        "chronological_calibration_metrics.csv",
        "forward_cohort_robustness.csv",
        "exploratory_survival_metrics.json",
    ]
    for name in required:
        assert (RESULTS_DIR / name).exists(), name
