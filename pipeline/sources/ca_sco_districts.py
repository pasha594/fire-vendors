"""California State Controller (SCO) Special Districts - Expenditures: annual totals of fire districts (tier 3).

    python3 pipeline/sources/ca_sco_districts.py fetch
    python3 pipeline/sources/ca_sco_districts.py normalize

Source: SCO "By The Numbers" (Socrata), "Special Districts - Expenditures", https://bythenumbers.sco.ca.gov/d/m9u3-wdam
(also listed on catalog.data.gov as "Special Districts - Expenditures"; licence: public domain). It is the
expenditure part of the Financial Transactions Reports (FTR) that every special district files with the State
Controller each year: FY2002-03 to FY2023-24 on 2026-10-06, about 4,800 districts, one row per entity, year and
report line. `fiscalyear` is the year the fiscal year ends (2024 = FY2023-24); districts' fiscal year runs
July to June. `activity` is the SCO's classification of the district's main function ("Fire Protection");
`districttype2` is Independent, Dependent (governed by a county board) or Joint Powers Authority (JPA).

fetch      raw/<date>/ca/ca_sco_districts/m9u3-wdam_meta.json.gz  Socrata metadata
           raw/<date>/ca/ca_sco_districts/fire.json.gz            every row with fiscalyear >= 2021 whose activity is
                                                                  Fire Protection or whose name has FIRE, RESCUE or
                                                                  EMERGENCY in it (server-side SoQL); JPAs carry
                                                                  their own activity, so fire authorities run as
                                                                  JPAs are only found by name
           raw/<date>/ca/ca_sco_districts/control.json.gz         rows and dollars per year for the same filter
           raw/<date>/ca/ca_sco_districts/sample.json.gz          100 unfiltered rows
normalize  data/states/ca/totals.csv          one row per agency, fiscal year and report line (zero lines dropped)
           config/states/ca/sources.csv       this source's row
           data/states/ca/agencies.json       via common.assemble_agencies

Attribution: an SCO entity counts only through a hand-reviewed row of config/states/ca/agency_sources.csv
(source ca_sco_districts, source_entity_name = SCO entity name, which is unique statewide; the SCO publishes no
stable entity id, so source_entity_id is empty). Every entity
with activity Fire Protection is linked: to its USFA registry department when name and county match (strictly,
see docs/sources/ca.md), otherwise to a row added in config/states/ca/agencies_added.csv (id CA-S-<slug>). A
JPA or other entity is linked only when it runs a fire department (for example Orange County Fire Authority);
fire-named entities that do not (insurance pools, training centres, dispatch, EMS agencies, fire-road
maintenance divisions) are listed in NOT_FIRE with the reason, and normalize stops on any fire-named entity
that is in neither list.

Duplicates and reversals: the FTR has one value per entity, year and line (`rownumber` is unique); normalize
asserts that. Amounts are as filed; a negative line (rare) is kept.
"""
import collections
import decimal
import json
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_sco_districts"
DOMAIN = "https://bythenumbers.sco.ca.gov"
DATASET = "m9u3-wdam"
FIRST_FY = 2021
WHERE = (f"fiscalyear >= {FIRST_FY} AND (activity = 'Fire Protection' OR upper(entityname) like '%FIRE%' "
         "OR upper(entityname) like '%RESCUE%' OR upper(entityname) like '%EMERGENCY%')")

# Fire-named SCO entities that are not fire agencies (no fire department of their own), with the reason.
NOT_FIRE = {
    "Butterfield Lane Emergency Fire Escape Road Permanent Road Division": "road maintenance division",
    "California Fire and Rescue Training Authority": "training JPA",
    "California Tahoe Emergency Services Operation Authority": "ambulance JPA",
    "Consolidated Emergency Dispatch Agency": "dispatch JPA",
    "Consolidated Fire Agencies": "dispatch JPA (CONFIRE)",
    "El Dorado County Emergency Services Authority": "ambulance JPA",
    "Fire Agencies Insurance Risk Authority": "insurance pool",
    "Fire Agencies Self Insurance System (FASIS)": "insurance pool",
    "Fire District Association of California Employment Benefits Authority": "benefits pool",
    "Fire House Community Park Agency": "park JPA",
    "Fire Risk Management Services (FRMS)": "insurance pool",
    "Firebaugh Canal Water District": "water district",
    "Firenet Lassen": "radio network JPA",
    "Firestone Garbage Disposal District": "garbage district",
    "Garth Drive Emergency Fire Escape Road Permanent Road Division": "road maintenance division",
    "Heartland Fire Training Authority": "training JPA",
    "Imperial Valley Emergency Communications Authority": "dispatch JPA",
    "Indian Wells Fire Access Maintenance District No. 1 (Riverside)": "road maintenance district",
    "Inland Counties Emergency Medical Agency": "EMS agency",
    "Jennifer Drive Emergency Fire Escape Permanent Road Division": "road maintenance division",
    "Los Palos Drive Emergency Fire Escape Road No. 2 Permanent Road Division": "road maintenance division",
    "Los Palos Emergency Fire Access Permanent Road Division": "road maintenance division",
    "Marin Emergency Radio Authority": "radio JPA",
    "Marin Wildfire Prevention Authority": "vegetation management JPA; no fire department",
    "Metro Cities Fire Authority": "dispatch JPA (Metro Net)",
    "Mountain Counties Emergency Medical Services Agency": "EMS agency",
    "Mountain Valley Emergency Medical Services Agency": "EMS agency",
    "North Coast Emergency Medical Services District": "EMS agency",
    "Orange County - City Hazardous Material Emergency Response Authority": "hazmat JPA",
    "Rescue District Facilities Corporation": "financing corporation",
    "San Bernardino Regional Emergency Training Center": "training JPA",
    "San Joaquin County Regional Fire Dispatch Authority": "dispatch JPA",
    "San Mateo County Operational Area Emergency Services Organization Authority": "emergency management JPA",
    "San Mateo County Pre-Hospital Emergency Medical Services Group": "EMS JPA",
    "Santa Cruz County Emergency Medical Services Integration Authority": "EMS JPA",
    "Santa Cruz County Fire Agencies Insurance Group": "insurance pool",
    "Santee-Lakeside Emergency Medical Services Joint Powers Authority": "ambulance JPA",
    "Sierra - Sacramento Valley Emergency Medical Services Agency": "EMS agency",
    "Skylark Lane Emergency Fire Escape Road Permanent Road Division": "road maintenance division",
    "Sol Semete Emergency Fire Escape Road Permanent Road Division": "road maintenance division",
    "Solano Emergency Medical Services Cooperative": "EMS agency",
    "Southern Marin Emergency Medical-Paramedic System": "paramedic JPA funding member agencies",
    "Squaw Carpet Fire Access No. 2 Permanent Road Division": "road maintenance division",
    "Squaw Carpet Fire Access Permanent Road Division": "road maintenance division",
    "Terri Lee Terrace Emergency Fire Escape Permanent Road Division": "road maintenance division",
    "Unified San Diego County Emergency Services Organization": "emergency management JPA",
    "West End Fire and Emergency Response Commission": "hazmat JPA",
    "Westview Road Emergency Fire Escape Permanent Road Division": "road maintenance division",
    "Yolo Emergency Communications Agency": "dispatch JPA",
}


