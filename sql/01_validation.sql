-- Key and join-grain checks. Any non-zero orphan/duplicate counts require investigation.
SELECT 'leads_rows' AS check_name, COUNT(*)::TEXT AS check_value FROM raw.marketing_qualified_leads
UNION ALL SELECT 'lead_duplicate_mql_ids', COUNT(*)::TEXT FROM (SELECT mql_id FROM raw.marketing_qualified_leads GROUP BY mql_id HAVING COUNT(*)>1) d
UNION ALL SELECT 'deal_duplicate_mql_ids', COUNT(*)::TEXT FROM (SELECT mql_id FROM raw.closed_deals GROUP BY mql_id HAVING COUNT(*)>1) d
UNION ALL SELECT 'deal_duplicate_seller_ids', COUNT(*)::TEXT FROM (SELECT seller_id FROM raw.closed_deals GROUP BY seller_id HAVING COUNT(*)>1) d
UNION ALL SELECT 'duplicate_order_ids', COUNT(*)::TEXT FROM (SELECT order_id FROM raw.orders GROUP BY order_id HAVING COUNT(*)>1) d
UNION ALL SELECT 'deal_rows_without_matching_lead', COUNT(*)::TEXT FROM raw.closed_deals d LEFT JOIN raw.marketing_qualified_leads l USING (mql_id) WHERE l.mql_id IS NULL
UNION ALL SELECT 'order_items_without_matching_order', COUNT(*)::TEXT FROM raw.order_items i LEFT JOIN raw.orders o USING (order_id) WHERE o.order_id IS NULL;

SELECT order_status, COUNT(DISTINCT order_id) AS orders
FROM raw.orders GROUP BY order_status ORDER BY orders DESC;
