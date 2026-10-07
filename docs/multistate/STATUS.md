# Multi-state sources: status

PRD (product requirements document) build-order steps 2, 3 and 4 for Ohio, California, Idaho and Texas
(`docs/prd/multistate-expansion.md`). Branch `multistate-sources`, run of 2026-10-06 to 2026-10-07. Output format:
`docs/multistate/data-contract.md`. One source note per state: `docs/sources/<st>.md`.

Files that existed on `main` and changed: `config/vendor_map.csv` (the states' vendor names merged in) and
`data/data.json`, `data/payments.json` (Utah rebuilt from the merged map). `config/vendor_name_merges.csv` is new.
Everything else is new and under `raw/2026-10-06/<st>/`, `config/states/`, `data/states/`, `pipeline/sources/`,
`tests/multistate/`, `docs/sources/` and `docs/multistate/`.

Numbers below were recomputed on 2026-10-07 from the committed files, after every normalize step was run twice with
byte-identical output. Dollars are net (refunds and reversals negative). Years are fiscal years named for the year
they end in, as each source defines them.

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
| OH | 2 | 736,423 | $1,965,902,997.65 | - | - | - | - |
| CA | 9 | 1,351,851 | $12,864,131,774.86 | 22,496 | $883,440,114.00 | 6,852 | $43,133,606,544.00 |
| ID | 2 | 47,000 | $329,402,882.55 | - | - | 577 | $577,476,035.00 |
| TX | 5 | 120,110 | $509,109,590.65 | 28,491 | $15,630,086.78 | 50 | $396,142,185.77 |

Most Ohio dollars are payroll, pensions and benefits; purchasing is about $400M. CAL FIRE (Open FI$Cal) is the
largest single source ($10.1B, FY2021-2026). State fire agencies (kind "State fire agency"): Ohio Division of
Forestry (tier 4), CAL FIRE (tier 1; 8 more CAL FIRE unit rows of the registry at tier 4), Idaho Department of
Lands fire program (tier 1), Texas A&M Forest Service (tier 2; a registry district row at tier 4).

## Built sources

| State | Source | Name | Tier | Agencies with rows | Rows | Dollars | Years |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OH | `oh_checkbook_local` | Ohio Checkbook, local governments | 1 | 186 | 702,661 | $1,925,866,499.97 | 2021-2026 |
| OH | `oh_cincinnati` | City of Cincinnati Vendor Payments | 1 | 1 | 33,762 | $40,036,497.68 | 2021-2027 |
| CA | `ca_fiscal` | Open FI$Cal vendor transactions (CAL FIRE) | 1 | 1 | 873,016 | $10,127,477,233.38 | 2021-2026 |
| CA | `ca_riverside_county` | County of Riverside Check Book (Riverside County Fire) | 1 | 1 | 252,798 | $1,657,358,386.01 | 2021-2027 |
| CA | `ca_la` | Checkbook L.A. (Los Angeles City Controller) | 1 | 1 | 175,405 | $696,804,689.78 | 2021-2027 |
| CA | `ca_sf` | San Francisco Vendor Payments (Vouchers) | 1 | 1 | 34,637 | $220,558,400.58 | 2021-2027 |
| CA | `ca_moreno_valley` | City of Moreno Valley Open Expenditures | 1 | 1 | 2,369 | $140,184,292.42 | 2021-2026 |
| CA | `ca_corona` | City of Corona Open Expenditures (CorStat) | 1 | 1 | 13,626 | $21,748,772.69 | 2021-2026 |
| CA | `ca_scprs` | SCPRS purchase orders (CAL FIRE) | 2 | 1 | 22,496 item lines | $883,440,114.00 | 2013-2015 |
| CA | `ca_sco_cities` | State Controller, city reports (fire function) | 3 | 224 | 892 totals | $22,802,615,689.00 | 2021-2024 |
| CA | `ca_sco_districts` | State Controller, special district reports | 3 | 363 | 5,960 totals | $20,330,990,855.00 | 2021-2024 |
| ID | `id_state` | Transparent Idaho state transactions (Department of Lands fire program) | 1 | 1 | 47,000 | $329,402,882.55 | 2021-2027 |
| ID | `id_lgr` | Idaho Local Government Registry, fire district totals | 3 | 156 | 577 totals | $577,476,035.00 | 2021-2024 |
| TX | `tx_houston` | City of Houston checkbook (Houston Fire Department) | 1 | 1 | 105,492 | $296,950,832.31 | 2021-2027 |
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

Owner rule of 2026-10-07 as corrected the same day (decision 9 below), applied per source on the raw columns. Upload
errors are removed first; the identical-line rule runs after them.

| Source | Id columns ignored | Upload-error copies dropped | Identical lines dropped (net) | Void rule kept | Published |
| --- | --- | --- | --- | --- | --- |
| `oh_checkbook_local` | `Id`, `TransactionId` | months uploaded twice 161 ($1,163,019.54); Perkins reload 82 ($86,589.34); 19 batch-total months 1,733 lines ($6.56B of false amounts) | 17,717 in 10,823 groups ($6,506,265.56; 3,743 negative) | 6,267 ($11,634,680.14) | 702,661, $1,925,866,499.97 |
| `oh_cincinnati` | none | - | 0 | 0 | 33,762, $40,036,497.68 |
| `ca_fiscal` | none | - | 1,308 distribution lines ($3,113,705.14) | 0 | 873,016 rows from 3,226,425 distribution lines |
| `ca_riverside_county` | `:id` | - | 25,077 in 5,749 sets ($9,444,820.95) | 134 ($38,324.23) | 252,798 of 277,875 |
| `ca_corona` | `:id` | - | 874 in 303 sets ($85,749.43) | 70 ($305,258.23) | 13,626 of 14,500 |
| `ca_scprs` | none | - | 302 in 112 sets ($2,636,703.36) | 0 | 22,496 item lines |
| `ca_la`, `ca_sf`, `ca_moreno_valley` | `:id` (SF also `data_as_of`, `data_loaded_at`) | - | 0 | 0 | as raw |
| `id_state` | `unique_id`, `date_of_load`, `zz_extract_date` | later load batch 567 ($4,880,745.10); doubled blocks 116 ($75,206.33) | 26 in 25 sets ($138,820.11) | 0 | 47,000 of 47,709 payment lines |
| `tx_houston` | none | - | 3 (-$12,174.28; one is a -$12,400 reversal) | 21 ($450,972.47) | 105,492 of 105,495 |
| `tx_austin`, `tx_dallas` | `:id` | - | 0 | 0 | as raw |
| `tx_dir` | exempt (decision 2) | 8 lines re-reported in a later month ($1,552.62) | - | - | 28,491 item lines |

Against the first reading of the rule (published contract columns only), the corrected rule restores Ohio local
6,356 lines ($11,760,502.05), Cincinnati 10,894 ($1,119,873.72), California 113,059 lines ($550,465,521.51, of
them SCPRS 842 item lines, $3,187,686.46) and Texas 3,065 ($18,657,014.66); Idaho is unchanged. Lines that differ
only in a document number are kept, for example Cincinnati 10,841 (invoice line), LA 4,710, Houston 4,313. Walnut
Township (Fairfield), 2021-11-24 (payment, void, payment, void, payment of $1,551,069.41) nets $1,551,069.41 as
published. Identical voids still raise some nets (first open question).

## Owner decisions

2026-10-06:

1. Payee names are shown as published, private persons included. `common.withhold_person` only withholds payee
   text with an email address or bank account text (`config/payee_name_redactions.csv`). Utah's `build.py` still
   withholds names; align the two at step 1.
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
| OH | $399,549,631 | 93.7% | 3.5% | 0.1% | 6.2% |
| CA | $6,237,728,211 | 93.1% | 2.7% | 1.0% | 5.9% |
| ID | $158,010,689 | 91.3% | 2.6% | 2.0% | 6.7% |
| TX | $497,079,955 | 97.4% | 1.4% | 0.0% | 2.5% |

## Checks (2026-10-07)

- `federal.py normalize` and all 18 adapters' normalize steps, run twice: the 41 files under `data/states/` and
  `config/states/` (and `config/vendor_map.csv`) are byte-identical between the runs and to the committed files.
- `merge_vendor_maps.py --check`: 14,676 rows, 0 problems.
- `tests/multistate/check_federal.py`, `check_oh.py`, `check_ca.py`, `check_id.py`, `check_tx.py`: all pass. They
  recompute totals and the dedup rule from the raw files without importing the adapters; with the rule switched off
  on a scratch copy, each failed.
- `python3 pipeline/build.py`: `data/data.json` and `data/payments.json` byte-identical to the committed files (Utah
  unchanged in this step; 185 of 185 agencies match the raw file).

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
- Identical voids. Rule 2 keeps identical negative lines once, and they count once as reversals, so where identical
  payments were reversed by as many identical voids the family now nets more than the raw lines: Ohio local 607
  families (+$874,766.22; Hamilton Township (Franklin), Global Emergency Vehicles, payment, void, reissue, void,
  reissue: raw $281,250, now $562,500), Riverside County 108 (+$6,840.05), Corona 5 (+$4,707.58), Houston 1
  (Life-Assist invoice 1369849, +$12,400), Idaho 1 (+$1,529.87). Proposed remedy that keeps every net and changes no
  positive line: in a family that has payments, drop an identical negative copy only together with an identical
  positive copy of the same family. It restores 1,155 negative lines; Walnut Township still nets $1,551,069.41.
  Apply it in all four states?
- Riverside County, Corona and SCPRS publish no line number, so equal item lines on one invoice or PO are dropped
  (AT&T PO CF140541 with 22 x $6,500 Cisco routers; Allstar Fire Equipment, 8 x $68,722.95 on one invoice; Corona
  P-card statements with 6 equal hotel nights). Should SCPRS, an item-line source like DIR, keep identical lines
  inside one PO (and Riverside County and Corona inside one invoice)?
- The contract columns leave out invoice and document numbers, so many kept rows look equal to another on the page
  (Houston 2,536, Austin 433, Dallas 96; also Cincinnati and California) although `source_record_id` differs. Add
  the invoice or document number to the description?
- Utah's `pipeline/build.py` keeps lines that repeat inside one upload batch and drops only copies uploaded again in
  a later batch. Apply the owner's rule to Utah at step 1?

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

PRD questions still open: first cities beyond those built, and whether to rename the repository.

## How to rebuild

```
python3 pipeline/sources/federal.py fetch OH CA ID TX      # USFA registry and OpenFEMA grants
python3 pipeline/sources/federal.py normalize OH CA ID TX
python3 pipeline/sources/<st>_<source>.py fetch             # each adapter; raw files are never overwritten
python3 pipeline/sources/<st>_<source>.py normalize
python3 pipeline/sources/merge_vendor_maps.py --check      # folds proposals only if a state wrote vendor_map_additions.csv
python3 tests/multistate/check_<st>.py
```

Python standard library only. Adapters: `oh_cincinnati`, `oh_checkbook_local`; `ca_sco_districts`, `ca_sco_cities`,
`ca_sf`, `ca_la`, `ca_riverside_county`, `ca_corona`, `ca_moreno_valley`, `ca_fiscal`, `ca_scprs`; `id_lgr`,
`id_state`; `tx_dir`, `tx_houston`, `tx_dallas`, `tx_austin`, `tx_cpa`.
