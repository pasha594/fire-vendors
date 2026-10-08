# Multi-state sources: status

PRD (product requirements document) build-order steps 2 to 7 (sources) for Ohio, California, Idaho and Texas
(`docs/prd/multistate-expansion.md`): branch `multistate-sources`, run of 2026-10-06 to 2026-10-07, merged to main as
`de1e5cf`. Steps 1 and 8 (multi-state build and page): branch `claude/artifact-implementation-kgowml`, 2026-10-07 to
2026-10-08, section "Steps 1 and 8" below. Output format: `docs/multistate/data-contract.md`. One source note per
state: `docs/sources/<st>.md`.

Sources step: files that existed on `main` and changed: `config/vendor_map.csv` (the states' vendor names merged in) and
`data/data.json`, `data/payments.json` (Utah rebuilt from the merged map). `config/vendor_name_merges.csv` is new.
Everything else is new and under `raw/2026-10-06/<st>/`, `config/states/`, `data/states/`, `pipeline/sources/`,
`tests/multistate/`, `docs/sources/` and `docs/multistate/`.

Numbers below were recomputed on 2026-10-07 from the committed files, after the owner's decisions 11 and 12 (identical
voids fixed, SCPRS purchase-order lines kept) and after every normalize step was run twice with byte-identical
output. Dollars are net (refunds and reversals negative). Years are fiscal years named for the year
they end in, as each source defines them.

## Steps 1 and 8: build and page (done, 2026-10-08)

- Build (step 1). `pipeline/build.py` builds Utah as before (agency ids `UT-<Transparent Utah id>`) and Ohio,
  California, Idaho and Texas from `data/states/<st>/` with the same vendor, keyword, account and description rules;
  states, fiscal years and partial years come from `config/states.csv`. It writes `data/index.json` (the first load:
  meta per state and source, categories, every agency with its tier, the precomputed default table of each scope)
  and per state `data/<st>.json`, `data/<st>-payments.json` and, for Texas and California, `data/<st>-items.json`
  (format: `docs/multistate/data-contract.md`, "Site files"). `data/data.json` and `data/payments.json` are no
  longer written; the tests read them from `de1e5cf` (`--base`) to prove Utah reads as before.
- Page (step 8). Renamed "Fire Agency Vendor Finances". State filter (all states by default; the county filter
  follows the state), coverage badges and "No vendor data" in place of $0 for tiers 3 and 4, a coverage summary on
  the home view and a coverage table by state on the About page, annual totals for tier 3 agencies, item lines
  (brand, product type, quantity, unit price) for vendors and agencies of Texas and California, source links and
  notes from `meta.sources`. The first view loads only `data/index.json`; a state's files load when a view needs
  them. Older links keep working: `agency=359` is `UT-359`, and a Utah county without a state means Utah.
- Utah unchanged: rows, vendors, payee names, payments, grants and meta equal the files of `de1e5cf` after mapping
  ids; the page shows the same summary, table, details and CSV for 22 Utah views as the page of `de1e5cf` (apart
  from the site name, the State chip, the Coverage and Sources facts and the CSV's Coverage column).
- A browser that still has the old `index.html` cached (GitHub Pages lets it keep the page for 10 minutes,
  `cache-control: max-age=600`) gets the old page's own message "Data did not load. Could not load the data:
  data/data.json returned HTTP 404." in place of a page; a reload gets the new page. A clearer text would need a
  stub `data/data.json` that the old page reads, and only browser-specific error texts can carry it, so none is kept.
  A tab opened before the switch keeps its data and shows "Payments did not load" when it first opens single
  payments.

Decisions on the design's open questions (orchestrator defaults of 2026-10-07, consistent with the owner's earlier
answers; the owner may revisit them):
1. Utah agencies with no lines (Rockville Springdale, UT-1141, and Thompson, UT-1577) keep $0, as before.
2. Utah's description-privacy withholding is not applied to other states (names and text as published; only
   `config/payee_name_redactions.csv` text, which the adapters remove).
3. "Individuals (names withheld)" stays Utah's category; the About page says other states publish payee names.
4. Partial years: Utah 2026; Ohio, California and Texas 2026 and 2027; Idaho 2027 (`config/states.csv`).
5. California single payments: no threshold; loaded when the payments section is opened in an all-states view.
6. Texas DIR-only (tier 2) agencies count as peers, with a note that DIR covers IT and telecom only.
7. Old links without a state show all states; a numeric agency id or a Utah county means Utah.
8. Vendor slug collisions across states: the Utah name wins.
9. The repository keeps its name; only the site is renamed.

