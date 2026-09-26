#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LERNASSISTENT – plattformübergreifende Version
==============================================

Diese Datei ist bewusst als "eine Datei" aufgebaut.

Start:
    python lernassistent_crossplatform.py

Beim ersten Start werden fehlende Python-Pakete automatisch über genau den
Python-Interpreter installiert, mit dem diese Datei gestartet wurde.

Unterstützt:
    • Windows
    • macOS
    • Linux (experimentell)

Kernfunktionen:
    • globaler Auswahl-Shortcut
    • Bildschirm markieren und an ein lokales Ollama-Vision-Modell senden
    • Text- und Sprachfragen mit direkter Nachfrage
    • lokale Sprachausgabe
    • lokale Spracheingabe
    • optionaler Freisprechmodus über den Mikrofoneingang
    • automatische Prüfung und Download des Ollama-Modells
    • moderne, kompakte Lernhilfe-Oberfläche

WICHTIG:
    Ollama selbst ist eine separate Systemanwendung. Aus Sicherheitsgründen
    wird kein fremder Installer ungeprüft aus dem Internet ausgeführt.
    Ist Ollama nicht vorhanden, öffnet die App die offizielle Download-Seite.
    Das Modell wird danach automatisch über "ollama pull" geladen.

Benötigte/optionale Pakete:
    Pflicht:
        pillow
        pynput

    Für Sprache:
        numpy
        sounddevice
        faster-whisper

    Für hochwertige Qwen-Sprachausgabe:
        qwen-tts
        torch

Die Sprachpakete werden erst installiert, wenn die jeweilige Funktion benötigt
wird. Dadurch bleibt der erste Start möglichst schlank.

Bedienung:
    Windows/Linux:
        Ctrl + Shift + Leertaste   Stelle markieren
        Ctrl + Alt + Leertaste     Sprachfrage starten/stoppen
        Ctrl + Alt + W             Freisprechen ein/aus

    macOS:
        Cmd + Shift + Leertaste    Stelle markieren
        Cmd + Option + Leertaste   Sprachfrage starten/stoppen
        Cmd + Option + W           Freisprechen ein/aus

macOS:
    Bei der ersten Nutzung können macOS-Berechtigungen für Bildschirmaufnahme,
    Mikrofon und Bedienungshilfen verlangt werden. Diese müssen in den
    Systemeinstellungen erlaubt werden.

"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Bootstrap: fehlende Python-Pakete automatisch installieren
# ---------------------------------------------------------------------------

import importlib.util
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import json
import base64
import io
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Any, Protocol


APP_NAME = "Lernhilfe"
APP_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / ".lernassistent"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_PACKAGES = {
    "PIL": "pillow",
    "pynput": "pynput",
}

OPTIONAL_PACKAGES = {
    "voice": {
        "numpy": "numpy",
        "sounddevice": "sounddevice",
        "faster_whisper": "faster-whisper",
    },
    "qwen_tts": {
        "qwen_tts": "qwen-tts",
        "torch": "torch",
        "sounddevice": "sounddevice",
    },
}


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _run_pip_install(packages: list[str]) -> None:
    if not packages:
        return

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        *packages,
    ]

    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Die automatische Installation von Python-Paketen ist fehlgeschlagen.\n\n"
            f"Python: {sys.executable}\n"
            f"Pakete: {', '.join(packages)}\n\n"
            "Mögliche Ursachen sind eine fehlende Internetverbindung, "
            "fehlende Schreibrechte oder eine verwaltete Python-Umgebung.\n"
            "Falls du die .py-Datei direkt startest, prüfe deine Internetverbindung "
            "und die Python-Umgebung. In einer fertig gebündelten App ist keine "
            "Python-Installation erforderlich."
        ) from exc


def ensure_packages(package_map: dict[str, str], optional: bool = False) -> bool:
    missing = [
        pip_name
        for module_name, pip_name in package_map.items()
        if not _module_available(module_name)
    ]

    if not missing:
        return True

    try:
        _run_pip_install(missing)
    except RuntimeError:
        if optional:
            return False
        raise

    return all(_module_available(module) for module in package_map)


def bootstrap_required_packages() -> None:
    # In a PyInstaller/packaged release, dependencies are bundled and pip must
    # never be invoked from the application itself.
    if getattr(sys, "frozen", False):
        return
    ensure_packages(REQUIRED_PACKAGES, optional=False)


try:
    bootstrap_required_packages()
except Exception as bootstrap_error:
    # Tkinter gehört bei den üblichen Python-Installationen zur Standardbibliothek.
    # Wenn nicht, kann die Fehlermeldung trotzdem sauber angezeigt werden.
    print(f"\n{APP_NAME}: {bootstrap_error}\n", file=sys.stderr)
    raise SystemExit(1)


import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from PIL import Image, ImageDraw, ImageGrab, ImageTk

try:
    from pynput import keyboard as pynput_keyboard
except ImportError as exc:
    raise SystemExit(f"pynput konnte nach der Installation nicht geladen werden: {exc}")


# ---------------------------------------------------------------------------
# 2. Konfiguration
# ---------------------------------------------------------------------------

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")

PRIMARY_SHORTCUT = "<cmd>+<shift>+space" if IS_MAC else "<ctrl>+<shift>+space"
VOICE_MODE_SHORTCUT = "<cmd>+<alt>+w" if IS_MAC else "<ctrl>+<alt>+w"
VOICE_QUESTION_SHORTCUT = "<cmd>+<alt>+space" if IS_MAC else "<ctrl>+<alt>+space"

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

# Das ursprüngliche Modell bleibt bevorzugt erhalten.
OLLAMA_MODEL = "qwen3-vl:4b-instruct"
OLLAMA_FALLBACK_MODEL = "qwen3-vl:2b-instruct"

OLLAMA_CONTEXT_TOKENS = 4096
OLLAMA_KEEP_ALIVE = "5m"
ANSWER_TOKEN_LIMIT = 420
AUTO_READ_ALOUD = False
STREAM_FLUSH_MS = 60
MAX_CONVERSATION_TURNS = 4

CONTEXT_IMAGE_SIZE = (1024, 700)
FOCUS_IMAGE_SIZE = (1024, 768)

WHISPER_MODEL = "base"
QWEN_TTS_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
USE_QWEN_TTS_BY_DEFAULT = False


OLLAMA_PULL_TIMEOUT = 1800
OLLAMA_TIMEOUT = 180
OLLAMA_START_TIMEOUT = 20

# ---------------------------------------------------------------------------
# UI-Design
# ---------------------------------------------------------------------------

BG = "#0d0b12"
SURFACE = "#17131f"
SURFACE_2 = "#211a2b"
SURFACE_3 = "#2a2036"
TEXT = "#f7f2ff"
MUTED = "#aaa0b7"
ACCENT = "#c084fc"
ACCENT_2 = "#e879f9"
SUCCESS = "#86efac"
WARNING = "#f9c74f"
ERROR = "#fb7185"
BORDER = "#33283f"


@dataclass
class MarkerStroke:
    points: list[tuple[int, int]]


# ---------------------------------------------------------------------------
# 3. Plattform-Helfer
# ---------------------------------------------------------------------------

class PlatformAdapter:
    """Kapselt Unterschiede zwischen Windows/macOS/Linux."""

    @staticmethod
    def modifier_label() -> str:
        return "Cmd" if IS_MAC else "Ctrl"

    @staticmethod
    def selection_shortcut_label() -> str:
        return "⌘ ⇧ Leertaste" if IS_MAC else "Ctrl + Shift + Leertaste"

    @staticmethod
    def voice_mode_shortcut_label() -> str:
        return "⌘ ⌥ W" if IS_MAC else "Ctrl + Alt + W"

    @staticmethod
    def voice_question_shortcut_label() -> str:
        return "⌘ ⌥ Leertaste" if IS_MAC else "Ctrl + Alt + Leertaste"

    @staticmethod
    def open_url(url: str) -> None:
        import webbrowser
        webbrowser.open(url)

    @staticmethod
    def ollama_commands() -> list[list[str]]:
        if IS_WINDOWS:
            local_candidates = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama" / "ollama.exe",
            ]
            return [[str(p)] for p in local_candidates if str(p) != "."]

        if IS_MAC:
            return [
                ["/usr/local/bin/ollama"],
                ["/opt/homebrew/bin/ollama"],
                [str(Path.home() / ".ollama" / "bin" / "ollama")],
                ["ollama"],
            ]

        return [
            ["/usr/local/bin/ollama"],
            [str(Path.home() / ".local" / "bin" / "ollama")],
            ["ollama"],
        ]

    @staticmethod
    def find_ollama() -> Optional[str]:
        found = shutil.which("ollama")
        if found:
            return found

        for candidate_group in PlatformAdapter.ollama_commands():
            if candidate_group and Path(candidate_group[0]).exists():
                return candidate_group[0]

        return None

    @staticmethod
    def official_ollama_url() -> str:
        return "https://ollama.com/download"

    @staticmethod
    def start_ollama_process(ollama_executable: str) -> subprocess.Popen:
        kwargs: dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
        }

        if IS_WINDOWS:
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            kwargs["creationflags"] = creation_flags

        return subprocess.Popen(
            [ollama_executable, "serve"],
            **kwargs,
        )

    @staticmethod
    def stop_process(process: Optional[subprocess.Popen]) -> None:
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 4. Globale Hotkeys – plattformneutral mit pynput
# ---------------------------------------------------------------------------


