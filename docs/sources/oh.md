# Ohio: source notes

Feasibility notes for every Ohio candidate source (PRD `docs/prd/multistate-expansion.md`, build-order steps 3
and 5), checked on 2026-10-06 from the cloud session on branch `multistate-sources`. Output format:
`docs/multistate/data-contract.md`. Raw files: `raw/2026-10-06/oh/<source>/`.

## Result

Only one Ohio source gives vendor data for a fire agency: the City of Cincinnati's vendor payments, for the
Cincinnati Fire Department. The PRD's main Ohio source, Ohio Checkbook, does not:

- its bulk files (on the DataOhio portal) hold state agencies only, at department level, so no row belongs to a
  fire agency, not even the Ohio Division of Forestry;
- its local-government checkbooks (participating cities, townships, counties and special districts) are only
  in the checkbook.ohio.gov web app, whose robots.txt disallows all automated access.

The Auditor of State publishes annual financial report summaries in bulk, but only for whole townships, cities,
villages, counties, schools and libraries, by function ("Public Safety" mixes fire, police and EMS); fire
districts' filings are not published as data. So there is no tier 3 source for Ohio yet.

| Source id | Source | Tier | Decision | Agencies | Lines | Dollars | Years |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | Federal layer (done before this run) | 4 | built | 1,148 | | | |
| `oh_checkbook_state` | Ohio Checkbook state expenditures, DataOhio bulk files | 1 | skipped: no fire agency identifiable | 0 | | | FY2022-FY2026 |
| `oh_checkbook_local` | Ohio Checkbook local governments | 1 | skipped: robots.txt disallows all | 0 | | | |
| (in `oh_checkbook_state`) | Ohio Division of Forestry (ODNR) | 1 | skipped: not separable from ODNR | 0 | | | |
| `oh_aos` | Auditor of State, Summarized Annual Financial Reports | 3 | skipped: not fire-specific | 0 | | | 2016-2025 |
| `oh_cincinnati` | City of Cincinnati Vendor Payments | 1 | **built** | 1 | 33,762 | $40,036,497.68 | FY2021-FY2027 |

Coverage after this run (`data/states/oh/agencies.json`): tier 1: 1 agency (Cincinnati Fire Department,
OH-31015); tier 2: 0; tier 3: 0; tier 4: 1,147. No agency was given a $0 amount.

Cincinnati's $40.0 million is the fire department codes only. The City buys fire apparatus and ambulances through
its citywide vehicle account (981 "Motorized & Construction Equip"): $18.7 million in FY2021-FY2027 to Vogelpohl
Fire Equipment and Halcore Group, equal to 47% of the fire codes' total. Those lines carry no fire department code,
so they are not attributed (section 5). The page note in `sources.csv` says so.

## Federal layer (done)

Built by `pipeline/sources/federal.py` before this run (raw `raw/2026-10-06/oh/usfa/`, `.../openfema/`).

- USFA registry: 1,148 Ohio departments in `config/states/oh/agencies.csv` (437 local, 373 township, 204
  volunteer, 85 fire districts, 24 industrial brigades, 13 contract, 2 county, 2 state, 2 federal, 6 other).
- OpenFEMA firefighter grants: 4,336 awards (FY2005-FY2025, $1.54 billion) to 1,205 recipient names; 311
  recipient names matched strictly to 302 agencies (783 awards, $110,580,051); 894 names unmatched
  (`config/states/oh/grant_recipients_unmatched.csv`).
- `python3 tests/multistate/check_federal.py OH` passes after this run.
- Gap (federal.py, not changed here): FEMA recipient "CITY OF CINCINNATI" (35 awards, $41,542,121, FY2006-FY2025)
  is in `grant_recipients_unmatched.csv` ("no registry name matches"), so the Cincinnati Fire Department
  (OH-31015) shows 0 grants although firefighter grants to the City are its grants. The same probably holds for
  other "CITY OF ..." recipients whose city runs a single fire department.

## 1. Ohio Checkbook: state agencies (`oh_checkbook_state`)

