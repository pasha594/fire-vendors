# Multi-state data contract

Format of the files the multi-state adapters write, which `pipeline/build.py` merges with Utah, and of the site
files the build writes from them (PRD build-order steps 1 and 8, done; section "Site files" below). PRD:
`docs/prd/multistate-expansion.md`.

All files are UTF-8. CSV files have a header row, comma separator, `\n` line ends and are sorted, so a rebuild
from the same raw files is byte-identical. `<st>` is the lower-case state code (`oh`, `ca`, `id`, `tx`).

## Layout

| Path | Written by | What |
| --- | --- | --- |
| `raw/<date>/<st>/<source>/` | adapter `fetch` | Downloads, gzipped, written once and never edited |
| `config/states/<st>/agencies.csv` | `federal.py normalize` | Every USFA registry department (generated; do not hand-edit) |
| `config/states/<st>/agencies_added.csv` | adapter (hand-reviewed) | Fire agencies a source names that the registry lacks; same columns as `agencies.csv`, id `<ST>-S-<slug>` |
| `config/states/<st>/agency_sources.csv` | adapter (hand-reviewed) | Which source entity is which agency |
| `config/states/<st>/sources.csv` | adapter | One row per vendor-data source and its coverage tier |
| `config/states/<st>/grant_recipients.csv` | `federal.py normalize` | FEMA recipient name to agency id, strict matches |
| `config/states/<st>/grant_recipients_unmatched.csv` | `federal.py normalize` | Recipients not matched, with award counts and dollars |
| `config/states/<st>/vendor_map_additions.csv` | adapter (hand-reviewed), transient | A state's proposed canonical names and categories for payees, until `merge_vendor_maps.py` folds them into `config/vendor_map.csv` (then deleted) |
| `config/vendor_map.csv` | hand-reviewed; `merge_vendor_maps.py` | Shared map, all states: payee key to canonical vendor name and category |
| `config/vendor_name_merges.csv` | hand-reviewed | Reviewed name decisions the merge applies (which spellings are one company) |
| `data/states/<st>/agencies.json` | `common.assemble_agencies` | Agencies with coverage tier and sources |
| `data/states/<st>/grants.csv` | `federal.py normalize` | Matched FEMA firefighter grant awards |
| `data/states/<st>/transactions.csv.gz` | adapters, tiers 1 and 2 | Payment lines |
| `data/states/<st>/line_items.csv.gz` | adapters, tier 2 | Item lines with brand, quantity, unit price |
| `data/states/<st>/totals.csv` | adapters, tier 3 | Published annual totals by category |

Several adapters share one state's table files. Each adapter writes through `common.upsert_rows`, which
replaces only the rows whose `source` is that adapter's, so adapters can run in any order.

## Agency ids

- `<ST>-<FDID>` for registry departments, for example `OH-18027` (Cleveland Division of Fire). FDIDs are the
  registry's own ids and can contain letters (Texas: `TX-KA357`).
- `<ST>-X-<name>-<city>` for registry rows without an FDID.
- `<ST>-S-<slug>` for agencies added from a source (`agencies_added.csv`), for example a fire protection
  district the registry does not list.
- Utah: `UT-<Transparent Utah id>`, for example `UT-359` (`tu_id` 359). Older page links with a number
  (`agency=359`) still resolve to the Utah agency.

## `config/states/<st>/sources.csv`

| Column | Meaning |
| --- | --- |
| `source` | Source id, the same string as the adapter's `source` column, for example `tx_dir` |
| `name` | Name shown on the page, for example "Texas DIR cooperative contract sales" |
| `tier` | Coverage tier its rows give an agency: 1 payee, 2 item lines, 3 totals |
| `url` | Public page for the source (shown on the page instead of the Transparent Utah link) |
| `years` | Fiscal years covered, for example `2021-2026` |
| `fiscal_year` | How the source defines fiscal year, for example `Texas state FY, Sep-Aug` |
| `fetched` | Date of the raw folder used |
| `note` | Scope limits a reader must know, for example "IT and telecom only" |

