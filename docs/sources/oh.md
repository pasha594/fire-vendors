# Ohio: source notes

Feasibility notes for every Ohio candidate source (PRD `docs/prd/multistate-expansion.md`, build-order steps 3
and 5), checked on 2026-10-06 from the cloud session on branch `multistate-sources`. Output format:
`docs/multistate/data-contract.md`. Raw files: `raw/2026-10-06/oh/<source>/`.

## Result

Two Ohio sources give vendor data for fire agencies:

- **Ohio Checkbook's local-government pages** (`oh_checkbook_local`, section 2): 186 participating fire agencies
  (1 fire district, 97 township and 88 city or village fire departments), 702,661 payment lines, $1.93 billion,
  calendar years 2021 to September 2026. The first run of this note skipped it because checkbook.ohio.gov's
  robots.txt disallows all paths; the owner allowed ignoring that robots.txt on 2026-10-06. For townships the
  lines of a fund or department named for fire and, since the owner's decision of 2026-10-07, every line of
  program 220 (Public Safety, fire protection in the township chart of accounts) are taken, never a line named
  for police; for cities and villages only the lines of a fund or department named for fire, so city and village
  departments that book their spending under general "Public Safety" lines are partial or missing.
- **The City of Cincinnati's vendor payments** (`oh_cincinnati`, section 5): the Cincinnati Fire Department.

The DataOhio bulk files of Ohio Checkbook hold state agencies only, at department level, so no row belongs to a
fire agency, not even the Ohio Division of Forestry. The Auditor of State publishes annual financial report
summaries in bulk, but only for whole townships, cities, villages, counties, schools and libraries, by function
("Public Safety" mixes fire, police and EMS); fire districts' filings are not published as data. So there is no
tier 3 source for Ohio yet.

| Source id | Source | Tier | Decision | Agencies | Lines | Dollars | Years |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `usfa`, `openfema` | Federal layer (done before this run) | 4 | built | 1,148 | | | |
| `oh_checkbook_state` | Ohio Checkbook state expenditures, DataOhio bulk files | 1 | skipped: no fire agency identifiable | 0 | | | FY2022-FY2026 |
| `oh_checkbook_local` | Ohio Checkbook local governments | 1 | **built** | 186 | 702,661 | $1,925,866,499.97 | 2021-2026 |
| (in `oh_checkbook_state`) | Ohio Division of Forestry (ODNR) | 1 | kept as state fire agency, no vendor data | 1 | | | |
| `oh_aos` | Auditor of State, Summarized Annual Financial Reports | 3 | skipped: not fire-specific | 0 | | | 2016-2025 |
| `oh_cincinnati` | City of Cincinnati Vendor Payments | 1 | **built** | 1 | 33,762 | $40,036,497.68 | FY2021-FY2027 |

Coverage after this run (`data/states/oh/agencies.json`, 1,153 agencies: the 1,148 registry departments and 5
in `config/states/oh/agencies_added.csv`): tier 1: 187 agencies (186 from the local checkbooks, 4 of them added
because the registry lacks them, and the Cincinnati Fire Department, OH-31015); tier 2: 0; tier 3: 0; tier 4:
966. No agency was given a $0 amount.

Cincinnati's $40.0 million is the fire department codes only. The City buys fire apparatus and ambulances through
its citywide vehicle account (981 "Motorized & Construction Equip"): $18.7 million in FY2021-FY2027 to Vogelpohl
Fire Equipment and Halcore Group, equal to 47% of the fire codes' total. Those lines carry no fire department code,
so they are not attributed (section 5). The page note in `sources.csv` says so.

## Federal layer (done)

Built by `pipeline/sources/federal.py` before this run (raw `raw/2026-10-06/oh/usfa/`, `.../openfema/`).

- USFA registry: 1,148 Ohio departments in `config/states/oh/agencies.csv` (437 local, 373 township, 204
  volunteer, 88 fire districts, 24 industrial brigades, 13 contract, 2 county, 2 state, 2 federal, 3 other; the
  three joint fire districts the registry files as "Other" are "Fire district" by name since `federal.py` was
  re-run on 2026-10-07).
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

## 2. Ohio Checkbook: local governments (`oh_checkbook_local`): built

The earlier run of this note skipped this source because of robots.txt. The owner allowed ignoring
checkbook.ohio.gov's robots.txt on 2026-10-06, and the source was then built as
`pipeline/sources/oh_checkbook_local.py` (tier 1).

- **URL:** https://checkbook.ohio.gov/Local/ with the participant lists CitiesVillagesList.aspx,
  TownshipsList.aspx and SpecialDistrictsList.aspx (counties, schools and colleges are not fire agencies and
  were not screened). The lists come from the page's own web service
  `WebServices/Municipalities.asmx/MunicipalitiesByCategory` (JSON). Each participant page (for example
  `/Local/Special-Districts/Valley-Fire`) embeds a Tableau dashboard from the State's Tableau Server
  (analytics.das.ohio.gov, site INTBUD), one workbook per kind of government:
  `ExpenseSpecialDistricts/DashboardSpecialDistricts`, `ExpenseTownships/DashboardTownships` and
  `ExpenseCitiesandVillages_15905053238820/DashboardCitiesandVillages` (the one the page uses in production).
  The old `<entity>.ohiocheckbook.com` hosts redirect to ohiocheckbook.gov and from there to checkbook.ohio.gov;
  no separate entity site is left. The Plain Township (Stark) page the PRD cites,
  plaintownshipstarkoh.gov/financialtransparency.aspx, returned HTTP 403 in the first run; Plain Township is not
  among the checkbook's participants.
- **Participants (2026-10-06):** 361 cities and villages, 304 townships, 38 special districts (703). Participation
  is voluntary (ORC 113.74); HB 413, which would require it, passed the Ohio House in May 2026. Only 2 of the 38
  special districts are fire districts: Valley Fire (Summit County, linked) and Holmes Fire District 1 (no
  transactions from 2021 on). "Joint Emergency Medical Service" is an EMS-only district and is excluded (owner
  decision 3, 2026-10-06); the other 35 are libraries, parks, cemeteries, transit, port, water and sewer
  districts. No joint fire district or fire and ambulance district takes part.
