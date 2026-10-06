-- Fire-related expense transactions, FY2021-FY2026, from the Transparent Utah BigQuery database
-- (Super User access). Run in BigQuery; the result is saved as
-- raw/<date>/transparent_utah_bigquery/fire_transactions_fy2021_2026.csv.gz
--
-- Scope: every expense line of the fire agencies in config/agencies.csv, plus every city, town
-- and county line coded fire (UCOA function 2009xx in account_number, or "fire" in org1/org2,
-- not fireworks). Payroll, benefits and refunds are left out (refunds can name patients).
-- Police department lines of a public safety district (Lone Peak) are left out.
-- Re-uploaded copies of a transaction (same entity, id, date, vendor and amount in a later batch,
-- even when the later batch changed the account) are dropped by keeping the first batch.
-- pipeline/build.py applies both rules again, and also drops copies that a later batch uploaded
-- with renumbered ids (see reupload_copies), so files saved with an older version of this query
-- give the same result.
SELECT
  entity_name, govt_lvl, fiscal_year, posting_date, id, batch_id,
  vendor_name, dba_name, description, contract_name, contract_number,
  fund1, org1, org2, org3, cat1, cat2, cat3, function1, function2,
  account_number, amount
FROM `ut-sao-transparency-prod.transaction.transaction`
WHERE type = 'EX'
  AND fiscal_year BETWEEN 2021 AND 2026
  AND (
    entity_name IN (
      'Beaver County Special Serv. District 2 (fire)', 'Beaver Fire District 1',
      'Central Box Elder Fire Special Service District', 'Dammeron Valley Fire Special Service District',
      'Diamond Valley Fire Special Service District', 'Emery County Fire Protection SSD',
      'Flaming Gorge Fire & EMS District', 'Garden City Fire Protection District',
      'Grand County Service Area Castle Valley Fire Protection District',
      'Hurricane Valley Fire Special Service District', 'Juab County Spec Serv Fire Protection District',
      'Laketown Fire District', 'Lone Peak Public Safety District', 'Mammoth Creek Fire District',
      'Millard County Fire District', 'Moab Valley Fire Protection District',
      'Mountain Green Fire Protection District', 'North Central Fire Special Service District',
      'North Davis Fire District', 'North Summit Fire Protection District',
      'North Tooele Fire Protection Service District', 'North View Fire District',
      'Park City Fire Service District', 'Randolph Fire District', 'Riverton Fire Service Area',
      'Rockville Springdale Fire Protection District', 'Sanpete County Fire Special Service District',
      'South Davis Metro Fire Agency', 'South Davis Metro Fire Service Area',
      'South Summit Fire Protection District', 'Thompson Fire Protection District',
      'Uintah Fire Suppression Special Service District', 'Unified Fire Authority',
      'Unified Fire Service Area', 'WPR Road and Fire District', 'Wasatch County Fire Protection SSD',
      'Weber Fire District', 'Woodruff Fire District')
    OR (
      govt_lvl IN ('City', 'Town', 'County')
      AND (
        REGEXP_CONTAINS(IFNULL(account_number, ''), r'^[^-]+-2009\d\d-')
        OR REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(org1, ''), ' ', IFNULL(org2, ''))), r'fire')
      )
      AND NOT REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(org1, ''), ' ', IFNULL(org2, ''))), r'firework')
    )
  )
  AND NOT REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(cat1, ''), ' ', IFNULL(cat2, ''))),
        r'salar|wage|payroll|personnel|employee benefit|employer paid|compensation|retirement')
  AND NOT REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(cat1, ''), ' ', IFNULL(cat2, ''), ' ', IFNULL(description, ''))), r'refund')
  AND NOT (REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(org1, ''), ' ', IFNULL(org2, ''))), r'\bpolice\b')
           AND NOT REGEXP_CONTAINS(LOWER(CONCAT(IFNULL(org1, ''), ' ', IFNULL(org2, ''), ' ', IFNULL(org3, ''))), r'fire|ems|wildland'))
QUALIFY batch_id = MIN(batch_id) OVER (
  PARTITION BY entity_name, id, posting_date, vendor_name,
               CAST(ROUND(amount * 100) AS INT64))
