"""Recompute Idaho vendor-data totals from the raw files and check data/states/id/ matches.

    python3 tests/multistate/check_id.py

Independent of the adapters' code: it imports neither id_state nor id_lgr. Raw files are parsed here with their
own filters and duplicate rules; shared with the adapters are only the hand-reviewed config files
(config/states/id/agency_sources.csv, agencies_added.csv) and common's file readers and norm(). Checks:
  - columns and their order exactly as docs/multistate/data-contract.md (tables, sources.csv, agency_sources.csv);
    dates YYYY-MM-DD inside the fiscal year; amounts with two decimals
  - id_lgr: every Fire District (registry entity type 6) has an agency_sources.csv row; one totals row per agency and
    fiscal year equal to the district's filed actual expenditures; every county copy of a multi-county district
    equal; no row for a null or zero actual
  - id_state: fetched lines per year equal the control file's non-Personnel line count, and raw dollars per year and
    account category equal the control file's server-side sums; identical lines dropped (owner rule of 2026-10-07:
    lines equal in every column but unique_id and the load dates are kept once, the earliest load batch's lowest
    unique_id, whether the copy came in a later batch or the same one); then, line by line, every kept payment
    line is in transactions.csv.gz under its own unique_id (or unique_id-<n>) with the same fiscal year, date,
    amount, account title and payee; and no two id_state rows are equal in every column but source_record_id
  - payee names as published (owner decision 2026-10-06): payee_name is the raw vendor with whitespace collapsed,
    or "Payee name withheld" exactly when it matches config/payee_name_redactions.csv; no column holds text those
    patterns match; no "Individual (name withheld)" left from the old rule
  - every agency_id in the tables, agency_sources.csv and grants exists in agencies.json; id_state rows go only to
    the Idaho Department of Lands fire row
  - no duplicate or empty source_record_id within a source
  - every table source is registered in sources.csv with every column filled; coverage tiers agree with the rows
    present; no agency gets a $0 totals row
  - vendor map: no unmerged config/states/id/vendor_map_additions.csv; config/vendor_map.csv, then the vendor and
    keyword rules (as pipeline/build.py applies them), give a real category to at least 90% of purchasing dollars
    (payees with net spend above zero; unmapped payees counted as purchasing); IDL keeps kind "State fire agency"
"""
import collections
import csv
import gzip
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "sources"))
import common  # noqa: E402  (file readers and norm only)
sys.path.insert(0, str(ROOT / "tests" / "multistate"))
import vendor_coverage  # noqa: E402  (pipeline/build.py's vendor classification over config/vendor_map.csv)

ST = "ID"
IDL = "ID-X-IDAHO-DEPARTMENT-OF-LANDS-FIRE-DEPARTMENT-COEUR-D-ALENE"
NOT_PAYMENTS = {"Encumbrances", "GAAP Expenses", "Loss", "Operating Transfers Out", "Other Financing Uses", "Personnel"}
LOAD_COLS = ("unique_id", "date_of_load", "zz_extract_date")


def cents(x):
    return round(float(x) * 100)


def gz_json(path):
    return json.loads(gzip.decompress(pathlib.Path(path).read_bytes()))


def links(source):
    return {r["source_entity_id"]: r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")
            if r["source"] == source}


def contract_columns():
    """Column lists from docs/multistate/data-contract.md: the three tables and two config files."""
    text = (ROOT / "docs" / "multistate" / "data-contract.md").read_text(encoding="utf-8")
    out = {}
    for name, heading in (("transactions.csv.gz", "## `data/states/<st>/transactions.csv.gz`"),
                          ("line_items.csv.gz", "## `data/states/<st>/line_items.csv.gz`"),
                          ("totals.csv", "## `data/states/<st>/totals.csv`"),
                          ("sources.csv", "## `config/states/<st>/sources.csv`"),
                          ("agency_sources.csv", "## `config/states/<st>/agency_sources.csv`")):
        section = text.split(heading, 1)[1].split("\n## ", 1)[0]
        cols = []
        for line in section.splitlines():
            m = re.match(r"^\| (`[^|]+`) \|", line)
            if m:
                cols += [c.strip().strip("`") for c in m.group(1).split(",")]
        out[name] = cols
    return out


