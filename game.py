#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐰 WACK-A-BUNNY — G PRO LED EDITION
====================================
Whack-a-mole jugado 100% sobre los LEDs per-key de un Logitech G Pro (TKL).

  · Todas las teclas "normales" (números, letras, símbolos, Ñ, Ç, <...) son portales.
  · Un conejo = una tecla que se ilumina en rosa y parpadea cada vez más rápido.
  · Si la pulsas a tiempo → onda expansiva de LEDs por todo el teclado.
  · Teclas especiales = HUD / controles:
        F1-F5 ........ vidas          F9-F12 + PrtSc/ScrLk/Pause ... medidor de combo
        Tab .......... pausa          Esc ... salir          Enter ... revancha (game over)
  · El terminal se pone a pantalla completa y hace de visualizador de stats en tiempo real.

Backends de LEDs
  logitech : Windows + G HUB (usa el SDK legacy de LED que trae G HUB).
             En G HUB → Ajustes → activar "Permitir que juegos y aplicaciones controlen la iluminación".
  openrgb  : Windows/Linux con OpenRGB abierto y el "SDK Server" arrancado (puerto 6742).
  sim      : sin hardware; los LEDs se ven solo en el espejo del dashboard.

Input
  Por defecto usa la lib `keyboard` (hook global por scancode, independiente del layout).
  En Linux necesita root (sudo). Si no está disponible, cae a leer el stdin del terminal.

Uso rápido
  pip install rich keyboard openrgb-python
  python wack_a_bunny.py                 # auto-detecta backend
  python wack_a_bunny.py --backend sim   # probar sin teclado RGB
  python wack_a_bunny.py --demo          # un bot juega solo (modo attract)
  python wack_a_bunny.py --ansi          # layout US/ANSI en vez de ES/ISO
