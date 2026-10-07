"""Recompute California vendor-data totals from the raw files and check data/states/ca/ matches.

    python3 tests/multistate/check_ca.py

Independent of the adapters' code paths: every raw file is parsed here with its own filters and its own duplicate
rules (written from the rules in docs/sources/ca.md, not imported). Shared with the adapters are only
config/states/ca/agency_sources.csv (the hand-reviewed attribution), config/payee_name_redactions.csv (the owner's
redaction rule) and common's file helpers and norm(). Checks:
  1. per source, agency and fiscal year: dollars (to the cent) and line counts equal the raw files after the owner's
     dedup rule of 2026-10-07 as corrected the same day: raw lines equal in every column the source publishes but its
     row and load ids (Socrata :id; SF also data_as_of and data_loaded_at; FI$Cal and SCPRS have none) are kept once,
     document numbers (voucher, invoice, payment, PO and their line numbers) being content; void-safe: n identical
     positive lines keep min(n, r + 1) copies, r = distinct negative lines with the same reversal fields (agency,
     payee, account and the document fields the source repeats on a void), the amount negated and the same or next
     fiscal year; identical voids (owner decision A of 2026-10-07): in a family that has payments (same reversal
     fields, amount up to sign, a payment linked to the negative lines of its fiscal year and the next), an identical
     negative copy is dropped only together with a dropped identical positive copy of the family, and every family
     where this keeps a negative copy nets exactly its raw lines (asserted). SCPRS purchase-order item lines are
     exempt (owner decision B of 2026-10-07): every line is kept. The multiset of (agency, fiscal year, date, payee,
     amount) lines is equal too; for ca_fiscal the rule applies to the raw distribution lines before they are summed
     per voucher
  2. payee names are shown as published (owner decision of 2026-10-06): every published payee is a raw payee
     name (whitespace collapsed), or "Payee name withheld" where the raw name matches a redaction pattern; the
     old person marker never appears; no published payee matches a redaction pattern; no payee, description or
     account carries an email address. Names that look like private persons (common.is_person / looks_like_person)
     are only counted and reported (shown, owner decision)
  3. every agency_id in the tables and agency_sources.csv exists in agencies.json; coverage tiers agree with the
     rows present; no agency without rows has a tier above 4; no zero-dollar totals rows; no agencies_added.csv row
     duplicates a registry fire district of the same county by name; SCO city fire lines go only to fire departments
  4. no duplicate and no empty source_record_id per source; tier-2 line items equal their transactions rows
  5. every source in a table is registered in sources.csv with the years present in the data and the raw folder date
  6. vendor map: no unmerged config/states/ca/vendor_map_additions.csv; config/vendor_map.csv, then the vendor and
     keyword rules (as pipeline/build.py applies them), give a real category to at least 90% of purchasing dollars
  7. raw files: each under 50 MB, California under 150 MB, every source folder has a sample of at most 100 rows
  8. contract conformance: table and config columns in the order docs/multistate/data-contract.md gives; dates
     YYYY-MM-DD; amounts with two decimals; payment dates inside the fiscal year they are filed under (July-June,
     named for the year it ends), SCPRS purchase-order dates excepted
"""
import collections
import csv
import difflib
import gzip
import hashlib
import io
import json
import pathlib
import re
import sys
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "pipeline" / "sources"))
import common  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vendor_coverage  # noqa: E402

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


def ws(text):
    return " ".join((text or "").split())


DROPPED = {}  # source -> (sets with a dropped copy, copies dropped, cents dropped, copies kept by the void rule, cents)
FIXED = {}  # source -> (negative copies kept by the void fix, cents, families touched; each nets its raw lines)
EXEMPT = {}  # source -> raw lines equal in every column to another line, all kept (exempt source)


