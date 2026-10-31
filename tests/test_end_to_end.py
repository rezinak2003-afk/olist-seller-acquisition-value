"""Integration test of pipeline.run() using the committed, small synthetic snapshot."""
from pathlib import Path
import shutil
import pandas as pd
import pytest

from src import pipeline

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "synthetic_olist"


@pytest.mark.integration
def test_pipeline_run_rebuilds_all_primary_outputs(monkeypatch, tmp_path):
    raw = tmp_path / "raw"
    out = tmp_path / "processed"
    ref = tmp_path / "reference"
    shutil.copytree(FIXTURE, raw)
    ref.mkdir()
    monkeypatch.setattr(pipeline, "RAW_DIR", raw)
    monkeypatch.setattr(pipeline, "REFERENCE_DIR", ref)
    monkeypatch.setattr(pipeline, "OUT_DIR", out)
    monkeypatch.setattr(pipeline, "build_workbook", lambda *_args, **_kwargs: None)
    from src.statistics import channel_omnibus_tests as stats_tests
    monkeypatch.setattr(pipeline, "channel_omnibus_tests",
                        lambda df, **kwargs: stats_tests(df, min_group_n=kwargs.get("min_group_n", 20),
                                                         monte_carlo_reps=1000))

    pipeline.run()
    required = ["acquisition_funnel.csv", "seller_90d_value.csv", "channel_90d_summary.csv",
                "validation_summary.csv", "maturity_sensitivity.csv", "pairwise_comparisons.csv",
                "linkage_diagnostics.csv", "activation_logistic_regression.csv"]
    assert all((out/name).exists() for name in required)
    seller = pd.read_csv(out/"seller_90d_value.csv")
    validation = pd.read_csv(out/"validation_summary.csv").set_index("check")
    assert int(seller.mature_90d.astype(bool).sum()) == len(seller)
    assert int(validation.loc["mature_windows_ending_after_data_end", "value"]) == 0
    assert pd.to_datetime(seller.data_end).nunique() == 1