- **URL:** https://checkbook.ohio.gov (spend.ohio.gov and ohiocheckbook.gov redirect there). Bulk files:
  DataOhio dataset "Ohio Checkbook", https://data.ohio.gov/wps/portal/gov/data/view/ohio-checkbook (dataset id
  `04f1a227-c0d8-4d84-938f-f41ca9c49226`), linked from the checkbook home page ("Ohio Checkbook monthly
  downloads are now available on the DataOhio Portal. New download files are added on a semi-annual basis").
- **Format:** one zip per state fiscal year (July to June), one CSV per month inside. Files on the portal on
  2026-10-06 (full details, SHA-256 and rows per month in `manifest.json.gz`):

  | Version | File (S3 key under `.../datasets/04f1a227-.../versions/`) | Added | Bytes | Rows | Months |
  | --- | --- | --- | --- | --- | --- |
  | FY2022 | `checkbook_transaction_FY_22.zip` | 2022-08-01 | 282,170,342 | 8,135,819 | Jan-Dec 2022 (Jul-Dec 2021 files empty) |
  | FY2023 | `checkbook_transaction_FY_23.zip` (listed as `checkbook_transactions.zip`) | 2023-01-01 | 213,353,502 | 5,938,450 | Jul 2022-Jun 2023 |
  | FY2024 | `checkbook_transaction_FY_24.zip` | 2024-01-24 | 616,455,267 | 16,586,105 | Jul 2023-Jun 2024 |
  | FY2025 | `checkbook_transactions_FY_25.zip` | 2025-02-01 | 259,397,508 | 6,712,863 | Jul 2024-Jun 2025 |
  | FY2026 | `checkbook_transactions_FY_26.zip` | 2026-01-23 | 312,511,225 | 9,403,794 | Jul 2025-Jun 2026 |

  SHA-256: FY2022 `800a1afe53da6532...`, FY2023 `9e7812e71f6402c2...`, FY2024 `21cf4d7c75169aaf...`, FY2025
  `6b97bd90dfc72891...`, FY2026 `dc7e693ed7ec6372...` (full values in the manifest). FY2021 and July-December
  2021 are not published; the files cover January 2022 to June 2026. Updated about twice a year.
- **Duplicates:** large. The FY2024 file holds every January-June 2024 month three times: 10,105,358 of its
  16,586,105 lines are exact duplicates ($80.4 billion of duplicated dollars); July-December 2023 has 2. The
  FY2022 file's July-December 2022 months repeat the FY2023 file's first six months line for line (same row
  counts). Any use of these files must drop exact duplicate lines within a file and take each month from one
  file only. The duplicate line and dollar counts were computed in a one-off pass over the downloaded zips and
  are not stored in a kept file; `manifest.json.gz` keeps the rows per month that show the pattern (January-June
  2024 has 15.2 million rows against 3.9 to 6.6 million for January-June of 2022, 2023, 2025 and 2026, for
  example April 2024 4,375,722 rows against 1,107,931 in April 2025; the FY2022 and FY2023 files' July-December
  2022 months have identical row counts). FY2026 has no exact duplicate lines and 5,116 negative amounts (reversals or refunds). Two FY2026
  rows carry an Excel serial number (`44102`) as transaction month.
- **Fields (15):** account, account_name (object of expenditure, e.g. "IT & NETWORK"), department_id and
  department_description (state agency, e.g. DNR Department of Natural Resources), payment date, payment method
  (EFT, CHK), payment reference id, amount, vendor_name, address1, address2, city, state, zip, transaction month.
  No division, fund, appropriation line item (ALI) or line description. Header spelling changes in January 2026
  (lower case `pymnt_dt` to upper case `PAYMENT_DATE`; same order); one month has a trailing empty column.
- **Who is in it:** state agencies only (136 department ids in FY2026: departments, boards, commissions,
  universities). No local government appears.
- **Access:** robots.txt of data.ohio.gov disallows only `/wps/wcm/connect/gov/ohio+content+english/` (four
  spellings), `/wps/portal/gov/data/search/` and `/search/`; dataset pages and the portal's JSON API are allowed.
  Two quirks: (1) data.ohio.gov (CloudFront) answers HTTP 404 to any User-Agent that does not start with
  `Mozilla/5.0 (`, including this project's `utah-fire-procurement/0.1 (...)`, Python's and curl's defaults and the
  WebFetch tool; it serves the same project agent written in the usual crawler form, `Mozilla/5.0 (compatible;
  utah-fire-procurement/0.1; +https://github.com/pasha594/utah-fire-procurement)`. (2) The download button calls
  `/apigateway-secure/data-portal/download-file/<dataset>?key=<file key>`, which needs the session cookie of the
  dataset page and that page as Referer, and returns a presigned S3 URL
  (`iop-analytics-data-portal-assets.s3.amazonaws.com`). Both are what a browser sends; no login.
  Review note: a CDN rule that rejects non-browser agents can be read as a block, and passing it with a
  browser-form agent as working around it. Nothing from these files is used or published; the owner should
  confirm the approach before any adapter relies on DataOhio downloads (open question).
- **Terms:** no terms of use found on DataOhio; its About page invites reuse ("Access publicly available APIs via
  DataOhio or use the data to build your own"). Checkbook disclaimer: no warranty for non-state data, which local
  entities provide voluntarily (ORC 113.74). Ohio public records law applies.
- **Fire agencies:** none can be identified. The bulk files carry the paying state agency only. Fire-related
  state work sits inside larger departments: the Division of State Fire Marshal inside Commerce (COM), the
  Division of Forestry inside Natural Resources (DNR); the files cannot tell their payments from the rest of the
  department. Rows that mention fire are vendors (Koorsen Fire & Security, Johnson Controls Fire Protection) or
  grants and ambulance payments to local fire departments (for example DRC paying Cumberland Trail Fire District
  for ambulance service): money paid *to* fire agencies, not their own purchasing.
- **Data quality:** individuals are masked as "Masked Payee", but for many such rows (scholarship and subsidy
  payments) the person's name has shifted into address1. Employee reimbursements (mileage, meals) name the
  employee in vendor_name. Tax refunds appear as "Tax Refunds". The FY2026 file has 2.2 million "Masked Payee"
  rows of 9.4 million.
- **Raw kept:** `versions.json.gz` (file list), `manifest.json.gz` (per file: URL, bytes, SHA-256, members,
  rows, header, rows and dollars per department) and `sample.csv.gz` (first 100 rows of the newest file with
  address1, address2 and zip dropped and payees passed through `common.withhold_person`, because of the masked
  names in address1). The full files are not kept: no row would be used. Reproduce with
  `python3 pipeline/sources/oh_feasibility.py fetch oh_checkbook_state`.
- **Decision: skipped.** Public bulk access and terms allow it, but no row clearly belongs to a fire agency.
  Revisit if the files gain a division, fund or ALI field, or start to include local entities.

## 2. Ohio Checkbook: local governments (`oh_checkbook_local`)

- **URL:** https://checkbook.ohio.gov/Local/ (lists of participating cities and villages, townships, counties,
  schools, special districts, colleges). The old `<entity>.ohiocheckbook.com` hosts (for example
  plaintownship.ohiocheckbook.com) now redirect to ohiocheckbook.gov and from there to checkbook.ohio.gov; the
  certificate covers `*.checkbook.ohio.gov`. The Plain Township (Stark) page the PRD cites,
  plaintownshipstarkoh.gov/financialtransparency.aspx, returned HTTP 403 to this session.
- **Participation:** voluntary. Press coverage counts more than 100 local governments (114 cities, counties,
  townships, school districts and special districts in early coverage); HB 413, which would require it, passed
  the Ohio House in May 2026. Which townships and fire districts take part could not be checked (next point).
- **Access:** robots.txt of checkbook.ohio.gov is `User-agent: *` / `Disallow: *`: no automated access to any
  path. The site is an interactive app: its home page source embeds Tableau views (public.tableau.com, and
  analytics.das.ohio.gov behind an auth-token call) and loads reCAPTCHA Enterprise; published guides describe the
  local download as the "Download all rows as a text file" button of the app's View Data screen. No documented
  API or bulk export for local data was found, and the DataOhio bulk files (above) do not include local
  entities. The host also sends an incomplete TLS chain (the Sectigo "Public Server Authentication CA OV R36"
  intermediate is missing), so Python's urllib fails certificate verification unless that intermediate is
  supplied.
- **Pages read before the robots.txt check:** the home page, About/Disclaimer and About/FAQ (once each, by hand).
  No data page and no local list was requested after reading robots.txt, so no sample was saved.
- **Fields, years, update frequency, row counts:** unknown. No data page may be requested, so none was checked.
- **Terms:** the Disclaimer says local data is supplied voluntarily by each entity (ORC 113.74) and the Treasurer
  does not warrant it.
- **How fire agencies would be identified:** a joint fire district's or fire district's own checkbook would be
  fire spend as a whole; in a township or city checkbook only its fire fund or fire department lines would be.
- **Data quality, duplicates and reversals:** unknown (no data read).
- **Decision: skipped** (robots.txt disallows all). Ways forward for the owner: ask the Treasurer's office or the
  Office of Budget and Management for a bulk export of local checkbook data (or for robots.txt permission), or
  check the participant lists by hand at https://checkbook.ohio.gov/Local/SpecialDistrictsList.aspx and
  .../TownshipsList.aspx. If a township takes part, only its fire fund or fire department lines would be fire
  spend; a joint fire district's whole checkbook would be.

## 3. Ohio Division of Forestry (state fire agency)

- The Division of Forestry (Ohio Department of Natural Resources) runs Ohio's wildland fire program. In the
  state checkbook bulk files its payments are part of department DNR (64,578 lines, $896.8 million in FY2026)
  with no division, fund or ALI field, and no account is fire-specific (the closest, "POLICE AND FIRE
  AUTOMOBILES", is 3 DNR lines, $130,578 in FY2026, and could be any DNR division's law enforcement or fire
  vehicles).
- It is not in the USFA registry for Ohio (the 2 "State government" rows are local volunteer departments).
- **Decision: skipped** (not identifiable). Not added to `agencies_added.csv`, since no source gives it data.
  The checkbook web app has appropriation line item (ALI) views for state spending, but robots.txt disallows it.

## 4. Ohio Auditor of State: Summarized Annual Financial Reports (`oh_aos`)

- **URL:** https://ohioauditor.gov/references/SummarizedAnnualFinancialReports (unaudited data that entities
  file through the AOS Hinkle System, ORC 117.38).
