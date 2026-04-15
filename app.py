"""Japan Labour Market Dashboard — Streamlit entry point."""
from __future__ import annotations

import io
import os
from datetime import date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from data.fetch import get_dataset, STATS_JOB_RATIO, STATS_LABOUR_FORCE
from data.process import (
    process_job_ratio,
    process_unemployment,
    compute_kpis,
    IT_INDUSTRY_KEYWORDS,
)
from charts.plots import (
    chart_ratio_over_time,
    chart_industry_breakdown,
    chart_tokyo_vs_national,
    chart_prefecture_bar,
    chart_unemployment,
    chart_salary_table,
)

load_dotenv()

st.set_page_config(
    page_title="Japan Labour Market Dashboard",
    page_icon="🇯🇵",
    layout="wide",
)

SOURCE_CAPTION = "Source: e-Stat API — Statistics Bureau of Japan (stat.go.jp)"

# ── Intro ─────────────────────────────────────────────────────────────────────
st.title("🇯🇵 Japan Labour Market Dashboard")
st.markdown(
    "An interactive analysis of Japan's labour market using official government "
    "data from the **Statistics Bureau of Japan (e-Stat)**. Tracks the "
    "**job-to-applicant ratio** (有効求人倍率), unemployment trends, and the "
    "outlook for data and technology roles in Tokyo. Built for Arthur Gagniare's "
    "data analyst portfolio — targeting roles in Tokyo's finance and tech sectors."
)
st.divider()


# ── Load data ─────────────────────────────────────────────────────────────────
api_key = os.getenv("ESTAT_API_KEY")


@st.cache_data(ttl=3600, show_spinner="Loading labour market data…")
def load_data(key: str | None) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    errors: list[str] = []

    try:
        raw_job, _ = get_dataset(STATS_JOB_RATIO, key)
        job_df = process_job_ratio(raw_job)
    except RuntimeError as exc:
        errors.append(str(exc))
        job_df = pd.DataFrame(columns=["date", "area", "industry", "ratio"])

    try:
        raw_unemp, _ = get_dataset(STATS_LABOUR_FORCE, key)
        unemp_df = process_unemployment(raw_unemp)
    except RuntimeError as exc:
        errors.append(str(exc))
        unemp_df = pd.DataFrame(columns=["date", "unemployment_rate"])

    return job_df, unemp_df, errors


job_df, unemp_df, load_errors = load_data(api_key)

if not api_key:
    st.warning(
        "⚠️ **No API key found.** To load live data: register for a free key at "
        "https://www.e-stat.go.jp/api/, add `ESTAT_API_KEY=your_key` to `.env`, "
        "and restart the app. Attempting to load from local cache…"
    )

for err in load_errors:
    st.error(f"❌ {err}")

if job_df.empty and unemp_df.empty:
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

min_year, max_year = 2015, date.today().year
year_range = st.sidebar.slider(
    "Date range (year)",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
)

available_industries = (
    sorted(job_df["industry"].dropna().unique().tolist())
    if not job_df.empty
    else []
)
default_industries = (
    [i for i in available_industries if any(kw in i for kw in IT_INDUSTRY_KEYWORDS)]
    or available_industries[:3]
)
selected_industries = st.sidebar.multiselect(
    "Industries",
    options=available_industries,
    default=default_industries or available_industries,
    help="Filter the industry breakdown chart (Section 3).",
)

available_prefectures = (
    sorted(job_df["area"].dropna().unique().tolist())
    if not job_df.empty
    else ["National"]
)
selected_prefecture = st.sidebar.selectbox(
    "Prefecture",
    options=["National"] + [p for p in available_prefectures if p != "National"],
    help="Used for the Tokyo Focus section (Section 4).",
)

# Apply date filter
if not job_df.empty:
    job_df = job_df[
        (job_df["date"].dt.year >= year_range[0])
        & (job_df["date"].dt.year <= year_range[1])
    ]
