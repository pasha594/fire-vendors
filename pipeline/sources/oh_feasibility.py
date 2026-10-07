"""Samples and manifests behind docs/sources/oh.md for the Ohio sources that were reached but not built.

    python3 pipeline/sources/oh_feasibility.py fetch [oh_checkbook_state] [oh_aos]

Not an adapter: it writes only raw/<date>/oh/<source>/ files and no table in data/states/oh/, because neither
source has a record that clearly belongs to a fire agency (see docs/sources/oh.md).

oh_checkbook_state  Ohio Checkbook state expenditures, the bulk files on the DataOhio portal (dataset "Ohio
                    Checkbook", id CHECKBOOK_ID): one zip per state fiscal year, one CSV per month, one row per
                    payment line of a state agency. The portal answers 404 to a User-Agent that does not start
                    with "Mozilla/5.0 (", so requests use the project's agent in the usual crawler form
                    (DATAOHIO_UA); its JSON API needs the session cookie of the dataset page and that page as
                    Referer, as the page's own download button sends. robots.txt allows both paths.
    raw/<date>/oh/oh_checkbook_state/versions.json.gz   the dataset's file list
    raw/<date>/oh/oh_checkbook_state/manifest.json.gz   per file: URL, bytes, SHA-256, members, rows, columns,
                                                        rows and dollars per department (state agency)
    raw/<date>/oh/oh_checkbook_state/sample.csv.gz      first 100 rows of the newest file. Address columns are
                                                        dropped and payees pass through common.withhold_person:
                                                        the source masks individuals as "Masked Payee" but
                                                        often leaves their name in ADDRESS1.
    The full files (213 to 616 MB each) are not kept: no row can be attributed to a fire agency.

oh_aos              Ohio Auditor of State, Summarized Annual Financial Reports (unaudited Hinkle System data):
                    one Excel workbook per entity type, filing year and basis of accounting.
    raw/<date>/oh/oh_aos/Township_2024_REG_Summarized.xlsx.gz   townships, regulatory cash basis, 2024
    raw/<date>/oh/oh_aos/sample.csv.gz                          first 100 rows of its total-governmental sheet
"""
import csv
import hashlib
import http.cookiejar
import io
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import common

ST = "OH"
DATAOHIO = "https://data.ohio.gov"
CHECKBOOK_PAGE = DATAOHIO + "/wps/portal/gov/data/view/ohio-checkbook"
CHECKBOOK_ID = "04f1a227-c0d8-4d84-938f-f41ca9c49226"
API = DATAOHIO + "/apigateway-secure/data-portal"
DATAOHIO_UA = "Mozilla/5.0 (compatible; utah-fire-procurement/0.1; +https://github.com/pasha594/utah-fire-procurement)"
CHECKBOOK_COLUMNS = ["account", "account_name", "department_id", "department_description", "payment_date",
                     "payment_method", "payment_reference_id", "amount", "vendor_name", "address1", "address2", "city",
                     "state", "zip", "transaction_month"]  # the files use two header spellings; order is the same
SAMPLE_DROP = {"address1", "address2", "zip"}

AOS_REPORTS = "https://ohioauditor.gov/references/SummarizedAnnualFinancialReports/SummarizedReports/"
AOS_FILE = "Township_2024_REG_Summarized.XLSX"


