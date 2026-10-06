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
DBA = re.compile(r"^(.*?)[\s,/]+D/?B/?A:?\s+(\S.*)$", re.I)
# Full names the common tests miss ("RONALD ALAN BISHOP", "THOMAS J FERGUSON MD PHD", "JILL GUSTAFSON LCSW"): 3 to 5
# words, the first a common first name, and no word that marks a business. Hand-curated list of first names.
FIRST_NAMES = set("""
AARON ABE ADAM ALAN ALBERT ALEX ALEXANDER ALICIA ALLEN AMANDA AMIR AMY ANA ANDREA ANDREW ANGELA ANGELICA ANN ANNA ANNE
ANTHONY ANTONIO APRIL ARTHUR AUSTIN BARBARA BARRY BENJAMIN BETH BETTY BEVERLY BILL BILLY BOB BOBBY BOBI BONNIE BRANDON
BRENDA BRETT BRIAN BRITTANY BRUCE BRYAN CANDACE CARL CARLOS CAROL CAROLE CAROLYN CAROLYNN CATHERINE CHAD CHARLES CHELSEA
CHERYL CHRIS CHRISTINA CHRISTINE CHRISTOPHER CINDY CLAUDIA CLIFFORD CODY CONNIE COREY COURTNEY CRAIG CRYSTAL CURTIS
CYNTHIA DALE DAN DANIEL DANNY DARREN DARRIN DARRELL DARRYL DAVID DAWN DEAN DEBBIE DEBORAH DEBRA DENISE DENNIS DEREK
DIANA DIANE DON DONALD DONNA DORIAN DOROTHY DOUG DOUGLAS DUANE DUSTIN DYLAN ED EDWARD EILEEN ELAINE ELIZABETH EMILY EMMA
ERIC ERICA ERICK ERIN EVAN EVELYN FERNANDO FRANCES FRANCISCO FRANK FRED FREDERICK FREDRICK GABRIEL GAIL GARY GEORGE
GERALD GINA GLENN GLORIA GORDON GREG GREGORY GUY HANNAH HAROLD HARRISON HEATHER HELEN HENRY HOLLY HOWARD HUGH IAN IRIS
JACK JACQUELINE JAI JAKE JAMES JANE JANELLE JANET JANICE JARED JASON JAY JEAN JEFF JEFFREY JENNIFER JEREMY JEROLD
JERRY JESSE JESSICA JILL JIM JIMMY JOAN JOANNA JOANNE JOE JOEL JOHN JOHNATHAN JON JONATHAN JORDAN JOSE JOSEPH JOSEPHINE
JOSHUA JOYCE JUAN JUDY JULIA JULIAN JULIE JUSTIN KAELUM KAREN KARL KARLA KATHERINE KATHLEEN KATHRYN KATHY KEITH KELLY
KEN KENNETH KEVIN KIM KIMBERLY KRISTEN KRISTIN KURT KYLE LANCE LARRY LAURA LAUREN LAWRENCE LEAH LEE LEO LEONARD LEROY
LESLIE LINDA LINDSAY LISA LLOYD LORI LORRAINE LOUIS LOUISE LUIS LUKE LYNN MANUEL MARC MARCIA MARCUS MARGARET MARIA MARIE
MARILYN MARIO MARK MARLENE MARTHA MARTIN MARVIN MARY MATT MATTHEW MAUREEN MEGAN MELINDA MELISSA MELVIN MICHAEL MICHELE
MICHELLE MIGUEL MIKE MIRIAM MITCHELL MOLLY MONICA NANCY NATALIE NATHAN NEAL NEIL NICHOLAS NICOLE NOREEN NORMAN OSCAR OWEN
PAMELA PATRICIA PATRICK PAUL PAULA PEDRO PEGGY PETER PHILIP PHILLIP RACHEL RAFAEL RALPH RANDALL RANDY RAUL RAY RAYMOND
REBECCA RENEE RHONDA RICARDO RICHARD RICK RICKY RITA ROBERT ROBERTA ROBIN RODNEY ROGER ROLAND RON RONALD ROSS ROY RUBEN
RUSSELL RUTH RYAN SABRINA SALVADOR SAM SAMUEL SANDRA SARAH SCOTT SEAN SERGIO SETH SHANE SHANNON SHARON SHAUN SHAWN SHEILA
SHELLENA SHIRLEY SIMON SONIA SPENCER STANLEY STEPHANIE STEPHEN STEVE STEVEN STUART SUSAN SUZANNE SYLVIA TAMMY TARA TED
TERESA TERRY THEODORE THERESA THOMAS TIFFANY TIM TIMOTHY TINA TODD TOM TONY TRACY TRAVIS TREVOR TROY TYLER VALERIE
VANESSA VERONICA VICTOR VICTORIA VINCENT VIRGINIA WADE WALTER WARREN WAYNE WENDY WESLEY WHITNEY WILLIAM YOLANDA ZACHARY
""".split())
TITLES = re.compile(r"\b(MD|M D|PHD|PH D|DDS|DMD|DVM|ESQ|CPA|RN|LCSW|LMFT|MFT|PSYD|DC|PE)\b")
BUSINESSISH = re.compile(
    r"&|\d|\b(LOGGING|TREE|DESIGNS?|GENERAL|BACKHOE|LANDSCAPES?|INSPECTIONS?|SONS?|NETWORKING|WILDLIFE|GAS|CABINETS|"
    r"CONCRETE|HAULING|LOWBED|CUTTING|CLEARING|PRODUCTIONS?|STUDIO|PHOTOGRAPHY|BUILDERS?|HOMES|LAW|AGENCY|COUNSELING|"
    r"THERAPY|CHIROPRACTIC|DENTAL|MEDICAL|CLINIC|AUTO|TRUCK|MOTORS|SERVICE|FEED|DAIRY|VINEYARDS?|ORCHARDS?|TRUST|ESTATE|"
    r"FAMILY|PARTNERSHIP|CONSULTANT|ARBORIST|SURVEYING|EXCAVATING|CONSTRUCTION|CIBSTRUCTION|AND)\b", re.I)


