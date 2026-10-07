# California: source notes

Run of 2026-10-06 (raw folder `raw/2026-10-06/ca/`; every fetch in this run was made on 2026-10-06). PRD:
`docs/prd/multistate-expansion.md`; output format: `docs/multistate/data-contract.md`. California fiscal years run July
to June and are written as the year they end in (FY2024 = July 2023 to June 2024).

## Result

| Source id | Source | Tier | Decision | Agencies with rows | Rows | Dollars | Years |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | Federal layer (USFA registry, OpenFEMA grants) | 4 | built earlier (`federal.py`) | 853 registry departments, 195 with grants | 579 matched awards | $255.3M matched | grants FY2005-FY2024 |
| `ca_sco_districts` | State Controller, Special Districts - Expenditures | 3 | **built** | 363 | 5,960 totals rows | $20.33B | FY2021-FY2024 |
| `ca_sco_cities` | State Controller, City - Expenditures (Fire function) | 3 | **built** | 224 | 892 totals rows | $22.80B | FY2021-FY2024 |
| `ca_sf` | San Francisco Vendor Payments (Vouchers) | 1 | **built** | 1 (San Francisco Fire Department) | 34,637 lines | $220.6M | FY2021-FY2027 (FY2027 partial) |
| `ca_la` | Checkbook L.A. (Los Angeles City Controller) | 1 | **built** | 1 (Los Angeles Fire Department) | 175,405 lines | $696.8M | FY2021-FY2027 (FY2027 partial) |
| `ca_riverside_county` | County of Riverside Check Book | 1 | **built** | 1 (Riverside County Fire Department) | 252,798 lines | $1,657.4M | FY2021-FY2027 (FY2027 partial) |
| `ca_corona` | City of Corona Open Expenditures (CorStat) | 1 | **built** | 1 (Corona Fire Department) | 13,626 lines | $21.7M | FY2021-FY2026 |
| `ca_moreno_valley` | City of Moreno Valley Open Expenditures | 1 | **built** | 1 (Moreno Valley Fire Service) | 2,369 lines | $140.2M | FY2021-FY2026 |
| `ca_fiscal` | Open FI$Cal department vendor transactions (CAL FIRE) | 1 | **built** | 1 (CAL FIRE, state fire agency) | 873,016 rows (3,226,425 source lines) | $10,127.5M | FY2021-FY2026 (FY2026 to 2026-06-30) |
| `ca_scprs` | SCPRS Purchase Order Data (CAL FIRE purchase orders) | 2 | **built** (old years only) | 1 (CAL FIRE) | 22,496 item lines | $883.4M | FY2013-FY2015 only |
| `ca_sandiego` | City of San Diego Operating Actuals | - | skipped: no payee; sample kept | 0 | - | - | - |
| `ca_sacramento` | City of Sacramento Checks Issued, Purchase Orders | - | skipped: no department field; samples kept | 0 | - | - | - |
| `ca_lacounty` | County of Los Angeles Open Expenditures | - | skipped: no payee; sample kept | 0 | - | - | - |
| `ca_modesto` | City of Modesto Weekly AP Transactions | - | skipped: weekly figures only; sample kept | 0 | - | - | - |
| (none) | San Jose, Indio, West Hollywood, Marin County, others | - | skipped (see "Other candidates") | 0 | - | - | - |

**Owner dedup rule of 2026-10-07 ("drop identical lines, drop identical days"), as corrected the same day, applied
to every line source above:** two raw lines are identical when every column the source publishes in its raw file is
equal except the columns that only identify the row or the load (Socrata `:id`; in San Francisco also `data_as_of`
and `data_loaded_at`; Open FI$Cal and SCPRS have none). Voucher, invoice, payment, PO and line numbers are content, so
lines that differ in one are different payments and are kept. Identical lines are kept once, except that a set of n
identical positive lines keeps min(n, reversals + 1) copies, so a payment, its void and an identical reissue keep
their net. It drops 27,561 lines and $15.3M (tier 1: 27,259 lines, $12.6M, 0.10% of tier-1 dollars; SCPRS 302 item
lines, $2.6M); the void part keeps 204 copies ($343,582.46). Lines that repeat inside one invoice or PO are dropped
only where the source has no line number (Riverside County, Corona, SCPRS) and in FI$Cal, whose repeated lines carry
the same document id, line and distribution number. The first version of the rule (published columns only, run
earlier on 2026-10-07) dropped 139,312 lines and $562.6M, most of them separate payments; this version restores
112,217 tier-1 lines ($547.3M) and 842 SCPRS lines ($3.2M). Numbers per source: "Duplicates and reversals: summary"
below.

