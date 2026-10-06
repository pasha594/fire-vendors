"""Federal layer for OH, CA, ID and TX: every USFA-registered fire department, plus OpenFEMA firefighter grants.

    python3 pipeline/sources/federal.py fetch [OH CA ID TX]
    python3 pipeline/sources/federal.py normalize [OH CA ID TX]

fetch      raw/<date>/<st>/usfa/registry.csv.gz and raw/<date>/<st>/openfema/firefighter_grants.json.gz
           (same endpoints as pipeline/fetch.py, which stays Utah-only)
normalize  config/states/<st>/agencies.csv            one row per registry department (id <ST>-<FDID>)
           config/states/<st>/grant_recipients.csv    FEMA recipient name -> agency id, strict matches only
           config/states/<st>/grant_recipients_unmatched.csv
           data/states/<st>/grants.csv                matched awards
           data/states/<st>/agencies.json             via common.assemble_agencies

Strict grant matching: the recipient name and the registry name are equal after spelling out abbreviations
(FD, VFD, FPD, ESD, DEPT, DIST, TWP, VOL, NO.) and dropping punctuation and a leading THE; or the recipient
name was cut at OpenFEMA's 40-character limit and exactly one registry name starts with it. A normalized name
that two registry departments share is never matched. "CITY OF X" recipients are not matched to "X Fire
Department": the grant may belong to the city, and the registry does not say which.
"""
import collections
import json
import re
import sys

import common

USFA_STATES = "https://apps.usfa.fema.gov/registry/api/lookups/states"
USFA_STATE_CSV = "https://apps.usfa.fema.gov/registry/api/download/state/{code}"
FEMA_GRANTS = "https://www.fema.gov/api/open/v1/NonDisasterAssistanceFirefighterGrants"

AGENCY_COLUMNS = ["id", "name", "kind", "county", "city", "usfa_fdid", "dept_type", "organization_type", "stations",
                  "career", "volunteer", "paid_per_call", "website", "grants"]


def fetch(states):
    codes = {s["shortDesc"]: s["code"] for s in json.loads(common.get(USFA_STATES))}
    for st in states:
        print(f"{st}: USFA registry")
        common.save_raw(st, "usfa", "registry.csv", common.get(USFA_STATE_CSV.format(code=codes[st])))
        print(f"{st}: OpenFEMA firefighter grants")
        rows, skip = [], 0
        while True:
            page = json.loads(common.get(FEMA_GRANTS, {"$filter": f"vendorState eq '{st}'", "$top": 1000, "$skip": skip}))
            page = page["NonDisasterAssistanceFirefighterGrants"]
            rows += page
            if len(page) < 1000:
                break
            skip += 1000
        common.save_raw(st, "openfema", "firefighter_grants.json", json.dumps(rows, indent=0).encode())
        print(f"  {len(rows)} awards")


def kind(name, org_type):
    """Department kind from the registry name and organization type (the registry has no finer field)."""
    n = name.upper()
    if not org_type.startswith("Local"):
        return org_type.split(" (")[0]  # State, Federal, Private or industrial, Contract, ...
    if re.search(r"\bESD\b|EMERGENCY SERVICES? DIST", n):
        return "Emergency services district"
    if re.search(r"\bFIRE (PROTECTION )?(DISTRICT|DIST)\b|\bFPD\b|\bFIRE AUTHORITY\b|\bJOINT FIRE\b|\bFIRE (AND|&) (RESCUE|EMS) DISTRICT\b", n):
        return "Fire district"
    if re.search(r"\bTOWNSHIP\b|\bTWP\b", n):
        return "Township fire department"
    if re.search(r"\bCOUNTY\b", n):
        return "County fire department"
    if re.search(r"\bVOLUNTEER\b|\bVFD\b|\bVOL\b", n):
        return "Volunteer fire department"
    return "Local fire department"


ABBREV = [(r"\bVFD\b", "VOLUNTEER FIRE DEPARTMENT"), (r"\bFD\b", "FIRE DEPARTMENT"),
          (r"\bFPD\b", "FIRE PROTECTION DISTRICT"), (r"\bESD\b", "EMERGENCY SERVICES DISTRICT"),
          (r"\bEMERGENCY SERVICE DISTRICT\b", "EMERGENCY SERVICES DISTRICT"),
          (r"\bDEPT\b", "DEPARTMENT"), (r"\bDIST\b", "DISTRICT"), (r"\bTWP\b", "TOWNSHIP"), (r"\bVOL\b", "VOLUNTEER"),
          (r"\bAND\b", " "), (r"\b(NO|NUMBER|NBR)\b", " "), (r"^THE\b", " "), (r"\b(INC|INCORPORATED)\b", " ")]


def match_key(name):
    s = (name or "").upper().replace("&", " AND ").replace("#", " ")
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = " ".join(s.split())
    for rx, rep in ABBREV:
        s = re.sub(rx, rep, s)
    return " ".join(s.split())


