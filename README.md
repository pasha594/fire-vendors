# Utah fire agency vendor payments (prototype)

Which vendors Utah fire agencies pay, how many agencies use each, and how much they spend.
Built from public data only: [Transparent Utah](https://transparent.utah.gov/) vendor payments,
the [USFA National Fire Department Registry](https://apps.usfa.fema.gov/registry/),
[OpenFEMA firefighter grants](https://www.fema.gov/openfema-data-page/non-disaster-assistance-firefighter-grants-v1)
and the [NERIS integration partner list](https://neris.fsri.org/integration-partners).

Page: https://pasha594.github.io/utah-fire-procurement/

## Coverage

- 38 Utah fire districts, fire service areas and interlocal fire agencies (`config/agencies.csv`).
- Fiscal years 2021 to 2026. FY2026 is partly reported.
- City and county fire departments are not included yet. Their fire spending is not separable by
  vendor in the public Transparent Utah data; that needs the Transparent Utah BigQuery ("Super User") access.

## What the numbers are

Each row is the net amount one agency paid one payee name in one fiscal year, as reported to
Transparent Utah. There are no invoice lines or item descriptions, so categories are assigned per
vendor, not per purchase. Payees that are private persons are grouped as "Individuals (names withheld)".

## Run locally

```
python3 -m http.server 8000
```

Then open http://localhost:8000. Opening `index.html` straight from disk does not work because the
page loads `data/data.json`.

## Refresh the data

```
python3 pipeline/fetch.py    # downloads into raw/<today>/ (about 2 minutes, throttled)
python3 pipeline/build.py    # rebuilds data/data.json from the newest raw folder
```

Both scripts use the Python standard library only. Raw files are kept as downloaded (gzipped) and
never edited; everything in `data/` is rebuilt from `raw/` and `config/`.

## Config files

| File | What it controls |
| --- | --- |
| `config/agencies.csv` | Which Transparent Utah entities are included, their USFA registry id and county |
| `config/categories.csv` | Category list, and which categories count as purchasing |
| `config/vendor_map.csv` | Payee name (normalized) to canonical vendor name and category |
| `config/keyword_rules.csv` | Fallback regex rules for payees not in the vendor map, first match wins |
| `config/grant_recipients.csv` | FEMA grant recipient names matched to agencies |
| `config/neris_partners.csv` | NERIS integration partners, used to flag vendors |

## Sources

The Transparent Utah numbers come from the public query service the transparent.utah.gov site
itself uses (`pipeline/fetch.py` lists the exact calls). It is not a documented API and may change.
