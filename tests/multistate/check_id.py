"""Recompute Idaho vendor-data totals from the raw files and check data/states/id/ matches.

    python3 tests/multistate/check_id.py

Independent of the adapters' code paths: raw files are parsed here with their own filters and duplicate rules;
shared with the adapters are config/states/id/agency_sources.csv (the hand-reviewed attribution) and, for the
person-name check, the business-word rule of id_state.payee (BUSINESS, a rule, not a computation). Checks:
  - id_lgr: one total per agency and fiscal year equal to the district's filed actual expenditures, every
    county copy of a multi-county district equal, no row for a null or zero actual
  - id_state: fetched lines per year equal the control file's non-Personnel line count; payment-category dollars
    and lines per fiscal year equal the transactions rows
  - every agency_id in the tables, agency_sources.csv and grants exists in agencies.json
  - no duplicate source_record_id within a source; no empty one
  - no payee looks like a private person unless withheld (names that config/vendor_map.csv or
    config/states/id/vendor_map_additions.csv list as businesses, or that carry a business word, are allowed)
  - every table source is registered in sources.csv; coverage tiers agree with the rows present
"""
import collections
import csv
import gzip
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "pipeline" / "sources"))
import common  # noqa: E402
import id_state  # noqa: E402  (BUSINESS, PCARD and FULL_NAME only)

ST = "ID"
NOT_PAYMENTS = {"Encumbrances", "GAAP Expenses", "Loss", "Operating Transfers Out", "Other Financing Uses", "Personnel"}


def cents(x):
    return round(float(x) * 100)


def links(source):
    return {r["source_entity_id"]: r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")
            if r["source"] == source}


def expect_lgr():
    """{(agency, fy): cents} from raw/<date>/id/id_lgr/fire_districts_fy*.json.gz."""
    raw, link = common.latest_raw(ST, "id_lgr"), links("id_lgr")
    seen, out = {}, collections.Counter()
    for path in sorted(raw.glob("fire_districts_fy*.json.gz")):
        fy = re.search(r"fy(\d{4})", path.name).group(1)
        for county, recs in json.loads(gzip.decompress(path.read_bytes())).items():
            for r in recs:
                key = (str(r["EntityID"]), fy)
                if key in seen:
                    assert seen[key] == r["Actual_Expenditures"], f"county copies disagree for {key}"
                    continue
                seen[key] = r["Actual_Expenditures"]
    for (eid, fy), actual in seen.items():
        assert eid in link, f"id_lgr: entity {eid} has no agency_sources.csv row"
        if actual:
            out[(link[eid], fy)] += round(actual * 100)
    return out


def expect_state():
    """{(agency, fy): [cents, lines]} from raw/<date>/id/id_state/lines_fy*.json.gz, checked against control."""
    raw = common.latest_raw(ST, "id_state")
    agency = links("id_state")["320-07H"]
    control = json.loads(gzip.decompress((raw / "control.json.gz").read_bytes()))
    out = collections.defaultdict(lambda: [0, 0])
    for path in sorted(raw.glob("lines_fy*.json.gz")):
        fy = re.search(r"fy(\d{4})", path.name).group(1)
        d = json.loads(gzip.decompress(path.read_bytes()))
        col = {c: i for i, c in enumerate(d["columns"])}
        expected = sum(v["lines"] for k, v in control[fy].items() if k != "Personnel")
        assert len(d["rows"]) == expected, f"id_state FY{fy}: {len(d['rows'])} lines, control {expected}"
        assert len({json.dumps(r) for r in d["rows"]}) == len(d["rows"]), f"id_state FY{fy}: a line repeats"
        for r in d["rows"]:
            assert r[col["agency_code_function_code"]] == "320-07H" and r[col["account_type"]] == "Expense"
            if r[col["account_category_0"]] in NOT_PAYMENTS:
                continue
            k = (agency, r[col["fiscal_year"]])
            out[k][0] += round((r[col["amount"]] or 0) * 100)
            out[k][1] += 1
    return out


