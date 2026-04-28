"""
Scuffers AI Ops Control Tower — premium dark UI · v0.5
- Real Scuffers logo via load_logo() (drop assets/scuffers_logo.png to override)
- Robust data cleaning + Data Health diagnostics
- Business-friendly naming everywhere
- Executive bullet-style explanations
- Bigger charts (pitch-ready)
- NEW v0.5: hot Shipping Status API integration with caching, fallback,
  and "Decision Delta" UI showing how the API changes priorities.

Run: streamlit run app.py
"""
from __future__ import annotations

import base64
import concurrent.futures as cf
import io
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


# ============================================================================
# 1) PAGE CONFIG + GLOBAL CSS
# ============================================================================
st.set_page_config(
    page_title="Scuffers · AI Ops Control Tower",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRAND = {
    "bg":           "#0A0E1A",
    "surface":      "#121829",
    "surface_2":    "#161D33",
    "border":       "#1F2A44",
    "border_soft":  "#26314D",
    "text":         "#F1F5F9",
    "text_muted":   "#94A3B8",
    "text_dim":     "#64748B",
    "primary":      "#38BDF8",
    "primary_deep": "#0EA5E9",
    "violet":       "#A855F7",
    "neon":         "#4ADE80",
    "amber":        "#FBBF24",
    "danger":       "#F87171",
    "critical":     "#F43F5E",
}


def _fmt(html: str) -> str:
    """Flatten HTML so Streamlit's markdown parser never treats indented lines as code blocks.
    Strips leading whitespace from every line and drops empty lines.
    """
    return "".join(line.strip() for line in html.splitlines() if line.strip())


CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: {BRAND['bg']}; color: {BRAND['text']};
}}
.stApp {{
    background:
      radial-gradient(1200px 600px at 8% -10%, rgba(56,189,248,0.14), transparent 60%),
      radial-gradient(1000px 600px at 100% 0%, rgba(168,85,247,0.10), transparent 60%),
      {BRAND['bg']};
}}
.main .block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1480px; }}
h1, h2, h3, h4 {{ font-family: 'Space Grotesk', 'Inter', sans-serif; color: {BRAND['text']}; letter-spacing: -0.015em; }}
h2 {{ font-size: 1.45rem; font-weight: 600; margin: 2rem 0 1rem 0; }}
h3 {{ font-size: 1.05rem; font-weight: 600; margin: 1rem 0 0.6rem 0; }}

