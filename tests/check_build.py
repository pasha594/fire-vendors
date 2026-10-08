"""Checks of the multi-state build output (pipeline/build.py). Run after a build:

    python3 tests/check_build.py              # check data/ as built
    python3 tests/check_build.py --base REF   # check 1 against another commit that has data/data.json
    python3 tests/check_build.py --base none  # skip check 1 (after Utah's inputs change on purpose)

1. Utah unchanged: Utah's files from before the multi-state split (data/data.json and data/payments.json, read with
   git show from --base REF; default de1e5cf, main before the multi-state page) against data/index.json,
   data/ut.json and data/ut-payments.json after mapping ids (agency 359 = 'UT-359', vendor index = vendor id, payee
   name index = text): agencies apart from the added fields, rows in the same order, vendors (id, name, category,
   method, NERIS, payee-name sets), payments and descriptions, grants, categories and meta (built dates aside).
2. Utah against the raw file: per agency, the net of its rows equals its raw transaction lines (lines left out by
   build.py's reupload_copies and police_only rules excluded), to half a cent per row.
3. Other states against data/states/<st>/ (recomputed here from the normalized files):
   - rows: per agency, fiscal year and payee name as shown, the rows' net equals the transaction lines in the
     state's years (config/states.csv); line counts per agency equal agency.lines;
   - item lines: one per line_items.csv.gz line, in file order, with its agency, year, date, brand, product type,
     description, quantity, unit price and amount; each in-year item's agency, vendor, year and category is a row;
   - totals rows equal totals.csv in the years; budget per agency and year is their sum;
   - grants equal grants.csv; payments are lines of $1,000 or more in purchasing categories and the years, each
     one its own transaction line (agency, year, date, payee name, amount, description), and none is missing for
     payees whose rows are in one purchasing category (fewer only by credits of the same amount to the vendor).
4. Coverage: every agency at tier 1 or 2 has rows, except the Utah agencies with no raw lines (kept at $0, owner
   decision); no agency at tier 3 or 4 has rows, payments or items; coverage counts agree with the agencies.
5. Files: every file carries the same built date; data/index.json is under 1,000,000 bytes gzipped and every data
   file under 50 MB; no data/data.json or data/payments.json is left; ids and indexes resolve; a vendor id has one
   name in every state.
6. home: the default table per scope (ALL and each state) recomputed from the state files with exact sums
   (math.fsum), compared to data/index.json: spend within a cent, row, vendor and agency counts and last year exact.
"""
import collections
import csv
import gzip
import io
import json
import math
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE = "de1e5cf"   # main before the multi-state page: its data/data.json and data/payments.json are Utah before the split
sys.path.insert(0, str(ROOT / "pipeline"))
import build  # noqa: E402  (string helpers and Utah's dedupe rules, for check 2 and payee names)

FAILS = []


def check(ok, msg):
    if not ok:
        FAILS.append(msg)
        print("FAIL:", msg)
    return ok


def load(name):
    return json.loads((DATA / name).read_bytes())