`data/states/ca/agencies.json` after this run: 926 agencies (853 registry rows plus 73 fire districts and fire
authorities added from the State Controller's data), coverage tier 1: 6, tier 2: 0, tier 3: 584, tier 4: 336. CAL FIRE
is tier 1 (its tier-2 SCPRS lines are older). No agency without vendor data has a $0 row: tier-3 rows are published
totals only, and no row is written for an agency a source does not cover.

Checks: `python3 tests/multistate/check_ca.py` and `python3 tests/multistate/check_federal.py CA` both pass (see
"Checks").

## Access, robots.txt and terms (all hosts used)

Every source section below takes its terms of use and robots.txt from this table. All requests go through
`common.get` (1 request per second, the project's User-Agent). Socrata hosts publish a
`robots.txt` with `Crawl-delay: 1` that disallows only catalog browse filters (`/browse?...`), not the SODA API or
`/api/views/<id>.json`; the throttle meets the crawl delay.

| Host | Used by | robots.txt | Terms / licence |
| --- | --- | --- | --- |
| `bythenumbers.sco.ca.gov` (Socrata) | `ca_sco_districts`, `ca_sco_cities` | Crawl-delay 1; browse filters only | Public Domain (dataset licence), attribution California State Controller's Office |
| `data.sf.gov` (Socrata; `data.sfgov.org` redirects) | `ca_sf` | Crawl-delay 1; browse filters only | Open Data Commons PDDL, attribution SF Controller's Office |
| `controllerdata.lacity.org` (Socrata) | `ca_la` | Crawl-delay 1; browse filters only | CC BY 4.0, attribution "Controller" (City of Los Angeles) |
| `data.countyofriverside.us` (Socrata) | `ca_riverside_county` | Crawl-delay 1; browse filters only | Public Domain U.S. Government, attribution RCIT |
| `corstat.coronaca.gov` (Socrata) | `ca_corona` | Crawl-delay 1; browse filters only | Public Domain (with the City's data disclaimer) |
| `moreno-valley.data.socrata.com` (Socrata) | `ca_moreno_valley` | Crawl-delay 1; browse filters only | none stated on the dataset |
| `open.fiscal.ca.gov`, files on `adwoutputfilesadlsstore.blob.core.windows.net` | `ca_fiscal` | none (`open.fiscal.ca.gov/robots.txt` answers a not-found page; the blob host answers an XML error) | Open FI$Cal Terms of Use: "You may use the data as you wish provided your use is neither illegal nor malicious"; data raw and unaudited |
| `data.ca.gov` (CKAN) | `ca_scprs` | disallows `/api/`, `/datastore/`, `/search?`, `/user/`; the `/dataset/.../download/` file link is allowed | no licence on the dataset (California Open Data Policy); no restriction on automated access found |
| `seshat.datasd.org`, `data.sandiego.gov` | `ca_sandiego` (sample) | seshat answers 403 to `/robots.txt`; data.sandiego.gov has none (404) | City of San Diego open data (no restriction found) |
| `data.cityofsacramento.org` (ArcGIS Hub); data on `services5.arcgis.com` | `ca_sacramento` (samples) | hub: Crawl-delay 60; services5: none (Esri 403) | not assessed further (no department field); samples only |
| `data.lacounty.gov` (ArcGIS Hub); data on `services.arcgis.com` | `ca_lacounty` (sample) | hub: Crawl-delay 60; services: none | samples only |
| `data.modestogov.com` (Socrata) | `ca_modesto` (sample) | Crawl-delay 1 | none stated |
| `indio.data.socrata.com` | not used | `Disallow: /` for every agent | not fetched |
| `data.sanjoseca.gov` (CKAN) | not used | disallows `/api/`, `/datastore/` | no payment dataset exists |
| `caleprocure.ca.gov` (Cal eProcure SCPRS search) | not used | answers 403 to `/robots.txt` | interactive search only, no bulk export |

## Federal layer (`usfa`, `openfema`)

Built by `pipeline/sources/federal.py` before this run and not changed by it: 853 USFA registry departments in
`config/states/ca/agencies.csv` (334 local fire departments, 253 fire districts, 103 volunteer fire departments, 9
CAL FIRE and CDF rows with kind "State fire agency", 29 other state government rows (mostly state prisons, hospitals
and universities), 36 federal, 31 county fire departments, and others; kinds as `federal.py` sets them on
2026-10-07);
579 OpenFEMA firefighter grant awards ($255.3M, FY2005-FY2024) to 195 registry departments matched strictly
(`grant_recipients.csv`); 655 recipients with 2,696 awards are unmatched (`grant_recipients_unmatched.csv`).
`check_federal.py CA` passes: "853 registry agencies, 195 with grants, $255,287,987".

## `ca_sco_districts`: State Controller, Special Districts - Expenditures (tier 3, built)

- **URL:** <https://bythenumbers.sco.ca.gov/d/m9u3-wdam> (catalog.data.gov: "Special Districts - Expenditures").
- **Format and access:** Socrata SODA API (JSON), paged with `$limit`/`$offset` in `:id` order; the fire filter is
  server-side SoQL: `fiscalyear >= 2021 AND (activity = 'Fire Protection' OR upper(entityname) like '%FIRE%' OR ...
  '%RESCUE%' OR ... '%EMERGENCY%')`.
- **What it is:** the expenditure part of the Financial Transactions Report every special district files with the
  State Controller: one row per entity, fiscal year and report line. Fields: `entityname`, `county`, `city_state`,
  `zip_code`, `activity` (the SCO's function, "Fire Protection"), `districttype2` (Independent, Dependent, Joint
  Powers Authority), `sd_type`, `category` (fund type), `subcategory1`, `subcategory2`, `linedescription`, `value`,
  `fiscalyear`, `rownumber`.
- **Years and updates:** FY2002-03 to FY2023-24 (FY2024 is the latest; rows last updated 2025-10-30); yearly. Taken:
  FY2021-FY2024.
- **Fire agencies:** `activity = 'Fire Protection'` (348 entities in FY2021-FY2024, all linked), plus fire authority
  JPAs found by name (JPAs carry the activity "Joint Powers Authority"; 17 that run a fire department are linked, such as
  Orange County Fire Authority and Livermore-Pleasanton Fire Department) and 1 community services district that runs a
  fire department. 49 fire-named entities are not fire agencies and are listed with the reason in the adapter's
  `NOT_FIRE` (11 fire-escape road divisions, 6 EMS agencies, dispatch, insurance pools, training centres, ambulance
  JPAs; EMS-only agencies stay out, in line with owner decision 3 on ambulance-only districts); normalize stops on any
  fire-named entity in neither list.
- **Matching:** 366 SCO entities link to 363 agencies (three districts filed under two names in different years, with
  no overlapping year). 186 match a registry department by exact name in the same county; 180 are manual (registry
  name differs, or the district is missing from the registry). 73 districts and fire authorities the registry lacks
  were added to `config/states/ca/agencies_added.csv` (65 fire districts, 8 fire authority JPAs, all with kind "Fire district", the label `federal.py` gives registry fire authorities such as Orange County Fire Authority); 74 entity links go to
  them. Review of 2026-10-06 moved three districts the registry does list under another spelling or an older name
  from `agencies_added.csv` to their registry rows: South Lake County FPD -> CA-17040 ("South Lake Couny Fire
  Protection District"), Humboldt Fire Protection District No. 1 -> CA-12050 ("Humboldt No. 1 Fire Protection
  District"), Coastside FPD -> CA-41045 ("Half Moon Bay Fire Protection District"; Coastside was formed in 2007 from
  the Half Moon Bay and Point Montara districts, and the registry row carries Coastside's website). `check_ca.py` now
  fails if an added agency resembles a registry fire district of the same county by name. The Consolidated Fire Protection District of Los Angeles County is linked to the registry's Los Angeles County
  Fire Department (CA-19110).
- **Rows:** 6,469 raw rows (control file agrees) -> 5,960 totals rows (agency, year, report line; zero lines dropped),
  $20.33B: FY2021 $4.57B, FY2022 $4.96B, FY2023 $5.23B, FY2024 $5.57B. 355, 354, 348 and 351 linked districts filed
  in FY2021-FY2024; a district that did not file a year simply has no row for it.
- **Data quality:** amounts are self-reported and unaudited by the SCO. Lines are by fund type and object class
  (salaries, benefits, services and supplies, capital outlay, debt service, contributions to outside agencies);
  there is no "total" line, so summing lines does not double count. Enterprise and internal service funds report
  operating expenses (including depreciation), which are kept as published.
- **Duplicates and reversals:** one value per entity, year and line; `rownumber` is unique (asserted). A rare negative
  line is kept as filed.
- **Decision:** built. Tier 3 (totals, no vendors).

## `ca_sco_cities`: State Controller, City - Expenditures, Fire function (tier 3, built)

- **URL:** <https://bythenumbers.sco.ca.gov/d/ju3w-4gxp>. Same host, API and licence as above.
- **What it is:** the expenditure part of every city's Financial Transactions Report, FY2002-03 to FY2023-24, 482
  cities. Current expenditures are reported by function; the Public Safety function "Fire" (form field
  `CURR_EXP_FIRE`, line "Fire_Current Expenditures") is one annual total of the city's fire operating spending.
  Capital outlay and debt service are not split by function; Emergency Medical Services is a separate line and is not
  taken. Fields: `entity_name`, `county`, `city_state_zip`, `estimated_population`, `fiscal_year`, `category`,
  `subcategory_1`, `subcategory_2`, `line_description`, `form_table`, `type`, `value`, `row_number`.
- **Years and updates:** FY2002-03 to FY2023-24, published yearly (FY2024 is the latest); taken FY2021-FY2024.
- **Access:** SoQL filter on the `CURR_EXP_FIRE` line and `fiscal_year >= 2021` (1,928 raw rows: 482 cities x 4 years);
  plus the list of cities with their county.
- **Fire agencies:** the function field is clean (one line per city and year). A city's fire line is linked only to
  the city's own fire department in the registry (same county; names such as "<City> Fire Department", "City of <City>
  Fire Department", "<City> Fire & Rescue"). 211 links are by exact name; 13 are manual where the SCO uses the city's
  legal name or the registry spells it differently (for example San Buenaventura -> Ventura City Fire Department, El
  Paso De Robles -> Paso Robles Department of Emergency Services, Mt. Shasta -> Mount Shasta City Fire Department,
  Angels -> Angels Camp Volunteer Fire Department). A city whose fire service is provided by a county, CAL FIRE, a fire
  district or a fire authority JPA is not linked, because its fire line pays that agency (120 cities with a non-zero
  fire line, $3.29B over four years, for example Rancho Cucamonga and Fontana (fire protection districts that file
  their own reports), Pomona, Inglewood and Santa Clarita (Los Angeles County Fire), San Mateo, Livermore and
  Pleasanton (JPAs), Moreno Valley and the other Riverside County contract cities). Cities that are dependent on a
  fire protection district filing its own report (Murrieta, Coachella, Gonzales) are linked through the district, not
  the city line, so no agency has both.
- **Rows:** 892 totals rows for 224 agencies, $22.80B (zero lines dropped).
- **Data quality:** operating spending only; some cities report contract payments under Fire (only cities with their
  own department are linked, which limits this). A few small cities with a fire line have no registry department
  (see Open questions).
- **Duplicates and reversals:** one value per city, year and line; `row_number` unique (asserted).
- **Decision:** built. Tier 3.

## `ca_sf`: San Francisco Vendor Payments (Vouchers) (tier 1, built)

- **URL:** <https://data.sf.gov/d/n9pm-xkyq> (SF OpenBook data, Controller's Office). Weekly (rows updated 2026-10-05).
- **Format and access:** Socrata SODA API; server-side filter `department_code = 'FIR' AND fiscal_year >= '2021'`;
  control query of rows and dollars per fiscal year; 100-row unfiltered sample.
- **Fields:** fiscal year, organization, department and code, program, character, object and sub-object, fund,
  purchase order, contract number and title, payee ("Supplier & Other Non-Supplier Payees"), vouchers paid, pending,
  pending retainage, voucher number, `data_as_of`. The Controller removes payments to employees, jurors, witnesses,
  revenue refunds, judgments, claims and human-services payments before publishing.
- **Years:** FY2007 on; taken FY2021-FY2027 (FY2027 partial, data loaded 2026-10-05).
- **Fire agency:** department code FIR ("FIR Fire Department") -> San Francisco Fire Department (CA-38005). Purchases
  other City departments make for Fire are not included.
- **Rows:** 35,749 raw lines (control agrees) -> 34,637 lines with a paid amount, $220.6M (the owner's dedup rule
  drops none); 1,112 lines with only pending or retainage amounts left out. FY2022 ($62.2M) is about
  twice a normal year because of one $38.8M capital outlay payment to Chicago Title Company (a property purchase
  through escrow; $5.9M more in FY2023); FY2021 ($15.1M) is about half a normal year.
- **Data quality:** no documented payment date (`data_as_of` is undocumented and often outside the fiscal year), so
  `posting_date` is empty for every SF row.
- **Duplicates and reversals:** owner rule of 2026-10-07 as corrected: raw lines equal in every column but `:id`,
  `data_as_of` ("Timestamp the data was updated in the source system") and `data_loaded_at` (portal load time) are
  kept once; voucher and PO numbers are content. No two raw lines are identical, so nothing is dropped and the void
  rule keeps nothing. The first version of the rule (published columns, no date) dropped 7,734 lines ($18.2M) on
  different vouchers, among them fire engines bought at one price (Ferrara, for example five payments of $590,765.75
  in FY2022); they are all kept again. The voucher number repeats across lines, so the record id is voucher plus a
  running number. 313 negative (credit) lines kept.
- **Decision:** built.

## `ca_la`: Checkbook L.A. (tier 1, built)

- **URL:** <https://controllerdata.lacity.org/d/pggv-e4fn> (Los Angeles City Controller; data behind Checkbook L.A.;
  FY2018 on; refresh "Monthly", rows updated 2026-09-22).
- **Format and access:** Socrata SODA API; filter `department_name = 'FIRE' AND fiscal_year >= 2021`; only the columns
  needed are kept (buyer names, links and calendar helper columns dropped).
- **Fields:** fiscal year, department name and number, vendor, transaction (check) date, amount, fund, account,
  expenditure type, program, payment method and status, invoice number, line and distribution line, purchase order
  and line, item description, quantity and unit price (for payments against a PO).
- **Fire agency:** department FIRE (number 38) -> Los Angeles Fire Department (CA-19105). General Services fleet and
  fuel bought for LAFD are not included.
- **Rows:** 175,405 lines, $696.8M (the owner's dedup rule drops none), FY2021-FY2027 (FY2027 partial, payments
  through 2026-09-09).
- **Data quality:** every line has a check date inside its fiscal year; item description, quantity and unit price
  only where the payment is against a purchase order; 722 negative lines kept (698 cancellations, other credits).
- **Payees:** the City publishes most refunds of ambulance charges and fire service fees to "PRIVACY-FIRE" (12,802 of
  12,808 ambulance-refund lines, $11.6M, all kept); a few refund payees are named and shown as named.
- **Duplicates and reversals:** owner rule of 2026-10-07 as corrected: raw lines equal in every column but `:id` are
  kept once; transaction id, invoice number, invoice line and distribution line, PO number and line are content. No
  two raw lines are identical, so nothing is dropped and the void rule keeps nothing (reversal fields: department,
  vendor, program, fund, account, invoice number and line, distribution line, PO number and line). The first
  version of the rule (published columns) dropped 34,299 lines ($51.0M), mostly separate invoice lines of one
  price (Braun Northwest ambulances, 12 at $205,625 on 2022-12-12); all are kept again. The raw file keeps the
  columns the adapter selects; 17 portal columns were not fetched (calendar helpers, links, invoice due dates,
  receiver id, buyer name, sales tax percent and others), so they cannot enter the comparison (not refetched; with
  no identical lines in the fetched columns they could not change the result). Cancelled checks are their own
  negative lines (payment status CANCELLED; 698 lines, 677 carrying the same transaction, invoice line and
  distribution line as the payment they cancel) and are kept, so a cancelled payment nets to zero; record id gets
  "-cancelled".
- **Decision:** built.

## `ca_riverside_county`: County of Riverside Check Book (tier 1, built)

- **URL:** <https://data.countyofriverside.us/d/swwh-4ka9> (RCIT for the Auditor-Controller; monthly; rows updated
  2026-09-10). About 71 million ledger lines from FY2011.
- **Access:** SODA; filter department "Fire Protection", `fiscal_year >= 2021`, vendor name present. Control: rows and
  dollars per year with and without a vendor (lines without a vendor are payroll, journal entries and internal
  charges: 205,098 lines, $803.8M, not taken).
- **Fields:** fiscal year and period, date, department, fund type, fund, account category, account, expense category,
  business unit, description, amount, vendor name and id, invoice id, payment id.
- **Fire agency:** department "Fire Protection" = Riverside County Fire Department (CA-33090; operated by CAL FIRE
  under the County's cooperative agreement). The registry's second row for the same operation, "Cal Fire - Riverside
  County Fire Department" (CA-33555), is not linked. The largest payee is the State (CAL FIRE) for contract staffing.
- **Rows:** 277,875 raw lines ($1,666.8M) -> 252,798 lines, $1,657.4M, after the owner's dedup rule, FY2021-FY2027
  (FY2027 partial, to 2026-08-26).
- **Data quality:** ledger lines with a date inside the fiscal year; vendor names as keyed (one company can appear
  in several spellings); $1.32B of the dollars are the County's contract payments to the State (CAL FIRE), an
  inter-agency payment rather than a purchase. One line of the department "Coachella Fire Protection Dist" exists in
  the source and is not taken (the district is tier 3 through `ca_sco_districts`).
- **Duplicates and reversals:** owner rule of 2026-10-07 as corrected: raw lines equal in every column but `:id` are
  kept once; invoice id and payment id are content. The source has **no line number**, so lines repeated inside one
  invoice (same date, business unit, account and amount; the description column is empty throughout) are identical:
  25,211 raw lines repeat another in every column, spread over every period with no reload burst. Void rule
  (reversal fields: department, vendor, business unit, fund, account, expense category, invoice id, payment id,
  description; amount negated; same or next fiscal year): 134 copies ($38,324.23, 127 sets) are kept because the
  line was reversed and paid again, for example Balance Industrial Scale invoice 16271 (two lines of $24,479.72 and
  two of $220 on 2022-01-13, each reversed once on 2022-02-01). Dropped: **25,077 lines, $9,444,820.95 (0.57%)**,
  5,749 sets, 196 of them negative (-$59,939.07); the largest are item lines of one price on one invoice that may
  be real (Allstar Fire Equipment protective gear, 8 lines of $68,722.95 on invoice 253471 of 2024-02-14, $481,061
  dropped; Bauer Compressors, 24 lines of $10,032.60 on one invoice of 2024-09-16, $230,750 dropped), plus wireless
  bills with one line per phone. The two CAL FIRE contract invoices of 2026-03-16 (176557 and 176845, each with lines
  of $36,159,244.27 and $36,227,427.80) are different invoices and both kept ($72.4M that the first version of the
  rule dropped); whether one quarter was paid twice needs the County's answer. The first version dropped 40,647
  lines ($86.2M). 5,446 negative lines (credits, reversals) kept.
- **Decision:** built.

## `ca_corona`: City of Corona Open Expenditures (tier 1, built)

- **URL:** <https://corstat.coronaca.gov/d/mdmf-aswt> (CorStat; uploaded every Friday after the check run; rows updated
  2026-10-02). FY2016 on.
- **Access:** SODA; filter department code 30 (FIRE), `fiscal_year >= 2021`.
- **Fields:** fiscal year and period, fund, department code and name, department activity, vendor id, name, city,
  state and zip, payment id and date, invoice id, expense category, description, amount.
- **Fire agency:** department 30 -> Corona Fire Department (CA-33025). Lines include pension and benefit payments
  naming the person paid (shown, owner decision).
- **Rows:** 14,500 raw ($21.8M) -> 13,626 lines, $21.7M, after the owner's dedup rule, FY2021-FY2026 (payments
  through 2026-06-30).
- **Data quality:** payment dates inside the fiscal year; many small lines (pension, benefit, refund and
  reimbursement payments name the person paid, shown as published).
- **Duplicates and reversals:** owner rule of 2026-10-07 as corrected: raw lines equal in every column but `:id` are
  kept once; payment id and invoice id are content. No line number, so lines repeated on one invoice and payment
  (CalCard statement lines for hotel nights or flights, copier invoices) are identical. Void rule (reversal fields:
  department, vendor, department activity, fund, expense category, invoice id, description; a void can carry a new
  payment id and date): 70 copies ($305,258.23, 70 sets) kept, for example L.N. Curtis invoice PINV893372 (GPS
  globe, $92,905.95 paid, reversed and paid again on payment 00017309 of 2024-08-15) and Jacob Green and Associates
  invoice 2876 ($54,050). Dropped: **874 lines, $85,749.43 (0.39%)**, 303 sets, 19 of them negative (-$7,420.74);
  largest: two $3,720 background investigation lines (Truview BSI) and six $619.56 hotel nights on one statement.
  The $690,075.97 KME custom pumper lines of 2020-09-25 are on two invoices (G11148001, G11149001) and both kept.
  The first version of the rule dropped 1,145 lines ($1.14M). 734 negative lines (voids, credits) kept.
- **Decision:** built.

## `ca_moreno_valley`: City of Moreno Valley Open Expenditures (tier 1, built)

- **URL:** <https://moreno-valley.data.socrata.com/d/qpw5-2938> ("Moreno Valley Ledger Dataset for OE"; FY2013 on;
  refreshed a few times a year, last 2026-07-16). No licence or terms stated; robots.txt allows the API.
