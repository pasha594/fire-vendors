"""Recompute California vendor-data totals from the raw files and check data/states/ca/ matches.

    python3 tests/multistate/check_ca.py

Independent of the adapters' code paths: every raw file is parsed here with its own filters and its own duplicate
rules (written from the rules in docs/sources/ca.md, not imported). Shared with the adapters are only
config/states/ca/agency_sources.csv (the hand-reviewed attribution), config/payee_name_redactions.csv (the owner's
redaction rule) and common's file helpers and norm(). Checks:
  1. per source, agency and fiscal year: dollars (to the cent) and, for line-level sources, line counts equal the
     raw files after the source's duplicate rule; for line-level sources the multiset of (fiscal year, payee,
     amount) lines is equal too; for ca_fiscal (rows summed per voucher) dollars per fiscal year and payee are equal
  2. payee names are shown as published (owner decision of 2026-10-06): every published payee is a raw payee
     name (whitespace collapsed), or "Payee name withheld" where the raw name matches a redaction pattern; the
     old person marker never appears; no published payee matches a redaction pattern. Names that look like private
     persons (common.is_person / looks_like_person) and email addresses in descriptions are counted and reported
  3. every agency_id in the tables and agency_sources.csv exists in agencies.json; coverage tiers agree with the
     rows present; no agency without rows has a tier above 4; no zero-dollar totals rows
  4. no duplicate and no empty source_record_id per source; tier-2 line items equal their transactions rows
  5. every source in a table is registered in sources.csv with the years present in the data
  6. vendor_map_additions.csv: spend and agency counts equal the transactions, categories are valid ids, no key
     repeats config/vendor_map.csv, and the mapped payees cover at least 90% of purchasing dollars
  7. raw files: each under 50 MB, California under 150 MB, every source folder has a sample of at most 100 rows
"""
import collections
import csv
import gzip
import io
import json
import pathlib
import re
import sys
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "pipeline" / "sources"))
import common  # noqa: E402

ST = "CA"
OLD_MARKER = "Individual (name withheld)"
CUT = "Payee name withheld"
REDACT = [re.compile(r["pattern"], re.I) for r in csv.DictReader(open(common.ROOT / "config" / "payee_name_redactions.csv",
                                                                       encoding="utf-8"))]
LINE_SOURCES = ["ca_sf", "ca_la", "ca_riverside_county", "ca_corona", "ca_moreno_valley", "ca_scprs"]


def cents(x):
    return int((Decimal(str(x or "0")) * 100).to_integral_value())


def published(name):
    name = " ".join((name or "").split())
    return CUT if any(rx.search(name) for rx in REDACT) else name


def raw_json(source, name):
    return json.loads(gzip.decompress((common.latest_raw(ST, source) / name).read_bytes()))


def links(source, key="source_entity_name"):
    out = {r[key]: r["agency_id"] for r in common.read_config(ST, "agency_sources.csv") if r["source"] == source}
    assert out, f"no agency_sources.csv rows for {source}"
    return out


