# JARVIS - AI Personal Assistant

JARVIS è un assistente AI personale ispirato a Iron Man, progettato per funzionare su PC Windows. Offre un'interfaccia desktop futuristica e scura, chat con modello AI in italiano, riconoscimento e risposta vocale, e funzioni per aprire applicazioni e siti web autorizzati in modo sicuro.

## ✨ Caratteristiche principali

- **Interfaccia moderna**: Tema scuro futuristico con dettagli blu e animazioni leggere (PyQt6)
- **Chat AI**: Conversazioni in italiano con modelli LLM (Anthropic Claude o OpenAI)
- **Riconoscimento vocale**: Comandi vocali in italiano con risposta vocale sintetizzata
- **Architettura modulare**: Facile da estendere con nuove funzionalità
- **Configurazione sicura**: Variabili d'ambiente per API keys (nessun segreto nel codice)
- **Funzioni iniziali**: Aprire siti web e applicazioni autorizzate su Windows
- **Gestione errori**: Log completi e segnalazione dei problemi
- **Documentazione completa**: Questo README in italiano

## 📋 Prerequisiti

- Windows 10/11
- Python 3.8+
- Connessione internet (per le API LLM)
- Microfono e altoparlanti (per funzionalità vocali)

## 🚀 Installazione

1. **Clona il repository**:
   ```bash
   git clone <repository-url>
   cd jarvis-ai
   ```

2. **Crea un ambiente virtuale** (opzionale ma consigliato):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Installa le dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura le variabili d'ambiente**:
   - Copia `.env.example` in `.env`
   - Modifica `.env` con le tue chiavi API e preferenze:
     ```env
     # Scegli il provider AI: "anthropic" (Claude) o "openai"
     JARVIS_AI_PROVIDER=anthropic

     # Chiave API Anthropic (ottienila su https://console.anthropic.com/)
     ANTHROPIC_API_KEY=la_tua_chiave_qui

     # O se usi OpenAI:
     # OPENAI_API_KEY=la_tua_chiave_openai_qui

     # Modello da usare (default: claude-3-5-sonnet-20241022)
     JARVIS_MODEL=claude-3-5-sonnet-20241022

     # Impostazioni vocali
     JARVIS_TTS_RATE=150
     JARVIS_TTS_VOLUME=0.9
     JARVIS_LANGUAGE=it-IT

     # Comportamento applicazione
     JARVIS_ALWAYS_ON_TOP=true
     JARVIS_SYSTEM_TRAY=true
     JARVIS_LOG_LEVEL=INFO
     ```

## ▶️ Esecuzione

Avvia JARVIS con:
```bash
python main.py
```

Oppure, se hai creato un eseguibile:
```bash
jarvis.exe
```

## 💡 Utilizzo

### Interfaccia grafica
- **Digitazione**: Scrivi nel campo in basso e premi Invio o clicca su "Invia"
- **Input vocale**: Tieni premuto il pulsante del microfono e parla
- **Visualizzazione**: La chat mostra i tuoi messaggi (a destra, blu) e le risposte di JARVIS (a sinistra, ciano)

### Comandi vocali disponibili
JARVIS riconosce naturalmente il linguaggio, ma alcuni esempi di comandi:
- "Apri Chrome" - apre il browser Chrome
- "Vai a YouTube" - apre YouTube nel browser predefinito
- "Apri Blocco note" - apre l'applicazione Blocco note
- "Ferma ascolto" - disattiva temporaneamente il microfono

JARVIS riconosce inoltre i sinonimi delle applicazioni (es. "calcolatrice" → calc, "blocco" → notepad, "esplora" → explorer) e l'apertura dei siti web sia con "apri <sito>" che "vai a <sito>".

### Applicazioni e siti autorizzati
Per motivi di sicurezza, JARVIS può aprire solo le applicazioni e i siti web elencati nella configurazione (`Config.AUTHORIZED_APPS` e `Config.AUTHORIZED_URLS` in `jarvis/config.py`). Per modificarli, aggiorna il file `.env` o il codice di configurazione.

## 🏗️ Struttura del progetto

