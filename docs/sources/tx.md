# Texas sources

Feasibility notes and build record for Texas (`st=tx`), PRD build-order steps 3 and 4 (`docs/prd/multistate-expansion.md`).
Output format: `docs/multistate/data-contract.md`. All sources were reached and fetched on 2026-10-06 from a cloud session
(raw folder `raw/2026-10-06/tx/`). Fiscal years 2021 on, as for Utah.

## Summary

| Source id | Source | Decision | Tier | Years | Rows | Dollars | Agencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | USFA registry and OpenFEMA grants (federal layer) | Done earlier | 4 | grants FY2005-2026 | 1,530 agencies; 641 matched awards | $130.2M grants | 1,530 |
| `tx_dir` | Texas DIR cooperative contract sales | Built | 2 | FY2021-2026 | 28,491 item lines | $15.63M | 318 |
| `tx_spd` | Comptroller Special Purpose District Public Information Database | Skipped: no spending fields | - | - | sample only | - | - |
| `tx_houston` | City of Houston checkbook, Houston Fire Department | Built | 1 | FY2021-2027 | 105,471 lines | $296.5M | 1 |
| `tx_dallas` | City of Dallas vendor payments, Dallas Fire-Rescue | Built | 1 | FY2026-2027 | 2,343 lines | $54.0M | 1 |
| `tx_austin` | City of Austin eCheckbook, Austin Fire Department | Built | 1 | FY2021-2027 | 12,275 lines | $158.1M | 1 |
| - | San Antonio Open Checkbook (OpenGov) | Skipped: no department field, no bulk download | - | - | - | - | - |
| `tx_fortworth` | Fort Worth accounts payable check register | Skipped: no department field | - | - | sample only | - | - |
| - | El Paso | Skipped: no vendor payment data found | - | - | - | - | - |
| `tx_cpa` | Comptroller State Expenditures by County (Texas A&M Forest Service) | Built | 3 | FY2021-2024 | 50 totals rows | $396.1M | 1 |
| - | Comptroller "Where the Money Goes" (state payee payments) | Skipped: interactive only | - | - | - | - | - |

Result in `data/states/tx/agencies.json`: 1,604 agencies (1,530 registry + 74 added from sources). Coverage: tier 1 (payee rows) 3
(Houston, Dallas, Austin fire departments), tier 2 (item lines) 316, tier 3 0 (the one agency with totals, Texas A&M Forest Service,
also has DIR item lines), tier 4 1,285. No agency without rows is given $0.

Owner decisions of 2026-10-06 applied in this note and the adapters: (1) payee names are shown as published, private persons
included; only email addresses and bank account text are cut (`config/payee_name_redactions.csv`); (2) identical DIR lines inside one
monthly report are kept as real repeat purchases, and only lines re-reported in a later month are dropped; (3) ESDs that provide only
EMS (ambulance districts) are excluded; (4) Texas A&M Forest Service stays in the main data with kind "State fire agency".

Fiscal years differ by source and are kept as each source defines them: DIR and the Comptroller use the Texas state FY (September to
August); Dallas and Austin use October to September; Houston uses July to June. `agency_sources.csv` records each link's `fy_start`, so an
agency with DIR and city rows (Houston, Austin) has two fiscal-year starts.

Tests: `python3 tests/multistate/check_tx.py` (no import of the adapters) recomputes from the raw files every total per source, agency
and fiscal year, every (agency, year, payee, amount) line and the row counts, and also checks DIR attribution (every raw customer name
linked or on a listed exclusion), redaction patterns, contract columns, dates, record ids, vendor map coverage and coverage tiers; it
passes. `python3 tests/multistate/check_federal.py TX` still passes. Running every adapter's normalize twice gives byte-identical files.

## Federal layer (done before this run)

From `config/states/tx/` (written by `pipeline/sources/federal.py`): 1,530 USFA registry departments (956 volunteer, 421 local,
59 county, 43 emergency services districts by name, 16 contract, 35 other kinds). OpenFEMA's firefighter grants dataset lists 2,665 Texas
awards for FY2005-2026 ($4.07 billion, including 430 Port Security grants to ports) to 1,051 recipient names; 367 names match a registry department strictly (641 awards,
$130.2M, 362 agencies) and 684 names are left unmatched in `grant_recipients_unmatched.csv`. This run did not touch those files.