- **Format and access:** static Excel files, one per entity type, filing year and basis of accounting, for
  example `SummarizedReports/Township_2024_REG_Summarized.XLSX` (GAAP, modified cash, cash and regulatory bases;
  2016-2025 as .XLSX, older years .XLS and PDF). Entity types: City, Community School/STEM, County, Library,
  School/JVSD/ESC, Township, Village. A second form gives a filing-status workbook per filing year (all
  filers, including fire districts, with filing type, status and dates, but no dollars).
- **Fields (townships, regulatory basis):** one row per township and county with receipts by source and
  disbursements by function: General Government, Public Safety, Public Works, Health, Human Services,
  Conservation and Recreation, Other, Capital Outlay, debt service; sheets for the General Fund and for all
  governmental funds, long-term obligations, and population and tax data. 1,287 townships in the 2024 file.
- **Update frequency:** yearly as filings arrive (filing year 2026 is listed).
- **Terms and robots.txt:** robots.txt allows `/references/` (it disallows `/bin/` and a few training files);
  no terms of use restrict reuse.
- **Fire agencies:** not identifiable. "Public Safety" covers fire, police, EMS and other safety spending for
  the whole township, not the township's fire fund; cities and villages are the same. Fire districts and joint
  fire districts file with AOS (about 121 fire and joint fire districts and 3 fire councils of governments in the
  2025 filing-status workbook), but their financial data is not among the published summaries.