- **Access:** SODA; filter the three Fire departments and `fiscal_year >= 2021`; control per department and year for
  every department whose name has FIRE.
- **Fields:** fiscal year and period, service, department, program, expense category, fund, vendor name, id and zip,
  payment id, method and date, invoice id, line, distribution line and date, amount, description.
- **Fire agency:** "Fire Operations", "Fire Prevention" and "Fire - Office of Emergency Mgmt" -> Moreno Valley Fire
  Service (CA-33054). Fire-station programs booked to Fleet & Facilities (Public Works; about $4.1M) and Technology
  Services are not included.
- **Rows:** 2,369 lines, $140.2M (the owner's dedup rule drops none), FY2021-FY2026 (payments through
  2026-06-24). Most dollars are the City's contract payments to the County of Riverside for fire staffing.
- **Data quality:** payment dates inside the fiscal year; "Fire - Office of Emergency Mgmt" is small ($0.9M, radios,
  satellite phones, supplies); Fire Operations ($132.2M) is mostly the County contract.
- **Duplicates and reversals:** owner rule of 2026-10-07 as corrected: raw lines equal in every column but `:id` are
  kept once; payment id, invoice id, invoice line and distribution line are content. No two raw lines are identical,
  so nothing is dropped and the void rule keeps nothing. The first version of the rule dropped 31 lines ($15,487),
  now kept. 3 negative lines kept.
