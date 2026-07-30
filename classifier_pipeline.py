"""Train the leakage-safe Capital IQ unicorn classifier.

The input table is built by :mod:`capitaliq_time_etl`. Every round used in a
feature is strictly earlier than the row's index date. This script keeps that
guarantee by selecting an explicit feature contract rather than passing all
Gold columns into a model.

Run from the project root with::

    python3 classifier_pipeline.py

The command writes a fitted model, evaluation metrics, forward-test
predictions, and feature importances under ``models/`` and ``data/gold/``.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent
GOLD_PATH = ROOT / "data" / "gold" / "capitaliq_classifier_time_safe.csv"
MODEL_DIR = ROOT / "models"
METRICS_PATH = MODEL_DIR / "capitaliq_classifier_metrics.json"
MODEL_PATH = MODEL_DIR / "capitaliq_unicorn_classifier.joblib"
PREDICTIONS_PATH = ROOT / "data" / "gold" / "capitaliq_classifier_forward_predictions.csv"
IMPORTANCE_PATH = MODEL_DIR / "capitaliq_classifier_feature_importance.csv"
RNG = 17

TARGET = "is_unicorn"
GROUP = "matched_positive_company"

# These are stable or pre-index-date company/round-history fields. In
# particular, do not add master_tier, label_source, outcome_date, match_method,
# match_gap_days, or matched_positive_company: they describe label creation or
# the one-to-one matching procedure and would leak the answer.
NUMERIC_FEATURES = [
    "index_year",
    "pre_round_count",
    "has_pre_round",
    "pre_rounds_with_amount",
    "ln_pre_funding",
    "ln_pre_funding_max",
    "pre_last_post_money_usd",
    "pre_max_post_money_usd",
    "pre_unique_investor_count",
    "pre_investor_count_max",
    "years_of_history_pre",
    "days_since_last_pre_round",
    "founded_year",
    "has_founded_year",
]
CATEGORICAL_FEATURES = ["industry_group", "continent", "country"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
        ]
    )
    return ColumnTransformer(
        [("numeric", numeric, NUMERIC_FEATURES), ("categorical", categorical, CATEGORICAL_FEATURES)]
    )


def _models() -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            [
                ("preprocess", _preprocessor()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=3000,
                        class_weight="balanced",
                        C=0.5,
                        random_state=RNG,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", _preprocessor()),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=600,
                        max_depth=7,
                        min_samples_leaf=5,
                        max_features=0.7,
                        class_weight="balanced",
                        random_state=RNG,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def _metrics(y_true: pd.Series, probability: np.ndarray) -> dict[str, float]:
    prediction = (probability >= 0.5).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_true, probability)),
        "average_precision": float(average_precision_score(y_true, probability)),
        "accuracy": float(accuracy_score(y_true, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, probability)),
    }


def _json_safe(value: object) -> object:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def run() -> dict:
    if not GOLD_PATH.exists():
        raise FileNotFoundError(f"Run etl.py first; missing {GOLD_PATH}")

    df = pd.read_csv(GOLD_PATH)
    required = set(FEATURES + [TARGET, GROUP, "company", "index_date", "index_year"])
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Capital IQ Gold is missing required columns: {missing}")

    X = df[FEATURES].copy()
    y = df[TARGET].astype(int)
    groups = df[GROUP].astype(str)
    if set(y.unique()) != {0, 1}:
        raise ValueError(f"Expected binary labels {{0, 1}}, got {sorted(y.unique())}")
    if not groups.is_unique and groups.nunique() != len(df) // 2:
        raise ValueError("Unexpected pair-group structure in Capital IQ Gold")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # A pair-group holdout keeps each positive company and its matched control
    # together, so the evaluation cannot benefit from the matching relationship.
    train_idx, holdout_idx = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RNG).split(X, y, groups)
    )
    pair_holdout = {}
    cv_summary = {}
    for name, pipeline in _models().items():
        pipeline.fit(X.iloc[train_idx], y.iloc[train_idx])
        pair_probability = pipeline.predict_proba(X.iloc[holdout_idx])[:, 1]
        pair_holdout[name] = _metrics(y.iloc[holdout_idx], pair_probability)

        cv = cross_validate(
            pipeline,
            X,
            y,
            groups=groups,
            cv=GroupKFold(n_splits=5),
            scoring=["roc_auc", "average_precision", "balanced_accuracy"],
            n_jobs=1,
        )
        cv_summary[name] = {
            metric.removeprefix("test_"): {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
            }
            for metric, values in cv.items()
            if metric.startswith("test_")
        }

    # The forward test is a chronological audit, not a random split. It is
    # held out from model selection and represents recent index dates.
    forward_train = df["index_year"] < 2024
    forward_test = ~forward_train
    if not forward_train.any() or not forward_test.any():
        raise ValueError("Need both pre-2024 training rows and 2024+ forward-test rows")
    forward_model = _models()["random_forest"]
    forward_model.fit(X.loc[forward_train], y.loc[forward_train])
    forward_probability = forward_model.predict_proba(X.loc[forward_test])[:, 1]
    forward_metrics = _metrics(y.loc[forward_test], forward_probability)
    forward_predictions = df.loc[forward_test, ["company", "company_key", "index_date", TARGET]].copy()
    forward_predictions["unicorn_probability"] = forward_probability
    forward_predictions["predicted_unicorn"] = (forward_probability >= 0.5).astype(int)
    forward_predictions.to_csv(PREDICTIONS_PATH, index=False)

    # Fit the selected model on all available pairs for use by downstream code.
    final_model = _models()["random_forest"]
    final_model.fit(X, y)
    joblib.dump(
        {
            "pipeline": final_model,
            "features": FEATURES,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "target": TARGET,
            "training_rows": len(df),
            "training_index_year_range": [int(df["index_year"].min()), int(df["index_year"].max())],
        },
        MODEL_PATH,
    )

    transformed_names = final_model.named_steps["preprocess"].get_feature_names_out()
    importances = final_model.named_steps["model"].feature_importances_
    importance_df = pd.DataFrame({"feature": transformed_names, "importance": importances})
    importance_df.sort_values("importance", ascending=False).to_csv(IMPORTANCE_PATH, index=False)

    metrics = {
        "dataset": {
            "path": str(GOLD_PATH.relative_to(ROOT)),
            "rows": int(len(df)),
            "positive_rows": int(y.sum()),
            "control_rows": int((y == 0).sum()),
            "pair_groups": int(groups.nunique()),
            "index_year_min": int(df["index_year"].min()),
            "index_year_max": int(df["index_year"].max()),
        },
        "feature_contract": {
            "numeric": NUMERIC_FEATURES,
            "categorical": CATEGORICAL_FEATURES,
            "excluded_label_or_matching_fields": [
                "label_source",
                "outcome_date",
                "match_method",
                "match_gap_days",
                "matched_positive_company",
                "master_tier",
            ],
        },
        "selected_model": "random_forest",
        "pair_group_holdout": pair_holdout,
        "pair_group_cv": cv_summary,
        "forward_test_2024_plus": {
            "train_rows": int(forward_train.sum()),
            "test_rows": int(forward_test.sum()),
            "test_years": sorted(df.loc[forward_test, "index_year"].unique().astype(int).tolist()),
            "metrics": forward_metrics,
        },
        "outputs": {
            "model": str(MODEL_PATH.relative_to(ROOT)),
            "forward_predictions": str(PREDICTIONS_PATH.relative_to(ROOT)),
            "feature_importance": str(IMPORTANCE_PATH.relative_to(ROOT)),
        },
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, default=_json_safe) + "\n")
    return metrics


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=_json_safe))
