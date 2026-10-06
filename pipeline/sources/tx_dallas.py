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

Duplicates and reversals: lines identical in every column except the Socrata row id are kept once (none in
the 2026-10-06 pull). Negative lines are kept. Payees on claims, damages, refund and reimbursement objects are
always withheld.
"""
import collections
import json
import re
import sys

import common

ST = "TX"
SOURCE = "tx_dallas"
DOMAIN = "https://www.dallasopendata.com"
DATASET = "x5ih-idh7"
DEPARTMENT = "DFD"
FIRST_FY = 2021
PAGE = 50000
FORCE_OBJECT = re.compile(r"REFUND|REIMB|JUDGE?MENT|DAMAGES|CLAIM|EMPLOYEE|WITNESS|JUROR|SETTLEMENT", re.I)


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


# --- Payee names (same rule as tx_dir.payee) ------------------------------------------------------------

_BUSINESS = None


def payee(name, person_flag=False):
    """common.withhold_person, except that a name config/states/tx/vendor_map_additions.csv lists as a business
    (rows reviewed by hand, never a person) is kept. withhold_person already trusts config/vendor_map.csv for its
    looks_like_person test; its is_person and looks_like_person tests also catch company names such as
    'WW GRAINGER' or 'Brycer, LP'. Payees a source flags (person_flag) and redaction patterns stay withheld."""
    global _BUSINESS
    if _BUSINESS is None:
        _BUSINESS = {r["name_key"] for r in common.read_config(ST, "vendor_map_additions.csv")
                     if r["category"] != "individuals"}
    name = " ".join((name or "").split())
    out = common.withhold_person(name, person_flag)
    if out == common.WITHHELD and not person_flag and common.norm(name) in _BUSINESS:
        return name
    return out


def normalize():
    raw = common.latest_raw(ST, SOURCE)
    assert raw, "run fetch first"
    links = [r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == SOURCE]
    assert len(links) == 1 and links[0]["source_entity_id"] == DEPARTMENT, "agency_sources.csv: one DFD row expected"
    aid = links[0]["agency_id"]
    lines = json.loads(common.read_gz(raw / "dfd.json.gz"))
    seen, rows, per_doc, stats = set(), [], collections.Counter(), collections.Counter()
    for r in sorted(lines, key=lambda r: r[":id"]):
        assert r["dpt"] == DEPARTMENT
        k = tuple(sorted((f, v) for f, v in r.items() if f != ":id"))
        if k in seen:
            stats["duplicate lines dropped"] += 1
            continue
        seen.add(k)
        per_doc[r["docid"]] += 1
        obj = r.get("object", "")
        rows.append({
            "agency_id": aid, "fiscal_year": int(r["fy"]), "posting_date": r.get("rundate", "")[:10],
            "payee_name": payee(r.get("vendor", ""), person_flag=bool(FORCE_OBJECT.search(obj))),
            "description": " / ".join(x for x in (r.get("commoditydscr", ""), r.get("activity", "")) if x and x != "NONE"),
            "account": " / ".join(x for x in (r.get("fundtype", ""), r.get("activity", ""), f"{r.get('obj', '')} {obj}".strip()) if x),
            "category_published": r.get("objectgroup", ""), "amount": f"{float(r['chksubtot']):.2f}",
            "source_record_id": f"{r['docid']}:{per_doc[r['docid']]}",
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)
    common.assemble_agencies(ST)
    by_fy = collections.Counter()
    for r in rows:
        by_fy[r["fiscal_year"]] += float(r["amount"])
    print(f"{ST} {SOURCE}: {len(rows)} lines; " + ", ".join(f"FY{y} ${v:,.0f}" for y, v in sorted(by_fy.items()))
          + f"; {stats['duplicate lines dropped']} duplicate lines dropped")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
