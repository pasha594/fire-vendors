"""Ohio Checkbook, local governments: payee lines of Ohio fire districts and of township, city and village fire
funds and fire departments.

    python3 pipeline/sources/oh_checkbook_local.py fetch [--date YYYY-MM-DD] [--only NAME ...]
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
villages only the lines whose fund or department is named for fire (FIRE_NAME, minus NOT_FIRE_NAME: shared
police-and-fire names, fire-loss insurance escrow, hydrants). A township's general-fund "Public Safety" lines are
never included, even under program code 220 (fire protection in the township chart of accounts), because the
name does not say fire. Only participants linked in config/states/oh/agency_sources.csv reach the data.

Fiscal year: Ohio local governments use the calendar year (fy_start 01); fiscal_year is the transaction date's
year. Years 2021 on.

Duplicates and broken uploads (normalize): rows are keyed by the checkbook's row Id; a row fetched twice
(overlapping requests) is kept once. TransactionId is unique per line in every fetched participant, so lines that
match in every field but TransactionId are separate lines (several identical invoices or benefit lines paid the
same day) and are kept, except in a month uploaded k times: a month of DOUBLED_MIN lines or more in which every
group of lines identical in date, payee, fund, department, object and amount has a size divisible by k >= 2
keeps size/k lines of each group (Beavercreek Township, March 2023). A month whose lines carry batch totals
instead of line amounts (BROKEN_SHARE rule; Jackson Township (Stark), 2026) is left out. Negative amounts
(voids, refunds, reversals) are kept so they net out. Every fetched slice is checked against the dashboard's
own summary totals for the same filters, per year.
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
NOT_FIRE_NAME = re.compile(r"POLICE|HYDRANT|FIRE ?LOSS|FIREWORK|INSURANCE|ESCROW|DAMAGED STRUCTURE|GARNISH", re.I)
# A month whose upload carries batch totals instead of line amounts: most of its lines share their date and amount
# with at least two other lines paid to other payees (Jackson Township (Stark), 2026: every line of a day shows
# the same $0.5-4.7 million). Its lines are dropped.
BROKEN_SHARE = decimal.Decimal("0.5")
DOUBLED_MIN = 10  # lines in a month before the month can be judged as uploaded twice
# Special districts that are fire agencies (whole checkbook), and the ones whose name suggests fire or EMS but
# which are not fire agencies, by participant name.
FIRE_DISTRICT = re.compile(r"\bFIRE\b", re.I)
EMS_ONLY = {"Joint Emergency Medical Service": "EMS-only joint district (no fire service); excluded by the owner's "
                                               "rule for EMS-only districts"}
SKIP = {"City of Cincinnati": "Cincinnati Fire Department comes from the City's own vendor payments (oh_cincinnati); "
                              "taking it here as well would count it twice"}
SOURCE_COLUMNS = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]
CENTS = decimal.Decimal("0.01")


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
    """(entity, [(filters, rows)], [(filters, summary rows)]) from one entity file."""
    d = json.loads(common.read_gz(path))
    rows, sums = [], []
    for req in d["requests"]:
        (rows if req["kind"] == "rows" else sums).append((req["filters"], table_rows(json.loads(req["body"]))))
    return d["entity"], rows, sums


def label(r, part):
    """The dashboard's own label for a fund, department or object: 'Fire District - 2111'."""
    return f"{r[part + 'Description']} - {r[part + 'Code']}"


def is_fire_line(kind, r):
    if kind == "special_districts":
        return True
    return fire_line_name(r["FundDescription"]) or fire_line_name(r["DeptDescription"])


def money(v):
    return decimal.Decimal(v).quantize(CENTS)


def entity_lines(path):
    """Every fetched row of one entity, once per row Id, checked against the summary totals of its slice."""
    entity, reqs, sums = entity_requests(path)
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
    return entity, by_id


def broken_months(rows):
    """Months (YYYY-MM) of one entity whose lines mostly share date and amount with 2+ other lines of 2+ payees."""
    pair, payees = collections.Counter(), collections.defaultdict(set)
    for r in rows:
        k = (r["TransDate"][:10], r["Amt"])
        pair[k] += 1
        payees[k].add(r["Payee"])
    n, rep = collections.Counter(), collections.Counter()
    for r in rows:
        k = (r["TransDate"][:10], r["Amt"])
        n[r["TransDate"][:7]] += 1
        rep[r["TransDate"][:7]] += pair[k] >= 3 and len(payees[k]) >= 2
    return {m for m in n if rep[m] > BROKEN_SHARE * n[m]}


