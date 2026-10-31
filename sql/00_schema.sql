-- PostgreSQL 16 schema. This is the single source of truth for table DDL.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS raw.marketing_qualified_leads (
  mql_id TEXT PRIMARY KEY,
  first_contact_date DATE,
  landing_page_id TEXT,
  origin TEXT
);
CREATE TABLE IF NOT EXISTS raw.closed_deals (
  mql_id TEXT PRIMARY KEY,
  seller_id TEXT,
  sdr_id TEXT,
  sr_id TEXT,
  won_date TIMESTAMP,
  business_segment TEXT,
  lead_type TEXT,
  lead_behaviour_profile TEXT,
  has_company TEXT,
  has_gtin TEXT,
  average_stock TEXT,
  business_type TEXT,
  declared_product_catalog_size NUMERIC,
  declared_monthly_revenue NUMERIC
);
CREATE TABLE IF NOT EXISTS raw.orders (
  order_id TEXT PRIMARY KEY,
  customer_id TEXT,
  order_status TEXT,
  order_purchase_timestamp TIMESTAMP,
  order_approved_at TIMESTAMP,
  order_delivered_carrier_date TIMESTAMP,
  order_delivered_customer_date TIMESTAMP,
  order_estimated_delivery_date TIMESTAMP
);
CREATE TABLE IF NOT EXISTS raw.order_items (
  order_id TEXT NOT NULL,
  order_item_id INTEGER NOT NULL,
  product_id TEXT,
  seller_id TEXT,
  shipping_limit_date TIMESTAMP,
  price NUMERIC,
  freight_value NUMERIC,
  PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS mart.seller_90d_value (
  mql_id TEXT PRIMARY KEY,
  seller_id TEXT,
  origin TEXT,
  lead_type TEXT,
  business_segment TEXT,
  business_type TEXT,
  won_month TEXT,
  first_contact_date DATE,
  won_date TIMESTAMP,
  close_days INTEGER,
  window_start_inclusive TIMESTAMP,
  window_end_exclusive TIMESTAMP,
  data_end TIMESTAMP,
  mature_90d BOOLEAN,
  seller_linked_to_order_items BOOLEAN,
  orders_90d INTEGER,
  delivered_orders_90d INTEGER,
  items_90d INTEGER,
  orders_delivered_within_90d INTEGER,
  activated_90d BOOLEAN,
  activated_90d_any_status BOOLEAN,
  activated_delivered_within_90d BOOLEAN,
  gmv_90d_all_statuses NUMERIC,
  gmv_90d_delivered_only NUMERIC,
  gmv_90d_delivered_within_90d NUMERIC,
  gmv_90d_non_delivered_proxy NUMERIC,
  freight_90d_all_statuses NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_order_items_seller_id ON raw.order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_timestamp ON raw.orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_closed_deals_seller_id ON raw.closed_deals(seller_id);
CREATE INDEX IF NOT EXISTS idx_seller_90d_origin ON mart.seller_90d_value(origin);
CREATE INDEX IF NOT EXISTS idx_seller_90d_maturity ON mart.seller_90d_value(mature_90d);
