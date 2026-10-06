"""Build data/data.json from the newest raw/<date>/ folder and the config/*.csv files.

    python3 pipeline/build.py                      # write data/data.json
    python3 pipeline/build.py --worklist out.csv   # also list vendors that need a manual category

Rules for vendors, in order:
  1. config/vendor_map.csv     normalized name -> canonical vendor name and category
  2. config/keyword_rules.csv  first regex that matches the normalized name sets the category
                               (and the vendor name, when the rule has one)
  3. otherwise                 "unclassified"
Payees that look like a person ("Last, First") are grouped as "Individuals (names withheld)".
"""
import collections
import csv
import datetime
import gzip
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
YEARS = list(range(2021, 2027))
PARTIAL_YEARS = [2026]
TU_SITE = "https://transparent.utah.gov/"

ENTITY_TYPES = {"Local and Special Service District": "Special district", "Interlocal": "Interlocal agency"}
STAFFING_GROUPS = {"Career": "Career", "Mostly career": "Combination", "Mostly volunteer": "Combination",
                   "Volunteer": "Volunteer"}
BUSINESS_WORDS = re.compile(
    r"\b(INC|LLC|LC|CORP|CO|COMPANY|LTD|LLP|PC|PLLC|GROUP|SERVICES?|SYSTEMS?|SUPPLY|CENTER|DEPT|DEPARTMENT|"
    r"DIVISION|BUREAU|OFFICE|CITY|COUNTY|STATE|UTAH|BANK|TRUST|FUND|ASSOCIATION|ASSOC|DISTRICT|AUTHORITY|"
    r"UNIVERSITY|COLLEGE|SCHOOL|HOSPITAL|CLINIC|FIRE|RESCUE|ACCOUNT|PAYABLE|TREASURER|INSURANCE|STORE)\b", re.I)
PERSON = re.compile(r"^[A-Za-z'\-\. ]+,\s*[A-Za-z'\-\. ]+$")


def read_csv(name):
    path = CONFIG / name
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_gz(path):
    return gzip.decompress(path.read_bytes())


def norm(name):
    s = (name or "").upper().replace("&", " AND ")
    s = re.sub(r"['’`]", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\b([A-Z]) (?=[A-Z]\b)", r"\1", s)  # "L N CURTIS" -> "LN CURTIS"
    s = re.sub(r"\b(INC|INCORPORATED|LLC|LC|CORP|CORPORATION|CO|COMPANY|LTD|LLP|PC|PLLC|PLC|THE|DBA)\b", " ", s)
    return " ".join(s.split())


PERSON_NO_COMMA = re.compile(r"^[A-Za-z'\-]{2,}( [A-Za-z]\.?)? [A-Za-z'\-]{2,}$")


def is_person(raw):
    raw = (raw or "").strip()
    return bool(PERSON.match(raw)) and not BUSINESS_WORDS.search(raw) and len(raw.split(",")[0].split()) <= 3


def looks_like_person(raw):
    """'NICK MOTTA'-style names. Only used for payees that no vendor_map row or keyword rule claims."""
    raw = re.sub(r"\(.*?\)|[*#0-9]", " ", raw or "")  # "NOLAN CURTIS (rent)", "MONTE CURTIS*"
    raw = " ".join(raw.split())
    return bool(PERSON_NO_COMMA.match(raw)) and not BUSINESS_WORDS.search(raw)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def latest_raw():
    dirs = sorted(p for p in (ROOT / "raw").iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))
    return dirs[-1]


