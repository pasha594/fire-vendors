# Fire Agency Vendor Finances (prototype)

Which vendors fire agencies pay, how many agencies use each, and how much they spend: fire districts and fire
departments in Utah, Ohio, California, Idaho and Texas, by category and fiscal year. Built from public data only:
state and city spending data (one source note per state in `docs/sources/<st>.md`), the
[USFA National Fire Department Registry](https://apps.usfa.fema.gov/registry/),
[OpenFEMA firefighter grants](https://www.fema.gov/openfema-data-page/non-disaster-assistance-firefighter-grants-v1)
and the [NERIS integration partner list](https://neris.fsri.org/integration-partners).

Page: https://pasha594.github.io/fire-vendors/ (repository `pasha594/fire-vendors`, named `utah-fire-procurement` until
2026-10-08; GitHub redirects the old repository URL, but not the old page URL).

The site has two pages:

- `index.html`, the vendor page: which vendors are most used in each category (ranked by how many agencies paid
  them), each vendor's agencies with what they bought and what they paid (yearly amounts, single payments, item
  lines with unit prices), and each agency's vendors by category (its stack). Scope by state and county. Fire and
  EMS categories come first, the rest (fleet, IT, utilities, general supplies...) under "Other spending"
  (`config/page_sections.csv`). Card issuers, banks and payments without a vendor name are not shown as vendors.
  Vendor logos come from `logos/` (`config/vendor_logos.csv`).
- `explore.html`, All data: the filterable, groupable table of every row (the site's `index.html` until the vendor
  page), with payee names as reported, FEMA grants, annual totals, CSV downloads and the About page. Links made
  for it before the vendor page (`#/?g=...`, `#/about`) open it from `index.html`.

## Coverage

Coverage is uneven: every agency in the registry is listed, but only some publish what they pay each vendor. Each
agency gets the best tier its sources support, and the page shows it wherever the agency appears:

| Tier | Label on the page | What it shows | Where it comes from |
| --- | --- | --- | --- |
| 1 | Payee lines | Vendor rows by agency and fiscal year, and single payments | Utah (all agencies); Ohio Checkbook local governments and Cincinnati; city checkbooks in California (San Francisco, Los Angeles, Corona, Moreno Valley, Riverside County) and Texas (Houston, Dallas, Austin); CAL FIRE (Open FI$Cal); the Idaho Department of Lands fire program |
| 2 | Item lines | Vendor rows plus brand, product type, quantity and unit price | Texas DIR cooperative contract sales (IT and telecom only); California SCPRS purchase orders of CAL FIRE (FY2013 to FY2015, shown apart) |
| 3 | Totals only | Published annual totals by category, no vendors | California State Controller reports (special districts, city fire functions); Idaho fire district totals; the Texas A&M Forest Service |
| 4 | Directory only | Staffing, stations and FEMA grants | Every other registry department |

Agencies at tiers 3 and 4 read "No vendor data", never $0, and are left out of vendor and agency counts. The About
page of the site has the counts per state and tier, each state's fiscal years and partial years
(`config/states.csv`), and every source with its link, years and raw files.

Utah: 185 agencies (`config/agencies.csv`, include=yes): fire districts, fire service areas and interlocal fire
agencies, and the fire spending of cities, towns and counties (lines coded fire: function 2009xx in the account
number, or "fire" in the department names). Cities, towns and counties that only pay another agency for fire service,
or have almost no fire lines, are listed with include=no and the reason. Fiscal years 2021 to 2026; FY2026 is partly
reported.

Other states: fiscal years 2021 to 2027 where published, the latest years partly reported. How each source was
chosen, fetched and checked is in `docs/sources/<st>.md`; the open questions and the checks of the last run are in
`docs/multistate/STATUS.md`.

## What the numbers are

Every line gets a category from the same rules in every state (see `pipeline/build.py`): the payee's vendor
(`config/vendor_map.csv`, shared by all states, then `config/vendor_rules.csv` and `config/keyword_rules.csv`), then
the account and description rules for broad payees. Each row is the net amount one agency paid one payee name in one
fiscal year in one category. Single payments are lines of $1,000 or more in purchasing categories, with date and
description.

Utah's source is every expense line the agencies reported to Transparent Utah (its BigQuery database,
`pipeline/sql/fire_transactions.sql`). The query leaves out payroll, benefit and refund accounts; payroll left under
other account names is categorized as payroll by `config/account_rules.csv`. Transactions an entity uploaded again
in a later batch are counted once, and police department lines of Lone Peak Public Safety District are left out. Fire
districts also have staff counts and pay from their compensation reports (employee names replaced by numbers),
revenue by account and total expenses; for cities, towns and counties the annual expenses are their fire-coded
expenses, including payroll (`pipeline/sql/fire_expenses_by_year.sql`). Utah payees that are private persons are
grouped as "Individuals (names withheld)", and descriptions that may name a person are not shown.

