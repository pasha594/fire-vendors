"""Fold the states' proposed vendor names and categories into the shared config/vendor_map.csv.

    python3 pipeline/sources/merge_vendor_maps.py           # fold proposals in, write the map and the report
    python3 pipeline/sources/merge_vendor_maps.py --check   # only check config/vendor_map.csv; exit 1 on a problem

Python standard library only, deterministic (same inputs, byte-identical outputs).

Inputs
  config/vendor_map.csv                        name_key,vendor,category,confidence (Utah rows hand-reviewed)
  config/states/<st>/vendor_map_additions.csv  a state's proposals: the same columns plus spend and agencies
  config/vendor_name_merges.csv                reviewed name decisions: from_vendor,to_vendor,note
  config/vendor_rules.csv, keyword_rules.csv   the regex rules pipeline/build.py applies after vendor_map
  config/categories.csv                        category ids
Outputs
  config/vendor_map.csv                        merged map, sorted by name_key, same four columns
  docs/multistate/vendor-merge.md              report; the block between the 'manual' markers is kept as written

When no additions file exists, nothing is folded: the map is only checked, and the report's cross-state section
(top vendors by spend over data/data.json and data/states/<st>/transactions.csv.gz) is refreshed.

Rules
  1. Key conflicts. A name_key already in config/vendor_map.csv keeps that row (hand-reviewed for Utah). The only
     state fix taken is a clear one: the row's category is 'unclassified' and a state proposes a real category for
     the same canonical vendor. A name_key proposed by several states gets one row: the proposal whose canonical
     vendor name config/vendor_map.csv (or a vendor rule) already uses, then the higher confidence, then the higher
     spend, then state order OH, CA, ID, TX. Every conflict is listed in the report.
  2. Canonical names. Each proposed name first goes through config/vendor_name_merges.csv (from_vendor ->
     to_vendor; a row with to_vendor equal to from_vendor keeps that name out of the automatic grouping). Names are
     then grouped when they are equal after ignoring case, punctuation, '&' versus 'and', legal suffixes (Inc, LLC,
     Corp, Co, Ltd, LP, N.A., USA ...), a leading 'The', parenthetical notes, common abbreviations (Intl, Dept,
     Svcs, Mfg, Assn, Equip ...) and a trailing branch region ('of Ohio', 'of Central California', 'Ohio'). The
     region is ignored only when the rest is a company name; for names of governments, associations, unions,
     funds and health or dental plans (which are separate bodies per state) only when every name comes from one
     state. A group's canonical name is, in order: a to_vendor of config/vendor_name_merges.csv, the name
     config/vendor_map.csv uses (most rows), a vendor named by a vendor rule, or the proposed form with the most
     spend (forms without a parenthetical note first), cleaned: no legal suffix, no lower-case parenthetical
     note, small words (of, and, the, for, by ...) in lower case. A row of config/vendor_name_merges.csv may also
     name the canonical name itself (to rename it or, with to_vendor equal, to set its category), and a row with an
     empty to_vendor leaves that name's proposals out of the shared map. Different companies that share words are never
     grouped by a rule; pairs that look alike (one name a prefix of the other, equal apart from generic words or
     leading initials, or one or two letters apart) are listed for review unless config/vendor_name_merges.csv
     decides them.
  3. Vendor rules. When a key matches a config/vendor_rules.csv pattern that names a vendor (the first matching
     rule, in pipeline/build.py's order), the row uses that vendor name; a row that would then say exactly what
     the rule says (same vendor and category) is left out because the rule already covers it.
  4. Categories are ids from config/categories.csv. One canonical vendor gets one category: the category
     config/vendor_map.csv gives it (when its rows there agree and are not 'unclassified'), else the category of
     the vendor rule that names it, else the category with the most proposed spend (then higher confidence, then
     id). Every vendor whose proposals disagreed is listed. Utah vendors that config/vendor_map.csv files under
     several categories keep them (a state row takes the matching one, else the most used).
  5. Output sorted by name_key with the columns name_key,vendor,category,confidence (spend and agencies are not
     copied). The row's confidence is the chosen proposal's.
"""
import collections
import csv
import gzip
import io
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config"
REPORT = ROOT / "docs" / "multistate" / "vendor-merge.md"
STATES = ["oh", "ca", "id", "tx"]
JURIS = ["UT"] + [s.upper() for s in STATES]
RANK = {"high": 0, "medium": 1, "low": 2}
FIELDS = ["name_key", "vendor", "category", "confidence"]
MANUAL = ("<!-- manual:start -->", "<!-- manual:end -->")
CROSS = ("<!-- cross-state:start -->", "<!-- cross-state:end -->")


# --- names ------------------------------------------------------------------------------------------------------

