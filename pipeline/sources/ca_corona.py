"""City of Corona Open Expenditures: payment lines of the Corona Fire Department (tier 1).

    python3 pipeline/sources/ca_corona.py fetch
    python3 pipeline/sources/ca_corona.py normalize

Source: CorStat, the City of Corona's open data portal (Socrata), "CorStat - Corona Open Expenditures",
https://corstat.coronaca.gov/d/mdmf-aswt, uploaded every Friday after the weekly check run; licence: public
domain (with the City's data disclaimer). One row per invoice line paid: fiscal year (July-June, the year it
ends in) and period, fund, department code and name, department activity, vendor id, name, city, state and
zip, payment id and date, invoice id, expense category, description, amount. FY2016 on.

fetch      raw/<date>/ca/ca_corona/mdmf-aswt_meta.json.gz   Socrata metadata
           raw/<date>/ca/ca_corona/fire.json.gz             every line of department 30 (FIRE) with fiscal_year >= 2021
           raw/<date>/ca/ca_corona/control.json.gz          rows and dollars per fiscal year for the same filter
           raw/<date>/ca/ca_corona/sample.json.gz           100 unfiltered lines
normalize  data/states/ca/transactions.csv.gz   one row per payment line
           config/states/ca/sources.csv         this source's row
           data/states/ca/agencies.json         via common.assemble_agencies

Attribution: department code 30 (FIRE), linked to CA-33025 (Corona Fire Department) in agency_sources.csv.

Payees: shown as published (owner decision of 2026-10-06), private persons included (pension, benefit, refund
and reimbursement payments name the person paid); common.withhold_person cuts only email and bank account text.

Duplicates and reversals: owner rule of 2026-10-07 as corrected the same day (ca_common.keep_identical): raw lines
equal in every published column but the portal's row id (:id, the only row or load id in the raw file) are kept
once; payment and invoice ids are content, so lines of different payments or invoices are always kept. The source
has no line number, so lines repeated inside one invoice and payment (same description, account and amount; a copier
invoice billing several machines at one price) are identical and kept once. Void-safe: a set of n identical positive
lines keeps min(n, reversals + 1), where a reversal is a negative line with the same department, vendor, department
activity, fund, expense category, invoice id and description, the amount negated and the same or next fiscal year
(REVERSAL; a void can carry a new payment id and date). Identical voids (owner decision of 2026-10-07): in a family
that has payments, an identical negative copy is dropped only together with an identical positive copy of the
family, so the family keeps its raw net. Negative lines (voids, credits) are kept; normalize prints the counts and
docs/sources/ca.md gives the numbers. The record id is payment id, invoice id and a running number in the sorted
order of the invoice's raw lines (before identical lines are dropped).
"""
import collections
import decimal
import json
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_corona"
DOMAIN = "https://corstat.coronaca.gov"
DATASET = "mdmf-aswt"
DEPARTMENT = "30"
FIRST_FY = 2021
WHERE = f"department_code = '{DEPARTMENT}' AND fiscal_year >= '{FIRST_FY}'"
COLUMNS = ["fiscal_year", "fiscal_year_period", "fund_name", "department_code", "department", "department_activity",
           "vendor_id", "vendor", "vendor_city", "vendor_st", "vendor_zip", "payment_id", "payment_date",
           "invoice_id", "expense_category", "description", "amount"]
ROW_IDS = {":id"}  # Socrata row id; every other raw column is content
REVERSAL = ["department_code", "vendor", "department_activity", "fund_name", "expense_category", "invoice_id",
            "description"]


def fetch():
    meta = common.get(f"{DOMAIN}/api/views/{DATASET}.json")
    common.save_raw(ST, SOURCE, f"{DATASET}_meta.json", meta)
    assert set(COLUMNS) <= set(ca_common.columns(meta)), "columns changed"
    select = ",".join([":id"] + COLUMNS)
    rows = ca_common.soql_all(DOMAIN, DATASET, select, WHERE)
    common.save_raw(ST, SOURCE, "fire.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    control = ca_common.soql(DOMAIN, DATASET, select="fiscal_year, count(*) as n, sum(amount) as amount",
                             where=WHERE, group="fiscal_year", order="fiscal_year")
    common.save_raw(ST, SOURCE, "control.json", json.dumps(control, indent=0, sort_keys=True).encode())
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{DATASET}.json",
                                                          {"$select": select, "$order": ":id", "$limit": 100}))
    print(f"{ST}: {SOURCE}: {len(rows)} rows")


def read_raw(d):
    rows = json.loads(common.read_gz(d / "fire.json.gz"))
    control = json.loads(common.read_gz(d / "control.json.gz"))
    assert len(rows) == sum(int(c["n"]) for c in control), "raw rows do not match control.json"
    return rows


def line_key(r):
    return tuple(r.get(c) or "" for c in COLUMNS)


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    links = {r["source_entity_id"]: r["agency_id"] for r in ca_common.links(SOURCE)}
    raw = read_raw(d)
    for r in raw:
        assert r["department_code"] in links and int(r["fiscal_year"]) >= FIRST_FY, f"row outside the filter: {r}"
    raw = sorted(raw, key=lambda r: (line_key(r), r[":id"]))
    seq, ids = collections.Counter(), {}
    for r in raw:
        base = f"{r.get('payment_id', '')}-{r.get('invoice_id', '')}"
        seq[base] += 1
        ids[r[":id"]] = f"{base}-{seq[base]}"
    kept, dropped = ca_common.keep_identical(
        raw, ca_common.socrata_ident(ROW_IDS), lambda r: tuple(r.get(c) or "" for c in REVERSAL),
        lambda r: decimal.Decimal(r["amount"]), lambda r: int(r["fiscal_year"]), lambda r: r[":id"])
    rows = []
    for r in kept:
        rows.append({
            "agency_id": links[r["department_code"]], "fiscal_year": r["fiscal_year"],
            "posting_date": (r.get("payment_date") or "")[:10],
            "payee_name": common.withhold_person(r["vendor"]),
            "description": " ".join((r.get("description") or "").split()),
            "account": " / ".join(x for x in [r.get("department_activity"), r.get("fund_name")] if x),
            "category_published": r.get("expense_category") or "",
            "amount": ca_common.money(r["amount"]),
            "source_record_id": ids[r[":id"]],
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["posting_date"] for r in rows)
    ca_common.register_source({
        "source": SOURCE, "name": "City of Corona Open Expenditures (CorStat)", "tier": "1",
        "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "City of Corona FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "Corona Fire Department (department 30) payment lines, including pension and benefit payments; "
                "raw lines identical in every column but the row id kept once (no line number, so equal lines inside "
                "one invoice count once; payment, void and reissue keep their net); "
                f"FY{years[-1]} partial (payments through {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    withheld = sum(r["payee_name"] == "Payee name withheld" for r in rows)
    print(f"{ST}: {SOURCE}: {len(raw)} source lines -> {len(rows)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; "
          f"{ca_common.dropped_text(dropped)}; {withheld} lines with the payee withheld")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
