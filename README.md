# Median Strategy Directa 📊

Simulatore di **Dollar Cost Averaging** ottimizzato per il broker **Directa**.

## Struttura: due pagine separate

### 📋 Piano (pagina principale)
Decidi cosa comprare *prima* di eseguire gli ordini. L'app genera una **checklist operativa**:
- Quante azioni comprare
- A che prezzo (target T1 + scenari di crollo)
- Quanto spendi (commissioni Directa incluse)
- PMC stimato e rimbalzo necessario per il profitto

### 📊 Monitoraggio
Dopo aver eseguito gli ordini su Directa, registri:
- Stato di ogni tranche (eseguita / pending / saltata)
- Prezzo e quantità realmente acquistate
- Prezzo di mercato attuale

L'app calcola:
- PMC reale (con commissioni effettive ricalcolate)
- Valore attuale del portafoglio
- P/L in € e %
- Rimbalzo necessario per il break-even

I monitoraggi si salvano in archivio per essere riaperti e aggiornati nel tempo.

## Caratteristiche tecniche

- **Capitale libero**: da 500€ a 1.000.000€ (input numerico)
- **Numero tranche automatico**: 2/3/4/5 secondo l'efficienza commissionale Directa
- **Commissione Directa**: 1,90€ ogni 1000€ (min 1,50€) calcolata automaticamente
- **Filtro efficienza** 0,20%: blocca tranche commissionalmente inefficienti
- **Export PNG** del piano per condivisione/screenshot
- **Archivio persistente** in session_state (export/import JSON disponibile)
- **UI mobile-first** ad alta luminosità

## Stack

- Python 3.11+
- Streamlit (multi-page con cartella `pages/`)
- Plotly + Matplotlib (export PNG)
- NumPy

## Deploy su Streamlit Cloud

1. Forka il repo su GitHub
2. Vai su [share.streamlit.io](https://share.streamlit.io), connetti il repo
3. Main file: `app.py`. La pagina Monitoraggio viene caricata automaticamente.

## Esecuzione locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Struttura file

```
.
├── app.py                          # Pagina Piano
├── common.py                       # Modulo condiviso (costanti, CSS, funzioni)
├── pages/
│   └── 2_📊_Monitoraggio.py        # Pagina Monitoraggio
├── requirements.txt
├── .streamlit/
│   └── config.toml
└── README.md
```

## Disclaimer

Nessuna simulazione garantisce il profitto. Lo Smart DCA è una tecnica di gestione del rischio, non di previsione.