def norm(name):
    """pipeline/build.py norm(): the vendor_map key."""
    s = (name or "").upper().replace("&", " AND ")
    s = re.sub(r"['’`]", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\b([A-Z]) (?=[A-Z]\b)", r"\1", s)
    s = re.sub(r"\b(INC|INCORPORATED|LLC|LC|CORP|CORPORATION|CO|COMPANY|LTD|LLP|PC|PLLC|PLC|THE|DBA)\b", " ", s)
    return " ".join(s.split())


def slug(s):
    """pipeline/build.py slug(): the site's vendor id."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


LEGAL = (r"inc|incorporated|llc|lc|corp|corporation|co|company|cos|companies|ltd|limited|llp|lp|lllp|pc|pllc|"
         r"plc|dba|na|usa")
ABBREVIATIONS = [
    (r"\bunited states\b", "us"), (r"\bdept\b", "department"), (r"\bintl\b", "international"),
    (r"\bassn\b|\bassoc\b", "association"), (r"\bmfg\b", "manufacturing"), (r"\bsvcs?\b", "services"),
    (r"\bservice\b", "services"), (r"\bsystem\b", "systems"), (r"\bnatl\b", "national"), (r"\bctr\b", "center"),
    (r"\btechnolog(?:y|ies)\b", "tech"), (r"\bbros\b", "brothers"), (r"\bequip\b", "equipment"),
    (r"\bproduct\b", "products"), (r"\bsupplies\b", "supply"), (r"\bcommunication\b", "communications"),
    (r"\bsolution\b", "solutions"), (r"\bdistributors?\b|\bdistributing\b", "distribution"),
]
US_STATES = ("alabama|alaska|arizona|arkansas|california|calif|colorado|connecticut|delaware|florida|georgia|hawaii|"
             "idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
             "mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|"
             "north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|"
             "south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|"
             "the west|the southwest|the northwest|the rockies|the midwest")
REGION = re.compile(rf"(?: of)?(?: the)?(?: (?:northern|southern|central|north|south|east|west|northeast|"
                    rf"northwest|southeast|southwest|eastern|western|greater))? (?:{US_STATES})$")
# Names of bodies that exist separately in each state: a trailing region is part of their name
SEPARATE_PER_STATE = re.compile(
    r"\b(state|states|county|city|town|township|village|university|college|schools?|district|department|division|"
    r"bureau|office|treasurer|secretary|comptroller|commission|board|council|association|society|federation|"
    r"league|union|chapter|fund|authority|agency|governments?|commonwealth|cross|shield|credit|firefighters|"
    r"chiefs|sheriff|police|court|clerk|auditor|attorney|employees|retirement|pension|public|medicaid|dental|"
    r"vision|health|insurance|pool|plan)\b")
LOCAL = re.compile(r"\b(city|county|town|township|village|borough|parish|fire department|fire dept|fire district|"
                   r"fire protection|volunteer fire|fire rescue|fire and rescue|police|sheriff|schools?|district|"
                   r"marshal)\b")
STATE_WORDS = re.compile(rf"\b(us|federal|national|{US_STATES})\b")
ABBREVIATED = re.compile(r"\b(Intl|Int'l|Svcs?|Dept|Assn|Assoc|Equip|Mfg|Natl|Ctr|Twp|Cty|Cnty|Sys)\b\.?", re.I)
GENERIC = set("services systems group holdings enterprises industries international solutions tech products supply "
              "equipment distribution of and the usa america north american national corporation company".split())
COMMON_NOUNS = set("construction contracting electric electrical communications concrete logging septic plumbing heating "
                   "trucking logistics excavating excavation tire tires automotive parts water rescue safety fire "
                   "consulting management insurance medical dental vision health financial leasing payroll".split())
SMALL = {"of", "and", "the", "for", "by", "at", "in", "on", "to"}


def level_a(name):
    """Grouping key: case, punctuation, '&'/'and', legal suffixes, a leading 'The', parenthetical notes and common
    abbreviations ignored."""
    s = name.lower().replace("&", " and ").replace("+", " and ")
    s = re.sub(r"\([^)]*\)?", " ", s)
    s = re.sub(r"['’`.]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\b([a-z]) (?=[a-z]\b)", r"\1", s)
    for rx, to in ABBREVIATIONS:
        s = re.sub(rx, to, s)
    s = " ".join(s.split())
    for _ in range(3):
        s = re.sub(r"^the ", "", s)
        s = re.sub(rf"( (?:{LEGAL}))+$", "", s).strip()
    return s


def strip_region(key):
    """Level-a key without a trailing branch region ('rush truck centers of ohio' -> 'rush truck centers')."""
    s = REGION.sub("", key).strip()
    s = re.sub(rf"( (?:{LEGAL}))+$", "", s).strip()
    return s if s and len(s.split()) >= 1 and len(s) >= 3 else key


def branch(name):
    """True for a company name with a trailing branch region ('Sysco of Central California')."""
    k = level_a(name)
    return bool(REGION.search(k)) and not SEPARATE_PER_STATE.search(k)


def clean_name(name, category="", drop_note=False):
    """Canonical form of a proposed name: no lower-case parenthetical note (unless the vendor is a placeholder),
    no note at all when another form of the name has none (drop_note), no legal suffix, small words in lower
    case."""
    s = " ".join(name.replace("*", " ").split()).strip(" ,;-")
    if category not in ("placeholder", "individuals"):
        s = re.sub(r"\s*\([a-z][^)]*\)$", "", s).strip(" ,;-")
    if drop_note:
        s = re.sub(r"\s*\([^)]*\)?$", "", s).strip(" ,;-") or s
    for _ in range(2):
        t = re.sub(r"(?<!&)(?:,\s*|\s+)(?:Inc\.?|Incorporated|L\.?L\.?C\.?|Corp\.?|Corporation|Co\.?|Company|"
                   r"Ltd\.?|Limited|L\.P\.|LP|LLP|PLLC|P\.C\.|N\.A\.?|Na)$", "", s, flags=re.I).strip(" ,;-")
        if len(re.sub(r"[^A-Za-z]", "", t)) >= 4:
            s = t
    if not s.isupper():
        words = s.split(" ")
        s = " ".join(w.lower() if i and w.lower() in SMALL and w[:1].isupper() else w for i, w in enumerate(words))
    return s


# --- inputs -----------------------------------------------------------------------------------------------------

def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8")


def load_rules():
    """(category, regex, vendor, note) in pipeline/build.py's order: vendor_rules.csv, then keyword_rules.csv."""
    return [(r["category"], re.compile(r["pattern"]), (r.get("vendor") or "").strip(), r.get("note", ""))
            for r in read_csv(CONFIG / "vendor_rules.csv") + read_csv(CONFIG / "keyword_rules.csv")]


def first_rule(rules, key):
    return next((r for r in rules if r[1].search(key)), None)


def money(x):
    x = float(x)
    return f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}"


def md(s):
    return str(s).replace("|", "\\|")


# --- merge ------------------------------------------------------------------------------------------------------

