"""
Median Strategy Directa — Simulatore di Dollar Cost Averaging ottimizzato
per il broker Directa.

Commissione Directa (regime "Start"):
  - 1.90€ per ogni 1000€ di controvalore (proporzionale 0.19%)
  - Minimo 1.50€ se la proporzionale risulta inferiore
  - Esempio: tranche 2000€ → 3.80€; tranche 500€ → 1.50€ (min)

Logica:
- Filtro efficienza: incidenza commissionale ≤ 0.20% per tranche
- Pesi crescenti (20/30/50 per 3 tranche, 10/20/30/40 per 4 tranche)
- Stress test su crollo consecutivo configurabile
- Buy Zone su -1σ / -2σ / -3σ dal prezzo iniziale
- Export PNG della simulazione
- Archivio storico delle simulazioni salvate

Author: Os — built with Claude
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
COMMISSIONE_PROPORZIONALE = 0.0019   # 1.90€ per 1000€ = 0.19%
COMMISSIONE_MIN = 1.50               # € minimo
SOGLIA_EFFICIENZA = 0.0020           # 0.20% max incidenza commissionale

# Palette ultra-luminosa, alto contrasto
COL_BG = "#000000"
COL_CARD = "#0F1419"
COL_CARD_HI = "#1A2230"
COL_BORDER = "#2A3441"
COL_PROFIT = "#00FF94"       # verde neon
COL_RISK = "#FF4757"         # rosso corallo brillante
COL_ACCENT = "#00D4FF"       # ciano elettrico
COL_WARN = "#FFB800"         # giallo ambra
COL_TEXT = "#FFFFFF"         # bianco puro
COL_TEXT_DIM = "#B8C5D6"     # grigio chiaro luminoso
COL_TEXT_LABEL = "#7FD3FF"   # ciano chiaro per label

PESI_2 = [0.35, 0.65]
PESI_3 = [0.20, 0.30, 0.50]
PESI_4 = [0.10, 0.20, 0.30, 0.40]
PESI_5 = [0.08, 0.15, 0.22, 0.25, 0.30]

PROFILI_TRANCHE = {
    5: PESI_5,
    4: PESI_4,
    3: PESI_3,
    2: PESI_2,
}


def seleziona_n_tranche_ottimale(budget_totale: float) -> tuple:
    """
    Sceglie il MASSIMO numero di tranche (5→4→3→2) per cui TUTTE le tranche
    rispettano la soglia di efficienza commissionale (incidenza ≤ 0.20%).

    Ritorna: (n_tranche, pesi, motivo)
    """
    for n in [5, 4, 3, 2]:
        pesi = PROFILI_TRANCHE[n]
        # Verifica che la tranche più piccola (peso minimo) rispetti la soglia
        peso_min = min(pesi)
        cap_min = budget_totale * peso_min
        comm_min = max(cap_min * COMMISSIONE_PROPORZIONALE, COMMISSIONE_MIN)
        incidenza = comm_min / cap_min if cap_min > 0 else 1

        if incidenza <= SOGLIA_EFFICIENZA:
            motivo = f"{n} tranche selezionate (efficienza max compatibile con soglia 0.20%)"
            return n, pesi, motivo

    # Fallback: anche 2 tranche non basta — uso 2 ma segnala il problema
    return 2, PESI_2, "⚠ Capitale insufficiente per soglia 0.20% — 2 tranche con avviso"

st.set_page_config(
    page_title="Median Strategy Directa",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS — Ultra-luminoso, font grandi, mobile-first
# ============================================================
st.markdown(f"""
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
section[data-testid="stSidebar"] * {{
    color: {COL_TEXT} !important;
}}

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
.metric-card:hover {{
    border-color: {COL_ACCENT};
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 212, 255, 0.15);
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
    letter-spacing: 0.3px;
}}
.profit  {{ color: {COL_PROFIT}; text-shadow: 0 0 12px rgba(0, 255, 148, 0.4); }}
.risk    {{ color: {COL_RISK};   text-shadow: 0 0 12px rgba(255, 71, 87, 0.4); }}
.warn    {{ color: {COL_WARN};   text-shadow: 0 0 12px rgba(255, 184, 0, 0.4); }}
.neutral {{ color: {COL_TEXT_DIM}; }}
.accent  {{ color: {COL_ACCENT}; text-shadow: 0 0 12px rgba(0, 212, 255, 0.4); }}

