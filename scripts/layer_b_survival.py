#!/usr/bin/env python3
"""Exploratory Cox survival analysis with explicit censoring limitations.

The supplied Capital IQ transaction exports do not include coverage end dates,
operating status, exits, or complete valuation histories.  The censoring time
below is therefore the last supplied sub-$1B transaction, which is an
observation proxy rather than independent administrative censoring.  The
script is reusable once proper coverage/status exports are supplied.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import roc_auc_score

from layer_b_audit_utils import RESULTS_DIR, ensure_output_dirs, history_features, load_source_rounds


FEATURES = [
    "pre_round_count", "pre_rounds_with_amount", "pre_funding_total_usd",
    "pre_funding_max_usd", "pre_unique_investor_count", "pre_investor_count_max",
    "years_of_history_pre", "days_since_last_pre_round",
]


def build_survival_input() -> pd.DataFrame:
    rounds, _, first_events = load_source_rounds()
    events = first_events.set_index("company_key")["outcome_date"]
    rows = []
    for key, company_rounds in rounds.groupby("company_key", sort=False):
        company_rounds = company_rounds.sort_values("event_date")
        landmark = company_rounds.event_date.iloc[0] + pd.Timedelta(days=round(365.25 * 2))
        event_date = events.get(key, pd.NaT)
        if pd.notna(event_date) and event_date <= landmark:
            continue
        last_observed_round = company_rounds.event_date.iloc[-1]
        if pd.notna(event_date):
            duration = (event_date - landmark).days / 365.25
            event = 1
            endpoint = event_date
        else:
            duration = (last_observed_round - landmark).days / 365.25
            event = 0
            endpoint = last_observed_round
        if duration <= 0:
            continue
        rows.append({
            "company_key": key, "company": company_rounds.company_name.iloc[0],
            "landmark_date": landmark, "endpoint_date": endpoint, "duration_years": duration,
            "event": event, "censoring_basis": "first_ge_1b_event" if event else "last_supplied_sub_1b_round_proxy",
            **history_features(rounds, key, landmark),
        })
    return pd.DataFrame(rows)


def fit_cox(x: np.ndarray, duration: np.ndarray, event: np.ndarray, ridge: float = 0.1) -> np.ndarray:
    """Fit a small Breslow-tie Cox PH model with L2 regularization."""
    event_times = np.unique(duration[event == 1])

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        score = np.clip(x @ beta, -50, 50)
        exp_score = np.exp(score)
        value, gradient = 0.0, np.zeros(x.shape[1])
        for time in event_times:
            events = (duration == time) & (event == 1)
            risk = duration >= time
            d = events.sum()
            risk_weight = exp_score[risk].sum()
            value += score[events].sum() - d * np.log(risk_weight)
            gradient += x[events].sum(axis=0) - d * (x[risk] * exp_score[risk, None]).sum(axis=0) / risk_weight
        value -= ridge * np.dot(beta, beta) / 2
        gradient -= ridge * beta
        return -value, -gradient

    outcome = minimize(lambda b: objective(b)[0], np.zeros(x.shape[1]), jac=lambda b: objective(b)[1], method="L-BFGS-B")
    if not outcome.success:
        raise RuntimeError(f"Cox optimization failed: {outcome.message}")
    return outcome.x


def concordance_index(duration: np.ndarray, event: np.ndarray, risk: np.ndarray) -> float:
    concordant = tied = comparable = 0
    for i in range(len(duration)):
        # i has an observed event before j's event/censor time.
        mask = (duration[i] < duration) & (event[i] == 1)
        if not mask.any():
            continue
        comparable += int(mask.sum())
        concordant += int((risk[i] > risk[mask]).sum())
        tied += int((risk[i] == risk[mask]).sum())
    return float((concordant + 0.5 * tied) / comparable) if comparable else float("nan")


def main() -> None:
    ensure_output_dirs()
    frame = build_survival_input()
    frame.to_csv(RESULTS_DIR / "exploratory_survival_input.csv", index=False)
    frame["landmark_year"] = pd.to_datetime(frame.landmark_date).dt.year
    years = sorted(frame.landmark_year.unique())
    test_years = years[max(1, int(np.floor(0.8 * len(years)))):]
    train = ~frame.landmark_year.isin(test_years)
    test = ~train
    # Log-transform highly skewed capital fields before standardization.
    design = frame[FEATURES].copy()
    for field in ["pre_funding_total_usd", "pre_funding_max_usd"]:
        design[field] = np.log1p(design[field])
    means, stds = design.loc[train].mean(), design.loc[train].std().replace(0, 1)
    x_train = ((design.loc[train] - means) / stds).to_numpy(float)
    x_test = ((design.loc[test] - means) / stds).to_numpy(float)
    beta = fit_cox(x_train, frame.loc[train, "duration_years"].to_numpy(float), frame.loc[train, "event"].to_numpy(int))
    risk_test = x_test @ beta
    c_index = concordance_index(
        frame.loc[test, "duration_years"].to_numpy(float), frame.loc[test, "event"].to_numpy(int), risk_test,
    )
    # A two-year time-dependent classification is reported only for companies
    # with either an event by 2y or a supplied low-valuation round after 2y.
    observed_2y = (frame.loc[test, "event"] == 1) | (frame.loc[test, "duration_years"] >= 2)
    within_2y = ((frame.loc[test, "event"] == 1) & (frame.loc[test, "duration_years"] <= 2)).astype(int)
    td_auc = float("nan")
    if observed_2y.sum() and within_2y.loc[observed_2y].nunique() == 2:
        td_auc = float(roc_auc_score(within_2y.loc[observed_2y], risk_test[observed_2y.to_numpy()]))
    coefficients = pd.DataFrame({"feature": FEATURES, "cox_log_hazard_ratio": beta, "hazard_ratio": np.exp(beta)})
    coefficients.to_csv(RESULTS_DIR / "exploratory_cox_coefficients.csv", index=False)
    prediction = frame.loc[test, ["company_key", "company", "landmark_date", "duration_years", "event", "censoring_basis"]].copy()
    prediction["cox_risk_score"] = risk_test
    prediction.to_csv(RESULTS_DIR / "exploratory_cox_forward_predictions.csv", index=False)
    metrics = {
        "status": "exploratory_only_not_defensible_for_production_without_coverage_and_status_fields",
        "population": "companies with supplied sub-$1B rounds and a two-year-after-first-round landmark",
        "rows": int(len(frame)), "events": int(frame.event.sum()), "proxy_censored": int((frame.event == 0).sum()),
        "train_rows": int(train.sum()), "test_rows": int(test.sum()), "test_landmark_years": test_years,
        "cox_concordance_index": c_index, "two_year_time_dependent_auc_proxy": td_auc,
        "censoring_warning": "Non-event duration ends at last supplied low-valuation financing, not Capital IQ coverage end; censoring is likely informative.",
    }
    (RESULTS_DIR / "exploratory_survival_metrics.json").write_text(json.dumps(metrics, indent=2, default=lambda value: value.item() if hasattr(value, "item") else str(value)) + "\n")
    print(json.dumps(metrics, indent=2, default=lambda value: value.item() if hasattr(value, "item") else str(value)))
    print(coefficients.to_string(index=False))


if __name__ == "__main__":
    main()
