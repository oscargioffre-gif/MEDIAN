"""
Median Strategy Directa — PAGINA MONITORAGGIO
Registra gli acquisti realmente eseguiti su Directa e calcola PMC reale + P/L.
"""
import streamlit as st
from datetime import datetime, date
import json
from common import (
    COL_BG, COL_CARD, COL_CARD_HI, COL_BORDER,
    COL_PROFIT, COL_RISK, COL_ACCENT, COL_WARN,
    COL_TEXT, COL_TEXT_DIM, COL_TEXT_LABEL,
    commissione_directa, calcola_pmc,
    apply_css, init_archive,
)

st.set_page_config(
    page_title="Monitoraggio · Median Strategy",
    page_icon="📊",
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
    st.markdown("**📊 Sei nella pagina MONITORAGGIO**\n\nUsa questa pagina dopo aver eseguito acquisti su Directa, per registrarli e vedere PMC e P/L reali.")
    st.markdown(
        "Per creare un nuovo piano di acquisto, vai alla pagina **📋 Piano** dal menu in alto a sinistra."
    )


# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="main-title">📊 Monitoraggio<br>Investimento</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="main-sub">Registra cosa hai comprato · Calcola PMC reale · Vedi P/L</div>',
    unsafe_allow_html=True,
)


# ============================================================
# STATE — Inizializzo monitoraggio corrente
# ============================================================
if "monitoraggio_corrente" not in st.session_state:
    st.session_state.monitoraggio_corrente = None


# ============================================================
# STEP 1 — Scegli da dove iniziare
# ============================================================
st.markdown('<div class="section-title">1️⃣ Scegli il monitoraggio</div>', unsafe_allow_html=True)

# Tre opzioni: nuovo da piano, nuovo manuale, oppure carica esistente
opzioni = ["✨ Nuovo da zero"]
if st.session_state.archivio_piani:
    opzioni.insert(0, "📋 Parti da un piano salvato")
if st.session_state.archivio_monitoraggi:
    opzioni.append("📂 Carica un monitoraggio esistente")

modo = st.radio(
    "Cosa vuoi fare?",
    options=opzioni,
    horizontal=False,
    label_visibility="collapsed",
)

# Logica di caricamento monitoraggio corrente
if modo == "📋 Parti da un piano salvato":
    piani_disponibili = st.session_state.archivio_piani
    nomi_piani = [f"{p['ticker']} · €{p['budget']:,} · {p['data_creazione']}".replace(",", ".")
                  for p in piani_disponibili]
    idx_sel = st.selectbox(
        "Seleziona il piano",
        range(len(piani_disponibili)),
        format_func=lambda i: nomi_piani[i],
    )
    piano_sel = piani_disponibili[idx_sel]

    if st.button("✓ Inizia monitoraggio di questo piano", use_container_width=True):
        # Costruisco un monitoraggio basato sul piano
        st.session_state.monitoraggio_corrente = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "ticker": piano_sel["ticker"],
            "budget": piano_sel["budget"],
            "n_tranche_pianificate": piano_sel["n_tranche"],
            "piano_di_origine": piano_sel["id"],
            "data_inizio": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "tranche_eseguite": [
                {
                    "num": op["num"],
                    "stato": "pending",  # pending / eseguita / saltata
                    "data": None,
                    "prezzo": None,
                    "n_azioni": None,
                    "prezzo_target_piano": op["prezzo_target"],
                    "n_azioni_target_piano": op["n_azioni"],
                }
                for op in piano_sel["operazioni"] if op["valido"]
            ],
            "prezzo_mercato_attuale": piano_sel["prezzo_iniziale"],
        }
        st.success("✓ Monitoraggio iniziato. Compila sotto le tranche eseguite.")
        st.rerun()

