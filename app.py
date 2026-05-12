"""
Smart DCA Directa — Simulatore di Dollar Cost Averaging ottimizzato
per il broker Directa (commissione fissa 1.5€).

Logica:
- Filtro efficienza: ogni tranche deve avere commissione ≤ 0.20% del valore
- Pesi crescenti (20/30/50 per 5k, 10/20/30/40 per 10k)
- Stress test su crollo consecutivo
- Buy Zone su -1σ / -2σ / -3σ dal prezzo iniziale

Author: Os — built with Claude
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# CONFIG
# ============================================================
COMMISSIONE_DIRECTA = 1.50  # €
SOGLIA_EFFICIENZA = 0.0020  # 0.20% max incidenza commissionale per tranche
COLORE_PROFITTO = "#50C878"   # verde smeraldo
COLORE_RISCHIO = "#FF6B6B"    # rosso corallo
COLORE_NEUTRO = "#94A3B8"     # grigio-blu
COLORE_ACCENT = "#38BDF8"     # azzurro accent
COLORE_BG = "#0A0E1A"
COLORE_CARD = "#131826"
COLORE_CARD_BORDER = "#1F2937"

PESI_5K = [0.20, 0.30, 0.50]
PESI_10K = [0.10, 0.20, 0.30, 0.40]

st.set_page_config(
    page_title="Smart DCA Directa",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS — Dark mode premium banking aesthetic
# ============================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, sans-serif;
    background-color: {COLORE_BG};
}}

.stApp {{
    background: linear-gradient(180deg, {COLORE_BG} 0%, #060912 100%);
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background-color: {COLORE_CARD};
    border-right: 1px solid {COLORE_CARD_BORDER};
}}

/* Header titolo */
.main-title {{
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 1.9rem;
    background: linear-gradient(135deg, {COLORE_PROFITTO} 0%, {COLORE_ACCENT} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
    margin-bottom: 0.2rem;
}}
.main-sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: {COLORE_NEUTRO};
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}}

/* Card metriche */
.metric-card {{
    background: {COLORE_CARD};
    border: 1px solid {COLORE_CARD_BORDER};
    border-radius: 14px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.7rem;
    transition: border-color 0.2s;
}}
.metric-card:hover {{
    border-color: {COLORE_ACCENT};
}}
.metric-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: {COLORE_NEUTRO};
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}}
.metric-value {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 1.4rem;
    line-height: 1.1;
}}
.metric-delta {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    margin-top: 0.3rem;
}}
.profit {{ color: {COLORE_PROFITTO}; }}
.risk   {{ color: {COLORE_RISCHIO}; }}
.neutral{{ color: {COLORE_NEUTRO}; }}
.accent {{ color: {COLORE_ACCENT}; }}

/* Tranche box */
.tranche-box {{
    background: {COLORE_CARD};
    border-left: 3px solid {COLORE_ACCENT};
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}}
.tranche-box.t1 {{ border-left-color: #94A3B8; }}
.tranche-box.t2 {{ border-left-color: #38BDF8; }}
.tranche-box.t3 {{ border-left-color: #50C878; }}
.tranche-box.t4 {{ border-left-color: #F59E0B; }}
.tranche-box.blocked {{ border-left-color: {COLORE_RISCHIO}; opacity: 0.7; }}

/* Sezione titoli */
.section-title {{
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 1.05rem;
    color: #E2E8F0;
    margin-top: 1.5rem;
    margin-bottom: 0.7rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid {COLORE_CARD_BORDER};
}}

/* Streamlit overrides */
.stSlider > div > div > div > div {{
    background-color: {COLORE_ACCENT};
}}
.stButton > button {{
    background: linear-gradient(135deg, {COLORE_ACCENT} 0%, {COLORE_PROFITTO} 100%);
    color: {COLORE_BG};
    border: none;
    border-radius: 10px;
    font-weight: 700;
    font-family: 'Inter', sans-serif;
    padding: 0.6rem 1.5rem;
}}
.stRadio > label, .stSelectbox > label, .stNumberInput > label, .stSlider > label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: {COLORE_NEUTRO};
}}

/* Expander */
.streamlit-expanderHeader {{
    background-color: {COLORE_CARD};
    border-radius: 10px;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
}}

/* Mobile responsive */
@media (max-width: 640px) {{
    .main-title {{ font-size: 1.5rem; }}
    .metric-value {{ font-size: 1.2rem; }}
    .block-container {{ padding-top: 1rem; padding-left: 0.8rem; padding-right: 0.8rem; }}
}}

footer, #MainMenu {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)


# ============================================================
# CORE LOGIC
# ============================================================

def calcola_tranches(budget_totale: float, pesi: list, prezzo_corrente: float):
    """
    Calcola le tranche e applica il filtro di efficienza commissionale.
    Ritorna lista di dict con: peso, capitale, valido, motivo_blocco.
    """
    tranches = []
    for i, peso in enumerate(pesi):
        capitale = budget_totale * peso
        # Capitale al netto della commissione disponibile per acquisto azioni
        capitale_netto = capitale - COMMISSIONE_DIRECTA
        incidenza = COMMISSIONE_DIRECTA / capitale if capitale > 0 else 1
        valido = incidenza <= SOGLIA_EFFICIENZA
        n_azioni = int(capitale_netto / prezzo_corrente) if prezzo_corrente > 0 else 0

        tranches.append({
            "num": i + 1,
            "peso": peso,
            "capitale_lordo": capitale,
            "capitale_netto": capitale_netto,
            "incidenza_pct": incidenza * 100,
            "valido": valido,
            "n_azioni_iniziali": n_azioni,
        })
    return tranches


def calcola_pmc(acquisti: list) -> dict:
    """
    Calcola Prezzo Medio di Carico, totale investito e azioni.
    acquisti: lista di dict {prezzo, n_azioni, commissione}
    """
    if not acquisti:
        return {"pmc": 0, "azioni_totali": 0, "investito_totale": 0, "commissioni_totali": 0}

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


def simula_stress_test(tranches_valide: list, prezzo_iniziale: float, crolli: list):
    """
    Esegue lo stress test: ad ogni step di crollo, esegue la tranche corrispondente.
    crolli: lista di percentuali negative [-3, -5, -10]
    Ritorna: prezzi_giornalieri, acquisti_eseguiti, pmc_progressivo
    """
    prezzi = [prezzo_iniziale]
    acquisti = []
    pmc_history = []

    # Day 0 — prima tranche al prezzo iniziale
    if len(tranches_valide) > 0:
        t = tranches_valide[0]
        n_az = int((t["capitale_lordo"] - COMMISSIONE_DIRECTA) / prezzo_iniziale)
        if n_az > 0:
            acquisti.append({
                "giorno": 0,
                "prezzo": prezzo_iniziale,
                "n_azioni": n_az,
                "commissione": COMMISSIONE_DIRECTA,
                "tranche_num": t["num"],
                "capitale": t["capitale_lordo"],
            })
    pmc_history.append(calcola_pmc(acquisti))

    # Day 1..N — applica crolli sequenziali e tranche successive
    prezzo_corrente = prezzo_iniziale
    for i, crollo_pct in enumerate(crolli):
        prezzo_corrente = prezzo_corrente * (1 + crollo_pct / 100)
        prezzi.append(prezzo_corrente)

        # Esegui tranche i+1 (se esiste e valida)
        if (i + 1) < len(tranches_valide):
            t = tranches_valide[i + 1]
            n_az = int((t["capitale_lordo"] - COMMISSIONE_DIRECTA) / prezzo_corrente)
            if n_az > 0:
                acquisti.append({
                    "giorno": i + 1,
                    "prezzo": prezzo_corrente,
                    "n_azioni": n_az,
                    "commissione": COMMISSIONE_DIRECTA,
                    "tranche_num": t["num"],
                    "capitale": t["capitale_lordo"],
                })
        pmc_history.append(calcola_pmc(acquisti))

    return {
        "prezzi": prezzi,
        "acquisti": acquisti,
        "pmc_history": pmc_history,
        "prezzo_finale": prezzo_corrente,
    }


def calcola_buy_zones(prezzo_iniziale: float, sigma_pct: float):
    """
    Buy Zone basate su deviazioni standard.
    sigma_pct = volatilità giornaliera attesa (%)
    Ritorna: livelli -1σ, -2σ, -3σ in € e in %
    """
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
# SIDEBAR — Parametri
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ PARAMETRI")

    budget = st.radio(
        "Budget totale",
        options=[5000, 10000],
        format_func=lambda x: f"{x:,}€".replace(",", "."),
        horizontal=True,
    )

    prezzo_iniziale = st.number_input(
        "Prezzo iniziale (€)",
        min_value=0.01,
        max_value=10000.0,
        value=25.00,
        step=0.10,
        format="%.2f",
    )

    sigma_giornaliera = st.slider(
        "Volatilità giornaliera σ (%)",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        help="Deviazione standard giornaliera del titolo. Biotech small-cap: 4-7%. Blue chip: 1-2%.",
    )

    st.markdown("---")
    st.markdown("### 📉 STRESS TEST")
    st.caption("Scenario di crollo consecutivo (giorni)")

    crollo_d1 = st.slider("Giorno 1", -20.0, 0.0, -3.0, 0.5, format="%.1f%%")
    crollo_d2 = st.slider("Giorno 2", -20.0, 0.0, -5.0, 0.5, format="%.1f%%")
    crollo_d3 = st.slider("Giorno 3", -20.0, 0.0, -10.0, 0.5, format="%.1f%%")

    n_tranche = 3 if budget == 5000 else 4
    if n_tranche == 4:
        crollo_d4 = st.slider("Giorno 4", -20.0, 0.0, -7.0, 0.5, format="%.1f%%")
        crolli = [crollo_d1, crollo_d2, crollo_d3, crollo_d4]
    else:
        crolli = [crollo_d1, crollo_d2, crollo_d3]


# ============================================================
# MAIN — Header
# ============================================================
st.markdown('<div class="main-title">Smart DCA Directa</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="main-sub">Budget {budget:,}€ · Commissione 1.50€ · Filtro 0.20%</div>'.replace(",", "."),
    unsafe_allow_html=True,
)

# ============================================================
# CALCOLI
# ============================================================
pesi = PESI_5K if budget == 5000 else PESI_10K
tranches_raw = calcola_tranches(budget, pesi, prezzo_iniziale)
tranches_valide = [t for t in tranches_raw if t["valido"]]

risultato = simula_stress_test(tranches_valide, prezzo_iniziale, crolli[:len(tranches_valide) - 1] if len(tranches_valide) > 1 else [])
buy_zones = calcola_buy_zones(prezzo_iniziale, sigma_giornaliera)

pmc_finale = risultato["pmc_history"][-1] if risultato["pmc_history"] else {}
prezzo_finale = risultato["prezzo_finale"]
pmc_value = pmc_finale.get("pmc", 0)

# Break-even necessario (per tornare al PMC dal prezzo attuale)
if prezzo_finale > 0 and pmc_value > 0:
    break_even_pct = ((pmc_value / prezzo_finale) - 1) * 100
else:
    break_even_pct = 0

# Perdita massima
valore_attuale = pmc_finale.get("azioni_totali", 0) * prezzo_finale
costo_totale = pmc_finale.get("costo_totale", 0)
perdita_eur = valore_attuale - costo_totale
perdita_pct = (perdita_eur / costo_totale * 100) if costo_totale > 0 else 0


# ============================================================
# CARD METRICHE CHIAVE
# ============================================================
st.markdown('<div class="section-title">📊 Dashboard</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">PMC Attuale</div>
        <div class="metric-value accent">€{pmc_value:.3f}</div>
        <div class="metric-delta neutral">{pmc_finale.get("azioni_totali", 0)} azioni</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Break-Even</div>
        <div class="metric-value {'profit' if break_even_pct < 10 else 'risk'}">+{break_even_pct:.2f}%</div>
        <div class="metric-delta neutral">da prezzo finale €{prezzo_finale:.3f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Investito</div>
        <div class="metric-value">€{pmc_finale.get("costo_totale", 0):,.2f}</div>
        <div class="metric-delta neutral">Comm: €{pmc_finale.get("commissioni_totali", 0):.2f}</div>
    </div>
    """.replace(",", "."), unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">P/L Attuale</div>
        <div class="metric-value {'profit' if perdita_eur >= 0 else 'risk'}">
            {'+' if perdita_eur >= 0 else ''}€{perdita_eur:.2f}
        </div>
        <div class="metric-delta {'profit' if perdita_eur >= 0 else 'risk'}">{perdita_pct:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# PIANO TRANCHE
# ============================================================
st.markdown('<div class="section-title">🎯 Piano Tranche</div>', unsafe_allow_html=True)

for t in tranches_raw:
    status_class = f"t{t['num']}" if t["valido"] else "blocked"
    status_icon = "✓" if t["valido"] else "✗"
    status_color = COLORE_PROFITTO if t["valido"] else COLORE_RISCHIO

    eseguito = next((a for a in risultato["acquisti"] if a["tranche_num"] == t["num"]), None)

    if eseguito:
        prezzo_exec = f"€{eseguito['prezzo']:.3f}"
        info_exec = f"@ {prezzo_exec} · giorno {eseguito['giorno']}"
        n_az_str = f"{eseguito['n_azioni']} az."
    else:
        info_exec = "in attesa"
        n_az_str = f"~{t['n_azioni_iniziali']} az."

    motivo = "" if t["valido"] else f"<br><span class='risk'>⚠ Incidenza {t['incidenza_pct']:.3f}% > soglia 0.20%</span>"

    st.markdown(f"""
    <div class="tranche-box {status_class}">
        <span style="color:{status_color}; font-weight:700;">{status_icon} TRANCHE {t['num']}</span>
        &nbsp;·&nbsp; <strong>{t['peso']*100:.0f}%</strong>
        &nbsp;·&nbsp; €{t['capitale_lordo']:,.0f}
        &nbsp;·&nbsp; {n_az_str}
        <br><span class="neutral" style="font-size:0.75rem;">{info_exec} · commissione {t['incidenza_pct']:.3f}%</span>
        {motivo}
    </div>
    """.replace(",", "."), unsafe_allow_html=True)


# ============================================================
# GRAFICO PLOTLY — PMC vs Prezzo
# ============================================================
st.markdown('<div class="section-title">📈 Stress Test Simulator</div>', unsafe_allow_html=True)

giorni = list(range(len(risultato["prezzi"])))
prezzi_serie = risultato["prezzi"]
pmc_serie = [h.get("pmc", None) for h in risultato["pmc_history"]]

fig = go.Figure()

# Linea prezzo di mercato
fig.add_trace(go.Scatter(
    x=giorni,
    y=prezzi_serie,
    mode="lines+markers",
    name="Prezzo Mercato",
    line=dict(color=COLORE_RISCHIO, width=3, shape="spline"),
    marker=dict(size=10, line=dict(width=2, color=COLORE_BG)),
    hovertemplate="<b>Giorno %{x}</b><br>Prezzo: €%{y:.3f}<extra></extra>",
))

# Linea PMC
fig.add_trace(go.Scatter(
    x=giorni,
    y=pmc_serie,
    mode="lines+markers",
    name="PMC",
    line=dict(color=COLORE_PROFITTO, width=3, dash="dot", shape="spline"),
    marker=dict(size=10, symbol="diamond", line=dict(width=2, color=COLORE_BG)),
    hovertemplate="<b>Giorno %{x}</b><br>PMC: €%{y:.3f}<extra></extra>",
))

# Buy Zones (linee orizzontali)
for zone, label, color, alpha in [
    (buy_zones["p1sigma"], "-1σ Buy Zone", COLORE_ACCENT, 0.5),
    (buy_zones["p2sigma"], "-2σ Buy Zone", "#F59E0B", 0.5),
    (buy_zones["p3sigma"], "-3σ Buy Zone", COLORE_RISCHIO, 0.6),
]:
    fig.add_hline(
        y=zone,
        line_dash="dash",
        line_color=color,
        opacity=alpha,
        annotation_text=f"{label} · €{zone:.2f}",
        annotation_position="right",
        annotation_font=dict(family="JetBrains Mono", size=10, color=color),
    )

# Marker acquisti eseguiti
for a in risultato["acquisti"]:
    fig.add_trace(go.Scatter(
        x=[a["giorno"]],
        y=[a["prezzo"]],
        mode="markers+text",
        marker=dict(size=18, color=COLORE_ACCENT, symbol="circle",
                    line=dict(width=3, color=COLORE_BG)),
        text=[f"T{a['tranche_num']}"],
        textposition="top center",
        textfont=dict(family="JetBrains Mono", size=11, color="white"),
        showlegend=False,
        hovertemplate=f"<b>Tranche {a['tranche_num']}</b><br>€{a['prezzo']:.3f}<br>{a['n_azioni']} azioni<extra></extra>",
    ))

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor=COLORE_BG,
    plot_bgcolor=COLORE_CARD,
    font=dict(family="JetBrains Mono", color="#E2E8F0", size=11),
    height=440,
    margin=dict(l=20, r=80, t=30, b=40),
    xaxis=dict(
        title="Giorno",
        gridcolor=COLORE_CARD_BORDER,
        zerolinecolor=COLORE_CARD_BORDER,
        dtick=1,
    ),
    yaxis=dict(
        title="Prezzo (€)",
        gridcolor=COLORE_CARD_BORDER,
        zerolinecolor=COLORE_CARD_BORDER,
        tickformat=".2f",
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor=COLORE_CARD,
        bordercolor=COLORE_CARD_BORDER,
        borderwidth=1,
    ),
    hovermode="x unified",
)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ============================================================
# BUY ZONES
# ============================================================
st.markdown('<div class="section-title">🎯 Buy Zones (σ-based)</div>', unsafe_allow_html=True)

