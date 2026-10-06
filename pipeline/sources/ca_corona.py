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

Payees: lines on the PERSONNEL SERVICES expense category (pension, benefit and payroll-related payments) and
lines whose description says refund or reimbursement are published as withheld unless the payee is a business
by the usual rules.

Duplicates and reversals: the source has no line number, and identical lines are ordinary in it (one copier
invoice bills several machines at the same price; a hotel folio bills several rooms at the same rate). In the
2026-10-06 pull 944 lines ($391,008) repeat another line exactly; in 239 of the 250 invoices concerned only
some lines repeat, which a reloaded batch cannot produce. ca_common.collapse_reloads keeps those; only a
payment-invoice whose every line repeats the same number of times is treated as loaded twice and kept once.
Negative lines (voids, credits) are kept. The record id is payment id, invoice id and a running number in the
sorted order of the invoice's lines.
"""
import collections
import decimal
import json
import re
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
PERSONAL = re.compile(r"\b(REFUND|REIMB|REIMBURSE|REIMBURSEMENT|TUITION|PER DIEM|MILEAGE)\b", re.I)


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
    lines, dropped, repeats = ca_common.collapse_reloads(
        [line_key(r) for r in raw], lambda k: (k[COLUMNS.index("payment_id")], k[COLUMNS.index("invoice_id")]))
    payees, seq, rows = ca_common.Payees(), collections.Counter(), []
    for key in lines:
        r = dict(zip(COLUMNS, key))
        base = f"{r.get('payment_id', '')}-{r.get('invoice_id', '')}"
        seq[base] += 1
        flag = bool(PERSONAL.search(r.get("description") or ""))
        name = payees.publish(r["vendor"])
        if flag and name == r["vendor"] and not common.BUSINESS_WORDS.search(name) \
                and common.norm(name) not in payees.claimed:
            name = common.WITHHELD
        rows.append({
            "agency_id": links[r["department_code"]], "fiscal_year": r["fiscal_year"],
            "posting_date": (r.get("payment_date") or "")[:10],
            "payee_name": name,
            "description": " ".join((r.get("description") or "").split()),
            "account": " / ".join(x for x in [r.get("department_activity"), r.get("fund_name")] if x),
            "category_published": r.get("expense_category") or "",
            "amount": ca_common.money(r["amount"]),
            "source_record_id": f"{base}-{seq[base]}",
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["posting_date"] for r in rows)
    ca_common.register_source({
        "source": SOURCE, "name": "City of Corona Open Expenditures (CorStat)", "tier": "1",
        "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "City of Corona FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "Corona Fire Department (department 30) payment lines, including pension and benefit payments; "
                f"FY{years[-1]} partial (payments through {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    withheld = sum(r["payee_name"] == common.WITHHELD for r in rows)
    print(f"{ST}: {SOURCE}: {len(rows)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; {dropped} "
          f"lines dropped as reloaded invoices; {repeats} identical lines kept as separate charges; {withheld} lines "
          "with the payee withheld")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
