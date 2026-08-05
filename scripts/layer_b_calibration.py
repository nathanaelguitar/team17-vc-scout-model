#!/usr/bin/env python3
"""Chronological calibration and decision-usefulness checks for Layer B.

Training ends in 2022, calibration uses 2023 only, and 2024+ is untouched
until final scoring.  This is intentionally stricter than the historical
reported 2024+ forward test, which fitted on all years through 2023.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from layer_b_audit_utils import (
    FIGURES_DIR, RESULTS_DIR, classification_metrics, ensure_output_dirs,
    load_original_gold, screening_metrics,
)
from layer_b_leakage_diagnostics import BASE_CATEGORICAL, BASE_NUMERIC, model_for


def calibration_curve_frame(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    frame = pd.DataFrame({"y": y, "p": p})
    frame["bin"] = pd.qcut(frame["p"].rank(method="first"), q=min(bins, len(frame)), duplicates="drop")
    return frame.groupby("bin", observed=True).agg(
        observations=("y", "size"), mean_prediction=("p", "mean"), observed_rate=("y", "mean"),
    ).reset_index(drop=True)


def main() -> None:
    ensure_output_dirs()
    df = load_original_gold()
    features = BASE_NUMERIC + BASE_CATEGORICAL
    train = df.index_year <= 2022
    calibration = df.index_year == 2023
    final_test = df.index_year >= 2024
    if not (train.any() and calibration.any() and final_test.any()):
        raise ValueError("Need nonempty train (<=2022), calibration (2023), and final test (>=2024) periods")
    model = model_for("random_forest", BASE_NUMERIC, BASE_CATEGORICAL)
    model.fit(df.loc[train, features], df.loc[train, "is_unicorn"])
    calibration_raw = np.clip(model.predict_proba(df.loc[calibration, features])[:, 1], 1e-6, 1 - 1e-6)
    final_raw = np.clip(model.predict_proba(df.loc[final_test, features])[:, 1], 1e-6, 1 - 1e-6)
    y_cal = df.loc[calibration, "is_unicorn"].to_numpy()
    y_test = df.loc[final_test, "is_unicorn"].to_numpy()
    platt = LogisticRegression(C=1e6, max_iter=2000).fit(np.log(calibration_raw / (1 - calibration_raw)).reshape(-1, 1), y_cal)
    platt_final = platt.predict_proba(np.log(final_raw / (1 - final_raw)).reshape(-1, 1))[:, 1]
    isotonic = IsotonicRegression(out_of_bounds="clip").fit(calibration_raw, y_cal)
    isotonic_final = isotonic.predict(final_raw)
    methods = {"uncalibrated": final_raw, "platt_2023": platt_final, "isotonic_2023": isotonic_final}
    metric_rows = []
    prediction_rows = []
    curve_rows = []
    for name, probability in methods.items():
        metric_rows.append({
            "method": name, "train_rows": int(train.sum()), "calibration_rows": int(calibration.sum()),
            "final_test_rows": int(final_test.sum()), "final_test_years": "2024-2026",
            **classification_metrics(y_test, probability),
        })
        prediction_rows.append(pd.DataFrame({
            "method": name, "company_key": df.loc[final_test, "company_key"].to_numpy(),
            "index_date": df.loc[final_test, "index_date"].to_numpy(), "is_unicorn": y_test,
            "probability": probability,
        }))
        curve = calibration_curve_frame(y_test, probability)
        curve["method"] = name
        curve_rows.append(curve)
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(RESULTS_DIR / "chronological_calibration_metrics.csv", index=False)
    pd.concat(prediction_rows, ignore_index=True).to_csv(RESULTS_DIR / "chronological_calibration_predictions.csv", index=False)
    curves = pd.concat(curve_rows, ignore_index=True)
    curves.to_csv(RESULTS_DIR / "reliability_curve_final_test.csv", index=False)
    screening_metrics(y_test, platt_final).assign(method="platt_2023").to_csv(
        RESULTS_DIR / "screening_metrics_final_test.csv", index=False
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for name in methods:
        part = curves[curves.method == name]
        axes[0].plot(part.mean_prediction, part.observed_rate, marker="o", label=name)
    axes[0].plot([0, 1], [0, 1], "--", color="black", linewidth=1)
    axes[0].set(xlabel="Mean predicted score", ylabel="Observed positive fraction", title="Final-test reliability")
    axes[0].legend()
    for label, probability in methods.items():
        axes[1].hist(probability[y_test == 0], bins=20, alpha=0.35, density=True, label=f"control — {label}")
    axes[1].hist(platt_final[y_test == 1], bins=20, alpha=0.5, density=True, label="positive — Platt")
    axes[1].set(xlabel="Score", ylabel="Density", title="Final-test score distributions")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "chronological_calibration_and_score_distribution.png", dpi=220)
    plt.close(fig)
    print(metrics[["method", "roc_auc", "pr_auc", "brier_score", "log_loss", "calibration_intercept", "calibration_slope"]].to_string(index=False))


if __name__ == "__main__":
    main()
