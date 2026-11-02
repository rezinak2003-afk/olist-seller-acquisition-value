DROP VIEW IF EXISTS mart.acquisition_funnel;

ALTER TABLE raw.closed_deals
ALTER COLUMN won_date TYPE TIMESTAMP
USING won_date::timestamp;

UPDATE raw.closed_deals d
SET won_date = NULLIF(TRIM(s.won_date), '')::timestamp
FROM public.stg_closed_deals s
WHERE d.mql_id = s.mql_id;

ALTER TABLE mart.seller_90d_value
ALTER COLUMN won_date TYPE TIMESTAMP
USING won_date::timestamp;

CREATE OR REPLACE VIEW mart.acquisition_funnel AS
WITH lead_base AS (
    SELECT mql_id,
           COALESCE(NULLIF(TRIM(origin), ''), '(missing)') AS origin,
           first_contact_date
    FROM raw.marketing_qualified_leads
),
deal_flags AS (
    SELECT mql_id,
           BOOL_OR(seller_id IS NOT NULL) AS has_seller,
           MIN(won_date) AS won_date
    FROM raw.closed_deals
    GROUP BY mql_id
)
SELECT l.origin,
       COUNT(DISTINCT l.mql_id) AS qualified_leads,
       COUNT(DISTINCT l.mql_id) FILTER (WHERE d.has_seller) AS closed_leads,
       COUNT(DISTINCT l.mql_id)
         - COUNT(DISTINCT l.mql_id) FILTER (WHERE d.has_seller) AS not_closed_leads,
       100.0 * COUNT(DISTINCT l.mql_id) FILTER (WHERE d.has_seller)
         / NULLIF(COUNT(DISTINCT l.mql_id), 0) AS lead_to_deal_conversion_pct,
       percentile_cont(0.5) WITHIN GROUP (
           ORDER BY d.won_date - l.first_contact_date
       ) FILTER (WHERE d.won_date >= l.first_contact_date) AS median_close_days
FROM lead_base l
LEFT JOIN deal_flags d USING (mql_id)
GROUP BY l.origin;