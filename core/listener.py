"""Ascolto microfono e filtro della wake word, eseguiti su un thread dedicato."""

import logging
import re
from threading import Event, Thread
from typing import Callable

import speech_recognition as sr

from config import Settings


class Listener:
    """Riconosce il parlato e inoltra solo le richieste attivate dalla wake word."""

    def __init__(
        self,
        settings: Settings,
        on_command: Callable[[str], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.settings = settings
        self.on_command = on_command
        self.on_error = on_error or (lambda message: logging.warning(message))
        self._recognizer = sr.Recognizer()
        self._stop_event = Event()
        self._thread = Thread(target=self._listen_loop, name="jarvis-listener", daemon=True)

    def start(self) -> None:
        """Avvia il thread di ascolto senza bloccare l'interfaccia principale."""
        self._thread.start()

    def stop(self) -> None:
        """Richiede la chiusura del thread di ascolto e attende il rilascio del microfono."""
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=self.settings.listen_timeout + 2)

    def _listen_loop(self) -> None:
        """Ascolta il microfono e inoltra al callback solo frasi attivate."""
        while not self._stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    audio = self._recognizer.listen(
                        source,
                        timeout=self.settings.listen_timeout,
                        phrase_time_limit=self.settings.phrase_time_limit,
                    )
                text = self._recognizer.recognize_google(
                    audio, language=self.settings.stt_language
                ).strip()
                command = self._extract_command(text)
                if command:
                    self.on_command(command)
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                logging.debug("Parlato non riconosciuto.")
            except sr.RequestError as error:
                self.on_error(f"Servizio di trascrizione non disponibile: {error}")
                self._stop_event.wait(2)
            except Exception as error:
                self.on_error(f"Problema con il microfono: {error}")
                self._stop_event.wait(2)

    def _extract_command(self, text: str) -> str | None:
        """Rimuove la wake word dalla frase; in modalità libera restituisce tutto il testo."""
        if not self.settings.require_wake_word:
            return text or None

        pattern = re.compile(rf"\b{re.escape(self.settings.wake_word)}\b", re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            return None
        command = (text[: match.start()] + " " + text[match.end() :]).strip(" ,.!?;:")
        return command or ""  # La wake word da sola viene ignorata dal chiamante.