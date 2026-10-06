"""Build data/data.json from the newest raw/<date>/ folder and the config/*.csv files.

    python3 pipeline/build.py                      # write data/data.json
    python3 pipeline/build.py --worklist out.csv   # also list vendors that need a manual category

Rules for vendors, in order:
  1. config/vendor_map.csv     normalized name -> canonical vendor name and category
  2. config/vendor_rules.csv   regex -> known vendor (folds rare spellings into a mapped vendor)
  3. config/keyword_rules.csv  first regex that matches the normalized name sets the category
                               (and the vendor name, when the rule has one)
  4. otherwise                 "unclassified"
Payees that look like a person are grouped as "Individuals (names withheld)", and payee text matching
config/payee_name_redactions.csv is not shown.
"""
import collections
import csv
import datetime
import gzip
import html
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


def fix_mojibake(s):
    """Undo UTF-8 text that was decoded as Windows-1252, possibly more than once ("Â·" -> "·")."""
    for _ in range(4):
        if not re.search(r"[ÃÂâ]", s):
            break
        try:
            s = s.encode("cp1252").decode("utf-8")
        except UnicodeError:
            break
    return s


def clean_payee(raw):
    s = fix_mojibake(html.unescape(raw or ""))
    s = re.sub(r"(?<=[A-Za-z])[ÃÂâ][^\sA-Za-z]*(?=s\b)", "'", s)  # unrecoverable debris before a possessive s
    s = re.sub(r"[ÃÂ][^\sA-Za-z]*", " ", s)
    return " ".join(s.split())


def clean_label(raw):
    """Account names: drop the leading account number and any separator, repair encoding."""
    s = fix_mojibake(html.unescape(raw or ""))
    s = re.sub(r"^\s*\d[\d.]*\s*[^A-Za-z0-9(]*\s*", "", s)
    s = re.sub(r"\s*[ÃÂ][^\sA-Za-z]*\s*", " ", s)
    return " ".join(s.split()) or (raw or "").strip()


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


def staff_by_year(tu, tid):
    """People paid, wages and benefits per fiscal year from the compensation files.
    A person is one employee number with wages in a year's file; their title is the title on their largest
    wage line. Benefits are employer-paid only; reimbursements and employee-paid deductions are left out."""
    out = {}
    for year in YEARS:
        path = tu / "compensation" / str(tid) / f"{year}.json.gz"
        if not path.exists():
            continue
        pay = collections.defaultdict(float)
        top_line = {}
        wages = benefits = 0.0
        for r in json.loads(read_gz(path)):
            amount = r["net_amount"] or 0
            kind = " ".join(r.get(f) or "" for f in ("cat1", "cat2", "description")).lower()
            if "reimb" in kind:
                continue
            if re.search(r"wage|compensation|salar|paid leave|payroll", kind):
                wages += amount
                pay[r["employee"]] += amount
                if amount > top_line.get(r["employee"], (0, ""))[0]:
                    title = " ".join(fix_mojibake(r.get("title") or "").split())
                    title = re.sub(r"^(?=[A-Z0-9]*\d)[A-Z][A-Z0-9]{2,}\s+", "", title)  # payroll code prefix "CAPO89 Captain"
                    top_line[r["employee"]] = (amount, title or "No title")
            elif "benefit" in kind and "employee paid" not in kind:
                benefits += amount
            # reimbursements and employee-paid deductions are left out
        paid = [e for e, total in pay.items() if total > 0]
        if not paid:
            continue
        titles = collections.Counter(top_line[e][1] for e in paid if e in top_line)
        out[str(year)] = {"people": len(paid), "wages": round(wages), "benefits": round(benefits),
                          "titles": dict(titles.most_common())}
    return out


def latest_raw():
    dirs = sorted(p for p in (ROOT / "raw").iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))
    return dirs[-1]


