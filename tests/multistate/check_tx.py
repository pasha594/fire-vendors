"""Recompute Texas vendor-data totals from the raw files and check data/states/tx/ matches.

    python3 tests/multistate/check_tx.py

Independent of the adapters' code: nothing is imported from pipeline/sources/tx_*.py. Raw files are parsed here with their
own filters and duplicate rules; only config/states/tx/agency_sources.csv (the hand-reviewed attribution) is shared, and
common.py is used only to read files (read_gz, latest_raw, read_config, read_data_csv, norm). Checks:
  1. totals per source, agency and fiscal year (transactions, line items, published totals) match the raw files, and so do the
     row counts and, per source, every (agency, fiscal year, payee, amount) line: payee names are published as the source
     publishes them (owner decision, 2026-10-06), except payee text matching config/payee_name_redactions.csv (email
     addresses, bank account text), which reads "Payee name withheld". City sources (Houston, Austin, Dallas) follow the
     owner's dedup rule of 2026-10-07: of the raw lines equal in every published field but the source's own ids (built
     here from the raw columns: fiscal year, date, payee, description fields, account fields, category, amount), one is
     kept; a doubled day is such a set; negative lines compare like any other. No two published rows of a city source
     are equal in every column but source_record_id. tx_dir is exempt (owner decision 2 of 2026-10-06): only lines
     re-reported in a later month are dropped
  2. no published text column (payee, vendor, description, account, category) still matches a redaction pattern
  3. every agency_id in the tables, agency_sources.csv and grants exists in agencies.json; agencies_added.csv ids are new
  4. DIR attribution: every fire-filtered DIR customer name in the raw files is either linked in agency_sources.csv or listed
     in DIR_NOT_LINKED below with its reason (pension systems, regulators, EMS-only ESDs, out-of-state, ambiguous names);
     no name on that list is linked
  5. no duplicate source_record_id within a source; no empty ids
  6. columns and their order exactly as docs/multistate/data-contract.md; dates YYYY-MM-DD; amounts with two decimals;
     each city line's posting date falls inside its fiscal year
  7. vendor map: no unmerged config/states/tx/vendor_map_additions.csv; config/vendor_map.csv, then the vendor and keyword
     rules (as pipeline/build.py applies them), give a real category to at least 90% of purchasing dollars
  8. every table source is registered in sources.csv; coverage tiers and coverage_counts agree with the rows present
"""
import collections
import csv
import gzip
import io
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "pipeline" / "sources"))
import common  # noqa: E402  (file readers and norm)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vendor_coverage  # noqa: E402  (pipeline/build.py's vendor classification over config/vendor_map.csv)

ST = "TX"
ROOT = common.ROOT
WITHHELD_TEXT = "Payee name withheld"

# DIR customer names in the fire-filtered raw files that are deliberately not linked (docs/sources/tx.md, section 1).
DIR_NOT_LINKED = {
    # pension systems, regulator, training institute
    "Texas Emergency Services Retirement System", "Dallas Police & Fire Pension System",
    "Houston Firefighters Relief & Retirement Fund", "Oklahoma Firefighters Pension, Oklahoma",
    "Texas Commission on Fire Protection", "Texas Emergency Services Training Institute",
    # fire marshal offices (not fire departments)
    "Fire Marshal's Office", "Harris County Fire Marshal's Office", "Oklahoma State Fire Marshall, Oklahoma",
    # out of state
    "Country Corner Fire District, Oklahoma", "Parker Fire District",
    # EMS-only (ambulance) emergency services districts (owner decision 3, 2026-10-06)
    "Harris County Emergency Services District 1", "Harris County Emergency Services District 11",
    "Harris County Emergency Services District # 3", "Harris County Emergency Services District 5",
    "Hays County Emergency Services District No. 9", "Bastrop County Emergency Services District Number 3",
    "Medina County Emergency Service District No. 4",
    # names that fit several registry departments, or do not clearly name a fire department
    "Mid-County Fire/Rescue", "Northwest County Volunteer Fire Department", "Pleasant Grove Volunteer Fire Department, Inc.",
    "Reno Volunteer Fire Department", "Tri-County Volunteer Fire Department", "Pontotoc Ranch Fire Association",
    "Pedernales Emergency Services",
}


def cents(x):
    return round(float(str(x or 0).replace(",", "").replace("$", "")) * 100)


