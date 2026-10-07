"""Idaho Local Government Registry (Transparent Idaho): annual expenditure totals of fire districts (tier 3).

    python3 pipeline/sources/id_lgr.py fetch
    python3 pipeline/sources/id_lgr.py normalize

Source: Transparent Idaho (Idaho State Controller's Office, SCO), "Local Districts" pages, https://transparent.idaho.gov/
local-district. Every local government entity files an Annual Financial Transparency Report in the Local Government
Registry (Idaho Code 67-1076, due December 1): its adopted budget and the prior year's actual revenues and
expenditures, with the budget, audit or actuals document. The site's own JSON API (https://transparent.idaho.gov/
api/, the one its pages call) returns, per county, entity type and fiscal year, each entity's Actual_Expenditures,
Actual_Revenue, Budgeted_Expenditures and Budgeted_Revenue (whole dollars, all funds) and links to the filed PDFs.
Entity type 6 is "Fire District" (Idaho Code 31-14). `FiscalYear` is the entity's own fiscal year, the year it ends
in: Kuna Rural Fire District's FY2024 actual equals its audit "for the year ended December 31, 2024". A fire
protection district's fiscal year starts October 1 or January 1, as its board chooses (Idaho Code 31-1422); the
registry does not say which, so agency_sources.csv leaves fy_start empty. The API lists FY2021 to FY2025; actuals
for a year arrive with the next year's filing, so the newest year has budgets only.

Access: robots.txt allows every path ("User-agent: * / Disallow:"). The site's CloudFront answers every request
whose User-Agent is an HTTP library or the project's plain agent with its app shell (HTML, status 200) instead of
the file, so requests use the project's agent in the usual crawler form (UA, as oh_feasibility.py does for
DataOhio). Fetch asserts every answer is JSON. The SCO terms of use (https://www.sco.idaho.gov/LivePages/
site-policies.aspx) say nothing about automated access but limit use of site content to non-commercial,
informational purposes and reserve copying and derived works; see docs/sources/id.md (open question).

fetch      raw/<date>/id/id_lgr/robots.txt.gz                  transparent.idaho.gov/robots.txt
           raw/<date>/id/id_lgr/fiscal_years.json.gz           years the API offers
           raw/<date>/id/id_lgr/counties.json.gz               the 44 counties (CountyID = EntityID)
           raw/<date>/id/id_lgr/entity_types.json.gz           registry entity types
           raw/<date>/id/id_lgr/entity_lists.json.gz           every registered entity per type (names, counties);
                                                               normalize checks no fire agency hides in another type
           raw/<date>/id/id_lgr/county_types.json.gz           entity types present in each county (the entity
                                                               query fails for a county without the type)
           raw/<date>/id/id_lgr/fire_districts_fy<YYYY>.json.gz  {CountyID: getCountyEntities answer} for type 6
           raw/<date>/id/id_lgr/sample.json.gz                 the first 100 entity records of the newest year with
                                                               actuals, as the API returns them
normalize  data/states/id/totals.csv          one row per district and fiscal year: "Total expenditures (actual)"
           config/states/id/sources.csv       this source's row
           data/states/id/agencies.json       via common.assemble_agencies

Attribution: every registry entity of type Fire District is a fire agency. It counts only through a hand-reviewed
row of config/states/id/agency_sources.csv (source id_lgr, source_entity_id = registry EntityID): linked to its USFA
registry department when the names are the same district (exact name, or the same place with a district suffix
such as "Rural Fire District" / "Fire Protection District"); a "<city> Rural Fire (Protection) District" is NOT
linked to the city's "<city> Fire Department", because the district is a separate taxing body that usually
contracts with the city. Unlinked districts are rows of config/states/id/agencies_added.csv (id ID-S-<slug>).
normalize stops on a type-6 entity without a link, and on a fire-named entity of another type that is not in
NOT_FIRE.

Duplicates and reversals: a district serving several counties is listed under each; normalize asserts the copies
agree and keeps one per EntityID and year. Only actual expenditures are written: budgets are plans, not spending,
and stay in the raw files. A null or zero actual means none was filed and gives no row (never $0).
"""
import collections
import json
import re
import sys