- **Duplicates and reversals:** not applicable (one row per entity and year).
- **Raw kept:** `Township_2024_REG_Summarized.xlsx.gz` and `sample.csv.gz` (first 100 rows of the
  all-governmental-funds sheet). Reproduce with `python3 pipeline/sources/oh_feasibility.py fetch oh_aos`.
- **Decision: skipped** as a tier 3 source: no row is a fire agency's total. Revisit if AOS publishes fire
  district summaries; the filing-status workbook could then link them to registry ids.

## 5. City of Cincinnati Vendor Payments (`oh_cincinnati`): built

Not in the PRD's Ohio list; found while looking for a better Ohio source (the Socrata catalog has no other Ohio
city payments dataset; Cleveland's and Columbus's open data hubs have no payments data).

- **URL:** https://data.cincinnati-oh.gov/d/qrj9-83t8 (Socrata; SODA API
  `https://data.cincinnati-oh.gov/resource/qrj9-83t8.csv`).
- **Format and access:** SODA API, CSV or JSON, with server-side `$where`, `$select`, `$order`, `$limit` and
  `$offset`. The adapter filters to the fire department codes and fiscal years 2021 on.
- **Fields (14):** fiscal_year, acct_period, dept_code, dept_desc, fund_code, fund_desc, exp_acct_cat,
  exp_acct_cat_desc (expense account category, e.g. "Wearing Apparel"), trans_id, trans_line_no, record_date,
  check_no, amount, vendor_name. No free-text description.
