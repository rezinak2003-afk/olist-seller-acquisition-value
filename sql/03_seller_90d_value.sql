-- Seller 90-day value mart
-- Mirrors src/pipeline.py: build_seller_value()

TRUNCATE TABLE mart.seller_90d_value;

WITH daily_orders AS (
    SELECT
        order_purchase_timestamp::date AS purchase_day,
        COUNT(*) AS order_count
    FROM raw.orders
    WHERE order_purchase_timestamp IS NOT NULL
    GROUP BY order_purchase_timestamp::date
),
last_qualifying_day AS (
    SELECT MAX(purchase_day) AS last_day
    FROM daily_orders
    WHERE order_count >= 50
),
data_boundary AS (
    SELECT (last_day + INTERVAL '1 day')::timestamp AS data_end
    FROM last_qualifying_day
),
deal_base AS (
    SELECT
        d.mql_id,
        d.seller_id,
        COALESCE(NULLIF(TRIM(l.origin), ''), '(missing)') AS origin,
        COALESCE(NULLIF(TRIM(d.lead_type), ''), '(missing)') AS lead_type,
        COALESCE(NULLIF(TRIM(d.business_segment), ''), '(missing)') AS business_segment,
        COALESCE(NULLIF(TRIM(d.business_type), ''), '(missing)') AS business_type,
        TO_CHAR(d.won_date, 'YYYY-MM') AS won_month,
        l.first_contact_date,
        d.won_date,
        CASE
            WHEN l.first_contact_date IS NOT NULL
             AND d.won_date >= l.first_contact_date
            THEN FLOOR(EXTRACT(EPOCH FROM
                (d.won_date - l.first_contact_date)
            ) / 86400)::integer
            ELSE NULL
        END AS close_days
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
        COUNT(*) AS item_count,
        SUM(COALESCE(i.price, 0)) AS item_gmv,
        SUM(COALESCE(i.freight_value, 0)) AS freight
    FROM raw.order_items i
    JOIN raw.orders o USING (order_id)
    GROUP BY
        i.seller_id,
        o.order_id,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_status
),
observed_sellers AS (
    SELECT DISTINCT seller_id
    FROM raw.order_items
    WHERE seller_id IS NOT NULL
)
INSERT INTO mart.seller_90d_value (
    mql_id, seller_id, origin, lead_type, business_segment,
    business_type, won_month, first_contact_date, won_date,
    close_days, window_start_inclusive, window_end_exclusive,
    data_end, mature_90d, seller_linked_to_order_items,
    orders_90d, delivered_orders_90d, items_90d,
    orders_delivered_within_90d, activated_90d,
    activated_90d_any_status, activated_delivered_within_90d,
    gmv_90d_all_statuses, gmv_90d_delivered_only,
    gmv_90d_delivered_within_90d, gmv_90d_non_delivered_proxy,
    freight_90d_all_statuses
)
SELECT
    d.mql_id,
    d.seller_id,
    d.origin,
    d.lead_type,
    d.business_segment,
    d.business_type,
    d.won_month,
    d.first_contact_date,
    d.won_date,
    d.close_days,
    d.won_date,
    d.won_date + INTERVAL '90 days',
    b.data_end,
    COALESCE(d.won_date + INTERVAL '90 days' <= b.data_end, FALSE),
    (s.seller_id IS NOT NULL),

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(v.order_id)::integer
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(v.order_id) FILTER (
             WHERE v.order_status = 'delivered'
         )::integer
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_count), 0)::integer
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(v.order_id) FILTER (
             WHERE v.order_status = 'delivered'
               AND v.order_delivered_customer_date >= d.won_date
               AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days'
         )::integer
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(v.order_id) FILTER (
             WHERE v.order_status = 'delivered'
         ) > 0
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(v.order_id) > 0
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COUNT(v.order_id) FILTER (
             WHERE v.order_status = 'delivered'
               AND v.order_delivered_customer_date >= d.won_date
               AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days'
         ) > 0
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_gmv), 0)
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_gmv) FILTER (
             WHERE v.order_status = 'delivered'
         ), 0)
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_gmv) FILTER (
             WHERE v.order_status = 'delivered'
               AND v.order_delivered_customer_date >= d.won_date
               AND v.order_delivered_customer_date < d.won_date + INTERVAL '90 days'
         ), 0)
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.item_gmv), 0)
            - COALESCE(SUM(v.item_gmv) FILTER (
                WHERE v.order_status = 'delivered'
            ), 0)
    END,

    CASE WHEN s.seller_id IS NULL THEN NULL
         ELSE COALESCE(SUM(v.freight), 0)
    END

FROM deal_base d
CROSS JOIN data_boundary b
LEFT JOIN observed_sellers s
    ON s.seller_id = d.seller_id
LEFT JOIN item_value v
    ON v.seller_id = d.seller_id
   AND v.order_purchase_timestamp >= d.won_date
   AND v.order_purchase_timestamp < d.won_date + INTERVAL '90 days'
GROUP BY
    d.mql_id, d.seller_id, d.origin, d.lead_type,
    d.business_segment, d.business_type, d.won_month,
    d.first_contact_date, d.won_date, d.close_days,
    b.data_end, s.seller_id;