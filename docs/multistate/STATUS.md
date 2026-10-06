# Multi-state sources: status

Run of 2026-10-06 (cloud session, branch `multistate-sources`). PRD: `docs/prd/multistate-expansion.md`, build-order steps 2 to 7.

## Result: stopped, no government website reachable

Nothing was built for Ohio, California, Idaho or Texas. This session's network policy blocks every
government host it tried. Each request failed at the egress proxy with `CONNECT tunnel failed, response 403`
("policy denial"), before reaching the site. Per the run instructions, the session wrote this file,
pushed the branch and stopped.

Hosts tried (2026-10-06, about 19:29 UTC), all blocked:

| Needed for | Host |
| --- | --- |
| Federal layer: USFA registry | apps.usfa.fema.gov (also blocked through the WebFetch tool: `EGRESS_BLOCKED`) |
| Federal layer: OpenFEMA grants | www.fema.gov |
| Texas DIR sales, Texas open data | data.texas.gov, dir.texas.gov, www.texas.gov |
| Texas special purpose districts | comptroller.texas.gov |
| Texas cities | data.houstontx.gov, www.dallasopendata.com, data.austintexas.gov |
| Ohio Checkbook | spend.ohio.gov, checkbook.ohio.gov, data.ohio.gov, www.ohio.gov |
| California special districts, SCPRS | bythenumbers.sco.ca.gov, sco.ca.gov, data.ca.gov, www.dgs.ca.gov, catalog.data.gov |
| California cities | data.sf.gov, data.sfgov.org, data.lacity.org, data.sandiego.gov |
| Idaho | transparent.idaho.gov, idaho.gov, www.sco.idaho.gov |
| Other checks | api.us.socrata.com, data.wa.gov, data.cityofchicago.org, usfa.fema.gov, www.usa.gov |

Reachable from the same session: github.com, raw.githubusercontent.com, pypi.org, storage.googleapis.com.
So the block is the environment's allow-list, not an outage at the sources.

## What the owner needs to do

Allow outbound access to the hosts above in the cloud environment's network policy (or choose a policy
with full internet access), then re-run the routine. Environment network policies are described at
https://code.claude.com/docs/en/claude-code-on-the-web. A minimal allow-list for the first steps:

- Federal layer (step 2): `apps.usfa.fema.gov`, `www.fema.gov`
- Texas DIR (step 4): `data.texas.gov`
- Ohio Checkbook (step 5): `spend.ohio.gov`, `checkbook.ohio.gov`, `data.ohio.gov`, `*.ohiocheckbook.com`
- California (step 6): `bythenumbers.sco.ca.gov`, `data.ca.gov`, `catalog.data.gov`, `data.sfgov.org`, `data.sf.gov`
- Idaho (step 7): `transparent.idaho.gov`, `transparencyresources.idaho.gov`

## Per state

| State | Built | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Skipped and why |
| --- | --- | --- | --- | --- | --- | --- |
| Ohio | Nothing | none | none | none | none | All sources blocked by network policy |
| California | Nothing | none | none | none | none | All sources blocked by network policy |
| Idaho | Nothing | none | none | none | none | All sources blocked by network policy |
| Texas | Nothing | none | none | none | none | All sources blocked by network policy |

No agency was given a coverage tier or a $0 amount; no files were added under `config/states/`,
`data/states/` or `raw/`.

## Open questions for the owner

- Can the environment's network policy be widened to the hosts above? Without it this routine cannot
  do any of steps 2 to 7.
- PRD open questions are unchanged (first cities, FY2021 on, state fire agencies, repository rename).
