"""HUD desktop in CustomTkinter con aggiornamenti sicuri tra thread."""

import logging
from queue import Empty, Queue
from threading import Event, Thread


class HUD:
    """Finestra HUD che possiede il proprio thread e riceve eventi tramite coda."""

    _STATUS = {
        "listening": ("IN ASCOLTO", "#40E0D0"),
        "thinking": ("IN ELABORAZIONE", "#5AA9FF"),
        "speaking": ("IN RISPOSTA", "#00BFFF"),
        "offline": ("NON DISPONIBILE", "#FF6B6B"),
    }

    def __init__(self, title: str = "J.A.R.V.I.S. | HUD") -> None:
        self.title = title
        self._events: Queue[tuple[str, str, str]] = Queue()
        self._ready = Event()
        self._closed = Event()
        self._thread = Thread(target=self._run, name="jarvis-hud", daemon=True)
        self._available = False

    @property
    def closed(self) -> bool:
        """Indica se l'utente ha chiuso la finestra HUD."""
        return self._closed.is_set()

    def start(self, timeout: float = 5.0) -> bool:
        """Avvia la GUI sul proprio thread; restituisce False se il toolkit non è disponibile."""
        self._thread.start()
        self._ready.wait(timeout)
        return self._available

    def set_status(self, status: str) -> None:
        """Accoda un cambio stato senza accedere ai widget dal thread chiamante."""
        self._events.put(("status", status, ""))

    def add_message(self, speaker: str, message: str) -> None:
        """Accoda una riga di conversazione da visualizzare nel log."""
        self._events.put(("message", speaker, message))

    def stop(self) -> None:
        """Richiede la chiusura ordinata della finestra e attende il thread GUI."""
        if self._thread.is_alive():
            self._events.put(("stop", "", ""))
            self._thread.join(timeout=3)

    def _run(self) -> None:
        """Crea e gestisce tutti i widget esclusivamente nel thread grafico."""
        try:
            import customtkinter as ctk
            import tkinter as tk

            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            root = ctk.CTk()
            root.title(self.title)
            root.geometry("900x620")
            root.minsize(680, 480)
            root.configure(fg_color="#07111B")
            root.grid_columnconfigure(0, weight=1)
            root.grid_rowconfigure(1, weight=1)

            header = ctk.CTkFrame(root, fg_color="#0B1C2A", corner_radius=8, height=72)
            header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
            header.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                header,
                text="J.A.R.V.I.S.",
                text_color="#8DEBFF",
                font=ctk.CTkFont(family="Orbitron", size=24, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=20, pady=(12, 0))
            ctk.CTkLabel(
                header,
                text="PERSONAL ASSISTANT  /  SYSTEM ONLINE",
                text_color="#5D8398",
                font=ctk.CTkFont(family="Consolas", size=11),
            ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 12))

            body = ctk.CTkFrame(root, fg_color="transparent")
            body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
            body.grid_columnconfigure(0, weight=1, minsize=210)
            body.grid_columnconfigure(1, weight=3)
            body.grid_rowconfigure(0, weight=1)

            status_panel = ctk.CTkFrame(body, fg_color="#0B1C2A", corner_radius=8)
            status_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            ctk.CTkLabel(
                status_panel,
                text="CORE STATUS",
                text_color="#6C98AC",
                font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            ).pack(pady=(24, 12))

            dial = tk.Canvas(
                status_panel,
                width=154,
                height=154,
                bg="#0B1C2A",
                highlightthickness=0,
            )
            dial.pack(pady=8)
            dial.create_oval(8, 8, 146, 146, outline="#16435A", width=2)
            dial.create_oval(18, 18, 136, 136, outline="#147D9B", width=1)
            indicator = dial.create_oval(58, 58, 96, 96, fill="#40E0D0", outline="")

            status_label = ctk.CTkLabel(
                status_panel,
                text="IN ASCOLTO",
                text_color="#40E0D0",
                font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            )
            status_label.pack(pady=(8, 4))
            ctk.CTkLabel(
                status_panel,
                text="VOICE INTERFACE  /  READY",
                text_color="#456579",
                font=ctk.CTkFont(family="Consolas", size=10),
            ).pack(pady=(0, 18))

            log_panel = ctk.CTkFrame(body, fg_color="#0B1C2A", corner_radius=8)
            log_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            log_panel.grid_columnconfigure(0, weight=1)
            log_panel.grid_rowconfigure(1, weight=1)
            ctk.CTkLabel(
                log_panel,
                text="CONVERSATION LOG",
                text_color="#6C98AC",
                font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=18, pady=16)
            log = ctk.CTkTextbox(
                log_panel,
                fg_color="#07111B",
                text_color="#C8DCE5",
                border_color="#123447",
                border_width=1,
                corner_radius=6,
                font=ctk.CTkFont(family="Consolas", size=13),
                wrap="word",
            )
            log.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
            log.tag_config("user", foreground="#8DEBFF")
            log.tag_config("assistant", foreground="#D6F4FF")
            log.tag_config("system", foreground="#FFB86B")
            log.configure(state="disabled")

            def close_window() -> None:
                """Segnala la chiusura e distrugge la finestra dal thread GUI."""
                self._closed.set()
                root.destroy()

            def process_events() -> None:
                """Applica gli eventi accodati ai widget nel thread proprietario della GUI."""
                try:
                    while True:
                        event, first, second = self._events.get_nowait()
                        if event == "stop":
                            close_window()
                            return
                        if event == "status":
                            label, color = self._STATUS.get(
                                first, self._STATUS["listening"]
                            )
                            status_label.configure(text=label, text_color=color)
                            dial.itemconfigure(indicator, fill=color)
                        elif event == "message":
                            tag = first.lower() if first.lower() in {
                                "user", "assistant", "system"
                            } else "system"
                            log.configure(state="normal")
                            log.insert("end", f"{first}: {second}\n\n", tag)
                            log.see("end")
                            log.configure(state="disabled")
                except Empty:
                    pass
                if not self._closed.is_set():
                    root.after(100, process_events)

            root.protocol("WM_DELETE_WINDOW", close_window)
            self._available = True
            self._ready.set()
            root.after(100, process_events)
            root.mainloop()
        except Exception as error:
            logging.warning("HUD non disponibile: %s", error)
            self._available = False
            self._ready.set()
