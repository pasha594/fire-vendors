"""Samples behind docs/sources/ca.md for the California sources that were reached but not built.

    python3 pipeline/sources/ca_feasibility.py fetch

Not an adapter: it writes only raw/<date>/ca/<source>/ files and no table in data/states/ca/.

ca_sandiego        City of San Diego "Operating Actuals" (https://data.sandiego.gov/datasets/operating-actuals/),
                   one 66 MB CSV of actual spending by fiscal year, fund, department and expense account; no payee,
                   so no tier 1 data. (San Diego publishes no vendor payment dataset; the city's fire spending is in
                   ca_sco_cities.) seshat.datasd.org answers 403 to /robots.txt; data.sandiego.gov has none (404).
    raw/<date>/ca/ca_sandiego/sample.csv.gz       header and first 100 rows (one HTTP range request)
    raw/<date>/ca/ca_sandiego/dictionary.csv.gz   the dataset's data dictionary
"""
import sys

import common

ST = "CA"
SD_CSV = "https://seshat.datasd.org/operating_actuals/actuals_operating_datasd.csv"
SD_DICT = "https://seshat.datasd.org/operating_actuals/operating_actuals_dictionary_datasd.csv"


def fetch():
    head = common.get(SD_CSV, headers={"Range": "bytes=0-65535"})
    lines = head.split(b"\n")[:101]
    common.save_raw(ST, "ca_sandiego", "sample.csv", b"\n".join(lines) + b"\n")
    common.save_raw(ST, "ca_sandiego", "dictionary.csv", common.get(SD_DICT))
    print(f"{ST}: feasibility samples saved")


if __name__ == "__main__":
    {"fetch": fetch}[sys.argv[1]]()