def header(path):
    path = pathlib.Path(path)
    body = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return body.split(b"\n", 1)[0].decode("utf-8")


def expect_lgr():
    """{(agency, fy): cents} from raw/<date>/id/id_lgr/fire_districts_fy*.json.gz."""
    raw, link = common.latest_raw(ST, "id_lgr"), links("id_lgr")
    fire = {str(e["EntityID"]) for e in gz_json(raw / "entity_lists.json.gz")["6"]}
    assert fire <= set(link), f"id_lgr: fire districts without agency_sources.csv row: {sorted(fire - set(link))[:5]}"
    seen, out = {}, collections.Counter()
    for path in sorted(raw.glob("fire_districts_fy*.json.gz")):
        fy = re.search(r"fy(\d{4})", path.name).group(1)
        for county, recs in gz_json(path).items():
            for r in recs:
                key = (str(r["EntityID"]), fy)
                assert key[0] in fire, f"id_lgr: entity {key[0]} answered for type 6 but not in the type-6 list"
                if key in seen:
                    assert seen[key] == r["Actual_Expenditures"], f"county copies disagree for {key}"
                    continue
                seen[key] = r["Actual_Expenditures"]
    for (eid, fy), actual in seen.items():
        if actual:
            out[(link[eid], fy)] += round(actual * 100)
    return out


def raw_state_lines():
    """Every fetched id_state line (dicts), checked against the control file's counts and dollars."""
    raw = common.latest_raw(ST, "id_state")
    control = gz_json(raw / "control.json.gz")
    lines = []
    for path in sorted(raw.glob("lines_fy*.json.gz")):
        fy = re.search(r"fy(\d{4})", path.name).group(1)
        d = gz_json(path)
        rows = [dict(zip(d["columns"], r)) for r in d["rows"]]
        expected = sum(v["lines"] for k, v in control[fy].items() if k != "Personnel")
        assert len(rows) == expected, f"id_state FY{fy}: {len(rows)} lines, control {expected}"
        assert len({json.dumps(r) for r in d["rows"]}) == len(rows), f"id_state FY{fy}: a line repeats"
        by_cat = collections.Counter()
        for r in rows:
            assert r["agency_code_function_code"] == "320-07H" and r["account_type"] == "Expense", r["unique_id"]
            assert str(r["fiscal_year"]) == fy, f"id_state: FY{fy} file holds a FY{r['fiscal_year']} line"
            by_cat[r["account_category_0"]] += round((r["amount"] or 0) * 100)
        for cat, v in control[fy].items():
            if cat != "Personnel":
                assert by_cat[cat] == round(v["amount"] * 100), f"id_state FY{fy} {cat}: raw {by_cat[cat]} vs control"
        assert set(by_cat) <= set(control[fy]), f"id_state FY{fy}: category not in control"
        lines += rows
    return lines


def kept_state_lines(lines):
    """Lines left after dropping identical lines (owner rule of 2026-10-07, see the module docstring): one line per
    set equal in every column but LOAD_COLS, the earliest load batch's lowest unique_id."""
    content = lambda r: json.dumps({k: v for k, v in r.items() if k not in LOAD_COLS}, sort_keys=True)
    order = lambda r: (r["date_of_load"] or "", r["zz_extract_date"] or "", int(r["unique_id"]))
    first = {}
    for r in lines:
        c = content(r)
        if c not in first or order(r) < order(first[c]):
            first[c] = r
    keep = list(first.values())
    dropped = len(lines) - len(keep)
    assert dropped < 0.02 * len(lines), f"id_state: {dropped} identical lines, more than 2% of lines"
    return keep, dropped


def redactions():
    return [re.compile(r["pattern"], re.I)
            for r in csv.DictReader(open(ROOT / "config" / "payee_name_redactions.csv", encoding="utf-8"))]


def published(vendor, rx):
    name = " ".join((vendor or "").split())
    return "Payee name withheld" if any(p.search(name) for p in rx) else name


