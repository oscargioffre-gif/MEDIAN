"""
Median Strategy Directa — PAGINA PIANO
Mostra la checklist operativa pre-trade: cosa comprare, quando, a quale prezzo.
"""
import streamlit as st
from datetime import datetime
from common import (
    COMMISSIONE_PROPORZIONALE, COMMISSIONE_MIN, SOGLIA_EFFICIENZA,
    COL_BG, COL_CARD, COL_CARD_HI, COL_BORDER,
    COL_PROFIT, COL_RISK, COL_ACCENT, COL_WARN,
    COL_TEXT, COL_TEXT_DIM, COL_TEXT_LABEL,
    commissione_directa, seleziona_n_tranche_ottimale, calcola_pmc,
    apply_css, init_archive,
)

st.set_page_config(
    page_title="Piano · Median Strategy",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)
apply_css()
init_archive()


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### 📊 MEDIAN STRATEGY")
    st.caption("Simulatore DCA per Directa")
    st.markdown("---")
    st.markdown("**📋 Sei nella pagina PIANO**\n\nUsa questa pagina per *decidere cosa fare prima di acquistare*.")
    st.markdown(
        "Per registrare invece gli acquisti già eseguiti e monitorare l'investimento, "
        "vai alla pagina **📊 Monitoraggio** dal menu in alto a sinistra."
    )
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
st.markdown('<div class="main-title">📋 Piano di<br>Acquisto</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="main-sub">Cosa comprare · A che prezzo · Quanto investire</div>',
    unsafe_allow_html=True,
)


# ============================================================
# PARAMETRI
# ============================================================
st.markdown('<div class="section-title">⚙️ Imposta lo scenario</div>', unsafe_allow_html=True)

budget = st.number_input(
    "💰 Capitale disponibile (€) — senza leva",
    min_value=500,
    max_value=1_000_000,
    value=10000,
    step=500,
    format="%d",
    help="Capitale che vuoi investire complessivamente. L'app decide il numero ottimale di tranche.",
)

n_tranche_choice, pesi_auto = seleziona_n_tranche_ottimale(budget)

# Box piano automatico
pesi_str_display = " / ".join(f"{int(p*100)}%" for p in pesi_auto)
cap_min_tranche = budget * min(pesi_auto)
st.markdown(f"""
<div style="background: linear-gradient(135deg, {COL_CARD} 0%, {COL_CARD_HI} 100%);
            border-left: 4px solid {COL_PROFIT};
            border-radius: 10px; padding: 0.9rem 1.1rem; margin: 0.5rem 0 1rem 0;
            font-family: 'JetBrains Mono', monospace;">
    <div style="color: {COL_TEXT_LABEL}; font-size: 0.72rem; font-weight: 700;
                letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 0.3rem;">
        🤖 Piano automatico
    </div>
    <div style="color: {COL_TEXT}; font-size: 1rem; font-weight: 700;">
        {n_tranche_choice} tranche · pesi {pesi_str_display}
    </div>
    <div style="color: {COL_TEXT_DIM}; font-size: 0.78rem; margin-top: 0.4rem;">
        Tranche minima: <strong style="color:{COL_PROFIT};">€{cap_min_tranche:,.0f}</strong>
    </div>
</div>
""".replace(",", "."), unsafe_allow_html=True)

col_p1, col_p2 = st.columns(2)
with col_p1:
    ticker_label = st.text_input("🏷️ Ticker", value="", placeholder="es. SRPT, ENI.MI")
with col_p2:
    prezzo_iniziale = st.number_input(
        "💲 Prezzo target T1 (€)",
        min_value=0.01, max_value=10000.0, value=25.00, step=0.10, format="%.2f",
        help="Prezzo puro di mercato senza commissioni. Le commissioni le calcola l'app.",
    )

