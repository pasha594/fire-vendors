"""Samples behind docs/sources/ca.md for the California sources that were reached but not built.

    python3 pipeline/sources/ca_feasibility.py fetch [ca_sandiego ca_sacramento ca_lacounty ca_modesto]

Not an adapter: it writes only raw/<date>/ca/<source>/ files and no table in data/states/ca/.

ca_sandiego        City of San Diego "Operating Actuals" (https://data.sandiego.gov/datasets/operating-actuals/),
                   one 66 MB CSV of actual spending by fiscal year, fund, department and expense account; no payee,
                   so no tier 1 data. (San Diego publishes no vendor payment dataset; the city's fire spending is in
                   ca_sco_cities.) seshat.datasd.org answers 403 to /robots.txt; data.sandiego.gov has none (404).
    raw/<date>/ca/ca_sandiego/sample.csv.gz       header and first 100 rows (one HTTP range request)
    raw/<date>/ca/ca_sandiego/dictionary.csv.gz   the dataset's data dictionary

ca_sacramento      City of Sacramento open data (https://data.cityofsacramento.org, ArcGIS Hub; robots.txt
                   Crawl-delay: 60 for that host). Two ArcGIS Online feature services of the City's Finance
                   department: "Checks Issued" (accounts payable checks: date, number, payee, amount; no department)
                   and "Purchase Orders to Date" (PO date, number, line, vendor, item description, amount; no
                   department). Neither can be attributed to the Fire Department. The services are on
                   services5.arcgis.com (no robots.txt; Esri answers 403 "Invalid URL").
    raw/<date>/ca/ca_sacramento/checks_meta.json.gz    layer metadata (fields)
    raw/<date>/ca/ca_sacramento/checks_sample.json.gz  first 100 rows by OBJECTID
    raw/<date>/ca/ca_sacramento/checks_control.json.gz row count and date range
    raw/<date>/ca/ca_sacramento/po_meta.json.gz        layer metadata (fields)
    raw/<date>/ca/ca_sacramento/po_sample.json.gz      first 100 rows by OBJECTID
    raw/<date>/ca/ca_sacramento/po_control.json.gz     row count

ca_lacounty        County of Los Angeles Auditor-Controller "LA County Open Expenditures"
                   (https://data.lacounty.gov, ArcGIS Hub, Crawl-delay: 60; the data are on services.arcgis.com):
                   monthly expenditure totals by fund, function, department, budget unit and expenditure class,
                   FY2025 on; no payee. The Fire Department (the Consolidated Fire Protection District) is already
                   tier 3 through ca_sco_districts.
    raw/<date>/ca/ca_lacounty/meta.json.gz             layer metadata (fields)
    raw/<date>/ca/ca_lacounty/sample.json.gz           first 100 rows by OBJECTID
    raw/<date>/ca/ca_lacounty/fire_control.json.gz     rows and dollars per fiscal year of departments or funds
                                                       whose name has FIRE

ca_modesto         City of Modesto open data (Socrata), "FIN - Weekly AP Transactions"
                   (https://data.modestogov.com/d/5qnw-bnyf): one row per week with one number per payment kind
                   (vendors, employees, refunds, uploads, ACH, P-cards; the unit is not documented); no payee and no
                   department, so it cannot give vendor rows. robots.txt: Crawl-delay 1, SODA API not disallowed.
    raw/<date>/ca/ca_modesto/meta.json.gz              Socrata metadata
    raw/<date>/ca/ca_modesto/sample.json.gz            first 100 rows
"""
import json
import sys

import common

ST = "CA"
DATE = "2026-10-06"  # the California raw folder of this run
SD_CSV = "https://seshat.datasd.org/operating_actuals/actuals_operating_datasd.csv"
SD_DICT = "https://seshat.datasd.org/operating_actuals/operating_actuals_dictionary_datasd.csv"
SAC = "https://services5.arcgis.com/54falWtcpty3V47Z/arcgis/rest/services"
LAC = "https://services.arcgis.com/RmCCgQtiZLDCtblq/arcgis/rest/services/Open_Expenditures/FeatureServer/0"
MODESTO = "https://data.modestogov.com"


def stats(*fields):
    out = [{"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "n"}]
    for kind, field in fields:
        out.append({"statisticType": kind, "onStatisticField": field, "outStatisticFieldName": f"{kind}_{field}"})
    return json.dumps(out)


def sample(layer):
    return common.get(f"{layer}/query", {"where": "1=1", "outFields": "*", "orderByFields": "OBJECTID",
                                         "resultRecordCount": 100, "f": "json"})


def sandiego():
    head = common.get(SD_CSV, headers={"Range": "bytes=0-65535"})
    lines = head.split(b"\n")[:101]
    common.save_raw(ST, "ca_sandiego", "sample.csv", b"\n".join(lines) + b"\n", date=DATE)
    common.save_raw(ST, "ca_sandiego", "dictionary.csv", common.get(SD_DICT), date=DATE)


def sacramento():
    for name, layer in [("checks", f"{SAC}/issuedchecks/FeatureServer/0"), ("po", f"{SAC}/purchaseorder/FeatureServer/1")]:
        common.save_raw(ST, "ca_sacramento", f"{name}_meta.json", common.get(layer, {"f": "json"}), date=DATE)
        common.save_raw(ST, "ca_sacramento", f"{name}_sample.json", sample(layer), date=DATE)
        extra = [("min", "Check_Date"), ("max", "Check_Date"), ("sum", "Check_Amount")] if name == "checks" \
            else [("sum", "SUM_AMOUNT")]
        common.save_raw(ST, "ca_sacramento", f"{name}_control.json",
                        common.get(f"{layer}/query", {"where": "1=1", "outStatistics": stats(*extra), "f": "json"}),
                        date=DATE)


def lacounty():
    common.save_raw(ST, "ca_lacounty", "meta.json", common.get(LAC, {"f": "json"}), date=DATE)
    common.save_raw(ST, "ca_lacounty", "sample.json", sample(LAC), date=DATE)
    common.save_raw(ST, "ca_lacounty", "fire_control.json", common.get(f"{LAC}/query", {
        "where": "UPPER(Department) LIKE '%FIRE%' OR UPPER(Fund) LIKE '%FIRE%'",
        "groupByFieldsForStatistics": "Department,Fiscal_Year", "orderByFields": "Department,Fiscal_Year",
        "outStatistics": stats(("sum", "Amount")), "f": "json"}), date=DATE)


def modesto():
    common.save_raw(ST, "ca_modesto", "meta.json", common.get(f"{MODESTO}/api/views/5qnw-bnyf.json"), date=DATE)
    common.save_raw(ST, "ca_modesto", "sample.json", common.get(f"{MODESTO}/resource/5qnw-bnyf.json",
                                                                {"$order": ":id", "$limit": 100}), date=DATE)


SOURCES = {"ca_sandiego": sandiego, "ca_sacramento": sacramento, "ca_lacounty": lacounty, "ca_modesto": modesto}


def fetch(names):
    for name in names or SOURCES:
        SOURCES[name]()
        print(f"{ST}: {name}: feasibility samples saved")


if __name__ == "__main__":
    assert sys.argv[1] == "fetch"
    fetch(sys.argv[2:])
