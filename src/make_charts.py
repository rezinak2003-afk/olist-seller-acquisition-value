"""Generate report-ready charts from regenerated, audited processed outputs."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from .config import OUT_DIR, ROOT

CHART_DIR = ROOT/"reports"/"charts"


def _save_bar(df, x, y, filename, title, xlabel, ylabel=""):
    if df.empty:
        return
    ordered = df.sort_values(y, ascending=True)
    ax = ordered.plot(kind="barh", x=x, y=y, legend=False, figsize=(10, 6), title=title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(CHART_DIR/filename, dpi=180)
    plt.close()


def run():
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    funnel = pd.read_csv(OUT_DIR/"acquisition_funnel.csv")
    channel = pd.read_csv(OUT_DIR/"channel_90d_summary.csv")
    if not funnel.empty:
        _save_bar(funnel, "origin", "qualified_leads", "qualified_leads_by_origin.png",
                  "Qualified leads by recorded origin", "Distinct qualified leads")
        _save_bar(funnel, "origin", "lead_to_deal_conversion_pct", "conversion_rate_by_origin.png",
                  "Lead-to-deal conversion by origin", "Conversion rate (%)")
    if not channel.empty:
        _save_bar(channel, "origin", "median_gmv_90d", "median_90d_gmv_by_origin.png",
                  "Median delivered 90-day GMV by origin (linked mature sellers)", "Median GMV (BRL)")
        _save_bar(channel, "origin", "marketplace_linkage_rate_pct", "seller_linkage_rate_by_origin.png",
                  "Seller linkage coverage by origin (all mature deals)", "Linkage rate (%)")

        # Forest plot: retain n in labels and explicitly identify small samples.
        c = channel.copy().sort_values("activation_rate_pct", na_position="last").reset_index(drop=True)
        fig, ax = plt.subplots(figsize=(10, 7))
        positions = list(range(len(c)))
        for i, row in c.iterrows():
            n = int(row.linked_mature_seller_deals)
            label = f"{row.origin} (n={n})"
            if n < 20:
                ax.text(2, i, f"{label} — insufficient data", va="center", fontsize=9, color="dimgray")
            else:
                rate = float(row.activation_rate_pct)
                low = float(row.activation_ci_95_low_pct)
                high = float(row.activation_ci_95_high_pct)
                ax.errorbar(rate, i, xerr=[[rate-low], [high-rate]], fmt="o", capsize=3, color="#176B87")
                ax.text(min(high+1.2, 97), i, f"{label}", va="center", fontsize=9)
        ax.set_yticks([])
        ax.set_xlim(0, 100)
        ax.set_xlabel("Purchase-window delivered activation (%)")
        ax.set_title("Origin activation with Wilson 95% confidence intervals")
        ax.grid(axis="x", alpha=.25)
        fig.tight_layout()
        fig.savefig(CHART_DIR/"activation_forest_by_origin.png", dpi=180)
        plt.close(fig)

    cumulative_path = OUT_DIR/"cumulative_activation_by_day.csv"
    if cumulative_path.exists():
        cumulative = pd.read_csv(cumulative_path)
        fig, ax = plt.subplots(figsize=(10, 6))
        for origin, group in cumulative.groupby("origin"):
            if int(group.linked_mature_denominator.max()) >= 20:
                ax.plot(group.day_since_win, group.cumulative_activation_pct, label=origin)
        ax.set_xlabel("Days since seller win")
        ax.set_ylabel("Cumulative activation (%)")
        ax.set_title("Cumulative delivered-order activation by purchase day")
        ax.legend(title="Recorded origin", fontsize=8)
        ax.grid(alpha=.25)
        fig.tight_layout()
        fig.savefig(CHART_DIR/"cumulative_activation_by_day.png", dpi=180)
        plt.close(fig)

    lorenz_path = OUT_DIR/"gmv_lorenz_curve.csv"
    if lorenz_path.exists():
        lorenz = pd.read_csv(lorenz_path)
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.plot(lorenz.seller_share_pct, lorenz.cumulative_gmv_share_pct, label="Delivered GMV")
        ax.plot([0, 100], [0, 100], linestyle="--", label="Perfect equality")
        ax.set_xlabel("Cumulative share of linked mature sellers (%)")
        ax.set_ylabel("Cumulative share of delivered GMV (%)")
        ax.set_title("Lorenz curve — delivered 90-day GMV")
        ax.legend()
        ax.grid(alpha=.25)
        fig.tight_layout()
        fig.savefig(CHART_DIR/"gmv_lorenz_curve.png", dpi=180)
        plt.close(fig)

    print(f"Charts written to {CHART_DIR}")


if __name__ == "__main__":
    run()
