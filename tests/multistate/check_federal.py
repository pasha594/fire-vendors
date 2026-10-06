"""Recompute the federal layer from raw files and check config/states/<st>/ and data/states/<st>/ match.

    python3 tests/multistate/check_federal.py [OH CA ID TX]
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "pipeline" / "sources"))
import common  # noqa: E402


def check(st):
    registry = common.read_csv_text(common.read_gz(common.latest_raw(st, "usfa") / "registry.csv.gz").decode("utf-8-sig"))
    agencies = common.read_config(st, "agencies.csv")
    assert len(agencies) == len(registry), f"{st}: {len(agencies)} agencies vs {len(registry)} registry rows"
    assert {a["usfa_fdid"] for a in agencies} == {r["FDID"].strip() for r in registry}, f"{st}: FDIDs differ"
    assert sum(int(a["career"]) for a in agencies) == sum(int(r["Active Firefighters - Career"] or 0) for r in registry)

    awards = json.loads(common.read_gz(common.latest_raw(st, "openfema") / "firefighter_grants.json.gz"))
    matched = {r["fema_recipient"]: r["agency_id"] for r in common.read_config(st, "grant_recipients.csv")}
    unmatched = {r["fema_recipient"] for r in common.read_config(st, "grant_recipients_unmatched.csv")}
    assert not set(matched) & unmatched, f"{st}: recipient both matched and unmatched"
    assert set(matched) | unmatched == {g["vendorName"] for g in awards}, f"{st}: recipients missing"
    expect = collections.Counter()
    for g in awards:
        if g["vendorName"] in matched:
            expect[matched[g["vendorName"]]] += g["awardAmount"] or 0
    got = collections.Counter()
    for g in common.read_data_csv(common.data_dir(st) / "grants.csv"):
        got[g["agency_id"]] += float(g["amount"] or 0)
    assert {k: round(v) for k, v in expect.items()} == {k: round(v) for k, v in got.items()}, f"{st}: grant totals differ"

    out = json.loads((common.data_dir(st) / "agencies.json").read_text())
    ids = {a["id"] for a in agencies} | {a["id"] for a in common.read_config(st, "agencies_added.csv")}
    assert {a["id"] for a in out["agencies"]} == ids, f"{st}: agencies.json ids differ from config"
    assert all(a["coverage"] in (1, 2, 3, 4) for a in out["agencies"])
    print(f"{st}: ok ({len(agencies)} registry agencies, {len(got)} with grants, ${sum(got.values()):,.0f})")


if __name__ == "__main__":
    for st in [s.upper() for s in sys.argv[1:]] or common.STATES:
        check(st)
