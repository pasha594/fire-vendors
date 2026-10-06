"""Helpers shared by the California adapters (pipeline/sources/ca_*.py). Not an adapter itself.

Kept here, not in common.py, because the multi-state run lets each state edit only its own files:
  soql_all         page through a Socrata SODA query (common.get, so the 1-second throttle applies)
  collapse_reloads duplicate handling for sources without a line number
  links            the hand-reviewed rows of config/states/ca/agency_sources.csv for one source
  register_source  this source's row in config/states/ca/sources.csv
  money            dollars as a two-decimal string

Payee names: the adapters call common.withhold_person directly (owner decision of 2026-10-06: payee names are
shown as published, private persons included; only email addresses and bank account text are cut).
"""
import collections
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
