"""City of Austin eCheckbook: payment lines of the Austin Fire Department (department 83, "Fire").

    python3 pipeline/sources/tx_austin.py fetch
    python3 pipeline/sources/tx_austin.py normalize

Source: City of Austin Open Data Portal (Socrata), "Austin Finance Online eCheckbook",
https://data.austintexas.gov/d/8c6z-qnmj, the flat file behind https://financeonline.austintexas.gov/afo/finance/.
FY2009 to the current year; City fiscal year runs October to September (the year it ends in). One row per
accounting line of a payment: fiscal year and period, department, fund, division, group, object category and
object, legal vendor name, vendor/customer indicator, referenced document (PO, contract), commodity, check or
EFT issue date, check status (Paid, Outstanding, Escheat), accounting line description, amount. Some Austin
Energy lines are withheld as competitive matters; none concern the Fire department.

fetch      raw/<date>/tx/tx_austin/8c6z-qnmj_meta.json.gz   Socrata metadata
           raw/<date>/tx/tx_austin/fire.json.gz             every line of department 83 with fy_dc >= 2021
           raw/<date>/tx/tx_austin/sample.json.gz           100 unfiltered lines
normalize  data/states/tx/transactions.csv.gz   one row per Fire department payment line
           data/states/tx/agencies.json         via common.assemble_agencies

Attribution: department code 83, "Fire", linked to TX-WP801 in agency_sources.csv. Austin-Travis County EMS
(department 93) and Public Safety & Emergency Management (96) are separate departments and are not linked.

Duplicates and reversals: owner rule of 2026-10-07 (tx_common.drop_identical): lines identical in every published
column but the source's ids are kept once: fiscal year, check or EFT issue date, payee, accounting line description
(or commodity description), account (fund, division, group, object), object category and amount. The source's ids
are the Socrata row id, the payment document id (rfed_doc_*) with its vendor, commodity and accounting line
numbers, and the referenced purchase order, delivery order or contract id (rf_doc_*); in the 2026-10-06 pull every
dropped line differs from the kept one only in those ids (mostly commodity or accounting lines of one payment
document with the same description and amount), and none is identical in every raw column.
source_record_id counts every raw line of the document, so a kept line's id does not move when a copy is dropped.
Checks of every status are kept (Outstanding = issued, not yet cashed; Escheat = uncashed and sent to the state as
unclaimed property; the City's expense stands either way). Payee names are published as the source publishes
them, employees and customer (non-vendor) payees included (owner decision, 2026-10-06); common.withhold_person
only cuts email addresses and bank account text.
"""
import collections
import decimal
import json
import sys

import common
import tx_common

ST = "TX"
SOURCE = "tx_austin"
DOMAIN = "https://data.austintexas.gov"
DATASET = "8c6z-qnmj"
DEPARTMENT = "83"
FIRST_FY = 2021
PAGE = 50000


def fetch():
    meta = common.get(f"{DOMAIN}/api/views/{DATASET}.json")
    common.save_raw(ST, SOURCE, f"{DATASET}_meta.json", meta)
    cols = [c["fieldName"] for c in json.loads(meta)["columns"] if not c["fieldName"].startswith(":")]
    select = ",".join([":id"] + cols)
    rows, offset = [], 0
    while True:
        page = json.loads(common.get(f"{DOMAIN}/resource/{DATASET}.json", {
            "$select": select, "$where": f"dept_cd = {DEPARTMENT} AND fy_dc >= '{FIRST_FY}'", "$order": ":id",
            "$limit": PAGE, "$offset": offset}))
        rows += page
        if len(page) < PAGE:
            break
        offset += PAGE
    print(f"  {DATASET}: {len(rows)} Fire lines")
    common.save_raw(ST, SOURCE, "fire.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{DATASET}.json",
                                                          {"$select": select, "$order": ":id", "$limit": 100}))




def normalize():
    raw = common.latest_raw(ST, SOURCE)
    assert raw, "run fetch first"
    links = [r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == SOURCE]
    assert len(links) == 1 and links[0]["source_entity_id"] == DEPARTMENT, "agency_sources.csv: one Fire row expected"
    aid = links[0]["agency_id"]
    lines = json.loads(common.read_gz(raw / "fire.json.gz"))
    seen, rows, per_doc, exact = set(), [], collections.Counter(), 0
    for r in sorted(lines, key=lambda r: r[":id"]):
        assert str(r["dept_cd"]) == DEPARTMENT
        k = tuple(sorted((f, v) for f, v in r.items() if f != ":id"))
        exact += k in seen  # identical in every raw column; drop_identical drops it below (counted for the report)
        seen.add(k)
        doc = "-".join(r.get(f, "") for f in ("rfed_doc_cd", "rfed_doc_dept_cd", "rfed_doc_id"))
        per_doc[doc] += 1
        obj = r.get("obj_nm", "")
        rows.append({
            "agency_id": aid, "fiscal_year": int(r["fy_dc"]), "posting_date": r.get("chk_eft_iss_dt", "")[:10],
            "payee_name": common.withhold_person(r.get("lgl_nm", "")),
            "description": r.get("actg_ln_dscr") or r.get("comm_dscr", ""),
            "account": " / ".join(x for x in (r.get("fund_nm", ""), r.get("div_nm", ""), r.get("gp_nm", ""),
                                              f"{r.get('obj_cd', '')} {obj}".strip()) if x),
            "category_published": r.get("ocat_nm", ""), "amount": f"{float(r['amount']):.2f}",
            "source_record_id": f"{doc}:{per_doc[doc]}",
        })
    n_raw = len(rows)
    rows, dropped = tx_common.drop_identical(rows)
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)
    common.assemble_agencies(ST)
    by_fy = collections.Counter()
    for r in rows:
        by_fy[r["fiscal_year"]] += float(r["amount"])
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    print(f"{ST} {SOURCE}: {n_raw} raw lines -> {len(rows)} lines (${total:,.2f}); "
          + ", ".join(f"FY{y} ${v:,.0f}" for y, v in sorted(by_fy.items()))
          + f"; {tx_common.dropped_text(dropped)}, of which {exact} identical in every raw column")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
