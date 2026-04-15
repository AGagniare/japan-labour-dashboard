# Japan Labour Market Dashboard — Design Spec

## Goal

A polished, deployable Streamlit dashboard targeting Data Analyst job search in Tokyo. Demonstrates Python data analysis, Plotly visualisation, e-Stat API integration, and data storytelling in a Japan-specific context. Runnable locally with `streamlit run app.py`, deployable free on Streamlit Community Cloud.

## Architecture

Single-page Streamlit app with three clean layers:

- **`data/fetch.py`** — e-Stat API client with 7-day CSV cache and graceful fallback
- **`data/process.py`** — cleaning, transformation, derived metrics (no I/O)
- **`charts/plots.py`** — all Plotly chart functions (no chart logic in `app.py`)
- **`app.py`** — layout, sidebar filters, section rendering only

```
japan-labour-dashboard/
├── app.py
├── data/
│   ├── fetch.py
│   ├── process.py
│   └── cache/           # auto-created, gitignored
├── charts/
│   └── plots.py
├── .env                 # gitignored
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Tech Stack

Python 3.10+, Streamlit ≥1.35, Plotly ≥5.22, pandas ≥2.2, requests ≥2.31, python-dotenv ≥1.0

## Data Source — e-Stat API

Base URL: `https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData`

API key read from `.env` as `ESTAT_API_KEY`. If missing or unreachable, falls back to cached CSVs in `data/cache/`. If cache also empty, shows `st.error` with setup instructions.

**Datasets:**
1. **Job-to-Applicant Ratio** (有効求人倍率) — Stats ID `0000010070`, monthly from 2015 to present, national + by industry
2. **Labour Force Survey** (労働力調査) — unemployment rate, employment rate, monthly
3. **IT/Information Services** — job openings in IT/professional-technical sector; if not isolatable, use broader Professional Services with a UI note

Cache policy: fetch on first run, re-fetch if cache file is older than 7 days. Each dataset cached as a separate timestamped CSV.

## Sidebar Filters

Always visible:
- **Date range slider** — year, 2015 to present
- **Industry multiselect** — defaults to All + IT/Information Services
- **Prefecture selector** — National, Tokyo, Osaka, Aichi minimum

## Dashboard Sections

### Section 1 — Market Overview (KPI Cards)
Four `st.metric` cards with delta vs previous month:
1. Current Job-to-Applicant Ratio (national, latest)
2. IT Sector Job-to-Applicant Ratio (latest, typically 2x+ national)
3. Unemployment Rate % (latest)
4. YoY Change in Job Openings %

### Section 2 — Job-to-Applicant Ratio Over Time
Line chart, national monthly 2015–present. Second line for IT/tech if available. Shaded COVID band (2020–2021) with annotation. Horizontal dotted line at y=1.0 labelled "Equilibrium". Insight text below explaining the metric.

### Section 3 — Industry Breakdown (Latest Month)
Horizontal bar chart sorted descending. IT/Professional Services bar highlighted. Vertical dotted line at x=1.0.

### Section 4 — Tokyo Focus
Line chart: Tokyo vs national ratio over time. Text callout on Tokyo premium. Bar chart by prefecture for latest month if prefecture data available.

### Section 5 — Unemployment Trends
Area chart 2015–present. OECD average (~4.5%) as horizontal reference line. Title: "Japan Unemployment Rate vs OECD Average".

### Section 6 — Data Analyst / IT Job Outlook (Narrative)
Salary table (hardcoded from public sources):
- Junior Data Analyst: ¥4M–¥6M/year
- Mid-level Data Analyst: ¥6M–¥9M/year
- Data Engineer: ¥7M–¥11M/year
- Data Scientist: ¥8M–¥14M/year

Note: foreign-affiliated firms typically 20–30% higher. `st.info` callout for English-speaking professionals in Tokyo.

### Section 7 — Raw Data Explorer
`st.dataframe` with column filters. `st.download_button` to export CSV. Source caption.

## Styling

- `st.set_page_config(page_title="Japan Labour Market Dashboard", layout="wide")`
- Plotly: `px.colors.sequential.Blues` for single-series, `px.colors.qualitative.Set2` for multi-series
- All charts: English axis labels, descriptive title, `template="plotly_white"`
- `st.caption("Source: e-Stat API — Statistics Bureau of Japan")` under every chart

## Error Handling

- API error → `st.warning` with API key instructions + auto-load from cache
- Cache empty → `st.error` with setup instructions
- All API calls wrapped in try/except — no silent crashes

## README

Includes: title + description, live demo link placeholder, screenshot placeholder, shields.io badges, setup instructions, data sources section, 有効求人倍率 explainer, project structure, author (Arthur Gagniare — linkedin.com/in/arthurgagniare).

## Deployment

Streamlit Community Cloud — push to public GitHub, connect repo, add `ESTAT_API_KEY` secret.