Output of the build of 2026-10-08 (every file under 50 MB; `data/index.json` must stay under 1,000,000 bytes
gzipped, the build stops otherwise):

| File | Size | Gzipped |
| --- | --- | --- |
| `data/index.json` | 2.07 MB | 0.20 MB (198,879 bytes) |
| `data/ut.json` | 4.10 MB | 1.02 MB |
| `data/ut-payments.json` | 3.23 MB | 0.65 MB |
| `data/oh.json` | 6.10 MB | 1.44 MB |
| `data/oh-payments.json` | 2.76 MB | 0.50 MB |
| `data/ca.json` | 4.67 MB | 0.98 MB |
| `data/ca-payments.json` | 17.23 MB | 2.75 MB |
| `data/ca-items.json` | 2.24 MB | 0.49 MB |
| `data/id.json` | 2.06 MB | 0.33 MB |
| `data/id-payments.json` | 0.71 MB | 0.07 MB |
| `data/tx.json` | 0.57 MB | 0.12 MB |
| `data/tx-payments.json` | 1.50 MB | 0.21 MB |
| `data/tx-items.json` | 2.07 MB | 0.09 MB |
| All | 49.3 MB | 8.86 MB |

| State | Agencies (tiers 1/2/3/4) | Rows | Vendors | Single payments | Item lines |
| --- | --- | --- | --- | --- | --- |
| Utah | 185/0/0/0 | 63,962 | 9,966 | 58,726 | 0 |
| Ohio | 187/0/0/966 | 74,696 | 19,158 | 52,401 | 0 |
| California | 6/0/584/336 | 38,891 | 15,825 | 323,079 | 22,798 |
| Idaho | 1/0/156/101 | 11,657 | 5,924 | 6,841 | 0 |
| Texas | 3/316/0/1,285 | 4,810 | 1,825 | 18,619 | 28,491 |

Default table (`home`), purchasing categories, all years: all states $8,054,382,429.21 in 164,025 rows, 43,278
vendors, 693 agencies; Utah $677,373,536.21, 56,821 rows, 8,886 vendors, 183 agencies.

Tests of 2026-10-08 (container with Node 22, Playwright 1.56 and Chromium; times are wall clock):

| Command | Result | Time |
| --- | --- | --- |
| `python3 pipeline/build.py`, twice | the 13 files byte-identical between the runs; 185 of 185 Utah agencies and every other state's agencies with lines match their lines | 182 s, 180 s |
| `python3 tests/check_build.py` (base `de1e5cf`) | all checks pass | 34 s |
| `python3 tests/multistate/check_oh.py`, `check_ca.py`, `check_id.py`, `check_tx.py`, `check_federal.py` | all pass | 152 s, 148 s, 5 s, 11 s, 0.4 s |
| `python3 pipeline/sources/merge_vendor_maps.py --check` | 14,676 rows, 0 problems | 0.1 s |
| `node tests/core_test.js` | 26,868 checks, 0 failed (1,962 generated states) | 49 s |
| `node tests/page/compare_utah.js` | 392 checks, 0 failed (22 Utah views, 60 state views, controls, the cached old page) | 55 s |
| `node tests/page/screens.js` | 111 checks, 0 failed (13 views at 1366x900 and 390x844) | 46 s |

Page timings in Chromium (desktop, local server): `#/` renders in about 250 ms from `data/index.json` alone; a
drill-down from `#/` that loads every state's rows (`#/?g=vendor&cat=apparatus`) takes about 0.65 s; the slowest
views are the agency and vendor groupings over all states (about 1 s) and CAL FIRE with its payments and item lines
(about 1.5 s).

## Coverage

Tiers: 1 payee-level payment lines; 2 item lines (brand, quantity, unit price); 3 published annual totals only;
4 directory only (USFA registry and FEMA grants; never shown as $0).

| State | Agencies | Registry | Added | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OH | 1,153 | 1,148 | 5 | 187 | 0 | 0 | 966 |
| CA | 926 | 853 | 73 | 6 | 0 | 584 | 336 |
| ID | 258 | 198 | 60 | 1 | 0 | 156 | 101 |
| TX | 1,604 | 1,530 | 74 | 3 | 316 | 0 | 1,285 |
| All four | 3,941 | 3,729 | 212 | 197 | 316 | 740 | 2,688 |

