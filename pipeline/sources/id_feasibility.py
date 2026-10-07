"""Samples behind docs/sources/id.md for the Idaho sources that were reached but not built.

    python3 pipeline/sources/id_feasibility.py fetch [id_cities] [id_lgr_compliance] [id_contracts]

Not an adapter: it writes only raw/<date>/id/<source>/ files and no table in data/states/id/, because none of these
sources has a record that clearly belongs to a fire agency (see docs/sources/id.md).

id_cities          Transparent Idaho city financial data: the site's JSON API (getCityFinancials, the call its City
                   pages make) gives each of the 198 cities' whole-city budgeted and actual revenue and expenditure
                   per fiscal year, with links to the filed budget, audit or actuals PDF. No department or function
                   field, so a city fire department's spend cannot be separated. The department views on the City
                   pages are Power BI reports (embed token per report), not a bulk download or API.
    raw/<date>/id/id_cities/city_financials_fy2024.json.gz   the full FY2024 answer (198 cities)
    raw/<date>/id/id_cities/sample.json.gz                   its first 100 records
id_lgr_compliance  Local Government Entity Registry compliance report (https://lgcr-compliance.sco.idaho.gov/): the
                   site's own data file lists every registered entity with its type, county and compliance status.
                   No dollars; used only to cross-check the fire district list of id_lgr.
    raw/<date>/id/id_lgr_compliance/current_data.json.gz     the site's data file as published
    raw/<date>/id/id_lgr_compliance/sample.json.gz           its first 100 entities
id_contracts       Statewide Agreements and Contracts (SCO open data portal, CKAN, Open Data Commons Attribution
                   License): one Excel file of state contracts. Contract awards, not payments, and statewide
                   agreements are not tied to a fire agency. robots.txt disallows the CKAN /api/, so the file is
                   read from its download link on the dataset page.
    raw/<date>/id/id_contracts/dataset.html.gz               the dataset page the link comes from
    raw/<date>/id/id_contracts/sample.csv.gz                 the first 100 rows of the first sheet, without the
                                                             agency contact name, e-mail and phone columns
"""
import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import common

ST = "ID"
TI_UA = "Mozilla/5.0 (compatible; utah-fire-procurement/0.1; +https://github.com/pasha594/utah-fire-procurement)"
CKAN = "https://idahoprod.ogopendata.com"


def cities():
    body = common.get("https://transparent.idaho.gov/api/getCityFinancials", {"FiscalYear": 2024},
                      headers={"User-Agent": TI_UA})
    assert body[:1] == b"[", f"not JSON: {body[:80]!r}"
    recs = json.loads(body)
    common.save_raw(ST, "id_cities", "city_financials_fy2024.json", json.dumps(recs, indent=0).encode())
    common.save_raw(ST, "id_cities", "sample.json", json.dumps(recs[:100], indent=0).encode())
    print(f"  id_cities: {len(recs)} cities, fields {sorted(recs[0])}")


def compliance():
    body = common.get("https://lgcr-compliance.sco.idaho.gov/assets/current_data.json")
    d = json.loads(body)
    common.save_raw(ST, "id_lgr_compliance", "current_data.json", body)
    common.save_raw(ST, "id_lgr_compliance", "sample.json", json.dumps(d["e"][:100], indent=0).encode())
    print(f"  id_lgr_compliance: {len(d['e'])} entities")


def xlsx_rows(body):
    """Rows of the first sheet of an .xlsx file (standard library only)."""
    z = zipfile.ZipFile(io.BytesIO(body))
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])))
    sheet = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))[0]
    rows = []
    for row in ET.fromstring(z.read(sheet)).iter("{%s}row" % ns["m"]):
        vals = {}
        for c in row.findall("m:c", ns):
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            v = c.find("m:v", ns)
            text = v.text if v is not None else "".join(t.text or "" for t in c.iter("{%s}t" % ns["m"]))
            vals[col] = shared[int(text)] if c.get("t") == "s" and text is not None else (text or "")
        idx = lambda s: sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(s)))
        width = max(idx(k) for k in vals) if vals else 0
        rows.append([next((v for k, v in vals.items() if idx(k) == i), "") for i in range(1, width + 1)])
    return rows


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def resolve(url):
    """Location of the portal's download redirect, a presigned S3 URL written with an explicit ':443' port whose
    signature fails when urllib follows it (as in tx_houston.py); the port is dropped."""
    time.sleep(common.DELAY)
    try:
        urllib.request.build_opener(_NoRedirect).open(urllib.request.Request(url, headers=common.HEADERS), timeout=60)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.headers["Location"].replace(".amazonaws.com:443/", ".amazonaws.com/")
        raise
    return url


def contracts():
    page = common.get(f"{CKAN}/dataset/statewide-agreements-and-contracts")
    common.save_raw(ST, "id_contracts", "dataset.html", page)
    url = re.search(rb'href="(https://idahoprod\.ogopendata\.com/dataset/[^"]+/download/[^"]+\.xlsx)"', page).group(1)
    rows = xlsx_rows(common.get(resolve(url.decode())))
    keep = [i for i, c in enumerate(rows[0]) if not c.startswith("Contact")]  # staff names, e-mails, phones
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([[r[i] if i < len(r) else "" for i in keep] for r in rows[:101]])
    common.save_raw(ST, "id_contracts", "sample.csv", buf.getvalue().encode())
    print(f"  id_contracts: {len(rows) - 1} rows, columns {rows[0]}")


if __name__ == "__main__":
    steps = {"id_cities": cities, "id_lgr_compliance": compliance, "id_contracts": contracts}
    assert sys.argv[1] == "fetch"
    for name in sys.argv[2:] or steps:
        steps[name]()
