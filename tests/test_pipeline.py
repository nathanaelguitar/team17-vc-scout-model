"""Tests for the Bronze → Silver → Gold ETL pipeline.

Run:  pytest tests/test_pipeline.py -v
Requires the ETL to have been run first (python3 etl.py).
"""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BRONZE_PATH  = ROOT / "data" / "bronze" / "startup_master_bronze.csv"
SILVER_PATH  = ROOT / "data" / "silver" / "signal_silver.csv"
GOLD_VAL     = ROOT / "data" / "gold"   / "valuation_gold.csv"
GOLD_CLS     = ROOT / "data" / "gold"   / "classifier_gold.csv"

UNICORN_TIERS    = {"unicorn_current", "unicorn_delisted", "unicorn_exited"}
ALL_SIGNAL_TIERS = UNICORN_TIERS | {"soonicorn_proxy"}
VALID_ERAS       = {"Pre-2021", "2021", "Post-2021"}
VALID_CONTINENTS = {"North America", "South America", "Europe", "Asia", "Africa", "Oceania"}

GOLD_NUM  = ["ln_funding", "years_to_unicorn", "select_investor_count"]
GOLD_CAT  = ["industry_group", "continent", "era"]
GOLD_BOOL = ["in_yc", "in_techstars", "in_500global"]


@pytest.fixture(scope="module")
def bronze():
    assert BRONZE_PATH.exists(), f"Bronze file missing — run etl.py first: {BRONZE_PATH}"
    return pd.read_csv(BRONZE_PATH, low_memory=False)


@pytest.fixture(scope="module")
def silver():
    assert SILVER_PATH.exists(), f"Silver file missing — run etl.py first: {SILVER_PATH}"
    return pd.read_csv(SILVER_PATH, low_memory=False)


@pytest.fixture(scope="module")
def gold_val():
    assert GOLD_VAL.exists(), f"Gold valuation file missing — run etl.py first: {GOLD_VAL}"
    return pd.read_csv(GOLD_VAL, low_memory=False)


@pytest.fixture(scope="module")
def gold_cls():
    assert GOLD_CLS.exists(), f"Gold classifier file missing — run etl.py first: {GOLD_CLS}"
    return pd.read_csv(GOLD_CLS, low_memory=False)


# ── Bronze tests ──────────────────────────────────────────────────────────────

class TestBronze:
    def test_has_rows(self, bronze):
        assert len(bronze) > 70_000, "Bronze should have 70k+ rows from the audited master"

    def test_has_ingestion_metadata(self, bronze):
        assert "_ingested_at" in bronze.columns
        assert "_source_file" in bronze.columns
        assert bronze["_ingested_at"].notna().all()

    def test_required_columns_present(self, bronze):
        required = [
            "company", "tier", "valuation_b_latest", "funding_audited_usd",
            "industry_group", "continent", "founded_year", "unicorn_year",
            "in_yc", "in_techstars", "in_500global", "investors", "investor_count",
        ]
        missing = [c for c in required if c not in bronze.columns]
        assert not missing, f"Bronze missing columns: {missing}"

    def test_known_tiers_present(self, bronze):
        tiers = set(bronze["tier"].dropna().unique())
        expected = {"unicorn_current", "unicorn_delisted", "unicorn_exited",
                    "soonicorn_proxy", "control_funded", "control_accelerator"}
        assert expected.issubset(tiers), f"Missing tiers: {expected - tiers}"

    def test_spot_check_companies_present(self, bronze):
        companies = set(bronze["company"].dropna())
        for name in ("OpenAI", "Stripe", "ByteDance"):
            assert name in companies, f"Expected company missing from bronze: {name}"


# ── Silver tests ──────────────────────────────────────────────────────────────