| State | Built sources | Tier 1 payment lines | Tier 1 dollars | Tier 2 item lines | Tier 2 dollars | Tier 3 totals rows | Tier 3 dollars |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OH | 2 | 737,380 | $1,965,024,254.71 | - | - | - | - |
| CA | 9 | 1,351,967 | $12,864,120,227.23 | 22,798 | $886,076,817.36 | 6,852 | $43,133,606,544.00 |
| ID | 2 | 47,001 | $329,401,352.68 | - | - | 577 | $577,476,035.00 |
| TX | 5 | 120,111 | $509,097,190.65 | 28,491 | $15,630,086.78 | 50 | $396,142,185.77 |

Most Ohio dollars are payroll, pensions and benefits; purchasing is about $400M. CAL FIRE (Open FI$Cal) is the
largest single source ($10.1B, FY2021-2026). State fire agencies (kind "State fire agency"): Ohio Division of
Forestry (tier 4), CAL FIRE (tier 1; 8 more CAL FIRE unit rows of the registry at tier 4), Idaho Department of
Lands fire program (tier 1), Texas A&M Forest Service (tier 2; a registry district row at tier 4).

## Built sources

| State | Source | Name | Tier | Agencies with rows | Rows | Dollars | Years |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OH | `oh_checkbook_local` | Ohio Checkbook, local governments | 1 | 186 | 703,618 | $1,924,987,757.03 | 2021-2026 |
| OH | `oh_cincinnati` | City of Cincinnati Vendor Payments | 1 | 1 | 33,762 | $40,036,497.68 | 2021-2027 |
| CA | `ca_fiscal` | Open FI$Cal vendor transactions (CAL FIRE) | 1 | 1 | 873,016 | $10,127,477,233.38 | 2021-2026 |
| CA | `ca_riverside_county` | County of Riverside Check Book (Riverside County Fire) | 1 | 1 | 252,908 | $1,657,351,545.96 | 2021-2027 |
| CA | `ca_la` | Checkbook L.A. (Los Angeles City Controller) | 1 | 1 | 175,405 | $696,804,689.78 | 2021-2027 |
| CA | `ca_sf` | San Francisco Vendor Payments (Vouchers) | 1 | 1 | 34,637 | $220,558,400.58 | 2021-2027 |
| CA | `ca_moreno_valley` | City of Moreno Valley Open Expenditures | 1 | 1 | 2,369 | $140,184,292.42 | 2021-2026 |
| CA | `ca_corona` | City of Corona Open Expenditures (CorStat) | 1 | 1 | 13,632 | $21,744,065.11 | 2021-2026 |
| CA | `ca_scprs` | SCPRS purchase orders (CAL FIRE) | 2 | 1 | 22,798 item lines | $886,076,817.36 | 2013-2015 |
| CA | `ca_sco_cities` | State Controller, city reports (fire function) | 3 | 224 | 892 totals | $22,802,615,689.00 | 2021-2024 |
| CA | `ca_sco_districts` | State Controller, special district reports | 3 | 363 | 5,960 totals | $20,330,990,855.00 | 2021-2024 |
| ID | `id_state` | Transparent Idaho state transactions (Department of Lands fire program) | 1 | 1 | 47,001 | $329,401,352.68 | 2021-2027 |
| ID | `id_lgr` | Idaho Local Government Registry, fire district totals | 3 | 156 | 577 totals | $577,476,035.00 | 2021-2024 |
| TX | `tx_houston` | City of Houston checkbook (Houston Fire Department) | 1 | 1 | 105,493 | $296,938,432.31 | 2021-2027 |
| TX | `tx_austin` | City of Austin eCheckbook (Austin Fire Department) | 1 | 1 | 12,275 | $158,135,868.45 | 2021-2027 |
| TX | `tx_dallas` | City of Dallas vendor payments (Dallas Fire-Rescue) | 1 | 1 | 2,343 | $54,022,889.89 | 2026-2027 |
| TX | `tx_dir` | Texas DIR cooperative contract sales | 2 | 318 | 28,491 item lines | $15,630,086.78 | 2021-2026 |
| TX | `tx_cpa` | Comptroller expenditures by county (Texas A&M Forest Service) | 3 | 1 | 50 totals | $396,142,185.77 | 2021-2024 |