elif modo == "✨ Nuovo da zero":
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        ticker_nuovo = st.text_input("Ticker", value="", placeholder="es. SRPT")
    with col_n2:
        n_tr_nuovo = st.number_input("Numero tranche pianificate", min_value=1, max_value=5, value=3)

    if st.button("✓ Crea monitoraggio vuoto", use_container_width=True) and ticker_nuovo.strip():
        st.session_state.monitoraggio_corrente = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "ticker": ticker_nuovo.strip().upper(),
            "budget": 0,
            "n_tranche_pianificate": int(n_tr_nuovo),
            "piano_di_origine": None,
            "data_inizio": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "tranche_eseguite": [
                {"num": i+1, "stato": "pending", "data": None, "prezzo": None, "n_azioni": None,
                 "prezzo_target_piano": None, "n_azioni_target_piano": None}
                for i in range(int(n_tr_nuovo))
            ],
            "prezzo_mercato_attuale": 0.0,
        }
        st.success("✓ Monitoraggio creato. Compila sotto le tranche eseguite.")
        st.rerun()

elif modo == "📂 Carica un monitoraggio esistente":
    monit_disponibili = st.session_state.archivio_monitoraggi
    nomi_monit = [f"{m['ticker']} · {m['data_inizio']}" for m in monit_disponibili]
    idx_sel = st.selectbox(
        "Seleziona il monitoraggio",
        range(len(monit_disponibili)),
        format_func=lambda i: nomi_monit[i],
    )
    if st.button("✓ Carica", use_container_width=True):
        st.session_state.monitoraggio_corrente = dict(monit_disponibili[idx_sel])
        st.success("✓ Caricato.")
        st.rerun()


# ============================================================
# STEP 2 — Compila tranche eseguite
# ============================================================
m = st.session_state.monitoraggio_corrente

