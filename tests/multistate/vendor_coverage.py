"""Vendor-map coverage of a state's purchasing dollars, shared by tests/multistate/check_<st>.py.

A payee is classified the way pipeline/build.py classifies a vendor key: its config/vendor_map.csv row first,
otherwise the first matching pattern of config/vendor_rules.csv and then config/keyword_rules.csv, otherwise it is
unmapped. The key is common.norm(payee as published). Reading the map also checks it (map_problems): a repeated or
unsorted name_key, an unknown category or confidence, or an empty vendor fails every state check.

Purchasing dollars: net spend per payee key over the state's transactions, for payees with net spend above zero whose
category is a purchasing category (config/categories.csv) or that are unmapped. Covered: payees mapped to a real
purchasing category (not 'unclassified').
"""
import collections
import csv
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config"


def _rows(name):
    with open(CONFIG / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


MAP_COLUMNS = ["name_key", "vendor", "category", "confidence"]


def map_problems(rows, fields, cat_ids):
    """Problems of config/vendor_map.csv that pipeline/build.py would not report: a repeated name_key (the later
    row silently wins), keys out of order, an unknown category or confidence, an empty vendor. The same checks as
    pipeline/sources/merge_vendor_maps.py --check, so every state check fails on a broken shared map."""
    out = [] if fields == MAP_COLUMNS else [f"columns {fields}, expected {MAP_COLUMNS}"]
    keys = [r["name_key"] for r in rows]
    if keys != sorted(keys):
        out.append("not sorted by name_key")
    out += [f"name_key {k!r} {n} times" for k, n in sorted(collections.Counter(keys).items()) if n > 1]
    out += [f"unknown category {r['category']!r} for {r['name_key']!r}" for r in rows if r["category"] not in cat_ids]
    out += [f"unknown confidence {r['confidence']!r} for {r['name_key']!r}" for r in rows
            if r["confidence"] not in ("high", "medium", "low")]
    out += [f"empty vendor for {r['name_key']!r}" for r in rows if not (r["vendor"] or "").strip()]
    return out


class Classifier:
    def __init__(self):
        with open(CONFIG / "vendor_map.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.purchasing = {c["id"]: c["purchasing"] == "yes" for c in _rows("categories.csv")}
        problems = map_problems(rows, reader.fieldnames, set(self.purchasing))
        assert not problems, f"config/vendor_map.csv: {problems[:5]} (see merge_vendor_maps.py --check)"
        self.vendor_map = {r["name_key"]: (r["vendor"], r["category"]) for r in rows}
        self.rules = [(r["category"], re.compile(r["pattern"]), (r.get("vendor") or "").strip())
                      for r in _rows("vendor_rules.csv") + _rows("keyword_rules.csv")]
        self._cache = {}

    def classify(self, key):
        """(vendor or None, category or None, how): how is 'map', 'rule' or None (unmapped)."""
        if key not in self._cache:
            if key in self.vendor_map:
                self._cache[key] = self.vendor_map[key] + ("map",)
            else:
                hit = next(((v or None, c, "rule") for c, rx, v in self.rules if rx.search(key)), None)
                self._cache[key] = hit or (None, None, None)
        return self._cache[key]

    def coverage(self, spend):
        """spend: {payee key: net dollars}. Returns a dict of dollar sums and shares."""
        out = {"purchasing": 0, "real": 0, "unclassified": 0, "by_map": 0, "by_rule": 0, "unmapped": 0}
        for key, v in spend.items():
            _, cat, how = self.classify(key)
            if v <= 0 or (cat and not self.purchasing[cat]):
                continue
            out["purchasing"] += v
            if not cat:
                out["unmapped"] += v
            elif cat == "unclassified":
                out["unclassified"] += v
            else:
                out["real"] += v
                out["by_" + how] += v
        p = out["purchasing"]
        out["share_real"] = out["real"] / p if p else 1
        out["share_mapped"] = (out["real"] + out["unclassified"]) / p if p else 1
        return out
