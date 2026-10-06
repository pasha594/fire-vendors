"""Helpers shared by the California adapters (pipeline/sources/ca_*.py). Not an adapter itself.

Kept here, not in common.py, because the multi-state run lets each state edit only its own files:
  soql_all         page through a Socrata SODA query (common.get, so the 1-second throttle applies)
  Payees           common.withhold_person plus the extra person-name shapes California payee lists show
  links            the hand-reviewed rows of config/states/ca/agency_sources.csv for one source
  register_source  this source's row in config/states/ca/sources.csv
  money            dollars as a two-decimal string
"""
import collections
import csv
import decimal
import json
import re

import common

ST = "CA"
SOURCE_COLUMNS = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]
CENTS = decimal.Decimal("0.01")


def soql_all(domain, dataset, select, where, order=":id", page=50000):
    """Every row of a SODA query, paged by $limit/$offset in a stable $order."""
    rows, offset = [], 0
    while True:
        params = {"$select": select, "$order": order, "$limit": page, "$offset": offset}
        if where:
            params["$where"] = where
        part = json.loads(common.get(f"{domain}/resource/{dataset}.json", params))
        rows += part
        print(f"  {dataset}: {len(rows)} rows", flush=True)
        if len(part) < page:
            return rows
        offset += page


def soql(domain, dataset, **params):
    return json.loads(common.get(f"{domain}/resource/{dataset}.json", {f"${k}": v for k, v in params.items()}))


def columns(meta):
    """Field names of a Socrata view's metadata (api/views/<id>.json), without the hidden ':' fields."""
    return [c["fieldName"] for c in json.loads(meta)["columns"] if not c["fieldName"].startswith(":")]


def collapse_reloads(lines, document):
    """Duplicate handling for sources without a line number (Riverside County, Corona, SCPRS).

    lines: hashable line tuples (every published column but the portal's row id), duplicates included;
    document: line -> its invoice or purchase order. A document whose every distinct line occurs the same
    number of times k > 1 looks loaded k times and is kept once; identical lines confined to part of a
    document (one line per phone on a wireless bill, two rooms at one rate) are separate charges and are kept.
    Returns (lines to keep, sorted; lines dropped as reloads; identical lines kept)."""
    counts = collections.Counter(lines)
    docs = collections.defaultdict(dict)
    for line, n in counts.items():
        docs[document(line)][line] = n
    keep, dropped, kept_repeats = [], 0, 0
    for doc_lines in docs.values():
        ns = set(doc_lines.values())
        reloaded = len(ns) == 1 and min(ns) > 1
        for line, n in doc_lines.items():
            if reloaded:
                keep.append(line)
                dropped += n - 1
            else:
                keep += [line] * n
                kept_repeats += n - 1
    return sorted(keep), dropped, kept_repeats


def money(x):
    return str(decimal.Decimal(str(x or "0")).quantize(CENTS))


def links(source):
    rows = [r for r in common.read_config(ST, "agency_sources.csv") if r["source"] == source]
    assert rows, f"no {source} rows in config/states/ca/agency_sources.csv"
    return rows


def register_source(row):
    path = common.config_dir(ST) / "sources.csv"
    rows = [r for r in common.read_config(ST, "sources.csv") if r["source"] != row["source"]] + [row]
    common.write_csv(path, SOURCE_COLUMNS, sorted(rows, key=lambda r: r["source"]))


# --- Payee names ------------------------------------------------------------------------------------------

