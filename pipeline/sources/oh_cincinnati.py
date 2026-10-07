"""City of Cincinnati vendor payments: payee lines for the Cincinnati Fire Department (OH-31015).

    python3 pipeline/sources/oh_cincinnati.py fetch
    python3 pipeline/sources/oh_cincinnati.py normalize

Source: data.cincinnati-oh.gov (Socrata) dataset qrj9-83t8 "City of Cincinnati Vendor Payments": every payment the
City makes to a vendor from FY2014 on, one row per payment line (trans_id + trans_line_no), with the paying
department, fund, expense account category, record date, check number, amount and vendor name. Refreshed weekly
from the Cincinnati Financial System. Licence: public domain. robots.txt allows the API (Crawl-delay: 1, which
common.get's 1-second throttle meets). Fiscal year is the City's, July to June, named for the year it ends in.

fetch      raw/<date>/oh/oh_cincinnati/meta.json.gz            Socrata metadata (columns, update time, licence)
           raw/<date>/oh/oh_cincinnati/departments.json.gz     every department code: rows, dollars, years
           raw/<date>/oh/oh_cincinnati/control_totals.json.gz  server-side count and sum per fiscal year and
                                                               department of the rows fetched (for the checks)
           raw/<date>/oh/oh_cincinnati/payments_NNN.csv.gz     rows of the linked fire department codes with
                                                               fiscal_year >= 2021, filtered server-side (SoQL)
           raw/<date>/oh/oh_cincinnati/sample.csv.gz           100 unfiltered rows
           raw/<date>/oh/oh_cincinnati/vehicle_accounts.json.gz  context only, not attributed: server-side totals
                                                               by vendor of the citywide vehicle accounts (981,
                                                               256) from fiscal year 2021, where the City buys
                                                               fire apparatus and ambulances (for the note)
normalize  data/states/oh/transactions.csv.gz   one row per payment line
           config/states/oh/sources.csv         this source's row (fetched = date of the raw folder)
           data/states/oh/agencies.json         via common.assemble_agencies

Attribution: only department codes linked in config/states/oh/agency_sources.csv (source oh_cincinnati) are
fetched: 271 Fire - Response, 272 Fire - Support Services and the older 224 Department Of Fire (no rows after
FY2016). Not linked: 922 Police & Fire Fighter's Ins (insurance shared by police and fire) and 103 and 223
Emergency Communications (the 911 center serves police and fire). normalize fails when a department whose name
says fire is neither linked nor listed in NOT_FIRE, so a new fire code gets noticed. Purchases that other city
departments or citywide accounts make for Fire carry those codes and are not included: above all fire apparatus
and ambulances, bought through the citywide vehicle account 981 "Motorized & Construction Equip" (FY2021 on:
$16.8 million to Vogelpohl Fire Equipment and $1.9 million to Halcore Group, more than 40% of what the fire codes
show), and Fleet Services repairs or IT purchases. The vendor alone does not make a line fire spend, so these stay
out; the sources.csv note states the gap, with the amount computed from vehicle_accounts.json.

Duplicates: owner rule of 2026-10-07 as corrected the same day (identical): two lines are identical when all
COLUMNS of the raw file are equal. The raw file has no row or load id (ROW_IDS is empty: the fetch does not select
Socrata's :id, and the dataset has no load timestamp); trans_id (the financial system's document), trans_line_no
(its line) and check_no (check or EFT number) are content, so separate invoice lines on one check are separate
payments. Identical lines are kept once; void-safe, a group of n identical positive lines keeps
min(n, reversals + 1), where reversals counts the distinct negative lines of the same department, fund, account
and vendor with the amount negated in the same or the next fiscal year (REVERSAL; a credit does not repeat the
document or check number of the payment it reverses). Identical voids (owner decision A of 2026-10-07): in a
family with a payment (same REVERSAL fields, amount up to sign, same or next fiscal year), identical negative copies
are dropped only together with identical positive copies of the family. (trans_id, trans_line_no) is unique in the
2026-10-06 pull, so no line is dropped. Credits (mostly purchasing-card credits from U.S. Bank and Fifth Third) are negative lines
and kept, so they net out.

Payees: published as the source has them (owner decision, 2026-10-06), through common.withhold_person, which
only cuts payee text with an email address or bank account text.
"""
import collections
import csv
import decimal
import io
import json
import sys