def ws(s):
    return " ".join((s or "").split())


REDACTIONS = [re.compile(r["pattern"], re.I) for r in csv.DictReader(open(ROOT / "config" / "payee_name_redactions.csv",
                                                                          encoding="utf-8"))]


def published(name):
    name = ws(name)
    return WITHHELD_TEXT if any(rx.search(name) for rx in REDACTIONS) else name


def links(source):
    return {r["source_entity_name"]: r["agency_id"] for r in common.read_config(ST, "agency_sources.csv") if r["source"] == source}


class Expect:
    """Expected lines of one source: totals per (agency, fy) and a multiset of (agency, fy, payee, cents)."""

    def __init__(self):
        self.totals, self.lines, self.n = collections.Counter(), collections.Counter(), 0

    def add(self, aid, fy, payee, amount):
        c = cents(amount)
        self.totals[(aid, fy)] += c
        self.lines[(aid, fy, published(payee), c)] += 1
        self.n += 1


def expect_dir():
    """tx_dir: linked customers, FY2021+; a line whose every field except row ids and months equals a line of an earlier
    reporting month is a re-report and dropped; identical lines inside one month are kept (owner decision 2)."""
    raw, link = common.latest_raw(ST, "tx_dir"), links("tx_dir")
    lines, names = [], set()
    for name, month_field in (("archive_fy2021_2025.json.gz", "report_received_month"),
                              ("current_fy2026.json.gz", "reporting_month")):
        for r in json.loads(common.read_gz(raw / name)):
            cust = ws(r.get("customer_name"))
            names.add(cust)
            fy = int(float(r["fiscal_year"]))
            if cust in link and fy >= 2021:
                sale = (name,) + tuple(sorted((k, str(v)) for k, v in r.items() if k not in (
                    ":id", "sales_fact_number", "report_received_month", "reporting_month", "purchase_month", "fiscal_year")))
                seller = r.get("reseller_name") or r.get("vendor_name") or ""
                lines.append((sale, r.get(month_field, ""), link[cust], fy, seller, r.get("purchase_amount")))
    first = {}
    for sale, month, *_ in lines:
        first[sale] = min(first.get(sale, month), month)
    e = Expect()
    for sale, month, aid, fy, seller, amount in lines:
        if month == first[sale]:
            e.add(aid, fy, seller, amount)
    return e, names


DROPPED = {}  # source -> (identical sets, lines dropped, cents dropped), for the report


def keep_one(source, lines):
    """Owner rule of 2026-10-07: of lines with equal identity (every published field but the source's own row, payment
    document, invoice, line or PO ids), keep the first. lines: (identity, (agency, fy, payee, amount)) in raw order."""
    e, seen, sets, n, dropped = Expect(), set(), set(), 0, 0
    for ident, (aid, fy, payee, amount) in lines:
        if ident in seen:
            sets.add(ident)
            n += 1
            dropped += cents(amount)
            continue
        seen.add(ident)
        e.add(aid, fy, payee, amount)
    DROPPED[source] = (len(sets), n, dropped)
    return e


def expect_houston():
    """Identity: fiscal year, clearing date, payee, type of procurement, WBS description, PO number and item, contract,
    fund name, GL account and amount. Payment document number, vendor invoice, WBS and fund codes are left out."""
    raw, aid = common.latest_raw(ST, "tx_houston"), next(iter(links("tx_houston").values()))
    manifest = {m["fiscal_year"]: m for m in json.loads(common.read_gz(raw / "manifest.json.gz"))}
    lines = []
    files = sorted(raw.glob("checkbook-*-hfd.csv.gz"))
    assert {int(p.name.split("-")[1]) for p in files} == set(manifest), "Houston files differ from the manifest"
    for path in files:
        rows = list(csv.reader(io.StringIO(common.read_gz(path).decode("utf-8"))))
        header, body = rows[0], rows[1:]
        fy = int(path.name.split("-")[1])
        assert manifest[fy]["hfd_lines"] == len(body), f"{path.name}: line count differs from manifest"
        col = {h: i for i, h in enumerate(header)}
        for row in body:
            assert row[col["Department ID"]] == "1200" and int(row[col["Fiscal Year"]]) == fy
            v = lambda h: row[col[h]]
            ident = (fy, v("Clearing Date"), published(v("Vendor Name")), v("Type of procurement"), v("WBS Description"),
                     *(x if x.strip("0") else "" for x in (v("Purchase Order Number"), v("Purchase Order Item"))),
                     v("Contract Number"),
                     v("Fund Name"), v("GL Account Number"), v("GL Account Description"), cents(v("Amount")))
            lines.append((ident, (aid, fy, v("Vendor Name"), v("Amount"))))
    return keep_one("tx_houston", lines)