if not unemp_df.empty:
    unemp_df = unemp_df[
        (unemp_df["date"].dt.year >= year_range[0])
        & (unemp_df["date"].dt.year <= year_range[1])
    ]


# ── Section 1: KPI Cards ──────────────────────────────────────────────────────
st.header("1. Market Overview")
st.caption("Key indicators for the latest available month. Delta shows month-on-month change.")

kpis = compute_kpis(job_df, unemp_df)
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Job-to-Applicant Ratio",
    f"{kpis['job_ratio_latest']:.2f}" if kpis.get("job_ratio_latest") else "N/A",
    delta=f"{kpis['job_ratio_delta']:+.2f}" if kpis.get("job_ratio_delta") is not None else None,
    help="有効求人倍率 — national, all industries, latest month.",
)
c2.metric(
    "IT Sector Ratio",
    f"{kpis['it_ratio_latest']:.2f}" if kpis.get("it_ratio_latest") else "N/A",
    delta=f"{kpis['it_ratio_delta']:+.2f}" if kpis.get("it_ratio_delta") is not None else None,
    help="Job-to-applicant ratio for IT / information services.",
)
c3.metric(
    "Unemployment Rate",
    f"{kpis['unemployment_latest']:.1f}%" if kpis.get("unemployment_latest") else "N/A",
    delta=f"{kpis['unemployment_delta']:+.2f}pp" if kpis.get("unemployment_delta") is not None else None,
    delta_color="inverse",
)
c4.metric(
    "YoY Job Openings Change",
    f"{kpis['job_openings_yoy']:+.1f}%" if kpis.get("job_openings_yoy") is not None else "N/A",
)

st.divider()


# ── Section 2: Ratio Over Time ────────────────────────────────────────────────
st.header("2. Job-to-Applicant Ratio Over Time")
st.caption(
    "The 有効求人倍率 (yūkō kyūjin bairitsu) is Japan's most-watched labour market "
    "indicator. A ratio above 1.0 means more open jobs than job seekers — a candidate's "
    "market. Below 1.0 means more applicants than openings."
)

if not job_df.empty:
    nat_all = job_df[
        (job_df["area"] == "National")
        & (job_df["industry"].isin(["合計", "All", "全産業"]))
    ]
    if nat_all.empty:
        nat_all = (
            job_df[job_df["area"] == "National"]
            .groupby("date")["ratio"]
            .mean()
            .reset_index()
        )

    it_national = job_df[
        (job_df["area"] == "National")
        & job_df["industry"].str.contains(
            "|".join(IT_INDUSTRY_KEYWORDS), case=False, na=False
        )
    ]

    st.plotly_chart(
        chart_ratio_over_time(nat_all, it_national if not it_national.empty else None),
        use_container_width=True,
    )
    st.caption(SOURCE_CAPTION)
else:
    st.info("No job-to-applicant data available.")

st.divider()


# ── Section 3: Industry Breakdown ─────────────────────────────────────────────
st.header("3. Industry Breakdown — Latest Month")
st.caption(
    "Comparison of the job-to-applicant ratio across industries for the most recent "
    "available month. The IT and professional services sectors consistently run "
    "well above the national average."
)

if not job_df.empty:
    latest_month = job_df["date"].max()
    industry_df = job_df[
        (job_df["date"] == latest_month)
        & (job_df["area"] == "National")
        & (job_df["industry"].isin(selected_industries) if selected_industries else True)
    ][["industry", "ratio"]].dropna()

    if not industry_df.empty:
        st.plotly_chart(
            chart_industry_breakdown(industry_df),
            use_container_width=True,
        )
        st.caption(SOURCE_CAPTION)
    else:
        st.info("No industry breakdown data for the selected filters.")

st.divider()


# ── Section 4: Tokyo Focus ────────────────────────────────────────────────────
st.header("4. Tokyo Focus")
st.markdown(
    "> **Tokyo consistently runs above the national average**, particularly in "
    "technology and professional services. The capital's concentration of global "
    "and foreign-affiliated firms drives exceptional demand for bilingual data talent."
)

