"""Recompute Texas vendor-data totals from the raw files and check data/states/tx/ matches.

    python3 tests/multistate/check_tx.py

Independent of the adapters' code: raw files are parsed here with their own filters and duplicate rules; only
config/states/tx/agency_sources.csv (the hand-reviewed attribution) is shared. Checks:
  - totals per source, agency and fiscal year (transactions, line items, published totals) match the raw files
  - every agency_id in the tables, agency_sources.csv and grants exists in agencies.json
  - no duplicate source_record_id within a source
  - no payee or item vendor looks like a private person unless withheld (names that config/vendor_map.csv or
    config/states/tx/vendor_map_additions.csv list as businesses are allowed, as the adapters allow them)
  - every table source is registered in sources.csv; coverage tiers agree with the rows present
"""
import collections
import csv
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "pipeline" / "sources"))
import common  # noqa: E402

ST = "TX"
CENT = 0.005


def cents(x):
    return round(float(x) * 100)


def links(source):
    return {r["source_entity_name"]: r["agency_id"] for r in common.read_config(ST, "agency_sources.csv") if r["source"] == source}


def expect_dir():
    """tx_dir: linked customers, FY2021+, drop a line already reported in an earlier month."""
    raw, link = common.latest_raw(ST, "tx_dir"), links("tx_dir")
    lines = []
    for name, month_field in (("archive_fy2021_2025.json.gz", "report_received_month"), ("current_fy2026.json.gz", "reporting_month")):
        for r in json.loads(common.read_gz(raw / name)):
            cust = " ".join(r.get("customer_name", "").split())
            fy = int(float(r["fiscal_year"]))
            if cust in link and fy >= 2021:
                sale = (name,) + tuple(sorted((k, str(v)) for k, v in r.items() if k not in (
                    ":id", "sales_fact_number", "report_received_month", "reporting_month", "purchase_month", "fiscal_year")))
                lines.append((sale, r.get(month_field, ""), link[cust], fy, r.get("purchase_amount")))
    first = {}
    for sale, month, *_ in lines:
        first[sale] = min(first.get(sale, month), month)
    out, n = collections.Counter(), 0
    for sale, month, aid, fy, amount in lines:
        if month == first[sale]:
            out[(aid, fy)] += cents(amount or 0)
            n += 1
    return out, n


def expect_houston():
    raw, aid = common.latest_raw(ST, "tx_houston"), next(iter(links("tx_houston").values()))
    manifest = {m["fiscal_year"]: m for m in json.loads(common.read_gz(raw / "manifest.json.gz"))}
    out, seen, n = collections.Counter(), set(), 0
    for path in sorted(raw.glob("checkbook-*-hfd.csv.gz")):
        rows = list(csv.reader(io.StringIO(common.read_gz(path).decode("utf-8"))))
        header, body = rows[0], rows[1:]
        fy = int(path.name.split("-")[1])
        assert manifest[fy]["hfd_lines"] == len(body), f"{path.name}: line count differs from manifest"
        i_dept, i_fy, i_amt = header.index("Department ID"), header.index("Fiscal Year"), header.index("Amount")
        for row in body:
            assert row[i_dept] == "1200" and int(row[i_fy]) == fy
            if tuple(row) in seen:
                continue
            seen.add(tuple(row))
            out[(aid, fy)] += cents(row[i_amt])
            n += 1
    return out, n


def expect_socrata(source, name, dept_field, dept, fy_field, amount_field):
    raw, aid = common.latest_raw(ST, source), next(iter(links(source).values()))
    out, seen, n = collections.Counter(), set(), 0
    for r in json.loads(common.read_gz(raw / name)):
        assert str(r[dept_field]) == dept
        k = tuple(sorted((f, v) for f, v in r.items() if f != ":id"))
        if k in seen:
            continue
        seen.add(k)
        out[(aid, int(r[fy_field]))] += cents(r[amount_field])
        n += 1
    return out, n


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
            amount = str(r.get("amount") or 0).replace(",", "")
            out[(row["agency_id"], int(float(r["fiscal_year"])))] += cents(amount)
    return out