import common

ST = "OH"
SOURCE = "oh_cincinnati"
DOMAIN = "https://data.cincinnati-oh.gov"
DATASET = "qrj9-83t8"
FIRST_FY = 2021
PAGE = 50000
COLUMNS = ["fiscal_year", "acct_period", "dept_code", "dept_desc", "fund_code", "fund_desc", "exp_acct_cat",
           "exp_acct_cat_desc", "trans_id", "trans_line_no", "record_date", "check_no", "amount", "vendor_name"]
# Departments whose names match common.FIRE_NAME but are not the fire department.
NOT_FIRE = {"922": "Police & Fire Fighter's Ins: insurance shared by police and fire"}
# Citywide vehicle accounts (context for the note only; never attributed) and the apparatus and ambulance makers
# or dealers paid from 981 for the Fire Department: Vogelpohl Fire Equipment (fire apparatus dealer) and Halcore
# Group (Horton and Leader ambulances). Reviewed by hand on 2026-10-06.
VEHICLE_DEPTS = {"981": "Motorized & Construction Equip", "256": "Fleet Services"}
APPARATUS_VENDORS = {"Vogelpohl Fire Equipment, Inc.", "Halcore Group, Inc."}
SOURCE_COLUMNS = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]
# Owner rule of 2026-10-07 (corrected): raw columns that only identify the row or the load (none in this file)
ROW_IDS = ()
# a reversal (credit) of a line repeats these: department, fund, account category and vendor
REVERSAL = ("dept_code", "dept_desc", "fund_code", "fund_desc", "exp_acct_cat", "exp_acct_cat_desc", "vendor_name")


def linked_codes():
    rows = [r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == SOURCE]
    assert rows, f"no {SOURCE} rows in config/states/oh/agency_sources.csv"
    return {r["source_entity_id"]: r for r in rows}


def soql(params, fmt="json"):
    return common.get(f"{DOMAIN}/resource/{DATASET}.{fmt}", params)


def fire_where(codes):
    return "dept_code in (%s) AND fiscal_year >= %d" % (", ".join(f"'{c}'" for c in sorted(codes)), FIRST_FY)


def parse_csv(body):
    reader = csv.DictReader(io.StringIO(body.decode("utf-8")))
    return reader.fieldnames, list(reader)


def fetch():
    codes = linked_codes()
    print(f"{ST}: {SOURCE} metadata and department list")
    common.save_raw(ST, SOURCE, "meta.json", common.get(f"{DOMAIN}/api/views/{DATASET}.json"))
    common.save_raw(ST, SOURCE, "departments.json", soql({
        "$select": "dept_code, dept_desc, count(*) as n, sum(amount) as amount, min(fiscal_year) as fy_min, "
                   "max(fiscal_year) as fy_max",
        "$group": "dept_code, dept_desc", "$order": "dept_code, dept_desc", "$limit": 5000}))
    where = fire_where(codes)
    totals = soql({"$select": "fiscal_year, dept_code, count(*) as n, sum(amount) as amount", "$where": where,
                   "$group": "fiscal_year, dept_code", "$order": "fiscal_year, dept_code", "$limit": 5000})
    common.save_raw(ST, SOURCE, "control_totals.json", totals)
    expected = sum(int(t["n"]) for t in json.loads(totals))
    print(f"{ST}: {SOURCE} payments where {where} ({expected} rows)")
    got, page = 0, 0
    while True:
        body = soql({"$select": ", ".join(COLUMNS), "$where": where, "$order": "trans_id, trans_line_no, :id",
                     "$limit": PAGE, "$offset": page * PAGE}, "csv")
        fields, rows = parse_csv(body)
        assert fields == COLUMNS, f"columns changed: {fields}"
        if not rows:
            break
        page += 1
        common.save_raw(ST, SOURCE, f"payments_{page:03d}.csv", body)
        got += len(rows)
        if len(rows) < PAGE:
            break
    print(f"  {got} rows in {page} file(s)")
    assert got == expected, f"fetched {got} rows but the control query counted {expected}: the dataset changed " \
                            "during the fetch; delete today's raw folder for this source and fetch again"
    common.save_raw(ST, SOURCE, "sample.csv", soql({"$order": ":id", "$limit": 100}, "csv"))
    fetch_context()