## 1. Texas DIR cooperative contract sales (`tx_dir`): built, tier 2

- **URL**: FY2026 on <https://data.texas.gov/d/a743-wj72> ("Official - VSR Data for Cooperative & Tele Contracts FY2026");
  FY2010-2025 <https://data.texas.gov/d/w64c-ndf7> ("ARCHIVE DIR Cooperative Contract Sales Data Fiscal 2010 To 2025").
- **Format and access**: Socrata, SODA API (`/resource/<id>.json` with `$select`, `$where`, `$order=:id`, `$limit`, `$offset`), no key.
  Fire rows are filtered server-side; contact-person columns (customer contact, vendor contact, DIR contract manager, ITSAC
  staffing contractor) and street addresses are not payees and are not requested.
- **Fields**: fiscal year, customer name and type, vendor (DIR contract holder), reseller, contract number, type and subtype, RFO
  description, brand, quantity, unit price, purchase amount (quantity x unit price), invoice and PO numbers, order date; the FY2026 set
  adds contract category (Cooperative or Telecomm), product type and subtype, invoice date; the archive adds customer city and zip,
  shipped date and a record number (`sales_fact_number`).
- **Years and updates**: archive FY2010-2025 (closed, last updated 2025-10-03); FY2026 set updated monthly as reporting periods close
  (updated 2026-10-06, reporting months 2025-09 to 2026-08, so FY2026 is complete except for late vendor reports).
- **Size**: archive 10.9 million rows, of which 3.7 million in FY2021-2025 ($16.0 billion); FY2026 set 2.16 million rows ($3.84 billion).
  The full sets were not downloaded (no SHA-256); raw files hold the server-side filter result: archive 6,639 rows ($10.10M), FY2026
  25,148 rows ($7.35M). Raw: `archive_fy2021_2025.json.gz`, `current_fy2026.json.gz`, both datasets' metadata, `sample.json.gz`
  (100 unfiltered FY2026 rows).
- **Terms and robots.txt**: data.texas.gov is the Texas Open Data Portal on Socrata (Socrata terms of service); the datasets carry no
  license restriction. robots.txt allows `/resource/` and `/api/views/` (it disallows browse/search pages and OData) and asks for a
  1-second crawl delay, which `common.get` keeps.
- **How fire agencies appear**: as their own customers, with customer type "Local Government" (rarely "Other" or "State Agency"):
  "Cy-Fair Volunteer Fire Department", "Harris County Emergency Services District 9", "Travis County Emergency Services District No. 2",
  and, in FY2026, city fire departments listed apart from their city: "City of Houston Fire", "City of Carrollton Fire", "City of
  Laredo Fire". Cities buying for themselves ("City of Houston") are never linked. The server-side filter keeps customer names matching
  FIRE, ESD, E.S.D, EMERGENCY SERV, EMERGENCY SRVC, RESCUE, VFD, " FD" or FOREST SERVICE (352 names).
- **Attribution** (`config/states/tx/agency_sources.csv`, source `tx_dir`, reviewed by hand): 327 DIR names link to 318 agencies.
  136 match a registry name after spelling out abbreviations (`exact name`); 191 are `manual` with a note: variants such as "Volunteer"
  added or dropped, "City of X Fire" for the city's department, an ESD whose number the registry name carries
  ("Oak Hill Fire Department-Travis County ESD 3"), or a DIR customer zip equal to the registry's HQ zip ("Travis County Emergency Services
  District" with no number, zip 78734, is ESD 6/Lake Travis Fire Rescue; "City of Fair Volunteer Fire Department", zip 77095, is a
  misspelling of Cy-Fair). 74 clear fire agencies the registry lacks were added to `agencies_added.csv` (27 ESDs, 33 volunteer fire
  departments, 12 local and 1 county fire department, and Texas A&M Forest Service as "State fire agency"). Review (2026-10-06)
  corrected "City of Burnet Fire" from Burnet Volunteer Fire Department to the registry's City of Burnet Fire Department (TX-BP601),
  linked two added names to the registry rows they match ("Brazos County District 2 Volunteer Fire Department" = Brazos County
  Volunteer Fire Department District 2, TX-BC201; "Sabine Volunteer Fire Department", Kilgore = Sabine Fire and Rescue, Gregg County,
  TX-HP605), and linked three ESDs that are the same body as a registry department to that department instead of adding them: Harris County ESD 13
  (operating name Cypress Creek Fire Department since the 2019 merger; TX-KA515), Travis County ESD 8 (Pedernales Fire Department,
  Spicewood 78669; TX-WP411) and Hays County ESD 8 (Buda Fire Department per the Hays County ESD list; TX-KG301). Other added ESDs
  fund or run a registry department known by another name (Harris County ESD 9 and Cy-Fair Fire Department; ESD 7 and Spring
  Volunteer Fire Department; ESD 28 and Ponderosa Fire Department; ESD 46 and Atascocita Fire Department; Montgomery County ESD 6 and
  Porter, ESD 8 and South Montgomery County); whether each is the same body was not confirmed, so they are kept apart and the
  directory can list such a pair twice, but no dollar is counted twice. Each added ESD was checked (web search on
  2026-10-06) to provide fire service; Henderson County ESD 8 ($152), Nueces County ESD 3 ($229), Jefferson County ESD 4 ($4.9K),
  Northeast Gaines County ESD (-$89) and the unnumbered "Burnet County Emergency Service District" ($5.7K, Burnet County has fire ESDs
  and one EMS ESD, No. 10) could not be confirmed and are kept as named fire-or-EMS districts.