def drop_exact(rows):
    """Keep one of each line identical in every published column (the portal row id ':id' aside)."""
    seen, out = set(), []
    for r in rows:
        key = json.dumps({k: v for k, v in r.items() if k != ":id"}, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def drop_reloads(rows, doc):
    """A document (invoice or PO) whose every distinct line occurs the same number k > 1 of times was loaded k times:
    keep each line once. Identical lines in any other document are separate charges and are all kept."""
    by_doc = collections.defaultdict(collections.Counter)
    for r in rows:
        by_doc[doc(r)][json.dumps({k: v for k, v in r.items() if k != ":id"}, sort_keys=True)] += 1
    out = []
    for lines in by_doc.values():
        ks = set(lines.values())
        once = len(ks) == 1 and min(ks) > 1
        for line, n in lines.items():
            out += [json.loads(line)] * (1 if once else n)
    return out


# --- 1. expected lines per source, from raw -----------------------------------------------------------------

def expect_sf():
    agency = links("ca_sf", "source_entity_id")["FIR"]
    raw = raw_json("ca_sf", "fir.json.gz")
    control = raw_json("ca_sf", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control), "ca_sf: raw rows differ from control"
    return [(agency, str(int(r["fiscal_year"])), published(r["vendor"]), cents(r["vouchers_paid"]))
            for r in drop_exact(raw) if r["department_code"] == "FIR" and cents(r.get("vouchers_paid")) != 0]


def expect_la():
    agency = links("ca_la")["FIRE"]
    raw = raw_json("ca_la", "fire.json.gz")
    control = raw_json("ca_la", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control), "ca_la: raw rows differ from control"
    return [(agency, str(int(r["fiscal_year"])), published(r.get("vendor_name")), cents(r["dollar_amount"]))
            for r in drop_exact(raw) if r["department_name"] == "FIRE" and r.get("dollar_amount") not in (None, "")]


def expect_riverside():
    agency = links("ca_riverside_county")["Fire Protection"]
    raw = raw_json("ca_riverside_county", "fire.json.gz")
    control = raw_json("ca_riverside_county", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control if str(c["has_vendor"]).lower() == "true")
    rows = drop_reloads([r for r in raw if r["department"] == "Fire Protection" and r.get("vendor_name")],
                        lambda r: r.get("invoice_id"))
    return [(agency, str(int(r["fiscal_year"])), published(r["vendor_name"]), cents(r["amount"])) for r in rows]


def expect_corona():
    agency = links("ca_corona", "source_entity_id")["30"]
    raw = raw_json("ca_corona", "fire.json.gz")
    control = raw_json("ca_corona", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control), "ca_corona: raw rows differ from control"
    rows = drop_reloads([r for r in raw if r["department_code"] == "30"],
                        lambda r: (r.get("payment_id"), r.get("invoice_id")))
    return [(agency, str(int(r["fiscal_year"])), published(r["vendor"]), cents(r["amount"])) for r in rows]


def expect_moreno_valley():
    link = links("ca_moreno_valley")
    raw = raw_json("ca_moreno_valley", "fire.json.gz")
    control = raw_json("ca_moreno_valley", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control), "ca_moreno_valley: raw rows differ from control"
    assert {c["department"] for c in control} == set(link), "ca_moreno_valley: a fire-named department is not linked"
    return [(link[r["department"]], str(int(r["fiscal_year"])), published(r.get("vendor")), cents(r["amount"]))
            for r in drop_exact(raw)]


def scprs_money(s):
    s = (s or "").replace("$", "").replace(",", "").strip()
    return -cents(s.strip("()")) if s.startswith("(") else cents(s or "0")


def expect_scprs():
    link = links("ca_scprs")
    d = common.latest_raw(ST, "ca_scprs")
    manifest = json.loads(gzip.decompress((d / "manifest.json.gz").read_bytes()))
    rows = list(csv.DictReader(io.StringIO(gzip.decompress((d / "calfire.csv.gz").read_bytes()).decode("utf-8"))))
    assert len(rows) == manifest["kept_rows"], "ca_scprs: raw rows differ from manifest"
    dept = manifest["kept_department"]
    assert all(r["Department Name"] == dept for r in rows) and dept in link
    rows = drop_reloads(rows, lambda r: (r["Purchase Order Number"], r["Fiscal Year"]))
    return [(link[dept], r["Fiscal Year"][5:], published(r["Supplier Name"]), scprs_money(r["Total Price"]))
            for r in rows if scprs_money(r["Total Price"]) != 0]


def expect_fiscal():
    """{(agency, fy, payee): cents} from the Open FI$Cal files, exact duplicate lines dropped within a file."""
    agency = links("ca_fiscal", "source_entity_id")["3540"]
    d = common.latest_raw(ST, "ca_fiscal")
    manifest = json.loads(gzip.decompress((d / "manifest.json.gz").read_bytes()))
    out = collections.Counter()
    for entry in manifest:
        reader = csv.reader(io.StringIO(gzip.decompress((d / (entry["file"] + ".gz")).read_bytes()).decode("utf-8-sig")))
        header = next(reader)
        ix = {c: i for i, c in enumerate(header)}
        seen, n, total = set(), 0, 0
        for r in reader:
            n += 1
            total += cents(r[ix["monetary_amount"]])
            key = "\x1f".join(r)
            if key in seen:
                continue
            seen.add(key)
            assert r[ix["business_unit"]] == "3540", r
            fy = str(int(r[ix["fiscal_year_begin"]]) + 1)
            assert fy == str(entry["fiscal_year"]), (entry["file"], fy)
            out[(agency, fy, published(r[ix["VENDOR_NAME"]]))] += cents(r[ix["monetary_amount"]])
        assert n == entry["rows"] and total == cents(entry["dollars"]), f"ca_fiscal {entry['file']}: differs from manifest"
    return out


def expect_sco(source, name_field, year_field):
    link = links(source)
    raw = raw_json(source, "fire.json.gz")
    ids = collections.Counter(r.get("rownumber") or r.get("row_number") for r in raw)
    assert max(ids.values()) == 1, f"{source}: a row number repeats"
    out = collections.Counter()
    for r in raw:
        if r[name_field] in link and r.get("value") not in (None, ""):
            out[(link[r[name_field]], str(int(r[year_field])))] += cents(r["value"])
    assert set(link) <= {r[name_field] for r in raw}, f"{source}: an agency_sources.csv row matches no raw entity"
    if source == "ca_sco_districts":
        fire = {r[name_field] for r in raw if r.get("activity") == "Fire Protection"}
        assert fire <= set(link), f"ca_sco_districts: Fire Protection entities not linked: {sorted(fire - set(link))[:5]}"
    return {k: v for k, v in out.items() if v}


# --- checks ---------------------------------------------------------------------------------------------------

def main():
    d = common.data_dir(ST)
    tx = common.read_data_csv(d / "transactions.csv.gz")
    li = common.read_data_csv(d / "line_items.csv.gz")
    tot = common.read_data_csv(d / "totals.csv")
    agencies = json.loads((d / "agencies.json").read_text(encoding="utf-8"))
    sources = {s["source"]: s for s in common.read_config(ST, "sources.csv")}
    report = []

    # 1. line-level sources: lines, dollars and payees per agency and fiscal year
    expect = {"ca_sf": expect_sf, "ca_la": expect_la, "ca_riverside_county": expect_riverside,
              "ca_corona": expect_corona, "ca_moreno_valley": expect_moreno_valley, "ca_scprs": expect_scprs}
    for source, fn in expect.items():
        want = collections.Counter(fn())
        got = collections.Counter((r["agency_id"], r["fiscal_year"], r["payee_name"], cents(r["amount"]))
                                  for r in tx if r["source"] == source)
        assert got == want, (f"{source}: lines differ from raw: {sorted((want - got).items())[:3]} missing, "
                             f"{sorted((got - want).items())[:3]} extra")
        per = collections.Counter()
        for (a, fy, _, c), n in want.items():
            per[(a, fy)] += c * n
        report.append(f"{source}: {sum(want.values())} lines, ${sum(per.values()) / 100:,.2f}, "
                      f"{len({a for a, _ in per})} agencies, FY{min(fy for _, fy in per)}-FY{max(fy for _, fy in per)}")

    # ca_fiscal: summed rows, so dollars per fiscal year and payee
    want = {k: v for k, v in expect_fiscal().items() if v}
    got = collections.Counter()
    for r in tx:
        if r["source"] == "ca_fiscal":
            got[(r["agency_id"], r["fiscal_year"], r["payee_name"])] += cents(r["amount"])
    got = {k: v for k, v in got.items() if v}
    assert got == want, f"ca_fiscal: payee dollars differ: {sorted(set(got.items()) ^ set(want.items()))[:4]}"
    assert all(cents(r["amount"]) != 0 for r in tx if r["source"] == "ca_fiscal"), "ca_fiscal: a $0 row"
    years = sorted({k[1] for k in want})
    report.append(f"ca_fiscal: {sum(r['source'] == 'ca_fiscal' for r in tx)} rows, ${sum(want.values()) / 100:,.2f}, "
                  f"FY{years[0]}-FY{years[-1]}")

    # tier 3 totals
    for source, name_field, year_field in [("ca_sco_districts", "entityname", "fiscalyear"),
                                           ("ca_sco_cities", "entity_name", "fiscal_year")]:
        want = expect_sco(source, name_field, year_field)
        got = collections.Counter()
        for r in tot:
            if r["source"] == source:
                assert cents(r["amount"]) != 0, f"{source}: zero totals row {r}"
                got[(r["agency_id"], r["fiscal_year"])] += cents(r["amount"])
        got = {k: v for k, v in got.items() if v}
        assert got == want, f"{source}: totals differ: {sorted(set(got.items()) ^ set(want.items()))[:4]}"
        report.append(f"{source}: {len({a for a, _ in want})} agencies, ${sum(want.values()) / 100:,.0f}")
    both = ({r["agency_id"] for r in tot if r["source"] == "ca_sco_districts"}
            & {r["agency_id"] for r in tot if r["source"] == "ca_sco_cities"})
    assert not both, f"agencies with both a district and a city filing: {sorted(both)[:5]}"
    assert {r["source"] for r in tx} == set(expect) | {"ca_fiscal"}, f"unexpected sources {sorted({r['source'] for r in tx})}"
    assert {r["source"] for r in tot} == {"ca_sco_districts", "ca_sco_cities"}
    assert {r["source"] for r in li} == {"ca_scprs"}

    # 2. payee names as published
    email = re.compile(r"[\w.+-]+@[A-Za-z][\w-]*\.[A-Za-z]{2,}")
    emails = 0
    for r in tx + li:
        name = r.get("payee_name", r.get("vendor"))
        assert name != OLD_MARKER, f"payee withheld by the old person rule: {r}"
        if name != CUT:
            assert not any(rx.search(name) for rx in REDACT), f"redaction pattern in a published payee: {r}"
        emails += any(email.search(r.get(f) or "") for f in ("description", "account"))
    person_like = collections.Counter(r["source"] for r in tx if common.is_person(r["payee_name"])
                                      or common.looks_like_person(r["payee_name"]))
    cut = collections.Counter(r["source"] for r in tx if r["payee_name"] == CUT)
    report.append(f"payees: published as in the source; {sum(cut.values())} lines cut by the redaction rule; "
                  f"{sum(person_like.values())} lines have person-shaped payee names (shown, owner decision) "
                  f"{dict(sorted(person_like.items()))}; {emails} lines carry an email address in description or account")

    # 3. agencies and coverage
    ids = {a["id"] for a in agencies["agencies"]}
    for table, rows in [("transactions", tx), ("line_items", li), ("totals", tot)]:
        missing = {r["agency_id"] for r in rows} - ids
        assert not missing, f"{table}: agency ids not in agencies.json: {sorted(missing)[:5]}"
    missing = {r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")} - ids
    assert not missing, f"agency_sources.csv: agency ids not in agencies.json: {sorted(missing)[:5]}"
    best = collections.defaultdict(lambda: 4)
    for r in tx:
        best[r["agency_id"]] = min(best[r["agency_id"]], int(sources[r["source"]]["tier"]))
    for r in li:
        best[r["agency_id"]] = min(best[r["agency_id"]], 2)
    for r in tot:
        best[r["agency_id"]] = min(best[r["agency_id"]], 3)
    for a in agencies["agencies"]:
        assert a["coverage"] == best[a["id"]], f"{a['id']}: coverage {a['coverage']}, rows say {best[a['id']]}"
    counts = collections.Counter(a["coverage"] for a in agencies["agencies"])
    assert agencies["coverage_counts"] == {str(t): counts[t] for t in (1, 2, 3, 4)}
    kinds = {a["id"]: a["kind"] for a in agencies["agencies"]}
    assert kinds["CA-00555"] in ("State government", "State fire agency"), "CAL FIRE (CA-00555) is not a state row"

    # 4. record ids
    for table, rows in [("transactions", tx), ("line_items", li)]:
        ids_ = collections.Counter((r["source"], r["source_record_id"]) for r in rows)
        dup = [k for k, n in ids_.items() if n > 1]
        assert not dup, f"{table}: duplicate source_record_id {dup[:3]}"
        assert all(r["source_record_id"] for r in rows), f"{table}: empty source_record_id"
    t2 = {(r["source_record_id"], r["fiscal_year"], r["payee_name"], r["amount"]) for r in tx if r["source"] == "ca_scprs"}
    l2 = {(r["source_record_id"], r["fiscal_year"], r["vendor"], r["amount"]) for r in li}
    assert t2 == l2, "ca_scprs: line items and transactions differ"

    # 5. sources.csv
    for name, rows, field in [("transactions", tx, "fiscal_year"), ("totals", tot, "fiscal_year")]:
        for source in {r["source"] for r in rows}:
            assert source in sources, f"{source} not in sources.csv"
            ys = sorted({int(r[field]) for r in rows if r["source"] == source})
            assert sources[source]["years"] == f"{ys[0]}-{ys[-1]}", f"{source}: years {sources[source]['years']} vs {ys}"

    # 6. vendor_map_additions.csv
    cats = {c["id"]: c["purchasing"] == "yes" for c in csv.DictReader(open(common.ROOT / "config/categories.csv"))}
    vm = {r["name_key"]: r["category"] for r in csv.DictReader(open(common.ROOT / "config/vendor_map.csv"))}
    va = common.read_config(ST, "vendor_map_additions.csv")
    spend, who = collections.Counter(), collections.defaultdict(set)
    for r in tx:
        k = common.norm(r["payee_name"])
        spend[k] += cents(r["amount"])
        who[k].add(r["agency_id"])
    keys = [r["name_key"] for r in va]
    assert len(keys) == len(set(keys)) and keys == sorted(keys), "vendor_map_additions.csv: keys repeat or unsorted"
    for r in va:
        assert r["category"] in cats, f"unknown category {r}"
        assert r["name_key"] not in vm, f"key already in config/vendor_map.csv: {r['name_key']}"
        assert r["confidence"] in ("high", "medium", "low"), r
        assert cents(r["spend"]) == spend[r["name_key"]] and int(r["agencies"]) == len(who[r["name_key"]]), \
            f"vendor_map_additions.csv: spend or agencies stale for {r['name_key']}"
    mapped = {**vm, **{r["name_key"]: r["category"] for r in va}}
    purchasing = covered = 0
    for k, v in spend.items():
        if v <= 0 or (k in mapped and not cats[mapped[k]]):
            continue
        purchasing += v
        covered += v if k in mapped else 0
    share = covered / purchasing
    assert share >= 0.90, f"vendor map covers {share:.1%} of purchasing dollars"
    report.append(f"vendor map: {len(va)} additions; {share:.1%} of ${purchasing / 100:,.0f} purchasing dollars mapped")

    # 7. raw files
    total = 0
    for folder in sorted({p.parent for p in (common.ROOT / "raw").glob("*/ca/*/*")}):
        files = list(folder.iterdir())
        for f in files:
            assert f.stat().st_size < 50e6, f"{f}: over 50 MB"
            total += f.stat().st_size
        if folder.name in ("usfa", "openfema"):
            continue
        samples = [f for f in files if f.name.startswith("sample") or f.name.endswith("_sample.json.gz")]
        assert samples, f"{folder}: no sample file"
        for f in samples:
            body = gzip.decompress(f.read_bytes())
            n = len(json.loads(body).get("features", [])) if body[:1] == b"{" else \
                len(json.loads(body)) if body[:1] == b"[" else \
                sum(1 for _ in csv.reader(io.StringIO(body.decode("utf-8-sig", errors="replace")))) - 1
            assert n <= 100, f"{f}: {n} rows in a sample"
    assert total < 150e6, f"California raw files are {total / 1e6:.0f} MB"
    report.append(f"raw: {total / 1e6:.1f} MB")

    print("CA: ok")
    for line in report:
        print("  " + line)


if __name__ == "__main__":
    main()
