"""e-Stat API client with 7-day CSV caching and graceful fallback."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_TTL_DAYS = 7
ESTAT_BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

STATS_JOB_RATIO = "0000010106"    # 社会・人口統計体系 — annual job-to-applicant ratio by prefecture
STATS_LABOUR_FORCE = "0003005865"  # 労働力調査 — monthly unemployment/employment rates

# Extra filter params passed to the API for each dataset to limit response size
_STATS_EXTRA_PARAMS: dict[str, dict] = {
    "0000010106": {"cdCat01": "F310301"},          # job-to-applicant ratio only
    "0003005865": {"cdTab": "02", "cdCat02": "08", "cdCat03": "0"},  # unemployment rate, total
}


def _cache_path(stats_id: str) -> Path:
    """Return the CSV cache file path for a given stats ID."""
    return CACHE_DIR / f"{stats_id}.csv"


def _is_cache_fresh(path: Path) -> bool:
    """Return True if the file exists and is younger than CACHE_TTL_DAYS."""
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=CACHE_TTL_DAYS)


def _parse_estat_response(data: dict) -> pd.DataFrame:
    """
    Parse an e-Stat getStatsData JSON response into a flat DataFrame.

    The e-Stat API returns classification codes in VALUE records.
    This function builds a code→name lookup from CLASS_OBJ metadata
    and decodes every code field so the DataFrame has human-readable values.
    The '$' field becomes the 'value' column as a float.
    """
    try:
        stat_data = data["GET_STATS_DATA"]["STATISTICAL_DATA"]
    except KeyError as exc:
        raise ValueError("Unexpected e-Stat response structure") from exc

    # Build lookup: dim_key → {code: name}, col_names: dim_key → dim_name
    class_objs = stat_data["CLASS_INF"]["CLASS_OBJ"]
    if isinstance(class_objs, dict):
        class_objs = [class_objs]

    lookups: dict[str, dict[str, str]] = {}
    col_names: dict[str, str] = {}
    for obj in class_objs:
        dim_id = obj["@id"]       # e.g. "tab", "cat01", "area", "time"
        dim_name = obj["@name"]   # e.g. "都道府県"
        key = f"@{dim_id}"
        col_names[key] = dim_name
        classes = obj["CLASS"]
        if isinstance(classes, dict):
            classes = [classes]
        lookups[key] = {c["@code"]: c["@name"] for c in classes}

    values = stat_data["DATA_INF"]["VALUE"]
    if isinstance(values, dict):
        values = [values]

    records = []
    for v in values:
        record: dict = {}
        for key, lookup in lookups.items():
            code = v.get(key, "")
            record[col_names[key]] = lookup.get(code, code)
        raw_val = v.get("$", "")
        try:
            record["value"] = float(raw_val)
        except (ValueError, TypeError):
            record["value"] = None
        records.append(record)

    return pd.DataFrame(records)


def fetch_from_api(stats_id: str, api_key: str, extra_params: dict | None = None) -> pd.DataFrame:
    """
    Fetch a stats dataset directly from the e-Stat API.
    Raises requests.HTTPError or ValueError on failure.
    """
    params = {
        "appId": api_key,
        "statsDataId": stats_id,
        "metaGetFlg": "Y",
        "cntGetFlg": "N",
        "explanationGetFlg": "N",
        "annotationGetFlg": "N",
        "sectionHeaderFlg": "1",
        "replaceSpChars": "0",
        "limit": "100000",
    }
    if extra_params:
        params.update(extra_params)
    resp = requests.get(ESTAT_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    status = (
        data.get("GET_STATS_DATA", {})
            .get("RESULT", {})
            .get("STATUS", -1)
    )
    if status != 0:
        msg = (
            data.get("GET_STATS_DATA", {})
                .get("RESULT", {})
                .get("ERROR_MSG", "Unknown error")
        )
        raise ValueError(f"e-Stat API error (status {status}): {msg}")

    return _parse_estat_response(data)


def load_from_cache(stats_id: str) -> pd.DataFrame:
    """
    Load a dataset from the local CSV cache.
    Raises FileNotFoundError if the cache file does not exist.
    """
    path = _cache_path(stats_id)
    if not path.exists():
        raise FileNotFoundError(f"No cache file found for stats ID {stats_id}")
    return pd.read_csv(path)


def get_dataset(
    stats_id: str,
    api_key: str | None = None,
) -> tuple[pd.DataFrame, str]:
    """
    Return (DataFrame, source) for a given stats ID.

    Resolution order:
      1. Fresh cache (< 7 days old) — returns immediately, no API call
      2. Live API (if api_key provided) — fetches, writes cache, returns
      3. Stale cache (any age) — warns and returns outdated data
      4. RuntimeError — no data at all

    source is one of: 'cache', 'api', 'stale_cache'
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_path(stats_id)

    if _is_cache_fresh(cache_path):
        return pd.read_csv(cache_path), "cache"

    if api_key:
        try:
            extra = _STATS_EXTRA_PARAMS.get(stats_id)
            df = fetch_from_api(stats_id, api_key, extra_params=extra)
            df.to_csv(cache_path, index=False)
            return df, "api"
        except Exception as exc:  # broad catch: fall back to stale cache on any API or parse failure
            logger.warning("API fetch failed for %s: %s", stats_id, exc)

    if cache_path.exists():
        logger.warning("Using stale cache for %s", stats_id)
        return pd.read_csv(cache_path), "stale_cache"

    raise RuntimeError(
        f"No data available for stats ID {stats_id}. "
        "Register for a free API key at https://www.e-stat.go.jp/api/, "
        "add ESTAT_API_KEY=your_key to .env, and restart the app."
    )
