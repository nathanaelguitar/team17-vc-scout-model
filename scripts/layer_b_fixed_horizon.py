#!/usr/bin/env python3
"""Construct current-data fixed-horizon snapshots and stricter control cohorts.

Important: Capital IQ coverage start/end and company status are absent from the
supplied extracts.  Therefore a negative below requires a later observed
sub-$1B transaction after the horizon.  That is a reproducible *observed
follow-up proxy*, not proof of continuous Capital IQ coverage or a permanent
non-unicorn outcome.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

from layer_b_audit_utils import (
    RESULTS_DIR, classification_metrics, ensure_output_dirs, history_features,
    load_original_gold, load_source_rounds,
)


FEATURES = [
    "pre_round_count", "pre_rounds_with_amount", "pre_funding_total_usd",
    "pre_funding_max_usd", "pre_unique_investor_count", "pre_investor_count_max",
    "years_of_history_pre", "days_since_last_pre_round",
]


def make_landmark_snapshots(horizon_years: int) -> pd.DataFrame:
    rounds, _, first_events = load_source_rounds()
    horizon = pd.Timedelta(days=round(365.25 * horizon_years))
    events = first_events.set_index("company_key")["outcome_date"]
    rows = []
    # A single two-year-after-first-round landmark is more decision-like than
    # evaluating multiple correlated snapshots from one company.
    for company_key, group in rounds.groupby("company_key", sort=False):
        group = group.sort_values("event_date")
        first_round = group.event_date.iloc[0]
        landmark = first_round + pd.Timedelta(days=round(365.25 * 2))
        event_date = events.get(company_key, pd.NaT)
        if pd.notna(event_date) and event_date <= landmark:
            continue  # already an event before the proposed prediction time
        event_within_horizon = pd.notna(event_date) and event_date <= landmark + horizon
        # The required control follow-up is intentionally strict: it has a
        # known later sub-$1B financing after the full horizon.  No later row
        # means censored/unknown, not a negative.
        observed_after_horizon = (group.event_date >= landmark + horizon).any()
        if event_within_horizon:
            label, label_basis = 1, "first_ge_1b_event_within_horizon"
        elif observed_after_horizon:
            label, label_basis = 0, "no_known_event_plus_later_sub_1b_round_proxy"
        else:
            continue
        features = history_features(rounds, company_key, landmark)
        rows.append({
            "company_key": company_key, "company": group.company_name.iloc[0],
            "first_recorded_round_date": first_round, "landmark_date": landmark,
            "horizon_years": horizon_years, "horizon_end_date": landmark + horizon,
            "first_ge_1b_outcome_date": event_date, "is_unicorn_within_horizon": label,
            "label_basis": label_basis, **features,
        })
    return pd.DataFrame(rows)


def evaluate_horizon(frame: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    if frame.empty or frame.is_unicorn_within_horizon.nunique() < 2:
        return {"status": "insufficient_labeled_snapshots"}, pd.DataFrame()
    frame = frame.copy()
    frame["landmark_year"] = pd.to_datetime(frame.landmark_date).dt.year
    years = sorted(frame.landmark_year.unique())
    # Latest ~20% of calendar years, at least one full year, are held out.
    test_years = years[max(1, int(np.floor(len(years) * 0.8))):]
    if not test_years or not (frame.landmark_year.isin(test_years)).any():
        return {"status": "insufficient_calendar_split"}, pd.DataFrame()
    test = frame.landmark_year.isin(test_years)
    train = ~test
    if frame.loc[train, "is_unicorn_within_horizon"].nunique() < 2 or frame.loc[test, "is_unicorn_within_horizon"].nunique() < 2:
        return {"status": "insufficient_class_variation_after_time_split"}, pd.DataFrame()
    model = RandomForestClassifier(
        n_estimators=500, max_depth=6, min_samples_leaf=8, max_features=0.8,
        class_weight="balanced", random_state=17, n_jobs=-1,
    )
    model.fit(frame.loc[train, FEATURES], frame.loc[train, "is_unicorn_within_horizon"])
    probability = model.predict_proba(frame.loc[test, FEATURES])[:, 1]
    metrics = {
        "status": "evaluated", "train_rows": int(train.sum()), "test_rows": int(test.sum()),
        "test_landmark_years": "|".join(map(str, test_years)),
        "sampled_positive_rows": int(frame.is_unicorn_within_horizon.sum()),
        "sampled_negative_rows": int((frame.is_unicorn_within_horizon == 0).sum()),
        **classification_metrics(frame.loc[test, "is_unicorn_within_horizon"], probability),
    }
    predictions = frame.loc[test, ["company_key", "company", "landmark_date", "is_unicorn_within_horizon", "label_basis"]].copy()
    predictions["probability"] = probability
    return metrics, predictions


def strict_negative_cohorts() -> pd.DataFrame:
    """Historical-target sensitivity to successively stricter controls.

    These filters use only data before the shared prediction index.  They do
    not solve right censoring, so output is a sensitivity analysis rather than
    a replacement target.
    """
    df = load_original_gold()
    controls = df[df.is_unicorn == 0].set_index("matched_positive_company")
    criteria = {
        "current_matched_controls": lambda c: pd.Series(True, index=c.index),
        "at_least_2_pre_rounds": lambda c: c.pre_round_count >= 2,
        "at_least_3_pre_rounds": lambda c: c.pre_round_count >= 3,
        "at_least_5_years_pre_index_history": lambda c: c.years_of_history_pre >= 5,
        "at_least_7_years_pre_index_history": lambda c: c.years_of_history_pre >= 7,
        "two_rounds_and_5_year_history": lambda c: (c.pre_round_count >= 2) & (c.years_of_history_pre >= 5),
    }
    output = []
    for name, rule in criteria.items():
        eligible_pairs = controls.index[rule(controls)]
        subset = df[df.matched_positive_company.isin(eligible_pairs)].copy()
        train = subset.index_year < 2024
        test = ~train
        if len(subset) < 20 or subset.loc[test, "is_unicorn"].nunique() < 2:
            output.append({"cohort": name, "status": "insufficient_rows", "rows": int(len(subset))})
            continue
        model = RandomForestClassifier(
            n_estimators=400, max_depth=7, min_samples_leaf=5, max_features=0.7,
            class_weight="balanced", random_state=17, n_jobs=-1,
        )
        model.fit(subset.loc[train, FEATURES + ["has_pre_round"]], subset.loc[train, "is_unicorn"])
        p = model.predict_proba(subset.loc[test, FEATURES + ["has_pre_round"]])[:, 1]
        output.append({
            "cohort": name, "status": "evaluated", "rows": int(len(subset)),
            "positive_rows": int(subset.is_unicorn.sum()), "control_rows": int((subset.is_unicorn == 0).sum()),
            "forward_test_rows": int(test.sum()), **classification_metrics(subset.loc[test, "is_unicorn"], p),
        })
    return pd.DataFrame(output)


def main() -> None:
    ensure_output_dirs()
    summaries = []
    all_predictions = []
    for horizon in (2, 3, 5):
        snapshots = make_landmark_snapshots(horizon)
        snapshots.to_csv(RESULTS_DIR / f"fixed_horizon_{horizon}y_snapshots.csv", index=False)
        result, predictions = evaluate_horizon(snapshots)
        summaries.append({"horizon_years": horizon, **result})
        if not predictions.empty:
            predictions["horizon_years"] = horizon
            all_predictions.append(predictions)
    pd.DataFrame(summaries).to_csv(RESULTS_DIR / "fixed_horizon_evaluation.csv", index=False)
    if all_predictions:
        pd.concat(all_predictions, ignore_index=True).to_csv(RESULTS_DIR / "fixed_horizon_forward_predictions.csv", index=False)
    cohorts = strict_negative_cohorts()
    cohorts.to_csv(RESULTS_DIR / "strict_negative_cohort_sensitivity.csv", index=False)
    (RESULTS_DIR / "fixed_horizon_design_notes.json").write_text(json.dumps({
        "landmark": "two years after the first supplied sub-$1B private-placement record",
        "feature_cutoff": "strictly before landmark_date",
        "positive": "first supplied >=$1B post-money event occurs within the horizon",
        "negative": "no supplied >=$1B event in horizon AND a supplied sub-$1B round at/after horizon end",
        "censoring": "companies without the required later low-valuation round are excluded as unknown/censored",
        "limitation": "later round is an observation proxy; supplied files lack Capital IQ coverage start/end and company status",
    }, indent=2) + "\n")
    print(pd.DataFrame(summaries).to_string(index=False))
    print(cohorts.to_string(index=False))


if __name__ == "__main__":
    main()
