# Idaho: source notes

Run of 2026-10-06 (raw folder `raw/2026-10-06/id/`). PRD: `docs/prd/multistate-expansion.md`; output format:
`docs/multistate/data-contract.md`.

## Result

| Source id | Source | Tier | Decision | Agencies with rows | Rows | Dollars | Years |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | Federal layer (USFA registry, OpenFEMA grants) | 4 | built earlier (`federal.py`) | 198 registry departments, 54 with grants | 120 matched awards | $28.9M matched | grants 2005-2025 |
| `id_lgr` | Transparent Idaho, Local Government Registry: fire district totals | 3 | **built** | 156 | 577 district-years | $577.5M actual expenditures | FY2021-FY2024 |
| `id_cities` | Transparent Idaho, city financial data | (3) | skipped: whole-city totals only, no fire department line | 0 | - | - | - |
| `id_state` | Transparent Idaho, state transactions: Idaho Department of Lands fire program | 1 | **built** | 1 (state fire agency) | 47,000 payment lines | $329.4M net | state FY2021-FY2027 (FY2027 partial) |
| `id_lgr_compliance`, `id_contracts` | Registry compliance report; SCO open data portal (statewide contracts) | - | skipped (no fire agency spend); samples kept | 0 | - | - | - |

`data/states/id/agencies.json` coverage after this run: tier 1: 1, tier 2: 0, tier 3: 156, tier 4: 101 (258 agencies:
198 registry rows plus 60 fire districts added from the registry of local governments). No agency without vendor data
has a $0 row.

Checks: `python3 tests/multistate/check_id.py` and `python3 tests/multistate/check_federal.py ID` both pass.
`check_id.py` imports neither adapter: it re-reads the raw files, checks the `id_state` raw lines against the
control file's server-side line counts and dollars per account category, applies the owner's dedup rule on its own
(upload-error copies, identical lines, void-safe copies), and compares every kept payment line with
`transactions.csv.gz` (unique_id, fiscal year, date, amount, account, account title and payee as published, so a
published row can repeat only as a copy the rule keeps); it recomputes each district-year total
of `id_lgr`, checks the contract's column lists, the coverage tiers, the redaction patterns and the vendor map
coverage.

