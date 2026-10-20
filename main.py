"""Avvio del nucleo vocale di J.A.R.V.I.S. (ascolto, risposta e sintesi)."""

import logging
from queue import Empty, Queue

from config import settings
from core.brain import AssistantBrain
from core.listener import Listener
from core.voice import Voice
from gui.hud import HUD
from modules.system_control import SystemControl


EXIT_COMMANDS = {"esci", "chiudi", "termina", "quit", "exit", "stop"}


def main() -> None:
    """Avvia i componenti e gestisce le richieste fino a un comando di uscita."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    commands: Queue[str] = Queue()
    brain = AssistantBrain(settings)
    hud = HUD(title=f"{settings.assistant_name} | HUD")
    if not hud.start():
        logging.warning("Avvio in modalità testuale: HUD non disponibile.")
    controls = SystemControl()
    voice = Voice(settings, on_state=hud.set_status)
    listener = Listener(
        settings,
        on_command=commands.put,
        on_error=lambda message: (logging.warning(message), hud.add_message("Sistema", message)),
    )

    print(f"{settings.assistant_name} pronto. Dica '{settings.wake_word}' per iniziare.")
    hud.set_status("listening")
    listener.start()
    try:
        while True:
            if hud.closed:
                break
            try:
                command = commands.get(timeout=0.5)
            except Empty:
                continue

            if command.strip().lower() in EXIT_COMMANDS:
                voice.say(f"A disposizione, {settings.user_title}.")
                break

            print(f"Tu: {command}")
            hud.add_message("Tu", command)
            hud.set_status("thinking")
            answer = controls.handle_command(command)
            if answer is None:
                answer = brain.respond(command)
            print(f"{settings.assistant_name}: {answer}")
            hud.add_message("J.A.R.V.I.S.", answer)
            voice.say(answer)
    except KeyboardInterrupt:
        print("\nArresto richiesto da tastiera.")
    finally:
        listener.stop()
        voice.close()
        hud.stop()


if __name__ == "__main__":
    main()