import common

ST = "ID"
SOURCE = "id_lgr"
API = "https://transparent.idaho.gov/api/"
UA = "Mozilla/5.0 (compatible; utah-fire-procurement/0.1; +https://github.com/pasha594/utah-fire-procurement)"
FIRE_TYPE = 6
FIRST_FY = 2021
CATEGORY = "Total expenditures (actual)"
# Registry entities of other types whose names suggest fire or emergency work but that run no fire department.
NOT_FIRE = {
    "Ada County Emergency Medical Services": "ambulance district",
    "Kootenai County Emergency Medical Services System": "ambulance district",
    "Valley County EMS District": "ambulance district",
    "Nez Perce County-City of Lewiston Emergency Communications Joint Powers Board": "dispatch joint powers board",
}
SOURCE_ROW = {
    "source": SOURCE, "name": "Idaho Local Government Registry (Transparent Idaho): fire district totals", "tier": "3",
    "url": "https://transparent.idaho.gov/local-district",
    "fiscal_year": "District FY, Oct-Sep or Jan-Dec (Idaho Code 31-1422), the year it ends in",
    "note": "Total actual expenditures (all funds) each fire district files with the State Controller; no vendor "
            "detail; the newest year has budgets only, so no row",
}


def api(path, **params):
    body = common.get(API + path, params or None, headers={"User-Agent": UA})
    assert body[:1] in (b"[", b"{"), f"{path}: not JSON (CloudFront app shell?): {body[:80]!r}"
    return body


def fetch():
    common.save_raw(ST, SOURCE, "robots.txt", common.get("https://transparent.idaho.gov/robots.txt",
                                                         headers={"User-Agent": UA}))
    years = json.loads(api("getFiscalYears"))
    common.save_raw(ST, SOURCE, "fiscal_years.json", json.dumps(years).encode())
    counties = json.loads(api("getAllCounties"))
    common.save_raw(ST, SOURCE, "counties.json", json.dumps(counties, indent=0).encode())
    types = json.loads(api("getCountyEntityTypeList"))
    common.save_raw(ST, SOURCE, "entity_types.json", json.dumps(types, indent=0).encode())
    lists = {}
    for t in types:
        lists[str(t["EntityTypeID"])] = json.loads(api("getCountyEntityList", EntityTypeId=t["EntityTypeID"]))
    common.save_raw(ST, SOURCE, "entity_lists.json", json.dumps(lists, indent=0, sort_keys=True).encode())
    print(f"  {len(counties)} counties, {len(types)} entity types, {len(lists[str(FIRE_TYPE)])} fire districts")
    # getCountyEntities answers HTTP 500 for a county without the entity type (Clark County has no fire
    # district), so each county's types are read first and only counties with fire districts are queried.
    county_types = {str(c["EntityID"]): json.loads(api("getCountyEntityTypes", CountyID=c["EntityID"]))
                    for c in counties}
    common.save_raw(ST, SOURCE, "county_types.json", json.dumps(county_types, indent=0, sort_keys=True).encode())
    with_fire = [c for c in counties if any(t["EntityTypeID"] == FIRE_TYPE for t in county_types[str(c["EntityID"])])]
    print(f"  {len(with_fire)} counties with fire districts")
    newest = None
    for fy in sorted(int(y) for y in years):
        if fy < FIRST_FY:
            continue
        out = {}
        for c in with_fire:
            out[str(c["EntityID"])] = json.loads(api("getCountyEntities", EntityTypeID=FIRE_TYPE,
                                                     CountyID=c["EntityID"], FiscalYear=fy))
        common.save_raw(ST, SOURCE, f"fire_districts_fy{fy}.json", json.dumps(out, indent=0, sort_keys=True).encode())
        recs = [r for rs in out.values() for r in rs]
        with_actual = [r for r in recs if r.get("Actual_Expenditures")]
        print(f"  FY{fy}: {len(recs)} county listings, {len({r['EntityID'] for r in recs})} districts,"
              f" {len({r['EntityID'] for r in with_actual})} with actual expenditures")
        if with_actual:
            newest = out
    sample = [r for c in sorted(newest, key=int) for r in newest[c]][:100]
    common.save_raw(ST, SOURCE, "sample.json", json.dumps(sample, indent=0).encode())