class Merge:
    def __init__(self):
        self.categories = read_csv(CONFIG / "categories.csv")
        self.cat_ids = {c["id"] for c in self.categories}
        self.purchasing = {c["id"] for c in self.categories if c["purchasing"] == "yes"}
        self.vm = read_csv(CONFIG / "vendor_map.csv")
        self.rules = load_rules()
        self.merges = read_csv(CONFIG / "vendor_name_merges.csv")
        self.proposals = []
        for st in STATES:
            for r in read_csv(CONFIG / "states" / st / "vendor_map_additions.csv"):
                self.proposals.append({"st": st.upper(), "key": r["name_key"], "vendor": r["vendor"].strip(),
                                       "category": r["category"], "confidence": r["confidence"],
                                       "spend": float(r["spend"] or 0), "agencies": int(r["agencies"] or 0)})
        self.log = collections.defaultdict(list)

    # -- checks shared with --check
    def problems(self, rows):
        out = []
        keys = [r["name_key"] for r in rows]
        if keys != sorted(keys):
            out.append("config/vendor_map.csv is not sorted by name_key")
        dupes = sorted(k for k, n in collections.Counter(keys).items() if n > 1)
        out += [f"duplicate name_key {k!r}" for k in dupes]
        out += [f"unknown category {r['category']!r} for {r['name_key']!r}" for r in rows if r["category"] not in self.cat_ids]
        out += [f"unknown confidence {r['confidence']!r} for {r['name_key']!r}" for r in rows if r["confidence"] not in RANK]
        out += [f"empty vendor for {r['name_key']!r}" for r in rows if not r["vendor"].strip()]
        froms = {m["from_vendor"]: m["to_vendor"] for m in self.merges if m["from_vendor"] != m["to_vendor"]}
        out += [f"{r['name_key']!r} uses {r['vendor']!r}, which config/vendor_name_merges.csv renames"
                for r in rows if r["vendor"] in froms]
        return out

    def vendor_rule_names(self):
        names = {}
        for cat, _, vendor, _ in self.rules:
            if vendor and vendor not in names:
                names[vendor] = cat
        return names

    def run(self):
        merges, merge_cat = {}, {}
        for m in self.merges:
            assert m["from_vendor"], f"vendor_name_merges.csv: empty from_vendor in {m}"
            assert m["from_vendor"] not in merges, f"vendor_name_merges.csv: {m['from_vendor']!r} twice"
            merges[m["from_vendor"]] = m["to_vendor"]
            cat = (m.get("category") or "").strip()
            if cat:
                assert cat in self.cat_ids, f"vendor_name_merges.csv: unknown category {cat!r}"
                assert merge_cat.get(m["to_vendor"], cat) == cat, f"vendor_name_merges.csv: two categories for {m['to_vendor']!r}"
                merge_cat[m["to_vendor"]] = cat
        for f, t in merges.items():
            assert t == f or t not in merges or merges[t] == t, f"vendor_name_merges.csv: chain {f!r} -> {t!r}"
        dropped = {f for f, t in merges.items() if not t}       # an empty to_vendor: not added to the shared map
        merges = {f: t for f, t in merges.items() if t}
        pinned = {f for f, t in merges.items() if f == t}
        targets = {t for f, t in merges.items() if f != t}
        vm = [dict(r) for r in self.vm]
        for r in vm:                    # a reviewed rename of a Utah name applies to its rows too
            if merges.get(r["vendor"], r["vendor"]) != r["vendor"]:
                self.log["vm_renamed"].append((r["name_key"], r["vendor"], merges[r["vendor"]]))
                r["vendor"] = merges[r["vendor"]]
        vm_by_key = {r["name_key"]: r for r in vm}
        vm_names = collections.Counter(r["vendor"] for r in vm)
        vm_cats = collections.defaultdict(collections.Counter)
        for r in vm:
            vm_cats[r["vendor"]][r["category"]] += 1
        rule_names = self.vendor_rule_names()
        for p in self.proposals:
            assert p["category"] in self.cat_ids, f"{p['st']}: unknown category {p['category']} for {p['key']}"
            assert p["confidence"] in RANK, f"{p['st']}: unknown confidence {p['confidence']} for {p['key']}"
        self.dropped = [p for p in self.proposals if p["vendor"] in dropped]
        self.proposals = [p for p in self.proposals if p["vendor"] not in dropped]

        # 2. canonical names: one group per company name
        forms = collections.defaultdict(lambda: {"spend": 0.0, "juris": set(), "cats": collections.Counter()})
        for p in self.proposals:
            name = merges.get(p["vendor"], p["vendor"])
            f = forms[name]
            f["spend"] += p["spend"]
            f["juris"].add(p["st"])
            f["cats"][p["category"]] += 1
        anchors = set(vm_names) | set(rule_names) | targets
        for a in anchors:
            forms[a]["juris"].add("UT" if a in vm_names or a in rule_names else "")
        for f in forms.values():
            f["juris"].discard("")
        by_a = collections.defaultdict(list)
        for name in sorted(forms):
            if name in pinned:
                by_a[("pin", name, "")].append(name)
                continue
            ka = level_a(name)
            # a local body's name ('Milford Volunteer Fire Dept', 'Union Township') is not the same body in
            # another state: such names are grouped only with names from the same state(s)
            scope = "+".join(sorted(forms[name]["juris"], key=JURIS.index)) if LOCAL.search(ka) and \
                not STATE_WORDS.search(ka) else ""
            by_a[("a", ka, scope)].append(name)
        scopes = collections.defaultdict(set)
        for ka in by_a:
            scopes[ka[1]].add(ka)
        self.local_kept_apart = [[by_a[ka] for ka in sorted(kas)] for k, kas in sorted(scopes.items()) if len(kas) > 1]
        by_b = collections.defaultdict(list)
        for ka in sorted(by_a):
            by_b[ka if ka[0] == "pin" else ("b", strip_region(ka[1]), ka[2])].append(ka)
        groups = []                     # lists of names
        self.region_kept_apart = []
        for kb in sorted(by_b):
            kas = by_b[kb]
            if len(kas) == 1:
                groups.append(by_a[kas[0]])
                continue
            juris = set().union(*(forms[n]["juris"] for ka in kas for n in by_a[ka]))
            if (SEPARATE_PER_STATE.search(kb[1]) or len(kb[1].split()) == 1) and len(juris) > 1:
                for ka in kas:
                    groups.append(by_a[ka])
                self.region_kept_apart.append([by_a[ka] for ka in kas])
            else:
                groups.append([n for ka in kas for n in by_a[ka]])
        canonical = {}                  # name -> canonical name
        used = {p["vendor"] for p in self.proposals if p["vendor"] in merges} | {k for k in merges if k in vm_names} | \
            {r[1] for r in self.log["vm_renamed"]} | {p["vendor"] for p in self.dropped}
        self.groups = []
        for names in groups:
            names = sorted(set(names))
            explicit = sorted(n for n in names if n in targets or n in pinned)
            in_vm = sorted((n for n in names if n in vm_names), key=lambda n: (-vm_names[n], n))
            in_rules = sorted(n for n in names if n in rule_names)
            if len(explicit) > 1:
                raise SystemExit(f"vendor_name_merges.csv: {explicit} fall into one group; merge them explicitly")
            if explicit and in_vm and explicit[0] not in in_vm:
                raise SystemExit(f"vendor_name_merges.csv: {explicit[0]!r} and config/vendor_map.csv's {in_vm} fall "
                                 f"into one group; rename the Utah name with a row of its own")
            if explicit:
                canon, how = explicit[0], "config/vendor_name_merges.csv"
            elif in_vm:
                canon, how = in_vm[0], "config/vendor_map.csv"
            elif in_rules:
                canon, how = in_rules[0], "config/vendor_rules.csv"
            else:
                best = sorted(names, key=lambda n: (bool(ABBREVIATED.search(n)), branch(n), -forms[n]["spend"], n))[0]
                cat = forms[best]["cats"].most_common(1)[0][0] if forms[best]["cats"] else ""
                canon, how = clean_name(best, cat, any("(" not in n for n in names)), "most spend"
            if not explicit and canon in merges:     # a reviewed decision on the canonical name itself
                used.add(canon)
                canon, how = merges[canon], "config/vendor_name_merges.csv"
            for n in names:
                canonical[n] = canon
            proposed = [n for n in names if forms[n]["cats"]]
            if proposed and (len(names) > 1 or canon != names[0]):
                self.groups.append({"canonical": canon, "how": how, "names": names,
                                    "juris": sorted(set().union(*(forms[n]["juris"] for n in names)),
                                                    key=JURIS.index),
                                    "spend": sum(forms[n]["spend"] for n in names)})
            if len(in_vm) > 1:
                self.log["vm_names_in_one_group"].append(in_vm)
        for p in self.proposals:
            p["canonical"] = canonical[merges.get(p["vendor"], p["vendor"])]
        prop_keys = {level_a(p["vendor"]) for p in self.proposals}
        used |= {f for f in merges if level_a(f) in prop_keys}
        self.unused_merges = sorted((set(merges) | dropped) - used)
        self.canonical = canonical
        self.forms = forms

        # 3. vendor rules: a key a vendor rule names keeps the rule's vendor, unless config/vendor_name_merges.csv
        #    names the vendor (a reviewed name: the rule's pattern catches another company there)
        for p in self.proposals:
            rule = first_rule(self.rules, p["key"])
            p["rule"] = rule
            if rule and rule[2] and p["canonical"] != rule[2]:
                if p["canonical"] in merges or p["canonical"] in targets:
                    self.log["rule_false_hit"].append((p["key"], p["st"], p["canonical"], rule[2]))
                    p["rule"] = None
                    continue
                self.log["renamed_by_rule"].append((p["key"], p["st"], p["canonical"], rule[2]))
                p["canonical"] = rule[2]

        # 4. one category per canonical vendor
        by_vendor = collections.defaultdict(list)
        for p in self.proposals:
            by_vendor[p["canonical"]].append(p)
        self.vendor_category = {}
        self.category_decisions = []
        vm_fix = {}                     # vendor -> category for Utah rows that were 'unclassified'
        for v in sorted(by_vendor):
            ps = by_vendor[v]
            spend = collections.defaultdict(float)
            conf = collections.defaultdict(lambda: 9)
            for p in ps:
                spend[p["category"]] += p["spend"]
                conf[p["category"]] = min(conf[p["category"]], RANK[p["confidence"]])
            by_spend = sorted(spend, key=lambda c: (-spend[c], conf[c], c))[0]
            cats_vm = vm_cats.get(v)
            if v in merge_cat:
                cat, why = merge_cat[v], "config/vendor_name_merges.csv"
            elif cats_vm and set(cats_vm) == {"unclassified"} and any(c != "unclassified" for c in spend):
                real = [c for c in sorted(spend, key=lambda c: (-spend[c], conf[c], c)) if c != "unclassified"]
                cat, why = real[0], "config/vendor_map.csv had it unclassified; proposals by spend"
                vm_fix[v] = cat
            elif cats_vm and len(cats_vm) == 1:
                cat, why = next(iter(cats_vm)), "config/vendor_map.csv"
            elif cats_vm:
                cat, why = None, "config/vendor_map.csv files it under several categories"
            elif v in rule_names:
                cat, why = rule_names[v], "vendor rule"
            else:
                cat, why = by_spend, "most proposed spend"
            self.vendor_category[v] = (cat, cats_vm)
            if len(spend) > 1 or (cat and set(spend) != {cat}):
                self.category_decisions.append({"vendor": v, "proposed": dict(spend), "category": cat or "(per key)",
                                                "why": why, "states": sorted({p["st"] for p in ps}, key=JURIS.index)})

        def category_of(p):
            cat, cats_vm = self.vendor_category[p["canonical"]]
            if cat:
                return cat
            return p["category"] if p["category"] in cats_vm else cats_vm.most_common(1)[0][0]

        # 1. key decisions
        by_key = collections.defaultdict(list)
        for p in self.proposals:
            by_key[p["key"]].append(p)
        known = set(vm_names) | set(rule_names)
        out = {k: dict(r) for k, r in vm_by_key.items()}
        self.key_conflicts, self.multi_state, self.left_out = [], [], []
        for v, cat in sorted(vm_fix.items()):
            for k, r in sorted(out.items()):
                if r["vendor"] == v and r["category"] == "unclassified":
                    self.log["vm_unclassified_filled"].append((k, v, cat))
                    r["category"] = cat
        for key in sorted(by_key):
            ps = sorted(by_key[key], key=lambda p: (p["canonical"] not in known, RANK[p["confidence"]], -p["spend"],
                                                    STATES.index(p["st"].lower())))
            if key in vm_by_key:
                g = vm_by_key[key]
                for p in ps:
                    if (p["canonical"], category_of(p)) != (g["vendor"], g["category"]) or \
                            (p["vendor"], p["category"]) != (g["vendor"], g["category"]):
                        new = out[key]
                        decision = ("kept config/vendor_map.csv row" if (new["vendor"], new["category"]) ==
                                    (g["vendor"], g["category"]) else
                                    f"category filled: {new['category']} (the row was unclassified)")
                        self.key_conflicts.append({"key": key, "vm": (g["vendor"], g["category"]), "st": p["st"],
                                                   "proposed": (p["vendor"], p["category"], p["confidence"],
                                                                p["spend"]), "decision": decision})
                continue
            p = ps[0]
            row = {"name_key": key, "vendor": p["canonical"], "category": category_of(p),
                   "confidence": p["confidence"]}
            if len({(q["vendor"], q["category"]) for q in ps}) > 1:
                self.multi_state.append({"key": key, "proposals": [(q["st"], q["vendor"], q["category"],
                                                                    q["confidence"], q["spend"]) for q in ps],
                                         "row": (row["vendor"], row["category"], p["st"])})
            rule = p["rule"]
            if rule and rule[2] and (row["vendor"], row["category"]) == (rule[2], rule[0]):
                self.left_out.append((key, row["vendor"], row["category"], "/".join(q["st"] for q in ps),
                                      sum(q["spend"] for q in ps)))
                continue
            out[key] = row
        self.rows = [out[k] for k in sorted(out)]
        self.added = len(self.rows) - len(self.vm)
        return self.rows

    # -- pairs that look alike but were not grouped
    def review_pairs(self, rows, spend_of):
        """Pairs of vendor names in the merged map, one of them proposed by a state, that look alike: one name's
        words begin the other's, equal apart from generic words or leading initials, or one letter apart (two in
        long names). Pairs of two government or local-body names are left out unless one letter apart."""
        juris = collections.defaultdict(set)
        for p in self.proposals:
            juris[p["canonical"]].add(p["st"])
        for r in rows:
            juris[r["vendor"]].add("UT") if r["name_key"] in {v["name_key"] for v in self.vm} else None
        names = sorted(juris)
        keys = {c: level_a(c) for c in names}
        toks = {c: keys[c].split() for c in names}
        public = {c for c in names if LOCAL.search(keys[c]) or SEPARATE_PER_STATE.search(keys[c])}

        def core(c):
            t = [w for w in toks[c] if w not in GENERIC]
            while len(t) > 1 and len(t[0]) <= 2:
                t = t[1:]
            return " ".join(t) if len(t) > 1 or (t and len(t[0]) >= 6 and t[0] not in COMMON_NOUNS) else ""

        pairs = set()
        buckets = collections.defaultdict(list)
        for c in names:
            if toks[c]:
                buckets[("first", toks[c][0])].append(c)
                buckets[("core", core(c))].append(c)
                buckets[("pre", keys[c][:4])].append(c)
                buckets[("suf", keys[c][-6:])].append(c)
        for (kind, b), cs in sorted(buckets.items()):
            if len(cs) < 2 or len(cs) > 400 or not b:
                continue
            for i, a in enumerate(cs):
                for c in cs[i + 1:]:
                    if not ((juris[a] - {"UT"}) or (juris[c] - {"UT"})) or keys[a] == keys[c]:
                        continue
                    ka, kc = keys[a], keys[c]
                    typo = len(ka) >= 8 and len(kc) >= 8 and re.sub(r"\d", "", ka) != re.sub(r"\d", "", kc) and \
                        edit_distance(ka, kc, 2) <= (2 if min(len(ka), len(kc)) >= 20 else 1)
                    if a in public and c in public and not typo:
                        continue
                    ta, tc = toks[a], toks[c]
                    short, long_ = (ta, tc) if len(ta) <= len(tc) else (tc, ta)
                    if (kind == "first" and long_[:len(short)] == short and
                        (len(short) >= 2 or (len(short[0]) >= 5 and len(long_) <= 3))) \
                            or (kind == "core" and len(b) >= 4) or (kind in ("pre", "suf") and typo):
                        pairs.add(tuple(sorted((a, c))))
        out = [(a, c, spend_of(a), spend_of(c)) for a, c in pairs]
        out.sort(key=lambda t: (-(abs(t[2]) + abs(t[3])), t[0], t[1]))
        return out


