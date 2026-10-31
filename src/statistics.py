"""Statistical utilities for acquisition and seller-value analysis.

Primary family: all pairwise Fisher exact tests across recorded origins with
n >= 20, Holm-adjusted within activation definition. CIs for risk differences
use Newcombe's independent-Wilson method. Omnibus origin comparisons use a
fixed-margin Monte Carlo chi-square test to avoid relying on asymptotic expected
cell counts below five.
"""
from __future__ import annotations
from itertools import combinations
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, kruskal, random_table
from statsmodels.stats.multitest import multipletests


def wilson_interval(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion; returns proportions."""
    if n <= 0:
        return (float("nan"), float("nan"))
    from scipy.stats import norm
    z = float(norm.ppf(1 - alpha / 2))
    p = successes / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n)) / den
    half = z * np.sqrt((p*(1-p) + z*z/(4*n))/n) / den
    return (max(0.0, float(center-half)), min(1.0, float(center+half)))


def newcombe_difference_ci(x1: int, n1: int, x2: int, n2: int,
                           alpha: float = 0.05) -> tuple[float, float]:
    """Newcombe hybrid-score CI for independent proportion difference p1-p2."""
    if n1 <= 0 or n2 <= 0:
        return (float("nan"), float("nan"))
    p1, p2 = x1/n1, x2/n2
    l1, u1 = wilson_interval(x1, n1, alpha)
    l2, u2 = wilson_interval(x2, n2, alpha)
    diff = p1 - p2
    lower = diff - np.sqrt((p1-l1)**2 + (u2-p2)**2)
    upper = diff + np.sqrt((u1-p1)**2 + (p2-l2)**2)
    return float(max(-1.0, lower)), float(min(1.0, upper))


def bootstrap_stat_ci(values, statistic="mean", reps=5000, seed=42, alpha=0.05):
    """Percentile bootstrap CI for mean or median, with a fixed seed."""
    x = np.asarray(pd.Series(values).dropna(), dtype=float)
    if len(x) == 0:
        return {"n": 0, "estimate": np.nan, "ci_low": np.nan, "ci_high": np.nan}
    fn = np.mean if statistic == "mean" else np.median if statistic == "median" else None
    if fn is None:
        raise ValueError("statistic must be 'mean' or 'median'")
    rng = np.random.default_rng(seed)
    stats = np.empty(reps, dtype=float)
    for i in range(reps):
        stats[i] = fn(rng.choice(x, size=len(x), replace=True))
    return {"n": int(len(x)), "estimate": float(fn(x)),
            "ci_low": float(np.quantile(stats, alpha/2)),
            "ci_high": float(np.quantile(stats, 1-alpha/2))}


def _monte_carlo_chi_square(table: np.ndarray, reps: int = 100_000,
                            seed: int = 42) -> tuple[float, float, float]:
    """Pearson chi-square statistic and fixed-margin Monte Carlo p-value."""
    table = np.asarray(table, dtype=int)
    total = int(table.sum())
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / total
    observed = float(((table-expected)**2/expected).sum())
    sims = random_table.rvs(table.sum(axis=1), table.sum(axis=0),
                           size=reps, random_state=np.random.default_rng(seed))
    sim_stats = ((sims-expected)**2/expected).sum(axis=(1, 2))
    p_value = (int(np.count_nonzero(sim_stats >= observed - 1e-12)) + 1)/(reps+1)
    return observed, float(p_value), float(expected.min())


def channel_omnibus_tests(linked_mature: pd.DataFrame, min_group_n: int = 20,
                          monte_carlo_reps: int = 100_000) -> pd.DataFrame:
    """Pairwise origin tests for both definitions plus origin omnibus tests.

    `activated_90d` is purchase-window activation; `activated_delivered_within_90d`
    is the strict purchase-and-delivery-within-window definition. All origin
    pairs with at least `min_group_n` valid observations are tested.
    """
    rows: list[dict] = []
    definitions = [
        ("purchase_window", "activated_90d"),
        ("strict_within_90d", "activated_delivered_within_90d"),
    ]
    for definition, outcome_col in definitions:
        if outcome_col not in linked_mature.columns:
            d = linked_mature.assign(**{outcome_col: np.nan})
        else:
            d = linked_mature.copy()
        d = d.dropna(subset=["origin", outcome_col]).copy()
        d[outcome_col] = pd.to_numeric(d[outcome_col], errors="coerce")
        d = d.dropna(subset=[outcome_col])
        counts = d.groupby("origin")[outcome_col].size()
        keep = sorted(counts[counts >= min_group_n].index.astype(str).tolist())
        pair_indexes = []
        for first, second in combinations(keep, 2):
            if {first, second} == {"paid_search", "organic_search"}:
                origin_a, origin_b = "paid_search", "organic_search"
            else:
                origin_a, origin_b = first, second
            a = d.loc[d.origin.eq(origin_a), outcome_col].astype(int)
            b = d.loc[d.origin.eq(origin_b), outcome_col].astype(int)
            x1, n1 = int(a.sum()), int(a.size)
            x2, n2 = int(b.sum()), int(b.size)
            table = np.array([[x1, n1-x1], [x2, n2-x2]], dtype=int)
            odds_ratio, p_value = fisher_exact(table, alternative="two-sided")
            ci_low, ci_high = newcombe_difference_ci(x1, n1, x2, n2)
            rows.append({
                "outcome": f"{definition}:{origin_a}_vs_{origin_b}",
                "definition": definition, "test": "Fisher exact (two-sided)",
                "origin_a": origin_a, "origin_b": origin_b,
                "groups_included": f"{origin_a};{origin_b}", "n": n1+n2,
                "successes_a": x1, "n_a": n1, "rate_a_pct": 100*x1/n1,
                "successes_b": x2, "n_b": n2, "rate_b_pct": 100*x2/n2,
                "risk_difference_a_minus_b_pp": 100*(x1/n1-x2/n2),
                "risk_difference_ci_95_low_pp": 100*ci_low,
                "risk_difference_ci_95_high_pp": 100*ci_high,
                "odds_ratio": float(odds_ratio), "p_value": float(p_value),
                "p_value_holm_adjusted": np.nan,
                "primary_comparison": {origin_a, origin_b} == {"paid_search", "organic_search"},
                "minimum_expected_cell": np.nan,
                "interpretation": "Origin contrast among linked mature deals; observational association, not causal. Holm adjustment covers all eligible pairs for this definition.",
            })
            pair_indexes.append(len(rows)-1)
        if pair_indexes:
            adjusted = multipletests([rows[i]["p_value"] for i in pair_indexes], method="holm")[1]
            for i, p_adj in zip(pair_indexes, adjusted):
                rows[i]["p_value_holm_adjusted"] = float(p_adj)

        if len(keep) >= 2:
            tab = pd.crosstab(d.loc[d.origin.astype(str).isin(keep), "origin"],
                              d.loc[d.origin.astype(str).isin(keep), outcome_col].astype(int))
            tab = tab.reindex(index=keep, columns=[0, 1], fill_value=0).to_numpy().T
            chi2, p_mc, min_expected = _monte_carlo_chi_square(tab, reps=monte_carlo_reps)
            rows.append({
                "outcome": f"{definition}:origin_omnibus", "definition": definition,
                "test": f"Monte Carlo Pearson chi-square, fixed margins ({monte_carlo_reps:,} replicates)",
                "origin_a": "", "origin_b": "", "groups_included": ";".join(keep),
                "n": int(tab.sum()), "successes_a": np.nan, "n_a": np.nan,
                "rate_a_pct": np.nan, "successes_b": np.nan, "n_b": np.nan,
                "rate_b_pct": np.nan, "risk_difference_a_minus_b_pp": np.nan,
                "risk_difference_ci_95_low_pp": np.nan, "risk_difference_ci_95_high_pp": np.nan,
                "odds_ratio": np.nan, "p_value": p_mc, "p_value_holm_adjusted": np.nan,
                "primary_comparison": False, "statistic": chi2,
                "minimum_expected_cell": min_expected,
                "interpretation": f"Omnibus test over {len(keep)} recorded origins with n >= {min_group_n}; fixed-margin Monte Carlo avoids relying on low expected counts.",
            })
        else:
            rows.append({
                "outcome": f"{definition}:origin_omnibus", "definition": definition,
                "test": "Not run", "origin_a": "", "origin_b": "",
                "groups_included": ";".join(keep), "n": int(len(d)),
                "p_value": np.nan, "p_value_holm_adjusted": np.nan,
                "primary_comparison": False,
                "interpretation": f"Fewer than two origins met min_group_n={min_group_n}.",
            })

    # Keep the GMV comparison as an exploratory distributional check.
    if {"origin", "gmv_90d_delivered_only"}.issubset(linked_mature.columns):
        gd = linked_mature.dropna(subset=["origin", "gmv_90d_delivered_only"])
        gcounts = gd.groupby("origin").size()
        gkeep = sorted(gcounts[gcounts >= min_group_n].index.astype(str).tolist())
        if len(gkeep) >= 2:
            samples = [gd.loc[gd.origin.eq(o), "gmv_90d_delivered_only"].to_numpy(float) for o in gkeep]
            h, p_kw = kruskal(*samples, nan_policy="omit")
            n = int(sum(len(x) for x in samples)); k = len(samples)
            eps2 = max(0.0, float((h-k+1)/(n-k))) if n > k else np.nan
            rows.append({"outcome":"delivered_90d_gmv_across_origins", "definition":"purchase_window",
                         "test":"Kruskal-Wallis H", "groups_included":";".join(gkeep), "n":n,
                         "statistic":float(h), "degrees_of_freedom":k-1, "p_value":float(p_kw),
                         "p_value_holm_adjusted":np.nan, "effect_size":eps2,
                         "effect_size_name":"epsilon-squared",
                         "interpretation":"Exploratory rank-distribution comparison among linked mature sellers; not causal."})
    return pd.DataFrame(rows)


def bootstrap_mean_ci(values, reps=2000, seed=42, alpha=.05):
    """Backward-compatible alias retained for notebook references."""
    x = bootstrap_stat_ci(values, "mean", reps, seed, alpha)
    return {"n":x["n"], "mean":x["estimate"], "ci_low":x["ci_low"], "ci_high":x["ci_high"]}
