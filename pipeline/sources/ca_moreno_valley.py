"""City of Moreno Valley Open Expenditures: payment lines of the Moreno Valley Fire Department (tier 1).

    python3 pipeline/sources/ca_moreno_valley.py fetch
    python3 pipeline/sources/ca_moreno_valley.py normalize

Source: the City of Moreno Valley's Socrata portal, "Moreno Valley Ledger Dataset for OE" (the ledger behind the
City's Open Expenditures app), https://moreno-valley.data.socrata.com/d/qpw5-2938, FY2013 on, refreshed a few
times a year (last on 2026-07-16 at the 2026-10-06 pull). No licence or terms are stated on the dataset; the
portal's robots.txt (Crawl-delay: 1) disallows only catalog browse filters, not the SODA API. One row per
invoice distribution line paid: fiscal year (July-June, the year it ends in) and period, service, department,
program, expense category, fund, vendor name, id and zip, payment id, method and date, invoice id, line,
distribution line and date, amount, description.

fetch      raw/<date>/ca/ca_moreno_valley/qpw5-2938_meta.json.gz  Socrata metadata
           raw/<date>/ca/ca_moreno_valley/fire.json.gz            every line of the three Fire departments
                                                                  (DEPARTMENTS) with fiscal_year >= 2021
           raw/<date>/ca/ca_moreno_valley/control.json.gz         rows and dollars per department and fiscal
                                                                  year for every department whose name has FIRE
           raw/<date>/ca/ca_moreno_valley/sample.json.gz          100 unfiltered lines
normalize  data/states/ca/transactions.csv.gz   one row per invoice distribution line
           config/states/ca/sources.csv         this source's row
           data/states/ca/agencies.json         via common.assemble_agencies

Attribution: the departments "Fire Operations", "Fire Prevention" and "Fire - Office of Emergency Mgmt" (the
Fire Department's emergency management division) are the Moreno Valley Fire Department, linked to CA-33054
("Moreno Valley Fire Service") in agency_sources.csv. The City contracts with the County of Riverside (County
Fire Department, operated by CAL FIRE) for fire and paramedic staffing, so most Fire Operations dollars are
payments to the County; ca_riverside_county shows the County's own spending, so the same dollars can appear
once as Moreno Valley's payment to the County and again as the County's payments to its vendors. Fire
spending booked to other departments (Fleet & Facilities, Technology Services) is not included.

Payees: shown as published (owner decision of 2026-10-06); common.withhold_person cuts only email and bank
account text.

Duplicates and reversals: the line is identified by payment id, invoice id, invoice line and distribution
line. Lines identical in every published column are kept once; lines that share the identifier but differ in
another column are kept (normalize reports how many). Voids and credits are their own negative lines and are
kept. The record id is payment id, invoice id, invoice line and distribution line (plus a running number if
one still repeats).
"""
import collections
import decimal
import json
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_moreno_valley"
DOMAIN = "https://moreno-valley.data.socrata.com"
DATASET = "qpw5-2938"
DEPARTMENTS = ["Fire - Office of Emergency Mgmt", "Fire Operations", "Fire Prevention"]
FIRST_FY = 2021
WHERE = "department in (" + ", ".join(f"'{d}'" for d in DEPARTMENTS) + f") AND fiscal_year >= {FIRST_FY}"
CONTROL_WHERE = f"upper(department) like '%FIRE%' AND fiscal_year >= {FIRST_FY}"
COLUMNS = ["fiscal_year", "fiscal_year_period", "service", "department", "program", "expense_category", "fund",
           "vendor", "vendor_id", "vendor_zip", "payment_id", "payment_method", "payment_date", "invoice_id",
           "invoice_line", "invoice_distribution_line", "invoice_date", "amount", "description"]


def fetch():
    meta = common.get(f"{DOMAIN}/api/views/{DATASET}.json")
    common.save_raw(ST, SOURCE, f"{DATASET}_meta.json", meta)
    assert set(COLUMNS) <= set(ca_common.columns(meta)), "columns changed"
    select = ",".join([":id"] + COLUMNS)
    rows = ca_common.soql_all(DOMAIN, DATASET, select, WHERE)
    common.save_raw(ST, SOURCE, "fire.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    control = ca_common.soql(DOMAIN, DATASET,
                             select="department, fiscal_year, count(*) as n, sum(amount) as amount",
                             where=CONTROL_WHERE, group="department, fiscal_year", order="department, fiscal_year")
    common.save_raw(ST, SOURCE, "control.json", json.dumps(control, indent=0, sort_keys=True).encode())
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{DATASET}.json",
                                                          {"$select": select, "$order": ":id", "$limit": 100}))
    print(f"{ST}: {SOURCE}: {len(rows)} rows")


def read_raw(d):
    rows = json.loads(common.read_gz(d / "fire.json.gz"))
    control = json.loads(common.read_gz(d / "control.json.gz"))
    assert {c["department"] for c in control} == set(DEPARTMENTS), \
        f"fire-named departments changed: {sorted({c['department'] for c in control})}"
    assert len(rows) == sum(int(c["n"]) for c in control), "raw rows do not match control.json"
    return rows


def line_key(r):
    return tuple(r.get(c) or "" for c in COLUMNS)


def line_id(r):
    return "-".join(str(r.get(c) or "") for c in ("payment_id", "invoice_id", "invoice_line",
                                                   "invoice_distribution_line"))


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    links = {r["source_entity_name"]: r["agency_id"] for r in ca_common.links(SOURCE)}
    assert set(links) == set(DEPARTMENTS), "agency_sources.csv rows must name each Fire department"
    raw = read_raw(d)
    unique = {}
    for r in raw:
        assert r["department"] in links and int(r["fiscal_year"]) >= FIRST_FY, f"row outside the filter: {r}"
        unique.setdefault(line_key(r), r)
    dropped = len(raw) - len(unique)
    ids, rows = collections.Counter(), []
    for key in sorted(unique):
        r = unique[key]
        rid = line_id(r)
        ids[rid] += 1
        if ids[rid] > 1:
            rid += f"#{ids[rid]}"
        rows.append({
            "agency_id": links[r["department"]], "fiscal_year": str(int(r["fiscal_year"])),
            "posting_date": (r.get("payment_date") or "")[:10],
            "payee_name": common.withhold_person(r.get("vendor")),
            "description": " ".join((r.get("description") or "").split()),
            "account": " / ".join(x for x in [r.get("department"), r.get("program"), r.get("fund")] if x),
            "category_published": r.get("expense_category") or "",
            "amount": ca_common.money(r.get("amount")),
            "source_record_id": rid,
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["posting_date"] for r in rows)
    ca_common.register_source({
        "source": SOURCE, "name": "City of Moreno Valley Open Expenditures", "tier": "1",
        "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "City of Moreno Valley FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "Moreno Valley Fire Department (departments Fire Operations, Fire Prevention and Fire - Office of "
                "Emergency Mgmt) invoice lines; most dollars are the City's contract payments to the County of "
                "Riverside for fire staffing (CAL FIRE operated); purchases other City departments make for Fire are "
                f"not included; FY{years[-1]} partial (payments through {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    repeated = sum(n - 1 for n in ids.values() if n > 1)
    print(f"{ST}: {SOURCE}: {len(rows)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; {dropped} exact duplicate "
          f"lines dropped; {repeated} lines share an identifier with another line but differ in another column")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