def full_name_person(name):
    k = common.norm(name)
    words = re.sub(r"[^A-Z ]", " ", re.sub(r"\b[A-Z]\b", " ", k)).split()
    if not words or words[0] not in FIRST_NAMES:
        return False
    if TITLES.search(k):
        return True  # "THOMAS J FERGUSON MD PHD", "STEPHEN G SANKO MD INC"
    return (3 <= len(k.split()) <= 5 and not BUSINESSISH.search(k) and not common.BUSINESS_WORDS.search(name)
            and not CA_BUSINESS.search(name))
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
    r"REFRIGERATION|EXPRESS|SPICERS|NEXIS|REUTERS|USD|SANITATION|DISPOSAL)\b"
    r"|\bN\.?A\.?$", re.I)


def _rows(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Payees:
    """Payee names as they may be published.

    publish(name, person_flag) is common.withhold_person with four additions:
      - "<owner> DBA <business>" with a person-shaped owner is published as the business name only;
      - a source's own privacy placeholder ("PRIVACY-FIRE" in Checkbook L.A.) is shown as withheld;
      - a name the person tests flag is kept when a hand-reviewed row of config/states/ca/vendor_map_additions.csv
        (or config/vendor_map.csv) names it as a business, or when it carries a company word of CA_BUSINESS:
        looks_like_person over-matches two-word company names ("UNION DOOR", "KLASSEN CORPORATION") and
        is_person matches "CITIBANK, N.A." (BANK is not a separate word there);
      - person shapes withhold_person misses ("SMITH, J", "J SMITH", "SMITH JR", "MR SMITH") are withheld
        unless a reviewed row claims the name; full names with a middle name or a professional title
        ("RONALD ALAN BISHOP", "THOMAS J FERGUSON MD PHD") are withheld (full_name_person) unless a reviewed row
        claims the name (GLENN E THOMAS is a car dealer), and any name a reviewed map assigns to the individuals
        category is always withheld.
    """

    def __init__(self):
        maps = _rows(common.config_dir(ST) / "vendor_map_additions.csv") + _rows(common.ROOT / "config" / "vendor_map.csv")
        self.claimed = {r["name_key"] for r in maps if r["category"] != "individuals"}
        self.individuals = {r["name_key"] for r in maps if r["category"] == "individuals"}
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
        m = DBA.match(name)
        if m and (common.is_person(m.group(1)) or common.looks_like_person(m.group(1))) \
                and not common.BUSINESS_WORDS.search(m.group(1)) and not CA_BUSINESS.search(m.group(1)):
            name = m.group(2)  # "James H. Nolt dba JHNolt Associates": publish the business, not the owner
        key = common.norm(name)
        if person_flag or PRIVACY.search(name) or key in self.individuals \
                or (full_name_person(name) and key not in self.claimed):
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
