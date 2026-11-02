TRUNCATE TABLE mart.seller_90d_value;

WITH max_observation AS (
    SELECT MAX(order_purchase_timestamp) AS max_purchase_ts
    FROM raw.orders
),
deal_base AS (
    SELECT
        d.mql_id,
        d.seller_id,
        d.won_date,
        l.first_contact_date,
        COALESCE(NULLIF(TRIM(l.origin), ''), '(missing)') AS origin,
        (d.won_date::date - l.first_contact_date) AS close_interval
    FROM raw.closed_deals d
    LEFT JOIN raw.marketing_qualified_leads l USING (mql_id)
    WHERE d.seller_id IS NOT NULL
      AND d.won_date IS NOT NULL
),
item_value AS (
    SELECT
        i.seller_id,
        o.order_id,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_status,
        SUM(COALESCE(i.price, 0)) AS item_gmv,
        SUM(COALESCE(i.freight_value, 0)) AS freight
    FROM raw.order_items i
    JOIN raw.orders o USING (order_id)
    GROUP BY
        i.seller_id, o.order_id, o.order_purchase_timestamp,
        o.order_delivered_customer_date, o.order_status
),
observed_sellers AS (
    SELECT DISTINCT seller_id
    FROM raw.order_items
    WHERE seller_id IS NOT NULL
)
INSERT INTO mart.seller_90d_value (
    mql_id, seller_id, origin, first_contact_date, won_date, close_days,
    window_start_inclusive, window_end_exclusive, mature_90d,
    seller_linked_to_order_items, orders_90d, delivered_orders_90d,
    orders_delivered_within_90d, activated_90d, activated_90d_any_status,
    activated_delivered_within_90d, gmv_90d_all_statuses,
    gmv_90d_delivered_only, gmv_90d_delivered_within_90d,
    gmv_90d_non_delivered_proxy, freight_90d_all_statuses
)
SELECT
    d.mql_id,
    d.seller_id,
    d.origin,
    d.first_contact_date,
    d.won_date,
    d.close_interval,
    d.won_date,
    d.won_date + INTERVAL '90 days',
    (d.won_date + INTERVAL '90 days' <= m.max_purchase_ts),
    (s.seller_id IS NOT NULL),

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(DISTINCT v.order_id) FILTER (
             WHERE v.order_id IS NOT NULL
         )::INT END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(DISTINCT v.order_id) FILTER (
             WHERE v.order_status = 'delivered'
         )::INT END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(DISTINCT v.order_id) FILTER (
             WHERE v.order_status = 'delivered'
               AND v.order_delivered_customer_date >= d.won_date
               AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days'
         )::INT END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(DISTINCT v.order_id) FILTER (
             WHERE v.order_status = 'delivered'
         ) > 0 END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(DISTINCT v.order_id) FILTER (
             WHERE v.order_id IS NOT NULL
         ) > 0 END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(DISTINCT v.order_id) FILTER (
             WHERE v.order_status = 'delivered'
               AND v.order_delivered_customer_date >= d.won_date
               AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days'
         ) > 0 END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_gmv), 0) END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_gmv) FILTER (
             WHERE v.order_status = 'delivered'
         ), 0) END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_gmv) FILTER (
             WHERE v.order_status = 'delivered'
               AND v.order_delivered_customer_date >= d.won_date
               AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days'
         ), 0) END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_gmv), 0)
            - COALESCE(SUM(v.item_gmv) FILTER (
                WHERE v.order_status = 'delivered'
            ), 0) END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.freight), 0) END

FROM deal_base d
CROSS JOIN max_observation m
LEFT JOIN observed_sellers s ON s.seller_id = d.seller_id
LEFT JOIN item_value v
    ON v.seller_id = d.seller_id
   AND v.order_purchase_timestamp >= d.won_date
   AND v.order_purchase_timestamp < d.won_date + INTERVAL '90 days'
GROUP BY
    d.mql_id, d.seller_id, d.origin, d.first_contact_date,
    d.won_date, d.close_interval, m.max_purchase_ts, s.seller_id;
	SELECT
    COUNT(*) AS seller_rows,
    COUNT(*) FILTER (WHERE mature_90d) AS mature_sellers,
    COUNT(*) FILTER (
        WHERE mature_90d AND seller_linked_to_order_items
    ) AS linked_mature_sellers,
    COUNT(*) FILTER (
        WHERE mature_90d AND seller_linked_to_order_items AND activated_90d
    ) AS activated_linked_mature_sellers,
    ROUND(SUM(gmv_90d_delivered_only) FILTER (
        WHERE mature_90d AND seller_linked_to_order_items
    ), 2) AS delivered_gmv
FROM mart.seller_90d_value;