def expect_socrata(source, name, dept_field, dept, fy_field, amount_field, payee_field, ident_fields):
    """ident_fields: the raw published fields (besides fiscal year, payee and amount) whose equality makes two lines
    identical; a value 'a|b' means field a, or field b when a is empty. Date fields compare on the day."""
    raw, aid = common.latest_raw(ST, source), next(iter(links(source).values()))
    lines = []
    for r in sorted(json.loads(common.read_gz(raw / name)), key=lambda r: r[":id"]):
        assert str(r[dept_field]) == dept
        fields = []
        for f in ident_fields:
            a, _, b = f.partition("|")
            x = r.get(a) or (r.get(b) if b else "") or ""
            fields.append(x[:10] if "dt" in a or "date" in a else x)
        ident = (int(r[fy_field]), published(r.get(payee_field, "")), *fields, cents(r[amount_field]))
        lines.append((ident, (aid, int(r[fy_field]), r.get(payee_field, ""), r[amount_field])))
    return keep_one(source, lines)


def expect_cpa():
    raw = common.latest_raw(ST, "tx_cpa")
    row = [r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == "tx_cpa"][0]
    out = collections.Counter()
    for path in sorted(raw.glob("*.json.gz")):
        if path.name.startswith("sample"):
            continue
        for r in json.loads(common.read_gz(path)):
            if str(r.get("agency_number") or r.get("number") or "").split(".")[0] != row["source_entity_id"]:
                continue
            out[(row["agency_id"], int(float(r["fiscal_year"])))] += cents(r.get("amount"))
    return out


def got_totals(rows, source):
    out = collections.Counter()
    for r in rows:
        if r["source"] == source:
            out[(r["agency_id"], int(r["fiscal_year"]))] += cents(r["amount"])
    return out


def got_lines(rows, source, payee_field):
    return collections.Counter((r["agency_id"], int(r["fiscal_year"]), r[payee_field], cents(r["amount"]))
                               for r in rows if r["source"] == source)


def same(label, want, have):
    keys = set(want) | set(have)
    bad = {k: (want.get(k, 0), have.get(k, 0)) for k in keys if want.get(k, 0) != have.get(k, 0)}
    assert not bad, f"{label}: differs (raw, normalized), {len(bad)} keys, e.g. {dict(sorted(bad.items(), key=str)[:4])}"


def contract_columns():
    """Column lists of the three tables, read from docs/multistate/data-contract.md."""
    text = (ROOT / "docs" / "multistate" / "data-contract.md").read_text(encoding="utf-8")
    out = {}
    for table in ("transactions.csv.gz", "line_items.csv.gz", "totals.csv"):
        section = text.split(f"## `data/states/<st>/{table}`", 1)[1].split("\n## ", 1)[0]
        cols = []
        for line in section.splitlines():
            m = re.match(r"^\| (`[^|]+`) \|", line)
            if m:
                cols += [c.strip().strip("`") for c in m.group(1).split(",")]
        out[table] = cols
    return out