def main(worklist_path=None):
    raw = latest_raw()
    tu = raw / "transparent_utah"
    categories = read_csv("categories.csv")
    cat_ids = {c["id"] for c in categories}
    rules = [(r["category"], re.compile(r["pattern"]), (r.get("vendor") or "").strip())
             for r in read_csv("keyword_rules.csv")]
    for c, _, _ in rules:
        assert c in cat_ids, f"keyword_rules.csv: unknown category {c}"
    vendor_map = {}
    for r in read_csv("vendor_map.csv"):
        assert r["category"] in cat_ids, f"vendor_map.csv: unknown category {r['category']} for {r['name_key']}"
        vendor_map[r["name_key"]] = (r["vendor"].strip(), r["category"])
    neris = [(r["vendor"], re.compile(r["match"])) for r in read_csv("neris_partners.csv")]

    # Agencies
    entity_types = {e["transparency_id"]: e["entity_government_type"]
                    for e in json.loads(read_gz(tu / "entities.json.gz")) if e.get("transparency_id")}
    usfa = {r["FDID"]: r for r in csv.DictReader(read_gz(raw / "usfa" / "registry_ut.csv.gz").decode("utf-8-sig").splitlines(),
                                                  skipinitialspace=True) if r["FDID"]}
    agencies = []
    for a in read_csv("agencies.csv"):
        if a["include"] != "yes":
            continue
        tid = int(a["tu_id"])
        details = json.loads(read_gz(tu / "details" / f"{tid}.json.gz"))
        details = details[0] if details else {}
        budget = collections.defaultdict(float)
        for x in json.loads(read_gz(tu / "expense_categories" / f"{tid}.json.gz")):
            if x["fiscal_year"] in YEARS:
                budget[x["fiscal_year"]] += x["net_amount"] or 0
        u = usfa.get(a["usfa_fdid"]) if a["usfa_fdid"] else None
        agencies.append({
            "id": tid,
            "name": a["name"],
            "type": ENTITY_TYPES.get(entity_types.get(tid), entity_types.get(tid)),
            "county": a["county"],
            "city": details.get("shipping_city") or details.get("billing_city"),
            "website": details.get("website"),
            "staffing": u["Dept Type"] if u else None,
            "staffing_group": STAFFING_GROUPS.get(u["Dept Type"]) if u else None,
            "usfa": {
                "fdid": u["FDID"], "name": u["Fire dept name"], "stations": int(u["Number Of Stations"] or 0),
                "career": int(u["Active Firefighters - Career"] or 0),
                "volunteer": int(u["Active Firefighters - Volunteer"] or 0),
                "paid_per_call": int(u["Active Firefighters - Paid per Call"] or 0),
            } if u else None,
            "budget": {str(y): round(budget[y]) for y in YEARS if y in budget},
            "notes": a["notes"] or None,
        })
    agency_ids = {a["id"] for a in agencies}

    # Vendor payments: one raw row = one agency x payee name x fiscal year (net amount)
    raw_rows = []
    for path in sorted((tu / "vendors").glob("*.json.gz")):
        tid = int(path.name.split(".")[0])
        if tid not in agency_ids:
            continue
        for x in json.loads(read_gz(path)):
            if x["fiscal_year"] in YEARS and x["net_amount"]:
                raw_rows.append((tid, x["vendor_name"] or "", x["fiscal_year"], float(x["net_amount"])))

    key_spend = collections.defaultdict(float)
    key_names = collections.defaultdict(collections.Counter)
    key_agencies = collections.defaultdict(set)
    for tid, name, year, amount in raw_rows:
        if is_person(name):
            continue
        k = norm(name)
        key_spend[k] += amount
        key_names[k][name] += abs(amount)
        key_agencies[k].add(tid)

    def classify(k):
        if k in vendor_map:
            return vendor_map[k][0], vendor_map[k][1], "map"
        display = key_names[k].most_common(1)[0][0].strip()
        for cat, rx, vendor in rules:
            if rx.search(k):
                return vendor or display, cat, "rule"
        return display, "unclassified", "none"

    def in_worklist(k):  # payees big enough to be reviewed one by one in config/vendor_map.csv
        return len(key_agencies[k]) >= 2 or abs(key_spend[k]) >= 10000

    # Payees whose names are withheld: mapped to "individuals", or small unclaimed payees shaped like a person's name
    person_keys = {k for k in key_spend
                   if classify(k)[1] == "individuals"
                   or (not in_worklist(k) and classify(k)[2] == "none"
                       and all(looks_like_person(n) for n in key_names[k]))}

    vendors, vendor_index, vendor_cat_spend = [], {}, collections.defaultdict(collections.Counter)
    key_vendor = {}
    for k in sorted(key_spend, key=lambda k: -abs(key_spend[k])):
        if k in person_keys:
            continue
        name, cat, method = classify(k)
        vid = slug(name) or "unnamed"
        if vid not in vendor_index:
            vendor_index[vid] = len(vendors)
            vendors.append({"id": vid, "name": name, "category": cat, "method": method, "aliases": []})
        v = vendors[vendor_index[vid]]
        vendor_cat_spend[vid][cat] += abs(key_spend[k])
        key_vendor[k] = vendor_index[vid]
    # A vendor reached through several names takes the category of the name with the most spend
    for v in vendors:
        v["category"] = vendor_cat_spend[v["id"]].most_common(1)[0][0]
        v["neris"] = any(rx.search(norm(v["name"])) for _, rx in neris) or None
    individuals_idx = len(vendors)
    vendors.append({"id": "individuals", "name": "Individuals (names withheld)", "category": "individuals",
                    "method": "rule", "aliases": [], "neris": None})

    aliases, alias_index = [], {}
    rows = collections.defaultdict(float)
    for tid, name, year, amount in raw_rows:
        if is_person(name) or norm(name) in person_keys:
            rows[(tid, individuals_idx, year, -1)] += amount
            continue
        vi = key_vendor[norm(name)]
        if name not in alias_index:
            alias_index[name] = len(aliases)
            aliases.append(name)
            vendors[vi]["aliases"].append(alias_index[name])
        rows[(tid, vi, year, alias_index[name])] += amount
    rows = [[t, v, y, round(a, 2), al] for (t, v, y, al), a in sorted(rows.items()) if round(a, 2) != 0]

    # FEMA firefighter grants matched to agencies through config/grant_recipients.csv
    recipient_map = {r["fema_recipient"]: int(r["tu_id"]) for r in read_csv("grant_recipients.csv")}
    grants = []
    for g in json.loads(read_gz(raw / "openfema" / "firefighter_grants_ut.json.gz")):
        tid = recipient_map.get(g["vendorName"])
        if tid in agency_ids:
            grants.append({"agency": tid, "recipient": g["vendorName"], "year": g["fiscalYear"],
                           "program": g["programName"], "amount": g["awardAmount"], "award": g["awardNumber"]})
    grants.sort(key=lambda g: (-g["year"], g["award"]))

    # Coverage numbers for the About section
    purchasing = {c["id"] for c in categories if c["purchasing"] == "yes"}
    vcat = [v["category"] for v in vendors]
    buy = sum(r[3] for r in rows if vcat[r[1]] in purchasing)
    classified = sum(r[3] for r in rows if vcat[r[1]] in purchasing and vcat[r[1]] != "unclassified")
    meta = {
        "built": datetime.date.today().isoformat(),
        "fetched": raw.name,
        "years": YEARS,
        "partial_years": PARTIAL_YEARS,
        "raw_path": f"raw/{raw.name}",
        "transparent_utah": TU_SITE,
        "counts": {"agencies": len(agencies), "vendors": len(vendors), "rows": len(rows), "grants": len(grants)},
        "purchasing_total": round(buy),
        "purchasing_classified_share": round(classified / buy, 4) if buy else None,
    }
    out = {"meta": meta, "categories": categories, "agencies": agencies, "vendors": vendors,
           "aliases": aliases, "rows": rows, "grants": grants}
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "data.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False))
    print(f"data/data.json: {len(agencies)} agencies, {len(vendors)} vendors, {len(rows)} rows, {len(grants)} grants;"
          f" purchasing ${buy:,.0f}, classified {meta['purchasing_classified_share']:.1%}")

    if worklist_path:
        names = {a["id"]: a["name"] for a in agencies}
        with open(worklist_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["name_key", "raw_names", "spend", "agencies", "agency_names", "current_category", "method"])
            for k in sorted(key_spend):
                if in_worklist(k):
                    _, cat, method = classify(k)
                    w.writerow([k, " | ".join(n for n, _ in key_names[k].most_common(4)), round(key_spend[k]),
                                len(key_agencies[k]), " | ".join(sorted(names[t] for t in key_agencies[k])[:4]),
                                cat, method])


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[args.index("--worklist") + 1] if "--worklist" in args else None)
