"""VC Scout ETL Pipeline

Reads the audited startup master, prunes and rebalances the dataset,
applies the funding denomination correction, engineers features, and
writes two clean outputs:

  data/model_ready.csv          — full pruned dataset (classifier use)
  data/model_ready_valuation.csv — unicorn-only rows with valuation target

Control-group cap: controls are downsampled so they are <= 20% of the
final row count. All unicorn and soonicorn rows are kept.
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "vc_scout_revised_results_audit_trail_final" / "vc_scout_final_assets" / "vc_scout_audited_startup_master_final.csv"
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)

RNG = 17

# ── 1. Load ────────────────────────────────────────────────────────────────────
print("Loading audited startup master...")
df = pd.read_csv(MASTER, low_memory=False)
print(f"  Raw rows: {len(df):,}")
print(f"  Tier counts:\n{df['tier'].value_counts().to_string()}\n")

# ── 2. Funding denomination correction ─────────────────────────────────────────
# The expanded builder stored many M-denominated unicorn funding values 1,000x
# too large. Where funding_audited_usd > valuation_usd we halve by 1,000.
unicorn_like = df["tier"].isin(["unicorn_current", "unicorn_delisted", "unicorn_exited"])

has_both = (
    unicorn_like
    & df["valuation_usd"].notna()
    & df["funding_audited_usd"].notna()
    & (df["funding_audited_usd"] > 0)
)
unit_suspect = has_both & (df["funding_audited_usd"] > df["valuation_usd"])
df.loc[unit_suspect, "funding_audited_usd"] = df.loc[unit_suspect, "funding_audited_usd"] / 1_000.0
df.loc[unit_suspect, "funding_audit_flag"] = "unit_corrected_div1000"

n_corrected = int(unit_suspect.sum())
still_bad = has_both & (df["funding_audited_usd"] > df["valuation_usd"])
print(f"Funding correction: {n_corrected:,} rows divided by 1,000")
print(f"  Rows still funding > valuation after correction: {int(still_bad.sum())}")

# ── 3. Feature engineering (shared) ────────────────────────────────────────────
df["founded_year"] = pd.to_numeric(df["founded_year"], errors="coerce")
df["unicorn_year"] = pd.to_numeric(df["unicorn_year"], errors="coerce")
df["years_to_unicorn"] = df["unicorn_year"] - df["founded_year"]

df["era"] = np.select(
    [df["unicorn_year"] <= 2020, df["unicorn_year"] == 2021, df["unicorn_year"] >= 2022],
    ["Pre-2021", "2021", "Post-2021"],
    default="Unknown",
)

df["investor_count"] = pd.to_numeric(df["investor_count"], errors="coerce").fillna(0).astype(int)
df["in_yc"] = df["in_yc"].fillna(False).astype(bool)
df["in_techstars"] = df["in_techstars"].fillna(False).astype(bool)
df["in_500global"] = df["in_500global"].fillna(False).astype(bool)

df["industry_group"] = df["industry_group"].fillna("Unknown").str.strip()
df["continent"] = df["continent"].fillna("Unknown").str.strip()

# ── 4. Control-group downsampling ──────────────────────────────────────────────
# Keep all unicorn + soonicorn rows; sample controls to <= 20% of final total.
# 20% cap:  n_control / (n_keep + n_control) <= 0.20
#           n_control <= n_keep * 0.25

keep_mask = df["tier"].isin(["unicorn_current", "unicorn_delisted", "unicorn_exited", "soonicorn_proxy"])
df_keep = df[keep_mask].copy()
df_control = df[~keep_mask].copy()

n_keep = len(df_keep)
max_control = int(n_keep * 0.25)  # 20% of (n_keep + max_control) => 25% of n_keep
n_control_raw = len(df_control)

if n_control_raw > max_control:
    df_control = df_control.sample(n=max_control, random_state=RNG)
    print(f"\nControl downsampling: {n_control_raw:,} → {max_control:,} rows sampled")
else:
    print(f"\nControl group already within cap ({n_control_raw:,} rows), no sampling needed")

df_full = pd.concat([df_keep, df_control], ignore_index=True)
n_total = len(df_full)
n_ctrl_final = len(df_control)
print(f"  Final dataset: {n_total:,} rows  ({n_ctrl_final:,} control = {n_ctrl_final/n_total*100:.1f}%)")

# ── 5. Save full pruned dataset ────────────────────────────────────────────────
full_out = OUT / "model_ready.csv"
df_full.to_csv(full_out, index=False)
print(f"\nWrote {full_out}  ({len(df_full):,} rows)")

# ── 6. Valuation-regression subset (unicorn rows only) ────────────────────────
# For the ln(valuation) regression we need: valuation, funding > 0,
# years_to_unicorn >= 0, and a known era.

df_val = df_full[unicorn_like.reindex(df_full.index, fill_value=False)].copy()

n_before = len(df_val)
drop_log = {}

# Missing valuation
m = df_val["valuation_usd"].isna() | (df_val["valuation_usd"] <= 0)
drop_log["missing/zero valuation"] = int(m.sum())
df_val = df_val[~m]

# Missing or zero funding
m = df_val["funding_audited_usd"].isna() | (df_val["funding_audited_usd"] <= 0)
drop_log["missing/zero funding"] = int(m.sum())
df_val = df_val[~m]

# Negative years to unicorn
m = df_val["years_to_unicorn"] < 0
drop_log["negative years_to_unicorn"] = int(m.sum())
df_val = df_val[~m]

# Unknown era
m = df_val["era"] == "Unknown"
drop_log["unknown era"] = int(m.sum())
df_val = df_val[~m]

# Unknown industry or continent
m = df_val["industry_group"].isin(["Unknown", ""]) | df_val["continent"].isin(["Unknown", ""])
drop_log["unknown industry/continent"] = int(m.sum())
df_val = df_val[~m]

print(f"\nValuation subset — exclusions from {n_before:,} unicorn rows:")
for reason, n in drop_log.items():
    print(f"  {reason}: {n:,}")
print(f"  Eligible for regression: {len(df_val):,}")

# Log-transform target and funding
df_val["ln_valuation"] = np.log(df_val["valuation_usd"])
df_val["ln_funding"] = np.log(df_val["funding_audited_usd"])

# Validate: no inf / nan in model inputs
MODEL_COLS = ["ln_valuation", "ln_funding", "years_to_unicorn", "investor_count",
              "industry_group", "continent", "era", "in_yc", "in_techstars", "in_500global"]
bad = df_val[MODEL_COLS].isnull().sum()
bad = bad[bad > 0]
if not bad.empty:
    print(f"\nWARNING — nulls remain in model columns:\n{bad}")
else:
    print("\nValidation passed: no nulls in model columns")

val_out = OUT / "model_ready_valuation.csv"
df_val.to_csv(val_out, index=False)
print(f"\nWrote {val_out}  ({len(df_val):,} rows)")

# ── 7. Summary ─────────────────────────────────────────────────────────────────
print("\n── ETL summary ──────────────────────────────────────────────────────────")
print(f"  Source rows:            {len(df):>6,}")
print(f"  After tier filter:      {n_keep:>6,}  (unicorn + soonicorn, all kept)")
print(f"  Control rows sampled:   {n_ctrl_final:>6,}  ({n_ctrl_final/n_total*100:.1f}% of total)")
print(f"  Full pruned dataset:    {n_total:>6,}  → data/model_ready.csv")
print(f"  Valuation-regression:   {len(df_val):>6,}  → data/model_ready_valuation.csv")
print(f"  Funding rows corrected: {n_corrected:>6,}")
