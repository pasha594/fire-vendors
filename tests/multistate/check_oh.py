"""Recompute Ohio's normalized files from the raw files and check data/states/oh/ and config/states/oh/ match.

    python3 tests/multistate/check_oh.py

Independent of the adapters' code (it never imports pipeline/sources/oh_*.py): it reads the raw files with gzip,
csv and json, applies each source's published rule and compares
- oh_cincinnati: the raw CSV pages with the source's own server-side control totals per fiscal year and
  department; the linked fire department codes, fiscal year 2021 on;
- oh_checkbook_local: every linked participant's raw Tableau responses (underlying rows) with the summary totals
  the same dashboard gave for the same filters; fire districts' whole checkbooks, and for townships, cities and
  villages the lines whose fund or department is named for fire (not shared police, hydrant, insurance or
  fire-loss escrow names); calendar years 2021 on; one line per row Id,
  re-uploads (same transaction id, date, payee, fund, department, object and amount under a new row Id) once,
  months uploaded k times (every group of identical lines a multiple of k) once, a date's lines repeated in a
  later upload (TransactionId jump over 100,000) once, and months whose upload carries batch totals instead of
  line amounts left out;
- both sources: the owner's rule of 2026-10-07 as corrected the same day: lines equal in every raw column except
  the columns that only identify the row (Ohio Checkbook: row Id and TransactionId; Cincinnati: none, its
  trans_id, line and check numbers are content) are kept once, the lowest row Id; void-safe, n identical positive
  lines keep min(n, distinct reversals + 1), a reversal being a negative line of the same payee and account with
  the amount negated in the same or next fiscal year; identical voids (owner decision A of 2026-10-07): in a family
  with a payment (same payee and account, amount up to sign, negative lines linked to the payments of their fiscal
  year and the one before, transitively) identical negative copies go only with identical positive copies, and
  every family the fix touches has its raw net;
- lines and dollars per agency, source and fiscal year with data/states/oh/transactions.csv.gz;
- every published line, field by field, with its raw line (agency, fiscal year, date, payee, account, amount).
Also checks: the contract's column names and order; attribution (Cincinnati: every linked code is a fire
department and every fire-named department is linked or a known exclusion; checkbook: every linked participant
is a fire district or a township, city or village whose county equals the agency's county, no EMS-only
district, every participant line published is a fire line); agency ids, links and coverage tiers; duplicate
source_record_ids; sort order; payees published as the source has them except email or bank account text
(owner decision 2026-10-06); emails in any published text; sources.csv; added agencies (no registry department
of the same county under another name, unless reviewed; Forestry kept as "State fire agency");
vendor map (no unmerged config/states/oh/vendor_map_additions.csv; config/vendor_map.csv, then the vendor and
keyword rules as pipeline/build.py applies them, give a real category to >= 90% of purchasing dollars); raw files
(location, size, samples for every reachable source, no address columns in the state checkbook sample).
common is used only for norm() (the vendor map key), tests/multistate/vendor_coverage.py for the vendor map.
"""
import collections
import csv
import decimal
import gzip
import io
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "sources"))
import common  # noqa: E402
sys.path.insert(0, str(ROOT / "tests" / "multistate"))
import vendor_coverage  # noqa: E402

ST = "OH"
FIRST_FY = 2021
D = decimal.Decimal
CENTS = D("0.01")
WITHHELD = "Payee name withheld"

# docs/multistate/data-contract.md, written out here so a change in common.TABLES is caught
TX_COLUMNS = ["agency_id", "fiscal_year", "posting_date", "payee_name", "description", "account",
              "category_published", "amount", "source", "source_record_id"]
SOURCES_COLUMNS = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]
LINK_COLUMNS = ["agency_id", "source", "source_entity_id", "source_entity_name", "fy_start", "match_method", "note"]
AGENCY_COLUMNS = ["id", "name", "kind", "county", "city", "usfa_fdid", "dept_type", "organization_type", "stations",
                  "career", "volunteer", "paid_per_call", "website", "grants"]
VENDOR_MAP_COLUMNS = ["name_key", "vendor", "category", "confidence"]

# Cincinnati: department codes whose name says fire but which are not the fire department (insurance shared by
# police and fire)
NOT_FIRE_CODES = {"922"}
REACHABLE = ["oh_cincinnati", "oh_checkbook_state", "oh_aos", "oh_checkbook_local"]  # sources with a sample

# Ohio Checkbook local: what a fire line is, written independently of the adapter
FIRE_WORD = re.compile(r"\bfire(s|fighters?|fighting|men|men'?s)?\b", re.I)
NOT_FIRE_WORDS = re.compile(r"police|hydrant|fire ?loss|firework|insurance|escrow|damaged? structure|garnish|"
                            r"fire damage|repair ?(and|/|&) ?removal|clean ?up", re.I)
# fire-loss insurance escrow (proceeds paid back to owners of burned buildings): excludes the line whichever of
# fund or department carries the name
ESCROW_WORDS = re.compile(r"fire ?loss|escrow|damaged? structure|fire damage|repair ?(and|/|&) ?removal|clean ?up", re.I)
EMS_ONLY_DISTRICTS = {"Joint Emergency Medical Service"}
# added agencies whose place word also appears in a registry name of the same county, checked by hand
ADDED_REVIEWED = {"OH-S-brunswick-hills-township-fire-department":
                  "Brunswick Division of Fire (OH-52003) is the City of Brunswick's; Brunswick Hills Township runs its own"}
