"""Download raw source data into raw/<YYYY-MM-DD>/.

Sources:
  transparent_utah  vendor totals, entity details and expense categories per agency
                    (the public query service behind transparent.utah.gov)
  usfa              National Fire Department Registry, Utah CSV
  openfema          Firefighter grant awards (AFG, SAFER, FP&S) to Utah recipients

Raw files are written once per fetch date and never edited. Python standard library only.

    python3 pipeline/fetch.py            # all sources
    python3 pipeline/fetch.py usfa       # one source
"""
import csv
import datetime
import gzip
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TODAY = datetime.date.today().isoformat()
OUT = ROOT / "raw" / TODAY

TU_API = "https://tu-query-handler-prod-778714388561.us-west3.run.app/"
USFA_STATES = "https://apps.usfa.fema.gov/registry/api/lookups/states"
USFA_STATE_CSV = "https://apps.usfa.fema.gov/registry/api/download/state/{code}"
FEMA_GRANTS = "https://www.fema.gov/api/open/v1/NonDisasterAssistanceFirefighterGrants"

HEADERS = {"User-Agent": "utah-fire-procurement/0.1 (github.com/pasha594/utah-fire-procurement)"}
DELAY = 1.0  # seconds between requests


def get(url, tries=4):
    for attempt in range(tries):
        time.sleep(DELAY)
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            if body.strip().startswith((b"Internal", b"<!doctype")):
                raise RuntimeError(body[:80].decode(errors="replace"))
            return body
        except Exception as e:
            if attempt == tries - 1:
                raise
            print(f"  retry {attempt + 1} after error: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def save(rel, body):
    path = OUT / (rel + ".gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(body, mtime=0))
    return path


def tu(function, parameter):
    q = urllib.parse.urlencode({"function": function, "parameter": json.dumps(parameter)})
    return get(TU_API + "?" + q)


def agencies():
    with open(ROOT / "config" / "agencies.csv", newline="") as f:
        return [r for r in csv.DictReader(f) if r["include"] == "yes"]


def fetch_transparent_utah():
    save("transparent_utah/entities.json", tu("getListOfAllEntities", {}))
    for a in agencies():
        tid, name = int(a["tu_id"]), a["name"]
        print(f"  {tid} {name}")
        save(f"transparent_utah/vendors/{tid}.json", tu("getVendorSearchByEntity", {"entity_name": name}))
        save(f"transparent_utah/details/{tid}.json", tu("getEntityDetails", {"entity_id": tid}))
        save(f"transparent_utah/expense_categories/{tid}.json",
             tu("getEntityExpensesCats", {"entity_id": tid, "fiscal_year": 2024}))


def fetch_usfa():
    states = json.loads(get(USFA_STATES))
    code = next(s["code"] for s in states if s["shortDesc"] == "UT")
    save("usfa/registry_ut.csv", get(USFA_STATE_CSV.format(code=code)))


def fetch_openfema():
    rows, skip = [], 0
    while True:
        q = urllib.parse.urlencode({"$filter": "vendorState eq 'UT'", "$top": 1000, "$skip": skip})
        page = json.loads(get(FEMA_GRANTS + "?" + q))["NonDisasterAssistanceFirefighterGrants"]
        rows += page
        if len(page) < 1000:
            break
        skip += 1000
    save("openfema/firefighter_grants_ut.json", json.dumps(rows, indent=0).encode())
    print(f"  {len(rows)} awards")


SOURCES = {"transparent_utah": fetch_transparent_utah, "usfa": fetch_usfa, "openfema": fetch_openfema}

if __name__ == "__main__":
    for name in sys.argv[1:] or SOURCES:
        print(f"{name} -> raw/{TODAY}/{name}")
        SOURCES[name]()
