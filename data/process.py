"""Data cleaning, transformation, and KPI computation. No I/O."""
from __future__ import annotations

import pandas as pd

PREFECTURE_MAP = {
    "全国": "National",
    "東京都": "Tokyo",
    "大阪府": "Osaka",
    "愛知県": "Aichi",
    "神奈川県": "Kanagawa",
    "埼玉県": "Saitama",
    "千葉県": "Chiba",
    "福岡県": "Fukuoka",
}

# Keywords that identify the IT / information services industry rows
IT_INDUSTRY_KEYWORDS = ["情報通信業", "情報サービス", "専門・技術"]


def _detect_col(df: pd.DataFrame, *keywords: str) -> str | None:
    """Return the first column name that contains any of the given keywords."""
    for kw in keywords:
        matches = [c for c in df.columns if kw in str(c)]
        if matches:
            return matches[0]
    return None


def _parse_month_label(label: str) -> pd.Timestamp | None:
    """
    Convert e-Stat date labels to Timestamps.
    Handles:
      - '2024年1月'   →  Timestamp('2024-01-01')
      - '2024年度'    →  Timestamp('2024-04-01')  (fiscal year start)
      - '2024010000' →  Timestamp('2024-01-01')
    """
    s = str(label).strip()
    try:
        if "年度" in s:
            year = int(s.replace("年度", ""))
            return pd.Timestamp(year=year, month=4, day=1)
        if "年" in s and "月" in s:
            year = int(s.split("年")[0])
            month = int(s.split("年")[1].replace("月", ""))
            return pd.Timestamp(year=year, month=month, day=1)
        if len(s) >= 6 and s[:6].isdigit():
            return pd.Timestamp(year=int(s[:4]), month=int(s[4:6]), day=1)
    except (ValueError, TypeError):
        pass
    return None


def process_job_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and reshape the raw job-to-applicant ratio DataFrame.

    Input: raw DataFrame from _parse_estat_response (column names are
           Japanese e-Stat dimension names, 'value' is float).
    Output: DataFrame with columns — date (Timestamp), area (str),
            industry (str), ratio (float). Rows with null ratio dropped.
    """
    df = df.copy().dropna(subset=["value"])

    # Parse date — handles "時間軸（月次）", "調査年", etc.
    time_col = _detect_col(df, "時間軸", "調査年", "time")
    if time_col:
        df["date"] = df[time_col].apply(_parse_month_label)
        df = df.dropna(subset=["date"])
    else:
        return pd.DataFrame(columns=["date", "area", "industry", "ratio"])

    # Map prefecture/region names to English — handles "都道府県" and "地域"
    area_col = _detect_col(df, "都道府県", "地域", "area")
    if area_col:
        df["area"] = df[area_col].map(PREFECTURE_MAP).fillna(df[area_col])
    else:
        df["area"] = "National"

    # Industry column (keep Japanese — used for keyword matching later)
    ind_col = _detect_col(df, "産業", "職種", "cat01")
    if ind_col:
        df["industry"] = df[ind_col]
    else:
        df["industry"] = "All"

    df["ratio"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df[["date", "area", "industry", "ratio"]]
        .dropna(subset=["ratio"])
        .sort_values("date")
        .reset_index(drop=True)
    )


def process_unemployment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the Labour Force Survey raw DataFrame.

    Input: raw DataFrame from _parse_estat_response.
    Output: DataFrame with columns — date (Timestamp),
            unemployment_rate (float), sorted ascending by date.
    """
    df = df.copy().dropna(subset=["value"])

    time_col = _detect_col(df, "時間軸", "time")
    if time_col:
        df["date"] = df[time_col].apply(_parse_month_label)
        df = df.dropna(subset=["date"])
    else:
        return pd.DataFrame(columns=["date", "unemployment_rate"])

    # Filter to unemployment rate rows.
    # For 0003005865: 就業状態 column has "完全失業者"; 表章項目 has "率".
    # Accept rows that look like a rate/unemployment measure.
    status_col = _detect_col(df, "就業状態")
    tab_col = _detect_col(df, "表章項目", "tab")
    if status_col:
        mask = df[status_col].str.contains("失業", na=False)
        if mask.any():
            df = df[mask]
    elif tab_col:
        mask = df[tab_col].str.contains("失業率|率", na=False)
        if mask.any():
            df = df[mask]

    df["unemployment_rate"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df[["date", "unemployment_rate"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )


def compute_kpis(job_df: pd.DataFrame, unemp_df: pd.DataFrame) -> dict:
    """
    Compute the 4 KPI card values from processed DataFrames.

    Returns dict with keys:
        job_ratio_latest (float), job_ratio_delta (float),
        it_ratio_latest (float | None), it_ratio_delta (float | None),
        unemployment_latest (float | None), unemployment_delta (float | None),
        job_openings_yoy (float)
    """
    kpis: dict = {}

    # ── National job-to-applicant ratio ───────────────────────────────────────
    national = job_df[job_df["area"] == "National"].copy()
    nat_all = national[
        national["industry"].isin(["合計", "All", "全産業"])
    ].sort_values("date")

    if nat_all.empty and not national.empty:
        # Fall back to mean across all industries per date
        nat_all = (
            national.groupby("date")["ratio"]
            .mean()
            .reset_index()
            .sort_values("date")
        )

    if not nat_all.empty:
        kpis["job_ratio_latest"] = float(nat_all["ratio"].iloc[-1])
        kpis["job_ratio_delta"] = (
            float(nat_all["ratio"].iloc[-1] - nat_all["ratio"].iloc[-2])
            if len(nat_all) >= 2
            else 0.0
        )
        kpis["job_openings_yoy"] = (
            float(
                (nat_all["ratio"].iloc[-1] / nat_all["ratio"].iloc[-13] - 1) * 100
            )
            if len(nat_all) >= 13
            else 0.0
        )
    else:
        kpis.update(
            {"job_ratio_latest": 0.0, "job_ratio_delta": 0.0, "job_openings_yoy": 0.0}
        )

    # ── IT sector ratio ───────────────────────────────────────────────────────
    it_mask = job_df["industry"].str.contains(
        "|".join(IT_INDUSTRY_KEYWORDS), case=False, na=False
    )
    it_df = job_df[it_mask & (job_df["area"] == "National")].sort_values("date")

    if not it_df.empty:
        kpis["it_ratio_latest"] = float(it_df["ratio"].iloc[-1])
        kpis["it_ratio_delta"] = (
            float(it_df["ratio"].iloc[-1] - it_df["ratio"].iloc[-2])
            if len(it_df) >= 2
            else 0.0
        )
    else:
        kpis["it_ratio_latest"] = None
        kpis["it_ratio_delta"] = None

    # ── Unemployment ──────────────────────────────────────────────────────────
    if not unemp_df.empty:
        kpis["unemployment_latest"] = float(unemp_df["unemployment_rate"].iloc[-1])
        kpis["unemployment_delta"] = (
            float(
                unemp_df["unemployment_rate"].iloc[-1]
                - unemp_df["unemployment_rate"].iloc[-2]
            )
            if len(unemp_df) >= 2
            else 0.0
        )
    else:
        kpis["unemployment_latest"] = None
        kpis["unemployment_delta"] = None

    return kpis