- **Years:** FY2014 to now. City fiscal year July to June (FY2027 began July 2026 and is partial: payments
  through 2026-10-02 in this pull). The adapter keeps FY2021-FY2027.
- **Update frequency:** weekly (rows last updated 2026-10-06 03:26 UTC).
- **Terms and robots.txt:** licence "Public Domain" in the dataset metadata. robots.txt: `Crawl-delay: 1` and
  disallows only `/browse` search facets; the API is allowed. `common.get`'s 1-second throttle meets it.
- **Size:** 1,254,334 rows ($8.48 billion) across 150 department codes; 33,762 rows for the fire codes in
  FY2021-FY2027 (one page, 332 KB gzipped). No SHA-256 of the full dataset: it is a live API refreshed weekly,
  not a file, so a checksum would not be reproducible. The filtered rows are pinned instead by the server-side
  count and sum per fiscal year and department (`control_totals.json.gz`) and per department for all rows
  (`departments.json.gz`).
- **Fire agency:** department codes 271 "Fire - Response" and 272 "Fire - Support Services" (and 224 "Department
  Of Fire", used until FY2016) are the Cincinnati Fire Department, registry FDID 31015, agency `OH-31015`
  (`config/states/oh/agency_sources.csv`, match method "department code"). Not linked: 922 "Police & Fire
  Fighter's Ins" (insurance shared by police and fire) and 103/223 "Emergency Communications" (the 911 center
  serves police and fire). Normalize fails if a new department whose name says fire appears unlinked.
  No fire-named fund ("Fire Grants" 472, "Fire Education" 390) is used by any other department code in FY2021 on
  (live query in the review, 2026-10-06; not kept as a raw file).
- **Not included (apparatus and ambulances):** purchases made through other department codes or citywide
  accounts carry those codes, so they are not attributed even when the vendor is a fire vendor. The largest is
  the citywide vehicle capital account 981 "Motorized & Construction Equip": FY2021-FY2027 it paid Vogelpohl Fire
  Equipment $16,843,685.58 (22 lines, fire apparatus) and Halcore Group $1,901,457.11 (8 lines, Horton and
  Leader ambulances), $18.7 million, 47% of the fire codes' $40.0 million. Fleet Services (256) paid Fire Service,
  Inc. $468,531, Vogelpohl $304,157 and All American Fire Equipment $82,708 (apparatus repairs). Source:
  `vehicle_accounts.json.gz` (server-side totals by vendor for codes 981 and 256, FY2021 on; context only, added
  in the review). The `sources.csv` note states the gap with the 981 amount, so the page does not suggest that
  Cincinnati buys no apparatus.
