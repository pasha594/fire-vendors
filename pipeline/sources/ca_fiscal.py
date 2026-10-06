"""Open FI$Cal department vendor transactions: payments of CAL FIRE, the state fire agency (tier 1).

    python3 pipeline/sources/ca_fiscal.py fetch
    python3 pipeline/sources/ca_fiscal.py normalize

Source: Open FI$Cal (https://open.fiscal.ca.gov), the State of California's expenditure transparency site, page
"Department Vendor Transaction Files" (https://open.fiscal.ca.gov/dept_vendor_transaction.html): one CSV per
state department and fiscal year with "the subset of spending transactions with associated vendor names",
listed in a pointer file and served from Azure blob storage (adwoutputfilesadlsstore.blob.core.windows.net,
no robots.txt). Terms of use (https://open.fiscal.ca.gov/terms-of-use.html): "You may use the data as you wish
provided your use is neither illegal nor malicious"; data are raw and unaudited. Files are named
Vendor_<business unit>_<department>_FY<yy>.csv where FY<yy> is the fiscal year that BEGINS in 20<yy> (FY23 =
July 2023-June 2024 = fiscal_year 2024 here). CAL FIRE is business unit 3540. Columns: business unit, agency
and department name, document id (business unit, voucher, line and distribution), related document,
accounting date, fiscal year begin, accounting period, vendor name, account (number, type, category,
sub-category, description), fund, program, sub-program, budget reference, year of enactment, amount. The State
masks individuals as "CONFIDENTIAL".

fetch      raw/<date>/ca/ca_fiscal/pointer.csv.gz                     the site's list of department vendor files
           raw/<date>/ca/ca_fiscal/Vendor_3540_CALFIRE_FY<yy>.csv.gz  each CAL FIRE file for fiscal years 2021 on,
                                                                      unmodified (137 to 236 MB each unzipped)
           raw/<date>/ca/ca_fiscal/manifest.json.gz                   per file: URL, upload date, bytes, SHA-256,
                                                                      rows, dollars
           raw/<date>/ca/ca_fiscal/sample.csv.gz                      header and first 100 rows of the newest file
normalize  data/states/ca/transactions.csv.gz   one row per voucher, payee, account, fund, program and
                                                accounting date (see below)
           config/states/ca/sources.csv         this source's row
           data/states/ca/agencies.json         via common.assemble_agencies

Attribution: the whole department (business unit 3540, "CAL FIRE"), linked to the registry's
"CA Department of Forestry and Fire Protection- HQ" (CA-00555) in agency_sources.csv as a state fire agency
(PRD open question). The registry's regional CAL FIRE rows are not linked. CAL FIRE spending covers wildland
fire protection, the State Fire Marshal and resource management (forestry grants), not only fire suppression.

Rows: each file has about 535,000 distribution lines a year, 60% of them CalCard (procurement card) lines whose
payee is the card issuer, US Bank. Lines are summed to one row per voucher (the document id without its line
and distribution numbers), payee, account, fund, program and accounting date, which keeps every published
field but the line number (about 142,000 rows a year). source_record_id is the voucher plus a running number
in the sorted order of its rows. Rows that sum to $0.00 are dropped.

Duplicates and reversals: lines identical in every column (same document id, line and distribution, amount
and date) are kept once (22 in FY2023-24). Lines that repeat a document id with a different date or amount are
later postings to the same line (corrections, reversals) and are kept, as negative amounts where published so.
"""
import collections
import csv
import decimal
import hashlib
import io
import json
import re
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_fiscal"
POINTER = ("https://adwoutputfilesadlsstore.blob.core.windows.net/transparency/DepartmentVendorTransactionPointer/"
           "DepartmentVendorTransactionPointer.csv")
FILE = re.compile(r"^Vendor_3540_CALFIRE_FY(\d\d)\.csv$")
FIRST_FY = 2021
COLUMNS = ["business_unit", "agency_name", "department_name", "document_id", "related_document", "accounting_date",
           "fiscal_year_begin", "accounting_period", "VENDOR_NAME", "account", "account_type", "account_category",
           "account_sub_category", "account_description", "fund_code", "fund_group", "fund_description",
           "program_code", "program_description", "sub_program_description", "budget_reference",
           "budget_reference_category", "budget_reference_sub_category", "budget_reference_description",
           "year_of_enactment", "monetary_amount"]


def files(pointer_body):
    out = []
    for r in csv.DictReader(io.StringIO(pointer_body.decode("utf-8-sig"))):
        m = FILE.match(r["FileName"].strip())
        if m and 2000 + int(m.group(1)) + 1 >= FIRST_FY:
            out.append({"file": r["FileName"].strip(), "fiscal_year": 2000 + int(m.group(1)) + 1,
                        "url": r["Download"].strip(), "upload_date": r["UploadDate"], "listed_size": r["FileSize"]})
    return sorted(out, key=lambda f: f["fiscal_year"])


