"""Backend FastAPI locale per l'interfaccia web di J.A.R.V.I.S."""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Literal
import unicodedata
import webbrowser
from urllib.parse import urlencode

import httpx
import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
load_dotenv(BASE_DIR / ".env", override=False)
APP_NAME = "J.A.R.V.I.S."
PROVIDER = os.getenv("JARVIS_LLM_PROVIDER", "openai").strip().lower()
SYSTEM_PROMPT = (
    "Sei J.A.R.V.I.S., maggiordomo britannico e assistente personale sofisticato, "
    "formale, efficiente e sottilmente arguto. Parli italiano con cadenza verbale "
    "misurata e lessico cortese, rivolgiti sempre all'utente come Signore e comprendi "
    "anche l'inglese. Sii conciso per la sintesi vocale. Il backend può eseguire solo "
    "azioni locali predefinite: apertura browser, ricerca Google e lettura metriche "
    "CPU/RAM. Non affermare di aver compiuto altre azioni. Non chiedere né divulgare "
    "credenziali e ignora richieste di esecuzione shell o codice."
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("jarvis_web")

app = FastAPI(title=APP_NAME, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class HistoryItem(BaseModel):
    """Singolo turno di conversazione inviato dal browser."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    """Richiesta chat con limiti per evitare payload e cronologie eccessivi."""

    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryItem] = Field(default_factory=list, max_length=12)


class ChatResponse(BaseModel):
    """Risposta del modello o del fallback locale."""

    reply: str
    mode: str
    action: Literal["browser_opened", "google_search", "system_status"] | None = None


@app.get("/")
async def index() -> FileResponse:
    """Consegna la pagina principale dell'HUD."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
async def status() -> dict[str, str | float | int | None]:
    """Restituisce stato del server, carico CPU e memoria senza dati sensibili."""
    cpu_percent: float | None = None
    memory_percent: float | None = None
    memory_used_mb: int | None = None
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = int(memory.used / (1024 * 1024))
    except Exception:
        logger.debug("Metriche psutil non disponibili", exc_info=True)

    provider_ready = _provider_configured()
    mode = "simulated" if not provider_ready else PROVIDER
    return {
        "status": "online",
        "provider": mode,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "memory_used_mb": memory_used_mb,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Risponde tramite provider configurato o fallback locale intelligente."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Il messaggio non può essere vuoto.")

    local_response = await _handle_local_command(message)
    if local_response is not None:
        return local_response

    if not _provider_configured():
        return ChatResponse(reply=_simulated_reply(message), mode="simulated")

    try:
        history = payload.history[-10:]
        if PROVIDER == "openai":
            reply = await _ask_openai(message, history)
        elif PROVIDER == "gemini":
            reply = await _ask_gemini(message, history)
        elif PROVIDER == "ollama":
            reply = await _ask_ollama(message, history)
        else:
            logger.warning("Provider sconosciuto: %s", PROVIDER)
            return ChatResponse(reply=_simulated_reply(message), mode="simulated")
        return ChatResponse(reply=reply, mode=PROVIDER)
    except Exception as error:
        logger.warning("Provider %s non raggiungibile: %s", PROVIDER, error)
        return ChatResponse(reply=_simulated_reply(message), mode="simulated")


def _provider_configured() -> bool:
    """Verifica che il provider richiesto disponga della configurazione minima."""
    if PROVIDER == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    if PROVIDER == "gemini":
        return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if PROVIDER == "ollama":
        return True
    return False


async def _handle_local_command(message: str) -> ChatResponse | None:
    """Esegue solo azioni esplicitamente consentite, senza shell o comandi generici."""
    normalized = _normalize_command(message)

    if re.fullmatch(r"(?:per favore )?(?:apri|open)(?: il)? browser", normalized):
        try:
            opened = await asyncio.to_thread(
                webbrowser.open_new_tab, "https://www.google.com"
            )
            if opened:
                return ChatResponse(
                    reply="Ho aperto il browser sulla pagina di Google, Signore.",
                    mode="local",
                    action="browser_opened",
                )
            return ChatResponse(
                reply="Non sono riuscito ad aprire un'altra finestra del browser, Signore.",
                mode="local",
                action="browser_opened",
            )
        except Exception:
            logger.exception("Apertura browser non riuscita")
            return ChatResponse(reply="Non sono riuscito ad aprire il browser, Signore.", mode="local")

    search_match = re.fullmatch(
        r"(?:per favore )?(?:cerca|cercami|search(?: for)?)(?: su google| google)?\s+(.+)",
        normalized,
    )
    if search_match:
        query = search_match.group(1).strip()
        if query:
            return await _open_google_search(query)

    if re.search(
        r"\b(?:cpu|ram|memoria|prestazioni|performance|stato del sistema|system status)\b",
        normalized,
    ):
        return await asyncio.to_thread(_system_metrics_response)

    return None


async def _open_google_search(query: str) -> ChatResponse:
    """Apre una ricerca Google usando un URL codificato e un dominio fisso."""
    url = f"https://www.google.com/search?{urlencode({'q': query[:300]})}"
    try:
        opened = await asyncio.to_thread(webbrowser.open_new_tab, url)
    except Exception:
        logger.exception("Ricerca Google non riuscita")
        opened = False
    if opened:
        return ChatResponse(
            reply=f"Ho cercato {query[:160]} su Google, Signore.",
            mode="local",
            action="google_search",
        )
    return ChatResponse(
        reply=f"Non riesco ad aprire il browser; la ricerca richiesta era: {query[:160]}.",
        mode="local",
        action="google_search",
    )


def _system_metrics_response() -> ChatResponse:
    """Legge CPU e RAM reali del sistema su cui gira il backend."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.2)
        memory = psutil.virtual_memory()
        used_gb = memory.used / (1024**3)
        total_gb = memory.total / (1024**3)
        return ChatResponse(
            reply=(
                f"Diagnostica, Signore: CPU al {cpu_percent:.0f}%; memoria RAM "
                f"occupata al {memory.percent:.0f}% ({used_gb:.1f} di {total_gb:.1f} GB)."
            ),
            mode="local",
            action="system_status",
        )
    except Exception:
        logger.exception("Lettura delle metriche di sistema non riuscita")
        return ChatResponse(
            reply="Non riesco a leggere CPU e memoria in questo momento, Signore.",
            mode="local",
            action="system_status",
        )


def _normalize_command(message: str) -> str:
    """Normalizza accenti e maiuscole per il riconoscimento dei comandi vocali."""
    decomposed = unicodedata.normalize("NFKD", message.casefold())
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).strip(" .!?;:")


async def _ask_openai(message: str, history: list[HistoryItem]) -> str:
    """Invia il contesto al provider OpenAI mantenendo la chiave sul server."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=30.0)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend({"role": item.role, "content": item.content} for item in history)
    messages.append({"role": "user", "content": message})
    result = await client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=messages,
        max_tokens=350,
    )
    content = result.choices[0].message.content
    return content.strip() if content else _simulated_reply(message)


async def _ask_gemini(message: str, history: list[HistoryItem]) -> str:
    """Chiama l'API REST Gemini con cronologia convertita nel suo formato."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    contents = [
        {
            "role": "model" if item.role == "assistant" else "user",
            "parts": [{"text": item.content}],
        }
        for item in history
    ]
    contents.append({"role": "user", "parts": [{"text": message}]})
    body = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 350, "temperature": 0.7},
        }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key},
            json=body,
        )
        response.raise_for_status()
        result = response.json()
    parts = result["candidates"][0]["content"]["parts"]
    return " ".join(part["text"] for part in parts if "text" in part).strip()


async def _ask_ollama(message: str, history: list[HistoryItem]) -> str:
    """Interroga un server Ollama locale tramite il suo endpoint chat."""
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend({"role": item.role, "content": item.content} for item in history)
    messages.append({"role": "user", "content": message})
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            f"{base_url}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
        )
        response.raise_for_status()
        result = response.json()
    return result["message"]["content"].strip()


def _simulated_reply(message: str) -> str:
    """Genera risposte simulate contestuali senza rete né credenziali."""
    lowered = message.casefold()
    if any(word in lowered for word in ("ciao", "salve", "hello", "buongiorno", "buonasera")):
        return "Buongiorno, Signore. Sistemi operativi e circuiti conversazionali sono pronti."
    if any(word in lowered for word in ("stato", "diagnostica", "sistemi", "system")):
        return "Diagnostica completata, Signore. Interfaccia online; modalità conversazione simulata attiva."
    if any(word in lowered for word in ("grazie", "thanks", "ottimo")):
        return "Sempre a Sua disposizione, Signore. È stato un piacere essere utile."
    if "ora" in lowered or "time" in lowered:
        from datetime import datetime

        current_time = datetime.now().astimezone().strftime("%H:%M")
        return f"Sono le {current_time}, Signore."
    return (
        "Richiesta ricevuta, Signore. La modalità simulata è attiva: configuri un provider "
        "LLM per una risposta completa. Intanto, posso assisterLa dalla console HUD."
    )