## `config/states/<st>/agency_sources.csv`

| Column | Meaning |
| --- | --- |
| `agency_id` | Id in `agencies.csv` or `agencies_added.csv` |
| `source` | Source id |
| `source_entity_id` | The source's own id for the entity (customer number, department code), if any |
| `source_entity_name` | The entity name exactly as the source publishes it |
| `fy_start` | First month of the agency's fiscal year in that source, `01` to `12` |
| `match_method` | How the link was made: `exact name`, `department code`, `manual` |
| `note` | Why, when not obvious |

A source entity is linked only when it clearly is a fire agency: a fire district or ESD (emergency services
district), a fire department code, or a fire department name. A city's general purchases are never linked.

## `data/states/<st>/agencies.json`

```json
{
  "state": "TX",
  "sources": [ {"source": "tx_dir", "name": "...", "tier": "2", "url": "...", ...} ],
  "coverage_counts": {"1": 3, "2": 140, "3": 610, "4": 777},
  "agencies": [
    {"id": "TX-KA357", "state": "TX", "name": "Village Fire Department", "kind": "Local fire department",
     "county": "Harris", "city": "Houston", "usfa_fdid": "KA357", "coverage": 4,
     "sources": ["usfa"], "fy_start": null,
     "usfa": {"dept_type": "Career", "organization_type": "Local (...)", "stations": 1, "career": 42,
              "volunteer": 0, "paid_per_call": 0},
     "grants": 0}
  ]
}
```

`coverage` is the best tier any source gives the agency: 1 when it has `transactions` rows from a tier-1
source; 2 when it has `line_items` rows (or `transactions` rows from a tier-2 source); 3 when it has `totals`
rows; otherwise 4. An agency at tier 3 or 4 has no vendor data and must never be shown as spending $0.
`fy_start` is a month string, a list when sources disagree, or null.

## `data/states/<st>/transactions.csv.gz` (tiers 1 and 2)

One row per payment line, as close to the source's own line as it publishes, matching the Utah BigQuery line
format so the same vendor and category rules apply.

| Column | Meaning |
| --- | --- |
| `agency_id` | Agency id |
| `fiscal_year` | Fiscal year as the agency defines it (the year it ends in) |
| `posting_date` | `YYYY-MM-DD`, empty if the source has none |
| `payee_name` | Payee as published, private persons included (owner decision, 2026-10-06); `common.withhold_person` only replaces payee text with an email address or bank account text by `Payee name withheld` |
| `description` | Line description as published, empty if none |
| `account` | Account, object or fund fields as published, joined with ` / ` |
| `category_published` | The source's own spend category, if any |
| `amount` | Dollars, two decimals; refunds and reversals negative |
| `source` | Source id |
| `source_record_id` | The source's row id (voucher, check or PO number plus line), for tracing back to raw |

Duplicate uploads and reloads are removed before writing; each adapter's note in `docs/sources/<st>.md` says how.

## `data/states/<st>/line_items.csv.gz` (tier 2)

| Column | Meaning |
| --- | --- |
| `agency_id`, `fiscal_year` | As above |
| `date` | Order or invoice date, `YYYY-MM-DD`, empty if none |
| `vendor` | Seller (reseller or manufacturer) as published |
| `brand` | Brand or manufacturer as published |
| `product_type` | Product or service type as published |
| `description` | Item description as published |
| `quantity`, `unit_price`, `amount` | As published; `amount` is the line total |
| `source`, `source_record_id` | As above |

Item lines are also rolled into `transactions.csv.gz` (one row per line, payee = `vendor`) so vendor totals
work the same way for every tier.

## `data/states/<st>/totals.csv` (tier 3)

| Column | Meaning |
| --- | --- |
| `agency_id`, `fiscal_year` | As above |
| `category_published` | The source's category or line name, as published |
| `amount` | Dollars |
| `source` | Source id |

## Vendor names and categories (`config/vendor_map.csv`)