# participants in two counties, listed under another county than the registry's (checked by hand)
COUNTY_EXCEPTIONS = {("City of Vermilion", "OH-22017")}  # Vermilion: Erie and Lorain counties
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
BROKEN = set()  # (participant, month) left out as broken uploads, for the summary line
DOUBLED = set()  # (participant, month) uploaded more than once
RELOADED = set()  # (participant, date) uploaded again in a later upload
IDENTICAL = {}  # participant (or source) -> identical lines dropped (owner rule of 2026-10-07)
VOID_KEPT = collections.defaultdict(lambda: [0, D(0)])  # source -> identical copies kept by the void rule
VOID_FIX = collections.defaultdict(lambda: [0, 0, D(0)])  # source -> families, negative lines, dollars the fix keeps
KEEP = {}  # (source, raw identity) -> copies the rule keeps
# owner rule of 2026-10-07 (corrected): raw columns that only identify the row or the load. Ohio Checkbook: the row
# Id and the TransactionId (numbered by the checkbook in upload order); Cincinnati's raw file has none (trans_id,
# trans_line_no and check_no are the financial system's document, line and check or EFT numbers: content)
LOCAL_ROW_IDS = {"Id", "TransactionId"}
CINCINNATI_ROW_IDS = set()


def copies_kept(lines, amount, year, reversal_of, order, src):
    """Owner rule of 2026-10-07 (corrected), written independently of the adapters. lines: raw lines that are
    identical to each other (every raw column but the row ids equal), grouped as {identity: [lines]}. Every
    identity is kept once; a positive identity with copies keeps min(copies, reversals + 1), reversals being the
    distinct negative identities with the same reversal fields, the amount negated, dated in the positive line's
    fiscal year or the next. Identical voids (owner decision A of 2026-10-07): identities with the same reversal
    fields and the amount up to sign are linked when one is negative and the other positive, the negative one dated
    in the positive one's fiscal year or the next; a family is a set of identities linked directly or through
    others. In a family with a positive line, the negative identities (in the order order(identity, lines) gives)
    give up their extra copies only while the family's positive identities have dropped copies left to pair with;
    a family of negative lines only keeps each identity once. Asserts that every family the fix changes nets as its raw lines
    and that no family with a payment nets more than its raw lines."""
    negative = collections.defaultdict(list)
    for ident, g in lines.items():
        if amount(g[0]) < 0:
            negative[reversal_of(g[0])].append((ident, amount(g[0]), year(g[0])))
    keep = {}
    for ident, g in lines.items():
        a, y = amount(g[0]), year(g[0])
        if a <= 0 or len(g) == 1:
            keep[ident] = 1
            continue
        reversals = {i for i, na, ny in negative[reversal_of(g[0])] if na == -a and ny in (y, y + 1)}
        keep[ident] = min(len(g), len(reversals) + 1)
    # families: identities with the same reversal fields and amount up to sign, a negative identity linked to every
    # positive one of its fiscal year or the year before; families are the connected sets (merged label by label)
    by_sign_free = collections.defaultdict(list)
    for ident, g in lines.items():
        if amount(g[0]):
            by_sign_free[(reversal_of(g[0]), abs(amount(g[0])))].append(ident)
    for idents in by_sign_free.values():
        label = {i: n for n, i in enumerate(idents)}
        neg = [i for i in idents if amount(lines[i][0]) < 0]
        pos = [i for i in idents if amount(lines[i][0]) > 0]
        for n_i in neg:
            for p_i in pos:
                if year(lines[n_i][0]) - year(lines[p_i][0]) in (0, 1) and label[n_i] != label[p_i]:
                    old, new = label[p_i], label[n_i]
                    for i in idents:
                        if label[i] == old:
                            label[i] = new
        family = collections.defaultdict(list)
        for i in idents:
            family[label[i]].append(i)
        for members in family.values():
            if all(amount(lines[i][0]) < 0 for i in members):
                continue
            paired = sum(len(lines[i]) - keep[i] for i in members if amount(lines[i][0]) > 0)
            changed = False
            for i in sorted((i for i in members if amount(lines[i][0]) < 0), key=lambda i: order(i, lines[i])):
                goes = max(0, min(len(lines[i]) - 1, paired))
                paired -= goes
                if len(lines[i]) - goes != keep[i]:
                    VOID_FIX[src][1] += len(lines[i]) - goes - keep[i]
                    VOID_FIX[src][2] += (len(lines[i]) - goes - keep[i]) * amount(lines[i][0])
                    keep[i], changed = len(lines[i]) - goes, True
            raw_net = sum(len(lines[i]) * amount(lines[i][0]) for i in members)
            kept_net = sum(keep[i] * amount(lines[i][0]) for i in members)
            assert kept_net <= raw_net, f"{src}: family {reversal_of(lines[members[0]][0])} nets more than raw"
            if changed:
                VOID_FIX[src][0] += 1
                assert kept_net == raw_net, f"{src}: family touched by the void fix has net {kept_net}, raw {raw_net}"
    return keep


POLICE_TOWNSHIPS = {}  # township with a program220 file -> years with police-named lines (2021 on)


