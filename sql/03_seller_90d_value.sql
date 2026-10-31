-- Materialise one record per closed seller deal.
-- The purchase interval is [won_date, won_date + 90 days). The maturity horizon
-- is the day after the last calendar date with >= 50 orders (exclusive).
-- Unlinked seller marketplace outcomes remain NULL; known linked zeroes remain 0.
TRUNCATE TABLE mart.seller_90d_value;

WITH daily AS (
  SELECT order_purchase_timestamp::date AS d, COUNT(*) AS n
  FROM raw.orders
  WHERE order_purchase_timestamp IS NOT NULL
  GROUP BY 1
), max_observation AS (
  SELECT (MAX(d) FILTER (WHERE n >= 50) + 1)::timestamp AS data_end
  FROM daily
), deal_base AS (
  SELECT d.mql_id, d.seller_id, d.won_date, l.first_contact_date,
         COALESCE(NULLIF(TRIM(l.origin), ''), '(missing)') AS origin,
         COALESCE(NULLIF(TRIM(d.lead_type), ''), '(missing)') AS lead_type,
         COALESCE(NULLIF(TRIM(d.business_segment), ''), '(missing)') AS business_segment,
         COALESCE(NULLIF(TRIM(d.business_type), ''), '(missing)') AS business_type,
         TO_CHAR(d.won_date, 'YYYY-MM') AS won_month,
         CASE WHEN d.won_date::date >= l.first_contact_date
              THEN (d.won_date::date-l.first_contact_date) END AS close_interval
  FROM raw.closed_deals d LEFT JOIN raw.marketing_qualified_leads l USING (mql_id)
  WHERE d.seller_id IS NOT NULL AND d.won_date IS NOT NULL
), item_value AS (
  SELECT i.seller_id, o.order_id, o.order_purchase_timestamp,
         o.order_delivered_customer_date, o.order_status,
         SUM(COALESCE(i.price,0)) AS item_gmv,
         SUM(COALESCE(i.freight_value,0)) AS freight,
         COUNT(*) AS item_count
  FROM raw.order_items i JOIN raw.orders o USING (order_id)
  GROUP BY i.seller_id,o.order_id,o.order_purchase_timestamp,o.order_delivered_customer_date,o.order_status
), observed_sellers AS (
  SELECT DISTINCT seller_id FROM raw.order_items WHERE seller_id IS NOT NULL
)
INSERT INTO mart.seller_90d_value (
  mql_id,seller_id,origin,lead_type,business_segment,business_type,won_month,
  first_contact_date,won_date,close_days,window_start_inclusive,window_end_exclusive,data_end,
  mature_90d,seller_linked_to_order_items,orders_90d,delivered_orders_90d,
  items_90d,orders_delivered_within_90d,activated_90d,activated_90d_any_status,
  activated_delivered_within_90d,gmv_90d_all_statuses,gmv_90d_delivered_only,
  gmv_90d_delivered_within_90d,gmv_90d_non_delivered_proxy,freight_90d_all_statuses
)
SELECT d.mql_id,d.seller_id,d.origin,d.lead_type,d.business_segment,d.business_type,d.won_month,
       d.first_contact_date,d.won_date,d.close_interval,d.won_date AS window_start_inclusive,
       d.won_date + INTERVAL '90 days' AS window_end_exclusive,m.data_end,
       (m.data_end IS NOT NULL AND d.won_date + INTERVAL '90 days' <= m.data_end) AS mature_90d,
       (s.seller_id IS NOT NULL) AS seller_linked_to_order_items,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE COUNT(DISTINCT v.order_id) FILTER (WHERE v.order_id IS NOT NULL)::INT END AS orders_90d,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE COUNT(DISTINCT v.order_id) FILTER (WHERE v.order_status='delivered')::INT END AS delivered_orders_90d,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE COALESCE(SUM(v.item_count),0)::INT END AS items_90d,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE COUNT(DISTINCT v.order_id) FILTER (
         WHERE v.order_status='delivered' AND v.order_delivered_customer_date >= d.won_date
           AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days')::INT END AS orders_delivered_within_90d,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE
         (COUNT(DISTINCT v.order_id) FILTER (WHERE v.order_status='delivered') > 0) END AS activated_90d,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE
         (COUNT(DISTINCT v.order_id) FILTER (WHERE v.order_id IS NOT NULL) > 0) END AS activated_90d_any_status,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE
         (COUNT(DISTINCT v.order_id) FILTER (WHERE v.order_status='delivered'
           AND v.order_delivered_customer_date >= d.won_date
           AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days') > 0) END AS activated_delivered_within_90d,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE COALESCE(SUM(v.item_gmv),0) END AS gmv_90d_all_statuses,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE COALESCE(SUM(v.item_gmv) FILTER (WHERE v.order_status='delivered'),0) END AS gmv_90d_delivered_only,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE COALESCE(SUM(v.item_gmv) FILTER (
         WHERE v.order_status='delivered' AND v.order_delivered_customer_date >= d.won_date
           AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days'),0) END AS gmv_90d_delivered_within_90d,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE
         COALESCE(SUM(v.item_gmv),0)-COALESCE(SUM(v.item_gmv) FILTER (WHERE v.order_status='delivered'),0) END AS gmv_90d_non_delivered_proxy,
       CASE WHEN s.seller_id IS NULL THEN NULL ELSE COALESCE(SUM(v.freight),0) END AS freight_90d_all_statuses
FROM deal_base d CROSS JOIN max_observation m
LEFT JOIN observed_sellers s ON s.seller_id=d.seller_id
LEFT JOIN item_value v ON v.seller_id=d.seller_id
 AND v.order_purchase_timestamp >= d.won_date
 AND v.order_purchase_timestamp < d.won_date + INTERVAL '90 days'
GROUP BY d.mql_id,d.seller_id,d.origin,d.lead_type,d.business_segment,d.business_type,d.won_month,
         d.first_contact_date,d.won_date,d.close_interval,m.data_end,s.seller_id;

-- Window-function model: seller's first observed marketplace sale and time to first sale.
DROP VIEW IF EXISTS mart.seller_first_sale CASCADE;
CREATE VIEW mart.seller_first_sale AS
WITH deal_wins AS (
  SELECT seller_id, MIN(won_date) AS won_date
  FROM raw.closed_deals
  WHERE seller_id IS NOT NULL AND won_date IS NOT NULL
  GROUP BY seller_id
), seller_orders AS (
  SELECT d.seller_id,d.won_date,o.order_id,o.order_purchase_timestamp,
         ROW_NUMBER() OVER (PARTITION BY d.seller_id ORDER BY o.order_purchase_timestamp,o.order_id,i.order_item_id) AS order_rank
  FROM deal_wins d
  JOIN raw.order_items i ON i.seller_id=d.seller_id
  JOIN raw.orders o USING (order_id)
  WHERE o.order_purchase_timestamp >= d.won_date
), first_sales AS (
  SELECT seller_id,won_date,order_id,order_purchase_timestamp AS first_sale_timestamp
  FROM seller_orders WHERE order_rank=1
)
SELECT f.seller_id,f.order_id,f.first_sale_timestamp,
       (f.first_sale_timestamp::date-f.won_date::date) AS days_from_win_to_first_sale
FROM first_sales f;