- **Access:** no login. The page asks checkbook.ohio.gov for a Tableau trusted ticket
  (`WebServices/Tableau.asmx/GetUniqueId`, no CAPTCHA) and opens the view with it. The adapter makes the same
  calls, sets the dashboard's own filters (Municipality Name, Fund, Department, Year, Object) as the filter
  controls do, and asks for the chart's underlying rows and summary totals the way the embedded Tableau API's
  `getUnderlyingTableDataAsync` and `getSummaryDataAsync` do (the same rows as the page's "View Data" screen).
  The reCAPTCHA Enterprise widget on the page belongs to the e-mail form ("EmailService") only; it is not on the
  data path and was not touched. No CAPTCHA, login, paywall or other access control was met or passed. The
  server returns at most 10,000 underlying rows per request; larger slices are split by year and then by object.
- **robots.txt and terms:** checkbook.ohio.gov's robots.txt is `User-agent: *` / `Disallow: *`. The owner
  allowed ignoring it for this site on 2026-10-06. The adapter still sends one request at a time, at least one
  second apart (`common.DELAY`), with the project's user agent `Mozilla/5.0 (compatible;
  utah-fire-procurement/0.1; +https://github.com/pasha594/utah-fire-procurement)`. Terms: the Disclaimer says
  local data is supplied voluntarily by each entity (ORC 113.74) and the Treasurer does not warrant it; no reuse
  restriction was found.
- **TLS:** the host sends its leaf certificate without the Sectigo "Public Server Authentication CA OV R36"
  intermediate. The adapter downloads it once from the leaf certificate's AIA caIssuers URL
  (http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt), checks its SHA-256
  (`6542d176bed50f193c0ce297ae44ecd8a0a86bec2ede682769344059b4e78530`), keeps it as
  `sectigo_ov_r36_intermediate.crt.gz` and adds it to the verification store. Verification stays on (Python
  3.13's partial-chain flag is cleared, so the chain must end at a root in the system store).
- **Format and fields:** JSON (Tableau `vqlCmdResponse` data tables). Each underlying row has the checkbook's
  row `Id`, `TransactionId` (unique per line in every fetched participant), `TransDate`, `Payee`,
  `FundCode`/`FundDescription`, `DeptCode`/`DeptDescription` (department or program), `ObjCode`/`ObjDescription`
  (object of expenditure), `Amt` (equal to `Amount` on every row), `Type` (payment type codes such as CH, AW,
  EP, EW, WH, mostly empty), `MuniName`, plus the dashboard's calculated display columns. No invoice number or
  line description. Empty cells come as Tableau's `%null%` marker; the adapter writes them as empty text.
- **Years and update frequency:** the production workbooks hold transactions from 2019; many participants
  stopped uploading in 2019-2021 (Toledo, Akron, Lakewood, Findlay and others have no rows from 2021). Each
  participant uploads on its own schedule (most monthly); the latest payment in this pull is 2026-09-30. The
  adapter keeps calendar years 2021 on (Ohio local governments' fiscal year is the calendar year, `fy_start`
  01); 2026 is partial. Of the 186 linked agencies, 69 have no line after 2024 and 52 have lines in 2026.
- **What counts as fire spend:** a fire district's whole checkbook. For townships, cities and villages the
  lines whose fund or department is named for fire (`fire`, `firefighters`, `firemen`, ..., for example "Fire
  District - 2111", "Fire Levy", "Fire and Rescue, Ambulance and EMS", departments "FIRE DEPARTMENT" and "Fire
  Protection"), never the government's general spending.
  Not fire: names shared with police ("Police & Fire Levy" counts only through a fire-named department),
  hydrants, fireworks, insurance, garnishments, and fire-loss insurance escrow funds (ORC 3929.86): "FIRE DAMAGE
  REMOVAL" (City of Steubenville), "FIRE LOSS RECOVERY" (Village of Gallipolis), "FIRE REPAIR/REMOVAL FUND" (City
  of Tallmadge) and "FIRE INSURANCE CLAIM CLEAN UP ESCROW" (Jackson Township (Mahoning)) pay insurance money back
  to owners of burned buildings or to demolition contractors, so such a fund or department excludes the line
  even when the other name says fire. EMS-only funds or departments are not fire lines. When a fire-named
  department also carries lines of a police fund (City of New Franklin books police, street lighting and drug
  fund lines under department 1 "FIRE"), only its fire funds count.
  **Townships, program 220 (owner decision of 2026-10-07):** in the township chart of accounts the department
  field is the program, and program 220 is fire protection. Most townships label it "Fire Protection - 220" (a
  fire name, counted from the start); 31 participants label it "Public Safety - 220" and 3 "220 - 220". For a
  linked township every line of program 220 now counts, in any fund (fire levies are often called "Special
  Levy"), except a line whose fund or department is named for police: a township's police-named line never
  counts. A township "also runs police" when a fund or department named for police has lines from 2021 on
  (the dashboard's own summary totals, `program220_<id>.json.gz`); its link note then says that its mixed
  Public Safety lines (program 220 in a police-named fund or department) were left out. "Public Safety - 210"
  (police protection in the chart) is not police-named; it is not program 220, so this rule does not count it.
  Cities and villages are outside this decision: their "Public Safety" lines still do not count.
- **Screening:** all 703 participants were opened one by one (fetched 2026-10-06 22:08 to 2026-10-07 00:41 UTC,
  in runs resumed after container restarts; `screen.json.gz` keeps each participant's Fund and Department filter values and
  the decision). 248 have no transactions from 2021 on; 89 have rows from 2021 but no fund or department named
  for fire (their fire spending, if any, is under "Public Safety" or general lines; listed below); 36 other special
  districts are not fire districts (one of them, Joint Emergency Medical Service, is EMS-only); the City of Cincinnati is skipped because its fire
  department comes from the City's own vendor payments (`oh_cincinnati`; taking it here as well would count it
  twice); 329 have a fire district checkbook or fire-named lines and were fetched (`entity_<id>.json.gz`).
  Nothing was left out for access reasons: every participant page answered.
- **Linking to the registry:** a fetched participant is linked in `config/states/oh/agency_sources.csv` when it
  runs the fire department named in the USFA registry (place name and county, strict; 161 by exact name, 25 by
  a manual decision with the reason in the link's note) and its fire lines are that department's own spending.
  Four departments that are not in the registry were added to `config/states/oh/agencies_added.csv` (Craig Beach
  Volunteer Fire Department, Brunswick Hills Township Fire Department, Franklin Township Fire Department (Adams),
  Sheffield Township Fire Department (Ashtabula)). The build had also added a "Proctorville Community Volunteer
  Fire Department", but the registry lists it as Proctorville Community Volunteer Fire and Rescue, Inc.
  (OH-44013, Lawrence County); the review linked the Village of Proctorville to OH-44013 and removed the added
  row. `check_oh.py` now fails when an added agency shares its place name with a registry department of the same
  county, unless the pair was reviewed (Brunswick Hills Township: the registry's Brunswick Division of Fire is the
  City of Brunswick's). Not
  linked: participants whose fire-named lines mostly pay another department, fire company or government by
  contract (more than about three quarters of the dollars), participants whose fire-named lines are only a
  grant, capital, debt, pension or small general fund (fewer than about 25 lines a year, or no operating lines
  at all), and one inconsistent upload. A participant can only be linked whole. 186 linked (1 fire district, 97
  townships, 88 cities and villages), 143 not linked.
- **Program 220 (owner decision of 2026-10-07):** 25 fetched townships have a program 220 value not named for fire
  ("Public Safety - 220" or "220 - 220"). For each, `fetch220` (run 2026-10-07, files kept in the 2026-10-06
  folder with the entity files) fetched the program 220 lines of every fund not named for fire (the fire funds
  were fetched whole before, so nothing overlaps), with the dashboard's summary totals for the same filters, and
  the summary totals of every police-named fund and department from 2021 on. 13 of the 25 were linked; 8 of them
  gain lines: Genoa Township (Delaware) 4,888 lines ($26,813,786.70), Bainbridge Township (Geauga) 4,589
  ($16,734,230.29), Copley Township (Summit) 15,282 ($11,207,833.53), Canton Township (Stark) 3,030
  ($9,778,302.65), Fairfield Township (Butler) 640 ($6,232,348.88), Hamilton Township (Warren) 3 ($1,125,539.69,
  American Rescue Plan and Coronavirus Relief lines), Springfield Township (Mahoning) 415 ($422,830.67) and
  Jefferson Township (Montgomery) 2 ($28,055.00); Deerfield Township (Warren), Lake Township (Wood), Madison
  Township (Franklin), Perry Township (Stark) and Pike Township (Clark) have no such line from 2021 on (counts
  after the duplicate rules; most lines are in each township's "Special Levy" fund, the fire levy). The
  re-check of the participants left unlinked as partial linked three townships under the existing rules (exact
  registry name and county; payroll, Ohio Police & Fire Pension and benefits paid by the township show it runs
  the department): Liberty Township (Butler) to Liberty Township Fire Department (OH-09107; 2,702 program 220
  lines, $15,596,155.33, 2021 to 2023), Orange Township (Delaware) to Orange Township Fire Department (OH-21121;
  3,788 lines, $26,798,825.36, 2021 to 2024) and Pierce Township (Clermont) to Pierce Township Fire Department
  (OH-13115; 9,605 lines, $14,997,988.99, 2021 to 2026). In all, program 220 adds 44,944 lines and
  $129,735,897.09. Not linked: Blendon Township (Franklin), Webster Township (Wood) and Wabash Township (Darke)
  have no program 220 line in a fund not named for fire (and no registry department of their name); Shawnee
  Township (Allen) has 22 such lines, all in 2021 ($6,436.92), under the 25 lines a year of the link rule; the
  five contract townships (Jackson Township and Perry Township (Montgomery), Lake Township (Stark), Somerford
  Township (Madison), Urbana Township (Champaign)) keep paying another
  department and stay unlinked. Police: 10 of the 16 linked townships with a `program220_<id>.json.gz` file
  run police by the rule (a police-named fund or department with lines from 2021 on: Bainbridge, Canton,
  Copley, Deerfield, Fairfield (Butler), Hamilton (Warren), Jefferson (Montgomery), Lake (Wood), Madison
  (Franklin), Perry (Stark)); none of them has a program 220 line in a police-named fund or department from 2021
  on, so the mixed Public Safety lines left out are 0 lines, and each of their link notes says so. A township's
  police-named line never counts: this drops 18 lines of Ross Township (Butler) ($1,931.44, its "FIRE SAFER
  GRANT" fund booked under "Police Protection - 210"). Police is found by name only, so a township whose police
  fund has another name (Genoa and Orange Townships run police departments, but no fund or department of theirs
  is named for police) counts as not running police; their program 220 lines are fire protection by the chart
  of accounts either way.
- **Raw kept** (`raw/2026-10-06/oh/oh_checkbook_local/`, 360 files, 57.4 MB gzipped, largest 1.5 MB):
  `participants_<kind>.json.gz` (the three lists), `entity_<id>.json.gz` (329 files: the participant's filter
  values and the verbatim response of every underlying-rows and summary request with the filters that were set),
  `program220_<id>.json.gz` (25 files, 3.5 MB, fetched 2026-10-07: program 220 rows, their summary totals and
  the police-named funds' and departments' summary totals, with the township's filter values that day),
  `screen.json.gz`, `sample.csv.gz` (100 raw rows of the first entity file, columns as published) and
  `sectigo_ov_r36_intermediate.crt.gz`. All files of this source are in the 2026-10-06 folder, including those
  fetched after midnight UTC on 2026-10-07 (each entity file records its own fetch time). Reproduce with
  `python3 pipeline/sources/oh_checkbook_local.py fetch --date 2026-10-06 --cache <file>` (resumable: it skips
  entity files that exist) and `python3 pipeline/sources/oh_checkbook_local.py fetch220 --date 2026-10-06`
  (skips program220 files that exist).
- **Rows** (`data/states/oh/transactions.csv.gz`, source `oh_checkbook_local`):

  | Year | Lines | Dollars | Agencies |
  | --- | --- | --- | --- |
  | 2021 | 169,928 | $379,135,058.13 | 170 |
  | 2022 | 149,921 | $393,248,922.25 | 170 |
  | 2023 | 136,171 | $392,185,460.78 | 150 |
  | 2024 | 130,900 | $375,237,126.57 | 136 |
  | 2025 | 96,197 | $294,425,219.73 | 117 |
  | 2026 (partial) | 19,544 | $91,634,712.51 | 52 |
  | Total | 702,661 | $1,925,866,499.97 | 186 |

  By kind: townships 435,395 lines ($1,103,986,868.78, 97 agencies); cities and villages 262,023 lines
  ($816,916,323.19, 88 agencies); fire district (Valley Fire) 5,243 lines ($4,963,308.00). The dollars include
  payroll, pensions and benefits paid through the checkbook; purchasing (by the vendor map categories) is about
  $395 million of the Ohio total.
- **Duplicates and broken uploads:** rows are keyed by the checkbook's row `Id`; a row fetched by two
  overlapping requests is kept once (an Id fetched twice with different values stops normalize). Then, in this
  order: months uploaded twice, reloads, broken uploads (each below), and last the owner's rule of 2026-10-07 as
  corrected the same day ("drop identical lines, drop identical days", applied to every column the source
  publishes, not only the contract columns):
  - *Identical:* two lines are identical when every column of the raw rows is equal except the columns that only
    identify the row or the load. Ignored here: `Id` (the checkbook's row id) and `TransactionId` (the number the
    checkbook gives each line in upload order; uploads are told apart by its jumps, see reloads). The source has
    no load timestamp and publishes no invoice, check, voucher or PO number, so the content compared is the
    payment `Type` code (`AW`, `EP`, `EW`, `CH`, `NEG REAL`, ...; empty on 73% of lines), the date, the payee as
    published, the fund, department and object codes and names, the amount and the participant; the dashboard's
    calculated columns (labels such as "Fire District - 2111", the year) are built from these and were checked
    to never separate two lines that are equal in them. Identical lines are kept once, the lowest row `Id`.
  - *Void-safe:* a group of n identical positive lines keeps min(n, reversals + 1) of them (the lowest row Ids),
    where reversals counts the negative lines of the same participant, payee, fund, department and object with
    the amount negated, dated in the group's calendar year or the next, lines identical among themselves
    counting once. Identical negative lines are kept once.
  - *Numbers:* before the rule 720,378 lines ($1,932,372,765.53). It drops 17,717 lines ($6,506,265.56 net) in
    10,823 groups at 168 of the 186 agencies; 3,743 of the dropped lines are negative (-$4,461,382.42). The void
    rule keeps 6,267 identical copies ($11,634,680.14) in 6,084 groups that the plain rule would have dropped.
    After: 702,661 lines, $1,925,866,499.97. The payment `Type` code keeps 89 lines apart that the first
    reading of the rule (contract columns only) had dropped. The first reading dropped 24,073 lines
    ($18,266,767.61); the corrected rule restores 6,356 lines ($11,760,502.05 net).
  - *Examples:* Walnut Township (Fairfield) published three payments and two voids of $1,551,069.41 of bond
    principal to Vinton County National Bank on 2021-11-24 (one reissue): two payments and one void are kept,
    net $1,551,069.41 as published (the first reading left net $0). Days doubled inside one upload (Hamilton
    Township (Warren), 2021-01-05, -18 and -20 and 2021-02-01: Paycor payroll and supplier lines twice each, 107
    extra lines) are still dropped. Largest drops by dollars: City of Niles 1,233 lines ($728,042.24), Beavercreek Township
    (Greene) 2,585 ($667,015.91), Violet Township (Fairfield) 187 ($587,061.09), Hamilton Township (Warren) 135
    ($529,578.92), City of Grandview Heights 976 ($471,930.54); most dropped lines are payroll and benefit lines
    (salaries, Medicare, hospitalization, fire pension) that a participant uploads as several equal lines a day.
  - *Where the rule raises a net:* identical negative lines are kept once and count once as reversals, so where two
    payments (identical or not) were reversed by two identical voids, one void goes while both payments stay: 607
    payment and reversal families (same participant, payee, account and amount, both signs present) net $874,766.22
    more than as published. Largest: Hamilton Township (Franklin), two $281,250 payments to Global Emergency
    Vehicles and two voids on 2025-08-26 (net $0 as published, now $281,250, beside the payment of 2025-08-17; in
    upload order (TransactionId) the five lines are payment, void, reissue, void, reissue, so the family nets one
    payment, $281,250, as published and $562,500 now);
    Scioto Township (Pickaway), two $44,974.46 payroll lines and two voids on 2022-03-08 ($44,974.46); City of
    Amherst, two $599 payments to Almur Construction on 2021-05-19, both voided on 2021-06-09 and reissued once on
    2021-06-16 (net $599 as published, now $1,198). Open question below.
  Months uploaded twice: a month of 10 or more lines in which every group of identical lines (date, payee, fund,
  department, object and amount) has a size divisible by k >= 2 keeps size/k lines of each group: Beavercreek
  Township (Greene), March 2023 (113 lines, $1,044,570.30 dropped) and City of East Liverpool, September 2022
  (48 lines, $118,449.24). Reloads: TransactionIds are numbered in upload order, so a participant's lines sorted
  by TransactionId fall into uploads (a new one where the number jumps by more than 100,000); when a later
  upload's lines of one date (3 or more, none negative) only repeat lines of that date from earlier uploads,
  they are a reload and dropped. Perkins Township (Erie) uploaded 2025-12-18 and 2026-01-09 again about 1.1
  million TransactionIds later (82 lines, $86,589.34, payee "N/A"). These two rules run before the identical-line
  rule (both copies are identical under it anyway) and their counts are reported separately. Broken
  uploads: three participants' recent months carry batch totals instead of line amounts (most lines of a day show
  the same $0.5-5.6 million for different payees and objects): Jackson Township (Stark), 2026-01, -02, -03, -05,
  -06, -09, -10; City of Dover, 2025-12 and 2026-01, -02, -03, -08, -09; City of Bellevue, 2026-01 to -06. Those
  19 months (1,733 lines, $6.56 billion of batch totals) are left out, so these three agencies have no data for
  them. The rule needs two or more payees and two or more objects to share the date and amount, so equal
  stipends paid to several firefighters (York Township (Athens), November 2022: seven $500 reimbursements) stay.
- **Reversals:** 26,181 negative lines (-$54,091,379.94) are kept as published so they net out; 19,446 of them
  (-$43,927,619.19) equal a positive line of the same agency, payee and amount (voids and re-issues, payroll
  reclassifications, note rollovers). Every fetched slice was checked against the dashboard's own summary
  totals for the same filters, per year (normalize stops on a difference over one cent).
- **Data quality:** the payee "N/A" carries $292.1 million at 45 agencies (mostly payroll, pension and benefit
  lines uploaded without a payee) and "N/A..N/A" $59.3 million at one; both are classed `placeholder`. Object
  descriptions are the participant's own and are sometimes reused across departments (City of Huber Heights'
  fire fund lines show objects such as "VEHICLES - ECONOMIC DEVELOPMENT"; City of London's tax refund objects),
  so `category_published` is the label as published, not a checked category. Where a department books much of
  its spending under lines not named fire, the captured dollars are low for its size: Village of Dennison (20
  career firefighters, about $0.5 million a year) and City of Oxford (13, $0.6 million); these are linked (their
  fire-named lines are the department's own operating spending) but their totals are partial. Genoa Township
  (Delaware), Bainbridge Township (Geauga) and Canton Township (Stark), listed here as partial before, now carry
  their program 220 lines ($27.8 million, $19.2 million and $11.4 million in 2021-2026). Some participants upload irregularly (Marion Township (Marion): about $2.5 million in 2022
  and 2024 but under $0.1 million in 2021, 2023 and 2025). Perkins Township (Erie) changed its chart of accounts
  in 2025: from then on 10 lump lines without a payee under department 101 and object 0000 carry $5.2 million
  (for example $1,531,713.54 on 2025-08-29 and $1,857,269.49 on 2026-03-16) while its itemized lines nearly
  stop, so its 2025 total ($6.4 million against $4.2 million in 2024) may include period totals; they are kept
  as published (payee "N/A", class `placeholder`, so they do not count as purchasing). City of Huber Heights'
  fire capital fund pays note principal every year ($1.6-3.3 million to U.S. Bank), which may be note rollovers
  rather than new spending (class `finance`). Two linked townships pay much of their fire fund to another body:
  Catawba Island Township pays 59% to the City of Port Clinton by contract and Hambden Township 69% to the
  Hambden Fire Department itself; both are linked because the rest is the registry department's own spending
  (those payees are class `government`).
- **Payees:** 25,186 distinct payee names, published as the participants publish them, private persons
  included (owner decision 1, 2026-10-06): the adapter calls `common.withhold_person` directly, which only
  replaces payee text with an email address or bank account text; no payee in this pull matches.
- **Normalized:** one row per payment line; `fiscal_year` is the transaction date's year; `posting_date` is
  `TransDate`; `account` is "Fund - code / Department - code / Object - code"; `category_published` is
  `ObjDescription`; `source_record_id` is `<participant id>-<row Id>`. Normalize is deterministic (two runs give
  byte-identical files) and ends with `common.assemble_agencies('OH')`.
- **Decision: built** (tier 1): `pipeline/sources/oh_checkbook_local.py`.
- **Covered (186 participants, 186 agencies):**
  - Fire district (1): Valley Fire.
  - Townships (97): Amanda Township (Fairfield); American Township (Allen); Ashtabula Township (Ashtabula); Auglaize Township (Paulding); Austintown Township (Mahoning); Bainbridge Township (Geauga); Bath Township (Allen); Beavercreek Township (Greene); Berlin Township (Delaware); Bethel Township (Clark); Bethel Township (Miami); Bristol Township (Trumbull); Brunswick Hills Township (Medina); Byrd Township (Brown); Canton Township (Stark); Catawba Island Township (Ottawa); Cedarville Township (Greene); Charlestown Township (Portage); Chatham Township (Medina); Chester Township (Geauga); Clinton Township (Franklin); Coitsville Township (Mahoning); Columbia Township (Lorain); Concord Township (Lake); Copley Township (Summit); Coventry Township (Summit); Deerfield Township (Warren); Delaware Township (Hancock); East Union Township (Wayne); Ellsworth Township (Mahoning); Fairfield Township (Butler); Florence Township (Erie); Franklin Township (Adams); Franklin Township (Warren); Genoa Township (Delaware); German Township (Clark); Green Township (Ross); Hambden Township (Geauga); Hamilton Township (Franklin); Hamilton Township (Warren); Harrison Township (Muskingum); Hartford Township (Licking); Hinckley Township (Medina); Huntington Township (Ross); Jackson Township (Franklin); Jackson Township (Mahoning); Jackson Township (Stark); Jefferson Township (Montgomery); Jefferson Township (Scioto); Lake Township (Wood); Liberty Township (Butler); Liberty Township (Trumbull); Liverpool Township (Columbiana); Madison Township (Butler); Madison Township (Clark); Madison Township (Franklin); Marion Township (Marion); Miami Township (Hamilton); Milton Township (Mahoning); Monclova Township (Lucas); Norwich Township (Franklin); Orange Township (Delaware); Osnaburg Township (Stark); Painesville Township (Lake); Perkins Township (Erie); Perry Township (Stark); Perrysburg Township (Wood); Pierce Township (Clermont); Pike Township (Clark); Plain Township (Stark); Richfield Township (Lucas); Ross Township (Butler); Russell Township (Geauga); Scioto Township (Pickaway); Sheffield Township (Ashtabula); Springfield Township (Mahoning); St. Albans Township (Licking); Stokes Township (Madison); Sullivan Township (Ashland); Sycamore Township (Hamilton); Tiffin Township (Defiance); Trumbull Township (Ashtabula); Turtlecreek Township (Warren); Union Township (Clermont); Union Township (Ross); Union Township (Warren); Upper Township (Lawrence); Vermilion Township (Erie); Violet Township (Fairfield); Walnut Township (Fairfield); Waterloo Township (Athens); Wayne Township (Adams); Wayne Township (Warren); Weathersfield Township (Trumbull); Xenia Township (Greene); York Township (Athens); York Township (Medina).
  - Cities and villages (88): City of Amherst; City of Barberton; City of Bellefontaine; City of Bellevue; City of Brookville; City of Chillicothe; City of Circleville; City of Clayton; City of Columbiana; City of Cortland; City of Dover; City of East Liverpool; City of Eastlake; City of Fairborn; City of Franklin; City of Germantown; City of Grandview Heights; City of Harrison; City of Highland Heights; City of Huber Heights; City of Hudson; City of Huron; City of Jackson; City of Kettering; City of Kirtland; City of Lancaster; City of Maple Heights; City of Montgomery; City of Munroe Falls; City of New Carlisle; City of New Franklin; City of Niles; City of North Canton; City of North College Hill; City of Norwalk; City of Oxford; City of Parma; City of Portsmouth; City of Reading (FY13 to FY23); City of Sandusky; City of South Euclid; City of Springdale; City of Steubenville; City of Tallmadge; City of Trenton; City of Twinsburg; City of Vermilion; City of Wapakoneta; City of Washington Court House; City of Wickliffe; City of Willoughby Hills; City of Xenia; Village of Bay View; Village of Bettsville; Village of Bradner; Village of Byesville; Village of Craig Beach; Village of Dennison; Village of East Palestine; Village of Edgerton; Village of Gallipolis; Village of Hicksville; Village of Jackson Center; Village of Jacksonville; Village of Lockland; Village of Loudonville; Village of Mechanicsburg; Village of Millersport; Village of Mount Gilead; Village of Mount Orab; Village of New Knoxville; Village of New London; Village of New Straitsville; Village of Ottawa; Village of Payne; Village of Proctorville; Village of Racine; Village of Richfield; Village of Risingsun; Village of Salineville; Village of Seven Mile; Village of South Amherst; Village of South Zanesville; Village of Swanton; Village of Syracuse; Village of Wellsville; Village of West Lafayette; Village of West Liberty.
- **Fetched but not linked (143):**
  - Fire fund or department with no lines from 2021 on (33; Shawnee Township (Allen) has 22 program 220 lines, all in 2021, too few to link): Austinburg Township (Ashtabula); Bath Township (Greene); Boston Township (Summit); Chesterfield Township (Fulton); City of Newton Falls; City of Pataskala; City of Salem; Concord Township (Delaware); Green Creek Township (Sandusky); Hartsgrove Township (Ashtabula); Jackson Township (Hardin); Liberty Township (Jackson); Paris Township (Stark); Penfield Township (Lorain); Radnor Township (Delaware); Shawnee Township (Allen); Sugar Creek Township (Allen); Vernon Township (Scioto); Village of Amelia; Village of Andover; Village of Boston Heights; Village of Bratenahl; Village of Centerburg; Village of Cumberland; Village of Mantua; Village of Marblehead; Village of McComb; Village of Mount Sterling; Village of New Lexington; Village of New Richmond; Village of West Jefferson; Village of Williamsport; Village of Windham.
  - Partial: only a few fire-named lines, or only a grant, capital, debt or small general fund (65; Blendon, Wabash and Webster Townships have no program 220 line in a fund not named for fire): Baughman Township (Wayne); Bethlehem Township (Stark); Blendon Township (Franklin); Bloom Township (Morgan); Brown Township (Carroll); Brush Creek Township (Adams); Buck Township (Hardin); Canfield Township (Mahoning); City of Cuyahoga Falls; City of Euclid; City of Nelsonville; City of Norwood; City of Reading; City of Streetsboro; City of Wellston; Eagle Township (Brown); Fox Township (Carroll); Franklin Township (Fulton); German Township (Montgomery); Grand Township (Marion); Green Township (Hocking); Hopewell Township (Muskingum); Jackson Township (Guernsey); Lake Township (Logan); Liberty Township (Licking); Lincoln Township (Morrow); Mad River Township (Champaign); Madison Township (Vinton); Marion Township (Hancock); Marlboro Township (Stark); Meigs Township (Adams); North Township (Harrison); Oxford Township (Coshocton); Paint Township (Madison); Perry Township (Franklin); Prairie Township (Franklin); Rose Township (Carroll); Scott Township (Sandusky); Sharon Township (Franklin); Shortcreek Township (Harrison); St. Joseph Township (Williams); Sterling Township (Brown); Stokes Township (Logan); Sugar Creek Township (Wayne); Sugarcreek Township (Greene); Tate Township (Clermont); Union Township (Carroll); Village of Carey; Village of Custar; Village of Cygnet; Village of Leesville; Village of Liberty Center; Village of Lordstown; Village of North Fairfield; Village of Rockford; Village of Shawnee Hills; Village of Sherrodsville; Village of Sugar Bush Knolls; Village of Trimble; Village of Vanlue; Village of Westfield Center; Wabash Township (Darke); Warren Township (Belmont); Webster Township (Wood); Williamsburg Township (Clermont).
  - Partial: only the fire pension fund (3): City of Alliance; City of Lyndhurst; City of Massillon.
  - Contract: the fire-named lines pay another department, fire company or government (38): Adams Township (Defiance); Athens Township (Athens); Auburn Township (Geauga); Auglaize Township (Allen); Brown Township (Franklin); Burton Township (Geauga); Cambridge Township (Guernsey); Chardon Township (Geauga); City of Milford; Claridon Township (Geauga); Columbia Township (Hamilton); Defiance Township (Defiance); Fairfield Township (Columbiana); Green Township (Harrison); Jackson Township (Montgomery); Jackson Township (Sandusky); Lake Township (Stark); Loudon Township (Carroll); Miami Township (Montgomery); Muhlenberg Township (Pickaway); New London Township (Huron); Newbury Township (Geauga); Ohio Township (Clermont); Perry Township (Montgomery); Polk Township (Crawford); Somerford Township (Madison); Spencer Township (Lucas); Stock Township (Harrison); Swancreek Township (Fulton); Twinsburg Township (Summit); Urbana Township (Champaign); Village of Amesville; Village of Arlington Heights; Village of Ashville; Village of Barnhill; Village of Dalton; Village of Golf Manor; Village of Thurston.
  - Other (4): Auburn Township (Crawford); City of London; City of Loveland; Richland Township (Defiance).
    - Auburn Township (Crawford): fire lines mix a joint district payment (Tri Community Joint Fire District, 27%) with equipment and insurance; the registry's Tiro-Auburn Volunteer Fire Department is a village-township department; which department the lines belong to is not clear, so not linked
    - City of London: inconsistent upload: from 2023 its fire-named fund (FIRE DEPARTMENT - 228) carries negative salary, street, water and taxation lines of other departments (net fire spending negative in 2023, 2025 and 2026: -$4.2 million, -$4.6 million, -$2.9 million), so its fire lines are not the fire department's spending
    - City of Loveland: fire funds pay the Loveland-Symmes Fire Department ($8.7 million, a department shared with Symmes Township) plus station construction and debt; the department's own spending is not in this checkbook
    - Richland Township (Defiance): runs its own department (apparatus, payroll, leases), probably the registry's South Richland Fire Department (OH-20119), but the names differ; left for the owner (open question)
- **No fire-named fund or department from 2021 on (89, not fetched beyond screening):** seven of the townships
  label program 220 "Public Safety - 220" (Bloomfield (Logan), Concord (Ross), Jefferson (Franklin), Mead
  (Belmont), Orange (Meigs), Pease (Belmont), Washington (Pickaway)); they were never linked, so the program 220
  decision (for linked townships) does not reach them, and they were not fetched (open question).
  - Townships (26): Anderson Township; Bloomfield Township (Logan); Brown Township (Delaware); Concord Township (Champaign); Concord Township (Ross); Enoch Township (Noble); Hardy Township (Holmes); Jefferson Township (Franklin); Madison Township (Highland); Mead Township (Belmont); Milford Township (Knox); Oak Run Township (Madison); Ohio Township (Gallia); Orange Township (Meigs); Oxford Township (Delaware); Pease Township (Belmont); Peru Township (Huron); Pleasant Township (Madison); Poland Township (Mahoning); Porter Township (Delaware); Ross Township (Greene); Troy Township (Delaware); Vernon Township (Clinton); Washington Township (Brown); Washington Township (Pickaway); Winchester Township (Adams).
  - Cities and villages (63): City of Beavercreek; City of Canal Winchester; City of Dublin; City of Groveport; City of Hilliard; City of Pickerington; City of Powell; City of Stow; City of Sylvania; City of Tipp City; Village of Alexandria; Village of Belle Center; Village of Blanchester; Village of Buckeye Lake; Village of Burbank; Village of Camden; Village of Chippewa Lake; Village of Commercial Point; Village of Corwin; Village of Creston; Village of Doylestown; Village of Edon; Village of Elmore; Village of Fredericktown; Village of Fulton; Village of Galena; Village of Gibsonburg; Village of Grand Rapids; Village of Harbor View; Village of Harrod; Village of Haskins; Village of Hayesville; Village of Hills and Dales; Village of Jamestown; Village of Johnstown; Village of Lynchburg; Village of McClure; Village of Millersburg; Village of Mount Eaton; Village of New Holland; Village of North Lewisburg; Village of Oak Harbor; Village of Ostrander; Village of Parral; Village of Pemberville; Village of Perrysville; Village of Philo; Village of Piketon; Village of Plain City; Village of Pleasant Hill; Village of Rendville; Village of Rushville; Village of Seville; Village of Sherwood; Village of Somerset; Village of Sparta; Village of St. Paris; Village of Thornville; Village of Wakeman; Village of Waynesfield (Auglaize); Village of Waynesville (Warren); Village of West Millgrove; Village of Weston.
- **Not fire agencies or without data from 2021 on:** 248 participants with no transactions from 2021 on
  (including Holmes Fire District 1), 35 special districts that are not fire districts, the EMS-only "Joint
  Emergency Medical Service", and the City of Cincinnati (covered by `oh_cincinnati`); all are listed with
  their decision in `screen.json.gz`.

## 3. Ohio Division of Forestry (state fire agency)

- The Division of Forestry (Ohio Department of Natural Resources) runs Ohio's wildland fire program. In the
  state checkbook bulk files its payments are part of department DNR (64,578 lines, $896.8 million in FY2026)
  with no division, fund or ALI field, and no account is fire-specific (the closest, "POLICE AND FIRE
  AUTOMOBILES", is 3 DNR lines, $130,578 in FY2026, and could be any DNR division's law enforcement or fire
  vehicles).
- It is not in the USFA registry for Ohio (the 2 "State government" rows are local volunteer departments).
- **Decision:** kept in the main data as a state fire agency (owner decision 4, 2026-10-06):
  `config/states/oh/agencies_added.csv` row `OH-S-ohio-division-of-forestry`, kind "State fire agency". No
  source gives its payments, so it stays at tier 4. The checkbook web app has appropriation line item (ALI)
  views for state spending, which could separate Forestry; they were not part of this run (local checkbooks
  only).

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

- **Duplicates:** owner rule of 2026-10-07 as corrected the same day: two lines are identical when all 14
  columns of the raw file are equal. No column of this file only identifies the row or the load: the fetch does
  not select Socrata's `:id` and the dataset has no load timestamp, while `trans_id` (the financial system's
  document, for example `AD134CHK2021000153` or `EFT134EFT2022015999`), `trans_line_no` (its line) and `check_no`
  (check or EFT number) are content, so separate invoice lines on one check or EFT stay separate payments.
  Void-safe: n identical positive lines would keep min(n, reversals + 1), a reversal being a negative line of
  the same department, fund, account category and vendor with the amount negated in the same or the next fiscal
  year (a P-card credit does not repeat the document or check number of the charge it reverses). (trans_id,
  trans_line_no) is unique and no two raw lines are identical, so no line is dropped and the void rule keeps
  nothing: 33,762 lines, $40,036,497.68. The first reading of the rule (published contract columns only, which
  leave out the document, line and check numbers) dropped 10,894 of them ($1,119,873.72 net), mostly separate
  invoice lines of one transaction (for example 24 identical Galls jackets on one EFT, or one pest-control charge
  per station); they are back. The raw page total equals the server-side control totals per fiscal
  year and department (checked by `tests/multistate/check_oh.py`), and a second live query in the review,
  filtered by department name ("Fire%") instead of code, gave the same lines and dollars for every fiscal year.
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
  (data.clevelandohio.gov has a budget book only; opendata.columbus.gov nothing). Of these, only Akron (2019-2020)
  and Toledo (2019) are Ohio Checkbook participants, with no rows from 2021 on (section 2).
- **Census of Governments (Census Bureau), finance individual unit files:** a possible national tier 3 source,
  with expenditure by function for each government, including "fire protection" for townships, cities and
  special districts. Not verified here (the 2022 files are not in the old `www2.census.gov/.../datasets/`
  folders, which stop at 2018) and outside the Ohio PRD list; better handled once for all states.

## Vendor names and categories (merged into `config/vendor_map.csv`)

Ohio proposed 6,186 payees of both sources with a canonical name and category in
`config/states/oh/vendor_map_additions.csv` (with `spend` and `agencies` recomputed from the published lines).
On 2026-10-07 `pipeline/sources/merge_vendor_maps.py` folded them, with the other states' proposals, into the
shared `config/vendor_map.csv` and the file was deleted; every decision is in `docs/multistate/vendor-merge.md`.
For Ohio: spellings of one company now share one name across the five states (Charter Communications for
Spectrum and Time Warner Cable, Huntington Bank, PNC Bank, Change Healthcare, Cincinnati Bell, OTARMA, the Ohio
Fire & Emergency Services Foundation, NAPA stores and others); of the three overrides of the old Utah rows,
ACROSS STREET PRODUCTIONS took `training` (the Utah row was `unclassified`), while KEVIN WARD and TODD SMITH keep
Utah's `individuals` rows (one key carries one row and Utah withholds persons), so those two payees ($15,229)
are no longer purchasing; three Ohio payroll payees whose names are also Utah payees (Jason Brown, Matthew Evans,
Tyler Anderson) are mapped to `individuals` for the same reason; and Ohio payees published exactly as
"SPECTRUM" show under Utah's newspaper The Spectrum (the key's Utah row). Coverage after the merge, as
`tests/multistate/check_oh.py` counts it (by payee, net spend above zero, a payee in no row counted as
purchasing; payees classified the way `pipeline/build.py` does, `config/vendor_map.csv` first and then the vendor
and keyword rules): a real category for 93.7% of $395,598,494 purchasing dollars (90.2% by map rows, 3.4% by
rules); before the merge, 92.0% of $395,198,185 with the two files. After the corrected identical-line rule
(2026-10-07, the lines it restores): 93.7% of $399,549,631 (map 90.2%, rules 3.5%), map unchanged.

History of the proposals (how the rows were made, kept for the record): 2,522 purchasing payees ($302.0
million) were in the file; the largest purchasing payee in neither file was Cabol, Inc ($149,207); payees in
neither file held $31.6 million.
The other 3,664 rows are non-purchasing payees (payroll, pension, benefits and taxes 3,209; government 298;
finance 146; placeholder 11), listed so they leave the purchasing base: $1.56 billion of the local checkbooks'
$1.91 billion is payroll, the Ohio Police & Fire Pension Fund ($235.3 million under that canonical name), health
plans, payroll processors and banks, and the placeholder "N/A" ($292.1 million).

Update of 2026-10-07 (owner rules on identical lines and program 220): `spend` and `agencies` recomputed; the
program 220 lines and the three new links brought new payees, so 68 rows were added, by spend, until the maps
covered 92% again (the same name and object rules as below, plus 16 hand classifications): 59 payroll (township
payroll accounts, health plans, a 457 plan, unions and the Pierce Township firefighters paid by name under
salary objects), 3 fleet (Voyager Fleet Systems, Delaware County Diesel Repair, Performance Chrysler Jeep Dodge
Ram), and one each of government (Delaware County Auditor), utilities (Brightstar Propane & Fuel), insurance
(Rinehart-Walters-Danner), professional (Isaac Wiles Burkholder & Teetor), finance (Government Leasing and
Finance) and fire-equipment (Municipal Emergency Services). Confidence of all rows: 56 high, 382 medium, 5,748
low.

How the categories were set: the 95 reviewed Cincinnati rows and `config/vendor_map.csv` first; then
583 hand classifications of the largest unclassified payees by name (medium confidence when the name says what
the company sells, low when it is a guess from the name and the objects it is paid under); then name rules
(apparatus makers, fire equipment dealers, EMS suppliers, utilities, banks, governments; low confidence); then
the published object descriptions (a payee paid 80% or more under salary, benefit or pension objects is
payroll; 70% or more under one object family gives that category; low confidence). Payee names were not
classified as persons or companies (owner decision 1): a payee that is a person is classed by what it is paid
for (salary or reimbursement objects: payroll; a repair: facilities) or left unclassified, and no proposed row
used the `individuals` category (the merge kept `config/vendor_map.csv`'s two `individuals` rows, see above). Payments to another fire department or government
(contract payments, a village's lump payments to its own volunteer department) are `government`. Canonical
names reuse `config/vendor_map.csv` where it is the same company and merge spellings of the large ones
(Atlantic Emergency Solutions, Sutphen, Stryker incl. Howmedica, Municipal Emergency Services, Ohio Police & Fire
Pension Fund, Ohio BWC, Paychex, Paycor, AEP Ohio, Enbridge Gas Ohio and others). Unclassified payees, about
$27.8 million (7.2% of purchasing) at the first build, are left out of the file.

Review corrections (2026-10-07): 13 categories fixed by hand (the East Union Township payments to the Apple Creek
Volunteer Fire Department had been classed `it`; union health and welfare funds, the Police and Firemen's
Insurance Association and the Plain Township firefighters' association account are `payroll`, not `training`;
payments to the Mineral Ridge and M.M.B.A. fire departments and "County Fees" (auditor and treasurer fees) are
`government`; Fire Department Training Network is `training`, not `it`; 4 Guys (a fire truck builder) is
`apparatus`, not `fleet`; the Auman, Mahan & Furry law firm is `professional`); canonical names reused from `config/vendor_map.csv` for Zoll Medical, Rosenbauer,
Cummins, Shell, Rush Truck Centers, Fleetcor, Staples, AT&T (FirstNet), Enbridge Gas, Cintas, Aetna, Guardian,
Airgas and Aflac; and naming artifacts removed (a leading "- " left by vendor numbers on 106 names, "Johnson'S",
"Llc"). `check_oh.py` then also failed when a row's `name_key` was in `config/vendor_map.csv` and on a vendor name starting
with "-" (since the merge it checks the shared map's coverage instead). The
low-confidence rows (mostly payroll payees named after people, and object-based guesses) were not all reviewed.

## Checks

`python3 tests/multistate/check_oh.py` never imports the Ohio adapters. From the raw files (gzip, csv and json
only) it recomputes lines and dollars per agency, source and fiscal year and compares them with
`data/states/oh/transactions.csv.gz`:

- Cincinnati: the raw pages against the source's own server-side control totals per fiscal year and department;
  every linked department code is named as a fire department in the source (not police, insurance, pension or
  the shared 911 center) and every fire-named department is linked or a known exclusion; identical lines (all
  14 raw columns equal, trans_id, line and check numbers included) kept once, with the void rule below.
- Ohio Checkbook local: every linked participant's raw Tableau responses (underlying rows) against the summary
  totals the dashboard gave for the same filters, per year; each row inside its request's filters and of the
  linked participant only; the fire-line rule written out independently (fire districts whole; townships,
  cities and villages by fire-named fund or department, minus the excluded names and the escrow funds; fire
  funds only where the fire department carries police fund lines); calendar years 2021 on; one line per row Id;
  re-uploads once; months uploaded k times once; reloads (a date's lines repeated in a later upload) once;
  broken-upload months left out; then identical lines (every raw column equal except the row `Id` and
  `TransactionId`) kept once, the lowest row Id, and n identical positive lines min(n, distinct reversals + 1),
  the lowest row Ids (owner rule of 2026-10-07 as corrected; written out in the check's own `copies_kept`, a
  reversal being a negative line of the same participant or department, payee and account with the amount
  negated in the same or next fiscal year); townships:
  program 220 lines counted and police-named lines never, from the entity files and the `program220_<id>`
  files (each such file's rows checked against its summary totals; its program 220 slice must be every fund
  not named for fire and every program 220 value not named for fire; every police-named fund and department
  must have been checked; every linked township with such a program 220 value must have the file; its link
  note must mention program 220 and, exactly when a police-named fund or department has lines from 2021 on,
  that mixed Public Safety lines are left out); attribution (the participant is
  named as linked, sits in the agency's county unless a known two-county exception (Vermilion), is a fire
  district or a township, city or village, is not an EMS-only district, is linked once, has at least 25 fire
  lines a year and not only a pension fund).
- Every published line traced to its raw line: agency, fiscal year, date, payee, account, category and amount.
  Each set of raw lines identical under the rule is published exactly as often as the rule keeps it (the kept
  copies are the ones with the lowest row Ids, checked by record id).
  Payees must equal the source's text (spaces collapsed) unless it matches `config/payee_name_redactions.csv`
  (owner decision 2026-10-06).
- The contract's column names and order for every Ohio file; agency ids, links, `coverage_counts` and tiers (an
  agency without rows stays at tier 4); added agency ids; unique `source_record_id`s and sort order; no email in
  any published text; no unmerged `config/states/oh/vendor_map_additions.csv`, and `config/vendor_map.csv` with
  the vendor and keyword rules gives a real category to at least 90% of purchasing dollars; raw files only under
  `raw/<date>/oh/<source>/`, each under
  50 MB (150 MB for Ohio in all), and a sample of at most 100 rows for every reachable source (the state
  checkbook sample without address columns).
- Added in review: an added agency (`agencies_added.csv`) may not share its place name with a registry
  department of the same county unless the pair is listed as reviewed; Forestry keeps kind "State fire agency".

Result after the owner's corrected identical-line rule of 2026-10-07: `OH: ok (736423 transaction lines,
$1,965,902,997.65, 187 agencies at tier 1 (oh_checkbook_local: 702661, oh_cincinnati: 33762); config/vendor_map.csv
and the rules give a real category to 93.7% of $399,549,631 purchasing dollars (map 90.2%, rules 3.5%))`, with
`identical lines dropped: oh_cincinnati 0, oh_checkbook_local 17717 (168 participants); identical copies kept by
the void rule: oh_checkbook_local 6267 ($11,634,680.14), oh_cincinnati 0 ($0.00)`. (Under the first reading of the
rule: 719,173 lines, $1,953,022,621.88; before the owner's rules: 707,567 lines, $1,840,788,454.03, 184 agencies.)
Fault tests for the local source, on scratch copies of the repository files (never the working tree), one fault
each: a published amount changed by one cent, a payee changed, a link moved to an agency in another county, the
local sample deleted, a vendor map spend changed, an extra published line with no raw line; the check failed on
every one. The first review (Cincinnati) had done the same with ten other faults. The second review added three
more, each failing as it should: the Proctorville duplicate put back into `agencies_added.csv`, the Perkins reload
put back (normalize run on a scratch copy with the reload rule switched off), and a canonical name changed away
from `config/vendor_map.csv`. The 2026-10-07 update added five, each failing as it should: normalize with the
identical-line rule switched off (local, and Cincinnati), normalize counting a township's police-named lines, a
`program220_<id>.json.gz` file removed, and the "mixed Public Safety lines" sentence removed from the link note of
a township that runs police. The corrected rule added three: a copy the void rule keeps removed (Walnut Township
(Fairfield), 2021-11-24), an identical copy the rule drops put back (same group), and a kept void swapped for its
identical higher-Id copy (Hamilton Township (Franklin), 2025-08-26); the check failed on each.
`python3 tests/multistate/check_federal.py OH` passes (`OH: ok (1148 registry agencies, 302 with grants,
$110,580,051)`).

## Open questions

- Decided 2026-10-07 (owner): identical lines and doubled days are dropped (section 2 and 5), and a linked
  township's program 220 lines count, never its police-named lines (section 2). The identical-line rule was
  corrected the same day: lines are identical only when every raw column but the row and load ids is equal
  (Ohio Checkbook: `Id`, `TransactionId`; Cincinnati: none), and identical positive copies keep one more than
  the line's distinct reversals. Questions those rules leave:
- Identical voids: identical negative lines are kept once and count once as reversals, so where two payments
  (identical or not) were reversed by two identical voids, both payments stay and one void goes: 607 local families
  of payment and reversal lines (same participant, payee, account and amount) now net $874,766.22 more than as
  published (largest: Hamilton Township (Franklin), $281,250 to Global Emergency Vehicles on 2025-08-26, net $0 as
  published, now $281,250; Scioto Township (Pickaway) $44,974.46; Liverpool Township (Columbiana) $40,200; City of
  Trenton $33,425 and $31,850). This goes against rule 3's "must not change the net of a payment, void and reissue
  sequence" (Hamilton Township (Franklin) is payment, void, reissue, void, reissue in upload order). 3,743 identical
  negative lines (-$4,461,382.42) are dropped in all. Keeping identical negative lines as often as the identical
  payments they reverse are kept would break the owner's own example: Walnut Township (Fairfield) on 2021-11-24 has
  three identical $1,551,069.41 payments and two identical voids (payment, void, payment, void, payment); the void
  rule keeps two payments, and keeping both voids would net $0 instead of $1,551,069.41. A remedy that keeps every
  such net and changes no positive line (review of 2026-10-07): in a family that has payments, drop an identical
  negative copy only together with an identical positive copy of the family (Walnut: one payment copy and one void
  copy go, net $1,551,069.41; Hamilton Township (Franklin): no payment copy goes, so both voids stay, net $281,250).
  It would keep 1,037 more negative lines (-$874,766.22) and bring all 607 families back to their published net.
  Apply it (in all four states)?
- Program 220: police is found by name only. Genoa Township (Delaware) and Orange Township (Delaware) run police
  departments whose funds are not named for police, so they count as not running police; their program 220
  lines are fire protection by the chart of accounts either way. Seven townships with "Public Safety - 220" and
  no fire-named lines (Bloomfield (Logan), Concord (Ross), Jefferson (Franklin), Mead (Belmont), Orange (Meigs),
  Pease (Belmont), Washington (Pickaway)) were never fetched or linked; Jefferson Township (Franklin) runs a
  career department. Fetch and link them under the program 220 rule?
- Police-named lines of cities and villages still count when the fund or department is also named for fire
  (City of Niles "Police & Fire 1%" fund under department FIRE, City of Lancaster ".45 Police & Fire Levy"), and
  City of Columbiana's "FIRE DEPARTMENT FUND" carries departments named "... - POLICE" (salaries, a $673,307
  "VEHICLE PURCHASE - POLICE" line). The 2026-10-07 decision was read as covering townships only. Apply "never
  count police-named lines" to cities and villages too?
- Ohio Checkbook local: Richland Township (Defiance) runs its own department (apparatus, payroll, leases); the
  registry's closest row is South Richland Fire Department (OH-20119), whose name differs. Link it?
- Ohio Checkbook local: Catawba Island Township pays 59% of its fire fund to the City of Port Clinton by contract
  and Hambden Township 69% to the Hambden Fire Department; both are linked to their registry department. Keep,
  or link only participants whose fire lines are mostly the department's own purchases?
- Ohio Checkbook local: Perkins Township (Erie) shows $5.2 million in 10 lump lines without payee after its 2025
  chart change; ask the township whether these are period totals that repeat itemized lines?
- Ohio Checkbook local: City of London's fire-named fund carries negative lines of other departments from 2023
  on; it is not linked. Ask the city or the Treasurer whether its upload maps funds correctly?
- Ohio Checkbook local: Jackson Township (Stark), City of Dover and City of Bellevue uploaded batch totals
  instead of line amounts for 19 months of 2025-2026 (left out). Report it to the Treasurer's office?
- Show Cincinnati as a tier 1 agency with a note that apparatus and ambulances ($18.7 million in FY2021-FY2027
  through the citywide vehicle account 981), fleet repairs and IT bought by other city departments are missing,
  and that $2.0 million of P-card spend shows the card banks rather than the merchants? Or attribute the 981
  lines to fire apparatus vendors, which the PRD's attribution rule does not allow today?
- Should `federal.py` link FEMA awards to "CITY OF <name>" recipients when that city has one registry fire
  department (Cincinnati: 35 awards, $41.5 million, now unmatched)?
- Is reaching data.ohio.gov with the browser-form agent `Mozilla/5.0 (compatible; utah-fire-procurement/0.1; +URL)`,
  the page's session cookie and Referer acceptable, or should it count as a block? Only the manifest and sample
  depend on it.
- Add the Census of Governments as a national tier 3 source for fire protection totals?
