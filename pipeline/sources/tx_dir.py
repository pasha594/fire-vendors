"""Texas DIR (Department of Information Resources) cooperative contract sales: item lines for fire agencies.

    python3 pipeline/sources/tx_dir.py fetch
    python3 pipeline/sources/tx_dir.py normalize

Source: data.texas.gov (Socrata), the vendor sales reports (VSR) DIR contract holders file for every sale on a
DIR cooperative or telecom contract. Two datasets with different columns:
  w64c-ndf7  ARCHIVE DIR Cooperative Contract Sales Data, Fiscal 2010 to 2025 (cooperative contracts only)
  a743-wj72  Official - VSR Data for Cooperative & Tele Contracts FY2026 (from Sep 2025; adds telecom contracts
             and product type fields)
Fiscal year is the Texas state fiscal year, September to August (the year it ends in). IT and telecom only.

fetch      raw/<date>/tx/tx_dir/archive_fy2021_2025.json.gz  rows of w64c-ndf7, fiscal_year >= 2021
           raw/<date>/tx/tx_dir/current_fy2026.json.gz       rows of a743-wj72
           both filtered server-side (SoQL) to customer names that look fire-related (FIRE_WHERE); the full
           datasets hold about 3.7 million FY2021-2025 rows and 2.2 million FY2026 rows
           raw/<date>/tx/tx_dir/<dataset>_meta.json.gz       Socrata metadata (columns, update time)
           raw/<date>/tx/tx_dir/sample.json.gz               100 unfiltered FY2026 rows
normalize  data/states/tx/line_items.csv.gz    one row per sales line of a linked customer
           data/states/tx/transactions.csv.gz  the same lines rolled up as payee rows (payee = reseller, else
                                               the DIR contract vendor)
           data/states/tx/agencies.json        via common.assemble_agencies

Attribution: a customer is a fire agency only through a row in config/states/tx/agency_sources.csv (source
tx_dir), keyed on the customer name exactly as DIR publishes it. Those rows were reviewed by hand: fire
departments, volunteer fire departments, ESDs and city fire departments that DIR lists as their own customer
("City of Houston Fire"). City, county, 911-district, EMS-only, pension and regulator customers are never
linked, so a city's own IT purchase is never fire spend.

Duplicates: an exact duplicate line (every published field equal except the row id) is kept once. The archive
has no such lines for linked customers; FY2026 telecom lines that repeat are distinct monthly bills and differ
in invoice number or date, so they are kept. Credits are published as negative purchase amounts and kept.
"""
import collections
import json
import sys

import common

ST = "TX"
SOURCE = "tx_dir"
DOMAIN = "https://data.texas.gov"
ARCHIVE = "w64c-ndf7"
CURRENT = "a743-wj72"
FIRST_FY = 2021
PAGE = 50000

# Columns kept in the raw files. Person-name columns (customer contact, vendor contact, DIR contract manager,
# ITSAC staffing contractor) and street addresses are left out server-side so raw files hold no private names.
ARCHIVE_COLUMNS = [
    "fiscal_year", "customer_name", "customer_type", "customer_city", "customer_zip", "vendor_name", "vendor_hub_type",
    "vendor_city", "vendor_state", "reseller_name", "reseller_hub_type", "reseller_city", "reseller_state",
    "purchase_amount", "contract_number", "contract_type", "contract_subtype", "rfo_description", "rfo_number",
    "report_received_month", "purchase_month", "brand_name", "order_quantity", "unit_price", "invoice_number",
    "po_number", "order_date", "shipped_date", "staffing_technology", "staffing_title", "staffing_level",
    "staffing_technology_type", "staffing_acquistion_type", "sales_fact_number"]
CURRENT_COLUMNS = [
    "fiscal_year", "customer_name", "customer_type", "customer_state", "vendor_name", "vendor_hub_type", "reseller_name",
    "reseller_hub_type", "subcontractor_name", "purchase_amount", "contract_number", "contract_category",
    "contract_type", "contract_subtype", "rfo_description", "rfo_number", "reporting_month", "brand_name",
    "order_quantity", "unit_price", "invoice_number", "invoice_date", "po_number", "order_date", "product_type",
    "product_subtype", "staffing_technology", "staffing_title", "staffing_level", "staffing_portal_solicitation_number",
    "bulk_purchase_agreement"]

# Customer names that might be fire agencies. Deliberately broad: normalize keeps only names linked in
# agency_sources.csv. ('%EMERG%' alone would pull in the Division of Emergency Management and 911 districts.)
FIRE_WHERE = "(" + " OR ".join(f"upper(customer_name) like '{p}'" for p in [
    "%FIRE%", "%ESD%", "%E.S.D%", "%EMERGENCY SERV%", "%EMERGENCY SRVC%", "%RESCUE%", "%VFD%", "% FD", "% FD %",
    "%FOREST SERVICE%"]) + ")"


def soql_all(dataset, columns, where):
    rows, offset = [], 0
    while True:
        page = json.loads(common.get(f"{DOMAIN}/resource/{dataset}.json", {
            "$select": ",".join([":id"] + columns), "$where": where, "$order": ":id", "$limit": PAGE,
            "$offset": offset}))
        rows += page
        print(f"  {dataset}: {len(rows)} rows")
        if len(page) < PAGE:
            return rows
        offset += PAGE


