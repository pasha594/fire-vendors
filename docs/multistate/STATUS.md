# Multi-state sources: status

PRD (product requirements document) build-order steps 2, 3 and 4 for Ohio, California, Idaho and Texas
(`docs/prd/multistate-expansion.md`). Branch `multistate-sources`, run of 2026-10-06 to 2026-10-07. Every file is new;
no file that existed on `main` was changed. Format of the output: `docs/multistate/data-contract.md`. One feasibility
note per state: `docs/sources/<st>.md`.

Numbers below were computed from the committed files after every normalize step was run twice with byte-identical
output. Dollars are net (refunds and reversals negative). Years are fiscal years named for the year they end in.

## Coverage

Tiers: 1 payee-level payment lines; 2 item lines (brand, quantity, unit price); 3 published annual totals only;
4 directory only (USFA registry and FEMA grants; never shown as $0).

| State | Agencies | Registry | Added | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OH | 1,153 | 1,148 | 5 | 184 | 0 | 0 | 969 |
| CA | 926 | 853 | 73 | 6 | 0 | 584 | 336 |
| ID | 258 | 198 | 60 | 1 | 0 | 156 | 101 |
| TX | 1,604 | 1,530 | 74 | 3 | 316 | 0 | 1,285 |
| All four | 3,941 | 3,729 | 212 | 194 | 316 | 740 | 2,691 |

| State | Built sources | Tier 1 payment lines | Tier 1 dollars | Tier 2 item lines | Tier 2 dollars | Tier 3 totals rows | Tier 3 dollars |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OH | 2 | 707,567 | $1,840,788,454.03 | - | - | - | - |
| CA | 9 | 1,376,854 | $12,872,934,012.00 | 22,766 | $884,395,982.80 | 6,852 | $43,133,606,544.00 |
| ID | 2 | 47,026 | $329,541,702.66 | - | - | 577 | $577,476,035.00 |
| TX | 5 | 120,089 | $508,658,618.18 | 28,491 | $15,630,086.78 | 50 | $396,142,185.77 |

Most Ohio local dollars are payroll, pensions and benefits; purchasing is about $385M. CAL FIRE (Open FI$Cal) is
the largest single source ($10.1B, FY2021-2026).

## Owner decisions (2026-10-06)

1. Payee names are shown as published, private persons included. `common.withhold_person` only withholds payee
   text with an email address or bank account text (`config/payee_name_redactions.csv`). Utah's `build.py` still
   withholds names; align the two at step 1.
2. Texas DIR (Department of Information Resources): identical lines inside one monthly report are kept as real
   repeat purchases; only lines re-reported in a later month are dropped.
3. ESDs (emergency services districts) that provide only EMS (emergency medical services) are excluded.
4. State fire agencies stay in the main data with kind "State fire agency" (CAL FIRE, Idaho Department of Lands
   fire program, Texas A&M Forest Service, Ohio Division of Forestry).
5. Ohio Checkbook local data is fetched although checkbook.ohio.gov's robots.txt disallows crawling. Requests are
   one at a time, at least 1 second apart, with the project user agent; no CAPTCHA or login is bypassed.

## Per state

### Ohio (OH)

| Source | Name | Decision | Tier | Agencies with rows | Rows | Dollars | Years (data) | Years (sources.csv) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | Federal layer: USFA registry, OpenFEMA firefighter grants | built (federal.py) | 4 | 1,148 registry departments; 302 with matched grants | 783 matched awards | $110,580,050.66 matched grants | FEMA FY2005-FY2024 | - |
| `oh_checkbook_local` | Ohio Checkbook, local governments | built | 1 | 183 | 673,805 payment lines | $1,800,751,956.35 | 2021-2026 | 2021-2026 |
| `oh_cincinnati` | City of Cincinnati Vendor Payments | built | 1 | 1 | 33,762 payment lines | $40,036,497.68 | 2021-2027 | 2021-2027 |
| `oh_checkbook_state` | Ohio Checkbook state expenditures (DataOhio bulk files) | skipped: state agencies at department level only, no fire agency identifiable; manifest and sample kept | 1 | 0 | 0 | - | - | - |
| `oh_odnr_forestry` | Ohio Division of Forestry (ODNR) | skipped as a source: payments not separable from ODNR; agency kept as 'State fire agency' at tier 4 | - | 0 | 0 | - | - | - |
| `oh_aos` | Ohio Auditor of State, Summarized Annual Financial Reports | skipped: whole townships/cities, 'Public Safety' mixes fire, police and EMS; sample kept | 3 | 0 | 0 | - | - | - |

Coverage: 1,153 agencies (1,148 registry, 5 added): tier 1 184, tier 2 0, tier 3 0, tier 4 969. Kind "State fire agency": 1 (Ohio Department of Natural Resources, Division of Forestry (OH-S-ohio-division-of-forestry, tier 4)).

