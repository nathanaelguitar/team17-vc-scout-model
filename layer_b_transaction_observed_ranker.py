"""A provisional, transaction-observed unicorn screening ranker.

This is deliberately separate from the certified Layer B v2 model.  Capital
IQ transaction history provides evidence that a company was observed after a
prediction date, not evidence of continuous coverage.  Therefore this module
predicts an *observed* $1B event within three years and emits a ranking score,
never a probability of becoming a unicorn.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from capitaliq_time_etl import ONE_BILLION_USD, canonical_name


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "layer_b_v2" / "transaction_observed"
MODEL_DIR = ROOT / "models"
CURRENT_MASTER = ROOT / "data" / "bronze" / "startup_master_bronze.csv"
REPORTS = [RAW / "capitaliq_control_private_placements_raw10k.csv", *sorted(RAW.glob("capitaliq_control_closed_*.csv")), RAW / "capitaliq_unicorn_private_placements.csv"]
NUMERIC = [
    "prediction_year", "pre_round_count", "pre_funding_usd", "pre_max_round_usd",
    "pre_last_post_money_usd", "pre_unique_investor_count", "years_since_first_round",
    "days_since_last_round", "current_round_usd", "current_investor_count",
]
FEATURE_FAMILIES = {
    "all_eligible_features": NUMERIC,
    "funding_only": ["pre_round_count", "pre_funding_usd", "pre_max_round_usd", "pre_last_post_money_usd", "current_round_usd", "current_investor_count"],
    "timing_only": ["prediction_year", "years_since_first_round", "days_since_last_round"],
    "single_current_round": ["current_round_usd"],
}


class ObservedDataError(ValueError):
    pass


def _header(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for index, row in enumerate(csv.reader(handle)):
            if "Target/Issuer" in row:
                return index
    raise ObservedDataError(f"Capital IQ header missing in {path}")


def _investors(value: object) -> set[str]:
    if not isinstance(value, str) or value.strip() in {"", "-"}:
        return set()
    return {key for key in (canonical_name(part) for part in value.split(";")) if key}


def read_reports() -> pd.DataFrame:
    missing = [str(path.relative_to(ROOT)) for path in REPORTS if not path.exists()]
    if missing:
        raise ObservedDataError(f"Missing Capital IQ transaction reports: {missing}")
    frames = []
    for path in REPORTS:
        frame = pd.read_csv(path, skiprows=_header(path), low_memory=False)
        frame["source_file"] = path.name
        frames.append(frame)
    raw = pd.concat(frames, ignore_index=True, sort=False)
    raw = raw[raw["Target/Issuer"].notna()].copy()
    raw["company_name"] = raw["Target/Issuer"].astype(str).str.strip()
    raw["company_key"] = raw.company_name.map(canonical_name)
    raw["event_date"] = pd.to_datetime(raw["All Transactions Closed Date"], errors="coerce").fillna(pd.to_datetime(raw["All Transactions Announced Date"], errors="coerce"))
    raw["transaction_id"] = raw["CIQ Transaction ID"].astype(str).str.strip()
    raw["round_value_usd"] = pd.to_numeric(raw["Total Transaction Value ($USDmm, Historical rate)"], errors="coerce") * 1e6
    raw["post_money_usd"] = pd.to_numeric(raw["Post-Money Valuation ($USDmm, Historical rate)"], errors="coerce") * 1e6
    raw["investors"] = raw["Buyers/Investors"].map(_investors)
    raw["investor_count"] = raw.investors.map(len)
    raw = raw[(raw.company_key.ne("")) & raw.event_date.notna() & raw.transaction_id.ne("")]
    raw = raw.drop_duplicates("transaction_id", keep="first").sort_values(["company_key", "event_date", "transaction_id"])
    # Conservative name normalization is only an entity-resolution fallback.
    # Excluding non-unique keys is safer than joining two legal entities.
    key_names = raw.groupby("company_key").company_name.nunique()
    raw = raw[~raw.company_key.isin(key_names[key_names.gt(1)].index)].copy()
    return raw.reset_index(drop=True)


def build_table(rounds: pd.DataFrame) -> pd.DataFrame:
    """Create one second-financing snapshot per unambiguous company."""
    rounds = rounds.copy()
    rounds["round_order"] = rounds.groupby("company_key").cumcount() + 1
    snapshots = rounds[rounds.round_order.eq(2)].copy()
    first_unicorn = rounds[rounds.post_money_usd.ge(ONE_BILLION_USD)].groupby("company_key").event_date.min()
    last_seen = rounds.groupby("company_key").event_date.max()
    rows: list[dict[str, object]] = []
    for snap in snapshots.itertuples(index=False):
        history = rounds[(rounds.company_key == snap.company_key) & (rounds.event_date < snap.event_date)].sort_values("event_date")
        outcome_date = first_unicorn.get(snap.company_key, pd.NaT)
        horizon_end = snap.event_date + pd.DateOffset(years=3)
        already_unicorn = pd.notna(outcome_date) and outcome_date <= snap.event_date
        observed_positive = pd.notna(outcome_date) and snap.event_date < outcome_date <= horizon_end
        observed_negative = (not already_unicorn) and (not observed_positive) and last_seen[snap.company_key] >= horizon_end
        state = "observed_positive" if observed_positive else "observed_no_future_outcome" if observed_negative else "already_unicorn" if already_unicorn else "insufficient_followup"
        investors = set().union(*history.investors.tolist()) if not history.empty else set()
        amounts = history.round_value_usd.dropna().clip(lower=0)
        previous_post = history.post_money_usd.dropna()
        last_history = history.event_date.max() if not history.empty else pd.NaT
        rows.append({
            "company": snap.company_name, "company_key": snap.company_key,
            "prediction_date": snap.event_date, "horizon_end": horizon_end,
            "first_observed_unicorn_date": outcome_date, "last_observed_transaction_date": last_seen[snap.company_key],
            "label_state": state, "target": 1 if observed_positive else 0 if observed_negative else np.nan,
            "prediction_year": snap.event_date.year, "pre_round_count": len(history),
            "pre_funding_usd": float(amounts.sum()), "pre_max_round_usd": float(amounts.max()) if not amounts.empty else 0.0,
            "pre_last_post_money_usd": float(previous_post.iloc[-1]) if not previous_post.empty else 0.0,
            "pre_unique_investor_count": len(investors),
            "years_since_first_round": max((snap.event_date - history.event_date.min()).days / 365.25, 0.0) if not history.empty else 0.0,
            "days_since_last_round": int((snap.event_date - last_history).days) if pd.notna(last_history) else -1,
            "current_round_usd": float(max(snap.round_value_usd, 0)) if pd.notna(snap.round_value_usd) else 0.0,
            "current_investor_count": int(snap.investor_count),
            "max_feature_event_date": max(last_history, snap.event_date) if pd.notna(last_history) else snap.event_date,
        })
    out = pd.DataFrame(rows)
    bad = out.max_feature_event_date.gt(out.prediction_date)
    if bad.any():
        raise AssertionError("Future transaction used in a feature")
    return out


def _model(kind: str, features: list[str] = NUMERIC) -> Pipeline:
    transformer = ColumnTransformer([("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), features)])
    estimator = LogisticRegression(max_iter=3000, class_weight="balanced", C=0.5, random_state=17) if kind == "logistic" else RandomForestClassifier(n_estimators=500, max_depth=5, min_samples_leaf=8, class_weight="balanced", random_state=17, n_jobs=-1)
    return Pipeline([("features", transformer), ("model", estimator)])


def _metrics(target: pd.Series, probability: np.ndarray) -> dict[str, float]:
    return {"roc_auc": float(roc_auc_score(target, probability)), "pr_auc": float(average_precision_score(target, probability)), "brier_observed_outcome": float(brier_score_loss(target, probability))}


def _decision_metrics(target: pd.Series, score: np.ndarray) -> list[dict[str, float]]:
    result = []
    base_rate = float(target.mean())
    for fraction in (0.10, 0.20, 0.30):
        n = max(1, int(np.ceil(len(target) * fraction)))
        selected = target.iloc[np.argsort(score)[::-1][:n]]
        precision = float(selected.mean())
        result.append({"top_fraction": fraction, "companies": n, "observed_positives": int(selected.sum()), "precision": precision, "lift_vs_observed_base_rate": precision / base_rate if base_rate else np.nan})
    return result


def _bootstrap_ci(target: pd.Series, score: np.ndarray, draws: int = 1000) -> dict[str, list[float]]:
    """Non-parametric uncertainty interval for the untouched final period."""
    rng = np.random.default_rng(17)
    y = target.to_numpy(dtype=int)
    values: dict[str, list[float]] = {"roc_auc": [], "pr_auc": []}
    for _ in range(draws):
        index = rng.integers(0, len(y), len(y))
        if np.unique(y[index]).size < 2:
            continue
        values["roc_auc"].append(roc_auc_score(y[index], score[index]))
        values["pr_auc"].append(average_precision_score(y[index], score[index]))
    return {key: [float(np.quantile(value, 0.025)), float(np.quantile(value, 0.975))] for key, value in values.items()}


def _current_suppression(candidates: pd.DataFrame) -> pd.DataFrame:
    """Remove current known outcomes and public listings from live triage only.

    This current-state lookup is deliberately not used for historical training
    or validation. It is an operational safeguard for the live candidate list.
    """
    out = candidates.copy()
    out["suppression_reason"] = ""
    if CURRENT_MASTER.exists():
        master = pd.read_csv(CURRENT_MASTER, low_memory=False)
        master["company_key"] = master["company"].map(canonical_name)
        counts = master.groupby("company_key").size()
        known = set(master.loc[(master["is_unicorn_history"].eq(1)) & master.company_key.map(counts).eq(1), "company_key"])
        out.loc[out.company_key.isin(known), "suppression_reason"] = "known_unicorn_or_former_unicorn_in_current_master"
    # Current exchange tickers indicate that the entity is no longer a private
    # company. This is a triage rule, not a historical model feature.
    public_pattern = r"\((?:NASDAQ(?:GM|CM)?|NYSE|AMEX|LSE|ASX|TSX|TSE|HKEX|KOSDAQ|SSE|SZSE|BSE|NSEI):"
    public_mask = out.company.str.contains(public_pattern, flags=re.IGNORECASE, regex=True, na=False)
    out.loc[public_mask & out.suppression_reason.eq(""), "suppression_reason"] = "currently_tickered_public_entity"
    return out


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    rounds = read_reports()
    table = build_table(rounds)
    table.to_csv(OUT / "second_financing_snapshots.csv", index=False, date_format="%Y-%m-%d")
    eligible = table[table.label_state.isin(["observed_positive", "observed_no_future_outcome"])].copy()
    # Fixed temporal protocol, chosen before candidate-model comparison. Since
    # this provisional model emits a rank (not a probability), it has no
    # calibration set.  2021–2022 remains untouched until final reporting.
    splits = {"train": eligible.prediction_year.le(2019), "validation": eligible.prediction_year.eq(2020), "final": eligible.prediction_year.isin([2021, 2022])}
    for name, mask in splits.items():
        if eligible.loc[mask, "target"].nunique() != 2:
            raise ObservedDataError(f"{name} period has not both observed outcome classes")
    candidate_metrics, fitted = {}, {}
    for kind in ("logistic", "random_forest"):
        model = _model(kind).fit(eligible.loc[splits["train"], NUMERIC], eligible.loc[splits["train"], "target"])
        probability = model.predict_proba(eligible.loc[splits["validation"], NUMERIC])[:, 1]
        candidate_metrics[kind] = _metrics(eligible.loc[splits["validation"], "target"], probability)
        fitted[kind] = model
    selected_name = max(candidate_metrics, key=lambda name: candidate_metrics[name]["pr_auc"])
    selected = fitted[selected_name]
    final_score = selected.predict_proba(eligible.loc[splits["final"], NUMERIC])[:, 1]
    final = eligible.loc[splits["final"], ["company", "company_key", "prediction_date", "target", "label_state"]].copy()
    final["ranking_score"] = final_score
    final = final.sort_values("ranking_score", ascending=False)
    final.to_csv(OUT / "final_2021_2022_ranked_predictions.csv", index=False)
    artifact = {"pipeline": selected, "features": NUMERIC, "scope": "transaction-observed 3-year ranking; not a population probability", "training_years": [2010, 2019]}
    joblib.dump(artifact, MODEL_DIR / "capitaliq_transaction_observed_ranker.joblib")
    # Companies with a second round in the latest three observed years cannot
    # yet be assigned an outcome label. They are the legitimate live scoring
    # population for this ranking tool, after excluding known-at-snapshot $1B
    # events. Older incomplete records are not silently treated as candidates.
    extraction_date = rounds.event_date.max()
    candidate_start = extraction_date - pd.DateOffset(years=3)
    candidates = table[(table.label_state == "insufficient_followup") & table.prediction_date.ge(candidate_start)].copy()
    candidates["ranking_score"] = selected.predict_proba(candidates[NUMERIC])[:, 1] if not candidates.empty else np.array([])
    candidates = _current_suppression(candidates).sort_values("ranking_score", ascending=False)
    candidates.to_csv(OUT / "current_candidate_suppression_audit.csv", index=False)
    live_candidates = candidates[candidates.suppression_reason.eq("")].copy()
    live_candidates[["company", "company_key", "prediction_date", "horizon_end", "ranking_score", "label_state"]].to_csv(OUT / "current_candidates_ranked.csv", index=False)
    ablations = {}
    for family, features in FEATURE_FAMILIES.items():
        model = _model("random_forest", features).fit(eligible.loc[splits["train"], features], eligible.loc[splits["train"], "target"])
        score = model.predict_proba(eligible.loc[splits["validation"], features])[:, 1]
        ablations[family] = _metrics(eligible.loc[splits["validation"], "target"], score)
    pd.DataFrame([{"feature_family": family, **metrics} for family, metrics in ablations.items()]).to_csv(OUT / "validation_feature_ablations.csv", index=False)
    if selected_name == "random_forest":
        importance = pd.DataFrame({"feature": NUMERIC, "importance": selected.named_steps["model"].feature_importances_}).sort_values("importance", ascending=False)
        importance.to_csv(OUT / "selected_model_feature_importance.csv", index=False)
    report = {
        "scope": "Ranks second observed financings by the chance of a subsequently observed $1B valuation/private-placement event within three years. It is not a certified unicorn probability or a verified-negative classifier.",
        "data": {"rounds": int(len(rounds)), "unambiguous_companies": int(rounds.company_key.nunique()), "snapshots": int(len(table)), "eligible_observed_rows": int(len(eligible)), "observed_positive": int(eligible.target.sum()), "observed_non_event_with_followup": int((eligible.target == 0).sum())},
        "current_candidate_scoring": {"as_of_transaction_date": str(extraction_date.date()), "candidate_prediction_start": str(candidate_start.date()), "candidate_snapshots_before_current_state_suppression": int(len(candidates)), "ranked_private_candidates": int(len(live_candidates)), "suppression_reasons": {str(key): int(value) for key, value in candidates.loc[candidates.suppression_reason.ne(""), "suppression_reason"].value_counts().items()}, "output": "data/layer_b_v2/transaction_observed/current_candidates_ranked.csv"},
        "label_states": {key: int(value) for key, value in table.label_state.value_counts().items()},
        "splits": {name: {"rows": int(mask.sum()), "positives": int(eligible.loc[mask, "target"].sum())} for name, mask in splits.items()},
        "validation_candidates": candidate_metrics,
        "validation_feature_family_ablations": ablations,
        "selected_model": selected_name,
        "final_2021_2022": {
            "metrics": _metrics(eligible.loc[splits["final"], "target"], final_score),
            "bootstrap_95_ci": _bootstrap_ci(eligible.loc[splits["final"], "target"].reset_index(drop=True), final_score),
            "decision_metrics": _decision_metrics(eligible.loc[splits["final"], "target"].reset_index(drop=True), final_score),
        },
        "release_gate": "Do not report ranking scores as probabilities. Replace this provisional model with the coverage-aware v2 model when coverage and lifecycle histories are supplied.",
    }
    (OUT / "model_card.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
