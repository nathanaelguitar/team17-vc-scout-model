"""Team 17 VC Scout: expanded tiered startup dataset builder.

Merges verified public sources into one master table with tier labels:
  unicorn_current    on the CB Insights live unicorn list (July 2026)
  unicorn_exited     former unicorns with exit outcomes (Wikipedia, CC BY-SA)
  unicorn_delisted   in the team's 2022 snapshot but no longer listed and no
                     recorded exit (fell below $1B, quiet acquisition, rename)
  soonicorn_proxy    non-unicorn with >= $100M total funding (Crunchbase 2015)
  control_funded     funded non-unicorn startups (Crunchbase 2015 export)
  control_accelerator YC / Techstars / 500 Global companies with outcome labels
                     but no public funding amounts

Also writes a unicorn valuation panel (2022 / 2024 / 2025 / 2026 snapshots)
and a current SEC Form D raises table (Q2 2026).
"""
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "expanded"
OUT.mkdir(parents=True, exist_ok=True)
TEAM_CSV = ROOT / "data" / "Unicorn_Companies.csv"

# ------------------------------------------------------------------ helpers
def name_key(s):
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"\b(inc|llc|ltd|corp|co|technologies|technology|labs|group|holdings)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)

def money_b(v):
    """Parse assorted valuation strings into $B float."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).strip().replace("$", "").replace(",", "").strip()
    if not s or s in {"-", "N/A", "nan"}:
        return np.nan
    try:
        return float(s)
    except ValueError:
        m = re.match(r"^([\d.]+)", s)
        return float(m.group(1)) if m else np.nan

CONTINENT = {
    "united states": "North America", "usa": "North America", "canada": "North America",
    "mexico": "North America", "china": "Asia", "india": "Asia", "israel": "Asia",
    "singapore": "Asia", "south korea": "Asia", "japan": "Asia", "hong kong": "Asia",
    "indonesia": "Asia", "vietnam": "Asia", "thailand": "Asia", "malaysia": "Asia",
    "philippines": "Asia", "taiwan": "Asia", "united arab emirates": "Asia",
    "saudi arabia": "Asia", "turkey": "Asia", "pakistan": "Asia", "bangladesh": "Asia",
    "united kingdom": "Europe", "germany": "Europe", "france": "Europe",
    "netherlands": "Europe", "sweden": "Europe", "switzerland": "Europe",
    "spain": "Europe", "italy": "Europe", "ireland": "Europe", "belgium": "Europe",
    "austria": "Europe", "denmark": "Europe", "finland": "Europe", "norway": "Europe",
    "estonia": "Europe", "lithuania": "Europe", "poland": "Europe", "portugal": "Europe",
    "czech republic": "Europe", "luxembourg": "Europe", "croatia": "Europe",
    "greece": "Europe", "romania": "Europe", "russia": "Europe", "ukraine": "Europe",
    "brazil": "South America", "argentina": "South America", "chile": "South America",
    "colombia": "South America", "peru": "South America", "ecuador": "South America",
    "uruguay": "South America", "australia": "Oceania", "new zealand": "Oceania",
    "nigeria": "Africa", "egypt": "Africa", "south africa": "Africa",
    "kenya": "Africa", "senegal": "Africa", "seychelles": "Africa",
}
ISO3_COUNTRY = {
    "USA": "United States", "GBR": "United Kingdom", "CHN": "China", "IND": "India",
    "CAN": "Canada", "DEU": "Germany", "FRA": "France", "ISR": "Israel",
    "ESP": "Spain", "NLD": "Netherlands", "SWE": "Sweden", "CHE": "Switzerland",
    "SGP": "Singapore", "BRA": "Brazil", "AUS": "Australia", "IRL": "Ireland",
    "ITA": "Italy", "JPN": "Japan", "KOR": "South Korea", "FIN": "Finland",
    "DNK": "Denmark", "RUS": "Russia", "BEL": "Belgium", "AUT": "Austria",
    "NOR": "Norway", "MEX": "Mexico", "ARG": "Argentina", "CHL": "Chile",
    "COL": "Colombia", "TUR": "Turkey", "POL": "Poland", "PRT": "Portugal",
    "EST": "Estonia", "HKG": "Hong Kong", "TWN": "Taiwan", "IDN": "Indonesia",
    "NZL": "Oceania", "NGA": "Nigeria", "EGY": "Egypt", "ZAF": "South Africa",
    "ARE": "United Arab Emirates", "UKR": "Ukraine",
}
def continent(country):
    if not isinstance(country, str):
        return "Unknown"
    return CONTINENT.get(country.strip().lower(), "Other")

IND_MAP = [
    ("fintech|finance|financial|payments|insurance|insurtech|banking|lending|crypto|blockchain|web3", "Fintech"),
    ("artificial intelligence|ai|machine learning|data analytics|big data|data management", "AI & Data"),
    ("e-commerce|ecommerce|commerce|retail|marketplace|direct-to-consumer|consumer goods|shopping", "E-commerce & Consumer"),
    ("health|medical|bio|pharma|life science|genomic|dental|care", "Health & Bio"),
    ("cyber|security", "Cybersecurity"),
    ("enterprise|saas|software|internet software|developer|cloud|it |information technology|productivity", "Enterprise Software"),
    ("media|entertainment|gaming|games|music|video|social|content|sports", "Media & Entertainment"),
    ("transport|logistics|supply chain|mobility|automotive|auto |delivery|ride", "Transport & Logistics"),
    ("hardware|semiconductor|robotics|industrial|manufacturing|electronics|iot|aerospace|space|drones", "Hardware & Industrials"),
    ("energy|climate|clean|solar|battery|sustainab", "Energy & Climate"),
    ("edtech|education|learning", "Education"),
    ("real estate|proptech|property|construction|housing", "Real Estate & Construction"),
    ("travel|hospitality|hotel", "Travel & Hospitality"),
    ("food|restaurant|agri|beverage|grocery", "Food & Agriculture"),
    ("hr |human resources|recruit|talent|work|staffing", "HR & Work"),
]
def industry_group(raw):
    if not isinstance(raw, str) or not raw.strip():
        return "Other / Unknown"
    low = " " + raw.lower() + " "
    for pat, grp in IND_MAP:
        if re.search(pat, low):
            return grp
    return "Other / Unknown"

skipped_lines = {}
def read_csv_tolerant(path, **kw):
    n = 0
    def bad(fields):
        nonlocal n
        n += 1
        return None
    df = pd.read_csv(path, engine="python", on_bad_lines=bad, **kw)
    skipped_lines[Path(path).name] = n
    return df

rows = []          # master rows as dicts
summary = {}

# ------------------------------------------------------------------ 1) unicorn snapshots
team = pd.read_csv(TEAM_CSV)
team["nk"] = team["Company"].map(name_key)
team["val_2022"] = team["Valuation"].map(money_b)
team["Funding_B"] = team["Funding"].map(money_b)
team_by_key = team.set_index("nk", drop=False)
team_by_key = team_by_key[~team_by_key.index.duplicated()]

import csv
with open(RAW / "cbinsights_unicorns_2026-07.csv", newline="") as f:
    rdr = list(csv.reader(f))
fixed = [rdr[0]]
for rec in rdr[1:]:
    if len(rec) == 14:          # two companies merged into one table row
        fixed.append(rec[:7]); fixed.append(rec[7:])
    elif len(rec) == 7:
        fixed.append(rec)
live = pd.DataFrame(fixed[1:], columns=fixed[0])
live["nk"] = live["Company"].map(name_key)
live["val_2026"] = live["Valuation ($B)"].map(money_b)
n_bad = int(live["val_2026"].isna().sum())
live = live.dropna(subset=["val_2026"])          # drops the 1 merged-row artifact
live = live[~live["nk"].duplicated()]

snap24 = read_csv_tolerant(RAW / "cbinsights_unicorns_2024.csv", skiprows=1)
snap24["nk"] = snap24["Company"].map(name_key)
snap24["val_2024"] = snap24["Valuation_Billions"].map(money_b)
snap24 = snap24.dropna(subset=["val_2024"])
snap24 = snap24[~snap24["nk"].duplicated()]

snap25 = read_csv_tolerant(RAW / "cbinsights_unicorns_2025-07.csv")
snap25["nk"] = snap25["Company"].map(name_key)
snap25["val_2025"] = snap25["Valuation ($B)"].map(money_b)
snap25 = snap25.dropna(subset=["val_2025"])
snap25 = snap25[~snap25["nk"].duplicated()]

wiki_x = read_csv_tolerant(RAW / "wikipedia_former_unicorns.csv")
wiki_x["nk"] = wiki_x["Company"].map(name_key)
wiki_x["exit_valuation_b"] = wiki_x["Exit valuation (US$ billions)"].map(money_b)
wiki_x["last_val_b"] = wiki_x["Last valuation (US$ billions)"].map(money_b)
wiki_x = wiki_x[~wiki_x["nk"].duplicated()]

# valuation panel
panel = live[["Company", "nk", "val_2026", "Date Joined", "Country", "City", "Industry", "Select Investors"]].copy()
panel = panel.merge(snap25[["nk", "val_2025"]], on="nk", how="outer")
panel = panel.merge(snap24[["nk", "val_2024", "Company"]].rename(columns={"Company": "Company_24"}), on="nk", how="outer")
panel = panel.merge(team[["nk", "val_2022", "Company"]].rename(columns={"Company": "Company_22"}), on="nk", how="outer")
panel["Company"] = panel["Company"].fillna(panel["Company_24"]).fillna(panel["Company_22"])
panel = panel.drop(columns=["Company_24", "Company_22"])
panel = panel[["Company", "nk", "val_2022", "val_2024", "val_2025", "val_2026", "Date Joined", "Country", "City", "Industry", "Select Investors"]]
panel.to_csv(OUT / "unicorn_valuation_panel.csv", index=False)

unicorn_keys = set(live["nk"]) | set(team["nk"]) | set(wiki_x["nk"])

# --- tier: unicorn_current
for _, r in live.iterrows():
    t = team_by_key.loc[r["nk"]] if r["nk"] in team_by_key.index else None
    inv = r.get("Select Investors")
    founded = t["Year Founded"] if t is not None else np.nan
    rows.append({
        "company": r["Company"], "nk": r["nk"], "tier": "unicorn_current",
        "primary_source": "CB Insights unicorn list (2026-07)",
        "valuation_b_latest": r["val_2026"], "valuation_asof": "2026-07",
        "date_joined_unicorn": r["Date Joined"],
        "funding_total_usd": (t["Funding_B"] * 1e9 if t is not None and pd.notna(t["Funding_B"]) else np.nan),
        "industry_raw": r["Industry"], "industry_group": industry_group(r["Industry"]),
        "country": r["Country"], "city": r.get("City"),
        "continent": continent(r["Country"]),
        "founded_year": founded,
        "outcome": "operating",
        "investors": inv,
        "investor_count": len([x for x in str(inv).split(",") if x.strip()]) if isinstance(inv, str) else np.nan,
    })

# --- tier: unicorn_exited
for _, r in wiki_x.iterrows():
    reason = str(r.get("Exit reason", "")).lower()
    outcome = "ipo" if "ipo" in reason else ("acquired" if "acqui" in reason or "merge" in reason else ("closed" if "defunct" in reason or "bankrupt" in reason or "shut" in reason else "exited_other"))
    t = team_by_key.loc[r["nk"]] if r["nk"] in team_by_key.index else None
    rows.append({
        "company": r["Company"], "nk": r["nk"], "tier": "unicorn_exited",
        "primary_source": "Wikipedia former unicorns (CC BY-SA)",
        "valuation_b_latest": r["last_val_b"], "valuation_asof": r.get("Valuation date"),
        "exit_date": r.get("Exit date"), "exit_reason": r.get("Exit reason"),
        "exit_valuation_b": r["exit_valuation_b"],
        "funding_total_usd": (t["Funding_B"] * 1e9 if t is not None and pd.notna(t["Funding_B"]) else np.nan),
        "industry_raw": (t["Industry"] if t is not None else np.nan),
        "industry_group": industry_group(t["Industry"]) if t is not None else "Other / Unknown",
        "country": r.get("Country"), "continent": continent(r.get("Country")),
        "founded_year": (t["Year Founded"] if t is not None else np.nan),
        "outcome": outcome,
        "investors": (t["Select Investors"] if t is not None else np.nan),
    })
exited_keys = set(wiki_x["nk"])

# --- tier: unicorn_delisted (in 2022 file, not on 2026 list, no recorded exit)
current_keys = set(live["nk"])
for _, r in team.iterrows():
    if r["nk"] in current_keys or r["nk"] in exited_keys:
        continue
    rows.append({
        "company": r["Company"], "nk": r["nk"], "tier": "unicorn_delisted",
        "primary_source": "Team 2022 snapshot (not on 2026 list, no recorded exit)",
        "valuation_b_latest": r["val_2022"], "valuation_asof": "2022 (stale)",
        "date_joined_unicorn": r["Date Joined"],
        "funding_total_usd": r["Funding_B"] * 1e9 if pd.notna(r["Funding_B"]) else np.nan,
        "industry_raw": r["Industry"], "industry_group": industry_group(r["Industry"]),
        "country": r["Country"], "city": r.get("City"),
        "continent": continent(r["Country"]),
        "founded_year": r["Year Founded"],
        "outcome": "unknown",
        "investors": r["Select Investors"],
    })

# ------------------------------------------------------------------ 2) Crunchbase 2015 control tiers
cb = pd.read_csv(RAW / "crunchbase2015_companies.csv", low_memory=False)
cb = cb.dropna(subset=["name"])
cb["nk"] = cb["name"].map(name_key)
cb = cb[cb["nk"] != ""]
cb = cb[~cb["nk"].duplicated()]
cb["funding_usd"] = pd.to_numeric(cb["funding_total_usd"].replace("-", np.nan), errors="coerce")
cb["founded_year"] = pd.to_datetime(cb["founded_at"], errors="coerce").dt.year
cb_ctl = cb[~cb["nk"].isin(unicorn_keys)]

for _, r in cb_ctl.iterrows():
    fund = r["funding_usd"]
    tier = "soonicorn_proxy" if (pd.notna(fund) and fund >= 1e8 and r["status"] == "operating") else "control_funded"
    rows.append({
        "company": r["name"], "nk": r["nk"], "tier": tier,
        "primary_source": "Crunchbase Dec-2015 export (CC-BY)",
        "funding_total_usd": fund,
        "funding_rounds": r["funding_rounds"],
        "first_funding_at": r["first_funding_at"], "last_funding_at": r["last_funding_at"],
        "industry_raw": r["category_list"], "industry_group": industry_group(str(r["category_list"]).replace("|", " ")),
        "country": ISO3_COUNTRY.get(r["country_code"], r["country_code"]),
        "continent": continent(ISO3_COUNTRY.get(r["country_code"], "")),
        "city": r["city"],
        "founded_year": r["founded_year"],
        "outcome": r["status"] if r["status"] in ("operating", "acquired", "ipo", "closed") else "unknown",
        "status_asof": "2015-12",
    })

# ------------------------------------------------------------------ 3) accelerator tier
seen = {r["nk"] for r in rows}
acc_flags = {}

yc = json.load(open(RAW / "yc_all.json"))
for x in yc:
    k = name_key(x.get("name", ""))
    if not k:
        continue
    acc_flags.setdefault(k, set()).add("YC")
    if k in seen:
        continue
    seen.add(k)
    status_map = {"Active": "operating", "Acquired": "acquired", "Public": "ipo", "Inactive": "closed"}
    batch = x.get("batch", "")
    ym = re.search(r"(20\d\d|19\d\d)", str(batch))
    rows.append({
        "company": x["name"], "nk": k, "tier": "control_accelerator",
        "primary_source": "Y Combinator directory (yc-oss, current)",
        "industry_raw": x.get("industry"), "industry_group": industry_group(f"{x.get('industry','')} {x.get('subindustry','')}"),
        "country": np.nan, "continent": "Unknown",
        "city": (x.get("all_locations") or "").split(",")[0] or np.nan,
        "outcome": status_map.get(x.get("status"), "unknown"),
        "accelerator": "YC", "batch": batch,
        "batch_year": int(ym.group(1)) if ym else np.nan,
        "team_size": x.get("team_size"),
        "status_asof": "2026-07",
    })

ts = json.load(open(RAW / "techstars_all.json"))
for x in ts:
    k = name_key(x.get("name", ""))
    if not k:
        continue
    acc_flags.setdefault(k, set()).add("Techstars")
    if k in seen:
        continue
    seen.add(k)
    st = str(x.get("program_status") or x.get("status") or "").lower()
    outcome = "acquired" if "acquir" in st else ("closed" if "out of business" in st else ("operating" if "operat" in st or "active" in st else "unknown"))
    rows.append({
        "company": x["name"], "nk": k, "tier": "control_accelerator",
        "primary_source": "Techstars portfolio (public index)",
        "industry_raw": np.nan, "industry_group": "Other / Unknown",
        "country": x.get("country"), "continent": continent(x.get("country")),
        "city": x.get("city"),
        "outcome": outcome,
        "accelerator": "Techstars", "batch": x.get("session"),
        "batch_year": x.get("sessionYear"),
        "status_asof": "2023",
    })

g500 = json.load(open(RAW / "500global_startups.json"))
recs = g500 if isinstance(g500, list) else list(g500.values())[0]
for x in recs:
    org = x.get("organization") or {}
    nm = org.get("name") or x.get("name") or ""
    k = name_key(nm)
    if not k:
        continue
    acc_flags.setdefault(k, set()).add("500Global")
    if k in seen:
        continue
    seen.add(k)
    stage = str(x.get("stage") or "")
    if stage in ("Active fund", "Fund"):
        continue
    outcome = "acquired" if stage == "Exited" else ("closed" if stage in ("Writeoff", "Dissolved") else "operating")
    country = (org.get("country") or "").title() if isinstance(org.get("country"), str) else np.nan
    inds = x.get("industries")
    if isinstance(inds, list):
        parts = [(i.get("name") or i.get("title") or "") if isinstance(i, dict) else str(i) for i in inds]
        ind = ", ".join(p for p in parts if p)
    else:
        ind = inds if isinstance(inds, str) else ""
    rows.append({
        "company": nm, "nk": k, "tier": "control_accelerator",
        "primary_source": "500 Global portfolio (public API)",
        "industry_raw": ind or np.nan, "industry_group": industry_group(ind),
        "country": country, "continent": continent(country if isinstance(country, str) else ""),
        "outcome": outcome,
        "accelerator": "500 Global",
        "funding_stage": stage,
        "status_asof": "2026",
    })

master = pd.DataFrame(rows)
for a, col in [("YC", "in_yc"), ("Techstars", "in_techstars"), ("500Global", "in_500global")]:
    master[col] = master["nk"].map(lambda k: a in acc_flags.get(k, set()))
master = master.drop(columns=["nk"])
col_order = ["company", "tier", "primary_source", "valuation_b_latest", "valuation_asof",
             "date_joined_unicorn", "exit_date", "exit_reason", "exit_valuation_b",
             "funding_total_usd", "funding_rounds", "first_funding_at", "last_funding_at",
             "industry_raw", "industry_group", "country", "continent", "city",
             "founded_year", "outcome", "status_asof", "investors", "investor_count",
             "accelerator", "batch", "batch_year", "team_size", "funding_stage",
             "in_yc", "in_techstars", "in_500global"]
master = master[[c for c in col_order if c in master.columns]]
master.to_csv(OUT / "startup_master.csv", index=False)

# ------------------------------------------------------------------ 4) SEC Form D current raises (optional: needs raw SEC zip, see fetch_raw_data.sh)
FORMD_DIR = RAW / "formd_2026q2" / "2026Q2_d"
if not FORMD_DIR.exists():
    print("NOTE: raw SEC Form D data not present; keeping committed data/expanded/formd_2026q2_raises.csv")
HAVE_FORMD = FORMD_DIR.exists()
sub = pd.read_csv(FORMD_DIR / "FORMDSUBMISSION.tsv", sep="\t", low_memory=False) if HAVE_FORMD else None
iss = pd.read_csv(FORMD_DIR / "ISSUERS.tsv", sep="\t", low_memory=False) if HAVE_FORMD else None
off = pd.read_csv(FORMD_DIR / "OFFERING.tsv", sep="\t", low_memory=False) if HAVE_FORMD else None
if HAVE_FORMD:
    iss1 = iss[iss["IS_PRIMARYISSUER_FLAG"] == "YES"] if "IS_PRIMARYISSUER_FLAG" in iss.columns else iss.drop_duplicates("ACCESSIONNUMBER")
    iss1 = iss1.drop_duplicates("ACCESSIONNUMBER")
    fd = sub.merge(iss1, on="ACCESSIONNUMBER", how="inner").merge(off, on="ACCESSIONNUMBER", how="inner")
    ind_col = "INDUSTRYGROUPTYPE"
    fd_ops = fd[fd[ind_col] != "Pooled Investment Fund"].copy()
    keep = {
        "ENTITYNAME": "entity", "FILING_DATE": "filing_date", ind_col: "industry_group_sec",
        "STATEORCOUNTRY": "state_or_country", "YEAROFINC_VALUE_ENTERED": "year_of_incorporation",
        "TOTALOFFERINGAMOUNT": "total_offering_usd", "TOTALAMOUNTSOLD": "total_sold_usd",
        "TOTALNUMBERALREADYINVESTED": "n_investors",
    }
    keep = {k: v for k, v in keep.items() if k in fd_ops.columns}
    fd_out = fd_ops[list(keep)].rename(columns=keep)
    fd_out["total_sold_usd"] = pd.to_numeric(fd_out["total_sold_usd"], errors="coerce")
    fd_out["total_offering_usd"] = pd.to_numeric(fd_out["total_offering_usd"], errors="coerce")
    fd_out["mega_raise_100m"] = fd_out["total_sold_usd"] >= 1e8
    fd_out.to_csv(OUT / "formd_2026q2_raises.csv", index=False)

# ------------------------------------------------------------------ summary + sanity
summary["master_rows"] = len(master)
summary["tier_counts"] = master["tier"].value_counts().to_dict()
summary["outcome_counts"] = master["outcome"].value_counts().to_dict()
summary["rows_with_valuation"] = int(master["valuation_b_latest"].notna().sum())
summary["rows_with_funding"] = int(master["funding_total_usd"].notna().sum())
summary["panel_rows"] = len(panel)
summary["panel_all4"] = int(panel[["val_2022", "val_2024", "val_2025", "val_2026"]].notna().all(axis=1).sum())
if HAVE_FORMD:
    summary["formd_rows"] = len(fd_out)
    summary["formd_mega_raises"] = int(fd_out["mega_raise_100m"].sum())
summary["live_parse_dropped"] = n_bad
summary["skipped_ragged_lines"] = skipped_lines

spot = {}
for nm in ["Anthropic", "OpenAI", "Stripe", "Airbnb", "SpaceX"]:
    m = master[master["company"].astype(str).str.fullmatch(nm, case=False)]
    if len(m):
        r = m.iloc[0]
        spot[nm] = f"{r['tier']} | val={r['valuation_b_latest']} | {r['outcome']}"
p = panel[panel["Company"].astype(str).str.fullmatch("Stripe", case=False)]
if len(p):
    spot["Stripe panel"] = p[["val_2022", "val_2024", "val_2025", "val_2026"]].iloc[0].to_dict()
summary["spot_checks"] = spot

with open(OUT / "build_summary.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