def undouble(entity, rows, stats):
    """A month uploaded k times: with DOUBLED_MIN lines or more, every group of lines identical in date, payee,
    fund, department, object and amount has a size divisible by k >= 2 (the gcd of the group sizes). Keep the
    first size/k lines of each group (lowest row Ids). Elsewhere identical lines are separate payments and kept."""
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


def entity_rows(eid, entity, by_id, stats):
    """The entity's published lines: fire lines from FIRST_FY, re-uploads once, broken-upload months dropped."""
    seen, rows = set(), []
    for rid in sorted(by_id, key=int):
        r = by_id[rid]
        if int(r["TransDate"][:4]) < FIRST_FY or not is_fire_line(entity["kind"], r):
            stats["outside"] += 1
            continue
        key = (r["TransactionId"], r["TransDate"], r["Payee"], r["FundCode"], r["DeptCode"], r["ObjCode"], r["Amt"])
        if key in seen:
            stats["reuploads"] += 1
            stats["reupload_dollars"] += money(r["Amt"])
            continue
        seen.add(key)
        rows.append(r)
    rows = undouble(entity, rows, stats)
    broken = broken_months(rows)
    for m in sorted(broken):
        lines = [r for r in rows if r["TransDate"][:7] == m]
        stats["broken_lines"] += len(lines)
        stats["broken_dollars"] += sum(money(r["Amt"]) for r in lines)
        print(f"  {entity['name']}: {m}: {len(lines)} lines dropped (upload carries batch totals, "
              f"${sum(money(r['Amt']) for r in lines):,.2f})")
    return [r for r in rows if r["TransDate"][:7] not in broken]


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    links = {r["source_entity_id"]: r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == SOURCE}
    out, stats = [], collections.Counter()
    for eid in sorted(links, key=int):
        link = links[eid]
        entity, by_id = entity_lines(d / f"entity_{eid}.json.gz")
        assert entity["name"] == link["source_entity_name"], f"link {eid}: {entity['name']!r} != {link}"
        for r in entity_rows(eid, entity, by_id, stats):
            out.append({
                "agency_id": link["agency_id"], "fiscal_year": r["TransDate"][:4], "posting_date": r["TransDate"][:10],
                "payee_name": common.withhold_person(r["Payee"]), "description": "",
                "account": " / ".join([label(r, "Fund"), label(r, "Dept"), label(r, "Obj")]),
                "category_published": r["ObjDescription"], "amount": str(money(r["Amt"])),
                "source_record_id": f"{eid}-{r['Id']}"})
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, out)
    years = sorted({int(r["fiscal_year"]) for r in out})
    last = max(r["posting_date"] for r in out)
    register_source({
        "source": SOURCE, "name": "Ohio Checkbook, local governments", "tier": "1",
        "url": f"{CHECKBOOK}/Local/", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "Calendar year (Ohio local governments)", "fetched": d.parent.parent.name,
        "note": f"{len(links)} participating fire agencies. Fire districts: whole checkbook. Townships, cities and "
                "villages: only lines whose fund or department is named for fire; fire spending they book under "
                "general 'Public Safety' lines is not included. Participation is voluntary and uploads lag by "
                f"entity (latest payment {last}); FY{years[-1]} partial"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in out)
    neg = [r for r in out if r["amount"].startswith("-")]
    print(f"{ST}: {SOURCE}: {len(out)} lines (${total:,.2f}), FY{years[0]}-FY{years[-1]}, {len(links)} agencies; "
          f"{stats['reuploads']} re-uploaded lines dropped (${stats['reupload_dollars']:,.2f}); "
          f"{stats['doubled_lines']} lines of months uploaded twice dropped (${stats['doubled_dollars']:,.2f}); "
          f"{stats['broken_lines']} lines of broken-upload months dropped (${stats['broken_dollars']:,.2f}); "
          f"{stats['outside']} fetched lines outside the rule or years; {len(neg)} negative lines "
          f"(${sum(decimal.Decimal(r['amount']) for r in neg):,.2f}) kept")


def register_source(row):
    path = common.config_dir(ST) / "sources.csv"
    rows = [r for r in common.read_config(ST, "sources.csv") if r["source"] != row["source"]] + [row]
    common.write_csv(path, SOURCE_COLUMNS, sorted(rows, key=lambda r: r["source"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["fetch", "normalize"])
    ap.add_argument("--date")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--cache", help="optional JSON file that keeps screening progress across interrupted runs")
    a = ap.parse_args()
    if a.step == "fetch":
        fetch(a.date, a.only, a.cache)
    else:
        normalize()