def normalize(states):
    for st in states:
        usfa_dir, fema_dir = common.latest_raw(st, "usfa"), common.latest_raw(st, "openfema")
        assert usfa_dir and fema_dir, f"{st}: run fetch first"
        text = common.read_gz(usfa_dir / "registry.csv.gz").decode("utf-8-sig")
        registry = common.read_csv_text(text)
        assert registry and "FDID" in registry[0] and "Fire dept name" in registry[0], f"{st}: registry columns changed"
        agencies, seen = [], set()
        for r in registry:
            fdid = r["FDID"].strip()
            aid = f"{st}-{fdid}" if fdid else f"{st}-X-{common.norm(r['Fire dept name']).replace(' ', '-')}-{common.norm(r['HQ city']).replace(' ', '-')}"
            assert aid not in seen, f"{st}: duplicate agency id {aid}"
            seen.add(aid)
            agencies.append({
                "id": aid, "name": r["Fire dept name"].strip(), "kind": kind(r["Fire dept name"], r["Organization Type"]),
                "county": r["County"].strip(), "city": r["HQ city"].strip() or r["Mail city"].strip(), "usfa_fdid": fdid,
                "dept_type": r["Dept Type"], "organization_type": r["Organization Type"],
                "stations": r["Number Of Stations"] or "0", "career": r["Active Firefighters - Career"] or "0",
                "volunteer": r["Active Firefighters - Volunteer"] or "0",
                "paid_per_call": r["Active Firefighters - Paid per Call"] or "0", "website": r["Website"].strip(),
            })

        # Strict grant matching
        by_key = collections.defaultdict(list)
        for a in agencies:
            by_key[match_key(a["name"])].append(a["id"])
        awards = json.loads(common.read_gz(fema_dir / "firefighter_grants.json.gz"))
        recipients = collections.defaultdict(list)
        for g in awards:
            recipients[g["vendorName"]].append(g)
        matched, unmatched = {}, []
        for name, gs in sorted(recipients.items()):
            k = match_key(name)
            ids, method = by_key.get(k, []), "exact"
            if not ids and len(name) >= 38:
                ids = sorted({i for key, v in by_key.items() if key.startswith(k) for i in v})
                method = "truncated name"
            if len(ids) == 1:
                matched[name] = (ids[0], method)
            else:
                unmatched.append({"fema_recipient": name, "awards": len(gs), "amount": round(sum(g["awardAmount"] or 0 for g in gs)),
                                  "fiscal_years": f"{min(g['fiscalYear'] for g in gs)}-{max(g['fiscalYear'] for g in gs)}",
                                  "reason": "ambiguous: " + "; ".join(ids) if ids else "no registry name matches"})
        grants = []
        for g in awards:
            if g["vendorName"] in matched:
                grants.append({"agency_id": matched[g["vendorName"]][0], "recipient": g["vendorName"],
                               "fiscal_year": g["fiscalYear"], "program": g["programName"],
                               "amount": g["awardAmount"], "award_number": g["awardNumber"]})
        grants.sort(key=lambda g: (g["agency_id"], -g["fiscal_year"], g["award_number"]))
        per_agency = collections.Counter(g["agency_id"] for g in grants)
        for a in agencies:
            a["grants"] = per_agency.get(a["id"], 0)

        cfg = common.config_dir(st)
        common.write_csv(cfg / "agencies.csv", AGENCY_COLUMNS, sorted(agencies, key=lambda a: a["id"]))
        common.write_csv(cfg / "grant_recipients.csv", ["fema_recipient", "agency_id", "method"],
                         [{"fema_recipient": n, "agency_id": i, "method": m} for n, (i, m) in sorted(matched.items())])
        common.write_csv(cfg / "grant_recipients_unmatched.csv",
                         ["fema_recipient", "awards", "amount", "fiscal_years", "reason"],
                         sorted(unmatched, key=lambda u: -u["amount"]))
        common.write_csv(common.data_dir(st) / "grants.csv",
                         ["agency_id", "recipient", "fiscal_year", "program", "amount", "award_number"], grants)
        if not (cfg / "sources.csv").exists():
            common.write_csv(cfg / "sources.csv", SOURCE_COLUMNS, [])
        common.assemble_agencies(st)
        total = sum(g["awardAmount"] or 0 for g in awards)
        print(f"{st}: {len(agencies)} registry agencies; {len(awards)} awards (${total:,.0f}) to {len(recipients)} recipients;"
              f" {len(matched)} recipients matched ({len(grants)} awards, ${sum(g['amount'] or 0 for g in grants):,.0f})")


SOURCE_COLUMNS = ["source", "name", "tier", "url", "years", "fiscal_year", "fetched", "note"]

if __name__ == "__main__":
    step, states = sys.argv[1], [s.upper() for s in sys.argv[2:]] or common.STATES
    {"fetch": fetch, "normalize": normalize}[step](states)
