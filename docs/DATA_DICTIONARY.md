# Data dictionary

This dictionary covers the source fields used by the analysis and derived fields in `data/processed/seller_90d_value.csv`.

## Marketing qualified leads (`olist_marketing_qualified_leads_dataset.csv`)

| Field | Meaning | Expected grain / handling |
|---|---|---|
| `mql_id` | Marketing qualified lead identifier | One row per lead; uniqueness validated |
| `first_contact_date` | First recorded contact date | Parsed as a date; used for close-duration QA |
| `origin` | Recorded lead source/origin | Lead-level categorical field; source blank/null is normalized to `(missing)`; literal `unknown` remains separate |

## Closed deals (`olist_closed_deals_dataset.csv`)

| Field | Meaning | Expected grain / handling |
|---|---|---|
| `mql_id` | Link to marketing lead | One row per closed deal in this snapshot; checked against lead IDs |
| `seller_id` | Seller identifier associated with the closed deal | Used to link to marketplace order-item rows; linkage is incomplete |
| `won_date` | Timestamp the seller deal was won | Starts the seller's post-win 90-day observation window |
| `business_segment`, `lead_type`, `business_type` | Deal descriptors | Used for descriptive segmentation and adjusted association models, not causal inference |

## Orders (`olist_orders_dataset.csv`)

| Field | Meaning | Expected grain / handling |
|---|---|---|
| `order_id` | Order identifier | One row per order; uniqueness validated |
| `order_purchase_timestamp` | Order purchase timestamp | Parsed year-first; determines purchase-window membership and daily-volume cutoff |
| `order_status` | Recorded order state | `delivered` is the primary fulfilled status used here |
| `order_delivered_customer_date` | Timestamp when the order was delivered to the customer | Required for the strict delivery-within-90-days definition; missing is not inferred |

## Order items (`olist_order_items_dataset.csv`)

| Field | Meaning | Expected grain / handling |
|---|---|---|
| `order_id`, `order_item_id` | Composite item-line identifier | `(order_id, order_item_id)` is the validated primary key |
| `seller_id` | Seller supplying the item | Establishes seller linkage and attributes item GMV |
| `price` | Item merchandise price, BRL | Summed as a GMV proxy; excludes freight and is not seller profit or platform revenue |
| `freight_value` | Item freight charge, BRL | Kept separate from merchandise GMV |

## Derived fields in `seller_90d_value.csv`

| Field | Meaning | NULL / denominator rule |
|---|---|---|
| `lead_type`, `business_segment`, `business_type` | Deal descriptors copied from closed deals | Slicers and adjusted model covariates; missing values normalized to `(missing)` |
| `won_month` | Calendar month of `won_date` (`YYYY-MM`) | Cohort dimension for reporting |
| `window_start_inclusive` | `won_date` | Inclusive start |
| `window_end_exclusive` | `won_date + 90 days` | Exclusive end; window is `[won_date, won_date + 90 days)` |
| `data_end` | Day after the last purchase date with at least 50 orders | Exclusive snapshot boundary; same value is repeated for every seller row |
| `mature_90d` | Whether `window_end_exclusive <= data_end` | Immature deals excluded from 90-day comparisons |
| `seller_linked_to_order_items` | Seller ID appears in at least one raw order-item row | False means no seller/order linkage was observed in this snapshot |
| `orders_90d` | Distinct orders purchased in the first 90 days after win | NULL for unlinked sellers; zero for linked sellers with no qualifying order |
| `delivered_orders_90d` | Distinct qualifying purchase-window orders with `order_status='delivered'` | NULL for unlinked sellers |
| `orders_delivered_within_90d` | Distinct orders both purchased and delivered inside the 90-day window | NULL for unlinked sellers |
| `items_90d` | Item-line count in the purchase window | NULL for unlinked sellers |
| `activated_90d` | At least one order purchased in the 90-day window and marked `delivered` in the snapshot | NULL for unlinked sellers; mature linked deals are denominator |
| `activated_90d_any_status` | At least one order purchased in the window, irrespective of status | NULL for unlinked sellers; sensitivity only |
| `activated_delivered_within_90d` | At least one order both purchased and customer-delivered inside the 90-day window | NULL for unlinked sellers; strict sensitivity |
| `gmv_90d_all_statuses` | Sum of item `price` across all status rows purchased in the 90-day window | NULL for unlinked sellers; sensitivity only |
| `gmv_90d_delivered_only` | Sum of item `price` for delivered-status orders purchased in the 90-day window | NULL for unlinked sellers; delivery may occur after day 90 |
| `gmv_90d_delivered_within_90d` | Sum of item `price` for orders both purchased and delivered inside the 90-day window | NULL for unlinked sellers |
| `gmv_90d_non_delivered_proxy` | All-status purchase-window item value minus delivered-status item value | NULL for unlinked sellers; not a formal loss/returns measure |
| `freight_90d_all_statuses` | Sum of `freight_value` for all item rows purchased in the window | NULL for unlinked sellers; reported separately from GMV |

## Interpretation and limitations
- A linked seller with no qualifying order has a known zero for that period; an unlinked seller has an unknown outcome and remains NULL.
- The primary activation KPI is conditional on seller linkage and complete 90-day maturity. It does not estimate activation for every acquired seller.
- The seller marketing funnel and marketplace transaction data are distinct datasets; missing seller-ID linkage is not proof that the seller never traded.
- GMV is item `price` in BRL only. It excludes freight, refunds, operating costs and marketplace economics.
