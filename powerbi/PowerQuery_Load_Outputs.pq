// Power Query M templates. Create one query per named block in Power BI Desktop.
// Define a text parameter ProjectRoot pointing to the project folder that contains README.md.
// Forward slashes avoid the old Windows-only backslash paths.

// Query: Acquisition_Funnel
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/acquisition_funnel.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"origin", type text}, {"qualified_leads", Int64.Type}, {"closed_leads", Int64.Type}, {"lead_to_deal_conversion_pct", type number}, {"conversion_ci_95_low_pct", type number}, {"conversion_ci_95_high_pct", type number}, {"not_closed_leads", Int64.Type}})
in
    Types

// Query: Seller_90d_Value
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/seller_90d_value.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"mql_id", type text}, {"seller_id", type text}, {"origin", type text}, {"lead_type", type text}, {"business_segment", type text}, {"business_type", type text}, {"won_month", type text}, {"first_contact_date", type date}, {"won_date", type datetime}, {"window_start_inclusive", type datetime}, {"window_end_exclusive", type datetime}, {"data_end", type date}, {"close_days", type number}, {"mature_90d", type logical}, {"seller_linked_to_order_items", type logical}, {"orders_90d", Int64.Type}, {"delivered_orders_90d", Int64.Type}, {"orders_delivered_within_90d", Int64.Type}, {"items_90d", Int64.Type}, {"activated_90d", type logical}, {"activated_90d_any_status", type logical}, {"activated_delivered_within_90d", type logical}, {"gmv_90d_all_statuses", Currency.Type}, {"gmv_90d_delivered_only", Currency.Type}, {"gmv_90d_delivered_within_90d", Currency.Type}, {"gmv_90d_non_delivered_proxy", Currency.Type}, {"freight_90d_all_statuses", Currency.Type}}),
    AddWonDateDate = if Table.HasColumns(Types, "won_date_date") then Types else Table.AddColumn(Types, "won_date_date", each Date.From([won_date]), type date)
in
    AddWonDateDate

// Query: Channel_Summary
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/channel_90d_summary.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"origin", type text}, {"mature_seller_deals", Int64.Type}, {"linked_mature_seller_deals", Int64.Type}, {"unlinked_mature_seller_deals", Int64.Type}, {"marketplace_linkage_rate_pct", type number}, {"activated_sellers_90d", Int64.Type}, {"non_activated_linked_sellers_90d", Int64.Type}, {"activation_rate_pct", type number}, {"activation_ci_95_low_pct", type number}, {"activation_ci_95_high_pct", type number}, {"activated_delivered_within_90d", Int64.Type}, {"delivery_within_90d_rate_pct", type number}, {"delivery_within_90d_ci_95_low_pct", type number}, {"delivery_within_90d_ci_95_high_pct", type number}, {"median_gmv_90d", Currency.Type}, {"mean_gmv_90d", Currency.Type}, {"p90_gmv_90d", Currency.Type}, {"total_gmv_90d", Currency.Type}, {"total_gmv_delivered_within_90d", Currency.Type}, {"mean_gmv_delivered_within_90d", Currency.Type}, {"median_close_days_all_mature_deals", type number}})
in
    Types

// Query: Validation_Summary
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/validation_summary.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"check", type text}, {"value", type text}, {"detail", type text}})
in
    Types

// Query: Pairwise_Comparisons
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/pairwise_comparisons.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"definition", type text}, {"origin_a", type text}, {"origin_b", type text}, {"n", Int64.Type}, {"rate_a_pct", type number}, {"rate_b_pct", type number}, {"risk_difference_a_minus_b_pp", type number}, {"risk_difference_ci_95_low_pp", type number}, {"risk_difference_ci_95_high_pp", type number}, {"p_value", type number}, {"p_value_holm_adjusted", type number}, {"primary_comparison", type logical}})
in
    Types

// Query: Inferential_Tests
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/inferential_tests.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"outcome", type text}, {"definition", type text}, {"test", type text}, {"groups_included", type text}, {"n", Int64.Type}, {"statistic", type number}, {"degrees_of_freedom", Int64.Type}, {"p_value", type number}, {"effect_size", type number}, {"effect_size_name", type text}, {"minimum_expected_cell", type number}, {"interpretation", type text}})
in
    Types

// Query: Statistics_Summary
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/statistics_summary.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"metric", type text}, {"n", Int64.Type}, {"successes", type number}, {"estimate", type number}, {"ci_95_low", type number}, {"ci_95_high", type number}, {"method", type text}})
in
    Types

// Query: Linkage_Diagnostics
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/linkage_diagnostics.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"dimension", type text}, {"group_value", type text}, {"mature_deals", Int64.Type}, {"linked_deals", Int64.Type}, {"unlinked_deals", Int64.Type}, {"linkage_rate_pct", type number}})
in
    Types

// Query: IPW_Activation
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/ipw_activation_by_origin.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"origin", type text}, {"linked_mature_n", Int64.Type}, {"observed_activated_n", Int64.Type}, {"observed_activation_pct", type number}, {"ipw_activation_pct", type number}, {"ipw_effective_sample_size", type number}, {"mean_stabilized_ipw", type number}, {"ipw_99pct_cap", type number}})
in
    Types

// Query: Activation_Logistic_Regression
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/activation_logistic_regression.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"term", type text}, {"odds_ratio", type number}, {"ci_95_low", type number}, {"ci_95_high", type number}, {"p_value", type number}, {"n", Int64.Type}, {"status", type text}, {"reference_levels", type text}})
in
    Types

// Query: Window_Sensitivity
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/window_sensitivity.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"window_days", Int64.Type}, {"origin", type text}, {"mature_deals", Int64.Type}, {"linked_mature_deals", Int64.Type}, {"activated_linked_deals", Int64.Type}, {"activation_pct", type number}})
in
    Types

// Query: Conversion_By_Lead_Type
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/conversion_by_lead_type.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Headers

// Query: Conversion_By_Business_Segment
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/conversion_by_business_segment.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Headers

// Query: Median_Days_To_Close
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/median_days_to_close_by_origin.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Headers

// Query: GMV_Concentration
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/gmv_concentration.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Headers

// Query: GMV_Lorenz_Curve
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/gmv_lorenz_curve.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Headers

// Query: GMV_And_Payment_Checks
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/gmv_and_payment_checks.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Headers

// Query: Cumulative_Activation_By_Day
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/cumulative_activation_by_day.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"origin", type text}, {"day_since_win", Int64.Type}, {"linked_mature_denominator", Int64.Type}, {"cumulative_activated", Int64.Type}, {"cumulative_activation_pct", type number}})
in
    Types

// Query: Maturity_Sensitivity
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/maturity_sensitivity.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {{"min_orders_per_day", Int64.Type}, {"data_end_exclusive", type date}, {"mature_90d_deals", Int64.Type}, {"rule", type text}})
in
    Types

// Query: Source_Manifest
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/source_manifest.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Headers
