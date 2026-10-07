"""Ohio Checkbook, local governments: payee lines of Ohio fire districts and of township, city and village fire
funds and fire departments.

    python3 pipeline/sources/oh_checkbook_local.py fetch [--date YYYY-MM-DD] [--only NAME ...]
    python3 pipeline/sources/oh_checkbook_local.py fetch220 --date YYYY-MM-DD [--only NAME ...]
    python3 pipeline/sources/oh_checkbook_local.py normalize

Source: Ohio Checkbook (checkbook.ohio.gov; ohiocheckbook.gov and the old <entity>.ohiocheckbook.com hosts
redirect there), local government pages. Participation is voluntary (ORC 113.74); each local government uploads
its own payments. The pages are Tableau dashboards on the State's Tableau Server (analytics.das.ohio.gov, site
INTBUD, one workbook per kind of government). The page itself asks checkbook.ohio.gov for a Tableau trusted
ticket (WebServices/Tableau.asmx/GetUniqueId, no CAPTCHA; the reCAPTCHA on the page guards only the contact
form) and opens the view with it. This adapter makes the same calls a browser makes for that page, then asks the
view for its underlying rows the way the embedded Tableau API's getUnderlyingTableDataAsync does
(tabdoc/api-get-worksheet-underlying-logical-table-data) and for the chart's summary totals
(tabdoc/api-get-worksheet-summary-logical-table-data), after setting the dashboard's own filters (Municipality
Name, Fund, Department, Year) with tabdoc/categorical-filter, as the page's filter controls do. No login,
CAPTCHA or other access control is passed. The owner allowed ignoring checkbook.ohio.gov's robots.txt
("Disallow: *") on 2026-10-06; requests are still one at a time, at least DELAY seconds apart, with the project's
user agent.

TLS: checkbook.ohio.gov sends its leaf certificate without the Sectigo "Public Server Authentication CA OV R36"
intermediate. fetch downloads that intermediate once from the leaf certificate's AIA caIssuers URL
(INTERMEDIATE_URL), checks its SHA-256 (INTERMEDIATE_SHA256), keeps it as a raw file and adds it to the
verification store. Verification stays on: the partial-chain flag Python 3.13 sets is cleared, so the chain must
still end at a root in the system store.

fetch220   raw/<date>/oh/oh_checkbook_local/program220_<id>.json.gz   per township with program 220 values not
             named for fire: the program 220 lines of its funds not named for fire, and the summary totals of its
             police-named funds and departments (pass --date of the folder the entity files are in)
fetch      raw/<date>/oh/oh_checkbook_local/
             sectigo_ov_r36_intermediate.crt.gz    the missing intermediate certificate (DER)
             participants_<kind>.json.gz           participant lists (MunicipalitiesByCategory web service)
             entity_<id>.json.gz                   per fire entity: its filter domains and the verbatim
                                                   responses of every underlying-rows and summary request,
                                                   with the filters that were set
             screen.json.gz                        every screened participant's Fund and Department filter
                                                   values (taken from the dashboard's filter controls after
                                                   choosing the participant; the 0.6 MB Tableau responses
                                                   they come from are not kept) and what was fetched
             sample.csv.gz                         100 raw rows (first entity file, columns as published)
normalize  data/states/oh/transactions.csv.gz     one row per published payment line (source oh_checkbook_local)
           config/states/oh/sources.csv           this source's row
           data/states/oh/agencies.json           via common.assemble_agencies

What is fire spend (docs/sources/oh.md): a fire district's whole checkbook (special districts named as fire
districts; an EMS-only district is not a fire agency, owner decision 2026-10-06); for townships, cities and
villages the lines whose fund or department is named for fire (FIRE_NAME, minus NOT_FIRE_NAME: shared
police-and-fire names, fire-loss insurance escrow, hydrants). Townships also count every line of program 220
(fire protection in the township chart of accounts, shown as "Public Safety - 220" or "220 - 220"; owner
decision of 2026-10-07), fetched by fetch220 for the funds not named for fire; a township line whose fund or
department is named for police never counts, so a township that also runs police (a police-named fund or
department with lines from FIRST_FY on, from the dashboard's summary totals) has its mixed Public Safety lines
left out, and its link note says so. EMS-only funds or departments are not fire lines. When a participant's
fire-named department also carries lines of a police fund, its department code is shared with police and only
its fire funds count (dept_trusted). Only participants linked in config/states/oh/agency_sources.csv reach the
data: a participant is linked when it runs the fire department named in the registry (place name and county)
and its fire lines are that department's spending; townships that pay another department by contract, and
participants whose fire lines are only a grant, capital or debt fund, are not linked (docs/sources/oh.md lists
them).

Fiscal year: Ohio local governments use the calendar year (fy_start 01); fiscal_year is the transaction date's
year. Years 2021 on.

Duplicates and broken uploads (normalize): rows are keyed by the checkbook's row Id; a row fetched twice
(overlapping requests) is kept once. A month uploaded k times: a month of DOUBLED_MIN lines or more in which every
group of lines identical in date, payee, fund, department, object and amount has a size divisible by k >= 2
keeps size/k lines of each group (Beavercreek Township, March 2023). A later upload (TransactionId jump of more
than RELOAD_GAP) whose lines of a date only repeat lines already uploaded for that date is a reload and dropped
(Perkins Township (Erie), December 2025 and January 2026). A month whose lines carry batch totals
instead of line amounts (BROKEN_SHARE rule; Jackson Township (Stark), City of Dover and City of Bellevue,
2025-2026) is left out. Then the owner's rule of 2026-10-07 as corrected the same day (unidentical): two lines
are identical when every column of the raw rows is equal except the row and load ids ROW_IDS (the checkbook's row
Id and the TransactionId it numbers lines with in upload order; the source has no load timestamp and publishes
no invoice, check, voucher or PO number, so its payment Type code, date, payee, fund, department, object and
amount are the content compared). Identical lines are kept once, the lowest row Id, which covers lines
re-uploaded under a new row Id and days doubled inside one upload (Hamilton Township (Warren), January-February
2021). Void-safe: a group of n identical positive lines keeps min(n, reversals + 1) of them, the lowest row Ids,
where reversals counts the distinct lines (identical reversals once) of the same participant, payee, fund,
department and object with the amount negated, dated in the group's year or the next (REVERSAL); so a payment,
its void and its identical reissue keep their net. Negative amounts (voids, refunds, reversals) are kept so they
net out. Identical voids (owner decision A of 2026-10-07): in a payment and reversal family (same REVERSAL fields,
amount up to sign, negative lines joined to the payments of their year and the year before) that has a payment,
identical negative copies are dropped only as often as the family's identical positive copies, so the family keeps
its raw net; identical negative lines of a family without payments are kept once. Every fetched slice is checked
against the dashboard's own summary totals for the same filters, per year.
"""
import argparse
import collections
import datetime
import decimal
import hashlib
import http.cookiejar
import io
import json
import math
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import common

ST = "OH"
SOURCE = "oh_checkbook_local"
UA = "Mozilla/5.0 (compatible; utah-fire-procurement/0.1; +https://github.com/pasha594/utah-fire-procurement)"
CHECKBOOK = "https://checkbook.ohio.gov"
TABLEAU = "https://analytics.das.ohio.gov"
SITE = "INTBUD"
INTERMEDIATE_URL = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"
INTERMEDIATE_SHA256 = "6542d176bed50f193c0ce297ae44ecd8a0a86bec2ede682769344059b4e78530"
INTERMEDIATE_FILE = "sectigo_ov_r36_intermediate.crt"
FIRST_FY = 2021
ROW_CAP = 10000  # the server returns at most 10,000 underlying rows per request; larger slices are split

