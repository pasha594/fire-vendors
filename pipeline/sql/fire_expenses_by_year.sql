-- Fire-coded expenses (including payroll) per city, town and county and fiscal year, used as the
-- "annual expenses" size measure for city/town/county fire departments.
-- Saved as raw/<date>/transparent_utah_bigquery/fire_expenses_by_year.csv.gz
-- Re-uploaded copies of a transaction are dropped by keeping the first batch, as in fire_transactions.sql.
SELECT entity_name, govt_lvl, fiscal_year, ROUND(SUM(amount)) AS fire_expenses
FROM (
  SELECT entity_name, govt_lvl, fiscal_year, amount
  FROM `ut-sao-transparency-prod.transaction.transaction`
  WHERE type = 'EX' AND fiscal_year BETWEEN 2021 AND 2026
    AND govt_lvl IN ('City', 'Town', 'County')
    AND (REGEXP_CONTAINS(IFNULL(account_number, ''), r'^[^-]+-2009\d\d-')
         OR REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(org1, ''), ' ', IFNULL(org2, ''))), r'fire'))
    AND NOT REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(org1, ''), ' ', IFNULL(org2, ''))), r'firework')
  QUALIFY batch_id = MIN(batch_id) OVER (
    PARTITION BY entity_name, id, posting_date, vendor_name, account_number,
                 CAST(ROUND(amount * 100) AS INT64))
)
GROUP BY 1, 2, 3
ORDER BY 1, 3