One shared map for Utah and every state: `name_key,vendor,category,confidence`, sorted by `name_key`. `name_key` is
`common.norm(payee)` (the same key as `pipeline/build.py`'s `norm()`), `vendor` the canonical vendor name (the site's
vendor id is a slug of it, so names decide which payees add up to one vendor), `category` an id from
`config/categories.csv`, `confidence` `high`, `medium` or `low`. `pipeline/build.py` classifies a payee by its row
here first, then by the first matching pattern of `config/vendor_rules.csv` and `config/keyword_rules.csv`.

A state adds vendors the same way as before, then merges:

1. Write `config/states/<st>/vendor_map_additions.csv` with the same four columns plus `spend` and `agencies` (net
   dollars and agency count per key over `transactions.csv.gz`), for the payees that make up at least 90% of the
   state's purchasing dollars, reusing a canonical name already in `config/vendor_map.csv` when the company is the
   same.
2. Run `python3 pipeline/sources/merge_vendor_maps.py`. It folds the proposals into `config/vendor_map.csv` (rules
   in its docstring: a key already in the map keeps its row; one canonical name per company, with judgment calls in
   `config/vendor_name_merges.csv`; a key a vendor rule names uses the rule's vendor; one category per vendor) and
   writes the decisions to `docs/multistate/vendor-merge.md`. Review the report, add rows to
   `config/vendor_name_merges.csv` for spellings that are one company (or a different company that a rule
   catches), restore `config/vendor_map.csv` and run it again until the report reads right.
3. Delete the additions file, rebuild Utah (`python3 pipeline/build.py`) and compare: a state row for a person's
   name shows a Utah payee with the same key under that name, and every Utah change must be intended.
4. `tests/multistate/check_<st>.py` fails while an additions file is left or when `config/vendor_map.csv` is
   broken (a repeated or unsorted `name_key`, an unknown category or confidence, an empty vendor:
   `tests/multistate/vendor_coverage.py`), and requires `config/vendor_map.csv` with the rules to give a real
   category (not `unclassified`) to at least 90% of the state's purchasing dollars (net spend per payee key above
   zero, in a purchasing category or unmapped).

`python3 pipeline/sources/merge_vendor_maps.py --check` checks the map alone (sorted unique keys, known
categories, no name that `config/vendor_name_merges.csv` renames).

## Site files (`data/`, written by `pipeline/build.py`)

`python3 pipeline/build.py` reads `config/states.csv` (states in page order, `years`, `partial_years`), builds Utah
from its raw files and every other state from `data/states/<st>/`, and writes the files below: compact JSON, UTF-8
(`ensure_ascii=False`), sorted, so two builds from the same inputs are byte-identical. Every file carries the same
`built` date, and the page refuses a file whose `built` differs from `data/index.json`'s. The build writes nothing
when `data/index.json` would be 1,000,000 bytes gzipped or more, or any file 50 MB or more. Indexes below are
0-based; a category index points into `categories`, a vendor or payee-name index into the same state file.

| File | Loaded | Content |
| --- | --- | --- |
| `data/index.json` | First, always | `meta`, `categories`, `agencies` (every state), `home` |
| `data/<st>.json` | When a view needs the state's rows | `{built, state, vendors, aliases, rows, grants, totals}` |
| `data/<st>-payments.json` | When a view shows single payments | `{built, state, payments, descriptions}` |
| `data/<st>-items.json` | For a vendor or agency of a state with item lines (`tx`, `ca`) | `{built, state, sources, strings, items}` |