def load(raw):
    """{(EntityID, fy): record} from every fire_districts_fy<YYYY> file, multi-county copies checked and merged;
    also {EntityID: sorted county names}."""
    counties = {str(c["EntityID"]): c["EntityName"] for c in json.loads(common.read_gz(raw / "counties.json.gz"))}
    recs, where = {}, collections.defaultdict(set)
    for path in sorted(raw.glob("fire_districts_fy*.json.gz")):
        fy = int(re.search(r"fy(\d{4})", path.name).group(1))
        for cid, rows in json.loads(common.read_gz(path)).items():
            for r in rows:
                key = (r["EntityID"], fy)
                where[r["EntityID"]].add(counties[cid])
                vals = {k: r.get(k) for k in ("EntityName", "Actual_Expenditures", "Actual_Revenue",
                                              "Budgeted_Expenditures", "Budgeted_Revenue")}
                assert recs.get(key, vals) == vals, f"county copies disagree: {key} {recs[key]} {vals}"
                recs[key] = vals
    return recs, {k: sorted(v) for k, v in where.items()}


def normalize():
    raw = common.latest_raw(ST, SOURCE)
    assert raw, "run fetch first"
    lists = json.loads(common.read_gz(raw / "entity_lists.json.gz"))
    fire = {e["EntityID"]: e["EntityName"] for e in lists[str(FIRE_TYPE)]}
    for tid, ents in lists.items():
        if int(tid) == FIRE_TYPE:
            continue
        for e in ents:
            if common.FIRE_NAME.search(e["EntityName"]) or re.search(r"EMERGENCY", e["EntityName"], re.I):
                assert e["EntityName"] in NOT_FIRE, f"fire-named entity of type {tid}: {e['EntityName']}"
    links = {int(r["source_entity_id"]): r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")
             if r["source"] == SOURCE}
    missing = sorted(n for i, n in fire.items() if i not in links)
    assert not missing, f"fire districts without a row in agency_sources.csv: {missing[:10]}"
    recs, _ = load(raw)
    rows, dropped = [], collections.Counter()
    for (eid, fy), r in sorted(recs.items()):
        assert eid in fire, f"type-6 answer for an entity missing from the type-6 list: {eid} {r['EntityName']}"
        amount = r["Actual_Expenditures"]
        if not amount:
            dropped["no actual filed" if amount is None else "actual of 0"] += 1
            continue
        rows.append({"agency_id": links[eid], "fiscal_year": str(fy), "category_published": CATEGORY,
                     "amount": f"{amount:.2f}"})
    keys = [(r["agency_id"], r["fiscal_year"]) for r in rows]
    dupes = {k for k in keys if keys.count(k) > 1}
    assert not dupes, f"two districts linked to one agency in one year: {sorted(dupes)[:5]}"
    years = sorted({r["fiscal_year"] for r in rows})
    write_source_row(f"{years[0]}-{years[-1]}", raw.parent.parent.name)
    common.upsert_rows(ST, "totals.csv", SOURCE, rows)
    common.assemble_agencies(ST)
    total = sum(float(r["amount"]) for r in rows)
    print(f"{SOURCE}: {len(rows)} district-years, {len({r['agency_id'] for r in rows})} agencies, ${total:,.0f};"
          f" skipped: {dict(dropped)}")


def write_source_row(years, fetched):
    """Replace this source's row in config/states/id/sources.csv, keep the others."""
    cols = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]
    rows = [r for r in common.read_config(ST, "sources.csv") if r["source"] != SOURCE]
    rows.append({**SOURCE_ROW, "years": years, "fetched": fetched})
    common.write_csv(common.config_dir(ST) / "sources.csv", cols, sorted(rows, key=lambda r: r["source"]))


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
