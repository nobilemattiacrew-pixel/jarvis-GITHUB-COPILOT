"""Comandi di sistema espliciti e limitati a operazioni locali consentite."""

import logging
import os
import platform
import re
import shutil
import subprocess
import unicodedata
import webbrowser


class SystemControl:
    """Apre applicazioni allowlistate, regola il volume e legge CPU e batteria."""

    _APP_ALIASES = {
        "browser": {"browser", "navigatore", "internet", "chrome", "firefox"},
        "notepad": {"blocco note", "notepad", "editor di testo", "text editor"},
        "spotify": {"spotify", "musica"},
    }

    def handle_command(self, command: str) -> str | None:
        """Esegue solo richieste esplicite note; restituisce None per le altre."""
        normalized = self._normalize(command)
        open_match = re.match(r"^(?:per favore )?(?:apri|open|avvia|launch)\s+(.+)$", normalized)
        if open_match:
            target = open_match.group(1).strip(" .!?\t")
            for app, aliases in self._APP_ALIASES.items():
                if target in aliases:
                    return self.open_application(app)

        volume_match = re.search(
            r"\bvolume\D{0,24}(\d{1,3})\s*(?:%|percento|per cento)?\b",
            normalized,
        )
        if volume_match:
            return self.set_volume(int(volume_match.group(1)))

        if any(term in normalized for term in (
            "batteria", "battery", "cpu", "processore", "stato del sistema", "system status"
        )):
            return self.get_system_status()

        return None

    def open_application(self, application: str) -> str:
        """Apre una delle applicazioni note senza passare comandi a una shell."""
        try:
            if application == "browser":
                if webbrowser.open_new_tab("https://www.google.com"):
                    return "Ho aperto il browser, Signore."
                return "Non riesco ad avviare il browser predefinito."

            system = platform.system()
            if application == "notepad":
                if system == "Windows":
                    subprocess.Popen(["notepad.exe"], shell=False)
                elif system == "Darwin":
                    subprocess.Popen(["open", "-a", "TextEdit"], shell=False)
                else:
                    editor = next(
                        (shutil.which(name) for name in (
                            "gnome-text-editor", "gedit", "mousepad", "xed", "kate", "kwrite"
                        ) if shutil.which(name)),
                        None,
                    )
                    if not editor:
                        return "Non trovo un editor di testo supportato su questo sistema."
                    subprocess.Popen([editor], shell=False)
                return "Blocco note avviato, Signore."

            if application == "spotify":
                if system == "Windows":
                    os.startfile("spotify:")
                elif system == "Darwin":
                    subprocess.Popen(["open", "-a", "Spotify"], shell=False)
                else:
                    spotify = shutil.which("spotify")
                    if spotify:
                        subprocess.Popen([spotify], shell=False)
                    elif webbrowser.open_new_tab("https://open.spotify.com"):
                        return "Spotify non è installato; ho aperto il player web."
                    else:
                        return "Non riesco ad avviare Spotify o il player web."
                return "Spotify avviato, Signore."

            return "Applicazione non consentita."
        except (OSError, subprocess.SubprocessError) as error:
            logging.warning("Avvio applicazione %s non riuscito: %s", application, error)
            return f"Non sono riuscito ad avviare {application}, Signore."
        except Exception as error:
            logging.exception("Errore imprevisto durante l'avvio di %s", application)
            return f"Si è verificato un errore avviando {application}: {error}"

    def set_volume(self, percent: int) -> str:
        """Imposta il volume tra 0 e 100 usando l'interfaccia prevista dal sistema."""
        if not 0 <= percent <= 100:
            return "Il volume deve essere compreso tra 0 e 100 percento, Signore."

        try:
            system = platform.system()
            if system == "Windows":
                from pycaw.pycaw import AudioUtilities

                AudioUtilities.GetSpeakers().EndpointVolume.SetMasterVolumeLevelScalar(
                    percent / 100, None
                )
            elif system == "Darwin":
                subprocess.run(
                    ["osascript", "-e", f"set volume output volume {percent}"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            elif system == "Linux":
                if shutil.which("wpctl"):
                    subprocess.run(
                        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent}%"],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                elif shutil.which("amixer"):
                    subprocess.run(
                        ["amixer", "sset", "Master", f"{percent}%"],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                else:
                    return "Installi wpctl o amixer per controllare il volume su Linux."
            else:
                return f"Il controllo del volume non è supportato su {system}."
            return f"Volume impostato al {percent} percento, Signore."
        except Exception as error:
            logging.warning("Impostazione volume non riuscita: %s", error)
            return "Non sono riuscito a modificare il volume. Verifichi i permessi e i driver audio."

    def get_system_status(self) -> str:
        """Legge utilizzo CPU e, se disponibile, percentuale e stato della batteria."""
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.2)
            battery = psutil.sensors_battery()
            if battery is None:
                battery_status = "batteria non rilevata"
            else:
                charging = ", collegata all'alimentazione" if battery.power_plugged else ""
                battery_status = f"batteria al {battery.percent:.0f}%{charging}"
            return f"CPU al {cpu:.0f}%; {battery_status}, Signore."
        except Exception as error:
            logging.warning("Lettura stato sistema non riuscita: %s", error)
            return "Non riesco a leggere lo stato del sistema in questo momento."

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalizza accenti e maiuscole per riconoscere comandi in italiano o inglese."""
        decomposed = unicodedata.normalize("NFKD", text.casefold())
        return "".join(character for character in decomposed if not unicodedata.combining(character))