# kind: (participant category in the web service, workbook, view, dashboard sheet)
KINDS = {
    "special_districts": ("Special Districts", "ExpenseSpecialDistricts", "DashboardSpecialDistricts",
                          "Dashboard | Special Districts"),
    "townships": ("Townships", "ExpenseTownships", "DashboardTownships", "Dashboard | Townships"),
    "cities_villages": ("Cities & Villages", "ExpenseCitiesandVillages_15905053238820", "DashboardCitiesandVillages",
                        "Dashboard | Cities and Villages"),
}
CHART = "Bar | SOH"  # the dashboard's default chart; its underlying rows are every transaction behind it

FIRE_NAME = re.compile(r"\bFIRE(S|FIGHTERS?|FIGHTING|MEN|MEN'?S)?\b", re.I)
# shared police-and-fire names, water hydrants, fire-loss insurance escrow (ORC 3929.86 "fire damaged structures"
# funds), fireworks permits, and wage garnishments passed through to creditors
NOT_FIRE_NAME = re.compile(r"POLICE|HYDRANT|FIRE ?LOSS|FIREWORK|INSURANCE|ESCROW|DAMAGED? STRUCTURE|GARNISH|"
                           r"FIRE DAMAGE|REPAIR ?(AND|/|&) ?REMOVAL|CLEAN ?UP", re.I)
# fire-loss insurance escrow funds pay insurance proceeds back to owners of burned buildings or to demolition
# contractors (City of Steubenville "FIRE DAMAGE REMOVAL", Village of Gallipolis "FIRE LOSS RECOVERY", City of
# Tallmadge "FIRE REPAIR/REMOVAL FUND", Jackson Township (Mahoning) "FIRE INSURANCE CLAIM CLEAN UP ESCROW"): such a
# fund or department name excludes the line even when the other one is named for fire
ESCROW_NAME = re.compile(r"FIRE ?LOSS|ESCROW|DAMAGED? STRUCTURE|FIRE DAMAGE|REPAIR ?(AND|/|&) ?REMOVAL|CLEAN ?UP",
                         re.I)
# A month whose upload carries batch totals instead of line amounts: most of its lines share their date and amount
# with at least two other lines paid to other payees for other objects (Jackson Township (Stark), City of Dover,
# City of Bellevue, 2025-2026: every line of a day shows the same $0.5-5.6 million). Its lines are dropped. Equal
# amounts paid to several people for the same object (York Township (Athens), November 2022: seven $500
# firefighter reimbursements) are real lines and do not count.
BROKEN_SHARE = decimal.Decimal("0.5")
POLICE_FUND = re.compile(r"POLICE", re.I)
# Owner decision of 2026-10-07 (Ohio Public Safety): a linked township's program 220 lines count as fire spend
# (program 220 is fire protection in the township chart of accounts), except lines in a police-named fund or
# department; police-named lines of a township never count
PROGRAM_220 = "220"
DOUBLED_MIN = 10  # lines in a month before the month can be judged as uploaded twice
# Reloads: TransactionIds are numbered in upload order, so a participant's lines sorted by TransactionId fall into
# uploads, a new one starting where the TransactionId jumps by more than RELOAD_GAP. A later upload's lines of one
# date (RELOAD_MIN or more, none negative) that are each an exact copy of a line of that date in an earlier upload
# are a reload (Perkins Township (Erie): 2025-12-18 and 2026-01-09 uploaded again about 1.1 million TransactionIds
# later). Identical lines left after these rules are kept once by unidentical (owner rule of 2026-10-07), copies
# of a voided and reissued payment as many times as it has reversals plus one, identical voids of a payment family
# as often as needed to keep its net (owner decision A of 2026-10-07).
RELOAD_GAP = 100000
RELOAD_MIN = 3
# Special districts that are fire agencies (whole checkbook), and the ones whose name suggests fire or EMS but
# which are not fire agencies, by participant name.
FIRE_DISTRICT = re.compile(r"\bFIRE\b", re.I)
EMS_ONLY = {"Joint Emergency Medical Service": "EMS-only joint district (no fire service); excluded by the owner's "
                                               "rule for EMS-only districts"}
SKIP = {"City of Cincinnati": "Cincinnati Fire Department comes from the City's own vendor payments (oh_cincinnati); "
                              "taking it here as well would count it twice"}
SOURCE_COLUMNS = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]
CENTS = decimal.Decimal("0.01")
IDENTICAL = {}  # participant -> (identical lines dropped, dollars), for the normalize report
# Owner rule of 2026-10-07 (corrected): columns that only identify the row or the load, never compared. Id is the
# checkbook's row id; TransactionId is the number the checkbook gives each line in upload order (not a document
# number of the local government). Every other raw column is content, including the payment Type code and the
# dashboard's calculated columns (labels built from the fund, department, object, date, payee and amount).
ROW_IDS = ("Id", "TransactionId")
# a reversal of a line repeats these (participant, payee and account); the source publishes no document number
REVERSAL = ("MuniName", "Payee", "FundCode", "FundDescription", "DeptCode", "DeptDescription", "ObjCode",
            "ObjDescription")
PROGRAM220 = {}  # township -> program 220 lines added, police years, police-named program 220 lines left out


def fire_line_name(name):
    return bool(FIRE_NAME.search(name or "")) and not NOT_FIRE_NAME.search(name or "")


# --- HTTP ---------------------------------------------------------------------------------------------------