"""
from __future__ import annotations

import argparse
import colorsys
import io
import math
import os
import queue
import random
import shutil
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

try:
    from rich.align import Align
    from rich.console import Console, Group
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:  # pragma: no cover
    sys.exit("Falta 'rich' →  pip install rich")

# ─────────────────────────────── constantes ────────────────────────────────
SC_ESC, SC_TAB, SC_ENTER = 0x01, 0x0F, 0x1C
PINK = (255, 60, 150)
GOLD = (255, 185, 0)
ROW_Y = (0.0, 1.5, 2.5, 3.5, 4.5, 5.5)  # centro vertical de cada fila (en "unidades de tecla")
KB_CENTER = (7.5, 3.5)
F_LIVES = (0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x41, 0x42)          # F1..F8
COMBO_METER = (0x43, 0x44, 0x57, 0x58, 0x137, 0x46, 0x145)          # F9..F12, PrtSc, ScrLk, Pause

Color = tuple  # (r, g, b) floats 0..255


def clamp(v, lo=0.0, hi=255.0):
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def scale(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def hsv(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (r * 255, g * 255, b * 255)


# ─────────────────────────────── layout físico ─────────────────────────────
@dataclass
class Key:
    sc: int          # scancode set-1 (= códigos del SDK de Logitech = evdev en Linux)
    label: str
    x: float         # borde izquierdo en unidades
    y: float         # centro vertical
    w: float
    game: bool       # ¿es un portal de juego?

    @property
    def cx(self) -> float:
        return self.x + self.w / 2


def build_layout(iso: bool = True):
    """Layout TKL del G Pro. Devuelve (keys{sc: Key}, spans[(row, sc, x, w)] para dibujar)."""
    keys: dict[int, Key] = {}
    spans: list[tuple] = []

    def k(sc, label, x, row, w=1.0, game=False):
        keys[sc] = Key(sc, label, x, ROW_Y[row], w, game)
        spans.append((row, sc, x, w))

    # Fila F
    k(0x01, "Esc", 0, 0)
    for i, sc in enumerate(F_LIVES[:4]):
        k(sc, f"F{i + 1}", 2 + i, 0)
    for i, sc in enumerate(F_LIVES[4:]):
        k(sc, f"F{i + 5}", 6.5 + i, 0)
    for i, sc in enumerate(COMBO_METER[:4]):
        k(sc, f"F{i + 9}", 11 + i, 0)
    k(0x137, "PrS", 15.25, 0); k(0x46, "ScL", 16.25, 0); k(0x145, "Pau", 17.25, 0)

    # Fila números
    num = (["º", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "'", "¡"] if iso
           else ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="])
    for i, (sc, lab) in enumerate(zip([0x29, *range(0x02, 0x0E)], num)):
        k(sc, lab, i, 1, game=True)
    k(0x0E, "⌫", 13, 1, 2)
    k(0x152, "Ins", 15.25, 1); k(0x147, "Hom", 16.25, 1); k(0x149, "PgU", 17.25, 1)

    # Fila QWERTY
    k(SC_TAB, "Tab", 0, 2, 1.5)
    top = list("QWERTYUIOP") + (["`", "+"] if iso else ["[", "]"])
    for i, (sc, lab) in enumerate(zip(range(0x10, 0x1C), top)):
        k(sc, lab, 1.5 + i, 2, game=True)
    if iso:
        k(SC_ENTER, "↵", 13.5, 2, 1.5)
    else:
        k(0x2B, "\\", 13.5, 2, 1.5, game=True)
    k(0x153, "Del", 15.25, 2); k(0x14F, "End", 16.25, 2); k(0x151, "PgD", 17.25, 2)

    # Fila ASDF
    k(0x3A, "Blq", 0, 3, 1.75)
    home = list("ASDFGHJKL") + (["Ñ", "´"] if iso else [";", "'"])
    for i, (sc, lab) in enumerate(zip(range(0x1E, 0x29), home)):
        k(sc, lab, 1.75 + i, 3, game=True)
    if iso:
        k(0x2B, "Ç", 12.75, 3, game=True)
        spans.append((3, SC_ENTER, 13.75, 1.25))   # la "L" del Enter ISO
        keys[SC_ENTER].y = 3.0
    else:
        k(SC_ENTER, "↵", 12.75, 3, 2.25)

    # Fila ZXCV
    if iso:
        k(0x2A, "⇧", 0, 4, 1.25); k(0x56, "<", 1.25, 4, game=True)
    else:
        k(0x2A, "⇧", 0, 4, 2.25)
    bot = list("ZXCVBNM") + ([",", ".", "-"] if iso else [",", ".", "/"])
    for i, (sc, lab) in enumerate(zip(range(0x2C, 0x36), bot)):
        k(sc, lab, 2.25 + i, 4, game=True)
    k(0x36, "⇧", 12.25, 4, 2.75); k(0x148, "↑", 16.25, 4)

    # Fila inferior
    k(0x1D, "Ctl", 0, 5, 1.25); k(0x15B, "Win", 1.25, 5, 1.25); k(0x38, "Alt", 2.5, 5, 1.25)
    k(0x39, "", 3.75, 5, 6.25); k(0x138, "AGr", 10, 5, 1.25); k(0x15C, "Fn", 11.25, 5, 1.25)
    k(0x15D, "Mnu", 12.5, 5, 1.25); k(0x11D, "Ctl", 13.75, 5, 1.25)
    k(0x14B, "←", 15.25, 5); k(0x150, "↓", 16.25, 5); k(0x14D, "→", 17.25, 5)
    return keys, spans


def openrgb_names() -> dict[int, list[str]]:
    """Nombres de LED de OpenRGB por posición física (US)."""
    m = {
        0x01: ["Escape"], 0x137: ["Print Screen"], 0x46: ["Scroll Lock"], 0x145: ["Pause/Break", "Pause"],
        0x29: ["`"], 0x0C: ["-"], 0x0D: ["="], 0x0E: ["Backspace"],
        0x152: ["Insert"], 0x147: ["Home"], 0x149: ["Page Up"],
        0x0F: ["Tab"], 0x1A: ["["], 0x1B: ["]"], 0x2B: ["\\ (ANSI)", "#", "\\"],
        0x153: ["Delete"], 0x14F: ["End"], 0x151: ["Page Down"],
        0x3A: ["Caps Lock"], 0x27: [";"], 0x28: ["'"], 0x1C: ["Enter", "Enter (ISO)"],
        0x2A: ["Left Shift"], 0x56: ["\\ (ISO)", "ISO \\"], 0x33: [","], 0x34: ["."], 0x35: ["/"],
        0x36: ["Right Shift"], 0x148: ["Up Arrow"],
        0x1D: ["Left Control"], 0x15B: ["Left Windows"], 0x38: ["Left Alt"], 0x39: ["Space"],
        0x138: ["Right Alt"], 0x15C: ["Right Windows", "Right Fn", "Fn"], 0x15D: ["Menu"],
        0x11D: ["Right Control"], 0x14B: ["Left Arrow"], 0x150: ["Down Arrow"], 0x14D: ["Right Arrow"],
    }
    for i, sc in enumerate(F_LIVES + COMBO_METER[:4]):
        m[sc] = [f"F{i + 1}"]
    for i, sc in enumerate(range(0x02, 0x0C)):
        m[sc] = [str((i + 1) % 10)]
    for row, start in (("QWERTYUIOP", 0x10), ("ASDFGHJKL", 0x1E), ("ZXCVBNM", 0x2C)):
        for i, ch in enumerate(row):
            m[start + i] = [ch]
    return m


# ─────────────────────────────── backends LED ──────────────────────────────
class NullBackend:
    name = "sim (solo pantalla)"

    def start(self): pass
    def set_frame(self, frame): pass
    def stop(self): pass


class LogitechBackend:
    """SDK legacy de LED de Logitech (lo instala G HUB). Solo Windows, Python 64-bit."""
    name = "Logitech G HUB SDK"

    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("solo Windows")
        import ctypes
        here = os.path.dirname(os.path.abspath(__file__))
        cands = [
            os.environ.get("LOGI_LED_DLL", ""),
            r"C:\Program Files\LGHUB\sdk_legacy_led_x64.dll",
            r"C:\Program Files\LGHUB\sdks\sdk_legacy_led_x64.dll",
            os.path.join(here, "LogitechLedEnginesWrapper.dll"),
            "LogitechLedEnginesWrapper.dll",
        ]
        self.dll, errs = None, []
        for p in cands:
            if not p or (os.path.isabs(p) and not os.path.exists(p)):
                continue
            try:
                self.dll = ctypes.CDLL(p)
                break
            except OSError as e:
                errs.append(f"{p}: {e}")
        if self.dll is None:
            raise RuntimeError("no encuentro la DLL del SDK (¿G HUB instalado? o define LOGI_LED_DLL)")
        c_int, c_bool = ctypes.c_int, ctypes.c_bool
        for fn, args in (("LogiLedInit", []), ("LogiLedSetTargetDevice", [c_int]),
                         ("LogiLedSaveCurrentLighting", []), ("LogiLedSetLighting", [c_int] * 3),
                         ("LogiLedSetLightingForKeyWithScanCode", [c_int] * 4),
                         ("LogiLedRestoreLighting", []), ("LogiLedShutdown", [])):
            f = getattr(self.dll, fn)
            f.argtypes, f.restype = args, (None if fn == "LogiLedShutdown" else c_bool)
        self.cache: dict[int, tuple] = {}

    def start(self):
        if not self.dll.LogiLedInit():
            raise RuntimeError("LogiLedInit falló (¿G HUB abierto y control de iluminación por apps activado?)")
        time.sleep(0.25)
        self.dll.LogiLedSetTargetDevice(0x04)          # LOGI_DEVICETYPE_PERKEY_RGB
        self.dll.LogiLedSaveCurrentLighting()
        self.dll.LogiLedSetLighting(0, 0, 0)

    def set_frame(self, frame):
        fn = self.dll.LogiLedSetLightingForKeyWithScanCode
        for sc, (r, g, b) in frame.items():
            p = (int(r * 100 / 255 + 0.5), int(g * 100 / 255 + 0.5), int(b * 100 / 255 + 0.5))
            if self.cache.get(sc) != p:               # solo mandamos lo que cambia
                self.cache[sc] = p
                fn(sc, *p)

    def stop(self):
        try:
            self.dll.LogiLedRestoreLighting()
            self.dll.LogiLedShutdown()
        except Exception:
            pass


class OpenRGBBackend:
    def __init__(self, keys, host="127.0.0.1", port=6742, name_filter=None):
        from openrgb import OpenRGBClient
        from openrgb.utils import DeviceType, RGBColor
        self.RGB = RGBColor
        self.client = OpenRGBClient(host, port, name="wack-a-bunny")
        devs = [d for d in self.client.devices if d.type == DeviceType.KEYBOARD]
        if name_filter:
            devs = [d for d in devs if name_filter.lower() in d.name.lower()]
        else:  # preferimos un G Pro si hay varios
            devs.sort(key=lambda d: "pro" not in d.name.lower())
        if not devs:
            raise RuntimeError("OpenRGB no ve ningún teclado")
        self.dev = devs[0]
        self.name = f"OpenRGB → {self.dev.name}"
        norm = lambda s: s.lower().replace("key:", "").strip()
        led_idx = {norm(led.name): i for i, led in enumerate(self.dev.leds)}
        self.idx: dict[int, int] = {}
        for sc, cands in openrgb_names().items():
            if sc not in keys:
                continue
            for c in cands:
                if norm(c) in led_idx:
                    self.idx[sc] = led_idx[norm(c)]
                    break
        self.colors = [RGBColor(0, 0, 0) for _ in self.dev.leds]

    def start(self):
        try:
            self.dev.set_mode("direct")
        except Exception:
            pass

    def set_frame(self, frame):
        for sc, i in self.idx.items():
            r, g, b = frame.get(sc, (0, 0, 0))
            self.colors[i] = self.RGB(int(r), int(g), int(b))
        self.dev.set_colors(self.colors, fast=True)

    def stop(self):
        try:
            self.dev.set_colors([self.RGB(40, 40, 40) for _ in self.dev.leds], fast=True)
            self.client.disconnect()
        except Exception:
            pass


def make_backend(args, keys):
    order = {"auto": ["logitech", "openrgb"] if os.name == "nt" else ["openrgb"],
             "logitech": ["logitech"], "openrgb": ["openrgb"], "sim": []}[args.backend]
    errs = []
    for name in order:
        try:
            be = (LogitechBackend() if name == "logitech"
                  else OpenRGBBackend(keys, args.openrgb_host, args.openrgb_port, args.device))
            be.start()
            return be, errs
        except Exception as e:
            errs.append(f"{name}: {e}")
    return NullBackend(), errs


# ─────────────────────────────── input ─────────────────────────────────────
class InputManager:
    """Hook global por scancode (lib keyboard) + drenado del stdin para que el terminal no se ensucie."""

    def __init__(self, keys, force_stdin=False):
        self.q: queue.SimpleQueue = queue.SimpleQueue()
        self._kb = None
        self._down: set[int] = set()
        self._stop = False
        self.cmap = {k.label.lower(): sc for sc, k in keys.items() if k.game}
        self.source = "stdin"
        if not force_stdin:
            try:
                import keyboard
                keyboard.hook(self._on_kb)
                self._kb = keyboard
                self.source = "hook global (scancodes)"
            except Exception as e:
                self.source = f"stdin (fallback: {type(e).__name__})"
        threading.Thread(target=self._stdin_loop, daemon=True).start()

    def _on_kb(self, e):
        sc = e.scan_code
        if e.event_type == "down":
            if sc in self._down:            # ignorar autorepeat
                return
            self._down.add(sc)
            self.q.put((sc, time.perf_counter()))
        else:
            self._down.discard(sc)

    def _char(self, ch):
        if self._kb:                        # el hook ya manda; el stdin solo se drena
            return
        sc = {"\x1b": SC_ESC, "\t": SC_TAB, "\r": SC_ENTER, "\n": SC_ENTER}.get(ch) or self.cmap.get(ch.lower())
        if sc:
            self.q.put((sc, time.perf_counter()))

    def _stdin_loop(self):
        try:
            if os.name == "nt":
                import msvcrt
                while not self._stop:
                    if msvcrt.kbhit():
                        ch = msvcrt.getwch()
                        if ch in ("\x00", "\xe0"):
                            msvcrt.getwch()
                            continue
                        self._char(ch)
                    else:
                        time.sleep(0.004)
            else:
                import select
                fd = sys.stdin.fileno()
                while not self._stop:
                    r, _, _ = select.select([fd], [], [], 0.05)
                    if not r:
                        continue
                    data = os.read(fd, 64).decode("utf-8", errors="ignore")
                    if data.startswith("\x1b") and len(data) > 1:
                        continue                  # secuencia de escape (flechas, etc.)
                    for ch in data:
                        self._char(ch)
        except Exception:
            pass

    def drain(self):
        out = []
        while True:
            try:
                out.append(self.q.get_nowait())
            except queue.Empty:
                return out

    def stop(self):
        self._stop = True
        if self._kb:
            try:
                self._kb.unhook_all()
            except Exception:
                pass


class RawTerminal:
    def __init__(self):
        self.old = None

    def enter(self):
        if os.name != "nt" and sys.stdin.isatty():
            import termios
            import tty
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)          # sin eco, sin buffer de línea

    def exit(self):
        if self.old is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
            self.old = None


class FullScreen:
    def __init__(self, enabled=True):
        self.enabled, self.how = enabled, None

    def _alt_enter(self):
        import ctypes
        u = ctypes.windll.user32
        u.keybd_event(0x12, 0, 0, 0); u.keybd_event(0x0D, 0, 0, 0)
        u.keybd_event(0x0D, 0, 2, 0); u.keybd_event(0x12, 0, 2, 0)

    def enter(self):
        if not self.enabled:
            return
        try:
            if os.name == "nt":                        # Windows Terminal y conhost: Alt+Enter
                self._alt_enter(); self.how = "altenter"
            elif shutil.which("wmctrl"):
                subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,fullscreen"], check=False)
                self.how = "wmctrl"
            elif shutil.which("xdotool"):
                subprocess.run(["xdotool", "key", "F11"], check=False); self.how = "xdotool"
        except Exception:
            self.how = None

    def exit(self):
        try:
            if self.how == "altenter":
                self._alt_enter()
            elif self.how == "wmctrl":
                subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "remove,fullscreen"], check=False)
            elif self.how == "xdotool":
                subprocess.run(["xdotool", "key", "F11"], check=False)
        except Exception:
            pass


# ─────────────────────────────── juego ─────────────────────────────────────
@dataclass
class Bunny:
    sc: int
    t0: float
    life: float
    golden: bool = False


@dataclass
class Wave:
    x: float
    y: float
    t0: float
    color: Color
    speed: float = 22.0
    thick: float = 1.3
    max_r: float = 22.0
    rainbow: bool = False
    gain: float = 1.0


@dataclass
class Flash:
    sc: int
    t0: float
    dur: float
    color: Color


class Stats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.score = self.hits = self.misses = self.escapes = self.golden = 0
        self.combo = self.max_combo = 0
        self.best_ms = math.inf
        self.reactions: deque = deque(maxlen=1000)
        self.spark: deque = deque(maxlen=48)
        self.key_hits = defaultdict(int)
        self.key_miss = defaultdict(int)
        self.play_time = 0.0
        self.events: deque = deque(maxlen=12)

    def accuracy(self):
        n = self.hits + self.misses + self.escapes
        return 100.0 * self.hits / n if n else 0.0

    def hpm(self):
        return self.hits / (self.play_time / 60) if self.play_time > 3 else 0.0

    def react_stats(self):
        if not self.reactions:
            return None
        xs = sorted(self.reactions)
        n = len(xs)
        return {"avg": sum(xs) / n, "best": xs[0], "p50": xs[n // 2], "p90": xs[min(n - 1, int(n * 0.9))]}


class Game:
    def __init__(self, keys, lives=5, rng=None, now=None):
        self.keys = keys
        self.game_keys = [sc for sc, k in keys.items() if k.game]
        self.lives_max = max(1, min(lives, len(F_LIVES)))
        self.rng = rng or random.Random()
        self.quit = False
        self.stats = Stats()
        self.new_game(time.perf_counter() if now is None else now)

    # ── ciclo de vida ──
    def new_game(self, now):
        self.stats.reset()
        self.lives, self.level = self.lives_max, 1
        self.bunnies: dict[int, Bunny] = {}
        self.waves: list[Wave] = []
        self.flashes: list[Flash] = []
        self.state, self.t_state, self.cd_step = "countdown", now, -1
        self.next_spawn = now
        self.pause_t = 0.0
        self.last_now = now
        self.log("Nueva partida — prepárate 🫡", "cyan")

    def log(self, msg, style="white"):
        self.stats.events.append((self.stats.play_time, msg, style))

    def params(self):
        """(vida del conejo s, intervalo de spawn s, conejos simultáneos) según nivel."""
        L = self.level
        return max(0.42, 1.6 * 0.9 ** (L - 1)), max(0.22, 1.05 * 0.88 ** (L - 1)), min(1 + (L - 1) // 2, 5)

    # ── input ──
    def on_key(self, sc, now):
        if sc == SC_ESC:
            self.quit = True
        elif sc == SC_TAB:
            self.toggle_pause(now)
        elif sc == SC_ENTER:
            if self.state == "over":
                self.new_game(now)
        else:
            k = self.keys.get(sc)
            if self.state == "playing" and k is not None and k.game:
                self.whack(sc, now)

    def toggle_pause(self, now):
        if self.state == "playing":
            self.state, self.pause_t = "paused", now
            self.log("Pausa ⏸", "yellow")
        elif self.state == "paused":
            d = now - self.pause_t
            for obj in (*self.bunnies.values(), *self.waves, *self.flashes):
                obj.t0 += d
            self.next_spawn += d
            self.state = "playing"
            self.log("Reanudado ▶", "green")

    def whack(self, sc, now):
        s, k = self.stats, self.keys[sc]
        b = self.bunnies.pop(sc, None)
        if b is None:                                          # fallo: no había conejo
            s.misses += 1; s.key_miss[sc] += 1
            if s.combo >= 5:
                self.log(f"Combo x{s.combo} roto 💔", "red")
            s.combo = 0
            s.score = max(0, s.score - 25)
            self.flashes.append(Flash(sc, now, 0.3, (255, 0, 0)))
            self.waves.append(Wave(k.cx, k.y, now, (160, 0, 0), speed=10, thick=1.0, max_r=3.0, gain=0.8))
            return

        react = max(0.0, now - b.t0)
        frac = min(1.0, react / b.life)
        s.combo += 1
        s.max_combo = max(s.max_combo, s.combo)
        mult = 1 + min(s.combo // 5, 7)
        pts = int((100 + 100 * (1 - frac)) * mult * (5 if b.golden else 1))
        s.score += pts; s.hits += 1; s.golden += int(b.golden)
        ms = react * 1000
        s.reactions.append(ms); s.spark.append(ms); s.key_hits[sc] += 1

        c = s.combo
        col = GOLD if b.golden else (0, 200, 255) if c < 5 else (170, 0, 255) if c < 10 \
            else (255, 170, 0) if c < 20 else (255, 255, 255)
        max_r = 22 if (c >= 5 or b.golden) else 15
        self.waves.append(Wave(k.cx, k.y, now, col, speed=24, thick=1.4, max_r=max_r,
                               rainbow=(c >= 20 and not b.golden)))
        if c >= 10 or b.golden:                               # eco de la onda
            echo = (255, 255, 200) if b.golden else (255, 0, 140)
            self.waves.append(Wave(k.cx, k.y, now + 0.12, echo, speed=20, thick=1.0, max_r=max_r, gain=0.6))
        self.flashes.append(Flash(sc, now, 0.15, (255, 255, 255)))

        if b.golden:
            self.log(f"🌟 Conejo DORADO en [{k.label}] +{pts}", "bold gold1")
        elif c in (10, 25, 50, 100, 200):
            self.log(f"Combo x{c} 🔥", "bold magenta")
        if ms < s.best_ms:
            if s.hits > 1:
                self.log(f"Récord de reacción: {ms:.0f} ms 🏎️", "bold green")
            s.best_ms = ms
        lvl = 1 + s.hits // 10
        if lvl > self.level:
            self.level = lvl
            self.log(f"Nivel {lvl} ⚡ más rápido", "bold cyan")
            self.waves.append(Wave(*KB_CENTER, now + 0.05, (255, 255, 255), speed=30, thick=1.8,
                                   max_r=14, rainbow=True, gain=0.9))

    def escape(self, sc, b, now):
        s, k = self.stats, self.keys[sc]
        if b.golden:                                          # el dorado no quita vida
            self.flashes.append(Flash(sc, now, 0.4, GOLD))
            self.log(f"El dorado se piró de [{k.label}] 🫥", "gold1")
            return
        s.escapes += 1
        s.combo = 0
        s.score = max(0, s.score - 50)
        self.lives -= 1
        self.flashes.append(Flash(sc, now, 0.5, (255, 80, 0)))
        self.waves.append(Wave(k.cx, k.y, now, (120, 20, 0), speed=12, thick=1.0, max_r=4, gain=0.8))
        self.log(f"Se escapó en [{k.label}] — vidas {self.lives}", "dark_orange")
        if self.lives <= 0:
            self.state, self.t_state = "over", now
            self.bunnies.clear()
            self.waves.append(Wave(*KB_CENTER, now, (255, 0, 0), speed=18, thick=2.5, max_r=20))
            self.log(f"GAME OVER 💀 score {s.score}", "bold red")

    def spawn(self, now, life):
        recent = {f.sc for f in self.flashes}
        free = [sc for sc in self.game_keys if sc not in self.bunnies]
        choices = [sc for sc in free if sc not in recent] or free
        if not choices:
            return
        sc = self.rng.choice(choices)
        golden = self.level >= 2 and self.rng.random() < 0.06
        self.bunnies[sc] = Bunny(sc, now, life * (0.85 if golden else 1.0), golden)

    # ── tick ──
    def update(self, now):
        dt, self.last_now = now - self.last_now, now
        if self.state == "countdown":
            step = int((now - self.t_state) / 0.75)
            while self.cd_step < step and self.state == "countdown":
                self.cd_step += 1
                if self.cd_step < 3:                          # 3 · 2 · 1 en las teclas numéricas
                    k = self.keys[(0x04, 0x03, 0x02)[self.cd_step]]
                    self.flashes.append(Flash(k.sc, now, 0.7, (0, 255, 90)))
                    self.waves.append(Wave(k.cx, k.y, now, (0, 160, 60), speed=14, thick=1.2, max_r=6))
                else:                                         # GO desde la G
                    g = self.keys[0x22]
                    self.waves.append(Wave(g.cx, g.y, now, (255, 255, 255), speed=26, thick=2.0,
                                           max_r=22, rainbow=True))
                    self.state, self.next_spawn = "playing", now + 0.35
                    self.log("GO! 🐇💨", "bold green")
        elif self.state == "playing":
            self.stats.play_time += dt
            for sc, b in list(self.bunnies.items()):
                if now - b.t0 >= b.life:
                    del self.bunnies[sc]
                    self.escape(sc, b, now)
                    if self.state != "playing":
                        break
            if self.state == "playing":
                life, interval, conc = self.params()
                if not self.bunnies:
                    self.next_spawn = min(self.next_spawn, now + 0.3)
                if now >= self.next_spawn and len(self.bunnies) < conc:
                    self.spawn(now, life)
                    self.next_spawn = now + interval * self.rng.uniform(0.6, 1.3)
        if self.state != "paused":
            self.waves = [w for w in self.waves if (now - w.t0) * w.speed < w.max_r + w.thick]
            self.flashes = [f for f in self.flashes if now - f.t0 < f.dur]

    # ── LEDs ──
    def led_frame(self, now) -> dict[int, Color]:
        st, out = self.state, {}
        for sc, k in self.keys.items():                       # fondo "respirando"
            if st == "paused":
                v = 0.3 + 0.2 * math.sin(now * 2.2); c = (255 * v, 120 * v, 0)
            elif st == "over":
                v = 0.18 + 0.12 * math.sin(now * 1.4 - k.cx * 0.35); c = (200 * v, 0, 12 * v)
            elif k.game:
                v = 0.5 + 0.5 * math.sin(now * 1.6 - k.cx * 0.45 + k.y * 0.7); c = (30 + 30 * v, 0, 55 + 45 * v)
            else:
                v = 0.5 + 0.5 * math.sin(now * 1.1 + k.cx * 0.2); c = (0, 6 + 10 * v, 30 + 25 * v)
            out[sc] = c

        if st != "over":                                      # HUD: vidas + medidor de combo
            for i in range(self.lives_max):
                out[F_LIVES[i]] = (255, 0, 40) if i < self.lives else (25, 0, 0)
            fill = min(self.stats.combo / 35, 1.0) * len(COMBO_METER)
            for i, sc in enumerate(COMBO_METER):
                a = clamp(fill - i, 0.0, 1.0)
                out[sc] = scale(mix((0, 200, 255), (255, 190, 0), i / (len(COMBO_METER) - 1)), a) if a > 0 \
                    else (8, 8, 12)
            out[SC_TAB] = (255, 130, 0) if (st == "paused" and int(now * 3) % 2) else (60, 35, 0)
        else:
            v = 0.5 + 0.5 * math.sin(now * 4)
            out[SC_ENTER] = (0, 255 * v, 80 * v)
        out[SC_ESC] = (90 + 40 * math.sin(now * 2), 0, 0)

        for w in self.waves:                                  # ondas expansivas (aditivas)
            r = (now - w.t0) * w.speed
            if r < 0:
                continue
            fade = max(0.0, 1 - r / w.max_r) * w.gain
            if fade <= 0:
                continue
            for sc, k in self.keys.items():
                d = math.hypot(k.cx - w.x, (k.y - w.y) * 1.15)
                i = 1 - abs(d - r) / w.thick
                if i > 0:
                    col = hsv(d * 0.08 - now * 0.6) if w.rainbow else w.color
                    out[sc] = add(out[sc], scale(col, i * fade))

        if st == "playing":                                   # conejos encima de todo
            for sc, b in self.bunnies.items():
                age = now - b.t0
                left = max(0.0, 1 - age / b.life)
                if age < 0.07:
                    out[sc] = (255, 255, 255)
                elif b.golden:
                    v = 0.65 + 0.35 * math.sin(age * 18)
                    out[sc] = scale(mix(GOLD, (255, 255, 200), 0.5 + 0.5 * math.sin(age * 9)), v)
                else:
                    v = 0.62 + 0.38 * math.sin(age * (4 + 16 * (1 - left)))   # parpadea más rápido al final
                    out[sc] = scale(mix(PINK, (255, 10, 30), (1 - left) ** 2), v)

        for f in self.flashes:
            a = 1 - (now - f.t0) / f.dur
            if 0 < a <= 1:
                out[f.sc] = mix(out[f.sc], f.color, a)
        return {sc: (clamp(c[0]), clamp(c[1]), clamp(c[2])) for sc, c in out.items()}


class DemoBot:
    """Jugador automático para el modo --demo y el selftest."""

    def __init__(self, rng, skill=0.9):
        self.rng, self.skill, self.plan = rng, skill, {}

    def step(self, g: Game, now):
        if g.state != "playing":
            self.plan.clear()
            return
        for sc, b in g.bunnies.items():
            if sc not in self.plan:
                hit_t = b.t0 + self.rng.uniform(0.17, 0.65) if self.rng.random() < self.skill else math.inf
                self.plan[sc] = (b.t0, hit_t)
        for sc, (t0, hit_t) in list(self.plan.items()):
            b = g.bunnies.get(sc)
            if b is None or b.t0 != t0:
                del self.plan[sc]
            elif now >= hit_t:
                del self.plan[sc]
                g.on_key(sc, now)
        if self.rng.random() < 0.004:
            g.on_key(self.rng.choice(g.game_keys), now)


# ─────────────────────────────── dashboard ─────────────────────────────────
BLOCKS = "▁▂▃▄▅▆▇█"
FONT = {
    "0": ["███", "█ █", "█ █", "█ █", "███"], "1": [" █ ", "██ ", " █ ", " █ ", "███"],
    "2": ["███", "  █", "███", "█  ", "███"], "3": ["███", "  █", "███", "  █", "███"],
    "4": ["█ █", "█ █", "███", "  █", "  █"], "5": ["███", "█  ", "███", "  █", "███"],
    "6": ["███", "█  ", "███", "█ █", "███"], "7": ["███", "  █", "  █", "  █", "  █"],
    "8": ["███", "█ █", "███", "█ █", "███"], "9": ["███", "█ █", "███", "  █", "███"],
}


@dataclass
class Ctx:
    backend: str
    input_src: str
    led_fps: float = 0.0
    frame: dict = field(default_factory=dict)


def big(s, style):
    rows = [""] * 5
    for ch in s:
        glyph = FONT.get(ch, ["   "] * 5)
        for i in range(5):
            rows[i] += glyph[i] + " "
    return Text("\n".join(rows), style=style)


def display_rgb(c):
    # los LEDs brillan, la pantalla no: un poco de gamma para que el espejo se parezca
    return tuple(int(255 * (clamp(v) / 255) ** 0.55) for v in c)


def render_keyboard(keys, spans, colors, labels=None) -> Text:
    rows = [[] for _ in ROW_Y]
    for row, sc, x, w in spans:
        rows[row].append((x, sc, w))
    out = Text(no_wrap=True, overflow="crop")
    for ri, row in enumerate(rows):
        row.sort(key=lambda t: t[0])
        col = 0
        for x, sc, w in row:
            start, width = int(round(x * 4)), max(2, int(round(w * 4)) - 1)
            if start > col:
                out.append(" " * (start - col))
                col = start
            r, g, b = display_rgb(colors.get(sc, (0, 0, 0)))
            lab = ((labels or {}).get(sc) or keys[sc].label)[:width].center(width)
            fg = "black" if 0.299 * r + 0.587 * g + 0.114 * b > 140 else "white"
            out.append(lab, style=f"bold {fg} on rgb({r},{g},{b})")
            out.append(" ")
            col = start + width + 1
        if ri < len(rows) - 1:
            out.append("\n\n" if ri == 0 else "\n")
    return out


def heat_colors(g: Game):
    s = g.stats
    mx = max(s.key_hits.values(), default=0)
    cols, labels = {}, {}
    for sc, k in g.keys.items():
        h, m = s.key_hits.get(sc, 0), s.key_miss.get(sc, 0)
        if not k.game:
            cols[sc] = (14, 14, 20)
        elif h == 0 and m == 0:
            cols[sc] = (18, 18, 40)
        else:
            t = h / mx if mx else 0
            cols[sc] = hsv(0.66 - 0.66 * t, 0.9, 0.3 + 0.7 * t)
            labels[sc] = ("✗" if h == 0 else str(h)) if h < 100 else "99+"
    return cols, labels


def build_dashboard(g: Game, ctx: Ctx, spans):
    s = g.stats
    badge = {"countdown": ("⏳ READY", "bold black on cyan"), "playing": ("▶ PLAYING", "bold black on green3"),
             "paused": ("⏸ PAUSA", "bold black on yellow"), "over": ("💀 GAME OVER", "bold white on red3")}[g.state]
    t = int(s.play_time)
    head = Text.assemble(("🐰 WACK-A-BUNNY ", "bold magenta"), ("// G PRO LED EDITION   ", "bold white"),
                         (f" {badge[0]} ", badge[1]), "   ", (f"⏱ {t // 60:02d}:{t % 60:02d}", "bold"),
                         "   ", (f"💡 {ctx.backend} @ {ctx.led_fps:.0f} fps", "grey70"),
                         "   ", (f"⌨ {ctx.input_src}", "grey70"))

    # stats
    if g.state == "countdown":
        top = big(str(max(1, 3 - max(0, g.cd_step))), "bold cyan")
    else:
        top = big(str(s.score), "bold gold1")
    rs = s.react_stats()
    lives = Text("♥ " * g.lives, style="bold red") + Text("♡ " * (g.lives_max - g.lives), style="grey35")
    tb = Table.grid(padding=(0, 2))
    tb.add_column(style="grey70", justify="right"); tb.add_column()
    tb.add_row("Vidas", lives)
    tb.add_row("Nivel", Text(f"{g.level}   (vida conejo {g.params()[0] * 1000:.0f} ms)", style="bold cyan"))
    tb.add_row("Combo", Text(f"{s.combo}  ·  max {s.max_combo}  ·  x{1 + min(s.combo // 5, 7)}", style="bold magenta"))
    tb.add_row("Aciertos", Text(str(s.hits), style="bold green3"))
    tb.add_row("Fallos", Text(str(s.misses), style="bold red"))
    tb.add_row("Escapados", Text(str(s.escapes), style="bold dark_orange"))
    tb.add_row("Dorados 🌟", Text(str(s.golden), style="bold gold1"))
    tb.add_row("Precisión", Text(f"{s.accuracy():.1f} %", style="bold"))
    tb.add_row("Hits/min", Text(f"{s.hpm():.1f}", style="bold"))
    tb.add_row("Reacción", Text(f"avg {rs['avg']:.0f} · best {rs['best']:.0f} · p90 {rs['p90']:.0f} ms", style="bold")
               if rs else Text("—", style="grey50"))
    stats_title = "GAME OVER · [Enter] revancha" if g.state == "over" else "STATS"
    stats_panel = Panel(Group(Align.center(top), Text(""), tb), title=stats_title,
                        border_style="red3" if g.state == "over" else "gold1")

    leds = Panel(Align.center(render_keyboard(g.keys, spans, ctx.frame), vertical="middle"),
                 title="LED MIRROR · live", border_style="magenta")
    hc, hl = heat_colors(g)
    heat = Panel(Align.center(render_keyboard(g.keys, spans, hc, hl), vertical="middle"),
                 title="HEATMAP · conejos cazados por tecla", border_style="blue")

    # reacción
    rt = Text()
    vals = list(s.spark)
    if vals:
        lo, hi = min(vals), max(vals)
        span = max(1.0, hi - lo)
        rt.append("Últimas reacciones (ms)\n", "grey70")
        for v in vals:
            rt.append(BLOCKS[int((v - lo) / span * 7)], "green3" if v < 300 else "yellow" if v < 500 else "red")
        rt.append(f"\n{lo:.0f} … {hi:.0f} ms\n\n", "grey50")
        xs = list(s.reactions)
        for name, a, b in (("<250", 0, 250), ("250-350", 250, 350), ("350-500", 350, 500),
                           ("500-700", 500, 700), ("700+", 700, 1e9)):
            c = sum(1 for x in xs if a <= x < b)
            rt.append(f"{name:>8} ", "grey70"); rt.append("█" * int(18 * c / len(xs)), "magenta")
            rt.append(f" {c}\n", "grey50")
    else:
        rt.append("\nCaza un conejo pa' empezar 🐇", "grey50")
    react = Panel(rt, title="REACTION TIME", border_style="green3")

    lg = Text()
    for pt, msg, style in list(s.events)[-10:]:
        lg.append(f"{int(pt) // 60:02d}:{int(pt) % 60:02d} ", "grey50"); lg.append(msg + "\n", style)
    log = Panel(lg, title="EVENTOS", border_style="grey50")

    foot = Text.assemble(("[Esc]", "bold red"), " salir   ", ("[Tab]", "bold yellow"), " pausa   ",
                         ("[Enter]", "bold green"), " revancha   ·   letras, números y símbolos = portales 🐇   ·   ",
                         ("F1-F5", "bold"), " vidas   ", ("F9→Pause", "bold"), " combo", style="grey70")

    lay = Layout()
    lay.split_column(Layout(Panel(head, border_style="magenta"), size=3), Layout(name="mid", ratio=3),
                     Layout(name="bot", ratio=2), Layout(foot, size=1))
    lay["mid"].split_row(Layout(stats_panel, ratio=2, minimum_size=40), Layout(leds, ratio=3, minimum_size=79))
    lay["bot"].split_row(Layout(heat, ratio=3, minimum_size=79), Layout(react, ratio=2), Layout(log, ratio=2))
    return lay


# ─────────────────────────────── main ──────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="Wack-a-Bunny en los LEDs de un Logitech G Pro")
    p.add_argument("--backend", choices=["auto", "logitech", "openrgb", "sim"], default="auto")
    p.add_argument("--ansi", action="store_true", help="layout US/ANSI (por defecto ES/ISO)")
    p.add_argument("--lives", type=int, default=5)
    p.add_argument("--fps", type=float, default=40, help="refresco de LEDs")
    p.add_argument("--ui-fps", type=float, default=15, help="refresco del dashboard")
    p.add_argument("--demo", action="store_true", help="un bot juega solo")
    p.add_argument("--no-fullscreen", action="store_true")
    p.add_argument("--stdin-input", action="store_true", help="no usar hook global; leer del terminal")
    p.add_argument("--openrgb-host", default="127.0.0.1")
    p.add_argument("--openrgb-port", type=int, default=6742)
    p.add_argument("--device", help="filtro por nombre del teclado en OpenRGB")
    p.add_argument("--list-leds", action="store_true", help="lista LEDs de OpenRGB y su mapeo")
    p.add_argument("--selftest", type=float, default=0, help=argparse.SUPPRESS)
    return p.parse_args()


def list_leds(args, keys):
    be = OpenRGBBackend(keys, args.openrgb_host, args.openrgb_port, args.device)
    inv = {i: sc for sc, i in be.idx.items()}
    print(be.name)
    for i, led in enumerate(be.dev.leds):
        print(f"{i:3d}  {led.name:<28} {'→ ' + keys[inv[i]].label if i in inv else '(sin mapear)'}")
    miss = [k.label or 'Space' for sc, k in keys.items() if sc not in be.idx]
    print("\nTeclas del layout sin LED:", ", ".join(miss) or "ninguna ✅")


def selftest(args, keys, spans):
    rng = random.Random(7)
    g = Game(keys, args.lives, rng, now=0.0)
    bot, t, frames, frame = DemoBot(rng), 0.0, 0, {}
    while t < args.selftest:
        t += 1 / 40
        bot.step(g, t)
        if g.state == "over" and t - g.t_state > 3:
            g.new_game(t)
        g.update(t)
        frame = g.led_frame(t)
        frames += 1
        assert all(0 <= v <= 255 for c in frame.values() for v in c)
    con = Console(width=200, height=48, record=True, file=io.StringIO(), color_system="truecolor")
    con.print(build_dashboard(g, Ctx("selftest", "bot", 40.0, frame), spans))
    print(con.export_text())
    print(f"frames={frames} hits={g.stats.hits} misses={g.stats.misses} escapes={g.stats.escapes} "
          f"level={g.level} score={g.stats.score}")


def main():
    args = parse_args()
    keys, spans = build_layout(iso=not args.ansi)
    if args.selftest:
        return selftest(args, keys, spans)
    if args.list_leds:
        return list_leds(args, keys)

    backend, errs = make_backend(args, keys)
    fs, raw = FullScreen(not args.no_fullscreen), RawTerminal()
    inp, game = None, None
    try:
        fs.enter()
        if fs.how:
            time.sleep(0.35)                                 # deja que la ventana cambie de tamaño
        raw.enter()
        inp = InputManager(keys, force_stdin=args.stdin_input)
        game = Game(keys, args.lives)
        for e in errs:
            game.log(f"⚠ {e}"[:80], "yellow")
        if isinstance(backend, NullBackend):
            game.log("Modo sim: LEDs solo en pantalla 👀", "yellow")
        bot = DemoBot(game.rng) if args.demo else None
        ctx = Ctx(backend.name, inp.source)
        led_dt, ui_dt = 1 / args.fps, 1 / args.ui_fps
        next_led = next_ui = fps_t = time.perf_counter()
        fps_n = 0
        with Live(console=Console(), screen=True, auto_refresh=False,
                  redirect_stdout=False, redirect_stderr=False) as live:
            while not game.quit:
                now = time.perf_counter()
                for sc, t_ev in inp.drain():
                    game.on_key(sc, t_ev)
                if bot:
                    bot.step(game, now)
                    if game.state == "over" and now - game.t_state > 4:
                        game.new_game(now)
                game.update(now)
                if now >= next_led:
                    ctx.frame = game.led_frame(now)
                    backend.set_frame(ctx.frame)
                    fps_n += 1
                    next_led = max(next_led + led_dt, now)
                if now - fps_t >= 1.0:
                    ctx.led_fps, fps_n, fps_t = fps_n / (now - fps_t), 0, now
                if now >= next_ui:
                    live.update(build_dashboard(game, ctx, spans), refresh=True)
                    next_ui = now + ui_dt
                time.sleep(min(0.004, max(0.0005, min(next_led, next_ui) - time.perf_counter())))
    except KeyboardInterrupt:
        pass
    finally:
        if inp:
            inp.stop()
        raw.exit()
        backend.stop()
        fs.exit()

    if game:
        s, rs = game.stats, game.stats.react_stats()
        print(f"\n🐰 Score {s.score} · hits {s.hits} · precisión {s.accuracy():.1f}% · max combo {s.max_combo}"
              + (f" · reacción media {rs['avg']:.0f} ms (best {rs['best']:.0f})" if rs else ""))
    for e in errs:
        print(f"⚠ backend {e}")


if __name__ == "__main__":
    main()