def check_state_lines(tx, rx):
    """Line-by-line comparison of the id_state rows with the kept raw payment lines."""
    lines = raw_state_lines()
    keep, dropped = kept_state_lines(lines)
    want = collections.Counter()
    for r in keep:
        if r["account_category_0"] in NOT_PAYMENTS:
            continue
        want[(str(r["unique_id"]), str(r["fiscal_year"]), r["effective_date"] or "", f"{r['amount'] or 0:.2f}",
              r["summary_account"] or "", published(r["vendor"], rx))] += 1
    have = collections.Counter()
    for r in tx:
        if r["source"] != "id_state":
            continue
        assert r["agency_id"] == IDL, f"id_state row for {r['agency_id']}"
        uid = re.fullmatch(r"(\d+)(-\d+)?", r["source_record_id"])
        assert uid, f"id_state: source_record_id {r['source_record_id']} is not a raw unique_id"
        have[(uid.group(1), r["fiscal_year"], r["posting_date"], r["amount"], r["category_published"],
              r["payee_name"])] += 1
    diff = (want - have) + (have - want)
    assert not diff, f"id_state: {sum(diff.values())} lines differ from raw, e.g. {list(diff)[:3]}"
    same = collections.Counter(tuple(v for k, v in r.items() if k != "source_record_id")
                               for r in tx if r["source"] == "id_state")
    assert max(same.values()) == 1, f"id_state: {sum(n - 1 for n in same.values() if n > 1)} identical rows left"
    return len(lines), dropped


