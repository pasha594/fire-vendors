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
normalize  data/states/oh/transactions.csv.gz   one row per payment line
           config/states/oh/sources.csv         this source's row (fetched = date of the raw folder)
           data/states/oh/agencies.json         via common.assemble_agencies

Attribution: only department codes linked in config/states/oh/agency_sources.csv (source oh_cincinnati) are
fetched: 271 Fire - Response, 272 Fire - Support Services and the older 224 Department Of Fire (no rows after
FY2016). Not linked: 922 Police & Fire Fighter's Ins (insurance shared by police and fire) and 103 and 223
Emergency Communications (the 911 center serves police and fire). normalize fails when a department whose name
says fire is neither linked nor listed in NOT_FIRE, so a new fire code gets noticed. Purchases that other city
departments make for Fire (Fleet Services buying apparatus, the IT department buying radios or software) carry
those departments' codes and are not included.

Duplicates: (trans_id, trans_line_no) is unique in the source; exact duplicate lines would be kept once (none in
the 2026-10-06 pull). Lines with the same vendor, amount and date on one check are separate invoice lines and
are kept. Credits (mostly purchasing-card credits from U.S. Bank and Fifth Third) are negative lines and kept,
so they net out.

Payees: common.withhold_person, plus local rules (Payees.publish, missed_person) for names it misses ("Last First
M.", a generational suffix such as "III", "Mr Name", a trailing tag after "First M. Last"), and every payee of the
"Uniform And Other Allowance" account (payments to individual employees and retirees) is withheld. Business names
that common.looks_like_person over-matches ("UC HEALTH", "T-Mobile USA") are published when a reviewed row of
config/states/oh/vendor_map_additions.csv claims them, as config/vendor_map.csv rows do inside common. A name
common.is_person matches ("OHD, LLLP") stays withheld even when claimed.
"""
import collections
import csv
import decimal
import io
import json
import re
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
# Expense accounts whose payees are individual people (employees, retirees): always withheld.
PERSON_ACCOUNTS = {"Uniform And Other Allowance"}
SOURCE_COLUMNS = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]


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


# --- Payee names -----------------------------------------------------------------------------------------------

SUFFIX = re.compile(r",?\s+(JR|SR|II|III|IV)\.?$", re.I)
LAST_FIRST_INITIAL = re.compile(r"^[A-Za-z'\-]{2,} [A-Za-z'\-]{2,},? [A-Za-z]\.?$")      # "Wiley Ruth M."
FIRST_INITIAL_LAST = re.compile(r"^[A-Za-z'\-]{2,} [A-Za-z]\.? [A-Za-z'\-]{2,}$")          # "Michael W Earls"
TRAILING_TAG = re.compile(r"^(.+) [A-Za-z]{2,4}$")
HONORIFIC = re.compile(r"^(MR|MRS|MS|DR)\.? [A-Za-z'\-]{2,}( [A-Za-z'\-]{2,})?$", re.I)          # "MR NYREN"


def _claimed():
    """name_keys that a reviewed vendor_map_additions row claims as a business (any category but individuals)."""
    return {r["name_key"] for r in common.read_config(ST, "vendor_map_additions.csv") if r["category"] != "individuals"}


def _redactions():
    path = common.ROOT / "config" / "payee_name_redactions.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return [re.compile(r["pattern"], re.I) for r in csv.DictReader(f)]


def missed_person(name):
    """Person-name shapes common.withhold_person does not catch."""
    if common.BUSINESS_WORDS.search(name):
        return False
    base = SUFFIX.sub("", name).strip()
    if base != name and (common.is_person(base) or common.looks_like_person(base)):
        return True
    if LAST_FIRST_INITIAL.match(name) or HONORIFIC.match(name):
        return True
    m = TRAILING_TAG.match(name)
    return bool(m and FIRST_INITIAL_LAST.match(m.group(1)))


class Payees:
    def __init__(self):
        self.claimed, self.redact = _claimed(), _redactions()

    def publish(self, raw, account_desc):
        name = " ".join((raw or "").split())
        if account_desc in PERSON_ACCOUNTS:
            return common.withhold_person(name, person_flag=True)
        out = common.withhold_person(name)
        claimed = common.norm(name) in self.claimed
        if claimed and out == common.WITHHELD and not common.is_person(name):
            # withheld only by looks_like_person, which over-matches short company names; a reviewed
            # vendor_map_additions row says this one is a business (as vendor_map rows do inside common)
            out = "Payee name withheld" if any(rx.search(name) for rx in self.redact) else name
        if out == name and not claimed and missed_person(name):
            out = common.WITHHELD
        return out


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

    unique = {}
    for r in raw:
        unique.setdefault(tuple(r[c] for c in COLUMNS), r)
    dropped = len(raw) - len(unique)
    payees, ids, rows = Payees(), collections.Counter(), []
    cents = decimal.Decimal("0.01")
    for key in sorted(unique):
        r = unique[key]
        fy = int(r["fiscal_year"])
        assert fy >= FIRST_FY and r["dept_code"] in codes, f"row outside the fetch filter: {r}"
        rid = f"{r['trans_id']}-{r['trans_line_no']}"
        ids[rid] += 1
        if ids[rid] > 1:
            rid += f"#{ids[rid]}"
        rows.append({
            "agency_id": codes[r["dept_code"]]["agency_id"], "fiscal_year": str(fy),
            "posting_date": r["record_date"][:10],
            "payee_name": payees.publish(r["vendor_name"], r["exp_acct_cat_desc"]), "description": "",
            "account": " / ".join([r["dept_desc"], f"{r['fund_code']} {r['fund_desc']}",
                                   f"{r['exp_acct_cat']} {r['exp_acct_cat_desc']}"]),
            "category_published": r["exp_acct_cat_desc"],
            "amount": str(decimal.Decimal(r["amount"]).quantize(cents)), "source_record_id": rid,
        })
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    last = max(r["posting_date"] for r in rows)
    register_source({
        "source": SOURCE, "name": "City of Cincinnati Vendor Payments", "tier": "1",
        "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "City of Cincinnati FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": f"Cincinnati Fire Department only (department codes {', '.join(sorted(codes))}); purchases other "
                f"city departments make for Fire (fleet, IT) are not included; FY{years[-1]} partial (payments "
                f"through {last})"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    withheld = sum(r["payee_name"] == common.WITHHELD for r in rows)
    print(f"{ST}: {SOURCE}: {len(rows)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}; {dropped} exact duplicate "
          f"lines dropped; {withheld} lines with the payee withheld")


def register_source(row):
    path = common.config_dir(ST) / "sources.csv"
    rows = [r for r in common.read_config(ST, "sources.csv") if r["source"] != row["source"]] + [row]
    common.write_csv(path, SOURCE_COLUMNS, sorted(rows, key=lambda r: r["source"]))


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
