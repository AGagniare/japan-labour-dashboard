"""Tests for data/process.py — all inputs are synthetic DataFrames."""
from __future__ import annotations

import pandas as pd
import pytest

from data.process import (
    process_job_ratio,
    process_unemployment,
    compute_kpis,
)


def _make_job_df() -> pd.DataFrame:
    """Synthetic raw e-Stat job ratio data (as parsed by fetch._parse_estat_response)."""
    return pd.DataFrame({
        "都道府県": ["全国", "全国", "東京都", "全国"],
        "時間軸(月次)": ["2024年1月", "2024年2月", "2024年1月", "2024年3月"],
        "産業": ["合計", "合計", "合計", "情報通信業"],
        "value": [1.27, 1.30, 1.85, 2.40],
    })


def _make_unemp_df() -> pd.DataFrame:
    """Synthetic raw e-Stat unemployment data."""
    return pd.DataFrame({
        "時間軸(月次)": ["2024年1月", "2024年2月", "2024年3月"],
        "表章項目": ["完全失業率", "完全失業率", "完全失業率"],
        "value": [2.4, 2.5, 2.3],
    })


def test_process_job_ratio_returns_required_columns():
    df = process_job_ratio(_make_job_df())
    assert set(["date", "area", "industry", "ratio"]).issubset(df.columns)


def test_process_job_ratio_parses_dates():
    df = process_job_ratio(_make_job_df())
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert df["date"].dt.year.isin([2024]).all()


def test_process_job_ratio_maps_prefecture_names():
    df = process_job_ratio(_make_job_df())
    assert "National" in df["area"].values
    assert "Tokyo" in df["area"].values


def test_process_job_ratio_drops_nan_values():
    raw = _make_job_df()
    raw.loc[0, "value"] = None
    df = process_job_ratio(raw)
    assert df["ratio"].isna().sum() == 0


def test_process_unemployment_returns_required_columns():
    df = process_unemployment(_make_unemp_df())
    assert "date" in df.columns
    assert "unemployment_rate" in df.columns


def test_process_unemployment_sorted_by_date():
    df = process_unemployment(_make_unemp_df())
    assert list(df["date"]) == sorted(df["date"].tolist())


def test_compute_kpis_national_ratio():
    job_df = process_job_ratio(_make_job_df())
    unemp_df = process_unemployment(_make_unemp_df())
    kpis = compute_kpis(job_df, unemp_df)
    assert "job_ratio_latest" in kpis
    assert isinstance(kpis["job_ratio_latest"], float)


def test_compute_kpis_delta_is_difference():
    job_df = process_job_ratio(_make_job_df())
    unemp_df = process_unemployment(_make_unemp_df())
    kpis = compute_kpis(job_df, unemp_df)
    # Latest national is 1.30 (Feb), prior is 1.27 (Jan) → delta ≈ 0.03
    assert abs(kpis["job_ratio_delta"] - 0.03) < 0.01


def test_compute_kpis_unemployment_latest():
    job_df = process_job_ratio(_make_job_df())
    unemp_df = process_unemployment(_make_unemp_df())
    kpis = compute_kpis(job_df, unemp_df)
    assert kpis["unemployment_latest"] == pytest.approx(2.3)


def test_compute_kpis_it_ratio_detected():
    job_df = process_job_ratio(_make_job_df())
    unemp_df = process_unemployment(_make_unemp_df())
    kpis = compute_kpis(job_df, unemp_df)
    # 情報通信業 row exists → it_ratio_latest should not be None
    assert kpis["it_ratio_latest"] is not None
