"""Recompute Ohio's normalized files from the raw files and check data/states/oh/ and config/states/oh/ match.

    python3 tests/multistate/check_oh.py

Independent of the adapters' code (it never imports pipeline/sources/oh_*.py): reads the raw CSV pages with gzip
and csv, applies the published filter (linked department codes, fiscal year 2021 on) and compares
- the raw pages with the source's own server-side control totals per fiscal year and department;
- lines and dollars per agency, source and fiscal year with data/states/oh/transactions.csv.gz;
- every published line, field by field, with its raw line (agency, fiscal year, date, payee, account, amount).
Also checks: the contract's column names and order; that every linked source entity is a fire department (not
police, insurance, pension or the shared 911 center) and every fire-named department is linked or a known
exclusion; agency ids, links and coverage tiers; duplicate source_record_ids; sort order; private persons
(common.is_person / looks_like_person plus independent person-name shapes); emails in any published text;
sources.csv; vendor_map_additions.csv (spend recomputed from raw, categories, >= 90% of purchasing dollars); raw
files (location, size, samples for every reachable source, no address columns in the state checkbook sample).
common is used only for the shared person rules, norm() and the withheld marker.
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
WITHHELD = {common.WITHHELD, "Payee name withheld"}

# docs/multistate/data-contract.md, written out here so a change in common.TABLES is caught
TX_COLUMNS = ["agency_id", "fiscal_year", "posting_date", "payee_name", "description", "account",
              "category_published", "amount", "source", "source_record_id"]
SOURCES_COLUMNS = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]
LINK_COLUMNS = ["agency_id", "source", "source_entity_id", "source_entity_name", "fy_start", "match_method", "note"]
ADDITION_COLUMNS = ["name_key", "vendor", "category", "confidence", "spend", "agencies"]

# Cincinnati: account paid to individual employees and retirees; department codes whose name says fire but which
# are not the fire department (insurance shared by police and fire)
PERSON_ACCOUNTS = {"Uniform And Other Allowance"}
NOT_FIRE_CODES = {"922"}
REACHABLE = ["oh_cincinnati", "oh_checkbook_state", "oh_aos"]  # sources with a sample (checkbook_local: robots.txt)

# person-name shapes the shared rules miss, written independently of the adapter
NAME = r"[A-Za-z'\-]{2,}"
PERSON_SHAPES = [
    re.compile(rf"^{NAME}( [A-Za-z]\.?)? {NAME},? (JR|SR|II|III|IV)\.?$", re.I),   # Donald Buchanan III
    re.compile(rf"^{NAME} {NAME},? [A-Za-z]\.?$"),                                  # Wiley Ruth M.
    re.compile(rf"^(MR|MRS|MS|DR)\.? {NAME}( {NAME})?$", re.I),                     # Mr Nyren
    re.compile(rf"^{NAME} [A-Za-z]\.? {NAME} [A-Za-z]{{2,4}}$"),                    # Michael W Earls SMS
    re.compile(rf"^{NAME} [A-Za-z]\.? {NAME}$"),                                    # Brian D. Vorholt
]
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


def expected_cincinnati():
    """(agency_id, fiscal_year) -> [lines, dollars] straight from the raw pages; also the raw lines by record id."""
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
        lines[rid] = r
    return out, lines, links


def is_person_like(name):
    if common.is_person(name) or common.looks_like_person(name):
        return True
    return not common.BUSINESS_WORDS.search(name) and any(rx.match(name) for rx in PERSON_SHAPES)


def main():
    tx_path = ROOT / "data" / "states" / "oh" / "transactions.csv.gz"
    assert header_of(tx_path) == TX_COLUMNS, "transactions.csv.gz header differs from the data contract"
    tx = rows_of(tx_path)
    assert header_of(ROOT / "config" / "states" / "oh" / "sources.csv") == SOURCES_COLUMNS, "sources.csv header"
    assert header_of(ROOT / "config" / "states" / "oh" / "agency_sources.csv") == LINK_COLUMNS, "agency_sources header"
    assert header_of(ROOT / "config" / "states" / "oh" / "vendor_map_additions.csv") == ADDITION_COLUMNS, \
        "vendor_map_additions.csv header"
    agencies = json.loads((ROOT / "data" / "states" / "oh" / "agencies.json").read_text())
    ids = {a["id"] for a in agencies["agencies"]}
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
    exp_cin, raw_lines, cin_links = expected_cincinnati()
    expect = {(a, "oh_cincinnati", fy): v for (a, fy), v in exp_cin.items()}
    assert set(got) == set(expect), f"agency/source/year keys differ: {sorted(set(got) ^ set(expect))[:5]}"
    for k in sorted(expect):
        assert got[k][0] == expect[k][0] and got[k][1] == expect[k][1], f"{k}: got {got[k]}, raw {expect[k]}"
    assert {s for _, s, _ in got} <= set(sources), "a source with rows is missing from sources.csv"

    # 2. every published line equals its raw line, field by field
    for r in tx:
        if r["source"] != "oh_cincinnati":
            continue
        raw = raw_lines[r["source_record_id"]]
        name = " ".join(raw["vendor_name"].split())
        want = {"agency_id": cin_links[raw["dept_code"]], "fiscal_year": raw["fiscal_year"],
                "posting_date": raw["record_date"][:10], "description": "",
                "account": f"{raw['dept_desc']} / {raw['fund_code']} {raw['fund_desc']} / "
                           f"{raw['exp_acct_cat']} {raw['exp_acct_cat_desc']}",
                "category_published": raw["exp_acct_cat_desc"]}
        assert all(r[k] == v for k, v in want.items()), f"{r['source_record_id']}: {r} differs from raw {raw}"
        assert D(raw["amount"]).quantize(CENTS) == D(r["amount"]), f"amount differs for {r['source_record_id']}"
        assert r["payee_name"] in WITHHELD | {name}, f"payee changed: {name!r} -> {r['payee_name']!r}"
        if raw["exp_acct_cat_desc"] in PERSON_ACCOUNTS or common.is_person(name):
            assert r["payee_name"] in WITHHELD, f"person payee published: {name!r}"

    # 3. agency ids, links and coverage
    assert {a for a, _, _ in got} <= ids, "transactions for agencies not in agencies.json"
    links = config_rows("agency_sources.csv")
    assert all(r["agency_id"] in ids and re.fullmatch(r"0[1-9]|1[0-2]", r["fy_start"]) for r in links), "agency_sources"
    linked = {(r["agency_id"], r["source"]) for r in links}
    assert {(a, s) for a, s, _ in got} <= linked, "rows for an agency and source without an agency_sources.csv link"
    added = config_rows("agencies_added.csv")
    assert all(r["id"].startswith("OH-S-") for r in added), "agencies_added ids must be OH-S-<slug>"
    with_rows = {a for a, _, _ in got}
    tiers = {}
    for a in agencies["agencies"]:
        tiers[a["id"]] = a["coverage"]
        if a["id"] in with_rows:
            assert a["coverage"] == 1, f"{a['id']} has payee rows but coverage {a['coverage']}"
            assert "oh_cincinnati" in a["sources"] and a["fy_start"] == "07", f"{a['id']}: {a}"
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

    # 5. no private person's name: is_person names are always withheld; looks_like_person names and the
    #    independent shapes only when no vendor_map / vendor_map_additions row claims them as a business (never
    #    for is_person); no email address in any published text
    claimed = {r["name_key"] for r in config_rows("vendor_map.csv", state=False) if r["category"] != "individuals"} \
        | {r["name_key"] for r in config_rows("vendor_map_additions.csv") if r["category"] != "individuals"}
    for r in tx:
        assert not any(EMAIL.search(r[c]) for c in ("payee_name", "description", "account")), f"email: {r}"
        name = r["payee_name"]
        if name in WITHHELD:
            continue
        assert not common.is_person(name), f"person-like payee published: {name!r}"
        assert not is_person_like(name) or common.norm(name) in claimed, f"person-like payee published: {name!r}"

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
        raw = raw_lines.get(r["source_record_id"]) if r["source"] == "oh_cincinnati" else None
        k = common.norm(" ".join(raw["vendor_name"].split()) if raw else r["payee_name"])
        raw_spend[k] += D(r["amount"])
        raw_agencies[k].add(r["agency_id"])
    for r in additions:
        assert D(r["spend"]) == raw_spend.get(r["name_key"]), f"spend differs from raw: {r}"
        assert int(r["agencies"]) == len(raw_agencies[r["name_key"]]), f"agencies differs from raw: {r}"
    add = {r["name_key"]: r["category"] for r in additions}
    purchasing, covered = D(0), D(0)
    for r in tx:
        key = common.norm(r["payee_name"])
        if r["payee_name"] in WITHHELD:
            cat = "individuals"
        else:
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
    print(f"{ST}: ok ({len(tx)} transaction lines, ${dollars:,.2f}, {len(with_rows)} agencies at tier 1; "
          f"vendor_map_additions covers {share:.1%} of ${purchasing:,.0f} purchasing dollars)")


if __name__ == "__main__":
    main()