/* ---------- HERO ---------- */
.hero {{
    position: relative;
    background:
      radial-gradient(900px 420px at 0% 0%, rgba(56,189,248,0.18), transparent 60%),
      radial-gradient(800px 420px at 100% 100%, rgba(168,85,247,0.22), transparent 60%),
      linear-gradient(135deg, #0B1228 0%, #161D33 100%);
    border: 1px solid {BRAND['border']}; border-radius: 22px;
    padding: 2rem 2.4rem 2rem 2.4rem; margin-bottom: 1.8rem; overflow: hidden;
}}
.hero::after {{
    content: ""; position: absolute; right: -120px; top: -120px;
    width: 380px; height: 380px;
    background: radial-gradient(circle, rgba(74,222,128,0.20), transparent 65%);
    pointer-events: none;
}}
.hero-top {{ display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1.4rem; }}
.hero-logo {{ height: 52px; color: {BRAND['text']}; display:flex; align-items:center; }}
.hero-logo svg, .hero-logo img {{ height: 52px; width: auto; }}
.hero-logo .badge-internal {{
    margin-left: 1rem; padding: 0.36rem 0.78rem;
    border-radius: 999px; font-size: 0.66rem; font-weight: 700;
    letter-spacing: 0.16em; text-transform: uppercase;
    color: {BRAND['primary']};
    background: rgba(56,189,248,0.10); border: 1px solid rgba(56,189,248,0.35);
}}
.tag-pill {{
    display:inline-flex; align-items:center; gap: 0.5rem;
    padding: 0.4rem 0.85rem; border-radius: 999px;
    background: rgba(74,222,128,0.10); border: 1px solid rgba(74,222,128,0.35);
    color: {BRAND['neon']};
    font-size: 0.74rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
}}
.tag-pill .dot {{ width:7px; height:7px; border-radius:50%; background:{BRAND['neon']}; box-shadow:0 0 12px {BRAND['neon']}; animation: pulse 1.6s infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.45}} }}
.hero h1 {{
    font-size: 2.85rem; font-weight: 700; margin: 0.2rem 0 0.5rem 0; line-height: 1.05;
    background: linear-gradient(90deg, #F1F5F9 0%, #BAE6FD 60%, #DDD6FE 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}}
.hero-sub {{ color: #CBD5E1; font-size: 1.08rem; max-width: 800px; margin: 0; line-height: 1.5; }}
.hero-meta {{ margin-top: 1.3rem; display:flex; flex-wrap: wrap; gap: 1.8rem; color: {BRAND['text_dim']}; font-size: 0.85rem; }}
.hero-meta b {{ color: {BRAND['text']}; font-weight: 600; }}

/* ---------- SECTION HEADER ---------- */
.section-head {{ display:flex; align-items: baseline; justify-content: space-between; margin: 2.2rem 0 1rem 0; gap: 1rem; }}
.section-head h2 {{ margin: 0; }}
.section-head .meta {{ color: {BRAND['text_dim']}; font-size: 0.88rem; text-align: right; }}
.section-head .eyebrow {{ color: {BRAND['primary']}; font-size: 0.74rem; letter-spacing: 0.18em; text-transform: uppercase; font-weight: 700; margin-bottom: 0.35rem; }}

/* ---------- KPI ---------- */
.kpi-grid {{ display:grid; grid-template-columns: repeat(4, 1fr); gap: 1.1rem; }}
@media (max-width: 1100px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
.kpi {{
    background: linear-gradient(160deg, {BRAND['surface']} 0%, {BRAND['surface_2']} 100%);
    border: 1px solid {BRAND['border']}; border-radius: 16px;
    padding: 1.2rem 1.3rem; position: relative; overflow: hidden;
    transition: transform 0.15s ease, border-color 0.15s ease;
}}
.kpi:hover {{ transform: translateY(-1px); border-color: {BRAND['border_soft']}; }}
.kpi::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--accent, {BRAND['primary']}); }}
.kpi-head {{ display:flex; align-items:center; justify-content:space-between; }}
.kpi-icon {{
    width: 34px; height: 34px; border-radius: 9px;
    display:flex; align-items:center; justify-content:center;
    font-size: 1.2rem; background: var(--icon-bg, rgba(56,189,248,0.10));
    color: var(--accent, {BRAND['primary']}); border: 1px solid var(--icon-border, rgba(56,189,248,0.25));
}}
.kpi-label {{ font-size: 0.72rem; color: {BRAND['text_muted']}; text-transform: uppercase; letter-spacing: 0.10em; font-weight: 600; }}
.kpi-value {{ font-family: 'Space Grotesk', sans-serif; font-size: 2.6rem; font-weight: 700; color: {BRAND['text']}; line-height: 1.05; margin: 0.6rem 0 0.3rem 0; }}
.kpi-desc {{ font-size: 0.84rem; color: {BRAND['text_dim']}; line-height: 1.4; }}
.kpi.bad     {{ --accent: {BRAND['critical']}; --icon-bg: rgba(244,63,94,0.10); --icon-border: rgba(244,63,94,0.30); }}
.kpi.warn    {{ --accent: {BRAND['amber']};    --icon-bg: rgba(251,191,36,0.10); --icon-border: rgba(251,191,36,0.30); }}
.kpi.primary {{ --accent: {BRAND['primary']};  --icon-bg: rgba(56,189,248,0.10); --icon-border: rgba(56,189,248,0.30); }}
.kpi.violet  {{ --accent: {BRAND['violet']};   --icon-bg: rgba(168,85,247,0.10); --icon-border: rgba(168,85,247,0.30); }}

/* ---------- DATA HEALTH ---------- */
.health-grid {{ display:grid; grid-template-columns: repeat(3, 1fr); gap: 0.9rem; }}
@media (max-width: 1100px) {{ .health-grid {{ grid-template-columns: 1fr 1fr; }} }}
.health-card {{ background: {BRAND['surface']}; border: 1px solid {BRAND['border']}; border-radius: 12px; padding: 0.85rem 1.05rem; display:flex; align-items: flex-start; gap: 0.7rem; }}
.health-dot {{ width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; flex: 0 0 10px; }}
.health-dot.ok       {{ background: {BRAND['neon']};   box-shadow: 0 0 8px {BRAND['neon']}; }}
.health-dot.cleaned  {{ background: {BRAND['primary']}; box-shadow: 0 0 8px {BRAND['primary']}; }}
.health-dot.warning  {{ background: {BRAND['amber']};  box-shadow: 0 0 8px {BRAND['amber']}; }}
.health-dot.missing  {{ background: {BRAND['critical']}; box-shadow: 0 0 8px {BRAND['critical']}; }}
.health-name {{ font-weight: 600; color: {BRAND['text']}; font-size: 0.96rem; }}
.health-status {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; margin-left: 0.5rem; }}
.health-status.ok      {{ color: {BRAND['neon']}; }}
.health-status.cleaned {{ color: {BRAND['primary']}; }}
.health-status.warning {{ color: {BRAND['amber']}; }}
.health-status.missing {{ color: {BRAND['critical']}; }}
.health-meta {{ color: {BRAND['text_muted']}; font-size: 0.8rem; margin-top: 0.25rem; line-height: 1.4; }}
.health-fix  {{ color: {BRAND['text_dim']};   font-size: 0.76rem; margin-top: 0.35rem; line-height: 1.45; }}
.health-fix b {{ color: {BRAND['text_muted']}; }}

/* ---------- TOP 10 TABLE ---------- */
.rank-table {{ background: {BRAND['surface']}; border: 1px solid {BRAND['border']}; border-radius: 16px; overflow: hidden; }}
.rank-row {{ display:grid; grid-template-columns: 56px 220px 1fr 140px 90px 100px; gap: 1rem; align-items: center; padding: 0.95rem 1.2rem; border-bottom: 1px solid {BRAND['border']}; transition: background 0.12s ease; }}
.rank-row:hover {{ background: rgba(56,189,248,0.05); }}
.rank-row:last-child {{ border-bottom: none; }}
.rank-row.head {{ background: rgba(56,189,248,0.04); color: {BRAND['text_muted']}; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; padding: 0.7rem 1.2rem; }}
.rank-num {{ font-family: 'Space Grotesk', sans-serif; font-size: 1.7rem; font-weight: 700; color: {BRAND['text_dim']}; }}
.rank-num.top {{ color: {BRAND['primary']}; }}
.rank-num.elite {{ background: linear-gradient(135deg, {BRAND['primary']}, {BRAND['violet']}); -webkit-background-clip: text; background-clip: text; color: transparent; }}
.cell-title {{ display:flex; flex-direction:column; gap: 0.2rem; min-width: 0; }}
.cell-title .t {{ font-size: 0.98rem; font-weight: 600; color: {BRAND['text']}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.cell-title .meta {{ font-size: 0.78rem; color: {BRAND['text_dim']}; }}
.cell-title .meta code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: {BRAND['text_muted']}; background: rgba(56,189,248,0.06); padding: 0.05rem 0.4rem; border-radius: 4px; }}
.tag-row {{ display:flex; flex-wrap: wrap; gap: 0.32rem; margin-top: 0.32rem; }}
.tag {{ display:inline-flex; align-items:center; padding: 0.18rem 0.5rem; border-radius: 5px; font-size: 0.72rem; font-weight: 600; border: 1px solid; }}
.tag-stock  {{ color: #FCA5A5; background: rgba(244,63,94,0.10); border-color: rgba(244,63,94,0.25); }}
.tag-vip    {{ color: #D8B4FE; background: rgba(168,85,247,0.10); border-color: rgba(168,85,247,0.25); }}
.tag-demand {{ color: #7DD3FC; background: rgba(56,189,248,0.10); border-color: rgba(56,189,248,0.25); }}
.tag-camp   {{ color: #93C5FD; background: rgba(96,165,250,0.10); border-color: rgba(96,165,250,0.25); }}
.tag-ticket {{ color: #FCD34D; background: rgba(251,191,36,0.10); border-color: rgba(251,191,36,0.25); }}
.tag-other  {{ color: #CBD5E1; background: rgba(148,163,184,0.10); border-color: rgba(148,163,184,0.20); }}
.score-pill {{ display:inline-flex; align-items:center; justify-content:center; gap:0.35rem; min-width: 56px; padding: 0.42rem 0.72rem; border-radius: 8px; font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.02rem; border: 1px solid; }}
.score-pill.crit {{ background: rgba(244,63,94,0.14);  color: #FCA5A5; border-color: rgba(244,63,94,0.40); }}
.score-pill.high {{ background: rgba(251,191,36,0.14); color: #FCD34D; border-color: rgba(251,191,36,0.40); }}
.score-pill.med  {{ background: rgba(56,189,248,0.14); color: #7DD3FC; border-color: rgba(56,189,248,0.40); }}
.chip {{ display:inline-flex; align-items:center; gap:0.35rem; padding: 0.3rem 0.65rem; border-radius: 7px; font-size: 0.76rem; font-weight: 600; border: 1px solid; white-space: nowrap; }}
.chip-blue   {{ background: rgba(56,189,248,0.10);  color: #7DD3FC; border-color: rgba(56,189,248,0.30); }}
.chip-violet {{ background: rgba(168,85,247,0.10);  color: #D8B4FE; border-color: rgba(168,85,247,0.30); }}
.chip-amber  {{ background: rgba(251,191,36,0.10);  color: #FCD34D; border-color: rgba(251,191,36,0.30); }}
.chip-red    {{ background: rgba(244,63,94,0.10);   color: #FCA5A5; border-color: rgba(244,63,94,0.30); }}
.chip-green  {{ background: rgba(74,222,128,0.10);  color: #86EFAC; border-color: rgba(74,222,128,0.30); }}
.chip-gray   {{ background: rgba(148,163,184,0.10); color: #CBD5E1; border-color: rgba(148,163,184,0.25); }}
.conf-bar {{ height: 6px; border-radius: 3px; background: {BRAND['border']}; position: relative; overflow: hidden; margin-top: 0.28rem; }}
.conf-bar > span {{ display:block; height: 100%; background: linear-gradient(90deg, {BRAND['primary']}, {BRAND['neon']}); border-radius: 3px; }}
.conf-text {{ font-size: 0.76rem; color: {BRAND['text_muted']}; font-weight: 600; }}
.auto-flag {{ display:inline-flex; align-items:center; gap:0.3rem; font-size: 0.74rem; color: {BRAND['neon']}; font-weight: 600; }}
.auto-flag.no {{ color: {BRAND['text_dim']}; }}

/* ---------- REASON CARDS ---------- */
.reason-grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
@media (max-width: 1100px) {{ .reason-grid {{ grid-template-columns: 1fr; }} }}
.reason {{ background: {BRAND['surface']}; border: 1px solid {BRAND['border']}; border-left: 4px solid var(--accent, {BRAND['primary']}); border-radius: 12px; padding: 1.05rem 1.2rem; transition: border-color 0.15s ease; }}
.reason:hover {{ border-color: {BRAND['border_soft']}; }}
.reason-head {{ display:flex; align-items:center; justify-content:space-between; gap: 0.6rem; margin-bottom: 0.55rem; }}
.reason-target {{ font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: {BRAND['text_muted']}; }}
.reason-title {{ font-weight: 600; font-size: 0.98rem; color: {BRAND['text']}; margin-top: 0.2rem; margin-bottom: 0.6rem; }}
.bullet-block {{ margin-top: 0.5rem; }}
.bullet-label {{ display:block; font-size: 0.7rem; color: {BRAND['text_dim']}; text-transform: uppercase; letter-spacing: 0.14em; margin-bottom: 0.4rem; font-weight: 700; }}
.bullet-list {{ list-style: none; padding: 0; margin: 0; display:flex; flex-wrap: wrap; gap: 0.35rem 0.6rem; }}
.bullet-list li {{ position: relative; padding-left: 1rem; color: {BRAND['text_muted']}; font-size: 0.88rem; line-height: 1.45; flex: 1 1 45%; }}
.bullet-list li::before {{ content: "•"; position: absolute; left: 0; color: var(--accent, {BRAND['primary']}); font-weight: 700; }}
.bullet-list.impact li::before {{ color: {BRAND['neon']}; }}
.reason.vip    {{ --accent: {BRAND['violet']}; }}
.reason.stock  {{ --accent: {BRAND['critical']}; }}
.reason.ticket {{ --accent: {BRAND['amber']}; }}
.reason.camp   {{ --accent: {BRAND['primary']}; }}
.reason-owner {{ margin-top: 0.7rem; padding-top: 0.55rem; border-top: 1px dashed {BRAND['border']}; font-size: 0.78rem; color: {BRAND['text_dim']}; }}
.reason-owner b {{ color: {BRAND['text_muted']}; }}

/* ---------- CHARTS ---------- */
.chart-grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 1.1rem; }}
@media (max-width: 1100px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
.chart-card {{ background: {BRAND['surface']}; border: 1px solid {BRAND['border']}; border-radius: 14px; padding: 0.6rem 0.8rem 0.4rem 0.8rem; }}

/* ---------- SIDEBAR ---------- */
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #0B1124 0%, #0A0E1A 100%); border-right: 1px solid {BRAND['border']}; }}
section[data-testid="stSidebar"] .stMarkdown h3 {{ font-size: 0.74rem; color: {BRAND['text_muted']}; text-transform: uppercase; letter-spacing: 0.14em; font-weight: 700; margin: 1.3rem 0 0.55rem 0; }}
.sb-brand {{ display:flex; align-items:center; gap:0.55rem; padding: 0.4rem 0 0.9rem 0; margin-bottom: 0.7rem; border-bottom: 1px solid {BRAND['border']}; }}
.sb-brand .logo {{ height: 36px; color: {BRAND['text']}; display:flex; align-items:center; }}
.sb-brand .logo svg, .sb-brand .logo img {{ height: 36px; width: auto; }}
.sb-help {{ background: rgba(56,189,248,0.07); border: 1px solid rgba(56,189,248,0.22); color: {BRAND['text_muted']}; font-size: 0.84rem; border-radius: 10px; padding: 0.7rem 0.8rem; line-height: 1.45; margin-bottom: 1rem; }}
.sb-help b {{ color: {BRAND['primary']}; }}

[data-testid="stExpander"] {{ background: {BRAND['surface']}; border: 1px solid {BRAND['border']}; border-radius: 12px; }}
[data-testid="stFileUploader"] section {{ background: {BRAND['surface']}; border: 1px dashed {BRAND['border_soft']}; border-radius: 10px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 0.4rem; }}
.stTabs [data-baseweb="tab"] {{ background: {BRAND['surface']}; border-radius: 8px; padding: 0.4rem 0.9rem; }}
footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
.scuffers-footer {{ margin-top: 2.6rem; padding-top: 1rem; border-top: 1px solid {BRAND['border']}; color: {BRAND['text_dim']}; font-size: 0.8rem; text-align: center; display:flex; align-items:center; justify-content:center; gap: 0.6rem; }}
.scuffers-footer .footer-logo {{ height: 18px; color: {BRAND['text_dim']}; display:inline-flex; align-items:center; opacity: 0.65; }}
.scuffers-footer .footer-logo svg, .scuffers-footer .footer-logo img {{ height: 18px; width: auto; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================================
# 2) BRANDING — load_logo + dataset/action labels
# ============================================================================
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def load_logo(variant: str = "light") -> str:
    """Returns inline HTML for the Scuffers logo. Drop your real PNG at:
       assets/scuffers_logo_light.png (preferred — no auto-invert)
       or assets/scuffers_logo.png (auto-invert applied for dark UI).
       Falls back to assets/scuffers_logo.svg, then to a minimal embedded wordmark.
    """
    color = "#F1F5F9" if variant == "light" else "#0A0E1A"
    invert = "filter: invert(1) brightness(2);" if variant == "light" else ""

    light_png = os.path.join(ASSETS_DIR, "scuffers_logo_light.png")
    if os.path.exists(light_png):
        with open(light_png, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{b64}" alt="Scuffers" />'

    default_png = os.path.join(ASSETS_DIR, "scuffers_logo.png")
    if os.path.exists(default_png):
        with open(default_png, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{b64}" alt="Scuffers" style="{invert}" />'

    svg_path = os.path.join(ASSETS_DIR, "scuffers_logo.svg")
    if os.path.exists(svg_path):
        with open(svg_path, "r", encoding="utf-8") as f:
            svg = f.read()
        return f'<span style="color:{color}; display:inline-block; line-height:0;">{svg}</span>'

    return (
        f'<svg height="48" viewBox="0 0 720 200" xmlns="http://www.w3.org/2000/svg" fill="{color}">'
        f'<text x="360" y="148" text-anchor="middle" '
        f'font-family="Space Grotesk, Inter, sans-serif" font-weight="900" font-style="italic" '
        f'font-size="140" letter-spacing="-5">scuffers</text></svg>'
    )


# Business-friendly labels — exposed everywhere
DATASET_LABELS = {
    "orders":          "Pedidos en curso",
    "customers":       "Clientes",
    "inventory":       "Stock disponible",
    "support_tickets": "Incidencias clientes",
    "campaigns":       "Campañas activas",
    "order_items":     "Detalle de pedido",
}
DATASET_ICONS = {
    "orders": "🛒", "customers": "👤", "inventory": "📦",
    "support_tickets": "🎫", "campaigns": "📣", "order_items": "🧾",
}

ACTION_LABELS = {
    "EXPEDITE_ORDER":    "Expedir pedido urgente",
    "PRIORITIZE_TICKET": "Atender incidencia crítica",
    "RESTOCK_SKU":       "Reponer producto",
    "PAUSE_CAMPAIGN":    "Pausar campaña",
    "PROACTIVE_CONTACT": "Contactar cliente VIP",
    "REVIEW_ORDER":      "Revisar pedido",
}
ACTION_CHIP = {
    "EXPEDITE_ORDER":    ("chip-blue",   "⚡ " + ACTION_LABELS["EXPEDITE_ORDER"]),
    "PRIORITIZE_TICKET": ("chip-amber",  "🎫 " + ACTION_LABELS["PRIORITIZE_TICKET"]),
    "RESTOCK_SKU":       ("chip-red",    "📦 " + ACTION_LABELS["RESTOCK_SKU"]),
    "PAUSE_CAMPAIGN":    ("chip-violet", "⏸ " + ACTION_LABELS["PAUSE_CAMPAIGN"]),
    "PROACTIVE_CONTACT": ("chip-green",  "📞 " + ACTION_LABELS["PROACTIVE_CONTACT"]),
    "REVIEW_ORDER":      ("chip-gray",   "🔍 " + ACTION_LABELS["REVIEW_ORDER"]),
}
OWNER_BY_TYPE = {
    "EXPEDITE_ORDER":    "Operaciones",
    "PRIORITIZE_TICKET": "Atención cliente",
    "RESTOCK_SKU":       "Inventario",
    "PAUSE_CAMPAIGN":    "Marketing",
    "PROACTIVE_CONTACT": "Atención cliente",
    "REVIEW_ORDER":      "Operaciones",
}


# ============================================================================
# 3) DATA CLEANING LAYER
# ============================================================================
COLUMN_ALIASES: Dict[str, List[str]] = {
    "order_id":                  ["orderid", "id_pedido", "pedido_id"],
    "customer_id":               ["customerid", "client_id", "cliente_id"],
    "order_status":              ["status", "estado", "order_state"],
    "customer_segment":          ["segment", "tier", "cliente_segmento"],
    "order_value":               ["total", "amount", "order_amount", "valor_pedido"],
    "shipping_method":           ["delivery_method", "envio", "shipping"],
    "shipping_country":          ["country", "pais"],
    "shipping_city":             ["city", "ciudad"],
    "campaign_source":           ["source", "utm_source", "fuente"],
    "created_at":                ["timestamp", "ts", "created", "fecha_creacion"],
    "is_vip":                    ["vip", "vip_flag", "es_vip"],
    "customer_lifetime_value":   ["clv", "lifetime_value", "ltv"],
    "customer_orders_count":     ["orders_count", "n_pedidos", "num_orders"],
    "customer_returns_count":    ["returns_count", "n_devoluciones"],
    "preferred_city":            ["city_pref", "ciudad_preferida"],
    "email_opt_in":              ["opt_in", "newsletter"],
    "sku":                       ["product_sku", "item_sku", "code"],
    "product_name":              ["product", "name", "producto"],
    "category":                  ["product_category", "categoria"],
    "size":                      ["talla"],
    "unit_price":                ["price", "precio"],
    "warehouse_stock":           ["stock", "warehouse"],
    "inventory_available_units": ["available", "available_units", "stock_disponible"],
    "inventory_reserved_units":  ["reserved", "reserved_units", "stock_reservado"],
    "inventory_incoming_units":  ["incoming", "incoming_units", "stock_entrante"],
    "inventory_incoming_eta":    ["eta", "incoming_eta"],
    "sell_through_rate_last_hour": ["sell_through", "sell_rate"],
    "product_page_views_last_hour": ["page_views", "views_hour"],
    "conversion_rate_last_hour": ["cvr", "conversion_rate_hour"],
    "ticket_id":                 ["id_ticket", "incidencia_id"],
    "channel":                   ["ticket_channel", "canal"],
    "support_ticket_message":    ["message", "ticket_message", "mensaje"],
    "support_ticket_urgency":    ["urgency", "priority", "priority_level", "urgencia"],
    "support_ticket_sentiment":  ["sentiment", "tono"],
    "campaign_id":               ["id_campaign", "campania_id"],
    "target_sku":                ["sku_target", "target"],
    "target_city":               ["city_target"],
    "campaign_intensity":        ["intensity", "intensidad"],
    "budget_spent":              ["spent", "presupuesto_gastado"],
    "traffic_growth":            ["growth", "trafico"],
    "conversion_rate":           ["tasa_conversion"],
    "started_at":                ["start", "fecha_inicio"],
    "quantity":                  ["qty", "cantidad"],
}

# Two-pass alias resolution: canonicals shadow conflicting aliases of other canonicals.
ALIAS_TO_CANONICAL: Dict[str, str] = {}
CANONICALS = set(COLUMN_ALIASES.keys())
for canonical, aliases in COLUMN_ALIASES.items():
    for a in aliases:
        if a.lower() in CANONICALS and a.lower() != canonical.lower():
            continue
        ALIAS_TO_CANONICAL[a.lower()] = canonical
for canonical in COLUMN_ALIASES.keys():
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical

# Per-dataset protected columns (legitimate name overlaps between datasets)
DATASET_PROTECTED_COLS: Dict[str, set] = {
    "campaigns": {"status"},  # campaigns.status is its own field, not order_status
}

URGENCY_MAP   = {"low": 1, "medium": 2, "med": 2, "normal": 2, "moderate": 2, "high": 3, "alta": 3, "critical": 4, "urgent": 4, "critica": 4}
SENTIMENT_MAP = {"positive": 1, "pos": 1, "neutral": 0, "neg": -1, "negative": -1, "very_negative": -2, "angry": -2, "negativo": -1}
INTENSITY_MAP = {"low": 1, "medium": 2, "med": 2, "high": 3, "very_high": 4, "extreme": 5, "alta": 3, "muy_alta": 4}
STATUS_MAP    = {"pago": "paid", "pagado": "paid", "en_proceso": "processing", "pendiente": "pending",
                 "entregado": "delivered", "cancelado": "cancelled", "devuelto": "returned"}


@dataclass
class CleaningLog:
    dataset: str
    rows_initial: int = 0
    rows_final: int = 0
    columns_renamed: List[Tuple[str, str]] = field(default_factory=list)
    missing_canonical: List[str] = field(default_factory=list)
    nulls_imputed: Dict[str, int] = field(default_factory=dict)
    categories_standardized: List[str] = field(default_factory=list)
    duplicates_removed: int = 0
    type_coercions: List[str] = field(default_factory=list)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(s).strip().lower().replace(" ", "_"))


def normalize_columns(df: pd.DataFrame, log: CleaningLog,
                     dataset_name: Optional[str] = None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    protected = DATASET_PROTECTED_COLS.get(dataset_name or "", set())
    rename_map = {}
    for col in df.columns:
        if col in protected:
            continue
        slug = _slug(col)
        canon = ALIAS_TO_CANONICAL.get(slug)
        if canon and canon != col:
            rename_map[col] = canon
            log.columns_renamed.append((col, canon))
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def clean_nulls(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip().replace(
            {"": np.nan, "nan": np.nan, "None": np.nan, "null": np.nan, "NULL": np.nan}
        )
    return df


def standardize_categories(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    if "order_status" in df.columns:
        df["order_status"] = df["order_status"].astype(str).str.lower().str.strip().replace(STATUS_MAP)
        log.categories_standardized.append("order_status")
    if "support_ticket_urgency" in df.columns:
        df["support_ticket_urgency"] = df["support_ticket_urgency"].astype(str).str.lower().str.strip()
        log.categories_standardized.append("support_ticket_urgency")
    if "support_ticket_sentiment" in df.columns:
        df["support_ticket_sentiment"] = df["support_ticket_sentiment"].astype(str).str.lower().str.strip()
        log.categories_standardized.append("support_ticket_sentiment")
    if "campaign_intensity" in df.columns:
        df["campaign_intensity"] = df["campaign_intensity"].astype(str).str.lower().str.strip()
        log.categories_standardized.append("campaign_intensity")
    if "shipping_method" in df.columns:
        df["shipping_method"] = df["shipping_method"].astype(str).str.lower().str.strip()
        log.categories_standardized.append("shipping_method")
    if "is_vip" in df.columns:
        df["is_vip"] = df["is_vip"].astype(str).str.lower().isin(["true", "1", "yes", "y", "si", "sí"])
        log.categories_standardized.append("is_vip")
    return df


def infer_missing_values(df: pd.DataFrame, log: CleaningLog,
                         numeric_defaults: Optional[Dict[str, float]] = None,
                         mode_fill_cols: Optional[List[str]] = None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    numeric_defaults = numeric_defaults or {}
    for c in df.columns:
        n = int(df[c].isna().sum())
        if n == 0:
            continue
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            log.nulls_imputed[c] = n
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            fill = numeric_defaults.get(c, df[c].median() if df[c].notna().any() else 0)
            df[c] = df[c].fillna(fill)
            log.nulls_imputed[c] = n
        else:
            if mode_fill_cols and c in mode_fill_cols and df[c].notna().any():
                fill = df[c].mode(dropna=True).iloc[0]
            else:
                fill = "unknown"
            df[c] = df[c].fillna(fill)
            log.nulls_imputed[c] = n
    return df


def resolve_duplicates(df: pd.DataFrame, log: CleaningLog, key: Optional[str] = None) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    before = len(df)
    df = df.drop_duplicates()
    if key and key in df.columns:
        df = df.drop_duplicates(subset=[key], keep="last")
    log.duplicates_removed += before - len(df)
    return df


def coerce_types(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    numeric_cols = ["order_value", "quantity", "unit_price", "warehouse_stock",
                    "inventory_available_units", "inventory_reserved_units",
                    "inventory_incoming_units", "sell_through_rate_last_hour",
                    "product_page_views_last_hour", "conversion_rate_last_hour",
                    "customer_lifetime_value", "customer_orders_count",
                    "customer_returns_count", "budget_spent", "traffic_growth",
                    "conversion_rate"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
            log.type_coercions.append(c)
    for c in ["created_at", "started_at", "inventory_incoming_eta"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
            log.type_coercions.append(c)
    return df


EXPECTED_COLS: Dict[str, List[str]] = {
    "orders":          ["order_id", "customer_id", "order_status", "sku", "quantity", "order_value", "created_at"],
    "customers":       ["customer_id", "is_vip", "customer_lifetime_value"],
    "inventory":       ["sku", "inventory_available_units", "inventory_reserved_units", "product_page_views_last_hour"],
    "support_tickets": ["ticket_id", "order_id", "customer_id", "support_ticket_urgency", "support_ticket_sentiment"],
    "campaigns":       ["campaign_id", "status", "target_sku", "campaign_intensity"],
    "order_items":     ["order_id", "sku", "quantity"],
}


def clean_dataset(name: str, df: Optional[pd.DataFrame]) -> Tuple[pd.DataFrame, CleaningLog]:
    log = CleaningLog(dataset=name)
    if df is None or df.empty:
        return pd.DataFrame(), log
    log.rows_initial = len(df)
    df = normalize_columns(df, log, dataset_name=name)
    df = clean_nulls(df, log)
    df = coerce_types(df, log)
    df = standardize_categories(df, log)

    expected = EXPECTED_COLS.get(name, [])
    log.missing_canonical = [c for c in expected if c not in df.columns]

    if name == "orders":
        df = infer_missing_values(df, log, numeric_defaults={"order_value": 0, "quantity": 1},
                                  mode_fill_cols=["customer_segment", "shipping_method", "campaign_source"])
        df = resolve_duplicates(df, log, key="order_id")
    elif name == "customers":
        df = infer_missing_values(df, log,
                                  numeric_defaults={"customer_lifetime_value": 0,
                                                    "customer_orders_count": 0,
                                                    "customer_returns_count": 0})
        df = resolve_duplicates(df, log, key="customer_id")
    elif name == "inventory":
        df = infer_missing_values(df, log,
                                  numeric_defaults={"inventory_available_units": 0,
                                                    "inventory_reserved_units": 0,
                                                    "inventory_incoming_units": 0})
        df = resolve_duplicates(df, log, key="sku")
    elif name == "support_tickets":
        df = infer_missing_values(df, log, mode_fill_cols=["support_ticket_urgency", "support_ticket_sentiment"])
        df = resolve_duplicates(df, log, key="ticket_id")
    elif name == "campaigns":
        df = infer_missing_values(df, log, numeric_defaults={"budget_spent": 0, "traffic_growth": 0, "conversion_rate": 0})
        df = resolve_duplicates(df, log, key="campaign_id")
    else:
        df = infer_missing_values(df, log)
        df = resolve_duplicates(df, log)

    log.rows_final = len(df)
    return df, log


def health_status(log: CleaningLog) -> str:
    if log.rows_initial == 0:
        return "missing"
    if log.missing_canonical:
        return "warning"
    if log.columns_renamed or log.nulls_imputed or log.duplicates_removed:
        return "cleaned"
    return "ok"


# ============================================================================
# 4) AUXILIARY SCORING COLUMNS
# ============================================================================
def add_score_columns(orders, customers, inventory, tickets, campaigns):
    if tickets is not None and not tickets.empty:
        tickets["urgency_score"] = tickets.get("support_ticket_urgency", "medium")\
            .astype(str).str.lower().map(URGENCY_MAP).fillna(2)
        tickets["sentiment_score"] = tickets.get("support_ticket_sentiment", "neutral")\
            .astype(str).str.lower().map(SENTIMENT_MAP).fillna(0)
    if campaigns is not None and not campaigns.empty:
        campaigns["intensity_score"] = campaigns.get("campaign_intensity", "medium")\
            .astype(str).str.lower().map(INTENSITY_MAP).fillna(2)
    return orders, customers, inventory, tickets, campaigns


# ============================================================================
# 5) ACTION DATACLASS + SCORING ENGINE (UNCHANGED LOGIC)
# ============================================================================
@dataclass
class Action:
    action_type: str
    target_id: str
    title: str
    score: float
    tags: List[str] = field(default_factory=list)
    impact_bullets: List[str] = field(default_factory=list)
    raw_reasons: List[str] = field(default_factory=list)
    confidence: float = 0.7
    owner: str = "Operaciones"
    automation_possible: bool = False
    category: str = "general"


def _safe_get(row, col, default=None):
    if col in row.index and pd.notna(row[col]):
        return row[col]
    return default


def build_master(orders, customers, inventory):
    o = orders.copy() if orders is not None and not orders.empty else pd.DataFrame()
    c = customers.copy() if customers is not None and not customers.empty else pd.DataFrame()
    inv = inventory.copy() if inventory is not None and not inventory.empty else pd.DataFrame()
    if not o.empty and not c.empty and "customer_id" in o and "customer_id" in c:
        o = o.merge(c, on="customer_id", how="left", suffixes=("", "_cust"))
    if not o.empty and not inv.empty and "sku" in o and "sku" in inv:
        o = o.merge(inv, on="sku", how="left", suffixes=("", "_inv"))
    return o


def score_orders(master, tickets, campaigns):
    actions: List[Action] = []
    if master is None or master.empty:
        return actions
    open_tickets_by_order = {}
    if tickets is not None and not tickets.empty:
        for _, t in tickets.iterrows():
            oid = _safe_get(t, "order_id")
            if oid:
                open_tickets_by_order[oid] = {
                    "urgency": _safe_get(t, "urgency_score", 2),
                    "sentiment": _safe_get(t, "sentiment_score", 0),
                }
    active_camp_skus = set()
    if campaigns is not None and not campaigns.empty:
        active = campaigns[campaigns.get("status", "active").astype(str).str.lower() == "active"] \
            if "status" in campaigns.columns else campaigns
        if "target_sku" in active.columns:
            active_camp_skus = set(active["target_sku"].dropna().astype(str))

    for _, r in master.iterrows():
        tags: List[str] = []
        raw: List[str] = []
        used_total, used_present = 0, 0
        order_id = _safe_get(r, "order_id", "?")
        sku = _safe_get(r, "sku", "")
        status = str(_safe_get(r, "order_status", "")).lower()
        is_vip = bool(_safe_get(r, "is_vip", False))
        clv = float(_safe_get(r, "customer_lifetime_value", 0) or 0)
        avail = float(_safe_get(r, "inventory_available_units", 0) or 0)
        reserved = float(_safe_get(r, "inventory_reserved_units", 0) or 0)
        views = float(_safe_get(r, "product_page_views_last_hour", 0) or 0)
        sell_thru = float(_safe_get(r, "sell_through_rate_last_hour", 0) or 0)
        ship_method = str(_safe_get(r, "shipping_method", "")).lower()
        order_value = float(_safe_get(r, "order_value", 0) or 0)
        camp_source = str(_safe_get(r, "campaign_source", "")).lower()

        used_total += 8
        for v in [is_vip, clv, avail, reserved, views, status, ship_method, order_value]:
            if v not in (None, "", 0, False, np.nan):
                used_present += 1

        if status in ("cancelled", "delivered", "refunded", "returned"):
            continue

        base = 0.0
        if status in ("paid", "processing", "pending"):
            base = 35
        if avail <= max(reserved, 1) * 0.5 and avail < 5:
            base += 25; tags.append("Stock crítico")
            raw.append(f"stock crítico ({int(avail)} disp · {int(reserved)} reservados)")
        elif avail <= reserved:
            base += 12; tags.append("Stock bajo"); raw.append("stock por debajo de reservas")
        if is_vip:
            base += 25; tags.append("Cliente VIP"); raw.append("cliente VIP")
        elif clv >= 500:
            base += 15; tags.append("Cliente recurrente"); raw.append(f"CLV alto ({clv:.0f}€)")
        if views >= 2000:
            base += 10; tags.append("Alta demanda"); raw.append(f"alta demanda ({int(views)} views/h)")
        if sell_thru >= 0.5:
            base += 8; tags.append("Sell-through alto"); raw.append("sell-through elevado")
        if ship_method in ("express", "next_day"):
            base += 5; tags.append("Envío express"); raw.append("envío express comprometido")
        if sku in active_camp_skus:
            base += 6; tags.append("Campaña activa"); raw.append("SKU bajo campaña activa")
        if order_id in open_tickets_by_order:
            t = open_tickets_by_order[order_id]
            if t["urgency"] >= 3:
                base += 14; tags.append("Ticket urgente"); raw.append("ticket abierto urgente")
            elif t["sentiment"] < 0:
                base += 8; tags.append("Sentimiento negativo"); raw.append("ticket con sentimiento negativo")

        if base >= 45:
            cat = "vip" if is_vip else ("stock" if avail <= reserved else "general")
            impact_eur = max(order_value, clv * 0.05, 30)
            if is_vip:
                impact_bullets = ["Protege cliente VIP",
                                  f"Salva ~{impact_eur:,.0f}€ del pedido",
                                  "Reduce riesgo de churn y NPS"]
            else:
                impact_bullets = ["Asegura ingreso comprometido",
                                  f"Protege ~{impact_eur:,.0f}€ del pedido",
                                  "Mantiene confianza del cliente"]
            actions.append(Action(
                action_type="EXPEDITE_ORDER", target_id=str(order_id),
                title=f"Expedir pedido {order_id}" + (" · VIP" if is_vip else ""),
                score=min(base, 100), tags=tags, impact_bullets=impact_bullets, raw_reasons=raw,
                confidence=round(used_present / max(used_total, 1), 2),
                owner=OWNER_BY_TYPE["EXPEDITE_ORDER"],
                automation_possible=False, category=cat,
            ))

        if is_vip and order_id not in open_tickets_by_order and avail <= reserved + 1:
            sc = 55 + (10 if clv >= 800 else 0) + (8 if views >= 2000 else 0)
            actions.append(Action(
                action_type="PROACTIVE_CONTACT", target_id=str(order_id),
                title=f"Contactar VIP del pedido {order_id}",
                score=min(sc, 100),
                tags=["Cliente VIP", "Stock al límite", "Sin queja registrada"],
                impact_bullets=["Anticipa incidencia",
                                "Reduce churn de cliente VIP",
                                "Protege CLV a largo plazo"],
                raw_reasons=[f"cliente VIP (CLV {clv:.0f}€)", "stock al límite", "aún sin queja registrada"],
                confidence=0.75, owner=OWNER_BY_TYPE["PROACTIVE_CONTACT"],
                automation_possible=True, category="vip",
            ))

        anomaly_tags, anomaly_raw = [], []
        if order_value > 0 and order_value > 500:
            anomaly_tags.append("Importe alto"); anomaly_raw.append(f"order_value alto ({order_value:.0f}€)")
        if int(_safe_get(r, "quantity", 1) or 1) >= 3:
            anomaly_tags.append("Cantidad alta"); anomaly_raw.append("quantity ≥ 3")
        if camp_source and camp_source not in ("organic", "email", "tiktok", "ig", "instagram", "google", "direct", "nan", "none", "unknown"):
            anomaly_tags.append("Origen no estándar"); anomaly_raw.append(f"campaign_source raro ({camp_source})")
        if order_value == 0 and status not in ("cancelled",):
            anomaly_tags.append("Importe = 0€"); anomaly_raw.append("order_value=0 con pedido no cancelado")
        if len(anomaly_tags) >= 2:
            actions.append(Action(
                action_type="REVIEW_ORDER", target_id=str(order_id),
                title=f"Revisar manualmente pedido {order_id}",
                score=40 + 8 * len(anomaly_tags),
                tags=anomaly_tags,
                impact_bullets=["Reduce riesgo de fraude", "Protege margen operativo"],
                raw_reasons=anomaly_raw,
                confidence=0.6, owner=OWNER_BY_TYPE["REVIEW_ORDER"],
                automation_possible=False, category="general",
            ))
    return actions


def score_tickets(tickets, master):
    actions: List[Action] = []
    if tickets is None or tickets.empty:
        return actions
    vip_ids = set()
    if master is not None and not master.empty and "is_vip" in master.columns:
        vip_ids = set(master[master["is_vip"] == True]["customer_id"].astype(str))
    open_orders = set()
    if master is not None and not master.empty and "order_status" in master.columns:
        open_orders = set(master[master["order_status"].astype(str).str.lower().isin(
            ["paid", "processing", "pending"])]["order_id"].astype(str))

    for _, t in tickets.iterrows():
        urgency = float(_safe_get(t, "urgency_score", 2) or 2)
        sentiment = float(_safe_get(t, "sentiment_score", 0) or 0)
        cid = str(_safe_get(t, "customer_id", ""))
        oid = str(_safe_get(t, "order_id", ""))
        msg = str(_safe_get(t, "support_ticket_message", ""))[:120]

        score = 35
        tags, raw = [], []
        if urgency >= 3:
            score += 25
            tag = "Urgencia crítica" if urgency >= 4 else "Urgencia alta"
            tags.append(tag); raw.append(tag.lower())
        if sentiment < 0:
            score += 18; tags.append("Sentimiento negativo"); raw.append("sentimiento negativo")
        if cid in vip_ids:
            score += 18; tags.append("Cliente VIP"); raw.append("cliente VIP")
        if oid in open_orders:
            score += 10; tags.append("Pedido en curso"); raw.append("pedido aún en curso")

        if score >= 50:
            actions.append(Action(
                action_type="PRIORITIZE_TICKET",
                target_id=str(_safe_get(t, "ticket_id", oid or cid)),
                title=f"Atender incidencia {_safe_get(t,'ticket_id','?')}: {msg[:55]}…",
                score=min(score, 100), tags=tags,
                impact_bullets=["Evita escalado público",
                                "Protege CSAT y reputación",
                                "Reduce riesgo de churn"],
                raw_reasons=raw,
                confidence=0.8, owner=OWNER_BY_TYPE["PRIORITIZE_TICKET"],
                automation_possible=False, category="ticket",
            ))
    return actions


def score_inventory(inventory, campaigns, orders):
    actions: List[Action] = []
    if inventory is None or inventory.empty:
        return actions
    active_camp_skus = set()
    if campaigns is not None and not campaigns.empty and "target_sku" in campaigns.columns:
        active_camp_skus = set(campaigns["target_sku"].dropna().astype(str))
    open_demand_per_sku: Dict[str, int] = {}
    if orders is not None and not orders.empty and "sku" in orders.columns:
        op = orders[orders["order_status"].astype(str).str.lower().isin(["paid", "processing", "pending"])]
        open_demand_per_sku = op.groupby("sku")["quantity"].sum().to_dict()

    for _, r in inventory.iterrows():
        sku = str(_safe_get(r, "sku", "?"))
        avail = float(_safe_get(r, "inventory_available_units", 0) or 0)
        reserved = float(_safe_get(r, "inventory_reserved_units", 0) or 0)
        incoming = float(_safe_get(r, "inventory_incoming_units", 0) or 0)
        views = float(_safe_get(r, "product_page_views_last_hour", 0) or 0)
        sell = float(_safe_get(r, "sell_through_rate_last_hour", 0) or 0)
        demand = open_demand_per_sku.get(sku, 0)
        coverage = avail - reserved - demand

        score = 0
        tags, raw = [], []
        if coverage <= 0:
            score += 50; tags.append("Cobertura negativa"); raw.append(f"cobertura negativa ({int(coverage)})")
        elif coverage <= 3:
            score += 35; tags.append("Cobertura baja"); raw.append(f"cobertura baja ({int(coverage)} ud)")
        if views >= 2000:
            score += 18; tags.append("Alta demanda"); raw.append(f"{int(views)} views/h")
        if sell >= 0.5:
            score += 12; tags.append("Sell-through alto"); raw.append(f"sell-through {sell:.0%}")
        if incoming == 0:
            score += 15; tags.append("Sin reposición"); raw.append("sin reposición programada")
        if sku in active_camp_skus:
            score += 12; tags.append("Campaña activa"); raw.append("SKU bajo campaña activa")

        if score >= 40:
            name = _safe_get(r, "product_name", sku)
            potential = max(int(views * sell * 0.05), 5)
            actions.append(Action(
                action_type="RESTOCK_SKU", target_id=sku,
                title=f"Reponer producto {sku} ({name})",
                score=min(score, 100), tags=tags,
                impact_bullets=[f"Recupera ~{potential} ventas/h potenciales",
                                "Evita rotura de stock",
                                "Mantiene presión comercial"],
                raw_reasons=raw,
                confidence=0.85, owner=OWNER_BY_TYPE["RESTOCK_SKU"],
                automation_possible=True, category="stock",
            ))
    return actions


def score_campaigns(campaigns, inventory):
    actions: List[Action] = []
    if campaigns is None or campaigns.empty:
        return actions
    inv_by_sku = inventory.set_index("sku").to_dict("index") if (inventory is not None and not inventory.empty and "sku" in inventory.columns) else {}
    for _, c in campaigns.iterrows():
        if str(_safe_get(c, "status", "active")).lower() != "active":
            continue
        intensity = float(_safe_get(c, "intensity_score", 2) or 2)
        sku = str(_safe_get(c, "target_sku", ""))
        budget = float(_safe_get(c, "budget_spent", 0) or 0)
        conv = float(_safe_get(c, "conversion_rate", 0) or 0)
        score = 0; tags, raw = [], []
        if intensity >= 3:
            tag = "Intensidad muy alta" if intensity >= 4 else "Intensidad alta"
            score += 30; tags.append(tag); raw.append(tag.lower())
        if sku in inv_by_sku:
            avail = float(inv_by_sku[sku].get("inventory_available_units", 0) or 0)
            reserved = float(inv_by_sku[sku].get("inventory_reserved_units", 0) or 0)
            if avail - reserved <= 0:
                score += 35; tags.append("Stock agotado"); raw.append(f"stock objetivo agotado ({int(avail)} disp)")
            elif avail <= 5:
                score += 22; tags.append("Stock objetivo bajo"); raw.append(f"stock objetivo bajo ({int(avail)} ud)")
        if conv >= 0.06:
            score += 12; tags.append("Conversión alta"); raw.append(f"conversión alta ({conv:.1%})")
        if budget >= 4000:
            score += 8; tags.append("Presupuesto quemado"); raw.append(f"presupuesto quemado ({budget:.0f}€)")

        if score >= 50:
            cid = _safe_get(c, "campaign_id", "?")
            actions.append(Action(
                action_type="PAUSE_CAMPAIGN", target_id=str(cid),
                title=f"Pausar campaña {cid} → {sku}",
                score=min(score, 100), tags=tags,
                impact_bullets=[f"Evita gasto inútil (~{budget*0.2:.0f}€/h)",
                                "Reduce frustración del cliente",
                                "Libera presión sobre stock crítico"],
                raw_reasons=raw,
                confidence=0.8, owner=OWNER_BY_TYPE["PAUSE_CAMPAIGN"],
                automation_possible=True, category="camp",
            ))
    return actions


def rank_actions(all_actions, top_n=10):
    cols = ["rank", "action_type", "target_id", "title", "tags", "impact_bullets",
            "raw_reasons", "confidence", "owner", "automation_possible", "score", "category"]
    if not all_actions:
        return pd.DataFrame(columns=cols)
    rows = []; seen = set()
    for a in sorted(all_actions, key=lambda x: x.score, reverse=True):
        key = (a.action_type, a.target_id)
        if key in seen:
            continue
        seen.add(key)
        seen_tags = set(); ordered_tags = []
        for t in a.tags:
            if t not in seen_tags:
                seen_tags.add(t); ordered_tags.append(t)
        rows.append({
            "rank": 0, "action_type": a.action_type, "target_id": a.target_id,
            "title": a.title, "tags": ordered_tags, "impact_bullets": a.impact_bullets,
            "raw_reasons": a.raw_reasons, "confidence": a.confidence, "owner": a.owner,
            "automation_possible": a.automation_possible,
            "score": round(a.score, 1), "category": a.category,
        })
        if len(rows) >= top_n:
            break
    df = pd.DataFrame(rows); df["rank"] = range(1, len(df) + 1)
    return df


# ============================================================================
# 6) RENDER HELPERS — return flat HTML (no leading whitespace per line)
# ============================================================================
TAG_CLASS_MAP = {
    "Stock crítico": "tag-stock", "Stock bajo": "tag-stock", "Cobertura negativa": "tag-stock",
    "Cobertura baja": "tag-stock", "Stock al límite": "tag-stock", "Stock agotado": "tag-stock",
    "Stock objetivo bajo": "tag-stock", "Sin reposición": "tag-stock",
    "Cliente VIP": "tag-vip", "Cliente recurrente": "tag-vip",
    "Alta demanda": "tag-demand", "Sell-through alto": "tag-demand", "Conversión alta": "tag-demand",
    "Campaña activa": "tag-camp", "Intensidad alta": "tag-camp", "Intensidad muy alta": "tag-camp",
    "Presupuesto quemado": "tag-camp",
    "Ticket urgente": "tag-ticket", "Urgencia alta": "tag-ticket", "Urgencia crítica": "tag-ticket",
    "Sentimiento negativo": "tag-ticket", "Pedido en curso": "tag-ticket",
}


def tag_class(t: str) -> str:
    return TAG_CLASS_MAP.get(t, "tag-other")


def score_class(s: float) -> str:
    if s >= 85: return "crit"
    if s >= 70: return "high"
    return "med"


def render_kpi_card(icon: str, label: str, value, desc: str, tone: str = "primary") -> str:
    return _fmt(f"""
    <div class="kpi {tone}">
      <div class="kpi-head">
        <div class="kpi-label">{escape(label)}</div>
        <div class="kpi-icon">{icon}</div>
      </div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-desc">{escape(desc)}</div>
    </div>""")


def render_health_card(log: CleaningLog) -> str:
    status = health_status(log)
    label = DATASET_LABELS.get(log.dataset, log.dataset)
    icon = DATASET_ICONS.get(log.dataset, "📊")
    status_word = {"ok": "OK", "cleaned": "Limpiado auto", "warning": "Atención", "missing": "No cargado"}[status]
    if status == "missing":
        meta = "Dataset no cargado · funciona con fallback"
        fix = ""
    else:
        meta = f"{log.rows_final} filas · {log.rows_initial - log.rows_final + log.duplicates_removed} eliminadas"
        fix_parts = []
        if log.columns_renamed:
            fix_parts.append(f"<b>{len(log.columns_renamed)}</b> columnas renombradas")
        if log.nulls_imputed:
            total_nulls = sum(log.nulls_imputed.values())
            fix_parts.append(f"<b>{total_nulls}</b> nulos imputados")
        if log.duplicates_removed:
            fix_parts.append(f"<b>{log.duplicates_removed}</b> duplicados resueltos")
        if log.categories_standardized:
            fix_parts.append(f"<b>{len(log.categories_standardized)}</b> categorías normalizadas")
        if log.missing_canonical:
            fix_parts.append(f"<b>faltan:</b> {', '.join(log.missing_canonical[:3])}")
        fix = " · ".join(fix_parts) if fix_parts else "Sin transformaciones necesarias"
    return _fmt(f"""
    <div class="health-card">
      <div class="health-dot {status}"></div>
      <div style="flex:1; min-width:0;">
        <span class="health-name">{icon} {escape(label)}</span>
        <span class="health-status {status}">{status_word}</span>
        <div class="health-meta">{meta}</div>
        <div class="health-fix">{fix}</div>
      </div>
    </div>""")


def render_top_table(df: pd.DataFrame) -> str:
    if df.empty:
        return _fmt(f"""
        <div class="rank-table" style="padding:1.5rem; text-align:center; color:{BRAND['text_muted']};">
          ✨ No hay acciones críticas con los filtros actuales.
        </div>""")
    head = """<div class="rank-row head"><div>#</div><div>Acción</div><div>Caso</div><div>Equipo · Confianza</div><div>Auto</div><div style="text-align:right;">Score</div></div>"""
    rows_html = [head]
    for _, r in df.iterrows():
        chip_cls, chip_label = ACTION_CHIP.get(r["action_type"], ("chip-gray", r["action_type"]))
        rank = int(r["rank"])
        rank_cls = "elite" if rank <= 3 else ("top" if rank <= 5 else "")
        sc_cls = score_class(float(r["score"]))
        conf_pct = int(round(float(r["confidence"]) * 100))
        title = escape(str(r["title"]))
        target = escape(str(r["target_id"]))
        owner = escape(str(r["owner"]))
        auto_cell = '<span class="auto-flag">● auto</span>' if r["automation_possible"] else '<span class="auto-flag no">— manual</span>'
        tags_html = "".join(
            f'<span class="tag {tag_class(t)}">{escape(t)}</span>'
            for t in (r.get("tags") or [])[:5]
        )
        rows_html.append(_fmt(f"""
        <div class="rank-row">
          <div class="rank-num {rank_cls}">{rank:02d}</div>
          <div><span class="chip {chip_cls}">{chip_label}</span></div>
          <div class="cell-title">
            <div class="t">{title}</div>
            <div class="meta"><code>{target}</code></div>
            <div class="tag-row">{tags_html}</div>
          </div>
          <div>
            <div class="conf-text">{owner}</div>
            <div class="conf-bar"><span style="width:{conf_pct}%;"></span></div>
            <div class="conf-text" style="margin-top:0.2rem;">{conf_pct}% confianza</div>
          </div>
          <div>{auto_cell}</div>
          <div style="text-align:right;"><span class="score-pill {sc_cls}">{int(round(float(r['score'])))}</span></div>
        </div>"""))
    return f'<div class="rank-table">{"".join(rows_html)}</div>'


def render_reason_card(row) -> str:
    cat = row.get("category", "general") or "general"
    cls = {"vip": "vip", "stock": "stock", "ticket": "ticket", "camp": "camp"}.get(cat, "")
    chip_cls, chip_label = ACTION_CHIP.get(row["action_type"], ("chip-gray", row["action_type"]))
    sc_cls = score_class(float(row["score"]))
    tags = list(row.get("tags") or [])
    impact = list(row.get("impact_bullets") or [])
    tags_li = "".join(f"<li>{escape(t)}</li>" for t in tags)
    impact_li = "".join(f"<li>{escape(t)}</li>" for t in impact)
    return _fmt(f"""
    <div class="reason {cls}">
      <div class="reason-head">
        <div>
          <span class="chip {chip_cls}">{chip_label}</span>
          <span class="reason-target" style="margin-left:0.4rem;">{escape(str(row['target_id']))}</span>
        </div>
        <span class="score-pill {sc_cls}">{int(round(float(row['score'])))}</span>
      </div>
      <div class="reason-title">#{int(row['rank'])} · {escape(str(row['title']))}</div>
      <div class="bullet-block">
        <span class="bullet-label">Por qué se prioriza</span>
        <ul class="bullet-list">{tags_li or '<li>señales agregadas</li>'}</ul>
      </div>
      <div class="bullet-block">
        <span class="bullet-label">Impacto esperado</span>
        <ul class="bullet-list impact">{impact_li or '<li>protege la operación</li>'}</ul>
      </div>
      <div class="reason-owner">Equipo responsable: <b>{escape(row['owner'])}</b></div>
    </div>""")


# Plotly tuned for dark + bigger
PLOTLY_LAYOUT_BIG = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#CBD5E1", size=13),
    title=dict(font=dict(family="Space Grotesk, sans-serif", size=17, color="#F1F5F9"),
               x=0.02, xanchor="left", y=0.96),
    margin=dict(t=70, b=50, l=40, r=30),
    xaxis=dict(gridcolor="rgba(31,42,68,0.6)", zerolinecolor="rgba(31,42,68,0.6)",
               tickfont=dict(size=12)),
    yaxis=dict(gridcolor="rgba(31,42,68,0.6)", zerolinecolor="rgba(31,42,68,0.6)",
               tickfont=dict(size=12)),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#CBD5E1", size=12)),
)
BRAND_PALETTE = ["#38BDF8", "#A855F7", "#4ADE80", "#FBBF24", "#F87171", "#22D3EE", "#F472B6", "#60A5FA"]


def style_plotly(fig: go.Figure) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT_BIG)
    return fig


# ============================================================================
# 7) FILE LOAD HELPERS
# ============================================================================
EXPECTED_FILES = {
    "orders": ["orders.csv", "pedidos.csv"],
    "customers": ["customers.csv", "clientes.csv"],
    "inventory": ["inventory.csv", "stock.csv"],
    "support_tickets": ["support_tickets.csv", "tickets.csv", "incidencias.csv"],
    "campaigns": ["campaigns.csv", "campanas.csv", "campanias.csv"],
    "order_items": ["order_items.csv", "items.csv"],
}


def _safe_read_csv(file) -> Optional[pd.DataFrame]:
    try:
        if hasattr(file, "read"):
            data = file.read()
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")
            return pd.read_csv(io.StringIO(data))
        return pd.read_csv(file)
    except Exception as e:
        st.warning(f"⚠️ No se pudo leer {getattr(file, 'name', file)}: {e}")
        return None


def load_sample_dataset() -> Dict[str, pd.DataFrame]:
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data")
    out = {}
    for key, names in EXPECTED_FILES.items():
        for n in names:
            p = os.path.join(base, n)
            if os.path.exists(p):
                try:
                    out[key] = pd.read_csv(p); break
                except Exception:
                    pass
    return out


# ============================================================================
# 8) SIDEBAR
# ============================================================================
LOGO_HTML = load_logo("light")

with st.sidebar:
    st.markdown(_fmt(f"""
        <div class="sb-brand">
          <div class="logo">{LOGO_HTML}</div>
        </div>
        <div style="font-size:0.72rem; color:{BRAND['text_muted']}; letter-spacing:0.16em;
                    text-transform:uppercase; margin-bottom:1rem; font-weight:600;">
          Retail Ops · Control Tower
        </div>"""), unsafe_allow_html=True)
    st.markdown(_fmt("""
        <div class="sb-help">
          Sube los CSVs del lanzamiento o usa el dataset de ejemplo.
          Esta torre <b>prioriza decisiones operativas</b> en tiempo real.
        </div>"""), unsafe_allow_html=True)

    st.markdown("### 📂 Datos")
    uploaded = st.file_uploader("CSV files",
                                type=["csv"], accept_multiple_files=True,
                                label_visibility="collapsed")
    use_sample = st.toggle("Usar dataset de ejemplo", value=True,
                           help="Activado por defecto. Lee de ./sample_data/")

    st.markdown("### ⚙️ Parámetros")
    top_n = st.slider("TOP N acciones", 5, 20, 10)

    st.markdown("### 🎯 Filtros")
    only_automatable = st.checkbox("Solo automatizables", value=False)
    owner_filter = st.multiselect(
        "Equipo responsable",
        ["Operaciones", "Atención cliente", "Inventario", "Marketing"], default=[]
    )
    type_filter = st.multiselect(
        "Tipo de acción",
        list(ACTION_LABELS.keys()),
        default=[],
        format_func=lambda x: ACTION_LABELS[x],
    )

    st.markdown("---")
    st.markdown(_fmt(f"""
        <div style="font-size:0.74rem; color:{BRAND['text_dim']}; line-height:1.5;">
          v0.4 · prototype<br/>
          Reglas + scoring ponderado<br/>
          Cleaning + health diagnostics
        </div>"""), unsafe_allow_html=True)


# ============================================================================
# 9) DATA LOAD
# ============================================================================
loaded: Dict[str, pd.DataFrame] = {}
if uploaded:
    for f in uploaded:
        name = f.name.lower()
        for key, candidates in EXPECTED_FILES.items():
            if any(name.endswith(c) for c in candidates) or name.replace(".csv", "") == key:
                df = _safe_read_csv(f)
                if df is not None:
                    loaded[key] = df
                break
if not loaded and use_sample:
    loaded = load_sample_dataset()


# ============================================================================
# 10) HERO
# ============================================================================
files_loaded = len(loaded)
files_total = len(EXPECTED_FILES)
st.markdown(_fmt(f"""
<div class="hero">
  <div class="hero-top">
    <div class="hero-logo">
      {LOGO_HTML}
      <span class="badge-internal">AI Ops · Internal Tool</span>
    </div>
    <span class="tag-pill"><span class="dot"></span> Live launch monitoring</span>
  </div>
  <h1>AI Ops Control Tower</h1>
  <p class="hero-sub">
    Prioriza en tiempo real las decisiones operativas de un lanzamiento Scuffers — pedidos en riesgo,
    clientes VIP afectados, rotura de stock, sobrepresión de campañas e incidencias críticas — todo en una sola vista.
  </p>
  <div class="hero-meta">
    <span><b>{files_loaded}/{files_total}</b> datasets conectados</span>
    <span><b>Reglas + scoring</b> ponderado</span>
    <span><b>TOP {top_n}</b> acciones por turno</span>
    <span><b>Equipos:</b> Operaciones · Atención cliente · Inventario · Marketing</span>
  </div>
</div>"""), unsafe_allow_html=True)

if not loaded:
    st.info("👈 Sube los CSV en el panel lateral o activa el dataset de ejemplo para arrancar la demo.")
    st.stop()


# ============================================================================
# 11) DATA HEALTH PANEL
# ============================================================================
clean: Dict[str, pd.DataFrame] = {}
logs: Dict[str, CleaningLog] = {}
for key in EXPECTED_FILES.keys():
    df_raw = loaded.get(key, pd.DataFrame())
    df_clean, log = clean_dataset(key, df_raw)
    clean[key] = df_clean
    logs[key] = log

st.markdown(_fmt("""
<div class="section-head">
  <div>
    <div class="eyebrow">Data Health</div>
    <h2>🧪 Estado de los datasets cargados</h2>
  </div>
  <div class="meta">Validación + limpieza automática<br/>antes de scoring</div>
</div>"""), unsafe_allow_html=True)

health_html = "".join(render_health_card(logs[k]) for k in EXPECTED_FILES.keys())
st.markdown(f'<div class="health-grid">{health_html}</div>', unsafe_allow_html=True)


# ============================================================================
# 12) SCORE
# ============================================================================
orders, customers, inventory, tickets, campaigns = add_score_columns(
    clean["orders"], clean["customers"], clean["inventory"],
    clean["support_tickets"], clean["campaigns"],
)
master = build_master(orders, customers, inventory)

all_actions: List[Action] = []
all_actions += score_orders(master, tickets, campaigns)
all_actions += score_tickets(tickets, master)
all_actions += score_inventory(inventory, campaigns, orders)
all_actions += score_campaigns(campaigns, inventory)

ranked = rank_actions(all_actions, top_n=top_n)
if only_automatable and not ranked.empty:
    ranked = ranked[ranked["automation_possible"]].reset_index(drop=True)
    ranked["rank"] = range(1, len(ranked) + 1)
if owner_filter and not ranked.empty:
    ranked = ranked[ranked["owner"].isin(owner_filter)].reset_index(drop=True)
    ranked["rank"] = range(1, len(ranked) + 1)
if type_filter and not ranked.empty:
    ranked = ranked[ranked["action_type"].isin(type_filter)].reset_index(drop=True)
    ranked["rank"] = range(1, len(ranked) + 1)


# ============================================================================
# 13) BUSINESS KPIs
# ============================================================================
orders_at_risk = 0
vip_affected_ids = set()
if not master.empty:
    open_mask = master["order_status"].astype(str).str.lower().isin(["paid", "processing", "pending"])
    avail_s = master.get("inventory_available_units", pd.Series([0]*len(master)))
    reserved_s = master.get("inventory_reserved_units", pd.Series([0]*len(master)))
    risk_mask = open_mask & (avail_s <= reserved_s)
    orders_at_risk = int(risk_mask.sum())
    if "is_vip" in master.columns and "customer_id" in master.columns:
        vip_affected_ids.update(master.loc[risk_mask & (master["is_vip"] == True), "customer_id"].astype(str).tolist())
if not tickets.empty and "customer_id" in tickets.columns and not master.empty and "is_vip" in master.columns:
    vip_set = set(master[master["is_vip"] == True]["customer_id"].astype(str))
    crit_t = tickets[(tickets.get("urgency_score", 0) >= 3) | (tickets.get("sentiment_score", 0) < 0)]
    for cid in crit_t["customer_id"].astype(str):
        if cid in vip_set:
            vip_affected_ids.add(cid)
vip_affected = len(vip_affected_ids)

low_stock_skus = 0
if not inventory.empty:
    low_stock_skus = int((inventory["inventory_available_units"] <= inventory["inventory_reserved_units"]).sum())

over_pressure_camps = 0
if not campaigns.empty and not inventory.empty:
    inv_lookup = inventory.set_index("sku")[["inventory_available_units", "inventory_reserved_units"]].to_dict("index")
    for _, c in campaigns.iterrows():
        if str(_safe_get(c, "status", "")).lower() != "active":
            continue
        if float(_safe_get(c, "intensity_score", 2) or 2) < 3:
            continue
        s = str(_safe_get(c, "target_sku", ""))
        if s in inv_lookup:
            a = inv_lookup[s].get("inventory_available_units", 0)
            r = inv_lookup[s].get("inventory_reserved_units", 0)
            if a <= r + 2:
                over_pressure_camps += 1

st.markdown(_fmt("""
<div class="section-head">
  <div><div class="eyebrow">Pulse</div><h2>📈 Estado del lanzamiento</h2></div>
  <div class="meta">KPIs clave · refresco al cargar datos</div>
</div>"""), unsafe_allow_html=True)

kpi_html = (
    render_kpi_card("⚠", "Pedidos en riesgo", orders_at_risk,
                    f"de {len(master)} abiertos · stock por debajo de reservas", "bad")
    + render_kpi_card("👑", "Clientes VIP afectados", vip_affected,
                      "VIPs con pedidos en riesgo o incidencia crítica", "violet")
    + render_kpi_card("📦", "SKUs con stock crítico", low_stock_skus,
                      f"de {len(inventory)} SKUs · sin cobertura", "bad")
    + render_kpi_card("📣", "Campañas en riesgo operativo", over_pressure_camps,
                      "alta intensidad sobre stock al límite", "warn")
)
st.markdown(f'<div class="kpi-grid">{kpi_html}</div>', unsafe_allow_html=True)


# ============================================================================
# 14) TOP N TABLE
# ============================================================================
st.markdown(_fmt(f"""
<div class="section-head">
  <div>
    <div class="eyebrow">Priority queue</div>
    <h2>🎯 TOP {len(ranked)} acciones priorizadas</h2>
  </div>
  <div class="meta">{len(all_actions)} candidatas<br/>ranking por score ponderado</div>
</div>"""), unsafe_allow_html=True)
st.markdown(render_top_table(ranked), unsafe_allow_html=True)


# ============================================================================
# 15) REASON CARDS
# ============================================================================
if not ranked.empty:
    st.markdown(_fmt("""
    <div class="section-head">
      <div>
        <div class="eyebrow">Decision rationale</div>
        <h2>🧠 Por qué se prioriza cada caso</h2>
      </div>
      <div class="meta">Top 6 · explicación ejecutiva</div>
    </div>"""), unsafe_allow_html=True)
    cards = "".join(render_reason_card(r) for _, r in ranked.head(6).iterrows())
    st.markdown(f'<div class="reason-grid">{cards}</div>', unsafe_allow_html=True)


# ============================================================================
# 16) CHARTS — bigger, fewer, more breathing room
# ============================================================================
st.markdown(_fmt("""
<div class="section-head">
  <div>
    <div class="eyebrow">Signals</div>
    <h2>📊 Señales operativas en vivo</h2>
  </div>
  <div class="meta">Visualización para contexto rápido</div>
</div>"""), unsafe_allow_html=True)

# Row 1 — two side-by-side charts at 420px
c1, c2 = st.columns(2)

with c1:
    if not ranked.empty:
        d = ranked["action_type"].value_counts().reset_index()
        d.columns = ["action_type", "count"]
        d["label"] = d["action_type"].map(lambda x: ACTION_LABELS.get(x, x))
        d = d.sort_values("count", ascending=True)
        fig = px.bar(d, x="count", y="label", orientation="h",
                     color="label", color_discrete_sequence=BRAND_PALETTE,
                     title="Distribución de acciones priorizadas")
        fig.update_traces(marker_line_width=0,
                          hovertemplate="<b>%{y}</b><br>%{x} acciones<extra></extra>",
                          texttemplate="%{x}", textposition="outside",
                          textfont=dict(color="#F1F5F9", size=13))
        fig.update_layout(showlegend=False, height=420,
                          xaxis_title=None, yaxis_title=None,
                          xaxis=dict(showgrid=True), yaxis=dict(showgrid=False))
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(style_plotly(fig), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

with c2:
    if not tickets.empty and "support_ticket_urgency" in tickets.columns:
        d3 = tickets["support_ticket_urgency"].value_counts().reset_index()
        d3.columns = ["urgencia", "count"]
        urgency_label = {"low": "Baja", "medium": "Media", "high": "Alta",
                         "critical": "Crítica", "urgent": "Urgente",
                         "alta": "Alta", "critica": "Crítica"}
        d3["urgencia"] = d3["urgencia"].astype(str).map(lambda x: urgency_label.get(x.lower(), x.title()))
        fig = px.pie(d3, names="urgencia", values="count", hole=0.6,
                     title="Incidencias por nivel de urgencia",
                     color_discrete_sequence=["#F87171", "#FBBF24", "#38BDF8", "#4ADE80", "#A855F7"])
        fig.update_traces(textinfo="label+percent",
                          textfont=dict(size=14, color="#F1F5F9"),
                          marker=dict(line=dict(color="#0A0E1A", width=2)),
                          hovertemplate="<b>%{label}</b><br>%{value} incidencias (%{percent})<extra></extra>")
        fig.update_layout(height=420, legend=dict(orientation="h", y=-0.1, font=dict(size=13)))
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(style_plotly(fig), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Row 2 — full-width stock chart
if not inventory.empty:
    inv_sorted = inventory.sort_values("inventory_reserved_units", ascending=False).head(15)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Disponible", x=inv_sorted["sku"],
                         y=inv_sorted["inventory_available_units"],
                         marker_color="#4ADE80",
                         hovertemplate="<b>%{x}</b><br>Disponible: %{y}<extra></extra>"))
    fig.add_trace(go.Bar(name="Reservado", x=inv_sorted["sku"],
                         y=inv_sorted["inventory_reserved_units"],
                         marker_color="#F43F5E",
                         hovertemplate="<b>%{x}</b><br>Reservado: %{y}<extra></extra>"))
    fig.update_layout(barmode="group",
                      title="Stock disponible vs reservado · top 15 SKUs por presión",
                      height=460, xaxis_title=None, yaxis_title=None,
                      legend=dict(orientation="h", y=-0.18, font=dict(size=13)),
                      bargap=0.18, bargroupgap=0.08)
    fig.update_xaxes(tickangle=-30, tickfont=dict(size=12))
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.plotly_chart(style_plotly(fig), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Row 3 — two side-by-side charts at 380px
c3, c4 = st.columns(2)

with c3:
    if not master.empty and "category" in master.columns:
        risk = master[
            master["order_status"].astype(str).str.lower().isin(["paid", "processing", "pending"]) &
            (master.get("inventory_available_units", 0) <= master.get("inventory_reserved_units", 0))
        ]
        if not risk.empty:
            d2 = risk["category"].value_counts().reset_index()
            d2.columns = ["category", "count"]
            d2 = d2.sort_values("count", ascending=True)
            fig = px.bar(d2, x="count", y="category", orientation="h",
                         color="count", color_continuous_scale=[[0, "#0EA5E9"], [1, "#F43F5E"]],
                         title="Pedidos en riesgo por categoría de producto")
            fig.update_traces(marker_line_width=0,
                              hovertemplate="<b>%{y}</b><br>%{x} pedidos<extra></extra>",
                              texttemplate="%{x}", textposition="outside",
                              textfont=dict(color="#F1F5F9", size=13))
            fig.update_layout(height=380, coloraxis_showscale=False,
                              xaxis_title=None, yaxis_title=None,
                              xaxis=dict(showgrid=True), yaxis=dict(showgrid=False))
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.plotly_chart(style_plotly(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

with c4:
    if not campaigns.empty and "campaign_intensity" in campaigns.columns:
        d4 = campaigns["campaign_intensity"].value_counts().reset_index()
        d4.columns = ["intensidad", "count"]
        intensity_label = {"low": "Baja", "medium": "Media", "high": "Alta",
                           "very_high": "Muy alta", "extreme": "Extrema",
                           "alta": "Alta", "muy_alta": "Muy alta"}
        d4["intensidad"] = d4["intensidad"].astype(str).map(lambda x: intensity_label.get(x.lower(), x.title()))
        order = ["Baja", "Media", "Alta", "Muy alta", "Extrema"]
        d4["intensidad"] = pd.Categorical(d4["intensidad"], categories=order, ordered=True)
        d4 = d4.sort_values("intensidad")
        fig = px.bar(d4, x="intensidad", y="count", color="intensidad",
                     title="Campañas activas por intensidad",
                     color_discrete_sequence=["#60A5FA", "#38BDF8", "#FBBF24", "#F87171", "#A855F7"])
        fig.update_traces(marker_line_width=0,
                          hovertemplate="<b>%{x}</b><br>%{y} campañas<extra></extra>",
                          texttemplate="%{y}", textposition="outside",
                          textfont=dict(color="#F1F5F9", size=14))
        fig.update_layout(height=380, showlegend=False,
                          xaxis_title=None, yaxis_title=None,
                          xaxis=dict(tickfont=dict(size=13)))
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(style_plotly(fig), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ============================================================================
# 17) RAW DATA EXPLORER
# ============================================================================
with st.expander("🔎 Datos crudos y diagnóstico de cleaning"):
    tab_labels = [DATASET_LABELS[k] for k in EXPECTED_FILES.keys()]
    tabs = st.tabs(tab_labels)
    for tab, key in zip(tabs, EXPECTED_FILES.keys()):
        with tab:
            df = clean.get(key, pd.DataFrame())
            log = logs.get(key)
            if df is None or df.empty:
                st.caption(f"{DATASET_LABELS[key]}: no se cargó este dataset.")
            else:
                if log:
                    diag = []
                    if log.columns_renamed:
                        diag.append(f"**{len(log.columns_renamed)} columnas renombradas:** "
                                    + ", ".join(f"`{a}`→`{b}`" for a, b in log.columns_renamed[:8]))
                    if log.nulls_imputed:
                        diag.append(f"**Nulos imputados:** "
                                    + ", ".join(f"`{c}`={n}" for c, n in list(log.nulls_imputed.items())[:8]))
                    if log.duplicates_removed:
                        diag.append(f"**Duplicados eliminados:** {log.duplicates_removed}")
                    if log.missing_canonical:
                        diag.append(f"**Columnas faltantes (no críticas):** "
                                    + ", ".join(f"`{c}`" for c in log.missing_canonical))
                    if diag:
                        st.markdown(" · ".join(diag))
                st.dataframe(df, use_container_width=True, height=280)

st.markdown(_fmt(f"""
<div class="scuffers-footer">
  <span class="footer-logo">{LOGO_HTML}</span>
  <span>AI Ops Control Tower · prototype interno · priorización por reglas + scoring ponderado</span>
</div>"""), unsafe_allow_html=True)