def lines_of(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def table(path):
    body = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return list(csv.DictReader(io.StringIO(body.decode("utf-8"), newline="")))


def legacy(aid):
    t = aid[3:]
    return int(t) if t.isdigit() else t


# --- 1. Utah unchanged ---------------------------------------------------------------------------------------------

def git_json(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True)
    if r.returncode:
        sys.exit(f"cannot read {path} at {ref}: {r.stderr.decode().strip()}\n"
                 f"pass --base <a commit that has {path}>, or --base none to skip check 1")
    return json.loads(r.stdout)


def check_utah_equivalence(I, U, UP, ref):
    D, LP = git_json(ref, "data/data.json"), git_json(ref, "data/payments.json")
    print(f"1. Utah: data/data.json at {ref} ({len(D['rows'])} rows) against index.json and ut.json")
    check(D["categories"] == I["categories"], "categories differ")
    added = {"state", "coverage", "sources", "tu_id", "lines"}
    ut_ag = [a for a in I["agencies"] if a["state"] == "UT"]
    mapped = [{"id": legacy(a["id"]), **{k: v for k, v in a.items() if k not in added and k != "id"}} for a in ut_ag]
    check(json.dumps(mapped) == json.dumps(D["agencies"]), "Utah agencies differ from data.json")
    check(all(a["coverage"] == 1 and a["tu_id"] == legacy(a["id"]) for a in ut_ag), "Utah agency coverage or tu_id")
    vid_l, vid_n = [v["id"] for v in D["vendors"]], [v["id"] for v in U["vendors"]]
    rl = [[r[0], vid_l[r[1]], r[2], r[3], r[4], D["aliases"][r[5]] if r[5] >= 0 else None] for r in D["rows"]]
    rn = [[legacy(r[0]), vid_n[r[1]], r[2], r[3], r[4], U["aliases"][r[5]] if r[5] >= 0 else None] for r in U["rows"]]
    check(rl == rn, "Utah rows differ (order included)")
    vkey = lambda V, A: [(v["id"], v["name"], v["category"], v["method"], v["neris"],  # noqa: E731
                          sorted(A[i] for i in v["aliases"])) for v in V]
    check(vkey(D["vendors"], D["aliases"]) == vkey(U["vendors"], U["aliases"]), "Utah vendors differ")
    pl = [[p[0], p[1], vid_l[p[2]], p[3], p[4], LP["descriptions"][p[5]], D["aliases"][p[6]] if p[6] >= 0 else None, p[7]]
          for p in LP["payments"]]
    pn = [[legacy(p[0]), p[1], vid_n[p[2]], p[3], p[4], UP["descriptions"][p[5]], U["aliases"][p[6]] if p[6] >= 0 else None,
           p[7]] for p in UP["payments"]]
    check(pl == pn, "Utah payments differ (order included)")
    check(LP["descriptions"] == UP["descriptions"], "Utah payment descriptions differ")
    check(D["grants"] == [{**g, "agency": legacy(g["agency"])} for g in U["grants"]], "Utah grants differ")
    m = I["meta"]["states"]["UT"]
    same = [k for k in D["meta"] if k not in ("built", "payments_file")]
    check(all(m.get(k) == D["meta"][k] for k in same), "Utah meta differs: " +
          ", ".join(k for k in same if m.get(k) != D["meta"][k]))
    check(U["totals"] == [] and m["coverage_counts"] == {"1": len(ut_ag), "2": 0, "3": 0, "4": 0}, "Utah totals or coverage")


# --- 2. Utah against the raw file -----------------------------------------------------------------------------------

def check_utah_raw(U, I):
    tx_path = build.latest_bq("fire_transactions*.csv.gz")
    print(f"2. Utah rows against {tx_path.relative_to(ROOT)}")
    cfg = [a for a in build.read_csv("agencies.csv") if a["include"] == "yes"]
    by_name = {a["name"]: f"UT-{a['id']}" for a in cfg}
    copies = build.reupload_copies(tx_path)
    years = set(I["meta"]["states"]["UT"]["years"])
    raw, n_lines = collections.defaultdict(list), collections.Counter()
    for n, r in enumerate(lines_of(tx_path)):
        aid = by_name.get(r["entity_name"])
        if aid is None or int(r["fiscal_year"]) not in years or n in copies or build.police_only(r):
            continue
        raw[aid].append(float(r["amount"] or 0))
        n_lines[aid] += 1
    net, n_rows = collections.defaultdict(list), collections.Counter()
    for r in U["rows"]:
        net[r[0]].append(r[4])
        n_rows[r[0]] += 1
    bad = [a["id"] for a in I["agencies"] if a["state"] == "UT" and
           abs(math.fsum(net[a["id"]]) - math.fsum(raw[a["id"]])) >= 0.005 * max(1, n_rows[a["id"]]) + 1e-6]
    check(not bad, f"Utah agencies not matching the raw file: {bad[:10]}")
    check(all(a["lines"] == n_lines[a["id"]] for a in I["agencies"] if a["state"] == "UT"), "Utah agency lines differ")
    ut = [a for a in I["agencies"] if a["state"] == "UT"]
    print(f"   {len(ut) - len(bad)} of {len(ut)} agencies match ({sum(n_lines.values()):,} lines)")


# --- 3 and 4. Other states ------------------------------------------------------------------------------------------

def check_state(st, I, S, P, IT, states_cfg, cat_ids, purchasing):
    low = st.lower()
    d = DATA / "states" / low
    m = I["meta"]["states"][st]
    years = set(states_cfg[st]["years"])
    agencies = [a for a in I["agencies"] if a["state"] == st]
    ids = {a["id"] for a in agencies}
    print(f"3. {m['name']}: {len(S['rows']):,} rows, {len(P['payments']):,} payments,"
          f" {len(IT['items']) if IT else 0:,} items, {len(S['totals']):,} totals rows against {d.relative_to(ROOT)}")
    src = json.loads((d / "agencies.json").read_text(encoding="utf-8"))
    check([a["id"] for a in src["agencies"]] == [a["id"] for a in agencies], f"{st}: agency list or order differs")
    check(all(a["coverage"] == b["coverage"] and a["sources"] == b["sources"]
              for a, b in zip(src["agencies"], agencies)), f"{st}: coverage or sources differ from agencies.json")
    counts = collections.Counter(str(a["coverage"]) for a in agencies)
    check(m["coverage_counts"] == {t: counts[t] for t in "1234"}, f"{st}: meta coverage_counts")

    # Rows against the transaction lines: agency x year x payee name as shown
    shown_of = {}
    want, lines = collections.defaultdict(list), collections.Counter()
    out_of_years = 0
    big = []                                                  # lines of $1,000 or more (or credits) in the years
    for r in lines_of(d / "transactions.csv.gz"):
        fy = int(r["fiscal_year"])
        if fy not in years:
            out_of_years += 1
            continue
        p = r["payee_name"]
        if p not in shown_of:
            shown_of[p] = build.payee_name(p)[0]
        amount = float(r["amount"] or 0)
        want[(r["agency_id"], fy, shown_of[p])].append(amount)
        lines[r["agency_id"]] += 1
        if abs(amount) >= build.PAYMENT_MIN:
            big.append((r["agency_id"], fy, r["posting_date"], shown_of[p], round(amount, 2), r["description"]))
    got, n = collections.defaultdict(list), collections.Counter()
    for r in S["rows"]:
        check(r[0] in ids and r[2] in years and 0 <= r[1] < len(S["vendors"]) and 0 <= r[3] < len(cat_ids)
              and 0 <= r[5] < len(S["aliases"]), f"{st}: bad row {r}") or sys.exit(1)
        got[(r[0], r[2], S["aliases"][r[5]])].append(r[4])
        n[(r[0], r[2], S["aliases"][r[5]])] += 1
    bad = [k for k in set(want) | set(got)
           if abs(math.fsum(got.get(k, [])) - math.fsum(want.get(k, []))) >= 0.005 * max(1, n[k]) + 1e-6]
    check(not bad, f"{st}: {len(bad)} agency-year-payee nets differ from transactions, e.g. {sorted(bad)[:3]}")
    check(all(a["lines"] == lines[a["id"]] for a in agencies), f"{st}: agency lines differ")
    check(m["counts"]["lines"] == sum(lines.values()) and m["lines_out_of_range"] == out_of_years,
          f"{st}: meta line counts")
    print(f"   {len(want):,} agency-year-payee sums match ({sum(lines.values()):,} lines; {out_of_years:,} outside the years)")

    # Coverage: tier 1-2 agencies have rows, tier 3-4 none
    with_rows = {r[0] for r in S["rows"]}
    no_rows = [a["id"] for a in agencies if a["coverage"] <= 2 and a["id"] not in with_rows]
    check(not no_rows, f"{st}: tier 1-2 agencies without rows: {no_rows[:10]}")
    tier34 = {a["id"] for a in agencies if a["coverage"] >= 3}
    check(not (tier34 & (with_rows | {p[0] for p in P["payments"]} | {x[0] for x in (IT or {}).get("items", [])})),
          f"{st}: tier 3-4 agencies with vendor data")

    # Payments
    nv, na, nd = len(S["vendors"]), len(S["aliases"]), len(P["descriptions"])
    check(all(p[0] in ids and 0 <= p[2] < nv and 0 <= p[5] < nd and 0 <= p[6] < na and p[7] in years
              and p[4] >= build.PAYMENT_MIN and cat_ids[p[3]] in purchasing for p in P["payments"]), f"{st}: bad payment")
    # Each payment is its own transaction line: agency, fiscal year, date, payee name, amount and description as published
    desc = lambda s: (lambda t: t.strip('"').replace('""', '"') if '""' in t else t)(build.clean_payee(s))  # noqa: E731
    lines_big = collections.Counter((a, fy, dt, who, x, desc(ds)) for a, fy, dt, who, x, ds in big if x > 0)
    pays = collections.Counter((p[0], p[7], p[1], S["aliases"][p[6]], p[4], P["descriptions"][p[5]]) for p in P["payments"])
    extra = pays - lines_big
    check(not extra, f"{st}: {sum(extra.values())} payments are no transaction line of their own, e.g. {list(extra)[:2]}")
    # None is missing: per agency, vendor and amount, the payments are at least the lines of payees whose rows that year
    # are all in one purchasing category, less the credits of that amount to the same vendor
    cats_of, vendor_of = collections.defaultdict(set), {}
    for a, v, y, c, x, al in S["rows"]:
        cats_of[(a, S["aliases"][al], y)].add(c)
        vendor_of[(a, S["aliases"][al])] = v
    need, credit = collections.Counter(), collections.Counter()
    for a, fy, _, who, x, _ in big:
        if (a, who) in vendor_of:
            k = (a, vendor_of[(a, who)], round(abs(x) * 100))
            cs = cats_of[(a, who, fy)]
            if x < 0:
                credit[k] += 1
            elif len(cs) == 1 and cat_ids[next(iter(cs))] in purchasing:
                need[k] += 1
    got = collections.Counter((p[0], p[2], round(p[4] * 100)) for p in P["payments"])
    short = [k for k, n in need.items() if got[k] < n - credit[k]]
    check(not short, f"{st}: {len(short)} agency-vendor-amounts with fewer payments than lines, e.g. {short[:2]}")
    print(f"   {len(P['payments']):,} payments are distinct transaction lines; none missing among"
          f" {sum(need.values()):,} lines of single-category purchasing payees")

    # Item lines, one per line_items.csv.gz line in file order
    path = d / "line_items.csv.gz"
    src_items = table(path) if path.exists() else []
    items = IT["items"] if IT else []
    check(len(items) == len(src_items), f"{st}: {len(items)} item lines, {len(src_items)} in line_items.csv.gz")
    if items:
        s = IT["strings"]
        sp = lambda x: " ".join((x or "").split())  # noqa: E731
        num = lambda x: float(x) if (x or "").strip() else None  # noqa: E731
        bad = [i for i, (it, r) in enumerate(zip(items, src_items)) if not (
            it[0] == r["agency_id"] and it[1] == int(r["fiscal_year"]) and it[2] == r["date"]
            and s[it[4]] == sp(r["brand"]) and s[it[5]] == sp(r["product_type"]) and s[it[6]] == sp(r["description"])
            and (it[7] is None) == (num(r["quantity"]) is None) and (it[7] is None or abs(it[7] - num(r["quantity"])) < 1e-9)
            and (it[8] is None) == (num(r["unit_price"]) is None) and (it[8] is None or abs(it[8] - num(r["unit_price"])) < 1e-9)
            and abs(it[9] - float(r["amount"])) < 0.005 and IT["sources"][it[11]] == r["source"] and 0 <= it[3] < nv)]
        check(not bad, f"{st}: {len(bad)} item lines differ from line_items.csv.gz, e.g. line {bad[:3]}")
        row_keys = {(r[0], r[1], r[2], r[3]) for r in S["rows"]}
        missing = [it for it in items if it[1] in years and (it[0], it[3], it[1], it[10]) not in row_keys]
        check(not missing, f"{st}: {len(missing)} in-year item lines whose agency, vendor, year and category is no row")
        print(f"   {len(items):,} item lines match ({sum(it[1] not in years for it in items):,} outside the years)")

    # Totals and budget
    path = d / "totals.csv"
    tot = [[r["agency_id"], int(r["fiscal_year"]), r["category_published"], float(r["amount"]), r["source"]]
           for r in (table(path) if path.exists() else []) if int(r["fiscal_year"]) in years]
    check(S["totals"] == tot, f"{st}: totals rows differ from totals.csv")
    budget = collections.defaultdict(lambda: collections.defaultdict(list))
    for a, y, _, x, _ in tot:
        budget[a][str(y)].append(x)
    check(all(a["budget"] == {y: round(math.fsum(v)) for y, v in sorted(budget[a["id"]].items())} for a in agencies),
          f"{st}: agency budgets differ from the totals")

    # Grants
    g = [(r["agency_id"], int(r["fiscal_year"]), r["award_number"], round(float(r["amount"]), 2))
         for r in table(d / "grants.csv") if r["agency_id"] in ids]
    check(sorted(g) == sorted((x["agency"], x["year"], x["award"], round(x["amount"], 2)) for x in S["grants"]),
          f"{st}: grants differ from grants.csv")


def check_coverage_ut(I, U):
    ut = [a for a in I["agencies"] if a["state"] == "UT"]
    with_rows = {r[0] for r in U["rows"]}
    no_rows = [a for a in ut if a["id"] not in with_rows]
    check(all(a["lines"] == 0 for a in no_rows), f"Utah agencies with lines but no rows: {[a['id'] for a in no_rows if a['lines']]}")
    print(f"4. Utah agencies without rows (no raw lines, kept at $0): {', '.join(a['id'] + ' ' + a['name'] for a in no_rows) or 'none'}")


# --- 5. Files -------------------------------------------------------------------------------------------------------

def check_files(I, files):
    built = I["meta"]["built"]
    for name, x in files.items():
        check(x.get("built", (x.get("meta") or {}).get("built")) == built, f"data/{name}: built differs from index.json")
    gz = len(gzip.compress((DATA / "index.json").read_bytes(), compresslevel=9, mtime=0))
    check(gz < 1_000_000, f"data/index.json is {gz:,} bytes gzipped")
    stale = [n for n in ("data.json", "payments.json") if (DATA / n).exists()]
    check(not stale, f"files the build no longer writes (the page before the split read them): {stale}")
    big = [p.name for p in DATA.rglob("*") if p.is_file() and p.stat().st_size >= 50_000_000]
    check(not big, f"files of 50 MB or more: {big}")
    ids = [a["id"] for a in I["agencies"]]
    check(len(ids) == len(set(ids)), "repeated agency ids in index.json")
    names = collections.defaultdict(set)
    for st in I["meta"]["states_order"]:
        S = files[f"{st.lower()}.json"]
        vids = [v["id"] for v in S["vendors"]]
        check(len(vids) == len(set(vids)), f"{st}: repeated vendor ids")
        for v in S["vendors"]:
            names[v["id"]].add((v["name"], v["method"], v["neris"]))
            check(all(0 <= i < len(S["aliases"]) for i in v["aliases"]), f"{st}: vendor {v['id']} payee names")
    multi = [k for k, v in names.items() if len(v) > 1]
    check(not multi, f"vendor ids with different names in different states: {multi[:5]}")
    for st, m in I["meta"]["states"].items():
        for kind, path in m["files"].items():
            check(path is None or (ROOT / path).exists(), f"{st}: {kind} file {path} missing")
        check(all(s in I["meta"]["sources"] for s in m["sources"]), f"{st}: unknown source in meta")
    check(all(s in I["meta"]["sources"] for a in I["agencies"] for s in a["sources"]), "agency with an unknown source")
    print(f"5. Files: built {built}; data/index.json {gz:,} bytes gzipped; {len(ids):,} agencies; "
          f"{len(names):,} vendor ids in {len(I['meta']['states_order'])} states")


# --- 6. home --------------------------------------------------------------------------------------------------------

def check_home(I, files, states_cfg):
    cats = I["categories"]
    purch = [i for i, c in enumerate(cats) if c["purchasing"] == "yes"]
    order = I["meta"]["states_order"]
    for scope in ["ALL"] + order:
        sts = order if scope == "ALL" else [scope]
        ys = sorted({y for s in sts for y in states_cfg[s]["years"]})
        per = {c: {"x": [], "yr": collections.defaultdict(list), "net": collections.defaultdict(list)} for c in purch}
        for s in sts:
            S = files[f"{s.lower()}.json"]
            for a, v, y, c, x, _ in S["rows"]:
                if c in per and ys[0] <= y <= ys[-1]:
                    per[c]["x"].append(x)
                    per[c]["yr"][y].append(x)
                    per[c]["net"][(a, S["vendors"][v]["id"], y)].append(x)
        h = I["home"][scope]
        check((h["from"], h["to"]) == (ys[0], ys[-1]), f"home {scope}: year range")
        got = {c[0]: c for c in h["cats"]}
        check(sorted(got) == purch, f"home {scope}: categories")
        all_ve, all_ag, all_x, all_yr, n_all = set(), set(), [], collections.defaultdict(list), 0
        for c in purch:
            p = per[c]
            pos = [k for k, v in p["net"].items() if math.fsum(v) > 0.005]
            ve, ag = {k[1] for k in pos}, {k[0] for k in pos}
            last = max((k[2] for k in pos), default=None)
            g = got.get(c)
            if not check(g is not None, f"home {scope}: category {c} missing"):
                continue
            check(abs(g[1] - math.fsum(p["x"])) < 0.01 and g[2] == len(p["x"]) and g[3] == len(ve) and g[4] == len(ag)
                  and g[5] == last, f"home {scope}: category {cats[c]['id']}: {g[:6]} vs "
                  f"{[c, round(math.fsum(p['x']), 2), len(p['x']), len(ve), len(ag), last]}")
            check(sorted(g[6]) == sorted(str(y) for y in p["yr"]) and all(
                abs(g[6][str(y)] - math.fsum(v)) < 0.01 for y, v in p["yr"].items()), f"home {scope}: {cats[c]['id']} years")
            all_ve |= ve
            all_ag |= ag
            all_x += p["x"]
            n_all += len(p["x"])
            for y, v in p["yr"].items():
                all_yr[y] += v
        s = h["sum"]
        check(abs(s[0] - math.fsum(all_x)) < 0.01 and s[1] == n_all and s[2] == len(all_ve) and s[3] == len(all_ag)
              and all(abs(s[4][str(y)] - math.fsum(v)) < 0.01 for y, v in all_yr.items()) and len(s[4]) == len(all_yr),
              f"home {scope}: sum {s[:4]} vs {[round(math.fsum(all_x), 2), n_all, len(all_ve), len(all_ag)]}")
        print(f"6. home {scope}: ${s[0]:,.2f}, {s[1]:,} rows, {s[2]:,} vendors, {s[3]:,} agencies")


def main(argv):
    if argv and (argv[0] != "--base" or len(argv) != 2):
        sys.exit("usage: python3 tests/check_build.py [--base REF | --base none]")
    base = argv[1] if argv else BASE
    I = load("index.json")
    states_cfg = build.read_states()
    check(list(states_cfg) == I["meta"]["states_order"], "states_order differs from config/states.csv")
    files = {"index.json": I}
    for st in I["meta"]["states_order"]:
        m = I["meta"]["states"][st]
        for kind in ("rows", "payments", "items"):
            if m["files"][kind]:
                files[pathlib.Path(m["files"][kind]).name] = json.loads((ROOT / m["files"][kind]).read_bytes())
    cat_ids = [c["id"] for c in I["categories"]]
    purchasing = {c["id"] for c in I["categories"] if c["purchasing"] == "yes"}
    U, UP = files["ut.json"], files["ut-payments.json"]
    if base == "none":
        print("1. Utah against the files from before the split: skipped (--base none)")
    else:
        check_utah_equivalence(I, U, UP, base)
    check_utah_raw(U, I)
    for st in I["meta"]["states_order"][1:]:
        low = st.lower()
        check_state(st, I, files[f"{low}.json"], files[f"{low}-payments.json"], files.get(f"{low}-items.json"),
                    states_cfg, cat_ids, purchasing)
    check_coverage_ut(I, U)
    check_files(I, files)
    check_home(I, files, states_cfg)
    if FAILS:
        sys.exit(f"\n{len(FAILS)} checks failed")
    print("\nAll build checks passed.")


if __name__ == "__main__":
    main(sys.argv[1:])