def fetch():
    for ds in (ARCHIVE, CURRENT):
        common.save_raw(ST, SOURCE, f"{ds}_meta.json", common.get(f"{DOMAIN}/api/views/{ds}.json"))
    archive = soql_all(ARCHIVE, ARCHIVE_COLUMNS, f"fiscal_year >= {FIRST_FY} AND {FIRE_WHERE}")
    common.save_raw(ST, SOURCE, "archive_fy2021_2025.json", json.dumps(archive, indent=0, sort_keys=True).encode())
    current = soql_all(CURRENT, CURRENT_COLUMNS, FIRE_WHERE)
    common.save_raw(ST, SOURCE, "current_fy2026.json", json.dumps(current, indent=0, sort_keys=True).encode())
    sample = common.get(f"{DOMAIN}/resource/{CURRENT}.json",
                        {"$select": ",".join([":id"] + CURRENT_COLUMNS), "$order": ":id", "$limit": 100})
    common.save_raw(ST, SOURCE, "sample.json", sample)


def money(x):
    return f"{float(x or 0):.2f}"


def num(x):
    """Quantity or unit price as published, without float noise ('1.000000' -> '1')."""
    if x in (None, ""):
        return ""
    s = f"{float(x):.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def day(x):
    return (x or "")[:10]


def lines(raw):
    """Common shape for rows of both datasets."""
    for r in json.loads(common.read_gz(raw / "archive_fy2021_2025.json.gz")):
        yield {
            "dataset": ARCHIVE, "id": r[":id"], "record": r.get("sales_fact_number") or r[":id"],
            "fiscal_year": int(float(r["fiscal_year"])), "customer": " ".join(r.get("customer_name", "").split()),
            "vendor": r.get("vendor_name", ""), "reseller": r.get("reseller_name", ""),
            "brand": r.get("brand_name", ""),
            "product_type": " / ".join(x for x in (r.get("contract_type", ""), r.get("contract_subtype", "")) if x),
            "description": r.get("rfo_description", ""), "contract": r.get("contract_number", ""),
            "category": r.get("contract_type", ""),
            "quantity": r.get("order_quantity"), "unit_price": r.get("unit_price"), "amount": r.get("purchase_amount"),
            "date": day(r.get("order_date") or r.get("shipped_date")), "po": r.get("po_number", ""),
            "invoice": r.get("invoice_number", ""), "row": r,
        }
    for r in json.loads(common.read_gz(raw / "current_fy2026.json.gz")):
        yield {
            "dataset": CURRENT, "id": r[":id"], "record": r[":id"],
            "fiscal_year": int(float(r["fiscal_year"])), "customer": " ".join(r.get("customer_name", "").split()),
            "vendor": r.get("vendor_name", ""), "reseller": r.get("reseller_name", ""),
            "brand": r.get("brand_name", ""),
            "product_type": " / ".join(x for x in (r.get("product_type", ""), r.get("product_subtype", "")) if x),
            "description": r.get("rfo_description", ""), "contract": r.get("contract_number", ""),
            "category": r.get("contract_category", ""),
            "quantity": r.get("order_quantity"), "unit_price": r.get("unit_price"), "amount": r.get("purchase_amount"),
            "date": day(r.get("order_date") or r.get("invoice_date")), "po": r.get("po_number", ""),
            "invoice": r.get("invoice_number", ""), "row": r,
        }


def dedup_key(line):
    return (line["dataset"],) + tuple(sorted((k, str(v)) for k, v in line["row"].items()
                                             if k not in (":id", "sales_fact_number")))


def normalize():
    raw = common.latest_raw(ST, SOURCE)
    assert raw, "run fetch first"
    links = {r["source_entity_name"]: r["agency_id"] for r in common.read_config(ST, "agency_sources.csv")
             if r["source"] == SOURCE}
    assert links, "no tx_dir rows in config/states/tx/agency_sources.csv"
    seen, items, txns = set(), [], []
    stats = collections.Counter()
    for ln in lines(raw):
        aid = links.get(ln["customer"])
        if not aid or ln["fiscal_year"] < FIRST_FY:
            continue
        k = dedup_key(ln)
        if k in seen:
            stats["duplicate lines dropped"] += 1
            continue
        seen.add(k)
        seller = (ln["reseller"] or ln["vendor"]).strip()
        rid = f"{ln['dataset']}:{ln['record']}"
        desc = " / ".join(x for x in (ln["description"], f"DIR vendor {ln['vendor']}" if ln["reseller"] else "") if x)
        items.append({
            "agency_id": aid, "fiscal_year": ln["fiscal_year"], "date": ln["date"],
            "vendor": common.withhold_person(seller), "brand": ln["brand"], "product_type": ln["product_type"],
            "description": desc, "quantity": num(ln["quantity"]), "unit_price": num(ln["unit_price"]),
            "amount": money(ln["amount"]), "source_record_id": rid,
        })
        txns.append({
            "agency_id": aid, "fiscal_year": ln["fiscal_year"], "posting_date": ln["date"],
            "payee_name": common.withhold_person(seller),
            "description": " / ".join(x for x in (ln["brand"], ln["product_type"], desc) if x),
            "account": " / ".join(x for x in (ln["contract"], f"PO {ln['po']}" if ln["po"] else "") if x),
            "category_published": ln["category"], "amount": money(ln["amount"]), "source_record_id": rid,
        })
        stats["lines"] += 1
    common.upsert_rows(ST, "line_items.csv.gz", SOURCE, items)
    common.upsert_rows(ST, "transactions.csv.gz", SOURCE, txns)
    common.assemble_agencies(ST)
    total = sum(float(i["amount"]) for i in items)
    print(f"{ST} {SOURCE}: {stats['lines']} lines, ${total:,.2f}, {len({i['agency_id'] for i in items})} agencies;"
          f" {stats['duplicate lines dropped']} duplicate lines dropped")


if __name__ == "__main__":
    {"fetch": fetch, "normalize": normalize}[sys.argv[1]]()
