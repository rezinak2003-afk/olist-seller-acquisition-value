import pandas as pd
from src.statistics import bootstrap_mean_ci

def test_90_day_interval_includes_start_excludes_end():
    won=pd.Timestamp("2018-01-01")
    end=won+pd.Timedelta(days=90)
    in_window=lambda event: won <= event < end
    assert in_window(won)
    assert in_window(end-pd.Timedelta(seconds=1))
    assert not in_window(end)

def test_bootstrap_ci_contains_sample_mean_for_constant_values():
    result=bootstrap_mean_ci([5,5,5,5], reps=200, seed=1)
    assert result["mean"]==5
    assert result["ci_low"]==5
    assert result["ci_high"]==5


def test_bootstrap_returns_empty_result_for_no_observations():
    result=bootstrap_mean_ci([float("nan"), float("nan")], reps=200, seed=1)
    assert result["n"]==0
    assert pd.isna(result["mean"])