- **Not linked** (25 names, $1.82M; the list is asserted in `tests/multistate/check_tx.py`): pension systems (Texas Emergency
  Services Retirement System $837K, Dallas Police & Fire Pension, Houston Firefighters Relief & Retirement Fund), the Texas Commission
  on Fire Protection (regulator, $516K), TEEX's Emergency Services Training Institute, out-of-state customers (Oklahoma, Colorado),
  EMS-only ambulance districts (owner decision 3): Harris County ESD 1 and ESD 11, Harris County ESD 3 ($21K; "HC ESD 3 - EMS", fire
  service there is ESD 21), Harris County ESD 5 ($54K; Crosby EMS, Crosby VFD is funded by ESD 80), Hays County ESD 9 ($52K; EMS,
  formerly by contract with San Marcos-Hays County EMS), Bastrop County ESD 3 ($461; EMS district formed in 2024) and Medina County
  ESD 4 ($3.8K; "created solely to fund and oversee local EMS ambulance service" in Devine and Natalia),
  fire marshal offices, names that fit several registry departments with no city to decide (Pleasant Grove VFD, Tri-County VFD,
  Reno VFD, Mid-County Fire/Rescue, Northwest County VFD), and names that do not clearly identify a fire department (Pontotoc Ranch
  Fire Association, Pedernales Emergency Services). Every other customer name in the raw files is linked in `agency_sources.csv`.
- **Rows written**: 28,491 lines, $15.63M (FY2021 $1.24M, FY2022 $2.00M, FY2023 $1.76M, FY2024 $2.06M, FY2025 $1.70M, FY2026 $6.87M).
  FY2026 is larger because it adds telecom contracts (contract category "Telecomm": 23,088 lines, $4.05M). Largest buyers: Texas A&M
  Forest Service $2.53M, Cy-Fair Fire Department $2.05M, Lake Travis Fire Rescue $1.15M. Each line is in `line_items.csv.gz` (vendor = reseller
  when one is named, else the DIR contract holder; brand, product type, quantity, unit price) and rolled into `transactions.csv.gz`
  (payee = the same seller; category_published = contract type or category).
- **Duplicates and reversals**: no DIR vendor-month report is duplicated as a whole. 8 lines ($1,552.62) repeat a line from an earlier
  reporting month with every other field equal (same invoice and PO numbers); they are re-reports and dropped. Identical lines inside
  one monthly report are kept as real repeat purchases (owner decision 2; 528 extra archive rows, $195K, and 16,856 extra FY2026 rows,
  $822K, mostly telecom): they carry distinct DIR record numbers and are items DIR publishes without a
  line number, such as three toner cartridges at one price on one invoice or six $20 lines on one wireless bill. Credits are negative
  amounts (76 lines, -$241K) and are kept; most offset an equal sale.
- **Data quality**: IT and telecom only, so DIR spend is a small slice of a fire agency's purchasing. DIR customer names are entered by
  vendors and vary (typos, "Volunteer" added or dropped). FY2021-2025 have no telecom contracts, so years before and after FY2026 are not
  comparable for telecom. Order dates can predate the fiscal year (long-running telecom orders); `fiscal_year` is DIR's own field.