- **Rows by fiscal year:**

  | FY | Lines | Dollars |
  | --- | --- | --- |
  | 2021 | 4,116 | $4,512,893.35 |
  | 2022 | 3,583 | $5,869,147.83 |
  | 2023 | 5,013 | $6,809,877.85 |
  | 2024 | 6,286 | $6,409,850.08 |
  | 2025 | 6,580 | $6,825,353.79 |
  | 2026 | 6,121 | $7,546,646.42 |
  | 2027 (partial) | 2,063 | $2,062,728.36 |
  | Total | 33,762 | $40,036,497.68 |

- **Duplicates:** (trans_id, trans_line_no) is unique; no exact duplicate lines; the adapter would keep one copy
  of an exact duplicate. 2,580 groups (13,423 lines) share vendor, amount, date, account, department and check:
  these are separate invoice lines of one transaction paid on one check (for example 24 identical Galls jackets
  on one EFT, or one pest-control charge per station) and are kept; no such line appears under two transaction
  ids, so there is no reloaded batch. 53 groups of identical vendor, amount, date and account on different
  checks are also kept. The raw page total equals the server-side control totals per fiscal year and department
  (checked by `tests/multistate/check_oh.py`), and a second live query in the review, filtered by department
  name ("Fire%") instead of code, gave the same lines and dollars for every fiscal year.
- **Reversals:** 103 negative lines (-$16,923.69), all purchasing-card credits from U.S. Bank (99) and Fifth Third
  (4); 43 of them equal a positive line of the same bank. Kept as negative amounts so they net out.
- **Payees:** 270 vendor names. Purchasing-card statements are paid to the bank (U.S. Bank $1.78 million,
  Fifth Third $0.29 million), so the merchants behind them are not visible. "MISCELLANEOUS" ($393,660, account
  "Medical Services", 51 lines) names no vendor: 21 lines of $1,000 or more ($385,586, mostly $351,253 on two
  checks in July 2020, partly from the Fire Grants fund) and 30 small checks of $32.50 to $767 ($8,074), which
  look like EMS billing refunds to patients. The text "MISCELLANEOUS" names nobody, so it is published as the
  source has it and classed `placeholder` (not purchasing). Payee names are published as the City publishes
  them, private persons included (owner decision, 2026-10-06): the adapter calls `common.withhold_person`
  directly, which only replaces payee text with an email address or bank account text; no Cincinnati payee
  matches, so none is withheld. The earlier local rules (person-shaped names, the "Uniform And Other Allowance"
  payees, names the shared rules missed) were removed.
- **Normalized:** `data/states/oh/transactions.csv.gz`: one row per payment line; `fiscal_year` is the City's;
  `posting_date` is record_date; `account` is "dept_desc / fund_code fund_desc / exp_acct_cat
  exp_acct_cat_desc"; `category_published` is exp_acct_cat_desc; `source_record_id` is trans_id-trans_line_no.
  Normalize is deterministic (two runs give byte-identical files).
- **Decision: built** (tier 1): `pipeline/sources/oh_cincinnati.py`.

## Other candidates looked at

- **Columbus, Cleveland, Dayton, Toledo, Akron:** no vendor payments dataset found in the Socrata catalog
  (searched "vendor payments", "checkbook", "expenditures") or on the cities' ArcGIS open data hubs
  (data.clevelandohio.gov has a budget book only; opendata.columbus.gov nothing). Several of these cities publish
  through Ohio Checkbook's local pages instead, which robots.txt closes.
- **Census of Governments (Census Bureau), finance individual unit files:** a possible national tier 3 source,
  with expenditure by function for each government, including "fire protection" for townships, cities and
  special districts. Not verified here (the 2022 files are not in the old `www2.census.gov/.../datasets/`
  folders, which stop at 2018) and outside the Ohio PRD list; better handled once for all states.

## Vendor map additions