Federal layer (`pipeline/sources/federal.py`, tier 4): every USFA registry department, and OpenFEMA firefighter
grants matched by exact name (or OpenFEMA's 40-character truncation): OH 302 departments, 783 awards,
$110,580,050.66; CA 195, 579, $255,287,987.39; ID 54, 120, $28,922,372.94; TX 362, 641, $130,187,574.11
(FY2005-FY2024, Texas to FY2025). Unmatched recipients are in `config/states/<st>/grant_recipients_unmatched.csv`.

Looked at and skipped (reasons in the state notes): Ohio Checkbook state agencies (department level only), Ohio
Auditor of State reports (fire not separable); San Diego, LA County (no payee), Sacramento (no department), Modesto
(weekly totals); Idaho city financial data (whole-city totals); Texas special purpose districts database (no
spending fields), San Antonio and Fort Worth (no department field), El Paso (no data found).

## Duplicates removed

Owner rule of 2026-10-07 as corrected the same day (decision 9 below), with the fix of identical voids (decision 11)
and the SCPRS exemption (decision 12), applied per source on the raw columns. Upload errors are removed first; the
identical-line rule runs after them.

| Source | Id columns ignored | Upload-error copies dropped | Identical lines dropped (net) | Void rule kept | Void fix kept | Published |
| --- | --- | --- | --- | --- | --- | --- |
| `oh_checkbook_local` | `Id`, `TransactionId` | months uploaded twice 161 ($1,163,019.54); Perkins reload 82 ($86,589.34); 19 batch-total months 1,733 lines ($6.56B of false amounts) | 16,760 in 10,195 groups ($7,385,008.50; 2,786 negative, -$3,582,639.48) | 6,267 ($11,634,680.14) | 957 (-$878,742.94) in 603 families | 703,618, $1,924,987,757.03 |
| `oh_cincinnati` | none | - | 0 | 0 | 0 | 33,762, $40,036,497.68 |
| `ca_fiscal` | none | - | 1,308 distribution lines ($3,113,705.14) | 0 | 0 (no family with payments) | 873,016 rows from 3,226,425 distribution lines |
| `ca_riverside_county` | `:id` | - | 24,967 in 5,650 sets ($9,451,661.00; 86 negative) | 134 ($38,324.23) | 110 (-$6,840.05) in 108 families | 252,908 of 277,875 |
| `ca_corona` | `:id` | - | 868 in 299 sets ($90,457.01; 13 negative) | 70 ($305,258.23) | 6 (-$4,707.58) in 5 families | 13,632 of 14,500 |
| `ca_scprs` | exempt (decision 12) | - | - (414 lines equal another in all 32 columns, 112 sets, all kept) | - | - | 22,798 item lines |
| `ca_la`, `ca_sf`, `ca_moreno_valley` | `:id` (SF also `data_as_of`, `data_loaded_at`) | - | 0 | 0 | 0 | as raw |
| `id_state` | `unique_id`, `date_of_load`, `zz_extract_date` | later load batch 567 ($4,880,745.10); doubled blocks 116 ($75,206.33) | 25 in 24 sets ($140,349.98) | 0 | 1 (-$1,529.87) in 1 family | 47,001 of 47,709 payment lines |
| `tx_houston` | none | - | 2 ($225.72) | 21 ($450,972.47) | 1 (-$12,400.00) in 1 family | 105,493 of 105,495 |
| `tx_austin`, `tx_dallas` | `:id` | - | 0 | 0 | 0 | as raw |
| `tx_dir` | exempt (decision 2) | 8 lines re-reported in a later month ($1,552.62) | - | - | - | 28,491 item lines |

Against the first reading of the rule (published contract columns only), the rule as it stands restores Ohio local
7,313 lines ($10,881,759.11), Cincinnati 10,894 ($1,119,873.72), California 113,477 lines ($553,090,677.24, of them
SCPRS 1,144 item lines, $5,824,389.82), Idaho 1 (-$1,529.87) and Texas 3,066 ($18,644,614.66). Lines that differ only
in a document number are kept, for example Cincinnati 10,841 (invoice line), LA 4,710, Houston 4,313.

Identical voids (decision 11): a family is the lines of one agency, payee, account and the document fields the source
repeats on a void, with the same amount up to sign, a negative line joined to the payments of its fiscal year and the
year before (Idaho also the year after), chained. In a family that has payments an identical negative copy is dropped
only together with an identical positive copy of the family that the void rule drops; positive lines are unchanged,
and a family of negative lines only keeps each identical negative line once. The fix keeps 1,075 negative lines
(-$904,220.44) in 718 families, and every family it touches nets exactly as its raw lines (each state's check asserts
it). Checked again from the raw files: Walnut Township (Fairfield), 2021-11-24 (three payments and two voids of
$1,551,069.41 in the raw file; two payments and one void published) nets $1,551,069.41; Hamilton Township (Franklin),
Global Emergency Vehicles, 2025-08-26 (two $281,250 payments, two voids) nets $0, as raw; Houston's Life-Assist invoice
1369849 family nets $12,400.00 and Idaho's -$1,529.87 credit family -$1,529.87, as raw. The review had counted 1,155
lines; Ohio restores 957 instead of 1,037 because 17 groups of one participant, payee, account and amount
(+$2,879.80, mostly benefit and tax deductions, such as 56 identical -$29.23 dental lines of Beavercreek Township
(Greene) on 2021-12-01) have no payment of that amount in the same or the previous year, so they are families without
payments and keep the old rule, while families the review missed (City of Amherst, $599, 2021) are fixed. A family
can still net less than raw where more payment copies are dropped than there are void copies (Corona, Staples invoice
8059495826: four $71.18 payments, two voids; $71.18 published against $142.36 raw).

## Owner decisions

2026-10-06:

1. Payee names are shown as published, private persons included. `common.withhold_person` only withholds payee
   text with an email address or bank account text (`config/payee_name_redactions.csv`). Utah's `build.py` still
   withholds names; at step 1 Utah kept its withholding (Utah unchanged) and the other states are shown as
   published (decision 2 of "Steps 1 and 8").
2. Texas DIR (Department of Information Resources): identical lines inside one monthly report are kept as real
   repeat purchases; only lines re-reported in a later month are dropped.
3. ESDs (emergency services districts) that provide only EMS (emergency medical services) are excluded.
4. State fire agencies stay in the main data with kind "State fire agency".
5. Ohio Checkbook local data is fetched although checkbook.ohio.gov's robots.txt disallows crawling. Requests are
   one at a time, at least 1 second apart, with the project user agent; no CAPTCHA or login is bypassed.

2026-10-07:

6. This is an internal tool, so the Idaho State Controller's terms of use are accepted as they are.
7. Internal tool, so California double counting is accepted: fire authorities and their member districts both file
   totals, and some districts served by a city department sit beside the city's fire line. Rows stay as published;
   `docs/sources/ca.md` lists the pairs.
8. Dallas from FY2026 only (all the city publishes) is accepted.
9. Duplicates, "drop identical lines, drop identical days", as corrected the same day: two lines are identical when
   every column the source publishes in its raw file is equal, except row and load ids; document numbers (voucher,
   invoice, check, PO and their line numbers) are content. Identical lines are kept once (lowest row id, earliest
   load). Void-safe: n identical positive lines keep min(n, reversals + 1), counting the distinct exact reversals
   (same agency, payee, account and document fields, amount negated, same or next fiscal year). The upload-error
   rules stay; Texas DIR stays exempt.
10. Ohio townships: program 220 (Public Safety, fire protection in the township chart of accounts) is counted for
    linked townships, never a line named for police.
11. Fix the voids (decision A, latest of 2026-10-07): in a family that has payments (same agency, payee, account and
    the document fields the source repeats on a void, amount up to sign, same or next fiscal year), an identical
    negative copy is dropped only together with an identical positive copy of the same family. Positive lines are
    unchanged; a family of negative lines only keeps the existing rule (identical copies once).
12. Keep PO lines (decision B, California only): `ca_scprs` keeps identical item lines inside one purchase order, like
    Texas DIR, and is exempt from the identical-line rule (the PO number is content, so lines of different POs are
    never identical). Riverside County and Corona are not PO data and keep the identical-line rule.

## Vendor names

On 2026-10-07 `pipeline/sources/merge_vendor_maps.py` folded the four states' proposals (9,627 rows) into the shared
`config/vendor_map.csv` and the proposal files were deleted. The map has 14,676 rows (5,172 Utah, 9,493 from the
states, 11 Utah rows added in review); one company has one canonical name across the five states, with the reviewed
name decisions in `config/vendor_name_merges.csv`. Utah impact: vendors 9,990 to 9,966, classified share of Utah
purchasing 97.21% to 97.23%. Details and the top vendors across states: `docs/multistate/vendor-merge.md`.

Purchasing dollars (net spend per payee key over `transactions.csv.gz`, payees above zero in a purchasing category
or unmapped), classified as `pipeline/build.py` does (map, then vendor and keyword rules). Every state check requires
at least 90% in a real category (`tests/multistate/vendor_coverage.py`).

| State | Purchasing dollars | Real category | Of which by rules | Unclassified | Unmapped |
| --- | --- | --- | --- | --- | --- |
| OH | $399,193,369 | 93.7% | 3.5% | 0.1% | 6.3% |
| CA | $6,240,319,745 | 93.1% | 2.7% | 1.0% | 5.9% |
| ID | $158,010,689 | 91.3% | 2.6% | 2.0% | 6.7% |
| TX | $497,067,555 | 97.4% | 1.4% | 0.0% | 2.5% |

## Checks (2026-10-07)

- `federal.py normalize` and all 18 adapters' normalize steps, run twice after the void fix and the SCPRS exemption:
  the 41 files under `data/states/` and `config/states/` (and `config/vendor_map.csv`) are byte-identical between the
  runs and to the committed files.
- `merge_vendor_maps.py --check`: 14,676 rows, 0 problems.
- `tests/multistate/check_federal.py`, `check_oh.py`, `check_ca.py`, `check_id.py`, `check_tx.py`: all pass. They
  recompute totals and the dedup rule, the void fix included, from the raw files without importing the adapters, and
  assert that every family the void fix touches nets exactly as its raw lines and no family with payments nets above
  them. Fault tests on scratch copies: with the rule switched off each check failed; with the void fix switched off
  each of the four state checks failed (Ohio 671 lines against 672 raw for OH-02107 in 2024; California 110 Riverside
  County lines missing; Idaho 1 line, source_record_id 13674118; Texas $12,400 off for TX-KA926 in 2024).
- Independent re-check from the raw files (verification, 2026-10-07): the families with identical negative lines
  follow the rule with no exception in Ohio local, Riverside County, Corona, Houston and Idaho; samples of 20 void
  families per state net as raw; SCPRS publishes all 22,798 non-zero raw lines (PO CF140541: 40 lines of $6,500 in raw
  and published); `tx_dir` rows are identical to those before the fixes.
- `python3 pipeline/build.py`: `data/data.json` and `data/payments.json` (the files the page read until step 8)
  byte-identical to the committed files (Utah unchanged in this step; 185 of 185 agencies match the raw file).

## Sizes

Every file under raw/, data/ and config/ is under 50 MB.

| State | raw/2026-10-06/<st> | data/states/<st> | config/states/<st> | Largest file |
| --- | --- | --- | --- | --- |
| OH | 61.4 MB | 10.4 MB | 0.38 MB | data/states/oh/transactions.csv.gz (9.7 MB) |
| CA | 97.3 MB | 24.8 MB | 0.32 MB | data/states/ca/transactions.csv.gz (23.0 MB) |
| ID | 1.3 MB | 1.1 MB | 0.08 MB | data/states/id/transactions.csv.gz (1.0 MB) |
| TX | 3.5 MB | 3.4 MB | 0.44 MB | data/states/tx/transactions.csv.gz (2.1 MB) |

Largest file anywhere: raw/2026-10-06/transparent_utah_bigquery/fire_transactions_fy2021_2026.csv.gz (24.8 MB).

## Open questions for the owner

Duplicates:
- Family years for the void fix. Ohio, California and Texas join a negative line to the payments of its fiscal year
  and the year before (the void rule's link); Idaho also joins the year after, which its listed case needs (two
  FY2026 credits of -$1,529.87, one re-reversed in FY2027). With the Idaho link, Ohio would keep about 50 more
  negative lines and still have 11 of its 17 negative-only groups above raw (+$1,083.60). Use one link for all
  states, and which?
- SCPRS lists every line at least twice on 26 POs (32 extra lines, $1,680,834.56, for example the $952,295 Nomex
  line on PO 9PA1K114); with decision 12 they are kept, as the extract has no load date to tell an upload error
  apart.
- FI$Cal: 123 doubled distribution lines ($103,648.18, May 2021 CalCard) that face a negated sibling on another fund
  are still dropped (not an exact reversal). Keep them dropped?
- The contract columns leave out invoice and document numbers, so many kept rows look equal to another on the page
  (Houston 2,536, Austin 433, Dallas 96; also Cincinnati and California) although `source_record_id` differs. Add
  the invoice or document number to the description?
- Utah's `pipeline/build.py` keeps lines that repeat inside one upload batch and drops only copies uploaded again in
  a later batch. Step 1 left Utah unchanged. Apply the owner's rule to Utah?

Vendor names (`docs/multistate/vendor-merge.md`):
- The key SPECTRUM is Utah's St. George newspaper (The Spectrum), so $165K of Ohio Charter Spectrum payments show
  under the newspaper; COMMUNITY FIRST NATIONAL BANK is one key for an Ohio bank and a Utah payee. A name-only map
  cannot give one key two vendors.
- Aircraft contractors are apparatus in California (Heli-1, HeliQwest, Timberline Helicopters) and wildland in Idaho
  (Aero Spray, Eagle Helicopters). One category for both?
- California grant recipients (fire safe councils, foundations, timber companies) are filed as government, which is
  not purchasing. Keep?
- Bank payees: JPMorgan Chase Bank is payroll by spend (Ohio payroll accounts) although California's lines are card
  and bank payments; Chase Card Services stays finance. Both are outside purchasing.

Counting and matching:
- Ohio cities and villages: police-named lines still count when the fund or department is also named for fire (City
  of Niles "Police & Fire 1%", City of Lancaster ".45 Police & Fire Levy", City of Columbiana's fire fund with
  "... - POLICE" departments). The program 220 decision covered townships only. Apply "never count police-named
  lines" to cities and villages?
- Ohio: seven townships with "Public Safety - 220" and no fire-named lines (Jefferson Township (Franklin) runs a
  career department) were never fetched or linked. Fetch and link them?
- Cincinnati buys apparatus and ambulances through a citywide vehicle account ($18.7M, FY2021-2027) without a fire
  code; it is left out and stated in the source note.
- FEMA grants to "CITY OF X" are not credited to X's fire department (Cincinnati: 35 awards, $41.5M). Allow it when
  the city has exactly one registry fire department?
- Riverside County's two CAL FIRE contract invoices of 2026-03-16 ($72.4M each) are both counted; one quarter may have
  been paid twice.
- Texas ESDs that fund a registry department under another name (Harris ESD 9 and Cy-Fair, ESD 7 and Spring) are
  separate agencies, so the directory lists the pair twice (no dollars counted twice). Idaho "<city> Rural Fire
  District" agencies are separate from the city departments; Sonoma County Fire District is added while its
  predecessors remain registry rows at tier 4.

Site (steps 1 and 8):
- California's single payments are 2.75 MB gzipped (323,079 lines), the largest file a view loads; they load only
  when the payments section is opened in an all-states view. A threshold above $1,000 for California would shrink
  it.
- The nine defaults under "Steps 1 and 8" (Utah's two agencies at $0, Utah-only withholding, the "Individuals (names
  withheld)" label, partial years, DIR-only agencies as peers, old links, name collisions, repository name) stand
  until the owner decides otherwise.
- PRD step 9 (per-state metrics on the About page and in the README): the About page has coverage, sources, fiscal
  years and categorization per state; the README describes tiers and sources and points to the About page for counts.

PRD question still open: first cities beyond those built.

## How to rebuild

```
python3 pipeline/sources/federal.py fetch OH CA ID TX      # USFA registry and OpenFEMA grants
python3 pipeline/sources/federal.py normalize OH CA ID TX
python3 pipeline/sources/<st>_<source>.py fetch             # each adapter; raw files are never overwritten
python3 pipeline/sources/<st>_<source>.py normalize
python3 pipeline/sources/merge_vendor_maps.py --check      # folds proposals only if a state wrote vendor_map_additions.csv
python3 tests/multistate/check_<st>.py
python3 pipeline/build.py                                  # data/index.json and the per-state site files
python3 tests/check_build.py
node tests/core_test.js
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers NODE_PATH=/opt/node22/lib/node_modules node tests/page/compare_utah.js
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers NODE_PATH=/opt/node22/lib/node_modules node tests/page/screens.js
```

Python standard library only. Adapters: `oh_cincinnati`, `oh_checkbook_local`; `ca_sco_districts`, `ca_sco_cities`,
`ca_sf`, `ca_la`, `ca_riverside_county`, `ca_corona`, `ca_moreno_valley`, `ca_fiscal`, `ca_scprs`; `id_lgr`,
`id_state`; `tx_dir`, `tx_houston`, `tx_dallas`, `tx_austin`, `tx_cpa`.
