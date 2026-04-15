# Japan Labour Market Dashboard

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?logo=streamlit)
![Plotly](https://img.shields.io/badge/Plotly-5.22%2B-3F4F75?logo=plotly)
![pandas](https://img.shields.io/badge/pandas-2.2%2B-150458?logo=pandas)

An interactive data dashboard analysing Japan's labour market using official government statistics from the **Statistics Bureau of Japan (e-Stat)**. Built as a portfolio project targeting **Data Analyst roles in Tokyo** — demonstrating API integration, data wrangling, and storytelling with data in a Japan-specific context.

[**Live Demo**](https://your-app.streamlit.app) · [**Portfolio**](https://agagniare.github.io/AGagniare-Portfolio)

![Dashboard Screenshot](docs/screenshot.png)

---

## What It Shows

- **Job-to-Applicant Ratio** (有効求人倍率) — Japan's most-cited labour market indicator, tracked monthly from 2015 to present
- **Industry Breakdown** — ratio by sector, highlighting IT and professional services
- **Tokyo vs National** — prefecture-level comparison
- **Unemployment Trends** — vs OECD average reference
- **IT / Data Role Outlook** — salary ranges for data roles in Japan
- **Raw Data Explorer** — browse and download the underlying dataset

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/AGagniare/japan-labour-dashboard.git
cd japan-labour-dashboard
pip install -r requirements.txt
```

### 2. Get an e-Stat API key (free)

1. Register at [https://www.e-stat.go.jp/api/](https://www.e-stat.go.jp/api/)
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Add your key to `.env`:
   ```
   ESTAT_API_KEY=your_key_here
   ```

### 3. Run

```bash
streamlit run app.py
```

The app fetches data on first run and caches it locally for 7 days. Subsequent runs are instant.

---

## Data Sources

All data comes from **e-Stat** ([estat.go.jp](https://www.e-stat.go.jp)), Japan's official government statistics portal, via its free REST API.

| Dataset | Description | Stats ID |
|---------|-------------|----------|
| 職業安定業務統計 | Job-to-applicant ratio by prefecture and industry | `0000010070` |
| 労働力調査 | Unemployment and employment rates | `0003001783` |

### What is 有効求人倍率?

The **有効求人倍率** (yūkō kyūjin bairitsu, "effective job-opening-to-applicant ratio") is the single most-watched labour market indicator in Japan. It measures the number of job openings per job seeker registered at public employment offices (Hello Work). A ratio **above 1.0** means more openings than applicants (employer shortage — good for job seekers). **Below 1.0** means more applicants than openings.

---

## Project Structure

```
japan-labour-dashboard/
├── app.py               # Streamlit entry point — layout only
├── data/
│   ├── fetch.py         # e-Stat API client + 7-day CSV cache
│   ├── process.py       # Data cleaning and KPI computation
│   └── cache/           # Auto-created; stores cached CSVs
├── charts/
│   └── plots.py         # All Plotly chart functions
├── tests/
│   ├── test_fetch.py
│   └── test_process.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Deployment (Streamlit Community Cloud — free)

1. Push this repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect the repo
3. Set `app.py` as the entry point
4. Add `ESTAT_API_KEY` as a secret in the Streamlit Cloud dashboard
5. Your app will be live at `https://your-username-japan-labour-dashboard.streamlit.app`

---

## Author

**Arthur Gagniare**
[linkedin.com/in/arthurgagniare](https://linkedin.com/in/arthurgagniare) · [agagniare.github.io/AGagniare-Portfolio](https://agagniare.github.io/AGagniare-Portfolio)
