"""Coverage-aware, fixed-horizon Layer B model pipeline.

This module intentionally refuses to manufacture negatives from an incomplete
transaction export.  It consumes four history-complete Capital IQ extracts in
``data/layer_b_v2/raw`` (companies, transactions, valuations, lifecycle),
builds company-specific funding snapshots, and labels the observed three-year
outcome only where coverage reaches the full horizon.

The vendor headers vary by export template.  The normalizer accepts common
Capital IQ names, but records the source columns used in the input manifest.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
V2 = ROOT / "data" / "layer_b_v2"
RAW = V2 / "raw"
INTERMEDIATE = V2 / "intermediate"
SNAPSHOTS = V2 / "snapshots"
RESULTS = V2 / "results"
HORIZON_YEARS = 3
ONE_BILLION_USD = 1_000_000_000.0


class DataContractError(ValueError):
    """Raised when an extract cannot support the promised model population."""


def read_export_manifest() -> dict:
    """Require provenance and as-of information alongside the raw extracts."""
    path = RAW / "export_manifest.json"
    if not path.exists():
        raise DataContractError(f"Missing required export manifest: {path.relative_to(ROOT)}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DataContractError(f"Invalid export manifest JSON: {error}") from error
    required = {"extract_as_of_date", "files"}
    missing = required.difference(manifest)
    if missing:
        raise DataContractError(f"Export manifest is missing {sorted(missing)}")
    if pd.isna(pd.to_datetime(manifest["extract_as_of_date"], errors="coerce")):
        raise DataContractError("Export manifest extract_as_of_date is not a valid date")
    required_files = {"companies.csv", "transactions.csv", "valuations.csv", "lifecycle.csv"}
    declared = set(manifest["files"])
    if not required_files.issubset(declared):
        raise DataContractError(f"Export manifest must describe {sorted(required_files)}")
    return manifest


def _pick(frame: pd.DataFrame, names: Iterable[str], required: bool = True) -> str | None:
    lookup = {str(column).strip().casefold(): column for column in frame.columns}
    for name in names:
        if name.casefold() in lookup:
            return lookup[name.casefold()]
    if required:
        raise DataContractError(f"Missing required column; expected one of {list(names)}")
    return None


def _date(frame: pd.DataFrame, names: Iterable[str], required: bool = True) -> pd.Series:
    column = _pick(frame, names, required=required)
    return pd.to_datetime(frame[column], errors="coerce") if column else pd.Series(pd.NaT, index=frame.index)


def _number(frame: pd.DataFrame, names: Iterable[str]) -> pd.Series:
    column = _pick(frame, names, required=False)
    if not column:
        return pd.Series(np.nan, index=frame.index)
    return pd.to_numeric(frame[column].astype(str).str.replace(",", "", regex=False), errors="coerce")


def _usd(frame: pd.DataFrame, names: Iterable[str]) -> pd.Series:
    """Normalize either a direct-USD or a Capital IQ USD-millions column."""
    column = _pick(frame, names, required=False)
    if not column:
        return pd.Series(np.nan, index=frame.index)
    value = pd.to_numeric(frame[column].astype(str).str.replace(",", "", regex=False), errors="coerce")
    return value * 1e6 if "usdmm" in str(column).casefold() else value


def _text(frame: pd.DataFrame, names: Iterable[str], default: str = "Unknown") -> pd.Series:
    column = _pick(frame, names, required=False)
    if not column:
        return pd.Series(default, index=frame.index)
    return frame[column].fillna(default).astype(str).str.strip().replace("", default)


def _read_csv(name: str) -> pd.DataFrame:
    path = RAW / name
    if not path.exists():
        raise DataContractError(f"Missing required history-complete extract: {path.relative_to(ROOT)}")
    return pd.read_csv(path, low_memory=False)


def normalize_companies(frame: pd.DataFrame) -> pd.DataFrame:
    company_id = _pick(frame, ["CIQ Company ID", "Company ID", "Capital IQ Company ID", "company_id"])
    out = pd.DataFrame({
        "company_id": frame[company_id].astype(str).str.strip(),
        "company_name": _text(frame, ["Company Name", "Company", "Target/Issuer", "company_name"]),
        "industry": _text(frame, ["Industry", "Industry Group", "Primary Industry", "industry"]),
        "country": _text(frame, ["Country/Region", "Country", "Headquarters Country", "country"]),
        "founded_date": _date(frame, ["Founded Date", "Date Founded", "Incorporation Date", "founded_date"], required=False),
        "coverage_start": _date(frame, ["Coverage Start Date", "Coverage Start", "coverage_start"]),
        "coverage_end": _date(frame, ["Coverage End Date", "Coverage End", "Last Verified Date", "coverage_end"]),
        "current_status": _text(frame, ["Company Status", "Status", "current_status"]),
    })
    out = out[out.company_id.ne("")].drop_duplicates("company_id", keep="last")
    if out.coverage_start.isna().all():
        raise DataContractError("Company extract has no usable coverage start dates")
    if out.coverage_end.isna().all():
        raise DataContractError("Company extract has no usable coverage end dates")
    return out.reset_index(drop=True)


def normalize_transactions(frame: pd.DataFrame) -> pd.DataFrame:
    company_id = _pick(frame, ["CIQ Company ID", "Target/Issuer CIQ Company ID", "Company ID", "company_id"])
    transaction_id = _pick(frame, ["CIQ Transaction ID", "Transaction ID", "transaction_id"])
    announced = _date(frame, ["All Transactions Announced Date", "Announced Date", "announced_date"], required=False)
    closed = _date(frame, ["All Transactions Closed Date", "Closed Date", "closed_date"], required=False)
    out = pd.DataFrame({
        "company_id": frame[company_id].astype(str).str.strip(),
        "transaction_id": frame[transaction_id].astype(str).str.strip(),
        "event_date": closed.fillna(announced),
        "transaction_type": _text(frame, ["Transaction Types", "Transaction Type", "Round Type", "transaction_type"]),
        "status": _text(frame, ["Transaction Status", "Status", "transaction_status"]),
        "amount_usd": _usd(frame, ["Total Transaction Value ($USDmm, Historical rate)", "Transaction Value ($USDmm, Historical rate)", "Amount (USD)", "amount_usd"]),
        "post_money_usd": _usd(frame, ["Post-Money Valuation ($USDmm, Historical rate)", "Post-Money Valuation (USD)", "post_money_usd"]),
        "source_date": _date(frame, ["Source Date", "Last Verified Date", "source_date"], required=False),
    })
    out = out[(out.company_id.ne("")) & out.event_date.notna() & out.transaction_id.ne("")]
    return out.drop_duplicates("transaction_id", keep="last").reset_index(drop=True)


def normalize_valuations(frame: pd.DataFrame) -> pd.DataFrame:
    company_id = _pick(frame, ["CIQ Company ID", "Company ID", "company_id"])
    out = pd.DataFrame({
        "company_id": frame[company_id].astype(str).str.strip(),
        "valuation_date": _date(frame, ["Valuation Date", "As Of Date", "Date", "valuation_date"]),
        "value_usd": _usd(frame, ["Valuation ($USDmm, Historical rate)", "Valuation (USD)", "value_usd"]),
        "source_date": _date(frame, ["Source Date", "Last Verified Date", "source_date"], required=False),
    })
    return out[(out.company_id.ne("")) & out.valuation_date.notna()].reset_index(drop=True)


def normalize_lifecycle(frame: pd.DataFrame) -> pd.DataFrame:
    company_id = _pick(frame, ["CIQ Company ID", "Company ID", "company_id"])
    out = pd.DataFrame({
        "company_id": frame[company_id].astype(str).str.strip(),
        "event_date": _date(frame, ["Event Date", "Effective Date", "Closed Date", "event_date"]),
        "event_type": _text(frame, ["Event Type", "Lifecycle Event", "Status", "event_type"]),
        "source_date": _date(frame, ["Source Date", "Last Verified Date", "source_date"], required=False),
    })
    return out[(out.company_id.ne("")) & out.event_date.notna()].reset_index(drop=True)


def _first_unicorn_event(transactions: pd.DataFrame, valuations: pd.DataFrame) -> pd.DataFrame:
    transaction_events = transactions.loc[transactions.post_money_usd.ge(ONE_BILLION_USD), ["company_id", "event_date"]]
    valuation_events = valuations.loc[valuations.value_usd.ge(ONE_BILLION_USD), ["company_id", "valuation_date"]].rename(columns={"valuation_date": "event_date"})
    events = pd.concat([transaction_events, valuation_events], ignore_index=True)
    return events.groupby("company_id", as_index=False).event_date.min().rename(columns={"event_date": "first_unicorn_date"})


def build_snapshots(companies: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    """Use each company's second private-placement event as the landmark."""
    private = transactions[transactions.transaction_type.str.contains("private placement", case=False, na=False)].copy()
    private = private.sort_values(["company_id", "event_date", "transaction_id"])
    private["financing_number"] = private.groupby("company_id").cumcount() + 1
    landmark = private[private.financing_number.eq(2)][["company_id", "event_date"]].rename(columns={"event_date": "prediction_date"})
    snapshots = landmark.merge(companies, on="company_id", how="inner", validate="one_to_one")
    snapshots["horizon_end"] = snapshots.prediction_date + pd.DateOffset(years=HORIZON_YEARS)
    return snapshots


