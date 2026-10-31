-- Denominators are explicit. Activation and GMV rates use linked mature deals only.
DROP VIEW IF EXISTS mart.channel_90d_summary CASCADE;
CREATE VIEW mart.channel_90d_summary AS
WITH mature AS (
  SELECT * FROM mart.seller_90d_value WHERE mature_90d IS TRUE
), grouped AS (
  SELECT origin,
         COUNT(*) AS mature_seller_deals,
         COUNT(*) FILTER (WHERE seller_linked_to_order_items) AS linked_mature_seller_deals,
         COUNT(*) FILTER (WHERE NOT seller_linked_to_order_items) AS unlinked_mature_seller_deals,
         COUNT(*) FILTER (WHERE activated_90d IS TRUE) AS activated_sellers_90d,
         COUNT(*) FILTER (WHERE activated_delivered_within_90d IS TRUE) AS activated_delivered_within_90d,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY gmv_90d_delivered_only)
           FILTER (WHERE seller_linked_to_order_items) AS median_gmv_90d,
         AVG(gmv_90d_delivered_only) FILTER (WHERE seller_linked_to_order_items) AS mean_gmv_90d,
         percentile_cont(0.9) WITHIN GROUP (ORDER BY gmv_90d_delivered_only)
           FILTER (WHERE seller_linked_to_order_items) AS p90_gmv_90d,
         SUM(gmv_90d_delivered_only) FILTER (WHERE seller_linked_to_order_items) AS total_gmv_90d,
         SUM(gmv_90d_delivered_within_90d) FILTER (WHERE seller_linked_to_order_items) AS total_gmv_delivered_within_90d,
         AVG(gmv_90d_delivered_within_90d) FILTER (WHERE seller_linked_to_order_items) AS mean_gmv_delivered_within_90d,
         percentile_cont(0.5) WITHIN GROUP (ORDER BY close_days) AS median_close_days_all_mature_deals
  FROM mature GROUP BY origin
), rates AS (
  SELECT *,
    activated_sellers_90d::NUMERIC/NULLIF(linked_mature_seller_deals,0) AS p_activation,
    activated_delivered_within_90d::NUMERIC/NULLIF(linked_mature_seller_deals,0) AS p_strict,
    linked_mature_seller_deals::NUMERIC/NULLIF(mature_seller_deals,0) AS p_linkage
  FROM grouped
)
SELECT origin,mature_seller_deals,linked_mature_seller_deals,unlinked_mature_seller_deals,
       100*p_linkage AS marketplace_linkage_rate_pct,
       activated_sellers_90d,
       linked_mature_seller_deals-activated_sellers_90d AS non_activated_linked_sellers_90d,
       100*p_activation AS activation_rate_pct,
       CASE WHEN linked_mature_seller_deals > 0 THEN
         100*((p_activation+1.95996398454^2/(2*linked_mature_seller_deals)) /
           (1+1.95996398454^2/linked_mature_seller_deals) -
           1.95996398454*SQRT((p_activation*(1-p_activation)+1.95996398454^2/(4*linked_mature_seller_deals))/linked_mature_seller_deals) /
           (1+1.95996398454^2/linked_mature_seller_deals))
       END AS activation_ci_95_low_pct,
       CASE WHEN linked_mature_seller_deals > 0 THEN
         100*((p_activation+1.95996398454^2/(2*linked_mature_seller_deals)) /
           (1+1.95996398454^2/linked_mature_seller_deals) +
           1.95996398454*SQRT((p_activation*(1-p_activation)+1.95996398454^2/(4*linked_mature_seller_deals))/linked_mature_seller_deals) /
           (1+1.95996398454^2/linked_mature_seller_deals))
       END AS activation_ci_95_high_pct,
       activated_delivered_within_90d,
       100*p_strict AS delivery_within_90d_rate_pct,
       CASE WHEN linked_mature_seller_deals > 0 THEN
         100*((p_strict+1.95996398454^2/(2*linked_mature_seller_deals)) /
           (1+1.95996398454^2/linked_mature_seller_deals) -
           1.95996398454*SQRT((p_strict*(1-p_strict)+1.95996398454^2/(4*linked_mature_seller_deals))/linked_mature_seller_deals) /
           (1+1.95996398454^2/linked_mature_seller_deals))
       END AS delivery_within_90d_ci_95_low_pct,
       CASE WHEN linked_mature_seller_deals > 0 THEN
         100*((p_strict+1.95996398454^2/(2*linked_mature_seller_deals)) /
           (1+1.95996398454^2/linked_mature_seller_deals) +
           1.95996398454*SQRT((p_strict*(1-p_strict)+1.95996398454^2/(4*linked_mature_seller_deals))/linked_mature_seller_deals) /
           (1+1.95996398454^2/linked_mature_seller_deals))
       END AS delivery_within_90d_ci_95_high_pct,
       median_gmv_90d,mean_gmv_90d,p90_gmv_90d,total_gmv_90d,
       total_gmv_delivered_within_90d,mean_gmv_delivered_within_90d,
       median_close_days_all_mature_deals
FROM rates;

-- Daily cumulative seller activation by origin; one event per seller at first delivered purchase day.
DROP VIEW IF EXISTS mart.cumulative_activation_by_day CASCADE;
CREATE VIEW mart.cumulative_activation_by_day AS
WITH mature AS (
  SELECT * FROM mart.seller_90d_value WHERE mature_90d IS TRUE AND seller_linked_to_order_items IS TRUE
), first_activation AS (
  SELECT s.mql_id,s.origin,
         MIN((o.order_purchase_timestamp::date-s.won_date::date)) AS activation_day
  FROM mature s JOIN raw.order_items i USING (seller_id)
  JOIN raw.orders o USING (order_id)
  WHERE o.order_status='delivered'
    AND o.order_purchase_timestamp >= s.won_date
    AND o.order_purchase_timestamp < s.won_date + INTERVAL '90 days'
  GROUP BY s.mql_id,s.origin
), origin_days AS (
  SELECT DISTINCT origin FROM mature
), days AS (SELECT generate_series(0,90) AS day_since_win), daily_events AS (
  SELECT origin,activation_day AS day_since_win,COUNT(*) AS new_activations
  FROM first_activation GROUP BY origin,activation_day
), grid AS (
  SELECT o.origin,d.day_since_win,COUNT(DISTINCT m.mql_id) AS linked_mature_denominator,
         COALESCE(e.new_activations,0) AS new_activations
  FROM origin_days o CROSS JOIN days d
  LEFT JOIN mature m ON m.origin=o.origin
  LEFT JOIN daily_events e ON e.origin=o.origin AND e.day_since_win=d.day_since_win
  GROUP BY o.origin,d.day_since_win,e.new_activations
)
SELECT origin,day_since_win,linked_mature_denominator,new_activations,
       SUM(new_activations) OVER (PARTITION BY origin ORDER BY day_since_win ROWS UNBOUNDED PRECEDING) AS cumulative_activated
FROM grid;