class Client:
    """One request at a time, at least common.DELAY seconds apart, cookies kept, TLS verified."""

    def __init__(self, date):
        self.date = date
        self.last = 0.0
        self.jar = http.cookiejar.CookieJar()
        self.ctx = ssl.create_default_context()
        if hasattr(ssl, "VERIFY_X509_PARTIAL_CHAIN"):
            self.ctx.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
        der = self.intermediate()
        self.ctx.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(der))
        self.opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=self.ctx),
                                                  urllib.request.HTTPCookieProcessor(self.jar))

    def intermediate(self):
        path = common.raw_dir(ST, SOURCE, self.date) / (INTERMEDIATE_FILE + ".gz")
        if path.exists():
            der = common.read_gz(path)
        else:
            self.wait()
            req = urllib.request.Request(INTERMEDIATE_URL, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                der = r.read()
        digest = hashlib.sha256(der).hexdigest()
        assert digest == INTERMEDIATE_SHA256, f"intermediate certificate changed: sha256 {digest}"
        common.save_raw(ST, SOURCE, INTERMEDIATE_FILE, der, date=self.date)
        return der

    def wait(self):
        pause = common.DELAY - (time.monotonic() - self.last)
        if pause > 0:
            time.sleep(pause)
        self.last = time.monotonic()

    def request(self, url, data=None, headers=None, tries=4, timeout=300):
        for attempt in range(tries):
            self.wait()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})},
                                         method="POST" if data is not None else "GET")
            try:
                with self.opener.open(req, timeout=timeout) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                body = e.read()[:300]
                if e.code < 500 or attempt == tries - 1:
                    raise RuntimeError(f"HTTP {e.code} for {url}: {body!r}") from None
                print(f"  retry {attempt + 1} after HTTP {e.code}", file=sys.stderr)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == tries - 1:
                    raise
                print(f"  retry {attempt + 1} after error: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))

    def cookie(self, name):
        for c in self.jar:
            if c.name == name and c.domain.endswith("analytics.das.ohio.gov"):
                return c.value
        return None


def multipart(fields):
    boundary = uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n".encode())
        out.write(str(v).encode("utf-8") + b"\r\n")
    out.write(f"--{boundary}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={boundary}"


# --- Checkbook and Tableau --------------------------------------------------------------------------------

def participants(client, category):
    body = client.request(f"{CHECKBOOK}/WebServices/Municipalities.asmx/MunicipalitiesByCategory",
                          json.dumps({"category": category}).encode(),
                          {"Content-Type": "application/json; charset=utf-8",
                           "Referer": f"{CHECKBOOK}/Local/"})
    return body, json.loads(json.loads(body)["d"])


def login(client, kind, name):
    """What the page does: ask checkbook.ohio.gov for a trusted ticket, open the view with it (sets the Tableau
    session cookie). The page retries every 10 seconds when the ticket service fails; so does this."""
    _, workbook, view, _ = KINDS[kind]
    for attempt in range(6):
        body = client.request(f"{CHECKBOOK}/WebServices/Tableau.asmx/GetUniqueId", b"",
                              {"Content-Type": "application/json; charset=utf-8", "Referer": f"{CHECKBOOK}/Local/"})
        ticket = json.loads(body)["d"]
        if len(ticket) == 49:
            break
        print(f"  ticket service: {ticket[:80]!r}; waiting", file=sys.stderr)
        time.sleep(10)
    else:
        raise RuntimeError("no Tableau ticket from checkbook.ohio.gov")
    q = urllib.parse.urlencode({":embed": "y", ":render": "true", "Municipality Name": name}, quote_via=urllib.parse.quote)
    client.request(f"{TABLEAU}/trusted/{ticket}/t/{SITE}/views/{workbook}/{view}?{q}")
    assert client.cookie("workgroup_session_id"), "Tableau session cookie not set"


def tableau_parts(body):
    """bootstrapSession bodies are '<length>;<json>' repeated."""
    text, out, i = body.decode("utf-8"), [], 0
    while i < len(text):
        j = text.index(";", i)
        n = int(text[i:j])
        out.append(json.loads(text[j + 1:j + 1 + n]))
        i = j + 1 + n
    return out


def domains(obj):
    """{filter caption: [values]} from every filtersJson in a Tableau response (the dashboard's filter controls)."""
    found = {}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "filtersJson" and isinstance(v, str):
                    for f in json.loads(v):
                        tab = f.get("table")
                        if isinstance(tab, dict) and tab.get("tuples"):
                            vals = [str(t["t"][0]["v"]) for t in tab["tuples"] if t.get("t")]
                            found.setdefault(f.get("caption"), [])
                            found[f.get("caption")] += [v for v in vals if v not in found[f.get("caption")]]
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return found


class Viz:
    """One Tableau viewing session for a workbook; participants are switched with the Municipality Name filter."""

    def __init__(self, client, kind):
        self.client, self.kind = client, kind
        _, self.workbook, self.view, self.dashboard = KINDS[kind]
        self.root = f"{TABLEAU}/vizql/t/{SITE}/w/{self.workbook}/v/{self.view}"

    def start(self, name):
        if not self.client.cookie("workgroup_session_id"):
            login(self.client, self.kind, name)
        q = urllib.parse.urlencode({":embed": "y", ":render": "true", "Municipality Name": name},
                                   quote_via=urllib.parse.quote)
        ss = json.loads(self.client.request(f"{self.root}/startSession/viewing?{q}", b"", self.headers()))
        self.sid, sheet = ss["sessionid"], urllib.parse.unquote(ss["sheetId"])
        assert sheet == self.dashboard, f"{self.kind}: dashboard is {sheet!r}"
        form = {"sheet_id": sheet, "worksheetPortSize": '{"w":1000,"h":800}', "dashboardPortSize": '{"w":1000,"h":800}',
                "clientDimension": '{"w":1000,"h":800}', "renderMapsClientSide": "true", "isBrowserRendering": "true",
                "browserRenderingThreshold": "100", "formatDataValueLocally": "false", "navType": "Reload",
                "navSrc": "Top", "devicePixelRatio": "1", "clientRenderPixelLimit": "25000000",
                "showParams": ss.get("showParams") or "{}",
                "filterTileSize": "200", "locale": "en_US", "language": "en", "verboseMode": "false",
                "keychain_version": "1"}
        body = self.client.request(f"{self.root}/bootstrapSession/sessions/{self.sid}",
                                   urllib.parse.urlencode(form).encode(),
                                   {**self.headers(), "Content-Type": "application/x-www-form-urlencoded"})
        boot = domains(tableau_parts(body))
        self.filters = {}
        # the URL filter is not always applied to the session; set it as the page's filter control does (when it
        # was applied, the command changes nothing and its response carries no filter lists: keep the bootstrap's)
        return self.set_filter("Municipality Name", [name]) or boot

    def headers(self):
        return {"X-XSRF-TOKEN": self.client.cookie("XSRF-TOKEN") or "", "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json"}

    def command(self, name, fields):
        body, ctype = multipart(fields)
        out = self.client.request(f"{self.root}/sessions/{self.sid}/commands/tabdoc/{name}", body,
                                  {**self.headers(), "Content-Type": ctype})
        data = json.loads(out)
        assert "vqlCmdResponse" in data, f"{name}: unexpected response {out[:200]!r}"
        return out, data

    def visual(self):
        return json.dumps({"worksheet": CHART, "dashboard": self.dashboard})

    def set_filter(self, caption, values):
        """values None = all values (the filter control's 'All')."""
        if self.filters.get(caption) == values:
            return None
        fields = {"visualIdPresModel": self.visual(), "qualifiedFieldCaption": caption, "exclude": "false"}
        if values is None:
            fields["filterUpdateType"] = "filter-all"
        else:
            fields["filterUpdateType"] = "filter-replace"
            fields["filterValues"] = json.dumps(values)
        _, data = self.command("categorical-filter", fields)
        self.filters[caption] = values
        return domains(data)

    def underlying(self):
        return self.command("api-get-worksheet-underlying-logical-table-data", {
            "visualIdPresModel": self.visual(), "versionName": "1.0", "showDataTableId": "single-table-id-sentinel",
            "maxRows": "0", "ignoreAliases": "false", "ignoreSelection": "true", "includeAllColumns": "true"})

    def summary(self):
        return self.command("api-get-worksheet-summary-logical-table-data", {
            "visualIdPresModel": self.visual(), "versionName": "1.0", "showDataTableId": "single-table-id-sentinel",
            "maxRows": "0", "ignoreAliases": "false", "ignoreSelection": "true"})


def table_rows(data):
    """Rows of an underlying or summary data response: list of {column name: value as published}."""
    ret = data["vqlCmdResponse"]["cmdResultList"][0]["commandReturn"]
    if not ret:
        return []  # the server returns an empty commandReturn when no row matches the filters
    dt = ret["dataTablePresModel"]
    t = json.loads(dt["showDataTable"])["table"]
    captions = {c["uniqueName"]: c["fieldCaption"] for c in dt.get("showDataTableColumnPresModels", [])}
    cols = []
    for c in t["schema"]:
        base = c.split("].[")[-1].rstrip("]")
        cols.append(base if not base.startswith(("Calculation_", "yr:", "sum:", "none:")) else captions.get(c, base))
    return [dict(zip(cols, x)) for x in t["tuples"]]


# --- fetch ------------------------------------------------------------------------------------------------

def fire_slices(kind, name, funds, depts):
    """Filter sets whose union is the entity's fire lines, without overlap."""
    if kind == "special_districts":
        return [("all", {})]
    # inclusive at fetch time (any name with "fire"); normalize applies the exclusions in NOT_FIRE_NAME
    fire_funds = [f for f in funds if FIRE_NAME.search(f)]
    fire_depts = [d for d in depts if FIRE_NAME.search(d)]
    other_funds = [f for f in funds if f not in fire_funds]
    out = []
    if fire_funds:
        out.append(("fire_funds", {"Fund": fire_funds}))
    if fire_depts and other_funds:
        out.append(("fire_departments", {"Fund": other_funds, "Department": fire_depts}))
    return out


def fetch_slice(viz, filters, years, log):
    """Set the slice's filters, record the chart's summary totals, then the underlying rows; split by year (2021
    on) and then by object when a request reaches the server's row cap."""
    for cap in ("Fund", "Department", "Year Of Transaction Date", "Object"):
        viz.set_filter(cap, filters.get(cap))
    raw, _ = viz.summary()
    log.append({"kind": "summary", "filters": filters, "body": raw.decode("utf-8")})
    raw, data = viz.underlying()
    n = len(table_rows(data))
    muni = {r.get("MuniName") for r in table_rows(data)}
    assert muni <= {viz.filters["Municipality Name"][0]}, f"rows of another participant: {sorted(muni)[:3]}"
    if n < ROW_CAP:
        log.append({"kind": "rows", "filters": filters, "rows": n, "body": raw.decode("utf-8")})
        return n
    total = 0
    for y in filters.get("Year Of Transaction Date") or [y for y in years if int(y) >= FIRST_FY]:
        dom = viz.set_filter("Year Of Transaction Date", [y]) or {}
        raw, data = viz.underlying()
        k = len(table_rows(data))
        if k < ROW_CAP:
            log.append({"kind": "rows", "filters": {**filters, "Year Of Transaction Date": [y]}, "rows": k,
                        "body": raw.decode("utf-8")})
            total += k
            continue
        for obj in dom.get("Select Object", []):
            viz.set_filter("Object", [obj])
            raw, data = viz.underlying()
            k = len(table_rows(data))
            assert k < ROW_CAP, f"{filters} {y} {obj}: still {k} rows"
            log.append({"kind": "rows", "filters": {**filters, "Year Of Transaction Date": [y], "Object": [obj]},
                        "rows": k, "body": raw.decode("utf-8")})
            total += k
        viz.set_filter("Object", None)
    viz.set_filter("Year Of Transaction Date", None)
    return total


def order_entities(lists):
    """Fire districts first, then townships and cities by the career firefighters of the registry department
    with the same base name in the same county (a rough pre-match used only for ordering)."""
    reg = collections.defaultdict(int)
    for a in common.read_config(ST, "agencies.csv"):
        base = re.sub(r"\b(fire|department|division|dept|township|twp|volunteer|and|rescue|ems|district|joint|inc)\b",
                      " ", a["name"].lower())
        reg[(" ".join(re.sub(r"[^a-z ]", " ", base).split()), a["county"])] += int(a["career"] or 0)
    out = []
    for kind, people in lists.items():
        for p in people:
            base = re.sub(r"\s*\(.*\)$", "", p["Name"]).lower()
            base = re.sub(r"^(city|village) of |\btownship\b", " ", base)
            base = " ".join(re.sub(r"[^a-z ]", " ", base).split())
            fire_sd = kind == "special_districts" and FIRE_DISTRICT.search(p["Name"])
            out.append((0 if fire_sd else 1, -reg.get((base, p["County"]), 0), kind, p["Name"], p))
    return [(kind, p) for _, _, kind, _, p in sorted(out, key=lambda t: t[:4])]


def process_entity(viz, kind, p, entry, dom, date):
    name = p["Name"]
    funds, depts = dom.get("Select Fund", []), dom.get("Select Department", [])
    years = dom.get("Select Transaction Date Year", [])
    entry.update({"funds": funds, "departments": depts, "years": years})
    recent = [y for y in years if y.isdigit() and int(y) >= FIRST_FY]
    if not years and "decision" not in entry:
        # no filter lists at all: confirm with the chart's own totals that the participant has no rows (and was not
        # just answered without filter lists)
        raw, data = viz.summary()
        entry["summary_rows"] = len(table_rows(data))
        if entry["summary_rows"]:
            raise RuntimeError(f"{name}: no filter lists but {entry['summary_rows']} summary rows")
    if "decision" not in entry and not recent:
        entry["decision"] = f"no transactions from {FIRST_FY} on"
    slices = [] if "decision" in entry else fire_slices(kind, name, funds, depts)
    slices = [(s, {**f, "Year Of Transaction Date": recent}) for s, f in slices]
    entry["slices"] = [s for s, _ in slices]
    if slices:
        log = []
        for sname, filters in slices:
            n = fetch_slice(viz, filters, years, log)
            print(f"  {name}: {sname}: {n} rows")
        for cap in ("Fund", "Department", "Year Of Transaction Date"):
            viz.set_filter(cap, None)
        common.save_raw(ST, SOURCE, f"entity_{p['Id']}.json", json.dumps(
            {"entity": entry, "fetched": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "requests": log}, ensure_ascii=False).encode("utf-8"), date=date)
    print(f"{ST}: {SOURCE}: {name}: {len(funds)} funds, {len(depts)} departments, years {','.join(recent) or '-'}, "
          f"fire slices {entry['slices'] or entry.get('decision', 'none')}")


def fetch(date=None, only=None, cache=None):
    date = date or common.TODAY
    client = Client(date)
    lists = {}
    for kind, (category, *_rest) in KINDS.items():
        body, people = participants(client, category)
        common.save_raw(ST, SOURCE, f"participants_{kind}.json", body, date=date)
        lists[kind] = [p for p in people if not p.get("IsDeleted")]
        print(f"{ST}: {SOURCE}: {len(lists[kind])} {category}")
    cache_path = None
    screen = {}
    if cache:
        import pathlib
        cache_path = pathlib.Path(cache)
        if cache_path.exists():
            screen = json.loads(cache_path.read_text())
    vizzes, failed = {}, []
    folder = common.raw_dir(ST, SOURCE, date)
    for kind, p in order_entities(lists):
        name, key = p["Name"], f"{kind}:{p['Id']}"
        if only and name not in only:
            continue
        if (folder / f"entity_{p['Id']}.json.gz").exists():
            continue
        if key in screen and not (not screen[key].get("years") and "summary_rows" not in screen[key]
                                  and screen[key].get("decision") == f"no transactions from {FIRST_FY} on"):
            continue  # screened (participants without filter lists screened before the summary check are redone)
        entry = {"kind": kind, "id": p["Id"], "name": name, "county": p["County"]}
        if kind == "special_districts" and not FIRE_DISTRICT.search(name):
            entry["decision"] = "not a fire district"
        elif name in EMS_ONLY or name in SKIP:
            entry["decision"] = EMS_ONLY.get(name) or SKIP[name]
        if "decision" in entry and kind == "special_districts":
            screen[key] = entry
            continue
        for attempt in range(3):
            try:
                if vizzes.get(kind) is None or attempt:
                    if attempt:
                        print(f"  {name}: new session after error: {err}", file=sys.stderr)
                        client.jar.clear()
                        time.sleep(30 * attempt)
                    vizzes[kind] = Viz(client, kind)
                    dom = vizzes[kind].start(name)
                else:
                    dom = vizzes[kind].set_filter("Municipality Name", [name]) or {}
                process_entity(vizzes[kind], kind, p, entry, dom, date)
                break
            except (RuntimeError, AssertionError, KeyError, ValueError, OSError) as e:
                err = e
                vizzes[kind] = None
        else:
            # not cached, so the next run tries it again; the run goes on with the other participants
            failed.append(name)
            print(f"{ST}: {SOURCE}: {name}: failed three times, left for the next run: {err}")
            continue
        screen[key] = entry
        if cache_path:
            cache_path.write_text(json.dumps(screen))
    if failed:
        raise RuntimeError(f"{len(failed)} participants failed; run fetch again: {failed}")
    if not only:
        done = {**screen}
        for path in sorted(folder.glob("entity_*.json.gz")):
            e = json.loads(common.read_gz(path))["entity"]
            done.setdefault(f"{e['kind']}:{e['id']}", e)
        common.save_raw(ST, SOURCE, "screen.json", json.dumps(
            [done[k] for k in sorted(done)], indent=0, ensure_ascii=False).encode("utf-8"), date=date)
        save_sample(date)


def program_220(depts):
    """A township's program 220 values (fire protection in the township chart of accounts, shown as "Public
    Safety - 220" or "220 - 220") whose name does not say fire; fire-named ones ("Fire Protection - 220") were
    fetched with the fire slices already."""
    return [d for d in depts if d.rsplit(" - ", 1)[-1] == PROGRAM_220 and not FIRE_NAME.search(d)]


def fetch_program_220(date=None, only=None):
    """Owner decision of 2026-10-07 (Ohio Public Safety): for each fetched township with program 220 values not
    named for fire, fetch the lines of program 220 in the funds not named for fire (the fire funds were fetched
    whole by the fire slices, so nothing overlaps) and the dashboard's summary totals of every police-named fund
    and department from FIRST_FY on (does the township run police?). One raw file per township:
    program220_<id>.json.gz, same layout as entity_<id>.json.gz (request kinds rows, summary, police)."""
    date = date or common.TODAY
    folder = common.raw_dir(ST, SOURCE, date)
    client, viz = Client(date), None
    todo = []
    for path in sorted(folder.glob("entity_*.json.gz"), key=lambda p: int(re.sub(r"\D", "", p.name))):
        e = json.loads(common.read_gz(path))["entity"]
        if e["kind"] == "townships" and program_220(e["departments"]) and (not only or e["name"] in only):
            todo.append(e)
    print(f"{ST}: {SOURCE}: {len(todo)} townships with program 220 lines not named for fire")
    for e in todo:
        if (folder / f"program220_{e['id']}.json.gz").exists():
            continue
        for attempt in range(3):
            try:
                if viz is None:
                    if attempt:
                        client.jar.clear()
                        time.sleep(30 * attempt)
                    viz = Viz(client, "townships")
                    dom = viz.start(e["name"])
                else:
                    dom = viz.set_filter("Municipality Name", [e["name"]]) or {}
                funds, depts = dom.get("Select Fund", []), dom.get("Select Department", [])
                years = dom.get("Select Transaction Date Year", [])
                if not funds or not depts:
                    raise RuntimeError(f"{e['name']}: no filter lists in the response")
                if (funds, depts) != (e["funds"], e["departments"]):
                    print(f"  {e['name']}: filter values differ from the entity file (new uploads); using today's")
                recent = [y for y in years if y.isdigit() and int(y) >= FIRST_FY]
                other_funds = [f for f in funds if not FIRE_NAME.search(f)]
                log = []
                if recent and other_funds:
                    n = fetch_slice(viz, {"Fund": other_funds, "Department": program_220(depts),
                                          "Year Of Transaction Date": recent}, years, log)
                    print(f"  {e['name']}: program 220: {n} rows")
                police = [("Fund", [f for f in funds if POLICE_FUND.search(f)]),
                          ("Department", [d for d in depts if POLICE_FUND.search(d)])]
                for cap, values in police:
                    if values and recent:
                        filters = {cap: values, "Year Of Transaction Date": recent}
                        for c in ("Fund", "Department", "Year Of Transaction Date", "Object"):
                            viz.set_filter(c, filters.get(c))
                        raw, data = viz.summary()
                        log.append({"kind": "police", "filters": filters, "body": raw.decode("utf-8")})
                        print(f"  {e['name']}: police-named {cap.lower()}s: {len(values)}, "
                              f"{sum(1 for r in table_rows(data) if r['SUM(Amount)'] != 'null')} fund-year totals")
                for c in ("Fund", "Department", "Year Of Transaction Date"):
                    viz.set_filter(c, None)
                entry = {**e, "funds": funds, "departments": depts, "years": years,
                         "slices": ["program_220"] if recent and other_funds else []}
                common.save_raw(ST, SOURCE, f"program220_{e['id']}.json", json.dumps(
                    {"entity": entry,
                     "fetched": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                     "requests": log}, ensure_ascii=False).encode("utf-8"), date=date)
                break
            except (RuntimeError, AssertionError, KeyError, ValueError, OSError) as err:
                print(f"  {e['name']}: attempt {attempt + 1} failed: {err}", file=sys.stderr)
                viz = None
        else:
            raise RuntimeError(f"{e['name']}: program 220 fetch failed three times; run again")


def save_sample(date):
    folder = common.raw_dir(ST, SOURCE, date)
    files = sorted(folder.glob("entity_*.json.gz"), key=lambda p: int(re.sub(r"\D", "", p.name)))
    for path in files:
        for req in json.loads(common.read_gz(path))["requests"]:
            if req["kind"] == "rows":
                rows = table_rows(json.loads(req["body"]))[:100]
                if rows:
                    common.write_csv(folder / "_sample.tmp", list(rows[0]), rows)
                    common.save_raw(ST, SOURCE, "sample.csv", (folder / "_sample.tmp").read_bytes(), date=date)
                    (folder / "_sample.tmp").unlink()
                    return

# --- normalize ---------------------------------------------------------------------------------------------

def entity_requests(path):
    """(entity, [(filters, rows)], [(filters, summary rows)], [(filters, police summary rows)]) from one entity
    file and, when there is one, its program220_<id> file (fetch220)."""
    d = json.loads(common.read_gz(path))
    reqs = d["requests"]
    extra = path.parent / path.name.replace("entity_", "program220_")
    if extra.exists():
        e = json.loads(common.read_gz(extra))
        assert (e["entity"]["id"], e["entity"]["name"]) == (d["entity"]["id"], d["entity"]["name"]), extra.name
        reqs = reqs + e["requests"]
    out = {"rows": [], "summary": [], "police": []}
    for req in reqs:
        out[req["kind"]].append((req["filters"], table_rows(json.loads(req["body"]))))
    return d["entity"], out["rows"], out["summary"], out["police"]


NULL = "%null%"  # Tableau's marker for an empty cell


def label(r, part):
    """The dashboard's own label for a fund, department or object: 'Fire District - 2111' ('' when empty)."""
    return " - ".join(v for v in (r[part + "Description"], r[part + "Code"]) if v and v != NULL)


def police_named(r):
    return bool(POLICE_FUND.search(r["FundDescription"] or "") or POLICE_FUND.search(r["DeptDescription"] or ""))


def is_fire_line(kind, r, dept_trusted=True):
    """Fire districts: every line. Townships, cities and villages: a fire-named fund or department (minus the
    excluded names and escrow funds). Townships also: program 220 (owner decision of 2026-10-07), and never a line
    whose fund or department is named for police."""
    if kind == "special_districts":
        return True
    if ESCROW_NAME.search(r["FundDescription"] or "") or ESCROW_NAME.search(r["DeptDescription"] or ""):
        return False
    if kind == "townships" and police_named(r):
        return False
    return fire_line_name(r["FundDescription"]) or (dept_trusted and fire_line_name(r["DeptDescription"])) \
        or (kind == "townships" and r["DeptCode"] == PROGRAM_220)


def runs_police(police):
    """Years (FIRST_FY on) in which a police-named fund or department of the participant has lines, from the
    dashboard's summary totals fetched by fetch220."""
    return sorted({s["YEAR(Transaction Date)"] for _, rows in police for s in rows
                   if s["SUM(Amount)"] != "null" and int(s["YEAR(Transaction Date)"]) >= FIRST_FY})


def dept_trusted(by_id):
    """False when the participant's fire-named department also carries lines of a police fund (a fund named for
    police and not for fire): its department code then covers police as well (City of New Franklin books police,
    street lighting and drug fund lines under department 1 "FIRE"), so only its fire funds are taken."""
    return not any(FIRE_NAME.search(r["DeptDescription"]) and POLICE_FUND.search(r["FundDescription"])
                   and not FIRE_NAME.search(r["FundDescription"]) for r in by_id.values())


def money(v):
    return decimal.Decimal(v).quantize(CENTS)


def entity_lines(path):
    """Every fetched row of one entity, once per row Id, checked against the summary totals of its slice."""
    entity, reqs, sums, police = entity_requests(path)
    by_id = {}
    for filters, rows in reqs:
        for r in rows:
            assert r["MuniName"] == entity["name"], f"{path.name}: row of {r['MuniName']!r}"
            assert money(r["Amt"]) == money(r["Amount"]), f"{path.name}: Amt and Amount differ: {r['Id']}"
            prev = by_id.setdefault(r["Id"], r)
            assert prev == r, f"{path.name}: row Id {r['Id']} fetched twice with different values"
    # control: each slice's rows per year equal the chart's summary totals for the same filters
    for filters, summary in sums:
        want = collections.defaultdict(decimal.Decimal)
        for s in summary:
            if s["SUM(Amount)"] != "null":  # the chart pads fund and year pairs without rows with null
                want[s["YEAR(Transaction Date)"]] += decimal.Decimal(s["SUM(Amount)"])
        got = collections.defaultdict(decimal.Decimal)
        for r in by_id.values():
            if all(r[{"Fund": "Fund", "Department": "Department", "Year Of Transaction Date": "Year Of Transaction Date"}
                     [k]] in v for k, v in filters.items() if k in ("Fund", "Department", "Year Of Transaction Date")):
                got[r["TransDate"][:4]] += money(r["Amt"])
        for y in set(want) | set(got):
            assert abs(want[y] - got[y]) <= CENTS, f"{path.name}: {filters} {y}: rows {got[y]} vs summary {want[y]}"
    has_220 = (path.parent / path.name.replace("entity_", "program220_")).exists()
    return {**entity, "program_220_fetched": has_220, "police_years": runs_police(police)}, by_id


def broken_months(rows):
    """Months (YYYY-MM) of one entity whose lines mostly share date and amount with 2+ other lines of 2+ payees
    and 2+ objects."""
    pair, payees, objects = collections.Counter(), collections.defaultdict(set), collections.defaultdict(set)
    for r in rows:
        k = (r["TransDate"][:10], r["Amt"])
        pair[k] += 1
        payees[k].add(r["Payee"])
        objects[k].add(r["ObjCode"])
    n, rep = collections.Counter(), collections.Counter()
    for r in rows:
        k = (r["TransDate"][:10], r["Amt"])
        n[r["TransDate"][:7]] += 1
        rep[r["TransDate"][:7]] += pair[k] >= 3 and len(payees[k]) >= 2 and len(objects[k]) >= 2
    return {m for m in n if rep[m] > BROKEN_SHARE * n[m]}


def undouble(entity, rows, stats):
    """A month uploaded k times: with DOUBLED_MIN lines or more, every group of lines identical in date, payee,
    fund, department, object and amount has a size divisible by k >= 2 (the gcd of the group sizes). Keep the
    first size/k lines of each group (lowest row Ids). Other identical lines are left to unidentical."""
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["TransDate"][:7], r["TransDate"][:10], r["Payee"], r["FundCode"], r["DeptCode"], r["ObjCode"],
                r["Amt"])].append(r)
    k = collections.defaultdict(int)
    n = collections.Counter()
    for key, g in groups.items():
        k[key[0]] = math.gcd(k[key[0]], len(g))
        n[key[0]] += len(g)
    doubled = {m: k[m] for m in n if n[m] >= DOUBLED_MIN and k[m] >= 2}
    drop = set()
    for key, g in groups.items():
        if key[0] in doubled:
            keep = len(g) // doubled[key[0]]
            drop |= {r["Id"] for r in sorted(g, key=lambda r: int(r["Id"]))[keep:]}
    for m in sorted(doubled):
        lines = [r for r in rows if r["Id"] in drop and r["TransDate"][:7] == m]
        stats["doubled_lines"] += len(lines)
        stats["doubled_dollars"] += sum(money(r["Amt"]) for r in lines)
        print(f"  {entity['name']}: {m}: uploaded {doubled[m]} times; {len(lines)} repeated lines dropped "
              f"(${sum(money(r['Amt']) for r in lines):,.2f})")
    return [r for r in rows if r["Id"] not in drop]