def label_snapshots(snapshots: pd.DataFrame, transactions: pd.DataFrame, valuations: pd.DataFrame, lifecycle: pd.DataFrame) -> pd.DataFrame:
    outcomes = _first_unicorn_event(transactions, valuations)
    competing = lifecycle[lifecycle.event_type.str.contains("acquir|ipo|bankrupt|liquidat|clos|inactive", case=False, na=False)]
    competing = competing.groupby("company_id", as_index=False).event_date.min().rename(columns={"event_date": "competing_event_date"})
    out = snapshots.merge(outcomes, on="company_id", how="left").merge(competing, on="company_id", how="left")
    already_unicorn = out.first_unicorn_date.le(out.prediction_date)
    positive_window = out.first_unicorn_date.gt(out.prediction_date) & out.first_unicorn_date.le(out.horizon_end)
    # A record first covered after the decision date cannot establish that a
    # company had no outcome during the horizon, even if its current coverage
    # end date is later than the horizon.
    covered = out.coverage_start.le(out.prediction_date) & out.coverage_end.ge(out.horizon_end)
    competing_window = out.competing_event_date.gt(out.prediction_date) & out.competing_event_date.le(out.horizon_end)
    # A company acquired or closed before its qualifying valuation is a
    # competing outcome, not a later positive label.
    positive = positive_window & (~competing_window | out.first_unicorn_date.lt(out.competing_event_date))
    competing_in_horizon = competing_window & (~positive_window | out.competing_event_date.le(out.first_unicorn_date))
    out["label_state"] = np.select(
        [already_unicorn, positive, competing_in_horizon, covered],
        ["already_unicorn", "positive", "competing", "negative"],
        default="censored",
    )
    out["target"] = np.where(out.label_state.eq("positive"), 1, np.where(out.label_state.eq("negative"), 0, np.nan))
    return out


