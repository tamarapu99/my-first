"""
Shared helpers for the VexarDrive fleet dashboard.

Everything in this file only READS the analytical outputs from Step 3-6.
Nothing here recomputes a driver safety score or a vehicle health status -
those numbers are loaded as-is from processed/analytical/ and never touched.
"""

from pathlib import Path
import json
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# Palette - deliberately restrained. One accent colour, neutral greys,
# three status colours used consistently everywhere in the app.
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#FFFFFF",
    "panel": "#F7F7F5",
    "border": "#E4E2DD",
    "text": "#1F1F1D",
    "text_muted": "#6B6963",
    "accent": "#2C5F4A",       # deep green - used sparingly for the primary accent
    "accent_soft": "#E8EFE9",
    "normal": "#3E7A57",
    "watch": "#B8860B",
    "investigate": "#A6402F",
    "normal_bg": "#EAF3EC",
    "watch_bg": "#FBF2DF",
    "investigate_bg": "#F8E9E5",
    "grid": "#ECEAE5",
}

STATUS_COLOR = {
    "Normal": COLORS["normal"],
    "Watch": COLORS["watch"],
    "Investigate": COLORS["investigate"],
}
STATUS_BG = {
    "Normal": COLORS["normal_bg"],
    "Watch": COLORS["watch_bg"],
    "Investigate": COLORS["investigate_bg"],
}

FONT = "'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif"
MONO = "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace"