def edit_distance(a, b, cap):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


# --- cross-state view -------------------------------------------------------------------------------------------

def classifier(rows, rules):
    vm = {r["name_key"]: (r["vendor"], r["category"]) for r in rows}
    cache = {}

    def classify(key):
        if key not in cache:
            if key in vm:
                cache[key] = vm[key]
            else:
                rule = first_rule(rules, key)
                cache[key] = (rule[2] or None, rule[0]) if rule else (None, None)
        return cache[key]
    return classify


BRANDS = [("Zoll", r"\bzoll\b"), ("Stryker / Physio-Control", r"\bstryker\b|\bphysio ?control\b"),
          ("L.N. Curtis", r"\bln curtis\b"), ("MSA", r"^msa\b|mine safety"), ("Pierce", r"^pierce manufacturing"),
          ("E-ONE", r"^e ?one\b"), ("Motorola", r"\bmotorola\b"), ("Verizon", r"\bverizon\b"), ("AT&T", r"^at ?and ?t\b"),
          ("Municipal Emergency Services", r"^municipal emergency serv"), ("Bound Tree", r"^bound ?tree"),
          ("Henry Schein", r"^henry schein"), ("Life-Assist", r"^life assist"), ("Globe", r"^globe manufacturing"),
          ("Fire-Dex", r"^fire ?dex"), ("LION", r"^lion\b"), ("Scott Safety", r"^scott (safety|health)"),
          ("Rosenbauer", r"^rosenbauer"), ("Ferrara", r"^ferrara"), ("Sutphen", r"^sutphen"), ("KME", r"^kme\b"),
          ("Spartan", r"^spartan (motors|fire|emergency)"), ("Grainger", r"\bgrainger\b"), ("Galls", r"^galls\b"),
          ("Teleflex", r"^teleflex"), ("Ferno", r"^ferno\b"), ("ImageTrend", r"^image ?trend"),
          ("ESO", r"^eso\b"), ("Lexipol", r"^lexipol"), ("Vector Solutions", r"^vector solutions|^target ?solutions")]