def unreload(entity, rows, stats):
    """Drop a later upload's lines of a date that only repeat lines already uploaded for that date (RELOAD_GAP,
    RELOAD_MIN)."""
    def same(r):
        return r["TransDate"][:10], r["Payee"], r["FundCode"], r["DeptCode"], r["ObjCode"], r["Amt"]
    uploads, prev = [], None
    for r in sorted(rows, key=lambda r: (int(r["TransactionId"]), int(r["Id"]))):
        if prev is None or int(r["TransactionId"]) - prev > RELOAD_GAP:
            uploads.append([])
        uploads[-1].append(r)
        prev = int(r["TransactionId"])
    seen, drop = collections.Counter(), set()
    for upload in uploads:
        days = collections.defaultdict(list)
        for r in upload:
            days[r["TransDate"][:10]].append(r)
        new = collections.Counter()
        for day in sorted(days):
            lines = days[day]
            count = collections.Counter(same(r) for r in lines)
            if len(lines) >= RELOAD_MIN and all(money(r["Amt"]) >= 0 for r in lines) \
                    and all(seen[k] >= n for k, n in count.items()):
                drop |= {r["Id"] for r in lines}
                stats["reload_lines"] += len(lines)
                stats["reload_dollars"] += sum(money(r["Amt"]) for r in lines)
                print(f"  {entity['name']}: {day}: {len(lines)} lines uploaded again in a later upload dropped "
                      f"(${sum(money(r['Amt']) for r in lines):,.2f})")
            else:
                new += count
        seen += new
    return [r for r in rows if r["Id"] not in drop]


