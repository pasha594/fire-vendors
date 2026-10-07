"""City of Houston checkbook: payment lines of the Houston Fire Department (HFD).

    python3 pipeline/sources/tx_houston.py fetch
    python3 pipeline/sources/tx_houston.py normalize

Source: https://data.houstontx.gov/dataset/checkbook (City of Houston Finance Department, CKAN, Open Data Commons
Attribution License). One CSV per City fiscal year (July to June, the year it ends in), 2018 to the current
year, about 55-62 MB and 230,000-280,000 lines each. Columns: payment document number, fund, department, WBS
(project), GL account, vendor name, vendor invoice, fiscal year, clearing date, amount, type of procurement,
purchase order number and item, contract number.

fetch      raw/<date>/tx/tx_houston/checkbook_page.html.gz       the dataset page the download links come from
           raw/<date>/tx/tx_houston/checkbook-<fy>-hfd.csv.gz    lines of department 1200 (HFD) only, FY2021 on
           raw/<date>/tx/tx_houston/manifest.json.gz             each full file's URL, bytes, SHA-256, line counts
           raw/<date>/tx/tx_houston/sample.csv.gz                first 100 lines of the newest full file
           The site's robots.txt disallows /api/, so links are read from the dataset page, not the CKAN API,
           and asks for a 10-second crawl delay, which resolve() keeps between requests to data.houstontx.gov.
           Downloads redirect to a presigned S3 URL written with an explicit ':443' port, whose signature fails
           when urllib follows the redirect; fetch resolves the redirect itself and drops the port.
normalize  data/states/tx/transactions.csv.gz   one row per HFD payment line
           data/states/tx/agencies.json         via common.assemble_agencies

Attribution: Department ID 1200, "Houston Fire Department (HFD)", linked to TX-KA926 in agency_sources.csv.

Duplicates and reversals: owner rule of 2026-10-07 as corrected the same day (tx_common.dedup): two lines are
identical when every column of the raw file is equal, except columns that only identify the row or the load; the
Houston files have none (no row id, no load stamp; ROW_IDS is empty), so all 18 columns are compared, the payment
document number, vendor invoice, PO number and item and contract number included: lines that differ in any of them
are different payments and are kept. Of a set of identical lines the first in file order is kept. Void-safe: a set
of n identical positive lines keeps min(n, reversals + 1), where reversals counts the distinct lines equal in every
REVERSAL_KEYS column (fund, department, WBS, GL account, vendor, vendor invoice, type of procurement, PO number and
item, contract; the City repeats them on a reversal, which can come in another payment document on another day)
with the amount negated in the same or the next fiscal year. Identical voids (owner decision A of 2026-10-07): a set
of identical negative lines keeps one copy when its family (same REVERSAL_KEYS, amount up to sign, same or next
fiscal year) has no payments; in a family with payments a negative copy is dropped only together with an identical
positive copy of the family that the void rule drops, so the family keeps its raw net. On the raw files of
2026-10-06: 24 sets of identical lines; 21 of the 23 positive sets are payment, reversal and re-payment sequences
inside one payment document and keep both copies; 2 lines are dropped ($206.10 and $19.62 to "*", no reversal,
$225.72). The one negative set, two -$12,400.00 Life-Assist reversals of invoice 1369849 (2024-03-29), keeps both:
its family's two identical payments are both kept, so no positive copy is dropped, and the family nets $12,400.00
as published (kept once, it netted $24,800.00). Negative lines (early payment discounts, credits, vendor offsets, reversals) are kept, so
amounts are net. Payee names are published as the source publishes them, employees included (owner decision,
2026-10-06); common.withhold_person only cuts email addresses and bank account text. Vendor name "*" is the City's
own mask for a withheld vendor and is kept as published.
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
import time
import urllib.error
import urllib.request

import common
import tx_common

ST = "TX"
SOURCE = "tx_houston"
PAGE = "https://data.houstontx.gov/dataset/checkbook"
DEPARTMENT = "1200"
FIRST_FY = 2021
CRAWL_DELAY = 10  # data.houstontx.gov robots.txt: "Crawl-delay: 10" for every user agent
ROW_IDS = ()  # raw columns that only identify the row or the load: the Houston files have none
REVERSAL_KEYS = ("Fund ID", "Fund Name", "Department ID", "Department Name", "WBS ID", "WBS Description",
                 "GL Account Number", "GL Account Description", "Vendor Name", "Vendor Invoice", "Type of procurement",
                 "Purchase Order Number", "Purchase Order Item", "Contract Number")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def resolve(url):
    """Location of a CKAN download redirect, with S3's explicit ':443' port removed (see docstring). Waits the
    host's 10-second crawl delay first (the download itself goes to S3, another host)."""
    time.sleep(max(common.DELAY, CRAWL_DELAY))
    try:
        urllib.request.build_opener(_NoRedirect).open(urllib.request.Request(url, headers=common.HEADERS), timeout=60)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.headers["Location"].replace(".amazonaws.com:443/", ".amazonaws.com/")
        raise
    return url


