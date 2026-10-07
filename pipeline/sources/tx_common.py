"""Helpers shared by the Texas city checkbook adapters (tx_houston, tx_austin, tx_dallas). Not an adapter itself.

tx_dir does not use dedup: identical DIR lines inside one monthly report are kept as real repeat purchases (owner
decision 2 of 2026-10-06, the one exception to the identical-line rule of 2026-10-07); it only drops lines re-reported
in a later month. tx_cpa writes totals only.
"""
import collections
import decimal


def family(key, amount, fy, present):
    """The family of a negative line of fiscal year fy (owner decision A of 2026-10-07): the lines with the same
    reversal_keys values and the same amount up to sign (amount > 0 here), a payment of fiscal year y being linked to
    the negative lines of y and y + 1 (the void rule's "same or next fiscal year"); lines linked through a chain of
    such links are one family. present: {(key, amount, fiscal year, sign)} of the source's lines (sign 1 payment, -1
    negative). Returns the family's (sign, fiscal year) nodes, sorted."""
    todo, seen = [(-1, fy)], {(-1, fy)}
    while todo:
        sign, y = todo.pop()
        for node in ([(1, y - 1), (1, y)] if sign < 0 else [(-1, y), (-1, y + 1)]):
            if node not in seen and (key, amount, node[1], node[0]) in present:
                seen.add(node)
                todo.append(node)
    return tuple(sorted(seen))


def dedup(records, row_ids, reversal_keys, amount_field, fy_field):
    """Owner rule of 2026-10-07 as corrected the same day ("drop identical lines, drop identical days"), with the
    owner's fix of identical voids (decision A of 2026-10-07), on the raw records of one source.

    records: the raw lines as published (dicts of raw column -> value), in the order that decides which copy is kept
    (lowest portal row id first, or file order when the file has no row id).
    row_ids: the raw columns that only identify the row or the load (portal row id, load or extract stamps); every
    other raw column, document numbers included (voucher, invoice, check, PO and line numbers), is content.

    1. Two lines are identical when every raw column but row_ids is equal (a column absent from one line and present
       in the other differs). A day loaded twice is a set of identical lines, so it is covered.
    2. Of each set of identical lines the first in records order is kept.
    3. Void-safe: a set of n identical positive lines keeps min(n, reversals + 1) lines, where reversals counts the
       exact reversals of that line: lines equal in every reversal_keys column with the amount negated, in the same or
       the next fiscal year; reversals identical among themselves count once. A set of zero lines keeps one.
    4. Identical voids (decision A): a set of n identical negative lines keeps one copy (rule 2) when its family (see
       family: same reversal_keys, amount up to sign, same or next fiscal year) has no payments; in a family that has
       payments a negative copy is dropped only together with an identical positive copy of the family that rule 3
       drops, so a payment, void and reissue family keeps its raw net. The family's sets, in order of (fiscal year,
       first copy), take the dropped positive copies until none is left. Positive lines are not changed by 4.

    Returns (indices of records to drop, stats): stats has "sets" (identical sets with a dropped line), "lines" and
    "dollars" (Decimal) dropped, "negative_lines" and "negative_dollars" among them, "void_lines" and "void_dollars",
    the identical positive copies the void rule keeps, and "fix_lines", "fix_dollars" and "fix_families", the
    identical negative copies the void fix keeps beyond the first and the families where it keeps one."""
    content = [tuple(sorted((k, v) for k, v in r.items() if k not in row_ids)) for r in records]
    amount = [decimal.Decimal(str(r[amount_field])) for r in records]
    rkey = [tuple(r.get(k) for k in reversal_keys) for r in records]
    fyear = [int(r[fy_field]) for r in records]
    groups = collections.defaultdict(list)
    reversals = collections.defaultdict(set)  # (reversal key values, amount reversed, fiscal year) -> distinct lines
    present = set()  # (reversal key values, amount up to sign, fiscal year, sign) of every line
    for i in range(len(records)):
        groups[content[i]].append(i)
        if amount[i] < 0:
            reversals[(rkey[i], -amount[i], fyear[i])].add(content[i])
        if amount[i]:
            present.add((rkey[i], abs(amount[i]), fyear[i], 1 if amount[i] > 0 else -1))
    keep = {}  # first index of a set -> copies kept
    gone = collections.Counter()  # (reversal key values, amount, fiscal year) -> positive copies rule 3 drops
    families = collections.defaultdict(list)  # (key, amount, family nodes) -> [(fiscal year, first index, n)]
    for idx in groups.values():
        if len(idx) < 2:
            continue
        i = idx[0]
        if amount[i] > 0:
            n_rev = len(reversals.get((rkey[i], amount[i], fyear[i]), set())
                        | reversals.get((rkey[i], amount[i], fyear[i] + 1), set()))
            keep[i] = min(len(idx), n_rev + 1)
            gone[(rkey[i], amount[i], fyear[i])] += len(idx) - keep[i]
        elif amount[i] < 0:
            nodes = family(rkey[i], -amount[i], fyear[i], present)
            families[(rkey[i], -amount[i], nodes)].append((fyear[i], i, len(idx)))
        else:
            keep[i] = 1
    stats = collections.Counter()
    stats.update(dollars=decimal.Decimal(0), negative_dollars=decimal.Decimal(0), void_dollars=decimal.Decimal(0),
                 fix_dollars=decimal.Decimal(0))
    for (key, a, nodes), members in sorted(families.items(), key=lambda kv: min(m[:2] for m in kv[1])):
        payments = [y for sign, y in nodes if sign > 0]
        pool = sum(gone[(key, a, y)] for y in payments)
        more = False
        for _, i, n in sorted(members):
            n_drop = min(n - 1, pool) if payments else n - 1
            if payments:
                pool -= n_drop
            keep[i] = n - n_drop
            more |= keep[i] > 1
        stats["fix_families"] += more
    drop = set()
    for idx in groups.values():
        if len(idx) < 2:
            continue
        i = idx[0]
        if keep[i] > 1:
            rule = "void" if amount[i] > 0 else "fix"
            stats[f"{rule}_lines"] += keep[i] - 1
            stats[f"{rule}_dollars"] += amount[i] * (keep[i] - 1)
        dropped = idx[keep[i]:]
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
            f"({money(stats['void_dollars'])}); void fix keeps {stats['fix_lines']} identical negative copies "
            f"({money(stats['fix_dollars'])}, {stats['fix_families']} families)")