def checkbook_state():
    src = "oh_checkbook_state"
    # DataOhio's API checks the portal session cookie: keep cookies for this process (common.get uses urlopen,
    # which goes through the installed opener).
    urllib.request.install_opener(urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())))
    page = {"User-Agent": DATAOHIO_UA}
    api = {**page, "Referer": CHECKBOOK_PAGE, "Accept": "application/json"}
    common.get(CHECKBOOK_PAGE, headers=page)
    body = common.get(f"{API}/data-sets/{CHECKBOOK_ID}/versions", headers=api)
    common.save_raw(ST, src, "versions.json", body)
    versions = sorted(json.loads(body), key=lambda v: v["name"])
    manifest, newest = [], None
    for v in versions:
        for ref in v["fileReferences"]:
            signed = json.loads(common.get(f"{API}/download-file/{CHECKBOOK_ID}?key={ref['url']}", headers=api))["url"]
            print(f"{ST}: {src}: {v['name']}: {ref['name']}")
            data = common.get(signed, timeout=600)
            entry = {"version": v["name"], "date_added": v["dateAdded"], "file": ref["name"],
                     "url": signed.split("?")[0], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                     "members": [], "rows": 0, "departments": {}}
            depts = {}
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for m in sorted(z.infolist(), key=lambda i: i.filename):
                    with z.open(m) as f:
                        reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline=""))
                        header = next(reader)
                        n = 0
                        for row in reader:
                            if len(row) < 15:
                                continue
                            n += 1
                            d = depts.setdefault(row[2], {"name": row[3], "rows": 0, "amount": 0.0})
                            d["rows"] += 1
                            try:
                                d["amount"] += float(row[7])
                            except ValueError:
                                pass
                    entry["members"].append({"name": m.filename, "rows": n, "header": header})
                    entry["rows"] += n
            entry["departments"] = {k: {**d, "amount": round(d["amount"], 2)} for k, d in sorted(depts.items())}
            manifest.append(entry)
            print(f"  {len(data):,} bytes, {entry['rows']:,} rows, {len(depts)} departments")
            if newest is None or v["dateAdded"] > newest[0]:
                newest = (v["dateAdded"], data)
    common.save_raw(ST, src, "manifest.json", json.dumps(manifest, indent=1).encode())
    with zipfile.ZipFile(io.BytesIO(newest[1])) as z:
        first = sorted(z.infolist(), key=lambda i: i.filename)[0]
        with z.open(first) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline=""))
            next(reader)
            rows = []
            for row in reader:
                r = dict(zip(CHECKBOOK_COLUMNS, row))
                r["vendor_name"] = common.withhold_person(r["vendor_name"])
                rows.append(r)
                if len(rows) == 100:
                    break
    buf = io.StringIO()
    w = csv.DictWriter(buf, [c for c in CHECKBOOK_COLUMNS if c not in SAMPLE_DROP], lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    common.save_raw(ST, src, "sample.csv", buf.getvalue().encode())


def xlsx_sheets(data):
    """Minimal standard-library .xlsx reader: {sheet name: [row lists]}."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    z = zipfile.ZipFile(io.BytesIO(data))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    out = {}
    for s in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", ns):
        target = rels[s.get("{%s}id" % ns["r"])].lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter("{%s}row" % ns["m"]):
            cells = {}
            for c in row.findall("m:c", ns):
                col = 0
                for ch in re.match(r"[A-Z]+", c.get("r")).group(0):
                    col = col * 26 + ord(ch) - 64
                v = c.find("m:v", ns)
                if c.get("t") == "s" and v is not None:
                    val = shared[int(v.text)]
                elif c.get("t") == "inlineStr":
                    val = "".join(t.text or "" for t in c.iter("{%s}t" % ns["m"]))
                else:
                    val = v.text if v is not None else ""
                cells[col - 1] = val
            if cells:
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
        out[s.get("name")] = rows
    return out


def aos():
    src = "oh_aos"
    data = common.get(AOS_REPORTS + AOS_FILE)
    common.save_raw(ST, src, AOS_FILE.replace(".XLSX", ".xlsx"), data)
    sheets = xlsx_sheets(data)
    rows = sheets["CSOCRCDACIFCB_TotalGov"]
    head = next(i for i, r in enumerate(rows) if r and r[0] == "Entity Name")
    header = [h.strip() or f"column_{i + 1}" for i, h in enumerate(rows[head])]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows[head + 1:head + 101]:
        w.writerow(r + [""] * (len(header) - len(r)))
    common.save_raw(ST, src, "sample.csv", buf.getvalue().encode())
    print(f"{ST}: {src}: {AOS_FILE}: sheets {', '.join(sheets)}; {len(rows) - head - 1} townships")


if __name__ == "__main__":
    assert sys.argv[1] == "fetch", "usage: oh_feasibility.py fetch [oh_checkbook_state] [oh_aos]"
    steps = {"oh_checkbook_state": checkbook_state, "oh_aos": aos}
    for name in sys.argv[2:] or steps:
        steps[name]()