def main():
    d = common.data_dir(ST)
    tx = common.read_data_csv(d / "transactions.csv.gz")
    li = common.read_data_csv(d / "line_items.csv.gz")
    tot = common.read_data_csv(d / "totals.csv")
    agencies = json.loads((d / "agencies.json").read_text())
    ids = {a["id"] for a in agencies["agencies"]}
    kinds = {a["id"]: a["kind"] for a in agencies["agencies"]}
    assert kinds.get("TX-S-texas-a-and-m-forest-service") == "State fire agency" \
        and kinds.get("TX-X-TEXAS-FOREST-SERVICE-JEFFERSON-DISTRICT-JEFFERSON") == "State fire agency", \
        "Texas A&M Forest Service keeps kind 'State fire agency' (owner decision 4)"

    # 1. Totals, row counts and payee lines per source
    e, dir_names = expect_dir()
    same("tx_dir transactions totals", e.totals, got_totals(tx, "tx_dir"))
    same("tx_dir line item totals", e.totals, got_totals(li, "tx_dir"))
    same("tx_dir transactions lines", e.lines, got_lines(tx, "tx_dir", "payee_name"))
    same("tx_dir line items lines", e.lines, got_lines(li, "tx_dir", "vendor"))
    assert e.n == sum(r["source"] == "tx_dir" for r in tx) == sum(r["source"] == "tx_dir" for r in li), "tx_dir row counts"
    for source, e in {
        "tx_houston": expect_houston(),
        "tx_dallas": expect_socrata("tx_dallas", "dfd.json.gz", "dpt", "DFD", "fy", "chksubtot", "vendor",
                                    ("rundate", "commoditydscr", "activity", "fundtype", "obj", "object", "objectgroup")),
        "tx_austin": expect_socrata("tx_austin", "fire.json.gz", "dept_cd", "83", "fy_dc", "amount", "lgl_nm",
                                    ("chk_eft_iss_dt", "actg_ln_dscr|comm_dscr", "fund_nm", "div_nm", "gp_nm", "obj_cd",
                                     "obj_nm", "ocat_nm")),
    }.items():
        same(f"{source} totals", e.totals, got_totals(tx, source))
        same(f"{source} lines", e.lines, got_lines(tx, source, "payee_name"))
        assert e.n == sum(r["source"] == source for r in tx), f"{source}: row count {e.n} raw vs normalized"
        cols = [c for c in contract_columns()["transactions.csv.gz"] if c != "source_record_id"]
        twins = collections.Counter(tuple(r[c] for c in cols) for r in tx if r["source"] == source)
        extra = sum(n - 1 for n in twins.values())
        assert not extra, f"{source}: {extra} published rows equal to another in every column but source_record_id"
    same("tx_cpa totals", expect_cpa(), got_totals(tot, "tx_cpa"))

    # 2. Redaction patterns no longer match any published text
    for table, rows, fields in (("transactions", tx, ("payee_name", "description", "account", "category_published")),
                                ("line_items", li, ("vendor", "brand", "product_type", "description")),
                                ("totals", tot, ("category_published",))):
        hits = [(f, r[f]) for r in rows for f in fields if any(rx.search(r[f]) for rx in REDACTIONS)]
        assert not hits, f"{table}: {len(hits)} values match a redaction pattern, e.g. {hits[:2]}"

    # 3. Agency ids
    for table, rows in (("transactions", tx), ("line_items", li), ("totals", tot)):
        missing = {r["agency_id"] for r in rows} - ids
        assert not missing, f"{table}: agency ids not in agencies.json: {sorted(missing)[:5]}"
    missing = {r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")} - ids
    assert not missing, f"agency_sources.csv: unknown agency ids {sorted(missing)[:5]}"
    missing = {r["agency_id"] for r in common.read_data_csv(d / "grants.csv")} - ids
    assert not missing, f"grants.csv: unknown agency ids {sorted(missing)[:5]}"
    registry = {r["id"] for r in common.read_config(ST, "agencies.csv")}
    added = [r["id"] for r in common.read_config(ST, "agencies_added.csv")]
    assert all(i.startswith("TX-S-") for i in added) and not set(added) & registry, "agencies_added.csv ids"
    assert len(set(added)) == len(added), "agencies_added.csv: duplicate id"

    # 4. DIR attribution covers every raw customer name, and excluded names stay unlinked
    linked = set(links("tx_dir"))
    assert not linked & DIR_NOT_LINKED, f"excluded DIR names are linked: {sorted(linked & DIR_NOT_LINKED)}"
    assert linked <= dir_names, f"linked DIR names absent from the raw files: {sorted(linked - dir_names)[:5]}"
    stray = dir_names - linked - DIR_NOT_LINKED
    assert not stray, f"DIR customer names neither linked nor excluded: {sorted(stray)[:5]}"
    used_added = {r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")}
    assert set(added) <= used_added, f"agencies_added.csv rows no source links: {sorted(set(added) - used_added)[:5]}"

    # 5. Unique source_record_id per source
    for table, rows in (("transactions", tx), ("line_items", li)):
        c = collections.Counter((r["source"], r["source_record_id"]) for r in rows)
        dup = [k for k, v in c.items() if v > 1]
        assert not dup, f"{table}: duplicate source_record_id {dup[:5]}"
        assert all(r["source_record_id"] for r in rows), f"{table}: empty source_record_id"

    # 6. Contract conformance
    for table, cols in contract_columns().items():
        body = (d / table).read_bytes()
        body = gzip.decompress(body) if table.endswith(".gz") else body
        header = body.decode("utf-8").split("\n", 1)[0]
        assert header == ",".join(cols), f"{table}: header {header} differs from the data contract {cols}"
    date = re.compile(r"\d{4}-\d{2}-\d{2}")
    money = re.compile(r"-?\d+\.\d{2}")
    fy_start = {"tx_houston": 7, "tx_dallas": 10, "tx_austin": 10}
    for r in tx:
        assert not r["posting_date"] or date.fullmatch(r["posting_date"]), r
        assert money.fullmatch(r["amount"]) and r["fiscal_year"].isdigit(), r
        if r["posting_date"] and r["source"] in fy_start:
            y, m = int(r["posting_date"][:4]), int(r["posting_date"][5:7])
            assert int(r["fiscal_year"]) == (y + 1 if m >= fy_start[r["source"]] else y), f"posting date outside FY: {r}"
    for r in li:
        assert not r["date"] or date.fullmatch(r["date"]), r
        assert money.fullmatch(r["amount"]) and r["fiscal_year"].isdigit(), r
    for r in tot:
        assert money.fullmatch(r["amount"]) and r["fiscal_year"].isdigit(), r

    # 7. vendor map: payees classified the way pipeline/build.py classifies them (config/vendor_map.csv, then the
    #    vendor and keyword rules); proposals are folded into config/vendor_map.csv by merge_vendor_maps.py
    assert not (common.config_dir(ST) / "vendor_map_additions.csv").exists(), \
        "config/states/tx/vendor_map_additions.csv: fold it into config/vendor_map.csv (merge_vendor_maps.py)"
    spend = collections.Counter()
    for r in tx:
        spend[common.norm(r["payee_name"])] += cents(r["amount"])
    cov = vendor_coverage.Classifier().coverage(spend)
    share = cov["share_real"]
    assert share >= 0.9, f"vendor map gives a real category to only {share:.1%} of purchasing dollars"

    # 8. Sources and coverage tiers
    sources = {r["source"]: r for r in common.read_config(ST, "sources.csv")}
    used = {r["source"] for r in tx} | {r["source"] for r in li} | {r["source"] for r in tot}
    assert used == set(sources), f"sources.csv and table sources differ: {used ^ set(sources)}"
    assert all(all(s[f] for f in ("name", "tier", "url", "years", "fiscal_year", "fetched")) for s in sources.values())
    best = collections.defaultdict(lambda: 4)
    for r in tx:
        best[r["agency_id"]] = min(best[r["agency_id"]], int(sources[r["source"]]["tier"]))
    for r in li:
        best[r["agency_id"]] = min(best[r["agency_id"]], 2)
    for r in tot:
        best[r["agency_id"]] = min(best[r["agency_id"]], 3)
    for a in agencies["agencies"]:
        assert a["coverage"] == best[a["id"]], f"{a['id']}: coverage {a['coverage']} vs rows {best[a['id']]}"
    counts = collections.Counter(a["coverage"] for a in agencies["agencies"])
    assert agencies["coverage_counts"] == {str(t): counts.get(t, 0) for t in (1, 2, 3, 4)}
    assert len(agencies["agencies"]) == len(registry) + len(added)

    by_source = collections.Counter()
    for r in tx:
        by_source[r["source"]] += cents(r["amount"])
    print(f"{ST}: ok ({len(tx)} payment lines, {len(li)} item lines, {len(tot)} totals rows; "
          + ", ".join(f"{s} ${v / 100:,.0f}" for s, v in sorted(by_source.items()))
          + f"; config/vendor_map.csv and the rules give a real category to {share:.1%} of "
          + f"${cov['purchasing'] / 100:,.0f} purchasing dollars (map {cov['by_map'] / cov['purchasing']:.1%}, rules "
          + f"{cov['by_rule'] / cov['purchasing']:.1%}); tiers {dict(sorted(agencies['coverage_counts'].items()))}; "
          + "identical lines dropped (owner rule of 2026-10-07): "
          + ", ".join(f"{s} {n} (${c / 100:,.2f}, {g} sets)" for s, (g, n, c) in sorted(DROPPED.items())) + ")")


if __name__ == "__main__":
    main()
