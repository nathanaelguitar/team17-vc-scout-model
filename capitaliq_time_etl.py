"""Leakage-safe Capital IQ round ETL.

This module turns the Capital IQ exports into a company-level classifier table
whose features are computed strictly before an index date.

Positive companies use their first observed private-placement round with a
post-money valuation of at least $1B as the outcome date. Controls are matched
one-to-one to positive companies by an earlier round history and (when the
existing master has a unique match) industry/continent. Control features are
then computed strictly before the matched positive's outcome date.

The raw control export is intentionally used for feature history. Companies
that overlap the positive export are excluded from the negative label pool,
but their sub-$1B rounds remain available as pre-outcome history for positives.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
SILVER_DIR = ROOT / "data" / "silver"
GOLD_DIR = ROOT / "data" / "gold"
MASTER_PATH = ROOT / "data" / "bronze" / "startup_master_bronze.csv"

POSITIVE_PATH = RAW_DIR / "capitaliq_unicorn_private_placements.csv"
CONTROL_RAW_PATH = RAW_DIR / "capitaliq_control_private_placements_raw10k.csv"
CONTROL_SLICE_GLOB = "capitaliq_control_closed_*.csv"

UNICORN_TIERS = {"unicorn_current", "unicorn_delisted", "unicorn_exited"}
ONE_BILLION_USD = 1_000_000_000.0


def canonical_name(value: object) -> str:
    """Create a conservative join key for company-name matching."""

    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = value.lower()
    # Remove legal/entity suffixes, but do not use fuzzy matching: false joins
    # would be more damaging than a missed enrichment.
    value = re.sub(
        r"\b(incorporated|inc|llc|ltd|limited|corp|corporation|co|company|"
        r"technologies|technology|labs|group|holdings|pbc|plc|l\.p\.|lp)\b",
        " ",
        value,
    )
    return re.sub(r"[^a-z0-9]", "", value)


def _header_row(path: Path) -> int:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for i, row in enumerate(csv.reader(handle)):
            if "Target/Issuer" in row:
                return i
    raise ValueError(f"Capital IQ header not found in {path}")


def _investor_count(value: object) -> int:
    if not isinstance(value, str) or not value.strip() or value.strip() == "-":
        return 0
    names = {canonical_name(part) for part in value.split(";")}
    return len({name for name in names if name})


def read_capitaliq(path: Path, source_role: str) -> pd.DataFrame:
    """Read a Capital IQ report and normalize its round-level fields."""

    frame = pd.read_csv(
        path,
        skiprows=_header_row(path),
        low_memory=False,
    )
    target = "Target/Issuer"
    frame = frame[frame[target].notna()].copy()
    frame[target] = frame[target].astype(str).str.strip()
    frame = frame[frame[target].ne("") & ~frame[target].str.startswith("*Denotes")]

    announced = pd.to_datetime(frame["All Transactions Announced Date"], errors="coerce")
    closed = pd.to_datetime(frame["All Transactions Closed Date"], errors="coerce")
    frame["event_date"] = closed.fillna(announced)
    frame["announced_date"] = announced
    frame["closed_date"] = closed
    frame["post_money_usd"] = (
        pd.to_numeric(
            frame["Post-Money Valuation ($USDmm, Historical rate)"], errors="coerce"
        )
        * 1e6
    )
    frame["round_value_usd"] = (
        pd.to_numeric(
            frame["Total Transaction Value ($USDmm, Historical rate)"], errors="coerce"
        )
        * 1e6
    )
    frame["company_name"] = frame[target]
    frame["company_key"] = frame[target].map(canonical_name)
    frame["investor_count"] = frame["Buyers/Investors"].map(_investor_count)
    frame["source_role"] = source_role
    frame["source_file"] = path.name
    frame["transaction_id"] = frame["CIQ Transaction ID"].astype(str)
    frame = frame[frame["event_date"].notna() & frame["company_key"].ne("")].copy()
    return frame.reset_index(drop=True)


def attach_master(frame: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Attach only uniquely matched master metadata; flag ambiguous joins."""

    frame = frame.copy()
    counts = master.groupby("company_key").size()
    unique = master[
        master["company_key"].ne("")
        & master["company_key"].map(counts).eq(1)
    ].copy()
    lookup = unique.set_index("company_key")
    ambiguous = set(counts[counts.gt(1)].index)

    frame["master_match_status"] = np.select(
        [frame["company_key"].isin(ambiguous), frame["company_key"].isin(lookup.index)],
        ["ambiguous", "exact_unique"],
        default="unmatched",
    )
    for source, output in (
        ("company", "master_company"),
        ("tier", "master_tier"),
        ("industry_group", "master_industry_group"),
        ("continent", "master_continent"),
        ("country", "master_country"),
        ("founded_year", "master_founded_year"),
    ):
        frame[output] = frame["company_key"].map(lookup[source])
    return frame


