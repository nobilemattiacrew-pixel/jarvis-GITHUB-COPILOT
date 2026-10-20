"""Avvia J.A.R.V.I.S. Web su localhost e apre il browser predefinito."""

import threading
import webbrowser

import uvicorn


HOST = "127.0.0.1"
PORT = 8000
URL = f"http://localhost:{PORT}"


def main() -> None:
    """Apre l'interfaccia dopo l'avvio del server ASGI."""
    threading.Timer(1.2, lambda: webbrowser.open(URL)).start()
    uvicorn.run("server:app", host=HOST, port=PORT, reload=False, log_level="info")


if __name__ == "__main__":
    main()