`data/index.json`:
- `meta`: `built`, `site`, `states_order` (as `config/states.csv`), `years` and `partial_years` (all states), `states`
  and `sources`.
  - `meta.states.<ST>`: `name`, `years`, `partial_years`, `fetched`, `counts`, `purchasing_total`,
    `purchasing_classified_share`, `coverage` (purchasing and all-line dollars and lines by how the category was
    set), `coverage_counts` (agencies per tier), `payments_rule`, `sources` (source ids, federal ones included),
    `files` (`rows`, `payments`, `items` paths or null), `bytes_gz` (gzipped sizes the page shows while loading),
    `registry_raw`, `grants_raw`; other states also `lines_out_of_range` and `lines_out_of_range_by_source` (lines
    outside the state's years). Utah also keeps the other keys its meta had before the split (`raw_path`,
    `transactions_fetched`, `transactions_file`, `fire_expenses_file`, `transparent_utah`).
  - `meta.sources.<id>`: `state` (null for federal), `name`, `tier` (null for a source that sets no tier), `url`,
    `note` and `raw` (a path, or one per state for `usfa` and `openfema`); state sources also `years`, `fiscal_year`
    and `fetched`, from `config/states/<st>/sources.csv` (Utah's two from build.py); other states' sources also
    `raw_dir` (the source's newest `raw/<date>/<st>/<source>/` folder, which the page links).
- `categories`: `config/categories.csv` rows.
- `agencies`: Utah first in its old order, then each state in `agencies.json` order. Every agency has `id`, `state`,
  `name`, `kind`, `county`, `city`, `type`, `staffing`, `staffing_group`, `usfa` (`fdid`, `name`, stations and
  firefighter counts, or null), `budget` (`{"<fy>": amount}`: Utah's expenses, other states' published annual totals
  summed), `budget_source`, `fy_start` (month names), `notes`, `coverage` (1 to 4), `sources` (source ids) and
  `lines` (transaction lines read). Utah agencies keep their other fields (`govt_lvl`, `website`, `revenue`, `staff`
  and so on) and add `tu_id`.
- `home.<scope>` for `ALL` and each state: the default table (all fiscal years, every agency, purchasing categories),
  so the first view needs no state file. `from`, `to`; `cats`: `[category index, spend, rows, vendors, agencies, last
  fiscal year, {"<fy>": spend}]`; `sum`: `[spend, rows, vendors, agencies, {"<fy>": spend}]`. Vendors and agencies
  count where an agency, vendor, year and category net above $0.005, as the page does.

`data/<st>.json`:
- `vendors`: `{id, name, category, method, aliases, neris}`. `id` is a slug of the canonical name and is shared by
  every state; `category` is the vendor's main category in this state; `aliases` are payee-name indexes.
- `aliases`: payee names as shown (Utah withholds private persons; other states as published).
- `rows`: `[agency id, vendor index, fiscal year, category index, net amount, payee-name index or -1]`.
- `grants`: `{agency, recipient, year, program, amount, award}`.
- `totals`: `[agency id, fiscal year, category as published, amount, source id]` (tier 3; empty for Utah and Ohio).

`data/<st>-payments.json`: `payments`: `[agency id, date, vendor index, category index, amount, description index,
payee-name index or -1, fiscal year]`: lines of $1,000 or more in purchasing categories within the state's years, a
line left out when a credit of the same amount to the same payee cancels it; `descriptions`: texts.

`data/<st>-items.json`: `sources` (source ids), `strings` (brand, product type and description texts), `items`:
`[agency id, fiscal year, date, vendor index, brand, product type, description (string indexes or -1), quantity,
unit price, amount, category index (the category of the item's transaction line), source index]`. Items before the
state's first fiscal year (SCPRS, FY2013 to FY2015) are kept here and shown apart; they are in no row or payment.

Until the multi-state page (commit `de1e5cf` on main), the build wrote Utah alone to `data/data.json` and
`data/payments.json`, which the page read. They are no longer written. `tests/check_build.py`,
`tests/core_test.js` and `tests/page/compare_utah.js` read them from that commit (`--base`) to prove Utah reads
as before.

## Checks

`tests/multistate/check_<st>.py` recomputes totals from the raw files and asserts the normalized files match.
`tests/multistate/check_federal.py` does the same for the registry and grants. `tests/check_build.py` checks the
site files against `data/states/<st>/` and Utah's raw file (see its docstring).