- **Decision:** built.

## Other city and county candidates (skipped)

- **San Diego (`ca_sandiego`, sample kept).** The City's open data portal (relaunched June 2026,
  <https://data.sandiego.gov/datasets/>) has budget and actuals datasets only. "Operating Actuals"
  (<https://data.sandiego.gov/datasets/operating-actuals/>, one 66 MB CSV on seshat.datasd.org) gives amount by fiscal
  year, fund, department, funds center and expense account, with no payee. The City posts "cumulative amounts paid" to
  vendors of $25,000 or more as PDFs, with no department. No vendor payments by department, so no tier-1 data; the San
  Diego Fire-Rescue Department's spending is in `ca_sco_cities`. Sample: header and first 100 rows of the actuals CSV
  (one HTTP range request) and the data dictionary.
- **San Jose (no sample).** data.sanjoseca.gov (CKAN) has no vendor payment, checkbook, expenditure or purchase
  dataset (portal searches for vendor, checkbook, payment, expenditure, spending, purchase and budget find none; the
  only fire datasets are stations, incidents and the wildland-urban interface map). robots.txt disallows `/api/` and
  `/datastore/`. Nothing to sample.
- **Sacramento (`ca_sacramento`, samples kept).** The City's hub (data.cityofsacramento.org) publishes two Finance
  feature services on services5.arcgis.com: "Checks Issued" (check date, number, payee, amount; 212,859 checks,
  $3.06B, check dates 2021-10-07 to 2026-10-07) and "Purchase Orders to Date" (PO date, number, line, vendor, item description, amount;
  128,643 lines, $7.60B). Neither has a department or fund, so no line can be attributed to the Sacramento Fire
  Department. Samples: layer metadata, first 100 rows, and a control query each.
- **Los Angeles County (`ca_lacounty`, sample kept).** The Auditor-Controller's "LA County Open Expenditures"
  (data.lacounty.gov, ArcGIS feature service) gives monthly totals by fund, function, department, budget unit and
  expenditure class from FY2025 (Fire Department FY2025 $1.80B, FY2026 $1.95B), with no payee. The Fire Department
  (Consolidated Fire Protection District) is already tier 3 through `ca_sco_districts`; adding these totals would put
  two overlapping totals sources on one agency. Sample: metadata, 100 rows, fire department totals per year.
- **Modesto (`ca_modesto`, sample kept).** data.modestogov.com "FIN - Weekly AP Transactions" (5qnw-bnyf) has one row
  per week with one number per payment kind (vendors, employees, refunds, uploads, ACH, P-cards); no payee, no
  department. Sample: metadata and 100 rows.
- **Indio (no sample).** indio.data.socrata.com "Expenditures" (3tyh-g5za) has vendor, organization and account per
  invoice line, but the domain's robots.txt is `Disallow: /` for every agent, so it was not fetched. (Indio's fire
  service is a County of Riverside/CAL FIRE contract, as in Moreno Valley.)