def cross_state(rows, rules, categories):
    """Spend and agencies per canonical vendor in Utah (data/data.json) and each state's transactions."""
    purchasing = {c["id"] for c in categories if c["purchasing"] == "yes"}
    classify = classifier(rows, rules)
    vcat = {}
    for r in rows:
        vcat.setdefault(r["vendor"], collections.Counter())[r["category"]] += 1
    spend = collections.defaultdict(lambda: collections.defaultdict(float))
    agencies = collections.defaultdict(lambda: collections.defaultdict(set))
    data = ROOT / "data" / "data.json"
    if data.exists():
        d = json.loads(data.read_text(encoding="utf-8"))
        by_slug = {}
        for r in rows:
            by_slug.setdefault(slug(r["vendor"]), r["vendor"])
        for a, v, y, c, x, al in d["rows"]:
            vend = d["vendors"][v]
            name = by_slug.get(vend["id"], vend["name"])
            if d["categories"][c]["id"] in purchasing:
                spend[name]["UT"] += x
                agencies[name]["UT"].add(a)
            vcat.setdefault(name, collections.Counter({vend["category"]: 1}))
    for st in STATES:
        path = ROOT / "data" / "states" / st / "transactions.csv.gz"
        if not path.exists():
            continue
        with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
            rd = csv.reader(f)
            head = next(rd)
            ia, ip, ix = head.index("agency_id"), head.index("payee_name"), head.index("amount")
            keys = {}
            for line in rd:
                payee = line[ip]
                k = keys.get(payee)
                if k is None:
                    k = keys[payee] = norm(payee)
                vendor, cat = classify(k)
                if vendor is None or cat not in purchasing:
                    continue
                spend[vendor][st.upper()] += float(line[ix])
                agencies[vendor][st.upper()].add(line[ia])
    table = []
    for v, by in spend.items():
        cat = vcat.get(v, collections.Counter()).most_common(1)[0][0] if vcat.get(v) else ""
        if cat not in purchasing or cat == "unclassified":
            continue
        table.append((v, cat, sum(by.values()), {j: (by[j], len(agencies[v][j])) for j in by}))
    table.sort(key=lambda t: (-t[2], t[0]))
    return table