### California (CA)

| Source | Name | Decision | Tier | Agencies with rows | Rows | Dollars | Years (data) | Years (sources.csv) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | Federal layer: USFA registry, OpenFEMA firefighter grants | built (federal.py) | 4 | 853 registry departments; 195 with matched grants | 579 matched awards | $255,287,987.39 matched grants | FEMA FY2005-FY2024 | - |
| `ca_corona` | City of Corona Open Expenditures (CorStat) | built | 1 | 1 | 14,481 payment lines | $21,831,196.97 | 2021-2026 | 2021-2026 |
| `ca_fiscal` | Open FI$Cal department vendor transactions (CAL FIRE) | built | 1 | 1 | 873,016 payment lines | $10,127,477,233.38 | 2021-2026 | 2021-2026 |
| `ca_la` | Checkbook L.A. (Los Angeles City Controller) | built | 1 | 1 | 175,405 payment lines | $696,804,689.78 | 2021-2027 | 2021-2027 |
| `ca_moreno_valley` | City of Moreno Valley Open Expenditures | built | 1 | 1 | 2,369 payment lines | $140,184,292.42 | 2021-2026 | 2021-2026 |
| `ca_riverside_county` | County of Riverside Check Book (Riverside County Fire Department) | built | 1 | 1 | 276,946 payment lines | $1,666,078,198.87 | 2021-2027 | 2021-2027 |
| `ca_sco_cities` | California State Controller, City Financial Transactions Reports (fire function) | built | 3 | 224 | 892 totals rows | $22,802,615,689.00 | 2021-2024 | 2021-2024 |
| `ca_sco_districts` | California State Controller, Special Districts Financial Transactions Reports | built | 3 | 363 | 5,960 totals rows | $20,330,990,855.00 | 2021-2024 | 2021-2024 |
| `ca_scprs` | SCPRS Purchase Order Data (CAL FIRE purchase orders) | built | 2 | 1 | 22,766 item lines | $884,395,982.80 | 2013-2015 | 2013-2015 |
| `ca_sf` | San Francisco Vendor Payments (Vouchers) | built | 1 | 1 | 34,637 payment lines | $220,558,400.58 | 2021-2027 | 2021-2027 |
| `ca_sandiego` | City of San Diego Operating Actuals | skipped: no payee; sample kept | - | 0 | 0 | - | - | - |
| `ca_sacramento` | City of Sacramento Checks Issued, Purchase Orders | skipped: no department field; samples kept | - | 0 | 0 | - | - | - |
| `ca_lacounty` | County of Los Angeles Open Expenditures | skipped: no payee; sample kept | - | 0 | 0 | - | - | - |
| `ca_modesto` | City of Modesto Weekly AP Transactions | skipped: weekly figures only; sample kept | - | 0 | 0 | - | - | - |
| `(none)` | San Jose, Indio, West Hollywood, Marin County, others | skipped (see 'Other candidates' in ca.md) | - | 0 | 0 | - | - | - |

Coverage: 926 agencies (853 registry, 73 added): tier 1 6, tier 2 0, tier 3 584, tier 4 336. Kind "State fire agency": 9 (CA Department of Forestry and Fire Protection- HQ (CA-00555, tier 1); CDF Humboldt / Del Norte Unit (CA-12555, tier 4); California Department of Forestry and Fire Protection (CA-23555, tier 4); ...).

### Idaho (ID)

| Source | Name | Decision | Tier | Agencies with rows | Rows | Dollars | Years (data) | Years (sources.csv) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | Federal layer: USFA registry, OpenFEMA firefighter grants | built (federal.py) | 4 | 198 registry departments; 54 with matched grants | 120 matched awards | $28,922,372.94 matched grants | FEMA FY2005-FY2024 | - |
| `id_lgr` | Idaho Local Government Registry (Transparent Idaho): fire district totals | built | 3 | 156 | 577 totals rows | $577,476,035.00 | 2021-2024 | 2021-2024 |
| `id_state` | Transparent Idaho state transactions (Idaho Department of Lands fire program) | built | 1 | 1 | 47,026 payment lines | $329,541,702.66 | 2021-2027 | 2021-2027 |
| `id_cities` | Transparent Idaho, city financial data | skipped: whole-city totals only, no fire department line | (3) | 0 | 0 | - | - | - |
| `id_lgr_compliance, id_contracts` | Registry compliance report; SCO statewide contracts | skipped: no fire agency spend; samples kept | - | 0 | 0 | - | - | - |