def account(r):
    """The published account: 'Fund - code / Department - code / Object - code' as the dashboard labels them."""
    return " / ".join(x for x in (label(r, "Fund"), label(r, "Dept"), label(r, "Obj")) if x)


def payee(r):
    return "" if r["Payee"] == NULL else r["Payee"]


def identity(r):
    """Every raw column but the row and load ids (ROW_IDS): two lines with the same identity are identical."""
    return tuple(sorted((k, v) for k, v in r.items() if k not in ROW_IDS))


def families(groups, year):
    """Payment and reversal families (owner decision A of 2026-10-07): groups whose lines share the REVERSAL fields
    and the amount up to sign, joined the way the void rule links a payment to its reversals (a negative line dated
    in a payment's year or the next): the negative groups of year y join the positive groups of years y - 1 and y.
    Placing a year's negative groups at 2y and its positive groups at 2y + 1, a family is a run of consecutive
    places. Lines of amount 0 belong to no family. Returns lists of identities, each family once, in a fixed
    order."""
    by_key = collections.defaultdict(lambda: collections.defaultdict(list))
    for k, g in groups.items():
        amount = money(g[0]["Amt"])
        if amount != 0:
            by_key[(tuple(g[0][c] for c in REVERSAL), abs(amount))][2 * year(g[0]) + (amount > 0)].append(k)
    out = []
    for key in sorted(by_key):
        prev = None
        for place in sorted(by_key[key]):
            if prev is None or place > prev + 1:
                out.append([])
            out[-1] += by_key[key][place]
            prev = place
    return out


