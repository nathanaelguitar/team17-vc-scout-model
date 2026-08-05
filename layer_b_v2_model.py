"""Temporal training and calibration for eligible Layer B v2 snapshots.

The module accepts only the verified positive/negative snapshot table produced
by :mod:`layer_b_v2_pipeline`.  Censored and competing events never enter a
binary classifier fit.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from layer_b_v2_pipeline import DataContractError, RESULTS, SNAPSHOTS


FEATURES_NUMERIC = ["prior_round_count", "prior_funding_usd", "prior_max_round_usd", "days_since_last_round", "company_age_years"]
FEATURES_CATEGORICAL = ["industry", "country"]
FEATURES = FEATURES_NUMERIC + FEATURES_CATEGORICAL


def _pipeline() -> Pipeline:
    return Pipeline([
        ("features", ColumnTransformer([
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), FEATURES_NUMERIC),
            ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), FEATURES_CATEGORICAL),
        ])),
        ("model", LogisticRegression(max_iter=3000, class_weight="balanced", C=0.5, random_state=17)),
    ])


def temporal_partitions(frame: pd.DataFrame) -> dict[str, pd.Index]:
    """Create four disjoint year blocks without random row-level splitting."""
    years = sorted(pd.to_datetime(frame.prediction_date).dt.year.unique())
    if len(years) < 4:
        raise DataContractError("Need at least four prediction years for train/validation/calibration/final separation")
    blocks = np.array_split(np.array(years), 4)
    labels = ["train", "validation", "calibration", "final"]
    partitions = {label: frame.index[pd.to_datetime(frame.prediction_date).dt.year.isin(block)].copy() for label, block in zip(labels, blocks)}
    for label, index in partitions.items():
        values = frame.loc[index, "target"]
        if len(index) < 20 or values.nunique() != 2:
            raise DataContractError(f"Temporal {label} partition lacks sufficient examples of both outcomes")
    return partitions


def _metrics(y: pd.Series, probability: np.ndarray) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(y, probability)),
        "pr_auc": float(average_precision_score(y, probability)),
        "brier": float(brier_score_loss(y, probability)),
    }


def _platt_fit(probability: np.ndarray, target: pd.Series) -> LogisticRegression:
    calibrator = LogisticRegression(C=1.0, max_iter=1000, random_state=17)
    calibrator.fit(np.asarray(probability).reshape(-1, 1), target.astype(int))
    return calibrator


def calibration_diagnostics(target: pd.Series, probability: np.ndarray, bins: int = 5) -> tuple[dict[str, float], pd.DataFrame]:
    """Return final-period calibration fit and a reliability table."""
    y = target.astype(int).to_numpy()
    p = np.clip(np.asarray(probability), 1e-6, 1 - 1e-6)
    logits = np.log(p / (1 - p)).reshape(-1, 1)
    fit = LogisticRegression(C=1_000_000, max_iter=3000, random_state=17).fit(logits, y)
    table = pd.DataFrame({"target": y, "probability": p})
    table["bin"] = pd.cut(table.probability, bins=np.linspace(0, 1, bins + 1), include_lowest=True)
    reliability = table.groupby("bin", observed=False).agg(companies=("target", "size"), observed_rate=("target", "mean"), mean_probability=("probability", "mean")).reset_index()
    reliability["bin"] = reliability["bin"].astype(str)
    return {"intercept": float(fit.intercept_[0]), "slope": float(fit.coef_[0][0])}, reliability


def decision_metrics(target: pd.Series, probability: np.ndarray) -> list[dict[str, float]]:
    y = target.reset_index(drop=True)
    base_rate = float(y.mean())
    result = []
    for fraction in (0.01, 0.05, 0.10, 0.20):
        count = max(1, int(np.ceil(len(y) * fraction)))
        selected = y.iloc[np.argsort(probability)[::-1][:count]]
        precision = float(selected.mean())
        result.append({"top_fraction": fraction, "companies": count, "positives": int(selected.sum()), "precision": precision, "recall": float(selected.sum() / y.sum()) if y.sum() else 0.0, "lift": float(precision / base_rate) if base_rate else np.nan})
    return result


def train() -> dict:
    table_path = SNAPSHOTS / "eligible_three_year_labels.csv"
    if not table_path.exists():
        raise DataContractError("Build eligible three-year snapshots before training")
    frame = pd.read_csv(table_path, parse_dates=["prediction_date", "max_feature_event_date"])
    missing = sorted(set(FEATURES + ["company_id", "target", "label_state", "prediction_date"]).difference(frame.columns))
    if missing:
        raise DataContractError(f"Eligible snapshot table is missing: {missing}")
    if not frame.label_state.isin(["positive", "negative"]).all():
        raise DataContractError("Censored or competing rows reached the training table")
    if frame.company_id.duplicated().any():
        raise DataContractError("A company appears in more than one landmark row; define an entity grouping policy")
    leakage = frame.max_feature_event_date.notna() & frame.max_feature_event_date.gt(frame.prediction_date)
    if leakage.any():
        raise DataContractError("Feature timestamp audit failed")
    split = temporal_partitions(frame)
    model = _pipeline()
    model.fit(frame.loc[split["train"], FEATURES], frame.loc[split["train"], "target"].astype(int))
    validation_probability = model.predict_proba(frame.loc[split["validation"], FEATURES])[:, 1]
    calibration_probability = model.predict_proba(frame.loc[split["calibration"], FEATURES])[:, 1]
    calibrator = _platt_fit(calibration_probability, frame.loc[split["calibration"], "target"])
    final_probability = model.predict_proba(frame.loc[split["final"], FEATURES])[:, 1]
    final_calibrated = calibrator.predict_proba(final_probability.reshape(-1, 1))[:, 1]
    final = frame.loc[split["final"], ["company_id", "prediction_date", "target"]].copy()
    final["ranking_score"] = final_probability
    final["calibrated_probability"] = final_calibrated
    RESULTS.mkdir(parents=True, exist_ok=True)
    final.to_csv(RESULTS / "final_temporal_predictions.csv", index=False)
    calibration, reliability = calibration_diagnostics(frame.loc[split["final"], "target"], final_calibrated)
    reliability.to_csv(RESULTS / "final_reliability.csv", index=False)
    metrics = {
        "feature_contract": FEATURES,
        "partitions": {name: {"rows": int(len(index)), "years": sorted(pd.to_datetime(frame.loc[index, "prediction_date"]).dt.year.unique().tolist())} for name, index in split.items()},
        "validation_uncalibrated": _metrics(frame.loc[split["validation"], "target"], validation_probability),
        "final_uncalibrated": _metrics(frame.loc[split["final"], "target"], final_probability),
        "final_platt": {**_metrics(frame.loc[split["final"], "target"], final_calibrated), "calibration": calibration, "decision_metrics": decision_metrics(frame.loc[split["final"], "target"], final_calibrated)},
        "temporal_feature_violations": int(leakage.sum()),
    }
    (RESULTS / "model_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    joblib.dump({"pipeline": model, "platt_calibrator": calibrator, "features": FEATURES, "training_period": metrics["partitions"]["train"]}, RESULTS / "layer_b_v2_model.joblib")
    model_card = {
        "outcome": "Verified $1B+ valuation/private-placement event within three years after the second private-placement financing",
        "population": "Companies covered continuously from the snapshot through the horizon, excluding censored, already-unicorn, and competing-outcome rows",
        "probability_scope": "Calibrated only for the supplied Capital IQ coverage-defined population and temporal range",
        "release_gates": ["coverage start <= prediction date", "coverage end >= horizon end", "no feature timestamp after prediction date", "temporal final period untouched during fitting and calibration"],
        "metrics": metrics,
    }
    (RESULTS / "model_card.json").write_text(json.dumps(model_card, indent=2) + "\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