def inject_base_css():
    """Apply one consistent, high-contrast visual system to every dashboard page."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        :root {{
            --vd-bg: {COLORS['bg']};
            --vd-panel: {COLORS['panel']};
            --vd-border: {COLORS['border']};
            --vd-text: {COLORS['text']};
            --vd-muted: {COLORS['text_muted']};
            --vd-accent: {COLORS['accent']};
        }}

        html, body {{
            font-family: {FONT};
            color: {COLORS['text']};
            background: {COLORS['bg']} !important;
        }}

        /* Avoid styling Streamlit's generated class names globally. Those
           names change between releases and can accidentally affect native
           menus/toolbars. Keep the theme scoped to stable Streamlit hooks. */
        .stApp,
        .stApp p,
        .stApp li,
        .stApp label,
        .stApp [data-testid="stMarkdownContainer"] {{
            font-family: {FONT};
        }}

        /* Keep the actual content area plain and readable even when the
           user's Streamlit/browser theme is dark. */
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {{
            background: {COLORS['bg']} !important;
        }}
        [data-testid="stMainBlockContainer"],
        .block-container {{
            background: {COLORS['bg']} !important;
            padding-top: 2.1rem !important;
            padding-bottom: 3rem !important;
            max-width: 1180px;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: {COLORS['panel']} !important;
            border-right: 1px solid {COLORS['border']};
        }}
        section[data-testid="stSidebar"] * {{
            color: {COLORS['text']} !important;
        }}
        section[data-testid="stSidebar"] .stMarkdown p {{
            color: {COLORS['text_muted']} !important;
        }}

        h1, h2, h3 {{
            font-family: {FONT};
            color: {COLORS['text']} !important;
            font-weight: 600;
            letter-spacing: -0.012em;
        }}
        h1 {{ font-size: 1.8rem !important; margin-bottom: 0.2rem; }}
        h2 {{ font-size: 1.25rem !important; margin-top: 1.7rem; }}
        h3 {{ font-size: 1.04rem !important; margin-top: 1rem; }}
        p, li, span, label, div[data-testid="stMarkdownContainer"] {{
            color: {COLORS['text']};
        }}
        .subtitle {{
            color: {COLORS['text_muted']} !important;
            font-size: 1rem;
            line-height: 1.55;
            margin-top: -0.1rem;
            margin-bottom: 1.25rem;
        }}
        hr {{ border-color: {COLORS['border']} !important; }}

        /* Inputs / controls */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div {{
            background: #FFFFFF !important;
            border-color: {COLORS['border']} !important;
        }}
        div[data-baseweb="select"] *,
        div[data-baseweb="input"] *,
        div[data-baseweb="textarea"] * {{
            color: {COLORS['text']} !important;
        }}
        [data-testid="stSelectbox"] label,
        [data-testid="stMultiSelect"] label {{
            color: {COLORS['text']} !important;
            font-weight: 500;
        }}

        /* Tables */
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {{
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            overflow: hidden;
            background: #FFFFFF !important;
        }}

        /* KPI cards */
        .kpi-card {{
            background: {COLORS['panel']} !important;
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 15px 16px 13px 16px;
            min-height: 92px;
            box-shadow: 0 1px 2px rgba(31,31,29,0.04);
        }}
        .kpi-label {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.055em;
            color: {COLORS['text_muted']} !important;
            margin-bottom: 5px;
            font-weight: 600;
        }}
        .kpi-value {{
            font-size: 1.6rem;
            font-weight: 600;
            color: {COLORS['text']} !important;
            font-family: {MONO};
            line-height: 1.15;
        }}
        .kpi-sub {{
            font-size: 0.78rem;
            color: {COLORS['text_muted']} !important;
            margin-top: 4px;
            line-height: 1.35;
        }}

        /* Status pills */
        .pill {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 600;
        }}

        /* Callouts */
        .note-box, .warn-box, .limit-box, .formula-box, .interview-box {{
            border-radius: 9px;
            padding: 13px 16px;
            margin: 0.65rem 0 1rem 0;
            line-height: 1.55;
        }}
        .note-box {{
            background: {COLORS['accent_soft']} !important;
            border: 1px solid #D2E1D6;
            border-left: 4px solid {COLORS['accent']};
            color: {COLORS['text']} !important;
            font-size: 0.91rem;
        }}
        .warn-box {{
            background: {COLORS['watch_bg']} !important;
            border: 1px solid #E9D8AE;
            border-left: 4px solid {COLORS['watch']};
            color: {COLORS['text']} !important;
            font-size: 0.9rem;
        }}
        .limit-box {{
            background: {COLORS['panel']} !important;
            border: 1px solid {COLORS['border']};
            color: {COLORS['text']} !important;
            font-size: 0.9rem;
        }}
        .formula-box {{
            background: #F3F5F3 !important;
            border: 1px solid #CBD7CE;
            border-left: 4px solid {COLORS['accent']};
            color: {COLORS['text']} !important;
            font-family: {MONO};
            font-size: 0.86rem;
            overflow-x: auto;
        }}
        .interview-box {{
            background: #F7F7F5 !important;
            border: 1px solid {COLORS['border']};
            color: {COLORS['text']} !important;
        }}
        .interview-box strong {{
            color: {COLORS['accent']} !important;
        }}
        .section-label {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: {COLORS['text_muted']} !important;
            margin-top: 1.4rem;
            margin-bottom: 0.3rem;
            font-weight: 600;
        }}

        /* Methodology flow */
        .flow-row {{
            display: flex;
            align-items: stretch;
            gap: 8px;
            margin: 0.6rem 0 0.9rem;
        }}
        .flow-step {{
            flex: 1;
            background: #FFFFFF !important;
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 11px 8px;
            text-align: center;
            font-size: 0.82rem;
            font-weight: 600;
            color: {COLORS['text']} !important;
            box-shadow: 0 1px 2px rgba(31,31,29,0.03);
        }}
        .flow-arrow {{
            align-self: center;
            color: {COLORS['text_muted']} !important;
            font-size: 1.1rem;
            font-weight: 600;
        }}

        div[data-testid="stMetricValue"] {{
            font-family: {MONO};
            color: {COLORS['text']} !important;
        }}

        /* Expander text and body copy */
        [data-testid="stExpander"] {{
            border: 1px solid {COLORS['border']} !important;
            border-radius: 9px !important;
            background: #FFFFFF !important;
        }}
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary * {{
            color: {COLORS['text']} !important;
        }}
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] * {{
            color: {COLORS['text']} !important;
        }}

        /* Native Streamlit toolbar/menu: keep it readable when it is opened.
           This prevents a dark browser/theme surface from looking like part
           of the dashboard. */
        [data-testid="stToolbar"],
        [data-testid="stToolbar"] > div,
        [data-testid="stToolbar"] [role="menu"],
        [data-testid="stToolbar"] [role="menuitem"],
        [data-testid="stMainMenu"],
        [data-testid="stMainMenu"] > div,
        [data-testid="stMainMenu"] [role="menu"],
        [data-testid="stMainMenu"] [role="menuitem"],
        [data-baseweb="popover"] > div {{
            background: #FFFFFF !important;
            color: {COLORS['text']} !important;
        }}
        [data-testid="stToolbar"] button,
        [data-testid="stToolbar"] button *,
        [data-testid="stMainMenu"] button,
        [data-testid="stMainMenu"] button *,
        [data-testid="stMainMenu"] [role="menuitem"] * {{
            color: {COLORS['text']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = ""):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(status: str) -> str:
    color = STATUS_COLOR.get(status, COLORS["text_muted"])
    bg = STATUS_BG.get(status, COLORS["panel"])
    return f'<span class="pill" style="color:{color};background:{bg};">{status}</span>'


def note(text: str):
    st.markdown(f'<div class="note-box">{text}</div>', unsafe_allow_html=True)


def warn(text: str):
    st.markdown(f'<div class="warn-box">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cached loaders - all read-only, all straight from processed/analytical
# ---------------------------------------------------------------------------
@st.cache_data
def load_driver_scores() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "driver_safety_scores.csv")


@st.cache_data
def load_vehicle_health() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "vehicle_health.csv")


@st.cache_data
def load_drivers() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "drivers.csv")


@st.cache_data
def load_vehicles() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "vehicles.csv")


@st.cache_data
def load_trips() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "trips.csv", parse_dates=["Trip_Date"])


@st.cache_data
def load_telemetry() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "telemetry.csv", parse_dates=["Timestamp"])


@st.cache_data
def load_driver_trip_features() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "driver_trip_features.csv")


@st.cache_data
def load_json(name: str) -> dict:
    with open(DATA_DIR / name) as f:
        return json.load(f)


@st.cache_data
def load_safety_validation() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "safety_score_validation_checks.csv")


@st.cache_data
def load_vehicle_validation() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "vehicle_health_validation_checks.csv")


@st.cache_data
def load_feature_validation() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "feature_validation_checks.csv")


@st.cache_data
def load_overlaps_driver() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "trip_overlaps_driver.csv")


@st.cache_data
def load_overlaps_vehicle() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "trip_overlaps_vehicle.csv")


def fleet_plot_layout(fig, height=360):
    """Shared, restrained Plotly styling used across every chart in the app."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family=FONT, size=12, color=COLORS["text"]),
        title_font=dict(family=FONT, size=14, color=COLORS["text"]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="white", font_family=FONT, font_color=COLORS["text"]),
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=COLORS["grid"], zeroline=False)
    return fig
