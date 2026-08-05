from __future__ import annotations

import pandas as pd
import pytest

from layer_b_v2_model import calibration_diagnostics, decision_metrics, temporal_partitions
from layer_b_v2_pipeline import DataContractError
from layer_b_v2_pipeline import build_snapshots, label_snapshots, make_features, read_export_manifest


def test_labels_require_coverage_for_negative_and_preserve_competing_outcome():
    snapshots = pd.DataFrame({
        "company_id": ["positive", "negative", "censored", "exit"],
        "prediction_date": pd.to_datetime(["2020-01-01"] * 4),
        "horizon_end": pd.to_datetime(["2023-01-01"] * 4),
        "coverage_start": pd.to_datetime(["2019-01-01", "2019-01-01", "2019-01-01", "2019-01-01"]),
        "coverage_end": pd.to_datetime(["2024-01-01", "2024-01-01", "2021-01-01", "2024-01-01"]),
    })
    transactions = pd.DataFrame({"company_id": ["positive"], "event_date": pd.to_datetime(["2022-01-01"]), "post_money_usd": [1_000_000_000.0]})
    valuations = pd.DataFrame(columns=["company_id", "valuation_date", "value_usd"])
    lifecycle = pd.DataFrame({"company_id": ["exit"], "event_date": pd.to_datetime(["2021-01-01"]), "event_type": ["Acquired"]})
    result = label_snapshots(snapshots, transactions, valuations, lifecycle).set_index("company_id")
    assert result.loc["positive", "label_state"] == "positive"
    assert result.loc["negative", "label_state"] == "negative"
    assert result.loc["censored", "label_state"] == "censored"
    assert result.loc["exit", "label_state"] == "competing"


def test_late_coverage_cannot_be_a_verified_negative():
    snapshots = pd.DataFrame({
        "company_id": ["late"], "prediction_date": pd.to_datetime(["2020-01-01"]),
        "horizon_end": pd.to_datetime(["2023-01-01"]),
        "coverage_start": pd.to_datetime(["2021-01-01"]), "coverage_end": pd.to_datetime(["2024-01-01"]),
    })
    empty_transactions = pd.DataFrame(columns=["company_id", "event_date", "post_money_usd"])
    empty_valuations = pd.DataFrame(columns=["company_id", "valuation_date", "value_usd"])
    empty_lifecycle = pd.DataFrame(columns=["company_id", "event_date", "event_type"])
    result = label_snapshots(snapshots, empty_transactions, empty_valuations, empty_lifecycle)
    assert result.loc[0, "label_state"] == "censored"


def test_snapshots_are_created_at_second_private_financing_only():
    companies = pd.DataFrame({
        "company_id": ["a", "b"], "company_name": ["A", "B"], "industry": ["x", "x"],
        "country": ["US", "US"], "founded_date": [pd.NaT, pd.NaT],
        "coverage_start": pd.to_datetime(["2010-01-01", "2010-01-01"]),
        "coverage_end": pd.to_datetime(["2030-01-01", "2030-01-01"]), "current_status": ["Operating", "Operating"],
    })
    transactions = pd.DataFrame({
        "company_id": ["a", "a", "b"], "transaction_id": ["1", "2", "3"],
        "event_date": pd.to_datetime(["2020-01-01", "2021-01-01", "2020-01-01"]),
        "transaction_type": ["Private Placement"] * 3,
    })
    snapshots = build_snapshots(companies, transactions)
    assert snapshots.company_id.tolist() == ["a"]
    assert snapshots.prediction_date.iloc[0] == pd.Timestamp("2021-01-01")


def test_features_are_limited_to_prediction_timestamp():
    labels = pd.DataFrame({
        "company_id": ["a"], "prediction_date": pd.to_datetime(["2020-01-01"]),
        "founded_date": pd.to_datetime(["2018-01-01"]),
    })
    transactions = pd.DataFrame({
        "company_id": ["a", "a"], "event_date": pd.to_datetime(["2019-01-01", "2021-01-01"]),
        "amount_usd": [2.0, 99.0],
    })
    result = make_features(labels, transactions)
    assert result.loc[0, "prior_round_count"] == 1
    assert result.loc[0, "prior_funding_usd"] == 2.0
    assert result.loc[0, "max_feature_event_date"] == pd.Timestamp("2019-01-01")


def test_temporal_partitions_are_disjoint_and_reject_short_history():
    rows = []
    for year in range(2016, 2020):
        rows.extend({"prediction_date": f"{year}-01-01", "target": target} for target in (0, 1) for _ in range(10))
    frame = pd.DataFrame(rows)
    split = temporal_partitions(frame)
    assert not set(split["train"]) & set(split["final"])
    with pytest.raises(DataContractError):
        temporal_partitions(frame[frame.prediction_date != "2019-01-01"])


def test_probability_diagnostics_return_reliability_and_top_k_metrics():
    target = pd.Series([0, 0, 1, 1, 0, 1, 0, 1])
    probability = [0.05, 0.10, 0.80, 0.95, 0.30, 0.70, 0.20, 0.90]
    calibration, reliability = calibration_diagnostics(target, probability)
    assert set(calibration) == {"intercept", "slope"}
    assert reliability.companies.sum() == len(target)
    assert decision_metrics(target, probability)[0]["positives"] == 1