def main():
    d = common.data_dir(ST)
    tx = common.read_data_csv(d / "transactions.csv.gz") if (d / "transactions.csv.gz").exists() else []
    tot = common.read_data_csv(d / "totals.csv") if (d / "totals.csv").exists() else []
    li = common.read_data_csv(d / "line_items.csv.gz") if (d / "line_items.csv.gz").exists() else []
    agencies = json.loads((d / "agencies.json").read_text(encoding="utf-8"))

    # 1. Totals per source, agency and fiscal year
    got = collections.Counter()
    for r in tot:
        assert r["source"] == "id_lgr", f"unexpected totals source {r['source']}"
        assert cents(r["amount"]) != 0, f"zero totals row {r}"
        got[(r["agency_id"], r["fiscal_year"])] += cents(r["amount"])
    want = expect_lgr()
    assert got == want, f"id_lgr totals differ: {sorted(set(got.items()) ^ set(want.items()))[:5]}"
    keys = collections.Counter((r["agency_id"], r["fiscal_year"]) for r in tot)
    assert max(keys.values()) == 1, "id_lgr: two totals rows for one agency and year"

    got = collections.defaultdict(lambda: [0, 0])
    for r in tx:
        assert r["source"] == "id_state", f"unexpected transactions source {r['source']}"
        k = (r["agency_id"], r["fiscal_year"])
        got[k][0] += cents(r["amount"])
        got[k][1] += 1
    want = expect_state()
    assert dict(got) == dict(want), f"id_state differs: {sorted(set(map(str, got.items())) ^ set(map(str, want.items())))[:5]}"

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
    added = [r["id"] for r in common.read_config(ST, "agencies_added.csv")]
    assert all(i.startswith("ID-S-") for i in added) and not set(added) & registry, "agencies_added.csv ids"
    assert len(set(added)) == len(added), "agencies_added.csv: duplicate id"

    # 3. Unique source_record_id per source
    c = collections.Counter((r["source"], r["source_record_id"]) for r in tx)
    dup = [k for k, v in c.items() if v > 1]
    assert not dup, f"transactions: duplicate source_record_id {dup[:5]}"
    assert all(r["source_record_id"] for r in tx), "transactions: empty source_record_id"

    # 4. No private persons' names
    vm_rows = list(csv.DictReader(open(common.ROOT / "config" / "vendor_map.csv", encoding="utf-8")))
    add_rows = common.read_config(ST, "vendor_map_additions.csv")
    claimed = {r["name_key"] for r in vm_rows + add_rows if r["category"] != "individuals"}
    withheld = {common.WITHHELD, "Payee name withheld", ""}
    bad = []
    for p in collections.Counter(r["payee_name"] for r in tx):
        if p in withheld:
            continue
        base = id_state.PCARD.sub("", p)
        if common.norm(p) in claimed or common.norm(base) in claimed or id_state.BUSINESS.search(base):
            continue
        if common.is_person(base) or common.looks_like_person(base) or id_state.FULL_NAME.match(base):
            bad.append(p)
    assert not bad, f"{len(bad)} payee names look like persons, e.g. {bad[:3]}"
    for r in add_rows:
        assert common.norm(r["vendor"]) and r["name_key"] == r["name_key"].strip(), r
    cats = {r["id"]: r for r in csv.DictReader(open(common.ROOT / "config" / "categories.csv", encoding="utf-8"))}
    assert all(r["category"] in cats for r in add_rows), "vendor_map_additions.csv: unknown category"
    assert len({r["name_key"] for r in add_rows}) == len(add_rows), "vendor_map_additions.csv: duplicate name_key"
    assert not {r["name_key"] for r in add_rows} & {r["name_key"] for r in vm_rows}, \
        "vendor_map_additions.csv repeats a vendor_map.csv key"
    published = {common.norm(r["payee_name"]) for r in tx}
    assert all(r["name_key"] in published for r in add_rows), "vendor_map_additions.csv: key not among published payees"

    # 5. Sources and coverage tiers
    sources = {r["source"]: r for r in common.read_config(ST, "sources.csv")}
    used = {r["source"] for r in tx} | {r["source"] for r in li} | {r["source"] for r in tot}
    assert used <= set(sources), f"sources missing from sources.csv: {used - set(sources)}"
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

    by_source = collections.Counter()
    for r in tx + tot:
        by_source[r["source"]] += float(r["amount"])
    print(f"{ST}: ok ({len(tx)} payment lines, {len(tot)} totals rows; "
          + ", ".join(f"{s} ${v:,.0f}" for s, v in sorted(by_source.items()))
          + f"; tiers {dict(sorted(agencies['coverage_counts'].items()))})")


if __name__ == "__main__":
    main()