def family_root(nodes):
    """Union-find over family nodes (reversal fields, amount > 0, fiscal year, sign): a payment (sign 1) of year y is
    linked with the negative lines (sign -1) of y and y + 1. Returns find(node) -> the family's root node."""
    parent = {node: node for node in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for rev, a, fy, sign in nodes:
        if sign > 0:
            for y in (fy, fy + 1):
                if (rev, a, y, -1) in parent:
                    parent[find((rev, a, y, -1))] = find((rev, a, fy, 1))
    return find


def fix_voids(negatives, positives, find):
    """Owner decision A of 2026-10-07 (written from docs/sources/ca.md): copies kept of each set of identical negative
    lines. negatives: [(order, node, copies)] per negative identity with copies >= 2 (order: fiscal year, then lowest
    row id or the raw line); positives: [(node, copies dropped)] per positive identity. A family with no payment keeps
    each set once; otherwise each copy dropped needs a positive copy dropped in the same family, sets taking them in
    order. Returns {order: copies kept}."""
    budget, paid = collections.Counter(), set()
    for node, gone in positives:
        budget[find(node)] += gone
        paid.add(find(node))
    out = {}
    for order, node, copies in sorted(negatives):
        root = find(node)
        gone = copies - 1 if root not in paid else min(copies - 1, budget[root])
        budget[root] -= gone
        out[order] = copies - gone
    return out


def identical_rule(source, lines):
    """The owner's rule of 2026-10-07 as corrected, with the void fix of the same day, written here from
    docs/sources/ca.md (not imported). lines: (identity, row id, reversal fields, fiscal year, cents, published tuple)
    per raw line; identity is every raw column but the row and load ids. Copies of one identity are kept once; a
    positive identity keeps min(n, r + 1) copies, r = how many distinct negative identities have its reversal fields,
    the negated amount and the same or the next fiscal year; a negative identity keeps the copies fix_voids gives.
    Asserts that every family where a negative set keeps more than one copy nets its raw lines. Returns the kept
    published tuples (a list, one entry per kept line)."""
    n = collections.Counter(ident for ident, *_ in lines)
    first = {}
    for ident, rid, rev, fy, c, out in lines:
        if ident not in first or rid < first[ident][0]:
            first[ident] = (rid, rev, fy, c, out)
    voids = collections.Counter((rev, -c, fy) for _, rev, fy, c, _ in first.values() if c < 0)
    copies = {}
    for ident, (_, rev, fy, c, _) in first.items():
        copies[ident] = min(n[ident], voids[(rev, c, fy)] + voids[(rev, c, fy + 1)] + 1) if c > 0 else 1
    node = {ident: (rev, abs(c), fy, 1 if c > 0 else -1) for ident, (_, rev, fy, c, _) in first.items() if c}
    find = family_root(set(node.values()))
    negatives = [((fy, rid), node[i], n[i]) for i, (rid, rev, fy, c, _) in first.items() if c < 0 and n[i] > 1]
    by_order = {(fy, rid): i for i, (rid, rev, fy, c, _) in first.items() if c < 0 and n[i] > 1}
    fixed = fix_voids(negatives, [(node[i], n[i] - copies[i]) for i, (_, _, _, c, _) in first.items() if c > 0], find)
    for order, kept in fixed.items():
        copies[by_order[order]] = kept
    raw_net, kept_net, touched = collections.Counter(), collections.Counter(), set()
    kept, sets, dropped, cents_dropped, void_kept, void_cents, fix_kept, fix_cents = [], 0, 0, 0, 0, 0, 0, 0
    for ident, (_, rev, fy, c, out) in first.items():
        kept += [out] * copies[ident]
        if copies[ident] < n[ident]:
            sets += 1
            dropped += n[ident] - copies[ident]
            cents_dropped += (n[ident] - copies[ident]) * c
        if c > 0:
            void_kept += copies[ident] - 1
            void_cents += (copies[ident] - 1) * c
        elif c < 0 and copies[ident] > 1:
            fix_kept += copies[ident] - 1
            fix_cents += (copies[ident] - 1) * c
            touched.add(find(node[ident]))
        if c:
            raw_net[find(node[ident])] += n[ident] * c
            kept_net[find(node[ident])] += copies[ident] * c
    off = [(root, raw_net[root], kept_net[root]) for root in touched if raw_net[root] != kept_net[root]]
    assert not off, f"{source}: {len(off)} families touched by the void fix do not net their raw lines: {off[:3]}"
    paid = {find(node[i]) for i, (_, _, _, c, _) in first.items() if c > 0}
    above = [root for root in paid if kept_net[root] > raw_net[root]]
    assert not above, f"{source}: {len(above)} families with payments net above their raw lines: {above[:3]}"
    DROPPED[source] = (sets, dropped, cents_dropped, void_kept, void_cents)
    FIXED[source] = (fix_kept, fix_cents, len(touched))
    return kept


def socrata(r, ids=(":id",)):
    """Identity of a Socrata raw line: every column it carries but the row and load ids (null columns are absent)."""
    return tuple(sorted((k, v) for k, v in r.items() if k not in ids and v not in (None, "")))


def fields(r, names):
    return tuple(r.get(f) or "" for f in names)


# --- 1. expected lines per source, from raw -----------------------------------------------------------------

def expect_sf():
    agency = links("ca_sf", "source_entity_id")["FIR"]
    raw = raw_json("ca_sf", "fir.json.gz")
    control = raw_json("ca_sf", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control), "ca_sf: raw rows differ from control"
    lines = []
    for r in raw:
        if r["department_code"] != "FIR" or cents(r.get("vouchers_paid")) == 0:
            continue
        fy, payee, c = int(r["fiscal_year"]), published(r["vendor"]), cents(r["vouchers_paid"])
        # row and load ids: :id, data_as_of ("updated in the source system"), data_loaded_at; no payment date
        lines.append((socrata(r, (":id", "data_as_of", "data_loaded_at")), r[":id"],
                      fields(r, ("department_code", "vendor", "purchase_order", "contract_number", "program_code",
                                 "character_code", "object_code", "sub_object_code", "fund_code")),
                      fy, c, (agency, str(fy), "", payee, c)))
    return identical_rule("ca_sf", lines)


def expect_la():
    agency = links("ca_la")["FIRE"]
    raw = raw_json("ca_la", "fire.json.gz")
    control = raw_json("ca_la", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control), "ca_la: raw rows differ from control"
    lines = []
    for r in raw:
        if r["department_name"] != "FIRE" or r.get("dollar_amount") in (None, ""):
            continue
        fy, payee, c = int(r["fiscal_year"]), published(r.get("vendor_name")), cents(r["dollar_amount"])
        lines.append((socrata(r), r[":id"],
                      fields(r, ("department_name", "vendor_name", "program", "fund", "account_code", "inv_num",
                                 "inv_line", "inv_dist_line", "po_num", "po_line_number")),
                      fy, c, (agency, str(fy), (r.get("transaction_date") or "")[:10], payee, c)))
    return identical_rule("ca_la", lines)


def expect_riverside():
    agency = links("ca_riverside_county")["Fire Protection"]
    raw = raw_json("ca_riverside_county", "fire.json.gz")
    control = raw_json("ca_riverside_county", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control if str(c["has_vendor"]).lower() == "true")
    lines = []
    for r in raw:
        if r["department"] != "Fire Protection" or not r.get("vendor_name"):
            continue
        fy, payee, c = int(r["fiscal_year"]), published(r["vendor_name"]), cents(r["amount"])
        lines.append((socrata(r), r[":id"],
                      fields(r, ("department", "vendor_name", "business_unit", "fund_type", "fund", "account_category",
                                 "account", "expense_category", "invoice_id", "payment_id", "description")),
                      fy, c, (agency, str(fy), (r.get("date") or "")[:10], payee, c)))
    return identical_rule("ca_riverside_county", lines)


def expect_corona():
    agency = links("ca_corona", "source_entity_id")["30"]
    raw = raw_json("ca_corona", "fire.json.gz")
    control = raw_json("ca_corona", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control), "ca_corona: raw rows differ from control"
    lines = []
    for r in raw:
        if r["department_code"] != "30":
            continue
        fy, payee, c = int(r["fiscal_year"]), published(r["vendor"]), cents(r["amount"])
        # a void can carry its own payment id and date, so those are not reversal fields
        lines.append((socrata(r), r[":id"],
                      fields(r, ("department_code", "vendor", "department_activity", "fund_name", "expense_category",
                                 "invoice_id", "description")),
                      fy, c, (agency, str(fy), (r.get("payment_date") or "")[:10], payee, c)))
    return identical_rule("ca_corona", lines)


def expect_moreno_valley():
    link = links("ca_moreno_valley")
    raw = raw_json("ca_moreno_valley", "fire.json.gz")
    control = raw_json("ca_moreno_valley", "control.json.gz")
    assert len(raw) == sum(int(c["n"]) for c in control), "ca_moreno_valley: raw rows differ from control"
    assert {c["department"] for c in control} == set(link), "ca_moreno_valley: a fire-named department is not linked"
    lines = []
    for r in raw:
        agency, fy, payee, c = link[r["department"]], int(r["fiscal_year"]), published(r.get("vendor")), cents(r["amount"])
        lines.append((socrata(r), r[":id"],
                      fields(r, ("department", "vendor", "program", "fund", "expense_category", "invoice_id",
                                 "invoice_line", "invoice_distribution_line")),
                      fy, c, (agency, str(fy), (r.get("payment_date") or "")[:10], payee, c)))
    return identical_rule("ca_moreno_valley", lines)


def scprs_money(s):
    s = (s or "").replace("$", "").replace(",", "").strip()
    return -cents(s.strip("()")) if s.startswith("(") else cents(s or "0")


def scprs_day(s, fy_end):
    """m/d/yyyy as yyyy-mm-dd when the year is 2000 to the fiscal year's end (typos such as 1912 or 2511 aside)."""
    s = (s or "").strip()
    if not s:
        return ""
    m, d, y = (int(x) for x in s.split("/"))
    return f"{y:04d}-{m:02d}-{d:02d}" if 2000 <= y <= fy_end else ""


def expect_scprs():
    link = links("ca_scprs")
    d = common.latest_raw(ST, "ca_scprs")
    manifest = json.loads(gzip.decompress((d / "manifest.json.gz").read_bytes()))
    rows = list(csv.DictReader(io.StringIO(gzip.decompress((d / "calfire.csv.gz").read_bytes()).decode("utf-8"))))
    assert len(rows) == manifest["kept_rows"], "ca_scprs: raw rows differ from manifest"
    dept = manifest["kept_department"]
    assert all(r["Department Name"] == dept for r in rows) and dept in link
    raw = list(csv.reader(io.StringIO(gzip.decompress((d / "calfire.csv.gz").read_bytes()).decode("utf-8"))))[1:]
    assert len(raw) == len(rows)
    lines, same = [], collections.Counter()
    for r, line in zip(rows, raw):
        c = scprs_money(r["Total Price"])
        if c == 0:
            continue
        fy_end = int(r["Fiscal Year"][5:])
        payee = published(r["Supplier Name"])
        lines.append((link[dept], str(fy_end),
                      scprs_day(r["Purchase Date"], fy_end) or scprs_day(r["Creation Date"], fy_end), payee, c))
        same[tuple(line)] += 1
    # PO item lines are exempt from the identical-line rule (owner decision B of 2026-10-07): every line is kept,
    # also lines equal in all 32 columns inside one PO (no line number in the file)
    EXEMPT["ca_scprs"] = sum(k for k in same.values() if k > 1)
    return lines


def expect_fiscal():
    """[(agency, fy, date, payee, cents)] rows of the Open FI$Cal files: the owner rule on the raw distribution lines
    (no row id or load date in the files, so a line is identical to another only when all its columns are, document
    id included; void-safe and void fix as identical_rule, negative sets ordered by their raw line), then lines summed
    per voucher, payee, accounting date, program,
    sub-program, fund and account, $0 sums left out. The summed rows are not compared with each other."""
    agency = links("ca_fiscal", "source_entity_id")["3540"]
    d = common.latest_raw(ST, "ca_fiscal")
    manifest = json.loads(gzip.decompress((d / "manifest.json.gz").read_bytes()))
    sums = collections.Counter()
    repeated = {}  # raw line seen more than once -> (sum key, reversal fields, fy, cents, copies)
    voids = collections.Counter()  # (reversal fields, cents negated, fy) -> distinct negative lines
    paid = set()  # md5 of (reversal fields, cents, fy) of every positive line: families that have payments
    for entry in manifest:
        reader = csv.reader(io.StringIO(gzip.decompress((d / (entry["file"] + ".gz")).read_bytes()).decode("utf-8-sig")))
        header = next(reader)
        ix = {c: i for i, c in enumerate(header)}
        fields_ = [ix[c] for c in ("program_description", "sub_program_description", "fund_code", "fund_description",
                                   "account", "account_description", "account_category")]
        rev_ix = [ix[c] for c in ("business_unit", "VENDOR_NAME", "document_id", "account", "fund_code", "program_code")]
        seen, n, total = set(), 0, 0
        for r in reader:
            n += 1
            c = cents(r[ix["monetary_amount"]])
            total += c
            key = "\x1f".join(r)
            fy = int(r[ix["fiscal_year_begin"]]) + 1
            voucher = r[ix["document_id"]].rsplit(".", 2)[0]
            sum_key = (str(fy), voucher, r[ix["VENDOR_NAME"]], r[ix["accounting_date"]][:10], *(r[i] for i in fields_))
            if key in seen:
                k = repeated.get(key)
                repeated[key] = (sum_key, tuple(r[i] for i in rev_ix), fy, c, (k[4] if k else 1) + 1)
                continue
            seen.add(key)
            assert r[ix["business_unit"]] == "3540", r
            assert fy == entry["fiscal_year"], (entry["file"], fy)
            if c < 0:
                voids[(tuple(r[i] for i in rev_ix), -c, fy)] += 1
            elif c > 0:
                paid.add(hashlib.md5(repr((tuple(r[i] for i in rev_ix), c, fy)).encode()).digest())
            sums[sum_key] += c
        assert n == entry["rows"] and total == cents(entry["dollars"]), f"ca_fiscal {entry['file']}: differs from manifest"
        del seen
    keep = {key: min(copies, voids[(rev, c, fy)] + voids[(rev, c, fy + 1)] + 1) if c > 0 else 1
            for key, (_, rev, fy, c, copies) in repeated.items()}
    # void fix: the family nodes of every (reversal fields, amount) that has a set of identical negative lines
    years = range(min(e["fiscal_year"] for e in manifest) - 1, max(e["fiscal_year"] for e in manifest) + 2)
    pairs = {(rev, -c) for _, rev, fy, c, _ in repeated.values() if c < 0}
    nodes = {(rev, a, y, sign) for rev, a in pairs for y in years for sign in (1, -1)
             if (sign < 0 and voids[(rev, a, y)]) or
             (sign > 0 and hashlib.md5(repr((rev, a, y)).encode()).digest() in paid)}
    find = family_root(nodes)
    fixed = fix_voids([((fy, key), (rev, -c, fy, -1), copies)
                       for key, (_, rev, fy, c, copies) in repeated.items() if c < 0],
                      [((rev, c, fy, 1), copies - keep[key])
                       for key, (_, rev, fy, c, copies) in repeated.items() if c > 0 and (rev, c) in pairs], find)
    for (_, key), kept in fixed.items():
        keep[key] = kept
    sets = dropped = cents_dropped = void_kept = void_cents = fix_kept = fix_cents = 0
    gone, touched = collections.Counter(), set()  # family -> cents dropped (a touched family must drop $0 net)
    for key, (sum_key, rev, fy, c, copies) in repeated.items():
        sums[sum_key] += (keep[key] - 1) * c
        sets += copies > keep[key]
        dropped += copies - keep[key]
        cents_dropped += (copies - keep[key]) * c
        void_kept += (keep[key] - 1) * (c > 0)
        void_cents += (keep[key] - 1) * c * (c > 0)
        if c and (rev, abs(c)) in pairs:
            root = find((rev, abs(c), fy, 1 if c > 0 else -1))
            gone[root] += (copies - keep[key]) * c
            if c < 0 and keep[key] > 1:
                fix_kept += keep[key] - 1
                fix_cents += (keep[key] - 1) * c
                touched.add(root)
    off = [root for root in touched if gone[root]]
    assert not off, f"ca_fiscal: {len(off)} families touched by the void fix do not net their raw lines: {off[:3]}"
    # only a dropped negative copy can raise a net, and those are all in these families
    paid_roots = {find(node) for node in nodes if node[3] > 0}
    above = [root for root in gone if gone[root] < 0 and root in paid_roots]
    assert not above, f"ca_fiscal: {len(above)} families with payments net above their raw lines: {above[:3]}"
    DROPPED["ca_fiscal"] = (sets, dropped, cents_dropped, void_kept, void_cents)
    FIXED["ca_fiscal"] = (fix_kept, fix_cents, len(touched))
    lines = []
    for (fy, _voucher, vendor, day, *acct), c in sorted(sums.items()):
        if c:
            lines.append((agency, fy, day, published(vendor), c))
    return lines


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


def contract_columns():
    """Column lists from docs/multistate/data-contract.md: the three tables and two config files."""
    text = (common.ROOT / "docs" / "multistate" / "data-contract.md").read_text(encoding="utf-8")
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
    body = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return body.split(b"\n", 1)[0].decode("utf-8").split(",")


NAME_STOP = {"FIRE", "PROTECTION", "DISTRICT", "DIST", "DEPARTMENT", "DEPT", "FPD", "OF", "THE", "AND", "VOLUNTEER",
             "RURAL", "AUTHORITY", "NO", "FD", "VFD"}
# Added agencies whose name resembles a registry fire district in the same county, reviewed: not the same body.
ADDED_REVIEWED = {"CA-S-ukiah-valley-fire-protection-district": "member district of the Ukiah Valley Fire Authority (CA-23080)"}


def name_key(name):
    return " ".join(sorted(t for t in re.findall(r"[A-Z0-9]+", name.upper()) if t not in NAME_STOP))


# --- checks ---------------------------------------------------------------------------------------------------

def main():
    d = common.data_dir(ST)
    tx = common.read_data_csv(d / "transactions.csv.gz")
    li = common.read_data_csv(d / "line_items.csv.gz")
    tot = common.read_data_csv(d / "totals.csv")
    agencies = json.loads((d / "agencies.json").read_text(encoding="utf-8"))
    sources = {s["source"]: s for s in common.read_config(ST, "sources.csv")}
    report = []

    # 1. line-level sources: lines, dollars, dates and payees per agency and fiscal year (ca_fiscal: rows summed per
    #    voucher after the rule on its raw lines)
    expect = {"ca_sf": expect_sf, "ca_la": expect_la, "ca_riverside_county": expect_riverside,
              "ca_corona": expect_corona, "ca_moreno_valley": expect_moreno_valley, "ca_scprs": expect_scprs,
              "ca_fiscal": expect_fiscal}
    for source, fn in expect.items():
        want = collections.Counter(fn())
        got = collections.Counter((r["agency_id"], r["fiscal_year"], r["posting_date"], r["payee_name"],
                                   cents(r["amount"])) for r in tx if r["source"] == source)
        assert got == want, (f"{source}: lines differ from raw: {sorted((want - got).items())[:3]} missing, "
                             f"{sorted((got - want).items())[:3]} extra")
        per = collections.Counter()
        for (a, fy, _, _, c), n in want.items():
            per[(a, fy)] += c * n
        report.append(f"{source}: {sum(want.values())} lines, ${sum(per.values()) / 100:,.2f}, "
                      f"{len({a for a, _ in per})} agencies, FY{min(fy for _, fy in per)}-FY{max(fy for _, fy in per)}")
    assert all(cents(r["amount"]) != 0 for r in tx if r["source"] == "ca_fiscal"), "ca_fiscal: a $0 row"

    # published rows equal in every column but source_record_id are different payments (their document numbers
    # differ in the raw file; the published columns leave voucher, invoice and line numbers out), so they stay;
    # count them for the report
    for source, (sets, n, dropped, void_kept, void_cents) in sorted(DROPPED.items()):
        rows = [r for r in tx if r["source"] == source]
        same = collections.Counter(tuple(v for k, v in r.items() if k != "source_record_id") for r in rows)
        alike = sum(n_ for n_ in same.values() if n_ > 1)
        fix_kept, fix_cents, families = FIXED[source]
        report.append(f"{source}: {n} identical raw lines dropped (${dropped / 100:,.2f}, {sets} sets); void rule kept "
                      f"{void_kept} copies (${void_cents / 100:,.2f}); void fix kept {fix_kept} negative copies "
                      f"(${fix_cents / 100:,.2f}) in {families} families, each at its raw net; {alike} published rows "
                      "share every published column with another row (kept: different documents or kept copies)")
    for source, n in sorted(EXEMPT.items()):
        report.append(f"{source}: exempt from the identical-line rule (PO item lines); {n} raw lines equal another in "
                      "every column, all kept")

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
    assert {r["source"] for r in tx} == set(expect), f"unexpected sources {sorted({r['source'] for r in tx})}"
    assert {r["source"] for r in tot} == {"ca_sco_districts", "ca_sco_cities"}
    assert {r["source"] for r in li} == {"ca_scprs"}

    # 2. payee names as published; no email address in a payee, description or account (strict address form: the
    #    redaction pattern also matches part numbers such as "6@1762.00" in descriptions)
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
    emails = 0
    for r in tx + li:
        name = r.get("payee_name", r.get("vendor"))
        assert name != OLD_MARKER, f"payee withheld by the old person rule: {r}"
        if name != CUT:
            assert not any(rx.search(name) for rx in REDACT), f"redaction pattern in a published payee: {r}"
        emails += any(email.search(r.get(f) or "") for f in ("payee_name", "vendor", "description", "account"))
    assert emails == 0, f"{emails} lines carry an email address"
    person_like = collections.Counter(r["source"] for r in tx if common.is_person(r["payee_name"])
                                      or common.looks_like_person(r["payee_name"]))
    cut = collections.Counter(r["source"] for r in tx if r["payee_name"] == CUT)
    report.append(f"payees: published as in the source; {sum(cut.values())} lines cut by the redaction rule; "
                  f"{sum(person_like.values())} lines have person-shaped payee names (shown, owner decision) "
                  f"{dict(sorted(person_like.items()))}; {emails} lines carry an email address in a payee, description or account")

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
    # owner decision 4: CAL FIRE stays in the main data with kind "State fire agency" (federal.kind, by name); a
    # county department CAL FIRE runs under contract stays a county department
    assert kinds["CA-00555"] == "State fire agency", "CAL FIRE (CA-00555) is not kind 'State fire agency'"
    assert kinds["CA-33555"] == "County fire department", "Cal Fire - Riverside County Fire Department is a county row"
    allowed_kinds = {"Fire district", "Emergency services district", "Local fire department",
                     "Volunteer fire department", "County fire department", "Township fire department",
                     "State fire agency"}
    assert all(a["kind"] in allowed_kinds for a in common.read_config(ST, "agencies_added.csv")), \
        "agencies_added.csv: kind outside federal.kind's labels"
    # agencies_added.csv: source-named agencies only, never a second row for a registry fire district of the county
    registry = common.read_config(ST, "agencies.csv")
    for a in common.read_config(ST, "agencies_added.csv"):
        assert a["id"].startswith("CA-S-"), a
        if a["id"] in ADDED_REVIEWED:
            continue
        for r in registry:
            if r["county"].upper() == a["county"].upper() and r["kind"] == "Fire district":
                ratio = difflib.SequenceMatcher(None, name_key(a["name"]), name_key(r["name"])).ratio()
                assert ratio < 0.9, f"{a['id']} {a['name']} looks like registry row {r['id']} {r['name']}"
    # a city's SCO fire line goes only to a fire department (or a public safety department that runs one)
    names = {a["id"]: a["name"] for a in agencies["agencies"]}
    for r in common.read_config(ST, "agency_sources.csv"):
        if r["source"] == "ca_sco_cities":
            assert re.search(r"FIRE|PUBLIC SAFETY|EMERGENCY SERVICES", names[r["agency_id"]].upper()), r

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
    for source, s in sources.items():
        assert s["fetched"] == common.latest_raw(ST, source).parent.parent.name, f"{source}: fetched {s['fetched']}"
        assert s["tier"] in ("1", "2", "3") and all(s[c] for c in ("name", "url", "years", "fiscal_year", "note")), s

    # 8. contract conformance: columns and order as docs/multistate/data-contract.md; dates YYYY-MM-DD; amounts with
    #    two decimals (whole dollars allowed in totals); fiscal year = the year the July-June fiscal year ends
    cols = contract_columns()
    for name in ("transactions.csv.gz", "line_items.csv.gz", "totals.csv"):
        assert header(d / name) == cols[name], f"{name}: columns {header(d / name)} vs contract {cols[name]}"
    for name in ("sources.csv", "agency_sources.csv"):
        assert header(common.config_dir(ST) / name) == cols[name], f"{name}: columns differ from the contract"
    iso = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for r in tx + li:
        assert re.fullmatch(r"-?\d+\.\d{2}", r["amount"]) and re.fullmatch(r"20\d\d", r["fiscal_year"]), r
        day = r.get("posting_date", r.get("date"))
        if day:
            assert iso.match(day), r
            # every source but SCPRS dates a payment inside its fiscal year; SCPRS dates are PO dates, which can
            # precede the fiscal year the PO is registered in
            if r["source"] != "ca_scprs":
                assert str(int(day[:4]) + (int(day[5:7]) >= 7)) == r["fiscal_year"], f"date outside fiscal year: {r}"
        else:
            assert r["source"] in ("ca_sf", "ca_scprs"), f"no date: {r}"
    for r in tot:
        assert re.fullmatch(r"-?\d+\.\d{2}", r["amount"]) and re.fullmatch(r"20\d\d", r["fiscal_year"]), r

    # 6. vendor map: payees classified the way pipeline/build.py classifies them (config/vendor_map.csv, then the
    #    vendor and keyword rules); proposals are folded into config/vendor_map.csv by merge_vendor_maps.py
    assert not (common.config_dir(ST) / "vendor_map_additions.csv").exists(), \
        "config/states/ca/vendor_map_additions.csv: fold it into config/vendor_map.csv (merge_vendor_maps.py)"
    spend = collections.Counter()
    for r in tx:
        spend[common.norm(r["payee_name"])] += cents(r["amount"])
    cov = vendor_coverage.Classifier().coverage(spend)
    share = cov["share_real"]
    assert share >= 0.90, f"vendor map gives a real category to {share:.1%} of purchasing dollars"
    report.append(f"vendor map: config/vendor_map.csv and the rules give a real category to {share:.1%} of "
                  f"${cov['purchasing'] / 100:,.0f} purchasing dollars (map {cov['by_map'] / cov['purchasing']:.1%}, "
                  f"rules {cov['by_rule'] / cov['purchasing']:.1%}; unclassified {cov['unclassified'] / cov['purchasing']:.1%})")

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
