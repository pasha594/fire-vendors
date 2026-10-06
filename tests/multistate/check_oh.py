"""Recompute Ohio's normalized files from the raw files and check data/states/oh/ and config/states/oh/ match.

    python3 tests/multistate/check_oh.py

Independent of the adapters' code (it never imports pipeline/sources/oh_*.py): it reads the raw files with gzip,
csv and json, applies each source's published rule and compares
- oh_cincinnati: the raw CSV pages with the source's own server-side control totals per fiscal year and
  department; the linked fire department codes, fiscal year 2021 on;
- oh_checkbook_local: every linked participant's raw Tableau responses (underlying rows) with the summary totals
  the same dashboard gave for the same filters; fire districts' whole checkbooks, and for townships, cities and
  villages the lines whose fund or department is named for fire; calendar years 2021 on; one line per row Id,
  re-uploads (same transaction id, date, payee, fund, department, object and amount under a new row Id) once;
- lines and dollars per agency, source and fiscal year with data/states/oh/transactions.csv.gz;
- every published line, field by field, with its raw line (agency, fiscal year, date, payee, account, amount).
Also checks: the contract's column names and order; attribution (Cincinnati: every linked code is a fire
department and every fire-named department is linked or a known exclusion; checkbook: every linked participant
is a fire district or a township, city or village whose county equals the agency's county, no EMS-only
district, every participant line published is a fire line); agency ids, links and coverage tiers; duplicate
source_record_ids; sort order; payees published as the source has them except email or bank account text
(owner decision 2026-10-06); emails in any published text; sources.csv; vendor_map_additions.csv (spend
recomputed from raw, categories, >= 90% of purchasing dollars); raw files (location, size, samples for every
reachable source, no address columns in the state checkbook sample).
common is used only for norm() (the vendor map key).
"""
import collections
import csv
import decimal
import gzip
import io
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "sources"))
import common  # noqa: E402

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
ADDITION_COLUMNS = ["name_key", "vendor", "category", "confidence", "spend", "agencies"]

# Cincinnati: department codes whose name says fire but which are not the fire department (insurance shared by
# police and fire)
NOT_FIRE_CODES = {"922"}
REACHABLE = ["oh_cincinnati", "oh_checkbook_state", "oh_aos", "oh_checkbook_local"]  # sources with a sample

