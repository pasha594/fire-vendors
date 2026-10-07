"""Helpers shared by the California adapters (pipeline/sources/ca_*.py). Not an adapter itself.

Kept here, not in common.py, because the multi-state run lets each state edit only its own files:
  soql_all         page through a Socrata SODA query (common.get, so the 1-second throttle applies)
  keep_identical   the owner's dedup rule of 2026-10-07 as corrected (identical raw lines, void-safe)
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


def copies_to_keep(n, amount, reversal, fy, reversals):
    """How many of n identical lines to keep (rule 3 of the owner's dedup rule, void-safe): one, except that a set of
    positive lines keeps min(n, r + 1), where r counts the exact reversals of the line: negative lines with the same
    reversal fields (agency, payee, account and the document fields the source repeats on a void), the amount
    negated and the same or the next fiscal year. reversals: {(reversal fields, -amount, fiscal year): set of
    identities of negative lines}; reversals identical among themselves are one identity, so they count once."""
    if n < 2 or amount <= 0:
        return 1
    r = len(reversals.get((reversal, amount, fy), set()) | reversals.get((reversal, amount, fy + 1), set()))
    return min(n, r + 1)


def keep_identical(lines, ident, reversal, amount, fiscal_year, first):
    """Owner dedup rule of 2026-10-07 as corrected the same day ("drop identical lines, drop identical days"), on
    one source's raw lines.

    1. Two lines are identical when every column the source publishes in its raw file is equal except the columns
       that only identify the row or the load (portal row ids, load timestamps). Document numbers the source
       publishes (voucher, invoice, check, PO and their line numbers) are content: lines that differ in one are
       different payments and are all kept. ident(line) returns those columns.
    2. Identical lines are kept once: the copy with the smallest first(line) (lowest row id).
    3. Void-safe: a set of n identical positive lines keeps min(n, reversals + 1) copies (copies_to_keep), so a
       payment, its void and an identical reissue keep their net. reversal(line) returns the reversal fields;
       amount(line) a Decimal; fiscal_year(line) an int.
    A doubled day is a set of identical lines, so it is covered. Returns (kept lines in input order, stats)."""
    groups = collections.defaultdict(list)
    for i, line in enumerate(lines):
        groups[ident(line)].append(i)
    reversals = collections.defaultdict(set)
    for key, members in groups.items():
        line = lines[members[0]]
        if amount(line) < 0:
            reversals[(reversal(line), -amount(line), fiscal_year(line))].add(key)
    drop, stats = set(), new_stats()
    for key, members in groups.items():
        if len(members) < 2:
            continue
        line = lines[members[0]]
        keep = copies_to_keep(len(members), amount(line), reversal(line), fiscal_year(line), reversals)
        members = sorted(members, key=lambda i: (first(lines[i]), i))
        drop.update(members[keep:])
        count(stats, len(members), keep, amount(line))
    return [line for i, line in enumerate(lines) if i not in drop], stats


def new_stats():
    return {"sets": 0, "lines": 0, "dollars": decimal.Decimal(0), "void_sets": 0, "void_kept": 0,
            "void_dollars": decimal.Decimal(0)}


def count(stats, n, keep, amount):
    """Add one set of n identical lines, of which keep are kept, to the stats."""
    if keep < n:
        stats["sets"] += 1
        stats["lines"] += n - keep
        stats["dollars"] += (n - keep) * amount
    if keep > 1:
        stats["void_sets"] += 1
        stats["void_kept"] += keep - 1
        stats["void_dollars"] += (keep - 1) * amount


def dropped_text(stats):
    return (f"{stats['lines']} identical lines dropped (${stats['dollars']:,.2f}, {stats['sets']} sets); the void "
            f"rule kept {stats['void_kept']} copies (${stats['void_dollars']:,.2f}, {stats['void_sets']} sets)")


def socrata_ident(ids):
    """ident for a Socrata raw line (a dict without its null columns): every column but the row and load ids."""
    return lambda r: tuple(sorted((k, v) for k, v in r.items() if k not in ids and v not in (None, "")))


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
