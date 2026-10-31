-- Fail-fast data contract checks. These assertions execute after raw loads and mart build.
DO $$
DECLARE n BIGINT;
BEGIN
  SELECT COUNT(*) INTO n FROM (SELECT mql_id FROM raw.marketing_qualified_leads GROUP BY mql_id HAVING COUNT(*)>1) q;
  IF n>0 THEN RAISE EXCEPTION 'Duplicate mql_id values in raw.marketing_qualified_leads: %', n; END IF;
  SELECT COUNT(*) INTO n FROM (SELECT mql_id FROM raw.closed_deals GROUP BY mql_id HAVING COUNT(*)>1) q;
  IF n>0 THEN RAISE EXCEPTION 'Duplicate mql_id values in raw.closed_deals: %', n; END IF;
  SELECT COUNT(*) INTO n FROM (SELECT order_id FROM raw.orders GROUP BY order_id HAVING COUNT(*)>1) q;
  IF n>0 THEN RAISE EXCEPTION 'Duplicate order_id values in raw.orders: %', n; END IF;
  SELECT COUNT(*) INTO n FROM raw.closed_deals d LEFT JOIN raw.marketing_qualified_leads l USING(mql_id) WHERE l.mql_id IS NULL;
  IF n>0 THEN RAISE EXCEPTION 'Closed-deal rows without matching qualified lead: %', n; END IF;
  SELECT COUNT(*) INTO n FROM raw.order_items i LEFT JOIN raw.orders o USING(order_id) WHERE o.order_id IS NULL;
  IF n>0 THEN RAISE EXCEPTION 'Order-item rows without matching order: %', n; END IF;
  SELECT COUNT(*) INTO n FROM (SELECT mql_id FROM mart.seller_90d_value GROUP BY mql_id HAVING COUNT(*)>1) q;
  IF n>0 THEN RAISE EXCEPTION 'Duplicate mql_id values in seller 90-day mart: %', n; END IF;
  SELECT COUNT(*) INTO n FROM mart.seller_90d_value WHERE NOT seller_linked_to_order_items
       AND (gmv_90d_delivered_only IS NOT NULL OR activated_90d IS NOT NULL);
  IF n>0 THEN RAISE EXCEPTION 'Unlinked sellers must retain NULL marketplace outcomes: %', n; END IF;
  SELECT COUNT(*) INTO n FROM mart.seller_90d_value WHERE seller_linked_to_order_items
       AND (gmv_90d_delivered_only IS NULL OR activated_90d IS NULL);
  IF n>0 THEN RAISE EXCEPTION 'Linked sellers must have observed numeric/boolean outcomes: %', n; END IF;
  SELECT COUNT(*) INTO n FROM mart.seller_90d_value WHERE gmv_90d_delivered_within_90d > gmv_90d_delivered_only + 0.005;
  IF n>0 THEN RAISE EXCEPTION 'Within-90-day delivered GMV exceeds purchase-window delivered GMV: %', n; END IF;
END $$;