class TestSilver:
    def test_only_signal_tiers(self, silver):
        unexpected = set(silver["tier"].unique()) - ALL_SIGNAL_TIERS
        assert not unexpected, f"Silver contains non-signal tiers: {unexpected}"

    def test_no_duplicate_companies(self, silver):
        dupes = silver["company"].duplicated().sum()
        assert dupes == 0, f"Silver has {dupes} duplicate company names"

    def test_no_funding_exceeds_valuation(self, silver):
        unicorn = silver[silver["tier"].isin(UNICORN_TIERS)].copy()
        has_both = (
            unicorn["valuation_b_latest"].notna()
            & unicorn["funding_audited_usd"].notna()
            & (unicorn["funding_audited_usd"] > 0)
        )
        val_usd = unicorn.loc[has_both, "valuation_b_latest"] * 1e9
        fund    = unicorn.loc[has_both, "funding_audited_usd"]
        bad = (fund > val_usd).sum()
        assert bad == 0, f"{bad} unicorn rows still have funding > valuation after correction"

    def test_no_negative_years_to_unicorn(self, silver):
        neg = (silver["years_to_unicorn"] < 0).sum()
        assert neg == 0, f"{neg} rows have negative years_to_unicorn"

    def test_era_values_valid(self, silver):
        era_values = set(silver["era"].dropna().unique())
        unexpected = era_values - VALID_ERAS - {"Unknown"}
        assert not unexpected, f"Unexpected era values: {unexpected}"

    def test_era_consistent_with_unicorn_year(self, silver):
        df = silver.dropna(subset=["unicorn_year", "era"])
        pre  = df[df["era"] == "Pre-2021"]["unicorn_year"]
        boom = df[df["era"] == "2021"]["unicorn_year"]
        post = df[df["era"] == "Post-2021"]["unicorn_year"]
        assert (pre  <= 2020).all(), "Pre-2021 rows have unicorn_year > 2020"
        assert (boom == 2021).all(), "2021 rows have unicorn_year != 2021"
        assert (post >= 2022).all(), "Post-2021 rows have unicorn_year < 2022"

    def test_select_investor_count_bounded(self, silver):
        assert silver["select_investor_count"].min() >= 0
        assert silver["select_investor_count"].max() <= 4, (
            "select_investor_count exceeds 4 — CB Insights source caps at 4 select investors"
        )

    def test_boolean_flags_are_bool(self, silver):
        for col in ("in_yc", "in_techstars", "in_500global"):
            assert silver[col].dtype == bool or silver[col].isin([True, False, 0, 1]).all(), \
                f"{col} contains non-boolean values"

    def test_continent_values_known(self, silver):
        vals = set(silver["continent"].dropna().unique())
        unknown = vals - VALID_CONTINENTS - {"Unknown"}
        assert not unknown, f"Unrecognised continent values: {unknown}"

    def test_quality_flag_columns_present(self, silver):
        for col in ("_flag_long_path", "_flag_missing_valuation", "_flag_invalid_continent"):
            assert col in silver.columns, f"Quality flag column missing: {col}"


# ── Gold: valuation dataset tests ─────────────────────────────────────────────

class TestGoldValuation:
    def test_only_unicorn_tiers(self, gold_val):
        unexpected = set(gold_val["tier"].unique()) - UNICORN_TIERS
        assert not unexpected, f"Non-unicorn tiers in valuation gold: {unexpected}"

    def test_no_nulls_in_model_columns(self, gold_val):
        cols = ["ln_valuation", "ln_funding"] + GOLD_NUM + GOLD_CAT
        null_counts = gold_val[cols].isnull().sum()
        bad = null_counts[null_counts > 0]
        assert bad.empty, f"Nulls in gold model columns:\n{bad}"

    def test_no_infinities(self, gold_val):
        for col in ("ln_valuation", "ln_funding"):
            assert np.isfinite(gold_val[col]).all(), f"Non-finite values in {col}"

    def test_log_valuation_range(self, gold_val):
        # ln($1B) ≈ 20.7,  ln($2T) ≈ 28.3 — anything outside is suspect
        assert gold_val["ln_valuation"].min() >= 20.0,  "ln_valuation below expected minimum"
        assert gold_val["ln_valuation"].max() <= 30.0,  "ln_valuation above expected maximum"

    def test_log_funding_positive(self, gold_val):
        assert (gold_val["ln_funding"] > 0).all(), "ln_funding has non-positive values"

    def test_years_to_unicorn_non_negative(self, gold_val):
        assert (gold_val["years_to_unicorn"] >= 0).all()

    def test_era_values_valid(self, gold_val):
        unexpected = set(gold_val["era"].unique()) - VALID_ERAS
        assert not unexpected, f"Invalid era values in gold: {unexpected}"

    def test_minimum_row_count(self, gold_val):
        # After all filtering we expect at least 800 rows
        assert len(gold_val) >= 800, f"Only {len(gold_val)} rows in valuation gold — expected >= 800"

    def test_industry_group_coverage(self, gold_val):
        # Should have at least 4 distinct industry groups
        n = gold_val["industry_group"].nunique()
        assert n >= 4, f"Only {n} industry groups in gold — expected >= 4"

    def test_no_duplicate_companies(self, gold_val):
        dupes = gold_val["company"].duplicated().sum()
        assert dupes == 0, f"{dupes} duplicate companies in valuation gold"


# ── Gold: classifier dataset tests ────────────────────────────────────────────

class TestGoldClassifier:
    def test_control_group_at_most_20_pct(self, gold_cls):
        n_ctrl = (~gold_cls["tier"].isin(ALL_SIGNAL_TIERS)).sum()
        pct = n_ctrl / len(gold_cls) * 100
        assert pct <= 20.1, f"Control group is {pct:.1f}% — exceeds 20% cap"

    def test_is_unicorn_label_present(self, gold_cls):
        assert "is_unicorn" in gold_cls.columns
        assert set(gold_cls["is_unicorn"].unique()).issubset({0, 1})

    def test_all_signal_tiers_present(self, gold_cls):
        tiers = set(gold_cls["tier"].unique())
        missing = ALL_SIGNAL_TIERS - tiers
        assert not missing, f"Signal tiers missing from classifier gold: {missing}"

    def test_minimum_row_count(self, gold_cls):
        assert len(gold_cls) >= 3_000, f"Only {len(gold_cls)} rows in classifier gold"
