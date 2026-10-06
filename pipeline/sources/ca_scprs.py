"""SCPRS Purchase Order Data (FY2012-13 to FY2014-15): CAL FIRE purchase order item lines (tier 2).

    python3 pipeline/sources/ca_scprs.py fetch
    python3 pipeline/sources/ca_scprs.py normalize

Source: California Department of General Services, "Purchase Order Data", https://data.ca.gov/dataset/purchase-order-data
(also on catalog.data.gov), one CSV of 344,504 lines (164 MB): the State Contract and Procurement Registration
System (eSCPRS) extract of state agencies' purchase orders for fiscal years 2012-13, 2013-14 and 2014-15 only.
Licence: not specified on the portal (California Open Data Policy, SAM 5160); robots.txt of data.ca.gov
disallows /api/ and /datastore/ but not the /dataset/.../download/ file link used here. Columns: creation and
purchase date, fiscal year, LPA (leveraged procurement agreement) number, PO and requisition number,
acquisition type and method, department, supplier code, name, qualifications and zip, CalCard flag, item name
and description, quantity, unit price, total price, UNSPSC codes and titles (commodity, class, family,
segment), location. There is no line number and no brand. Current data (FY2015-16 on) are in Cal eProcure /
FI$Cal, which offer no bulk download (caleprocure.ca.gov answers 403 to robots.txt); for current CAL FIRE
payments see ca_fiscal.

fetch      raw/<date>/ca/ca_scprs/calfire.csv.gz   header and every line of department "Forestry and Fire
                                                   Protection, Department of" (23,244 lines), as published
           raw/<date>/ca/ca_scprs/manifest.json.gz full file: URL, bytes, SHA-256, rows, columns, lines and
                                                   dollars per department with "Fire" or "Forestry" in its name
           raw/<date>/ca/ca_scprs/sample.csv.gz    header and first 100 lines of the full file
           The full file is not kept (164 MB; no other department is a fire agency).
normalize  data/states/ca/line_items.csv.gz      one row per PO line
           data/states/ca/transactions.csv.gz    the same lines as payee rows (payee = supplier)
           config/states/ca/sources.csv          this source's row
           data/states/ca/agencies.json          via common.assemble_agencies

Attribution: CAL FIRE as a whole (state fire agency, PRD open question), linked to CA-00555 in
agency_sources.csv. Fiscal year 2012-2013 is written as 2013 (the year it ends in).

Amounts: "Total Price" as published ("$1,234.56", negatives in parentheses). These are purchase order amounts
(commitments), not payments. Lines of $0.00 (443, mostly contract-amendment text) are left out. Date: the
purchase date, else the creation date, when it falls between 2000 and the end of the fiscal year (a few
purchase dates are typos such as 1912 or 2511); otherwise empty.

Duplicates and reversals: no line number, so ca_common.collapse_reloads applies: a PO whose every line repeats
the same number of times is kept once (27 POs in the 2026-10-06 file, for example a $952,295 Nomex line listed
twice as the only line of its PO); identical lines inside a larger PO are kept. Negative lines are kept.
"""
import collections
import csv
import datetime
import decimal
import hashlib
import io
import json
import re
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_scprs"
URL = ("https://data.ca.gov/dataset/ae343670-f827-4bc8-9d44-2af937d60190/resource/bb82edc5-9c78-44e2-8947-68ece26197c5/"
       "download/purchase-order-data-2012-2015-.csv")
PAGE = "https://data.ca.gov/dataset/purchase-order-data"
DEPARTMENT = "Forestry and Fire Protection, Department of"