Other states' payee names and descriptions are shown as their sources publish them (only email addresses and bank
references are removed, `config/payee_name_redactions.csv`). Their lines are read from the normalized files of
`docs/multistate/data-contract.md` (`data/states/<st>/`), which the adapters in `pipeline/sources/` write.

## Files

| Path | What |
| --- | --- |
| `index.html` | The vendor page: plain JavaScript, no build step |
| `explore.html` | All data: the table page (plain JavaScript) |
| `data/stack.json` | The vendor page's first load with `data/index.json` (about 0.55 MB gzipped): vendors used by two agencies or more, their net amounts by agency, category and fiscal year, and sums for the rest (`pipeline/build_stack.py`) |
| `data/stack-tail.json` | Vendors used by one agency and their amounts, and each state file's vendor index map; loaded after the first view (agency pages need it) |
| `logos/` | Vendor logos (site icons), downloaded once by `pipeline/fetch_logos.py` |
| `data/index.json` | The first load (under 1 MB gzipped): meta per state and per source, categories, every agency of every state with its coverage tier, and the precomputed default table of each scope (all states, each state) |
| `data/<st>.json` | One state's vendors, payee names, rows, FEMA grants and published annual totals (`ut`, `oh`, `ca`, `id`, `tx`); loaded when a view needs the state |
| `data/<st>-payments.json` | One state's single payments; loaded when a view shows them (when the section is opened in an all-states view, or for a file over 1 MB gzipped: California) |
| `data/<st>-items.json` | Item lines (`tx`: DIR, `ca`: SCPRS); loaded for a vendor or an agency of that state |
| `data/states/<st>/` | The normalized files of each state (agencies, transactions, item lines, totals, grants) |
| `raw/<date>/` | Downloads, gzipped, never edited |

The output format is in `docs/multistate/data-contract.md`. Until the multi-state page, the page read
`data/data.json` and `data/payments.json` (Utah only); they were removed after the commit `de1e5cf`, which the tests
use to prove Utah reads as before.

## Run locally

```
python3 -m http.server 8000
```

Then open http://localhost:8000. Opening `index.html` straight from disk does not work because the page loads
`data/index.json` and the state files with requests.

## Refresh the data

```
python3 pipeline/fetch.py    # Utah: downloads into raw/<today>/ (about 2 minutes, throttled)
python3 pipeline/sources/federal.py fetch OH CA ID TX && python3 pipeline/sources/federal.py normalize OH CA ID TX
python3 pipeline/sources/<st>_<source>.py fetch      # each state adapter (see docs/multistate/STATUS.md)
python3 pipeline/sources/<st>_<source>.py normalize  # writes data/states/<st>/
python3 pipeline/build.py    # rebuilds data/index.json, the per-state files and data/stack*.json (about 3 minutes)
python3 pipeline/build_stack.py   # data/stack.json and data/stack-tail.json alone (after a config/vendor_logos.csv change)
python3 pipeline/fetch_logos.py   # downloads logos for config/vendor_logos.csv rows with a domain and no logo yet
python3 pipeline/build.py --worklist DIR   # also writes DIR/worklist_<st>.csv: payees that need a vendor_map row
```

The Utah BigQuery files are saved by hand: run `pipeline/sql/fire_transactions.sql` and
`pipeline/sql/fire_expenses_by_year.sql` in BigQuery and save the results, gzipped, in
`raw/<date>/transparent_utah_bigquery/`. The build uses the newest folder that has them.

All scripts use the Python standard library only. Raw files are kept as downloaded (gzipped) and never edited;
everything in `data/` is rebuilt from `raw/`, `data/states/` and `config/`, and two builds from the same inputs are
byte-identical. The build stops without writing when `data/index.json` would be 1,000,000 bytes gzipped or more, or a
file 50 MB or more. The raw files keep payee names exactly as published, including private persons.

## Tests

```
python3 tests/check_build.py                    # the build output (after python3 pipeline/build.py)
python3 tests/check_stack.py                    # data/stack*.json against the state files and the default tables
python3 tests/multistate/check_<st>.py          # each state's normalized files against its raw files; also check_federal.py
node tests/stack_test.js                        # the vendor page's VCore in Node
node tests/core_test.js                         # the table page's Core in Node
node tests/page/compare_utah.js                 # the page in Chromium (Playwright)
node tests/page/screens.js                      # views and screenshots, desktop and phone
```