def cross_state_md(rows, rules, categories, n=50):
    table = cross_state(rows, rules, categories)
    out = [CROSS[0], "",
           f"Top {n} canonical vendors by purchasing spend over the five states: Utah from `data/data.json` (rows in",
           "purchasing categories), the states from `data/states/<st>/transactions.csv.gz` (payee key through",
           "config/vendor_map.csv, then the vendor rules; payees in a purchasing category). Each cell: net dollars",
           "(agencies). Recomputed by every run of the script.", "",
           "| # | Vendor | Category | Total | " + " | ".join(JURIS) + " | States |",
           "| --- | --- | --- | --- | " + " | ".join("---" for _ in JURIS) + " | --- |"]
    for i, (v, cat, total, by) in enumerate(table[:n], 1):
        cells = [f"{money(by[j][0])} ({by[j][1]})" if j in by and round(by[j][0]) else "" for j in JURIS]
        out.append(f"| {i} | {md(v)} | {cat} | {money(total)} | " + " | ".join(cells) + f" | {sum(1 for c in cells if c)} |")
    multi = [t for t in table if sum(1 for j in t[3] if round(t[3][j][0])) >= 3]
    out += ["", f"Vendors with purchasing spend in at least three of the five states: {len(multi)}. The {min(n, len(multi))}",
            "with the most spend (the national vendors, each under one name):", "",
            "| # | Vendor | Category | Total | " + " | ".join(JURIS) + " | States |",
            "| --- | --- | --- | --- | " + " | ".join("---" for _ in JURIS) + " | --- |"]
    for i, (v, cat, total, by) in enumerate(multi[:n], 1):
        cells = [f"{money(by[j][0])} ({by[j][1]})" if j in by and round(by[j][0]) else "" for j in JURIS]
        out.append(f"| {i} | {md(v)} | {cat} | {money(total)} | " + " | ".join(cells) + f" | {sum(1 for c in cells if c)} |")
    out += ["", "Large fire and EMS vendors: every vendor name with purchasing spend whose name matches the brand, so a",
            "second spelling would show here (Zoll Data Systems is Zoll's ePCR software company, kept apart as in",
            "config/vendor_rules.csv).", "",
            "| Brand | Vendor names (states) | Total |", "| --- | --- | --- |"]
    for label, rx in BRANDS:
        hits = [t for t in table if re.search(rx, level_a(t[0]))]
        if hits:
            names = "; ".join(f"{md(v)} ({', '.join(j for j in JURIS if j in by and round(by[j][0]))})"
                              for v, cat, total, by in hits)
            out.append(f"| {label} | {names} | {money(sum(t[2] for t in hits))} |")
    out += ["", CROSS[1]]
    return "\n".join(out)


# --- report -----------------------------------------------------------------------------------------------------