**Owner decisions of 2026-10-06 applied (review):** payee names are shown as published, private persons included
(`id_state` calls `common.withhold_person` directly; its local withholding rules were removed and 10,722 lines,
$14.7M, that they withheld now show the published name); ESDs that provide only EMS are excluded (Idaho's ambulance
districts are a separate registry type and are not linked, see `id_lgr`); state fire agencies stay in the main data
(IDL's fire program, see `id_state`). Decisions 2 (Texas DIR) and 5 (Ohio) do not apply to Idaho.

**Owner decisions of 2026-10-07 applied:** this is an internal tool, so the State Controller's terms of use are
accepted as is (see Access). Dedup rule ("drop identical lines, drop identical days"), as corrected the same day:
lines are identical when every column the source publishes is equal except the row id and load stamps
(`unique_id`, `date_of_load`, `zz_extract_date`); identical lines are kept once, except that a set of identical
payments keeps one copy more per reversal (void-safe). For `id_state` the first reading already compared every raw
column, and Idaho publishes no voucher, invoice or check number, so the corrected rule drops the same 709 lines and
the void rule keeps none: 47,000 payment lines, $329,402,882.55, unchanged (see `id_state`, Duplicates). `id_lgr`
holds one total per district and year and has no identical rows. The Ohio program-220 rule and the California double-counting decision do not apply to Idaho.

## Access to Transparent Idaho (applies to `id_lgr`, `id_cities`, `id_state`)

- **Who runs it:** Idaho State Controller's Office (SCO). `transparent.idaho.gov` is a React single-page app on
  CloudFront; its data come from a JSON REST API at `https://transparent.idaho.gov/api/` (the calls its pages make,
  for example `getCountyEntities`, `getCityFinancials`), a GraphQL endpoint for page text, embedded Power BI reports,
  and OpenGov Transparency Reporting at `https://idaho.opengov.com/` (state budget, transactions, vendors, payroll).
- **robots.txt:** `transparent.idaho.gov/robots.txt` is `User-agent: * / Disallow:` ("Allow crawling all pages").
  `idaho.opengov.com/robots.txt` disallows nothing. The SCO's CKAN portal `idahoprod.ogopendata.com` disallows
  `/api/` and `/datastore/` (only its dataset page and file download were used, after two exploratory API calls made
  before robots.txt was read; see `id_contracts`).
- **User agent:** CloudFront answers every request to `transparent.idaho.gov` whose User-Agent is an HTTP library
  (`curl/…`, `Python-urllib/…`) or the project's plain agent (`utah-fire-procurement/0.1 (…)`) with the app shell
  (HTML, status 200, `x-cache: Error from cloudfront`) instead of the file. The project's agent in the usual crawler
  form, `Mozilla/5.0 (compatible; utah-fire-procurement/0.1; +https://github.com/pasha594/utah-fire-procurement)`,
  is served. `id_lgr` and `id_feasibility` use that form (as `oh_feasibility.py` does for DataOhio); robots.txt
  invites crawlers, and the agent still names the project. `idaho.opengov.com` accepts the plain agent.
- **Terms of use:** Transparent Idaho links to the SCO site policies,
  <https://www.sco.idaho.gov/LivePages/site-policies.aspx>. They say nothing about automated access or crawling, but
  section 1 allows use of site content "solely for your non-commercial, personal purposes as an informational
  source" and says "you may not use, alter, copy, distribute, transmit, or derive another work from any Content …
  except as expressly permitted". The data are public records of the State (Idaho Code 74-102) published under
  Idaho Code 67-1076, and the SCO's own open data portal licenses its datasets under the Open Data Commons
  Attribution License, but the site terms as written restrict redistribution. **Owner decision of 2026-10-07:**
  this is an internal tool, so the terms are accepted as is (no request to the SCO). The adapters were built
  because the terms do not forbid automated access. Publishing Idaho data on a public site later would reopen the
  question (transparentidaho@sco.idaho.gov).
- **Throttle:** every request goes through `common.get` (1 request per second); the OpenGov query endpoint needs a
  POST, which `common.get` cannot send, so `id_state.post_json` does the same throttle and retries.

## Federal layer (`usfa`, `openfema`)

Built by `pipeline/sources/federal.py` before this run: 198 USFA registry departments in
`config/states/id/agencies.csv` (98 fire districts, 69 local fire departments, 22 volunteer fire departments, the
Idaho Department of Lands row as "State fire agency", and others); 424 OpenFEMA firefighter grant awards to Idaho recipients (FY2005-FY2025, $305.8M), of which 120 awards
($28.9M) to 54 recipients are matched strictly to a registry department (`grant_recipients.csv`); 113 recipients are
unmatched (`grant_recipients_unmatched.csv`). This run did not change it; `check_federal.py ID` passes.

## `id_lgr`: Local Government Registry, fire district totals (tier 3, built)

- **URL:** <https://transparent.idaho.gov/local-district> (per-county pages, for example
  <https://transparent.idaho.gov/county/Ada>); registry background:
  [Local Government Registry Support Session](https://transparencyresources.idaho.gov/transparentidaho/Documents/Local%20Government%20Registry%20Support%20Session.pdf),
  [FAQ](https://transparencyresources.idaho.gov/transparentidaho/Documents/Central%20Registry%20FAQ.pdf).
- **What it is:** every local government entity files an Annual Financial Transparency Report in the Local
  Government Registry (Idaho Code 67-1076; SCO since 2022, submitted through OpenGov since 2023) by December 1: the
  adopted budget for the new fiscal year and the prior year's actual revenues and expenditures, with the budget,
  audit (required above an expenditure threshold) or actuals document.
- **Access:** JSON API. `getCountyEntityTypeList` (36 entity types; type 6 = Fire District), `getCountyEntityList
  ?EntityTypeId=6` (163 fire districts with the counties they serve), `getCountyEntityTypes?CountyID=` (types present
  in a county), `getCountyEntities?EntityTypeID=6&CountyID=<id>&FiscalYear=<yyyy>` (one record per district: EntityID,
  EntityName, Actual_Expenditures, Actual_Revenue, Budgeted_Expenditures, Budgeted_Revenue, ReportDocs with links to
  the filed PDFs on `entity-documents.s3-us-gov-west-1.amazonaws.com`). The entity query answers HTTP 500 for a
  county without the type (Clark County has no fire district), so fetch reads each county's types first: 43 counties
  with fire districts, about 300 requests in all. No paging needed.
- **Fields used:** `Actual_Expenditures` (whole dollars, all funds) per district and fiscal year. Budgets stay in the
  raw files: a budget is a plan, not spending.
- **Years:** the API offers FY2021-FY2025. Actuals: FY2021 151 districts, FY2022 152, FY2023 144, FY2024 130;
  FY2025 has budgets only (its actuals are due December 1, 2026). Normalized: FY2021-FY2024.
- **Fiscal year:** `FiscalYear` is the district's own fiscal year, the year it ends in. Verified on Kuna Rural Fire
  District: its FY2024 actual ($4,407,885) equals total expenditures in its audit "for the year ended December 31,
  2024", and its FY2024 budget PDF is headed "FISCAL YEAR 2024". A fire protection district's fiscal year starts
  October 1 or January 1 as its board resolves (Idaho Code 31-1422); the registry does not say which, so
  `agency_sources.csv` leaves `fy_start` empty for these rows.
- **Update frequency:** annual filings (December 1 deadline); the compliance report is refreshed quarterly.
- **How fire agencies are identified:** registry entity type 6, "Fire District" (Idaho Code 31-14). Every other type
  was scanned for fire, rescue, EMS or emergency names: only three ambulance districts and one dispatch joint powers
  board, none a fire agency (`NOT_FIRE` in the adapter; normalize stops on any new one).
- **Linking (config/states/id/agency_sources.csv, hand-reviewed):** 163 districts: 72 linked by exact name to a USFA
  registry department; 31 linked by hand where the registry name differs only in the district suffix ("Bliss Rural
  Fire District" = "Bliss Fire District") or the registry's "<place> Fire Department" is in a place that is not an
  incorporated city (so the department is the district's own); 60 added to `config/states/id/agencies_added.csv`
  (`ID-S-<slug>`, kind "Fire district", one "Volunteer fire department"). A "<city> Rural Fire (Protection) District"
  is never linked to the city's "<city> Fire Department" (Nampa, Meridian, Caldwell, Twin Falls, Moscow, Ketchum and
  others): the district is a separate taxing body that usually contracts with the city department, so the city
  department stays at tier 4. Two added districts serve two counties; their `county` holds both, separated by "; ".
  Three exact-name links have a registry county that disagrees with the registry of local governments (Eagle FPD,
  Carey RFPD, Wendell RFD; the USFA county looks wrong); noted in `agency_sources.csv`.
- **Rows:** 577 district-years, $577.5M; 231 district-years without an actual (mostly FY2025) and one actual of $0
  give no row.
- **Duplicates and reversals:** a district serving several counties is listed under each county; normalize asserts
  the copies agree and keeps one per EntityID and year. No reversals (one figure per entity and year). Checked under
  the owner's dedup rule of 2026-10-07: no two rows are identical (one row per agency and fiscal year, asserted by
  normalize and `check_id.py`). 11 districts filed the same actual in two to four consecutive years (14 district-years,
  $521,929, for example $5,000 a year in FY2021-FY2024); the fiscal years differ, so the rows are not identical and are
  kept as published.
- **Data quality:** self-reported, unaudited for small districts. Outliers kept as published: Cambridge FPD FY2021
  $1,411,410 against $84K-$189K in other years (its FY2021 actual revenue, $1,508,334, is as high, so a one-time
  capital project is as likely as a filing error); Nampa Fire Protection District FY2021 $3.4M against about $20M in
  FY2022-FY2024. Two Valley County entities, Yellow Pine Fire Protection District (EntityID 288, est. 1990) and
  Yellow Pine Rural Fire District (289, est. 1995), both filed FY2021 actuals ($20,744 and $19,183) and are kept as
  two agencies; the compliance report lists only one "Yellow Pine Fire", so they may be one district registered
  twice (open question). 163 fire districts here against 161 in the compliance report. Three districts (Potlatch
  Rural, Troy Rural, Shoshone County Fire District No. 2) never filed an actual and one (Ketchum Fire District) filed
  $0: they have no rows and stay at tier 4.
- **Sample:** `raw/2026-10-06/id/id_lgr/sample.json.gz` (first 100 FY2024 records).
- **Decision:** built (`pipeline/sources/id_lgr.py`).

## `id_cities`: city financial data (skipped)

- **URL:** <https://transparent.idaho.gov/city>; news: [Spokane Public Radio, 2024-10-22](https://www.spokanepublicradio.org/regional-news/2024-10-22/financial-data-on-each-of-idahos-198-cities-now-available-on-transparent-idaho).
- **Format and access:** JSON from the site's API, `getCityFinancials?FiscalYear=<yyyy>` (all 198 cities in one
  answer), `getAllCities`, `getCityInfoById?EntityID=`; terms of use and robots.txt as in "Access to Transparent
  Idaho" above.
- **Years and update frequency:** FY2021-FY2025 (the API's fiscal years; the newest year has budgets only); annual
  filings due December 1.
- **Fields:** EntityID, EntityName, FiscalYear, RevenueBudget, ExpenseBudget, RevenueActual, ExpenseActual,
  ReportDocs (budget, audit or actuals PDFs). FY2024: 198 cities, 145 with an actual ($2.61B in all).
- **Transaction-level?** No. The API gives whole-city totals only; there is no department, function or vendor
  field. The department and fund views on the City pages are Power BI reports (embed token per report from
  `/api/embedtoken`), whose only download is the "export data" menu of each visual in a browser: not a bulk download
  or documented API. The filed PDFs are budgets and audits, one per city and year.
- **How fire would be identified:** it cannot be: a city total mixes every department.
- **Data quality, duplicates:** one self-reported record per city and year (no duplicates or reversals to remove);
  53 of 198 cities had not filed an FY2024 actual.
- **Sample:** `raw/2026-10-06/id/id_cities/city_financials_fy2024.json.gz` (198 records) and `sample.json.gz` (100).
- **Decision:** skipped. A city's own spending is never fire spend, and no fire department line is published.
  City fire departments (Boise, Meridian, Nampa, Idaho Falls, Pocatello, Coeur d'Alene, Twin Falls and the rest)
  stay at tier 4. A later phase could read fire lines from the filed budget PDFs, or ask cities for check registers.

## `id_state`: state transactions, Idaho Department of Lands fire program (tier 1, built)

- **URL:** Transparent Idaho, Vendor Payments, "Transaction" report on OpenGov:
  <https://idaho.opengov.com/transparency-reporting/idaho/2b17eed6-3282-4416-ab38-656795512745/9711ec09-4057-47c6-8ebc-1f27ee4261d3?savedViewId=79113c65-e697-4dd8-a78a-9e92aca0d6d8>
  (saved view "Expenditure Transactions").
- **What it is:** every state agency's accounting lines: 25.2 million expense lines, state FY2020 to FY2027, loaded
  almost daily (606 load dates; latest 2026-10-05). Lines before FY2024 come from the legacy STARS system (function
  titles end in "(historical)"), later ones from Luma.
- **Access:** the report page's own JSON API, no login. `GET /api/reporting_service/v2/reports/<id>` and
  `/reports/<id>/lenses` (column definitions), `GET /api/reporting_service/v2/reportConfigurations/<id>` (the saved
  view), `POST /api/reporting_service/v2/reports/<id>/queries/detailTable` with that configuration and a replaced
  filter (server-side SQL `where`), `…/queries/detailTableCount` for counts. At most 250 rows per request (larger
  pages fail with HTTP 500); paged with `paginationOffset`, sorted on `unique_id`. Listing endpoints and the SQL
  endpoint `/api/query/v1` need a login (401) and were not used.
- **Fields:** unique_id, fund (category, type, title, code), state goal and objective, agency (title, function, code,
  agency_code_function_code), account type, account category, summary account (title), account (code), vendor,
  fiscal year, effective date, load date, amount, extract date, account number string.
- **Selection (server-side):** `agency_code_function_code = '320-07H'`: agency 320 Department of Lands, function 07H
  Forest and Range Fire Protection, titled "FIRE MANAGEMENT (historical)" in FY2020-21, "FOREST AND RANGE
  PROTECTION (historical)" in FY2021-23, and "FOREST AND RANGE FIRE PROTECTN" plus "FOREST & RANGE FIRE
  PROTECTION-DEFICIENCY" (fire suppression paid from deficiency warrants) from FY2024; account type Expense; account
  category not Personnel; one fiscal year at a time from FY2021. 47,790 lines fetched, equal to the control counts.
  Personnel lines (wages and benefits, employees' names as vendor; $98.6M over FY2021-FY2027) are left out and only
  their totals kept in `control.json.gz`. Function 03H "FOREST AND FIRE (historical)" (FY2021-23, $23.8M: Good
  Neighbor Authority timber work, forest practices, federal forestry grants) is forestry, not clearly fire, and is
  left out.
- **Years:** state FY2021-FY2027, July to June, the year it ends in. FY2027 holds July 1 to late September 2026.
- **How fire is identified:** the agency function code (07H), which is IDL's fire program in every year.
- **Attribution:** the registry's "Idaho Department of Lands Fire Department" (`ID-X-IDAHO-DEPARTMENT-OF-LANDS-FIRE-
  DEPARTMENT-COEUR-D-ALENE`, no FDID). IDL is a state fire agency and stays in the main data (owner decision 4)
  with kind "State fire agency": `federal.py` sets that kind by name ("Department of Lands"), although the
  registry files the row under a local organization type.
- **Rows:** 47,000 payment lines, $329,402,882.55 net: FY2021 $24.9M, FY2022 $62.2M, FY2023 $34.5M, FY2024 $33.7M,
  FY2025 $70.3M, FY2026 $78.0M, FY2027 (partial) $25.8M. By function title: deficiency warrants $182.9M, Forest and
  Range Protection (historical) $97.4M, Forest and Range Fire Protection $24.9M, Fire Management (historical) $24.2M.
  7,749 distinct payee names. `description` is empty (the source has no line description); `category_published` is the
  summary account title; `account` joins fund, function, account category and account.
- **Duplicates and reversals:** owner rule of 2026-10-07 ("drop identical lines, drop identical days"), as corrected
  the same day to compare every column the source publishes, not only the contract columns. Applied to the raw lines
  before the payment-category filter, in this order (`id_state.dedup`):
  - *Identical, and the columns ignored:* two lines are identical when every raw column is equal except `unique_id`
    (the portal's row id), `date_of_load` and `zz_extract_date` (load and extract stamps). Compared are the other 27
    columns of the saved view: fund category, type, title and code; state goal, objective title and code; agency
    title, code and function, `agency_code_function_code`; account type, category, summary account and account;
    vendor; fiscal year; effective date; amount; the seven `zz_filler` columns (empty on every line); the account
    number string. Idaho publishes no voucher, invoice, check, PO or line number, so no document number keeps two
    lines apart. The report's lens also defines OpenGov's `__og_quasi_id` and `__og_upload_id` (row and upload ids,
    which the rule ignores anyway) and `__og_fiscal_year_fiscal_period` (a fiscal period OpenGov computes); the saved
    view leaves them out, the raw files lack them and nothing was refetched.
  - *Upload errors first (rule of 2026-10-06, kept):* (a) copies from a later load batch (load date, extract date)
    than the line's first copy, 567 lines, $4,880,745.10: the same line, same `unique_id`, loaded again by a later
    extract (108 lines, $4.61M, extracts of 2024-12-07 and 2025-11-15, for example a $3,451,591 payment to the US
    Department of Agriculture and a dozen fire district and protective association payments of 2025-10-31, each
    twice), and purchase-card lines loaded again under new `unique_id`s, mostly in the loads of 2024-08-21 and
    2024-08-22, which consist almost entirely of such copies; (b) blocks of purchase-card lines inserted twice inside
    one load batch (the extra copies of a batch that holds 4 or more), 116 lines, $75,206.33, in 8 batches from
    2024-08-19 to 2025-07-07; the copies' `unique_id`s run in a parallel series at a near-constant offset (all 26
    copies of the 2025-07-07 batch at +14,313 or +14,764) and include the same airline ticket numbers ("UNITED
    0162410148953") and marketplace order numbers twice. In all 683 lines, $4,955,951.43; every one is identical to
    the copy kept.
  - *Identical lines:* each remaining identical set keeps the copy of the earliest load batch with the lowest
    `unique_id`. 26 lines dropped, $138,820.11, in 25 sets, each set inside one load batch: 18 payment copies
    ($140,433.98, for example two $97,378.20 vehicles from Mountain Home Auto Ranch on 2026-03-03 and two $31,500
    payments to one contractor on 2024-09-06), 6 zero-dollar lines and 2 credits (-$1,613.87).
  - *Void-safe:* a set of n identical positive lines keeps min(n, reversals + 1) copies, where reversals counts the
    lines of the same fund, function, objective, account and vendor with the amount negated, in the same or the next
    fiscal year, lines identical among themselves counting once; identical negative lines are kept once. **The void
    rule keeps no line here:** none of the 18 payment sets has a reversal. Two upload-error copies do have a
    reversal of their amount and stay dropped, because the reversal belongs to another line: a $122.58 US Bank
    purchase-card line of 2024-09-01 loaded again on 2024-10-08, whose reversal of 2025-02-24 moves the one payment
    from account 698000 to 698100 (reversal and repost the same day), and a $116.77 Westlock Inn line in the doubled
    block of 2025-07-07, whose reversal pairs with a separate $116.77 line of 2025-06-25 loaded with it on
    2025-07-09. Kept, each would count its payment twice.
  - *Numbers:* raw 47,790 lines ($338,100,490.00), 47,709 in payment categories ($334,497,654.09). With the upload
    errors dropped (the rule before 2026-10-07): 47,026 payment lines, $329,541,702.66. With the owner's rule, first
    reading and corrected alike: 709 lines dropped ($5,094,771.54, all in payment categories), 47,000 payment lines,
    $329,402,882.55; `transactions.csv.gz` is byte-identical to the first reading's. The first reading's second pass
    over the published columns was removed (it dropped nothing here); normalize prints how many published rows
    repeat (0), and `check_id.py` no longer requires none.
  - *Where the rule changes a net:* the -$1,529.87 credit (no vendor, account 599400 Employee In State Travel Costs,
    2026-06-22, twice in the load of 2026-07-06) is reversed once by a +$1,529.87 line of 2026-07-22 (FY2027), after
    a $1,529.87 Enterprise Holdings payment of 2025-09-08 to the same account: as published the four lines net $0;
    with one credit kept, $1,529.87. The -$84 Super 8 credit (2025-01-28, twice) has no counterpart. Open question
    below.

  A `unique_id` can also be reused by a different line (a transfer and its reversal), so `source_record_id` is
  `unique_id`, or `unique_id-<n>` when the id repeats (32 lines, 26 of them payment lines). Reversals and credits are
  kept as negative lines (2,974 lines, -$14.6M) and are never identical to the payment they reverse, so amounts are
  net. Accounting entries that are not payments are dropped: encumbrances (14 lines, $3.34M), year-end accrual "GAAP
  Expenses" (36, $0.08M), loss on disposal (4, $0.14M), transfers (27, $0.04M).
- **Payees:** shown as published, private persons included (owner decision of 2026-10-06): `common.withhold_person`
  only cuts payee text matching `config/payee_name_redactions.csv`. Since main's Utah work was merged (2026-10-07)
  that file also holds patterns for a named officer, a sole member and an owner's name after "LLC"; one `id_state`
  payee matches the last and shows as "Payee name withheld" (19 lines, $3,211.04). Many payees are private persons:
  sole proprietors hired with their equipment on fires (the largest $2.0M), couples paid as landowners, and
  employees reimbursed for travel. "REDACTED" ($11.7M, 26 lines, account "Misc Payments As Agent") is the State's
  own mask and is kept as published; 1,871 lines have no vendor.
- **Data quality:** amounts are cash basis. Vendor names are free text with store numbers and card-processor
  prefixes ("PCARD - …", "SQ *…"), so one company appears under several names; the vendor map (`config/vendor_map.csv`) folds the
  large ones. Purchase-card payments to U.S. Bank ($3.5M) also appear as merchant lines, so they are tagged
  "finance".
- **Sample:** `raw/2026-10-06/id/id_state/sample.json.gz` (first 100 lines of the unfiltered saved view).
- **Decision:** built (`pipeline/sources/id_state.py`).

## Vendor categories (merged into `config/vendor_map.csv`)

Idaho's proposals (`config/states/id/vendor_map_additions.csv`, 488 rows) were folded, with the other states', into
the shared `config/vendor_map.csv` by `pipeline/sources/merge_vendor_maps.py` on 2026-10-07 and the file was
deleted; every decision is in `docs/multistate/vendor-merge.md`. For Idaho: the U.S. Department of Agriculture is
one name (the Forest Service proposal and California's USDA rows); helicopter operators shared with California
(Heli-1, HeliQwest International, Timberline Helicopters) take California's `apparatus` by spend, not `wildland`;
Expeditors by Lindale and Axcess Fire and Safety Supply are one name each across states; the Oregon Department of
Forestry is one name with California's spelling. Coverage after the merge, as `tests/multistate/check_id.py`
counts it (payees classified the way `pipeline/build.py` does, `config/vendor_map.csv` first and then the vendor
and keyword rules; every unmapped payee with net spend above zero counted as purchasing): a real category for
**91.3%** of $158,010,689 purchasing dollars (88.6% by map rows, 2.6% by rules), up from 88.7% before the merge,
when only the two files counted.

The proposals, for the record: 488 rows (61 high, 212 medium, 215 low confidence). With the 149 payee names `config/vendor_map.csv`
already maps (after the merge of main on 2026-10-07), they cover 90.7% of `id_state`'s purchasing dollars ($144.0M of
$158.8M, counting every unmapped payee with net spend above zero as purchasing, the rule the other states' checks use;
the additions alone 86.1%; 88.7% with a real category, not `unclassified`). After the dedup rule of 2026-10-07, spend
and agencies were recomputed, and the 6 rows whose keys `config/vendor_map.csv` now holds were removed (Bureau of Land
Management, H&E Equipment Services, Johnson Controls, Motion & Flow Control Products, Ricoh USA, Safety-Kleen
Systems); their payees take the shared file's name and category. No other row names a company that the shared file
spells differently. The
cross-state check of 2026-10-07 found that under that rule the file covered 89.97% (90.5% only when payees with net
refunds, such as a -$0.9M "Idaho Department of Lands" line, reduce the base), and added 30 rows for the largest
unmapped payees (logging, excavation, water tender and firefighting contractors `wildland`; fire districts,
cities and a school district `government`; rentals `general`; auto parts `fleet`; B&H Photo `it`), most with low
or medium confidence from the name and account. In review, after the owner decision to show names, the "Individual name
withheld" row was dropped, spend and agencies were recomputed, and 129 rows were added for the largest payees that
were withheld before (mostly sole proprietors paid from "Professional Services", given `wildland` with low
confidence from the account, like the builder's account-based rows). IDL's fire program buys mostly wildland
suppression services: aircraft, contract crews and engines, water tenders, heavy equipment hired from logging and
excavation firms, camp catering and sanitation, medics. The shared categories were written for structural
departments, so these rows use `wildland` for suppression resources (confidence low or medium), `general` for
catering and rentals, `facilities` for camp sanitation and `professional` for medical standby. Payments to other
governments and fire agencies (US Forest Service, BLM, cities, fire districts, timber protective associations, other
states) are `government`. **Open question:** add a "wildland suppression services and aviation" category before
merging. Low-confidence rows were inferred from the account the payment was coded to and need review.

## Other candidates

- **Registry compliance report** (`id_lgr_compliance`): <https://lgcr-compliance.sco.idaho.gov/>, a static page whose
  data file lists 1,316 registered entities with type, county and compliance status (1,034 compliant; 161 fire
  entities). No dollars. Used only as a cross-check. Sample: `raw/2026-10-06/id/id_lgr_compliance/`. Skipped.
- **SCO open data portal** (`id_contracts`): <https://idahoprod.ogopendata.com/> (CKAN, Open Data Commons
  Attribution License) holds two datasets: Statewide Agreements and Contracts (one Excel file, 15,743 rows: agency,
  title, type, dates, parties, monetary value) and Idaho Rebounds small business grants. Contract awards, not
  payments, and not tied to a fire agency. robots.txt disallows `/api/`; the file was read from its dataset page
  link (its presigned S3 redirect carries an explicit `:443` port that breaks the signature in urllib, handled as in
  `tx_houston.py`). Sample (without the contact name, e-mail and phone columns):
  `raw/2026-10-06/id/id_contracts/sample.csv.gz`. Full file (not kept): <https://idahoprod.ogopendata.com/dataset/4bef0e9f-4ff3-4c06-88ca-d8cb5ef6f370/resource/09267ead-bc1b-476d-831c-a627b750b148/download/statewide-agreements.xlsx>,
  1,740,081 bytes, 15,743 rows, SHA-256 `5cc678288b4677276b50e814497ef2cc5540e9d734acfc0eda64d0a460296de9` (read
  2026-10-06 in review). Skipped.
- **Filed budgets and audits** (`entity-documents.s3-us-gov-west-1.amazonaws.com`): the PDFs behind `id_lgr` and
  `id_cities`; many are scans (Eagle FPD's FY2024 audit and budget have no text layer). Expenditure by category would
  need PDF table extraction or OCR per entity. Skipped; a later phase could use them for category detail.
- **OpenGov "Top Vendors" reports:** aggregated per agency, vendor and year (about 800 rows a year), whole agencies,
  FY2020 on. Not fire-specific; the Transaction report has the same payments at line level. Skipped.
- **State Fire Marshal** (Department of Insurance, functions "STATE FIRE MARSHAL" and "DIVISION OF STATE FIRE
  MARSHAL (historical)" in the same transaction data, $8.4M since FY2020): inspections and training, not a fire department.
  Skipped; easy to add to `id_state` with a second function code if the owner wants it.
- **Idaho State Tax Commission** property tax budgets and levies by taxing district (fire districts included): revenue
  and levy, not spending. Not fetched.
- **State Fire Marshal fire department directory** (<https://doi.idaho.gov/state-fire-marshal/fire-department-directory/>):
  a list of departments, no spending. Could help find departments missing from the USFA registry. Not fetched.
- **Idaho Fire Chiefs Association, Idaho Association of Counties:** no published spending data for fire agencies was
  found (only the associations' own nonprofit filings). Not fetched.
- **City open data:** Boise's open data portal (ArcGIS Hub) has no expenditure or payment dataset (search for
  "expenditure" and "payments": 0 results). Other cities were not found to publish checkbooks. Third-party
  aggregators (OpenTheBooks) were not used.

## Open questions

- The crawler-form User-Agent for `transparent.idaho.gov` (its CloudFront serves the app shell to library agents
  although robots.txt allows all): acceptable, or should the project ask the SCO to allow its plain agent?
- Should `id_state` also carry the State Fire Marshal, or IDL's forestry function 03H?
- Fire district fiscal year start (October or January) is unknown per district; `fy_start` is empty.
- A wildland suppression services / aviation category (see Vendor categories): helicopter and air tanker services
  are `apparatus` in the shared map (California's choice, by spend) and contract crews and equipment `wildland`.
- Yellow Pine: one district registered twice in the Local Government Registry, or two? (see `id_lgr` data quality)
- Identical credits: the void rule protects identical payments only, so identical negative lines are kept once even
  when a later line reverses one of them. In `id_state` this raises one family's net from $0 to $1,529.87 (see
  `id_state`, Duplicates). Counting re-reversals for identical credits the same way (keep min(n, re-reversals + 1))
  would fix this family but break the owner's own Ohio example (Walnut Township (Fairfield): three identical payments
  and two identical voids, payment, void, payment, void, payment; the void rule keeps two payments, and two voids
  would net $0 instead of one payment). A remedy that keeps every such net and changes no positive line (review of
  2026-10-07): in a family that has payments, drop an identical negative copy only together with an identical
  positive copy of the family. Here it keeps the second -$1,529.87 credit (the family has the +$1,529.87 line and
  no payment copy is dropped), so the four lines net $0 as published. Ohio, California and Texas have the same case.
  Apply it in all four states?