# Stress test
st.markdown("")
with st.expander("📉 **Scenario di crollo** — Imposta i ribassi attesi", expanded=True):
    st.caption("A che prezzo vuoi comprare le tranche successive? Imposta i ribassi giornalieri attesi.")
    default_crolli = [-3.0, -5.0, -10.0, -7.0, -4.0]
    crolli = []
    for i in range(n_tranche_choice - 1):
        cr = st.slider(
            f"Giorno {i+1} → Tranche {i+2}",
            min_value=-20.0, max_value=0.0,
            value=default_crolli[i] if i < len(default_crolli) else -5.0,
            step=0.5, format="%.1f%%",
            key=f"crollo_{i}",
        )
        crolli.append(cr)


# ============================================================
# CALCOLO TRANCHE — operative
# ============================================================
ticker_clean = ticker_label.strip().upper() if ticker_label.strip() else "TITOLO"

# Costruisco la lista delle operazioni pianificate
operazioni = []
prezzo_corrente = prezzo_iniziale

for i, peso in enumerate(pesi_auto):
    if i == 0:
        prezzo_target = prezzo_iniziale
        prezzo_label = "OGGI"
    else:
        crollo = crolli[i-1]
        prezzo_corrente = prezzo_corrente * (1 + crollo / 100)
        prezzo_target = prezzo_corrente
        prezzo_label = f"SE SCENDE A {prezzo_target:.3f}€ ({crollo:.1f}%)"

    capitale_lordo = budget * peso
    comm = commissione_directa(capitale_lordo)
    incidenza = comm / capitale_lordo if capitale_lordo > 0 else 1
    valido = incidenza <= SOGLIA_EFFICIENZA

    if valido:
        n_azioni = int((capitale_lordo - comm) / prezzo_target)
        controvalore = n_azioni * prezzo_target
        spesa_totale = controvalore + comm
    else:
        n_azioni = 0
        controvalore = 0
        spesa_totale = 0

    operazioni.append({
        "num": i + 1,
        "peso": peso,
        "label_evento": prezzo_label,
        "prezzo_target": prezzo_target,
        "capitale_lordo": capitale_lordo,
        "n_azioni": n_azioni,
        "controvalore": controvalore,
        "commissione": comm,
        "spesa_totale": spesa_totale,
        "incidenza_pct": incidenza * 100,
        "valido": valido,
    })


# ============================================================
# CHECKLIST OPERATIVA
# ============================================================
st.markdown('<div class="section-title">🎯 Cosa devi fare</div>', unsafe_allow_html=True)
st.caption(f"Piano per **{ticker_clean}** — segui questi passi nell'ordine. Spesa totale e commissioni già conteggiate.")

