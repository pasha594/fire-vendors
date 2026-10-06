# PRD: Add Ohio, California, Idaho and Texas

Oct 6, 2026 · Pasha. Source of truth: the Claude Docs PRD "PRD: Add Ohio, California, Idaho and Texas"; this copy is for sessions working in the repository.

## Goal and current state

Extend the [Utah site](https://pasha594.github.io/utah-fire-procurement/) to Ohio, California, Idaho and Texas, so a fire agency in any of the five states can see which vendors peer agencies pay, how many use each, and how much they spend. None of the four new states publishes data as complete as Utah's, so the site must label each state's and each agency's coverage.

Current state ([repo](https://github.com/pasha594/utah-fire-procurement), commit 4a0a636):

- **Page:** one `index.html` (plain JavaScript) reads `data/data.json` (1.7 MB, 0.4 MB gzipped). One table with filters for category (multi-select), vendor, agency, county and annual expenses; group by category, vendor, agency or fiscal year.
- **Pipeline:** `pipeline/fetch.py` saves raw files to `raw/<date>/` (gzipped, never edited); `pipeline/build.py` rebuilds `data/data.json` from raw files plus `config/*.csv`. Python standard library only.
- **Coverage:** 38 Utah fire districts, service areas and interlocal agencies; FY2021 to FY2026; 4,742 vendors; 97% of purchasing spend classified.
- **Core unit:** the net amount one agency paid one payee name in one fiscal year. Categories come from `config/vendor_map.csv`, `vendor_rules.csv` and `keyword_rules.csv`.
- **Already national:** the USFA (U.S. Fire Administration) registry download takes a state code; OpenFEMA grants filter by `vendorState`; the NERIS partner list and FEMA equipment codes are state-neutral.
- **Utah-specific:** agency ids are Transparent Utah integer ids; links and page text name Transparent Utah; city and county fire transactions from Transparent Utah's BigQuery database (about 740,000 rows) are being brought in by a separate session (per-payment categories, payments with dates and descriptions) and are not yet used by `build.py`.

## Objectives and success metrics

The expansion succeeds when every fire agency in the five states is listed, vendor data is added wherever it exists, and no one mistakes missing data for zero spend.

| Objective | Metric | Target |
| --- | --- | --- |
| Keep Utah unchanged | Utah totals per agency, vendor and year after the refactor | Identical to today's build |
| Verify sources before building | One feasibility note per state: endpoint, fields, years, terms of use, sample pull | 4 notes, reviewed before any state build |
| List every fire agency | USFA registry agencies per state, with FEMA grants | All registry entries for Ohio, California, Idaho and Texas |
| Add vendor-level data where it exists | Agencies with payee-level or item-level rows, per state | Reported per state; no fixed target |
| Classify spend | Share of purchasing spend classified, per state | 90% or more where payee data exists (Utah: 97%) |
| Label coverage | Every agency and state shows its coverage level in the table and About page | 100% |
| Keep the page fast | First data load | Under 1 MB gzipped; per-state files loaded on demand |

## Data sources per state

Ohio and the large California and Texas cities offer Utah-style payee data; Texas adds item lines for IT; Idaho and most special districts offer annual totals only. Items marked "verify" must be confirmed in the feasibility notes before building.

| State | Source | What it gives | Coverage tier | Verify first |
| --- | --- | --- | --- | --- |
| All | USFA registry state CSV (endpoint already in `fetch.py`) | Every registered department: type, stations, firefighter counts | 4 Directory | None |
| All | OpenFEMA firefighter grants, filtered by `vendorState` (already in `fetch.py`) | Grant awards per recipient | 4 Directory | Recipient name matching per state |
| Ohio | [Ohio Checkbook](https://spend.ohio.gov) | Check-level payments for state agencies and participating local governments; monthly downloads on the DataOhio portal. Local checkbooks sit at `<entity>.OhioCheckbook.com` ([example](https://plaintownshipstarkoh.gov/financialtransparency.aspx)) | 1 Payee | Whether bulk downloads include local entities; fields; which townships and fire districts take part (participation is voluntary; [HB 413](https://ohiohouse.gov/news/republican/ohio-house-passes-reps-young-peterson-bill-to-expand-government-transparency-through-ohio-checkbook-144418) to require it passed the House in May 2026) |
| California | City checkbooks, starting with San Francisco [Vendor Payments (Vouchers)](https://data.sf.gov/d/n9pm-xkyq) (FY2007 on, weekly) | Payments by department and vendor | 1 Payee | Department field for the fire department; candidate cities beyond San Francisco (Los Angeles, San Diego, San Jose, Sacramento) |
| California | State Controller [Special Districts - Expenditures](https://catalog.data.gov/dataset/special-districts-expenditures-74f14) (2002-03 to 2023-24) | Annual expenditure totals by category for about 4,800 special districts, including fire protection districts | 3 Totals | How fire districts are flagged; category detail |
| California | SCPRS (State Contract and Procurement Registration System) [search](https://www.dgs.ca.gov/-/media/Divisions/PD/PTCS/eBISS/eProcurement/ADA-CaleProcureFISCalSCPRSSearch.docx) and [Purchase Order Data](https://catalog.data.gov/dataset/purchase-order-data) (FY2012 to FY2015) | State agency purchase orders with line items and UNSPSC (United Nations Standard Products and Services Code) codes, including CAL FIRE | 2 Item lines (state) | Bulk access to current data |
| Idaho | Transparent Idaho | State agency transactions (Idaho Department of Lands fire spend); [city financial data](https://www.spokanepublicradio.org/regional-news/2024-10-22/financial-data-on-each-of-idahos-198-cities-now-available-on-transparent-idaho); fire districts file annual totals through the [Local Government Registry](https://transparencyresources.idaho.gov/transparentidaho/Documents/Local%20Government%20Registry%20Support%20Session.pdf) | 1 Payee (state), 3 Totals (districts) | Whether city data is transaction-level; bulk access |
| Texas | DIR (Department of Information Resources) cooperative contract sales: [FY2026 on](https://data.texas.gov/d/a743-wj72), [FY2010 to FY2025](https://data.texas.gov/d/w64c-ndf7) | Line items: customer name and type, vendor, brand, quantity, unit price, product type, PO number. IT and telecom only | 2 Item lines | How fire departments and ESDs (emergency services districts) appear as customers |
| Texas | Comptroller [Special Purpose District Public Information Database](https://comptroller.texas.gov/transparency/local/sb625/lookup.php) (downloadable from data.texas.gov) | Self-reported financial information for special purpose districts | 3 Totals | Whether ESDs are included; fields |
| Texas | Large-city open data (Houston, Dallas, Austin, San Antonio, Fort Worth) | Payments by department and vendor, where published | 1 Payee | Which cities publish vendor payments with a fire department field |

## Coverage tiers

Every agency gets the best tier its sources support, and the page shows that tier wherever the agency appears.

| Tier | What the user sees | Fit with today's data model | Where it comes from |
| --- | --- | --- | --- |
| 1 Payee | Vendor rows by agency and year, as in Utah | Fits: roll transactions up to agency, payee and year | Utah; Ohio participating locals; California and Texas city checkbooks; state agencies in all four states |
| 2 Item lines | Vendor rows plus brand, quantity and unit price | New `line_items` table; also rolled up into tier 1 rows | Texas DIR (IT and telecom); California SCPRS (state agencies) |
| 3 Totals | Agency listed with annual spend by category, no vendors | Agency budget fields only | California special districts; Idaho fire districts; Texas special purpose districts |
| 4 Directory | Agency, staffing, stations and FEMA grants | Agency and grant records only | Every USFA registry agency not covered above |

Two rules keep the numbers honest:

- An agency without vendor data is never counted as spending $0. It is left out of vendor counts and peer comparisons and labeled "No vendor data".
- Spend is attributed to a fire agency only when the record clearly belongs to one: a fire district or ESD, a fire department code, or a fire department name. A city's own IT purchase in the Texas DIR data is not fire spend unless the customer is the fire department.

## Required app changes

The pipeline becomes one adapter per source feeding a shared build; the page gains a state filter and coverage labels.

**Data model**

- Agencies get `state`, `coverage` (tier 1 to 4) and `sources`. Ids become strings such as `UT-1363`; old numeric Utah ids in URLs still resolve.
- New optional `line_items` array: agency, vendor, date or fiscal year, brand, product type, quantity, unit price, amount, source.
- `meta` holds years, partial years, fetch date and source links per state. Each agency keeps its own fiscal-year start.
- Split output when the first load would exceed 1 MB gzipped: `data/index.json` (agencies, categories, vendors) plus `data/<state>.json` rows loaded on demand.

**Pipeline**

- One adapter per source in `pipeline/sources/<state>_<source>.py`, each with a fetch step (raw files) and a normalize step (common agencies, payments, line items and totals). `build.py` merges them.
- Keep today's rules: standard library only, immutable dated raw folders, 1-second throttle, rebuild everything in `data/` from `raw/` and `config/`.

**Config**

- `config/<state>/agencies.csv` and `grant_recipients.csv` per state.
- Shared `categories.csv`, `vendor_map.csv`, `vendor_rules.csv` and `keyword_rules.csv`, since national distributors recur across states; state overrides allowed.
- `build.py --worklist` per state to review unmapped payees with high spend.

**Page**

- State filter (all states by default); the county filter follows the chosen state.
- Coverage badge per agency and a per-state coverage summary on the home view and About page.
- Per-source links from `meta` instead of the hard-coded Transparent Utah links and text.
- Item-line view (brand, quantity, unit price) on vendor and agency views for tier 2 data.
- Rename the site to "Fire Agency Vendor Finances" (title, description, header).
- Withhold private persons' names in every state, as `build.py` does today.

## Risks and open questions

The main risk is uneven coverage that reads as a market picture; tier labels and per-state counts are the mitigation.

| Risk | Mitigation |
| --- | --- |
| Ohio local participation is voluntary, so coverage leans toward participating entities | Show participating share; revisit if HB 413 becomes law |
| California and Texas city data favors large cities | Label tiers; choose cities by fire department size |
| Idaho and many California and Texas districts have totals only | Tier 3 labels; public records requests in a later phase |
| Texas DIR customers are often cities, not fire departments; IT and telecom only | Attribute only fire-named customers; state the category scope on the page |
| Fiscal years differ by state and entity (calendar, July to June, October to September) | Keep each agency's fiscal-year start; note it when comparing across states |
| Undocumented endpoints change (Utah's query service already is one) | Dated raw snapshots; builds fail loudly on schema changes |
| Terms of use or blocked access | Record terms in feasibility notes; skip sources that forbid automated access |
| Payload growth | Per-state data files loaded on demand |

Open questions:

- [ ] Which California and Texas cities first? (Proposed: San Francisco, Los Angeles, Houston, Dallas, Austin, San Antonio, pending verification)
- [ ] Same year range as Utah (FY2021 on)?
- [ ] State fire agencies (CAL FIRE, Texas A&M Forest Service, Idaho Department of Lands, Ohio Division of Forestry) in the main table or a separate view?
- [ ] Rename the repository as well as the site?

## Build order

Refactor first, list every agency second, verify sources third; only then add state data.

1. Refactor for multiple states with Utah as the only state; prove Utah output is unchanged.
2. Federal layer for Ohio, California, Idaho and Texas: USFA registry and OpenFEMA grants. Every agency appears at tier 4.
3. Feasibility notes for every candidate source in `docs/sources/<state>.md`. Stop for review.
4. Texas DIR item lines.
5. Ohio Checkbook.
6. California: special district totals, then city checkbooks, then SCPRS.
7. Idaho: Transparent Idaho.
8. Page: state filter, coverage labels, item-line view, new name and per-source links.
9. Per-state metrics on the About page and in the README.

## Scope of the cloud session launched Oct 6, 2026

The cloud session adds only new files on its own branch (`multistate-sources`), because a separate session is changing the Utah pipeline and page on `main` at the same time. It does build-order steps 2 to 7 as source adapters writing normalized per-state files, builds adapters without waiting for review only where a source's terms allow automated bulk or API access, and leaves step 1 (the refactor) and steps 8 and 9 (page) until the Utah work merges. Its full instructions are in the Claude Docs PRD under "Prompt for Claude Code".

## Sources

- [Current site](https://pasha594.github.io/utah-fire-procurement/) and [repository](https://github.com/pasha594/utah-fire-procurement)
- [Ohio Checkbook](https://spend.ohio.gov)
- [Ohio House: HB 413](https://ohiohouse.gov/news/republican/ohio-house-passes-reps-young-peterson-bill-to-expand-government-transparency-through-ohio-checkbook-144418)
- [San Francisco Vendor Payments (Vouchers)](https://data.sf.gov/d/n9pm-xkyq)
- [California Special Districts - Expenditures](https://catalog.data.gov/dataset/special-districts-expenditures-74f14)
- [California Purchase Order Data](https://catalog.data.gov/dataset/purchase-order-data)
- [Transparent Idaho city data (Spokane Public Radio)](https://www.spokanepublicradio.org/regional-news/2024-10-22/financial-data-on-each-of-idahos-198-cities-now-available-on-transparent-idaho)
- [Idaho Local Government Registry](https://transparencyresources.idaho.gov/transparentidaho/Documents/Local%20Government%20Registry%20Support%20Session.pdf)
- [Texas DIR sales, FY2026 on](https://data.texas.gov/d/a743-wj72)
- [Texas Special Purpose District Public Information Database](https://comptroller.texas.gov/transparency/local/sb625/lookup.php)