def links(page):
    """{fiscal year: download URL} from the dataset page."""
    out = {}
    for url in re.findall(r'href="(https://data\.houstontx\.gov/dataset/[^"]+/download/checkbook-(\d{4})\.csv)"', page):
        out[int(url[1])] = url[0]
    return out


def fetch():
    page = common.get(PAGE)
    common.save_raw(ST, SOURCE, "checkbook_page.html", page)
    files = links(page.decode("utf-8", "replace"))
    assert files and max(files) >= 2026, f"no checkbook links found on {PAGE}"
    manifest = []
    for fy in sorted(y for y in files if y >= FIRST_FY):
        body = common.get(resolve(files[fy]), timeout=900)
        text = body.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        dept = header.index("Department ID")
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\n")
        w.writerow(header)
        n = kept = 0
        for row in reader:
            n += 1
            if row[dept] == DEPARTMENT:
                w.writerow(row)
                kept += 1
        common.save_raw(ST, SOURCE, f"checkbook-{fy}-hfd.csv", out.getvalue().encode("utf-8"))
        manifest.append({"fiscal_year": fy, "url": files[fy], "bytes": len(body),
                         "sha256": hashlib.sha256(body).hexdigest(), "lines": n, "hfd_lines": kept})
        print(f"  FY{fy}: {n} lines, {kept} HFD lines, {len(body):,} bytes")
        if fy == max(files):
            common.save_raw(ST, SOURCE, "sample.csv", "".join(text.splitlines(keepends=True)[:101]).encode("utf-8"))
    common.save_raw(ST, SOURCE, "manifest.json", json.dumps(manifest, indent=1).encode())




def iso(d):
    return datetime.datetime.strptime(d, "%m/%d/%Y").date().isoformat() if d else ""


def normalize():
    raw = common.latest_raw(ST, SOURCE)
    assert raw, "run fetch first"
    links_ = [r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == SOURCE]
    assert len(links_) == 1 and links_[0]["source_entity_id"] == DEPARTMENT, "agency_sources.csv: one HFD row expected"
    aid = links_[0]["agency_id"]
    records, fys = [], []  # raw lines in file order (files by fiscal year), and each line's file year
    for path in sorted(raw.glob("checkbook-*-hfd.csv.gz")):
        fy_file = int(re.search(r"checkbook-(\d{4})-hfd", path.name).group(1))
        for r in csv.DictReader(io.StringIO(common.read_gz(path).decode("utf-8"))):
            assert r["Department ID"] == DEPARTMENT
            assert int(r["Fiscal Year"]) == fy_file, f"{path.name}: line from FY{r['Fiscal Year']}"
            records.append(r)
            fys.append(fy_file)
    drop, dropped = tx_common.dedup(records, ROW_IDS, REVERSAL_KEYS, "Amount", "Fiscal Year")
    rows, per_doc = [], collections.Counter()
    for i, (r, fy_file) in enumerate(zip(records, fys)):
        doc = r["Payment Document Number"]
        per_doc[(fy_file, doc)] += 1  # counts every raw line, so a kept line's id does not move when a copy is dropped
        if i in drop:
            continue
        gl, gl_desc = r["GL Account Number"], r["GL Account Description"]
        po = "/".join(x for x in (r["Purchase Order Number"], r["Purchase Order Item"]) if x and x.strip("0"))
        rows.append({
            "agency_id": aid, "fiscal_year": fy_file, "posting_date": iso(r["Clearing Date"]),
            "payee_name": common.withhold_person(r["Vendor Name"]),
            "description": " / ".join(x for x in (r["Type of procurement"], r["WBS Description"],
                                                   f"PO {po}" if po else "",
                                                   f"contract {r['Contract Number']}" if r["Contract Number"] else "") if x),
            "account": " / ".join(x for x in (r["Fund Name"], f"{gl} {gl_desc}") if x.strip()),
            "category_published": gl_desc, "amount": f"{float(r['Amount']):.2f}",
            "source_record_id": f"FY{fy_file}:{doc}:{per_doc[(fy_file, doc)]}",
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
