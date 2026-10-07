"""Texas Comptroller "State Expenditures by County": annual spending totals of the Texas A&M Forest Service.

    python3 pipeline/sources/tx_cpa.py fetch
    python3 pipeline/sources/tx_cpa.py normalize

Source: data.texas.gov (Socrata), one dataset per state fiscal year (September to August), built by the
Comptroller from the Uniform Statewide Accounting System: net expenditures of funds held in the State Treasury,
by agency, county and major spending category. Texas A&M Forest Service (agency 576) is the state's wildland
fire agency; the PRD leaves state fire agencies an open question, so it is listed as kind "State fire agency"
(config/states/tx/agencies_added.csv). Its totals cover the whole agency (forestry and fire), and only funds
held in the State Treasury. Payee-level state payments ("Where the Money Goes") are published only through an
interactive QlikView tool, with no bulk download, so they are not used.

fetch      raw/<date>/tx/tx_cpa/<dataset>.json.gz   rows of agency 576 from each FY2021+ dataset (server-side SoQL)
           raw/<date>/tx/tx_cpa/sample.json.gz      100 unfiltered rows of the newest dataset
normalize  data/states/tx/totals.csv                one row per fiscal year and major spending category
           data/states/tx/agencies.json             via common.assemble_agencies

Duplicates: each dataset is one fiscal year; rows are summed over counties. A dataset that holds no TFS rows,
or a fiscal year published twice, stops normalize.
"""
import collections
import json
import sys

import common

ST = "TX"
SOURCE = "tx_cpa"
DOMAIN = "https://data.texas.gov"
DATASETS = {2021: "tup7-smjg", 2022: "xys8-xb33", 2023: "iyey-5sid", 2024: "2zpi-yjjs"}  # FY2025 not yet published
WHERE = "upper(agency_name) like '%FOREST SERVICE%'"


def fetch():
    for fy, ds in sorted(DATASETS.items()):
        rows = json.loads(common.get(f"{DOMAIN}/resource/{ds}.json", {"$where": WHERE, "$limit": 50000}))
        print(f"  FY{fy} {ds}: {len(rows)} rows")
        common.save_raw(ST, SOURCE, f"{ds}.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    newest = DATASETS[max(DATASETS)]
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{newest}.json", {"$limit": 100}))


def amount(x):
    return float(str(x or 0).replace(",", "").replace("$", ""))


def normalize():
    raw = common.latest_raw(ST, SOURCE)
    assert raw, "run fetch first"
    links = [r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == SOURCE]
    assert len(links) == 1, "agency_sources.csv: one tx_cpa row expected"
    aid, agency_no = links[0]["agency_id"], links[0]["source_entity_id"]
    totals = collections.Counter()
    years = set()
    for fy, ds in sorted(DATASETS.items()):
        rows = json.loads(common.read_gz(raw / f"{ds}.json.gz"))
        rows = [r for r in rows if str(r.get("agency_number") or r.get("number") or "").split(".")[0] == agency_no]
        assert rows, f"{ds}: no rows for agency {agency_no}"
        for r in rows:
            assert int(float(r["fiscal_year"])) == fy, f"{ds}: row from FY{r['fiscal_year']}"
            cat = (r.get("major_spending_category") or r.get("expenditure_category") or "").strip()
            totals[(fy, cat)] += amount(r.get("amount"))
        assert fy not in years
        years.add(fy)
    out = [{"agency_id": aid, "fiscal_year": fy, "category_published": cat, "amount": f"{v:.2f}"}
           for (fy, cat), v in sorted(totals.items())]
    common.upsert_rows(ST, "totals.csv", SOURCE, out)
    common.assemble_agencies(ST)
    by_fy = collections.Counter()
    for (fy, _), v in totals.items():
        by_fy[fy] += v
    print(f"{ST} {SOURCE}: {len(out)} rows; " + ", ".join(f"FY{y} ${v:,.0f}" for y, v in sorted(by_fy.items())))


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
