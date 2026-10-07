"""Idaho state transactions (Transparent Idaho): payment lines of the Idaho Department of Lands fire program (tier 1).

    python3 pipeline/sources/id_state.py fetch
    python3 pipeline/sources/id_state.py normalize

Source: Transparent Idaho "Vendor Payments" -> "Transaction" report (Idaho State Controller's Office, hosted on
OpenGov Transparency Reporting): https://idaho.opengov.com/transparency-reporting/idaho/2b17eed6-3282-4416-ab38-
656795512745/9711ec09-4057-47c6-8ebc-1f27ee4261d3?savedViewId=79113c65-e697-4dd8-a78a-9e92aca0d6d8 (saved view
"Expenditure Transactions"). One row per accounting line of every state agency: fund, agency, agency function
(program), account type, account category, account, vendor, state fiscal year (July to June, the year it ends in),
effective date, load date and amount; 25.2 million expense lines, FY2020 to the current year on 2026-10-06. Lines
before FY2024 come from the legacy STARS system (function titles end in "(historical)"), later ones from Luma.

Access: the report page's own JSON API. GET /api/reporting_service/v2/reportConfigurations/<id> returns the saved
view; POST /api/reporting_service/v2/reports/<report>/queries/detailTable with that configuration (its filter
replaced) returns rows, at most 250 per request (larger pages fail with HTTP 500), paged with paginationOffset and
sorted on unique_id; queries/detailTableCount returns the row count. No login. robots.txt of idaho.opengov.com
disallows nothing. common.get has no POST, so post_json below does the same throttle and retries. The SCO terms of
use (https://www.sco.idaho.gov/LivePages/site-policies.aspx) say nothing about automated access but limit use of
site content to non-commercial, informational purposes; see docs/sources/id.md (open question).

Selection (server-side): agency_code_function_code = '320-07H' (agency 320 Department of Lands, function 07H Forest
and Range Fire Protection; titled "FIRE MANAGEMENT (historical)" in FY2020-21, "FOREST AND RANGE PROTECTION
(historical)" in FY2021-23, and "FOREST AND RANGE FIRE PROTECTN" plus "FOREST & RANGE FIRE PROTECTION-DEFICIENCY"
(fire suppression paid from deficiency warrants) from FY2024), account_type Expense, account category not
Personnel, one fiscal year at a time from FY2021. Personnel lines (wages, benefits, and employees' names as vendor)
are payroll, not vendor payments; their totals per year are kept in the control file. Function 03H "FOREST AND FIRE
(historical)" (forestry: Good Neighbor Authority, forest practices) is not clearly fire and is left out.

fetch      raw/<date>/id/id_state/robots.txt.gz          idaho.opengov.com/robots.txt
           raw/<date>/id/id_state/report.json.gz          report metadata (lens, entity)
           raw/<date>/id/id_state/report_config.json.gz   the saved view's configuration used for every query
           raw/<date>/id/id_state/lens.json.gz            column definitions
           raw/<date>/id/id_state/control.json.gz         per fiscal year: lines and dollars by account category for
                                                          320-07H expense lines, Personnel included
           raw/<date>/id/id_state/lines_fy<YYYY>.json.gz  {"columns": [...], "rows": [[...], ...]} every selected line
           raw/<date>/id/id_state/sample.json.gz          the first 100 lines of the unfiltered saved view
normalize  data/states/id/transactions.csv.gz   one row per line in a payment category (PAYMENT_CATEGORIES)
           config/states/id/sources.csv          this source's row
           data/states/id/agencies.json          via common.assemble_agencies

Attribution: all lines go to the registry's "Idaho Department of Lands Fire Department" (no FDID) through
config/states/id/agency_sources.csv. IDL is a state fire agency (PRD open question: main table or separate view).

Duplicates and reversals: owner rule of 2026-10-07 as corrected the same day ("drop identical lines, drop identical
days", applied to every column the source publishes, not only the contract columns), function dedup:
(1) Identical: two lines are identical when every column of the raw line is equal except the columns that only
identify the row or the load: unique_id (the portal's row id), date_of_load and zz_extract_date (load and extract
stamps); ROW_LOAD_IDS. Compared are the other 27 columns the saved view publishes: fund (category, type, title,
code), state goal and objective, agency, function, account type, account category, summary account, account,
vendor, fiscal year, effective date, amount, the empty zz_filler columns and the account number string. Idaho
publishes no voucher, invoice, check or PO number. (2) Upload errors first (rule of 2026-10-06, kept): copies of a
line from a later load batch (date_of_load, zz_extract_date) than its first copy (567 lines, $4,880,745.10: the same
unique_id loaded again by a later extract, and purchase-card lines loaded again under new unique_ids, mostly the
loads of 2024-08-21 and 2024-08-22), and blocks of purchase-card lines inserted twice inside one load batch, the
extra copies of a batch that holds BLOCK_COPIES or more (116 lines, $75,206.33; unique_ids in a parallel series at a
near-constant offset). In all 683 lines, $4,955,951.43. (3) Of the remaining identical lines, a set of n identical
positive lines keeps min(n, reversals + 1) copies, the earliest load batch's lowest unique_ids first, where
reversals counts the lines of the same fund, function, objective, account and vendor (REVERSAL_KEYS) with the
amount negated in the same or the next fiscal year, lines identical among themselves counting once; a set of
negative or zero lines keeps one. On the raw files of 2026-10-06 this drops 26 lines ($138,820.11, 25 sets; among
them two $97,378.20 vehicles from one dealer on one day, two $31,500 payments to one contractor, and one copy each of
a -$84 and a -$1,529.87 credit) and the void rule keeps none (no such set has a reversal); 709 lines dropped in all,
$5,094,771.54. The -$1,529.87 credit (no vendor, 2026-06-22) is reversed once by a +$1,529.87 line of FY2027, so
keeping it once raises that family's net from $0 as published to $1,529.87 (open question in docs/sources/id.md).
Two upload-error copies have a reversal of their amount: a $122.58 purchase-card line whose reversal moves the one
payment to another account, and a $116.77 hotel line whose reversal pairs with a later $116.77 line; they stay
dropped. fetch asserts each year's paging matches the row count, normalize that no line appears twice in
the raw files. unique_id can also be reused by a different line (FY2021: a transfer and its reversal), so
source_record_id is unique_id, or unique_id-<n> when the id repeats (record_ids). Negative lines (credits,
reversals, refunds) are kept, so amounts are net. Lines in EXCLUDED_CATEGORIES are accounting entries, not payments
(encumbrances, accrual adjustments, transfers), and are dropped with their totals printed.

Payees: shown as published, private persons included (owner decision of 2026-10-06): every vendor goes through
common.withhold_person, which only replaces payee text matching config/payee_name_redactions.csv (e-mail addresses,
bank account text) by "Payee name withheld". "REDACTED" is the State's own mask and is kept as published; lines
without a vendor have an empty payee_name.
"""
import collections
import json
import sys
import time
import urllib.request

