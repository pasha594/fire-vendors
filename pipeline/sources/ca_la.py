"""Checkbook L.A.: payment lines of the Los Angeles Fire Department (tier 1).

    python3 pipeline/sources/ca_la.py fetch
    python3 pipeline/sources/ca_la.py normalize

Source: Los Angeles City Controller open data (Socrata), "Checkbook L.A. Data", https://controllerdata.lacity.org/d/pggv-e4fn
(the data behind the Controller's Checkbook L.A. app; FY2018 on; licence CC BY 4.0, attribution "Controller").
One row per invoice distribution line paid from the City's financial system (FMS): fiscal year (July-June, the
year it ends in), department, vendor, transaction (check) date, amount, fund, account, expenditure type,
program, payment method and status, invoice number, line and distribution line, purchase order and line,
item description, quantity and unit price where the payment is against a purchase order. Payees the City
treats as private are published as "PRIVACY-<DEPARTMENT>" (for example ambulance-bill refunds).

fetch      raw/<date>/ca/ca_la/pggv-e4fn_meta.json.gz   Socrata metadata
           raw/<date>/ca/ca_la/fire.json.gz             every line of department FIRE with fiscal_year >= 2021,
                                                        the columns in COLUMNS (buyer names, links and calendar
                                                        helper columns are not kept)
           raw/<date>/ca/ca_la/control.json.gz          rows and dollars per fiscal year for the same filter
           raw/<date>/ca/ca_la/sample.json.gz           100 unfiltered lines
normalize  data/states/ca/transactions.csv.gz   one row per invoice distribution line
           config/states/ca/sources.csv         this source's row
           data/states/ca/agencies.json         via common.assemble_agencies

Attribution: department_name FIRE (department number 38), linked to CA-19105 in agency_sources.csv. Purchases
other City departments make for the Fire Department (General Services fleet and fuel, ITA) are not included.

Payees: shown as published (owner decision of 2026-10-06), including the City's own "PRIVACY-FIRE" placeholder and
the persons named on revenue refunds (ambulance charges, fire department services, plan checking fees);
common.withhold_person cuts only email and bank account text.

Duplicates and reversals: lines identical in every kept column other than the Socrata row id are kept once.
Cancelled checks appear as their own negative lines (payment_status CANCELLED) and are kept, so a cancelled
payment nets to zero (in the 2026-10-06 pull 677 of the 698 cancellation lines carry the same transaction id,
invoice line and distribution line as the payment they cancel). The record id is transaction id, invoice line
and distribution line, with "-cancelled" on a cancellation (plus a running number if one still repeats).
"""
import collections
import decimal
import json
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_la"
DOMAIN = "https://controllerdata.lacity.org"
DATASET = "pggv-e4fn"
DEPARTMENT = "FIRE"
FIRST_FY = 2021
WHERE = f"department_name = '{DEPARTMENT}' AND fiscal_year >= {FIRST_FY}"
COLUMNS = ["fiscal_year", "department_name", "department_number", "vendor_name", "vendor_id", "vendor_num",
           "transaction_date", "dollar_amount", "value_of_spend", "authority", "authority_name", "government_activity",
           "fund_group_name", "fund_type", "fund_name", "fund", "account_name", "account_code", "transaction_id",
           "expenditure_type", "settlement_judgment", "fiscal_month_number", "data_source", "program",
           "payment_method", "payment_status", "inv_num", "inv_date", "inv_line", "inv_dist_line", "po_num",
           "po_date", "po_line_number", "description", "detailed_item_description", "unit_price", "unit_of_measure",
           "quantity", "sales_tax", "discount", "item_code", "item_code_name", "procurement_organization",
           "supplier_city", "zip"]


def fetch():
    meta = common.get(f"{DOMAIN}/api/views/{DATASET}.json")
    common.save_raw(ST, SOURCE, f"{DATASET}_meta.json", meta)
    missing = set(COLUMNS) - set(ca_common.columns(meta))
    assert not missing, f"columns gone from {DATASET}: {sorted(missing)}"
    select = ",".join([":id"] + COLUMNS)
    rows = ca_common.soql_all(DOMAIN, DATASET, select, WHERE)
    common.save_raw(ST, SOURCE, "fire.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    control = ca_common.soql(DOMAIN, DATASET, select="fiscal_year, count(*) as n, sum(dollar_amount) as amount",
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


def describe(r):
    """Item description as published: the PO line's item text, else the invoice description."""
    return " ".join((r.get("detailed_item_description") or r.get("description") or "").split())


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    links = {r["source_entity_name"]: r["agency_id"] for r in ca_common.links(SOURCE)}
    raw = read_raw(d)
    unique = {}
    for r in raw:
        assert r["department_name"] in links and int(r["fiscal_year"]) >= FIRST_FY, f"row outside the filter: {r}"
        unique.setdefault(line_key(r), r)
    dropped = len(raw) - len(unique)
    ids, rows = collections.Counter(), []
    for key in sorted(unique):
        r = unique[key]
        if r.get("dollar_amount") in (None, ""):
            continue
        rid = f"{r.get('transaction_id', '')}-{r.get('inv_line', '')}-{r.get('inv_dist_line', '')}"
        if r.get("payment_status") == "CANCELLED":
            rid += "-cancelled"
        ids[rid] += 1
        if ids[rid] > 1:
            rid += f"#{ids[rid]}"
        rows.append({
            "agency_id": links[r["department_name"]], "fiscal_year": str(int(r["fiscal_year"])),
            "posting_date": (r.get("transaction_date") or "")[:10],
            "payee_name": common.withhold_person(r.get("vendor_name")),
            "description": describe(r),
            "account": " / ".join(x for x in [r.get("program"), r.get("fund_name"),
                                               f"{r.get('account_code', '')} {r.get('account_name', '')}".strip()] if x),
            "category_published": r.get("expenditure_type") or "",
            "amount": ca_common.money(r["dollar_amount"]),
            "source_record_id": rid,
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["posting_date"] for r in rows)
    ca_common.register_source({
        "source": SOURCE, "name": "Checkbook L.A. (Los Angeles City Controller)", "tier": "1",
        "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "City of Los Angeles FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "Los Angeles Fire Department (department 38) invoice lines; cancelled checks are negative lines; "
                "refunds of ambulance and fire service charges are shown without payee names; purchases other City "
                f"departments make for Fire are not included; FY{years[-1]} partial (payments through {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    withheld = sum(r["payee_name"] == "Payee name withheld" for r in rows)
    print(f"{ST}: {SOURCE}: {len(rows)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; {dropped} exact duplicate "
          f"lines dropped; {withheld} lines with the payee withheld")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
