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

Duplicates and reversals: the source holds reloaded copies. (a) The same line (same unique_id, every column equal)
loaded again by a later extract: 108 lines, $4.6 million, from the extracts of 2024-12-07 and 2025-11-15 (for
example a $3,451,591 payment to the US Department of Agriculture twice). (b) Purchase-card lines loaded again under
new unique_ids in later loads, with no reversal: about 460 lines, $0.27 million, mostly the loads of 2024-08-21 and
2024-08-22, which consist almost entirely of such copies. (c) Blocks of purchase-card lines inserted twice inside
one load batch: 116 lines, $75,206, in 8 batches (2024-08-19 to 2025-07-07); the copies' unique_ids run in a
parallel series at a near-constant offset (all 26 copies of 2025-07-07 at +14,313 or +14,764) and include the same
airline ticket and marketplace order numbers twice. Rule (reloads): among lines identical in every column but
unique_id, date_of_load and zz_extract_date, keep the copies of the earliest load batch (date_of_load,
zz_extract_date) and drop copies from later batches (567 lines, $4.88 million); inside that batch keep only the
lowest unique_id when the batch inserts BLOCK_COPIES (4) or more such copies (116 lines). Identical lines inside a
batch with fewer copies are kept as possible repeat purchases (26 lines, $138,820, among them two $97,378.20
vehicles from one dealer on one day). In all 683 lines ($4.96 million) are dropped. fetch asserts each year's paging
matches the row count, normalize that no line appears twice in the raw files. unique_id can also be reused by a
different line (FY2021: a transfer and its reversal), so source_record_id is unique_id, or unique_id-<n> when the id
repeats (record_ids). Negative lines (credits, reversals, refunds) are kept, so amounts are net. Lines in
EXCLUDED_CATEGORIES are accounting entries, not payments (encumbrances, accrual adjustments, transfers), and are
dropped with their totals printed.

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
BLOCK_COPIES = 4  # same-batch identical copies that make a reloaded block (see reloads)
PAGE = 250
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


def reloads(rows):
    """Indexes of reloaded copies among lines identical in every column but unique_id and the load dates:
    (1) copies from a later load batch (date_of_load, zz_extract_date) than the first copy are dropped;
    (2) copies inside one batch are dropped, keeping the lowest unique_id, when that batch inserts BLOCK_COPIES or
    more lines twice (a block reloaded within one load: the copies' unique_ids run in a parallel series at a
    near-constant offset, and include airline tickets and marketplace orders with their own order numbers);
    identical lines inside a batch with fewer such copies are kept as possible repeat purchases."""
    batch = lambda i: (rows[i]["date_of_load"] or "", rows[i]["zz_extract_date"] or "")
    groups = collections.defaultdict(list)
    for i, r in enumerate(rows):
        groups[tuple((k, v) for k, v in sorted(r.items())
                     if k not in ("unique_id", "date_of_load", "zz_extract_date"))].append(i)
    drop, same_batch = set(), collections.defaultdict(list)  # batch -> [extra copies]
    for idx in groups.values():
        if len(idx) < 2:
            continue
        first = min(batch(i) for i in idx)
        drop |= {i for i in idx if batch(i) != first}
        kept = sorted((i for i in idx if batch(i) == first), key=lambda i: int(rows[i]["unique_id"]))
        same_batch[first] += kept[1:]
    for b, extra in same_batch.items():
        if len(extra) >= BLOCK_COPIES:
            drop |= set(extra)
    return drop


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
    drop = reloads(rows_in)
    print(f"  reloaded copies dropped: {len(drop)} lines, ${sum(rows_in[i]['amount'] or 0 for i in drop):,.0f}")
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
