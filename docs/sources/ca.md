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
| `ca_sf` | San Francisco Vendor Payments (Vouchers) | 1 | **built** | 1 (San Francisco Fire Department) | 26,903 lines | $202.3M | FY2021-FY2027 (FY2027 partial) |
| `ca_la` | Checkbook L.A. (Los Angeles City Controller) | 1 | **built** | 1 (Los Angeles Fire Department) | 141,106 lines | $645.8M | FY2021-FY2027 (FY2027 partial) |
| `ca_riverside_county` | County of Riverside Check Book | 1 | **built** | 1 (Riverside County Fire Department) | 237,228 lines | $1,580.6M | FY2021-FY2027 (FY2027 partial) |
| `ca_corona` | City of Corona Open Expenditures (CorStat) | 1 | **built** | 1 (Corona Fire Department) | 13,355 lines | $20.7M | FY2021-FY2026 |
| `ca_moreno_valley` | City of Moreno Valley Open Expenditures | 1 | **built** | 1 (Moreno Valley Fire Service) | 2,338 lines | $140.2M | FY2021-FY2026 |
| `ca_fiscal` | Open FI$Cal department vendor transactions (CAL FIRE) | 1 | **built** | 1 (CAL FIRE, state fire agency) | 818,704 rows (3,226,425 source lines) | $9,727.3M | FY2021-FY2026 (FY2026 to 2026-06-30) |
| `ca_scprs` | SCPRS Purchase Order Data (CAL FIRE purchase orders) | 2 | **built** (old years only) | 1 (CAL FIRE) | 21,654 item lines | $880.3M | FY2013-FY2015 only |
| `ca_sandiego` | City of San Diego Operating Actuals | - | skipped: no payee; sample kept | 0 | - | - | - |
| `ca_sacramento` | City of Sacramento Checks Issued, Purchase Orders | - | skipped: no department field; samples kept | 0 | - | - | - |
| `ca_lacounty` | County of Los Angeles Open Expenditures | - | skipped: no payee; sample kept | 0 | - | - | - |
| `ca_modesto` | City of Modesto Weekly AP Transactions | - | skipped: weekly figures only; sample kept | 0 | - | - | - |
| (none) | San Jose, Indio, West Hollywood, Marin County, others | - | skipped (see "Other candidates") | 0 | - | - | - |

**Owner dedup rule of 2026-10-07, applied to every line source above:** lines equal in every published field but
the source's own row, voucher, invoice, payment or PO ids are kept once. It drops 139,312 lines and $562.6M (tier 1:
138,168 lines, $556.8M, 4.3% of tier-1 dollars; SCPRS 1,144 item lines, $5.8M). In these sources almost none of
that is a reloaded batch or a doubled day: most dropped lines are separate items or payments of one price (several
ambulances or engines on one invoice, quarterly contract installments, employee reimbursements), because three
sources have no description (FI$Cal) or no payment date (SF) or no line number (Riverside County, Corona, SCPRS).
Numbers per source and the largest cases: "Duplicates and reversals: summary" below.

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
- **Rows:** 35,749 raw lines (control agrees) -> 34,637 lines with a paid amount ($220.6M) -> 26,903 lines ($202.3M)
  after the owner's dedup rule; 1,112 lines with only pending or retainage amounts left out. FY2022 ($57.2M) is about
  twice a normal year because of one $38.8M capital outlay payment to Chicago Title Company (a property purchase
  through escrow; $5.9M more in FY2023); FY2021 ($13.6M) is about half a normal year.
- **Data quality:** no documented payment date (`data_as_of` is undocumented and often outside the fiscal year), so
  `posting_date` is empty for every SF row.
