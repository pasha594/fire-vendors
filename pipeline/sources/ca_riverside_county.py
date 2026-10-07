"""County of Riverside Check Book: vendor payment lines of the Riverside County Fire Department (tier 1).

    python3 pipeline/sources/ca_riverside_county.py fetch
    python3 pipeline/sources/ca_riverside_county.py normalize

Source: County of Riverside open data (Socrata), "Check Book" ("County of Riverside Open Expenditures"),
https://data.countyofriverside.us/d/swwh-4ka9, published by RCIT; licence: public domain (U.S. government).
About 71 million ledger lines from FY2011 on: fiscal year (July-June, the year it ends in) and period, date,
department, fund type, account category, account and expense category, fund, business unit, description,
amount, and for accounts-payable lines the vendor name and id, invoice id and payment id. Lines without a
vendor (payroll, journal entries, internal service charges, transfers) are not payments to a payee.

fetch      raw/<date>/ca/ca_riverside_county/swwh-4ka9_meta.json.gz  Socrata metadata
           raw/<date>/ca/ca_riverside_county/fire.json.gz             every line of department "Fire Protection"
                                                                      with fiscal_year >= 2021 and a vendor name
           raw/<date>/ca/ca_riverside_county/control.json.gz          per fiscal year: rows and dollars of the
                                                                      department with and without a vendor
           raw/<date>/ca/ca_riverside_county/sample.json.gz           100 unfiltered lines
normalize  data/states/ca/transactions.csv.gz   one row per vendor payment line
           config/states/ca/sources.csv         this source's row
           data/states/ca/agencies.json         via common.assemble_agencies

Attribution: department "Fire Protection" (the County Fire Department, operated by CAL FIRE under the
county's cooperative agreement), linked to CA-33090 in agency_sources.csv. The registry lists the same
operation a second time as "Cal Fire - Riverside County Fire Department" (CA-33555), which is not linked.
The department's largest payee is the State (CAL FIRE) for contract staffing.

Duplicates and reversals: owner rule of 2026-10-07 as corrected the same day (ca_common.keep_identical): raw
lines equal in every published column but the portal's row id (:id, the only row or load id in the raw file) are
kept once; invoice and payment ids are content, so lines of different invoices or payments are always kept. The
source has no line number, so lines repeated inside one invoice (same business unit, account, date and amount;
for example one line per phone on a wireless bill) are identical and kept once. Void-safe: a set of n identical
positive lines keeps min(n, reversals + 1), where a reversal is a negative line with the same department, vendor,
business unit, fund, account, expense category, invoice id, payment id and description, the amount negated and
the same or next fiscal year (REVERSAL). Credits and reversals are their own negative lines and are kept; normalize
prints the counts and docs/sources/ca.md gives the numbers. The record id is the invoice id plus a running number
in the sorted order of the invoice's raw lines (before identical lines are dropped).
"""
import collections
import decimal
import json
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_riverside_county"
DOMAIN = "https://data.countyofriverside.us"
DATASET = "swwh-4ka9"
DEPARTMENT = "Fire Protection"
FIRST_FY = 2021
DEPT_WHERE = f"department = '{DEPARTMENT}' AND fiscal_year >= {FIRST_FY}"
WHERE = DEPT_WHERE + " AND vendor_name IS NOT NULL"


def fetch():
    meta = common.get(f"{DOMAIN}/api/views/{DATASET}.json")
    common.save_raw(ST, SOURCE, f"{DATASET}_meta.json", meta)
    cols = ca_common.columns(meta)
    select = ",".join([":id"] + cols)
    rows = ca_common.soql_all(DOMAIN, DATASET, select, WHERE)
    common.save_raw(ST, SOURCE, "fire.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    control = ca_common.soql(DOMAIN, DATASET,
                             select="fiscal_year, vendor_name IS NOT NULL as has_vendor, count(*) as n, sum(amount) as amount",
                             where=DEPT_WHERE, group="fiscal_year, has_vendor", order="fiscal_year, has_vendor")
    common.save_raw(ST, SOURCE, "control.json", json.dumps(control, indent=0, sort_keys=True).encode())
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{DATASET}.json",
                                                          {"$select": select, "$order": ":id", "$limit": 100}))
    print(f"{ST}: {SOURCE}: {len(rows)} rows")


COLUMNS = ["fiscal_year", "fiscal_period", "date", "department", "fund_type", "account_category", "account",
           "expense_category", "fund", "business_unit", "description", "amount", "vendor_name", "vendor_id",
           "invoice_id", "payment_id"]
ROW_IDS = {":id"}  # Socrata row id; every other raw column is content
REVERSAL = ["department", "vendor_name", "business_unit", "fund_type", "fund", "account_category", "account",
            "expense_category", "invoice_id", "payment_id", "description"]


def read_raw(d):
    rows = json.loads(common.read_gz(d / "fire.json.gz"))
    control = json.loads(common.read_gz(d / "control.json.gz"))
    expect = sum(int(c["n"]) for c in control if c["has_vendor"] in (True, "true"))
    assert len(rows) == expect, f"raw rows {len(rows)} do not match control.json {expect}"
    return rows


def line_key(r):
    return tuple(r.get(c) or "" for c in COLUMNS)


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    links = {r["source_entity_name"]: r["agency_id"] for r in ca_common.links(SOURCE)}
    raw = read_raw(d)
    for r in raw:
        assert r["department"] in links and int(r["fiscal_year"]) >= FIRST_FY and r.get("vendor_name"), r
    raw = sorted(raw, key=lambda r: (line_key(r), r[":id"]))
    seq, ids = collections.Counter(), {}
    for r in raw:
        base = r.get("invoice_id") or r.get("payment_id") or "noinvoice"
        seq[base] += 1
        ids[r[":id"]] = f"{base}-{seq[base]}"
    kept, dropped = ca_common.keep_identical(
        raw, ca_common.socrata_ident(ROW_IDS), lambda r: tuple(r.get(c) or "" for c in REVERSAL),
        lambda r: decimal.Decimal(r["amount"]), lambda r: int(r["fiscal_year"]), lambda r: r[":id"])
    rows = []
    for r in kept:
        rows.append({
            "agency_id": links[r["department"]], "fiscal_year": str(int(r["fiscal_year"])),
            "posting_date": (r.get("date") or "")[:10],
            "payee_name": common.withhold_person(r["vendor_name"]),
            "description": " ".join((r.get("description") or "").split()),
            "account": " / ".join(x for x in [r.get("business_unit"), r.get("fund"), r.get("account")] if x),
            "category_published": r.get("expense_category") or "",
            "amount": ca_common.money(r["amount"]),
            "source_record_id": ids[r[":id"]],
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["posting_date"] for r in rows)
    ca_common.register_source({
        "source": SOURCE, "name": "County of Riverside Check Book (Riverside County Fire Department)", "tier": "1",
        "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "County of Riverside FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "County Fire Department (department Fire Protection) accounts-payable lines with a vendor; payroll, "
                "journal entries and internal charges are not included; the largest payee is the State (CAL FIRE) "
                "for contract staffing; raw lines identical in every column but the row id kept once (no line "
                "number, so equal lines inside one invoice count once; payment, void and reissue keep their net); "
                f"FY{years[-1]} partial (lines through {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    withheld = sum(r["payee_name"] == "Payee name withheld" for r in rows)
    print(f"{ST}: {SOURCE}: {len(raw)} source lines -> {len(rows)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; "
          f"{ca_common.dropped_text(dropped)}; {withheld} lines with the payee withheld")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