```
jarvis-ai/
├── main.py                 # Punto d'ingresso
├── requirements.txt        # Dipendenze Python
├── .env.example            # Template per configurazione
├── .gitignore              # File da ignorare in Git
├── README.md               # Questo file
├── assets/                 # Risorse (icone, suoni)
└── jarvis/                 # Pacchetto sorgente
    ├── __init__.py
    ├── config.py           # Gestione configurazione
    ├── core/               # Nucleo logico
    │   ├── __init__.py
    │   ├── llm_client.py   # Client per API LLM
    │   └── engine.py       # Motore di orchestramento
    ├── modules/            # Moduli funzionali
    │   ├── __init__.py
    │   ├── speech.py       # Riconoscimento e sintesi vocale
    │   └── windows_tools.py# Funzioni Windows sicure
    ├── gui/                # Interfaccia grafica
    │   ├── __init__.py
    │   └── app.py          # Finestra principale PyQt6
    └── utils/              # Utility
        ├── __init__.py
        └── logger.py       # Sistema di logging
```

## 🔧 Personalizzazione

### Cambiare il modello AI
Modifica `JARVIS_MODEL` nel file `.env`:
- Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, etc.
- OpenAI: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`, etc.

### Regolare le impostazioni vocali
- `JARVIS_TTS_RATE`: Velocità della parola (parole al minuto, default 150)
- `JARVIS_TTS_VOLUME`: Volume (0.0 a 1.0, default 0.9)
- `JARVIS_LANGUAGE`: Lingua per riconoscimento/sintesi (default `it-IT`)
- `JARVIS_MICROPHONE_INDEX` (opzionale): Forza l'uso di un microfono specifico per indice. Per vedere gli indici disponibili, esegui:
  ```bash
  python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"
  ```

### Aggiungere applicazioni/websites autorizzati
Modifica il file `.env` o direttamente `jarvis/config.py` nelle sezioni:
- `AUTHORIZED_APPS`: dizionario `{nome: eseguibile}`
- `AUTHORIZED_URLS`: lista di URL HTTPS

## 🛠️ Sviluppo e contribuzione

### Aggiungere nuovi moduli
1. Crea un nuovo file in `jarvis/modules/` (es. `jarvis/modules/nuovo_modulo.py`)
2. Implementa le funzioni necessarie
3. Importa e usa il modulo in `jarvis/core/engine.py` o dove necessario
4. Aggiorna `__init__.py` nella cartella modules se necessario

### Estendere l'interfaccia
Modifica `jarvis/gui/app.py` per aggiungere nuove funzionalità GUI, mantenendo lo stile scuro futuristico.

## ⚠️ Sicurezza

- **Nessuna chiave API nel codice**: Tutte le credenziali sono in `.env` (mai committato)
- **Whitelist rigorosa**: Solo applicazioni e siti esplicitamente autorizzati possono essere aperti
- **Nessun accesso arbitrario**: JARVIS non esegue comandi di sistema non autorizzati
- **Log locali**: I log sono salvati localmente nella cartella `logs/`

## 📝 Log e risoluzione problemi

I log sono disponibili nella cartella `logs/jarvis.log`. Livelli di log configurabili tramite `JARVIS_LOG_LEVEL` nel `.env`:
- `DEBUG`: Informazioni dettagliate (utile per sviluppo)
- `INFO`: Informazioni generali (default)
- `WARNING`: Avvisi
- `ERROR`: Solo errori

### Problemi comuni

1. **Microfono non funzionante**
   - Controlla che il microfono sia attivato nelle impostazioni di Windows
   - Assicurati che nessuna altra applicazione lo stia utilizzando esclusivamente
   - Prova a riavviare l'applicazione

2. **Riconoscimento vocale inaccurato**
   - Parla chiaramente e vicino al microfono
   - Riduci il rumore di fondo
   - Assicurati che `JARVIS_LANGUAGE` sia impostato su `it-IT`

3. **Applicazioni che non si aprono**
   - Verifica che l'applicazione sia effettivamente installata
   - Controlla che il nome dell'eseguibile corrisponda a quello in `AUTHORIZED_APPS`
   - Alcune applicazioni potrebbero richiedere percorsi completi

4. **Errori API LLM**
   - Verifica che la chiave API sia corretta e attiva
   - Controlla il tuo credito/quota con il provider
   - Assicurati di avere connessione internet

## 📄 Licenza

Questo progetto è distribuito sotto la licenza MIT. Vedi il file `LICENSE` per dettagli.

## 👥 Crediti

Ispirato a JARVIS dell'Universo Cinematografico Marvel.
Sviluppato con Python, PyQt6, SpeechRecognition, pyttsx3, e le API di Anthropic/OpenAI.

---

**Nota**: JARVIS è progettato come assistente personale domestico. Non utilizzare per scopi che possano compromettere la sicurezza o la privacy. L'utente è responsabile dell'uso corretto e sicuro dell'applicazione.