def rows_of(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def header_of(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


def config_rows(name, state=True):
    path = (ROOT / "config" / "states" / "oh" / name) if state else (ROOT / "config" / name)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def raw_folder(source):
    dirs = sorted(p for p in (ROOT / "raw").iterdir() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
                  and (p / "oh" / source).is_dir())
    assert dirs, f"no raw folder for {source}"
    return dirs[-1] / "oh" / source


def redacted(name):
    """What the published payee must be: as the source has it (spaces collapsed), or the withheld marker when
    the text matches config/payee_name_redactions.csv (email, bank account text)."""
    name = " ".join((name or "").split())
    if any(re.search(r["pattern"], name, re.I) for r in config_rows("payee_name_redactions.csv", state=False)):
        return WITHHELD
    return name


def expected_cincinnati():
    """(agency_id, fiscal_year) -> [lines, dollars] straight from the raw pages; the raw lines by record id."""
    src = "oh_cincinnati"
    d = raw_folder(src)
    link_rows = [r for r in config_rows("agency_sources.csv") if r["source"] == src]
    links = {r["source_entity_id"]: r["agency_id"] for r in link_rows}
    assert links, "no oh_cincinnati links"

    # attribution: every linked code is a fire department code, named as the source names it
    departments = json.loads(gzip.decompress((d / "departments.json.gz").read_bytes()))
    names = collections.defaultdict(set)
    for r in departments:
        names[r["dept_code"]].add(r["dept_desc"])
    for r in link_rows:
        assert r["source_entity_name"] in names.get(r["source_entity_id"], set()), f"link not in source: {r}"
        name = r["source_entity_name"]
        assert re.search(r"\bfire\b", name, re.I) and not re.search(
            r"police|insurance|\bins\b|pension|communications", name, re.I), f"linked entity is not a fire dept: {r}"
        assert r["match_method"] == "department code" and r["fy_start"] == "07", f"oh_cincinnati link: {r}"
    for code, ns in names.items():
        if any(re.search(r"\bfire\b", n, re.I) for n in ns):
            assert code in links or code in NOT_FIRE_CODES, f"fire-named department {code} {ns} neither linked " \
                                                            "nor a known exclusion"

    raw = []
    for p in sorted(d.glob("payments_*.csv.gz")):
        raw += rows_of(p)
    # the raw pages equal the source's own server-side totals per fiscal year and department
    control = json.loads(gzip.decompress((d / "control_totals.json.gz").read_bytes()))
    by = collections.defaultdict(lambda: [0, D(0)])
    for r in raw:
        by[(r["fiscal_year"], r["dept_code"])][0] += 1
        by[(r["fiscal_year"], r["dept_code"])][1] += D(r["amount"])
    assert {(c["fiscal_year"], c["dept_code"]): (int(c["n"]), D(c["amount"]).quantize(CENTS)) for c in control} \
        == {k: (n, a.quantize(CENTS)) for k, (n, a) in by.items()}, "raw pages differ from control_totals.json"
    out, lines, candidates = collections.defaultdict(lambda: [0, D(0)]), {}, collections.defaultdict(list)
    for r in raw:
        if int(r["fiscal_year"]) < FIRST_FY or r["dept_code"] not in links:
            continue
        candidates[tuple((k, v) for k, v in r.items() if k not in CINCINNATI_ROW_IDS)].append(r)
    # owner rule of 2026-10-07 (corrected): lines equal in every raw column are identical and kept once; positive
    # copies of a line that was reversed (credit of the same department, fund, account category and vendor) keep
    # one more than its reversals; identical credits of a family with a payment go only with its identical payments
    keep = copies_kept(candidates, lambda r: D(r["amount"]), lambda r: int(r["fiscal_year"]),
                       lambda r: (r["dept_code"], r["dept_desc"], r["fund_code"], r["fund_desc"], r["exp_acct_cat"],
                                  r["exp_acct_cat_desc"], r["vendor_name"]),
                       lambda ident, g: tuple(v for _, v in ident), src)
    IDENTICAL["oh_cincinnati"] = sum(len(g) - keep[i] for i, g in candidates.items())
    VOID_KEPT[src][0] += 0  # reported even when nothing is kept
    VOID_FIX[src][0] += 0
    for ident, g in candidates.items():
        KEEP[(src, ident)] = keep[ident]
        if keep[ident] > 1 and D(g[0]["amount"]) > 0:  # positive copies (negative ones: VOID_FIX)
            VOID_KEPT[src][0] += keep[ident] - 1
            VOID_KEPT[src][1] += (keep[ident] - 1) * D(g[0]["amount"])
        rid = f"{g[0]['trans_id']}-{g[0]['trans_line_no']}"
        assert rid not in lines, f"raw record id {rid} is not unique"
        for copy in range(1, keep[ident] + 1):
            r = dict(g[0])
            k = (links[r["dept_code"]], r["fiscal_year"])
            out[k][0] += 1
            out[k][1] += D(r["amount"])
            r["_want"] = {"agency_id": links[r["dept_code"]], "fiscal_year": r["fiscal_year"],
                          "posting_date": r["record_date"][:10], "description": "",
                          "account": f"{r['dept_desc']} / {r['fund_code']} {r['fund_desc']} / "
                                     f"{r['exp_acct_cat']} {r['exp_acct_cat_desc']}",
                          "category_published": r["exp_acct_cat_desc"], "payee_name": redacted(r["vendor_name"]),
                          "amount": str(D(r["amount"]).quantize(CENTS))}
            r["_ident"] = ident
            lines[rid if copy == 1 else f"{rid}#{copy}"] = r
    return out, lines


def tableau_table(body):
    """Rows of a Tableau underlying or summary data response, keyed by the data source's own column names (the
    caption for calculated columns)."""
    ret = json.loads(body)["vqlCmdResponse"]["cmdResultList"][0]["commandReturn"]
    if not ret:
        return []
    dt = ret["dataTablePresModel"]
    t = json.loads(dt["showDataTable"])["table"]
    caps = {c["uniqueName"]: c["fieldCaption"] for c in dt.get("showDataTableColumnPresModels", [])}
    cols = []
    for c in t["schema"]:
        base = c.split("].[")[-1].rstrip("]")
        cols.append(caps.get(c, base) if base.startswith(("Calculation_", "yr:", "sum:", "none:")) else base)
    return [dict(zip(cols, x)) for x in t["tuples"]]


def fire_line(kind, r, by_department=True):
    if kind == "special_districts":
        return True
    if any(ESCROW_WORDS.search(r[f]) for f in ("FundDescription", "DeptDescription")):
        return False
    # townships (owner decision 2026-10-07, Ohio Public Safety): never a police-named line; program 220 counts
    if kind == "townships" and any(re.search(r"police", r[f], re.I) for f in ("FundDescription", "DeptDescription")):
        return False
    if kind == "townships" and r["DeptCode"] == "220":
        return True
    fields = ("FundDescription", "DeptDescription") if by_department else ("FundDescription",)
    return any(FIRE_WORD.search(r[f]) and not NOT_FIRE_WORDS.search(r[f]) for f in fields)


def expected_checkbook_local(agency_county):
    """(agency_id, fiscal_year) -> [lines, dollars] from the raw Tableau responses; the raw lines by record id."""
    src = "oh_checkbook_local"
    d = raw_folder(src)
    links = [r for r in config_rows("agency_sources.csv") if r["source"] == src]
    assert links, "no oh_checkbook_local links"
    people = {}
    for kind in ("special_districts", "townships", "cities_villages"):
        for p in json.loads(json.loads(gzip.decompress((d / f"participants_{kind}.json.gz").read_bytes()))["d"]):
            people[str(p["Id"])] = (kind, p)
    out, lines = collections.defaultdict(lambda: [0, D(0)]), {}
    assert len({r["source_entity_id"] for r in links}) == len(links), "a participant linked twice"
    for link in links:
        eid = link["source_entity_id"]
        kind, p = people[eid]
        # attribution: the participant is named as linked, sits in the agency's county, is a fire district or a
        # township, city or village (whose fire lines only are taken), and is not an EMS-only district
        assert p["Name"] == link["source_entity_name"], f"link name differs from the participant list: {link}"
        assert p["County"] == agency_county[link["agency_id"]] or (p["Name"], link["agency_id"]) in COUNTY_EXCEPTIONS, \
            f"county differs: {link} vs {p['County']}"
        assert link["fy_start"] == "01", f"Ohio locals use the calendar year: {link}"
        assert p["Name"] not in EMS_ONLY_DISTRICTS, f"EMS-only district linked: {link}"
        if kind == "special_districts":
            assert re.search(r"\bfire\b", p["Name"], re.I), f"special district that is not a fire district: {link}"
        doc = json.loads(gzip.decompress((d / f"entity_{eid}.json.gz").read_bytes()))
        assert doc["entity"]["name"] == p["Name"] and doc["entity"]["kind"] == kind, f"entity file {eid}"
        requests = list(doc["requests"])
        # townships: program 220 lines of the funds not named for fire, and police-named funds and departments
        # (fetch220); every township whose program 220 values include one not named for fire has that file
        p220 = [x for x in doc["entity"]["departments"] if x.rsplit(" - ", 1)[-1] == "220" and not FIRE_WORD.search(x)]
        police_years = set()
        extra = d / f"program220_{eid}.json.gz"
        if kind == "townships" and p220:
            assert extra.exists(), f"{eid} {p['Name']}: program 220 values {p220} but no program220 file"
        if extra.exists():
            doc220 = json.loads(gzip.decompress(extra.read_bytes()))
            e220 = doc220["entity"]
            assert e220["name"] == p["Name"] and kind == "townships", f"{extra.name}: not this township"
            years220 = [y for y in e220["years"] if y.isdigit() and int(y) >= FIRST_FY]
            others = [f for f in e220["funds"] if not FIRE_WORD.search(f)]
            p220_now = [x for x in e220["departments"] if x.rsplit(" - ", 1)[-1] == "220" and not FIRE_WORD.search(x)]
            row_filters = [q["filters"] for q in doc220["requests"] if q["kind"] != "police"]
            if years220 and others:
                assert {"Fund": others, "Department": p220_now, "Year Of Transaction Date": years220} in row_filters, \
                    f"{extra.name}: the program 220 slice is not every non-fire fund and program 220 value"
            want_police = [(c, [x for x in e220[k] if re.search(r"police", x, re.I)])
                           for c, k in (("Fund", "funds"), ("Department", "departments"))]
            got_police = [q["filters"] for q in doc220["requests"] if q["kind"] == "police"]
            assert got_police == [{c: v, "Year Of Transaction Date": years220} for c, v in want_police
                                  if v and years220], f"{extra.name}: police-named funds or departments not all checked"
            for q in doc220["requests"]:
                if q["kind"] == "police":
                    police_years |= {s["YEAR(Transaction Date)"] for s in tableau_table(q["body"])
                                     if s["SUM(Amount)"] != "null" and int(s["YEAR(Transaction Date)"]) >= FIRST_FY}
            requests += [q for q in doc220["requests"] if q["kind"] != "police"]
            # the link's note says program 220 counts and, when the township runs police, that its mixed Public
            # Safety lines are left out
            assert "program 220" in link["note"], f"{p['Name']}: link note does not mention program 220"
            assert ("mixed Public Safety lines" in link["note"]) == bool(police_years), \
                f"{p['Name']}: police years {sorted(police_years)}, note {link['note']!r}"
            POLICE_TOWNSHIPS[p["Name"]] = sorted(police_years)
        by_id, sums = {}, []
        for req in requests:
            rows = tableau_table(req["body"])
            if req["kind"] == "summary":
                sums.append((req["filters"], rows))
                continue
            for r in rows:
                assert r["MuniName"] == p["Name"], f"{eid}: a row of {r['MuniName']}"
                for k, v in req["filters"].items():
                    assert r[k] in v, f"{eid}: row outside its request's filter {k}: {r[k]!r}"
                assert by_id.setdefault(r["Id"], r) == r, f"{eid}: row Id {r['Id']} differs between requests"
        # the rows of each slice equal the dashboard's own summary totals for the same filters, per year
        assert sums, f"{eid}: no summary totals"
        for filters, summary in sums:
            want, got = collections.defaultdict(D), collections.defaultdict(D)
            for s in summary:
                if s["SUM(Amount)"] != "null":  # fund and year pairs without rows
                    want[s["YEAR(Transaction Date)"]] += D(s["SUM(Amount)"])
            for r in by_id.values():
                if all(r[k] in v for k, v in filters.items()):
                    got[r["TransDate"][:4]] += D(r["Amt"]).quantize(CENTS)
            assert all(abs(want[y] - got[y]) <= CENTS for y in set(want) | set(got)), \
                f"{eid}: rows differ from the summary totals for {filters}"
        # a fire department that also books police fund lines is a shared code: then only fire funds count
        by_department = not any(FIRE_WORD.search(r["DeptDescription"]) and re.search(r"police", r["FundDescription"], re.I)
                                and not FIRE_WORD.search(r["FundDescription"]) for r in by_id.values())
        seen, kept = set(), []
        for rid in sorted(by_id, key=int):
            r = by_id[rid]
            if int(r["TransDate"][:4]) < FIRST_FY or not fire_line(kind, r, by_department):
                continue
            key = (r["TransactionId"], r["TransDate"], r["Payee"], r["FundCode"], r["DeptCode"], r["ObjCode"], r["Amt"])
            if key in seen:
                continue
            seen.add(key)
            kept.append(r)
        # months uploaded k times (10+ lines, every group of identical date, payee, fund, department, object and
        # amount has a size divisible by k >= 2): keep size/k lines of each group, lowest row Ids first
        same = collections.defaultdict(list)
        for r in kept:
            same[(r["TransDate"][:10], r["Payee"], r["FundCode"], r["DeptCode"], r["ObjCode"], r["Amt"])].append(r)
        month_sizes = collections.defaultdict(list)
        for key, g in same.items():
            month_sizes[key[0][:7]].append(len(g))
        times = {m: math.gcd(*sz) for m, sz in month_sizes.items() if sum(sz) >= 10 and math.gcd(*sz) >= 2}
        DOUBLED.update((p["Name"], m) for m in times)
        extra = set()
        for key, g in same.items():
            if key[0][:7] in times:
                extra |= {r["Id"] for r in sorted(g, key=lambda r: int(r["Id"]))[len(g) // times[key[0][:7]]:]}
        kept = [r for r in kept if r["Id"] not in extra]
        # reloads: uploads are runs of TransactionIds without a jump over 100,000; in a later upload, a date's
        # lines (3 or more, none negative) that all repeat lines of that date from earlier uploads are dropped
        order = sorted(kept, key=lambda r: (int(r["TransactionId"]), int(r["Id"])))
        upload_of, n_up = {}, 0
        for i, r in enumerate(order):
            if i and int(r["TransactionId"]) - int(order[i - 1]["TransactionId"]) > 100000:
                n_up += 1
            upload_of[r["Id"]] = n_up
        by_upload = collections.defaultdict(lambda: collections.defaultdict(list))
        for r in kept:
            by_upload[upload_of[r["Id"]]][r["TransDate"][:10]].append(r)
        earlier, reloaded = collections.Counter(), set()
        for u in range(n_up + 1):
            this = collections.Counter()
            for day, ls in sorted(by_upload[u].items()):
                c = collections.Counter((day, r["Payee"], r["FundCode"], r["DeptCode"], r["ObjCode"], r["Amt"])
                                        for r in ls)
                if len(ls) >= 3 and min(D(r["Amt"]) for r in ls) >= 0 and all(earlier[k] >= v for k, v in c.items()):
                    reloaded |= {r["Id"] for r in ls}
                    RELOADED.add((p["Name"], day))
                else:
                    this.update(c)
            earlier.update(this)
        kept = [r for r in kept if r["Id"] not in reloaded]
        # broken uploads: a month in which more than half the lines share date and amount with 2+ other lines
        # paid to 2+ different payees for 2+ different objects carries batch totals, not line amounts; the whole
        # month is left out (equal amounts to several people for one object, e.g. stipends, are real lines)
        groups = collections.defaultdict(list)
        for r in kept:
            groups[(r["TransDate"][:10], r["Amt"])].append((r["Payee"], r["ObjCode"]))
        month_n, month_rep = collections.Counter(), collections.Counter()
        for r in kept:
            g = groups[(r["TransDate"][:10], r["Amt"])]
            month_n[r["TransDate"][:7]] += 1
            month_rep[r["TransDate"][:7]] += (len(g) >= 3 and len({x for x, _ in g}) >= 2
                                              and len({o for _, o in g}) >= 2)
        broken = {m for m, n in month_n.items() if 2 * month_rep[m] > n}
        BROKEN.update((p["Name"], m) for m in broken)
        # a linked participant's fire lines are a department's spending, not a stray grant or capital line:
        # at least 25 lines a year in the years it has any
        years = {r["TransDate"][:4] for r in kept}
        assert kept and len(kept) >= 25 * len(years), \
            f"{eid} {p['Name']}: only {len(kept)} fire lines in {len(years)} years"
        # ... and not only its fire pension fund (contributions to the pension system, no purchasing)
        pension = [r for r in kept if re.search(r"pension|disab", r["FundDescription"], re.I)
                   and not (by_department and FIRE_WORD.search(r["DeptDescription"]))]
        assert len(pension) < 0.9 * len(kept), f"{eid} {p['Name']}: fire lines are a pension fund only"
        # owner rule of 2026-10-07 (corrected): lines equal in every raw column but the row Id and TransactionId
        # (payment Type, date, payee, fund, department, object, amount and the dashboard's labels) are identical and
        # kept once, the lowest row Id; positive copies of a line that was reversed (a negative line of the same
        # payee, fund, department and object) keep one more than its distinct reversals, the lowest row Ids;
        # identical voids of a family with a payment go only with its identical payments (decision A, 2026-10-07),
        # the family's negative identities by lowest row Id, each keeping its lowest row Ids
        groups = collections.defaultdict(list)
        for r in sorted((r for r in kept if r["TransDate"][:7] not in broken), key=lambda r: int(r["Id"])):
            groups[tuple((k, v) for k, v in r.items() if k not in LOCAL_ROW_IDS)].append(r)
        keep = copies_kept(groups, lambda r: D(r["Amt"]).quantize(CENTS), lambda r: int(r["TransDate"][:4]),
                           lambda r: tuple(r[c] for c in ("MuniName", "Payee", "FundCode", "FundDescription", "DeptCode",
                                                          "DeptDescription", "ObjCode", "ObjDescription")),
                           lambda ident, g: min(int(r["Id"]) for r in g), src)
        IDENTICAL[p["Name"]] = sum(len(g) - keep[i] for i, g in groups.items())
        first = []
        for ident, g in groups.items():
            KEEP[(src, ident)] = keep[ident]
            if keep[ident] > 1 and D(g[0]["Amt"]) > 0:  # positive copies (negative ones: VOID_FIX)
                VOID_KEPT[src][0] += keep[ident] - 1
                VOID_KEPT[src][1] += (keep[ident] - 1) * D(g[0]["Amt"]).quantize(CENTS)
            first += [dict(r, _ident=ident) for r in g[:keep[ident]]]
        for r in first:
            fy = r["TransDate"][:4]
            amount = D(r["Amt"]).quantize(CENTS)
            k = (link["agency_id"], fy)
            out[k][0] += 1
            out[k][1] += amount
            r = dict(r)
            r["_want"] = {"agency_id": link["agency_id"], "fiscal_year": fy, "posting_date": r["TransDate"][:10],
                          "description": "", "amount": str(amount),
                          "payee_name": redacted("" if r["Payee"] == "%null%" else r["Payee"]),
                          "account": " / ".join(x for x in (
                              " - ".join(v for v in (r[d], r[c]) if v not in ("", "%null%"))
                              for d, c in (("FundDescription", "FundCode"), ("DeptDescription", "DeptCode"),
                                           ("ObjDescription", "ObjCode"))) if x),
                          "category_published": "" if r["ObjDescription"] == "%null%" else r["ObjDescription"]}
            lines[f"{eid}-{r['Id']}"] = r
    return out, lines


def main():
    tx_path = ROOT / "data" / "states" / "oh" / "transactions.csv.gz"
    assert header_of(tx_path) == TX_COLUMNS, "transactions.csv.gz header differs from the data contract"
    tx = rows_of(tx_path)
    assert header_of(ROOT / "config" / "states" / "oh" / "sources.csv") == SOURCES_COLUMNS, "sources.csv header"
    assert header_of(ROOT / "config" / "states" / "oh" / "agency_sources.csv") == LINK_COLUMNS, "agency_sources header"
    if (ROOT / "config" / "states" / "oh" / "agencies_added.csv").exists():
        assert header_of(ROOT / "config" / "states" / "oh" / "agencies_added.csv") == AGENCY_COLUMNS, \
            "agencies_added.csv header"
    agencies = json.loads((ROOT / "data" / "states" / "oh" / "agencies.json").read_text())
    ids = {a["id"] for a in agencies["agencies"]}
    county = {a["id"]: a["county"] for a in config_rows("agencies.csv") + config_rows("agencies_added.csv")}
    sources = {r["source"]: r for r in config_rows("sources.csv")}
    assert agencies["sources"] == config_rows("sources.csv"), "agencies.json sources differ from sources.csv"
    assert all(s["tier"] in ("1", "2") for s in sources.values() if s["source"] in {r["source"] for r in tx}), \
        "transactions rows from a source that is not tier 1 or 2"

    # 1. totals per agency, source and fiscal year, recomputed from raw
    got = collections.defaultdict(lambda: [0, D(0)])
    for r in tx:
        got[(r["agency_id"], r["source"], r["fiscal_year"])][0] += 1
        got[(r["agency_id"], r["source"], r["fiscal_year"])][1] += D(r["amount"])
        assert re.fullmatch(r"-?\d+\.\d\d", r["amount"]), f"amount format: {r}"
        assert int(r["fiscal_year"]) >= FIRST_FY, f"fiscal year before {FIRST_FY}: {r}"
        assert not r["posting_date"] or re.fullmatch(r"\d{4}-\d\d-\d\d", r["posting_date"]), f"date: {r}"
    expect, raw_lines = {}, {}
    for src, fn in (("oh_cincinnati", expected_cincinnati), ("oh_checkbook_local", expected_checkbook_local)):
        totals, lines = fn(county) if src == "oh_checkbook_local" else fn()
        expect.update({(a, src, fy): v for (a, fy), v in totals.items()})
        raw_lines.update({(src, rid): r for rid, r in lines.items()})
    assert set(got) == set(expect), f"agency/source/year keys differ: {sorted(set(got) ^ set(expect))[:5]}"
    for k in sorted(expect):
        assert got[k][0] == expect[k][0] and got[k][1] == expect[k][1], f"{k}: got {got[k]}, raw {expect[k]}"
    assert {s for _, s, _ in got} <= set(sources), "a source with rows is missing from sources.csv"

    # 2. every published line equals its raw line, field by field (payees as published, owner decision 2026-10-06)
    for r in tx:
        raw = raw_lines[(r["source"], r["source_record_id"])]
        diff = {k: (r[k], v) for k, v in raw["_want"].items() if r[k] != v}
        assert not diff, f"{r['source']} {r['source_record_id']} differs from raw: {diff}"

    # 3. agency ids, links and coverage
    assert {a for a, _, _ in got} <= ids, "transactions for agencies not in agencies.json"
    links = config_rows("agency_sources.csv")
    assert all(r["agency_id"] in ids and re.fullmatch(r"0[1-9]|1[0-2]", r["fy_start"]) for r in links), "agency_sources"
    linked = {(r["agency_id"], r["source"]) for r in links}
    assert {(a, s) for a, s, _ in got} <= linked, "rows for an agency and source without an agency_sources.csv link"
    added = config_rows("agencies_added.csv")
    assert all(r["id"].startswith("OH-S-") for r in added), "agencies_added ids must be OH-S-<slug>"
    assert not {r["id"] for r in added} & {r["id"] for r in config_rows("agencies.csv")}, "added id in registry"
    # an added agency must not be a registry department under another name: no registry row of the same county
    # shares its place word (the first word that is not generic), unless reviewed by hand (ADDED_REVIEWED)
    generic = {"city", "village", "township", "twp", "of", "the", "fire", "department", "volunteer", "community",
               "ohio", "department", "division", "north", "south", "east", "west", "new", "mount", "joint"}
    for r in added:
        words = [w for w in re.findall(r"[a-z]+", r["name"].lower()) if w not in generic]
        if not words or r["kind"] == "State fire agency":
            continue
        clash = [g["name"] for g in config_rows("agencies.csv") if g["county"] == r["county"]
                 and words[0] in re.findall(r"[a-z]+", g["name"].lower())]
        assert not clash or r["id"] in ADDED_REVIEWED, f"added agency {r['id']} may be registry {clash}"
    assert all(r["kind"] == "State fire agency" for r in added if "forestry" in r["name"].lower()), \
        "state fire agencies are kept with kind 'State fire agency' (owner decision 4)"
    with_rows = {a for a, _, _ in got}
    sources_of = collections.defaultdict(set)
    for a, s, _ in got:
        sources_of[a].add(s)
    fy_of = collections.defaultdict(set)
    for r in links:
        fy_of[r["agency_id"]].add(r["fy_start"])
    tiers = {}
    for a in agencies["agencies"]:
        tiers[a["id"]] = a["coverage"]
        if a["id"] in with_rows:
            assert a["coverage"] == 1, f"{a['id']} has payee rows but coverage {a['coverage']}"
            assert sources_of[a["id"]] <= set(a["sources"]), f"{a['id']}: sources {a['sources']}"
            fys = sorted(fy_of[a["id"]])
            assert a["fy_start"] == (fys[0] if len(fys) == 1 else fys), f"{a['id']}: fy_start {a['fy_start']}"
        else:
            assert a["coverage"] == 4, f"{a['id']} has no vendor data (no line items or totals) but coverage " \
                                       f"{a['coverage']}"
    assert agencies["coverage_counts"] == {str(t): sum(v == t for v in tiers.values()) for t in (1, 2, 3, 4)}, \
        "coverage_counts"
    for table in ("line_items.csv.gz", "totals.csv"):
        assert not (ROOT / "data" / "states" / "oh" / table).exists(), f"unexpected {table}: no Ohio tier 2 or 3 source"

    # 4. no duplicate source_record_id per source; file sorted as the contract says
    ids_by_source = collections.Counter((r["source"], r["source_record_id"]) for r in tx)
    dupes = [k for k, n in ids_by_source.items() if n > 1]
    assert not dupes, f"duplicate source_record_id: {dupes[:5]}"
    keys = [tuple(r[c] for c in TX_COLUMNS) for r in tx]
    assert keys == sorted(keys), "transactions.csv.gz is not sorted"
    # owner rule of 2026-10-07 (corrected; no exception in Ohio): published lines identical in every raw column but
    # the row ids appear once, or as often as the void rule keeps them
    same = collections.Counter((r["source"], raw_lines[(r["source"], r["source_record_id"])]["_ident"]) for r in tx)
    over = [k for k, n in same.items() if n != KEEP[k]]
    assert not over, f"identical lines published more often than the rule keeps: {over[:2]}"

    # 5. no email address in any published text (payee text with one is withheld)
    for r in tx:
        assert not any(EMAIL.search(r[c]) for c in ("payee_name", "description", "account")), f"email: {r}"

    # 6. vendor map: payees classified the way pipeline/build.py classifies them (config/vendor_map.csv, then the
    #    vendor and keyword rules); the state's proposals are folded into config/vendor_map.csv by
    #    pipeline/sources/merge_vendor_maps.py, so no proposals file is left behind; >= 90% of purchasing dollars
    #    (payees with net spend above zero, purchasing category or unmapped) mapped to a real category
    assert not (ROOT / "config" / "states" / "oh" / "vendor_map_additions.csv").exists(), \
        "config/states/oh/vendor_map_additions.csv: fold it into config/vendor_map.csv (merge_vendor_maps.py)"
    assert header_of(ROOT / "config" / "vendor_map.csv") == VENDOR_MAP_COLUMNS, "config/vendor_map.csv header"
    payee_spend = collections.defaultdict(D)
    for r in tx:
        payee_spend[common.norm(r["payee_name"])] += D(r["amount"])
    cov = vendor_coverage.Classifier().coverage(payee_spend)
    share = cov["share_real"]
    assert share >= D("0.9"), f"vendor map gives a real category to {share:.1%} of purchasing dollars"

    # 7. raw files: only gzipped files under raw/<date>/oh/<source>/, each under 50 MB, Ohio under 150 MB; a
    #    sample of at most 100 rows for every reachable source; no address columns in the state checkbook sample
    total = 0
    for p in (ROOT / "raw").glob("*/oh/**/*"):
        if p.is_file():
            assert p.suffix == ".gz" and len(p.relative_to(ROOT / "raw").parts) == 4, f"raw file outside layout: {p}"
            assert p.stat().st_size < 50 * 2 ** 20, f"raw file over 50 MB: {p}"
            total += p.stat().st_size
    assert total < 150 * 2 ** 20, f"Ohio raw files total {total:,} bytes"
    for src in REACHABLE:
        sample = raw_folder(src) / "sample.csv.gz"
        assert sample.exists(), f"no sample for {src}"
        n = len(rows_of(sample))
        assert 0 < n <= 100, f"{src} sample has {n} rows"
    assert not {"address1", "address2", "zip"} & set(header_of(raw_folder("oh_checkbook_state") / "sample.csv.gz")), \
        "state checkbook sample keeps address columns (they leak masked payees' names)"

    dollars = sum(v[1] for v in got.values())
    by_source = collections.Counter()
    for (a, s, fy), (n, _) in got.items():
        by_source[s] += n
    print(f"{ST}: oh_checkbook_local: months uploaded twice {sorted(DOUBLED)}; dates reloaded {sorted(RELOADED)}; "
          f"broken uploads left out {sorted(BROKEN)}")
    print(f"{ST}: program 220 townships linked: {len(POLICE_TOWNSHIPS)}, of them running police: "
          f"{sorted(k for k, v in POLICE_TOWNSHIPS.items() if v)}")
    print(f"{ST}: identical lines dropped: oh_cincinnati {IDENTICAL.pop('oh_cincinnati')}, oh_checkbook_local "
          f"{sum(IDENTICAL.values())} ({sum(1 for v in IDENTICAL.values() if v)} participants); identical copies kept "
          f"by the void rule: " + ", ".join(f"{s} {n} (${a:,.2f})" for s, (n, a) in sorted(VOID_KEPT.items())) +
          "; identical negative lines kept by the void fix (families at raw net): " +
          ", ".join(f"{s} {n} (${a:,.2f}, {f} families)" for s, (f, n, a) in sorted(VOID_FIX.items())))
    print(f"{ST}: ok ({len(tx)} transaction lines, ${dollars:,.2f}, {len(with_rows)} agencies at tier 1 "
          f"({', '.join(f'{s}: {n}' for s, n in sorted(by_source.items()))}); config/vendor_map.csv and the rules give "
          f"a real category to {share:.1%} of ${cov['purchasing']:,.0f} purchasing dollars (map "
          f"{cov['by_map'] / cov['purchasing']:.1%}, rules {cov['by_rule'] / cov['purchasing']:.1%}))")


if __name__ == "__main__":
    main()