def make_features(labels: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in labels.itertuples(index=False):
        history = transactions[(transactions.company_id == row.company_id) & (transactions.event_date <= row.prediction_date)].sort_values("event_date")
        feature_max = history.event_date.max() if not history.empty else pd.NaT
        if pd.notna(feature_max) and feature_max > row.prediction_date:
            raise AssertionError("Feature timestamp is after prediction timestamp")
        amounts = history.amount_usd.dropna().clip(lower=0)
        rows.append({
            **row._asdict(),
            "prior_round_count": len(history),
            "prior_funding_usd": float(amounts.sum()),
            "prior_max_round_usd": float(amounts.max()) if not amounts.empty else 0.0,
            "days_since_last_round": int((row.prediction_date - feature_max).days) if pd.notna(feature_max) else -1,
            "company_age_years": max((row.prediction_date - row.founded_date).days / 365.25, 0.0) if pd.notna(row.founded_date) else np.nan,
            "max_feature_event_date": feature_max,
        })
    return pd.DataFrame(rows)


def _manifest(tables: dict[str, pd.DataFrame]) -> dict:
    return {name: {"rows": int(len(frame)), "columns": list(frame.columns)} for name, frame in tables.items()}


def run() -> dict:
    """Build frozen v2 tables.  Does not fit a model until eligibility exists."""
    for directory in (INTERMEDIATE, SNAPSHOTS, RESULTS):
        directory.mkdir(parents=True, exist_ok=True)
    manifest = read_export_manifest()
    companies = normalize_companies(_read_csv("companies.csv"))
    transactions = normalize_transactions(_read_csv("transactions.csv"))
    valuations = normalize_valuations(_read_csv("valuations.csv"))
    lifecycle = normalize_lifecycle(_read_csv("lifecycle.csv"))
    snapshots = build_snapshots(companies, transactions)
    labels = label_snapshots(snapshots, transactions, valuations, lifecycle)
    features = make_features(labels, transactions)
    eligible = features[features.label_state.isin(["positive", "negative"])].copy()
    if eligible.target.nunique() != 2:
        raise DataContractError("Eligible snapshots do not contain both verified positive and negative outcomes")
    for name, frame in {"companies": companies, "transactions": transactions, "valuations": valuations, "lifecycle": lifecycle}.items():
        frame.to_csv(INTERMEDIATE / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    features.to_csv(SNAPSHOTS / "all_landmarks.csv", index=False, date_format="%Y-%m-%d")
    eligible.to_csv(SNAPSHOTS / "eligible_three_year_labels.csv", index=False, date_format="%Y-%m-%d")
    bad = eligible[eligible.max_feature_event_date.notna() & eligible.max_feature_event_date.gt(eligible.prediction_date)]
    if not bad.empty:
        raise AssertionError("Temporal feature audit failed")
    summary = {
        "horizon_years": HORIZON_YEARS,
        "extract_as_of_date": manifest["extract_as_of_date"],
        "tables": _manifest({"companies": companies, "transactions": transactions, "valuations": valuations, "lifecycle": lifecycle}),
        "snapshots": int(len(features)),
        "eligible": int(len(eligible)),
        "positive": int(eligible.target.sum()),
        "negative": int((eligible.target == 0).sum()),
        "censored": int((features.label_state == "censored").sum()),
        "competing": int((features.label_state == "competing").sum()),
        "temporal_feature_violations": int(len(bad)),
    }
    (RESULTS / "build_manifest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
