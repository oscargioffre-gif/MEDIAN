"""
common.py — Modulo condiviso tra le pagine di Median Strategy Directa.

Contiene:
- Costanti commissione Directa
- Palette colori
- Funzione commissione e calcolo PMC
- CSS comune
"""
import streamlit as st
import json
from datetime import datetime

# ============================================================
# COSTANTI COMMISSIONE DIRECTA
# ============================================================
COMMISSIONE_PROPORZIONALE = 0.0019   # 1.90€ per 1000€ = 0.19%
COMMISSIONE_MIN = 1.50               # € minimo
SOGLIA_EFFICIENZA = 0.0020           # 0.20% max incidenza commissionale

# ============================================================
# PALETTE COLORI
# ============================================================
COL_BG = "#000000"
COL_CARD = "#0F1419"
COL_CARD_HI = "#1A2230"
COL_BORDER = "#2A3441"
COL_PROFIT = "#00FF94"       # verde neon
COL_RISK = "#FF4757"         # rosso corallo brillante
COL_ACCENT = "#00D4FF"       # ciano elettrico
COL_WARN = "#FFB800"         # giallo ambra
COL_TEXT = "#FFFFFF"
COL_TEXT_DIM = "#B8C5D6"
COL_TEXT_LABEL = "#7FD3FF"

# ============================================================
# PROFILI TRANCHE
# ============================================================
PESI_2 = [0.35, 0.65]
PESI_3 = [0.20, 0.30, 0.50]
PESI_4 = [0.10, 0.20, 0.30, 0.40]
PESI_5 = [0.08, 0.15, 0.22, 0.25, 0.30]

PROFILI_TRANCHE = {5: PESI_5, 4: PESI_4, 3: PESI_3, 2: PESI_2}


def commissione_directa(controvalore: float) -> float:
    """Directa: 1.90€ ogni 1000€ (0.19%), minimo 1.50€."""
    if controvalore <= 0:
        return 0.0
    return max(controvalore * COMMISSIONE_PROPORZIONALE, COMMISSIONE_MIN)


def seleziona_n_tranche_ottimale(budget_totale: float) -> tuple:
    """
    Sceglie il MASSIMO numero di tranche (5→4→3→2) per cui TUTTE le tranche
    rispettano la soglia di efficienza commissionale (0.20%).
    """
    for n in [5, 4, 3, 2]:
        pesi = PROFILI_TRANCHE[n]
        peso_min = min(pesi)
        cap_min = budget_totale * peso_min
        comm_min = max(cap_min * COMMISSIONE_PROPORZIONALE, COMMISSIONE_MIN)
        incidenza = comm_min / cap_min if cap_min > 0 else 1
        if incidenza <= SOGLIA_EFFICIENZA:
            return n, pesi
    return 2, PESI_2


def calcola_pmc(acquisti: list) -> dict:
    """Calcola PMC da una lista di acquisti."""
    if not acquisti:
        return {"pmc": 0, "azioni_totali": 0, "investito_totale": 0,
                "commissioni_totali": 0, "costo_totale": 0}
    investito = sum(a["prezzo"] * a["n_azioni"] for a in acquisti)
    commissioni = sum(a["commissione"] for a in acquisti)
    n_tot = sum(a["n_azioni"] for a in acquisti)
    costo_totale = investito + commissioni
    pmc = costo_totale / n_tot if n_tot > 0 else 0
    return {
        "pmc": pmc,
        "azioni_totali": n_tot,
        "investito_totale": investito,
        "commissioni_totali": commissioni,
        "costo_totale": costo_totale,
    }


# ============================================================
# CSS — caricato una volta per pagina
# ============================================================
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;600;700;800&display=swap');

* {{
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, sans-serif;
    background-color: {COL_BG};
    color: {COL_TEXT};
}}

.stApp {{
    background: radial-gradient(ellipse at top, #0A1628 0%, {COL_BG} 60%);
}}

section[data-testid="stSidebar"] {{
    background-color: {COL_CARD};
    border-right: 1px solid {COL_BORDER};
}}
section[data-testid="stSidebar"] * {{ color: {COL_TEXT} !important; }}

.main-title {{
    font-family: 'Inter', sans-serif;
    font-weight: 900;
    font-size: clamp(1.4rem, 6.5vw, 2.4rem);
    line-height: 0.95;
    background: linear-gradient(135deg, {COL_PROFIT} 0%, {COL_ACCENT} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -1.5px;
    margin-bottom: 0.3rem;
    text-shadow: 0 0 40px rgba(0, 255, 148, 0.3);
    word-break: keep-all;
}}
.main-sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: {COL_TEXT_LABEL};
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-weight: 600;
    margin-bottom: 1.5rem;
}}

.metric-card {{
    background: linear-gradient(135deg, {COL_CARD} 0%, {COL_CARD_HI} 100%);
    border: 1.5px solid {COL_BORDER};
    border-radius: 18px;
    padding: 1.2rem 1.3rem;
    margin-bottom: 0.8rem;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}}