def _company_summary(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    return (
        frame.groupby("company_key", as_index=False)
        .agg(
            company_name=("company_name", "first"),
            first_date=("event_date", "min"),
            last_date=("event_date", "max"),
            round_count=("company_key", "size"),
            master_match_status=("master_match_status", "first"),
            master_company=("master_company", "first"),
            master_tier=("master_tier", "first"),
            industry_group=("master_industry_group", "first"),
            continent=("master_continent", "first"),
            country=("master_country", "first"),
            founded_year=("master_founded_year", "first"),
        )
        .rename(
            columns={
                "first_date": f"first_{prefix}_date",
                "last_date": f"last_{prefix}_date",
                "round_count": f"{prefix}_round_count",
            }
        )
    )


def _match_controls(
    positives: pd.DataFrame, controls: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create deterministic one-to-one controls with available pre-index history.

    A control only needs at least one round before the positive's index date;
    later rounds are ignored by the feature cutoff. Selecting the latest
    eligible control round would make recency a property of the matching
    algorithm, so the final tie-break uses company key instead.
    """

    available = set(controls.index)
    matches: list[dict[str, object]] = []
    unmatched: list[dict[str, object]] = []

    ordered = positives.sort_values(["outcome_date", "company_key"])
    for _, positive in ordered.iterrows():
        candidate = controls.loc[list(available)]
        candidate = candidate[
            candidate["first_control_date"] < positive["outcome_date"]
        ]
        if candidate.empty:
            unmatched.append(
                {
                    "positive_company_key": positive["company_key"],
                    "positive_company": positive["company_name"],
                    "outcome_date": positive["outcome_date"],
                    "reason": "no_control_with_pre_index_history",
                }
            )
            continue

        method = "date_only"
        for fields, label in (
            (("industry_group", "continent"), "industry_continent"),
            (("industry_group",), "industry"),
            (("continent",), "continent"),
        ):
            narrowed = candidate.copy()
            usable = True
            for field in fields:
                value = positive[field]
                if pd.isna(value) or value in {"", "Unknown", "Other / Unknown"}:
                    usable = False
                    break
                narrowed = narrowed[narrowed[field] == value]
            if usable and not narrowed.empty:
                candidate = narrowed
                method = label
                break

        # Do not select on last-round date or round count: either would make a
        # feature partly encode the control-sampling procedure.
        chosen = candidate.sort_values("company_key").iloc[0]
        control_index = chosen.name
        available.remove(control_index)
        matches.append(
            {
                "positive_company_key": positive["company_key"],
                "control_company_key": chosen["company_key"],
                "positive_company": positive["company_name"],
                "control_company": chosen["company_name"],
                "index_date": positive["outcome_date"],
                "outcome_date": positive["outcome_date"],
                "match_method": method,
                "match_gap_days": int(
                    (positive["outcome_date"] - chosen["first_control_date"]).days
                ),
            }
        )

    return pd.DataFrame(matches), pd.DataFrame(unmatched)


def _history_features(rounds: pd.DataFrame, company_key: str, index_date: pd.Timestamp) -> dict:
    history = rounds[
        (rounds["company_key"] == company_key) & (rounds["event_date"] < index_date)
    ].sort_values("event_date")
    if history.empty:
        return {
            "pre_round_count": 0,
            "pre_rounds_with_amount": 0,
            "pre_funding_total_usd": 0.0,
            "pre_funding_max_usd": 0.0,
            "pre_last_post_money_usd": 0.0,
            "pre_max_post_money_usd": 0.0,
            "pre_unique_investor_count": 0,
            "pre_investor_count_max": 0,
            "years_of_history_pre": 0.0,
            "days_since_last_pre_round": -1,
            "max_feature_round_date": pd.NaT,
        }

    amounts = history["round_value_usd"].dropna()
    investors: set[str] = set()
    for value in history["Buyers/Investors"].fillna(""):
        if isinstance(value, str):
            investors.update(
                key for key in (canonical_name(x) for x in value.split(";")) if key
            )
    first_date = history["event_date"].min()
    last_date = history["event_date"].max()
    positive_amounts = amounts[amounts > 0]
    total = float(positive_amounts.sum()) if not positive_amounts.empty else 0.0
    maximum = float(positive_amounts.max()) if not positive_amounts.empty else 0.0
    post_money = history["post_money_usd"].dropna()
    return {
        "pre_round_count": int(len(history)),
        "pre_rounds_with_amount": int((history["round_value_usd"] > 0).sum()),
        "pre_funding_total_usd": total,
        "pre_funding_max_usd": maximum,
        "pre_last_post_money_usd": float(post_money.iloc[-1]) if not post_money.empty else 0.0,
        "pre_max_post_money_usd": float(post_money.max()) if not post_money.empty else 0.0,
        "pre_unique_investor_count": len(investors),
        "pre_investor_count_max": int(history["investor_count"].max()),
        "years_of_history_pre": max((index_date - first_date).days / 365.25, 0.0),
        "days_since_last_pre_round": max((index_date - last_date).days, 0),
        "max_feature_round_date": last_date,
    }


def run() -> dict:
    """Run the Capital IQ Silver → Gold ETL and return its summary."""

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    if not POSITIVE_PATH.exists() or not CONTROL_RAW_PATH.exists():
        raise FileNotFoundError(
            "Capital IQ raw files are missing. Expected: "
            f"{POSITIVE_PATH.name} and {CONTROL_RAW_PATH.name}"
        )

    positive_raw = read_capitaliq(POSITIVE_PATH, "positive_export")

    # The original control export is capped at 10,000 rows. Date-partitioned
    # exports extend the history without changing the matching or labeling
    # rules. Deduplicate by CIQ transaction ID because the original export can
    # overlap a downloaded date slice.
    control_paths = [CONTROL_RAW_PATH] + sorted(RAW_DIR.glob(CONTROL_SLICE_GLOB))
    control_frames = [
        read_capitaliq(
            path,
            "control_export_raw" if path == CONTROL_RAW_PATH else "control_date_slice",
        )
        for path in control_paths
    ]
    control_raw = (
        pd.concat(control_frames, ignore_index=True, sort=False)
        .drop_duplicates(subset=["transaction_id"], keep="first")
        .reset_index(drop=True)
    )

    # The positive export is an outcome screen. The raw control export is the
    # history source and negative pool; strict thresholds remove rounded $1B
    # rows that Capital IQ included despite the UI's "less than" selection.
    positive = positive_raw[positive_raw["post_money_usd"] >= ONE_BILLION_USD].copy()
    low_rounds = control_raw[control_raw["post_money_usd"] < ONE_BILLION_USD].copy()
    low_rounds = low_rounds[low_rounds["post_money_usd"].notna()].copy()

    if MASTER_PATH.exists():
        master = pd.read_csv(MASTER_PATH, low_memory=False)
    else:
        raise FileNotFoundError(f"Bronze master missing: {MASTER_PATH}")
    master["company_key"] = master["company"].map(canonical_name)

    positive = attach_master(positive, master)
    low_rounds = attach_master(low_rounds, master)

    positive_keys = set(positive["company_key"])
    low_rounds["known_unicorn_master"] = low_rounds["master_tier"].isin(UNICORN_TIERS)

    # All normalized round-level records used for history. Positive outcome
    # rows remain in the silver table, but are naturally excluded by the
    # strict-before index-date rule when constructing features.
    silver_rounds = pd.concat([positive, low_rounds], ignore_index=True, sort=False)
    silver_rounds["round_label"] = (silver_rounds["post_money_usd"] >= ONE_BILLION_USD).astype(int)
    silver_rounds.to_csv(SILVER_DIR / "capitaliq_rounds_silver.csv", index=False)

    positive_companies = (
        _company_summary(positive, "positive")
        .rename(columns={"first_positive_date": "outcome_date"})
    )
    positive_companies["positive_round_count"] = positive_companies["positive_round_count"]

    control_candidates = low_rounds[
        ~low_rounds["company_key"].isin(positive_keys)
        & ~low_rounds["known_unicorn_master"]
    ].copy()
    control_companies = _company_summary(control_candidates, "control").rename(
        columns={
            "first_control_date": "first_control_date",
            "last_control_date": "last_control_date",
        }
    )

    # Company-level match audit across both source exports.
    audit_cols = [
        "company_key", "company_name", "master_match_status", "master_company",
        "master_tier", "master_industry_group", "master_continent", "master_country",
        "master_founded_year",
    ]
    audit = pd.concat(
        [positive[audit_cols].assign(source_role="positive_export"),
         low_rounds[audit_cols].assign(source_role="control_export_raw")],
        ignore_index=True,
    ).drop_duplicates(["source_role", "company_key"])
    audit = audit.rename(
        columns={
            "master_industry_group": "industry_group",
            "master_continent": "continent",
            "master_country": "country",
            "master_founded_year": "founded_year",
        }
    )
    audit["positive_export_company"] = audit["company_key"].isin(positive_keys)
    audit["known_unicorn_master"] = audit["master_tier"].isin(UNICORN_TIERS)
    audit.to_csv(SILVER_DIR / "capitaliq_company_match_audit.csv", index=False)

    matches, unmatched = _match_controls(positive_companies, control_companies)
    matches.to_csv(SILVER_DIR / "capitaliq_control_matches.csv", index=False)
    unmatched.to_csv(SILVER_DIR / "capitaliq_unmatched_positives.csv", index=False)

    # Round history is only allowed to come from sub-$1B control-export rows.
    history_rounds = low_rounds.copy()
    grouped = {key: group for key, group in history_rounds.groupby("company_key")}
    master_by_key = (
        master[master["company_key"].ne("")]
        .drop_duplicates("company_key")
        .set_index("company_key")
    )

    feature_rows: list[dict[str, object]] = []
    for _, positive_row in positive_companies.iterrows():
        key = positive_row["company_key"]
        index_date = positive_row["outcome_date"]
        features = _history_features(history_rounds, key, index_date)
        feature_rows.append(
            {
                "company": positive_row["company_name"],
                "company_key": key,
                "is_unicorn": 1,
                "label_source": "capitaliq_post_money_ge_1b",
                "index_date": index_date,
                "outcome_date": index_date,
                "matched_positive_company": positive_row["company_name"],
                "match_method": "positive_self",
                "match_gap_days": 0,
                **features,
                "master_match_status": positive_row["master_match_status"],
                "master_tier": positive_row["master_tier"],
                "industry_group": positive_row["industry_group"],
                "continent": positive_row["continent"],
                "country": positive_row["country"],
                "founded_year": positive_row["founded_year"],
            }
        )

    control_lookup = control_companies.set_index("company_key")
    for _, match in matches.iterrows():
        control_key = match["control_company_key"]
        positive_key = match["positive_company_key"]
        control = control_lookup.loc[control_key]
        index_date = pd.Timestamp(match["index_date"])
        features = _history_features(history_rounds, control_key, index_date)
        feature_rows.append(
            {
                "company": control["company_name"],
                "company_key": control_key,
                "is_unicorn": 0,
                "label_source": "capitaliq_below_1b_matched_control",
                "index_date": index_date,
                "outcome_date": pd.NaT,
                "matched_positive_company": match["positive_company"],
                "match_method": f"control_{match['match_method']}",
                "match_gap_days": int(match["match_gap_days"]),
                **features,
                "master_match_status": control["master_match_status"],
                "master_tier": control["master_tier"],
                "industry_group": control["industry_group"],
                "continent": control["continent"],
                "country": control["country"],
                "founded_year": control["founded_year"],
            }
        )

    gold = pd.DataFrame(feature_rows)
    gold["index_date"] = pd.to_datetime(gold["index_date"])
    gold["outcome_date"] = pd.to_datetime(gold["outcome_date"])
    gold["index_year"] = gold["index_date"].dt.year.astype(int)
    gold["index_era"] = np.select(
        [gold["index_year"] <= 2020, gold["index_year"] == 2021, gold["index_year"] >= 2022],
        ["Pre-2021", "2021", "Post-2021"],
        default="Unknown",
    )
    gold["has_pre_round"] = (gold["pre_round_count"] > 0).astype(int)
    gold["ln_pre_funding"] = np.log1p(gold["pre_funding_total_usd"])
    gold["ln_pre_funding_max"] = np.log1p(gold["pre_funding_max_usd"])
    gold["industry_group"] = gold["industry_group"].fillna("Unknown").replace("", "Unknown")
    gold["continent"] = gold["continent"].fillna("Unknown").replace("", "Unknown")
    gold["master_match_status"] = gold["master_match_status"].fillna("unmatched")
    gold["master_tier"] = gold["master_tier"].fillna("unmatched")
    gold["founded_year"] = pd.to_numeric(gold["founded_year"], errors="coerce")
    gold["has_founded_year"] = gold["founded_year"].notna().astype(int)
    gold["founded_year"] = gold["founded_year"].fillna(-1).astype(int)
    gold["pre_round_count"] = gold["pre_round_count"].astype(int)

    # The hard leakage check: every round used in a feature row is strictly
    # earlier than that row's index date. No outcome valuation is a feature.
    bad = gold[
        gold["max_feature_round_date"].notna()
        & ~(pd.to_datetime(gold["max_feature_round_date"]) < gold["index_date"])
    ]
    if not bad.empty:
        raise AssertionError(f"Temporal leakage detected in {len(bad)} feature rows")

    # Helpful ordering for downstream model code and human inspection.
    ordered = [
        "company", "company_key", "is_unicorn", "label_source", "index_date", "outcome_date",
        "matched_positive_company", "match_method", "match_gap_days", "index_year", "index_era",
        "pre_round_count", "has_pre_round", "pre_rounds_with_amount", "pre_funding_total_usd",
        "ln_pre_funding", "pre_funding_max_usd", "ln_pre_funding_max", "pre_last_post_money_usd",
        "pre_max_post_money_usd", "pre_unique_investor_count", "pre_investor_count_max",
        "years_of_history_pre", "days_since_last_pre_round", "max_feature_round_date",
        "industry_group", "continent", "country", "founded_year", "has_founded_year",
        "master_match_status", "master_tier",
    ]
    gold = gold[ordered]
    gold_path = GOLD_DIR / "capitaliq_classifier_time_safe.csv"
    gold.to_csv(gold_path, index=False, date_format="%Y-%m-%d")

    summary = {
        "positive_round_rows": int(len(positive)),
        "positive_companies": int(len(positive_companies)),
        "raw_control_round_rows": int(len(control_raw)),
        "control_source_files": [path.name for path in control_paths],
        "eligible_sub_1b_history_round_rows": int(len(low_rounds)),
        "control_candidate_companies": int(len(control_companies)),
        "known_unicorn_control_rows_excluded": int(
            low_rounds[low_rounds["known_unicorn_master"]].shape[0]
        ),
        "positive_companies_with_pre_rounds": int(
            sum(row["pre_round_count"] > 0 for row in feature_rows if row["is_unicorn"] == 1)
        ),
        "matched_control_companies": int(len(matches)),
        "unmatched_positive_companies": int(len(unmatched)),
        "gold_rows": int(len(gold)),
        "gold_positive_rows": int((gold["is_unicorn"] == 1).sum()),
        "gold_control_rows": int((gold["is_unicorn"] == 0).sum()),
        "gold_controls_are_one_to_one": bool(
            gold.loc[gold["is_unicorn"] == 0, "matched_positive_company"].is_unique
        ),
        "leakage_check_rows": int(len(bad)),
        "outputs": {
            "rounds_silver": str((SILVER_DIR / "capitaliq_rounds_silver.csv").relative_to(ROOT)),
            "match_audit": str((SILVER_DIR / "capitaliq_company_match_audit.csv").relative_to(ROOT)),
            "control_matches": str((SILVER_DIR / "capitaliq_control_matches.csv").relative_to(ROOT)),
            "unmatched_positives": str((SILVER_DIR / "capitaliq_unmatched_positives.csv").relative_to(ROOT)),
            "classifier_gold": str(gold_path.relative_to(ROOT)),
        },
    }
    (GOLD_DIR / "capitaliq_etl_summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8"
    )

    print("CAPITAL IQ TIME-SAFE ETL")
    print(f"  Positive companies:       {summary['positive_companies']:,}")
    print(f"  Control candidates:       {summary['control_candidate_companies']:,}")
    print(f"  Matched controls:         {summary['matched_control_companies']:,}")
    print(f"  Unmatched positives:      {summary['unmatched_positive_companies']:,}")
    print(f"  Positives with history:   {summary['positive_companies_with_pre_rounds']:,}")
    print(f"  Gold rows:                {summary['gold_rows']:,}")
    print(f"  Leakage-check violations: {summary['leakage_check_rows']:,}")
    print(f"  Written → {gold_path.relative_to(ROOT)}")
    return summary


if __name__ == "__main__":
    run()