def report(m, rows, review):
    old = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    manual = old.split(MANUAL[0], 1)[1].split(MANUAL[1], 1)[0] if MANUAL[0] in old else "\n(none yet)\n"
    by_st = collections.Counter(p["st"] for p in m.proposals)
    keys = {p["key"] for p in m.proposals}
    L = ["# Vendor name merge", "",
         "Written by `pipeline/sources/merge_vendor_maps.py` (rules in its docstring), except the block between the",
         "`manual` markers. The states' proposed vendor names and categories",
         "(`config/states/<st>/vendor_map_additions.csv`) were folded into the shared `config/vendor_map.csv`, so one",
         "company has one canonical vendor name across Utah, Ohio, California, Idaho and Texas. The site's vendor id",
         "is a slug of the canonical name, so the names decide which payees add up to one vendor.", "",
         "## Result", "",
         "| | Rows |", "| --- | --- |",
         f"| config/vendor_map.csv before | {len(m.vm):,} |"]
    for st in JURIS[1:]:
        L.append(f"| Proposed by {st} | {by_st[st]:,} |")
    L += [f"| Distinct proposed keys | {len(keys):,} |",
          f"| Keys already in config/vendor_map.csv | {sum(k in {r['name_key'] for r in m.vm} for k in keys):,} |",
          f"| Left out because a vendor rule already says the same | {len(m.left_out):,} |",
          f"| Rows added | {m.added:,} |",
          f"| config/vendor_map.csv after | {len(rows):,} |",
          f"| Canonical names covering more than one proposed form, or renamed | {len(m.groups):,} |", ""]

    L += ["## Rules", "",
          "1. **Key conflicts.** A key already in `config/vendor_map.csv` keeps that row (hand-reviewed for Utah); the",
          "   only state fix taken is a category for a row that was `unclassified`, for the same company. A key",
          "   proposed by several states gets one row: the proposal that uses a name `config/vendor_map.csv` or a",
          "   vendor rule already uses, then higher confidence, then higher spend.",
          "2. **Canonical names.** Names are grouped when equal apart from case, punctuation, '&'/'and', legal",
          "   suffixes, a leading 'The', parenthetical notes, common abbreviations and a trailing branch region",
          "   ('of Ohio'); for governments, associations, unions, funds and health plans the region counts unless",
          "   every name comes from one state. Canonical name: a `to_vendor` of `config/vendor_name_merges.csv`, else",
          "   the name `config/vendor_map.csv` uses, else a vendor rule's name, else the proposed form with the most",
          "   spend, cleaned (no legal suffix or lower-case note, small words in lower case). Judgment calls are rows",
          "   of `config/vendor_name_merges.csv`; pairs that only look alike stay apart and are listed below.",
          "3. **Vendor rules.** A key that a `config/vendor_rules.csv` pattern names keeps the rule's vendor; a row",
          "   that would say exactly what the rule says is left out.",
          "4. **Categories.** One canonical vendor, one category: `config/vendor_map.csv`'s (unless `unclassified`),",
          "   else the vendor rule's, else the category with the most proposed spend.",
          "5. **Output** sorted by `name_key`, columns `name_key,vendor,category,confidence`.", ""]

    L += ["## Key conflicts with config/vendor_map.csv", ""]
    if m.key_conflicts:
        L += ["| Key | config/vendor_map.csv | State | Proposed (confidence, spend) | Decision |", "| --- | --- | --- | --- | --- |"]
        for c in m.key_conflicts:
            v, cat, conf, sp = c["proposed"]
            L.append(f"| {md(c['key'])} | {md(c['vm'][0])} / {c['vm'][1]} | {c['st']} | {md(v)} / {cat} ({conf}, "
                     f"{money(sp)}) | {c['decision']} |")
    else:
        L.append("None.")
    if m.log["vm_unclassified_filled"]:
        L += ["", "Rows of config/vendor_map.csv whose `unclassified` category was filled from the proposals:", ""]
        L += [f"- {md(k)}: {md(v)} -> {cat}" for k, v, cat in m.log["vm_unclassified_filled"]]
    if m.dropped:
        L += ["", "Proposals left out of the shared map by an empty `to_vendor` in `config/vendor_name_merges.csv`:", ""]
        L += [f"- {md(p['key'])} ({p['st']}): {md(p['vendor'])} / {p['category']}, {money(p['spend'])}"
              for p in sorted(m.dropped, key=lambda p: (p["key"], p["st"]))]
    L += ["", "## Keys proposed by several states", ""]
    if m.multi_state:
        L += ["| Key | Proposals (state: vendor / category, confidence, spend) | Row written |", "| --- | --- | --- |"]
        for c in m.multi_state:
            props = "; ".join(f"{st}: {md(v)} / {cat}, {conf}, {money(sp)}" for st, v, cat, conf, sp in c["proposals"])
            L.append(f"| {md(c['key'])} | {props} | {md(c['row'][0])} / {c['row'][1]} (from {c['row'][2]}) |")
    else:
        L.append("None with different proposals.")
    multi = [g for g in m.groups if len(g["names"]) > 1]
    single = [g for g in m.groups if len(g["names"]) == 1]
    L += ["", "## Canonical names", "",
          f"{len(multi)} canonical names cover more than one proposed form (or a proposed form and a Utah name).",
          "`How`: where the canonical name came from.", "",
          "| Canonical name | Other forms folded in | States | How | Proposed spend |", "| --- | --- | --- | --- | --- |"]
    for g in sorted(multi, key=lambda g: (-abs(g["spend"]), g["canonical"])):
        others = [n for n in g["names"] if n != g["canonical"]]
        L.append(f"| {md(g['canonical'])} | {md('; '.join(others))} | {', '.join(g['juris'])} | {g['how']} | "
                 f"{money(g['spend'])} |")
    L += ["", f"{len(single)} proposed names were only cleaned (legal suffix or lower-case note dropped, small words in",
          "lower case), or renamed by `config/vendor_name_merges.csv`:", "", "<details><summary>List</summary>", ""]
    L += [f"- {md(g['names'][0])} -> {md(g['canonical'])} ({', '.join(g['juris'])})"
          for g in sorted(single, key=lambda g: (g["names"][0], g["canonical"]))]
    L += ["", "</details>"]
    if m.region_kept_apart:
        L += ["", "Names equal apart from a region that were kept apart (bodies that exist separately per state):", ""]
        for gs in m.region_kept_apart:
            L.append("- " + " / ".join(md("; ".join(g)) for g in gs))
    if m.local_kept_apart:
        L += ["", "Names of local bodies (cities, counties, townships, fire departments, districts) that are equal in",
              "several states were not grouped across states; equal names still share a vendor id:", ""]
        for gs in m.local_kept_apart:
            L.append("- " + " / ".join(md("; ".join(g)) for g in gs))
    if m.log["vm_renamed"]:
        L += ["", "Utah rows renamed by `config/vendor_name_merges.csv`:", ""]
        L += [f"- {md(k)}: {md(a)} -> {md(b)}" for k, a, b in m.log["vm_renamed"]]
    if m.log["vm_names_in_one_group"]:
        L += ["", "Utah names in config/vendor_map.csv that fall into one group (left as they are):", ""]
        L += ["- " + " / ".join(md(n) for n in g) for g in m.log["vm_names_in_one_group"]]
    L += ["", "## Names set by a vendor rule", "",
          "Keys a `config/vendor_rules.csv` pattern names: the row uses the rule's vendor.", ""]
    if m.log["renamed_by_rule"]:
        L += ["| Key | State | Proposed canonical name | Rule's vendor |", "| --- | --- | --- | --- |"]
        L += [f"| {md(k)} | {st} | {md(a)} | {md(b)} |" for k, st, a, b in sorted(m.log["renamed_by_rule"])]
    else:
        L.append("None.")
    if m.log["rule_false_hit"]:
        L += ["", "Keys where a rule's pattern catches another company; the reviewed name in",
              "`config/vendor_name_merges.csv` is kept (the config/vendor_map.csv row decides before the rule):", ""]
        L += [f"- {md(k)} ({st}): {md(a)}, not {md(b)}" for k, st, a, b in sorted(m.log["rule_false_hit"])]
    L += ["", f"Left out because the vendor rule already gives the same vendor and category ({len(m.left_out)}):", ""]
    L += [f"- {md(k)} -> {md(v)} / {cat} ({st}, {money(sp)})" for k, v, cat, st, sp in m.left_out] or ["None."]
    L += ["", "## Category decisions", "",
          "Canonical vendors whose proposals named different categories, or whose category came from",
          "config/vendor_map.csv or a vendor rule instead of the proposal.", "",
          "| Vendor | States | Proposed (category: spend) | Category | Why |", "| --- | --- | --- | --- | --- |"]
    for c in sorted(m.category_decisions, key=lambda c: (-sum(abs(x) for x in c["proposed"].values()), c["vendor"])):
        props = "; ".join(f"{k}: {money(x)}" for k, x in sorted(c["proposed"].items(), key=lambda t: (-t[1], t[0])))
        L.append(f"| {md(c['vendor'])} | {', '.join(c['states'])} | {props} | {c['category']} | {c['why']} |")
    L += ["", "## Judgment calls", "",
          "Merged or kept apart by `config/vendor_name_merges.csv` (a row whose `to_vendor` equals its `from_vendor`",
          "keeps that name out of the automatic grouping):", "",
          "| From | To | Note |", "| --- | --- | --- |"]
    L += [f"| {md(r['from_vendor'])} | {md(r['to_vendor'])} | {md(r['note'])} |" for r in m.merges] or ["| - | - | - |"]
    shown = [p for p in review if abs(p[2]) + abs(p[3]) >= 25000]
    L += ["", f"Pairs that look alike but stay apart, for review ({len(review)} found; the {len(shown)} with $25,000",
          "or more of proposed and Utah spend together are listed). Merge one by adding a row to",
          "`config/vendor_name_merges.csv` and running the script again.", "",
          "| Name | Name | Spend | Spend |", "| --- | --- | --- | --- |"]
    L += [f"| {md(a)} | {md(c)} | {money(sa)} | {money(sc)} |" for a, c, sa, sc in shown]
    L += ["", "## Cross-state vendors", "", cross_state_md(rows, m.rules, m.categories), "",
          "## Review notes and Utah impact", "", MANUAL[0] + manual + MANUAL[1], ""]
    return "\n".join(L)