if not job_df.empty:
    nat_series = (
        job_df[job_df["area"] == "National"]
        .groupby("date")["ratio"]
        .mean()
        .reset_index()
    )
    tokyo_series = (
        job_df[job_df["area"] == "Tokyo"]
        .groupby("date")["ratio"]
        .mean()
        .reset_index()
    )

    st.plotly_chart(
        chart_tokyo_vs_national(nat_series, tokyo_series),
        use_container_width=True,
    )
    st.caption(SOURCE_CAPTION)

    # Prefecture bar — latest month
    latest_month = job_df["date"].max()
    pref_df = (
        job_df[job_df["date"] == latest_month]
        .groupby("area")["ratio"]
        .mean()
        .reset_index()
        .rename(columns={"ratio": "ratio"})
    )
    if len(pref_df) > 1:
        st.plotly_chart(chart_prefecture_bar(pref_df), use_container_width=True)
        st.caption(SOURCE_CAPTION)

st.divider()


# ── Section 5: Unemployment Trends ────────────────────────────────────────────
st.header("5. Unemployment Trends")
st.caption(
    "Japan's unemployment rate has remained well below the OECD average for decades, "
    "reflecting structural full employment and rigid labour market norms. "
    f"The OECD average reference line is set at {4.5}%."
)

if not unemp_df.empty:
    st.plotly_chart(chart_unemployment(unemp_df), use_container_width=True)
    st.caption(SOURCE_CAPTION)
else:
    st.info("No unemployment data available.")

st.divider()


# ── Section 6: IT Job Outlook ─────────────────────────────────────────────────
st.header("6. Data Analyst / IT Job Outlook in Tokyo")
st.caption(
    "Estimated salary ranges for data roles in Japan, based on publicly available "
    "recruitment data (Doda, Nikkei, LinkedIn Japan, 2024–2025)."
)

st.plotly_chart(chart_salary_table(), use_container_width=True)

st.info(
    "💡 **Opportunity for English-speaking data professionals:** "
    "Tokyo's technology sector faces a structural shortage of bilingual analysts "
    "and engineers. Foreign-affiliated (外資系) firms — including financial services, "
    "consulting, and global tech companies — typically offer salaries **20–30% above** "
    "the ranges shown, with English as a working language. "
    "The job-to-applicant ratio in IT services regularly exceeds 2.0x the national average."
)

st.markdown(
    "**Note:** Salaries at foreign-affiliated (外資系) firms are typically 20–30% higher. "
    "Figures are approximate annual gross; bonuses and stock compensation not included."
)

st.divider()


# ── Section 7: Raw Data Explorer ──────────────────────────────────────────────
st.header("7. Raw Data Explorer")
st.caption("Browse and download the underlying processed dataset.")

combined_df = pd.DataFrame()
if not job_df.empty:
    j = job_df.copy()
    j["dataset"] = "Job-to-Applicant Ratio"
    j["date"] = j["date"].dt.strftime("%Y-%m")
    combined_df = pd.concat([combined_df, j], ignore_index=True)

if not unemp_df.empty:
    u = unemp_df.copy()
    u["dataset"] = "Unemployment Rate"
    u["area"] = "National"
    u["industry"] = "All"
    u["ratio"] = u["unemployment_rate"]
    u["date"] = u["date"].dt.strftime("%Y-%m")
    combined_df = pd.concat(
        [combined_df, u[["date", "area", "industry", "ratio", "dataset"]]],
        ignore_index=True,
    )

if not combined_df.empty:
    st.dataframe(combined_df, use_container_width=True, height=350)

    csv_bytes = combined_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv_bytes,
        file_name="japan_labour_market_data.csv",
        mime="text/csv",
    )
    st.caption(SOURCE_CAPTION)
else:
    st.info("No data loaded yet.")
