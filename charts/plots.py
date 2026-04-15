"""All Plotly chart functions. No Streamlit or I/O here."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

OECD_UNEMPLOYMENT = 4.5  # approximate OECD average, used as reference line


def _apply_base_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title, font=dict(size=16)),
        font=dict(family="sans-serif", size=12),
        margin=dict(t=70, b=50, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def chart_ratio_over_time(
    national_df: pd.DataFrame,
    it_df: pd.DataFrame | None = None,
) -> go.Figure:
    """
    Section 2: Monthly job-to-applicant ratio line chart (national).

    national_df: columns [date, ratio] — national all-industry series.
    it_df: optional columns [date, ratio] — IT/professional services series.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=national_df["date"],
        y=national_df["ratio"],
        mode="lines",
        name="National (All Industries)",
        line=dict(color=px.colors.qualitative.Set2[0], width=2.5),
    ))

    if it_df is not None and not it_df.empty:
        fig.add_trace(go.Scatter(
            x=it_df["date"],
            y=it_df["ratio"],
            mode="lines",
            name="IT / Professional Services",
            line=dict(color=px.colors.qualitative.Set2[1], width=2, dash="dot"),
        ))

    # COVID shading
    fig.add_vrect(
        x0="2020-01-01", x1="2021-12-31",
        fillcolor="rgba(180,180,180,0.2)",
        layer="below",
        line_width=0,
        annotation_text="COVID-19",
        annotation_position="top left",
        annotation_font_size=10,
    )

    # Equilibrium line
    fig.add_hline(
        y=1.0,
        line_dash="dot",
        line_color="red",
        line_width=1.5,
        annotation_text="Equilibrium (1 job per applicant)",
        annotation_position="bottom right",
        annotation_font_size=10,
    )

    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Job-to-Applicant Ratio (有効求人倍率)")
    return _apply_base_layout(fig, "Japan Job-to-Applicant Ratio (2015–Present)")


def chart_industry_breakdown(df: pd.DataFrame) -> go.Figure:
    """
    Section 3: Horizontal bar chart of ratio by industry for the latest month.

    df: columns [industry, ratio] — latest month, sorted ascending for display.
    IT rows are highlighted in a distinct colour.
    """
    from data.process import IT_INDUSTRY_KEYWORDS

    df = df.copy().sort_values("ratio", ascending=True)

    colors = [
        px.colors.qualitative.Set2[1]
        if any(kw in str(ind) for kw in IT_INDUSTRY_KEYWORDS)
        else px.colors.sequential.Blues[4]
        for ind in df["industry"]
    ]

    fig = go.Figure(go.Bar(
        x=df["ratio"],
        y=df["industry"],
        orientation="h",
        marker_color=colors,
        hovertemplate="%{y}: %{x:.2f}<extra></extra>",
    ))

    fig.add_vline(
        x=1.0,
        line_dash="dot",
        line_color="red",
        line_width=1.5,
        annotation_text="Equilibrium",
        annotation_position="top right",
        annotation_font_size=10,
    )

    fig.update_xaxes(title_text="Job-to-Applicant Ratio")
    fig.update_yaxes(title_text="")
    return _apply_base_layout(
        fig, "Job-to-Applicant Ratio by Industry — Latest Available Month"
    )


def chart_tokyo_vs_national(
    national_df: pd.DataFrame,
    tokyo_df: pd.DataFrame,
) -> go.Figure:
    """
    Section 4: Line chart comparing Tokyo vs national ratio over time.

    national_df / tokyo_df: columns [date, ratio].
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=national_df["date"],
        y=national_df["ratio"],
        mode="lines",
        name="National",
        line=dict(color=px.colors.qualitative.Set2[0], width=2),
    ))

    if not tokyo_df.empty:
        fig.add_trace(go.Scatter(
            x=tokyo_df["date"],
            y=tokyo_df["ratio"],
            mode="lines",
            name="Tokyo",
            line=dict(color=px.colors.qualitative.Set2[2], width=2),
        ))

    fig.add_hline(
        y=1.0,
        line_dash="dot",
        line_color="red",
        line_width=1,
        annotation_text="Equilibrium",
        annotation_position="bottom right",
        annotation_font_size=9,
    )

    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Job-to-Applicant Ratio")
    return _apply_base_layout(fig, "Job-to-Applicant Ratio: Tokyo vs National")


def chart_prefecture_bar(df: pd.DataFrame) -> go.Figure:
    """
    Section 4: Bar chart of ratio by prefecture for the latest month.

    df: columns [area, ratio].
    """
    df = df.sort_values("ratio", ascending=False)

    fig = px.bar(
        df,
        x="area",
        y="ratio",
        color_discrete_sequence=[px.colors.sequential.Blues[4]],
        labels={"area": "Prefecture", "ratio": "Job-to-Applicant Ratio"},
    )
    fig.update_xaxes(title_text="Prefecture")
    fig.update_yaxes(title_text="Job-to-Applicant Ratio")
    return _apply_base_layout(fig, "Job-to-Applicant Ratio by Prefecture — Latest Month")


def chart_unemployment(df: pd.DataFrame) -> go.Figure:
    """
    Section 5: Area chart of Japan's unemployment rate with OECD reference line.

    df: columns [date, unemployment_rate].
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["unemployment_rate"],
        fill="tozeroy",
        mode="lines",
        name="Japan",
        line=dict(color=px.colors.sequential.Blues[5], width=2),
        fillcolor="rgba(99,143,200,0.2)",
    ))

    fig.add_hline(
        y=OECD_UNEMPLOYMENT,
        line_dash="dot",
        line_color="orange",
        line_width=1.5,
        annotation_text=f"OECD Average (~{OECD_UNEMPLOYMENT}%)",
        annotation_position="top right",
        annotation_font_size=10,
    )

    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Unemployment Rate (%)")
    return _apply_base_layout(fig, "Japan Unemployment Rate vs OECD Average")


def chart_salary_table() -> go.Figure:
    """
    Section 6: Floating bar chart showing salary ranges for data roles in Japan.
    Bars start at the low end of the range and extend to the high end.
    """
    roles = [
        "Junior Data Analyst",
        "Mid-level Data Analyst",
        "Data Engineer",
        "Data Scientist",
    ]
    low =  [4, 6, 7, 8]
    high = [6, 9, 11, 14]

    fig = go.Figure(go.Bar(
        name="Salary Range",
        x=roles,
        y=[h - l for l, h in zip(low, high)],
        base=low,
        marker_color=px.colors.sequential.Blues[3],
        text=[f"¥{l}M – ¥{h}M" for l, h in zip(low, high)],
        textposition="outside",
        hovertemplate="%{x}: ¥%{base}M – ¥%{top}M/year<extra></extra>",
    ))

    fig.update_xaxes(title_text="Role")
    fig.update_yaxes(title_text="Annual Salary (¥ Millions)")
    return _apply_base_layout(
        fig, "Estimated Salary Ranges — Data Roles in Japan (¥M / year)"
    )
