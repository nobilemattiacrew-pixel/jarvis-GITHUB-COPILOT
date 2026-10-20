"""Configurazione dell'assistente tramite variabili d'ambiente e file .env."""

from dataclasses import dataclass
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _env_bool(name: str, default: bool) -> bool:
    """Legge un booleano da ambiente; i valori non riconosciuti usano il default."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si", "sì"}


@dataclass(frozen=True)
class Settings:
    """Impostazioni runtime; non inserire mai credenziali direttamente nel codice."""

    assistant_name: str
    user_title: str
    language: str
    wake_word: str
    require_wake_word: bool
    stt_language: str
    llm_provider: str
    openai_api_key: str
    openai_model: str
    anthropic_api_key: str
    anthropic_model: str
    ollama_base_url: str
    ollama_model: str
    speech_rate: int
    listen_timeout: int
    phrase_time_limit: int

    @classmethod
    def from_env(cls) -> "Settings":
        """Carica le impostazioni, accettando i provider openai, anthropic, ollama o local."""
        provider = os.getenv("JARVIS_LLM_PROVIDER", "openai").strip().lower()
        if provider not in {"openai", "anthropic", "ollama", "local"}:
            raise ValueError(
                "JARVIS_LLM_PROVIDER deve essere openai, anthropic, ollama o local"
            )

        return cls(
            assistant_name=os.getenv("JARVIS_NAME", "J.A.R.V.I.S."),
            user_title=os.getenv("JARVIS_USER_TITLE", "Signore"),
            language=os.getenv("JARVIS_LANGUAGE", "it"),
            wake_word=os.getenv("JARVIS_WAKE_WORD", "jarvis").strip().lower(),
            require_wake_word=_env_bool("JARVIS_REQUIRE_WAKE_WORD", True),
            stt_language=os.getenv("JARVIS_STT_LANGUAGE", "it-IT"),
            llm_provider=provider,
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            speech_rate=int(os.getenv("JARVIS_SPEECH_RATE", "185")),
            listen_timeout=int(os.getenv("JARVIS_LISTEN_TIMEOUT", "5")),
            phrase_time_limit=int(os.getenv("JARVIS_PHRASE_TIME_LIMIT", "12")),
        )


settings = Settings.from_env()