def money(s):
    s = (s or "").replace("$", "").replace(",", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").strip()
    return -decimal.Decimal(s) if neg else decimal.Decimal(s or "0")


def fetch():
    body = common.get(URL, timeout=1200)
    text = body.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    dep, total_price = header.index("Department Name"), header.index("Total Price")
    rows, keep, per_dept = 0, [], collections.defaultdict(lambda: [0, decimal.Decimal(0)])
    for r in reader:
        rows += 1
        if re.search(r"fire|forestry", r[dep], re.I):
            per_dept[r[dep]][0] += 1
            per_dept[r[dep]][1] += money(r[total_price])
        if r[dep] == DEPARTMENT:
            keep.append(r)
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(header)
    w.writerows(keep)
    common.save_raw(ST, SOURCE, "calfire.csv", out.getvalue().encode("utf-8"))
    manifest = {"url": URL, "page": PAGE, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "rows": rows,
                "columns": header, "kept_department": DEPARTMENT, "kept_rows": len(keep),
                "fire_or_forestry_departments": {k: {"rows": v[0], "dollars": str(v[1])} for k, v in sorted(per_dept.items())}}
    common.save_raw(ST, SOURCE, "manifest.json", json.dumps(manifest, indent=1).encode())
    sample = io.StringIO()
    w = csv.writer(sample, lineterminator="\n")
    reader = csv.reader(io.StringIO(text))
    for i, r in enumerate(reader):
        if i > 100:
            break
        w.writerow(r)
    common.save_raw(ST, SOURCE, "sample.csv", sample.getvalue().encode("utf-8"))
    print(f"{ST}: {SOURCE}: {rows} lines in the full file, {len(keep)} CAL FIRE lines kept")


def day(s, fy_end):
    """m/d/yyyy as ISO, or "" when empty or implausible for the fiscal year (the file has typos such as 1912
    and 2511 for purchase dates; long-running contracts legitimately start years earlier)."""
    s = (s or "").strip()
    if not s:
        return ""
    d = datetime.datetime.strptime(s, "%m/%d/%Y").date()
    return d.isoformat() if 2000 <= d.year <= fy_end else ""


def read_raw(d):
    manifest = json.loads(common.read_gz(d / "manifest.json.gz"))
    reader = csv.reader(io.StringIO(common.read_gz(d / "calfire.csv.gz").decode("utf-8")))
    header = next(reader)
    assert header == manifest["columns"], "columns changed"
    rows = [tuple(r) for r in reader]
    assert len(rows) == manifest["kept_rows"], "raw rows do not match manifest.json"
    return header, rows


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    link = ca_common.links(SOURCE)
    assert len(link) == 1 and link[0]["source_entity_name"] == DEPARTMENT
    agency = link[0]["agency_id"]
    header, raw = read_raw(d)
    c = {name: i for i, name in enumerate(header)}
    assert all(r[c["Department Name"]] == DEPARTMENT for r in raw)
    po = lambda r: (r[c["Purchase Order Number"]], r[c["Fiscal Year"]])
    lines, dropped, repeats = ca_common.collapse_reloads(raw, po)
    seq, items, txns, zero = collections.Counter(), [], [], 0
    for r in lines:
        fy = r[c["Fiscal Year"]]
        assert re.fullmatch(r"20\d\d-20\d\d", fy), fy
        number, year = po(r)
        seq[(number, year)] += 1
        rid = f"{year[:4]}/{number}/{seq[(number, year)]}"
        if money(r[c["Total Price"]]) == 0:
            zero += 1  # $0 lines are amendment text ("Removes and replaces Exhibit B ..."), not purchases
            continue
        vendor = common.withhold_person(r[c["Supplier Name"]])
        date = day(r[c["Purchase Date"]], int(fy[5:])) or day(r[c["Creation Date"]], int(fy[5:]))
        description = " ".join((r[c["Item Description"]] or r[c["Item Name"]]).split())
        product = next((r[c[k]] for k in ("Commodity Title", "Class Title", "Family Title", "Segment Title") if r[c[k]]), "")
        amount = str(money(r[c["Total Price"]]).quantize(ca_common.CENTS))
        items.append({"agency_id": agency, "fiscal_year": fy[5:], "date": date, "vendor": vendor, "brand": "",
                      "product_type": product, "description": description,
                      "quantity": r[c["Quantity"]].strip(), "unit_price": str(money(r[c["Unit Price"]])) if r[c["Unit Price"]].strip() else "",
                      "amount": amount, "source_record_id": rid})
        txns.append({"agency_id": agency, "fiscal_year": fy[5:], "posting_date": date, "payee_name": vendor,
                     "description": description,
                     "account": " / ".join(x for x in [r[c["Acquisition Type"]], r[c["Acquisition Method"]],
                                                       r[c["Sub-Acquisition Method"]]] if x),
                     "category_published": r[c["Segment Title"]], "amount": amount, "source_record_id": rid})
    common.upsert_rows(ST, "line_items.csv.gz", SOURCE, items)
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, txns)

    years = sorted({int(r["fiscal_year"]) for r in items})
    ca_common.register_source({
        "source": SOURCE, "name": "SCPRS Purchase Order Data (CAL FIRE purchase orders)", "tier": "2",
        "url": PAGE, "years": f"{years[0]}-{years[-1]}", "fiscal_year": "California state FY, Jul-Jun",
        "fetched": d.parent.parent.name,
        "note": "CAL FIRE (state fire agency) purchase order lines with quantity, unit price and UNSPSC commodity; "
                "FY2012-13 to FY2014-15 only (the State publishes no later bulk extract); purchase order amounts, "
                "not payments; no brand field"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in items)
    print(f"{ST}: {SOURCE}: {len(items)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; {dropped} lines dropped as "
          f"reloaded POs; {repeats} identical lines kept as separate PO lines; {zero} $0 lines left out")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