def unidentical(entity, rows, stats):
    """Owner rule of 2026-10-07 as corrected: identical lines (identity) are kept once, the lowest row Id. A group
    of n identical positive lines keeps min(n, reversals + 1), the lowest row Ids: reversals counts the distinct
    identities (identical reversals once) of the negative lines with the same REVERSAL fields, the amount negated
    and a date in the group's year or the next, so a payment voided and reissued identically keeps its net.
    Identical voids (owner decision A of 2026-10-07): in a family (families) that has a payment, identical negative
    copies are dropped only as often as the family's identical positive copies are dropped (the family's negative
    groups in order of their lowest row Id, each keeping its lowest row Ids), so the family keeps its raw net; a
    family without payments keeps each identical negative line once. Returns the kept rows and the dropped ones."""
    groups = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: int(r["Id"])):
        groups[identity(r)].append(r)
    reversals = collections.defaultdict(set)  # (REVERSAL fields, amount reversed) -> {(year, identity)}
    for k, g in groups.items():
        if money(g[0]["Amt"]) < 0:
            reversals[(tuple(g[0][c] for c in REVERSAL), -money(g[0]["Amt"]))].add((int(g[0]["TransDate"][:4]), k))
    keep = {}
    for k, g in groups.items():
        amount, year, keep[k] = money(g[0]["Amt"]), int(g[0]["TransDate"][:4]), 1
        if amount > 0 and len(g) > 1:
            n_rev = sum(y in (year, year + 1) for y, _ in reversals[(tuple(g[0][c] for c in REVERSAL), amount)])
            keep[k] = min(len(g), n_rev + 1)
            if keep[k] > 1:
                stats["void_kept_groups"] += 1
                stats["void_kept_lines"] += keep[k] - 1
                stats["void_kept_dollars"] += (keep[k] - 1) * amount
    # identical voids: a family with payments drops a negative copy only together with a positive copy
    for fam in families(groups, lambda r: int(r["TransDate"][:4])):
        if not any(money(groups[k][0]["Amt"]) > 0 for k in fam):
            continue  # negative lines only: each identical negative line kept once
        allowed = sum(len(groups[k]) - keep[k] for k in fam if money(groups[k][0]["Amt"]) > 0)
        touched = False
        for k in sorted((k for k in fam if money(groups[k][0]["Amt"]) < 0), key=lambda k: int(groups[k][0]["Id"])):
            drop_n = min(len(groups[k]) - 1, allowed)
            allowed -= drop_n
            if len(groups[k]) - drop_n != keep[k]:
                touched = True
                stats["void_fix_lines"] += len(groups[k]) - drop_n - keep[k]
                stats["void_fix_dollars"] += (len(groups[k]) - drop_n - keep[k]) * money(groups[k][0]["Amt"])
                keep[k] = len(groups[k]) - drop_n
        if touched:
            stats["void_fix_families"] += 1
            assert sum(keep[k] * money(groups[k][0]["Amt"]) for k in fam) \
                == sum(len(groups[k]) * money(groups[k][0]["Amt"]) for k in fam), f"{entity['name']}: family net"
    drop = set()
    for k, g in groups.items():
        amount = money(g[0]["Amt"])
        if len(g) > keep[k]:
            stats["identical_groups"] += 1
            drop |= {r["Id"] for r in g[keep[k]:]}
            if amount < 0:
                stats["identical_negative_lines"] += len(g) - keep[k]
                stats["identical_negative_dollars"] += (len(g) - keep[k]) * amount
    lines = [r for r in rows if r["Id"] in drop]
    kept = [r for r in rows if r["Id"] not in drop]
    stats["identical_lines"] += len(lines)
    stats["identical_dollars"] += sum(money(r["Amt"]) for r in lines)
    # reported: payment and reversal families (REVERSAL fields and amount, both signs present) whose net the rule
    # raised; none since the identical-void fix (a negative copy goes only with a positive copy)
    net = collections.defaultdict(lambda: [decimal.Decimal(0), decimal.Decimal(0), set()])
    for r in rows:
        f = net[(tuple(r[c] for c in REVERSAL), abs(money(r["Amt"])))]
        f[0] += money(r["Amt"])
        f[2].add(money(r["Amt"]) > 0)
    for r in kept:
        net[(tuple(r[c] for c in REVERSAL), abs(money(r["Amt"])))][1] += money(r["Amt"])
    for raw_net, kept_net, signs in net.values():
        if len(signs) == 2 and kept_net > raw_net:
            stats["net_raised_families"] += 1
            stats["net_raised_dollars"] += kept_net - raw_net
    return kept, lines


