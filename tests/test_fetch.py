"""Tests for data/fetch.py — all API calls are mocked."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data.fetch import (
    _cache_path,
    _is_cache_fresh,
    _parse_estat_response,
    get_dataset,
    load_from_cache,
    STATS_JOB_RATIO,
)

# Minimal valid e-Stat response fixture
ESTAT_RESPONSE = {
    "GET_STATS_DATA": {
        "RESULT": {"STATUS": 0, "ERROR_MSG": "正常に終了しました。", "DATE": "2024-12-01"},
        "STATISTICAL_DATA": {
            "CLASS_INF": {
                "CLASS_OBJ": [
                    {
                        "@id": "area",
                        "@name": "都道府県",
                        "CLASS": [
                            {"@code": "00000", "@name": "全国"},
                            {"@code": "13000", "@name": "東京都"},
                        ],
                    },
                    {
                        "@id": "time",
                        "@name": "時間軸(月次)",
                        "CLASS": [
                            {"@code": "2024010000", "@name": "2024年1月"},
                            {"@code": "2024020000", "@name": "2024年2月"},
                        ],
                    },
                ]
            },
            "DATA_INF": {
                "VALUE": [
                    {"@area": "00000", "@time": "2024010000", "$": "1.27"},
                    {"@area": "13000", "@time": "2024010000", "$": "1.85"},
                    {"@area": "00000", "@time": "2024020000", "$": "1.30"},
                ]
            },
        },
    }
}


def test_parse_estat_response_returns_dataframe():
    df = _parse_estat_response(ESTAT_RESPONSE)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "value" in df.columns
    assert "都道府県" in df.columns
    assert df["value"].tolist() == [1.27, 1.85, 1.30]


def test_parse_estat_response_decodes_codes():
    df = _parse_estat_response(ESTAT_RESPONSE)
    areas = df["都道府県"].tolist()
    assert "全国" in areas
    assert "東京都" in areas


def test_is_cache_fresh_missing_file(tmp_path):
    assert _is_cache_fresh(tmp_path / "missing.csv") is False


def test_is_cache_fresh_old_file(tmp_path):
    import time
    p = tmp_path / "old.csv"
    p.write_text("a,b\n1,2")
    # Backdate modification time by 8 days
    old_time = time.time() - 8 * 86400
    import os
    os.utime(p, (old_time, old_time))
    assert _is_cache_fresh(p) is False


def test_is_cache_fresh_new_file(tmp_path):
    p = tmp_path / "new.csv"
    p.write_text("a,b\n1,2")
    assert _is_cache_fresh(p) is True


def test_load_from_cache_raises_if_absent(tmp_path):
    with patch("data.fetch.CACHE_DIR", tmp_path):
        with pytest.raises(FileNotFoundError):
            load_from_cache("9999999999")


def test_get_dataset_uses_cache_when_fresh(tmp_path):
    """If cache is fresh, get_dataset returns it without calling the API."""
    cache_file = tmp_path / f"{STATS_JOB_RATIO}.csv"
    pd.DataFrame({"a": [1]}).to_csv(cache_file, index=False)

    with patch("data.fetch.CACHE_DIR", tmp_path):
        with patch("data.fetch._is_cache_fresh", return_value=True):
            df, source = get_dataset(STATS_JOB_RATIO, api_key=None)
    assert source == "cache"
    assert isinstance(df, pd.DataFrame)


def test_get_dataset_falls_back_to_stale_cache_on_api_error(tmp_path):
    cache_file = tmp_path / f"{STATS_JOB_RATIO}.csv"
    pd.DataFrame({"a": [1]}).to_csv(cache_file, index=False)

    with patch("data.fetch.CACHE_DIR", tmp_path):
        with patch("data.fetch._is_cache_fresh", return_value=False):
            with patch("data.fetch.fetch_from_api", side_effect=Exception("API down")):
                df, source = get_dataset(STATS_JOB_RATIO, api_key="fake_key")
    assert source == "stale_cache"


def test_get_dataset_raises_when_no_data_available(tmp_path):
    with patch("data.fetch.CACHE_DIR", tmp_path):
        with patch("data.fetch._is_cache_fresh", return_value=False):
            with pytest.raises(RuntimeError, match="No data available"):
                get_dataset(STATS_JOB_RATIO, api_key=None)