.metric-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, {COL_ACCENT}, transparent);
    opacity: 0.6;
}}
.metric-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: {COL_TEXT_LABEL};
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.5rem;
}}
.metric-value {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 1.9rem;
    line-height: 1.05;
    color: {COL_TEXT};
    letter-spacing: -0.5px;
}}
.metric-delta {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 600;
    margin-top: 0.5rem;
}}
.profit {{ color: {COL_PROFIT}; text-shadow: 0 0 12px rgba(0, 255, 148, 0.4); }}
.risk    {{ color: {COL_RISK};   text-shadow: 0 0 12px rgba(255, 71, 87, 0.4); }}
.warn    {{ color: {COL_WARN};   text-shadow: 0 0 12px rgba(255, 184, 0, 0.4); }}
.neutral {{ color: {COL_TEXT_DIM}; }}
.accent  {{ color: {COL_ACCENT}; text-shadow: 0 0 12px rgba(0, 212, 255, 0.4); }}

.section-title {{
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 1.25rem;
    color: {COL_TEXT};
    margin-top: 1.8rem;
    margin-bottom: 0.9rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid {COL_BORDER};
    letter-spacing: -0.3px;
}}

/* Checklist card per la modalità PIANO */
.checklist-card {{
    background: linear-gradient(135deg, {COL_CARD} 0%, {COL_CARD_HI} 100%);
    border: 1.5px solid {COL_BORDER};
    border-left: 5px solid {COL_ACCENT};
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.8rem;
}}
.checklist-card.t1 {{ border-left-color: #7FD3FF; }}
.checklist-card.t2 {{ border-left-color: {COL_ACCENT}; }}
.checklist-card.t3 {{ border-left-color: {COL_PROFIT}; }}
.checklist-card.t4 {{ border-left-color: {COL_WARN}; }}
.checklist-card.t5 {{ border-left-color: #FFA0F0; }}
.checklist-card.bloccata {{ border-left-color: {COL_RISK}; opacity: 0.7; }}
.checklist-head {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 0.95rem;
    color: {COL_TEXT};
    margin-bottom: 0.5rem;
    letter-spacing: 0.3px;
}}
.checklist-action {{
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 1.15rem;
    color: {COL_TEXT};
    margin: 0.4rem 0;
    line-height: 1.4;
}}
.checklist-detail {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: {COL_TEXT_DIM};
    margin-top: 0.3rem;
    line-height: 1.6;
}}
.big-number {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    color: {COL_PROFIT};
    font-size: 1.25rem;
}}

.stSlider label, .stRadio label, .stSelectbox label,
.stNumberInput label, .stTextInput label, .stDateInput label {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: {COL_TEXT_LABEL} !important;
    font-weight: 700 !important;
}}
.stSlider div[data-baseweb="slider"] > div > div > div {{ background-color: {COL_ACCENT} !important; }}
.stNumberInput input, .stTextInput input {{
    background-color: {COL_CARD} !important;
    color: {COL_TEXT} !important;
    border: 1.5px solid {COL_BORDER} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
}}
.stButton > button {{
    background: linear-gradient(135deg, {COL_ACCENT} 0%, {COL_PROFIT} 100%);
    color: {COL_BG} !important;
    border: none;
    border-radius: 12px;
    font-weight: 800;
    font-family: 'Inter', sans-serif;
    padding: 0.7rem 1.6rem;
    font-size: 0.95rem;
    box-shadow: 0 4px 16px rgba(0, 212, 255, 0.25);
}}
.stDownloadButton > button {{
    background: linear-gradient(135deg, {COL_PROFIT} 0%, {COL_ACCENT} 100%);
    color: {COL_BG} !important;
    border: none;
    border-radius: 12px;
    font-weight: 800;
}}

[data-testid="stExpander"] summary {{
    background-color: {COL_CARD} !important;
    border-radius: 12px;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    color: {COL_TEXT} !important;
}}
[data-testid="stExpander"] {{
    border: 1.5px solid {COL_BORDER};
    border-radius: 12px;
    margin-bottom: 0.6rem;
}}

.archive-item {{
    background: linear-gradient(135deg, {COL_CARD} 0%, {COL_CARD_HI} 100%);
    border: 1.5px solid {COL_BORDER};
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}}

[data-testid="stCaptionContainer"], .stMarkdown p {{
    color: {COL_TEXT_DIM} !important;
    font-size: 0.92rem;
    line-height: 1.6;
}}

@media (max-width: 640px) {{
    .main-sub {{ font-size: 0.7rem; }}
    .metric-value {{ font-size: 1.55rem; }}
    .metric-label {{ font-size: 0.65rem; }}
    .section-title {{ font-size: 1.1rem; }}
    .block-container {{
        padding-top: 1rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
        padding-bottom: 2rem !important;
    }}
    .stButton > button, .stDownloadButton > button {{
        width: 100%;
        font-size: 1rem;
        padding: 0.85rem 1rem;
    }}
    .checklist-action {{ font-size: 1.05rem; }}
    .big-number {{ font-size: 1.1rem; }}
}}

footer, #MainMenu, [data-testid="stToolbar"] {{ visibility: hidden; }}

::-webkit-scrollbar {{ width: 8px; }}
::-webkit-scrollbar-track {{ background: {COL_BG}; }}
::-webkit-scrollbar-thumb {{ background: {COL_BORDER}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {COL_ACCENT}; }}
</style>
"""


def apply_css():
    """Carica il CSS comune."""
    st.markdown(CSS, unsafe_allow_html=True)


def init_archive():
    """Inizializza la sessione archivio se non esiste."""
    if "archivio_piani" not in st.session_state:
        st.session_state.archivio_piani = []
    if "archivio_monitoraggi" not in st.session_state:
        st.session_state.archivio_monitoraggi = []
