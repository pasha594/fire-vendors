"""Build data/stack.json and data/stack-tail.json, the data of the vendor page (index.html), from the build output.

Reads data/index.json and data/<st>.json (written by pipeline/build.py), config/page_sections.csv and
config/vendor_logos.csv. Run it after pipeline/build.py (build.py runs it at the end).

data/stack.json (the first load, with data/index.json):
- built: the build date of data/index.json (the page refuses files from another build)
- sections: [[category id, "fire" or "other"]] in page order (config/page_sections.csv)
- agencies: ids of the agencies with lines in purchasing categories
- vendors: the vendors used by two agencies or more, then (in stack-tail.json) the rest; each
  [name, category id, flags, domain, logo path, logo size in pixels], trailing nulls left out. The vendor's id is the slug of its name (as in pipeline/build.py)
  unless ids gives it. category: the purchasing category with the largest net amount; flags: 1 NERIS partner,
  2 not a merchant: card issuers, banks and payment services (config/card_programs.csv, except card lines that
  name the merchant, 'PCARD - <merchant>'), and payees whose own category (by net amount) is no vendor named,
  individuals, payroll, finance or payments to other governments. Those are kept out of vendor lists and
  stacks and only counted in a note.
- ids: {vendor index: id} where the id is not the slug of the name
- lines: [agency index, vendor index, category index, fiscal year, net amount, fiscal year, net amount, ...]:
  the net amount one agency paid one vendor (by id) in one purchasing category in each fiscal year, summed over
  payee names and rounded to the cent, years ascending, years that net to zero left out
- tail_sums: [agency index, category index, merchants' net, merchants with a positive year, others' net] per agency
  and category with lines of vendors in stack-tail.json, and per agency over all categories (category index -1),
  so totals and counts are exact before it loads (each of those vendors is used by one agency only, so their
  counts add up across agencies). A positive year: net over $0.005 in one fiscal year and category.
- tail: {file, bytes_gz, vendors}: data/stack-tail.json

data/stack-tail.json (loaded after the first view): {built, vendors, ids, lines, vmap}; vendors used by one
agency (their indexes follow those of stack.json) and their lines; vmap: per state, the vendor index (of both
files) for each vendor index of data/<st>.json (-1: no purchasing lines), so the page reads
data/<st>-payments.json and data/<st>-items.json without data/<st>.json.

Standard library only; two runs on the same inputs write the same bytes.

    python3 pipeline/build_stack.py
"""

