"""Build the site's data files from the newest raw/<date>/ folders, data/states/<st>/ and the config/*.csv files.

    python3 pipeline/build.py                    # write data/index.json and the per-state files
    python3 pipeline/build.py --worklist DIR     # also write DIR/worklist_<st>.csv: payees that need a vendor_map row

Output (all compact JSON, deterministic; every file carries the same "built" date):
  data/index.json          meta (per state and per source), categories, every agency of every state, and the
                           precomputed default table per scope (home): the first load, under 1 MB gzipped
  data/<st>.json           vendors, payee names, rows, grants and published totals of one state (ut, oh, ca, id, tx)
  data/<st>-payments.json  single payments of one state
  data/<st>-items.json     item lines (tier 2: Texas DIR, California SCPRS)
States, their fiscal years and partial years are in config/states.csv. Other states are read from the normalized
files of docs/multistate/data-contract.md (data/states/<st>/) and classified with the same rules as Utah, but with
no person grouping and no withholding: their payee names and descriptions are shown as published.

Utah: vendor payments come from the Transparent Utah BigQuery transaction lines
(raw/<date>/transparent_utah_bigquery/fire_transactions_*.csv.gz) for every agency in config/agencies.csv with
include=yes. Fire districts and interlocal agencies also get details, expenses, revenue and staff from the public
Transparent Utah query service (raw/<date>/transparent_utah/); every agency gets USFA registry data and FEMA grants
where they match.

Vendors (one per payee name), in order:
  1. config/vendor_map.csv     normalized name -> canonical vendor name and category
  2. config/vendor_rules.csv   regex -> known vendor (folds rare spellings into a mapped vendor)
  3. config/keyword_rules.csv  first regex that matches the normalized name sets the category
                               (and the vendor name, when the rule has one)
  4. otherwise                 "unclassified"
A config/vendor_map.csv row decides first, whatever the payee name looks like. Other payees that look like a person
are grouped as "Individuals (names withheld)": names shaped like a person's, names matching a payee-name privacy
pattern, payees on ambulance revenue, bad debt or refund accounts (patients), and small unclaimed payees paid for
reimbursements, tuition or by employee number (staff). Payee text matching config/payee_name_redactions.csv is
not shown.

Lines left out before anything else: copies of a transaction that an entity uploaded again in a later batch
(reupload_copies), and police department lines of Lone Peak Public Safety District (police_only).

Category of each transaction line, in order (the method is counted for the About page):
  override     config/account_rules.csv row with mode=override for the line's accounts ("cat1 | cat2 | cat3")
  vendor       the payee's vendor category, when it is specific
  description  broad payees only: first config/description_rules.csv pattern that matches the description
  fallback     no vendor named, the payee text (checked before the description rules), description or accounts are a
               journal entry, reclassification, correction, reversal, allocation or accrual, and the agency pays named
               payees from the same accounts (so the entry corrects those payments): No vendor named (placeholder)
  refine       broad payees only: config/account_rules.csv row with mode=refine, unless the payee's vendor category
               is in the row's skip_vendor_category list
  fallback     broad payees only: the payee's vendor category; card statement lines (finance) outside debt, loan,
               lease and transfer accounts, and not described as a lease or loan, are Unclassified
Broad payees: vendor categories fire-equipment, general, unclassified and placeholder, and finance payees that are card
programs (config/card_programs.csv).
"""
import collections
import csv
import datetime
import gzip
import html
import io
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
DATA = ROOT / "data"
STATE_DATA = DATA / "states"
INDEX_MAX_GZ = 1_000_000                                    # data/index.json, gzipped
FILE_MAX = 50_000_000                                       # any written file


def read_states():
    """config/states.csv: {state: {"name", "years", "partial_years"}} in the file's order (Utah first)."""
    out = {}
    with open(CONFIG / "states.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            y0, y1 = (int(x) for x in r["years"].split("-"))
            partial = sorted(int(x) for x in r["partial_years"].split(";") if x.strip())
            assert set(partial) <= set(range(y0, y1 + 1)), f"config/states.csv: partial years of {r['state']}"
            out[r["state"]] = {"name": r["name"], "years": list(range(y0, y1 + 1)), "partial_years": partial}
    assert next(iter(out)) == "UT", "config/states.csv: Utah must be the first state"
    return out


STATES = read_states()
YEARS = STATES["UT"]["years"]
PARTIAL_YEARS = STATES["UT"]["partial_years"]
TU_SITE = "https://transparent.utah.gov/"
BQ_DIR = "transparent_utah_bigquery"

ENTITY_TYPES = {"Local and Special Service District": "Special district", "Interlocal": "Interlocal agency"}
API_KINDS = {"Fire district or service area", "Interlocal fire agency"}  # agencies with public-API extras
STAFFING_GROUPS = {"Career": "Career", "Mostly career": "Combination", "Mostly volunteer": "Combination",
                   "Volunteer": "Volunteer"}
BROAD = {"fire-equipment", "general", "unclassified", "placeholder"}
METHODS = ["override", "vendor", "description", "refine", "fallback"]
PAYMENT_MIN = 1000
INDIVIDUALS = "Individuals (names withheld)"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\(?\b\d{3}\)?[\s.\-]?\d{3}[\s.\-]\d{4}\b")
CONFIDENCE = {"high": 0, "medium": 1, "low": 2}
BUSINESS_WORDS = re.compile(
    r"\b(INC|LLC|LC|CORP|CO|COMPANY|LTD|LLP|PC|PLLC|GROUP|SERVICES?|SYSTEMS?|SUPPLY|CENTER|DEPT|DEPARTMENT|"
    r"DIVISION|BUREAU|OFFICE|CITY|COUNTY|STATE|UTAH|BANK|TRUST|FUND|ASSOCIATION|ASSOC|DISTRICT|AUTHORITY|"
    r"UNIVERSITY|COLLEGE|SCHOOL|HOSPITAL|CLINIC|FIRE|RESCUE|ACCOUNT|PAYABLE|TREASURER|INSURANCE|STORE)\b", re.I)
PERSON = re.compile(r"^[A-Za-z'\-\. ]+,\s*[A-Za-z'\-\. ]+$")
CARD_PAYEE = re.compile(r"^VISA - (.+?)(?:\s+\d{1,2}/\d{1,2}/\d{2,4})?$")  # Orem City card lines
VENDOR_NO = re.compile(r"^V\d{3,}\s+")                                     # vendor numbers: 'V0409 MOTOROLA SOLUTIONS'
VENDOR_NO_END = re.compile(r"\s*\(v\d{4,}\)$", re.I)                         # 'HAYES GODFREY BELL PC (v0000749)'
SLASH_FIRE = re.compile(r"^(.+?)\s*/\s*FIRE\s*/", re.I)                     # Newton Town: 'PAYEE/FIRE/ITEM'
PROCESSOR = re.compile(r"^(?:SQ|SP|PY|IN|TST|WPY|PP|PAYPAL)\s?\*\s*|^SP\s+", re.I)   # card processors: 'SQ *', 'PY *'
SLASH = re.compile(r"\s*/\s*")
# Parts of a payee name that can carry a person's name after a business name ('BANK - FIRST LAST', 'LLC, FIRST LAST',
# 'FIRST LAST DBA BUSINESS', 'BUSINESS/FIRST LAST INC')
SEGMENT = re.compile(r"\s*(?:/|,|\s-\s|\bdba\b|\bc/o\b)\s*", re.I)
# Payees on these accounts are patients (EMS bad debt write-offs, ambulance revenue refunds); in these descriptions,
# staff (reimbursements, tuition, employee numbers)
PATIENT_ACCOUNT = re.compile(r"ambulance revenue|bad debt|refund", re.I)
STAFF_DESC = re.compile(r"emp\s*#|reimbursement|tuition", re.I)
# Lines with no vendor named that move money between accounts rather than pay anyone
JOURNAL = re.compile(r"journal|\bje\b|reclass|\brcls\b|correct|revers|allocat|accru", re.I)
# Card statement accounts that are loan, lease or transfer payments rather than purchases
DEBT_ACCOUNT = re.compile(r"debt|loan|lease|principal|interest|bonds?\b|issuance|financ|\btans?\b|\btrans?\b|payment|pmt|"
                          r"transfer|reserve", re.I)
DEBT_DESC = re.compile(r"\b(lease|loan|principal|interest|bonds?)\b", re.I)    # '... for the 2025 lease payment'
POLICE = re.compile(r"\bpolice\b", re.I)
FIRE_ORG = re.compile(r"fire|ems|wildland", re.I)
COMMA_ID = re.compile(r"^([^,]*),(\d{1,2}/\d{2}),([^,]*),([^,]*)")         # 'AP,10/22,155000,106,1'


def read_csv(name):
    path = CONFIG / name
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_gz(path):
    return gzip.decompress(path.read_bytes())


def read_json_gz(path, default):
    return json.loads(read_gz(path)) if path.exists() else default


def read_table(path):
    """Rows of a CSV file, gzipped (.csv.gz) or not."""
    text = read_gz(path).decode("utf-8-sig") if path.suffix == ".gz" else path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(io.StringIO(text, newline="")))


def norm(name):
    s = (name or "").upper().replace("&", " AND ")
    s = re.sub(r"['’`]", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\b([A-Z]) (?=[A-Z]\b)", r"\1", s)  # "L N CURTIS" -> "LN CURTIS"
    s = re.sub(r"\b(INC|INCORPORATED|LLC|LC|CORP|CORPORATION|CO|COMPANY|LTD|LLP|PC|PLLC|PLC|THE|DBA)\b", " ", s)
    return " ".join(s.split())


def fix_mojibake(s):
    """Undo UTF-8 text that was decoded as Windows-1252, possibly more than once ("Â·" -> "·")."""
    for _ in range(4):
        if not re.search(r"[ÃÂâ]", s):
            break
        try:
            s = s.encode("cp1252").decode("utf-8")
        except UnicodeError:
            break
    return s


def clean_payee(raw):
    s = fix_mojibake(html.unescape(raw or ""))
    s = re.sub(r"(?<=[A-Za-z])[ÃÂâ][^\sA-Za-z]*(?=s\b)", "'", s)  # unrecoverable debris before a possessive s
    s = re.sub(r"[ÃÂ][^\sA-Za-z]*", " ", s)
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s)                         # control characters between items
    return " ".join(s.split())


