"""Helpers shared by the California adapters (pipeline/sources/ca_*.py). Not an adapter itself.

Kept here, not in common.py, because the multi-state run lets each state edit only its own files:
  soql_all         page through a Socrata SODA query (common.get, so the 1-second throttle applies)
  drop_identical   the owner's dedup rule of 2026-10-07 (identical lines and doubled days), every line source
  links            the hand-reviewed rows of config/states/ca/agency_sources.csv for one source
  register_source  this source's row in config/states/ca/sources.csv
  money            dollars as a two-decimal string

Payee names: the adapters call common.withhold_person directly (owner decision of 2026-10-06: payee names are
shown as published, private persons included; only email addresses and bank account text are cut).
"""
import decimal
import json

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


def drop_identical(rows, table):
    """Owner decision of 2026-10-07 (dedup rule): drop identical lines and identical (doubled) days.

    rows: one source's normalized rows for data/states/ca/<table>, in the adapter's deterministic order. Two rows
    are identical when every column but source_record_id (the source's own row or transaction id) is equal:
    agency, fiscal year, date, payee as published, description, account, published category and amount (item
    lines: also vendor, brand, product type, quantity and unit price). The first row of each set is kept, the
    rest dropped. A day loaded twice is a set of identical rows, so it is covered; rows without a date compare on
    fiscal year; a negative row (reversal) is never identical to the positive row it reverses.
    Returns (kept rows, {"groups": sets with a dropped row, "lines": rows dropped, "dollars": Decimal dropped})."""
    fields = [f for f in common.TABLES[table] if f not in ("source", "source_record_id")]
    seen, groups, keep, lines, dollars = set(), set(), [], 0, decimal.Decimal(0)
    for r in rows:
        key = tuple(r.get(f) or "" for f in fields)
        if key in seen:
            groups.add(key)
            lines += 1
            dollars += decimal.Decimal(r["amount"])
            continue
        seen.add(key)
        keep.append(r)
    return keep, {"groups": len(groups), "lines": lines, "dollars": dollars}


def dropped_text(stats):
    return (f"{stats['lines']} identical lines dropped (${stats['dollars']:,.2f}, {stats['groups']} sets; "
            "owner rule of 2026-10-07)")


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
