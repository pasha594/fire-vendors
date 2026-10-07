# Fire Agency Vendor Finances (prototype)

Which vendors Utah fire agencies pay, how many agencies use each, and how much they spend.
Built from public data only: [Transparent Utah](https://transparent.utah.gov/) transaction lines,
the [USFA National Fire Department Registry](https://apps.usfa.fema.gov/registry/),
[OpenFEMA firefighter grants](https://www.fema.gov/openfema-data-page/non-disaster-assistance-firefighter-grants-v1)
and the [NERIS integration partner list](https://neris.fsri.org/integration-partners).

Page: https://pasha594.github.io/utah-fire-procurement/

## Coverage

- 185 agencies (`config/agencies.csv`, include=yes): 38 fire districts, fire service areas and interlocal fire
  agencies, and the fire spending of 87 cities, 42 towns and 18 counties. Cities, towns and counties that only pay
  another agency for fire service, or have almost no fire lines, are listed with include=no and the reason.
- Fiscal years 2021 to 2026. FY2026 is partly reported.
- City, town and county lines are the ones coded fire: function 2009xx in the account number, or "fire" in the
  department names.

## What the numbers are

The source is every expense line the agencies reported to Transparent Utah (its BigQuery database,
`pipeline/sql/fire_transactions.sql`). The query leaves out payroll, benefit and refund accounts; payroll left under
other account names is categorized as payroll by `config/account_rules.csv`. Transactions an entity uploaded again
in a later batch are counted once, and police department lines of Lone Peak Public Safety District are left out. Each line gets a category from its
account names, its payee and its description (see `pipeline/build.py`). Each row in `data/data.json` is the net
amount one agency paid one payee name in one fiscal year in one category. `data/payments.json` lists single lines of
$1,000 or more in purchasing categories, with date and description. Fire districts also have staff counts and pay from
their compensation reports (employee names replaced by numbers), revenue by account and total expenses; for cities,
towns and counties the annual expenses are their fire-coded expenses, including payroll
(`pipeline/sql/fire_expenses_by_year.sql`). Payees that are private persons are grouped as "Individuals (names
withheld)", and descriptions that may name a person are not shown.

## Run locally

```
python3 -m http.server 8000
```

Then open http://localhost:8000. Opening `index.html` straight from disk does not work because the
page loads `data/data.json` (and `data/payments.json` for single payments).

## Refresh the data

```
python3 pipeline/fetch.py    # downloads into raw/<today>/ (about 2 minutes, throttled)
python3 pipeline/build.py    # rebuilds data/data.json and data/payments.json from the newest raw folders
```

The BigQuery files are saved by hand: run `pipeline/sql/fire_transactions.sql` and
`pipeline/sql/fire_expenses_by_year.sql` in BigQuery and save the results, gzipped, in
`raw/<date>/transparent_utah_bigquery/`. The build uses the newest folder that has them.

Both scripts use the Python standard library only. Raw files are kept as downloaded (gzipped) and
never edited; everything in `data/` is rebuilt from `raw/` and `config/`. The raw files keep payee
names exactly as Transparent Utah publishes them, including private persons; the page withholds those names.

## Config files

| File | What it controls |
| --- | --- |
| `config/agencies.csv` | Which Transparent Utah entities are included, their kind, USFA registry id and county. `id` is the Transparent Utah entity id (`tu_id`); an entity without one would get a slug of its name |
| `config/categories.csv` | Category list, and which categories count as purchasing |
| `config/vendor_map.csv` | Payee name (normalized) to canonical vendor name and category |
| `config/vendor_rules.csv` | Regex rules that fold rare spellings into a vendor already in the vendor map |
| `config/keyword_rules.csv` | Fallback regex rules for payees not in the vendor map, first match wins |
| `config/account_rules.csv` | Account names ("cat1 \| cat2 \| cat3") to a category: `override` always applies, `refine` only to broad payees (except the vendor categories in `skip_vendor_category`); category `vendor` keeps the payee's category |
| `config/description_rules.csv` | Regex on the line description for broad payees, first match wins; `skip_vendor_category` names payee categories a rule does not apply to |
| `config/card_programs.csv` | Card issuers and payment services whose lines are categorized like broad payees |
| `config/description_privacy_patterns.csv` | Descriptions that may identify a person and are not shown; `payee_names` says whether a pattern also withholds payee names that are not in the vendor map |
| `config/payee_name_redactions.csv` | Payee text that is not shown (email addresses, bank references) |
| `config/revenue_exclusions.csv` | Revenue accounts left out of revenue totals (borrowing, transfers, donated infrastructure) |
| `config/grant_recipients.csv` | FEMA grant recipient names matched to agencies (`agency_id`) |
| `config/neris_partners.csv` | NERIS integration partners, used to flag vendors |

## Sources

Vendor payments come from the Transparent Utah BigQuery database (`ut-sao-transparency-prod.transaction`,
"Super User" access); the queries are in `pipeline/sql/`. District details, total expenses, revenue and
compensation come from the public query service the transparent.utah.gov site itself uses (`pipeline/fetch.py`
lists the exact calls). It is not a documented API and may change.