import collections
import csv
import gzip
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = ROOT / "config"
NOT_MERCHANT_CATEGORIES = {"placeholder", "individuals", "payroll", "finance", "government"}
CARD_LINE_MERCHANT = re.compile(r"^P-?CARD\s*-\s*\S", re.I)   # 'PCARD - NORTH RIDGE FIRE EQUIPMEN': the merchant is named
STACK_MAX_GZ = 1_000_000                                     # data/stack.json, gzipped (the first load)
TAIL_MAX_GZ = 2_000_000                                      # data/stack-tail.json, gzipped


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def dumps(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()


def gz_size(body):
    return len(gzip.compress(body, compresslevel=9, mtime=0))


def build():
    """(stack, tail, report) as dicts."""
    index = json.loads((DATA / "index.json").read_bytes())
    built = index["meta"]["built"]
    categories = index["categories"]
    cat_pos = {c["id"]: i for i, c in enumerate(categories)}
    purchasing = {i for i, c in enumerate(categories) if c["purchasing"] == "yes"}
    purchasing_ids = {categories[i]["id"] for i in purchasing}

    sections = [[r["category"], r["section"]] for r in read_csv(CONFIG / "page_sections.csv")]
    bad = [c for c, s in sections if c not in purchasing_ids or s not in ("fire", "other")]
    missing = sorted(purchasing_ids - {c for c, _ in sections})
    if bad or missing:
        sys.exit(f"config/page_sections.csv: unknown or non-purchasing categories {bad}, missing {missing}")

    # (agency id, vendor id, category index) -> {year: net}; vendor id -> facts from the state files
    net = collections.defaultdict(lambda: collections.defaultdict(float))
    vname, neris, own_cat = {}, {}, collections.defaultdict(collections.Counter)
    state_vendors = {}
    for st in index["meta"]["states_order"]:
        f = index["meta"]["states"][st]["files"]["rows"]
        d = json.loads((ROOT / f).read_bytes())
        if d.get("built") != built:
            sys.exit(f"{f} (built {d.get('built')}) is not from the build of data/index.json ({built})")
        V = d["vendors"]
        state_vendors[st] = [v["id"] for v in V]
        for a, vi, y, ci, x, _ in d["rows"]:
            if ci not in purchasing:
                continue
            v = V[vi]
            net[(a, v["id"], ci)][y] += x
            vname.setdefault(v["id"], v["name"])
            neris.setdefault(v["id"], bool(v.get("neris")))
            own_cat[v["id"]][v["category"]] += abs(x)

    # Years that net to zero (to the cent) are left out, then pairs with no year left
    cells = {}
    for k, ys in net.items():
        ys = {y: round(x, 2) for y, x in sorted(ys.items()) if abs(round(x, 2)) >= 0.01}
        if ys:
            cells[k] = ys

    by_cat = collections.defaultdict(collections.Counter)   # vendor id -> category index -> net
    users = collections.defaultdict(set)                      # vendor id -> agencies
    for (a, v, c), ys in cells.items():
        by_cat[v][c] += sum(ys.values())
        users[v].add(a)

    logos = {}
    if (CONFIG / "vendor_logos.csv").exists():
        for r in read_csv(CONFIG / "vendor_logos.csv"):
            logo = (r.get("logo") or "").strip()
            logo = "" if logo == "-" else logo                    # checked by hand: no usable logo
            if logo and not (ROOT / logo).is_file():
                sys.exit(f"config/vendor_logos.csv: {r['vendor_id']}: {logo} does not exist")
            px = int(r["logo_px"]) if (r.get("logo_px") or "").strip().isdigit() else None
            logos[r["vendor_id"]] = ((r.get("domain") or "").strip() or None, logo or None, px if logo else None)

    # Vendors used by two agencies or more first, then the rest; each part by total net amount, largest first
    total = {v: round(sum(by_cat[v].values()), 2) for v in by_cat}
    shared = sorted((v for v in by_cat if len(users[v]) > 1), key=lambda v: (-total[v], v))
    single = sorted((v for v in by_cat if len(users[v]) == 1), key=lambda v: (-total[v], v))
    vids = shared + single
    vpos = {v: i for i, v in enumerate(vids)}

    cards = [re.compile(r["pattern"], re.I) for r in read_csv(CONFIG / "card_programs.csv")]

    def merchant(v):
        if any(rx.search(vname[v]) for rx in cards) and not CARD_LINE_MERCHANT.search(vname[v]):
            return False
        return max(own_cat[v].items(), key=lambda kv: (kv[1], kv[0]))[0] not in NOT_MERCHANT_CATEGORIES

    def vendor(v):
        main_cat = max(by_cat[v].items(), key=lambda kv: (kv[1], -kv[0]))[0]
        flags = (1 if neris[v] else 0) | (0 if merchant(v) else 2)
        domain, logo, px = logos.get(v, (None, None, None))
        out = [vname[v], categories[main_cat]["id"], flags, domain, logo, px]
        while out[-1] is None:
            out.pop()
        return out

    used = {a for a, _, _ in cells}
    agencies = [a["id"] for a in index["agencies"] if a["id"] in used]          # in the order of data/index.json
    apos = {a: i for i, a in enumerate(agencies)}
    lines = ([], [])                                          # (stack.json, stack-tail.json)
    for (a, v, c), ys in sorted(cells.items(), key=lambda kv: (apos[kv[0][0]], vpos[kv[0][1]], kv[0][2])):
        row = [apos[a], vpos[v], c]
        for y, x in ys.items():
            row += [y, int(x) if x == int(x) else x]
        lines[vpos[v] >= len(shared)].append(row)

    sums = collections.defaultdict(lambda: [0.0, 0, 0.0])    # (agency, category) -> merchants' net, merchants, others' net
    flags = {v: vendor(v)[2] for v in single}
    positive = collections.defaultdict(set)                   # agency -> merchants of stack-tail.json with a positive year
    for (a, v, c), ys in cells.items():
        if vpos[v] < len(shared):
            continue
        for o in (sums[(a, c)], sums[(a, -1)]):
            if flags[v] & 2:
                o[2] += sum(ys.values())
            elif o is sums[(a, c)]:
                o[0] += sum(ys.values())
                o[1] += any(x > 0.005 for x in ys.values())
            else:
                o[0] += sum(ys.values())
                if any(x > 0.005 for x in ys.values()):
                    positive[a].add(v)
    for (a, c), o in sums.items():
        if c == -1:
            o[1] = len(positive[a])
    num = lambda x: int(round(x, 2)) if round(x, 2) == int(round(x, 2)) else round(x, 2)  # noqa: E731
    tail_sums = [[apos[a], c, num(o[0]), o[1], num(o[2])] for (a, c), o in sorted(sums.items(), key=lambda kv: (apos[kv[0][0]], kv[0][1]))]

    ids = lambda part, off: {str(i + off): v for i, v in enumerate(part) if slug(vname[v]) != v}  # noqa: E731
    tail = {"built": built, "vendors": [vendor(v) for v in single], "ids": ids(single, len(shared)), "lines": lines[1],
            "vmap": {st: [vpos.get(v, -1) for v in vs] for st, vs in state_vendors.items()}}
    tail_body = dumps(tail)
    stack = {"built": built, "sections": sections, "agencies": agencies, "vendors": [vendor(v) for v in shared],
             "ids": ids(shared, 0), "lines": lines[0], "tail_sums": tail_sums,
             "tail": {"file": "data/stack-tail.json", "bytes_gz": gz_size(tail_body), "vendors": len(single)}}
    report = {"agencies": len(agencies), "shared": len(shared), "single": len(single),
              "not_merchants": sum(1 for v in vids if vendor(v)[2] & 2), "logos": sum(1 for v in vids if logos.get(v, (0, 0, 0))[1]),
              "lines": [len(lines[0]), len(lines[1])]}
    return stack, tail_body, report


def main():
    stack, tail_body, r = build()
    body = dumps(stack)
    problems = []
    if gz_size(body) > STACK_MAX_GZ:
        problems.append(f"data/stack.json is {gz_size(body):,} bytes gzipped, over {STACK_MAX_GZ:,}")
    if gz_size(tail_body) > TAIL_MAX_GZ:
        problems.append(f"data/stack-tail.json is {gz_size(tail_body):,} bytes gzipped, over {TAIL_MAX_GZ:,}")
    if problems:
        sys.exit("stack build failed, nothing written: " + "; ".join(problems))
    (DATA / "stack.json").write_bytes(body)
    (DATA / "stack-tail.json").write_bytes(tail_body)
    for p, b in (("stack.json", body), ("stack-tail.json", tail_body)):
        print(f"data/{p}: {len(b) / 1e6:.2f} MB ({gz_size(b) / 1e6:.2f} MB gzipped)")
    print(f"{r['agencies']} agencies; {r['shared']} vendors used by two agencies or more, {r['single']} by one "
          f"({r['not_merchants']} not merchants, {r['logos']} with logos); lines {r['lines'][0]} + {r['lines'][1]}")


if __name__ == "__main__":
    main()