if m is not None:
    st.markdown('<div class="section-title">2️⃣ Registra cosa hai comprato</div>', unsafe_allow_html=True)
    st.caption(
        f"Monitoraggio per **{m['ticker']}** — per ogni tranche, dimmi se l'hai eseguita, "
        "saltata, o non ancora fatta."
    )

    for idx, tr in enumerate(m["tranche_eseguite"]):
        with st.expander(
            f"**TRANCHE {tr['num']}** — "
            f"{'✅ Eseguita' if tr['stato'] == 'eseguita' else ('⏸️ Pending' if tr['stato'] == 'pending' else '❌ Saltata')}",
            expanded=(tr['stato'] == 'pending'),
        ):
            # Riferimento al piano se presente
            if tr.get("prezzo_target_piano") is not None:
                st.caption(
                    f"📋 Piano originale: comprare ~{tr['n_azioni_target_piano']} azioni a "
                    f"~€{tr['prezzo_target_piano']:.3f}"
                )

            stato_nuovo = st.radio(
                "Stato",
                options=["pending", "eseguita", "saltata"],
                format_func=lambda x: {
                    "pending": "⏸️ Non ancora eseguita",
                    "eseguita": "✅ Eseguita",
                    "saltata": "❌ Saltata (prezzo non raggiunto / cambio idea)",
                }[x],
                index=["pending", "eseguita", "saltata"].index(tr['stato']),
                key=f"stato_{idx}",
                horizontal=False,
            )
            tr['stato'] = stato_nuovo

            if stato_nuovo == "eseguita":
                col_a, col_b, col_c = st.columns([1, 1, 1])
                with col_a:
                    data_default = date.today() if tr['data'] is None else \
                                   datetime.strptime(tr['data'], "%d/%m/%Y").date()
                    data_acq = st.date_input(
                        "Data", value=data_default, key=f"data_{idx}",
                        format="DD/MM/YYYY",
                    )
                    tr['data'] = data_acq.strftime("%d/%m/%Y")
                with col_b:
                    prezzo_default = tr['prezzo'] if tr['prezzo'] is not None else \
                                     (tr.get('prezzo_target_piano') or 0.01)
                    prezzo_reale = st.number_input(
                        "Prezzo (€)", min_value=0.01, max_value=10000.0,
                        value=float(prezzo_default), step=0.001, format="%.3f",
                        key=f"prezzo_{idx}",
                        help="Prezzo medio reale di eseguito (senza commissione)",
                    )
                    tr['prezzo'] = prezzo_reale
                with col_c:
                    az_default = tr['n_azioni'] if tr['n_azioni'] is not None else \
                                 (tr.get('n_azioni_target_piano') or 0)
                    n_az_reale = st.number_input(
                        "Azioni", min_value=0, max_value=1_000_000,
                        value=int(az_default), step=1,
                        key=f"azioni_{idx}",
                    )
                    tr['n_azioni'] = int(n_az_reale)

                # Mostra calcolo commissione
                if tr['prezzo'] and tr['n_azioni']:
                    cv = tr['prezzo'] * tr['n_azioni']
                    co = commissione_directa(cv)
                    st.caption(
                        f"💸 Controvalore €{cv:,.2f} → commissione Directa €{co:.2f} → "
                        f"**costo totale €{cv+co:,.2f}**".replace(",", ".")
                    )

    # ========================================================
    # STEP 3 — Prezzo mercato attuale
    # ========================================================
    st.markdown('<div class="section-title">3️⃣ Prezzo di mercato adesso</div>', unsafe_allow_html=True)
    st.caption("Inserisci il prezzo a cui il titolo viene quotato in questo momento. Serve per calcolare il P/L attuale.")

    prezzo_corrente = st.number_input(
        f"Prezzo attuale di {m['ticker']} (€)",
        min_value=0.01, max_value=10000.0,
        value=max(0.01, float(m.get('prezzo_mercato_attuale', 0.01))),
        step=0.001, format="%.3f",
    )
    m['prezzo_mercato_attuale'] = prezzo_corrente

    # ========================================================
    # CALCOLO PMC REALE + P/L
    # ========================================================
    acquisti_eseguiti = [
        {
            "prezzo": tr['prezzo'],
            "n_azioni": tr['n_azioni'],
            "commissione": commissione_directa(tr['prezzo'] * tr['n_azioni']),
        }
        for tr in m['tranche_eseguite']
        if tr['stato'] == 'eseguita' and tr['prezzo'] and tr['n_azioni']
    ]

    if acquisti_eseguiti:
        pmc_reale = calcola_pmc(acquisti_eseguiti)
        valore_attuale = pmc_reale['azioni_totali'] * prezzo_corrente
        pl_eur = valore_attuale - pmc_reale['costo_totale']
        pl_pct = (pl_eur / pmc_reale['costo_totale'] * 100) if pmc_reale['costo_totale'] > 0 else 0
        break_even_pct = ((pmc_reale['pmc'] / prezzo_corrente - 1) * 100) if prezzo_corrente > 0 else 0

        st.markdown('<div class="section-title">📊 Situazione attuale</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">AZIONI POSSEDUTE</div>
                <div class="metric-value accent">{pmc_reale['azioni_totali']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">PMC REALE</div>
                <div class="metric-value">€{pmc_reale['pmc']:.3f}</div>
                <div class="metric-delta neutral">vs prezzo €{prezzo_corrente:.3f}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">SPESO FINORA</div>
                <div class="metric-value">€{pmc_reale['costo_totale']:,.2f}</div>
                <div class="metric-delta neutral">Comm €{pmc_reale['commissioni_totali']:.2f}</div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)

            pl_class = 'profit' if pl_eur >= 0 else 'risk'
            pl_sign = '+' if pl_eur >= 0 else ''
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">P/L ATTUALE</div>
                <div class="metric-value {pl_class}">{pl_sign}€{pl_eur:,.2f}</div>
                <div class="metric-delta {pl_class}">{pl_pct:+.2f}%</div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)

        # Card valore attuale e break-even
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">VALORE ATTUALE</div>
                <div class="metric-value">€{valore_attuale:,.2f}</div>
                <div class="metric-delta neutral">{pmc_reale['azioni_totali']} × €{prezzo_corrente:.3f}</div>
            </div>
            """.replace(",", "."), unsafe_allow_html=True)
        with col4:
            if break_even_pct > 0:
                be_class = 'profit' if break_even_pct < 10 else ('warn' if break_even_pct < 20 else 'risk')
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">RIMBALZO X PROFITTO</div>
                    <div class="metric-value {be_class}">+{break_even_pct:.2f}%</div>
                    <div class="metric-delta neutral">da €{prezzo_corrente:.3f}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">SEI IN PROFITTO ✓</div>
                    <div class="metric-value profit">+{-break_even_pct:.2f}%</div>
                    <div class="metric-delta profit">sopra PMC</div>
                </div>
                """, unsafe_allow_html=True)

        # Spiegazione semplice
        with st.expander("❓ Come si leggono questi numeri"):
            pl_word = "guadagno" if pl_eur >= 0 else "perdita"
            st.markdown(f"""
**Hai comprato {pmc_reale['azioni_totali']} azioni di {m['ticker']}** spendendo
in totale **€{pmc_reale['costo_totale']:,.2f}** (commissioni Directa incluse: €{pmc_reale['commissioni_totali']:.2f}).

Il tuo **prezzo medio di acquisto (PMC)** è di **€{pmc_reale['pmc']:.3f}** per azione.

Oggi il titolo vale **€{prezzo_corrente:.3f}** sul mercato. Le tue azioni quindi valgono in totale:
- {pmc_reale['azioni_totali']} azioni × €{prezzo_corrente:.3f} = **€{valore_attuale:,.2f}**

Differenza vs quello che hai speso: **{pl_sign}€{abs(pl_eur):,.2f}** ({pl_pct:+.2f}%) → una virtuale **{pl_word}**.

{"✅ **Sei già in profitto.** Il prezzo di mercato è sopra il tuo PMC." if pl_eur >= 0 else f"📉 Per tornare in pari il titolo deve risalire del **{break_even_pct:.2f}%** (da €{prezzo_corrente:.3f} a €{pmc_reale['pmc']:.3f})."}
""".replace(",", "."))

    else:
        st.info("⏸️ Nessuna tranche eseguita ancora. Imposta lo stato di almeno una tranche su \"Eseguita\" e compila i dati.")


    # ========================================================
    # STEP 4 — Salva
    # ========================================================
    st.markdown('<div class="section-title">💾 Salva monitoraggio</div>', unsafe_allow_html=True)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("💾 Salva in archivio", use_container_width=True):
            # Verifica se già esiste (stesso id), in caso aggiorna
            esistente = next((i for i, x in enumerate(st.session_state.archivio_monitoraggi)
                              if x['id'] == m['id']), None)
            if esistente is not None:
                st.session_state.archivio_monitoraggi[esistente] = dict(m)
                st.success("✓ Monitoraggio aggiornato in archivio")
            else:
                st.session_state.archivio_monitoraggi.append(dict(m))
                st.success("✓ Monitoraggio salvato in archivio")

    with col_s2:
        if st.button("🆕 Nuovo monitoraggio", use_container_width=True):
            st.session_state.monitoraggio_corrente = None
            st.rerun()