def clean_label(raw):
    """Account names: drop the leading account number and any separator, repair encoding."""
    s = fix_mojibake(html.unescape(raw or ""))
    s = re.sub(r"^\s*\d[\d.]*\s*[^A-Za-z0-9(]*\s*", "", s)
    s = re.sub(r"\s*[ÃÂ][^\sA-Za-z]*\s*", " ", s)
    return " ".join(s.split()) or (raw or "").strip()


# 'NICK MOTTA', 'JOHN Q PUBLIC', 'ROBERT JR. DEKORVER', 'FRANK N MURDOCK JR', 'THOMAS STEWART II'. Couples and
# three-word names are left to the first-name privacy pattern and vendor_map rows: as a shape they also match
# businesses ('The Bow Shop', 'Rib and Chop House').
PERSON_NO_COMMA = re.compile(r"^[A-Za-z'\-]{2,}( (JR|SR)\.?)?( [A-Za-z]\.?)? [A-Za-z'\-]{2,}( (JR|SR|II|III)\.?)?$", re.I)


def is_person(raw):
    raw = (raw or "").strip()
    return bool(PERSON.match(raw)) and not BUSINESS_WORDS.search(raw) and len(raw.split(",")[0].split()) <= 3


def looks_like_person(raw):
    """'NICK MOTTA'-style names. Only used for payees that no vendor_map row or keyword rule claims."""
    raw = re.sub(r"\(.*?\)|[*#0-9]", " ", raw or "")  # "NOLAN CURTIS (rent)", "MONTE CURTIS*"
    raw = " ".join(raw.split())
    return bool(PERSON_NO_COMMA.match(raw)) and not BUSINESS_WORDS.search(raw)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def payee_name(raw):
    """(payee name as shown, text that names the vendor). Card lines reported as 'VISA - merchant date' are
    shown without the date and named after the merchant. A vendor number ('V0409 ', ' (v0000749)'), a card processor prefix
    ('SQ *', 'PY *') and Newton Town's '/FIRE/item' tail are not part of the vendor's name."""
    s = clean_payee(raw)
    m = CARD_PAYEE.match(s)
    shown, text = (f"VISA - {m.group(1)}", m.group(1)) if m else (s, s)
    text = VENDOR_NO.sub("", text)
    text = VENDOR_NO_END.sub("", text) or text
    m = SLASH_FIRE.match(text)
    if m:
        text = m.group(1).strip()
    text = PROCESSOR.sub("", text).strip() or text
    return shown, text


def person_parts(name):
    """The name and its '/'-separated parts ('MEMORY LANE/RUSSEL BROWN')."""
    return [name] + [p for p in SLASH.split(name) if p and p != name]


def police_only(r):
    """Lines of a police department (Lone Peak Public Safety District), not of fire, EMS or wildland."""
    return bool(POLICE.search(f"{r['org1']} {r['org2']}")) and not FIRE_ORG.search(f"{r['org1']} {r['org2']} {r['org3']}")


def desc_key(s):
    return re.sub(r"[^a-z0-9]+", "", clean_payee(s).lower())


def reupload_copies(path):
    """{line number: rule} for transaction lines an entity uploaded again in a later batch. The query keeps one line
    per entity, id, posting date, payee, account and amount; these rules find the copies it misses:
      same id      the same id, posting date, payee and amount in a later batch (the batch changed the account)
      new id       ids 'TYPE,MM/YY,DOC,SEQ,...': the same type, period, posting date, payee, amount and description, and
                   the same DOC or SEQ, in a later batch (the batch renumbered the ids)
      whole batch  a later batch repeats at least 90% of the lines of an earlier batch of 20 or more lines (posting
                   date, payee, amount and description): its matching lines
    Lines that repeat within one batch are kept: they are separate entries (monthly charges, split invoices)."""
    lines = []                                                 # (entity, batch, id, date, payee, cents, description)
    for r in transactions(path):
        lines.append((sys.intern(r["entity_name"]), sys.intern(r["batch_id"]), r["id"], r["posting_date"],
                      r["vendor_name"], round(float(r["amount"] or 0) * 100), desc_key(r["description"])))
    copies, source = {}, {}                                    # line -> rule; line -> batch it repeats
    first = {}
    for e, b, i, d, v, c, _ in lines:
        k = (e, i, d, v, c)
        if k not in first or b < first[k]:
            first[k] = b
    for n, (e, b, i, d, v, c, _) in enumerate(lines):
        if first[(e, i, d, v, c)] != b:
            copies[n], source[n] = "same id", first[(e, i, d, v, c)]
    groups = collections.defaultdict(list)
    for n, (e, b, i, d, v, c, ds) in enumerate(lines):
        m = COMMA_ID.match(i)
        if m and n not in copies:
            groups[(e, m[1], m[2], d, v, c, ds)].append((n, b, m[3], m[4]))
    for g in groups.values():
        b0 = min(x[1] for x in g)
        docs = {x[2] for x in g if x[1] == b0}
        seqs = {x[3] for x in g if x[1] == b0}
        for n, b, doc, seq in g:
            if b != b0 and (doc in docs or seq in seqs):
                copies[n], source[n] = "new id", b0
    # Whole batches: lines found above count toward the overlap, the other lines match by content
    size = collections.Counter((e, b) for e, b, *_ in lines)
    overlap = collections.Counter((lines[n][0], b0, lines[n][1]) for n, b0 in source.items())
    content = collections.defaultdict(collections.Counter)     # (entity, batch) -> other lines by content
    for n, (e, b, _, d, v, c, ds) in enumerate(lines):
        if n not in copies:
            content[(e, b)][(d, v, c, ds)] += 1
    batches = collections.defaultdict(set)
    for (e, b), cnt in content.items():
        for k in cnt:
            batches[(e, k)].add(b)
    for (e, k), bs in batches.items():
        bs = sorted(bs)
        for j, b0 in enumerate(bs):
            for b1 in bs[j + 1:]:
                overlap[(e, b0, b1)] += min(content[(e, b0)][k], content[(e, b1)][k])
    repeat = {}                                                # (entity, later batch) -> earlier batch it repeats
    for (e, b0, b1), n in sorted(overlap.items()):
        if size[(e, b0)] >= 20 and n >= 0.9 * size[(e, b0)]:
            repeat.setdefault((e, b1), b0)
    left = {eb: {k: min(n, content[(eb[0], b0)][k]) for k, n in content[eb].items()} for eb, b0 in repeat.items()}
    for n, (e, b, _, d, v, c, ds) in enumerate(lines):
        if n not in copies and left.get((e, b), {}).get((d, v, c, ds), 0) > 0:
            left[(e, b)][(d, v, c, ds)] -= 1
            copies[n] = "whole batch"
    return copies


def account_names(r):
    """The line's account names as the account worklists joined them (config/account_rules.csv)."""
    return " | ".join(x for x in (r["cat1"], r["cat2"], r["cat3"]) if x.strip())


def loose(s):
    return " ".join(s.lower().split())


def staff_by_year(tu, tid):
    """People paid, wages and benefits per fiscal year from the compensation files.
    A person is one employee number with wages in a year's file; their title is the title on their largest
    wage line. Benefits are employer-paid only; reimbursements and employee-paid deductions are left out."""
    out = {}
    for year in YEARS:
        path = tu / "compensation" / str(tid) / f"{year}.json.gz"
        if not path.exists():
            continue
        pay = collections.defaultdict(float)
        top_line = {}
        wages = benefits = 0.0
        for r in json.loads(read_gz(path)):
            amount = r["net_amount"] or 0
            kind = " ".join(r.get(f) or "" for f in ("cat1", "cat2", "description")).lower()
            if "reimb" in kind:
                continue
            if re.search(r"wage|compensation|salar|paid leave|payroll", kind):
                wages += amount
                pay[r["employee"]] += amount
                if amount > top_line.get(r["employee"], (0, ""))[0]:
                    title = " ".join(fix_mojibake(r.get("title") or "").split())
                    title = re.sub(r"^(?=[A-Z0-9]*\d)[A-Z][A-Z0-9]{2,}\s+", "", title)  # payroll code prefix "CAPO89 Captain"
                    top_line[r["employee"]] = (amount, title or "No title")
            elif "benefit" in kind and "employee paid" not in kind:
                benefits += amount
            # reimbursements and employee-paid deductions are left out
        paid = [e for e, total in pay.items() if total > 0]
        if not paid:
            continue
        titles = collections.Counter(top_line[e][1] for e in paid if e in top_line)
        out[str(year)] = {"people": len(paid), "wages": round(wages), "benefits": round(benefits),
                          "titles": dict(titles.most_common())}
    return out


def raw_dirs():
    return sorted(p for p in (ROOT / "raw").iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))


def latest_raw():
    """Newest raw folder with public-API files."""
    dirs = [p for p in raw_dirs() if (p / "transparent_utah").is_dir()]
    return dirs[-1]


def latest_bq(pattern):
    """Newest raw/<date>/transparent_utah_bigquery/ file matching pattern, or None."""
    for d in reversed(raw_dirs()):
        found = sorted((d / BQ_DIR).glob(pattern)) if (d / BQ_DIR).is_dir() else []
        if found:
            return found[-1]
    return None


