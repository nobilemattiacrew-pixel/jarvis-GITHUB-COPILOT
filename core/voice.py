"""Sintesi vocale asincrona con ripiego testuale se il motore locale non è disponibile."""

import logging
from queue import Queue
from threading import Thread
from typing import Callable

from config import Settings


class Voice:
    """Elabora le risposte vocali in un thread distinto dal ciclo principale."""

    def __init__(
        self,
        settings: Settings,
        on_state: Callable[[str], None] | None = None,
    ) -> None:
        self.settings = settings
        self.on_state = on_state or (lambda state: None)
        self._queue: Queue[str | None] = Queue()
        self._thread = Thread(target=self._speak_loop, name="jarvis-voice", daemon=True)
        self._thread.start()

    def say(self, text: str) -> None:
        """Accoda una frase senza bloccare chi la invoca."""
        self._queue.put(text)

    def close(self) -> None:
        """Completa la coda vocale e attende la terminazione del thread."""
        self._queue.put(None)
        self._thread.join(timeout=10)

    def _speak_loop(self) -> None:
        """Consuma la coda e parla tramite il motore locale se disponibile."""
        engine = None
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self.settings.speech_rate)
        except Exception as error:
            logging.warning("Sintesi vocale non disponibile; uso il testo: %s", error)

        while True:
            text = self._queue.get()
            if text is None:
                break
            try:
                self.on_state("speaking")
                if engine is None:
                    print(f"J.A.R.V.I.S.: {text}")
                else:
                    engine.say(text)
                    engine.runAndWait()
            except Exception as error:
                logging.warning("Errore durante la sintesi vocale: %s", error)
                print(f"J.A.R.V.I.S.: {text}")
            finally:
                self.on_state("listening")

        if engine is not None:
            try:
                engine.stop()
            except Exception:
                logging.debug("Chiusura del motore vocale non riuscita.", exc_info=True)