class AIBackend(Protocol):
    """Kleiner Vertrag für austauschbare KI-Backends.

    Die aktuelle Release nutzt Ollama. Ein späteres OpenAI-Backend kann
    implementiert werden, ohne UI, Lernlogik oder Sprachsteuerung umzubauen.
    """

    active_model: str

    def ensure_ready(self) -> None:
        ...

    def chat(
        self,
        prompt: str,
        images: list[str],
        cancel_event: threading.Event,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        ...



class UserActionRouter:
    """Behandelt explizite Nutzeraktionen vor dem KI-Backend.

    Bewusst eng gefasst: Nur eindeutig erkannte Aktionen werden lokal
    ausgeführt. Normale Fragen gehen weiterhin vollständig an die KI.
    """

    SEARCH_PREFIXES = (
        "suche ",
        "such ",
    )

    @classmethod
    def search_query(cls, text: str) -> Optional[str]:
        cleaned = " ".join((text or "").strip().split())
        lowered = cleaned.casefold()

        for prefix in cls.SEARCH_PREFIXES:
            if lowered.startswith(prefix):
                query = cleaned[len(prefix):].strip(" \t:;,.!?")
                return query or None

        return None

    @classmethod
    def execute(cls, text: str) -> Optional[str]:
        query = cls.search_query(text)
        if not query:
            return None

        # webbrowser.open() delegiert an den vom Betriebssystem registrierten
        # Standardbrowser und funktioniert unter Windows/macOS/Linux.
        import urllib.parse
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        opened = webbrowser.open(url, new=2)
        if not opened:
            raise RuntimeError(
                "Der Standardbrowser konnte nicht geöffnet werden. "
                "Bitte prüfe die Standardbrowser-Einstellung des Betriebssystems."
            )

        return query


LEARNING_MODES: dict[str, tuple[str, str]] = {
    "Erklären": (
        "Erkläre den markierten Inhalt verständlich und präzise. "
        "Nenne die zentrale Idee zuerst und erläutere Fachbegriffe kurz."
    ),
    "Hinweis": (
        "Gib bewusst nur einen hilfreichen Hinweis zum Weiterdenken. "
        "Verrate die vollständige Lösung nicht, außer die lernende Person "
        "fragt ausdrücklich danach."
    ),
    "Schritt für Schritt": (
        "Führe die lernende Person Schritt für Schritt durch die Aufgabe. "
        "Begründe jeden Schritt kurz und übersichtlich."
    ),
    "Prüfen": (
        "Prüfe die markierte Lösung oder Aussage. Benenne zuerst, was stimmt, "
        "und danach konkrete Fehler oder Verbesserungen. Wenn keine eigene "
        "Lösung erkennbar ist, sage das offen."
    ),
    "Üben": (
        "Erstelle auf Basis des markierten Inhalts eine kurze passende "
        "Übungsaufgabe. Gib die Lösung erst nach einer Nachfrage."
    ),
}


class GlobalHotkeys:
    """Nur explizite Tastenkombinationen – niemals einzelne Buchstaben."""

    def __init__(
        self,
        on_selection: Callable[[], None],
        on_voice_mode_toggle: Callable[[], None],
        on_voice_question: Callable[[], None],
    ) -> None:
        self.on_selection = on_selection
        self.on_voice_mode_toggle = on_voice_mode_toggle
        self.on_voice_question = on_voice_question
        self.listener: Optional[pynput_keyboard.GlobalHotKeys] = None

    def start(self) -> None:
        self.listener = pynput_keyboard.GlobalHotKeys(
            {
                PRIMARY_SHORTCUT: self.on_selection,
                VOICE_MODE_SHORTCUT: self.on_voice_mode_toggle,
                VOICE_QUESTION_SHORTCUT: self.on_voice_question,
            }
        )
        self.listener.start()

    def stop(self) -> None:
        try:
            if self.listener is not None:
                self.listener.stop()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 5. Bildschirm-Auswahl
# ---------------------------------------------------------------------------

class ScreenSelector:
    def __init__(
        self,
        root: tk.Tk,
        on_selection: Callable[[Image.Image, MarkerStroke], None],
    ) -> None:
        self.root = root
        self.on_selection = on_selection

        self.window: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.screenshot: Optional[Image.Image] = None
        self.photo: Optional[ImageTk.PhotoImage] = None
        self.points: list[tuple[int, int]] = []
        self.stroke_id: Optional[int] = None

    def open(self) -> None:
        if self.window is not None:
            return

        try:
            # Für eine robuste Koordinatenzuordnung verwenden wir den
            # Primärbildschirm. Auf Retina/HiDPI kann Pillow physische Pixel
            # liefern, während Tk logische Pixel meldet. Deshalb wird das
            # Bild anschließend exakt auf die Tk-Fenstergröße skaliert.
            raw_screenshot = ImageGrab.grab()

            width = max(1, self.root.winfo_screenwidth())
            height = max(1, self.root.winfo_screenheight())

            if raw_screenshot.size != (width, height):
                resampling = getattr(Image, "Resampling", Image).LANCZOS
                self.screenshot = raw_screenshot.resize(
                    (width, height),
                    resampling,
                )
            else:
                self.screenshot = raw_screenshot

            self.window = tk.Toplevel(self.root)
            self.window.overrideredirect(True)
            self.window.attributes("-topmost", True)
            self.window.geometry(f"{width}x{height}+0+0")
            self.window.configure(bg="black")

            self.photo = ImageTk.PhotoImage(self.screenshot)

            self.canvas = tk.Canvas(
                self.window,
                width=width,
                height=height,
                highlightthickness=0,
                bd=0,
                cursor="crosshair",
            )
            self.canvas.pack(fill="both", expand=True)
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

            # Dunkler Schleier
            self.canvas.create_rectangle(
                0, 0, width, height,
                fill="#08060c",
                stipple="gray25",
                outline="",
            )

            self.canvas.create_text(
                width // 2,
                42,
                text=(
                    "Markiere die unklare Stelle  •  "
                    "Maus gedrückt halten  •  Esc = abbrechen"
                ),
                fill="white",
                font=("TkDefaultFont", 14, "bold"),
            )

            self.canvas.bind("<ButtonPress-1>", self.start_stroke)
            self.canvas.bind("<B1-Motion>", self.extend_stroke)
            self.canvas.bind("<ButtonRelease-1>", self.finish_stroke)
            self.window.bind("<Escape>", lambda _event: self.close())
            self.window.focus_force()

        except Exception as exc:
            self.close()
            messagebox.showerror(
                APP_NAME,
                "Die Bildschirmaufnahme konnte nicht geöffnet werden.\n\n"
                f"{exc}\n\n"
                "Unter macOS bitte unter Datenschutz & Sicherheit → "
                "Bildschirmaufnahme die Berechtigung für Python/Terminal "
                "bzw. die verwendete App erlauben.",
            )

    def start_stroke(self, event: tk.Event) -> None:
        if self.canvas is None:
            return

        self.points = [(event.x, event.y)]
        self.stroke_id = self.canvas.create_line(
            event.x, event.y,
            event.x + 1, event.y + 1,
            fill=ACCENT_2,
            width=34,
            capstyle="round",
            joinstyle="round",
            smooth=True,
            stipple="gray50",
        )

    def extend_stroke(self, event: tk.Event) -> None:
        if self.canvas is None or self.stroke_id is None:
            return

        self.points.append((event.x, event.y))
        coords = [coordinate for point in self.points for coordinate in point]
        self.canvas.coords(self.stroke_id, *coords)

    def finish_stroke(self, event: tk.Event) -> None:
        if self.screenshot is None or self.stroke_id is None:
            return

        self.points.append((event.x, event.y))

        if len(self.points) < 2:
            self.close()
            return

        screenshot = self.screenshot.copy()
        stroke = MarkerStroke(self.points.copy())

        self.close()
        self.on_selection(screenshot, stroke)

    def close(self) -> None:
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass

        self.window = None
        self.canvas = None
        self.photo = None
        self.screenshot = None
        self.points = []
        self.stroke_id = None


# ---------------------------------------------------------------------------
# 6. Moderne Lernhilfe-Oberfläche
# ---------------------------------------------------------------------------

class AssistantPanel:
    def __init__(
        self,
        root: tk.Tk,
        on_repeat: Callable[[], None],
        on_stop: Callable[[], None],
        on_send_question: Callable[[str], None],
        on_voice_mode: Callable[[], None],
        on_help: Callable[[], None],
        on_select: Callable[[], None],
        on_mode_change: Callable[[str], None],
    ) -> None:
        self.root = root
        self.on_repeat = on_repeat
        self.on_stop = on_stop
        self.on_send_question = on_send_question
        self.on_voice_mode = on_voice_mode
        self.on_help = on_help
        self.on_select = on_select
        self.on_mode_change = on_mode_change
        self.current_mode = "Erklären"
        self.mode_buttons: dict[str, ttk.Button] = {}

        self.loading = False
        self.loading_step = 0

        self.window = tk.Toplevel(root)
        self.window.title(APP_NAME)
        self.window.configure(bg=BG)
        self.window.geometry("560x620")
        self.window.minsize(460, 480)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window.withdraw()

        self._configure_style()
        self._build()

    def _configure_style(self) -> None:
        style = ttk.Style(self.window)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#170d20",
            borderwidth=0,
            padding=(14, 9),
            font=("TkDefaultFont", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_2), ("disabled", SURFACE_3)],
            foreground=[("disabled", MUTED)],
        )

        style.configure(
            "Dark.TButton",
            background=SURFACE_3,
            foreground=TEXT,
            borderwidth=0,
            padding=(12, 9),
            font=("TkDefaultFont", 10),
        )
        style.map(
            "Dark.TButton",
            background=[("active", "#3a2d49")],
        )

    def _build(self) -> None:
        header = tk.Frame(self.window, bg=SURFACE, height=76)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=SURFACE)
        brand.pack(side="left", padx=22)

        tk.Label(
            brand,
            text="✦",
            bg=SURFACE,
            fg=ACCENT_2,
            font=("TkDefaultFont", 20, "bold"),
        ).pack(side="left", padx=(0, 10))

        title_frame = tk.Frame(brand, bg=SURFACE)
        title_frame.pack(side="left")

        tk.Label(
            title_frame,
            text="Lernhilfe",
            bg=SURFACE,
            fg=TEXT,
            font=("TkDefaultFont", 17, "bold"),
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="lokal • verständlich • bildbasiert",
            bg=SURFACE,
            fg=MUTED,
            font=("TkDefaultFont", 8),
        ).pack(anchor="w")

        tk.Button(
            header,
            text="×",
            command=self.hide,
            bg=SURFACE,
            fg=MUTED,
            activebackground=SURFACE,
            activeforeground=TEXT,
            bd=0,
            font=("TkDefaultFont", 20),
            cursor="hand2",
        ).pack(side="right", padx=16)

        body = tk.Frame(self.window, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=18)

        self.status_card = tk.Frame(
            body,
            bg=SURFACE_2,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.status_card.pack(fill="x", pady=(0, 12))

        self.status = tk.Label(
            self.status_card,
            text="●  Bereit zum Markieren",
            bg=SURFACE_2,
            fg=ACCENT,
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
        )
        self.status.pack(fill="x", padx=16, pady=(13, 3))

        self.hint = tk.Label(
            self.status_card,
            text=self._shortcut_hint(),
            bg=SURFACE_2,
            fg=MUTED,
            font=("TkDefaultFont", 9),
            anchor="w",
            justify="left",
        )
        self.hint.pack(fill="x", padx=16, pady=(0, 13))

        mode_card = tk.Frame(
            body,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        mode_card.pack(fill="x", pady=(0, 12))

        tk.Label(
            mode_card,
            text="Lernmodus",
            bg=SURFACE,
            fg=MUTED,
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(9, 5))

        mode_row = tk.Frame(mode_card, bg=SURFACE)
        mode_row.pack(fill="x", padx=10, pady=(0, 10))

        for mode_name in LEARNING_MODES:
            button = ttk.Button(
                mode_row,
                text=mode_name,
                command=lambda name=mode_name: self.set_mode(name),
                style="Dark.TButton",
            )
            button.pack(side="left", padx=(0, 6))
            self.mode_buttons[mode_name] = button

        self._refresh_mode_buttons()

        answer_card = tk.Frame(
            body,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        answer_card.pack(fill="both", expand=True)

        self.answer_box = scrolledtext.ScrolledText(
            answer_card,
            wrap="word",
            height=18,
            font=("TkDefaultFont", 11),
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground="#56346e",
            relief="flat",
            bd=0,
            padx=18,
            pady=16,
        )
        self.answer_box.pack(fill="both", expand=True, padx=1, pady=1)
        self.answer_box.configure(state="disabled")

        question_card = tk.Frame(
            body,
            bg=SURFACE_2,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        question_card.pack(fill="x", pady=(14, 0))

        tk.Label(
            question_card,
            text="Frage oder Nachfrage",
            bg=SURFACE_2,
            fg=TEXT,
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w", padx=12, pady=(9, 4))

        question_row = tk.Frame(question_card, bg=SURFACE_2)
        question_row.pack(fill="x", padx=10, pady=(0, 10))

        self.question_entry = tk.Entry(
            question_row,
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            font=("TkDefaultFont", 10),
        )
        self.question_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self.question_entry.bind("<Return>", self._submit_question)

        self.ask_button = ttk.Button(
            question_row,
            text="Fragen",
            command=self._submit_question,
            style="Accent.TButton",
        )
        self.ask_button.pack(side="right")

        controls = tk.Frame(body, bg=BG)
        controls.pack(fill="x", pady=(10, 0))

        self.select_button = ttk.Button(
            controls,
            text=f"✦ Stelle markieren  {PlatformAdapter.selection_shortcut_label()}",
            command=self.on_select,
            style="Accent.TButton",
        )
        self.select_button.pack(side="left")

        self.stop_button = ttk.Button(
            controls,
            text="■ Stoppen",
            command=self.on_stop,
            style="Dark.TButton",
        )
        self.stop_button.pack(side="left")

        self.voice_button = ttk.Button(
            controls,
            text=f"🎙 Freisprechen  {PlatformAdapter.voice_mode_shortcut_label()}",
            command=self.on_voice_mode,
            style="Dark.TButton",
        )
        self.voice_button.pack(side="left", padx=8)

        self.help_button = ttk.Button(
            controls,
            text="ⓘ Bedienung",
            command=self.on_help,
            style="Dark.TButton",
        )
        self.help_button.pack(side="left")

        self.copy_button = ttk.Button(
            controls,
            text="⧉ Kopieren",
            command=self.copy_answer,
            style="Dark.TButton",
            state="disabled",
        )
        self.copy_button.pack(side="right", padx=(0, 8))

        self.repeat_button = ttk.Button(
            controls,
            text="▶ Vorlesen",
            command=self.on_repeat,
            style="Accent.TButton",
            state="disabled",
        )
        self.repeat_button.pack(side="right")

    def _shortcut_hint(self) -> str:
        return (
            f"{PlatformAdapter.selection_shortcut_label()}  markieren  •  "
            f"{PlatformAdapter.voice_question_shortcut_label()}  Sprachfrage  •  "
            f"{PlatformAdapter.voice_mode_shortcut_label()}  Freisprechen"
        )

    def copy_answer(self) -> None:
        try:
            text = self.answer_box.get("1.0", "end").strip()
            if not text:
                return
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
            self.window.update()
            self.status.configure(text="●  Erklärung in die Zwischenablage kopiert", fg=SUCCESS)
        except tk.TclError:
            pass

    def set_mode(self, mode: str) -> None:
        if mode not in LEARNING_MODES:
            return
        self.current_mode = mode
        self._refresh_mode_buttons()
        self.on_mode_change(mode)

    def _refresh_mode_buttons(self) -> None:
        for name, button in self.mode_buttons.items():
            if name == self.current_mode:
                button.configure(style="Accent.TButton")
            else:
                button.configure(style="Dark.TButton")

    def _submit_question(self, _event: Optional[tk.Event] = None) -> str:
        question = self.question_entry.get().strip()
        if question:
            self.question_entry.delete(0, "end")
            self.on_send_question(question)
        return "break"

    def set_voice_mode(self, active: bool) -> None:
        if active:
            self.voice_button.configure(
                text=f"● Freisprechen aktiv  {PlatformAdapter.voice_mode_shortcut_label()}"
            )
        else:
            self.voice_button.configure(
                text=f"🎙 Freisprechen  {PlatformAdapter.voice_mode_shortcut_label()}"
            )

    def show(self) -> None:
        self.window.deiconify()
        self.window.attributes("-topmost", True)
        self.window.lift()
        self.window.update_idletasks()

        x = max(18, self.window.winfo_screenwidth() - self.window.winfo_width() - 28)
        y = max(18, self.window.winfo_screenheight() - self.window.winfo_height() - 56)
        self.window.geometry(f"+{x}+{y}")

    def hide(self) -> None:
        self.window.withdraw()

    def _set_text(self, text: str) -> None:
        self.answer_box.configure(state="normal")
        self.answer_box.delete("1.0", "end")
        self.answer_box.insert("1.0", text)
        self.answer_box.configure(state="disabled")

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.select_button.configure(state=state)
        self.ask_button.configure(state=state)
        self.voice_button.configure(state=state)

    def show_streaming(self, text: str) -> None:
        self.show()
        self.loading = True
        self.status.configure(text="●  Erklärung wird formuliert …", fg=ACCENT)
        self._set_text(text)

    def show_loading(self, question: Optional[str] = None) -> None:
        self.show()
        self.loading = True
        self.loading_step = 0
        self.repeat_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.set_busy(True)

        if question:
            self._set_text(
                f"Deine Frage\n\n„{question}“\n\n"
                "Ich verbinde sie mit deiner Markierung …"
            )
        else:
            self._set_text(
                "Ich analysiere die markierte Stelle und den relevanten "
                "Bildschirm-Kontext …"
            )

        self._animate_loading()

    def _animate_loading(self) -> None:
        if not self.loading:
            return

        phases = (
            "● ○ ○  Markierung und Kontext werden vorbereitet",
            "● ● ○  Das lokale Vision-Modell liest die Stelle",
            "● ● ●  Erklärung wird formuliert",
        )
        self.status.configure(
            text=phases[self.loading_step % len(phases)],
            fg=ACCENT,
        )
        self.loading_step += 1
        self.window.after(800, self._animate_loading)

    def show_answer(self, answer: str) -> None:
        self.loading = False
        self.status.configure(
            text=f"●  {self.current_mode} • Erklärung fertig",
            fg=SUCCESS,
        )
        self._set_text(answer)
        self.repeat_button.configure(state="normal")
        self.copy_button.configure(state="normal")
        self.set_busy(False)

    def show_listening(self) -> None:
        self.show()
        self.loading = False
        self.status.configure(text="●  Ich höre zu …", fg=ACCENT_2)
        self._set_text(
            "Sprich jetzt ganz normal.\n\n"
            "Nach kurzer Stille endet die Aufnahme automatisch."
        )
        self.repeat_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.set_busy(False)

    def show_message(self, text: str) -> None:
        self.show()
        self.loading = False
        self.status.configure(text="●  " + text, fg=ACCENT)
        self._set_text(text)

    def show_error(self, message: str) -> None:
        self.loading = False
        self.show()
        self.status.configure(text="●  Das hat noch nicht geklappt", fg=ERROR)
        self._set_text(message)
        self.repeat_button.configure(state="disabled")
        self.set_busy(False)

    def show_speaking(self, fallback: bool = False) -> None:
        suffix = "  •  Systemstimme" if fallback else ""
        self.status.configure(
            text=f"●  Lernhilfe spricht{suffix}",
            fg=ACCENT_2,
        )
        self.repeat_button.configure(text="■ Vorlesen stoppen", state="normal")

    def show_settings(self, info: str) -> None:
        messagebox.showinfo("Lernhilfe – Status", info, parent=self.window)


# ---------------------------------------------------------------------------
# 7. Ollama
# ---------------------------------------------------------------------------

class OllamaManager:
    def __init__(self, post_message: Callable[[str], None]) -> None:
        self.post_message = post_message
        self.process: Optional[subprocess.Popen] = None
        self.active_model = OLLAMA_MODEL
        self.ready = False
        self.lock = threading.Lock()

    @staticmethod
    def _json_get(url: str, timeout: float = 2.0) -> Any:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _post_json(
        url: str,
        payload: dict[str, Any],
        timeout: float = OLLAMA_TIMEOUT,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)

    def _models(self) -> Optional[set[str]]:
        try:
            data = self._json_get(OLLAMA_TAGS_URL, timeout=2.0)
            if not isinstance(data, dict):
                return set()

            models = data.get("models", [])
            return {
                item.get("name")
                for item in models
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return None

    def ensure_ready(self) -> None:
        with self.lock:
            if self.ready:
                return

            models = self._models()

            if models is None:
                self._start_ollama()
                models = self._wait_for_server()

            if models is None:
                raise RuntimeError(
                    "Ollama konnte nicht erreicht werden.\n\n"
                    "Bitte starte Ollama einmal und versuche es erneut."
                )

            # Bereits vorhandenes Modell bevorzugen.
            if OLLAMA_MODEL in models:
                self.active_model = OLLAMA_MODEL
            elif OLLAMA_FALLBACK_MODEL in models:
                self.active_model = OLLAMA_FALLBACK_MODEL
            else:
                # Erst das bevorzugte Modell versuchen. Falls der Download
                # scheitert (z.B. zu wenig RAM/VRAM oder Speicherplatz), wird
                # automatisch auf das deutlich kleinere Fallback gewechselt.
                try:
                    self._pull_model(OLLAMA_MODEL)
                except Exception as preferred_error:
                    self.post_message(
                        "Das 4B-Modell konnte nicht geladen werden. "
                        "Ich versuche automatisch das kleinere 2B-Modell …"
                    )
                    try:
                        self._pull_model(OLLAMA_FALLBACK_MODEL)
                    except Exception as fallback_error:
                        raise RuntimeError(
                            "Kein passendes Qwen-Vision-Modell konnte bereitgestellt werden.\n\n"
                            f"4B: {preferred_error}\n\n"
                            f"2B: {fallback_error}\n\n"
                            "Prüfe Speicherplatz, Internetverbindung und Ollama-Version."
                        ) from fallback_error

                models = self._models() or set()

                if OLLAMA_MODEL in models:
                    self.active_model = OLLAMA_MODEL
                elif OLLAMA_FALLBACK_MODEL in models:
                    self.active_model = OLLAMA_FALLBACK_MODEL
                else:
                    raise RuntimeError(
                        "Das Qwen-Vision-Modell konnte nicht bereitgestellt werden.\n\n"
                        f"Versucht wurden: {OLLAMA_MODEL} und {OLLAMA_FALLBACK_MODEL}\n"
                        "Bitte prüfe Speicherplatz, Internetverbindung und Ollama-Version."
                    )

            self.ready = True

    def _start_ollama(self) -> None:
        executable = PlatformAdapter.find_ollama()

        if not executable:
            raise RuntimeError(
                "Ollama ist auf diesem Computer nicht installiert.\n\n"
                "Die App lädt absichtlich keinen unbekannten Installer herunter.\n"
                "Bitte installiere Ollama von der offiziellen Seite:\n\n"
                f"{PlatformAdapter.official_ollama_url()}\n\n"
                "Danach genügt ein Neustart dieser Datei."
            )

        try:
            self.process = PlatformAdapter.start_ollama_process(executable)
        except Exception as exc:
            raise RuntimeError(
                "Ollama wurde gefunden, konnte aber nicht automatisch gestartet werden.\n\n"
                f"Technischer Hinweis: {exc}"
            ) from exc

    def _wait_for_server(self) -> Optional[set[str]]:
        deadline = time.monotonic() + OLLAMA_START_TIMEOUT

        while time.monotonic() < deadline:
            models = self._models()
            if models is not None:
                return models
            time.sleep(0.35)

        return None

    def _pull_model(self, model: str) -> None:
        executable = PlatformAdapter.find_ollama()

        if not executable:
            raise RuntimeError("Die Ollama-Befehlszeile wurde nicht gefunden.")

        self.post_message(
            f"Qwen-Vision-Modell wird einmalig geladen: {model}\n"
            "Das kann je nach Internetverbindung einige Minuten dauern."
        )

        try:
            # stdout/stderr werden nicht verworfen: Fehler werden für die
            # Diagnose gesammelt. Ollama meldet Pull-Fortschritt typischerweise
            # zeilenweise als JSON.
            process = subprocess.Popen(
                [executable, "pull", model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            raise RuntimeError(
                "Ollama konnte das Modell nicht herunterladen.\n\n"
                f"{exc}"
            ) from exc

        output: list[str] = []

        try:
            stdout, _ = process.communicate(timeout=OLLAMA_PULL_TIMEOUT)
            output = [line.strip() for line in stdout.splitlines() if line.strip()]

            for line in output[-20:]:
                try:
                    event = json.loads(line)
                    status = event.get("status")
                    if status:
                        self.post_message(f"Modell: {status}")
                except json.JSONDecodeError:
                    if len(line) < 180:
                        self.post_message(f"Modell: {line}")

            return_code = process.returncode

        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise RuntimeError(
                "Der Modelldownload hat zu lange gedauert und wurde beendet."
            ) from exc

        if return_code != 0:
            details = "\n".join(output[-8:])
            raise RuntimeError(
                "Ollama konnte das Qwen-Modell nicht herunterladen.\n\n"
                f"Letzte Meldungen:\n{details}"
            )

    def chat(
        self,
        prompt: str,
        images: list[str],
        cancel_event: Optional[threading.Event] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        self.ensure_ready()

        payload = {
            "model": self.active_model,
            "stream": True,
            "think": False,
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": images,
                }
            ],
            "options": {
                "temperature": 0.2,
                "num_ctx": OLLAMA_CONTEXT_TOKENS,
                "num_predict": ANSWER_TOKEN_LIMIT,
            },
        }

        request = urllib.request.Request(
            OLLAMA_CHAT_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        answer_parts: list[str] = []

        try:
            with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT) as response:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        return ""

                    line = response.readline()
                    if not line:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if event.get("error"):
                        raise RuntimeError(f"Ollama meldet: {event['error']}")

                    message = event.get("message")
                    piece = (
                        message.get("content", "")
                        if isinstance(message, dict)
                        else ""
                    )

                    if piece:
                        answer_parts.append(piece)
                        if on_chunk is not None:
                            on_chunk("".join(answer_parts))

                    if event.get("done"):
                        break

        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama meldet einen HTTP-Fehler ({exc.code}).\n\n{details}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Ollama ist während der Anfrage nicht erreichbar.\n\n"
                "Prüfe, ob Ollama noch läuft."
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError(
                "Die lokale KI hat zu lange für die Antwort gebraucht."
            ) from exc

        answer = "".join(answer_parts).strip()

        if not answer:
            if cancel_event is not None and cancel_event.is_set():
                return ""
            raise RuntimeError(
                "Ollama hat keine verständliche Textantwort zurückgegeben."
            )

        return answer

    def shutdown(self) -> None:
        PlatformAdapter.stop_process(self.process)


# ---------------------------------------------------------------------------
# 8. Audio / Sprache
# ---------------------------------------------------------------------------

class SpeechManager:
    def __init__(
        self,
        post_ui: Callable[..., None],
        show_speaking: Callable[[bool], None],
        on_finished: Callable[[], None],
    ) -> None:
        self.post_ui = post_ui
        self.show_speaking = show_speaking
        self.on_finished = on_finished

        self.cancel_event = threading.Event()
        self.record_stop_event = threading.Event()
        self._active_state = False
        self.speech_id = 0
        self._lock = threading.Lock()

        self.tts_model: Any = None
        self.whisper_model: Any = None
        self.system_process: Optional[subprocess.Popen] = None

    @property
    def active(self) -> bool:
        with self._lock:
            return bool(getattr(self, "_active_state", False))

    def interrupt(self) -> None:
        self.cancel_event.set()
        self.record_stop_event.set()

        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

        process = self.system_process
        if process is not None:
            try:
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass

        with self._lock:
            self.speech_id += 1
            self._active_state = False

    def speak(self, text: str) -> None:
        if not text.strip():
            return

        with self._lock:
            if self.active:
                return
            self._active_state = True
            self.speech_id += 1
            current_id = self.speech_id

        self.cancel_event.clear()

        threading.Thread(
            target=self._worker,
            args=(text, current_id),
            daemon=True,
        ).start()

    def _worker(self, text: str, speech_id: int) -> None:
        try:
            self.show_speaking(False)

            try:
                if USE_QWEN_TTS_BY_DEFAULT:
                    self._speak_qwen(text)
                else:
                    self.show_speaking(True)
                    self._speak_system(text)
            except Exception:
                if self.cancel_event.is_set():
                    return

                self.show_speaking(True)
                self._speak_system(text)

        except Exception as exc:
            if not self.cancel_event.is_set():
                self.post_ui(
                    self._show_nonfatal_status,
                    str(exc),
                )
        finally:
            with self._lock:
                if speech_id == self.speech_id:
                    self._active_state = False

            if speech_id == self.speech_id:
                self.post_ui(self.on_finished)

    def _speak_qwen(self, text: str) -> None:
        # Die hochwertigen Pakete werden erst bei tatsächlicher Nutzung
        # installiert. Wenn das nicht klappt, greift die Systemstimme.
        if not ensure_packages(OPTIONAL_PACKAGES["qwen_tts"], optional=True):
            raise RuntimeError("Qwen-TTS ist nicht verfügbar.")

        import sounddevice as sd
        import torch
        from qwen_tts import Qwen3TTSModel

        if self.tts_model is None:
            self.post_ui(
                self._show_speech_preparation,
                "Hochwertige Stimme wird einmalig vorbereitet …",
            )

            # CPU ist der universellste Fallback. Auf CUDA wird automatisch
            # gewechselt, wenn Torch eine NVIDIA-GPU anbietet.
            if torch.cuda.is_available():
                device_map = "cuda:0"
                dtype = torch.bfloat16
            else:
                device_map = "cpu"
                dtype = torch.float32

            self.tts_model = Qwen3TTSModel.from_pretrained(
                QWEN_TTS_MODEL,
                device_map=device_map,
                dtype=dtype,
            )

        wavs, sample_rate = self.tts_model.generate_voice_design(
            text=text,
            language="German",
            instruct=(
                "Eine warme, klare und natürliche deutsche Stimme einer "
                "geduldigen Lernbegleitung. Ruhiges Tempo, deutliche "
                "Aussprache und freundlicher Ton."
            ),
        )

        if self.cancel_event.is_set():
            return

        sd.play(wavs[0], sample_rate)

        try:
            while True:
                if self.cancel_event.wait(0.05):
                    sd.stop()
                    return

                stream = sd.get_stream()
                if stream is None or not stream.active:
                    break
        finally:
            try:
                sd.stop()
            except Exception:
                pass

    def _speak_system(self, text: str) -> None:
        if self.cancel_event.is_set():
            return

        if IS_MAC:
            # macOS: eingebaute "say"-Stimme, keine zusätzliche Installation.
            process = subprocess.Popen(
                ["say", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.system_process = process

        elif IS_WINDOWS:
            # Windows: System.Speech ohne zusätzliche Python-Abhängigkeit.
            encoded = base64.b64encode(
                text.encode("utf-16-le")
            ).decode("ascii")

            command = (
                "$text = [Text.Encoding]::Unicode.GetString("
                "[Convert]::FromBase64String('"
                + encoded
                + "')); "
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.Speak($text)"
            )

            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.system_process = process

        elif shutil.which("espeak-ng"):
            self.system_process = subprocess.Popen(
                ["espeak-ng", "-v", "de", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        elif shutil.which("espeak"):
            self.system_process = subprocess.Popen(
                ["espeak", "-v", "de", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        else:
            raise RuntimeError(
                "Keine System-Sprachausgabe gefunden. "
                "Installiere optional espeak-ng oder aktiviere Qwen-TTS."
            )

        process = self.system_process

        while process is not None and process.poll() is None:
            if self.cancel_event.wait(0.05):
                try:
                    process.terminate()
                except Exception:
                    pass
                break

        self.system_process = None

    def stop_recording(self) -> None:
        self.record_stop_event.set()

    def record_until_silence(self) -> Any:
        self.record_stop_event.clear()

        if not ensure_packages(OPTIONAL_PACKAGES["voice"], optional=False):
            raise RuntimeError(
                "Die Sprachaufnahme benötigt numpy, sounddevice und faster-whisper."
            )

        import numpy as np
        import sounddevice as sd

        sample_rate = 16_000
        chunks: list[Any] = []
        heard_speech = False
        last_voice = time.monotonic()
        started = time.monotonic()

        def callback(indata, _frames, _time_info, _status) -> None:
            nonlocal heard_speech, last_voice

            audio_chunk = indata[:, 0].copy()
            chunks.append(audio_chunk)

            level = float(np.sqrt(np.mean(np.square(audio_chunk))))
            if level > 0.015:
                heard_speech = True
                last_voice = time.monotonic()

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1600,
                callback=callback,
            ):
                while not self.record_stop_event.is_set():
                    now = time.monotonic()

                    if heard_speech and now - last_voice > 1.3:
                        break

                    if not heard_speech and now - started > 8:
                        break

                    if now - started > 25:
                        break

                    time.sleep(0.05)
        except Exception as exc:
            raise RuntimeError(
                "Das Mikrofon konnte nicht geöffnet werden.\n\n"
                f"{exc}\n\n"
                "Prüfe die Mikrofon-Berechtigung des Programms."
            ) from exc

        if not chunks or not heard_speech:
            raise RuntimeError(
                "Ich habe keine Sprache gehört. "
                "Prüfe dein Mikrofon und versuche es erneut."
            )

        return np.concatenate(chunks)

    def transcribe(self, audio: Any) -> str:
        if not ensure_packages(OPTIONAL_PACKAGES["voice"], optional=False):
            raise RuntimeError(
                "Für Spracheingabe fehlen numpy, sounddevice oder faster-whisper."
            )

        from faster_whisper import WhisperModel

        if self.whisper_model is None:
            try:
                self.whisper_model = WhisperModel(
                    WHISPER_MODEL,
                    device="cuda",
                    compute_type="float16",
                )
            except Exception:
                self.whisper_model = WhisperModel(
                    WHISPER_MODEL,
                    device="cpu",
                    compute_type="int8",
                )

        segments, _ = self.whisper_model.transcribe(
            audio,
            language="de",
            beam_size=3,
            vad_filter=True,
        )

        return " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()

    def _show_speech_preparation(self, message: str) -> None:
        # Statusmeldung statt Fehlerdialog: Das Laden des TTS-Modells ist
        # beim ersten Einsatz normal und kann einige Zeit dauern.
        self.post_ui(self._show_nonfatal_status, message)

    @staticmethod
    def _show_nonfatal_status(message: str) -> None:
        print(f"{APP_NAME}: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 9. Hauptanwendung
# ---------------------------------------------------------------------------

class LearningAssistant:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()

        self.ui_events: queue.Queue[tuple[Callable[..., Any], tuple[Any, ...]]] = queue.Queue()
        self.root.after(50, self._drain_ui_events)

        self.panel = AssistantPanel(
            self.root,
            on_repeat=self.repeat_answer,
            on_stop=self.interrupt_current_output,
            on_send_question=self.handle_text_question,
            on_voice_mode=self.toggle_voice_mode,
            on_help=self.show_help,
            on_select=lambda: self.post_ui(self.selector.open),
            on_mode_change=self.set_learning_mode,
        )

        self.selector = ScreenSelector(
            self.root,
            self.handle_marked_image,
        )

        self.ollama = OllamaManager(
            post_message=lambda message: self.post_ui(
                self.panel.show_message,
                message,
            )
        )
        # Die Lernlogik spricht nur mit diesem Backend-Vertrag. Dadurch kann
        # später OpenAI ergänzt werden, ohne die Anwendung umzubauen.
        self.backend: AIBackend = self.ollama

        self.speech = SpeechManager(
            post_ui=self.post_ui,
            show_speaking=lambda fallback: self.post_ui(
                self.panel.show_speaking,
                fallback,
            ),
            on_finished=lambda: self.post_ui(
                self._finish_speaking,
            ),
        )

        self.last_marked_image: Optional[Image.Image] = None
        self.last_stroke: Optional[MarkerStroke] = None
        self.last_answer = ""
        self.pending_question: Optional[str] = None
        self.active_question: Optional[str] = None
        self.current_mode = "Erklären"
        self.conversation: list[tuple[str, str, str]] = []

        # Streaming wird bewusst gebündelt. Ein UI-Update pro Token macht
        # Tkinter unnötig langsam und erzeugt sichtbares Flackern.
        self.stream_lock = threading.Lock()
        self.stream_text = ""
        self.stream_request_id = 0
        self.stream_update_pending = False

        self.request_id = 0
        self.analysis_cancel_event = threading.Event()
        self.analysis_lock = threading.Lock()
        self.voice_active = False
        self.voice_stop_event = threading.Event()
        self.voice_lock = threading.Lock()

        self.voice_mode_active = False
        self.voice_mode_stop_event = threading.Event()
        self.voice_mode_cooldown_until = 0.0

        self.hotkeys = GlobalHotkeys(
            on_selection=lambda: self.post_ui(self.selector.open),
            on_voice_mode_toggle=lambda: self.post_ui(self.toggle_voice_mode),
            on_voice_question=lambda: self.post_ui(self.toggle_voice_capture),
        )

        try:
            self.hotkeys.start()
        except Exception as exc:
            self.panel.show_error(
                "Die globalen Tastenkürzel konnten nicht aktiviert werden.\n\n"
                f"{exc}\n\n"
                "Unter macOS muss die App gegebenenfalls unter "
                "Datenschutz & Sicherheit → Bedienungshilfen erlaubt werden."
            )

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def set_learning_mode(self, mode: str) -> None:
        if mode in LEARNING_MODES:
            self.current_mode = mode
            self.panel.show_message(
                f"Lernmodus: {mode}. Markiere eine Stelle oder stelle direkt eine Nachfrage."
            )

    # ---------------------------- UI threading ----------------------------

    def post_ui(self, callback: Callable[..., Any], *args: Any) -> None:
        self.ui_events.put((callback, args))

    def _drain_ui_events(self) -> None:
        try:
            while True:
                callback, args = self.ui_events.get_nowait()
                callback(*args)
        except queue.Empty:
            pass

        try:
            self.root.after(50, self._drain_ui_events)
        except tk.TclError:
            pass

    # ---------------------------- Markierung -------------------------------

    @staticmethod
    def marked_image(
        screenshot: Image.Image,
        stroke: MarkerStroke,
    ) -> Image.Image:
        marker_layer = Image.new(
            "RGBA",
            screenshot.size,
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(marker_layer)

        if len(stroke.points) >= 2:
            draw.line(
                stroke.points,
                fill=(232, 121, 249, 125),
                width=34,
                joint="curve",
            )

        for point in (stroke.points[0], stroke.points[-1]):
            x, y = point
            draw.ellipse(
                (x - 17, y - 17, x + 17, y + 17),
                fill=(232, 121, 249, 125),
            )

        return Image.alpha_composite(
            screenshot.convert("RGBA"),
            marker_layer,
        ).convert("RGB")

    def handle_marked_image(
        self,
        screenshot: Image.Image,
        stroke: MarkerStroke,
    ) -> None:
        # Eine neue Markierung ist ein neuer Lernkontext. Die vorherige
        # Erklärung darf nicht versehentlich in die neue Aufgabe einfließen.
        self.last_answer = ""
        self.active_question = None
        self.conversation.clear()
        self.last_marked_image = self.marked_image(screenshot, stroke)
        self.last_stroke = stroke

        question = self.pending_question
        self.pending_question = None
        self.active_question = question

        self.start_analysis(
            self.last_marked_image,
            stroke,
            question,
        )

    @staticmethod
    def _resize_for_model(
        image: Image.Image,
        maximum_size: tuple[int, int],
    ) -> Image.Image:
        result = image.copy()
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        result.thumbnail(maximum_size, resampling)
        return result

    @staticmethod
    def _encode_jpeg(image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.convert("RGB").save(
            buffer,
            format="JPEG",
            quality=88,
            optimize=True,
        )
        return base64.b64encode(
            buffer.getvalue()
        ).decode("ascii")

    @staticmethod
    def _focus_crop(
        image: Image.Image,
        stroke: MarkerStroke,
    ) -> Image.Image:
        xs, ys = zip(*stroke.points)
        margin = 240

        left = max(0, min(xs) - margin)
        top = max(0, min(ys) - margin)
        right = min(image.width, max(xs) + margin)
        bottom = min(image.height, max(ys) + margin)

        # Logischer Fehler aus dem Prototypen abgefangen:
        # Ein extrem kurzer/kleiner Crop darf nie 0 Pixel breit/hoch sein.
        if right <= left:
            right = min(image.width, left + 1)
        if bottom <= top:
            bottom = min(image.height, top + 1)

        return image.crop((left, top, right, bottom))

    # ----------------------------- Analyse ---------------------------------

    def start_analysis(
        self,
        image: Image.Image,
        stroke: MarkerStroke,
        spoken_question: Optional[str] = None,
    ) -> None:
        # Eine neue Anfrage ersetzt eine alte. Die UI blockiert parallele
        # Klicks; das Cancel-Event sorgt zusätzlich dafür, dass Streaming
        # nicht unnötig weiterverarbeitet wird.
        self.request_id += 1
        request_id = self.request_id
        self.analysis_cancel_event.set()
        self.analysis_cancel_event = threading.Event()
        cancel_event = self.analysis_cancel_event

        with self.stream_lock:
            self.stream_text = ""
            self.stream_request_id = request_id
            self.stream_update_pending = False

        self.panel.show_loading(spoken_question)

        def worker() -> None:
            try:
                answer = self.ask_ollama(
                    image,
                    stroke,
                    spoken_question,
                    request_id,
                    cancel_event,
                )
            except Exception as error:
                if cancel_event.is_set() or request_id != self.request_id:
                    return
                message = (
                    str(error).strip()
                    or f"Unerwarteter Fehler: {type(error).__name__}"
                )
                self.post_ui(
                    self._deliver_error,
                    request_id,
                    message,
                )
            else:
                if answer and not cancel_event.is_set():
                    self.post_ui(
                        self._deliver_answer,
                        request_id,
                        answer,
                    )

        threading.Thread(
            target=worker,
            daemon=True,
            name="Lernhilfe-Ollama",
        ).start()


    def ask_ollama(
        self,
        image: Image.Image,
        stroke: MarkerStroke,
        question: Optional[str],
        request_id: int,
        cancel_event: threading.Event,
    ) -> str:
        # Für Geschwindigkeit bekommt das Modell primär den relevanten Ausschnitt.
        # Der frühere vollständige Bildschirm war oft redundant und teuer.
        focus_image = self._resize_for_model(
            self._focus_crop(image, stroke),
            FOCUS_IMAGE_SIZE,
        )

        question_part = (
            f"\nAktuelle Frage der lernenden Person: „{question.strip()}“\n"
            if question and question.strip()
            else ""
        )

        mode_instruction = LEARNING_MODES.get(
            self.current_mode,
            LEARNING_MODES["Erklären"],
        )[0]

        prompt = (
            "Du bist eine geduldige deutschsprachige Lernhilfe. "
            "Das Bild zeigt die aktuell markierte Stelle eines Lerninhalts.\n"
            f"Lernmodus: {self.current_mode}. {mode_instruction}\n"
            f"{question_part}"
            "Arbeite ausschließlich mit dem erkennbaren Inhalt. "
            "Wenn Text, Formel oder Bild nicht sicher lesbar ist, sage das "
            "offen und erfinde nichts. Antworte direkt, natürlich und "
            "altersgerecht. Verwende kurze Absätze und bei mehreren "
            "Schritten eine nummerierte Liste. "
            "Zielumfang: etwa 50 bis 110 Wörter, außer der Inhalt erfordert "
            "mehr Erklärung."
        )

        if self.conversation and question:
            prompt += "\n\nBisheriger Dialog zu dieser Markierung:"
            for mode, previous_question, previous_answer in self.conversation[-3:]:
                prompt += (
                    f"\n[{mode}] Frage: {previous_question or '(keine)'}"
                    f"\nAntwort: {previous_answer[:1200]}"
                )
            prompt += (
                "\nBeziehe dich nur dann auf diesen Dialog, wenn die aktuelle "
                "Frage eine Nachfrage dazu ist."
            )

        image_data = self._encode_jpeg(focus_image)

        def on_chunk(partial: str) -> None:
            if cancel_event.is_set() or request_id != self.request_id:
                return

            with self.stream_lock:
                self.stream_text = partial
                should_schedule = not self.stream_update_pending
                if should_schedule:
                    self.stream_update_pending = True

            if should_schedule:
                self.post_ui(self._flush_stream, request_id)

        return self.backend.chat(
            prompt,
            [image_data],
            cancel_event=cancel_event,
            on_chunk=on_chunk,
        )


    def _flush_stream(self, request_id: int) -> None:
        with self.stream_lock:
            text = self.stream_text
            self.stream_update_pending = False

        if request_id != self.request_id:
            return

        if text:
            self.panel.show_streaming(text)

        with self.stream_lock:
            newer_text = self.stream_text != text
            if (
                newer_text
                and self.stream_request_id == request_id
                and not self.stream_update_pending
            ):
                self.stream_update_pending = True
                schedule_next = True
            else:
                schedule_next = False

        if schedule_next:
            try:
                self.root.after(
                    STREAM_FLUSH_MS,
                    lambda: self.post_ui(self._flush_stream, request_id),
                )
            except tk.TclError:
                pass

    def _deliver_answer(
        self,
        request_id: int,
        answer: str,
    ) -> None:
        if request_id != self.request_id:
            return

        self.last_answer = answer
        question = self.active_question or ""
        self.conversation.append((self.current_mode, question, answer))
        self.active_question = None
        self.conversation = self.conversation[-MAX_CONVERSATION_TURNS:]
        self.panel.show_answer(answer)
        if AUTO_READ_ALOUD:
            self.speech.speak(answer)

    def _deliver_error(
        self,
        request_id: int,
        message: str,
    ) -> None:
        if request_id == self.request_id:
            self.panel.show_error(message)

    def handle_text_question(self, question: str) -> None:
        # Explizite lokale Aktionen werden vor der KI ausgeführt.
        # Beispiel: „Suche aktuelle Nachrichten zu …“
        try:
            search_query = UserActionRouter.execute(question)
        except Exception as exc:
            self.panel.show_error(str(exc))
            return

        if search_query:
            self.pending_question = None
            self.active_question = None
            self.panel.show_message(
                f"Suche im Standardbrowser: {search_query}"
            )
            return

        question = question.strip()
        if not question:
            return

        # Ohne Markierung darf die App die Frage vormerken. Danach reicht
        # eine einzige Bildschirmmarkierung, um die Frage auszuführen.
        if self.last_marked_image is None or self.last_stroke is None:
            self.pending_question = question
            self.panel.show_message(
                "Frage gespeichert. Markiere jetzt die passende Stelle mit "
                f"{PlatformAdapter.selection_shortcut_label()}."
            )
            return

        self.pending_question = None
        self.active_question = question
        self.start_analysis(
            self.last_marked_image,
            self.last_stroke,
            question,
        )

    # ------------------------------ T / Frage ------------------------------


    def toggle_voice_capture(self) -> None:
        with self.voice_lock:
            if self.voice_active:
                self.voice_stop_event.set()
                self.speech.stop_recording()
                self.panel.show_message(
                    "Aufnahme wird beendet – ich verarbeite deine Frage …"
                )
                return

            self.voice_active = True
            self.voice_stop_event.clear()

        self.speech.cancel_event.clear()
        self.panel.show_listening()

        threading.Thread(
            target=self._record_and_transcribe,
            daemon=True,
            name="Lernhilfe-Voice",
        ).start()

    def _record_and_transcribe(self) -> None:
        try:
            audio = self.speech.record_until_silence()

            if self.speech.record_stop_event.is_set():
                self.post_ui(
                    self.panel.show_message,
                    "Aufnahme beendet.",
                )
                return

            self.post_ui(
                self.panel.show_message,
                "Ich schreibe deine Frage auf …",
            )

            transcript = self.speech.transcribe(audio)

            if not transcript:
                raise RuntimeError(
                    "Ich konnte keine verständliche Frage erkennen. "
                    "Versuch es bitte noch einmal."
                )

            self.post_ui(
                self._handle_transcript,
                transcript,
            )

        except Exception as error:
            message = (
                str(error).strip()
                or "Die Sprachaufnahme konnte nicht gestartet werden."
            )
            self.post_ui(
                self.panel.show_error,
                message,
            )

        finally:
            with self.voice_lock:
                self.voice_active = False
            self.voice_stop_event.clear()
            self.speech.record_stop_event.clear()

    def _handle_transcript(self, transcript: str) -> None:
        self.panel.show_message(f"Verstanden: „{transcript}“")

        if self.last_marked_image is None or self.last_stroke is None:
            self.pending_question = transcript
            self.panel.show_message(
                "Frage gespeichert. Markiere jetzt mit "
                f"{PlatformAdapter.selection_shortcut_label()} "
                "die passende Stelle."
            )
            return

        self.start_analysis(
            self.last_marked_image,
            self.last_stroke,
            transcript,
        )

    # ------------------------- Freisprechmodus -----------------------------

    def toggle_voice_mode(self) -> None:
        """Schaltet einen verständlichen, lokalen Freisprechmodus ein/aus.

        Es wird bewusst kein geheimnisvolles "PC"-Wakeword vorausgesetzt.
        Im Freisprechmodus wartet die App lokal auf Sprache und startet danach
        automatisch eine normale Frageaufnahme.
        """
        if self.voice_mode_active:
            self.voice_mode_stop_event.set()
            self.voice_mode_active = False
            self.panel.set_voice_mode(False)
            self.panel.show_message(
                "Freisprechen ist aus. Das Mikrofon wird nicht mehr dauerhaft "
                "von der Lernhilfe überwacht."
            )
            return

        if not ensure_packages(
            OPTIONAL_PACKAGES["voice"],
            optional=True,
        ):
            self.panel.show_error(
                "Für den Freisprechmodus fehlen Mikrofon-Pakete.\n\n"
                "Die App konnte sie nicht automatisch installieren. "
                "Du kannst weiterhin per Text fragen oder den Sprachfrage-Button verwenden."
            )
            return

        self.voice_mode_active = True
        self.voice_mode_stop_event.clear()
        self.panel.set_voice_mode(True)
        self.panel.show_message(
            "Freisprechen ist aktiv. Die App wartet lokal auf deine Stimme.\n\n"
            "Sobald du sprichst, wird die Frage aufgenommen und danach "
            "wieder auf das nächste Wort gewartet. "
            "Mit dem Freisprech-Button oder "
            f"{PlatformAdapter.voice_mode_shortcut_label()} kannst du es ausschalten."
        )

        threading.Thread(
            target=self._voice_mode_loop,
            daemon=True,
            name="Lernhilfe-HandsFree",
        ).start()

    def _voice_mode_loop(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd

            sample_rate = 16_000
            blocksize = 1280
            threshold = 0.018
            consecutive_voice_blocks = 2

            while not self.voice_mode_stop_event.is_set():
                if time.monotonic() < self.voice_mode_cooldown_until:
                    time.sleep(0.1)
                    continue

                # Während die App spricht oder gerade eine Aufnahme läuft,
                # soll der Freisprechmodus nicht sich selbst triggern.
                if self.speech.active or self.voice_active:
                    time.sleep(0.15)
                    continue

                voice_blocks = 0

                def callback(indata, _frames, _time_info, _status) -> None:
                    nonlocal voice_blocks
                    chunk = indata[:, 0]
                    level = float(np.sqrt(np.mean(np.square(chunk))))
                    if level > threshold:
                        voice_blocks += 1
                    else:
                        voice_blocks = 0

                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=blocksize,
                    callback=callback,
                ):
                    while (
                        not self.voice_mode_stop_event.is_set()
                        and not self.speech.active
                        and not self.voice_active
                    ):
                        if voice_blocks >= consecutive_voice_blocks:
                            self.voice_mode_cooldown_until = time.monotonic() + 1.5
                            self.post_ui(self.toggle_voice_capture)
                            break
                        time.sleep(0.05)

        except Exception as error:
            self.voice_mode_active = False
            self.voice_mode_stop_event.set()
            self.post_ui(self.panel.set_voice_mode, False)
            self.post_ui(
                self.panel.show_error,
                str(error).strip()
                or "Der Freisprechmodus konnte nicht gestartet werden.",
            )
        finally:
            self.voice_mode_active = False
            self.voice_mode_stop_event.set()
            self.post_ui(self.panel.set_voice_mode, False)

    # ---------------------------- Ausgabe ----------------------------------

    def interrupt_current_output(self) -> None:
        self.request_id += 1
        self.analysis_cancel_event.set()
        self.speech.interrupt()

    def repeat_answer(self) -> None:
        if self.speech.active:
            self.speech.interrupt()
            self.panel.show_message("Vorlesen gestoppt.")
        elif self.last_answer:
            self.speech.speak(self.last_answer)

    def _finish_speaking(self) -> None:
        self.panel.repeat_button.configure(text="▶ Vorlesen")
        self.panel.show_message(
            "Erklärung fertig. Du kannst direkt nachfragen."
        )

    def show_help(self) -> None:
        text = (
            "SO FUNKTIONIERT DIE LERNHILFE\n\n"
            f"1. Markieren\n"
            f"{PlatformAdapter.selection_shortcut_label()}: "
            "Bildschirmbereich markieren.\n\n"
            "2. Fragen\n"
            "Schreibe unten eine Frage oder nutze den Sprachfrage-Button. "
            "Ohne Markierung wird die Frage vorgemerkt.\n\n"
            "3. Erklären\n"
            "Die markierte Stelle wird zusammen mit dem Bildschirmkontext "
            "an das lokale Vision-Modell übergeben.\n\n"
            "4. Lernmodus und Nachfragen\n"
            "Wähle Erklären, Hinweis, Schritt für Schritt, Prüfen oder Üben. "
            "Danach kannst du direkt nachfragen; mehrere letzte Dialogschritte "
            "bleiben im Lernkontext.\n\n"
            "5. Freisprechen\n"
            f"{PlatformAdapter.voice_mode_shortcut_label()} schaltet einen "
            "lokalen Freisprechmodus ein/aus. Das ist KEIN geheimnisvolles "
            "Wakeword: Im Freisprechmodus wartet die App auf Sprache und "
            "startet dann automatisch die Aufnahme.\n\n"
            "AKTIONEN\n"
            "Beginnt deine Eingabe mit „Suche …“, öffne ich die Suchanfrage im Standardbrowser.\n\n"
            "TECHNIK\n"
            f"Backend: Ollama • Modell: {self.ollama.active_model}\n"
            "Antworten werden standardmäßig nicht automatisch vorgelesen.\n\n"
            "DATENSCHUTZ\n"
            "Die Bildanalyse läuft über Ollama auf deinem Computer. "
            "Für Sprache werden Mikrofon und lokale Spracherkennung verwendet."
        )
        self.panel.show_settings(text)

    def show_status(self) -> None:
        ollama = PlatformAdapter.find_ollama()
        status = (
            f"System: {platform.system()} {platform.release()}\n"
            f"Python: {platform.python_version()}\n\n"
            f"Ollama: {'gefunden' if ollama else 'nicht gefunden'}\n"
            f"Modell: {self.ollama.active_model}\n\n"
            "Bildanalyse: lokal über Ollama\n"
            f"Freisprechen: {'aktiv' if self.voice_mode_active else 'aus'}"
        )
        self.panel.show_settings(status)

    # ---------------------------- Lebenszyklus -----------------------------

    def shutdown(self) -> None:
        self.voice_mode_stop_event.set()
        self.voice_stop_event.set()
        self.speech.stop_recording()
        self.speech.interrupt()
        self.hotkeys.stop()
        self.ollama.shutdown()

        try:
            self.selector.close()
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self) -> None:
        print(
            f"{APP_NAME} läuft. "
            f"{PlatformAdapter.selection_shortcut_label()} markieren · "
            f"{PlatformAdapter.voice_question_shortcut_label()} Sprachfrage · "
            f"{PlatformAdapter.voice_mode_shortcut_label()} Freisprechen"
        )

        # Kleine Startkarte nur beim ersten Start anzeigen.
        self.panel.show_message(
            "Bereit.\n\n"
            f"1. {PlatformAdapter.selection_shortcut_label()} drücken und "
            "eine unklare Stelle markieren.\n"
            "2. Frage eingeben oder Sprachfrage starten.\n"
            "3. Danach kannst du direkt nachfragen."
        )

        self.root.mainloop()


# ---------------------------------------------------------------------------
# 10. Start
# ---------------------------------------------------------------------------

def validate_configuration() -> None:
    """Prüft statische Konfiguration vor dem Programmstart."""
    if not OLLAMA_MODEL or ":" not in OLLAMA_MODEL:
        raise RuntimeError("OLLAMA_MODEL ist ungültig.")
    if not OLLAMA_BASE_URL.startswith(("http://", "https://")):
        raise RuntimeError("OLLAMA_BASE_URL ist ungültig.")
    if ANSWER_TOKEN_LIMIT <= 0:
        raise RuntimeError("ANSWER_TOKEN_LIMIT muss größer als 0 sein.")
    if OLLAMA_TIMEOUT <= 0 or OLLAMA_START_TIMEOUT <= 0:
        raise RuntimeError("Ollama-Timeouts müssen größer als 0 sein.")


def main() -> None:
    try:
        validate_configuration()
        app = LearningAssistant()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                APP_NAME,
                "Die Lernhilfe konnte nicht gestartet werden.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            root.destroy()
        except Exception:
            print(
                f"{APP_NAME}: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
        raise


if __name__ == "__main__":
    main()