- **West Hollywood** demand registers (data.weho.org): the city has no fire department (Los Angeles County Fire).
  **Marin County** "Delegated Contracts" (data.marincounty.gov): contract awards, not payments. **Los Angeles City**
  older datasets ("EcheckBook_Data_2012_To_2017", 2014 invoices) predate FY2021. Not fetched.
- A Socrata catalog search (vendor payments, checkbook, expenditures, accounts payable, check register, vendor,
  payments, purchase orders) found no other California city or county publishing payments with a department field.
  ArcGIS Hub and OpenGov sites of other large fire departments (Long Beach, Oakland, Fresno, San Bernardino County,
  Orange County Fire Authority) were not found to publish bulk vendor payments.

## `ca_fiscal`: Open FI$Cal department vendor transactions, CAL FIRE (tier 1, built)

- **URL:** <https://open.fiscal.ca.gov/dept_vendor_transaction.html> ("Department Vendor Transaction Files"). One CSV per
  state department and fiscal year with "the subset of spending transactions with associated vendor names", listed in
  a pointer CSV and served from Azure blob storage. Files are refreshed periodically (all six used were uploaded
  2026-09-07).
- **Access:** bulk file download (no API needed). Files are named `Vendor_<business unit>_<department>_FY<yy>.csv`
  where FY<yy> is the year the fiscal year begins (FY23 = fiscal_year 2024 here). CAL FIRE is business unit 3540.
- **Fields:** business unit, agency and department name, document id (business unit, voucher, line and
  distribution), related document, accounting date, fiscal year begin, accounting period, vendor name, account
  (number, type, category, sub-category, description), fund, program, sub-program, budget reference, year of
  enactment, amount.
- **Raw files:** the six CAL FIRE files FY20-FY25 kept unmodified (149 to 248 MB each unzipped, 8.3 to 13.5 MB
  gzipped); `manifest.json` records URL, upload date, bytes, SHA-256, rows and dollars of each (373,001 to 623,342 rows
  a year; 3,226,425 in all).
- **Fire agency:** the whole department, linked to the registry row "CA Department of Forestry and Fire Protection- HQ"
  (CA-00555) as a state fire agency (owner decision: state fire agencies stay in the main data). The registry's
  regional CAL FIRE unit rows are not linked. CAL FIRE spending covers fire protection, the State Fire Marshal and
  resource management (forest health and urban forestry grants), not only suppression.
- **Rows:** 60% of lines are CalCard (procurement card) lines whose payee is the card issuer, US Bank ($605.9M over
  the years). Lines are summed to one row per voucher, payee, account, fund, program and accounting date (keeps every
  published field but the line number): 873,016 rows, $10,127.5M, after the owner's dedup rule on the raw lines
  (FY2021 $1,562M, FY2022 $1,480M, FY2023 $1,459M, FY2024 $1,295M, FY2025 $2,370M, FY2026 $1,963M to
  2026-06-30). Rows summing to $0.00 are dropped (34,994).
- **Data quality:** raw and unaudited (terms of use); accounting dates inside the fiscal year; CalCard lines name the
  card issuer, not the merchant; much of the money is payments to other governments (contract counties, cities and
  fire districts reimbursed for mutual aid) and grants (forest health, urban forestry), which are not purchases.
- **Payees:** the State publishes employee travel, per diem and training reimbursements to "CONFIDENTIAL" ($35.1M);
  other payees, sole proprietors included, are named and shown as published.
- **Duplicates and reversals:** owner rule of 2026-10-07 as corrected, on the raw distribution lines before they are
  summed. The files have no row id and no load or extract date, so a line is identical to another only when all 26
  columns are equal, document id (voucher, line and distribution number) included. Identical lines are kept once:
  **1,308 lines, $3,113,705.14 (0.03%)**, all pairs (FY2021 134, FY2022 398, FY2023 411, FY2024 22, FY2025 54,
  FY2026 289; 1,171 on distribution 0001, 136 on 0002, 1 on 0003; 141 negative). This is the same set the adapter
  dropped before the owner's rule. Void rule (reversal fields: business unit, vendor, document id, account, fund,
  program; amount negated; same or next fiscal year): keeps nothing. 123 of the doubled lines ($103,648.18; 122 of
  them CalCard lines of May 2021) are distribution 0002 lines whose sibling distribution 0001 of the same voucher
  line carries the negated amount on another fund (fund 0001 against fund 9752 in the cases checked); that sibling has another distribution
  number, fund and program, so it is not an exact reversal of the doubled line and the copy is dropped (net $0 for
  those voucher lines; $103,648.18 more if the doubling is real). The summed rows are not compared with each other:
  rows on different vouchers are different payments even with equal date, payee, account and amount (83,757
  published rows share every published column with another row). The first version of the rule, on the summed rows,
  dropped 54,312 rows ($400.1M: cooperative fire protection installments to contract counties, Holt of California
  vehicles of $617,325.88, seven on 2024-04-02, Air Methods aircraft, CONFIDENTIAL reimbursements); all are kept
  again. Source lines inside one voucher that differ only in line or distribution number are summed into the
  voucher's row, not dropped. Lines repeating a document id with another date or amount are later postings
  (corrections, reversals) and are kept, negative where published so (5,739 negative rows).