def fetch():
    meta = common.get(f"{DOMAIN}/api/views/{DATASET}.json")
    common.save_raw(ST, SOURCE, f"{DATASET}_meta.json", meta)
    select = ",".join([":id"] + ca_common.columns(meta))
    rows = ca_common.soql_all(DOMAIN, DATASET, select, WHERE)
    common.save_raw(ST, SOURCE, "fire.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    control = ca_common.soql(DOMAIN, DATASET, select="fiscalyear, count(*) as n, sum(value) as value",
                             where=WHERE, group="fiscalyear", order="fiscalyear")
    common.save_raw(ST, SOURCE, "control.json", json.dumps(control, indent=0, sort_keys=True).encode())
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{DATASET}.json",
                                                          {"$select": select, "$order": ":id", "$limit": 100}))
    print(f"{ST}: {SOURCE}: {len(rows)} rows")


def category(r):
    """The report line as published: the line description, under its group when the two differ."""
    sub, line = r["subcategory2"].strip(), r["linedescription"].strip()
    return line if line == sub else f"{sub} / {line}"


def read_raw(d):
    rows = json.loads(common.read_gz(d / "fire.json.gz"))
    control = json.loads(common.read_gz(d / "control.json.gz"))
    assert len(rows) == sum(int(c["n"]) for c in control), "raw rows do not match control.json"
    return rows


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    raw = read_raw(d)
    linked = {r["source_entity_name"]: r["agency_id"] for r in ca_common.links(SOURCE)}
    entities = {r["entityname"]: r["activity"] for r in raw}
    assert len(entities) == len({(r["entityname"], r["county"]) for r in raw}), "an SCO entity name is in two counties"
    unlinked = sorted(k for k, act in entities.items()
                      if k not in linked and (act == "Fire Protection" or k not in NOT_FIRE))
    assert not unlinked, (f"{SOURCE}: fire entities neither linked in config/states/ca/agency_sources.csv nor in "
                          f"NOT_FIRE: {unlinked[:10]} ({len(unlinked)})")
    stale = sorted(k for k in linked if k not in entities)
    assert not stale, f"{SOURCE}: agency_sources.csv rows match no SCO entity: {stale[:5]}"
    ids = collections.Counter(r["rownumber"] for r in raw)
    assert max(ids.values()) == 1, "duplicate rownumber in SCO rows"

    sums = collections.defaultdict(decimal.Decimal)
    for r in raw:
        key = r["entityname"]
        if key not in linked:
            continue
        fy = int(r["fiscalyear"])
        assert fy >= FIRST_FY
        sums[(linked[key], fy, category(r))] += decimal.Decimal(r["value"])
    rows = [{"agency_id": a, "fiscal_year": str(fy), "category_published": c, "amount": ca_common.money(v)}
            for (a, fy, c), v in sorted(sums.items()) if v != 0]
    common.upsert_rows(ST, "totals.csv", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    ca_common.register_source({
        "source": SOURCE, "name": "California State Controller, Special Districts Financial Transactions Reports",
        "tier": "3", "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "Special district FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "Annual expenditure totals by report line (salaries, benefits, services and supplies, capital "
                "outlay, debt service) as filed by fire protection districts and fire authority JPAs; no vendors. "
                f"FY{years[-1]} (2023-24) is the latest year the SCO has published"})
    common.assemble_agencies(ST)
    agencies = {r["agency_id"] for r in rows}
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    print(f"{ST}: {SOURCE}: {len(rows)} total lines for {len(agencies)} agencies (${total:,.0f}), "
          f"FY{years[0]}-FY{years[-1]}")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
