"""Shared helpers for the multi-state source adapters in pipeline/sources/.

Python standard library only. Every adapter has two steps:
  fetch      download into raw/<date>/<st>/<source>/ (gzipped, written once, never edited)
  normalize  read the newest raw folder and write data/states/<st>/ (format: docs/multistate/data-contract.md)

Payee names are published as the source publishes them (owner decision, 2026-10-06); withhold_person only cuts
email addresses and bank account text. is_person and looks_like_person (copied from pipeline/build.py) remain
for checks and reports, not for withholding.
"""
import collections
import csv
import datetime
import gzip
import io
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TODAY = datetime.date.today().isoformat()
STATES = ["OH", "CA", "ID", "TX"]
HEADERS = {"User-Agent": "utah-fire-procurement/0.1 (github.com/pasha594/utah-fire-procurement)"}
DELAY = 1.0  # seconds between requests


def get(url, params=None, tries=4, timeout=180, headers=None):
    """GET with a 1-second throttle and retries. Returns bytes."""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    for attempt in range(tries):
        time.sleep(DELAY)
        try:
            req = urllib.request.Request(url, headers={**HEADERS, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if attempt == tries - 1:
                raise
            print(f"  retry {attempt + 1} after error: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def raw_dir(st, source, date=TODAY):
    return ROOT / "raw" / date / st.lower() / source


def save_raw(st, source, name, body, date=TODAY):
    """Write one raw file once. An existing file is left untouched (raw files are immutable)."""
    path = raw_dir(st, source, date) / (name + ".gz")
    if path.exists():
        print(f"  exists, kept: {path.relative_to(ROOT)}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(body, mtime=0))
    return path


def latest_raw(st, source):
    """Newest raw/<date>/<st>/<source>/ folder, or None."""
    dirs = sorted(p for p in (ROOT / "raw").iterdir()
                  if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name) and (p / st.lower() / source).is_dir())
    return dirs[-1] / st.lower() / source if dirs else None


def read_gz(path):
    return gzip.decompress(pathlib.Path(path).read_bytes())


def read_csv_text(text):
    return list(csv.DictReader(io.StringIO(text), skipinitialspace=True))


def config_dir(st):
    return ROOT / "config" / "states" / st.lower()


def data_dir(st):
    d = ROOT / "data" / "states" / st.lower()
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_config(st, name):
    path = config_dir(st) / name
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows, gz=False):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    body = buf.getvalue().encode("utf-8")
    path.write_bytes(gzip.compress(body, mtime=0) if gz else body)


def read_data_csv(path):
    path = pathlib.Path(path)
    body = read_gz(path) if path.suffix == ".gz" else path.read_bytes()
    return list(csv.DictReader(io.StringIO(body.decode("utf-8"))))


# --- Names ------------------------------------------------------------------------------------------------

def norm(name):
    """Same key as pipeline/build.py norm(): used to match payees against config/vendor_map.csv."""
    s = (name or "").upper().replace("&", " AND ")
    s = re.sub(r"['’`]", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\b([A-Z]) (?=[A-Z]\b)", r"\1", s)
    s = re.sub(r"\b(INC|INCORPORATED|LLC|LC|CORP|CORPORATION|CO|COMPANY|LTD|LLP|PC|PLLC|PLC|THE|DBA)\b", " ", s)
    return " ".join(s.split())


BUSINESS_WORDS = re.compile(
    r"\b(INC|LLC|LC|CORP|CO|COMPANY|LTD|LLP|PC|PLLC|GROUP|SERVICES?|SYSTEMS?|SUPPLY|CENTER|DEPT|DEPARTMENT|"
    r"DIVISION|BUREAU|OFFICE|CITY|COUNTY|STATE|UTAH|OHIO|IDAHO|TEXAS|CALIFORNIA|BANK|TRUST|FUND|ASSOCIATION|"
    r"ASSOC|DISTRICT|AUTHORITY|UNIVERSITY|COLLEGE|SCHOOL|HOSPITAL|CLINIC|FIRE|RESCUE|ACCOUNT|PAYABLE|TREASURER|"
    r"INSURANCE|STORE)\b", re.I)
PERSON = re.compile(r"^[A-Za-z'\-\. ]+,\s*[A-Za-z'\-\. ]+$")
PERSON_NO_COMMA = re.compile(r"^[A-Za-z'\-]{2,}( [A-Za-z]\.?)? [A-Za-z'\-]{2,}$")
WITHHELD = "Individual (name withheld)"


def is_person(raw):
    """'SMITH, JOHN'-style payee names (as pipeline/build.py)."""
    raw = (raw or "").strip()
    return bool(PERSON.match(raw)) and not BUSINESS_WORDS.search(raw) and len(raw.split(",")[0].split()) <= 3


def looks_like_person(raw):
    """'JOHN SMITH'-style payee names (as pipeline/build.py). Over-matches some two-word company names, so the
    adapters only apply it to payees that no vendor_map row claims (see withhold_person)."""
    raw = re.sub(r"\(.*?\)|[*#0-9]", " ", raw or "")
    raw = " ".join(raw.split())
    return bool(PERSON_NO_COMMA.match(raw)) and not BUSINESS_WORDS.search(raw)


_REDACTIONS = None
_KNOWN = None


def _load_name_rules():
    global _REDACTIONS, _KNOWN
    if _REDACTIONS is None:
        def rows(name):
            path = ROOT / "config" / name
            if not path.exists():
                return []
            with open(path, newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        _REDACTIONS = [re.compile(r["pattern"], re.I) for r in rows("payee_name_redactions.csv")]
        _KNOWN = {r["name_key"] for r in rows("vendor_map.csv") if r["category"] != "individuals"}
    return _REDACTIONS, _KNOWN


def withhold_person(payee, person_flag=False):
    """Payee name as it may be published. Owner decision of 2026-10-06: payee names are shown as published,
    private persons included. Only payee text matching config/payee_name_redactions.csv (email addresses,
    bank transfer text with account numbers) is withheld. person_flag is accepted and ignored, so adapters
    written for the earlier rule need no change."""
    redactions, _ = _load_name_rules()
    payee = " ".join((payee or "").split())
    if any(rx.search(payee) for rx in redactions):
        return "Payee name withheld"
    return payee


FIRE_NAME = re.compile(r"\b(FIRE|FIRE ?FIGHTERS?|ESD|EMERGENCY SERVICES? DIST|FPD|RESCUE|E\.?M\.?S\.?)\b", re.I)


def write_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# --- Normalized state files (docs/multistate/data-contract.md) ----------------------------------------------

TABLES = {
    "transactions.csv.gz": ["agency_id", "fiscal_year", "posting_date", "payee_name", "description", "account",
                            "category_published", "amount", "source", "source_record_id"],
    "line_items.csv.gz": ["agency_id", "fiscal_year", "date", "vendor", "brand", "product_type", "description",
                          "quantity", "unit_price", "amount", "source", "source_record_id"],
    "totals.csv": ["agency_id", "fiscal_year", "category_published", "amount", "source"],
}


def upsert_rows(st, table, source, rows):
    """Replace this source's rows in data/states/<st>/<table>, keep every other source's rows, sort, write.
    Re-running one adapter therefore never touches another adapter's output."""
    fields = TABLES[table]
    path = data_dir(st) / table
    keep = [r for r in read_data_csv(path) if r["source"] != source] if path.exists() else []
    for r in rows:
        r["source"] = source
        missing = set(fields) - set(r) - {"source_record_id", "description", "account", "category_published",
                                          "posting_date", "date", "brand", "product_type", "quantity", "unit_price"}
        assert not missing, f"{table}: row without {sorted(missing)}: {r}"
    out = keep + rows
    out.sort(key=lambda r: tuple(str(r.get(f) or "") for f in fields))
    write_csv(path, fields, out, gz=table.endswith(".gz"))
    print(f"  data/states/{st.lower()}/{table}: {len(rows)} rows from {source} ({len(out)} in file)")


AGENCY_FIELDS = ["id", "name", "kind", "county", "city", "usfa_fdid", "dept_type", "organization_type", "stations",
                 "career", "volunteer", "paid_per_call"]


def assemble_agencies(st):
    """Write data/states/<st>/agencies.json from config/states/<st>/agencies.csv (USFA registry),
    agencies_added.csv (agencies a source names that the registry lacks), agency_sources.csv (which source
    entity is which agency, with its fiscal-year start) and the rows present in the normalized tables.

    Coverage tier, best first: 1 payee rows from a tier-1 source; 2 item lines (or payee rows from a tier-2
    source); 3 published totals only; 4 directory only. An agency without rows is never given $0."""
    sources = {s["source"]: s for s in read_config(st, "sources.csv")}
    links = collections.defaultdict(list)
    for r in read_config(st, "agency_sources.csv"):
        links[r["agency_id"]].append(r)
    has = collections.defaultdict(set)  # agency_id -> {(table, source)}
    for table in TABLES:
        path = data_dir(st) / table
        if path.exists():
            for r in read_data_csv(path):
                has[r["agency_id"]].add((table, r["source"]))
    agencies = []
    for a in read_config(st, "agencies.csv") + read_config(st, "agencies_added.csv"):
        tiers = [4]
        for table, source in has.get(a["id"], ()):
            if table == "transactions.csv.gz":
                tiers.append(int(sources.get(source, {}).get("tier") or 1))
            elif table == "line_items.csv.gz":
                tiers.append(2)
            else:
                tiers.append(3)
        fy = sorted({r["fy_start"] for r in links.get(a["id"], []) if r.get("fy_start")})
        agencies.append({
            "id": a["id"], "state": st, "name": a["name"], "kind": a.get("kind") or None,
            "county": a.get("county") or None, "city": a.get("city") or None,
            "usfa_fdid": a.get("usfa_fdid") or None, "coverage": min(tiers),
            "sources": sorted(({"usfa"} if a.get("usfa_fdid") or a.get("dept_type") else set())
                              | ({"openfema"} if a.get("grants") not in (None, "", "0") else set())
                              | {s for _, s in has.get(a["id"], ())}),
            "fy_start": fy[0] if len(fy) == 1 else (fy or None),
            "usfa": {"dept_type": a.get("dept_type") or None, "organization_type": a.get("organization_type") or None,
                     **{k: int(a[k]) if a.get(k) else None for k in ("stations", "career", "volunteer", "paid_per_call")}}
            if a.get("usfa_fdid") or a.get("dept_type") else None,
            "grants": int(a["grants"]) if a.get("grants") else 0,
        })
    ids = [a["id"] for a in agencies]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate agency ids: {sorted(dupes)[:5]}"
    orphans = set(has) - set(ids)
    assert not orphans, f"rows for agencies not in agencies.csv/agencies_added.csv: {sorted(orphans)[:5]}"
    write_json(data_dir(st) / "agencies.json", {
        "state": st,
        "sources": list(sources.values()),
        "coverage_counts": {str(t): sum(a["coverage"] == t for a in agencies) for t in (1, 2, 3, 4)},
        "agencies": agencies,
    })
    print(f"  data/states/{st.lower()}/agencies.json: {len(agencies)} agencies, tiers "
          + ", ".join(f"{t}: {sum(a['coverage'] == t for a in agencies)}" for t in (1, 2, 3, 4)))