- **Duplicates and reversals:** owner rule of 2026-10-07: lines equal in fiscal year, payee, contract title, program,
  character, object, sub-object, fund and amount paid are kept once (the voucher and PO numbers are ids). With no
  payment date this drops 7,734 lines, **$18.2M (8.3% of SF dollars)**, all on different vouchers: fleet bought at one
  price in one year (Ferrara engines $4.2M, Braun ambulances $2.3M, Rosenbauer hose tenders $1.4M) and equal recurring
  payments ("Single Payment Payees" $1.8M, UCSF/SFGH Medical Group $1.2M). No line was identical in every raw column.
  The voucher number repeats across lines, so the record id is voucher plus a running number. 300 negative (credit)
  lines kept.
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
- **Rows:** 175,405 lines ($696.8M) -> 141,106 lines ($645.8M) after the owner's dedup rule, FY2021-FY2027 (FY2027
  partial, payments through 2026-09-09).
- **Data quality:** every line has a check date inside its fiscal year; item description, quantity and unit price
  only where the payment is against a purchase order; 586 negative lines kept (722 before the dedup rule; 698
  cancellations, other credits).
- **Payees:** the City publishes most refunds of ambulance charges and fire service fees to "PRIVACY-FIRE" (12,802 of
  12,808 ambulance-refund lines, $11.6M, before the dedup rule; 11,422 lines, $9.2M after it, because refunds of one
  amount to different people on one day are identical lines); a few refund payees are named and shown as named.
- **Duplicates and reversals:** owner rule of 2026-10-07: lines equal in payment date, payee, description, program,
  fund, account, expenditure type and amount are kept once (transaction id, invoice and PO numbers and their line
  numbers are ids). This drops 34,299 lines, **$51.0M (7.3% of LA dollars)**; 25,098 of them ($47.8M) are other
  lines of the same payment, mostly invoices that list several vehicles at one price on separate lines (Braun
  Northwest ambulances $26.3M, for example 12 at $205,625 on one invoice of 2022-12-12; Pierce aerial ladder trucks
  $3.6M); 9,201 ($3.2M) are on other payments. PRIVACY-FIRE refunds are $2.4M of the $51.0M. No line was identical in
  every raw column. Cancelled checks are their own negative
  lines (payment status CANCELLED; 698 lines, 677 carrying the same transaction, invoice line and distribution line as
  the payment they cancel) and are kept, so a cancelled payment nets to zero; record id gets "-cancelled".
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
- **Rows:** 277,875 raw lines ($1,666.8M) -> 237,228 lines, $1,580.6M, after the owner's dedup rule, FY2021-FY2027
  (FY2027 partial, to 2026-08-26).
- **Data quality:** ledger lines with a date inside the fiscal year; vendor names as keyed (one company can appear
  in several spellings); $1.32B of the dollars are the County's contract payments to the State (CAL FIRE), an
  inter-agency payment rather than a purchase. One line of the department "Coachella Fire Protection Dist" exists in
  the source and is not taken (the district is tier 3 through `ca_sco_districts`).
- **Duplicates and reversals:** owner rule of 2026-10-07: lines equal in date, payee, description, business unit,
  fund, account, expense category and amount are kept once (invoice and payment ids are ids). The source has no line
  number, so this drops 40,647 lines, **$86.2M (5.2% of the dollars)**: 22,609 lines ($8.7M) inside one invoice (one
  line per phone on a wireless bill, several items at one price; 25,211 lines, $9.5M, repeat another in every raw
  column, spread over every period with no reload burst) and 18,038 lines ($77.6M) on other invoices, of which
  **$72.4M are two CAL FIRE contract invoices** (176557 and 176845, both paid 2026-03-16, each with lines of
  $36,159,244.27 and $36,227,427.80): either one quarter paid twice or two quarters billed at the same amount; the
  source does not say which. The earlier rule (drop only invoices loaded twice) dropped 929 lines ($725,008). 5,262
  negative lines (credits, reversals) kept.
- **Decision:** built.

## `ca_corona`: City of Corona Open Expenditures (tier 1, built)

- **URL:** <https://corstat.coronaca.gov/d/mdmf-aswt> (CorStat; uploaded every Friday after the check run; rows updated
  2026-10-02). FY2016 on.