- **Decision:** built. It is the current source for CAL FIRE that the PRD asked for under SCPRS ("bulk access to
  current data").

## `ca_scprs`: SCPRS Purchase Order Data (tier 2, built for FY2013-FY2015 only)

- **URL:** <https://data.ca.gov/dataset/purchase-order-data> (also on catalog.data.gov). One CSV, 344,504 lines,
  164,463,591 bytes, SHA-256 `45aa37a683e308c17c28c2edaadf08692be18ed17131afe8edf2e701abc6c9b5`: the eSCPRS extract of
  state agencies' purchase orders for FY2012-13, FY2013-14 and FY2014-15. Static (never updated).
- **Access:** the dataset's file download link (allowed by robots.txt). The full file is not kept (164 MB; no other
  department is a fire agency): `calfire.csv.gz` keeps the header and every CAL FIRE line as published (23,244 lines,
  2.0 MB gzipped); the manifest records the full file's URL, size, row count, checksum, columns, and lines and
  dollars of each department with Fire or Forestry in its name (only CAL FIRE).
- **Fields:** creation and purchase date, fiscal year, LPA number, PO and requisition number, acquisition type and
  method, department, supplier code, name, qualifications and zip, CalCard flag, item name and description, quantity,
  unit price, total price, UNSPSC commodity, class, family and segment, location. No line number and no brand.
- **Current data:** later purchase orders are in Cal eProcure's SCPRS search (caleprocure.ca.gov), an interactive
  search with no bulk export; the host answers 403 to `/robots.txt`. Not scraped. Current CAL FIRE payments come from
  `ca_fiscal` instead.
- **Fire agency:** department "Forestry and Fire Protection, Department of" -> CA-00555 (CAL FIRE).
- **Rows:** 23,244 raw lines -> 22,496 item lines after the owner's dedup rule ($883.4M: FY2013 $192.3M, FY2014
  $132.5M, FY2015 $558.7M), also rolled into `transactions.csv.gz` (payee = supplier). 446 $0.00 lines
  (contract-amendment text) left out.
  Amounts are purchase order amounts (commitments), not payments.
- **Data quality:** some purchase dates are typos (1912, 2511) and are left empty; PO dates of long-running agreements
  can precede the fiscal year the line is registered in; no brand field.
- **Duplicates and reversals:** owner rule of 2026-10-07 as corrected, on the raw lines: the file has no row id and
  no load date, so a line is identical to another only when all 32 columns are equal (PO, requisition and LPA
  numbers are content); the transaction copy of a dropped item line is dropped with it. There is no line number, so
  a line repeated inside one PO with the same item, quantity and price is identical: **302 lines, $2,636,703.36
  (0.30%)**, 112 sets, none negative; largest: a $952,295 Prison Industry Authority Nomex line listed twice on PO
  9PA1K114, a $454,469 mobile kitchen unit (Tom's Equipment Rental) twice on PO 1ui2e861, AT&T network equipment on
  PO CF140541 (22 lines of $6,500, 24 of $4,500). Void rule (reversal fields: department, supplier code and name,
  PO, requisition and LPA number): keeps nothing (no identical positive set has a negated line on its PO). The first
  version of the rule dropped 1,144 lines ($5.8M). 427 negative lines kept.
- **Decision:** built with years labelled 2013-2015 in `sources.csv`; tier 2 (brand is absent; product type is the
  UNSPSC commodity).

## Duplicates and reversals: summary

Owner decision of 2026-10-07: "drop identical lines, drop identical days", as corrected the same day:

1. Two lines are identical when every column the source publishes in its raw file is equal, except columns that only
   identify the row or the load. Document numbers (voucher, invoice, check or payment, PO and their line or
   distribution numbers) are content: lines that differ in one are different payments and are kept.
2. Identical lines are kept once (the copy with the lowest row id).
3. Void-safe: a set of n identical positive lines keeps min(n, reversals + 1) copies, where a reversal is a negative
   line with the same reversal fields (agency, payee, account and the document fields the source repeats on a void),
   the amount negated and the same or the next fiscal year; reversals identical among themselves count once.

A doubled day is a set of identical lines, so it is covered. Applied by `ca_common.keep_identical` (FI$Cal:
`ca_common.copies_to_keep` on the raw distribution lines, before they are summed per voucher; SCPRS: the item lines,
transaction copies follow) and mirrored independently in `check_ca.py`. The totals sources (`ca_sco_*`) are not
affected. No California source needs an upload-error rule of its own: control queries and manifests match the raw
files, and the adapters' earlier rule (an invoice or PO loaded twice in full: Riverside County 929 lines, Corona 19,
SCPRS 35) is covered by rule 1, because such copies are equal in every raw column.

Columns ignored as row or load ids, per source (every other raw column is compared):

| Source | Ignored columns | Reversal fields (with the negated amount, same or next fiscal year) |
| --- | --- | --- |
| `ca_fiscal` | none (no row id or load date in the files) | business unit, vendor, document id, account, fund, program |
| `ca_riverside_county` | `:id` | department, vendor, business unit, fund type, fund, account category, account, expense category, invoice id, payment id, description |
| `ca_la` | `:id` (17 portal columns were not fetched into the raw file, see the source) | department, vendor, program, fund, account, invoice number, invoice line, distribution line, PO number and line |
| `ca_sf` | `:id`, `data_as_of`, `data_loaded_at` | department, vendor, PO, contract, program, character, object, sub-object, fund |
| `ca_corona` | `:id` | department, vendor, department activity, fund, expense category, invoice id, description |
| `ca_moreno_valley` | `:id` | department, vendor, program, fund, expense category, invoice id, invoice line, distribution line |
| `ca_scprs` | none (no row id or load date in the file) | department, supplier code and name, PO, requisition and LPA number |

Numbers (2026-10-06 raw files). "Before" is the raw lines with an amount (SF: with a paid amount; SCPRS: not $0;
FI$Cal: distribution lines, which are then summed to 873,016 rows); "first version" is the published-columns rule
run earlier on 2026-10-07.

