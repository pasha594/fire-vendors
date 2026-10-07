"""Helpers shared by the Texas city checkbook adapters (tx_houston, tx_austin, tx_dallas). Not an adapter itself.

tx_dir does not use drop_identical: identical DIR lines inside one monthly report are kept as real repeat purchases
(owner decision 2 of 2026-10-06, the one exception to the dedup rule of 2026-10-07). tx_cpa writes totals only.
"""
import decimal

import common


def drop_identical(rows, table="transactions.csv.gz"):
    """Owner decision of 2026-10-07 (dedup rule): drop identical lines and identical (doubled) days.

    rows: one source's normalized rows, in the adapter's deterministic order (raw file order). Two rows are
    identical when every column but source_record_id (the source's own row, document, invoice or line ids) is
    equal: agency, fiscal year, posting date, payee as published, description, account, published category and
    amount. The first row of each set is kept, the rest dropped. A day loaded twice is a set of identical rows, so
    it is covered; rows without a posting date compare on fiscal year (both are columns); a negative row (a
    reversal) is never identical to the payment it reverses (the amount differs).
    Returns (kept rows, {"groups": sets with a dropped row, "lines": rows dropped, "dollars": Decimal dropped})."""
    fields = [f for f in common.TABLES[table] if f not in ("source", "source_record_id")]
    seen, groups, keep, lines, dollars = set(), set(), [], 0, decimal.Decimal(0)
    for r in rows:
        key = tuple(str(r.get(f) if r.get(f) is not None else "") for f in fields)
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