def transactions(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def agency_id(a):
    """Utah agency id: 'UT-' and the Transparent Utah entity id ('UT-359')."""
    return f"UT-{a['id']}"


def ut_sort_key(aid):
    """Today's Utah order: numeric ids in number order, then any slug ids."""
    t = aid[3:]
    return (0, int(t), "") if t.isdigit() else (1, 0, t)


class Rules:
    """Config rules for payees, accounts and descriptions."""

    def __init__(self, categories):
        cat_ids = {c["id"] for c in categories}
        self.purchasing = {c["id"] for c in categories if c["purchasing"] == "yes"}
        self.vendor_rules = [(r["category"], re.compile(r["pattern"]), (r.get("vendor") or "").strip())
                             for r in read_csv("vendor_rules.csv") + read_csv("keyword_rules.csv")]
        for c, _, _ in self.vendor_rules:
            assert c in cat_ids, f"keyword_rules.csv: unknown category {c}"
        self.vendor_map = {}
        for r in read_csv("vendor_map.csv"):
            assert r["category"] in cat_ids, f"vendor_map.csv: unknown category {r['category']} for {r['name_key']}"
            self.vendor_map[r["name_key"]] = (r["vendor"].strip(), r["category"])
        self.redactions = [re.compile(r["pattern"], re.I) for r in read_csv("payee_name_redactions.csv")]
        self.cards = [re.compile(r["pattern"], re.I) for r in read_csv("card_programs.csv")]
        # Account rules: exact account names first, then the same names ignoring case and spacing
        self.accounts, self.accounts_loose = {}, {}
        for r in sorted(read_csv("account_rules.csv"), key=lambda r: CONFIDENCE.get(r["confidence"], 3)):
            assert r["mode"] in ("override", "refine"), f"account_rules.csv: unknown mode {r['mode']}"
            assert r["category"] in cat_ids or r["category"] == "vendor", f"account_rules.csv: unknown category {r['category']}"
            # skip_vendor_category: a refine row leaves payees of these vendor categories alone
            skip = frozenset(s.strip() for s in (r.get("skip_vendor_category") or "").split(";") if s.strip())
            assert skip <= cat_ids, f"account_rules.csv: unknown skip_vendor_category {skip - cat_ids}"
            rule = (r["category"], r["mode"], skip)
            self.accounts[r["account_names"]] = rule
            self.accounts_loose.setdefault(loose(r["account_names"]), rule)
        self.descriptions = []
        for r in read_csv("description_rules.csv"):
            assert r["category"] in cat_ids, f"description_rules.csv: unknown category {r['category']}"
            skip = {s.strip() for s in r.get("skip_vendor_category", "").split(";") if s.strip()}
            self.descriptions.append((r["category"], re.compile(r["pattern"], re.I), skip))
        # Privacy patterns: all apply to descriptions; payee_names says whether one also applies to payee names
        # that no vendor_map row covers ("yes", "no", or "without business words")
        self.privacy, self.payee_privacy = [], []
        for r in read_csv("description_privacy_patterns.csv"):
            rx = re.compile(r["pattern"], re.I)
            self.privacy.append(rx)
            mode = r.get("payee_names", "yes")
            assert mode in ("yes", "no", "without business words"), f"description_privacy_patterns.csv: payee_names {mode}"
            if mode != "no":
                self.payee_privacy.append((rx, mode == "yes"))
        self._acct, self._desc, self._withhold = {}, {}, {}

    def account(self, names):
        """(category, mode, skip, how) for a line's account names; how is 'exact', 'loose' or None."""
        if names not in self._acct:
            if names in self.accounts:
                self._acct[names] = self.accounts[names] + ("exact",)
            elif loose(names) in self.accounts_loose:
                self._acct[names] = self.accounts_loose[loose(names)] + ("loose",)
            else:
                self._acct[names] = (None, None, frozenset(), None)
        return self._acct[names]

    def is_broad(self, name, category):
        return category in BROAD or (category == "finance" and any(rx.search(name) for rx in self.cards))

    def description(self, text, vendor_category):
        key = (text, vendor_category)
        if key not in self._desc:
            low = text.lower()
            self._desc[key] = next((c for c, rx, skip in self.descriptions
                                    if vendor_category not in skip and rx.search(low)), None)
        return self._desc[key]

    def private_name(self, name, always_only=False):
        """True when an unreviewed payee name may be a person's name. always_only: only the patterns that apply
        to every payee name (payee_names=yes), for the payee names of a mapped vendor."""
        business = bool(BUSINESS_WORDS.search(name))
        return any(rx.search(name) for rx, always in self.payee_privacy if always or not (business or always_only))

    def person_segment(self, name):
        """True when a part of the name after the first ('BANK - FIRST LAST', 'LLC, FIRST LAST', 'BUSINESS/FIRST LAST INC')
        is shaped like a person's name and matches a payee-name privacy pattern (most often the first-name list)."""
        parts = [p for p in SEGMENT.split(name) if p]
        return any(looks_like_person(norm(p)) and self.private_name(norm(p)) for p in parts[1:])

    def withhold(self, raw, shown):
        """True when a description may identify a person (privacy patterns, payee redactions, email, phone)."""
        if raw not in self._withhold:
            self._withhold[raw] = any(rx.search(t) for t in {raw, shown}
                                      for rx in self.privacy + self.redactions + [EMAIL, PHONE])
        return self._withhold[raw]


def classify_line(rules, vendor_name, vendor_category, accounts, description, vendor_account=False, payee=""):
    """(category, method) of one transaction line. vendor_name and vendor_category are the payee's vendor;
    vendor_account: the agency also pays named payees from these accounts; payee: the payee text as reported."""
    cat, mode, skip, _ = rules.account(accounts)
    if mode == "override" and cat != "vendor":
        return cat, "override"
    if not rules.is_broad(vendor_name, vendor_category):
        return vendor_category, "vendor"
    journal = vendor_category == "placeholder" and vendor_account     # corrections of vendor payments stay under
    if journal and JOURNAL.search(payee):                              # No vendor named ('JE RECON - TURNOUT RECON')
        return "placeholder", "fallback"
    d = rules.description(description, vendor_category)
    if d:
        return d, "description"
    if journal and JOURNAL.search(f"{description} {accounts}"):
        return "placeholder", "fallback"
    if mode == "refine" and cat != "vendor" and vendor_category not in skip:
        return cat, "refine"
    if vendor_category == "finance" and not DEBT_ACCOUNT.search(accounts) and not DEBT_DESC.search(description):
        return "unclassified", "fallback"                   # a card purchase with no rule for its item
    return vendor_category, "fallback"


def fy_start_from_lines(counts):
    """'July' or 'January' from how July-December posting dates map to fiscal years; None when unclear."""
    total = sum(counts.values())
    if total < 30:
        return None
    k = max(counts, key=counts.get)
    if k == "other" or counts[k] < 0.8 * total:
        return None
    return {"jul": "July", "jan": "January"}[k]


def load_agencies(raw, rows_cfg, fy_counts, fire_expenses):
    tu = raw / "transparent_utah"
    entity_types = {e["transparency_id"]: e["entity_government_type"]
                    for e in read_json_gz(tu / "entities.json.gz", []) if e.get("transparency_id")}
    usfa = {r["FDID"]: r for r in csv.DictReader(read_gz(raw / "usfa" / "registry_ut.csv.gz").decode("utf-8-sig").splitlines(),
                                                  skipinitialspace=True) if r["FDID"]}
    revenue_exclusions = [re.compile(r["pattern"], re.I) for r in read_csv("revenue_exclusions.csv")]
    agencies = []
    for a in rows_cfg:
        api = a["kind"] in API_KINDS and a["tu_id"]
        tid = int(a["tu_id"]) if api else None
        details = read_json_gz(tu / "details" / f"{tid}.json.gz", []) if api else []
        details = details[0] if details else {}
        budget = collections.defaultdict(float)
        if api:
            for x in read_json_gz(tu / "expense_categories" / f"{tid}.json.gz", []):
                if x["fiscal_year"] in YEARS:
                    budget[x["fiscal_year"]] += x["net_amount"] or 0
            budget_source = "expense_categories" if budget else None
        else:
            budget.update(fire_expenses.get(a["name"], {}))
            budget_source = "fire_expenses_by_year" if budget else None
        revenue = collections.defaultdict(lambda: collections.defaultdict(float))
        for x in read_json_gz(tu / "revenue_categories" / f"{tid}.json.gz", []) if api else []:
            if x["fiscal_year"] in YEARS:
                revenue[str(x["fiscal_year"])][clean_label(x["agg1"])] += x["net_amount"] or 0
        revenue_excluded = sorted({c for cats in revenue.values() for c in cats
                                   if any(rx.search(c) for rx in revenue_exclusions)})
        u = usfa.get(a["usfa_fdid"]) if a["usfa_fdid"] else None
        etype = entity_types.get(tid) if api else a["govt_lvl"]
        fy_start = ({"01": "January", "07": "July"}.get((details.get("fiscal_year_begins") or "")[5:7]) if api
                    else fy_start_from_lines(fy_counts.get(a["name"], {})))
        agencies.append({
            "id": agency_id(a),
            "name": a["name"],
            "type": ENTITY_TYPES.get(etype, etype),
            "kind": a["kind"],
            "govt_lvl": a["govt_lvl"],
            "county": a["county"] or None,
            "city": details.get("shipping_city") or details.get("billing_city"),
            "website": details.get("website"),
            "staffing": u["Dept Type"] if u else None,
            "staffing_group": STAFFING_GROUPS.get(u["Dept Type"]) if u else None,
            "usfa": {
                "fdid": u["FDID"], "name": u["Fire dept name"], "stations": int(u["Number Of Stations"] or 0),
                "career": int(u["Active Firefighters - Career"] or 0),
                "volunteer": int(u["Active Firefighters - Volunteer"] or 0),
                "paid_per_call": int(u["Active Firefighters - Paid per Call"] or 0),
            } if u else None,
            "budget": {str(y): round(budget[y]) for y in YEARS if y in budget},
            "budget_source": budget_source,
            "revenue": {y: {c: round(v) for c, v in sorted(cats.items()) if round(v)} for y, cats in sorted(revenue.items())},
            "revenue_total": {y: sum(round(v) for c, v in cats.items() if c not in revenue_excluded)
                              for y, cats in sorted(revenue.items())},
            "revenue_excluded": revenue_excluded,
            "staff": staff_by_year(tu, tid) if api else {},
            "fy_start": fy_start,
            "notes": a["notes"] or None,
        })
    return agencies


# --- Shared by every state -----------------------------------------------------------------------------------

def classify_key(rules, k, display):
    """(vendor name, category, method, named) of a payee key: named is True when config names the vendor
    (vendor_map, or a rule with a vendor name); otherwise the vendor is shown under display, the payee's own name."""
    if k in rules.vendor_map:
        return rules.vendor_map[k][0], rules.vendor_map[k][1], "map", True
    if not k:
        return "No vendor named", "placeholder", "rule", True
    for cat, rx, vendor in rules.vendor_rules:
        if rx.search(k):
            return vendor or display, cat, "rule", bool(vendor)
    return display, "unclassified", "none", False


def cancel_credits(pay_lines, credits):
    """Single payments a credit cancels: a payment is left out when a credit or reversal of the same amount to the
    same payee cancels it (the latest payment on or before the credit date, else the earliest after it).
    pay_lines: (agency, date, vendor, category, amount, ...); credits: (agency, vendor, cents) -> credit dates."""
    by_key = collections.defaultdict(list)
    for i, p in enumerate(pay_lines):
        by_key[(p[0], p[2], round(p[4] * 100))].append(i)
    dropped = set()
    for key, dates in credits.items():
        cands = sorted(by_key.get(key, []), key=lambda i: pay_lines[i][1])
        for d in sorted(dates):
            left = [i for i in cands if i not in dropped]
            if not left:
                break
            before = [i for i in left if pay_lines[i][1] <= d]
            dropped.add(before[-1] if before else left[0])
    return dropped


def finish_vendors(rows, payments, vendors, aliases, categories, neris, sort_key, used=()):
    """Keep vendors and payee names that appear in a row, a payment or `used` (vendor indexes of item lines), renumber
    them, sort rows and payments, and set each vendor's main category (largest net spend), payee names and NERIS flag.
    rows: {(agency, vendor, year, category, alias): net}. Returns (rows, payments, vendors, aliases, old -> new vendor)."""
    rows = [[a, v, y, c, round(x, 2), al] for (a, v, y, c, al), x in rows.items() if round(x, 2) != 0]
    used_v = {r[1] for r in rows} | {p[2] for p in payments} | set(used)
    used_a = {r[5] for r in rows} | {p[6] for p in payments}
    used_a.discard(-1)
    v_new = {vi: n for n, vi in enumerate(vi for vi in range(len(vendors)) if vi in used_v)}
    a_new = {ai: n for n, ai in enumerate(ai for ai in range(len(aliases)) if ai in used_a)}
    remap_a = lambda ai: a_new[ai] if ai >= 0 else -1  # noqa: E731
    rows = sorted(([a, v_new[v], y, c, x, remap_a(al)] for a, v, y, c, x, al in rows), key=lambda r: (sort_key(r[0]), r[1:]))
    payments = sorted([[a, d, v_new[v], c, x, di, remap_a(al), fy] for a, d, v, c, x, di, al, fy in payments],
                      key=lambda p: (sort_key(p[0]), p[1], -p[4], p[2]))
    vendors = [vendors[vi] for vi in sorted(v_new)]
    aliases = [aliases[ai] for ai in sorted(a_new)]
    cat_net = collections.defaultdict(collections.Counter)
    names_of = collections.defaultdict(set)
    for a, v, y, c, x, al in rows:
        cat_net[v][categories[c]["id"]] += x
        names_of[v].add(al)
    for p in payments:
        names_of[p[2]].add(p[6])
    for vi, v in enumerate(vendors):
        net = cat_net[vi]
        if net:
            pos = {c: x for c, x in net.items() if x > 0}
            v["category"] = max(pos, key=lambda c: (pos[c], c)) if pos else max(net, key=lambda c: (abs(net[c]), c))
        v["aliases"] = sorted(al for al in names_of[vi] if al >= 0)
        v["neris"] = None if v["id"] == "individuals" else (any(rx.search(norm(v["name"])) for _, rx in neris) or None)
    return rows, payments, vendors, aliases, v_new


def coverage_numbers(rows, categories, cov):
    """(purchasing total, unclassified, meta coverage by method) of a state's rows."""
    buy = sum(r[4] for r in rows if categories[r[3]]["purchasing"] == "yes")
    unclassified = sum(r[4] for r in rows if categories[r[3]]["id"] == "unclassified")
    by_method = {m: {"purchasing": round(cov[m]["purchasing"]), "all": round(cov[m]["all"]), "lines": cov[m]["lines"]}
                 for m in METHODS}
    return buy, unclassified, by_method


def rel(p):
    return p.relative_to(ROOT).as_posix() if p else None


def write_worklist(path, key_spend, key_names, key_agencies, key_class, names, pick, method_of=None):
    """Payees to review in config/vendor_map.csv: name key, most common names, net spend, agencies, category."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name_key", "raw_names", "spend", "agencies", "agency_names", "current_category", "method"])
        for k in sorted(key_spend):
            _, cat, method, named = key_class[k]
            if pick(k):
                w.writerow([k, " | ".join(n for n, _ in key_names[k].most_common(4)), round(key_spend[k]),
                            len(key_agencies[k]), " | ".join(sorted(names[t] for t in key_agencies[k])[:4]),
                            cat, method_of(k, method) if method_of else method])


# --- Utah ------------------------------------------------------------------------------------------------------

def build_utah(rules, categories, cat_pos, neris):
    """Utah from the Transparent Utah BigQuery lines and query service files, as the single-state build did; only
    the agency ids changed ('UT-359'). Returns the state's tables, today's meta and what the report needs."""
    raw = latest_raw()
    tx_path = latest_bq("fire_transactions*.csv.gz")
    assert tx_path, f"no raw/<date>/{BQ_DIR}/fire_transactions*.csv.gz file"
    fx_path = latest_bq("fire_expenses_by_year.csv.gz") or latest_bq("fire_expenses_by_year.csv")
    purchasing = rules.purchasing

    cfg = [a for a in read_csv("agencies.csv") if a["include"] == "yes"]
    aid_by_name = {a["name"]: agency_id(a) for a in cfg}

    def payee_parts(raw_name):
        """(payee name as shown, vendor key or None for a person, text that names the vendor). A vendor_map row
        decides first ('HAYES GODFREY BELL, P.C.' is a firm, not 'Last, First')."""
        shown, text = payee_name(raw_name)
        k, kt = norm(shown), norm(text)
        if k in rules.vendor_map:
            return shown, k, text
        if kt in rules.vendor_map:
            return shown, kt, text
        if any(is_person(p) for p in person_parts(shown) + person_parts(text)):
            return shown, None, text
        return shown, (kt if text != shown else k), text   # card line or prefixed name: the merchant is the vendor

    # Lines left out: copies of a transaction uploaded again, and police lines
    copies = reupload_copies(tx_path)

    def line_kept(n, r):
        return n not in copies and not police_only(r)

    # Pass 1 over the transaction lines: payee statistics for vendor naming, and fiscal-year layout per entity
    payee_of = {}                                             # raw vendor_name -> payee_parts()
    key_spend = collections.defaultdict(float)
    key_names = collections.defaultdict(collections.Counter)
    key_agencies = collections.defaultdict(set)
    patient_keys, staff_keys = set(), set()                   # payees seen on patient accounts / staff lines
    account_keys = collections.defaultdict(set)               # (agency, account names) -> payees paid from them
    fy_counts = collections.defaultdict(collections.Counter)
    raw_total = collections.defaultdict(float)
    raw_lines = collections.Counter()
    skipped = collections.Counter()
    left_out = collections.defaultdict(lambda: [0, 0.0])      # reason -> [lines, dollars]
    for n, r in enumerate(transactions(tx_path)):
        aid = aid_by_name.get(r["entity_name"])
        fy, amount = int(r["fiscal_year"]), float(r["amount"] or 0)
        if aid is None or fy not in YEARS:
            skipped[r["entity_name"]] += 1
            continue
        if not line_kept(n, r):
            why = f"uploaded again ({copies[n]})" if n in copies else "police department"
            left_out[why][0] += 1
            left_out[why][1] += amount
            continue
        raw_total[aid] += amount
        raw_lines[aid] += 1
        d = r["posting_date"]
        if len(d) >= 7 and d[5:7] >= "07":
            fy_counts[r["entity_name"]]["jul" if fy == int(d[:4]) + 1 else "jan" if fy == int(d[:4]) else "other"] += 1
        parts = payee_of.get(r["vendor_name"])
        if parts is None:
            parts = payee_of[r["vendor_name"]] = payee_parts(r["vendor_name"])
        _, k, text = parts
        if k is None:
            continue
        key_spend[k] += amount
        key_names[k][text] += abs(amount)
        key_agencies[k].add(aid)
        account_keys[(aid, account_names(r))].add(k)
        if PATIENT_ACCOUNT.search(account_names(r)):
            patient_keys.add(k)
        if STAFF_DESC.search(r["description"]):
            staff_keys.add(k)

    # Vendors
    def classify(k):
        """classify_key with Utah's clean-up of the payee's own name: a person's name after a business name is cut
        off, and payee text matching config/payee_name_redactions.csv is not shown."""
        if k in rules.vendor_map or not k:
            return classify_key(rules, k, None)
        display = key_names[k].most_common(1)[0][0].strip()
        if rules.person_segment(display):                     # 'ZIONS BANK - FIRST LAST' -> 'ZIONS BANK'
            display = SEGMENT.split(display)[0].strip(" ()-,") or display
        if any(rx.search(display) for rx in rules.redactions):
            display = re.sub(r"\S+@\S+", "", display).strip(" ()-,")
            if not display or any(rx.search(display) for rx in rules.redactions):
                display = "Payee name withheld"
        return classify_key(rules, k, display)

    key_class = {k: classify(k) for k in key_spend}

    def in_worklist(k):  # payees big enough to be reviewed one by one in config/vendor_map.csv
        return len(key_agencies[k]) >= 2 or abs(key_spend[k]) >= 10000

    # Payees whose names are withheld: mapped to "individuals"; small unclaimed payees shaped like a person's name
    # (any '/'-separated part); payees shown under their own name when it matches a payee-name privacy pattern, or
    # when they were paid on a patient account; unclaimed payees without business words paid as staff
    def person_like(n):
        return any(looks_like_person(p) or is_person(p) for p in person_parts(n))

    person_keys = {k for k, (_, cat, method, named) in key_class.items()
                   if cat == "individuals"
                   or (not in_worklist(k) and method == "none" and all(person_like(n) for n in key_names[k]))
                   or (not named and any(rules.private_name(n) for n in key_names[k]))
                   or (not named and k in patient_keys)
                   or (method == "none" and k in staff_keys and not any(BUSINESS_WORDS.search(n) for n in key_names[k]))}

    # Accounts an agency pays named payees from: there, journal entries with no vendor correct those payments
    vendor_accounts = {ak for ak, ks in account_keys.items() if any(key_class[k][1] != "placeholder" for k in ks)}

    vendors, vendor_index, key_vendor = [], {}, {}
    for k in sorted(key_spend, key=lambda k: (-abs(key_spend[k]), k)):
        if k in person_keys:
            continue
        name, cat, method, _ = key_class[k]
        vid = slug(name) or "unnamed"
        if vid not in vendor_index:
            vendor_index[vid] = len(vendors)
            vendors.append({"id": vid, "name": name, "category": cat, "method": method, "aliases": []})
        key_vendor[k] = vendor_index[vid]
    individuals_idx = len(vendors)
    vendors.append({"id": "individuals", "name": INDIVIDUALS, "category": "individuals", "method": "rule", "aliases": []})

    aliases, alias_index = [], {}
    payee_info = {}                                           # raw vendor_name -> (vendor index, vendor name, category, alias)
    withheld_names = 0

    def payee(raw_name):
        nonlocal withheld_names
        if raw_name in payee_info:
            return payee_info[raw_name]
        name, k, _ = payee_of[raw_name]
        if k is None or k in person_keys:
            info = (individuals_idx, INDIVIDUALS, "individuals", -1)
        elif "(names withheld)" in vendors[key_vendor[k]]["name"]:
            vi = key_vendor[k]                                # a vendor_map group of people: no payee names
            info = (vi, key_class[k][0], key_class[k][1], -1)
        else:
            vi = key_vendor[k]
            if name not in alias_index:
                alias_index[name] = len(aliases)
                shown = name
                if any(rx.search(name) for rx in rules.redactions) or rules.private_name(
                        name, always_only=key_class[k][2] == "map") or rules.person_segment(name):
                    shown = vendors[vi]["name"] + " (payee text withheld)"
                    withheld_names += 1
                aliases.append(shown)
            info = (vi, key_class[k][0], key_class[k][1], alias_index[name])
        payee_info[raw_name] = info
        return info

    # Pass 2: category of each line, rows, coverage and single payments
    rows = collections.defaultdict(float)
    cov = {m: {"purchasing": 0.0, "all": 0.0, "lines": 0} for m in METHODS}
    acct_hits = collections.Counter()
    pay_lines = []                                            # candidate single payments
    credits = collections.defaultdict(list)                   # (agency, vendor, cents) -> dates of credits
    for n, r in enumerate(transactions(tx_path)):
        aid = aid_by_name.get(r["entity_name"])
        fy = int(r["fiscal_year"])
        if aid is None or fy not in YEARS or not line_kept(n, r):
            continue
        amount = float(r["amount"] or 0)
        vi, vname, vcat, al = payee(r["vendor_name"])
        accounts = account_names(r)
        cat, method = classify_line(rules, vname, vcat, accounts, r["description"], (aid, accounts) in vendor_accounts,
                                    payee_of[r["vendor_name"]][0])
        acct_hits[rules.account(accounts)[3]] += 1
        rows[(aid, vi, fy, cat_pos[cat], al)] += amount
        c = cov[method]
        c["all"] += amount
        c["lines"] += 1
        if cat in purchasing:
            c["purchasing"] += amount
            if amount >= PAYMENT_MIN:
                pay_lines.append((aid, r["posting_date"], vi, cat_pos[cat], round(amount, 2), r["description"], al, fy))
        if amount <= -PAYMENT_MIN:
            credits[(aid, vi, round(-amount * 100))].append(r["posting_date"])

    # Single payments: a payment is left out when a credit or reversal of the same amount to the same payee
    # cancels it (cancel_credits). Descriptions that may identify a person are withheld.
    dropped = cancel_credits(pay_lines, credits)
    descriptions, desc_index = [""], {"": 0}
    payments, withheld = [], 0
    for i, (aid, date, vi, ci, amount, desc, al, fy) in enumerate(pay_lines):
        if i in dropped:
            continue
        shown = clean_payee(desc)
        if '""' in shown:                                     # CSV quoting left in the source: '"5"" hose"'
            shown = shown.strip('"').replace('""', '"')
        if shown and (vi == individuals_idx or rules.withhold(desc, shown)):
            shown = ""
            withheld += 1
        if shown not in desc_index:
            desc_index[shown] = len(descriptions)
            descriptions.append(shown)
        payments.append([aid, date, vi, ci, amount, desc_index[shown], al, fy])

    # Keep vendors and payee names that appear in a row or payment; primary category = largest net spend
    rows, payments, vendors, aliases, _ = finish_vendors(rows, payments, vendors, aliases, categories, neris, ut_sort_key)

    # Agencies, with annual fire expenses for cities, towns and counties when the file is there
    fire_expenses = collections.defaultdict(dict)
    for x in read_table(fx_path) if fx_path else []:
        if int(x["fiscal_year"]) in YEARS and x["govt_lvl"] in ("City", "Town", "County"):
            fire_expenses[x["entity_name"]][int(x["fiscal_year"])] = float(x["fire_expenses"] or 0)
    agencies = load_agencies(raw, cfg, fy_counts, fire_expenses)
    agency_ids = {a["id"] for a in agencies}

    # FEMA firefighter grants matched to agencies through config/grant_recipients.csv
    recipient_map = {r["fema_recipient"]: agency_id({"id": r["agency_id"]}) for r in read_csv("grant_recipients.csv")}
    grants = []
    grants_path = raw / "openfema" / "firefighter_grants_ut.json.gz"
    for g in json.loads(read_gz(grants_path)):
        aid = recipient_map.get(g["vendorName"])
        if aid in agency_ids:
            grants.append({"agency": aid, "recipient": g["vendorName"], "year": g["fiscalYear"],
                           "program": g["programName"], "amount": g["awardAmount"], "award": g["awardNumber"]})
    grants.sort(key=lambda g: (-g["year"], g["award"]))

    # Multi-state fields: every Utah agency is tier 1 (payee lines), also the two without lines (owner decision)
    with_grants = {g["agency"] for g in grants}
    tu_ids = {agency_id(a): int(a["tu_id"]) if a["tu_id"].isdigit() else None for a in cfg}
    for i, a in enumerate(agencies):
        u = a["usfa"]
        sources = {"ut_transparent_utah"} | ({"ut_query_service"} if a["kind"] in API_KINDS else set()) | (
            {"usfa"} if u else set()) | ({"openfema"} if a["id"] in with_grants else set())
        agencies[i] = {"id": a["id"], "state": "UT", **{k: v for k, v in a.items() if k != "id"},
                       "coverage": 1, "sources": sorted(sources), "tu_id": tu_ids[a["id"]], "lines": raw_lines[a["id"]]}

    # Coverage numbers for the About section
    buy, unclassified, by_method = coverage_numbers(rows, categories, cov)
    meta = {
        "built": datetime.date.today().isoformat(),
        "fetched": raw.name,
        "transactions_fetched": tx_path.parent.parent.name,
        "years": YEARS,
        "partial_years": PARTIAL_YEARS,
        "raw_path": f"raw/{raw.name}",
        "transactions_file": rel(tx_path),
        "fire_expenses_file": rel(fx_path),
        "transparent_utah": TU_SITE,
        "counts": {"agencies": len(agencies), "vendors": len(vendors), "rows": len(rows), "grants": len(grants),
                   "payments": len(payments), "lines": sum(raw_lines.values()),
                   "lines_reuploaded": sum(v[0] for k, v in left_out.items() if k.startswith("uploaded again")),
                   "lines_police": left_out["police department"][0]},
        "payments_rule": f"Transaction lines of ${PAYMENT_MIN:,} or more in purchasing categories, as posted (gross). A line"
                         " is left out when a credit or reversal of the same amount to the same payee cancels it; smaller"
                         " credits are not matched, so the lines can add up to more than the net yearly total."
                         " Descriptions that may identify a person are withheld.",
        "purchasing_total": round(buy),
        "purchasing_classified_share": round(1 - unclassified / buy, 4) if buy else None,
        "coverage": by_method,
    }
    usfa_path = raw / "usfa" / "registry_ut.csv.gz"
    sources = {
        "ut_transparent_utah": {
            "state": "UT", "name": "Transparent Utah transaction lines", "tier": 1, "url": TU_SITE,
            "years": f"{YEARS[0]}-{YEARS[-1]}", "fiscal_year": "Each entity's own fiscal year (cities, towns and districts"
            " mostly July-June, counties January-December), the year it ends in", "fetched": meta["transactions_fetched"],
            "note": "Every expense line the agencies reported to Transparent Utah (BigQuery database), payroll, benefit and"
                    " refund accounts left out; city, town and county lines coded fire. Lines uploaded again in a later"
                    " batch are counted once, police lines of Lone Peak Public Safety District are left out.",
            "raw": meta["transactions_file"]},
        "ut_query_service": {
            "state": "UT", "name": "Transparent Utah public query service", "tier": None, "url": TU_SITE,
            "years": f"{YEARS[0]}-{YEARS[-1]}", "fiscal_year": "Each entity's own fiscal year", "fetched": raw.name,
            "note": "Fire district and interlocal agency details, total expenses, revenue and compensation (employee"
                    " names replaced by numbers); not a documented API.",
            "raw": f"raw/{raw.name}/transparent_utah"},
    }
    return {"state": "UT", "agencies": agencies, "vendors": vendors, "aliases": aliases, "rows": rows,
            "payments": payments, "descriptions": descriptions, "grants": grants, "totals": [], "items": None,
            "meta": meta, "sources": sources, "registry_raw": rel(usfa_path), "grants_raw": rel(grants_path),
            "report": dict(person_keys=person_keys, key_class=key_class, key_spend=key_spend, withheld_names=withheld_names,
                           payments=len(payments), dropped=len(dropped), descriptions=len(descriptions), withheld=withheld,
                           raw_lines=raw_lines, tx_path=tx_path, skipped=skipped, acct_hits=acct_hits, left_out=left_out,
                           buy=buy, unclassified=unclassified, cov=cov, raw_total=raw_total),
            "worklist": dict(key_spend=key_spend, key_names=key_names, key_agencies=key_agencies, key_class=key_class,
                             pick=lambda k: in_worklist(k) or (k in person_keys and key_class[k][1] != "individuals"
                                                               and not key_class[k][3]),
                             method_of=lambda k, m: "withheld" if k in person_keys and key_class[k][1] != "individuals"
                             else m)}


def report_utah(ut):
    R = ut["report"]
    agencies, vendors, rows = ut["agencies"], ut["vendors"], ut["rows"]
    key_class, key_spend, person_keys = R["key_class"], R["key_spend"], R["person_keys"]
    print(f"Utah: {len(agencies)} agencies, {len(vendors)} vendors, {len(ut['aliases'])} payee names,"
          f" {len(rows)} rows, {len(ut['grants'])} grants")
    hidden = [k for k in person_keys if key_class[k][1] != "individuals"]
    print(f"Payees grouped as {INDIVIDUALS} without a vendor_map row: {len(hidden)} names,"
          f" ${sum(key_spend[k] for k in hidden):,.0f}; payee texts withheld under a named vendor: {R['withheld_names']}")
    print(f"Utah payments: {R['payments']} payments ({R['dropped']} cancelled by a credit left out),"
          f" {R['descriptions'] - 1} distinct descriptions, {R['withheld']} descriptions withheld")
    raw_lines, acct_hits, skipped = R["raw_lines"], R["acct_hits"], R["skipped"]
    print(f"Lines: {sum(raw_lines.values()):,} used from {rel(R['tx_path'])}; {sum(skipped.values()):,} lines of"
          f" {len(skipped)} entities not included. Account rules: {acct_hits['exact']:,} lines exact,"
          f" {acct_hits['loose']:,} ignoring case, {acct_hits[None]:,} without a rule")
    for why, (n, dollars) in sorted(R["left_out"].items()):
        print(f"Left out, {why}: {n:,} lines, ${dollars:,.2f}")
    # Payee names shown under their own name with a part shaped like a person's name: review them in vendor_map.csv
    review = sorted({v["name"] for v in vendors if v["method"] != "map" and v["id"] != "individuals"
                     and any(is_person(p) or looks_like_person(p) for p in SLASH.split(v["name"])
                             if p != v["name"] and not re.search(r"\d", p))})
    print(f"Vendor names with a '/' part shaped like a person's name (not in vendor_map.csv): {len(review)}")
    for name in review[:40]:
        print("   ", name)
    buy, unclassified, cov = R["buy"], R["unclassified"], R["cov"]
    print(f"\nPurchasing ${buy:,.0f}; unclassified ${unclassified:,.0f} ({unclassified / buy:.1%})")
    print(f"{'method':12} {'purchasing $':>16} {'share':>7} {'all lines $':>16} {'lines':>9}")
    for m in METHODS:
        c = cov[m]
        print(f"{m:12} {c['purchasing']:16,.0f} {c['purchasing'] / buy:7.1%} {c['all']:16,.0f} {c['lines']:9,}")
    net = collections.defaultdict(float)
    for r in rows:
        net[r[0]] += r[4]
    raw_total = R["raw_total"]
    print(f"\n{'agency':58} {'lines':>7} {'raw file $':>15} {'rows $':>15} {'diff':>6}")
    bad = 0
    for a in sorted(agencies, key=lambda a: -abs(raw_total.get(a["id"], 0))):
        diff = net.get(a["id"], 0) - raw_total.get(a["id"], 0)
        bad += abs(diff) >= 0.01 * max(1, raw_lines[a["id"]])  # rounding: at most half a cent per row
        print(f"{a['name'][:58]:58} {raw_lines[a['id']]:7,} {raw_total.get(a['id'], 0):15,.2f} {net.get(a['id'], 0):15,.2f}"
              f" {diff:6.2f}" + ("" if raw_lines[a["id"]] else "  (no lines)"))
    print(f"{len(agencies) - bad} of {len(agencies)} agencies match the raw file")
    return bad


# --- Other states (data/states/<st>/, docs/multistate/data-contract.md) -----------------------------------------

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
FEDERAL = {
    "usfa": {"name": "USFA National Fire Department Registry", "url": "https://apps.usfa.fema.gov/registry/",
             "note": "Every registered fire department: type, stations and firefighter counts."},
    "openfema": {"name": "OpenFEMA firefighter grants",
                 "url": "https://www.fema.gov/openfema-data-page/non-disaster-assistance-firefighter-grants-v1",
                 "note": "Assistance to Firefighters, SAFER and related grant awards, matched to agencies by recipient name."},
    "neris": {"name": "NERIS integration partner list", "url": "https://neris.fsri.org/integration-partners",
              "note": "Vendors certified to integrate with NERIS, the National Emergency Response Information System."},
}


def month_names(fy_start):
    """'07' -> 'July'; ['07', '09'] -> 'July and September'; None -> None."""
    if not fy_start:
        return None
    ms = [MONTHS[int(m) - 1] for m in ([fy_start] if isinstance(fy_start, str) else fy_start)]
    return ms[0] if len(ms) == 1 else ", ".join(ms[:-1]) + " and " + ms[-1]


def number(s):
    """A published quantity or price as a number: int when whole, None when empty."""
    s = (s or "").strip()
    if not s:
        return None
    x = float(s)
    return int(x) if x == int(x) and "." not in s and "e" not in s.lower() else x


def latest_state_raw(st, source, pattern):
    """Newest raw/<date>/<st>/<source>/ file matching pattern, or None."""
    for d in reversed(raw_dirs()):
        found = sorted((d / st.lower() / source).glob(pattern)) if (d / st.lower() / source).is_dir() else []
        if found:
            return found[-1]
    return None


def state_agency(a, budget, budget_source, lines):
    """An agency of data/states/<st>/agencies.json in the shape of a Utah agency."""
    u = a.get("usfa")
    dept = u.get("dept_type") if u else None
    return {
        "id": a["id"], "state": a["state"], "name": a["name"], "type": None, "kind": a.get("kind"),
        "county": a.get("county"), "city": a.get("city"),
        "staffing": dept, "staffing_group": STAFFING_GROUPS.get(dept) if dept else None,
        "usfa": {"fdid": a.get("usfa_fdid"), "name": a["name"], "stations": u.get("stations") or 0,
                 "career": u.get("career") or 0, "volunteer": u.get("volunteer") or 0,
                 "paid_per_call": u.get("paid_per_call") or 0} if u else None,
        "budget": budget, "budget_source": budget_source, "fy_start": month_names(a.get("fy_start")),
        "notes": None, "coverage": a["coverage"], "sources": list(a["sources"]), "lines": lines,
    }


def build_state(st, rules, categories, cat_pos, neris):
    """One state from data/states/<st>/: the same vendor and category rules as Utah (config/vendor_map.csv,
    vendor_rules.csv, keyword_rules.csv, then classify_line), but payee names and descriptions as published: no
    person grouping and no withholding. A vendor_map row for a group of people ('Individuals (names withheld)')
    gives the category only; the vendor is the payee under its published name.

    Rows and single payments come from the lines in the state's fiscal years (config/states.csv); lines outside them
    (California SCPRS purchase orders, FY2013-FY2015) only name the vendor and category of their item lines."""
    cfg = STATES[st]
    years = set(cfg["years"])
    d = STATE_DATA / st.lower()
    aj = json.loads((d / "agencies.json").read_text(encoding="utf-8"))
    assert aj["state"] == st, f"{d}/agencies.json: state {aj['state']}"
    src_list = aj["sources"]
    tier = {s["source"]: int(s["tier"]) for s in src_list}
    ids = {a["id"] for a in aj["agencies"]}
    assert len(ids) == len(aj["agencies"]), f"{st}: repeated agency ids"
    tx_path, items_path, totals_path = d / "transactions.csv.gz", d / "line_items.csv.gz", d / "totals.csv"
    purchasing = rules.purchasing

    def payee_parts(raw_name):
        """(payee name as shown, vendor key, text that names the vendor), as Utah's payee_parts with no person check."""
        shown, text = payee_name(raw_name)
        k, kt = norm(shown), norm(text)
        if k in rules.vendor_map:
            return shown, k, text
        if kt in rules.vendor_map:
            return shown, kt, text
        return shown, (kt if text != shown else k), text

    # Pass 1, every line (also those outside the years): payee statistics and the accounts named payees are paid from
    payee_of = {}
    key_spend = collections.defaultdict(float)
    key_names = collections.defaultdict(collections.Counter)
    key_agencies = collections.defaultdict(set)
    account_keys = collections.defaultdict(set)
    raw_total = collections.defaultdict(float)
    raw_lines = collections.Counter()
    out_of_range = collections.Counter()                      # source -> lines outside the state's years
    for r in transactions(tx_path):
        aid = r["agency_id"]
        assert aid in ids, f"{rel(tx_path)}: unknown agency {aid}"
        assert r["source"] in tier, f"{rel(tx_path)}: unknown source {r['source']}"
        amount = float(r["amount"] or 0)
        if int(r["fiscal_year"]) in years:
            raw_total[aid] += amount
            raw_lines[aid] += 1
        else:
            out_of_range[r["source"]] += 1
        parts = payee_of.get(r["payee_name"])
        if parts is None:
            parts = payee_of[r["payee_name"]] = payee_parts(r["payee_name"])
        _, k, text = parts
        key_spend[k] += amount
        key_names[k][text] += abs(amount)
        key_agencies[k].add(aid)
        account_keys[(aid, r["account"])].add(k)

    # Vendors: one per canonical name (slug), shown under the payee's most common name when config names none
    def classify(k):
        if k in rules.vendor_map and "(names withheld)" in rules.vendor_map[k][0]:
            return key_names[k].most_common(1)[0][0].strip(), rules.vendor_map[k][1], "map", True
        if k in rules.vendor_map or not k:
            return classify_key(rules, k, None)
        return classify_key(rules, k, key_names[k].most_common(1)[0][0].strip())

    key_class = {k: classify(k) for k in key_spend}
    vendor_accounts = {ak for ak, ks in account_keys.items() if any(key_class[k][1] != "placeholder" for k in ks)}
    vendors, vendor_index, key_vendor = [], {}, {}
    for k in sorted(key_spend, key=lambda k: (-abs(key_spend[k]), k)):
        name, cat, method, _ = key_class[k]
        vid = slug(name) or "unnamed"
        if vid not in vendor_index:
            vendor_index[vid] = len(vendors)
            vendors.append({"id": vid, "name": name, "category": cat, "method": method, "aliases": []})
        key_vendor[k] = vendor_index[vid]

    aliases, alias_index, payee_info = [], {}, {}

    def payee(raw_name):
        """(vendor index, vendor name, vendor category, payee name index) of a published payee name."""
        if raw_name not in payee_info:
            shown, k, _ = payee_of[raw_name]
            if shown not in alias_index:
                alias_index[shown] = len(aliases)
                aliases.append(shown)
            payee_info[raw_name] = (key_vendor[k], key_class[k][0], key_class[k][1], alias_index[shown])
        return payee_info[raw_name]

    # Pass 2: category of each line; rows, coverage and single payments from the lines in the years; the vendor and
    # category of every tier-2 line for its item line
    rows = collections.defaultdict(float)
    cov = {m: {"purchasing": 0.0, "all": 0.0, "lines": 0} for m in METHODS}
    acct_hits = collections.Counter()
    pay_lines, credits = [], collections.defaultdict(list)
    item_of = {}                                              # (source, source_record_id) -> (vendor, category)
    for r in transactions(tx_path):
        aid, fy, amount = r["agency_id"], int(r["fiscal_year"]), float(r["amount"] or 0)
        vi, vname, vcat, al = payee(r["payee_name"])
        accounts = r["account"]
        cat, method = classify_line(rules, vname, vcat, accounts, r["description"], (aid, accounts) in vendor_accounts,
                                    payee_of[r["payee_name"]][0])
        if tier[r["source"]] == 2:
            key = (r["source"], r["source_record_id"])
            assert key not in item_of, f"{rel(tx_path)}: tier-2 line {key} twice"
            item_of[key] = (vi, cat)
        if fy not in years:
            continue
        acct_hits[rules.account(accounts)[3]] += 1
        rows[(aid, vi, fy, cat_pos[cat], al)] += amount
        c = cov[method]
        c["all"] += amount
        c["lines"] += 1
        if cat in purchasing:
            c["purchasing"] += amount
            if amount >= PAYMENT_MIN:
                pay_lines.append((aid, r["posting_date"], vi, cat_pos[cat], round(amount, 2), r["description"], al, fy))
        if amount <= -PAYMENT_MIN:
            credits[(aid, vi, round(-amount * 100))].append(r["posting_date"])

    # Single payments as Utah's, descriptions as published (owner decision: nothing withheld)
    dropped = cancel_credits(pay_lines, credits)
    descriptions, desc_index = [""], {"": 0}
    payments = []
    for i, (aid, date, vi, ci, amount, desc, al, fy) in enumerate(pay_lines):
        if i in dropped:
            continue
        shown = clean_payee(desc)
        if '""' in shown:
            shown = shown.strip('"').replace('""', '"')
        if shown not in desc_index:
            desc_index[shown] = len(descriptions)
            descriptions.append(shown)
        payments.append([aid, date, vi, ci, amount, desc_index[shown], al, fy])

    # Item lines (tier 2), joined one to one to their transaction line for vendor and category
    items, strings, string_index, item_sources = [], [""], {"": 0}, []

    def si(s):
        s = " ".join((s or "").split())
        if s not in string_index:
            string_index[s] = len(strings)
            strings.append(s)
        return string_index[s]

    if items_path.exists():
        for r in read_table(items_path):
            key = (r["source"], r["source_record_id"])
            assert key in item_of, f"{rel(items_path)}: item line {key} has no tier-2 transaction line"
            vi, cat = item_of.pop(key)
            if r["source"] not in item_sources:
                item_sources.append(r["source"])
            items.append([r["agency_id"], int(r["fiscal_year"]), r["date"], vi, si(r["brand"]), si(r["product_type"]),
                          si(r["description"]), number(r["quantity"]), number(r["unit_price"]), round(float(r["amount"]), 2),
                          cat_pos[cat], item_sources.index(r["source"])])
    assert not item_of, f"{st}: {len(item_of)} tier-2 transaction lines have no item line, e.g. {next(iter(item_of))}"

    rows, payments, vendors, aliases, v_new = finish_vendors(rows, payments, vendors, aliases, categories, neris,
                                                             lambda a: a, {it[3] for it in items})
    for it in items:
        it[3] = v_new[it[3]]

    # Published annual totals (tier 3) in the years: rows, and the agency's annual expenses (size filter)
    totals, budget = [], collections.defaultdict(dict)
    budget_src = collections.defaultdict(set)
    for r in read_table(totals_path) if totals_path.exists() else []:
        assert r["agency_id"] in ids, f"{rel(totals_path)}: unknown agency {r['agency_id']}"
        fy = int(r["fiscal_year"])
        if fy not in years:
            continue
        amount = float(r["amount"])
        totals.append([r["agency_id"], fy, r["category_published"], amount, r["source"]])
        budget[r["agency_id"]][fy] = budget[r["agency_id"]].get(fy, 0.0) + amount
        budget_src[r["agency_id"]].add(r["source"])

    # FEMA firefighter grants (federal.py matched them to agencies)
    grants = []
    for r in read_table(d / "grants.csv"):
        if r["agency_id"] in ids:
            amount = float(r["amount"])
            grants.append({"agency": r["agency_id"], "recipient": r["recipient"], "year": int(r["fiscal_year"]),
                           "program": r["program"], "amount": int(amount) if amount == int(amount) else amount,
                           "award": r["award_number"]})
    grants.sort(key=lambda g: (-g["year"], g["award"]))

    agencies = []
    for a in aj["agencies"]:
        b = budget.get(a["id"], {})
        agencies.append(state_agency(
            a, {str(y): round(b[y]) for y in sorted(b)},
            "totals:" + ";".join(sorted(budget_src[a["id"]])) if b else None, raw_lines[a["id"]]))
    coverage_counts = {str(t): sum(a["coverage"] == t for a in agencies) for t in (1, 2, 3, 4)}
    assert coverage_counts == {str(k): v for k, v in aj["coverage_counts"].items()}, f"{st}: coverage counts differ"

    buy, unclassified, by_method = coverage_numbers(rows, categories, cov)
    registry, grants_raw = latest_state_raw(st, "usfa", "*.csv.gz"), latest_state_raw(st, "openfema", "*.json.gz")
    sources = {}
    for s in src_list:
        tbl = {1: "transactions.csv.gz", 2: "line_items.csv.gz", 3: "totals.csv"}[int(s["tier"])]
        raw_dir = next((p / st.lower() / s["source"] for p in reversed(raw_dirs())
                        if (p / st.lower() / s["source"]).is_dir()), None)
        sources[s["source"]] = {"state": st, "name": s["name"], "tier": int(s["tier"]), "url": s["url"],
                                "years": s["years"], "fiscal_year": s["fiscal_year"], "fetched": s["fetched"],
                                "note": s["note"], "raw": rel(d / tbl), "raw_dir": rel(raw_dir)}
    meta = {
        "name": cfg["name"], "years": cfg["years"], "partial_years": cfg["partial_years"],
        "fetched": max([s["fetched"] for s in src_list] + [p.parent.parent.parent.name for p in (registry, grants_raw) if p]),
        "counts": {"agencies": len(agencies), "vendors": len(vendors), "rows": len(rows), "grants": len(grants),
                   "payments": len(payments), "lines": sum(raw_lines.values()), "items": len(items), "totals": len(totals)},
        "payments_rule": f"Transaction lines of ${PAYMENT_MIN:,} or more in purchasing categories, as published. A line"
                         " is left out when a credit or reversal of the same amount to the same payee cancels it; smaller"
                         " credits are not matched, so the lines can add up to more than the net yearly total.",
        "purchasing_total": round(buy),
        "purchasing_classified_share": round(1 - unclassified / buy, 4) if buy else None,
        "coverage": by_method,
        "coverage_counts": coverage_counts,
        "lines_out_of_range": sum(out_of_range.values()),
        "lines_out_of_range_by_source": dict(sorted(out_of_range.items())),
    }
    report = dict(raw_total=raw_total, raw_lines=raw_lines, acct_hits=acct_hits, buy=buy, unclassified=unclassified,
                  cov=cov, dropped=len(dropped), renamed=0)
    names = {a["id"]: a["name"] for a in agencies}
    return {"state": st, "agencies": agencies, "vendors": vendors, "aliases": aliases, "rows": rows,
            "payments": payments, "descriptions": descriptions, "grants": grants, "totals": totals,
            "items": {"sources": item_sources, "strings": strings, "items": items} if items else None,
            "meta": meta, "sources": sources, "registry_raw": rel(registry), "grants_raw": rel(grants_raw),
            "report": report,
            "worklist": dict(key_spend=key_spend, key_names=key_names, key_agencies=key_agencies, key_class=key_class,
                             names=names, pick=lambda k: len(key_agencies[k]) >= 2 or abs(key_spend[k]) >= 10000)}


def report_state(b):
    R, st, m = b["report"], b["state"], b["meta"]
    buy, unclassified, cov = R["buy"], R["unclassified"], R["cov"]
    print(f"\n{m['name']}: {len(b['agencies'])} agencies (tiers 1/2/3/4: "
          f"{'/'.join(str(m['coverage_counts'][t]) for t in '1234')}), {len(b['vendors'])} vendors"
          f" ({R['renamed']} named as in an earlier state), {len(b['aliases'])} payee names, {len(b['rows'])} rows,"
          f" {len(b['payments'])} payments ({R['dropped']} cancelled by a credit left out), {m['counts']['items']} item"
          f" lines, {len(b['totals'])} totals rows, {len(b['grants'])} grants")
    print(f"Lines: {m['counts']['lines']:,} in FY{m['years'][0]}-FY{m['years'][-1]}; outside: "
          + (", ".join(f"{s} {n:,}" for s, n in m["lines_out_of_range_by_source"].items()) or "none")
          + f". Account rules: {R['acct_hits']['exact']:,} lines exact, {R['acct_hits']['loose']:,} ignoring case")
    if buy:
        print(f"Purchasing ${buy:,.0f}; unclassified ${unclassified:,.0f} ({unclassified / buy:.1%})")
        print(f"{'method':12} {'purchasing $':>16} {'share':>7} {'all lines $':>16} {'lines':>9}")
        for meth in METHODS:
            c = cov[meth]
            print(f"{meth:12} {c['purchasing']:16,.0f} {c['purchasing'] / buy:7.1%} {c['all']:16,.0f} {c['lines']:9,}")
    net = collections.defaultdict(float)
    for r in b["rows"]:
        net[r[0]] += r[4]
    raw_total, raw_lines = R["raw_total"], R["raw_lines"]
    bad = []
    for a in b["agencies"]:
        diff = net.get(a["id"], 0) - raw_total.get(a["id"], 0)
        if abs(diff) >= 0.01 * max(1, raw_lines[a["id"]]):
            bad.append((a, diff))
    with_lines = [a for a in b["agencies"] if raw_lines[a["id"]]]
    print(f"{'agency':58} {'lines':>9} {'raw file $':>17} {'rows $':>17}")
    for a in sorted(with_lines, key=lambda a: (-abs(raw_total[a["id"]]), a["id"]))[:8]:
        print(f"{a['name'][:58]:58} {raw_lines[a['id']]:9,} {raw_total[a['id']]:17,.2f} {net.get(a['id'], 0):17,.2f}")
    for a, diff in bad:
        print(f"  DIFFERS: {a['id']} {a['name']}: rows - raw = {diff:,.2f}")
    print(f"{len(with_lines) - sum(1 for a, _ in bad if raw_lines[a['id']])} of {len(with_lines)} agencies with lines"
          f" match {rel(STATE_DATA / st.lower() / 'transactions.csv.gz')}")
    return len(bad)


# --- All states ---------------------------------------------------------------------------------------------------

def merge_vendor_ids(builds):
    """A vendor id names one vendor in every state: the first state with the id (Utah, then the order of
    config/states.csv) gives its display name, method and NERIS flag; each state keeps its own main category."""
    first = {}
    for b in builds:
        renamed = 0
        for v in b["vendors"]:
            w = first.setdefault(v["id"], v)
            if w is not v and (v["name"], v["method"], v["neris"]) != (w["name"], w["method"], w["neris"]):
                v["name"], v["method"], v["neris"] = w["name"], w["method"], w["neris"]
                renamed += 1
        b["report"]["renamed"] = renamed


def home_tables(builds, categories):
    """The default view (category grouping, no filters, every agency, purchasing categories, the scope's full year
    range) per scope, ALL and each state, with the page's rules (Core.agg): spend, rows and spend per year per
    category; vendors and agencies counted where an agency's net with a vendor (by id) in a year and category is
    positive to the cent; the last such year. Rows are summed in the page's order: states in config/states.csv
    order, each state's rows in file order."""
    purch = [i for i, c in enumerate(categories) if c["purchasing"] == "yes"]
    ok = set(purch)
    out = {}
    for scope in ["ALL"] + [b["state"] for b in builds]:
        bs = builds if scope == "ALL" else [b for b in builds if b["state"] == scope]
        ys = sorted({y for b in bs for y in STATES[b["state"]]["years"]})
        agg = {c: [0.0, 0, collections.defaultdict(float)] for c in purch}
        net = collections.defaultdict(float)                  # (agency, vendor id, year, category) -> net
        tot = [0.0, 0, collections.defaultdict(float)]
        for b in bs:
            vid = [v["id"] for v in b["vendors"]]
            for a, v, y, c, x, _ in b["rows"]:
                if c not in ok or not ys[0] <= y <= ys[-1]:
                    continue
                o = agg[c]
                o[0] += x
                o[1] += 1
                o[2][y] += x
                tot[0] += x
                tot[1] += 1
                tot[2][y] += x
                net[(a, vid[v], y, c)] += x
        ve, ag, last = collections.defaultdict(set), collections.defaultdict(set), {}
        for (a, v, y, c), x in net.items():
            if x > 0.005:
                ve[c].add(v)
                ag[c].add(a)
                last[c] = max(last.get(c, y), y)
        yr = lambda d: {str(y): round(d[y], 2) for y in sorted(d)}  # noqa: E731
        out[scope] = {
            "from": ys[0], "to": ys[-1],
            "cats": [[c, round(agg[c][0], 2), agg[c][1], len(ve[c]), len(ag[c]), last.get(c), yr(agg[c][2])] for c in purch],
            "sum": [round(tot[0], 2), tot[1], len(set().union(*ve.values())), len(set().union(*ag.values())), yr(tot[2])],
        }
    return out


def dumps(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()


def gz_size(body):
    return len(gzip.compress(body, compresslevel=9, mtime=0))


def write_outputs(builds, categories, home):
    """Serialize every file, check the size limits, then write: data/index.json, data/<st>.json,
    data/<st>-payments.json and data/<st>-items.json."""
    built = datetime.date.today().isoformat()
    files = {}                                                # path relative to data/ -> body
    states_meta, sources = {}, {}
    for b in builds:
        st, low = b["state"], b["state"].lower()
        body = dumps({"built": built, "state": st, "vendors": b["vendors"], "aliases": b["aliases"], "rows": b["rows"],
                      "grants": b["grants"], "totals": b["totals"]})
        pbody = dumps({"built": built, "state": st, "payments": b["payments"], "descriptions": b["descriptions"]})
        files[f"{low}.json"], files[f"{low}-payments.json"] = body, pbody
        ibody = None
        if b["items"]:
            ibody = dumps({"built": built, "state": st, **b["items"]})
            files[f"{low}-items.json"] = ibody
        m = b["meta"]
        if st == "UT":
            keep = ["fetched", "transactions_fetched", "raw_path", "transactions_file", "fire_expenses_file",
                    "transparent_utah", "counts", "payments_rule", "purchasing_total", "purchasing_classified_share",
                    "coverage"]
            m = {"name": STATES[st]["name"], "years": m["years"], "partial_years": m["partial_years"],
                 **{k: m[k] for k in keep}, "coverage_counts": {"1": len(b["agencies"]), "2": 0, "3": 0, "4": 0}}
        used = {s for a in b["agencies"] for s in a["sources"]}
        states_meta[st] = {
            **m, "sources": list(b["sources"]) + [s for s in ("usfa", "openfema") if s in used],
            "files": {"rows": f"data/{low}.json", "payments": f"data/{low}-payments.json",
                      "items": f"data/{low}-items.json" if ibody else None},
            "bytes_gz": {"rows": gz_size(body), "payments": gz_size(pbody), "items": gz_size(ibody) if ibody else 0},
            "registry_raw": b["registry_raw"], "grants_raw": b["grants_raw"]}
        sources.update(b["sources"])
    for sid, s in FEDERAL.items():
        raw = {b["state"]: b[{"usfa": "registry_raw", "openfema": "grants_raw"}[sid]] for b in builds} if sid != "neris" \
            else "config/neris_partners.csv"
        sources[sid] = {"state": None, **s, "tier": 4 if sid != "neris" else None, "raw": raw}
    all_years = sorted({y for s in STATES.values() for y in s["years"]})
    meta = {"built": built, "site": "Fire Agency Vendor Finances", "states_order": list(STATES), "years": all_years,
            "partial_years": sorted({y for s in STATES.values() for y in s["partial_years"]}),
            "states": states_meta, "sources": sources}
    index = dumps({"meta": meta, "categories": categories, "agencies": [a for b in builds for a in b["agencies"]],
                   "home": home})
    out = {"index.json": index, **files}
    problems = [f"data/index.json is {gz_size(index):,} bytes gzipped, over {INDEX_MAX_GZ:,}"] if gz_size(index) > INDEX_MAX_GZ else []
    problems += [f"data/{p} is {len(body):,} bytes, over {FILE_MAX:,}" for p, body in out.items() if len(body) > FILE_MAX]
    if problems:
        sys.exit("build failed, nothing written: " + "; ".join(problems))
    DATA.mkdir(exist_ok=True)
    print()
    for p, body in out.items():
        (DATA / p).write_bytes(body)
        print(f"data/{p}: {len(body) / 1e6:.2f} MB ({gz_size(body) / 1e6:.2f} MB gzipped)")


def main(worklist_dir=None):
    categories = read_csv("categories.csv")
    cat_pos = {c["id"]: i for i, c in enumerate(categories)}
    rules = Rules(categories)
    neris = [(r["vendor"], re.compile(r["match"])) for r in read_csv("neris_partners.csv")]
    ut = build_utah(rules, categories, cat_pos, neris)
    report_utah(ut)
    builds = [ut]
    for st in list(STATES)[1:]:
        builds.append(build_state(st, rules, categories, cat_pos, neris))
    merge_vendor_ids(builds)
    bad = sum(report_state(b) for b in builds[1:])
    home = home_tables(builds, categories)
    write_outputs(builds, categories, home)
    if worklist_dir:
        out = pathlib.Path(worklist_dir)
        out.mkdir(parents=True, exist_ok=True)
        for b in builds:
            w = b["worklist"]
            names = w.get("names") or {a["id"]: a["name"] for a in b["agencies"]}
            write_worklist(out / f"worklist_{b['state'].lower()}.csv", w["key_spend"], w["key_names"],
                           w["key_agencies"], w["key_class"], names, w["pick"], w.get("method_of"))
        print(f"Worklists: {out}/worklist_<st>.csv")
    if bad:
        print(f"\n{bad} agencies of other states do not match their transaction lines")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[args.index("--worklist") + 1] if "--worklist" in args else None)