import common

ST = "ID"
SOURCE = "id_state"
HOST = "https://idaho.opengov.com"
REPORT = "2b17eed6-3282-4416-ab38-656795512745"
CONFIG = "9711ec09-4057-47c6-8ebc-1f27ee4261d3"   # saved view "Expenditure Transactions"
FUNCTION = "320-07H"
FIRST_FY = 2021
PAGE = 250
ROW_LOAD_IDS = ("unique_id", "date_of_load", "zz_extract_date")  # row id and load stamps: not compared
BLOCK_COPIES = 4  # same-batch identical copies that make a block inserted twice (upload error)
REVERSAL_KEYS = ("fund_code", "agency_code_function_code", "state_objective_code", "account", "vendor")
AGENCY_ID = "ID-X-IDAHO-DEPARTMENT-OF-LANDS-FIRE-DEPARTMENT-COEUR-D-ALENE"
PAYMENT_CATEGORIES = {"Operating", "Capital Expenditures", "Trustee & Benefit Payments", "FED PAYMENTS TO SUBGRANTES",
                      "Refunds"}
EXCLUDED_CATEGORIES = {"Encumbrances": "commitments, not payments", "GAAP Expenses": "year-end accrual entries",
                       "Loss": "loss on asset disposal", "Operating Transfers Out": "transfers between funds",
                       "Other Financing Uses": "transfers between funds"}