- **Access:** SODA; filter department code 30 (FIRE), `fiscal_year >= 2021`.
- **Fields:** fiscal year and period, fund, department code and name, department activity, vendor id, name, city,
  state and zip, payment id and date, invoice id, expense category, description, amount.
- **Fire agency:** department 30 -> Corona Fire Department (CA-33025). Lines include pension and benefit payments
  naming the person paid (shown, owner decision).
- **Rows:** 14,500 raw ($21.8M) -> 13,355 lines, $20.7M, after the owner's dedup rule, FY2021-FY2026 (payments
  through 2026-06-30).
- **Data quality:** payment dates inside the fiscal year; many small lines (pension, benefit, refund and
  reimbursement payments name the person paid, shown as published).
- **Duplicates and reversals:** owner rule of 2026-10-07: lines equal in payment date, payee, description, department
  activity, fund, expense category and amount are kept once (payment and invoice ids are ids). No line number, so
  this drops 1,145 lines, **$1.14M (5.2%)**: 903 ($0.39M) inside one invoice (copier and hotel invoices) and 242
  ($0.76M) across invoices, mostly one $690,075.97 KME custom pumper line paid on 2020-09-25 on two invoices
  (G11148001, G11149001; probably two pumpers). The earlier rule dropped 19 lines. 688 negative lines (voids, credits)
  kept.
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
- **Rows:** 2,369 lines -> 2,338 lines, $140.2M, after the owner's dedup rule, FY2021-FY2026 (payments through
  2026-06-24). Most dollars are the City's contract
  payments to the County of Riverside for fire staffing.
- **Data quality:** payment dates inside the fiscal year; "Fire - Office of Emergency Mgmt" is small ($0.9M, radios,
  satellite phones, supplies); Fire Operations ($132.2M) is mostly the County contract.
- **Duplicates and reversals:** owner rule of 2026-10-07: lines equal in payment date, payee, description,
  department, program, fund, expense category and amount are kept once (payment id, invoice id, invoice line and
  distribution line are ids): 31 lines, $15,487 (15 inside one invoice, 16 across invoices; largest: N95 masks from
  Office Depot, $3,043.94 on three invoices of 2022-03-21). No line was identical in every raw column. 3 negative
  lines kept.
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
  published field but the line number): 873,016 rows, $10,127.5M; after the owner's dedup rule 818,704 rows,
  $9,727.3M (FY2021 $1,491M, FY2022 $1,418M, FY2023 $1,421M, FY2024 $1,228M, FY2025 $2,277M, FY2026 $1,893M to
  2026-06-30). Rows summing to $0.00 are dropped (34,994).
- **Data quality:** raw and unaudited (terms of use); accounting dates inside the fiscal year; CalCard lines name the
  card issuer, not the merchant; much of the money is payments to other governments (contract counties, cities and
  fire districts reimbursed for mutual aid) and grants (forest health, urban forestry), which are not purchases.
- **Payees:** the State publishes employee travel, per diem and training reimbursements to "CONFIDENTIAL" ($35.1M;
  $31.9M after the dedup rule);
  other payees, sole proprietors included, are named and shown as published.
- **Duplicates and reversals:** lines identical in every column (same document id, line and distribution, amount and
  date) are kept once before summing (1,308 dropped across six years). Then the owner rule of 2026-10-07 on the
  summed rows: rows equal in accounting date, payee, program, sub-program, fund, account, account category and
  amount are kept once (the voucher number is an id). FI$Cal has **no description field**, so this drops 54,312
  rows, **$400.1M (4.0% of CAL FIRE dollars)**, all on different vouchers: cooperative fire protection installments
  to contract counties paid in equal amounts on one day ($147.0M to governments: Kern $35.8M, Los Angeles $30.0M,
  Ventura $24.7M, Santa Barbara $22.6M), equipment bought at one price (Air Methods aircraft $24.5M, Holt of
  California seven vehicles of $617,325.88 on 2024-04-02, Downtown Ford $16.1M), Perimeter Solutions retardant
  ($18.3M), 17,366 "CONFIDENTIAL" employee reimbursements ($3.2M) and 852 US Bank CalCard rows ($1.8M). The raw lines
  of these vouchers are identical in every column but the document id (checked for the largest sets). Source lines
  inside one voucher that differ only in line or distribution number (205,953 lines, $106.2M, mostly CalCard
  statement lines) are summed into the voucher's row, not dropped. Lines repeating a document id with another date
  or amount are later postings (corrections, reversals) and are kept, negative where published so (5,401 negative
  rows).
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
- **Rows:** 23,244 raw lines -> 21,654 item lines after the owner's dedup rule ($880.3M: FY2013 $191.5M, FY2014
  $131.7M, FY2015 $557.1M), also rolled into `transactions.csv.gz` (payee = supplier). 446 $0.00 lines
  (contract-amendment text) left out.
  Amounts are purchase order amounts (commitments), not payments.
