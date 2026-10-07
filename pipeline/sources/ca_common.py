"""Helpers shared by the California adapters (pipeline/sources/ca_*.py). Not an adapter itself.

Kept here, not in common.py, because the multi-state run lets each state edit only its own files:
  soql_all         page through a Socrata SODA query (common.get, so the 1-second throttle applies)
  keep_identical   the owner's dedup rule of 2026-10-07 as corrected (identical raw lines, void-safe, identical
                   voids fixed); copies_to_keep and negative_copies_to_keep are its two halves (ca_fiscal uses them)
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


def family(reversal, amount, fy, present):
    """The family of a negative line of fiscal year fy: the lines with the same reversal fields and the same amount up
    to sign (amount > 0 here), a payment of fiscal year y being linked to the negative lines of y and y + 1 (the
    void-safe rule's "same or next fiscal year"); lines linked through a chain of such links are one family.
    present(reversal, amount, fy, sign) says whether a line of that sign (1 payment, -1 negative) exists. Returns the
    family's (sign, fiscal year) nodes, sorted."""
    todo, seen = [(-1, fy)], {(-1, fy)}
    while todo:
        sign, y = todo.pop()
        for node in ([(1, y - 1), (1, y)] if sign < 0 else [(-1, y), (-1, y + 1)]):
            if node not in seen and present(reversal, amount, node[1], node[0]):
                seen.add(node)
                todo.append(node)
    return tuple(sorted(seen))


def negative_copies_to_keep(sets, dropped, present):
    """How many copies of each set of identical negative lines to keep (owner decision A of 2026-10-07, "fix the
    voids"). In a family (see family) that has payments, an identical negative copy is dropped only together with an
    identical positive copy of the same family that copies_to_keep drops, so a payment, void and reissue family keeps
    its raw net; positive lines are not changed. A family without payments keeps its identical copies once (rule 2).
    sets: [(order, reversal, amount negated (> 0), fiscal year, n)], one per set of n >= 2 identical negative lines,
    order being the set's lowest row id (or its raw line where the source has no row id); dropped: {(reversal,
    amount, fiscal year): positive copies dropped}. Within a family, the sets in order of (fiscal year, order) pair
    their copies with the family's dropped positive copies until none is left.
    Returns ({order: copies kept}, families where a set keeps more than one copy)."""
    families = collections.defaultdict(list)
    for order, reversal, amount, fy, n in sets:
        families[(reversal, amount, family(reversal, amount, fy, present))].append((fy, order, n))
    keep, touched = {}, 0
    for (reversal, amount, nodes), members in families.items():
        payments = [y for sign, y in nodes if sign > 0]
        left = sum(dropped.get((reversal, amount, y), 0) for y in payments)
        more = False
        for fy, order, n in sorted(members):
            drop = min(n - 1, left) if payments else n - 1
            left -= drop if payments else 0
            keep[order] = n - drop
            more |= drop < n - 1
        touched += more
    return keep, touched


def keep_identical(lines, ident, reversal, amount, fiscal_year, first):
    """Owner dedup rule of 2026-10-07 as corrected the same day ("drop identical lines, drop identical days"), on
    one source's raw lines, with the owner's fix of identical voids (decision A, 2026-10-07).

    1. Two lines are identical when every column the source publishes in its raw file is equal except the columns
       that only identify the row or the load (portal row ids, load timestamps). Document numbers the source
       publishes (voucher, invoice, check, PO and their line numbers) are content: lines that differ in one are
       different payments and are all kept. ident(line) returns those columns.
    2. Identical lines are kept once: the copies with the smallest first(line) (lowest row id).
    3. Void-safe: a set of n identical positive lines keeps min(n, reversals + 1) copies (copies_to_keep), so a
       payment, its void and an identical reissue keep their net. reversal(line) returns the reversal fields;
       amount(line) a Decimal; fiscal_year(line) an int.
    4. Identical voids: in a family that has payments (same reversal fields, amount up to sign, same or next fiscal
       year), an identical negative copy is dropped only together with an identical positive copy of the family
       that rule 3 drops (negative_copies_to_keep); a negative-only family keeps its identical copies once (rule 2).
    A doubled day is a set of identical lines, so it is covered. Returns (kept lines in input order, stats)."""
    groups = collections.defaultdict(list)
    for i, line in enumerate(lines):
        groups[ident(line)].append(i)
    reversals, present = collections.defaultdict(set), set()
    for key, members in groups.items():
        line = lines[members[0]]
        a = amount(line)
        if a < 0:
            reversals[(reversal(line), -a, fiscal_year(line))].add(key)
        if a:
            present.add((reversal(line), abs(a), fiscal_year(line), 1 if a > 0 else -1))
    keep, dropped, negative = {}, collections.Counter(), []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda i: (first(lines[i]), i))
        line = lines[members[0]]
        a, fy = amount(line), fiscal_year(line)
        if a < 0:
            negative.append(((first(line), members[0]), reversal(line), -a, fy, len(members)))
            continue
        keep[members[0]] = copies_to_keep(len(members), a, reversal(line), fy, reversals)
        dropped[(reversal(line), a, fy)] += len(members) - keep[members[0]]
    kept_negative, touched = negative_copies_to_keep(negative, dropped, lambda *node: node in present)
    keep.update({i: n for (_, i), n in kept_negative.items()})
    drop, stats = set(), new_stats()
    stats["fix_families"] = touched
    for key, members in groups.items():
        if len(members) < 2:
            continue
        drop.update(members[keep[members[0]]:])
        count(stats, len(members), keep[members[0]], amount(lines[members[0]]))
    return [line for i, line in enumerate(lines) if i not in drop], stats


def new_stats():
    return {"sets": 0, "lines": 0, "dollars": decimal.Decimal(0), "void_sets": 0, "void_kept": 0,
            "void_dollars": decimal.Decimal(0), "fix_sets": 0, "fix_kept": 0, "fix_dollars": decimal.Decimal(0),
            "fix_families": 0}


def count(stats, n, keep, amount):
    """Add one set of n identical lines, of which keep are kept, to the stats (copies kept beyond the first: void
    rule for positive sets, void fix for negative sets)."""
    if keep < n:
        stats["sets"] += 1
        stats["lines"] += n - keep
        stats["dollars"] += (n - keep) * amount
    if keep > 1:
        rule = "void" if amount > 0 else "fix"
        stats[f"{rule}_sets"] += 1
        stats[f"{rule}_kept"] += keep - 1
        stats[f"{rule}_dollars"] += (keep - 1) * amount


def dropped_text(stats):
    return (f"{stats['lines']} identical lines dropped (${stats['dollars']:,.2f}, {stats['sets']} sets); the void "
            f"rule kept {stats['void_kept']} copies (${stats['void_dollars']:,.2f}, {stats['void_sets']} sets); the "
            f"void fix kept {stats['fix_kept']} negative copies (${stats['fix_dollars']:,.2f}, {stats['fix_sets']} "
            f"sets, {stats['fix_families']} families)")


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
