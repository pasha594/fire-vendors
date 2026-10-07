"""Helpers shared by the Texas city checkbook adapters (tx_houston, tx_austin, tx_dallas). Not an adapter itself.

tx_dir does not use dedup: identical DIR lines inside one monthly report are kept as real repeat purchases (owner
decision 2 of 2026-10-06, the one exception to the identical-line rule of 2026-10-07); it only drops lines re-reported
in a later month. tx_cpa writes totals only.
"""
import collections
import decimal


def dedup(records, row_ids, reversal_keys, amount_field, fy_field):
    """Owner rule of 2026-10-07 as corrected the same day ("drop identical lines, drop identical days"), on the raw
    records of one source.

    records: the raw lines as published (dicts of raw column -> value), in the order that decides which copy is kept
    (lowest portal row id first, or file order when the file has no row id).
    row_ids: the raw columns that only identify the row or the load (portal row id, load or extract stamps); every
    other raw column, document numbers included (voucher, invoice, check, PO and line numbers), is content.

    1. Two lines are identical when every raw column but row_ids is equal (a column absent from one line and present
       in the other differs). A day loaded twice is a set of identical lines, so it is covered.
    2. Of each set of identical lines the first in records order is kept.
    3. Void-safe: a set of n identical positive lines keeps min(n, reversals + 1) lines, where reversals counts the
       exact reversals of that line: lines equal in every reversal_keys column with the amount negated, in the same or
       the next fiscal year; reversals identical among themselves count once. A set of negative or zero lines keeps one.

    Returns (indices of records to drop, stats): stats has "sets" (identical sets with a dropped line), "lines" and
    "dollars" (Decimal) dropped, "negative_lines" and "negative_dollars" among them, and "void_lines" and
    "void_dollars", the identical positive copies the void rule keeps."""
    content = [tuple(sorted((k, v) for k, v in r.items() if k not in row_ids)) for r in records]
    amount = [decimal.Decimal(str(r[amount_field])) for r in records]
    groups = collections.defaultdict(list)
    reversals = collections.defaultdict(set)  # (reversal key values, amount reversed, fiscal year) -> distinct lines
    for i, r in enumerate(records):
        groups[content[i]].append(i)
        if amount[i] < 0:
            reversals[(tuple(r.get(k) for k in reversal_keys), -amount[i], int(r[fy_field]))].add(content[i])
    drop = set()
    stats = collections.Counter()
    stats.update(dollars=decimal.Decimal(0), negative_dollars=decimal.Decimal(0), void_dollars=decimal.Decimal(0))
    for idx in groups.values():
        if len(idx) < 2:
            continue
        i = idx[0]
        keep = 1
        if amount[i] > 0:
            key, fy = tuple(records[i].get(k) for k in reversal_keys), int(records[i][fy_field])
            n_rev = len(reversals.get((key, amount[i], fy), set()) | reversals.get((key, amount[i], fy + 1), set()))
            keep = min(len(idx), n_rev + 1)
            stats["void_lines"] += keep - 1
            stats["void_dollars"] += amount[i] * (keep - 1)
        dropped = idx[keep:]
        if dropped:
            drop.update(dropped)
            stats["sets"] += 1
            stats["lines"] += len(dropped)
            stats["dollars"] += amount[i] * len(dropped)
            if amount[i] < 0:
                stats["negative_lines"] += len(dropped)
                stats["negative_dollars"] += amount[i] * len(dropped)
    return drop, stats


def money(d):
    return f"{'-' if d < 0 else ''}${abs(d):,.2f}"


def dropped_text(stats):
    return (f"identical lines (owner rule of 2026-10-07, every raw column but row ids): {stats['lines']} dropped "
            f"({money(stats['dollars'])} net, {stats['sets']} sets; {stats['negative_lines']} of them negative, "
            f"{money(stats['negative_dollars'])}); void rule keeps {stats['void_lines']} identical positive copies "
            f"({money(stats['void_dollars'])})")