bz_col1, bz_col2, bz_col3 = st.columns(3)
for col, (key_p, key_pct, label, color) in zip(
    [bz_col1, bz_col2, bz_col3],
    [
        ("p1sigma", "pct1", "-1σ ENTRY", COLORE_ACCENT),
        ("p2sigma", "pct2", "-2σ ADD", "#F59E0B"),
        ("p3sigma", "pct3", "-3σ AVERAGE", COLORE_RISCHIO),
    ]
):
    with col:
        triggered = prezzo_finale <= buy_zones[key_p]
        trig_label = "🟢 TRIGGERED" if triggered else "⚪ pending"
        st.markdown(f"""
        <div class="metric-card" style="border-left:3px solid {color};">
            <div class="metric-label" style="color:{color};">{label}</div>
            <div class="metric-value" style="font-size:1.1rem;">€{buy_zones[key_p]:.3f}</div>
            <div class="metric-delta neutral">{buy_zones[key_pct]:+.1f}% · {trig_label}</div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# LEGENDA INGEGNERIA DEL RISCHIO
# ============================================================
st.markdown('<div class="section-title">🛠️ Ingegneria del Rischio</div>', unsafe_allow_html=True)

with st.expander("💰 Money Management — Perché tranche crescenti?"):
    st.markdown(f"""
**La regola del 20/30/50 (e 10/20/30/40)** non è arbitraria. Si fonda su tre principi:

1. **Asimmetria della convinzione**: al primo ingresso *non sai* se hai ragione. La tranche iniziale piccola (10–20%) è una "sonda".
2. **Pull-down matematico del PMC**: la tranche più grande va investita al prezzo più basso. Se compri 50% del capitale al minimo, sposti il PMC molto più di quanto farebbe l'equal-weight.
3. **Munizioni residue**: lasciare il 40–50% del capitale per l'ultima tranche significa avere potenza di fuoco proprio quando il mercato è in panic mode (quando gli altri vendono).

**Esempio numerico** ({budget:,}€):
- Equal-weight su 4 tranche → PMC = media semplice dei 4 prezzi
- Pesato 10/20/30/40 → l'ultimo prezzo pesa **4 volte** il primo

Se il prezzo crolla, il PMC scende molto più velocemente.
""".replace(",", "."))

with st.expander("⚖️ Incidenza Commissionale — Il filtro 0.20%"):
    st.markdown(f"""
Directa applica una **commissione fissa di 1.50€** indipendente dal controvalore.

**Il problema**: 1.50€ su 500€ = **0.30%** (alto). 1.50€ su 1.500€ = **0.10%** (accettabile).

**La regola d'oro**: la commissione *one-way* non deve superare lo **0.20%** del controvalore.
Questo significa che ogni tranche deve essere ≥ **750€**.

Considerando che andata + ritorno costano 3€, su una tranche da 750€ paghi lo 0.40% di "frizione" — già al limite di quanto una mean-reversion può rendere in pochi giorni.

**Cosa fa questa app**: se imposti tranche troppo piccole, le marca come 🔴 *bloccate* e te lo dice. Non te lo fa scegliere per non regalare soldi al broker.
""")

with st.expander("📐 Legge del Recupero Percentuale — La matematica delle perdite"):
    st.markdown("""
Questa è la trappola psicologica più sottovalutata del trading:

| Perdita | Recupero necessario |
|---------|---------------------|
| −10%    | +11.1%              |
| −20%    | +25.0%              |
| −30%    | +42.9%              |
| −50%    | **+100%**           |
| −70%    | +233%               |

Formula: `recupero = perdita / (1 - perdita)`

**Implicazione operativa**:
- Sotto il **−10%** dal PMC, mediare ha senso solo se la tesi è ancora valida.
- Sotto il **−25%**, devi chiederti se non sei in un "value trap".
- Sotto il **−40%**, lo *stop loss* è quasi sempre meglio del *double down*.

**Lo Smart DCA funziona** finché i crolli rimangono entro range statistici (entro ±2–3σ). Oltre, il titolo probabilmente sta scontando informazioni *fondamentali* nuove (delisting, fraud, FDA rejection per i biotech) e nessuna media risolve.
""")

with st.expander("📊 Deviazioni Standard — Come leggere le Buy Zones"):
    st.markdown(f"""
Le **Buy Zones** sono calcolate sulla volatilità giornaliera (σ) che hai impostato in sidebar ({sigma_giornaliera}%).

- **−1σ**: copre il 68% dei movimenti normali. È una correzione *fisiologica*. Entrata standard.
- **−2σ**: copre il 95%. Statisticamente "oversold". Buon punto di add.
- **−3σ**: copre il 99.7%. È un evento raro. O è panic selling (occasione), o c'è una *news* che cambia tutto (fuggi).

**Tarare σ correttamente è essenziale**:
- Blue chip (Enel, Generali): σ ≈ 1.0–1.5%
- Tech mid-cap NASDAQ: σ ≈ 2.5–3.5%
- **Biotech small-cap pre-catalyst**: σ ≈ 4–7% (il tuo caso)
- Biotech in PDUFA week: σ può schizzare al 15–20%

Sottostimare σ ti fa entrare troppo presto. Sovrastimarla ti fa aspettare prezzi che non arrivano mai.
""")

st.markdown("---")
st.caption(
    "⚠️ **Disclaimer**: nessuna simulazione garantisce il profitto. Lo Smart DCA è una "
    "tecnica di gestione del rischio, non una strategia di previsione. Il successo dipende "
    "dalla disciplina di eseguire l'ultima tranche quando *tutto è rosso* — è lì che la matematica lavora per te."
)
