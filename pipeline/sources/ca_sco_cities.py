"""California State Controller (SCO) City - Expenditures: each city's annual fire spending (tier 3).

    python3 pipeline/sources/ca_sco_cities.py fetch
    python3 pipeline/sources/ca_sco_cities.py normalize

Source: SCO "By The Numbers" (Socrata), "City - Expenditures", https://bythenumbers.sco.ca.gov/d/ju3w-4gxp (licence:
public domain): the expenditure part of the Financial Transactions Report every California city files with the
State Controller, FY2002-03 to FY2023-24 on 2026-10-06, 482 cities. `fiscal_year` is the year the fiscal year
ends (2024 = FY2023-24); city fiscal years run July to June. Current expenditures are reported by function;
the Public Safety function "Fire" (form field CURR_EXP_FIRE, line "Fire_Current Expenditures") is a single
annual total of the city's fire operating spending. Capital outlay and debt service are not split by function,
and Emergency Medical Services is a separate line (CURR_EXP_EMERG_MEDICAL_SERV) that is not taken here.

fetch      raw/<date>/ca/ca_sco_cities/ju3w-4gxp_meta.json.gz  Socrata metadata
           raw/<date>/ca/ca_sco_cities/fire.json.gz            every CURR_EXP_FIRE row with fiscal_year >= 2021
           raw/<date>/ca/ca_sco_cities/cities.json.gz          every city that filed in those years, with county
                                                               (used to tell a city fire department from a
                                                               fire protection district of the same name)
           raw/<date>/ca/ca_sco_cities/sample.json.gz          100 unfiltered rows
normalize  data/states/ca/totals.csv          one row per agency and fiscal year ("Fire_Current Expenditures")
           config/states/ca/sources.csv       this source's row
           data/states/ca/agencies.json       via common.assemble_agencies

Attribution: a city's fire line counts only through a hand-reviewed row of config/states/ca/agency_sources.csv
(source ca_sco_cities, source_entity_name = SCO city name; source_entity_id = the SCO's 4-digit city code, the
digits after the year in `row_number`) that links the city to its
own fire department in the USFA registry: the registry department in the same county named "<City> Fire
Department", "City of <City> Fire Department", "<City> Fire", "<City> Fire & Rescue" or "<City> Fire-Rescue".
A city with no such department (it contracts with a county, CAL FIRE or a fire district, or is served by a
fire authority JPA) is not linked, because its fire line then pays another agency. Lines of $0 are dropped.

Duplicates and reversals: one value per city, year and line (`row_number` is unique; normalize asserts it).
"""
import collections
import decimal
import json
import sys

import common
import ca_common

ST = "CA"
SOURCE = "ca_sco_cities"
DOMAIN = "https://bythenumbers.sco.ca.gov"
DATASET = "ju3w-4gxp"
FIRST_FY = 2021
FIELD = "CURR_EXP_FIRE"
WHERE = f"form_table = '{FIELD}' AND fiscal_year >= {FIRST_FY}"


def fetch():
    meta = common.get(f"{DOMAIN}/api/views/{DATASET}.json")
    common.save_raw(ST, SOURCE, f"{DATASET}_meta.json", meta)
    select = ",".join([":id"] + ca_common.columns(meta))
    rows = ca_common.soql_all(DOMAIN, DATASET, select, WHERE)
    common.save_raw(ST, SOURCE, "fire.json", json.dumps(rows, indent=0, sort_keys=True).encode())
    cities = ca_common.soql(DOMAIN, DATASET, select="entity_name, county, count(*) as n",
                            where=f"fiscal_year >= {FIRST_FY}", group="entity_name, county",
                            order="entity_name, county", limit=5000)
    common.save_raw(ST, SOURCE, "cities.json", json.dumps(cities, indent=0, sort_keys=True).encode())
    common.save_raw(ST, SOURCE, "sample.json", common.get(f"{DOMAIN}/resource/{DATASET}.json",
                                                          {"$select": select, "$order": ":id", "$limit": 100}))
    print(f"{ST}: {SOURCE}: {len(rows)} rows, {len(cities)} cities")


def normalize():
    d = common.latest_raw(ST, SOURCE)
    assert d, f"{ST}: run fetch first"
    raw = json.loads(common.read_gz(d / "fire.json.gz"))
    assert raw and all(r["form_table"] == FIELD and int(r["fiscal_year"]) >= FIRST_FY for r in raw)
    assert max(collections.Counter(r["row_number"] for r in raw).values()) == 1, "duplicate row_number"
    linked = {r["source_entity_name"]: r["agency_id"] for r in ca_common.links(SOURCE)}
    entities = {r["entity_name"] for r in raw}
    district_agencies = {r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")
                         if r["source"] == "ca_sco_districts"}
    both = sorted(set(linked.values()) & district_agencies)
    assert not both, f"{SOURCE}: agencies also linked to a district filing (would count one budget twice): {both[:5]}"
    stale = sorted(k for k in linked if k not in entities)
    assert not stale, f"{SOURCE}: agency_sources.csv rows match no SCO city: {stale[:5]}"

    sums = collections.defaultdict(decimal.Decimal)
    for r in raw:
        key = r["entity_name"]
        if key in linked and r.get("value") not in (None, ""):
            sums[(linked[key], int(r["fiscal_year"]), r["line_description"].strip())] += decimal.Decimal(r["value"])
    rows = [{"agency_id": a, "fiscal_year": str(fy), "category_published": c, "amount": ca_common.money(v)}
            for (a, fy, c), v in sorted(sums.items()) if v != 0]
    common.upsert_rows(ST, "totals.csv", SOURCE, rows)

    years = sorted({int(r["fiscal_year"]) for r in rows})
    ca_common.register_source({
        "source": SOURCE, "name": "California State Controller, City Financial Transactions Reports (fire function)",
        "tier": "3", "url": f"{DOMAIN}/d/{DATASET}", "years": f"{years[0]}-{years[-1]}",
        "fiscal_year": "City FY, Jul-Jun", "fetched": d.parent.parent.name,
        "note": "One annual total per city: current expenditures of the Fire function (operations only; capital "
                "outlay, debt service and the separate Emergency Medical Services line are not included); "
                "linked only to the city's own fire department; no vendors. "
                f"FY{years[-1]} (2023-24) is the latest year the SCO has published"})
    common.assemble_agencies(ST)
    total = sum(decimal.Decimal(r["amount"]) for r in rows)
    print(f"{ST}: {SOURCE}: {len(rows)} totals for {len({r['agency_id'] for r in rows})} agencies (${total:,.0f}), "
          f"FY{years[0]}-FY{years[-1]}")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
