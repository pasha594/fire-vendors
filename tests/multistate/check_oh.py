"""Recompute Ohio's normalized files from the raw files and check data/states/oh/ and config/states/oh/ match.

    python3 tests/multistate/check_oh.py

Independent of the adapters' code: reads the raw CSV pages with gzip and csv, applies the published filter (linked
department codes, fiscal year 2021 on) and compares totals per agency, source and fiscal year with
data/states/oh/transactions.csv.gz, and the raw files with the source's own server-side control totals.
Also checks agency ids, duplicate source_record_ids, person names, sources.csv and vendor_map_additions.csv.
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
PERSON_ACCOUNTS = {"Uniform And Other Allowance"}  # Cincinnati account paid to individual employees and retirees


def rows_of(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


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
    links = {r["source_entity_id"]: r["agency_id"] for r in config_rows("agency_sources.csv") if r["source"] == src}
    assert links, "no oh_cincinnati links"
    raw = []
    for p in sorted(d.glob("payments_*.csv.gz")):
        raw += rows_of(p)
    # the raw pages equal the source's own server-side totals per fiscal year and department
    control = json.loads(gzip.decompress((d / "control_totals.json.gz").read_bytes()))
    by = collections.defaultdict(lambda: [0, D(0)])
    for r in raw:
        by[(r["fiscal_year"], r["dept_code"])][0] += 1
        by[(r["fiscal_year"], r["dept_code"])][1] += D(r["amount"])
    assert {(c["fiscal_year"], c["dept_code"]): (int(c["n"]), D(c["amount"]).quantize(D("0.01"))) for c in control} \
        == {k: (n, a.quantize(D("0.01"))) for k, (n, a) in by.items()}, "raw pages differ from control_totals.json"
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
        lines[f"{r['trans_id']}-{r['trans_line_no']}"] = r
    return out, lines


def main():
    tx = common.read_data_csv(common.data_dir(ST) / "transactions.csv.gz")
    with gzip.open(common.data_dir(ST) / "transactions.csv.gz", "rt", encoding="utf-8") as f:
        assert f.readline().strip().split(",") == common.TABLES["transactions.csv.gz"], "transactions header"
    agencies = json.loads((common.data_dir(ST) / "agencies.json").read_text())
    ids = {a["id"] for a in agencies["agencies"]}
    sources = {r["source"]: r for r in config_rows("sources.csv")}

    # 1. totals per agency, source and fiscal year, recomputed from raw
    got = collections.defaultdict(lambda: [0, D(0)])
    for r in tx:
        got[(r["agency_id"], r["source"], r["fiscal_year"])][0] += 1
        got[(r["agency_id"], r["source"], r["fiscal_year"])][1] += D(r["amount"])
        assert re.fullmatch(r"-?\d+\.\d\d", r["amount"]), f"amount format: {r}"
        assert int(r["fiscal_year"]) >= FIRST_FY, f"fiscal year before {FIRST_FY}: {r}"
        assert not r["posting_date"] or re.fullmatch(r"\d{4}-\d\d-\d\d", r["posting_date"]), f"date: {r}"
    exp_cin, raw_lines = expected_cincinnati()
    expect = {(a, "oh_cincinnati", fy): v for (a, fy), v in exp_cin.items()}
    assert set(got) == set(expect), f"agency/source/year keys differ: {sorted(set(got) ^ set(expect))[:5]}"
    for k in sorted(expect):
        assert got[k][0] == expect[k][0] and got[k][1] == expect[k][1], f"{k}: got {got[k]}, raw {expect[k]}"
    assert {s for _, s, _ in got} <= set(sources), "a source with rows is missing from sources.csv"

    # 2. agency ids and coverage
    assert {a for a, _, _ in got} <= ids, "transactions for agencies not in agencies.json"
    links = config_rows("agency_sources.csv")
    assert all(r["agency_id"] in ids and re.fullmatch(r"0[1-9]|1[0-2]", r["fy_start"]) for r in links), "agency_sources"
    with_rows = {a for a, _, _ in got}
    for a in agencies["agencies"]:
        if a["id"] in with_rows:
            assert a["coverage"] == 1, f"{a['id']} has payee rows but coverage {a['coverage']}"
        else:
            assert a["coverage"] in (3, 4), f"{a['id']} has no payee rows but coverage {a['coverage']}"
    assert agencies["coverage_counts"]["1"] == len(with_rows)

    # 3. no duplicate source_record_id per source; every id traces back to a raw line
    ids_by_source = collections.Counter((r["source"], r["source_record_id"]) for r in tx)
    dupes = [k for k, n in ids_by_source.items() if n > 1]
    assert not dupes, f"duplicate source_record_id: {dupes[:5]}"
    for r in tx:
        if r["source"] == "oh_cincinnati":
            raw = raw_lines[r["source_record_id"]]
            assert D(raw["amount"]) == D(r["amount"]), f"amount differs from raw for {r['source_record_id']}"

    # 4. no private person's name: is_person names are always withheld; looks_like_person names only when no
    #    vendor_map / vendor_map_additions row claims them as a business (the rule common.withhold_person uses)
    claimed = {r["name_key"] for r in config_rows("vendor_map.csv", state=False) if r["category"] != "individuals"} \
        | {r["name_key"] for r in config_rows("vendor_map_additions.csv") if r["category"] != "individuals"}
    withheld = {common.WITHHELD, "Payee name withheld"}
    for r in tx:
        name = r["payee_name"]
        if name in withheld:
            continue
        assert not common.is_person(name), f"person-like payee published: {name!r}"
        assert not common.looks_like_person(name) or common.norm(name) in claimed, f"person-like payee: {name!r}"
        if r["source"] == "oh_cincinnati":
            raw = raw_lines[r["source_record_id"]]
            assert raw["exp_acct_cat_desc"] not in PERSON_ACCOUNTS, f"allowance payee published: {name!r}"
            assert not common.is_person(raw["vendor_name"]), f"raw person name published: {name!r}"

    # 5. vendor_map_additions: valid categories, unique keys, and >= 90% of purchasing dollars covered
    categories = {c["id"]: c["purchasing"] == "yes" for c in config_rows("categories.csv", state=False)}
    vendor_map = {r["name_key"]: r["category"] for r in config_rows("vendor_map.csv", state=False)}
    additions = config_rows("vendor_map_additions.csv")
    keys = [r["name_key"] for r in additions]
    assert len(keys) == len(set(keys)), "duplicate name_key in vendor_map_additions.csv"
    assert all(r["category"] in categories for r in additions), "unknown category in vendor_map_additions.csv"
    assert all(k == common.norm(k) for k in keys), "name_key is not common.norm(name)"
    add = {r["name_key"]: r["category"] for r in additions}
    purchasing, covered = D(0), D(0)
    for r in tx:
        key = common.norm(r["payee_name"])
        if r["payee_name"] in withheld:
            cat = "individuals"
        else:
            cat = add.get(key) or vendor_map.get(key) or "unclassified"  # unmapped counts as purchasing
        if categories[cat]:
            purchasing += D(r["amount"])
            covered += D(r["amount"]) if key in add else 0
    share = covered / purchasing if purchasing else D(1)
    assert share >= D("0.9"), f"vendor_map_additions covers {share:.1%} of purchasing dollars"

    # 6. raw files stay small
    for p in (ROOT / "raw").glob("*/oh/**/*.gz"):
        assert p.stat().st_size < 50 * 2 ** 20, f"raw file over 50 MB: {p}"

    total = sum(v[1] for v in got.values())
    print(f"{ST}: ok ({len(tx)} transaction lines, ${total:,.2f}, {len(with_rows)} agencies at tier 1; "
          f"vendor_map_additions covers {share:.1%} of ${purchasing:,.0f} purchasing dollars)")


if __name__ == "__main__":
    main()
