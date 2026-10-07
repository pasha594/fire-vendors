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

Duplicates and reversals: owner rule of 2026-10-07 as corrected the same day (tx_common.dedup): two lines are
identical when every raw column is equal except the Socrata row id (:id), the only column that identifies the row or
the load (ROW_IDS; the pull selects :id and the published columns, no :created_at or :updated_at). Compared are the
other 34 columns, the payment document (rfed_doc_*) with its vendor, commodity and accounting line numbers, the
referenced purchase order, delivery order or contract (rf_doc_*), the commodity and the period fields included:
lines that differ in any of them are different payments and are kept. Of a set of identical lines the one with the
lowest :id is kept; a set of n identical positive lines keeps min(n, reversals + 1), reversals being the distinct
lines equal in every REVERSAL_KEYS column (department, fund, division, group, object, vendor, referenced document)
with the amount negated in the same or the next fiscal year; identical negative lines follow the void fix (owner
decision A of 2026-10-07, tx_common.dedup rule 4: in a family with payments a negative copy is dropped only with a
positive copy). In the 2026-10-06 pull no two lines are identical and there is no negative line, so nothing is
dropped. source_record_id counts every raw line of the document.
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
ROW_IDS = (":id",)  # Socrata row id: the only raw column that identifies the row or the load
REVERSAL_KEYS = ("dept_cd", "fund_cd", "div_cd", "gp_cd", "obj_cd", "vend_cust_cd", "lgl_nm", "rf_doc_cd",
                 "rf_doc_dept_cd", "rf_doc_id")


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
    records = sorted(lines, key=lambda r: r[":id"])
    drop, dropped = tx_common.dedup(records, ROW_IDS, REVERSAL_KEYS, "amount", "fy_dc")
    rows, per_doc = [], collections.Counter()
    for i, r in enumerate(records):
        assert str(r["dept_cd"]) == DEPARTMENT
        doc = "-".join(r.get(f, "") for f in ("rfed_doc_cd", "rfed_doc_dept_cd", "rfed_doc_id"))
        per_doc[doc] += 1  # counts every raw line, so a kept line's id does not move when a copy is dropped
        if i in drop:
            continue
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
    n_raw = len(records)
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)
    common.assemble_agencies(ST)
    by_fy = collections.Counter()
    for r in rows:
        by_fy[r["fiscal_year"]] += float(r["amount"])
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    print(f"{ST} {SOURCE}: {n_raw} raw lines -> {len(rows)} lines (${total:,.2f}); "
          + ", ".join(f"FY{y} ${v:,.0f}" for y, v in sorted(by_fy.items()))
          + f"; {tx_common.dropped_text(dropped)}")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