# ============================================================
# ARCHIVIO MONITORAGGI
# ============================================================
if st.session_state.archivio_monitoraggi:
    st.markdown('<div class="section-title">🗄️ Archivio monitoraggi</div>', unsafe_allow_html=True)

    for idx in range(len(st.session_state.archivio_monitoraggi) - 1, -1, -1):
        mon = st.session_state.archivio_monitoraggi[idx]

        # Calcolo veloce stato
        acquisti_es = [
            {"prezzo": tr['prezzo'], "n_azioni": tr['n_azioni'],
             "commissione": commissione_directa(tr['prezzo'] * tr['n_azioni'])}
            for tr in mon['tranche_eseguite']
            if tr['stato'] == 'eseguita' and tr['prezzo'] and tr['n_azioni']
        ]
        n_eseguite = len(acquisti_es)
        n_pianificate = len(mon['tranche_eseguite'])

        if acquisti_es and mon.get('prezzo_mercato_attuale', 0) > 0:
            pmc_arc = calcola_pmc(acquisti_es)
            val = pmc_arc['azioni_totali'] * mon['prezzo_mercato_attuale']
            pl = val - pmc_arc['costo_totale']
            pl_pct_arc = (pl / pmc_arc['costo_totale'] * 100) if pmc_arc['costo_totale'] > 0 else 0
            pl_color = COL_PROFIT if pl >= 0 else COL_RISK
            pl_sign = '+' if pl >= 0 else ''
            riga_pl = (
                f"<span style='color:{COL_TEXT_LABEL};'>PMC </span>"
                f"<strong style='color:{COL_ACCENT};'>€{pmc_arc['pmc']:.3f}</strong> &nbsp;·&nbsp; "
                f"<span style='color:{COL_TEXT_LABEL};'>P/L </span>"
                f"<strong style='color:{pl_color};'>{pl_sign}€{pl:,.2f} ({pl_pct_arc:+.2f}%)</strong>"
            ).replace(",", ".")
        else:
            riga_pl = f"<span style='color:{COL_TEXT_DIM};'>Nessuna tranche eseguita</span>"

        col_a, col_b, col_c = st.columns([8, 1, 1])
        with col_a:
            st.markdown(f"""
            <div class="archive-item">
                <div style="font-weight:800; color:{COL_TEXT}; font-size:0.95rem;">
                    📊 {mon['ticker']} · {n_eseguite}/{n_pianificate} tranche
                </div>
                <div style="color:{COL_TEXT_DIM}; font-size:0.78rem; margin-top:0.3rem;">
                    Iniziato il {mon['data_inizio']}
                </div>
                <div style="margin-top:0.5rem;">{riga_pl}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_b:
            if st.button("📂", key=f"open_mon_{mon['id']}_{idx}", help="Apri"):
                st.session_state.monitoraggio_corrente = dict(mon)
                st.rerun()
        with col_c:
            if st.button("🗑️", key=f"del_mon_{mon['id']}_{idx}", help="Elimina"):
                st.session_state.archivio_monitoraggi.pop(idx)
                st.rerun()

    # Export JSON archivio
    archivio_json = json.dumps(st.session_state.archivio_monitoraggi, indent=2, ensure_ascii=False, default=str)
    st.download_button(
        label="📥 Esporta archivio (JSON)",
        data=archivio_json,
        file_name=f"median_strategy_monitoraggi_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )


# ============================================================
# GUIDA
# ============================================================
st.markdown('<div class="section-title">📖 Come si usa questa pagina</div>', unsafe_allow_html=True)

with st.expander("🚀 Guida rapida"):
    st.markdown("""
**Step 1** — Scegli un piano salvato dalla pagina **Piano**, oppure creane uno nuovo da zero.

**Step 2** — Per ogni tranche pianificata, imposta lo stato:
- ⏸️ **Non ancora eseguita** — Aspetti che il prezzo arrivi al livello giusto
- ✅ **Eseguita** — Compili: data, prezzo reale di acquisto, numero di azioni effettive
- ❌ **Saltata** — Il prezzo non è mai sceso fino a lì, oppure hai cambiato idea

**Step 3** — Inserisci il prezzo di mercato corrente del titolo. L'app calcola in tempo reale:
- 💰 PMC reale (prezzo medio a cui hai comprato, commissioni incluse)
- 💵 Spesa totale
- 📊 Valore attuale del tuo investimento
- 📈 P/L in euro e in %
- 🎯 Quanto deve risalire il titolo per andare in profitto

**Step 4** — Salva. Quando vuoi controllare di nuovo, riapri il monitoraggio dall'archivio
e aggiorna solo il prezzo di mercato (oppure aggiungi nuove tranche se nel frattempo ne hai eseguite altre).
""")

with st.expander("ℹ️ Come vengono calcolate le commissioni"):
    st.markdown("""
Per ogni tranche eseguita, la commissione Directa è ricalcolata sul **controvalore reale**:

- Se compri **150 azioni a €12,50** → controvalore €1.875,00 → commissione €3,56
- Se compri **30 azioni a €25,00** → controvalore €750,00 → commissione €1,50 (minimo)

Tu inserisci solo *prezzo* e *quantità*. La commissione è automatica.
""")
