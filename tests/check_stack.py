"""Checks of data/stack.json and data/stack-tail.json (pipeline/build_stack.py) against the build output.

    python3 tests/check_stack.py

1. Both files are from the build of data/index.json; the stack build run again writes the same bytes.
2. Every line of both files, summed by agency, vendor id, category and fiscal year, equals the net amount of the
   purchasing rows of data/<st>.json to the cent, and no such amount is missing.
3. Vendors: ids (slug of the name, or ids), stack.json has the vendors more than one agency used and
   stack-tail.json the rest; categories, NERIS flags and the not-a-merchant flag as pipeline/build_stack.py defines
   them; every logo file exists, is an image and is not SVG, and every file in logos/ is a logo of
   config/vendor_logos.csv.
4. tail_sums equal the sums of the lines of stack-tail.json.
5. vmap names, for every vendor index of data/<st>.json, the vendor with the same id (or -1 for vendors without
   purchasing lines).
6. Per scope (all states and each state), per category, the vendors and agencies with a positive year and the
   net amount equal the precomputed default table of data/index.json (home), which pipeline/build.py computes
   from the state files.
"""

import collections
import csv
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import build_stack  # noqa: E402

failures = 0
checks = 0


def ok(cond, msg):
    global failures, checks
    checks += 1
    if not cond:
        failures += 1
        print("FAIL " + msg)


