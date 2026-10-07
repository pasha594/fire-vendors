# Multi-state data contract

Format of the files the multi-state adapters write, so `pipeline/build.py` can merge them once the Utah
rewrite lands (PRD build-order steps 1 and 8). PRD: `docs/prd/multistate-expansion.md`.

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
- Utah will use `UT-<Transparent Utah id>` when step 1 lands.

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

## Checks

`tests/multistate/check_<st>.py` recomputes totals from the raw files and asserts the normalized files match.
`tests/multistate/check_federal.py` does the same for the registry and grants.