SOURCE_ROW = {
    "source": SOURCE, "name": "Transparent Idaho state transactions (Idaho Department of Lands fire program)",
    "tier": "1",
    "url": f"{HOST}/transparency-reporting/idaho/{REPORT}/{CONFIG}?savedViewId=79113c65-e697-4dd8-a78a-9e92aca0d6d8",
    "fiscal_year": "Idaho state FY, Jul-Jun",
    "note": "Idaho Department of Lands Forest and Range Fire Protection program (agency 320, function 07H), "
            "including fire suppression paid from deficiency warrants; payroll left out; state fire agency",
}


def post_json(url, obj, tries=4, timeout=300):
    """POST JSON with common.get's throttle and retries. Returns the parsed answer."""
    data = json.dumps(obj).encode()
    for attempt in range(tries):
        time.sleep(common.DELAY)
        try:
            req = urllib.request.Request(url, data=data, method="POST",
                                         headers={**common.HEADERS, "Content-Type": "application/json",
                                                  "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == tries - 1:
                raise
            print(f"  retry {attempt + 1} after error: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def query(config, kind, filters, limit=PAGE, offset=0, sort="", group=None):
    c = json.loads(json.dumps(config))
    dq = c["detailTableQuery"]
    dq.update({"filter": filters, "filterBooleanOperators": [], "paginationLimit": limit, "paginationOffset": offset,
               "sortColumn": sort, "sortDirection": "ASC", "groupByColumns": group or []})
    c["visualizationQuery"].update({"filter": filters, "filterBooleanOperators": []})
    out = post_json(f"{HOST}/api/reporting_service/v2/reports/{REPORT}/queries/{kind}", c)
    assert out.get("state") == "finished", f"query not finished: {str(out)[:300]}"
    return out["jobResult"]


def where(fy, personnel=False):
    f = [{"operator": "equal", "value": FUNCTION, "columnName": "agency_code_function_code"},
         {"operator": "equal", "value": "Expense", "columnName": "account_type"},
         {"operator": "equal", "value": str(fy), "columnName": "fiscal_year"}]
    if not personnel:
        f.append({"operator": "notEqual", "value": "Personnel", "columnName": "account_category_0"})
    return f


def fetch():
    get = lambda path: common.get(HOST + path)
    common.save_raw(ST, SOURCE, "robots.txt", get("/robots.txt"))
    common.save_raw(ST, SOURCE, "report.json", get(f"/api/reporting_service/v2/reports/{REPORT}"))
    lens = get(f"/api/reporting_service/v2/reports/{REPORT}/lenses")
    common.save_raw(ST, SOURCE, "lens.json", lens)
    config = json.loads(get(f"/api/reporting_service/v2/reportConfigurations/{CONFIG}"))
    common.save_raw(ST, SOURCE, "report_config.json", json.dumps(config, indent=0, sort_keys=True).encode())
    sample = query(config, "detailTable", config["detailTableQuery"]["filter"], limit=100)
    common.save_raw(ST, SOURCE, "sample.json", json.dumps(sample, indent=0).encode())
    years = sorted(int(r[0]) for r in query(config, "detailTable", [{"operator": "equal", "value": FUNCTION,
                                                                       "columnName": "agency_code_function_code"}],
                                            group=["fiscal_year"])["data"])
    control = {}
    for fy in [y for y in years if y >= FIRST_FY]:
        by_cat = query(config, "detailTable", where(fy, personnel=True), group=["account_category_0"])
        control[str(fy)] = {r[0]: {"amount": r[1], "lines": r[-1]} for r in by_cat["data"]}
        expected = sum(v["lines"] for k, v in control[str(fy)].items() if k != "Personnel")
        for attempt in range(3):
            rows, columns = [], None
            while True:
                page = query(config, "detailTable", where(fy), offset=len(rows), sort="unique_id")
                columns = columns or [c["name"] for c in page["metadata"]["columns"]]
                rows += page["data"]
                if len(page["data"]) < PAGE:
                    break
            # unique_id is not unique (a reversal loaded later can reuse it), so a tie on a page boundary could
            # repeat one line and skip another: the year is good when the count matches and no line repeats.
            count = query(config, "detailTableCount", where(fy))["data"][0][0]
            repeated = len(rows) - len({json.dumps(r) for r in rows})
            if len(rows) == count and not repeated:
                break
            print(f"  FY{fy}: {len(rows)} lines, count {count}, {repeated} repeated; fetching the year again")
        else:
            raise AssertionError(f"FY{fy}: paging never matched the count")
        assert len(rows) >= expected, f"FY{fy}: {len(rows)} lines fetched, {expected} expected"
        common.save_raw(ST, SOURCE, f"lines_fy{fy}.json",
                        json.dumps({"columns": columns, "rows": rows}, separators=(",", ":")).encode())
        print(f"  FY{fy}: {len(rows)} lines (control {expected}), ${sum(r[columns.index('amount')] or 0 for r in rows):,.0f}")
    common.save_raw(ST, SOURCE, "control.json", json.dumps(control, indent=0, sort_keys=True).encode())


def lines(raw):
    """Every fetched line as a dict, oldest year first."""
    out = []
    for path in sorted(raw.glob("lines_fy*.json.gz")):
        d = json.loads(common.read_gz(path))
        out += [dict(zip(d["columns"], r)) for r in d["rows"]]
    return out


def dedup(rows):
    """Lines to drop (owner rule of 2026-10-07 as corrected; see the module docstring). Returns {index: reason},
    reason "later batch" or "doubled block" (upload errors, dropped first) or "identical" (rule 1 with the void
    rule), and the number of positive identical copies the void rule keeps."""
    content = lambda r: tuple((k, v) for k, v in sorted(r.items()) if k not in ROW_LOAD_IDS)
    order = lambda i: (rows[i]["date_of_load"] or "", rows[i]["zz_extract_date"] or "", int(rows[i]["unique_id"]))
    groups = collections.defaultdict(list)
    for i, r in enumerate(rows):
        groups[content(r)].append(i)
    drop, extra = {}, collections.defaultdict(list)  # load batch -> same-batch copies beyond the first
    for idx in groups.values():
        if len(idx) < 2:
            continue
        idx.sort(key=order)
        first = order(idx[0])[:2]
        for i in idx[1:]:
            if order(i)[:2] != first:
                drop[i] = "later batch"
            else:
                extra[first].append(i)
    for copies in extra.values():
        if len(copies) >= BLOCK_COPIES:
            drop.update(dict.fromkeys(copies, "doubled block"))
    left = [i for i in range(len(rows)) if i not in drop]
    reversals = collections.defaultdict(set)  # (REVERSAL_KEYS, amount, fiscal year) -> distinct negative lines
    for i in left:
        r = rows[i]
        if (r["amount"] or 0) < 0:
            reversals[(tuple(r[k] for k in REVERSAL_KEYS), -r["amount"], int(r["fiscal_year"]))].add(content(r))
    kept_by_void = 0
    for idx in groups.values():
        idx = [i for i in idx if i not in drop]
        if len(idx) < 2:
            continue
        r = rows[idx[0]]
        keep = 1
        if (r["amount"] or 0) > 0:
            key, fy = (tuple(r[k] for k in REVERSAL_KEYS), r["amount"]), int(r["fiscal_year"])
            n_rev = len(reversals.get((*key, fy), set()) | reversals.get((*key, fy + 1), set()))
            keep = min(len(idx), n_rev + 1)
            kept_by_void += keep - 1
        drop.update(dict.fromkeys(idx[keep:], "identical"))
    return drop, kept_by_void


def record_ids(rows):
    """source_record_id per line (by index): the source's unique_id, or unique_id-<n> when the source gives one
    unique_id to several lines (a reversal loaded later reuses it), numbered by load date, then content."""
    groups = collections.defaultdict(list)
    for i, r in enumerate(rows):
        groups[r["unique_id"]].append(i)
    out = {}
    for uid, idx in groups.items():
        if len(idx) == 1:
            out[idx[0]] = uid
            continue
        for n, i in enumerate(sorted(idx, key=lambda i: (rows[i]["date_of_load"] or "",
                                                          json.dumps(rows[i], sort_keys=True))), 1):
            out[i] = f"{uid}-{n}"
    return out


def normalize():
    raw = common.latest_raw(ST, SOURCE)
    assert raw, "run fetch first"
    rows_in = lines(raw)
    exact = collections.Counter(json.dumps(r, sort_keys=True) for r in rows_in)
    assert max(exact.values()) == 1, "a line appears twice in the raw files"
    drop, kept_by_void = dedup(rows_in)
    cents = lambda idx: sum(round((rows_in[i]["amount"] or 0) * 100) for i in idx)
    by_reason = {k: [i for i, w in drop.items() if w == k] for k in ("later batch", "doubled block", "identical")}
    print(f"  dropped: {len(drop)} lines, ${cents(drop) / 100:,.2f} (" + ", ".join(
        f"{k} {len(v)} lines ${cents(v) / 100:,.2f}" for k, v in by_reason.items())
        + f"); identical copies kept by the void rule: {kept_by_void}")
    rows_in = [r for i, r in enumerate(rows_in) if i not in drop]
    record_id = record_ids(rows_in)
    excluded, out = collections.defaultdict(lambda: [0, 0.0]), []
    for i, r in enumerate(rows_in):
        cat = r["account_category_0"]
        assert r["agency_code_function_code"] == FUNCTION and r["account_type"] == "Expense", r["unique_id"]
        if cat in EXCLUDED_CATEGORIES:
            excluded[cat][0] += 1
            excluded[cat][1] += r["amount"] or 0
            continue
        assert cat in PAYMENT_CATEGORIES, f"unknown account category {cat!r}: add it to PAYMENT_ or EXCLUDED_CATEGORIES"
        out.append({
            "agency_id": AGENCY_ID, "fiscal_year": r["fiscal_year"], "posting_date": r["effective_date"] or "",
            "payee_name": common.withhold_person(r["vendor"]),
            "description": "",
            "account": " / ".join(x for x in (f"{r['fund_code']} {r['fund_title']}", r["agency_function"], cat,
                                               f"{r['account']} {r['summary_account']}") if x and x.strip()),
            "category_published": r["summary_account"] or "",
            "amount": f"{r['amount']:.2f}", "source_record_id": record_id[i],
        })
    fields = [f for f in common.TABLES["transactions.csv.gz"] if f not in ("source", "source_record_id")]
    same = collections.Counter(tuple(r[f] for f in fields) for r in out)
    print(f"  rows equal to another in every published column (kept: they differ in a raw column or the void rule "
          f"keeps them): {sum(n for n in same.values() if n > 1)}")
    years = sorted({r["fiscal_year"] for r in out})
    write_source_row(f"{years[0]}-{years[-1]}", raw.parent.parent.name)
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, out)
    common.assemble_agencies(ST)
    by_year = collections.defaultdict(float)
    for r in out:
        by_year[r["fiscal_year"]] += float(r["amount"])
    print(f"{SOURCE}: {len(out)} lines, " + ", ".join(f"FY{y} ${v:,.0f}" for y, v in sorted(by_year.items())))
    print("  excluded: " + ", ".join(f"{k} {n} lines ${v:,.0f}" for k, (n, v) in sorted(excluded.items())))
    print(f"  unique_ids shared by different lines: {sum(1 for v in record_id.values() if '-' in v)} lines")


def write_source_row(years, fetched):
    """Replace this source's row in config/states/id/sources.csv, keep the others."""
    cols = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]
    rows = [r for r in common.read_config(ST, "sources.csv") if r["source"] != SOURCE]
    rows.append({**SOURCE_ROW, "years": years, "fetched": fetched})
    common.write_csv(common.config_dir(ST) / "sources.csv", cols, sorted(rows, key=lambda r: r["source"]))


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