def fetch():
    pointer = common.get(POINTER)
    common.save_raw(ST, SOURCE, "pointer.csv", pointer)
    manifest, todo = [], files(pointer)
    for f in todo:
        body = common.get(f["url"], timeout=1200)
        rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
        assert rows[0] == COLUMNS, f"{f['file']}: columns changed: {rows[0]}"
        dollars = sum(decimal.Decimal(r[COLUMNS.index("monetary_amount")] or "0") for r in rows[1:])
        manifest.append({**f, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "rows": len(rows) - 1,
                         "dollars": str(dollars)})
        common.save_raw(ST, SOURCE, f["file"], body)
        print(f"  {f['file']}: {len(rows) - 1} rows, ${dollars:,.2f}", flush=True)
        if f is todo[-1]:
            common.save_raw(ST, SOURCE, "sample.csv", b"\n".join(body.split(b"\n")[:101]) + b"\n")
    common.save_raw(ST, SOURCE, "manifest.json", json.dumps(manifest, indent=1).encode())


def read_file(d, entry):
    text = common.read_gz(d / (entry["file"] + ".gz")).decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    assert next(reader) == COLUMNS, f"{entry['file']}: columns changed"
    return reader


def voucher(document_id):
    """'3540.00481153.0.00002.0001' -> '3540.00481153.0' (business unit, voucher, sequence)."""
    parts = document_id.split(".")
    assert len(parts) == 5, document_id
    return ".".join(parts[:3])


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    link = ca_common.links(SOURCE)
    assert len(link) == 1
    agency = link[0]["agency_id"]
    manifest = json.loads(common.read_gz(d / "manifest.json.gz"))
    ix = {c: i for i, c in enumerate(COLUMNS)}
    groups = collections.defaultdict(decimal.Decimal)
    dropped = lines = 0
    for entry in manifest:
        seen = set()
        n = 0
        for r in read_file(d, entry):
            n += 1
            h = hashlib.blake2b("\x1f".join(r).encode(), digest_size=16).digest()
            if h in seen:
                dropped += 1
                continue
            seen.add(h)
            fy = int(r[ix["fiscal_year_begin"]]) + 1
            assert fy == entry["fiscal_year"] and r[ix["business_unit"]] == link[0]["source_entity_id"], r
            key = (fy, voucher(r[ix["document_id"]]), r[ix["VENDOR_NAME"]], r[ix["accounting_date"]],
                   r[ix["account"]], r[ix["account_category"]], r[ix["account_description"]], r[ix["fund_code"]],
                   r[ix["fund_description"]], r[ix["program_description"]], r[ix["sub_program_description"]])
            groups[key] += decimal.Decimal(r[ix["monetary_amount"]] or "0")
        assert n == entry["rows"], f"{entry['file']}: {n} rows, manifest says {entry['rows']}"
        lines += n
    seq, rows, zero = collections.Counter(), [], 0
    for key in sorted(groups):
        fy, vch, vendor, date, acct, acat, adesc, fund, fdesc, prog, sub = key
        amount = groups[key].quantize(ca_common.CENTS)
        if amount == 0:
            zero += 1
            continue
        seq[vch] += 1
        rows.append({
            "agency_id": agency, "fiscal_year": str(fy), "posting_date": date[:10],
            "payee_name": common.withhold_person(vendor), "description": "",
            "account": " / ".join(x for x in [prog, sub, f"{fund} {fdesc}", f"{acct} {adesc}"] if x.strip()),
            "category_published": f"{acat}: {adesc}", "amount": str(amount),
            "source_record_id": f"{vch}/{seq[vch]}",
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["posting_date"] for r in rows)
    ca_common.register_source({
        "source": SOURCE, "name": "Open FI$Cal department vendor transactions (CAL FIRE)", "tier": "1",
        "url": "https://open.fiscal.ca.gov/dept_vendor_transaction.html", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "California state FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "CAL FIRE (state fire agency, business unit 3540), whole department: fire protection, State Fire "
                "Marshal and resource management; lines summed per voucher, payee, account, fund, program and date; "
                "CalCard purchases appear as payments to US Bank; individuals are masked by the State; "
                f"FY{years[-1]} partial (postings through {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    withheld = sum(r["payee_name"] == "Payee name withheld" for r in rows)
    print(f"{ST}: {SOURCE}: {lines} source lines -> {len(rows)} rows (${total:,.2f}), FY{years[0]}-FY{years[-1]}; "
          f"{dropped} exact duplicate lines dropped; {zero} rows summing to $0 dropped; {withheld} rows withheld")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