def got(rows, source):
    out = collections.Counter()
    for r in rows:
        if r["source"] == source:
            out[(r["agency_id"], int(r["fiscal_year"]))] += cents(r["amount"])
    return out


def same(label, want, have):
    keys = set(want) | set(have)
    bad = {k: (want.get(k, 0) / 100, have.get(k, 0) / 100) for k in keys if want.get(k, 0) != have.get(k, 0)}
    assert not bad, f"{label}: totals differ (raw, normalized): {dict(sorted(bad.items())[:5])}"


def main():
    d = common.data_dir(ST)
    tx = common.read_data_csv(d / "transactions.csv.gz")
    li = common.read_data_csv(d / "line_items.csv.gz")
    tot = common.read_data_csv(d / "totals.csv")
    agencies = json.loads((d / "agencies.json").read_text())
    ids = {a["id"] for a in agencies["agencies"]}

    # 1. Totals per source, agency and fiscal year
    want, n = expect_dir()
    same("tx_dir transactions", want, got(tx, "tx_dir"))
    same("tx_dir line items", want, got(li, "tx_dir"))
    assert n == sum(r["source"] == "tx_dir" for r in tx) == sum(r["source"] == "tx_dir" for r in li), "tx_dir row counts"
    for source, (want, n) in {
        "tx_houston": expect_houston(),
        "tx_dallas": expect_socrata("tx_dallas", "dfd.json.gz", "dpt", "DFD", "fy", "chksubtot"),
        "tx_austin": expect_socrata("tx_austin", "fire.json.gz", "dept_cd", "83", "fy_dc", "amount"),
    }.items():
        same(source, want, got(tx, source))
        assert n == sum(r["source"] == source for r in tx), f"{source}: row count {n} raw vs normalized"
    same("tx_cpa totals", expect_cpa(), got(tot, "tx_cpa"))

    # 2. Agency ids
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

    # 3. Unique source_record_id per source
    for table, rows in (("transactions", tx), ("line_items", li)):
        c = collections.Counter((r["source"], r["source_record_id"]) for r in rows)
        dup = [k for k, v in c.items() if v > 1]
        assert not dup, f"{table}: duplicate source_record_id {dup[:5]}"
        assert all(r["source_record_id"] for r in rows), f"{table}: empty source_record_id"

    # 4. No private persons' names
    vm = {r["name_key"] for r in csv.DictReader(open(common.ROOT / "config" / "vendor_map.csv", encoding="utf-8"))
          if r["category"] != "individuals"}
    adds = {r["name_key"] for r in common.read_config(ST, "vendor_map_additions.csv") if r["category"] != "individuals"}
    withheld = {common.WITHHELD, "Payee name withheld"}
    names = collections.Counter(r["payee_name"] for r in tx) + collections.Counter(r["vendor"] for r in li)
    bad = []
    for p in names:
        if p in withheld or common.norm(p) in adds:
            continue
        if common.is_person(p) or (common.looks_like_person(p) and common.norm(p) not in vm):
            bad.append(p)
    assert not bad, f"{len(bad)} payee names look like persons, e.g. {bad[:3]}"
    add_rows = common.read_config(ST, "vendor_map_additions.csv")
    cats = {r["id"] for r in csv.DictReader(open(common.ROOT / "config" / "categories.csv", encoding="utf-8"))}
    assert all(r["category"] in cats for r in add_rows), "vendor_map_additions.csv: unknown category"
    assert len({r["name_key"] for r in add_rows}) == len(add_rows), "vendor_map_additions.csv: duplicate name_key"
    assert not {r["name_key"] for r in add_rows} & {r["name_key"] for r in csv.DictReader(open(common.ROOT / "config" / "vendor_map.csv", encoding="utf-8"))}, \
        "vendor_map_additions.csv repeats a vendor_map.csv key"

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
    for r in tx:
        by_source[r["source"]] += float(r["amount"])
    print(f"{ST}: ok ({len(tx)} payment lines, {len(li)} item lines, {len(tot)} totals rows; "
          + ", ".join(f"{s} ${v:,.0f}" for s, v in sorted(by_source.items()))
          + f"; tiers {dict(sorted(agencies['coverage_counts'].items()))})")


if __name__ == "__main__":
    main()