## 2. Comptroller Special Purpose District Public Information Database (`tx_spd`): skipped

- **URL**: <https://comptroller.texas.gov/transparency/local/sb625/lookup.php>, search app <https://spdpid.comptroller.texas.gov/>,
  bulk CSVs at `https://assets.comptroller.texas.gov/open-data-files/spdpid-<name>.csv` (entity, county, alternate, individual-debt,
  non-compliant, related-party), joined on `spd_publ_id`. The lookup page says the database "can also be downloaded from Data.Texas.gov";
  no such dataset turned up in the data.texas.gov catalog, so the Comptroller's own CSV links are the bulk source.
- **Access, terms, robots.txt**: plain HTTPS downloads offered "for offline use"; comptroller.texas.gov robots.txt allows
  `/transparency/`; assets.comptroller.texas.gov has no robots.txt. Self-reported, unverified by the Comptroller.
- **ESDs**: included. Entity type "Emergency Services District": 282 ESDs, 190 to 267 reports a year for report years 2018-2026
  (2,048 entity-year rows in all).
- **Fields** (entity file, 21,689 rows, 8.1 MB, SHA-256 `1e429481bb627bf333867a635c02689720050e128ad20560efe081f5dc5d2d55`): name,
  report year, taxpayer id, city, county code, website, entity type, flags (outstanding bonds, gross receipts, cash and temporary
  investments, no criteria), authorized and outstanding debt, principal and interest, sales tax rate, ad valorem tax rates
  (maintenance and operations, interest and sinking, total, effective, rollback). No revenue, expenditure or spending fields. Other
  files: county links (22,595 rows), uploaded audit and budget documents by file name (11,075), individual debt obligations (991),
  non-compliant entities (85), related parties (board members and contacts with personal names, 38 MB; not downloaded).
- **Updates, duplicates**: districts report once a year (report years 2018-2026 present); duplicate entity-year rows were not checked
  (only the 100-row sample is kept). No spending lines, so reversals do not apply.
- **Decision**: skipped. It gives tax rates and debt, not annual spend, so it cannot supply tier-3 totals. It could later help identify
  ESDs (taxpayer ids, cities) or point to uploaded audit PDFs. Sample: `raw/2026-10-06/tx/tx_spd/sample.csv.gz` (100 ESD rows of the
  entity file).

## 3. Large-city open data

### Houston (`tx_houston`): built, tier 1

- **URL**: <https://data.houstontx.gov/dataset/checkbook> (Finance Department, CKAN); one CSV per City fiscal year 2018 to the current
  one. License: Open Data Commons Attribution.
- **Access**: download links read from the dataset page (robots.txt disallows `/api/`, so the CKAN API is not used; it also disallows
  `*.gz`, which is not fetched). Downloads redirect to a presigned S3 URL written with an explicit `:443` port; Python's urllib follows
  the redirect with a Host header that breaks the signature (403 SignatureDoesNotMatch), so the adapter resolves the redirect itself and
  drops the port. robots.txt also sets `Crawl-delay: 10` for every user agent: the 2026-10-06 fetch spaced its 8 requests to
  data.houstontx.gov by the 1-second `common.get` throttle plus each 12-62 MB S3 download in between; review added a 10-second wait
  before each request to that host to `tx_houston.py` for future fetches.
- **Update frequency**: the dataset page shows "Last Updated September 17, 2026"; the current-year file is refreshed during the year
  (FY2027 holds July to mid-September 2026). No stated schedule.
- **Fields**: payment document number, fund, department id and name, WBS (project), GL account number and description, vendor name,
  vendor invoice, fiscal year, clearing date, amount, type of procurement, PO number and item, contract number. No line description.
- **Years and size** (full files; SHA-256 of each in `manifest.json.gz`):

  | FY (Jul-Jun) | Lines | HFD lines | Bytes |
  | --- | --- | --- | --- |
  | 2021 | 240,674 | 12,822 | 55,166,834 |
  | 2022 | 235,142 | 15,543 | 53,449,845 |
  | 2023 | 268,192 | 17,740 | 61,595,615 |
  | 2024 | 267,983 | 16,195 | 60,577,629 |
  | 2025 | 272,348 | 17,210 | 61,881,423 |
  | 2026 | 271,696 | 19,967 | 61,873,844 |
  | 2027 (Jul-Sep 2026) | 52,637 | 6,018 | 11,902,906 |

  Raw keeps only Department ID 1200 lines (`checkbook-<fy>-hfd.csv.gz`, 1.2 MB in all) plus the dataset page and a 100-line sample.