- **Data quality:** some purchase dates are typos (1912, 2511) and are left empty; PO dates of long-running agreements
  can precede the fiscal year the line is registered in; no brand field.
- **Duplicates and reversals:** owner rule of 2026-10-07 on the item lines: lines equal in date, supplier, product
  type, description, quantity, unit price and amount are kept once (PO and requisition numbers are ids); the
  transaction copy of a dropped item line is dropped with it. No line number, so this drops 1,144 lines, **$5.8M
  (0.7%)**: 555 ($3.6M) inside one PO (AT&T network maintenance, 38 lines of $6,500 on one PO; CompuCom licences
  $1.0M) and 589 ($2.2M) across POs (a $952,295 Prison Industry Authority Nomex line listed twice). The earlier rule
  dropped 35 lines. 406 negative lines kept. Two SCPRS transaction rows can still be equal where their item lines
  differ in quantity, unit price or product type (21 such sets).
- **Decision:** built with years labelled 2013-2015 in `sources.csv`; tier 2 (brand is absent; product type is the
  UNSPSC commodity).

## Duplicates and reversals: summary

Owner decision of 2026-10-07: drop identical lines and identical (doubled) days. A line is identical to another
when every published field except the source's own row or transaction id is equal: agency, fiscal year, posting
date, payee as published, description, account, published category and amount (item lines: also vendor, brand,
product type, quantity and unit price). One is kept, the rest dropped; a doubled day is a set of identical lines;
lines without a date compare on fiscal year; negative lines compare like any other (a reversal is not identical to
the payment it reverses). Applied by `ca_common.drop_identical` to every row an adapter writes (FI$Cal: to the rows
summed per voucher; SCPRS: to the item lines, transaction copies follow), and mirrored independently in
`check_ca.py`. The totals sources (`ca_sco_*`) are not affected.