def entity_rows(eid, entity, by_id, stats):
    """The entity's published lines: fire lines from FIRST_FY, re-uploads and reloads once, broken-upload months
    dropped, then identical lines once (owner rule of 2026-10-07)."""
    seen, rows = set(), []
    trusted = dept_trusted(by_id)
    if not trusted:
        print(f"  {entity['name']}: its fire department also carries police fund lines; fire funds only")
    for rid in sorted(by_id, key=int):
        r = by_id[rid]
        if int(r["TransDate"][:4]) < FIRST_FY or not is_fire_line(entity["kind"], r, trusted):
            stats["outside"] += 1
            if int(r["TransDate"][:4]) >= FIRST_FY and entity["kind"] == "townships" and police_named(r) \
                    and is_fire_line("cities_villages", r, trusted):
                # a township line named for fire and for police: never counted (owner decision of 2026-10-07)
                stats["township_police_lines"] += 1
                stats["township_police_dollars"] += money(r["Amt"])
            continue
        key = (r["TransactionId"], r["TransDate"], r["Payee"], r["FundCode"], r["DeptCode"], r["ObjCode"], r["Amt"])
        if key in seen:
            stats["reuploads"] += 1
            stats["reupload_dollars"] += money(r["Amt"])
            continue
        seen.add(key)
        rows.append(r)
    rows = undouble(entity, rows, stats)
    rows = unreload(entity, rows, stats)
    broken = broken_months(rows)
    for m in sorted(broken):
        lines = [r for r in rows if r["TransDate"][:7] == m]
        stats["broken_lines"] += len(lines)
        stats["broken_dollars"] += sum(money(r["Amt"]) for r in lines)
        print(f"  {entity['name']}: {m}: {len(lines)} lines dropped (upload carries batch totals, "
              f"${sum(money(r['Amt']) for r in lines):,.2f})")
    rows, dropped = unidentical(entity, [r for r in rows if r["TransDate"][:7] not in broken], stats)
    if dropped:
        IDENTICAL[entity["name"]] = (len(dropped), sum(money(r["Amt"]) for r in dropped))
    if entity["kind"] == "townships" and entity["program_220_fetched"]:
        # what the program 220 rule adds (lines not named for fire), and what it leaves out as police-named
        added = [r for r in rows if not (fire_line_name(r["FundDescription"])
                                         or (trusted and fire_line_name(r["DeptDescription"])))]
        assert all(r["DeptCode"] == PROGRAM_220 for r in added), entity["name"]
        mixed = [r for r in by_id.values() if int(r["TransDate"][:4]) >= FIRST_FY and r["DeptCode"] == PROGRAM_220
                 and police_named(r)]
        PROGRAM220[entity["name"]] = {
            "lines": len(added), "dollars": sum(money(r["Amt"]) for r in added),
            "police_years": entity["police_years"], "mixed_lines": len(mixed),
            "mixed_dollars": sum(money(r["Amt"]) for r in mixed)}
    return rows


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    links = {r["source_entity_id"]: r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == SOURCE}
    out, stats = [], collections.Counter()
    for eid in sorted(links, key=int):
        link = links[eid]
        entity, by_id = entity_lines(d / f"entity_{eid}.json.gz")
        assert entity["name"] == link["source_entity_name"], f"link {eid}: {entity['name']!r} != {link}"
        if entity["kind"] == "townships" and entity["program_220_fetched"]:
            # the link's note says that program 220 counts and, when the township also runs police, that its
            # mixed Public Safety lines (program 220 in police-named funds or departments) are left out
            assert "program 220" in link["note"], f"{entity['name']}: note does not mention program 220"
            assert ("mixed Public Safety lines" in link["note"]) == bool(entity["police_years"]), \
                f"{entity['name']}: police from 2021 on {entity['police_years']}; note: {link['note']!r}"
        for r in entity_rows(eid, entity, by_id, stats):
            out.append({
                "agency_id": link["agency_id"], "fiscal_year": r["TransDate"][:4], "posting_date": r["TransDate"][:10],
                "payee_name": common.withhold_person(payee(r)), "description": "", "account": account(r),
                "category_published": "" if r["ObjDescription"] == NULL else r["ObjDescription"],
                "amount": str(money(r["Amt"])),
                "source_record_id": f"{eid}-{r['Id']}"})
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, out)
    years = sorted({int(r["fiscal_year"]) for r in out})
    last = max(r["posting_date"] for r in out)
    register_source({
        "source": SOURCE, "name": "Ohio Checkbook, local governments", "tier": "1",
        "url": f"{CHECKBOOK}/Local/", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "Calendar year (Ohio local governments)", "fetched": d.parent.parent.name,
        "note": f"{len(links)} participating fire agencies. Fire districts: whole checkbook. Townships: lines whose "
                "fund or department is named for fire and lines of program 220 (Public Safety, fire protection in "
                "the township chart of accounts), never lines named for police, so where a township also runs "
                "police its mixed Public Safety lines are left out. Cities and villages: only lines whose fund or "
                "department is named for fire; fire spending they book under general 'Public Safety' lines is not "
                "included. Lines identical in every column the checkbook publishes (row ids aside) are shown "
                "once, a voided and identically reissued payment as often as it was voided plus one, and identical "
                "voids of a payment as often as needed to keep its net as published. Most of the "
                "dollars are payroll, pensions and benefits paid through the checkbook. Participation is voluntary "
                f"and uploads lag by entity (latest payment {last}); FY{years[-1]} partial"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in out)
    neg = [r for r in out if r["amount"].startswith("-")]
    print(f"{ST}: {SOURCE}: {len(out)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}, {len(links)} agencies; "
          f"{stats['reuploads']} re-uploaded lines dropped (${stats['reupload_dollars']:,.2f}); "
          f"{stats['doubled_lines']} lines of months uploaded twice dropped (${stats['doubled_dollars']:,.2f}); "
          f"{stats['reload_lines']} reloaded lines dropped (${stats['reload_dollars']:,.2f}); "
          f"{stats['broken_lines']} lines of broken-upload months dropped (${stats['broken_dollars']:,.2f}); "
          f"{stats['identical_lines']} identical lines dropped (${stats['identical_dollars']:,.2f}, "
          f"{stats['identical_groups']} groups, {len(IDENTICAL)} agencies; of them "
          f"{stats['identical_negative_lines']} negative, ${stats['identical_negative_dollars']:,.2f}); void rule kept "
          f"{stats['void_kept_lines']} identical lines (${stats['void_kept_dollars']:,.2f}, "
          f"{stats['void_kept_groups']} groups); identical-void fix kept {stats['void_fix_lines']} negative lines "
          f"(${stats['void_fix_dollars']:,.2f}) in {stats['void_fix_families']} families, each at its raw net; "
          f"{stats['net_raised_families']} payment and reversal families netted higher than raw "
          f"(${stats['net_raised_dollars']:,.2f}); "
          f"{stats['outside']} fetched lines outside the rule or years (of them {stats['township_police_lines']} "
          f"township lines named for fire and police, ${stats['township_police_dollars']:,.2f}); {len(neg)} negative lines "
          f"(${sum(decimal.Decimal(r['amount']) for r in neg):,.2f}) kept")
    for name, v in sorted(PROGRAM220.items()):
        print(f"  program 220: {name}: {v['lines']} lines (${v['dollars']:,.2f}) added; police "
              f"{','.join(v['police_years']) or 'none'}; {v['mixed_lines']} police-named program 220 lines "
              f"(${v['mixed_dollars']:,.2f}) left out")
    top = sorted(IDENTICAL.items(), key=lambda kv: -abs(kv[1][1]))[:5]
    print("  identical lines dropped, largest: " + "; ".join(f"{k} {n} (${v:,.2f})" for k, (n, v) in top))


def register_source(row):
    path = common.config_dir(ST) / "sources.csv"
    rows = [r for r in common.read_config(ST, "sources.csv") if r["source"] != row["source"]] + [row]
    common.write_csv(path, SOURCE_COLUMNS, sorted(rows, key=lambda r: r["source"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["fetch", "fetch220", "normalize"])
    ap.add_argument("--date")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--cache", help="optional JSON file that keeps screening progress across interrupted runs")
    a = ap.parse_args()
    if a.step == "fetch":
        fetch(a.date, a.only, a.cache)
    elif a.step == "fetch220":
        fetch_program_220(a.date, a.only)
    else:
        normalize()