- **Fire identification**: Department ID 1200 "Houston Fire Department (HFD)" -> TX-KA926 (`department code`).
- **Rows written**: 105,471 lines, $296.5M (FY2021 $36.2M, FY2022 $43.3M, FY2023 $30.8M, FY2024 $38.8M, FY2025 $70.1M, FY2026 $62.1M,
  FY2027 to date $15.2M). Description = type of procurement, project, PO and contract; account = fund and GL account; category_published
  = GL account description.
- **Duplicates and reversals**: 24 lines identical in every column ($438,798) dropped, for example one invoice's PO lines listed twice in
  the same payment document. 1,457 negative lines (-$11.7M: early payment discounts, credits, vendor offsets on the reconciliation
  account) are kept, so amounts are net.
- **Names**: published as the City publishes them (owner decision 1), individuals included; `common.withhold_person` cuts only email
  addresses and bank account text (none in the HFD lines). The City itself pays deceased employees' unclaimed wages (GL 220550, 88
  lines, $4.27M) through "GENERAL ONE-TIME VENDOR" ($4.7M in all) and masks some vendors as `*` (vehicle and equipment leases, $5.46M);
  both are kept as published.
- **Data quality**: lines can be charged to inventory (GL "COH General Inventory Account") rather than an expense account; capital
  projects for fire stations appear under HFD when coded to HFD.

### Dallas (`tx_dallas`): built, tier 1, FY2026 only

- **URL**: <https://www.dallasopendata.com/d/x5ih-idh7> "Vendor Payments for Fiscal Year 2019 - Present" (Socrata, SODA API). License:
  Open Data Commons Attribution. robots.txt allows `/resource/` (crawl delay 1 s).
- **Fields**: run date, fiscal year and month (October = month 1, period 13 adjustments), document id, payment subtotal per line,
  vendor code and name, zip, fund type, department code and name, activity, object group, object, commodity code and description.
- **Years**: despite the title the dataset now holds only FY2026 (October 2025 to September 2026, all 12 months) and the first days of
  FY2027 (93,790 rows in all, $2.14 billion). Earlier years are not published in it any more; the separate FY2016-2018 dataset
  (`awax-wfz9`) and 2012-2016 payment registers are older than FY2021 and not used. Updated daily.
- **Fire identification**: department `DFD` "Dallas Fire-Rescue" -> TX-DH807 (registry name "Dallas Fire Department").
- **Rows written**: 2,343 lines: FY2026 $53.9M (Capital Outlay $35.0M, mostly apparatus), FY2027 to date $0.13M. Raw: `dfd.json.gz`
  (server-side filter), metadata, 100-row sample.
- **Duplicates and reversals**: no lines identical apart from the Socrata row id. 14 negative lines (-$763K) kept.
- **Names**: published as the City publishes them (owner decision 1), payees on claims, refund and reimbursement objects included.
  The City itself leaves out some payments "for vendor anonymity", so totals are below the budget.

### Austin (`tx_austin`): built, tier 1

- **URL**: <https://data.austintexas.gov/d/8c6z-qnmj> "Austin Finance Online eCheckbook" (Socrata, SODA API), the flat file behind
  <https://financeonline.austintexas.gov/afo/finance/>. No license in the metadata; robots.txt allows `/resource/` (crawl delay 1 s).
- **Fields**: fiscal year and period, department, fund, division, group, object category and object, legal vendor name, vendor/customer
  indicator, referenced documents (PO, contract), commodity, check/EFT issue date, check status, accounting line description, amount.
- **Years and size**: FY2009 to the current year (2.14 million lines, $38.6 billion), updated daily. Some Austin Energy lines are withheld
  as competitive matters (none concern Fire).
- **Fire identification**: department 83 "Fire" -> TX-WP801. Emergency Medical Services (93, Austin-Travis County EMS) and Public
  Safety & Emergency Management (96) are separate departments and not linked.
