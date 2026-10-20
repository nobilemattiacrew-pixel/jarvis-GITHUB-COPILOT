"""Gestione del contesto e instradamento verso provider LLM configurabili."""

import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from config import Settings


class AssistantBrain:
    """Mantiene una breve cronologia e genera risposte con il provider selezionato."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._history: list[dict[str, str]] = []
        self._system_prompt = (
            f"Sei {settings.assistant_name}, assistente personale dal tono sofisticato, "
            f"formale, efficiente e sottilmente arguto. Rivolgiti sempre all'utente come "
            f"'{settings.user_title}'. Rispondi in italiano, ma comprendi l'inglese. "
            "Non dichiarare di aver eseguito azioni che non puoi compiere. "
            "Non richiedere né rivelare password o chiavi API."
        )

    def respond(self, prompt: str) -> str:
        """Invia una richiesta al provider e conserva solo il contesto recente."""
        self._history.append({"role": "user", "content": prompt})
        try:
            if self.settings.llm_provider == "openai":
                answer = self._respond_openai()
            elif self.settings.llm_provider == "anthropic":
                answer = self._respond_anthropic()
            elif self.settings.llm_provider == "ollama":
                answer = self._respond_ollama()
            else:
                answer = self._local_reply()
        except Exception:
            logging.exception("Errore nel provider LLM %s", self.settings.llm_provider)
            answer = self._local_reply()

        self._history.append({"role": "assistant", "content": answer})
        self._history = self._history[-20:]
        return answer

    def _respond_openai(self) -> str:
        """Invia la cronologia recente al modello OpenAI configurato."""
        if not self.settings.openai_api_key:
            raise ValueError("Impostare OPENAI_API_KEY oppure selezionare un altro provider.")
        from openai import OpenAI

        client = OpenAI(api_key=self.settings.openai_api_key, timeout=30.0)
        result = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[{"role": "system", "content": self._system_prompt}, *self._history],
            timeout=30.0,
        )
        content = result.choices[0].message.content
        return content.strip() if content else self._local_reply()

    def _respond_anthropic(self) -> str:
        """Invia la cronologia recente al modello Anthropic configurato."""
        if not self.settings.anthropic_api_key:
            raise ValueError("Impostare ANTHROPIC_API_KEY oppure selezionare un altro provider.")
        from anthropic import Anthropic

        client = Anthropic(api_key=self.settings.anthropic_api_key, timeout=30.0)
        result = client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=500,
            system=self._system_prompt,
            messages=self._history,
        )
        text_parts = [block.text for block in result.content if block.type == "text"]
        return " ".join(text_parts).strip() or self._local_reply()

    def _respond_ollama(self) -> str:
        """Interroga il servizio Ollama locale usando il suo endpoint chat."""
        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                *self._history,
            ],
            "stream": False,
        }
        request = Request(
            f"{self.settings.ollama_base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result["message"]["content"].strip()

    def _local_reply(self) -> str:
        """Risposta di cortesia usata quando un provider non è configurato o disponibile."""
        return (
            f"Certamente, {self.settings.user_title}. Ho ricevuto la richiesta, "
            "ma il servizio di elaborazione non è disponibile al momento."
        )