| Source | Lines before | Dollars before | Lines dropped | Dollars dropped | Share | Sets | Negative lines dropped | Void rule kept | Lines after | Dollars after | First version: lines, dollars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ca_fiscal` | 3,226,425 | $10,130,590,938.52 | 1,308 | $3,113,705.14 | 0.03% | 1,308 | 141 (-$13,302.00) | 0 | 873,016 rows | $10,127,477,233.38 | 818,704 rows, $9,727,334,191.20 |
| `ca_riverside_county` | 277,875 | $1,666,803,206.96 | 25,077 | $9,444,820.95 | 0.57% | 5,749 | 196 (-$59,939.07) | 134 ($38,324.23, 127 sets) | 252,798 | $1,657,358,386.01 | 237,228, $1,580,559,165.01 |
| `ca_la` | 175,405 | $696,804,689.78 | 0 | $0.00 | 0% | 0 | 0 | 0 | 175,405 | $696,804,689.78 | 141,106, $645,783,065.81 |
| `ca_sf` | 34,637 | $220,558,400.58 | 0 | $0.00 | 0% | 0 | 0 | 0 | 34,637 | $220,558,400.58 | 26,903, $202,316,391.78 |
| `ca_corona` | 14,500 | $21,834,522.12 | 874 | $85,749.43 | 0.39% | 303 | 19 (-$7,420.74) | 70 ($305,258.23, 70 sets) | 13,626 | $21,748,772.69 | 13,355, $20,692,320.71 |
| `ca_moreno_valley` | 2,369 | $140,184,292.42 | 0 | $0.00 | 0% | 0 | 0 | 0 | 2,369 | $140,184,292.42 | 2,338, $140,168,805.30 |
| `ca_scprs` (item lines) | 22,798 | $886,076,817.36 | 302 | $2,636,703.36 | 0.30% | 112 | 0 | 0 | 22,496 | $883,440,114.00 | 21,654, $880,252,427.54 |
| Tier 1 (six sources) | | | 27,259 | $12,644,275.52 | 0.10% | 7,360 | 356 | 204 ($343,582.46) | 1,351,851 | $12,864,131,774.86 | 1,239,634, $12,316,853,939.81 |

Where lines are still dropped, the source has no line number (Riverside County, Corona, SCPRS) and the copies are
equal in every published column, invoice or PO included; some are probably separate items of one price on one
invoice (Riverside County: Allstar Fire Equipment protective gear, 8 lines of $68,722.95 on one invoice; SCPRS: a
$952,295 Nomex line listed twice on one PO). FI$Cal's copies carry the same document id, line and distribution
number. Every adapter keeps credits, voids and reversals as published (negative lines), so totals are net.

Where the rule raises a net (review of 2026-10-07): identical negative lines are kept once (rule 2) and count once
as reversals, so where two identical payments were reversed by two identical reversals, both payments stay and one
reversal goes. Payment and reversal families (same reversal fields and amount, both signs present) that now net more
than the raw lines: Riverside County 108 (+$6,840.05; for example "State of California Office of Emergency"
invoice CSTI7617-24, two lines of $2,610 on 2025-04-21, both reversed on 2025-06-02: raw net $0, now $2,610) and
Corona 5 (+$4,707.58; for example JEROMES FURNITURE WAREHOUSE invoice 0111407WE59D, two $4,416.72 payments and two
reversals on 2024-02-15, raw net $0, now $4,416.72; DOUBLETREE HOTEL FRESNO, $200.82 "mistakenly charged" twice and
refunded twice, raw net $0, now $200.82). FI$Cal, LA, SF, Moreno Valley and SCPRS: none. Open question below; Ohio,
Idaho and Texas have the same case.

## Payee names

Owner decision of 2026-10-06: payee names are shown as published, private persons included. Every adapter calls
`common.withhold_person` directly, which cuts only payee text matching `config/payee_name_redactions.csv` (email
addresses, bank account text, and a few name patterns from the Utah build): 6 Los Angeles lines of FY2025-FY2026 are
cut because their payee ("INDOFF LLC - " followed by three words, an office supplier) matches the pattern
`\bllc - [a-z]+ [a-z]+ [a-z]+$` of that shared file. The sources' own masking stays as the
sources publish it ("PRIVACY-FIRE" in Los Angeles, "CONFIDENTIAL" in FI$Cal, the SF Controller's removal of payments
to employees). `check_ca.py` reports 132,804 lines whose payee looks like a person's name (shown).

## Agencies, overlaps and state fire agency

- **CAL FIRE:** included in the main data (owner decision 4) through the registry row CA-00555, with kind "State fire
  agency" in `agencies.json`. `federal.py` sets that kind by name for CAL FIRE and CDF rows (8 registry rows besides
  CA-00555), whatever the registry's organization type. A county department that CAL FIRE runs under contract
  ("Cal Fire - Riverside County Fire Department", CA-33555) has kind "County fire department".
- **Money flowing between agencies:** Moreno Valley pays the County of Riverside for fire staffing; the County Fire
  Department pays the State (CAL FIRE) for contract staffing ("STATE OF CALIFORNIA DEPT OF FORESTRY", $1.32B); CAL FIRE
  pays contract counties (Kern, Los Angeles, Ventura, Santa Barbara, Marin, Orange) for state responsibility area
  protection. The same dollars can therefore appear once as one agency's payment to another and again as that agency's
  payments to vendors. These payees are mapped to the category `government` (not purchasing), so they do not count as
  vendor spend.
- **Two tiers on one agency:** Los Angeles Fire Department and Corona Fire Department have both tier-1 lines and
  `ca_sco_cities` totals; CAL FIRE has FI$Cal lines and older SCPRS lines (FY2013-FY2015 do not overlap FY2021 on).

## Vendor names and categories (merged into `config/vendor_map.csv`)

California proposed 2,753 payees with a canonical name and category in `config/states/ca/vendor_map_additions.csv`
(with `spend` and `agencies` recomputed after the dedup rule of 2026-10-07; 24 keys that `config/vendor_map.csv`
already carried after main's merge were dropped then, 9 of them taking that file's category: Carahsoft software,
Entenmann-Rovin and Sun Badge uniforms, OHD scba, Sigtronics radios, Highway Products apparatus, Vortex Industries
facilities, Lawson Products fleet, Ricoh it). On 2026-10-07 `pipeline/sources/merge_vendor_maps.py` folded them,
with the other states' proposals, into the shared `config/vendor_map.csv` and the file was deleted; every decision
is in `docs/multistate/vendor-merge.md`. For California: CAL FIRE is one name (Cal Fire and "CAL FIRE (State of
California)"); helicopter operators keep `apparatus` (Heli-1, HeliQwest International, Timberline Helicopters,
where Idaho had proposed `wildland`); Snap-on Industrial is Snap-on; Recology is `utilities`; Harris & Harris is
`ems-billing`; Regents of the University of California covers the UC campuses; US Foodservice is US Foods; the
CANOPY payee was left out of the shared map (the key also names an unrelated Utah payee). Coverage after the merge,
as `tests/multistate/check_ca.py` counts it ("purchasing dollars" = net positive spend per `common.norm(payee)` key,
excluding keys whose category is not purchasing; payees classified the way `pipeline/build.py` does,
`config/vendor_map.csv` first and then the vendor and keyword rules): a real category for **92.9%** of
$5,927,730,905 purchasing dollars (90.1% by map rows, 2.8% by rules; 1.1% `unclassified`, mostly CAL FIRE
forest-health and urban-forestry grantees). After the corrected dedup rule (more lines kept): **93.1%** of
$6,237,728,211 (90.4% by map rows, 2.7% by rules; 1.0% `unclassified`); the map was not changed. Before the merge the two files mapped 91.3% of $5.93B (real category
90.2%; by source: FI$Cal 91.9%, LA 94.5%, SF 89.2%, Riverside County 86.7%, SCPRS 87.1%, Moreno Valley 75.3%,
Corona 69.2%).

How the proposals were made (kept for the record):
Categories: names first (keywords: aviation, apparatus makers, logging and water tenders, vehicles, utilities,
telecom, governments), else the payee's dominant published account (confidence low); the top payees were reviewed by
hand. Review of 2026-10-06 added 441 rows for payees of $25,000 or more that are governments or public fire agencies
(cities, counties, fire districts and departments, community services, water and irrigation districts, tribes,
state prisons and departments, universities; $64.0M, almost all CAL FIRE mutual-aid and agreement payments) as
`government` (confidence medium), which takes them out of purchasing dollars; names with business words (Inc, LLC,
Supply, Association, Foundation, Council) were left out of that rule. Canonical names from `config/vendor_map.csv`
are reused when the company is the same (Verizon, AT&T, Comcast, Goodyear, FedEx, Grainger, Staples, Municipal
Emergency Services, Rush Truck Centers). Confidence: 26 high, 1,765 medium, 962 low. No row classifies a name as a
person (owner decision 1). CalCard payments (US Bank, $604.1M) are `finance` and the "CONFIDENTIAL" and
"PRIVACY-FIRE" placeholders are `placeholder`, so they are outside purchasing dollars.

## Checks

`python3 tests/multistate/check_ca.py` recomputes, independently of the adapters (its own filters and duplicate rules,
sharing only `agency_sources.csv`, the redaction patterns and common's file helpers):

1. per source, agency and fiscal year, line counts and dollars to the cent (the multiset of agency, fiscal year,
   date, payee and amount lines) after the owner's dedup rule as corrected, whose identity (every raw column but the
   row and load ids), reversal fields and void rule the check builds from the raw files itself, for SF, LA,
   Riverside County, Corona, Moreno Valley, SCPRS and FI$Cal (the rule on the raw distribution lines, then rows
   summed per voucher from the six raw files, checked against the manifest's rows and dollars); it reports the lines
   dropped, the copies the void rule keeps, and the published rows that share every published column with another
   row (kept: different documents); totals per agency and year for both SCO sources (every Fire Protection district
   linked);
2. payee names as published (only redaction-pattern text cut; the old person marker never appears; no payee,
   description or account carries an email address); person-shaped names are only counted (shown, owner decision);
3. every agency id exists in `agencies.json`; coverage tiers agree with the rows; no zero totals rows; no added agency
   resembles a registry fire district of its county by name; a city's SCO fire line goes only to a fire department;
4. no duplicate or empty `source_record_id` per source; SCPRS item lines equal their transaction rows;
5. every source is registered in `sources.csv` with the years present and the raw folder date as `fetched`;
6. vendor map: no unmerged `config/states/ca/vendor_map_additions.csv`; `config/vendor_map.csv` with the vendor and
   keyword rules (as `pipeline/build.py` applies them) gives a real category to at least 90% of purchasing dollars;
7. raw files under 50 MB each and California under 150 MB (97 MB), every source folder has a sample of at most 100 rows;
8. contract conformance: table, `sources.csv` and `agency_sources.csv` columns in the contract's order (read from
   `docs/multistate/data-contract.md`), dates `YYYY-MM-DD`, amounts with two decimals, and every payment date inside
   the fiscal year it is filed under (SCPRS purchase-order dates excepted).

Normalize is deterministic: every adapter's normalize was run twice; the data files were byte-identical (re-run in the
review of 2026-10-06 after its changes: all nine normalizes twice, every file in `data/states/ca/` and
`config/states/ca/` byte-identical between the runs; again on 2026-10-07 after the first version of the dedup rule;
and on 2026-10-07 after the corrected rule: the seven line adapters twice, every file in `data/states/ca/` and
`config/states/ca/` byte-identical). The check was fault-tested with faults injected into the rows it reads (no file
changed): a removed Riverside County row that repeats another's published columns, an extra FI$Cal row under a new
record id, and an LA row moved by one day each fail the line multiset.

## Open questions

- Cities with an SCO fire line but no registry fire department (Imperial, Delano, Willows, Corcoran, Blythe, Orland,
  Crescent City and some smaller cities): some may run their own departments (would be added to `agencies_added.csv`
  after confirmation); left unlinked.
- Should the SCO city line also include Emergency Medical Services (a separate line) for cities whose fire department
  runs ambulances?
- Moreno Valley fire-station costs booked to Fleet & Facilities (about $4.1M) are excluded; include them?
- San Francisco has no payment date; should the page show SF rows by fiscal year only?
- Dedup rule of 2026-10-07 as corrected: in California it drops 27,561 lines ($15.3M), all copies equal in every
  raw column. Riverside County, Corona and SCPRS publish no line number, so equal item lines on one invoice or PO are
  dropped although some are probably separate items (Riverside County: Allstar Fire Equipment protective gear, 8
  lines of $68,722.95 on invoice 253471, $481,061 dropped; Bauer Compressors, 24 lines of $10,032.60, $230,750
  dropped; SCPRS: a $952,295 Nomex line twice on one PO). Keep them dropped, or keep identical lines inside one
  invoice where the source has no line number? FI$Cal: 123 doubled distribution lines ($103,648.18, May 2021
  CalCard) face a negated sibling distribution on another fund; the rule drops the copy (not an exact reversal).
- Identical voids (same question in Ohio, Idaho and Texas): rule 2 keeps identical negative lines once, so 113
  payment and reversal families net more than the raw lines (Riverside County 108, +$6,840.05; Corona 5, +$4,707.58;
  see Duplicates and reversals: summary), against rule 3's "must not change the net of a payment, void and reissue
  sequence". Keeping identical negative lines as often as the payments they reverse are kept would break the
  owner's own example (Walnut Township (Fairfield), Ohio: three identical payments and two identical voids, net one
  payment, would net $0). A remedy that keeps every such net and changes no positive line: in a family that has
  payments, drop an identical negative copy only together with an identical positive copy of the family. In
  California it would keep 116 more negative lines (Riverside County 110, -$6,840.05; Corona 6, -$4,707.58).
- Riverside County's two CAL FIRE contract invoices of 2026-03-16 (176557 and 176845, $72.4M each) are both counted;
  whether one quarter was paid twice needs the County's answer.
- SCPRS gives only FY2013-FY2015; keep it, given FI$Cal covers CAL FIRE from FY2021?
- LA County Open Expenditures (FY2025 on, monthly totals by expenditure class) could later replace or extend the SCO
  totals for the Los Angeles County Fire Department.
- Fire districts and JPAs that buy their fire service from another agency (review of 2026-10-06): each is a fire
  district or fire authority, so it is linked, but its spending is largely a payment to another listed agency. Member
  districts and their JPA both have totals (Tracy FPD and South San Joaquin County Fire Authority; Williams FPD and
  Williams Fire Protection Authority; Fort Bragg Rural FPD and Fort Bragg Fire Protection Authority; Big Bear Lake FPD
  and Big Bear Fire Authority; Humboldt FPD No. 1 and Humboldt Bay Fire; Belmont FPD, Belmont-San Carlos Fire
  Department and San Mateo Consolidated Fire Department); districts served by a city department have totals beside the
  city's own fire line (Vista FPD, Dixon FPD, Winters FPD, Natomas and Pacific-Fruitridge FPDs with Sacramento, Lower
  Sweetwater FPD with National City, Kensington FPD with El Cerrito, East Vallejo FPD with Vallejo). A state or
  peer total that adds agencies would count these dollars twice; per-agency figures are as filed.
- Sonoma County Fire District is an added agency, while the registry still lists its predecessors Rincon Valley FPD
  (CA-49170) and Windsor FPD (CA-49215), which therefore show at tier 4. Which legal entity survived the 2019
  consolidation is not settled here, so the district was not relinked.
- "Nevada County Fire Agency" (a JPA of Nevada County fire agencies, $0.1M over four years) is linked as a fire
  authority; it may be a coordination body without a department of its own.
- `config/categories.csv` has no category for grants. CAL FIRE's forest-health and urban-forestry grantees are split
  between `unclassified` (counted as purchasing) and `government` (not purchasing); a `grants` category (not
  purchasing) would describe them better.
