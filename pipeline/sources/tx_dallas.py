"""City of Dallas vendor payments: payment lines of Dallas Fire-Rescue (department DFD).

    python3 pipeline/sources/tx_dallas.py fetch
    python3 pipeline/sources/tx_dallas.py normalize

Source: Dallas OpenData (Socrata), "Vendor Payments for Fiscal Year 2019 - Present", https://www.dallasopendata.com/d/x5ih-idh7
(Open Data Commons Attribution License). Despite its name the dataset now holds only the current and the
previous City fiscal year (FY2026, Oct 2025-Sep 2026, and the first days of FY2027 on 2026-10-06); earlier
years are no longer published there. City fiscal year runs October to September (the year it ends in).
Columns: run date, fiscal year and month, document id, payment subtotal per line, vendor code and name, vendor
zip, fund type, department, activity, object group, object, commodity code and description. The city withholds
some payments for vendor anonymity, so totals do not match the City's budget documents.

fetch      raw/<date>/tx/tx_dallas/x5ih-idh7_meta.json.gz   Socrata metadata
           raw/<date>/tx/tx_dallas/dfd.json.gz              every DFD line with fy >= 2021 (server-side SoQL)
           raw/<date>/tx/tx_dallas/sample.json.gz           100 unfiltered lines
normalize  data/states/tx/transactions.csv.gz   one row per DFD payment line
           data/states/tx/agencies.json         via common.assemble_agencies

Attribution: department code DFD, "Dallas Fire-Rescue", linked to TX-DH807 in agency_sources.csv.

Duplicates and reversals: owner rule of 2026-10-07 (tx_common.drop_identical): lines identical in every published
column but the source's ids are kept once: fiscal year, run date, payee, description (commodity, activity),
account (fund type, activity, object), object group and amount. The source's ids are the Socrata row id and the
payment document id (docid); in the 2026-10-06 pull every dropped line differs from the kept one only in docid
(the same payment to one vendor on one run date under another document), and none is identical in every raw
column. source_record_id counts every raw line of the document. Negative lines are kept and never equal the
payment they reverse. Payee names are published as the source publishes them
(owner decision, 2026-10-06); common.withhold_person only cuts email addresses and bank account text.
"""
import collections
import decimal
import json
import sys

import common
import tx_common

ST = "TX"
SOURCE = "tx_dallas"
DOMAIN = "https://www.dallasopendata.com"
DATASET = "x5ih-idh7"
DEPARTMENT = "DFD"
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
            "$select": select, "$where": f"dpt = '{DEPARTMENT}' AND fy >= {FIRST_FY}", "$order": ":id",
            "$limit": PAGE, "$offset": offset}))
        rows += page
        if len(page) < PAGE:
            break
        offset += PAGE
    print(f"  {DATASET}: {len(rows)} DFD lines")
    common.save_raw(ST, SOURCE, "dfd.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{DATASET}.json",
                                                          {"$select": select, "$order": ":id", "$limit": 100}))




def normalize():
    raw = common.latest_raw(ST, SOURCE)
    assert raw, "run fetch first"
    links = [r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == SOURCE]
    assert len(links) == 1 and links[0]["source_entity_id"] == DEPARTMENT, "agency_sources.csv: one DFD row expected"
    aid = links[0]["agency_id"]
    lines = json.loads(common.read_gz(raw / "dfd.json.gz"))
    seen, rows, per_doc, exact = set(), [], collections.Counter(), 0
    for r in sorted(lines, key=lambda r: r[":id"]):
        assert r["dpt"] == DEPARTMENT
        k = tuple(sorted((f, v) for f, v in r.items() if f != ":id"))
        exact += k in seen  # identical in every raw column; drop_identical drops it below (counted for the report)
        seen.add(k)
        per_doc[r["docid"]] += 1
        obj = r.get("object", "")
        rows.append({
            "agency_id": aid, "fiscal_year": int(r["fy"]), "posting_date": r.get("rundate", "")[:10],
            "payee_name": common.withhold_person(r.get("vendor", "")),
            "description": " / ".join(x for x in (r.get("commoditydscr", ""), r.get("activity", "")) if x and x != "NONE"),
            "account": " / ".join(x for x in (r.get("fundtype", ""), r.get("activity", ""), f"{r.get('obj', '')} {obj}".strip()) if x),
            "category_published": r.get("objectgroup", ""), "amount": f"{float(r['chksubtot']):.2f}",
            "source_record_id": f"{r['docid']}:{per_doc[r['docid']]}",
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