# Ohio Checkbook local: what a fire line is, written independently of the adapter
FIRE_WORD = re.compile(r"\bfire(s|fighters?|fighting|men|men'?s)?\b", re.I)
NOT_FIRE_WORDS = re.compile(r"police|hydrant|fire ?loss|firework|insurance|escrow|damaged structure|garnish", re.I)
EMS_ONLY_DISTRICTS = {"Joint Emergency Medical Service"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


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
    seen, out, lines = set(), collections.defaultdict(lambda: [0, D(0)]), {}
    for r in raw:
        key = tuple(r.values())
        if key in seen:
            continue
        seen.add(key)
        if int(r["fiscal_year"]) < FIRST_FY or r["dept_code"] not in links:
            continue
        k = (links[r["dept_code"]], r["fiscal_year"])
        out[k][0] += 1
        out[k][1] += D(r["amount"])
        rid = f"{r['trans_id']}-{r['trans_line_no']}"
        assert rid not in lines, f"raw record id {rid} is not unique"
        r = dict(r)
        r["_want"] = {"agency_id": links[r["dept_code"]], "fiscal_year": r["fiscal_year"],
                      "posting_date": r["record_date"][:10], "description": "",
                      "account": f"{r['dept_desc']} / {r['fund_code']} {r['fund_desc']} / "
                                 f"{r['exp_acct_cat']} {r['exp_acct_cat_desc']}",
                      "category_published": r["exp_acct_cat_desc"], "payee_name": redacted(r["vendor_name"]),
                      "amount": str(D(r["amount"]).quantize(CENTS))}
        r["_payee"] = r["vendor_name"]
        lines[rid] = r
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


def fire_line(kind, r):
    if kind == "special_districts":
        return True
    return any(FIRE_WORD.search(r[f]) and not NOT_FIRE_WORDS.search(r[f]) for f in ("FundDescription",
                                                                                    "DeptDescription"))


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
        assert p["County"] == agency_county[link["agency_id"]], f"county differs: {link} vs {p['County']}"
        assert link["fy_start"] == "01", f"Ohio locals use the calendar year: {link}"
        assert p["Name"] not in EMS_ONLY_DISTRICTS, f"EMS-only district linked: {link}"
        if kind == "special_districts":
            assert re.search(r"\bfire\b", p["Name"], re.I), f"special district that is not a fire district: {link}"
        doc = json.loads(gzip.decompress((d / f"entity_{eid}.json.gz").read_bytes()))
        assert doc["entity"]["name"] == p["Name"] and doc["entity"]["kind"] == kind, f"entity file {eid}"
        by_id, sums = {}, []
        for req in doc["requests"]:
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
                want[s["YEAR(Transaction Date)"]] += D(s["SUM(Amount)"])
            for r in by_id.values():
                if all(r[k] in v for k, v in filters.items()):
                    got[r["TransDate"][:4]] += D(r["Amt"]).quantize(CENTS)
            assert all(abs(want[y] - got[y]) <= CENTS for y in set(want) | set(got)), \
                f"{eid}: rows differ from the summary totals for {filters}"
        seen = set()
        for rid in sorted(by_id, key=int):
            r = by_id[rid]
            fy = r["TransDate"][:4]
            if int(fy) < FIRST_FY or not fire_line(kind, r):
                continue
            key = (r["TransactionId"], r["TransDate"], r["Payee"], r["FundCode"], r["DeptCode"], r["ObjCode"], r["Amt"])
            if key in seen:
                continue
            seen.add(key)
            amount = D(r["Amt"]).quantize(CENTS)
            k = (link["agency_id"], fy)
            out[k][0] += 1
            out[k][1] += amount
            r = dict(r)
            r["_want"] = {"agency_id": link["agency_id"], "fiscal_year": fy, "posting_date": r["TransDate"][:10],
                          "description": "", "payee_name": redacted(r["Payee"]), "amount": str(amount),
                          "account": f"{r['FundDescription']} - {r['FundCode']} / {r['DeptDescription']} - "
                                     f"{r['DeptCode']} / {r['ObjDescription']} - {r['ObjCode']}",
                          "category_published": r["ObjDescription"]}
            r["_payee"] = r["Payee"]
            lines[f"{eid}-{rid}"] = r
    return out, lines


def main():
    tx_path = ROOT / "data" / "states" / "oh" / "transactions.csv.gz"
    assert header_of(tx_path) == TX_COLUMNS, "transactions.csv.gz header differs from the data contract"
    tx = rows_of(tx_path)
    assert header_of(ROOT / "config" / "states" / "oh" / "sources.csv") == SOURCES_COLUMNS, "sources.csv header"
    assert header_of(ROOT / "config" / "states" / "oh" / "agency_sources.csv") == LINK_COLUMNS, "agency_sources header"
    assert header_of(ROOT / "config" / "states" / "oh" / "vendor_map_additions.csv") == ADDITION_COLUMNS, \
        "vendor_map_additions.csv header"
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

    # 5. no email address in any published text (payee text with one is withheld)
    for r in tx:
        assert not any(EMAIL.search(r[c]) for c in ("payee_name", "description", "account")), f"email: {r}"

    # 6. vendor_map_additions: spend recomputed from raw, valid categories, unique keys, >= 90% of purchasing
    categories = {c["id"]: c["purchasing"] == "yes" for c in config_rows("categories.csv", state=False)}
    vendor_map = {r["name_key"]: r["category"] for r in config_rows("vendor_map.csv", state=False)}
    additions = config_rows("vendor_map_additions.csv")
    keys = [r["name_key"] for r in additions]
    assert len(keys) == len(set(keys)), "duplicate name_key in vendor_map_additions.csv"
    assert all(r["category"] in categories for r in additions), "unknown category in vendor_map_additions.csv"
    assert all(k == common.norm(k) for k in keys), "name_key is not common.norm(name)"
    raw_spend = collections.defaultdict(D)
    raw_agencies = collections.defaultdict(set)
    for r in tx:
        k = common.norm(" ".join(raw_lines[(r["source"], r["source_record_id"])]["_payee"].split()))
        raw_spend[k] += D(r["amount"])
        raw_agencies[k].add(r["agency_id"])
    for r in additions:
        assert D(r["spend"]) == raw_spend.get(r["name_key"]), f"spend differs from raw: {r}"
        assert int(r["agencies"]) == len(raw_agencies[r["name_key"]]), f"agencies differs from raw: {r}"
    add = {r["name_key"]: r["category"] for r in additions}
    purchasing, covered = D(0), D(0)
    for r in tx:
        key = common.norm(r["payee_name"])
        cat = add.get(key) or vendor_map.get(key) or "unclassified"  # unmapped counts as purchasing
        if categories[cat]:
            purchasing += D(r["amount"])
            covered += D(r["amount"]) if key in add else 0
    share = covered / purchasing if purchasing else D(1)
    assert share >= D("0.9"), f"vendor_map_additions covers {share:.1%} of purchasing dollars"

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
    print(f"{ST}: ok ({len(tx)} transaction lines, ${dollars:,.2f}, {len(with_rows)} agencies at tier 1 "
          f"({', '.join(f'{s}: {n}' for s, n in sorted(by_source.items()))}); vendor_map_additions covers "
          f"{share:.1%} of ${purchasing:,.0f} purchasing dollars)")


if __name__ == "__main__":
    main()