def fetch_context():
    """Totals by vendor of the citywide vehicle accounts, fiscal year 2021 on: context for the note, never rows."""
    where = "dept_code in (%s) AND fiscal_year >= %d" % (", ".join(f"'{c}'" for c in sorted(VEHICLE_DEPTS)), FIRST_FY)
    common.save_raw(ST, SOURCE, "vehicle_accounts.json", soql({
        "$select": "dept_code, dept_desc, vendor_name, count(*) as n, sum(amount) as amount", "$where": where,
        "$group": "dept_code, dept_desc, vendor_name", "$order": "dept_code, vendor_name", "$limit": 50000}))


def apparatus_outside(d):
    """Dollars the citywide vehicle account 981 paid to fire apparatus and ambulance vendors (not attributed)."""
    path = d / "vehicle_accounts.json.gz"
    if not path.exists():
        return None
    return sum(decimal.Decimal(r["amount"]) for r in json.loads(common.read_gz(path))
               if r["dept_code"] == "981" and r["vendor_name"] in APPARATUS_VENDORS)


# --- Normalize -------------------------------------------------------------------------------------------------

def read_raw(d):
    rows = []
    for path in sorted(d.glob("payments_*.csv.gz")):
        fields, page = parse_csv(common.read_gz(path))
        assert fields == COLUMNS, f"{path.name}: columns changed: {fields}"
        rows += page
    return rows


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    codes = linked_codes()
    for r in json.loads(common.read_gz(d / "departments.json.gz")):
        if common.FIRE_NAME.search(r.get("dept_desc") or "") and r["dept_code"] not in codes \
                and r["dept_code"] not in NOT_FIRE:
            raise SystemExit(f"{SOURCE}: department {r['dept_code']} {r['dept_desc']!r} looks like fire: link it in "
                             "config/states/oh/agency_sources.csv or add it to NOT_FIRE")
    raw = read_raw(d)
    control = json.loads(common.read_gz(d / "control_totals.json.gz"))
    assert len(raw) == sum(int(t["n"]) for t in control), "raw rows do not match control_totals.json"

    kept, stats = identical(raw)
    ids, rows = collections.Counter(), []
    cents = decimal.Decimal("0.01")
    for key in sorted(kept):
        r, copies = kept[key]
        fy = int(r["fiscal_year"])
        assert fy >= FIRST_FY and r["dept_code"] in codes, f"row outside the fetch filter: {r}"
        for _ in range(copies):
            rid = f"{r['trans_id']}-{r['trans_line_no']}"
            ids[rid] += 1
            if ids[rid] > 1:
                rid += f"#{ids[rid]}"
            rows.append({
                "agency_id": codes[r["dept_code"]]["agency_id"], "fiscal_year": str(fy),
                "posting_date": r["record_date"][:10],
                "payee_name": common.withhold_person(r["vendor_name"]), "description": "",
                "account": " / ".join([r["dept_desc"], f"{r['fund_code']} {r['fund_desc']}",
                                       f"{r['exp_acct_cat']} {r['exp_acct_cat_desc']}"]),
                "category_published": r["exp_acct_cat_desc"],
                "amount": str(decimal.Decimal(r["amount"]).quantize(cents)), "source_record_id": rid,
            })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["posting_date"] for r in rows)
    outside = apparatus_outside(d)
    gap = f" (FY{years[0]}-FY{years[-1]}: ${outside / 1000000:.1f} million)" if outside else ""
    register_source({
        "source": SOURCE, "name": "City of Cincinnati Vendor Payments", "tier": "1",
        "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "City of Cincinnati FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": f"Cincinnati Fire Department only (department codes {', '.join(sorted(codes))}). Not included: fire "
                f"apparatus and ambulances, which the City buys through its citywide vehicle account 981{gap}, and "
                f"other purchases city departments make for Fire (fleet repairs, IT); P-card spend is paid to the "
                f"card banks, so those merchants are not shown; FY{years[-1]} partial (payments through {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    withheld = sum(r["payee_name"] == "Payee name withheld" for r in rows)
    print(f"{ST}: {SOURCE}: {len(rows)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; {stats['dropped']} "
          f"identical lines dropped (${stats['dropped_dollars']:,.2f}); void rule kept {stats['void_kept']} identical "
          f"lines (${stats['void_kept_dollars']:,.2f}); identical-void fix kept {stats['void_fix']} negative lines; "
          f"{withheld} lines with the payee withheld")


def identical(raw):
    """Owner rule of 2026-10-07 as corrected: raw lines equal in every column but ROW_IDS are identical and kept
    once; a group of n identical positive lines keeps min(n, reversals + 1), reversals being the distinct negative
    lines with the same REVERSAL fields, the amount negated, in the group's fiscal year or the next; identical
    negative copies of a family with a payment go only with identical positive copies of the family. Returns
    {identity: (line, copies kept)} and the counts for the report."""
    groups = collections.defaultdict(list)
    for r in raw:
        groups[tuple(r[c] for c in COLUMNS if c not in ROW_IDS)].append(r)
    reversals = collections.defaultdict(set)
    for k, g in groups.items():
        if decimal.Decimal(g[0]["amount"]) < 0:
            reversals[(tuple(g[0][c] for c in REVERSAL), -decimal.Decimal(g[0]["amount"]))].add(
                (int(g[0]["fiscal_year"]), k))
    keep, stats = {}, collections.Counter()
    for k, g in groups.items():
        amount, fy, keep[k] = decimal.Decimal(g[0]["amount"]), int(g[0]["fiscal_year"]), 1
        if amount > 0 and len(g) > 1:
            n_rev = sum(y in (fy, fy + 1) for y, _ in reversals[(tuple(g[0][c] for c in REVERSAL), amount)])
            keep[k] = min(len(g), n_rev + 1)
            stats["void_kept"] += keep[k] - 1
            stats["void_kept_dollars"] += (keep[k] - 1) * amount
    # identical voids (owner decision A of 2026-10-07): in a family (same REVERSAL fields, amount up to sign, fiscal
    # years chained by same or next year) that has a payment, identical negative copies are dropped only as often as
    # the family's identical positive copies (negative groups in the order of their raw columns), so the family keeps
    # its raw net; a family without payments keeps each identical negative line once
    by_key = collections.defaultdict(lambda: collections.defaultdict(list))
    for k, g in groups.items():
        if decimal.Decimal(g[0]["amount"]) != 0:
            by_key[(tuple(g[0][c] for c in REVERSAL), abs(decimal.Decimal(g[0]["amount"])))][
                int(g[0]["fiscal_year"])].append(k)
    families = []
    for key in sorted(by_key):
        prev = None
        for y in sorted(by_key[key]):
            if prev is None or y > prev + 1:
                families.append([])
            families[-1] += by_key[key][y]
            prev = y
    for fam in families:
        if not any(decimal.Decimal(groups[k][0]["amount"]) > 0 for k in fam):
            continue
        allowed = sum(len(groups[k]) - keep[k] for k in fam if decimal.Decimal(groups[k][0]["amount"]) > 0)
        for k in sorted(k for k in fam if decimal.Decimal(groups[k][0]["amount"]) < 0):
            drop_n = min(len(groups[k]) - 1, allowed)
            allowed -= drop_n
            stats["void_fix"] += len(groups[k]) - drop_n - keep[k]
            keep[k] = len(groups[k]) - drop_n
    kept = {}
    for k, g in groups.items():
        kept[k] = (g[0], keep[k])
        stats["dropped"] += len(g) - keep[k]
        stats["dropped_dollars"] += (len(g) - keep[k]) * decimal.Decimal(g[0]["amount"])
    return kept, stats


def register_source(row):
    path = common.config_dir(ST) / "sources.csv"
    rows = [r for r in common.read_config(ST, "sources.csv") if r["source"] != row["source"]] + [row]
    common.write_csv(path, SOURCE_COLUMNS, sorted(rows, key=lambda r: r["source"]))


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