.tranche-box {{
    background: linear-gradient(135deg, {COL_CARD} 0%, {COL_CARD_HI} 100%);
    border-left: 4px solid {COL_ACCENT};
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    color: {COL_TEXT};
    font-weight: 500;
}}
.tranche-box.t1 {{ border-left-color: #7FD3FF; }}
.tranche-box.t2 {{ border-left-color: {COL_ACCENT}; }}
.tranche-box.t3 {{ border-left-color: {COL_PROFIT}; }}
.tranche-box.t4 {{ border-left-color: {COL_WARN}; }}
.tranche-box.blocked {{ border-left-color: {COL_RISK}; opacity: 0.85; }}
.tranche-head {{
    font-weight: 800;
    font-size: 1rem;
    letter-spacing: 0.5px;
}}
.tranche-info {{
    color: {COL_TEXT_DIM};
    font-size: 0.82rem;
    margin-top: 0.4rem;
    font-weight: 500;
}}

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

.stSlider label, .stRadio label, .stSelectbox label,
.stNumberInput label, .stTextInput label {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: {COL_TEXT_LABEL} !important;
    font-weight: 700 !important;
}}
.stSlider div[data-baseweb="slider"] > div > div > div {{
    background-color: {COL_ACCENT} !important;
}}
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
    letter-spacing: 0.3px;
    transition: all 0.2s;
    box-shadow: 0 4px 16px rgba(0, 212, 255, 0.25);
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(0, 212, 255, 0.4);
}}
.stDownloadButton > button {{
    background: linear-gradient(135deg, {COL_PROFIT} 0%, {COL_ACCENT} 100%);
    color: {COL_BG} !important;
    border: none;
    border-radius: 12px;
    font-weight: 800;
    font-family: 'Inter', sans-serif;
    padding: 0.7rem 1.6rem;
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
[data-testid="stExpander"] p, [data-testid="stExpander"] li {{
    color: {COL_TEXT} !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
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
    .tranche-box {{ font-size: 0.85rem; padding: 0.85rem 1rem; }}
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
}}

footer, #MainMenu, [data-testid="stToolbar"] {{ visibility: hidden; }}

::-webkit-scrollbar {{ width: 8px; }}
::-webkit-scrollbar-track {{ background: {COL_BG}; }}
::-webkit-scrollbar-thumb {{ background: {COL_BORDER}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {COL_ACCENT}; }}
</style>
""", unsafe_allow_html=True)


# ============================================================
# COMMISSIONE DIRECTA
# ============================================================
def commissione_directa(controvalore: float) -> float:
    """
    Directa: 1.90€ ogni 1000€ (0.19%), minimo 1.50€.
    Sotto ~789.47€ scatta il minimo fisso.
    """
    if controvalore <= 0:
        return 0.0
    proporzionale = controvalore * COMMISSIONE_PROPORZIONALE
    return max(proporzionale, COMMISSIONE_MIN)


# ============================================================
# CORE LOGIC
# ============================================================
def calcola_tranches(budget_totale: float, pesi: list, prezzo_corrente: float):
    tranches = []
    for i, peso in enumerate(pesi):
        capitale = budget_totale * peso
        comm = commissione_directa(capitale)
        capitale_netto = capitale - comm
        incidenza = comm / capitale if capitale > 0 else 1
        valido = incidenza <= SOGLIA_EFFICIENZA
        n_azioni = int(capitale_netto / prezzo_corrente) if prezzo_corrente > 0 else 0
        tranches.append({
            "num": i + 1,
            "peso": peso,
            "capitale_lordo": capitale,
            "capitale_netto": capitale_netto,
            "commissione": comm,
            "incidenza_pct": incidenza * 100,
            "valido": valido,
            "n_azioni_iniziali": n_azioni,
        })
    return tranches


def calcola_pmc(acquisti: list) -> dict:
    if not acquisti:
        return {"pmc": 0, "azioni_totali": 0, "investito_totale": 0,
                "commissioni_totali": 0, "costo_totale": 0}
    investito = sum(a["prezzo"] * a["n_azioni"] for a in acquisti)
    commissioni = sum(a["commissione"] for a in acquisti)
    azioni_totali = sum(a["n_azioni"] for a in acquisti)
    costo_totale = investito + commissioni
    pmc = costo_totale / azioni_totali if azioni_totali > 0 else 0
    return {
        "pmc": pmc,
        "azioni_totali": azioni_totali,
        "investito_totale": investito,
        "commissioni_totali": commissioni,
        "costo_totale": costo_totale,
    }


def simula_stress_test(tranches_valide: list, prezzo_iniziale: float, crolli: list,
                        azioni_override: list = None):
    """
    Esegue stress test: ad ogni step di crollo esegue la tranche corrispondente.

    Se azioni_override è fornito (lista di int allineata a tranches_valide),
    per ogni tranche con override > 0 usa quel valore invece del calcolo automatico.
    La commissione viene comunque ricalcolata sul controvalore effettivo (n_azioni × prezzo).
    """
    prezzi = [prezzo_iniziale]
    acquisti = []
    pmc_history = []

    def get_override(idx):
        """Ritorna l'override se presente e > 0, altrimenti None."""
        if azioni_override is None:
            return None
        if idx >= len(azioni_override):
            return None
        return azioni_override[idx] if azioni_override[idx] > 0 else None

    if len(tranches_valide) > 0:
        t = tranches_valide[0]
        override_n = get_override(0)
        if override_n is not None:
            # USO override: ricalcolo commissione sul controvalore reale
            n_az = override_n
            controvalore = n_az * prezzo_iniziale
            comm = commissione_directa(controvalore)
        else:
            comm = commissione_directa(t["capitale_lordo"])
            n_az = int((t["capitale_lordo"] - comm) / prezzo_iniziale)
        if n_az > 0:
            acquisti.append({
                "giorno": 0,
                "prezzo": prezzo_iniziale,
                "n_azioni": n_az,
                "commissione": comm,
                "tranche_num": t["num"],
                "capitale": t["capitale_lordo"],
                "override": override_n is not None,
            })
    pmc_history.append(calcola_pmc(acquisti))

    prezzo_corrente = prezzo_iniziale
    for i, crollo_pct in enumerate(crolli):
        prezzo_corrente = prezzo_corrente * (1 + crollo_pct / 100)
        prezzi.append(prezzo_corrente)

        if (i + 1) < len(tranches_valide):
            t = tranches_valide[i + 1]
            override_n = get_override(i + 1)
            if override_n is not None:
                n_az = override_n
                controvalore = n_az * prezzo_corrente
                comm = commissione_directa(controvalore)
            else:
                comm = commissione_directa(t["capitale_lordo"])
                n_az = int((t["capitale_lordo"] - comm) / prezzo_corrente)
            if n_az > 0:
                acquisti.append({
                    "giorno": i + 1,
                    "prezzo": prezzo_corrente,
                    "n_azioni": n_az,
                    "commissione": comm,
                    "tranche_num": t["num"],
                    "capitale": t["capitale_lordo"],
                    "override": override_n is not None,
                })
        pmc_history.append(calcola_pmc(acquisti))

    return {
        "prezzi": prezzi,
        "acquisti": acquisti,
        "pmc_history": pmc_history,
        "prezzo_finale": prezzo_corrente,
    }


def calcola_buy_zones(prezzo_iniziale: float, sigma_pct: float):
    sigma = prezzo_iniziale * (sigma_pct / 100)
    return {
        "p1sigma": prezzo_iniziale - sigma,
        "p2sigma": prezzo_iniziale - 2 * sigma,
        "p3sigma": prezzo_iniziale - 3 * sigma,
        "pct1": -sigma_pct,
        "pct2": -2 * sigma_pct,
        "pct3": -3 * sigma_pct,
    }


# ============================================================
# ARCHIVIO
# ============================================================
if "archivio" not in st.session_state:
    st.session_state.archivio = []


# ============================================================
# SIDEBAR — Vuota (info app)
# ============================================================
with st.sidebar:
    st.markdown("### 📊 MEDIAN STRATEGY")
    st.caption("Simulatore DCA per Directa")
    st.markdown("---")
    st.caption(
        "**Commissione Directa**\n\n"
        "1,90€ ogni 1000€\n"
        "(min 1,50€)\n\n"
        "**Filtro efficienza**\n\n"
        "Incidenza ≤ 0,20%"
    )


# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="main-title">Median Strategy<br>Directa</div>', unsafe_allow_html=True)


# ============================================================
# PARAMETRI PRINCIPALI — visibili in pagina
# ============================================================
st.markdown('<div class="section-title">⚙️ Parametri</div>', unsafe_allow_html=True)

budget = st.number_input(
    "💰 Capitale disponibile (€) — senza leva",
    min_value=500,
    max_value=1000000,
    value=10000,
    step=500,
    format="%d",
    help="Inserisci il capitale che vuoi investire. L'app deciderà automaticamente il numero ottimale di tranche per rispettare la soglia di efficienza commissionale Directa (0.20%).",
)

# Selezione automatica numero tranche
n_tranche_choice, pesi_auto, motivo_tranche = seleziona_n_tranche_ottimale(budget)

# Info box sulla scelta automatica
pesi_str_display = " / ".join(f"{int(p*100)}%" for p in pesi_auto)
st.markdown(f"""
<div style="background: linear-gradient(135deg, {COL_CARD} 0%, {COL_CARD_HI} 100%);
            border-left: 4px solid {COL_PROFIT};
            border-radius: 10px; padding: 0.9rem 1.1rem; margin: 0.5rem 0 1rem 0;
            font-family: 'JetBrains Mono', monospace;">
    <div style="color: {COL_TEXT_LABEL}; font-size: 0.72rem; font-weight: 700;
                letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 0.3rem;">
        🤖 Piano automatico ottimizzato
    </div>
    <div style="color: {COL_TEXT}; font-size: 1rem; font-weight: 700;">
        {n_tranche_choice} tranche · pesi {pesi_str_display}
    </div>
    <div style="color: {COL_TEXT_DIM}; font-size: 0.78rem; margin-top: 0.4rem; line-height: 1.4;">
        Selezione basata sull'efficienza commissionale Directa.
        Tranche minima: <strong style="color:{COL_PROFIT};">€{budget * min(pesi_auto):,.0f}</strong>.
    </div>
</div>
""".replace(",", "."), unsafe_allow_html=True)

col_p1, col_p2 = st.columns(2)
with col_p1:
    ticker_label = st.text_input(
        "🏷️ Ticker",
        value="",
        placeholder="es. SRPT, ENI.MI",
    )
with col_p2:
    prezzo_iniziale = st.number_input(
        "💲 Prezzo di acquisto T1 (€)",
        min_value=0.01,
        max_value=10000.0,
        value=25.00,
        step=0.10,
        format="%.2f",
        help="Prezzo PURO di mercato senza commissioni. Le commissioni Directa (1.90€ ogni 1000€, min 1.50€) le calcola l'app automaticamente per ogni tranche.",
    )

# Badge esplicativo prezzo pulito
st.markdown(f"""
<div style="background: rgba(0, 212, 255, 0.08);
            border: 1px solid {COL_ACCENT};
            border-radius: 8px; padding: 0.6rem 0.9rem; margin: 0.3rem 0 1rem 0;
            font-family: 'Inter', sans-serif; font-size: 0.82rem;
            color: {COL_TEXT};">
    💡 <strong style="color:{COL_ACCENT};">Nota</strong>:
    inserisci il prezzo <em>puro di mercato</em> (senza commissioni).
    L'app calcola PMC, azioni e commissioni Directa per ogni tranche in automatico.
</div>
""", unsafe_allow_html=True)

sigma_giornaliera = st.slider(
    "📊 Volatilità σ giornaliera del titolo (%)",
    min_value=1.0,
    max_value=10.0,
    value=4.0,
    step=0.5,
    help="Biotech small-cap: 4-7% · Mid-cap: 2-3% · Blue chip: 1-2%",
)

# Stress Test in un expander pieghevole nel body principale
st.markdown("")  # spacer
with st.expander("📉 **Stress Test** — Imposta lo scenario di crollo", expanded=True):
    st.caption("Crollo consecutivo per giorno (in % vs giorno precedente)")
    default_crolli = [-3.0, -5.0, -10.0, -7.0, -4.0]
    crolli_widgets = []
    for i in range(n_tranche_choice - 1):
        cr = st.slider(
            f"Giorno {i+1}",
            min_value=-20.0,
            max_value=0.0,
            value=default_crolli[i] if i < len(default_crolli) else -5.0,
            step=0.5,
            format="%.1f%%",
            key=f"crollo_{i}",
        )
        crolli_widgets.append(cr)
crolli = crolli_widgets

# Override manuale azioni per tranche (acquisti reali da Directa)
with st.expander("✏️ **Override manuale** — Inserisci le azioni effettivamente acquistate", expanded=False):
    st.caption(
        "Se hai già eseguito ordini su Directa e vuoi calcolare il PMC sui numeri reali, "
        "inserisci qui le quantità effettive per ciascuna tranche. "
        "Se lasci 0, l'app userà il calcolo automatico."
    )
    azioni_override = []
    cols_override = st.columns(min(n_tranche_choice, 3))
    for i in range(n_tranche_choice):
        col = cols_override[i % len(cols_override)]
        with col:
            n_az = st.number_input(
                f"T{i+1} azioni",
                min_value=0,
                max_value=1_000_000,
                value=0,
                step=1,
                key=f"override_az_{i}",
                help=f"Quantità reale eseguita per la Tranche {i+1}. 0 = usa calcolo automatico.",
            )
            azioni_override.append(n_az)
    # Flag: l'override è attivo se almeno una tranche ha azioni > 0
    override_attivo = any(a > 0 for a in azioni_override)
    if override_attivo:
        st.markdown(
            f"<div style='color:{COL_PROFIT}; font-weight:700; font-family:JetBrains Mono;'>"
            f"✓ Override attivo — PMC ricalcolato sui valori reali"
            f"</div>",
            unsafe_allow_html=True,
        )

# Sub-header dinamico sotto il titolo
ticker_display = f" · {ticker_label.upper()}" if ticker_label else ""
st.markdown(
    f'<div class="main-sub" style="margin-top:1rem;">Capitale {budget:,}€ · {n_tranche_choice} tranche{ticker_display}</div>'.replace(",", "."),
    unsafe_allow_html=True,
)


# ============================================================
# CALCOLI
# ============================================================
ticker_clean = ticker_label.strip().upper() if ticker_label.strip() else "TITOLO"

pesi = pesi_auto  # pesi selezionati automaticamente in base al capitale
tranches_raw = calcola_tranches(budget, pesi, prezzo_iniziale)
tranches_valide = [t for t in tranches_raw if t["valido"]]

crolli_usati = crolli[:max(0, len(tranches_valide) - 1)]
# Mappo gli override solo sulle tranche valide (le bloccate non hanno acquisto)
override_per_valide = []
if 'azioni_override' in dir() or 'azioni_override' in locals():
    idx_valide = [t["num"] - 1 for t in tranches_valide]  # indici originali delle valide
    override_per_valide = [azioni_override[i] if i < len(azioni_override) else 0
                           for i in idx_valide]
risultato = simula_stress_test(tranches_valide, prezzo_iniziale, crolli_usati,
                                azioni_override=override_per_valide if override_per_valide else None)
buy_zones = calcola_buy_zones(prezzo_iniziale, sigma_giornaliera)

pmc_finale = risultato["pmc_history"][-1] if risultato["pmc_history"] else {}
prezzo_finale = risultato["prezzo_finale"]
pmc_value = pmc_finale.get("pmc", 0)

if prezzo_finale > 0 and pmc_value > 0:
    break_even_pct = ((pmc_value / prezzo_finale) - 1) * 100
else:
    break_even_pct = 0

valore_attuale = pmc_finale.get("azioni_totali", 0) * prezzo_finale
costo_totale = pmc_finale.get("costo_totale", 0)
perdita_eur = valore_attuale - costo_totale
perdita_pct = (perdita_eur / costo_totale * 100) if costo_totale > 0 else 0


# ============================================================
# DASHBOARD METRICHE
# ============================================================
st.markdown('<div class="section-title">📊 Dashboard</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">PMC ATTUALE</div>
        <div class="metric-value accent">€{pmc_value:.3f}</div>
        <div class="metric-delta neutral">{pmc_finale.get("azioni_totali", 0)} azioni</div>
    </div>
    """, unsafe_allow_html=True)

    be_class = 'profit' if break_even_pct < 10 else ('warn' if break_even_pct < 20 else 'risk')
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">BREAK-EVEN</div>
        <div class="metric-value {be_class}">+{break_even_pct:.2f}%</div>
        <div class="metric-delta neutral">da €{prezzo_finale:.3f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">INVESTITO</div>
        <div class="metric-value">€{pmc_finale.get("costo_totale", 0):,.2f}</div>
        <div class="metric-delta neutral">Comm €{pmc_finale.get("commissioni_totali", 0):.2f}</div>
    </div>
    """.replace(",", "."), unsafe_allow_html=True)

    pl_class = 'profit' if perdita_eur >= 0 else 'risk'
    pl_sign = '+' if perdita_eur >= 0 else ''
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">P/L ATTUALE</div>
        <div class="metric-value {pl_class}">{pl_sign}€{perdita_eur:.2f}</div>
        <div class="metric-delta {pl_class}">{perdita_pct:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# LEGENDA P/L — Spiegazione passo-passo con numeri reali
# ============================================================
acquisti_list = risultato["acquisti"]
n_acq = len(acquisti_list)

if n_acq > 0:
    # Pre-calcolo tutti i valori in variabili locali
    totale_azioni = pmc_finale.get('azioni_totali', 0)
    totale_investito_azioni = pmc_finale.get('investito_totale', 0)
    totale_comm = pmc_finale.get('commissioni_totali', 0)
    totale_costo = pmc_finale.get('costo_totale', 0)
    valore_finale = totale_azioni * prezzo_finale

    pl_sign_str = '+' if perdita_eur >= 0 else ''
    pl_word = "guadagno" if perdita_eur >= 0 else "perdita"
    pl_emoji = "🟢" if perdita_eur >= 0 else "🔴"

    # Confronto con all-in
    be_allin = ((prezzo_iniziale / prezzo_finale - 1) * 100) if prezzo_finale > 0 else 0
    risparmio_be = be_allin - break_even_pct

    # Formatto budget con punto come migliaia (italiano)
    budget_fmt = f"{budget:,}".replace(",", ".")
    investito_fmt = f"{totale_costo:,.2f}".replace(",", ".")
    investito_azioni_fmt = f"{totale_investito_azioni:,.2f}".replace(",", ".")
    valore_finale_fmt = f"{valore_finale:,.2f}".replace(",", ".")
    perdita_fmt = f"{abs(perdita_eur):.2f}"

    # Lista acquisti formattata
    riga_acquisti = ""
    for a in acquisti_list:
        controvalore_t = a['n_azioni'] * a['prezzo']
        controvalore_fmt = f"{controvalore_t:,.2f}".replace(",", ".")
        riga_acquisti += (
            f"- **Giorno {a['giorno']}** → Tranche {a['tranche_num']}: "
            f"{a['n_azioni']} azioni × €{a['prezzo']:.3f} = "
            f"€{controvalore_fmt} (+ commissione €{a['commissione']:.2f})\n"
        )

    with st.expander("❓ **Come si leggono i numeri?** — Spiegazione con i tuoi dati"):
        # SEZIONE 1 — Cosa è successo
        st.markdown("### 📋 Cosa è successo nella simulazione")
        st.markdown(
            f"Hai impostato budget **€{budget_fmt}** su **{n_tranche_choice} tranche** "
            f"per il titolo **{ticker_clean}** che parte da **€{prezzo_iniziale:.2f}**. "
            f"L'app ha simulato il crollo che hai impostato nello Stress Test ed eseguito "
            f"**{n_acq} acquisti**:"
        )
        st.markdown(riga_acquisti)

        st.markdown("---")
        st.markdown("### 🧮 Da dove vengono i numeri")

        # 1 — INVESTITO
        st.markdown(f"**1️⃣ INVESTITO = €{investito_fmt}**")
        st.markdown(
            f"È quanto hai *speso davvero* sommando tutti gli acquisti più le commissioni:\n"
            f"- Costo azioni: €{investito_azioni_fmt}\n"
            f"- Commissioni Directa: €{totale_comm:.2f}\n"
            f"- **Totale: €{investito_fmt}**"
        )

        # 2 — AZIONI
        st.markdown(f"**2️⃣ AZIONI TOTALI = {totale_azioni}**")
        st.markdown(f"Hai accumulato {totale_azioni} azioni sommando le quantità di ogni tranche.")

        # 3 — PMC
        st.markdown(f"**3️⃣ PMC = €{pmc_value:.3f}** *(Prezzo Medio di Carico)*")
        st.markdown("È il prezzo *medio ponderato* a cui hai comprato. Formula:")
        st.code(
            f"PMC = Costo Totale ÷ Azioni Totali\n"
            f"    = €{investito_fmt} ÷ {totale_azioni}\n"
            f"    = €{pmc_value:.3f}",
            language="text"
        )
        st.markdown("È il tuo *vero* prezzo di acquisto, commissioni incluse.")

        # 4 — Prezzo finale
        st.markdown(f"**4️⃣ Prezzo finale di mercato = €{prezzo_finale:.3f}**")
        st.markdown(f"Dopo tutti i crolli impostati, il titolo vale **€{prezzo_finale:.3f}**.")

        # 5 — VALORE ATTUALE
        st.markdown(f"**5️⃣ VALORE ATTUALE = €{valore_finale_fmt}**")
        st.markdown("Quanto valgono ora le tue azioni se le vendessi al prezzo di mercato:")
        st.code(
            f"Valore = Azioni × Prezzo finale\n"
            f"       = {totale_azioni} × €{prezzo_finale:.3f}\n"
            f"       = €{valore_finale_fmt}",
            language="text"
        )

        # 6 — P/L
        st.markdown(f"**6️⃣ P/L = {pl_sign_str}€{perdita_eur:.2f} ({perdita_pct:+.2f}%)** {pl_emoji}")
        st.markdown("Profit/Loss = quanto stai *guadagnando o perdendo* in questo momento:")
        st.code(
            f"P/L = Valore attuale − Investito\n"
            f"    = €{valore_finale_fmt} − €{investito_fmt}\n"
            f"    = {pl_sign_str}€{perdita_eur:.2f}",
            language="text"
        )
        st.markdown(
            f"Nel tuo caso: una **{pl_word} virtuale di €{perdita_fmt}** "
            f"(= {perdita_pct:+.2f}% sul capitale investito)."
        )

        # 7 — BREAK-EVEN
        st.markdown(f"**7️⃣ BREAK-EVEN = +{break_even_pct:.2f}%**")
        st.markdown("È di quanto deve risalire il prezzo per *tornare in pari*:")
        st.code(
            f"Break-even = (PMC ÷ Prezzo finale − 1) × 100\n"
            f"           = (€{pmc_value:.3f} ÷ €{prezzo_finale:.3f} − 1) × 100\n"
            f"           = +{break_even_pct:.2f}%",
            language="text"
        )
        st.markdown(
            f"Cioè dal prezzo attuale di €{prezzo_finale:.3f}, il titolo deve salire del "
            f"**{break_even_pct:.2f}%** per riportarti a profitto zero."
        )

        # CONFRONTO
        st.markdown("---")
        st.markdown("### 💡 Perché questo è importante")
        st.markdown(
            f"Senza Median Strategy (cioè comprando tutto il budget a €{prezzo_iniziale:.2f} "
            f"il giorno 1), il tuo PMC sarebbe **€{prezzo_iniziale:.3f}** e il break-even "
            f"necessario sarebbe **+{be_allin:.2f}%**."
        )
        st.markdown(
            f"Con la Median Strategy il break-even è sceso a **+{break_even_pct:.2f}%** — "
            f"*risparmio di {risparmio_be:.2f} punti percentuali* di recupero necessario."
        )
        st.markdown("È questa la matematica che lavora per te.")


# ============================================================
# PIANO TRANCHE
# ============================================================
st.markdown('<div class="section-title">🎯 Piano Tranche</div>', unsafe_allow_html=True)

for t in tranches_raw:
    status_class = f"t{t['num']}" if t["valido"] else "blocked"
    status_icon = "✓" if t["valido"] else "✗"
    status_color = COL_PROFIT if t["valido"] else COL_RISK

    eseguito = next((a for a in risultato["acquisti"] if a["tranche_num"] == t["num"]), None)

    if eseguito:
        override_badge = ""
        if eseguito.get("override"):
            override_badge = f" <span style='background:{COL_ACCENT}; color:{COL_BG}; padding:1px 6px; border-radius:6px; font-size:0.7rem; font-weight:800;'>MANUAL</span>"
        info_exec = f"@ €{eseguito['prezzo']:.3f} · giorno {eseguito['giorno']}{override_badge}"
        n_az_str = f"{eseguito['n_azioni']} az."
    else:
        info_exec = "in attesa"
        n_az_str = f"~{t['n_azioni_iniziali']} az."

    motivo = ""
    if not t["valido"]:
        motivo = f"<br><span class='risk' style='font-weight:700;'>⚠ Tranche troppo piccola — incidenza {t['incidenza_pct']:.3f}% > 0.20%</span>"

    st.markdown(f"""
    <div class="tranche-box {status_class}">
        <div class="tranche-head">
            <span style="color:{status_color};">{status_icon} TRANCHE {t['num']}</span>
            &nbsp;·&nbsp; {t['peso']*100:.0f}%
            &nbsp;·&nbsp; €{t['capitale_lordo']:,.0f}
            &nbsp;·&nbsp; {n_az_str}
        </div>
        <div class="tranche-info">
            {info_exec} · commissione €{t['commissione']:.2f} ({t['incidenza_pct']:.3f}%)
        </div>
        {motivo}
    </div>
    """.replace(",", "."), unsafe_allow_html=True)


# ============================================================
# GRAFICO
# ============================================================
st.markdown('<div class="section-title">📈 Stress Test Simulator</div>', unsafe_allow_html=True)

giorni = list(range(len(risultato["prezzi"])))
prezzi_serie = risultato["prezzi"]
pmc_serie = [h.get("pmc", None) if h.get("pmc", 0) > 0 else None for h in risultato["pmc_history"]]

def build_chart(for_export=False):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=giorni, y=prezzi_serie, mode="lines+markers",
        name="Prezzo",
        line=dict(color=COL_RISK, width=4, shape="spline"),
        marker=dict(size=14, line=dict(width=3, color=COL_BG)),
        hovertemplate="<b>Giorno %{x}</b><br>Prezzo: €%{y:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=giorni, y=pmc_serie, mode="lines+markers",
        name="PMC",
        line=dict(color=COL_PROFIT, width=4, dash="dot", shape="spline"),
        marker=dict(size=14, symbol="diamond", line=dict(width=3, color=COL_BG)),
        hovertemplate="<b>Giorno %{x}</b><br>PMC: €%{y:.3f}<extra></extra>",
    ))
    for zone, label, color in [
        (buy_zones["p1sigma"], "-1σ", COL_ACCENT),
        (buy_zones["p2sigma"], "-2σ", COL_WARN),
        (buy_zones["p3sigma"], "-3σ", COL_RISK),
    ]:
        fig.add_hline(
            y=zone, line_dash="dash", line_color=color, line_width=2, opacity=0.6,
            annotation_text=f"<b>{label}</b> €{zone:.2f}",
            annotation_position="right",
            annotation_font=dict(family="JetBrains Mono", size=12, color=color),
        )
    for a in risultato["acquisti"]:
        fig.add_trace(go.Scatter(
            x=[a["giorno"]], y=[a["prezzo"]], mode="markers+text",
            marker=dict(size=24, color=COL_ACCENT, symbol="circle",
                        line=dict(width=4, color=COL_BG)),
            text=[f"<b>T{a['tranche_num']}</b>"],
            textposition="top center",
            textfont=dict(family="JetBrains Mono", size=14, color=COL_TEXT),
            showlegend=False,
            hovertemplate=f"<b>T{a['tranche_num']}</b><br>€{a['prezzo']:.3f}<br>{a['n_azioni']} az.<extra></extra>",
        ))

    layout_kwargs = dict(
        template="plotly_dark",
        paper_bgcolor=COL_BG, plot_bgcolor=COL_CARD,
        font=dict(family="JetBrains Mono", color=COL_TEXT, size=13),
        xaxis=dict(
            title=dict(text="<b>Giorno</b>", font=dict(size=13, color=COL_TEXT_LABEL)),
            gridcolor=COL_BORDER, zerolinecolor=COL_BORDER, dtick=1,
            tickfont=dict(size=12, color=COL_TEXT),
        ),
        yaxis=dict(
            title=dict(text="<b>Prezzo (€)</b>", font=dict(size=13, color=COL_TEXT_LABEL)),
            gridcolor=COL_BORDER, zerolinecolor=COL_BORDER, tickformat=".2f",
            tickfont=dict(size=12, color=COL_TEXT),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor=COL_CARD, bordercolor=COL_BORDER, borderwidth=1.5,
            font=dict(size=13, color=COL_TEXT, family="JetBrains Mono"),
        ),
        hovermode="x unified",
    )
    if for_export:
        ticker_clean = ticker_label.strip().upper() if ticker_label.strip() else "TITOLO"
        titolo = f"Median Strategy Directa · {ticker_clean} · {budget:,}€".replace(",", ".")
        sub = (f"PMC €{pmc_value:.3f} · BE +{break_even_pct:.2f}% · "
               f"P/L {'+' if perdita_eur >= 0 else ''}€{perdita_eur:.2f} ({perdita_pct:+.2f}%)")
        layout_kwargs["title"] = dict(
            text=f"<b>{titolo}</b><br><sup style='color:{COL_TEXT_LABEL};'>{sub}</sup>",
            font=dict(size=18, color=COL_TEXT), x=0.5, xanchor="center",
        )
        layout_kwargs["width"] = 1080
        layout_kwargs["height"] = 1080
        layout_kwargs["margin"] = dict(l=60, r=80, t=110, b=60)
    else:
        layout_kwargs["height"] = 460
        layout_kwargs["margin"] = dict(l=15, r=70, t=40, b=45)

    fig.update_layout(**layout_kwargs)
    return fig

fig_display = build_chart(for_export=False)
st.plotly_chart(fig_display, use_container_width=True, config={"displayModeBar": False})


# ============================================================
# BUY ZONES
# ============================================================
st.markdown('<div class="section-title">🎯 Buy Zones (σ-based)</div>', unsafe_allow_html=True)

bz_col1, bz_col2, bz_col3 = st.columns(3)
for col, (key_p, key_pct, label, color) in zip(
    [bz_col1, bz_col2, bz_col3],
    [
        ("p1sigma", "pct1", "-1σ", COL_ACCENT),
        ("p2sigma", "pct2", "-2σ", COL_WARN),
        ("p3sigma", "pct3", "-3σ", COL_RISK),
    ]
):
    with col:
        triggered = prezzo_finale <= buy_zones[key_p]
        trig_label = "🟢 HIT" if triggered else "⚪ —"
        st.markdown(f"""
        <div class="metric-card" style="border-left:4px solid {color};">
            <div class="metric-label" style="color:{color};">{label}</div>
            <div class="metric-value" style="font-size:1.3rem;">€{buy_zones[key_p]:.2f}</div>
            <div class="metric-delta neutral">{buy_zones[key_pct]:+.1f}%</div>
            <div class="metric-delta" style="font-weight:800;">{trig_label}</div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# EXPORT + ARCHIVIO
# ============================================================
st.markdown('<div class="section-title">📤 Esporta & Salva</div>', unsafe_allow_html=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
nome_sim = f"{ticker_clean}_{budget}_{timestamp}"


def genera_png_matplotlib():
    """
    Genera PNG via matplotlib — robusto su Streamlit Cloud (zero deps di sistema).
    Output verticale formato story-friendly con:
    - Header (titolo + ticker + budget)
    - Grafico prezzo/PMC con Buy Zones
    - Tabella tranche con numero azioni per ciascuna
    - Griglia statistiche chiave
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    import io

    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.weight': 'bold',
    })

    # 4 sezioni: header, chart, tranche, stats
    fig, (ax_head, ax_chart, ax_tranche, ax_stats) = plt.subplots(
        4, 1, figsize=(10.8, 16.2),
        gridspec_kw={'height_ratios': [1.0, 4.0, 2.8, 2.2]},
        facecolor=COL_BG,
    )

    # ---- HEADER ----
    ax_head.set_facecolor(COL_BG)
    ax_head.axis('off')
    ax_head.text(0.5, 0.78, "MEDIAN STRATEGY DIRECTA",
                 ha='center', va='center', fontsize=28, fontweight='bold',
                 color=COL_PROFIT, transform=ax_head.transAxes)
    ax_head.text(0.5, 0.38, f"{ticker_clean} · Budget {budget:,}€ · {n_tranche_choice} Tranche".replace(",", "."),
                 ha='center', va='center', fontsize=16, fontweight='bold',
                 color=COL_TEXT_LABEL, transform=ax_head.transAxes)
    ax_head.text(0.5, 0.08, datetime.now().strftime("%d/%m/%Y · %H:%M"),
                 ha='center', va='center', fontsize=11,
                 color=COL_TEXT_DIM, transform=ax_head.transAxes)

    # ---- CHART ----
    ax_chart.set_facecolor(COL_CARD)

    ax_chart.plot(giorni, prezzi_serie, 'o-', color=COL_RISK, linewidth=3.5,
                  markersize=12, markeredgewidth=2.5, markeredgecolor=COL_BG,
                  label='Prezzo', zorder=3)
    pmc_clean = [p if p else None for p in pmc_serie]
    valid_idx = [i for i, p in enumerate(pmc_clean) if p is not None]
    valid_x = [giorni[i] for i in valid_idx]
    valid_y = [pmc_clean[i] for i in valid_idx]
    ax_chart.plot(valid_x, valid_y, 'D--', color=COL_PROFIT, linewidth=3.5,
                  markersize=12, markeredgewidth=2.5, markeredgecolor=COL_BG,
                  label='PMC', zorder=4)

    for zone, label, color in [
        (buy_zones["p1sigma"], "-1σ", COL_ACCENT),
        (buy_zones["p2sigma"], "-2σ", COL_WARN),
        (buy_zones["p3sigma"], "-3σ", COL_RISK),
    ]:
        ax_chart.axhline(y=zone, linestyle='--', color=color, linewidth=1.8, alpha=0.6)
        ax_chart.text(max(giorni) + 0.15, zone, f" {label}  €{zone:.2f}",
                      color=color, fontsize=11, fontweight='bold', va='center')

    for a in risultato["acquisti"]:
        ax_chart.scatter(a["giorno"], a["prezzo"], s=400, c=COL_ACCENT,
                         edgecolors=COL_BG, linewidths=3, zorder=5)
        ax_chart.annotate(f'T{a["tranche_num"]}',
                          (a["giorno"], a["prezzo"]),
                          textcoords="offset points", xytext=(0, 22),
                          ha='center', fontsize=13, fontweight='bold',
                          color=COL_TEXT, zorder=6)

    ax_chart.set_xlabel('GIORNO', color=COL_TEXT_LABEL, fontsize=12, fontweight='bold', labelpad=10)
    ax_chart.set_ylabel('PREZZO (€)', color=COL_TEXT_LABEL, fontsize=12, fontweight='bold', labelpad=10)
    ax_chart.tick_params(colors=COL_TEXT, labelsize=11)
    for spine in ax_chart.spines.values():
        spine.set_color(COL_BORDER)
    ax_chart.grid(True, color=COL_BORDER, alpha=0.4, linestyle='-', linewidth=0.5)
    ax_chart.set_xticks(giorni)
    ax_chart.legend(loc='upper right', facecolor=COL_CARD, edgecolor=COL_BORDER,
                    labelcolor=COL_TEXT, fontsize=12, framealpha=1)

    # ---- TRANCHE TABLE ----
    ax_tranche.set_facecolor(COL_BG)
    ax_tranche.axis('off')

    # Titolo sezione
    ax_tranche.text(0.5, 0.96, "PIANO TRANCHE",
                    ha='center', va='top', fontsize=18, fontweight='bold',
                    color=COL_TEXT, transform=ax_tranche.transAxes)

    # Header tabella
    headers = ["#", "PESO", "CAPITALE", "PREZZO", "AZIONI", "COMM."]
    col_x = [0.05, 0.17, 0.32, 0.50, 0.68, 0.85]  # posizioni X colonne
    header_y = 0.80
    for hx, h in zip(col_x, headers):
        ax_tranche.text(hx, header_y, h, ha='left', va='center',
                        fontsize=11, fontweight='bold',
                        color=COL_TEXT_LABEL, transform=ax_tranche.transAxes)

    # Linea separatrice header
    ax_tranche.plot([0.04, 0.96], [header_y - 0.08, header_y - 0.08],
                    color=COL_BORDER, linewidth=1.5,
                    transform=ax_tranche.transAxes, clip_on=False)

    # Righe tranche (sia eseguite che pending/bloccate per chiarezza)
    row_start = header_y - 0.18
    row_height = 0.16

    # Colori per tranche progressivi
    tranche_colors = ["#7FD3FF", COL_ACCENT, COL_PROFIT, COL_WARN]

    for idx, t in enumerate(tranches_raw):
        y = row_start - idx * row_height
        eseguito = next((a for a in risultato["acquisti"] if a["tranche_num"] == t["num"]), None)

        # Bullet colorato + numero tranche
        t_color = tranche_colors[idx] if t["valido"] else COL_RISK
        ax_tranche.scatter(col_x[0] + 0.01, y, s=180, c=t_color,
                           edgecolors=COL_BG, linewidths=2,
                           transform=ax_tranche.transAxes, clip_on=False, zorder=3)
        ax_tranche.text(col_x[0] + 0.01, y, f"{t['num']}",
                        ha='center', va='center', fontsize=11, fontweight='bold',
                        color=COL_BG, transform=ax_tranche.transAxes, zorder=4)

        # Peso
        ax_tranche.text(col_x[1], y, f"{int(t['peso']*100)}%",
                        ha='left', va='center', fontsize=14, fontweight='bold',
                        color=COL_TEXT, transform=ax_tranche.transAxes)

        # Capitale
        ax_tranche.text(col_x[2], y, f"€{t['capitale_lordo']:,.0f}".replace(",", "."),
                        ha='left', va='center', fontsize=14, fontweight='bold',
                        color=COL_TEXT, transform=ax_tranche.transAxes)

        # Prezzo (solo se eseguita)
        if eseguito:
            prezzo_str = f"€{eseguito['prezzo']:.3f}"
            # Aggiungo asterisco se override manuale
            azioni_str = f"{eseguito['n_azioni']}*" if eseguito.get("override") else f"{eseguito['n_azioni']}"
            azioni_color = t_color
            prezzo_color = COL_TEXT
        elif not t["valido"]:
            prezzo_str = "—"
            azioni_str = "✗ BLOCCATA"
            azioni_color = COL_RISK
            prezzo_color = COL_TEXT_DIM
        else:
            prezzo_str = "in attesa"
            azioni_str = f"~{t['n_azioni_iniziali']}"
            azioni_color = COL_TEXT_DIM
            prezzo_color = COL_TEXT_DIM

        ax_tranche.text(col_x[3], y, prezzo_str,
                        ha='left', va='center', fontsize=14, fontweight='bold',
                        color=prezzo_color, transform=ax_tranche.transAxes)

        # Azioni (in evidenza con colore tranche)
        ax_tranche.text(col_x[4], y, azioni_str,
                        ha='left', va='center', fontsize=15, fontweight='bold',
                        color=azioni_color, transform=ax_tranche.transAxes)

        # Commissione
        ax_tranche.text(col_x[5], y, f"€{t['commissione']:.2f}",
                        ha='left', va='center', fontsize=13,
                        color=COL_TEXT_DIM, transform=ax_tranche.transAxes)

    # Legenda asterisco se ci sono override
    has_override = any(a.get("override") for a in risultato["acquisti"])
    if has_override:
        ax_tranche.text(0.5, 0.04,
                        "* = quantità inserita manualmente",
                        ha='center', va='center', fontsize=10, fontstyle='italic',
                        color=COL_ACCENT, transform=ax_tranche.transAxes)

    # ---- STATS GRID ----
    ax_stats.set_facecolor(COL_BG)
    ax_stats.axis('off')

    pl_sign = '+' if perdita_eur >= 0 else ''
    pl_color = COL_PROFIT if perdita_eur >= 0 else COL_RISK
    be_color = COL_PROFIT if break_even_pct < 10 else (COL_WARN if break_even_pct < 20 else COL_RISK)

    metrics = [
        ("PMC",       f"€{pmc_value:.3f}",                         COL_ACCENT),
        ("BREAK-EVEN", f"+{break_even_pct:.2f}%",                  be_color),
        ("INVESTITO", f"€{pmc_finale.get('costo_totale', 0):,.0f}".replace(",", "."), COL_TEXT),
        ("P/L",       f"{pl_sign}€{perdita_eur:.2f}",              pl_color),
        ("AZIONI TOT", f"{pmc_finale.get('azioni_totali', 0)}",    COL_TEXT),
        ("COMM. TOT", f"€{pmc_finale.get('commissioni_totali', 0):.2f}", COL_TEXT_DIM),
    ]
    n_cols = 3
    for i, (label, value, color) in enumerate(metrics):
        row = i // n_cols
        col = i % n_cols
        x = 0.04 + col * 0.32
        y = 0.78 - row * 0.42
        w = 0.28
        h = 0.36

        box = FancyBboxPatch((x, y - h), w, h,
                             boxstyle="round,pad=0.01,rounding_size=0.02",
                             linewidth=1.5, edgecolor=COL_BORDER,
                             facecolor=COL_CARD, transform=ax_stats.transAxes)
        ax_stats.add_patch(box)
        ax_stats.text(x + w/2, y - 0.08, label,
                      ha='center', va='top', fontsize=10, fontweight='bold',
                      color=COL_TEXT_LABEL, transform=ax_stats.transAxes)
        ax_stats.text(x + w/2, y - h/2 - 0.02, value,
                      ha='center', va='center', fontsize=18, fontweight='bold',
                      color=color, transform=ax_stats.transAxes)

    plt.tight_layout()
    plt.subplots_adjust(top=0.97, bottom=0.03, left=0.06, right=0.94, hspace=0.20)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=COL_BG, dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    try:
        png_bytes = genera_png_matplotlib()
        st.download_button(
            label="📸 Scarica PNG",
            data=png_bytes,
            file_name=f"{nome_sim}.png",
            mime="image/png",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Errore export PNG: {e}")

with col_exp2:
    if st.button("💾 Salva in archivio", use_container_width=True):
        sim_data = {
            "id": timestamp,
            "nome": nome_sim,
            "ticker": ticker_clean,
            "budget": budget,
            "n_tranche": n_tranche_choice,
            "prezzo_iniziale": prezzo_iniziale,
            "sigma": sigma_giornaliera,
            "crolli": crolli_usati,
            "pmc_finale": pmc_value,
            "break_even_pct": break_even_pct,
            "prezzo_finale": prezzo_finale,
            "perdita_eur": perdita_eur,
            "perdita_pct": perdita_pct,
            "azioni_totali": pmc_finale.get("azioni_totali", 0),
            "investito": pmc_finale.get("costo_totale", 0),
            "commissioni": pmc_finale.get("commissioni_totali", 0),
            "data_creazione": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        st.session_state.archivio.append(sim_data)
        st.success(f"✓ Salvata: {nome_sim}")

st.caption("💡 *Su smartphone: tocca \"Scarica PNG\", poi nella schermata di download tocca \"Salva immagine\" per portarla in Galleria.*")


# ============================================================
# ARCHIVIO STORICO
# ============================================================
st.markdown('<div class="section-title">🗄️ Archivio Storico</div>', unsafe_allow_html=True)

if not st.session_state.archivio:
    st.caption("Nessuna simulazione salvata. Usa 'Salva in archivio' per aggiungerla qui.")
else:
    for idx in range(len(st.session_state.archivio) - 1, -1, -1):
        sim = st.session_state.archivio[idx]
        col_a, col_b = st.columns([10, 1])
        with col_a:
            be_color = COL_PROFIT if sim["break_even_pct"] < 10 else (COL_WARN if sim["break_even_pct"] < 20 else COL_RISK)
            pl_color = COL_PROFIT if sim["perdita_eur"] >= 0 else COL_RISK
            pl_sign = '+' if sim["perdita_eur"] >= 0 else ''
            st.markdown(f"""
            <div class="archive-item">
                <div style="font-weight:800; color:{COL_TEXT}; font-size:0.95rem;">
                    {sim["ticker"]} · €{sim["budget"]:,} · {sim["n_tranche"]}T
                </div>
                <div style="color:{COL_TEXT_DIM}; font-size:0.78rem; margin-top:0.3rem;">
                    {sim["data_creazione"]}
                </div>
                <div style="margin-top:0.5rem; display:flex; gap:1rem; flex-wrap:wrap;">
                    <span><span style="color:{COL_TEXT_LABEL};">PMC </span>
                        <strong style="color:{COL_ACCENT};">€{sim["pmc_finale"]:.3f}</strong></span>
                    <span><span style="color:{COL_TEXT_LABEL};">BE </span>
                        <strong style="color:{be_color};">+{sim["break_even_pct"]:.2f}%</strong></span>
                    <span><span style="color:{COL_TEXT_LABEL};">P/L </span>
                        <strong style="color:{pl_color};">{pl_sign}€{sim["perdita_eur"]:.2f}</strong></span>
                </div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)
        with col_b:
            if st.button("🗑️", key=f"del_{sim['id']}_{idx}", help="Elimina simulazione"):
                st.session_state.archivio.pop(idx)
                st.rerun()

    archivio_json = json.dumps(st.session_state.archivio, indent=2, ensure_ascii=False)
    st.download_button(
        label="📥 Esporta archivio (JSON)",
        data=archivio_json,
        file_name=f"median_strategy_archivio_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )


# ============================================================
# INGEGNERIA DEL RISCHIO
# ============================================================
st.markdown('<div class="section-title">🛠️ Ingegneria del Rischio</div>', unsafe_allow_html=True)

with st.expander("💰 Money Management — Perché tranche crescenti?"):
    st.markdown(f"""
**La regola 20/30/50 (3 tranche) e 10/20/30/40 (4 tranche)** si fonda su tre principi:

1. **Asimmetria della convinzione**: al primo ingresso *non sai* se hai ragione. La tranche iniziale piccola è una "sonda".
2. **Pull-down matematico del PMC**: la tranche più grande va investita al prezzo più basso. Se compri il 50% del capitale al minimo, sposti il PMC molto più di quanto farebbe l'equal-weight.
3. **Munizioni residue**: lasciare 40–50% del capitale per l'ultima tranche significa avere potenza di fuoco quando il mercato è in panic mode.

**Esempio numerico** ({budget:,}€):
- Equal-weight su {n_tranche_choice} tranche → PMC = media semplice dei {n_tranche_choice} prezzi
- Pesato {'10/20/30/40' if n_tranche_choice == 4 else '20/30/50'} → l'ultimo prezzo pesa **{'4' if n_tranche_choice == 4 else '2.5'} volte** il primo

Se il prezzo crolla, il PMC scende molto più velocemente.
""".replace(",", "."))

with st.expander("⚖️ Commissione Directa — Il filtro 0.20%"):
    st.markdown("""
**Commissione Directa**: 1.90€ ogni 1000€ di controvalore (**0.19%**), minimo **1.50€**.

| Controvalore | Commissione | Incidenza |
|---|---|---|
| 500€ | 1.50€ (min) | 0.300% ❌ |
| 789€ | 1.50€ (min) | 0.190% ✓ |
| 1.000€ | 1.90€ | 0.190% ✓ |
| 2.000€ | 3.80€ | 0.190% ✓ |
| 5.000€ | 9.50€ | 0.190% ✓ |

**La regola d'oro**: la commissione one-way non deve superare lo **0.20%** del controvalore. Sotto ~789€ scatta il minimo fisso di 1.50€ e l'incidenza supera lo 0.20% → l'app marca la tranche come *bloccata*.

Tranche minima efficiente: **~750€**.

Considerando andata + ritorno (0.38% complessivo a regime), su una mean-reversion del 1% lasci sul tavolo già metà del rendimento atteso.
""")

with st.expander("📐 Legge del Recupero Percentuale"):
    st.markdown("""
La trappola psicologica più sottovalutata del trading:

| Perdita | Recupero necessario |
|---|---|
| −10% | +11.1% |
| −20% | +25.0% |
| −30% | +42.9% |
| −40% | +66.7% |
| **−50%** | **+100%** |
| −70% | +233% |

Formula: `recupero = perdita / (1 − perdita)`

**Implicazione operativa**:
- Sotto **−10%** dal PMC → mediare se la tesi è ancora valida
- Sotto **−25%** → chiediti se non sei in una "value trap"
- Sotto **−40%** → lo stop loss è quasi sempre meglio del double down

La Median Strategy funziona finché i crolli stanno entro range statistici (±2-3σ). Oltre, il titolo sta probabilmente scontando informazioni *fondamentali* nuove (delisting, FDA rejection, fraud) e nessuna media risolve.
""")

with st.expander("📊 Deviazioni Standard — Buy Zones"):
    st.markdown(f"""
Le **Buy Zones** usano la volatilità giornaliera σ ({sigma_giornaliera}%):

- **−1σ**: copre il 68% dei movimenti. Correzione *fisiologica*. Entrata standard.
- **−2σ**: copre il 95%. Statisticamente "oversold". Buon punto di add.
- **−3σ**: copre il 99.7%. Evento raro. O panic selling (occasione), o c'è una *news* che cambia tutto.

**Tarare σ correttamente**:
- Blue chip (Enel, Generali): σ ≈ 1.0–1.5%
- Tech mid-cap NASDAQ: σ ≈ 2.5–3.5%
- **Biotech small-cap pre-catalyst**: σ ≈ 4–7%
- Biotech in PDUFA week: σ può schizzare al 15–20%

Sottostimare σ → entri troppo presto. Sovrastimarla → aspetti prezzi che non arrivano mai.
""")

st.markdown("---")
st.caption(
    "⚠️ **Disclaimer**: nessuna simulazione garantisce il profitto. La Median Strategy è una "
    "tecnica di gestione del rischio, non di previsione. Il successo dipende dalla disciplina "
    "di eseguire l'ultima tranche quando *tutto è rosso* — è lì che la matematica lavora per te."
)