for op in operazioni:
    css_class = f"t{op['num']}" if op['valido'] else "bloccata"

    if op['valido']:
        st.markdown(f"""
        <div class="checklist-card {css_class}">
            <div class="checklist-head">
                ▢ TRANCHE {op['num']} — {op['label_evento']}
            </div>
            <div class="checklist-action">
                Compra <span class="big-number">{op['n_azioni']}</span> azioni
                a <span class="big-number">€{op['prezzo_target']:.3f}</span>
            </div>
            <div class="checklist-detail">
                💸 Spendi €{op['controvalore']:,.2f} + €{op['commissione']:.2f} commissione
                <br>
                💰 <strong style="color:{COL_TEXT};">Totale: €{op['spesa_totale']:,.2f}</strong>
                &nbsp;·&nbsp; Peso {int(op['peso']*100)}%
                &nbsp;·&nbsp; Incidenza {op['incidenza_pct']:.3f}%
            </div>
        </div>
        """.replace(",", "."), unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="checklist-card bloccata">
            <div class="checklist-head" style="color:{COL_RISK};">
                ✗ TRANCHE {op['num']} — BLOCCATA
            </div>
            <div class="checklist-detail">
                Peso {int(op['peso']*100)}% = €{op['capitale_lordo']:,.0f} → commissione €{op['commissione']:.2f}
                (incidenza {op['incidenza_pct']:.3f}% > soglia 0.20%).
                <br>
                <strong style="color:{COL_WARN};">⚠ Tranche troppo piccola per essere commissionalmente efficiente.</strong>
            </div>
        </div>
        """.replace(",", "."), unsafe_allow_html=True)


# ============================================================
# SE TUTTO VA COME PREVISTO
# ============================================================
operazioni_valide = [op for op in operazioni if op['valido']]

if operazioni_valide:
    # Calcolo PMC del piano completo
    acquisti_simulati = [
        {"prezzo": op['prezzo_target'], "n_azioni": op['n_azioni'],
         "commissione": op['commissione']}
        for op in operazioni_valide
    ]
    pmc_piano = calcola_pmc(acquisti_simulati)
    prezzo_finale = operazioni_valide[-1]['prezzo_target']
    break_even_pct = ((pmc_piano['pmc'] / prezzo_finale) - 1) * 100 if prezzo_finale > 0 else 0
    investito_tot = pmc_piano['costo_totale']
    n_az_tot = pmc_piano['azioni_totali']

    st.markdown('<div class="section-title">📌 Se tutto va come previsto</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">AZIONI TOTALI</div>
            <div class="metric-value accent">{n_az_tot}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">PMC FINALE</div>
            <div class="metric-value">€{pmc_piano['pmc']:.3f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">SPESA TOTALE</div>
            <div class="metric-value">€{investito_tot:,.2f}</div>
            <div class="metric-delta neutral">Comm: €{pmc_piano['commissioni_totali']:.2f}</div>
        </div>
        """.replace(",", "."), unsafe_allow_html=True)

        be_color_class = 'profit' if break_even_pct < 10 else ('warn' if break_even_pct < 20 else 'risk')
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">RIMBALZO PER PROFITTO</div>
            <div class="metric-value {be_color_class}">+{break_even_pct:.2f}%</div>
            <div class="metric-delta neutral">da €{prezzo_finale:.3f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Confronto All-in
    pmc_allin = prezzo_iniziale + (commissione_directa(budget) / int((budget - commissione_directa(budget)) / prezzo_iniziale))
    be_allin = ((pmc_allin / prezzo_finale) - 1) * 100
    risparmio = be_allin - break_even_pct

    st.markdown(f"""
    <div style="background: rgba(0, 255, 148, 0.08);
                border: 1px solid {COL_PROFIT};
                border-radius: 10px; padding: 0.9rem 1.1rem; margin: 1rem 0;
                font-family: 'Inter', sans-serif; font-size: 0.9rem;
                color: {COL_TEXT}; line-height: 1.6;">
        💡 <strong style="color:{COL_PROFIT};">Vantaggio Median Strategy</strong><br>
        Se avessi comprato tutto subito a €{prezzo_iniziale:.2f}, ti servirebbe un rimbalzo del
        <strong>+{be_allin:.2f}%</strong> per tornare in pari.<br>
        Con questo piano ti basta <strong>+{break_even_pct:.2f}%</strong> —
        <strong style="color:{COL_PROFIT};">risparmio di {risparmio:.2f} punti percentuali</strong>.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# SALVA IN ARCHIVIO
# ============================================================
st.markdown('<div class="section-title">💾 Salva il piano</div>', unsafe_allow_html=True)
st.caption("Salva questo piano in archivio. Potrai poi aprirlo nella pagina **Monitoraggio** per registrare gli acquisti reali.")

if st.button("💾 Salva piano in archivio", use_container_width=True):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_sim = f"{ticker_clean}_{budget}_{timestamp}"
    piano_data = {
        "id": timestamp,
        "nome": nome_sim,
        "ticker": ticker_clean,
        "budget": budget,
        "n_tranche": n_tranche_choice,
        "pesi": pesi_auto,
        "prezzo_iniziale": prezzo_iniziale,
        "crolli": crolli,
        "data_creazione": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "operazioni": [
            {
                "num": op['num'],
                "peso": op['peso'],
                "prezzo_target": op['prezzo_target'],
                "n_azioni": op['n_azioni'],
                "commissione": op['commissione'],
                "spesa_totale": op['spesa_totale'],
                "valido": op['valido'],
            }
            for op in operazioni
        ],
    }
    st.session_state.archivio_piani.append(piano_data)
    st.success(f"✓ Piano salvato: **{nome_sim}**. Ora vai alla pagina **Monitoraggio** per registrare gli acquisti reali.")


# ============================================================
# ARCHIVIO PIANI
# ============================================================
if st.session_state.archivio_piani:
    st.markdown('<div class="section-title">🗄️ Piani salvati</div>', unsafe_allow_html=True)
    for idx in range(len(st.session_state.archivio_piani) - 1, -1, -1):
        p = st.session_state.archivio_piani[idx]
        col_a, col_b = st.columns([10, 1])
        with col_a:
            st.markdown(f"""
            <div class="archive-item">
                <div style="font-weight:800; color:{COL_TEXT}; font-size:0.95rem;">
                    📋 {p['ticker']} · €{p['budget']:,} · {p['n_tranche']}T
                </div>
                <div style="color:{COL_TEXT_DIM}; font-size:0.78rem; margin-top:0.3rem;">
                    Creato il {p['data_creazione']} · Prezzo target T1: €{p['prezzo_iniziale']:.2f}
                </div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)
        with col_b:
            if st.button("🗑️", key=f"del_piano_{p['id']}_{idx}", help="Elimina piano"):
                st.session_state.archivio_piani.pop(idx)
                st.rerun()


# ============================================================
# LEGENDA
# ============================================================
st.markdown('<div class="section-title">📖 Cose da sapere</div>', unsafe_allow_html=True)

with st.expander("❓ Perché tranche con pesi diversi?"):
    st.markdown("""
**La strategia non è "comprare a piccoli pezzi uguali".** È comprare *poco al primo prezzo* e
*tanto agli ultimi prezzi*, perché:

1. Quando entri la prima volta **non sai** se il titolo continuerà a scendere.
   La prima tranche è una "sonda" — piccola.
2. **L'ultima tranche è la più grande** perché va eseguita al prezzo più basso.
   Comprare 40% del capitale ai minimi tira giù il PMC molto più che farlo al 25%.
3. **Risparmi munizioni** per il momento di panic: quando il prezzo è scesso davvero,
   hai ancora quasi metà capitale per "fare media".

L'app sceglie il numero di tranche (2, 3, 4 o 5) in base al tuo capitale,
massimizzando lo smoothing senza pagare commissioni inefficienti.
""")

with st.expander("⚖️ Filtro 0.20% — Perché blocca alcune tranche?"):
    st.markdown("""
Directa applica **1,90€ ogni 1000€ con minimo 1,50€**. Esempio:

| Spesa | Commissione | Incidenza |
|---|---|---|
| 500€ | 1,50€ (min) | 0,300% ❌ |
| 789€ | 1,50€ (min) | 0,190% ✓ |
| 1.000€ | 1,90€ | 0,190% ✓ |
| 2.000€ | 3,80€ | 0,190% ✓ |

Quando la commissione supera lo **0,20%** del controvalore, l'app marca la tranche come
*bloccata* perché sarebbe un regalo al broker. Aumenta il capitale o riduci il numero di tranche.
""")

with st.expander("📐 Legge del recupero — Perché conta il PMC basso"):
    st.markdown("""
| Perdita | Rimbalzo necessario |
|---|---|
| −10% | +11,1% |
| −20% | +25,0% |
| −30% | +42,9% |
| **−50%** | **+100%** |

Se il tuo PMC è alto, anche un piccolo crollo richiede un rimbalzo grosso per tornare in pari.
Lo scopo della Median Strategy è **abbassare il PMC** in modo che servano rimbalzi piccoli per andare in profitto.
""")

st.markdown("---")
st.caption(
    "⚠️ Nessuna simulazione garantisce il profitto. Questo piano funziona se il titolo "
    "scende davvero ai prezzi che hai impostato. Se scende molto di più o di meno, "
    "il PMC reale sarà diverso. Vai alla pagina **Monitoraggio** per registrare cosa è successo davvero."
)
