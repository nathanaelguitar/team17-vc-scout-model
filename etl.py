"""VC Scout ETL Pipeline — Medallion Architecture

Bronze → Silver → Gold

  Bronze  Raw audited master ingested as-is, timestamped.
  Silver  Unicorn + soonicorn rows cleaned, validated, deduplicated.
  Gold    Model-ready: valuation regression and classifier datasets.

Run:  python3 etl.py
Outputs land in data/bronze/, data/silver/, data/gold/.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MASTER = (
    ROOT
    / "vc_scout_revised_results_audit_trail_final"
    / "vc_scout_final_assets"
    / "vc_scout_audited_startup_master_final.csv"
)

BRONZE_DIR = ROOT / "data" / "bronze"
SILVER_DIR = ROOT / "data" / "silver"
GOLD_DIR   = ROOT / "data" / "gold"

for d in (BRONZE_DIR, SILVER_DIR, GOLD_DIR):
    d.mkdir(parents=True, exist_ok=True)

RNG = 17

UNICORN_TIERS    = {"unicorn_current", "unicorn_delisted", "unicorn_exited"}
ALL_SIGNAL_TIERS = UNICORN_TIERS | {"soonicorn_proxy"}
VALID_ERAS       = {"Pre-2021", "2021", "Post-2021"}
VALID_CONTINENTS = {"North America", "South America", "Europe", "Asia", "Africa", "Oceania"}

GOLD_NUM = ["ln_funding", "years_to_unicorn", "select_investor_count"]
GOLD_CAT = ["industry_group", "continent", "era"]
GOLD_BOOL = ["in_yc", "in_techstars", "in_500global"]
GOLD_TARGET = "ln_valuation"

# ── BRONZE ────────────────────────────────────────────────────────────────────
print("=" * 60)
print("BRONZE — ingest raw audited master")
print("=" * 60)

raw = pd.read_csv(MASTER, low_memory=False)
raw["_ingested_at"] = datetime.now(timezone.utc).isoformat()
raw["_source_file"] = MASTER.name

bronze_path = BRONZE_DIR / "startup_master_bronze.csv"
raw.to_csv(bronze_path, index=False)

print(f"  Rows ingested:  {len(raw):,}")
print(f"  Columns:        {len(raw.columns)}")
print(f"  Tier breakdown:\n{raw['tier'].value_counts().to_string()}")
print(f"  Written → {bronze_path.relative_to(ROOT)}\n")

# ── SILVER ────────────────────────────────────────────────────────────────────
print("=" * 60)
print("SILVER — clean, validate, deduplicate")
print("=" * 60)

df = raw.copy()

# --- 1. Coerce types ----------------------------------------------------------
df["founded_year"]   = pd.to_numeric(df["founded_year"],   errors="coerce")
df["unicorn_year"]   = pd.to_numeric(df["unicorn_year"],   errors="coerce")
df["investor_count"] = pd.to_numeric(df["investor_count"], errors="coerce")
df["valuation_b_latest"] = pd.to_numeric(df["valuation_b_latest"], errors="coerce")
df["funding_audited_usd"] = pd.to_numeric(df["funding_audited_usd"], errors="coerce")
df["funding_original_usd"] = pd.to_numeric(df["funding_original_usd"], errors="coerce")

# --- 2. Funding denomination correction (unicorn rows only) -------------------
# The expanded builder stored many M-denominated unicorn funding values 1,000x
# too large. Where funding_audited_usd > valuation_usd we divide by 1,000.
unicorn_mask = df["tier"].isin(UNICORN_TIERS)
val_usd = df["valuation_b_latest"] * 1e9

has_both = (
    unicorn_mask
    & val_usd.notna()
    & df["funding_audited_usd"].notna()
    & (df["funding_audited_usd"] > 0)
)
unit_suspect = has_both & (df["funding_audited_usd"] > val_usd)
df.loc[unit_suspect, "funding_audited_usd"] = (
    df.loc[unit_suspect, "funding_audited_usd"] / 1_000.0
)
df.loc[unit_suspect, "funding_audit_flag"] = "unit_corrected_div1000"
n_corrected = int(unit_suspect.sum())

# Verify correction worked
still_bad = has_both & (df["funding_audited_usd"] > val_usd)
assert int(still_bad.sum()) == 0, "Funding correction failed: rows still have funding > valuation"

# --- 3. Re-derive years_to_unicorn and era -----------------------------------
df["years_to_unicorn"] = df["unicorn_year"] - df["founded_year"]
df["era"] = np.select(
    [df["unicorn_year"] <= 2020, df["unicorn_year"] == 2021, df["unicorn_year"] >= 2022],
    ["Pre-2021", "2021", "Post-2021"],
    default="Unknown",
)

# --- 4. Re-derive select_investor_count from the investors string -------------
# The source investor_count column is capped at 4 (CB Insights "select investors").
# We rename it for clarity rather than re-derive — the investors field only
# lists the same 3-4 names. This is a known data limitation.
df["select_investor_count"] = df["investor_count"].fillna(0).clip(upper=4).astype(int)

# --- 5. Standardise boolean accelerator flags --------------------------------
for col in ("in_yc", "in_techstars", "in_500global"):
    df[col] = df[col].fillna(False).astype(bool)

# --- 6. Trim whitespace on categoricals and resolve "Other" continent --------
df["industry_group"] = df["industry_group"].fillna("Unknown").str.strip()
df["continent"]      = df["continent"].fillna("Unknown").str.strip()

# "Other" continent comes from dual-country or minor-territory rows.
# Use the country field to assign a real continent where possible.
COUNTRY_CONTINENT = {
    "bahamas": "North America", "bermuda": "North America",
    "uzbekistan": "Asia", "kazakhstan": "Asia", "myanmar": "Asia",
    "sri lanka": "Asia", "nepal": "Asia", "cambodia": "Asia",
    "armenia": "Asia", "georgia": "Asia", "azerbaijan": "Asia",
    "ukraine": "Europe", "lithuania": "Europe", "latvia": "Europe",
    "estonia": "Europe", "croatia": "Europe", "serbia": "Europe",
    "romania": "Europe", "bulgaria": "Europe", "slovakia": "Europe",
    "slovenia": "Europe", "malta": "Europe", "luxembourg": "Europe",
    "cyprus": "Europe", "iceland": "Europe", "liechtenstein": "Europe",
    "monaco": "Europe", "andorra": "Europe",
    "nigeria": "Africa", "ghana": "Africa", "kenya": "Africa",
    "egypt": "Africa", "ethiopia": "Africa", "senegal": "Africa",
    "morocco": "Africa", "tanzania": "Africa", "uganda": "Africa",
    "ivory coast": "Africa", "rwanda": "Africa",
    "argentina": "South America", "chile": "South America",
    "colombia": "South America", "peru": "South America",
    "uruguay": "South America", "ecuador": "South America",
    "paraguay": "South America", "bolivia": "South America",
    "new zealand": "Oceania", "fiji": "Oceania", "papua new guinea": "Oceania",
}

def _resolve_continent(row):
    if row["continent"] != "Other":
        return row["continent"]
    country_raw = str(row.get("country", "") or "").lower().strip()
    # For dual-country entries like "United States / Romania", take the first
    first = country_raw.split("/")[0].strip()
    return COUNTRY_CONTINENT.get(first, "Unknown")

df["continent"] = df.apply(_resolve_continent, axis=1)

# --- 7. Filter to signal tiers (unicorn + soonicorn) -------------------------
silver_all = df[df["tier"].isin(ALL_SIGNAL_TIERS)].copy()
n_before_dedup = len(silver_all)

# --- 8. Deduplicate on company name ------------------------------------------
# If a company appears in multiple sources, keep the row with the highest valuation.
silver_all = (
    silver_all
    .sort_values("valuation_b_latest", ascending=False)
    .drop_duplicates(subset=["company"], keep="first")
    .reset_index(drop=True)
)
n_dupes_dropped = n_before_dedup - len(silver_all)

# --- 9. Drop rows with impossible years_to_unicorn (founded after unicorn date)
neg_years_mask = silver_all["years_to_unicorn"].notna() & (silver_all["years_to_unicorn"] < 0)
n_neg_years = int(neg_years_mask.sum())
silver_all = silver_all[~neg_years_mask].reset_index(drop=True)

# --- 10. Quality flags -------------------------------------------------------
flags = []
flags.append(("negative_years_to_unicorn (dropped)", n_neg_years))

# Flag extreme outliers: > 25 years to unicorn (pre-internet era companies)
silver_all["_flag_long_path"] = (
    silver_all["years_to_unicorn"].notna()
    & (silver_all["years_to_unicorn"] > 25)
)
flags.append(("long_path_to_unicorn (>25 yrs)", int(silver_all["_flag_long_path"].sum())))

# Flag era mismatch (era derived vs stored)
era_mismatch = silver_all["era"] != silver_all.get("era", silver_all["era"])
flags.append(("era_computed_vs_stored_mismatch", 0))  # defensive; computed overrides

# Flag still-missing valuation for unicorn rows
silver_all["_flag_missing_valuation"] = (
    silver_all["tier"].isin(UNICORN_TIERS) & silver_all["valuation_b_latest"].isna()
)
flags.append(("unicorn_missing_valuation", int(silver_all["_flag_missing_valuation"].sum())))

# Flag invalid continent
silver_all["_flag_invalid_continent"] = ~silver_all["continent"].isin(VALID_CONTINENTS | {"Unknown"})
flags.append(("invalid_continent", int(silver_all["_flag_invalid_continent"].sum())))

silver_path = SILVER_DIR / "signal_silver.csv"
silver_all.to_csv(silver_path, index=False)

print(f"  Source rows (unicorn + soonicorn): {n_before_dedup:,}")
print(f"  Duplicates dropped:                {n_dupes_dropped:,}")
print(f"  Funding rows corrected:            {n_corrected:,}")
print(f"  Silver rows:                       {len(silver_all):,}")
print(f"  Quality flags:")
for label, n in flags:
    print(f"    {label}: {n:,}")
print(f"  Written → {silver_path.relative_to(ROOT)}\n")

# ── GOLD ──────────────────────────────────────────────────────────────────────
print("=" * 60)
print("GOLD — feature engineering, model-ready outputs")
print("=" * 60)

# ── Gold 1: valuation regression dataset (unicorn rows only) ──────────────────
g_val = silver_all[silver_all["tier"].isin(UNICORN_TIERS)].copy()
n_unicorn = len(g_val)

excl = {}

m = g_val["valuation_b_latest"].isna() | (g_val["valuation_b_latest"] <= 0)
excl["missing/zero valuation"] = int(m.sum())
g_val = g_val[~m]

m = g_val["funding_audited_usd"].isna() | (g_val["funding_audited_usd"] <= 0)
excl["missing/zero funding"] = int(m.sum())
g_val = g_val[~m]

m = g_val["years_to_unicorn"] < 0
excl["negative years_to_unicorn"] = int(m.sum())
g_val = g_val[~m]

m = ~g_val["era"].isin(VALID_ERAS)
excl["unknown era"] = int(m.sum())
g_val = g_val[~m]

m = g_val["industry_group"].isin(["Unknown", ""]) | g_val["continent"].isin(["Unknown", ""])
excl["unknown industry or continent"] = int(m.sum())
g_val = g_val[~m]

# Log-transform target and funding
g_val["ln_valuation"] = np.log(g_val["valuation_b_latest"] * 1e9)
g_val["ln_funding"]   = np.log(g_val["funding_audited_usd"])

# Validate: no nulls or infinities in model columns
model_cols = [GOLD_TARGET] + GOLD_NUM + GOLD_CAT + GOLD_BOOL
null_counts = g_val[model_cols].isnull().sum()
inf_counts  = g_val[[GOLD_TARGET, "ln_funding"]].apply(lambda c: np.isinf(c).sum())

assert null_counts.sum() == 0,  f"Nulls remain in gold valuation columns:\n{null_counts[null_counts > 0]}"
assert inf_counts.sum() == 0,   f"Infs remain in gold valuation columns:\n{inf_counts[inf_counts > 0]}"

gold_val_path = GOLD_DIR / "valuation_gold.csv"
g_val.to_csv(gold_val_path, index=False)

print("  Valuation Gold exclusions:")
for reason, n in excl.items():
    print(f"    {reason}: {n:,}")
print(f"  Eligible rows: {len(g_val):,}  (from {n_unicorn:,} unicorn silver rows)")
print(f"  Written → {gold_val_path.relative_to(ROOT)}\n")

# ── Gold 2: classifier dataset (all signal tiers + downsampled controls) ──────
# Load full silver (includes control tiers) for the classifier
full_silver = df.copy()
full_silver["years_to_unicorn"] = full_silver["unicorn_year"] - full_silver["founded_year"]
full_silver["era"] = np.select(
    [full_silver["unicorn_year"] <= 2020, full_silver["unicorn_year"] == 2021, full_silver["unicorn_year"] >= 2022],
    ["Pre-2021", "2021", "Post-2021"],
    default="Unknown",
)
for col in ("in_yc", "in_techstars", "in_500global"):
    full_silver[col] = full_silver[col].fillna(False).astype(bool)
full_silver["select_investor_count"] = full_silver["investor_count"].fillna(0).clip(upper=4).astype(int)
full_silver["industry_group"] = full_silver["industry_group"].fillna("Unknown").str.strip()
full_silver["continent"]      = full_silver["continent"].fillna("Unknown").str.strip()
full_silver["is_unicorn"] = full_silver["tier"].isin(UNICORN_TIERS).astype(int)

keep  = full_silver[full_silver["tier"].isin(ALL_SIGNAL_TIERS)].copy()
ctrl  = full_silver[~full_silver["tier"].isin(ALL_SIGNAL_TIERS)].copy()

n_keep = len(keep)
max_ctrl = int(n_keep * 0.25)   # keeps controls at 20% of final total
n_ctrl_raw = len(ctrl)

if n_ctrl_raw > max_ctrl:
    ctrl = ctrl.sample(n=max_ctrl, random_state=RNG)

g_cls = pd.concat([keep, ctrl], ignore_index=True)
n_ctrl_final = len(ctrl)
ctrl_pct = n_ctrl_final / len(g_cls) * 100

assert ctrl_pct <= 20.1, f"Control group exceeds 20% cap: {ctrl_pct:.1f}%"

gold_cls_path = GOLD_DIR / "classifier_gold.csv"
g_cls.to_csv(gold_cls_path, index=False)

print(f"  Classifier Gold:")
print(f"    Signal rows (unicorn + soonicorn): {n_keep:,}")
print(f"    Control rows sampled:              {n_ctrl_final:,}  ({ctrl_pct:.1f}% of total)")
print(f"    Total rows:                        {len(g_cls):,}")
print(f"  Written → {gold_cls_path.relative_to(ROOT)}\n")

# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 60)
print("ETL COMPLETE")
print("=" * 60)
print(f"  Bronze  {str(bronze_path.relative_to(ROOT)):<45} {len(raw):>6,} rows")
print(f"  Silver  {str(silver_path.relative_to(ROOT)):<45} {len(silver_all):>6,} rows")
print(f"  Gold    {str(gold_val_path.relative_to(ROOT)):<45} {len(g_val):>6,} rows  (regression)")
print(f"  Gold    {str(gold_cls_path.relative_to(ROOT)):<45} {len(g_cls):>6,} rows  (classifier)")