def main():
    d = common.data_dir(ST)
    tx = common.read_data_csv(d / "transactions.csv.gz") if (d / "transactions.csv.gz").exists() else []
    tot = common.read_data_csv(d / "totals.csv") if (d / "totals.csv").exists() else []
    li = common.read_data_csv(d / "line_items.csv.gz") if (d / "line_items.csv.gz").exists() else []
    agencies = json.loads((d / "agencies.json").read_text(encoding="utf-8"))
    rx = redactions()

    # 0. Contract columns, dates and amounts
    cols = contract_columns()
    for name in ("transactions.csv.gz", "line_items.csv.gz", "totals.csv"):
        if (d / name).exists():
            assert header(d / name) == ",".join(cols[name]), f"{name}: header differs from the data contract"
    for name in ("sources.csv", "agency_sources.csv"):
        assert header(common.config_dir(ST) / name) == ",".join(cols[name]), f"{name}: header differs from contract"
    for r in tx + tot:
        assert re.fullmatch(r"-?\d+\.\d\d", r["amount"]), f"amount {r['amount']!r}"
        assert re.fullmatch(r"20\d\d", r["fiscal_year"]), f"fiscal_year {r['fiscal_year']!r}"
    for r in tx:
        p, fy = r["posting_date"], int(r["fiscal_year"])
        assert re.fullmatch(r"\d{4}-\d\d-\d\d", p), f"posting_date {p!r}"
        assert f"{fy - 1}-07-01" <= p <= f"{fy}-06-30", f"{r['source_record_id']}: {p} outside state FY{fy}"

    # 1. Totals per source, agency and fiscal year; no $0 rows
    got = collections.Counter()
    for r in tot:
        assert r["source"] == "id_lgr", f"unexpected totals source {r['source']}"
        assert cents(r["amount"]) != 0, f"zero totals row {r}"
        got[(r["agency_id"], r["fiscal_year"])] += cents(r["amount"])
    want = expect_lgr()
    assert got == want, f"id_lgr totals differ: {sorted(set(got.items()) ^ set(want.items()))[:5]}"
    keys = collections.Counter((r["agency_id"], r["fiscal_year"]) for r in tot)
    assert not keys or max(keys.values()) == 1, "id_lgr: two totals rows for one agency and year"

    for r in tx:
        assert r["source"] == "id_state", f"unexpected transactions source {r['source']}"
    n_raw, dropped = check_state_lines(tx, rx)

    # 2. Agency ids
    ids = {a["id"] for a in agencies["agencies"]}
    for name, rows in (("transactions", tx), ("totals", tot), ("line_items", li)):
        missing = {r["agency_id"] for r in rows} - ids
        assert not missing, f"{name}: unknown agency ids {sorted(missing)[:5]}"
    missing = {r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")} - ids
    assert not missing, f"agency_sources.csv: unknown agency ids {sorted(missing)[:5]}"
    missing = {r["agency_id"] for r in common.read_data_csv(d / "grants.csv")} - ids
    assert not missing, f"grants.csv: unknown agency ids {sorted(missing)[:5]}"
    registry = {r["id"] for r in common.read_config(ST, "agencies.csv")}
    added = common.read_config(ST, "agencies_added.csv")
    assert all(r["id"].startswith("ID-S-") and r["kind"] for r in added), "agencies_added.csv: id or kind"
    assert not {r["id"] for r in added} & registry, "agencies_added.csv repeats a registry id"
    assert len({r["id"] for r in added}) == len(added), "agencies_added.csv: duplicate id"
    assert IDL in registry, "Idaho Department of Lands fire row missing from the registry"
    kinds = {a["id"]: a["kind"] for a in agencies["agencies"]}
    assert kinds[IDL] == "State fire agency", "IDL keeps kind 'State fire agency' (owner decision 4)"

    # 3. Unique source_record_id per source
    c = collections.Counter((r["source"], r["source_record_id"]) for r in tx)
    dup = [k for k, v in c.items() if v > 1]
    assert not dup, f"transactions: duplicate source_record_id {dup[:5]}"
    assert all(r["source_record_id"] for r in tx), "transactions: empty source_record_id"

    # 4. Payee names as published; only e-mail and bank account text cut
    for r in tx:
        assert r["payee_name"] != common.WITHHELD, "payee withheld under the old person rule"
        for col in ("payee_name", "description", "account", "category_published"):
            assert not any(p.search(r[col]) for p in rx), f"{col} holds redactable text: {r[col]!r}"

    # 5. Sources and coverage tiers
    sources = {r["source"]: r for r in common.read_config(ST, "sources.csv")}
    used = {r["source"] for r in tx} | {r["source"] for r in li} | {r["source"] for r in tot}
    assert used <= set(sources), f"sources missing from sources.csv: {used - set(sources)}"
    for s, r in sources.items():
        assert all(r[k] for k in cols["sources.csv"]), f"sources.csv {s}: empty column"
        assert r["fetched"] == common.latest_raw(ST, s).parent.parent.name, f"sources.csv {s}: fetched date"
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

    # 6. vendor map: payees classified the way pipeline/build.py classifies them (config/vendor_map.csv, then the
    #    vendor and keyword rules); proposals are folded into config/vendor_map.csv by merge_vendor_maps.py
    assert not (common.config_dir(ST) / "vendor_map_additions.csv").exists(), \
        "config/states/id/vendor_map_additions.csv: fold it into config/vendor_map.csv (merge_vendor_maps.py)"
    spend = collections.Counter()
    for r in tx:
        spend[common.norm(r["payee_name"])] += cents(r["amount"])
    cov = vendor_coverage.Classifier().coverage(spend)
    share = cov["share_real"]
    assert share >= 0.9, f"vendor map gives a real category to {share:.1%} of purchasing dollars, under 90%"

    by_source = collections.Counter()
    for r in tx + tot:
        by_source[r["source"]] += float(r["amount"])
    print(f"{ST}: ok ({len(tx)} payment lines from {n_raw} raw lines, {dropped} identical lines dropped; "
          f"{len(tot)} totals rows; " + ", ".join(f"{s} ${v:,.0f}" for s, v in sorted(by_source.items()))
          + f"; config/vendor_map.csv and the rules give a real category to {share:.1%} of "
          + f"${cov['purchasing'] / 100:,.0f} purchasing dollars (map {cov['by_map'] / cov['purchasing']:.1%}, rules "
          + f"{cov['by_rule'] / cov['purchasing']:.1%}); "
          + f"tiers {dict(sorted(agencies['coverage_counts'].items()))})")


if __name__ == "__main__":
    main()
