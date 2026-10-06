"""San Francisco Vendor Payments (Vouchers): payment lines of the San Francisco Fire Department (tier 1).

    python3 pipeline/sources/ca_sf.py fetch
    python3 pipeline/sources/ca_sf.py normalize

Source: DataSF (Socrata), "Vendor Payments (Vouchers)", https://data.sf.gov/d/n9pm-xkyq (data.sfgov.org redirects
there), published by the SF Controller's Office for SF OpenBook, updated weekly; licence: Open Data Commons PDDL.
One row per voucher line: fiscal year (July-June, the year it ends in), organization, department, program,
character, object and sub-object (the City's spend classification), fund, purchase order, contract, payee
("Supplier & Other Non-Supplier Payees"), amount paid, pending and pending retainage, voucher number. The
Controller removes payments to employees (reimbursements, garnishments), jurors, witnesses, revenue refunds,
judgments and claims and human-services payments before publishing. There is no documented payment date:
`data_as_of` varies per voucher from FY2018 on but is not described, and for many lines falls outside the
fiscal year (FY2022 lines carry dates from 2020-12 to 2023-02), so posting_date is left empty.

fetch      raw/<date>/ca/ca_sf/n9pm-xkyq_meta.json.gz   Socrata metadata
           raw/<date>/ca/ca_sf/fir.json.gz              every line of department FIR with fiscal_year >= 2021
           raw/<date>/ca/ca_sf/control.json.gz          rows and dollars per fiscal year for the same filter
           raw/<date>/ca/ca_sf/sample.json.gz           100 unfiltered lines
normalize  data/states/ca/transactions.csv.gz   one row per voucher line with a paid amount
           config/states/ca/sources.csv         this source's row
           data/states/ca/agencies.json         via common.assemble_agencies

Attribution: department code FIR ("FIR Fire Department"), linked to CA-38005 in agency_sources.csv. Fire-related
spending other departments make for the Fire Department (for example fleet or IT bought centrally) is not
included.

Amounts: `vouchers_paid`. Lines with nothing paid yet (only pending or retainage) are left out; pending amounts
are not counted.

Duplicates and reversals: lines identical in every published column (other than the Socrata row id) are kept
once. The voucher number is not unique per line (a voucher can pay several objects or funds), so the record id
is the voucher number plus a running number. Negative lines (credits) are kept.
"""
import collections
import decimal
import json
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_sf"
DOMAIN = "https://data.sf.gov"
DATASET = "n9pm-xkyq"
DEPARTMENT = "FIR"
FIRST_FY = 2021
WHERE = f"department_code = '{DEPARTMENT}' AND fiscal_year >= '{FIRST_FY}'"


def fetch():
    meta = common.get(f"{DOMAIN}/api/views/{DATASET}.json")
    common.save_raw(ST, SOURCE, f"{DATASET}_meta.json", meta)
    select = ",".join([":id"] + ca_common.columns(meta))
    rows = ca_common.soql_all(DOMAIN, DATASET, select, WHERE)
    common.save_raw(ST, SOURCE, "fir.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    control = ca_common.soql(DOMAIN, DATASET, select="fiscal_year, count(*) as n, sum(vouchers_paid) as paid",
                             where=WHERE, group="fiscal_year", order="fiscal_year")
    common.save_raw(ST, SOURCE, "control.json", json.dumps(control, indent=0, sort_keys=True).encode())
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{DATASET}.json",
                                                          {"$select": select, "$order": ":id", "$limit": 100}))
    print(f"{ST}: {SOURCE}: {len(rows)} rows")


FIELDS = ["fiscal_year", "organization_group_code", "department_code", "program_code", "program", "character_code",
          "character", "object_code", "object", "sub_object_code", "sub_object", "fund_type_code", "fund_code", "fund",
          "fund_category_code", "purchase_order", "vendor", "vouchers_paid", "vouchers_pending",
          "vouchers_pending_retainage", "voucher", "data_as_of", "non_profit_indicator", "contract_number",
          "contract_title", "purchasing_authority_title"]


def read_raw(d):
    rows = json.loads(common.read_gz(d / "fir.json.gz"))
    control = json.loads(common.read_gz(d / "control.json.gz"))
    assert len(rows) == sum(int(c["n"]) for c in control), "raw rows do not match control.json"
    return rows


def line_key(r):
    return tuple(r.get(f) or "" for f in FIELDS)


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    links = {r["source_entity_id"]: r["agency_id"] for r in ca_common.links(SOURCE)}
    raw = read_raw(d)
    unique = {}
    for r in raw:
        assert r["department_code"] in links and int(r["fiscal_year"]) >= FIRST_FY, f"row outside the filter: {r}"
        unique.setdefault(line_key(r), r)
    dropped = len(raw) - len(unique)
    payees, seq, rows, pending_only = ca_common.Payees(), collections.Counter(), [], 0
    for key in sorted(unique):
        r = unique[key]
        paid = decimal.Decimal(r.get("vouchers_paid") or "0")
        if paid == 0:
            pending_only += 1
            continue
        seq[r["voucher"]] += 1
        rows.append({
            "agency_id": links[r["department_code"]], "fiscal_year": r["fiscal_year"],
            "posting_date": "",
            "payee_name": payees.publish(r["vendor"]),
            "description": r.get("contract_title") or "",
            "account": " / ".join(x for x in [r.get("program"), f"{r['character_code']} {r['character']}",
                                               f"{r['object_code']} {r['object']}",
                                               f"{r['sub_object_code']} {r['sub_object']}", r.get("fund")] if x),
            "category_published": r["sub_object"],
            "amount": ca_common.money(paid),
            "source_record_id": f"{r['voucher']}-{seq[r['voucher']]}",
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["data_loaded_at"] for r in raw)[:10]
    ca_common.register_source({
        "source": SOURCE, "name": "San Francisco Vendor Payments (Vouchers)", "tier": "1",
        "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "City and County of San Francisco FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "Fire Department (FIR) voucher lines, amounts paid; the Controller removes payments to employees, "
                "jurors, witnesses, refunds, judgments and claims before publishing; purchases other departments make "
                f"for Fire are not included; FY{years[-1]} partial (data loaded {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    withheld = sum(r["payee_name"] == common.WITHHELD for r in rows)
    print(f"{ST}: {SOURCE}: {len(rows)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; {dropped} exact duplicate "
          f"lines dropped; {pending_only} lines with nothing paid left out; {withheld} lines with the payee withheld")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