| Source | Lines before | Lines dropped | Dollars dropped | Share of dollars | Sets | Same document | Other documents | Negative lines dropped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ca_fiscal` (summed rows) | 873,016 | 54,312 | $400,143,042.18 | 3.95% | 29,445 | 0 | 54,312 ($400.1M) | 338 (-$2.3M) |
| `ca_riverside_county` | 277,875 | 40,647 | $86,244,041.95 | 5.17% | 14,908 | 22,609 ($8.7M) | 18,038 ($77.6M) | 380 (-$128K) |
| `ca_la` | 175,405 | 34,299 | $51,021,623.97 | 7.32% | 15,040 | 25,098 ($47.8M) | 9,201 ($3.2M) | 136 (-$68K) |
| `ca_sf` (no date) | 34,637 | 7,734 | $18,242,008.80 | 8.27% | 2,154 | 0 | 7,734 ($18.2M) | 13 (-$4K) |
| `ca_corona` | 14,500 | 1,145 | $1,142,201.41 | 5.23% | 462 | 903 ($0.39M) | 242 ($0.76M) | 65 (-$17K) |
| `ca_moreno_valley` | 2,369 | 31 | $15,487.12 | 0.01% | 23 | 15 ($4K) | 16 ($12K) | 0 |
| `ca_scprs` (item lines) | 22,798 | 1,144 | $5,824,389.82 | 0.66% | 506 | 555 ($3.6M) | 589 ($2.2M) | 21 (-$11K) |
| All | 1,400,600 | 139,312 | $562,632,795.25 | | 62,538 | | | |

"Lines before" counts lines with an amount (SF: with a paid amount; SCPRS: not $0) before the rule; "same document"
means the same voucher, invoice, payment or PO as the line kept. **What the rule drops here is mostly not
duplication.** No source has a reloaded batch: control queries (rows and dollars per year, taken at fetch time)
match the raw files, and no (fiscal year, date) in any dated source has every line repeated the same number of times
(SCPRS aside: two PO dates, 8 lines, $16,615). The sets are separate items and payments of one price that the
source cannot tell apart once its ids are set aside:
- Open FI$Cal has no description: equal installments to contract counties on one day ($147.0M), vehicles and
  aircraft bought at one price ($24.5M Air Methods, $16.1M Downtown Ford, $16.2M Holt of California), employee
  reimbursements to CONFIDENTIAL ($3.2M).
- San Francisco has no payment date, so equal payments within a fiscal year count once (vehicles $10.6M).
- Los Angeles, Riverside County and Corona list several identical items on separate lines of one invoice (LA
  ambulances $26.3M), and Riverside County has two CAL FIRE contract invoices of $72.4M each paid the same day.
Before this rule the adapters dropped only lines identical in every raw column (FI$Cal 1,308) and invoices or POs
loaded twice in full (Riverside County 929, Corona 19, SCPRS 35). Every adapter keeps credits, voids and reversals
as published (negative lines), so totals are net.

## Payee names

Owner decision of 2026-10-06: payee names are shown as published, private persons included. Every adapter calls
`common.withhold_person` directly, which cuts only payee text matching `config/payee_name_redactions.csv` (email
addresses, bank account text); no California payee matched, so no line is cut. The sources' own masking stays as the
sources publish it ("PRIVACY-FIRE" in Los Angeles, "CONFIDENTIAL" in FI$Cal, the SF Controller's removal of payments
to employees). `check_ca.py` reports 126,232 lines whose payee looks like a person's name (shown).

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
forest-health and urban-forestry grantees). Before the merge the two files mapped 91.3% of $5.93B (real category
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
   payee and amount lines) after the owner's dedup rule, whose line identity the check builds from the raw columns
   itself, for SF, LA, Riverside County, Corona, Moreno Valley, SCPRS and FI$Cal (rows summed per voucher from the six
   raw files, checked against the manifest's rows and dollars); no two published rows of one source equal in every
   column but `source_record_id` (SCPRS transaction copies aside, see above); totals per agency and year for both
   SCO sources (every Fire Protection district linked);
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
`config/states/ca/` byte-identical between the runs; and again on 2026-10-07 after the dedup rule: the seven line
adapters twice, all 12 files byte-identical). The check was fault-tested with an injected copy of one SF line under a
new record id (fails on the line multiset).

## Open questions

- Cities with an SCO fire line but no registry fire department (Imperial, Delano, Willows, Corcoran, Blythe, Orland,
  Crescent City and some smaller cities): some may run their own departments (would be added to `agencies_added.csv`
  after confirmation); left unlinked.
- Should the SCO city line also include Emergency Medical Services (a separate line) for cities whose fire department
  runs ambulances?
- Moreno Valley fire-station costs booked to Fleet & Facilities (about $4.1M) are excluded; include them?
- San Francisco has no payment date; should the page show SF rows by fiscal year only?
- Dedup rule of 2026-10-07: in California it removes $562.6M, mostly separate items and payments of one price
  (table under "Duplicates and reversals: summary"). Keep it as decided, or exempt lines on the same document with
  different line numbers (LA, $47.8M) and sources without a description or date (FI$Cal $400.1M, SF $18.2M)?
  Riverside County's two $72.4M CAL FIRE invoices of 2026-03-16 need the County's answer either way.
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
