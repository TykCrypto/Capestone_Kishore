"""Cognizant-inspired brand palette and shared Streamlit chrome.

Single source of truth for colors/fonts. Every page and chart pulls from
here so the visual identity never drifts between sections.
"""

PRIMARY = "#0033A0"        # Cognizant blue
ACCENT = "#00A9E0"         # Cognizant cyan
DARK_NAVY = "#001B4D"
BACKGROUND = "#F5F7FA"
CARD_BG = "#FFFFFF"

RISK_LOW = "#2E7D32"
RISK_MEDIUM = "#F9A825"
RISK_HIGH = "#C62828"

RISK_COLOR_MAP = {"LOW": RISK_LOW, "MEDIUM": RISK_MEDIUM, "HIGH": RISK_HIGH}

CATEGORICAL_SEQUENCE = [PRIMARY, ACCENT, RISK_MEDIUM, RISK_HIGH, DARK_NAVY, RISK_LOW]

FONT_STACK = '"Segoe UI", Roboto, sans-serif'


def inject_custom_css(st) -> None:
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{ font-family: {FONT_STACK}; }}
        .block-container {{ padding-top: 1.5rem; }}
        div[data-testid="stSidebar"] {{ background-color: {DARK_NAVY}; }}
        div[data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
        .kpi-card {{
            background-color: {CARD_BG};
            border-radius: 10px;
            padding: 1rem 1.25rem;
            border-left: 6px solid {PRIMARY};
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}
        .kpi-label {{ font-size: 0.8rem; color: #5A6B87; text-transform: uppercase; letter-spacing: .04em; }}
        .kpi-value {{ font-size: 1.9rem; font-weight: 700; color: {DARK_NAVY}; }}
        h1, h2, h3 {{ color: {DARK_NAVY}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(st, label: str, value, accent: str = PRIMARY) -> None:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color:{accent};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(st, items: list[tuple[str, object]], accent: str = PRIMARY) -> None:
    """items: list of (label, value) rendered as an evenly spaced KPI row."""
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            kpi_card(st, label, value, accent)