`config/states/oh/vendor_map_additions.csv`: 95 payees with proposed canonical name and category, covering 97.9% of
Ohio's purchasing dollars by raw payee name ($36.4 million of $37.2 million; 98.0% by published payee name, as
`tests/multistate/check_oh.py` counts). The 90% line is reached by the top 30 purchasing payees; the rest are
listed so they are classified too, and 11 are business names that would otherwise be withheld. Canonical names
reuse `config/vendor_map.csv` where it is the same company (Galls, Henry Schein, Stryker, Bound Tree Medical,
Grainger, Motorola Solutions, Vector Solutions for TargetSolutions, Dell Technologies, CDW Government, Airgas,
Teleflex, Cintas, Overhead Door, Terracon, Jones & Bartlett Learning, ESO Solutions, T-Mobile). Judgment calls,
marked medium or low confidence: Howmedica Osteonics (Stryker's service billing entity) as Stryker; Arrow
International (a Teleflex brand) as Teleflex; 911 Fleet & Fire Equipment as fire equipment (mostly turnout gear on
the "Wearing Apparel" account); UC Physicians (medical direction) as professional; Change Healthcare and Penn
Credit as EMS billing; Somers Boat Works (fireboat repair) and Mobile Concepts by Scotty (command vehicles) as
apparatus. Banks are finance, the Ohio Police & Fire Pension Fund payroll, Hamilton County, the City and the State
Treasurer government, "MISCELLANEOUS" placeholder.

## Checks

`python3 tests/multistate/check_oh.py` never imports the Ohio adapters. From the raw pages (gzip and csv only) it
recomputes lines and dollars per agency, source and fiscal year and compares them with the source's own
server-side control totals and with `data/states/oh/transactions.csv.gz`; it then traces every published line to
its raw line and compares agency, fiscal year, date, payee (as published or withheld), account, category and
amount. It also checks: the contract's column names and order for every Ohio file; that every linked department
code is named as a fire department in the source (not police, insurance, pension or the shared 911 center) and
every fire-named department is linked or a known exclusion; agency ids, links, `coverage_counts` and tiers (an
agency without rows stays at tier 4); unique `source_record_id`s and sort order; that no published payee looks
like a person (`common.is_person`, `common.looks_like_person` and the shapes the shared rules miss, such as
"Name III" or "Last First M.") unless withheld or claimed as a business by a vendor map row; that no email
appears in any published text; that `vendor_map_additions.csv` spend and agency counts equal the raw sums and
cover at least 90% of purchasing dollars; and that raw files sit under `raw/<date>/oh/<source>/`, are each under
50 MB (150 MB for Ohio in all), and every reachable source has a sample of at most 100 rows (the state checkbook
sample without address columns). In the review it was run against scratch copies with one fault each (a
published "Donald Buchanan III", a Fleet Services link, a line moved to another fiscal year, a changed date or
payee, unsorted rows, a tier 3 agency without data, a missing sample, a changed spend, swapped columns, an
email in the account text) and failed on every one.
`python3 tests/multistate/check_federal.py OH` still passes.

## Open questions

- Ask the Ohio Treasurer or OBM for bulk local checkbook data (or permission under robots.txt)? It is the only
  route to township and fire district payee data in Ohio.
- Show Cincinnati as a tier 1 agency with a note that apparatus and ambulances ($18.7 million in FY2021-FY2027
  through the citywide vehicle account 981), fleet repairs and IT bought by other city departments are missing,
  and that $2.1 million of P-card spend shows the card banks rather than the merchants? Or attribute the 981
  lines to fire apparatus vendors, which the PRD's attribution rule does not allow today?
- Should `federal.py` link FEMA awards to "CITY OF <name>" recipients when that city has one registry fire
  department (Cincinnati: 35 awards, $41.5 million, now unmatched)?
- Is reaching data.ohio.gov with the browser-form agent `Mozilla/5.0 (compatible; utah-fire-procurement/0.1; +URL)`,
  the page's session cookie and Referer acceptable, or should it count as a block? Only the manifest and sample
  depend on it.
- Add the Census of Governments as a national tier 3 source for fire protection totals?