SUFFIX = re.compile(r",? (JR|SR|II|III|IV|MD|DDS|PHD|ESQ)\.?$", re.I)
LAST_FIRST_INITIAL = re.compile(r"^[A-Za-z'\-]{2,}, ?[A-Za-z]\.?$")                           # "SMITH, J"
FIRST_INITIAL_LAST = re.compile(r"^[A-Za-z]\.? [A-Za-z'\-]{2,}$")                             # "J SMITH"
HONORIFIC = re.compile(r"^(MR|MRS|MS|DR)\.? [A-Za-z'\-]{2,}( [A-Za-z'\-]{2,})?$", re.I)
PRIVACY = re.compile(r"^PRIVACY\b|\bCONFIDENTIAL\b|^REDACTED\b|^NAME WITHHELD", re.I)
# Company words common.BUSINESS_WORDS lacks (it has CORP but not CORPORATION, for example). Words that are
# also common surnames (FORD, STEEL, GLASS, STONE, WOOD, KING, PRICE) are deliberately left out.
CA_BUSINESS = re.compile(
    r"\b(CORPORATION|INDUSTRIES|INDUSTRIAL|ENTERPRISES?|CONTRACTING|CONTRACTORS?|CONSTRUCTION|ENGINEERING|EQUIPMENT|"
    r"INSTITUTE|COLLECTIVE|INTERNATIONAL|SOLUTIONS|COMPRESSORS|ELECTRIC|STAFFING|CANOPIES|WORKWEAR|METALS|PAINTING|"
    r"TOWING|PRINTING|FURNITURE|ENERGY|COMMUNICATIONS|TECHNOLOGY|TECHNOLOGIES|PRODUCTS|HEALTHCARE|WIRELESS|"
    r"CONSULTING|ASSOCIATES|STRUCTURES|SHOWROOM|CONCEPTS|LIGHTING|MANUFACTURING|LOCKERS|FITNESS|TRAILERS?|HOTELS?|"
    r"INNS?|MOTEL|LP|LLLP|USA|CATERING|PAVING|COMPONENTS|RESTAURANT|FOUNDATION|SPECIALTIES|NETWORKS?|LIMITED|"
    r"WAREHOUSE|ERGONOMICS|HARDWARE|LOCKSMITH|FLOWERS|SUPPLIERS|SUPPLIES|LABORATORIES|PHARMACY|PROPANE|PETROLEUM|"
    r"RENTALS?|LEASING|MARKETING|SOFTWARE|TELECOM|GRAPHICS|SECURITY|SAFETY|ACADEMY|PARTNERS|HOLDINGS|PROPERTIES|"
    r"REALTY|ARCHITECTS|BUILDERS|JANITORIAL|MAINTENANCE|MECHANICAL|HYDRAULICS|AVIATION|HELICOPTERS?|FLYING|"
    r"COUNCIL|SOCIETY|ALLIANCE|COALITION|UNIVERISTY|AUTOMOTIVE|TIRES?|PLUMBING|ROOFING|LANDSCAPING|NURSERY|PEST|"
    r"WELDING|DOORS?|EXPENDABLES|DECON|DIVING|CHEVROLET|TOYOTA|DODGE|HONDA|NISSAN|STORES|MART|MARKETPLACE|DEPOT|"
    r"FD|FPD|PUD|RCD|TRUCKING|EXCAVATING|EXCAVATION|FARMS|RANCH|TRIBE|AEROSPACE|AIRCRAFT|INCORPORATED|OIL|TREASURY|"
    r"FORESTRY|RESOURCES?|PORTABLES|CONTAINERS|MOTORSPORTS|GRADING|DOZER|AFFILIATES|GEOGRAPHICS|COMPANIES|"
    r"DIVERSIFIED|AMBULANCE|TRACTOR|FUELS|BROTHERS|STRIPING|PPE|GEAR|COMPUTER|WATER|UC|CSU|CONSERVATION|KLEEN|"
    r"TREES|FREIGHT|TRANSPORT|TRANSPORTATION|LIVESTOCK|MASONRY|FENCE|CARPET|FABRICATION|MACHINE|EQUIP|KENWORTH|"
    r"FREIGHTLINER|FEES|LODGE|PERFORMANCE|REPAIR|CUSTOMS|ARMOR|ADVANTAGE|WORKS|MIDWEST|BUILT|SALES|PAINT|MASTERS|"
    r"WORKPLACE|DECAL|TRAVEL|PAPER|BIKES|ANALYTICS|WILDERNESS|SURFACES|STEEMER|LAPTOPS|MARITIME|WIREWORKS|"
    r"REFRIGERATION|EXPRESS|SPICERS|NEXIS|REUTERS)\b"
    r"|\bN\.?A\.?$", re.I)


def _rows(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Payees:
    """Payee names as they may be published.

    publish(name, person_flag) is common.withhold_person with three additions:
      - a source's own privacy placeholder ("PRIVACY-FIRE" in Checkbook L.A.) is shown as withheld;
      - a name the person tests flag is kept when a hand-reviewed row of config/states/ca/vendor_map_additions.csv
        (or config/vendor_map.csv) names it as a business, or when it carries a company word of CA_BUSINESS:
        looks_like_person over-matches two-word company names ("UNION DOOR", "KLASSEN CORPORATION") and
        is_person matches "CITIBANK, N.A." (BANK is not a separate word there);
      - person shapes withhold_person misses ("SMITH, J", "J SMITH", "SMITH JR", "MR SMITH") are withheld
        unless a reviewed row claims the name.
    """

    def __init__(self):
        self.claimed = {r["name_key"] for r in _rows(common.config_dir(ST) / "vendor_map_additions.csv")
                        if r["category"] != "individuals"}
        self.claimed |= {r["name_key"] for r in _rows(common.ROOT / "config" / "vendor_map.csv")
                         if r["category"] != "individuals"}
        self.redact = [re.compile(r["pattern"], re.I) for r in _rows(common.ROOT / "config" / "payee_name_redactions.csv")]
        self.seen = collections.Counter()

    def missed_person(self, name):
        if common.BUSINESS_WORDS.search(name):
            return False
        base = SUFFIX.sub("", name).strip()
        if base != name and (common.is_person(base) or common.looks_like_person(base)):
            return True
        return bool(LAST_FIRST_INITIAL.match(name) or FIRST_INITIAL_LAST.match(name) or HONORIFIC.match(name))

    def publish(self, raw, person_flag=False):
        name = " ".join((raw or "").split())
        if person_flag or PRIVACY.search(name):
            out = common.WITHHELD
        else:
            out = common.withhold_person(name)
            claimed = common.norm(name) in self.claimed or bool(CA_BUSINESS.search(name))
            if claimed and out == common.WITHHELD:
                out = "Payee name withheld" if any(rx.search(name) for rx in self.redact) else name
            if out == name and not claimed and self.missed_person(name):
                out = common.WITHHELD
        self.seen[out == common.WITHHELD] += 1
        return out
