"""Validation tests for the Capital IQ time-safe ETL outputs."""

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold" / "capitaliq_classifier_time_safe.csv"
SUMMARY = ROOT / "data" / "gold" / "capitaliq_etl_summary.json"
MATCHES = ROOT / "data" / "silver" / "capitaliq_control_matches.csv"


def test_capitaliq_outputs_exist():
    assert GOLD.exists(), "Run python3 etl.py first"
    assert SUMMARY.exists(), "Capital IQ summary missing"
    assert MATCHES.exists(), "Capital IQ control match audit missing"


def test_capitaliq_has_both_labels_and_unique_controls():
    df = pd.read_csv(GOLD, low_memory=False)
    assert set(df["is_unicorn"].unique()) == {0, 1}
    controls = df[df["is_unicorn"] == 0]
    assert controls["matched_positive_company"].is_unique


def test_capitaliq_features_are_strictly_pre_index():
    df = pd.read_csv(GOLD, parse_dates=["index_date", "max_feature_round_date"])
    used = df["max_feature_round_date"].notna()
    assert (df.loc[used, "max_feature_round_date"] < df.loc[used, "index_date"]).all()
    assert (df["outcome_date"].isna() | (df["outcome_date"] == df["index_date"])).all()
    numeric_features = [
        "pre_round_count", "pre_funding_total_usd", "ln_pre_funding",
        "pre_funding_max_usd", "ln_pre_funding_max", "days_since_last_pre_round",
    ]
    assert df[numeric_features].notna().all().all()


def test_capitaliq_summary_reports_zero_leakage():
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["leakage_check_rows"] == 0
    assert summary["gold_controls_are_one_to_one"] is True
