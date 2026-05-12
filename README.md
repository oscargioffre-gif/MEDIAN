# Smart DCA Directa 📊

Simulatore di **Dollar Cost Averaging ottimizzato** per il broker Directa (commissione fissa 1.50€), con stress test su crolli consecutivi e visualizzazione del PMC contro le Buy Zones statistiche.

## Filosofia ingegneristica

- **Filtro efficienza commissionale**: nessuna tranche viene ammessa se 1.50€ supera lo 0.20% del controvalore (tranche minima ≈ 750€).
- **Pesi crescenti**: 20/30/50 (budget 5k) o 10/20/30/40 (budget 10k). La tranche più grande va al prezzo più basso → pull-down massimo del PMC.
- **Buy Zones σ-based**: livelli −1σ / −2σ / −3σ dal prezzo iniziale (Bollinger-style).
- **Stress test interattivo**: sliders in sidebar per simulare crolli giornalieri consecutivi.

## Stack

- **Python 3.11+**
- **Streamlit** per UI
- **Plotly** per grafici interattivi
- **NumPy** per calcoli

## Deploy su Streamlit Cloud

1. Forka questo repo su GitHub.
2. Vai su [share.streamlit.io](https://share.streamlit.io), connetti il repo.
3. Main file: `app.py`. Done.

## Esecuzione locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Struttura

```
.
├── app.py                   # logica + UI
├── requirements.txt
├── .streamlit/
│   └── config.toml          # tema dark
└── README.md
```

## Logica dei pesi (perché 10/20/30/40?)

Scelta basata su:
- **Kelly criterion frazionario** applicato a strategie di mean-reversion (Faber, *Cambria*).
- **Asimmetria della convinzione**: bassa esposizione iniziale, alta esposizione su prezzi statisticamente "oversold".
- **Munizioni residue**: 40% di capitale per l'ultima tranche = potenza di fuoco quando il mercato è in panic mode.

## Disclaimer

Nessuna simulazione garantisce il profitto. Lo Smart DCA è una tecnica di gestione del rischio, non di previsione. L'app rifiuta di calcolare tranche commissionalmente inefficienti — non aggira la matematica del mercato.

---
*Built for retail traders su orizzonte 1–4 settimane, ottimizzato per biotech small/mid-cap NASDAQ e FTSE MIB.*