def refresh_cross_state(rows, rules, categories):
    if not REPORT.exists():
        return
    old = REPORT.read_text(encoding="utf-8")
    if CROSS[0] not in old:
        return
    head, rest = old.split(CROSS[0], 1)
    tail = rest.split(CROSS[1], 1)[1]
    REPORT.write_text(head + cross_state_md(rows, rules, categories) + tail, encoding="utf-8")


def main(argv):
    m = Merge()
    if "--check" in argv or not m.proposals:
        problems = m.problems(m.vm)
        for p in problems[:20]:
            print("problem:", p)
        if "--check" in argv:
            print(f"config/vendor_map.csv: {len(m.vm):,} rows, {len(problems)} problems")
            return 1 if problems else 0
        if problems:
            return 1
        refresh_cross_state(m.vm, m.rules, m.categories)
        print(f"no config/states/<st>/vendor_map_additions.csv: nothing to fold; config/vendor_map.csv "
              f"{len(m.vm):,} rows checked; cross-state section of {REPORT.relative_to(ROOT)} refreshed")
        return 0
    rows = m.run()
    problems = m.problems(rows)
    assert not problems, problems[:10]
    write_csv(CONFIG / "vendor_map.csv", FIELDS, rows)
    spend_ut = collections.Counter()
    data = ROOT / "data" / "data.json"
    if data.exists():
        d = json.loads(data.read_text(encoding="utf-8"))
        for a, v, y, c, x, al in d["rows"]:
            spend_ut[d["vendors"][v]["id"]] += x
    prop_spend = collections.Counter()
    for p in m.proposals:
        prop_spend[p["canonical"]] += p["spend"]
    review = m.review_pairs(rows, lambda c: prop_spend[c] + spend_ut[slug(c)])
    merged = {(r["from_vendor"], r["to_vendor"]) for r in m.merges}
    review = [p for p in review if (p[0], p[1]) not in merged and (p[1], p[0]) not in merged]
    REPORT.write_text(report(m, rows, review), encoding="utf-8")
    for f in m.unused_merges:
        print(f"  config/vendor_name_merges.csv: {f!r} matches no proposed or canonical name")
    print(f"config/vendor_map.csv: {len(m.vm):,} -> {len(rows):,} rows ({m.added:,} added from "
          f"{len(m.proposals):,} proposals); {len(m.key_conflicts)} key conflicts, {len(m.multi_state)} keys "
          f"proposed differently by several states, {len(m.groups)} canonical names, "
          f"{len(m.category_decisions)} category decisions, {len(review)} pairs for review")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