- `tests/check_build.py`: Utah unchanged against `data/data.json` and `data/payments.json` at `--base REF` (default
  `de1e5cf`; `--base none` skips it after Utah's inputs change on purpose), Utah against its raw file, each other
  state against `data/states/<st>/`, coverage, file sizes, and the precomputed default tables recomputed.
- `tests/check_stack.py`: every amount of `data/stack*.json` against the state files to the cent, vendor flags and
  logos, the vendor index maps, and per scope and category the vendor and agency counts and amounts against the
  default tables of `data/index.json`.
- `tests/stack_test.js`: the vendor page shows the same numbers before and after `data/stack-tail.json` loads;
  categories against the default tables; vendor pages, agency stacks and the agencies list agree; payments and item
  lines map to vendors; search.
- `tests/core_test.js`: the old page's Core (at `--base`, default `de1e5cf`) on the old Utah files against the new
  Core in the Utah view for about 2,000 generated filter states; the precomputed tables against computed ones.
- `tests/page/compare_utah.js` and `tests/page/screens.js` test the table page (`explore.html`): they serve the working
  tree and the old page (at `--base`) on free ports, so nothing else needs to run. Both need Node and Playwright with Chromium; for a global install, set
  `NODE_PATH` to the global modules folder (`NODE_PATH=$(npm root -g)`) and `PLAYWRIGHT_BROWSERS_PATH` to the folder
  that holds Chromium, if it is not Playwright's default.
- The tests read the old files with `git` from `de1e5cf`, so they need a clone with history (not `--depth 1`).

## Config files

| File | What it controls |
| --- | --- |
| `config/states.csv` | States in page order, their names, fiscal years and partly reported years |
| `config/agencies.csv` | Which Transparent Utah entities are included, their kind, USFA registry id and county. `id` is the Transparent Utah entity id (`tu_id`; the site's id is `UT-<id>`); an entity without one would get a slug of its name |
| `config/states/<st>/` | Other states: agencies (registry and added), which source entity is which agency, sources with their coverage tier, FEMA grant recipients (`docs/multistate/data-contract.md`) |
| `config/categories.csv` | Category list, and which categories count as purchasing |
| `config/vendor_map.csv` | Payee name (normalized) to canonical vendor name and category, all states (`pipeline/sources/merge_vendor_maps.py` folds in a state's proposals) |
| `config/vendor_name_merges.csv` | Reviewed decisions on which spellings are one company |
| `config/vendor_rules.csv` | Regex rules that fold rare spellings into a vendor already in the vendor map |
| `config/keyword_rules.csv` | Fallback regex rules for payees not in the vendor map, first match wins |
| `config/account_rules.csv` | Account names ("cat1 \| cat2 \| cat3") to a category: `override` always applies, `refine` only to broad payees (except the vendor categories in `skip_vendor_category`); category `vendor` keeps the payee's category. Written for Utah's account names |
| `config/description_rules.csv` | Regex on the line description for broad payees, first match wins; `skip_vendor_category` names payee categories a rule does not apply to |
| `config/card_programs.csv` | Card issuers and payment services whose lines are categorized like broad payees |
| `config/description_privacy_patterns.csv` | Utah: descriptions that may identify a person and are not shown; `payee_names` says whether a pattern also withholds payee names that are not in the vendor map |
| `config/payee_name_redactions.csv` | Payee text that is not shown (email addresses, bank references) |
| `config/revenue_exclusions.csv` | Utah revenue accounts left out of revenue totals (borrowing, transfers, donated infrastructure) |
| `config/grant_recipients.csv` | Utah: FEMA grant recipient names matched to agencies (`agency_id`) |
| `config/neris_partners.csv` | NERIS integration partners, used to flag vendors |
| `config/page_sections.csv` | The vendor page: purchasing categories in page order, `fire` (Fire and EMS) or `other` (Other spending) |
| `config/vendor_logos.csv` | The vendor page: each vendor's website domain (researched by hand for the vendors most agencies use), its logo file in `logos/` and where it was downloaded from |

## Sources

Utah vendor payments come from the Transparent Utah BigQuery database (`ut-sao-transparency-prod.transaction`,
"Super User" access); the queries are in `pipeline/sql/`. District details, total expenses, revenue and
compensation come from the public query service the transparent.utah.gov site itself uses (`pipeline/fetch.py`
lists the exact calls). It is not a documented API and may change. The other states' sources, their terms and how
each is fetched are in `docs/sources/<st>.md`; the page's About section links every source.
