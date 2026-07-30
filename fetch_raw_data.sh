#!/usr/bin/env bash
# Re-downloads the public sources behind data/raw/ (all verified July 2026).
# Licensed Capital IQ exports are intentionally not part of this script or the
# repository; supply them locally when rebuilding the Capital IQ Gold table.
set -euo pipefail
cd "$(dirname "$0")/data/raw"

# Crunchbase Dec-2015 open export mirror (CC-BY, attribute Crunchbase).
# Companion files rounds.csv / investments.csv / acquisitions.csv live in the same repo path.
curl -sL -o crunchbase2015_companies.csv \
  "https://raw.githubusercontent.com/notpeter/crunchbase-data/master/companies.csv"

# Y Combinator directory, auto-updated daily (yc-oss/api, MIT).
curl -sL -o yc_all.json "https://yc-oss.github.io/api/companies/all.json"

# CB Insights unicorn list snapshots.
# 2024 snapshot: public GitHub mirror (single command).
curl -sL -o cbinsights_unicorns_2024.csv \
  "https://raw.githubusercontent.com/LNshuti/saas-winners/main/cbinsights_data.csv"
# 2026-07 live list and the 2025-07 Wayback snapshot are parsed from the
# server-rendered HTML table at cbinsights.com/research-unicorn-companies
# (and web.archive.org snapshots of it). The parsed CSVs are committed;
# see README for the parsing approach. Cite CB Insights.

# Wikipedia unicorn tables (CC BY-SA): parsed from
# https://en.wikipedia.org/wiki/List_of_unicorn_startup_companies
# (current + former tables). Parsed CSVs are committed.

# SEC EDGAR Form D structured data, Q2 2026 (public domain).
# SEC requires a descriptive User-Agent. Unzip into data/raw/formd_2026q2/.
mkdir -p formd_2026q2
curl -sL -A "Team17 Cornell capstone research" \
  "https://www.sec.gov/files/datastandardsinnovation/data/form-d-data-sets/2026q2_d.zip" \
  -o formd_2026q2/2026q2_d.zip
(cd formd_2026q2 && unzip -o 2026q2_d.zip)

echo "Done. Re-run: python3 build_expanded_dataset.py"
