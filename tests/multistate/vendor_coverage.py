"""Vendor-map coverage of a state's purchasing dollars, shared by tests/multistate/check_<st>.py.

A payee is classified the way pipeline/build.py classifies a vendor key: its config/vendor_map.csv row first,
otherwise the first matching pattern of config/vendor_rules.csv and then config/keyword_rules.csv, otherwise it is
unmapped. The key is common.norm(payee as published).

Purchasing dollars: net spend per payee key over the state's transactions, for payees with net spend above zero whose
category is a purchasing category (config/categories.csv) or that are unmapped. Covered: payees mapped to a real
purchasing category (not 'unclassified').
"""
import csv
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config"


def _rows(name):
    with open(CONFIG / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Classifier:
    def __init__(self):
        self.vendor_map = {r["name_key"]: (r["vendor"], r["category"]) for r in _rows("vendor_map.csv")}
        self.rules = [(r["category"], re.compile(r["pattern"]), (r.get("vendor") or "").strip())
                      for r in _rows("vendor_rules.csv") + _rows("keyword_rules.csv")]
        self.purchasing = {c["id"]: c["purchasing"] == "yes" for c in _rows("categories.csv")}
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