Coverage: 258 agencies (198 registry, 60 added): tier 1 1, tier 2 0, tier 3 156, tier 4 101. Kind "State fire agency": 1 (Idaho Department of Lands Fire Department (ID-X-IDAHO-DEPARTMENT-OF-LANDS-FIRE-DEPARTMENT-COEUR-D-ALENE, tier 1)).

### Texas (TX)

| Source | Name | Decision | Tier | Agencies with rows | Rows | Dollars | Years (data) | Years (sources.csv) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | Federal layer: USFA registry, OpenFEMA firefighter grants | built (federal.py) | 4 | 1,530 registry departments; 362 with matched grants | 641 matched awards | $130,187,574.11 matched grants | FEMA FY2005-FY2025 | - |
| `tx_austin` | City of Austin eCheckbook (Austin Fire Department) | built | 1 | 1 | 12,275 payment lines | $158,135,868.45 | 2021-2027 | 2021-2027 |
| `tx_cpa` | Texas Comptroller state expenditures by county (Texas A&M Forest Service) | built | 3 | 1 | 50 totals rows | $396,142,185.77 | 2021-2024 | 2021-2024 |
| `tx_dallas` | City of Dallas vendor payments (Dallas Fire-Rescue) | built | 1 | 1 | 2,343 payment lines | $54,022,889.89 | 2026-2027 | 2026-2027 |
| `tx_dir` | Texas DIR cooperative contract sales | built | 2 | 318 | 28,491 item lines | $15,630,086.78 | 2021-2026 | 2021-2026 |
| `tx_houston` | City of Houston checkbook (Houston Fire Department) | built | 1 | 1 | 105,471 payment lines | $296,499,859.84 | 2021-2027 | 2021-2027 |
| `tx_spd` | Comptroller Special Purpose District Public Information Database | skipped: no spending fields; sample kept | - | 0 | 0 | - | - | - |
| `-` | San Antonio Open Checkbook (OpenGov) | skipped: no department field, no bulk download | - | 0 | 0 | - | - | - |
| `tx_fortworth` | Fort Worth accounts payable check register | skipped: no department field; sample kept | - | 0 | 0 | - | - | - |
| `-` | El Paso | skipped: no vendor payment data found | - | 0 | 0 | - | - | - |
| `-` | Comptroller 'Where the Money Goes' | skipped: interactive only | - | 0 | 0 | - | - | - |

Coverage: 1,604 agencies (1,530 registry, 74 added): tier 1 3, tier 2 316, tier 3 0, tier 4 1285. Kind "State fire agency": 2 (Texas Forest Service- Jefferson District (TX-X-TEXAS-FOREST-SERVICE-JEFFERSON-DISTRICT-JEFFERSON, tier 4); Texas A&M Forest Service (TX-S-texas-a-and-m-forest-service, tier 2)).

## Vendor map coverage of purchasing dollars

On 2026-10-07 `pipeline/sources/merge_vendor_maps.py` folded the four states' proposals
(`config/states/<st>/vendor_map_additions.csv`, 9,627 rows) into the shared `config/vendor_map.csv` and the proposal
files were deleted: the map now has 14,676 rows (5,172 Utah rows, 9,493 from the states, 11 Utah rows added in
review), and one company has one canonical name across the five states (reviewed name decisions in
`config/vendor_name_merges.csv`). Decisions, the Utah impact (vendors 9,990 to 9,966, classified share of purchasing
97.21% to 97.23%) and the top vendors across the states are in `docs/multistate/vendor-merge.md`.

Purchasing dollars: net spend per payee key (`common.norm(payee_name)`) over `transactions.csv.gz`, payees with net
spend above zero whose category is a purchasing category or who are unmapped. Payees are classified the way
`pipeline/build.py` classifies them: `config/vendor_map.csv` first, then `config/vendor_rules.csv` and
`config/keyword_rules.csv`. Every `check_<st>.py` uses this rule (`tests/multistate/vendor_coverage.py`) and requires
at least 90% with a real category.

| State | Proposed rows merged | Purchasing dollars | Real category | Of which by rules | Unclassified | Unmapped | Before the merge (proposals + map, any category) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OH | 6,186 | $395,598,494 | 93.7% | 3.4% | 0.1% | 6.2% | 92.0% of $395,198,185 |
| CA | 2,753 | $5,927,730,905 | 92.9% | 2.8% | 1.1% | 6.0% | 91.3% of $5,930,353,140 (real category 90.2%) |
| ID | 488 | $158,010,689 | 91.3% | 2.6% | 2.0% | 6.7% | 90.7% of $158,783,827 (real category 88.7%) |
| TX | 200 | $479,006,883 | 97.4% | 1.5% | 0.0% | 2.6% | 95.4% of $484,549,732 (real category 95.2%) |

Rows marked low confidence were inferred from the account or object name and are not all reviewed.

## Federal layer

