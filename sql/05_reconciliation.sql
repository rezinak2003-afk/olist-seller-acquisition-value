-- SQL-side source controls and mart aggregates for reconciliation with Python.
SELECT 'qualified_leads' AS metric, COUNT(DISTINCT mql_id)::NUMERIC AS value FROM raw.marketing_qualified_leads
UNION ALL SELECT 'closed_deals', COUNT(DISTINCT mql_id)::NUMERIC FROM raw.closed_deals
UNION ALL SELECT 'orders', COUNT(DISTINCT order_id)::NUMERIC FROM raw.orders
UNION ALL SELECT 'order_items', COUNT(*)::NUMERIC FROM raw.order_items
UNION ALL SELECT 'item_price_sum', SUM(price)::NUMERIC FROM raw.order_items
UNION ALL SELECT 'freight_sum', SUM(freight_value)::NUMERIC FROM raw.order_items
UNION ALL SELECT 'seller_mart_rows', COUNT(*)::NUMERIC FROM mart.seller_90d_value
UNION ALL SELECT 'data_end_epoch_seconds', EXTRACT(EPOCH FROM MAX(data_end))::NUMERIC FROM mart.seller_90d_value
UNION ALL SELECT 'mature_deals', COUNT(*)::NUMERIC FROM mart.seller_90d_value WHERE mature_90d
UNION ALL SELECT 'linked_mature_deals', COUNT(*)::NUMERIC FROM mart.seller_90d_value WHERE mature_90d AND seller_linked_to_order_items
UNION ALL SELECT 'activated_linked_mature_deals', COUNT(*)::NUMERIC FROM mart.seller_90d_value WHERE mature_90d AND seller_linked_to_order_items AND activated_90d
UNION ALL SELECT 'strict_activated_linked_mature_deals', COUNT(*)::NUMERIC FROM mart.seller_90d_value WHERE mature_90d AND seller_linked_to_order_items AND activated_delivered_within_90d
UNION ALL SELECT 'delivered_gmv_90d', SUM(gmv_90d_delivered_only)::NUMERIC FROM mart.seller_90d_value WHERE mature_90d AND seller_linked_to_order_items
UNION ALL SELECT 'strict_delivered_gmv_90d', SUM(gmv_90d_delivered_within_90d)::NUMERIC FROM mart.seller_90d_value WHERE mature_90d AND seller_linked_to_order_items
UNION ALL SELECT 'close_days_sum', SUM(close_days)::NUMERIC FROM mart.seller_90d_value
UNION ALL SELECT 'close_days_n', COUNT(close_days)::NUMERIC FROM mart.seller_90d_value;
