import json
import warnings
from pathlib import Path

import joblib
import pandas as pd

from classifier_pipeline import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES


ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "gold" / "capitaliq_classifier_time_safe.csv"
METRICS = ROOT / "models" / "capitaliq_classifier_metrics.json"
MODEL = ROOT / "models" / "capitaliq_unicorn_classifier.joblib"


def test_model_feature_contract_excludes_label_and_matching_metadata():
    forbidden = {
        "is_unicorn",
        "label_source",
        "outcome_date",
        "match_method",
        "match_gap_days",
        "matched_positive_company",
        "master_tier",
    }
    assert not forbidden.intersection(FEATURES)
    assert set(NUMERIC_FEATURES).isdisjoint(CATEGORICAL_FEATURES)


def test_fitted_capitaliq_classifier_artifacts_exist_and_score():
    assert GOLD.exists()
    assert METRICS.exists()
    assert MODEL.exists()
    df = pd.read_csv(GOLD)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        bundle = joblib.load(MODEL)
    probabilities = bundle["pipeline"].predict_proba(df[FEATURES].head(8))[:, 1]
    assert len(probabilities) == 8
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_forward_evaluation_is_recorded():
    metrics = json.loads(METRICS.read_text())
    forward = metrics["forward_test_2024_plus"]
    assert forward["train_rows"] > 0
    assert forward["test_rows"] > 0
    assert forward["test_years"] == [2024, 2025, 2026]
    assert forward["metrics"]["roc_auc"] >= 0.80