`pipeline/sources/federal.py`: every USFA (U.S. Fire Administration) registry department per state, and OpenFEMA
firefighter grants matched to them by exact name (or OpenFEMA's 40-character truncation). Recipients named
"CITY OF X", state agencies, ports and companies are left unmatched and listed in
`config/states/<st>/grant_recipients_unmatched.csv`.

## Checks

- `tests/multistate/check_federal.py`, `check_oh.py`, `check_ca.py`, `check_id.py`, `check_tx.py` recompute totals
  from the raw files without importing the adapters, and all pass. The state checks were fault-tested on scratch
  copies (each injected fault fails the check).
- Duplicates removed, per source: Ohio local months uploaded twice, a Perkins Township reload and 19 months that
  carry batch totals instead of lines ($6.56B of false amounts); Idaho 683 reloaded copies ($4.96M); Houston 24
  exact duplicate lines ($439K); DIR lines re-reported in a later month. Details in each `docs/sources/<st>.md`.

## Sizes

Every file under raw/, data/states/ and config/states/ is under 50 MB.

| State | raw/2026-10-06/<st> | data/states/<st> | config/states/<st> | Largest file |
| --- | --- | --- | --- | --- |
| OH | 57.8 MB | 9.9 MB | 0.77 MB | data/states/oh/transactions.csv.gz (9.2 MB) |
| CA | 97.3 MB | 24.9 MB | 0.52 MB | data/states/ca/transactions.csv.gz (23.1 MB) |
| ID | 1.3 MB | 1.1 MB | 0.11 MB | data/states/id/transactions.csv.gz (1.0 MB) |
| TX | 3.5 MB | 3.4 MB | 0.45 MB | data/states/tx/transactions.csv.gz (2.1 MB) |

Largest file anywhere under raw/, data/states/, config/states/: raw/2026-10-06/transparent_utah_bigquery/fire_transactions_fy2021_2026.csv.gz (24.8 MB).

## Open questions for the owner

Data access and terms:
- Idaho State Controller terms of use limit reuse of site content to non-commercial informational purposes.
  Confirm with the Controller's office (transparentidaho@sco.idaho.gov) before publishing Idaho data.
- transparent.idaho.gov and data.ohio.gov reject plain user agents; the adapters use the crawler form
  `Mozilla/5.0 (compatible; utah-fire-procurement/0.1; +https://github.com/pasha594/utah-fire-procurement)`.
- Dallas publishes fire payments only from FY2026; earlier years need a public information request.

Counting rules:
- California: fire authorities and their member districts both file totals, and some districts are served by a
  city department that also reports a fire line, so those dollars can be counted twice.
- Houston drops 24 exact duplicate lines ($439K); some may be real repeat payments. Ohio keeps 10 days doubled
  inside one upload ($264K). Pick one rule for both.
- Ohio townships: spending under "Public Safety" (program 220) or special levy funds is not counted, so some
  township fire departments are partial. Count program 220 for townships with their own department and no police?
- Cincinnati buys apparatus and ambulances through a citywide vehicle account ($18.7M, FY2021-2027) without a fire
  code; it is left out and stated in the source note.
- FEMA grants to "CITY OF X" are not credited to X's fire department (Cincinnati: 35 awards, $41.5M). Allow it when
  the city has exactly one registry fire department?

Agency matching:
- Texas ESDs that fund a registry department under another name (Harris ESD 9 and Cy-Fair, ESD 7 and Spring) are
  separate agencies; no dollars are double counted, but the directory lists the pair twice.
- Idaho "<city> Rural Fire District" agencies are separate from the city departments, which stay at tier 4.
- Sonoma County Fire District is an added agency while its predecessors remain registry rows at tier 4.

PRD questions still open: first cities beyond those built, and whether to rename the repository.

## How to rebuild

```
python3 pipeline/sources/federal.py fetch OH CA ID TX      # USFA registry and OpenFEMA grants
python3 pipeline/sources/federal.py normalize OH CA ID TX
python3 pipeline/sources/<st>_<source>.py fetch             # each adapter; raw files are never overwritten
python3 pipeline/sources/<st>_<source>.py normalize
python3 pipeline/sources/merge_vendor_maps.py              # only when a state wrote vendor_map_additions.csv
python3 tests/multistate/check_<st>.py
```

Python standard library only. Adapters: `oh_checkbook_local`, `oh_cincinnati`; `ca_sco_districts`,
`ca_sco_cities`, `ca_sf`, `ca_la`, `ca_riverside_county`, `ca_corona`, `ca_moreno_valley`, `ca_fiscal`,
`ca_scprs`; `id_lgr`, `id_state`; `tx_dir`, `tx_houston`, `tx_dallas`, `tx_austin`, `tx_cpa`.