def main():
    I = json.loads((ROOT / "data/index.json").read_bytes())
    S = json.loads((ROOT / "data/stack.json").read_bytes())
    T = json.loads((ROOT / "data/stack-tail.json").read_bytes())
    built = I["meta"]["built"]
    cats = I["categories"]
    purchasing = {i for i, c in enumerate(cats) if c["purchasing"] == "yes"}

    # 1. Same build; rebuilding writes the same bytes
    ok(S["built"] == built and T["built"] == built, f"built: stack {S['built']}, tail {T['built']}, index {built}")
    stack, tail_body, _ = build_stack.build()
    ok(build_stack.dumps(stack) == (ROOT / "data/stack.json").read_bytes(), "data/stack.json differs from a new stack build")
    ok(tail_body == (ROOT / "data/stack-tail.json").read_bytes(), "data/stack-tail.json differs from a new stack build")
    ok(S["tail"]["vendors"] == len(T["vendors"]), "tail.vendors does not match stack-tail.json")

    # 2. Lines against the state files
    expect = collections.defaultdict(float)
    state_vendors, own, names, neris = {}, collections.defaultdict(collections.Counter), {}, {}
    for st in I["meta"]["states_order"]:
        d = json.loads((ROOT / I["meta"]["states"][st]["files"]["rows"]).read_bytes())
        state_vendors[st] = d["vendors"]
        for a, vi, y, c, x, _ in d["rows"]:
            if c in purchasing:
                v = d["vendors"][vi]
                expect[(a, v["id"], c, y)] += x
                own[v["id"]][v["category"]] += abs(x)
                names.setdefault(v["id"], v["name"])
                neris.setdefault(v["id"], bool(v.get("neris")))
    vendors = S["vendors"] + T["vendors"]
    ids = {**S["ids"], **T["ids"]}
    vid = [ids.get(str(i)) or build_stack.slug(v[0]) for i, v in enumerate(vendors)]
    ok(len(set(vid)) == len(vid), "vendor ids are not unique")
    got = collections.defaultdict(float)
    for r in S["lines"] + T["lines"]:
        for k in range(3, len(r), 2):
            got[(S["agencies"][r[0]], vid[r[1]], r[2], r[k])] += r[k + 1]
    bad = [k for k in set(expect) | set(got) if abs(round(expect.get(k, 0), 2) - got.get(k, 0)) > 0.005]
    ok(not bad, f"{len(bad)} agency, vendor, category and year amounts differ from the state files, e.g. {bad[:3]}")
    ok(len(S["agencies"]) == len({k[0] for k, x in expect.items() if abs(round(x, 2)) >= 0.01}), "agencies list")

    # 3. Vendors
    users = collections.defaultdict(set)
    for r in S["lines"] + T["lines"]:
        users[r[1]].add(r[0])
    ok(all(len(users[i]) > 1 for i in range(len(S["vendors"]))), "a vendor of stack.json is used by one agency")
    ok(all(len(users[i]) == 1 for i in range(len(S["vendors"]), len(vendors))), "a vendor of stack-tail.json is used by more than one agency")
    cards = [re.compile(r["pattern"], re.I) for r in csv.DictReader(open(ROOT / "config/card_programs.csv", encoding="utf-8"))]
    by_cat = collections.defaultdict(collections.Counter)
    for r in S["lines"] + T["lines"]:
        by_cat[r[1]][r[2]] += sum(r[k + 1] for k in range(3, len(r), 2))
    wrong = []
    for i, v in enumerate(vendors):
        k = vid[i]
        v = v + [None] * (6 - len(v))                         # trailing nulls are left out
        main_cat = cats[max(by_cat[i].items(), key=lambda kv: (kv[1], -kv[0]))[0]]["id"]
        card = any(rx.search(names[k]) for rx in cards) and not build_stack.CARD_LINE_MERCHANT.search(names[k])
        own_main = max(own[k].items(), key=lambda kv: (kv[1], kv[0]))[0]
        merchant = not card and own_main not in build_stack.NOT_MERCHANT_CATEGORIES
        if v[0] != names[k] or v[1] != main_cat or bool(v[2] & 1) != neris[k] or bool(v[2] & 2) == merchant:
            wrong.append(k)
        if v[4]:
            p = ROOT / v[4]
            head = p.read_bytes()[:12] if p.is_file() else b""
            image = head[:8] == b"\x89PNG\r\n\x1a\n" or head[:4] == b"\x00\x00\x01\x00" or head[:3] == b"\xff\xd8\xff" \
                or head[:4] == b"GIF8" or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
            if not (v[4].startswith("logos/") and image):
                wrong.append(k + " (logo " + v[4] + ")")
    ok(not wrong, f"{len(wrong)} vendors with a wrong name, category, flag or logo, e.g. {wrong[:5]}")
    listed = {r["logo"] for r in csv.DictReader(open(ROOT / "config/vendor_logos.csv", encoding="utf-8"))}
    unused = sorted(f"logos/{f.name}" for f in (ROOT / "logos").iterdir() if f"logos/{f.name}" not in listed)
    ok(not unused, f"files in logos/ that config/vendor_logos.csv does not name: {unused[:5]}")

    # 4. tail_sums
    sums = collections.defaultdict(lambda: [0.0, 0, 0.0])
    pos_by_agency = collections.defaultdict(set)
    for r in T["lines"]:
        net = sum(r[k + 1] for k in range(3, len(r), 2))
        pos = any(r[k + 1] > 0.005 for k in range(3, len(r), 2))
        other = vendors[r[1]][2] & 2
        for c in (r[2], -1):
            o = sums[(r[0], c)]
            if other:
                o[2] += net
            else:
                o[0] += net
                if c != -1:
                    o[1] += pos
        if pos and not other:
            pos_by_agency[r[0]].add(r[1])
    for (a, c), o in sums.items():
        if c == -1:
            o[1] = len(pos_by_agency[a])
    have = {(a, c): (m, n, x) for a, c, m, n, x in S["tail_sums"]}
    bad = [k for k in set(sums) | set(have) if k not in have or k not in sums or abs(have[k][0] - sums[k][0]) > 0.01
           or have[k][1] != sums[k][1] or abs(have[k][2] - sums[k][2]) > 0.01]
    ok(not bad, f"{len(bad)} tail_sums rows differ from the lines of stack-tail.json, e.g. {bad[:3]}")

    # 5. vmap
    pos_of = {k: i for i, k in enumerate(vid)}
    for st, V in state_vendors.items():
        m = T["vmap"].get(st, [])
        ok(len(m) == len(V) and all(m[i] == pos_of.get(v["id"], -1) for i, v in enumerate(V)), f"vmap of {st}")

    # 6. The default tables of data/index.json
    for scope, H in I["home"].items():
        net = collections.defaultdict(float)
        ve, ag = collections.defaultdict(set), collections.defaultdict(set)
        for r in S["lines"] + T["lines"]:
            a = S["agencies"][r[0]]
            if scope != "ALL" and not a.startswith(scope + "-"):
                continue
            for k in range(3, len(r), 2):
                if H["from"] <= r[k] <= H["to"]:
                    net[r[2]] += r[k + 1]
                    if r[k + 1] > 0.005:
                        ve[r[2]].add(r[1])
                        ag[r[2]].add(r[0])
        for c, spend, _, nv, na, _, _ in H["cats"]:
            ok(abs(net[c] - spend) < 0.05 and len(ve[c]) == nv and len(ag[c]) == na,
               f"{scope} {cats[c]['id']}: {net[c]:.2f}, {len(ve[c])} vendors, {len(ag[c])} agencies; home {spend}, {nv}, {na}")
    print(f"{checks} checks, {failures} failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
