"""
Southlake Medical AI Agent — Custom Styling
"""

CUSTOM_CSS = """
<style>
    /* ─── Google Fonts ─── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* ─── Global ─── */
    .stApp {
        font-family: 'DM Sans', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* ─── Hero Card ─── */
    .hero-card {
        background: linear-gradient(135deg, #0052A5 0%, #0077CC 50%, #00A3E0 100%);
        color: white;
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .hero-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: rgba(255,255,255,0.06);
        border-radius: 50%;
    }
    .hero-card h1 { color: white !important; margin-bottom: 0.5rem; font-size: 2rem !important; }
    .hero-card p { color: rgba(255,255,255,0.9); font-size: 1.05rem; margin: 0; }
    
    /* ─── Metric Cards ─── */
    .metric-row {
        display: flex;
        gap: 1rem;
        margin: 1.5rem 0;
    }
    .metric-card {
        flex: 1;
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .metric-card .number {
        font-size: 2rem;
        font-weight: 700;
        color: #0066CC;
    }
    .metric-card .label {
        font-size: 0.85rem;
        color: #64748B;
        margin-top: 4px;
    }
    
    /* ─── Status Badges ─── */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .badge-green { background: #DCFCE7; color: #166534; }
    .badge-yellow { background: #FEF9C3; color: #854D0E; }
    .badge-red { background: #FEE2E2; color: #991B1B; }
    .badge-blue { background: #DBEAFE; color: #1E40AF; }
    
    /* ─── Info Panel ─── */
    .info-panel {
        background: #F0F7FF;
        border-left: 4px solid #0066CC;
        padding: 1rem 1.25rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
        font-size: 0.95rem;
    }
    
    /* ─── Result Card ─── */
    .result-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .result-card h3 {
        margin-top: 0;
        color: #1A1A2E;
    }
    
    /* ─── Risk Level Banners ─── */
    .risk-green {
        background: linear-gradient(90deg, #22C55E, #16A34A);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        text-align: center;
        font-size: 1.1rem;
    }
    .risk-yellow {
        background: linear-gradient(90deg, #EAB308, #CA8A04);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        text-align: center;
        font-size: 1.1rem;
    }
    .risk-red {
        background: linear-gradient(90deg, #EF4444, #DC2626);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        text-align: center;
        font-size: 1.1rem;
    }
    
    /* ─── Score Breakdown ─── */
    .score-breakdown {
        display: flex;
        gap: 0.75rem;
        margin: 1rem 0;
    }
    .score-item {
        flex: 1;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .score-item .score-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0066CC;
    }
    .score-item .score-label {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 2px;
    }
    
    /* ─── Patient Case Card ─── */
    .case-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.75rem 0;
        border-left: 4px solid #0066CC;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .case-card-red { border-left-color: #EF4444; }
    .case-card-yellow { border-left-color: #EAB308; }
    .case-card-green { border-left-color: #22C55E; }
    
    /* ─── Transport Node ─── */
    .transport-node {
        background: #FFF7ED;
        border: 1px solid #FED7AA;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .transport-node .node-name {
        font-weight: 600;
        color: #9A3412;
    }
    .transport-node .node-distance {
        font-size: 0.85rem;
        color: #C2410C;
    }
    
    /* ─── Disclaimer ─── */
    .disclaimer {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 0.85rem;
        color: #92400E;
        margin: 1rem 0;
    }
    
    /* ─── Safety Banner ─── */
    .safety-banner {
        background: #FEF2F2;
        border: 2px solid #FECACA;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        margin: 1rem 0;
    }
    .safety-banner strong { color: #991B1B; }
    
    /* ─── Clean up Streamlit defaults ─── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 500;
    }
    
    /* ─── Sidebar branding ─── */
    [data-testid="stSidebar"] {
        background: #FAFBFC;
        font-size: 1.1rem;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        font-size: 1.15rem !important;
        padding: 0.6rem 1rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] span {
        font-size: 1.15rem !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] div {
        font-size: 1.05rem;
    }
</style>
"""


def inject_css():
    """Inject custom CSS into Streamlit page."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def risk_badge(level: str) -> str:
    """Return HTML for a colored risk badge."""
    cls = {
        "Green": "badge-green",
        "Yellow": "badge-yellow",
        "Red": "badge-red",
    }.get(level, "badge-blue")
    return f'<span class="badge {cls}">{level}</span>'


def risk_circle(level: str) -> str:
    """Return colored circle emoji + label for risk level."""
    mapping = {
        "Green": "🟢 Green / Low",
        "Yellow": "🟡 Yellow / Moderate",
        "Red": "🔴 Red / Urgent",
    }
    return mapping.get(level, level)


def risk_circle_short(level: str) -> str:
    """Return colored circle emoji + short label."""
    mapping = {
        "Green": "🟢 Green",
        "Yellow": "🟡 Yellow",
        "Red": "🔴 Red",
    }
    return mapping.get(level, level)


def format_risk_column(df, col: str = "risk_level"):
    """Replace risk_level text with colored circle labels in a DataFrame (returns copy)."""
    import pandas as pd
    df = df.copy()
    if col in df.columns:
        df[col] = df[col].map(lambda x: risk_circle_short(x) if isinstance(x, str) else x)
    return df


def risk_banner(level: str, message: str) -> str:
    """Return HTML for a full-width risk banner."""
    cls = f"risk-{level.lower()}"
    return f'<div class="{cls}">{message}</div>'


def score_breakdown_html(pain: int, age_risk: int, ai_sev: int, total: int) -> str:
    """Return HTML for the triage score breakdown."""
    return f"""
    <div class="score-breakdown">
        <div class="score-item">
            <div class="score-value">{age_risk}</div>
            <div class="score-label">Age Risk 60%<br>(0-60)</div>
        </div>
        <div class="score-item">
            <div class="score-value">{pain}</div>
            <div class="score-label">Pain 20%<br>(0-20)</div>
        </div>
        <div class="score-item">
            <div class="score-value">{ai_sev}</div>
            <div class="score-label">AI Severity 20%<br>(0-20)</div>
        </div>
        <div class="score-item">
            <div class="score-value" style="color: {'#EF4444' if total >= 60 else '#EAB308' if total >= 30 else '#22C55E'}">{total}</div>
            <div class="score-label">Total<br>(0-100)</div>
        </div>
    </div>
    """