- **Rows written**: 12,275 lines, $158.1M (FY2021 $27.8M, FY2022 $23.1M, FY2023 $31.7M, FY2024 $44.5M, FY2025 $23.0M, FY2026 $8.0M,
  FY2027 to date $0.05M). FY2024 is high from station construction contracts; FY2026 is low because few construction contracts were paid
  under department 83 that year (Contractuals $4.6M against $16-40M before). Raw: `fire.json.gz`, metadata, 100-row sample.
- **Duplicates and reversals**: no identical lines; no negative lines. Check statuses Paid (12,129), Outstanding (136, issued not yet
  cashed) and Escheat (10, uncashed and sent to the state) are all kept, since the City's expense stands.
- **Names**: published as the City publishes them (owner decision 1); individuals paid as vendors (artists, consultants, mileage and
  expense refunds) appear by name.
- **Data quality**: one line per accounting line, so one check can be several rows; capital projects for fire stations appear under
  department 83 only when charged there; FY2027 holds only its first days.

### San Antonio: skipped

The City's "Open Checkbook" (<https://www.sa.gov/Directory/Departments/Finance/Transparency/Payments>) is an OpenGov report
(sanantoniotx.opengov.com) that shows payments "aggregated by month by provided service type"; it has no department field and no
documented bulk download or API, and data.sanantonio.gov (CKAN) has no payment dataset. Terms and robots.txt (checked 2026-10-06):
sanantoniotx.opengov.com serves an empty robots.txt; www.sa.gov disallows many `/Directory/Departments/...` pages but not the
Transparency pages; data.sanantonio.gov disallows `/api/` and `/datastore/` and asks for a 10-second crawl delay. No years, fields or
row counts could be read beyond the report's monthly service-type totals. The fire department's own DIR purchases are covered ("City of
San Antonio Fire", $152K in FY2026). No sample: no downloadable file.

### Fort Worth (`tx_fortworth`): skipped

- **URL**: <https://www.fortworthtexas.gov/departments/finance/check-register>; monthly Excel files for the current year and one file per
  year for FY2021-2025 (for example `z_ap_checkbook-fy25-vchrlines.xlsx`, 15.7 MB, 231,744 voucher lines, $2.45 billion, SHA-256
  `26444dcff69ab07e6de8cd8c438870305f914b443081edbd2e713f0f945d7ef0`). robots.txt does not restrict `/files/`.
- **Fields**: payment id, date, status, amount, method, voucher id, supplier name, invoice number and date, fund, account, project.
  No department.
- **Data quality, duplicates**: not examined beyond the sample, since the source is skipped; the files carry a payment status column
  (voided payments would need handling). No separate terms of use are posted for the files.
- **Decision**: skipped. Fire lines can be picked out only through fire-named capital projects ("Fire Station 37", "Fire Apparatus 2024
  Tax Notes": about $15M in FY2025) and one account ("Fire Inventory", $1.1M); the department's operating purchases cannot be told apart
  from other General Fund spending, so the rows would understate Fort Worth Fire badly while looking like tier 1. Its DIR purchases are
  covered ("City of Fort Worth Fire"). Sample: `raw/2026-10-06/tx/tx_fortworth/sample.csv.gz` (100 FY2025 lines, converted from Excel).

### El Paso: skipped

data.elpasotexas.gov was unreachable from the session (proxy 502); the City's ArcGIS Hub (opendata.elpasotexas.gov, crawl delay 60 s)
returned no checkbook or payment dataset, and a web search found none. El Paso County ESD 1 and 2, Horizon City and Socorro fire
departments are covered through DIR.

## 4. Other sources looked at

### Comptroller State Expenditures by County (`tx_cpa`): built, tier 3, Texas A&M Forest Service only

- **URL**: one data.texas.gov dataset per state fiscal year: FY2021 `tup7-smjg`, FY2022 `xys8-xb33`, FY2023 `iyey-5sid`, FY2024
  `2zpi-yjjs` (<https://data.texas.gov/d/2zpi-yjjs>); FY2025 not yet published. Socrata, SODA API; same terms and robots.txt as DIR.
- **Fields**: fiscal year, agency number and name, county, major spending category, amount. Net expenditures of funds held in the State
  Treasury (USAS). Column names change by year (FY2023 uses `expenditure_category`, `number`, and text amounts with commas); the adapter
  handles each.
- **Why**: the PRD leaves state fire agencies open. Texas A&M Forest Service (agency 576) is the state's wildland fire agency; it is
  added as kind "State fire agency" (`TX-S-texas-a-and-m-forest-service`) and also appears in DIR. The registry lists only one of its
  district offices ("Texas Forest Service- Jefferson District"), which is not linked.
- **Rows written**: 50 totals rows (fiscal year x category, summed over counties): FY2021 $68.3M, FY2022 $98.3M, FY2023 $76.3M, FY2024
  $153.3M (the 2024 Panhandle fires). Categories: salaries, benefits, intergovernmental payments (grants to local fire departments),
  supplies, capital outlay, other expenditures. These are whole-agency totals (forestry and fire), not fire purchasing.
- **Updates**: one dataset per state fiscal year, published after the year closes (FY2025 was not out on 2026-10-06).
- **Duplicates**: one dataset per year; normalize stops if a year repeats or a dataset has no rows for agency 576.

### Comptroller "Where the Money Goes": skipped

State agency payments by payee are published only in an interactive QlikView application (bivisual.cpa.texas.gov) with no bulk download
or documented API (bivisual.cpa.texas.gov has no robots.txt; it returns 404); scraping it was not attempted. This would be the source for Texas A&M Forest Service payee rows if the Comptroller
publishes a bulk file.

## Payee names

Owner decision 1 (2026-10-06): payee names are shown as published, private persons included. Every payee and item vendor goes
through `common.withhold_person` directly, which now only replaces payee text matching `config/payee_name_redactions.csv` (email
addresses, bank transfer text with account numbers) by "Payee name withheld"; no Texas payee matches, and no description, account or
category text does either. The earlier local `payee()` wrappers (which trusted `vendor_map_additions.csv`) and the forced
`person_flag` rules on employee, refund, claims and reimbursement accounts were removed from all four adapters. Names are not
classified as persons or companies. `tests/multistate/check_tx.py` checks every published payee against the raw name (whitespace
collapsed) and asserts that no redaction pattern matches any published text.

## Vendor map additions

`config/states/tx/vendor_map_additions.csv`: 210 payee keys (82 high, 99 medium, 29 low confidence), reusing `config/vendor_map.csv`
canonical names when the company is the same (Grainger, AT&T, Verizon, Stryker, SHI International, CDW Government, Esri, Staples, Home
Depot, Rush Truck Centers, Municipal Emergency Services, Jones & Bartlett Learning). Payees already in `vendor_map.csv` under the same
key are not repeated; `spend` and `agencies` are recomputed from the data after review. Texas purchasing dollars (positive net spend of
payees not mapped to a non-purchasing category) are $502.3M; the additions cover 77.4% and keys already in `vendor_map.csv` another
18.0%: 95.4% together (`check_tx.py` asserts at least 90%). Unmapped: $23.0M across 1,577 smaller payees, the largest being Houston's
masked `*` vendor ($5.46M) and payees named after a person or a person's firm (now shown by name).

## Open questions

- Resolved by the owner on 2026-10-06 and applied: names shown as published (decision 1); identical DIR lines inside one monthly report
  kept (decision 2); EMS-only ESDs excluded (decision 3; seven DIR names, above); Texas A&M Forest Service in the main data as "State
  fire agency" (decision 4).
- ESD service checks rest on web sources read on 2026-10-06 (district and county pages, local news); five small added ESDs could not be
  confirmed (section 1). An ESD-to-department table would let the directory merge ESDs with the departments they fund.
- Dallas publishes only the current and previous fiscal year in its open data set (confirmed 2026-10-06 by a grouped SoQL query: FY2026
  92,904 lines and FY2027 886 lines, nothing earlier); FY2021-2025 for Dallas Fire-Rescue would need a public information request or an
  archived copy.
- DIR `fiscal_year` is the Texas state FY (September to August) even for cities with another fiscal year, so Houston and Austin fire
  departments carry two `fy_start` values in `agencies.json`.
- Totals cross-checked on 2026-10-06 with separate grouped SoQL queries: Dallas DFD FY2026 $53,891,181.76 and FY2027 $131,708.13, Austin
  department 83 FY2021-2027 (each year to the cent) and the Comptroller FY2024 Texas A&M Forest Service total $153,278,599.18 all equal
  the normalized files.