def main(worklist_path=None):
    raw = latest_raw()
    tu = raw / "transparent_utah"
    categories = read_csv("categories.csv")
    cat_ids = {c["id"] for c in categories}
    rules = [(r["category"], re.compile(r["pattern"]), (r.get("vendor") or "").strip())
             for r in read_csv("vendor_rules.csv") + read_csv("keyword_rules.csv")]
    redactions = [re.compile(r["pattern"], re.I) for r in read_csv("payee_name_redactions.csv")]
    revenue_exclusions = [re.compile(r["pattern"], re.I) for r in read_csv("revenue_exclusions.csv")]
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
        revenue = collections.defaultdict(lambda: collections.defaultdict(float))
        path = tu / "revenue_categories" / f"{tid}.json.gz"
        for x in json.loads(read_gz(path)) if path.exists() else []:
            if x["fiscal_year"] in YEARS:
                revenue[str(x["fiscal_year"])][clean_label(x["agg1"])] += x["net_amount"] or 0
        revenue_excluded = sorted({c for cats in revenue.values() for c in cats
                                   if any(rx.search(c) for rx in revenue_exclusions)})
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
            "revenue": {y: {c: round(v) for c, v in sorted(cats.items()) if round(v)} for y, cats in sorted(revenue.items())},
            "revenue_total": {y: sum(round(v) for c, v in cats.items() if c not in revenue_excluded)
                              for y, cats in sorted(revenue.items())},
            "revenue_excluded": revenue_excluded,
            "staff": staff_by_year(tu, tid),
            "fy_start": {"01": "January", "07": "July"}.get((details.get("fiscal_year_begins") or "")[5:7]),
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
                raw_rows.append((tid, clean_payee(x["vendor_name"]), x["fiscal_year"], float(x["net_amount"])))

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
        if any(rx.search(display) for rx in redactions):
            display = re.sub(r"\S+@\S+", "", display).strip(" ()-,") or "Payee name withheld"
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
            shown = name
            if any(rx.search(name) for rx in redactions):
                shown = vendors[vi]["name"] + " (payee text withheld)"
            aliases.append(shown)
            vendors[vi]["aliases"].append(alias_index[name])
        rows[(tid, vi, year, alias_index[name])] += amount
    rows = [[t, v, y, round(a, 2), al] for (t, v, y, al), a in sorted(rows.items()) if round(a, 2) != 0]

    # Single payments: each agency's 100 largest payments per fiscal year. Kept when the payee maps to a
    # purchasing vendor and the payment is $1,000 or more. The lists include payments that were later voided
    # or duplicated, so per agency, vendor and year the kept payments (largest first) never add up to more
    # than the net amount paid.
    purchasing = {c["id"] for c in categories if c["purchasing"] == "yes"}
    net_paid = collections.defaultdict(float)
    for t, v, y, a, _ in rows:
        net_paid[(t, v, y)] += a
    payments, unmatched, over_net = [], 0, 0
    for tid in sorted(agency_ids):
        for year in YEARS:
            path = tu / "top_payments" / str(tid) / f"{year}.json.gz"
            room = {}
            for x in sorted(json.loads(read_gz(path)) if path.exists() else [], key=lambda x: x["ven_rank"]):
                name, amount = clean_payee(x["vendor_name"]), float(x["amount"] or 0)
                k = norm(name)
                if is_person(name) or k in person_keys:
                    continue
                if k not in key_vendor:
                    unmatched += 1
                    continue
                vi = key_vendor[k]
                if vendors[vi]["category"] not in purchasing or amount < 1000:
                    continue
                left = room.setdefault(vi, net_paid[(tid, vi, year)])
                if amount > left + 1:  # $1 tolerance for rounding
                    over_net += 1
                    continue
                room[vi] = left - amount
                payments.append([tid, year, x["ven_rank"], vi, round(amount, 2), alias_index.get(name, -1)])
    payments.sort(key=lambda p: (p[0], p[1], p[2]))

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
        "counts": {"agencies": len(agencies), "vendors": len(vendors), "rows": len(rows), "grants": len(grants),
                   "payments": len(payments)},
        "payments_rule": "Each agency's 100 largest payments per fiscal year, purchasing vendors, $1,000 or more,"
                         " capped so they never add up to more than the net amount paid to that vendor that year",
        "purchasing_total": round(buy),
        "purchasing_classified_share": round(classified / buy, 4) if buy else None,
    }
    out = {"meta": meta, "categories": categories, "agencies": agencies, "vendors": vendors,
           "aliases": aliases, "rows": rows, "payments": payments, "grants": grants}
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "data.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False))
    print(f"data/data.json: {len(agencies)} agencies, {len(vendors)} vendors, {len(rows)} rows, {len(grants)} grants,"
          f" {len(payments)} single payments ({unmatched} with an unmatched payee, {over_net} over the net paid);"
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
