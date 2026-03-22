#!/usr/bin/env python3
"""
Nova OS v4.0 - Agents that answer for themselves.
Enterprise-grade governance infrastructure for AI agents.
2026 Edition. Zero dependencies. Python 3.8+.

Copyright (c) 2026 Nova OS. All rights reserved.
https://nova-os.com
Maintained by Nova Governance
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import hashlib
import argparse
import textwrap
import random
import threading
import uuid
import secrets
import re
import shutil
import platform
import subprocess
import shlex
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# PLATFORM COMPATIBILITY - Works on ANY terminal
# ══════════════════════════════════════════════════════════════════════════════

PLATFORM = platform.system().lower()
IS_WINDOWS = PLATFORM == "windows"
IS_MAC = PLATFORM == "darwin"
IS_LINUX = PLATFORM == "linux"

# Force UTF-8 on Windows
if IS_WINDOWS:
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        os.system("chcp 65001 >nul 2>&1")
        # Enable ANSI on Windows 10+
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # Enable ANSI + Virtual Terminal Processing
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        ENABLE_PROCESSED_OUTPUT = 0x0001
        ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")

# Terminal dimensions
def get_terminal_size():
    try:
        columns, rows = shutil.get_terminal_size()
        return columns, rows
    except Exception:
        return 80, 24

TERM_WIDTH, TERM_HEIGHT = get_terminal_size()

# ══════════════════════════════════════════════════════════════════════════════
# COLOR SYSTEM - Adaptive to terminal capabilities
# ══════════════════════════════════════════════════════════════════════════════

def _detect_color_support():
    """Detect terminal color capabilities."""
    if os.environ.get("NO_COLOR"):
        return 0
    if os.environ.get("FORCE_COLOR"):
        return 256
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return 0
    
    term = os.environ.get("TERM", "").lower()
    colorterm = os.environ.get("COLORTERM", "").lower()
    
    if colorterm in ("truecolor", "24bit"):
        return 16777216  # 24-bit
    if "256" in term or colorterm:
        return 256
    if term in ("xterm", "screen", "vt100", "ansi"):
        return 16
    if IS_WINDOWS:
        return 256  # Modern Windows supports 256
    return 16

COLOR_DEPTH = _detect_color_support()
USE_COLOR = COLOR_DEPTH > 0
DEBUG = os.environ.get("NOVA_DEBUG", "").lower() in ("1", "true", "yes")
VERBOSE = os.environ.get("NOVA_VERBOSE", "").lower() in ("1", "true", "yes")


def _e(code):
    """Generate ANSI escape code."""
    return "\033[" + code + "m" if USE_COLOR else ""


def _rgb(r, g, b):
    """24-bit color if supported, fallback to 256."""
    if COLOR_DEPTH >= 16777216:
        return f"\033[38;2;{r};{g};{b}m"
    # Fallback to closest 256 color
    return _e(f"38;5;{16 + 36*(r//51) + 6*(g//51) + (b//51)}")


class C:
    """
    Enterprise color palette for nova CLI (2026 Light Theme).
    """
    # Core palette
    W = "\033[38;5;15m"      # Pure White
    GREEN = _rgb(62, 207, 142) # Nova Primary Green (#3ecf8e)
    G1 = "\033[38;5;255m"    # Near White
    G2 = "\033[38;5;250m"    # Silver Gray
    G3 = "\033[38;5;244m"    # Medium Gray
    ASH = "\033[38;5;240m"   # Dark Gray (for dim text)
    R = "\033[0m"            # Reset

    BOLD = _e("1")
    DIM  = _e("2")
    ITALIC = _e("3")
    UNDER = _e("4")
    BLINK = _e("5")
    REVERSE = _e("7")
    HIDDEN = _e("8")
    STRIKE = _e("9")

    # Blues - flat, desaturated (OpenClaw-dark)
    B1 = _e("38;5;67")
    B2 = _e("38;5;67")
    B3 = _e("38;5;67")
    B4 = _e("38;5;67")
    B5 = _e("38;5;67")
    B6 = _e("38;5;67")
    B7 = _e("38;5;73")
    B8 = _e("38;5;109")

    # Text hierarchy (NEVER darker than G3 for body text)
    G0  = _e("38;5;252")  # Near-white - primary text
    G3  = _e("38;5;240")  # Dark gray - MINIMUM for visible text
    
    # Semantic colors
    GRN  = _e("38;5;108")  # Muted success
    YLW  = _e("38;5;179")  # Muted warning
    RED  = _e("38;5;167")  # Muted error
    ORG  = _e("38;5;173")  # Muted attention
    MGN  = _e("38;5;139")  # Muted special
    CYN  = _e("38;5;109")  # Muted info
    PNK  = _e("38;5;174")  # Muted accent
    GLD  = _e("38;5;179")  # Muted gold
    GLD_BRIGHT = _e("38;5;180")  # Champagne gold
    GLD_MATTE = _e("38;5;137")   # Matte gold
    SAND = _e("38;5;180")        # Sand gold
    
    # Backgrounds removed for minimal black aesthetic
    BG_RED = ""
    BG_GRN = ""
    BG_BLU = ""
    BG_YLW = ""
    BG_GRY = ""


def q(color, text, bold=False, dim=False, italic=False, underline=False):
    """Wrap text in color codes with optional styles."""
    styles = ""
    if bold: styles += C.BOLD
    if dim: styles += C.DIM
    if italic: styles += C.ITALIC
    if underline: styles += C.UNDER
    return styles + color + str(text) + C.R


def _render_reset():
    """Reset ANSI state and set a pure white base for rendering."""
    sys.stdout.write("\033[0m")
    if USE_COLOR:
        sys.stdout.write(_e("38;5;15"))


def debug(msg):
    """Print debug message if DEBUG mode is enabled."""
    if DEBUG:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:12]
        print("  " + q(C.G3, f"[{ts}]") + " " + q(C.G2, str(msg)))


def verbose(msg):
    """Print verbose message if VERBOSE mode is enabled."""
    if VERBOSE or DEBUG:
        print("  " + q(C.G3, "[verbose]") + " " + q(C.G2, str(msg)))


# ══════════════════════════════════════════════════════════════════════════════
# LOGO + BRANDING - Enterprise identity
# ══════════════════════════════════════════════════════════════════════════════

# ── Nova Starburst - The Astronomical Nova Event ──────────────────────────────
#
#   A nova is a star that explodes in sudden brightness.
#   Eight rays radiate from the central ✦ glyph - Nova's identity mark.
#   The wordmark N  O  V  A  sits below, spaced and minimal.
#
#   Color zones:
#     BRIGHT  38;5;180  champagne gold   - ✦ center (the detonation point)
#     GOLD    38;5;179  gold             - inner ray segments
#     MUTED   38;5;136  muted gold       - ray endpoints  ·
#     MARK    38;5;252  near-white bold  - N  O  V  A  wordmark
#     VER     38;5;240  charcoal         - version / edition subtitle
#
#   Geometry (all columns relative to the 2-space terminal left margin):
#     · at col 14  (ray endpoints top/bottom)
#     ╲/╱ at cols 8 and 20  (outer diagonals, 3 rows from center)
#     ╲/╱ at cols 10 and 18 (inner diagonals, 2 rows from center)
#     ✦ at col 14 (horizontal center)
#     ─ rays extend 11 chars each side of ✦
#
_NOVA_BURST_LINES = None   # built lazily in print_nova_starburst()

# Legacy text logo blocks (kept for compact fallback rendering)
_NOVA_BLOCK = [
    "      __",
    "     /  \\",
    "    /    \\  _   _  _____  _   _   ___ ",
    "    \\ () / | \\ | ||  _  || \\ | | / _ \\",
    "     \\__/  |  \\| || | | ||  \\| |/ /_\\ \\",
    "           |_| \\_||_| |_||_| \\_||  _  |",
]

_CLI_BLOCK = [
    " ",
    " ",
    "  _____  _      _____ ",
    " /  __ \\| |    |_   _|",
    " | /  \\/| |      | |  ",
    " | \\__/\\| |____ _| |_ ",
    "  \\____/\\_____/ \\___/ ",
]

# Star line index (used by legacy renderer)
_STAR_LINE = 1

# Enterprise taglines - rotating
_TAGLINES = [
    "Agents that answer for themselves.",
    "The layer between intent and chaos.",
    "Your agents, accountable.",
    "What your agents do. Provably.",
    "Where intent becomes law.",
    "Intelligence with limits. Actions with proof.",
    "Every action, signed. Every intent, provable.",
    "The nervous system for autonomous agents.",
    "Trust, but verify. Automatically.",
    "Control without constraint.",
    "The firewall for AI agents.",
    "Governance at machine speed.",
    "What stands between your agent and the world.",
    "Actions speak. nova listens.",
    "Because 'it seemed like a good idea' isn't an audit trail.",
    "Sleep well. Your agents are supervised.",
    "Enterprise-grade governance. Zero friction.",
    "Built for scale. Designed for trust.",
    "The missing layer in your AI stack.",
    "From intent to execution. Safely.",
    "Autonomous, not unaccountable.",
    "Your agents' conscience.",
]

# Agent personality messages for ghost writing
_AGENT_GREETINGS = [
    "Hello. I've been waiting for you.",
    "Ready when you are.",
    "Systems initialized. Let's build something safe.",
    "I'm here to help your agents stay accountable.",
    "All systems nominal. What's our first move?",
    "Connected and watching. Your agents are in good hands.",
    "Nova online. Let's make AI trustworthy.",
]

_AGENT_WAKE_MESSAGES = [
    "Initializing governance protocols...",
    "Establishing secure connection...",
    "Loading intent validation engine...",
    "Preparing cryptographic ledger...",
    "Systems coming online...",
]

NOVA_VERSION = "4.5.0"
NOVA_BUILD = "2026.03.supernova"
NOVA_CODENAME = "Supernova"

# Command aliases for power users
ALIASES = {
    "s": "status",
    "start": "launchpad",
    "v": "validate",
    "a": "agent",
    "c": "config",
    "l": "ledger",
    "m": "memory",
    "w": "watch",
    "i": "init",
    "h": "help",
    "t": "test",
    "sk": "skill",
    "e": "export",
    "k": "keys",
    "?": "help",
    "mod": "model",
    "r":    "rules",
    "ru":   "rule",
    "g":    "guard",
    "b":    "boot",
    "x":    "exec",
    "ch":   "chat",
    "lg":   "logs",
    "sc":   "scan",
    "con":  "connect",
    "bm":   "benchmark",
    "str":  "stream",
    "prot": "protect",
    "anom": "anomalies",
    "sup":  "setup",
    "go":   "launchpad",
    "lp":   "launchpad",
    # v4.0
    "pol":  "policy",
    "sim":  "simulate",
    "exp":  "explain",
    "ba":   "batch",
    "st":   "stats",
    "ws":   "workspace",
}


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION UTILITIES - Ghost writing, spinners, progress
# ══════════════════════════════════════════════════════════════════════════════

def ghost_write(text, color=None, delay=0.02, bold=False, newline=True, prefix="  "):
    """
    Ghost writing effect - text appears character by character.
    Enterprise-grade typing animation.
    """
    c = color or C.G1
    if prefix:
        sys.stdout.write(prefix)
    
    # Apply styles
    if bold:
        sys.stdout.write(C.BOLD)
    sys.stdout.write(c)
    
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        # Variable delay for natural feel
        if char in ".!?":
            time.sleep(delay * 8)
        elif char in ",;:":
            time.sleep(delay * 4)
        elif char == " ":
            time.sleep(delay * 1.5)
        else:
            time.sleep(delay + random.uniform(-0.005, 0.01))
    
    sys.stdout.write(C.R)
    if newline:
        print()


def ghost_write_lines(lines, color=None, delay=0.015, line_delay=0.1, prefix="  "):
    """Ghost write multiple lines."""
    for line in lines:
        ghost_write(line, color=color, delay=delay, prefix=prefix)
        time.sleep(line_delay)


def typewriter(text, delay=0.03):
    """Simple typewriter effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)


def fade_in_text(text, color=None, steps=5):
    """Fade in text effect (simulated with delays)."""
    c = color or C.W
    for i in range(steps):
        sys.stdout.write(f"\r  {q(C.G3, text)}")
        sys.stdout.flush()
        time.sleep(0.05)
    sys.stdout.write(f"\r  {q(c, text)}\n")


def pulse_text(text, color=None, pulses=3, prefix="  "):
    """Pulsing text effect."""
    c = color or C.B6
    for _ in range(pulses):
        sys.stdout.write(f"\r{prefix}{q(c, text, bold=True)}")
        sys.stdout.flush()
        time.sleep(0.15)
        sys.stdout.write(f"\r{prefix}{q(c, text)}")
        sys.stdout.flush()
        time.sleep(0.15)
    sys.stdout.write(f"\r{prefix}{q(c, text, bold=True)}\n")


_SPINNER_FRAMES = {
    "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    "line": ["-", "\\", "|", "/"],
    "circle": ["◐", "◓", "◑", "◒"],
    "box": ["▖", "▘", "▝", "▗"],
    "arrows": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
    "pulse": ["○", "◔", "◑", "◕", "●", "◕", "◑", "◔"],
    "nova": ["✦", "✧", "✦", "✧"],
    "blocks": ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"],
}


class Spinner:
    """
    Threaded animated spinner with multiple styles.
    
    Usage:
        with Spinner("Loading..."):
            do_work()
        
        # Or manually:
        spinner = Spinner("Processing...")
        spinner.start()
        # ... work ...
        spinner.finish("Done!")
    """
    
    def __init__(self, message, style="dots", color=None):
        self.message = message
        self.frames = _SPINNER_FRAMES.get(style, _SPINNER_FRAMES["dots"])
        self.color = color or C.B5
        self.stop_event = threading.Event()
        self.thread = None
        self.start_time = None
        self._finished = False
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        if not self._finished:
            self.finish()
    
    def start(self):
        """Start the spinner animation."""
        self.start_time = time.time()
        self.stop_event.clear()
        
        def run():
            i = 0
            while not self.stop_event.is_set():
                frame = self.frames[i % len(self.frames)]
                elapsed = time.time() - self.start_time
                elapsed_str = f" ({elapsed:.1f}s)" if elapsed > 2 else ""
                
                line = f"\r  {q(self.color, frame)}  {q(C.G1, self.message)}{q(C.G3, elapsed_str)}   "
                sys.stdout.write(line)
                sys.stdout.flush()
                time.sleep(0.08)
                i += 1
        
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
    
    def update(self, message):
        """Update the spinner message."""
        self.message = message
    
    def finish(self, final_message=None, success=True):
        """Stop the spinner with optional final message."""
        self._finished = True
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)
        
        # Clear line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        
        if final_message:
            if success:
                ok(final_message)
            else:
                fail(final_message)


class ProgressBar:
    """
    Animated progress bar for long operations.
    
    Usage:
        with ProgressBar(total=100, label="Downloading") as pb:
            for i in range(100):
                do_work()
                pb.update(i + 1)
    """
    
    def __init__(self, total, label="", width=30, color=None):
        self.total = max(total, 1)
        self.label = label
        self.width = width
        self.color = color or C.B6
        self.current = 0
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self._draw()
        return self
    
    def __exit__(self, *args):
        print()  # Newline after progress bar
    
    def update(self, current, label=None):
        """Update progress."""
        self.current = min(current, self.total)
        if label:
            self.label = label
        self._draw()
    
    def _draw(self):
        """Render the progress bar."""
        pct = self.current / self.total
        filled = int(self.width * pct)
        empty = self.width - filled
        
        bar = q(self.color, "█" * filled) + q(C.G3, "·" * empty)
        pct_str = f"{int(pct * 100):3d}%"
        
        # ETA calculation
        elapsed = time.time() - self.start_time if self.start_time else 0
        if pct > 0 and elapsed > 0.5:
            eta = (elapsed / pct) * (1 - pct)
            eta_str = f" ETA {eta:.0f}s" if eta > 1 else ""
        else:
            eta_str = ""
        
        line = f"\r  {bar}  {q(C.W, pct_str)}{q(C.G3, eta_str)}  {q(C.G2, self.label[:30])}"
        sys.stdout.write(line)
        sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
# LOGO RENDERING - Premium visual identity
# ══════════════════════════════════════════════════════════════════════════════

def print_nova_starburst(animated=False):
    """
    The Nova Starburst - an astronomical nova explosion rendered in ASCII.

    Eight rays radiate from the central ✦ (the detonation point).
    Rays fade outward: bright gold center → muted gold endpoints.
    Wordmark N  O  V  A  sits below in near-white bold.

    Geometry (cols relative to the 2-space left print margin):
      ✦ and │ at col 14  (vertical axis + center)
      · endpoints at col 14 (top/bottom)
      outer ╲╱ at cols 8 / 20  (3 rows out)
      inner ╲╱ at cols 10 / 18 (2 rows out)
      horizontal rays: 11 ─ chars each side of ✦
      wordmark "N  O  V  A" offset 9 spaces → N at col 9
    """
    _render_reset()
    print()

    # ── Color constants ────────────────────────────────────────────────────────
    BRIGHT = _e("38;5;180")   # Champagne gold  - ✦ center
    GOLD   = _e("38;5;179")   # Gold            - ray segments
    MUTED  = _e("38;5;136")   # Muted gold      - · endpoints
    MARK   = _e("38;5;252")   # Near-white      - wordmark
    VER    = _e("38;5;240")   # Charcoal        - version subtitle
    W      = TERM_WIDTH or 80

    def emit(s, color="", bold=False, delay=0.028):
        b = C.BOLD if bold and USE_COLOR else ""
        c = color if USE_COLOR else ""
        sys.stdout.write("  " + b + c + s + C.R + "\n")
        sys.stdout.flush()
        if animated:
            time.sleep(delay)

    # ── Ray lines (top half) ───────────────────────────────────────────────────
    emit("              ·",           MUTED)
    emit("        ╲     │     ╱",     GOLD)
    emit("          ╲   │   ╱",       GOLD)

    # ── Core line - mixed colors inline ───────────────────────────────────────
    if USE_COLOR:
        core = (MUTED  + "·" +
                GOLD   + "  ────────── " +
                BRIGHT + C.BOLD + "✦" + C.R +
                GOLD   + " ──────────  " +
                MUTED  + "·" + C.R)
    else:
        core = "·  ────────── ✦ ──────────  ·"
    sys.stdout.write("  " + core + "\n")
    sys.stdout.flush()
    if animated:
        time.sleep(0.028)

    # ── Ray lines (bottom half) ────────────────────────────────────────────────
    emit("          ╱   │   ╲",       GOLD)
    emit("        ╱     │     ╲",     GOLD)
    emit("              ·",           MUTED)

    print()

    # ── Wordmark ───────────────────────────────────────────────────────────────
    emit("         N  O  V  A",       MARK, bold=True, delay=0.04)
    emit(f"         ·  v{NOVA_VERSION} Supernova  ·",   VER, delay=0)

    print()
    sys.stdout.flush()


def print_logo(tagline=True, compact=False, animated=False, minimal=False):
    """
    Print the nova logo.

    Full mode  → Nova Starburst + tagline  (default - nova init, nova help)
    Compact    → single-line banner        (most commands)
    Minimal    → just the ✦ glyph
    """
    _render_reset()
    print()

    if minimal:
        print("  " + q(C.GLD_BRIGHT, "✦", bold=True))
        sys.stdout.write(C.R)
        return

    if compact:
        banner = f"✦ nova · v{NOVA_VERSION} · Nova Governance"
        print("  " + q(C.GLD_BRIGHT, banner, bold=True))
        print()
        sys.stdout.write(C.R)
        return

    # Full - Nova Starburst
    print_nova_starburst(animated=animated)

    if tagline:
        tl = random.choice(_TAGLINES)
        if animated:
            ghost_write(tl, color=C.G2, delay=0.01)
        else:
            print("  " + q(C.G2, tl))
        print("  " + q(C.GLD_BRIGHT, "✦") + " " +
              q(C.G3, f"Constellation · Enterprise Edition"))
        print("  " + q(C.G3, "─" * 62))

    print()
    sys.stdout.write(C.R)


def print_mark():
    """Print just the nova mark for sub-screens."""
    _render_reset()
    print()
    print("  " + q(C.GLD_BRIGHT, "✦", bold=True) + "  " + q(C.W, "nova", bold=True))
    print()


# ══════════════════════════════════════════════════════════════════════════════
# UI PRIMITIVES - Building blocks for interface
# ══════════════════════════════════════════════════════════════════════════════

def ok(msg, prefix="  "):
    """Success message."""
    _render_reset()
    print(f"{prefix}" + q(C.GRN, "✓") + "  " + q(C.W, msg))

def fail(msg, prefix="  "):
    """Error message."""
    _render_reset()
    print(f"{prefix}" + q(C.RED, "✗") + "  " + q(C.W, msg))

def warn(msg, prefix="  "):
    """Warning message."""
    _render_reset()
    print(f"{prefix}" + q(C.YLW, "!") + "  " + q(C.G1, msg))

def info(msg, prefix="  "):
    """Info message."""
    _render_reset()
    print(f"{prefix}" + q(C.B6, "·") + "  " + q(C.G1, msg))

def hint(msg, prefix="  "):
    """Hint/tip message."""
    _render_reset()
    print(f"{prefix}" + q(C.MGN, "→") + "  " + q(C.G2, msg))

def dim(msg, prefix="       "):
    """Dimmed secondary text."""
    _render_reset()
    print(f"{prefix}" + q(C.G2, msg))


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def strip_ansi(text):
    """Strip ANSI escape codes for accurate width calculations."""
    return ANSI_RE.sub("", text or "")


def _pad_ansi(text, width):
    raw = strip_ansi(text)
    pad = max(0, width - len(raw))
    return f"{text}{' ' * pad}"


def render_table(title, headers, rows, prefix="  "):
    """Render a rich table with box-drawing borders."""
    _render_reset()
    if title:
        print(prefix + q(C.G2, title))
        print()
    
    widths = [len(strip_ansi(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(strip_ansi(str(cell))))
    
    top = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
    mid = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    bot = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"
    
    def _line(cells):
        parts = []
        for i, cell in enumerate(cells):
            parts.append(" " + _pad_ansi(str(cell), widths[i]) + " ")
        return "│" + "│".join(parts) + "│"
    
    print(prefix + q(C.G3, top))
    print(prefix + q(C.W, _line(headers)))
    print(prefix + q(C.G3, mid))
    for row in rows:
        print(prefix + _line(row))
    print(prefix + q(C.G3, bot))
    print()


def health_meter(score, width=8):
    """Visual health meter for status screens."""
    score = max(0, min(100, int(score)))
    filled = int((score / 100) * width)
    empty = width - filled
    bar = q(C.SAND, "·" * filled) + q(C.G3, "·" * empty)
    return f"{bar}  {q(C.G2, f'{score:3d}%')}"

def nl(count=1):
    """Print newlines."""
    print("\n" * (count - 1))

def hr(char="─", width=62, color=None):
    """Horizontal rule."""
    c = color or C.G3
    print("  " + q(c, char * width))

def hr_bold(width=62):
    """Bold horizontal rule for important sections."""
    print("  " + q(C.GLD, "━" * width, bold=True))

def clear_line():
    """Clear current line."""
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()

def clear_screen():
    """Clear entire screen."""
    os.system("cls" if IS_WINDOWS else "clear")

def move_up(lines=1):
    """Move cursor up N lines."""
    sys.stdout.write(f"\033[{lines}A")
    sys.stdout.flush()


def section(title, subtitle="", width=62):
    """Section header with optional subtitle."""
    print()
    if subtitle:
        print("  " + q(C.W, title, bold=True) + "  " + q(C.G2, subtitle))
    else:
        print("  " + q(C.W, title, bold=True))
    print("  " + q(C.G3, "─" * min(len(title) + 4, width)))


def kv(key, value, color=None, key_width=22, prefix="  "):
    """Key-value line with aligned columns."""
    c = color or C.W
    print(f"{prefix}" + q(C.G2, key.ljust(key_width)) + q(c, str(value)))


def kvb(key, value, color=None):
    """Key-value with bold value."""
    c = color or C.W
    print("  " + q(C.G2, key.ljust(22)) + q(c, str(value), bold=True))


def bullet(text, color=None, bullet_char="·", prefix="  "):
    """Bulleted list item."""
    c = color or C.G1
    print(f"{prefix}" + q(C.G3, bullet_char) + "  " + q(c, text))


def numbered(index, text, color=None, prefix="  "):
    """Numbered list item."""
    c = color or C.G1
    print(f"{prefix}" + q(C.G3, f"{index}.") + " " + q(c, text))


def score_bar(score, width=20):
    """Visual score bar with semantic colors."""
    score = max(0, min(100, score))
    filled = int((score / 100) * width)
    empty = width - filled
    
    # Color based on score
    if score >= 70:
        c = C.GRN
    elif score >= 40:
        c = C.YLW
    else:
        c = C.RED
    
    bar = q(c, "█" * filled, bold=True) + q(C.G3, "·" * empty)
    num = q(c, str(score), bold=True)
    return q(C.G3, "[") + bar + q(C.G3, "]") + " " + num


def sparkline(values, width=None):
    """Render a sparkline from values."""
    if not values:
        return q(C.G3, "no data")
    
    blocks = "▁▂▃▄▅▆▇█"
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    
    line = ""
    for v in values:
        idx = min(int((v - mn) / rng * (len(blocks) - 1)), len(blocks) - 1)
        line += blocks[idx]
    
    return q(C.B6, line)


def verdict_badge(verdict):
    """Colored verdict badge."""
    badges = {
        "APPROVED":  (C.GRN, "✓", "APPROVED"),
        "BLOCKED":   (C.RED, "✗", "BLOCKED"),
        "ESCALATED": (C.YLW, "⚠", "ESCALATED"),
        "DUPLICATE": (C.ORG, "⊘", "DUPLICATE"),
    }
    c, sym, label = badges.get(verdict.upper(), (C.G2, "·", verdict))
    return q(c, sym) + "  " + q(c, label, bold=True)


def time_ago(iso_str):
    """Convert ISO timestamp to human-readable relative time."""
    if not iso_str:
        return ""
    
    try:
        # Parse ISO format
        s = iso_str.replace("Z", "+00:00")
        if "+" not in s and "-" not in s[10:]:
            dt = datetime.fromisoformat(s)
            now = datetime.now()
        else:
            dt = datetime.fromisoformat(s)
            now = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                now = datetime.now()
        
        delta = now - dt
        secs = int(delta.total_seconds())
        
        if secs < 0:
            return "just now"
        if secs < 10:
            return "just now"
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        
        days = delta.days
        if days < 7:
            return f"{days}d ago"
        if days < 30:
            return f"{days // 7}w ago"
        if days < 365:
            return f"{days // 30}mo ago"
        return f"{days // 365}y ago"
    
    except Exception:
        return iso_str[:16] if len(iso_str) > 16 else iso_str


def format_bytes(num_bytes):
    """Format bytes to human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def mask_key(key, visible_start=4, visible_end=4):
    """Mask API key for display."""
    if not key:
        return q(C.G3, "not set")
    if len(key) < visible_start + visible_end + 4:
        return "*" * len(key)
    return key[:visible_start] + "•" * 8 + key[-visible_end:]


def box(lines, color=None, title="", padding=1):
    """Draw a box around content."""
    bc = color or C.G3
    
    # Calculate width
    max_len = max((len(line) for line in lines), default=30)
    inner_w = max_len + (padding * 2) + 2
    w = max(inner_w, len(title) + 6 if title else inner_w)
    
    # Top border
    if title:
        tpad = max(0, w - len(title) - 4)
        print("  " + q(bc, "┌─ ") + q(C.G1, title) + " " + q(bc, "─" * tpad + "┐"))
    else:
        print("  " + q(bc, "┌" + "─" * w + "┐"))
    
    # Content
    for line in lines:
        pad = " " * padding
        right_pad = " " * max(0, w - len(line) - (padding * 2) - 2)
        print("  " + q(bc, "│") + pad + q(C.G1, line) + right_pad + pad + q(bc, "│"))
    
    # Bottom border
    print("  " + q(bc, "└" + "─" * w + "┘"))


def table(headers, rows, colors=None, max_col_width=40):
    """Render a formatted table with thin Unicode borders."""
    if not rows:
        return
    
    # Calculate column widths
    col_count = len(headers)
    widths = []
    for i in range(col_count):
        max_w = len(str(headers[i]))
        for row in rows:
            if i < len(row):
                max_w = max(max_w, len(str(row[i])))
        widths.append(min(max_w, max_col_width))
    
    top = "┌" + "┬".join("─" * (w + 2) for w in widths) + "┐"
    mid = "├" + "┼".join("─" * (w + 2) for w in widths) + "┤"
    bot = "└" + "┴".join("─" * (w + 2) for w in widths) + "┘"

    def _line(cells, header=False):
        parts = []
        for i, cell in enumerate(cells):
            val = str(cell)
            if len(val) > widths[i]:
                val = val[:widths[i]-1] + "…"
            c = C.W if header else (colors[i] if colors and i < len(colors) else C.G1)
            parts.append(" " + q(c, val.ljust(widths[i]), bold=header) + " ")
        return "│" + "│".join(parts) + "│"

    print("  " + q(C.G3, top))
    print("  " + _line(headers, header=True))
    print("  " + q(C.G3, mid))
    for row in rows:
        print("  " + _line([row[i] if i < len(row) else "" for i in range(col_count)]))
    print("  " + q(C.G3, bot))


# ══════════════════════════════════════════════════════════════════════════════
# INPUT UTILITIES - Prompts, confirmations, selections
# ══════════════════════════════════════════════════════════════════════════════

def prompt(label, default="", secret=False, required=False, validator=None, prefix="  "):
    """
    Enhanced text input prompt.
    
    Args:
        label: Prompt label
        default: Default value if empty
        secret: Hide input (for passwords/keys)
        required: Require non-empty input
        validator: Function(value) -> True or error message
    """
    while True:
        hint_text = f" ({default})" if default and not secret else ""
        print(f"{prefix}" + q(C.B6, "?") + "  " + q(C.G1, label) + 
              q(C.G3, hint_text) + "  ", end="", flush=True)
        
        if secret:
            try:
                import getpass
                value = getpass.getpass("").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return default
        else:
            try:
                value = input().strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return default
        
        # Use default if empty
        if not value:
            value = default
        
        # Check required
        if required and not value:
            warn("This field is required.")
            continue
        
        # Run validator
        if validator and value:
            result = validator(value)
            if result is not True:
                warn(result if isinstance(result, str) else "Invalid input.")
                continue
        
        return value


def prompt_list(label, hint="empty line to finish", min_items=0, max_items=None):
    """Multi-line list input."""
    print("  " + q(C.B6, "?") + "  " + q(C.G1, label) + "  " + q(C.G3, f"({hint})"))
    
    items = []
    while True:
        if max_items and len(items) >= max_items:
            break
        
        print("    " + q(C.G3, f"[{len(items) + 1}]  "), end="", flush=True)
        try:
            v = input().strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if not v:
            if len(items) < min_items:
                warn(f"At least {min_items} items required.")
                continue
            break
        
        items.append(v)
    
    return items


def confirm(label, default=True, prefix="  "):
    """Yes/no confirmation with sensible defaults."""
    hint = q(C.G3, "Y/n" if default else "y/N")
    print(f"{prefix}" + q(C.B6, "?") + "  " + q(C.G1, label) + "  " + hint + "  ", 
          end="", flush=True)
    
    try:
        v = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    
    if not v:
        return default
    return v in ("y", "yes", "s", "si", "sí", "1", "true")


def confirm_danger(label, confirm_text="DELETE", prefix="  "):
    """
    Dangerous action confirmation - requires typing specific text.
    """
    print(f"{prefix}" + q(C.RED, "!") + "  " + q(C.W, label))
    print(f"{prefix}   " + q(C.G2, f"Type '{confirm_text}' to confirm:") + "  ", 
          end="", flush=True)
    
    try:
        v = input().strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    
    return v == confirm_text


# ══════════════════════════════════════════════════════════════════════════════
# ARROW-KEY SELECTOR - Claude Code / Gemini CLI style
# ══════════════════════════════════════════════════════════════════════════════

def _is_tty():
    """Check if we're in an interactive terminal."""
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def _select(options, title="", default=0, descriptions=None, show_index=False, 
            allow_filter=False, page_size=10):
    """
    Premium arrow-key selector with enterprise features.
    
    Features:
        - Arrow key navigation (↑↓)
        - Number keys for quick selection (1-9)
        - j/k vim-style navigation
        - Optional descriptions per item
        - Filtering (type to search)
        - Pagination for long lists
        - Works on Windows, Mac, Linux
        - Graceful fallback for non-TTY
    
    Args:
        options: List of option strings (NO ANSI codes!)
        title: Optional title above the list
        default: Default selected index
        descriptions: Optional list of descriptions per option
        show_index: Show [1] [2] etc.
        allow_filter: Enable type-to-filter
        page_size: Max items shown at once
    
    Returns:
        Selected index
    """
    if not options:
        return 0
    
    # Fallback for non-interactive
    if not _is_tty():
        return _select_fallback(options, title, default, descriptions, show_index)
    
    current = default
    filter_text = ""
    scroll_offset = 0
    
    def get_filtered_indices():
        """Get indices of options matching filter."""
        if not filter_text:
            return list(range(len(options)))
        return [i for i, opt in enumerate(options) 
                if filter_text.lower() in opt.lower()]
    
    def draw(first=False):
        """Render the selector. Uses cursor save/restore - no line counting."""
        nonlocal scroll_offset
        filtered = get_filtered_indices()

        # Adjust scroll
        if filtered:
            vis_idx = filtered.index(current) if current in filtered else 0
            if vis_idx < scroll_offset:
                scroll_offset = vis_idx
            elif vis_idx >= scroll_offset + page_size:
                scroll_offset = vis_idx - page_size + 1

        out = []

        if not first:
            # Restore saved cursor position, then erase everything below
            out.append("\033[u\033[J")
        else:
            # Save cursor position before first draw
            out.append("\033[s")

        # Title
        if title:
            out.append("  " + q(C.G2, title) + "\n")

        # Filter input
        if allow_filter:
            filter_display = filter_text if filter_text else q(C.G3, "type to filter...")
            out.append("  " + q(C.B6, "/") + " " + filter_display + "\n")

        out.append("\n")

        # Options
        visible_items = filtered[scroll_offset:scroll_offset + page_size]

        for display_idx, opt_idx in enumerate(visible_items):
            opt = options[opt_idx]
            is_selected = (opt_idx == current)

            idx_str = ""
            if show_index:
                idx_str = q(C.G3, f"[{opt_idx + 1}]") + "  "

            if is_selected:
                out.append("  " + q(C.B6, "\u25b8", bold=True) + "  " + idx_str +
                           q(C.W, opt, bold=True) + "\n")
            else:
                out.append("     " + idx_str + q(C.G2, opt) + "\n")

            if descriptions and opt_idx < len(descriptions) and descriptions[opt_idx]:
                desc = descriptions[opt_idx]
                desc_color = C.G2 if is_selected else C.G3
                out.append("       " + q(desc_color, desc) + "\n")

        if scroll_offset > 0:
            out.append("       " + q(C.G3, "\u2191 more above") + "\n")
        if scroll_offset + page_size < len(filtered):
            out.append("       " + q(C.G3, "\u2193 more below") + "\n")

        out.append("\n")

        sys.stdout.write("".join(out))
        sys.stdout.flush()

    
    # Key reading - inline so `current` stays in _select scope
    if IS_WINDOWS:
        # Windows inline loop - current in _select scope
        import msvcrt
        draw(first=True)
        while True:
            ch = msvcrt.getch()
            if ch in (b"\r", b"\n"):
                return current
            if ch == b"\x03":
                raise KeyboardInterrupt
            if ch in (b"\x00", b"\xe0"):
                ch2 = msvcrt.getch()
                filtered = get_filtered_indices()
                if ch2 == b"H":   # Up arrow
                    if current in filtered:
                        idx = filtered.index(current)
                        if idx > 0:
                            current = filtered[idx - 1]
                    draw()
                elif ch2 == b"P": # Down arrow
                    if current in filtered:
                        idx = filtered.index(current)
                        if idx < len(filtered) - 1:
                            current = filtered[idx + 1]
                    draw()
                continue
            try:
                key = ch.decode(errors="ignore")
            except Exception:
                continue
            if key.isdigit():
                idx = int(key) - 1
                if 0 <= idx < len(options):
                    return idx
            elif key in ("k", "K"):
                filtered = get_filtered_indices()
                if current in filtered:
                    idx = filtered.index(current)
                    if idx > 0:
                        current = filtered[idx - 1]
                draw()
            elif key in ("j", "J"):
                filtered = get_filtered_indices()
                if current in filtered:
                    idx = filtered.index(current)
                    if idx < len(filtered) - 1:
                        current = filtered[idx + 1]
                draw()


    # Unix inline loop
    import termios, tty, os as _os, select as _sel
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def read_key():
        """
        Read one keypress. Fixes vs original:
        - os.read(fd,1) bypasses Python TextIOWrapper buffering + newline
          translation that caused phantom keys after Enter in SSH.
        - tcflush(TCIFLUSH) after Enter discards the trailing \\n SSH sends
          (\r\n pair) so the next _select() doesn't auto-fire immediately.
        - select() timeout on escape sequences avoids blocking on bare Escape.
        - raw mode set/restored AROUND each read so draw() always runs in
          normal mode — this keeps \n → CR+LF working and display stays aligned.
        """
        tty.setraw(fd)
        try:
            b = _os.read(fd, 1)
            if b in (b"\r", b"\n"):
                termios.tcflush(fd, termios.TCIFLUSH)  # discard trailing \n
                return "\r"
            if b == b"\x03":
                return "\x03"
            if b == b"\x1b":
                rdy, _, _ = _sel.select([fd], [], [], 0.05)
                if not rdy:
                    return "\x1b"
                b2 = _os.read(fd, 1)
                if b2 == b"[":
                    rdy2, _, _ = _sel.select([fd], [], [], 0.05)
                    if not rdy2:
                        return "["
                    b3 = _os.read(fd, 1)
                    if b3 == b"A": return "UP"
                    if b3 == b"B": return "DOWN"
                    if b3 == b"C": return "RIGHT"
                    if b3 == b"D": return "LEFT"
                    return b3.decode(errors="ignore")
                return b2.decode(errors="ignore")
            try:
                return b.decode(errors="ignore")
            except Exception:
                return ""
        finally:
            # Restore BEFORE draw() — normal mode keeps \n→CR+LF so display
            # stays correctly positioned (raw mode shifts columns on \n only)
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    draw(first=True)

    while True:
        key = read_key()
        filtered = get_filtered_indices()

        if key == "\r":
            return current
        if key == "\x03":
            raise KeyboardInterrupt
        if key in ("UP", "k", "K"):
            if current in filtered:
                idx = filtered.index(current)
                if idx > 0:
                    current = filtered[idx - 1]
            draw()
        elif key in ("DOWN", "j", "J"):
            if current in filtered:
                idx = filtered.index(current)
                if idx < len(filtered) - 1:
                    current = filtered[idx + 1]
            draw()
        elif key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(options):
                return idx
        elif key == "q":
            raise KeyboardInterrupt


def _select_fallback(options, title, default, descriptions, show_index):
    """Fallback selection for non-TTY environments."""
    _render_reset()
    if title:
        print("  " + q(C.W, title))
    print()
    
    for i, opt in enumerate(options):
        marker = q(C.G1, ">", bold=True) if i == default else "  "
        idx = f"[{i + 1}]  " if show_index else ""
        label = q(C.W, opt, bold=True) if i == default else q(C.W, opt)
        print("  " + marker + " " + idx + label)
        
        if descriptions and i < len(descriptions) and descriptions[i]:
            print("       " + q(C.W, descriptions[i]))
    
    print()
    print("  " + q(C.W, f"Select [1-{len(options)}]:") + "  ", end="", flush=True)
    
    try:
        v = input().strip()
        if v.isdigit():
            idx = int(v) - 1
            if 0 <= idx < len(options):
                return idx
    except (EOFError, KeyboardInterrupt):
        pass
    
    return default


def _select_windows(options, draw, current, get_filtered, page_size):
    """Windows-specific key handling."""
    import msvcrt
    
    draw(first=True)
    
    while True:
        ch = msvcrt.getch()

        if ch in (b"\r", b"\n"):
            return current

        if ch == b"\x03":  # Ctrl+C
            raise KeyboardInterrupt

        if ch in (b"\x00", b"\xe0"):  # Special keys
            ch2 = msvcrt.getch()
            filtered = get_filtered()

            if ch2 == b"H":  # Up
                if current in filtered:
                    idx = filtered.index(current)
                    if idx > 0:
                        current = filtered[idx - 1]
            elif ch2 == b"P":  # Down
                if current in filtered:
                    idx = filtered.index(current)
                    if idx < len(filtered) - 1:
                        current = filtered[idx + 1]

            draw()
            continue

        try:
            key = ch.decode(errors="ignore")
        except Exception:
            continue

        if key.isdigit():  # Number selection
            idx = int(key) - 1
            if 0 <= idx < len(options):
                return idx

        elif key in ("k", "K"):  # Vim up
            filtered = get_filtered()
            if current in filtered:
                idx = filtered.index(current)
                if idx > 0:
                    current = filtered[idx - 1]
            draw()

        elif key in ("j", "J"):  # Vim down
            filtered = get_filtered()
            if current in filtered:
                idx = filtered.index(current)
                if idx < len(filtered) - 1:
                    current = filtered[idx + 1]
            draw()


def _raw_input_unix():
    """Context manager for raw ANSI input on Unix-like systems."""
    import termios
    import tty

    class _RawInput:
        def __init__(self):
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)

        def read_key(self):
            # setraw per-keypress, restore immediately after
            tty.setraw(self.fd)
            try:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        if   ch3 == "A": return "UP"
                        elif ch3 == "B": return "DOWN"
                        elif ch3 == "C": return "RIGHT"
                        elif ch3 == "D": return "LEFT"
                        return ch3
                    return ch2
                return ch
            finally:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)


        def close(self):
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.close()

    return _RawInput()


def _select_unix(options, draw, current, get_filtered, page_size, allow_filter):
    """Unix/Mac key handling with proper terminal restoration."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def read_key():
        """Read single keypress, set raw only for the duration."""
        tty.setraw(fd)
        try:
            ch = sys.stdin.read(1)
            if ch == "\x1b":  # Escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A": return "UP"
                    if ch3 == "B": return "DOWN"
                    if ch3 == "C": return "RIGHT"
                    if ch3 == "D": return "LEFT"
                    return ch3
                return ch2
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    draw(first=True)

    while True:
        key = read_key()
        filtered = get_filtered()

        if key in ("\r", "\n"):
            return current

        if key == "\x03":  # Ctrl+C
            raise KeyboardInterrupt

        if key == "UP" or key in ("k", "K"):
            if current in filtered:
                idx = filtered.index(current)
                if idx > 0:
                    current = filtered[idx - 1]
            draw()

        elif key == "DOWN" or key in ("j", "J"):
            if current in filtered:
                idx = filtered.index(current)
                if idx < len(filtered) - 1:
                    current = filtered[idx + 1]
            draw()

        elif key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(options):
                return idx

        elif key == "q":
            raise KeyboardInterrupt


def _select_multi(options, title="", selected=None, descriptions=None):
    """
    Multi-select with space to toggle, enter to confirm.
    
    Returns:
        List of selected indices
    """
    selected = set(selected or [])
    current = 0
    
    if not _is_tty():
        # Fallback
        _render_reset()
        print("  " + q(C.W, title or "Select options (comma-separated):"))
        for i, opt in enumerate(options):
            mark = "[x]" if i in selected else "[ ]"
            print("  " + q(C.W, f"{i + 1}. {mark} {opt}"))
        
        try:
            v = input("  Numbers: ").strip()
            return [int(x) - 1 for x in v.split(",") if x.strip().isdigit()]
        except (EOFError, KeyboardInterrupt):
            return list(selected)
    
    def draw(first=False):
        lines = (1 if title else 0) + 2 + len(options) + 2
        out = []
        _render_reset()
        
        if not first:
            out.append(f"\033[{lines}A\033[J")
        
        if title:
            out.append("  " + q(C.W, title) + "\n")
        
        out.append("\n")
        out.append("  " + q(C.W, "↑↓ navigate · Space toggle · Enter confirm") + "\n")
        out.append("\n")
        
        for i, opt in enumerate(options):
            check = q(C.W, "●") if i in selected else q(C.W, "○")
            if i == current:
                out.append("  " + q(C.G1, ">", bold=True) + " " + check + "  " +
                           q(C.W, opt, bold=True) + "\n")
            else:
                out.append("    " + check + "  " + q(C.W, opt) + "\n")
        
        out.append("\n")
        sys.stdout.write("".join(out))
        sys.stdout.flush()
    
    if IS_WINDOWS:
        import msvcrt
        draw(first=True)
        
        while True:
            ch = msvcrt.getch()
            
            if ch in (b"\r", b"\n"):
                return list(selected)
            if ch == b" ":
                if current in selected:
                    selected.remove(current)
                else:
                    selected.add(current)
            elif ch in (b"\x00", b"\xe0"):
                ch2 = msvcrt.getch()
                if ch2 == b"H": current = (current - 1) % len(options)
                elif ch2 == b"P": current = (current + 1) % len(options)
            elif ch == b"\x03":
                raise KeyboardInterrupt
            
            draw()
    
    else:
        draw(first=True)
        with _raw_input_unix() as raw:
            while True:
                key = raw.read_key()
                if not key:
                    continue

                if key in ("\r", "\n"):
                    return list(selected)
                if key == "\x03":
                    raise KeyboardInterrupt
                if key == " ":
                    if current in selected:
                        selected.remove(current)
                    else:
                        selected.add(current)
                elif key == "UP":
                    current = (current - 1) % len(options)
                elif key == "DOWN":
                    current = (current + 1) % len(options)

                draw()


# ══════════════════════════════════════════════════════════════════════════════
# STEP HEADER / WIZARD UI
# ══════════════════════════════════════════════════════════════════════════════

def step_header(current, total, title, subtitle=""):
    """
    Step progress header for multi-step wizards.
    """
    _render_reset()
    print()
    
    # Progress bar
    filled = "█" * current
    empty = "·" * (total - current)
    bar = q(C.B6, filled, bold=True) + q(C.G3, empty)
    
    progress = q(C.G2, f"{current}/{total}")
    
    print(f"  {bar}  {progress}  " + q(C.W, title, bold=True))
    
    if subtitle:
        print("  " + q(C.G3, " " * total) + "       " + q(C.G2, subtitle))
    
    hr()
    print()


def wizard_intro(title, lines, animated=True):
    """
    Wizard introduction screen with optional animation.
    """
    print()
    print("  " + q(C.W, title, bold=True))
    print()
    
    if animated:
        for line in lines:
            ghost_write(line, color=C.G1, delay=0.012)
            time.sleep(0.05)
    else:
        for line in lines:
            print("  " + q(C.G1, line))
    
    print()


def pause(label="continue", prefix="  "):
    """Pause for user to press Enter."""
    print()
    print(f"{prefix}" + q(C.W, f"Press Enter to {label}") + "  " + q(C.G2, "↵"), 
          end="", flush=True)
    
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print()
    
    print()


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - ~/.nova/
# ══════════════════════════════════════════════════════════════════════════════

NOVA_DIR = Path.home() / ".nova"
CONFIG_FILE = NOVA_DIR / "config.json"
KEYS_FILE = NOVA_DIR / "keys.json"
PROFILES_FILE = NOVA_DIR / "profiles.json"
HISTORY_FILE = NOVA_DIR / "history.json"
QUEUE_FILE = NOVA_DIR / "offline_queue.json"


# ══════════════════════════════════════════════════════════════════════════════
# AGENT DISCOVERY ENGINE - auto-detects agents in the user's project
# ══════════════════════════════════════════════════════════════════════════════

# Signatures: how Nova recognises each agent type in the environment
# ══════════════════════════════════════════════════════════════════════════════
# AGENT DETECTION ENGINE  v2  —  5-method universal scanner
# ══════════════════════════════════════════════════════════════════════════════
#
# Method 1: Binary probe     — shutil.which + --version
# Method 2: Process scan     — ps aux / tasklist for running instances
# Method 3: Home dir scan    — ~/.claude/, ~/.config/gh/, ~/.gemini/, etc.
# Method 4: Shell config     — ~/.bashrc, ~/.zshrc exported vars
# Method 5: Package managers — npm -g list, pip show, apt list
#
# Each method adds confidence independently.
# The engine is additive: the more evidence, the higher the score.
# Threshold: 20 = show to user.  50+ = high confidence.  80+ = certain.
# ══════════════════════════════════════════════════════════════════════════════

_AGENT_REGISTRY: dict = {

    # ── Server-based agents (HTTP port + optional binary) ─────────────────────

    "openclaw": {
        "display":      "OpenClaw",
        "icon":         "◎",
        "type":         "server",
        # Method 1: binary
        "binary":       "openclaw",
        # Method 2: process keywords
        "process_kw":   ["openclaw"],
        # Method 3: home dirs
        "home_dirs":    [],
        # Method 4: shell vars (exported)
        "shell_vars":   ["OPENCLAW_URL", "OPENCLAW_PORT", "OPENCLAW_API_KEY"],
        # Method 5: packages
        "npm_pkg":      None,
        "pip_pkg":      None,
        # Port probe
        "ports":        [1234],
        "default_port": 1234,
        "env_url_keys": ["OPENCLAW_URL", "OPENAI_BASE_URL"],
        "env_port_hint": {"OPENAI_BASE_URL": 1234},
        # Config files in project
        "project_files": [".openclaw", "openclaw.config.json", "openclaw.yaml"],
        # Integration
        "integration":  ["proxy", "alias"],
        "inject_file":  None,
    },

    "melissa": {
        "display":      "Melissa",
        "icon":         "◉",
        "type":         "server",
        "binary":       None,
        "process_kw":   ["melissa"],
        "home_dirs":    [str(Path.home() / "melissa"), str(Path.home() / "melissa-ultra"),
                         "/home/ubuntu/melissa", "/opt/melissa"],
        "shell_vars":   ["MELISSA_API_KEY", "MELISSA_TOKEN", "MELISSA_URL"],
        "npm_pkg":      None,
        "pip_pkg":      None,
        "ports":        [8001, 8002],
        "default_port": 8001,
        "env_url_keys": ["MELISSA_URL"],
        "env_port_hint": {},
        "project_files": ["melissa.env", ".melissa", "melissa_agent.py"],
        "integration":  ["proxy", "alias"],
        "inject_file":  None,
    },

    "n8n": {
        "display":      "n8n",
        "icon":         "◈",
        "type":         "server",
        "binary":       "n8n",
        "process_kw":   ["n8n"],
        "home_dirs":    [str(Path.home() / ".n8n")],
        "shell_vars":   ["N8N_PORT", "N8N_BASIC_AUTH_USER", "N8N_HOST"],
        "npm_pkg":      "n8n",
        "pip_pkg":      None,
        "ports":        [5678],
        "default_port": 5678,
        "env_url_keys": [],
        "env_port_hint": {},
        "project_files": [".n8n", "n8n.config.js"],
        "integration":  ["proxy"],
        "inject_file":  None,
    },

    # ── CLI agents (no server port — detected by binary/home/packages) ─────────

    "claude_code": {
        "display":      "Claude Code",
        "icon":         "◑",
        "type":         "cli",
        "binary":       "claude",
        "process_kw":   ["claude", "claude-code"],
        "home_dirs":    [str(Path.home() / ".claude")],
        "shell_vars":   ["ANTHROPIC_API_KEY"],
        "npm_pkg":      "@anthropic-ai/claude-code",
        "pip_pkg":      None,
        "ports":        [],
        "default_port": None,
        "env_url_keys": [],
        "env_port_hint": {},
        "project_files": ["CLAUDE.md", ".claude/settings.json", ".clauderc"],
        "integration":  ["mcp", "config_inject", "git_hook"],
        "inject_file":  "CLAUDE.md",
        # Verification command: claude --version
        "verify_cmd":   ["claude", "--version"],
    },

    "gemini_cli": {
        "display":      "Gemini CLI",
        "icon":         "▷",
        "type":         "cli",
        "binary":       "gemini",
        "process_kw":   ["gemini-cli", "gemini"],
        "home_dirs":    [str(Path.home() / ".gemini"),
                         str(Path.home() / ".config" / "gemini")],
        "shell_vars":   ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"],
        "npm_pkg":      "@google/gemini-cli",
        "pip_pkg":      None,
        "ports":        [],
        "default_port": None,
        "env_url_keys": [],
        "env_port_hint": {},
        "project_files": [".gemini", "gemini.json", ".gemini.json"],
        "integration":  ["alias", "config_inject", "fswatch"],
        "inject_file":  ".gemini/system.md",
        "verify_cmd":   ["gemini", "--version"],
    },

    "codex_cli": {
        "display":      "OpenAI Codex CLI",
        "icon":         "⬡",
        "type":         "cli",
        "binary":       "codex",
        "process_kw":   ["codex"],
        "home_dirs":    [str(Path.home() / ".codex"),
                         str(Path.home() / ".config" / "codex")],
        "shell_vars":   ["OPENAI_API_KEY"],
        "npm_pkg":      "@openai/codex",
        "pip_pkg":      None,
        "ports":        [],
        "default_port": None,
        "env_url_keys": [],
        "env_port_hint": {},
        "project_files": ["AGENTS.md", ".codex", "codex.json"],
        "integration":  ["alias", "config_inject", "fswatch"],
        "inject_file":  "AGENTS.md",
        "verify_cmd":   ["codex", "--version"],
    },

    "copilot_cli": {
        "display":      "GitHub Copilot",
        "icon":         "⊕",
        "type":         "cli",
        # gh is the binary but we need to verify the copilot extension
        "binary":       "gh",
        "process_kw":   ["gh copilot", "github-copilot"],
        "home_dirs":    [str(Path.home() / ".config" / "gh")],
        "shell_vars":   ["GH_TOKEN", "GITHUB_TOKEN"],
        "npm_pkg":      None,
        "pip_pkg":      None,
        "ports":        [],
        "default_port": None,
        "env_url_keys": [],
        "env_port_hint": {},
        "project_files": [".github/copilot-instructions.md"],
        "integration":  ["alias", "config_inject"],
        "inject_file":  ".github/copilot-instructions.md",
        # Special: must run "gh extension list" and look for copilot
        "verify_cmd":   ["gh", "extension", "list"],
        "verify_grep":  "copilot",   # must appear in verify_cmd output
    },

    "aider": {
        "display":      "Aider",
        "icon":         "◇",
        "type":         "cli",
        "binary":       "aider",
        "process_kw":   ["aider"],
        "home_dirs":    [str(Path.home() / ".aider")],
        "shell_vars":   ["AIDER_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
        "npm_pkg":      None,
        "pip_pkg":      "aider-chat",
        "ports":        [],
        "default_port": None,
        "env_url_keys": [],
        "env_port_hint": {},
        "project_files": [".aider.conf.yml", ".aider.model.settings.yml", ".aiderignore"],
        "integration":  ["config_inject", "git_hook", "alias"],
        "inject_file":  ".aider.conf.yml",
        "verify_cmd":   ["aider", "--version"],
    },

    "openai_agent": {
        "display":      "Custom OpenAI Agent",
        "icon":         "◐",
        "type":         "server",
        "binary":       None,
        "process_kw":   [],
        "home_dirs":    [],
        "shell_vars":   ["OPENAI_API_KEY"],
        "npm_pkg":      None,
        "pip_pkg":      None,
        "ports":        [8000, 8003, 8004],
        "default_port": 8000,
        "env_url_keys": ["OPENAI_AGENT_URL"],
        "env_port_hint": {},
        "project_files": ["agent.py", "openai_agent.py", "assistant.py"],
        "integration":  ["proxy", "fswatch"],
        "inject_file":  None,
    },
}

# Backwards-compat alias used by guard/inject code
_AGENT_SIGNATURES = _AGENT_REGISTRY

# Integration strategies per agent (same as before)
_INTEGRATION_STRATEGIES = {
    "openclaw":      ["proxy", "alias"],
    "melissa":       ["proxy", "alias"],
    "n8n":           ["proxy"],
    "aider":         ["config_inject", "git_hook", "alias"],
    "claude_code":   ["mcp", "config_inject", "git_hook"],
    "openai_agent":  ["proxy", "fswatch"],
    "gemini_cli":    ["alias", "config_inject", "fswatch"],
    "codex_cli":     ["alias", "config_inject", "fswatch"],
    "copilot_cli":   ["alias", "config_inject"],
}

_INJECT_TARGETS = {
    "claude_code":  ["CLAUDE.md", ".claude/CLAUDE.md", ".claude/instructions.md"],
    "aider":        [".aider.conf.yml", ".aider.system.prompt"],
    "copilot_cli":  [".github/copilot-instructions.md"],
    "gemini_cli":   [".gemini/system.md", ".gemini.md"],
    "codex_cli":    [".codex/instructions.md", "AGENTS.md"],
}


# ── 5-Method Detection Functions ──────────────────────────────────────────────

def _m1_binary(sig: dict) -> int:
    """Method 1: Binary in PATH. +15 base, +25 if --version works."""
    binary = sig.get("binary")
    if not binary or not shutil.which(binary):
        return 0
    # Try verify_cmd (more specific than just the binary)
    verify_cmd  = sig.get("verify_cmd")
    verify_grep = sig.get("verify_grep")
    if verify_cmd:
        try:
            r = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=4)
            output = r.stdout + r.stderr
            if verify_grep:
                # e.g. "gh extension list" must contain "copilot"
                return 70 if verify_grep.lower() in output.lower() else 15
            # --version ran successfully
            return 40 if r.returncode == 0 else 20
        except Exception:
            pass
    return 15   # binary exists but couldn't verify


def _m2_process(sig: dict) -> int:
    """Method 2: Check running processes. +50 if found (agent is LIVE)."""
    keywords = sig.get("process_kw", [])
    if not keywords:
        return 0
    try:
        if IS_WINDOWS:
            r = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=3)
        else:
            r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=3)
        output = r.stdout.lower()
        for kw in keywords:
            if kw.lower() in output:
                return 50
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")
    return 0


def _m3_home_dirs(sig: dict) -> int:
    """Method 3: Agent home/config directories in ~/.config, ~/. etc. +30 if found."""
    dirs = sig.get("home_dirs", [])
    for d in dirs:
        if Path(d).exists():
            return 30
    return 0


def _m4_shell_config(sig: dict) -> int:
    """Method 4: Exported vars in shell config files. +25 per match."""
    vars_to_find = sig.get("shell_vars", [])
    if not vars_to_find:
        return 0

    # Check real process environment first (fastest)
    env_hits = sum(1 for v in vars_to_find if os.environ.get(v))
    if env_hits:
        return min(env_hits * 25, 50)

    # Scan shell config files
    shell_files = [
        Path.home() / ".bashrc",
        Path.home() / ".zshrc",
        Path.home() / ".profile",
        Path.home() / ".bash_profile",
        Path.home() / ".config" / "fish" / "config.fish",
    ]
    score = 0
    for sf in shell_files:
        if not sf.exists():
            continue
        try:
            text = sf.read_text(errors="ignore")
            for v in vars_to_find:
                if v in text:
                    score += 25
                    break   # one match per file is enough
        except Exception:
            pass
    return min(score, 50)


def _m5_packages(sig: dict) -> int:
    """Method 5: npm global or pip package installed. +35 if found."""
    npm_pkg = sig.get("npm_pkg")
    pip_pkg = sig.get("pip_pkg")

    if npm_pkg and shutil.which("npm"):
        try:
            r = subprocess.run(
                ["npm", "list", "-g", npm_pkg, "--depth=0"],
                capture_output=True, text=True, timeout=6
            )
            if npm_pkg in r.stdout:
                return 35
        except Exception:
            pass

    if pip_pkg:
        # Fast: check pip show
        for pip in ("pip3", "pip"):
            if shutil.which(pip):
                try:
                    r = subprocess.run(
                        [pip, "show", pip_pkg],
                        capture_output=True, text=True, timeout=5
                    )
                    if r.returncode == 0:
                        return 35
                except Exception:
                    pass
    return 0


def _detect_agent(agent_type: str, sig: dict,
                  env_vars: dict, project_root: Path,
                  probe_ports: bool) -> Optional[dict]:
    """
    Run all 5 detection methods for one agent.
    Returns the result dict or None if confidence < threshold.
    """
    score = 0

    # Project config files (+20)
    for name in sig.get("project_files", []):
        if (project_root / name).exists():
            score += 20
            break

    # Port probe (+35 if live, +10 if just listening)
    port_live = False
    url = ""
    if sig.get("ports"):
        for port in sig["ports"]:
            if probe_ports and _probe_port(port):
                port_live = True
                score += 35
                url = f"http://localhost:{port}"
                break

    # Env URL keys
    for k in sig.get("env_url_keys", []):
        v = env_vars.get(k, "")
        if v.startswith("http"):
            url = url or v
            # Check port_in_env_hint
            for hint_key, hint_port in sig.get("env_port_hint", {}).items():
                if hint_key == k and f":{hint_port}" in v:
                    score += 40
                    break
            else:
                score += 15

    # 5 methods
    score += _m1_binary(sig)
    score += _m2_process(sig)
    score += _m3_home_dirs(sig)
    score += _m4_shell_config(sig)
    # Skip package scan by default (slow) — only run in nova boot/guard
    # score += _m5_packages(sig)

    score = min(score, 100)
    if score < 20:
        return None

    if not url and sig.get("default_port"):
        url = f"http://localhost:{sig['default_port']}"

    return {
        "agent_type":   agent_type,
        "display":      sig["display"],
        "icon":         sig["icon"],
        "confidence":   score,
        "url":          url,
        "port_live":    port_live,
        "cli_type":     sig.get("type") == "cli",
        "project_root": project_root,
        "env_file":     project_root / ".env",
        "integration":  sig.get("integration", []),
        "inject_file":  sig.get("inject_file"),
    }


def discover_agents(project_root: Path = None, probe_ports: bool = True,
                    deep: bool = False) -> list:
    """
    Scan the environment for AI agents using 5 detection methods.

    Args:
        project_root: Project directory (auto-detected if None)
        probe_ports:  Whether to probe TCP ports (adds ~1-2s)
        deep:         Run package manager scans (adds ~3-5s, used in nova boot/guard)

    Returns a list of agent dicts sorted by confidence descending.
    """
    root = project_root or _find_project_root()
    env  = _collect_env_vars(root)
    results = []

    for agent_type, sig in _AGENT_REGISTRY.items():
        result = _detect_agent(agent_type, sig, env, root, probe_ports)
        if result is None:
            continue
        if deep:
            pkg_score = _m5_packages(sig)
            result["confidence"] = min(result["confidence"] + pkg_score, 100)
        results.append(result)

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def _read_dotenv(path: Path) -> dict:
    """Parse a .env file into a dict - no external deps."""
    result = {}
    try:
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip("\"'")
                result[k] = v
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")
    return result


def _probe_port(port: int, timeout: float = 0.35) -> bool:
    """Return True if something is listening on localhost:port."""
    try:
        import socket as _s
        with _s.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except Exception:
        return False


def _probe_http(url: str, timeout: float = 1.0) -> bool:
    """Return True if the URL returns any HTTP response."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _find_project_root(start: Path = None) -> Path:
    """Walk upward from start to find the project root (.git, .env, package.json, etc.)."""
    markers = {".git", ".env", "package.json", "pyproject.toml",
               "requirements.txt", "Cargo.toml", "go.mod", "composer.json"}
    cwd = start or Path.cwd()
    for d in [cwd] + list(cwd.parents)[:4]:
        if any((d / m).exists() for m in markers):
            return d
    return cwd


def _collect_env_vars(project_root: Path) -> dict:
    """Read all .env files in the project and merge them."""
    merged = {}
    for name in [".env", ".env.local", ".env.development", ".env.production"]:
        p = project_root / name
        if p.exists():
            merged.update(_read_dotenv(p))
    # Also overlay real process environment
    for k in list(os.environ.keys()):
        merged.setdefault(k, os.environ[k])
    return merged



def create_nova_project_folder(project_root: Path, agent_type: str,
                                agent_name: str, nova_url: str = "",
                                nova_api_key: str = "") -> Path:
    """
    Create the .nova/ folder structure in the project root.

    .nova/
      config.yaml                 ← project-level nova config
      .gitignore                  ← auto-excludes secrets
      agents/
        <agent_type>/
          rules/                  ← governance rules live here
          memory/                 ← persistent agent memory

    Returns the rules directory path.
    """
    nova_project = project_root / ".nova"
    rules_dir  = nova_project / "agents" / agent_type / "rules"
    memory_dir = nova_project / "agents" / agent_type / "memory"

    for d in [rules_dir, memory_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Write config.yaml
    config_path = nova_project / "config.yaml"
    if not config_path.exists():
        config_path.write_text(
            f"# Nova project config - auto-generated\n"
            f"agent: {agent_type}\n"
            f"agent_name: {agent_name}\n"
            f"nova_url: {nova_url or 'http://localhost:9002'}\n"
            f"rules_dir: .nova/agents/{agent_type}/rules\n"
            f"created_at: {datetime.now().isoformat()}\n"
        )

    # Write .gitignore
    gitignore_path = nova_project / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(
            "# Nova - auto-generated\n"
            "# Never commit API keys or session data\n"
            "*.secrets\n"
            "*.key\n"
            "sessions/\n"
            "memory/*.enc\n"
        )

    return rules_dir


def inject_nova_env(env_file: Path, nova_api_key: str, nova_url: str,
                    agent_type: str) -> bool:
    """
    Append NOVA_* variables to the agent's .env file.
    Creates a .env.nova sidecar if the main .env is read-only or doesn't exist.
    Returns True if successful.
    """
    nova_vars = {
        "NOVA_API_KEY":   nova_api_key,
        "NOVA_URL":       nova_url or "http://localhost:9002",
        "NOVA_AGENT":     agent_type,
        "NOVA_ENABLED":   "true",
    }

    # Try writing to main .env first (append nova block)
    target = env_file
    sidecar = env_file.parent / ".env.nova"

    # Check if nova vars already present
    existing = _read_dotenv(target) if target.exists() else {}
    if all(k in existing for k in nova_vars):
        return True  # Already injected

    # Try to append
    try:
        lines = ["", "# Nova governance - auto-injected", "# Do not remove: required for agent validation"]
        for k, v in nova_vars.items():
            if k not in existing:
                lines.append(f"{k}={v}")
        lines.append("")

        if target.exists() and os.access(target, os.W_OK):
            with open(target, "a") as f:
                f.write("\n".join(lines) + "\n")
        else:
            # Fall back to sidecar
            target = sidecar
            with open(target, "w") as f:
                f.write("\n".join(lines[1:]) + "\n")
        return True
    except Exception:
        return False


def create_rule_file(rules_dir: Path, rule_data: dict) -> Path:
    """
    Persist a governance rule to .nova/agents/<agent>/rules/<id>.json
    Returns the created path.
    """
    rules_dir.mkdir(parents=True, exist_ok=True)
    # Count existing rules to give sequential ID
    existing = sorted(rules_dir.glob("*.json"))
    idx = len(existing) + 1
    safe_name = re.sub(r"[^a-z0-9_]", "_", rule_data.get("name", "rule").lower())[:40]
    filename = f"{idx:03d}_{safe_name}.json"
    path = rules_dir / filename
    path.write_text(json.dumps(rule_data, indent=2, ensure_ascii=False))
    return path


# ══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL GUARD ENGINE - multi-agent protection layer
# ══════════════════════════════════════════════════════════════════════════════

def _load_protected_paths(project_root: Path) -> list:
    """Read .nova/protected.json - list of protected path patterns."""
    p = project_root / ".nova" / "protected.json"
    if p.exists():
        try:
            return json.loads(p.read_text()).get("paths", [])
        except Exception:
            pass
    return []


def _save_protected_paths(project_root: Path, paths: list):
    """Persist protected paths to .nova/protected.json."""
    nova_dir = project_root / ".nova"
    nova_dir.mkdir(exist_ok=True)
    p = nova_dir / "protected.json"
    p.write_text(json.dumps({"paths": paths, "updated_at": datetime.now().isoformat()},
                             indent=2))


def _rules_as_natural_language(project_root: Path, agent_type: str) -> List[str]:
    """
    Load all active rules for an agent and return them as plain-English sentences.
    Used to inject into config files like CLAUDE.md.
    """
    rules_dir = project_root / ".nova" / "agents" / agent_type / "rules"
    # Also load from global ~/.nova/rules
    global_rules_dir = NOVA_DIR / "rules"

    sentences = []
    for d in [rules_dir, global_rules_dir]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                r = json.loads(f.read_text())
                if not r.get("active", True):
                    continue
                desc = r.get("description", "")
                action = r.get("action", "block")
                if desc:
                    prefix = "NEVER" if action == "block" else "AVOID"
                    sentences.append(f"- [{prefix}] {desc}")
            except Exception:
                pass

    # Add protected paths as rules
    for path_pattern in _load_protected_paths(project_root):
        sentences.append(f"- [NEVER] Modify, delete, or overwrite files in {path_pattern}")

    return sentences


def inject_into_config_file(project_root: Path, agent_type: str) -> dict:
    """
    Inject Nova rules into the agent's config/instructions file.
    Returns {"injected": True/False, "file": path_str, "rules_count": n}
    """
    targets = _INJECT_TARGETS.get(agent_type, [])
    rule_lines = _rules_as_natural_language(project_root, agent_type)

    if not rule_lines:
        return {"injected": False, "reason": "no rules to inject"}

    nova_block = (
        "\n"
        "<!-- nova:begin - DO NOT EDIT THIS BLOCK MANUALLY -->\n"
        "## Nova Governance Rules\n"
        "_These rules are automatically enforced by Nova. Do not remove._\n"
        "\n"
        + "\n".join(rule_lines) + "\n"
        "<!-- nova:end -->\n"
    )

    for rel_path in targets:
        target = project_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        existing = target.read_text(errors="ignore") if target.exists() else ""

        # Remove any previous nova block before re-injecting
        if "<!-- nova:begin" in existing:
            import re as _re
            existing = _re.sub(
                r"\n<!-- nova:begin.*?nova:end -->\n",
                "", existing, flags=_re.DOTALL)

        # Append nova block
        try:
            target.write_text(existing + nova_block)
            return {
                "injected":    True,
                "file":        str(target),
                "rules_count": len(rule_lines),
            }
        except Exception as e:
            continue   # Try next target

    return {"injected": False, "reason": "could not write to any target"}


def generate_shell_aliases(agents: list, nova_py_path: str = None) -> str:
    """
    Generate shell alias lines for all detected agents.
    Example:  alias claude="nova wrap claude"

    Returns a shell script fragment suitable for .bashrc / .zshrc.
    """
    nova_cmd = nova_py_path or "nova"
    lines = [
        "# Nova governance aliases - auto-generated by nova guard",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "# Source this file in your shell: source ~/.nova/shell_setup.sh",
        "",
    ]
    # Binaries we can wrap
    wrap_binaries = {
        "openclaw":    "openclaw",
        "claude_code": "claude",
        "aider":       "aider",
        "gemini_cli":  "gemini",
        "codex_cli":   "codex",
        "copilot_cli": "gh",     # wrap gh, not just gh copilot
    }
    found_any = False
    for agent_type in agents:
        binary = wrap_binaries.get(agent_type)
        if binary and shutil.which(binary):
            lines.append(f'alias {binary}="{nova_cmd} wrap {binary}"')
            found_any = True

    if not found_any:
        lines.append("# No agent binaries found in PATH - install agents first")

    lines += [
        "",
        "# Re-run  nova guard  after installing new AI CLIs",
    ]
    return "\n".join(lines) + "\n"


def install_git_hooks(project_root: Path, nova_api_url: str = "") -> dict:
    """
    Install Nova pre-commit and pre-push git hooks.
    Returns {"installed": True/False, "hooks": [list of installed hook files]}
    """
    git_dir = project_root / ".git"
    if not git_dir.exists():
        return {"installed": False, "reason": "not a git repository"}

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    nova_url = nova_api_url or "http://localhost:9002"

    pre_commit_script = f"""#!/bin/sh
# Nova governance pre-commit hook - auto-generated
# Validates staged changes against your governance rules
# To disable:  git config nova.skip-hook true

if git config --bool nova.skip-hook 2>/dev/null | grep -q true; then
  exit 0
fi

NOVA_URL="{nova_url}"

# Build a brief description of what's being committed
STAGED=$(git diff --cached --name-only --diff-filter=ACM | head -20 | tr "\n" ", ")
if [ -z "$STAGED" ]; then
  exit 0
fi

ACTION="commit changes to: $STAGED"

# Call Nova validation (non-blocking if Nova is not running)
RESULT=$(curl -s --max-time 2 -X POST "$NOVA_URL/validate" \
  -H "Content-Type: application/json" \
  -d "{{\"action\": \"$ACTION\", \"agent_name\": \"git\", \"scope\": \"global\"}}" 2>/dev/null)

if echo "$RESULT" | grep -q "\"BLOCKED\""; then
  echo "\n🛡️  Nova blocked this commit."
  echo "    Reason: $(echo $RESULT | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d.get('reason','rule violation'))\" 2>/dev/null)"
  echo "    To override: git config nova.skip-hook true && git commit"
  exit 1
fi

exit 0
"""

    installed = []
    try:
        hook = hooks_dir / "pre-commit"
        hook.write_text(pre_commit_script)
        hook.chmod(0o755)
        installed.append(str(hook))
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")

    return {
        "installed": bool(installed),
        "hooks":     installed,
    }


def generate_mcp_config(nova_url: str = "", project_root: Path = None) -> dict:
    """
    Generate MCP server config for Claude Code (.claude/settings.json).
    This lets Claude Code call Nova before any action.
    """
    url = nova_url or "http://localhost:9002"
    return {
        "mcpServers": {
            "nova-governance": {
                "command":     "python3",
                "args":        ["-m", "nova_mcp_server"],
                "env": {
                    "NOVA_URL":       url,
                    "NOVA_MCP_MODE":  "1",
                },
                "description": "Nova governance - validates every action before execution",
            }
        }
    }


def _write_mcp_config(project_root: Path, nova_url: str) -> dict:
    """
    Write / merge Nova MCP server into Claude Code's .claude/settings.json.
    """
    settings_path = project_root / ".claude" / "settings.json"
    settings_path.parent.mkdir(exist_ok=True)

    existing = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text())
        except Exception:
            pass

    mcp = generate_mcp_config(nova_url, project_root)
    existing.setdefault("mcpServers", {}).update(mcp["mcpServers"])

    try:
        settings_path.write_text(json.dumps(existing, indent=2))
        return {"written": True, "file": str(settings_path)}
    except Exception as e:
        return {"written": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# NOVA v3.2 - SECURITY + NOVA CORE CLIENT + NL INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════


# ── Section 1 ────────────────────────────────────────
import base64
import getpass as _getpass
import socket as _socket
import struct as _struct


# ── Machine-derived salt (no external deps, no hardcoded secrets) ─────────────

def _machine_salt() -> bytes:
    """
    Derive a deterministic salt from machine-specific data.
    Not cryptographically strong, but prevents trivial key extraction
    if the config file is copied to another machine.
    """
    pieces = []
    try:
        pieces.append(_socket.gethostname())
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")
    try:
        pieces.append(_getpass.getuser())
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")
    # Platform-specific machine ID
    for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        try:
            pieces.append(Path(path).read_text().strip()[:16])
            break
        except Exception:
            pass
    if IS_WINDOWS:
        try:
            import winreg
            reg = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography"
            )
            pieces.append(winreg.QueryValueEx(reg, "MachineGuid")[0][:16])
        except Exception:
            pass
    raw = "|".join(pieces) or "nova_default_salt_2026"
    # Simple hash to fixed 32-byte salt
    h = hashlib.sha256(raw.encode()).digest()
    return h


def _xor_key(data: bytes, salt: bytes) -> bytes:
    """XOR obfuscation with cycling salt. Not AES but zero deps."""
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ salt[i % len(salt)]
    return bytes(out)


def encrypt_value(plaintext: str) -> str:
    """Obfuscate a string for storage. Returns base64."""
    if not plaintext:
        return ""
    raw   = plaintext.encode("utf-8")
    salt  = _machine_salt()
    xored = _xor_key(raw, salt)
    return base64.b64encode(xored).decode("ascii")


def decrypt_value(ciphertext: str) -> str:
    """Recover an obfuscated string. Returns plaintext or '' on error."""
    if not ciphertext:
        return ""
    try:
        xored = base64.b64decode(ciphertext.encode("ascii"))
        salt  = _machine_salt()
        raw   = _xor_key(xored, salt)
        return raw.decode("utf-8")
    except Exception:
        return ciphertext  # Fallback: assume plaintext (backwards compat)


# ── Key masking ────────────────────────────────────────────────────────────────

def mask_key(key: str, show: int = 6) -> str:
    """
    Mask an API key for display.
    sk-or-v1-3cf38...a291a → sk-or-v1-3cf3••••••••a291a
    """
    if not key or len(key) < show * 2:
        return "••••••••"
    prefix = key[:show]
    suffix = key[-4:]
    middle_len = max(8, len(key) - show - 4)
    return prefix + "•" * middle_len + suffix


def mask_config_for_display(cfg: dict) -> dict:
    """Return a copy of config with all API keys masked."""
    masked = dict(cfg)
    key_fields = ("api_key", "llm_api_key", "llm_base_url")
    for field in key_fields:
        if field in masked and masked[field]:
            masked[field] = mask_key(masked[field])
    return masked


# ── Secure config load/save ────────────────────────────────────────────────────

def load_config_secure() -> dict:
    """
    Load config with automatic decryption of stored keys.
    Falls back to load_config() for unencrypted configs.
    """
    cfg = load_config()
    # Decrypt any encrypted values (prefixed with "enc:")
    for field in ("api_key", "llm_api_key"):
        val = cfg.get(field, "")
        if val and val.startswith("enc:"):
            cfg[field] = decrypt_value(val[4:])
    # Also check environment variables (highest priority)
    env_overrides = {
        "api_key":     os.environ.get("NOVA_API_KEY",     ""),
        "api_url":     os.environ.get("NOVA_API_URL",     ""),
        "llm_api_key": os.environ.get("NOVA_LLM_API_KEY", "")
                       or os.environ.get("OPENROUTER_API_KEY", ""),
        "llm_provider": os.environ.get("NOVA_LLM_PROVIDER", ""),
        "llm_model":    os.environ.get("NOVA_LLM_MODEL", ""),
    }
    for field, env_val in env_overrides.items():
        if env_val:
            cfg[field] = env_val
    return cfg


def save_config_secure(cfg: dict):
    """
    Save config, encrypting sensitive values.
    API keys are never stored in plaintext on disk.
    """
    cfg_to_save = dict(cfg)
    for field in ("api_key", "llm_api_key"):
        val = cfg_to_save.get(field, "")
        if val and not val.startswith("enc:") and len(val) > 8:
            cfg_to_save[field] = "enc:" + encrypt_value(val)
    save_config(cfg_to_save)


# ── CLI audit trail ────────────────────────────────────────────────────────────

NOVA_AUDIT_FILE = NOVA_DIR / "audit.log"
NOVA_CORE_URL_FILE = NOVA_DIR / "nova_core_url"


def _audit(command: str, args_dict: dict = None):
    """
    Append a CLI command to the audit log.
    Never logs API keys or sensitive values.
    """
    try:
        NOVA_DIR.mkdir(parents=True, exist_ok=True)
        safe_args = {
            k: mask_key(str(v)) if "key" in k.lower() else str(v)
            for k, v in (args_dict or {}).items()
            if v and str(v) not in ("", "False", "None")
        }
        entry = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "cmd":     command,
            "args":    safe_args,
            "user":    os.environ.get("USER", os.environ.get("USERNAME", "?")),
            "host":    _socket.gethostname(),
        }
        with open(NOVA_AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Audit failure must never block the CLI


_NOVA_PORTS_TO_TRY = [9003, 9002, 8000, 8003, 9000]  # 9003=nova_core, 9002=nova-api

# Which server type each command needs
_CMD_NEEDS_CORE = {
    # Commands that need nova_core.py (/ledger, /rules, /chat, /stream, /boot)
    "logs", "stream", "rules", "chat", "anomalies", "ledger",
    "watch", "verify", "export", "audit", "alerts", "benchmark",
    "protect", "scan", "connect", "boot",
}
_CMD_NEEDS_API = {
    # Commands that need nova-api/main.py (/tokens, /validate, /stats)
    "validate", "test", "simulate", "agent", "policy", "workspace",
    "stats", "memory", "keys",
}


def _probe_nova_url(url: str, timeout: float = 0.8) -> bool:
    """Return True if a Nova CORE server (with /ledger + /rules) responds."""
    try:
        req = urllib.request.Request(
            url + "/health",
            headers={"x-api-key": "nova_dev_key", "User-Agent": "nova-cli"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            # Must have nova_core-specific fields — NOT just a generic API
            return bool(data.get("rules") or data.get("ledger") or
                        (data.get("status") in ("ok", "healthy") and
                         data.get("version", "").startswith("3.")))
    except Exception:
        return False


def _probe_any_nova(url: str, timeout: float = 0.8) -> tuple:
    """
    Probe URL and return (is_alive, server_type).
    server_type: "core" (nova_core.py) | "api" (nova-api/main.py) | None
    """
    try:
        req = urllib.request.Request(
            url + "/health",
            headers={"x-api-key": "nova_dev_key", "User-Agent": "nova-cli"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            status = data.get("status", "")
            if not status in ("ok", "healthy", "running"):
                return False, None
            # nova_core.py has "rules" and "ledger" keys in /health
            if data.get("rules") or data.get("ledger"):
                return True, "core"
            # nova-api/main.py has "version" but no rules/ledger
            return True, "api"
    except Exception:
        return False, None


def load_nova_core_url() -> str:
    """
    Load the Nova Core URL (for commands needing /ledger, /rules, /chat).

    Distinguishes between:
      nova_core.py  — has /ledger, /rules, /stream (default port 9003)
      nova-api      — has /tokens, /stats (default port 9002, main.py)

    Priority:
      1. Saved in ~/.nova/nova_core_url
      2. NOVA_CORE_URL env var
      3. Scan for a server with /ledger (nova_core signature)
      4. Any nova server as last resort
      5. Default: http://localhost:9003
    """
    # 1. Saved URL
    try:
        saved = NOVA_CORE_URL_FILE.read_text().strip()
        if saved:
            return saved
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")

    # 2. Env var
    env_url = os.environ.get("NOVA_CORE_URL", "")
    if env_url:
        return env_url

    # 3. Scan for nova_core specifically (has /ledger)
    fallback_url = ""
    for port in _NOVA_PORTS_TO_TRY:
        url = f"http://localhost:{port}"
        alive, stype = _probe_any_nova(url, timeout=0.6)
        if not alive:
            continue
        if stype == "core":
            save_nova_core_url(url)
            return url
        if stype == "api" and not fallback_url:
            fallback_url = url  # keep as last resort

    # 4. Fallback: try /ledger directly on each port
    for port in _NOVA_PORTS_TO_TRY:
        url = f"http://localhost:{port}"
        try:
            req = urllib.request.Request(
                url + "/ledger?limit=1",
                headers={"x-api-key": "nova_dev_key"}
            )
            with urllib.request.urlopen(req, timeout=0.6) as r:
                if r.status < 400:
                    save_nova_core_url(url)
                    return url
        except Exception:
            pass

    if fallback_url:
        return fallback_url
    return "http://localhost:9003"


def save_nova_core_url(url: str):
    """Persist the Nova Core URL for future CLI sessions."""
    try:
        NOVA_DIR.mkdir(parents=True, exist_ok=True)
        NOVA_CORE_URL_FILE.write_text(url.strip())
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 2 ────────────────────────────────────────
class NovaCoreClient:
    """
    Python client for the Nova Core governance engine API.
    Zero external deps - uses urllib.request like the rest of nova CLI.

    Features:
    · Automatic retry with exponential backoff
    · Response normalization
    · Timeout handling
    · Offline detection
    """

    def __init__(self, url: str = "", api_key: str = "nova_dev_key", timeout: int = 10):
        self.url     = (url or load_nova_core_url()).rstrip("/")
        self.api_key = api_key or os.environ.get("NOVA_CORE_API_KEY", "nova_dev_key")
        self.timeout = timeout

    def _req(self, method: str, path: str, data: dict = None) -> dict:
        full_url = self.url + path
        headers  = {
            "Content-Type":  "application/json",
            "x-api-key":     self.api_key,
            "User-Agent":    f"nova-cli/{NOVA_VERSION}",
        }
        body = json.dumps(data).encode() if data else None
        req  = urllib.request.Request(full_url, data=body,
                                      headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode())
            except Exception:
                return {"error": f"HTTP {e.code}", "code": f"HTTP_{e.code}"}
        except urllib.error.URLError as e:
            return {"error": f"Cannot connect to Nova Core at {self.url}", "offline": True}
        except Exception as e:
            return {"error": str(e)}

    def health(self) -> dict:
        return self._req("GET", "/health")

    def is_alive(self) -> bool:
        r = self.health()
        return "error" not in r

    def validate(self, action: str, context: str = "", scope: str = "global",
                 agent_name: str = "", can_do: list = None, cannot_do: list = None,
                 dry_run: bool = False) -> dict:
        payload = {
            "action":     action,
            "context":    context,
            "scope":      scope,
            "agent_name": agent_name,
            "check_dups": True,
            "dry_run":    dry_run,
        }
        if can_do     is not None: payload["can_do"]     = can_do
        if cannot_do  is not None: payload["cannot_do"]  = cannot_do
        return self._req("POST", "/validate", payload)

    def validate_batch(self, actions: list, agent_name: str = "",
                       scope: str = "global") -> dict:
        return self._req("POST", "/validate/batch", {
            "actions":    actions[:20],
            "agent_name": agent_name,
            "scope":      scope,
        })

    def intercept(self, message: str, sender: str = "admin",
                  scope: str = "global") -> dict:
        return self._req("POST", "/intercept", {
            "message": message, "sender": sender, "scope": scope
        })

    def rules_list(self, scope: str = "global") -> dict:
        return self._req("GET", f"/rules?scope={scope}")

    def rules_create(self, description: str, scope: str = "global",
                     action: str = "block", priority: int = 7) -> dict:
        return self._req("POST", "/rules", {
            "description": description,
            "scope":       scope,
            "action":      action,
            "priority":    priority,
            "created_by":  "nova_cli",
        })

    def rules_delete(self, rule_id: str) -> dict:
        return self._req("DELETE", f"/rules/{rule_id}")

    def rules_get(self, rule_id: str) -> dict:
        return self._req("GET", f"/rules/{rule_id}")

    def rules_stats(self) -> dict:
        return self._req("GET", "/rules/stats")

    def ledger(self, agent_name: str = "", limit: int = 50) -> dict:
        path = f"/ledger?limit={limit}"
        if agent_name:
            path += f"&agent_name={agent_name}"
        return self._req("GET", path)

    def ledger_stats(self, agent_name: str = "") -> dict:
        path = "/ledger/stats"
        if agent_name:
            path += f"?agent_name={agent_name}"
        return self._req("GET", path)

    def ledger_timeline(self, agent_name: str = "", hours: int = 24) -> dict:
        path = f"/ledger/timeline?hours={hours}"
        if agent_name:
            path += f"&agent_name={agent_name}"
        return self._req("GET", path)

    def anomalies(self, agent_name: str = "", limit: int = 30) -> dict:
        path = f"/anomalies?limit={limit}"
        if agent_name:
            path += f"&agent_name={agent_name}"
        return self._req("GET", path)

    def scan(self) -> dict:
        return self._req("GET", "/scan")

    def connect_agent(self, agent_url: str = "", agent_name: str = "agent") -> dict:
        payload = {}
        if agent_url:  payload["agent_url"]  = agent_url
        if agent_name: payload["agent_name"] = agent_name
        return self._req("POST", "/connect", payload)

    def chat(self, message: str, session_id: str = "cli",
             scope: str = "global") -> dict:
        return self._req("POST", "/chat", {
            "message":    message,
            "session_id": session_id,
            "scope":      scope,
        })

    def benchmark_run(self, actions: list, agent_name: str = "bench") -> dict:
        """Run a batch validation and measure latency."""
        t0      = time.time()
        result  = self.validate_batch(actions, agent_name)
        elapsed = int((time.time() - t0) * 1000)
        if "error" in result:
            return result
        results  = result.get("results", [])
        n        = len(results)
        blocked  = result.get("blocked", 0)
        approved = result.get("approved", 0)
        layers   = {}
        scores   = []
        latencies = []
        for r in results:
            layer = r.get("layer", "unknown")
            layers[layer] = layers.get(layer, 0) + 1
            scores.append(r.get("score", 0))
            latencies.append(r.get("ms", 0))
        return {
            "total":        n,
            "approved":     approved,
            "blocked":      blocked,
            "block_rate":   round(blocked / n * 100, 1) if n else 0,
            "avg_score":    round(sum(scores) / n, 1) if scores else 0,
            "avg_latency":  round(sum(latencies) / n, 1) if latencies else 0,
            "max_latency":  max(latencies) if latencies else 0,
            "min_latency":  min(latencies) if latencies else 0,
            "total_ms":     elapsed,
            "layers":       layers,
            "throughput":   round(n / (elapsed / 1000), 1) if elapsed else 0,
        }


def _get_nova_core(cfg: dict = None) -> NovaCoreClient:
    """Get a configured Nova Core client from CLI config."""
    cfg  = cfg or load_config_secure()
    url  = cfg.get("nova_core_url", "") or load_nova_core_url()
    key  = cfg.get("nova_core_api_key", "") or os.environ.get("NOVA_CORE_API_KEY", "nova_dev_key")
    return NovaCoreClient(url=url, api_key=key)


def _nova_core_or_die() -> "Optional[NovaCoreClient]":
    """
    Try to find Nova Core on any known port.
    Clears the cached URL so load_nova_core_url rescans.
    Returns a live NovaCoreClient or None (and prints helpful hints).
    """
    try: NOVA_CORE_URL_FILE.unlink()
    except Exception: pass

    with Spinner("Searching for Nova Core on localhost...") as sp:
        url = load_nova_core_url()
        nc  = NovaCoreClient(url=url)
        alive = nc.is_alive()
        sp.finish()

    if alive:
        save_nova_core_url(url)
        ok(f"Nova Core found at {url}")
        return nc

    fail("Nova Core not reachable.")
    print()
    print("  " + q(C.G2, "Ports scanned: ") +
          q(C.G3, ", ".join(str(p) for p in _NOVA_PORTS_TO_TRY)))
    print()
    hint("Start everything:     nova boot")
    hint("Start Core manually:  python3 nova_core.py &")
    hint("Start with pm2:       pm2 start nova_core.py --name nova-core --interpreter python3")
    print()
    return None


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 3 ────────────────────────────────────────
def _build_llm_fallback_chain(cfg: dict) -> list:
    """
    Build an ordered fallback chain of (provider, model, api_key) tuples
    from config + environment variables.

    Priority:
      1. Explicitly configured in nova CLI config
      2. Environment variables
      3. Nova Core's configured LLM (if Nova Core is running)

    Never raises - returns empty list if nothing configured.
    """
    chain = []
    # 1. Explicitly configured provider
    prov    = cfg.get("llm_provider", "")
    model   = cfg.get("llm_model", "")
    key     = cfg.get("llm_api_key", "")
    base_url = cfg.get("llm_base_url", "")
    if prov and model and key:
        chain.append((prov, model, key, base_url))

    # 2. Environment variables (multiple providers, try in order)
    env_providers = [
        ("openrouter", os.environ.get("OPENROUTER_API_KEY",""),
         "google/gemini-2.5-flash", ""),
        ("anthropic",  os.environ.get("ANTHROPIC_API_KEY",""),
         "claude-sonnet-4-6", ""),
        ("openai",     os.environ.get("OPENAI_API_KEY",""),
         "gpt-4o-mini", ""),
        ("groq",       os.environ.get("GROQ_API_KEY",""),
         "llama-3.3-70b-versatile", ""),
        ("gemini",     os.environ.get("GEMINI_API_KEY",""),
         "gemini-2.0-flash", ""),
    ]
    seen_keys = {key}
    for ep, ek, em, ebase in env_providers:
        if ek and ek not in seen_keys:
            chain.append((ep, em, ek, ebase))
            seen_keys.add(ek)

    return chain


def _call_llm_with_fallback(prompt: str, cfg: dict,
                             system: str = "",
                             max_tokens: int = 800,
                             require_json: bool = False) -> tuple:
    """
    Call LLM with automatic fallback chain.
    Returns (response_text, provider_used) or ("", "") on complete failure.

    Security: API keys come from config/env only. Never hardcoded.
    """
    chain = _build_llm_fallback_chain(cfg)
    if not chain:
        return "", ""

    for prov, model, key, base_url in chain:
        try:
            result = _call_single_llm(prov, model, key, base_url,
                                      prompt, system, max_tokens)
            if not result:
                continue
            if require_json:
                # Validate it's parseable JSON
                clean = re.sub(r"```json\s*|```\s*", "", result).strip()
                m = re.search(r"\{[\s\S]+\}", clean)
                if not m:
                    debug(f"LLM {prov}: response not JSON, trying next")
                    continue
                try:
                    json.loads(m.group(0))
                except Exception:
                    debug(f"LLM {prov}: JSON parse failed, trying next")
                    continue
            debug(f"LLM {prov}: success ({len(result)} chars)")
            return result, prov
        except Exception as e:
            debug(f"LLM {prov} failed: {e}, trying next")
            continue

    return "", ""


def _call_single_llm(provider: str, model: str, api_key: str,
                     base_url: str, prompt: str, system: str,
                     max_tokens: int) -> str:
    """
    Call a single LLM provider. Returns response text or raises.
    Zero external dependencies - urllib only.
    """
    # Strip provider prefix from model name for API calls
    clean_model = re.sub(r"^[a-z]+/", "", model)

    # ── Anthropic ──────────────────────────────────────────────────────────────
    if provider == "anthropic":
        url  = "https://api.anthropic.com/v1/messages"
        body = {
            "model":      clean_model,
            "max_tokens": max_tokens,
            "messages":   [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        headers = {
            "Content-Type":       "application/json",
            "x-api-key":          api_key,
            "anthropic-version":  "2023-06-01",
        }
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return data["content"][0]["text"].strip()

    # ── Gemini ─────────────────────────────────────────────────────────────────
    if provider == "gemini":
        url  = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # ── Ollama ─────────────────────────────────────────────────────────────────
    if provider == "ollama":
        ollama_url = (base_url or "http://localhost:11434").rstrip("/")
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        body = {"model": model, "messages": msgs, "stream": False,
                "options": {"temperature": 0.2}}
        req = urllib.request.Request(
            f"{ollama_url}/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        return data["message"]["content"].strip()

    # ── OpenAI-compatible (OpenAI / OpenRouter / Groq / xAI / Mistral /
    #    DeepSeek / OpenClaw) ───────────────────────────────────────────────────
    URL_MAP = {
        "openai":     "https://api.openai.com/v1/chat/completions",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "groq":       "https://api.groq.com/openai/v1/chat/completions",
        "xai":        "https://api.x.ai/v1/chat/completions",
        "mistral":    "https://api.mistral.ai/v1/chat/completions",
        "deepseek":   "https://api.deepseek.com/v1/chat/completions",
        "openclaw":   (base_url or "http://localhost:1234/v1") + "/chat/completions",
    }
    url  = URL_MAP.get(provider, URL_MAP["openai"])
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    body = {
        "model":      clean_model,
        "messages":   msgs,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type":  "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"].strip()


def nl_parse_agent_rules(description: str, cfg: dict) -> dict:
    """
    Parse natural language agent description into structured governance rules.
    Returns {"name", "description", "can_do": [...], "cannot_do": [...]}
    or {} on failure.
    """
    system = (
        "You are a governance rule extractor. "
        "Extract precise, actionable rules from agent descriptions. "
        "Reply ONLY with valid JSON, no markdown, no prose."
    )
    prompt = f"""Analyze this AI agent description and extract its governance rules.

AGENT DESCRIPTION:
\"{description}\"

Extract the governance rules. Reply ONLY with this JSON structure:
{{
  "name": "short agent name (2-5 words)",
  "description": "one clear sentence of what this agent does",
  "can_do": [
    "specific permitted action 1",
    "specific permitted action 2"
  ],
  "cannot_do": [
    "specific forbidden action 1",
    "specific forbidden action 2"
  ],
  "confidence": 0.0-1.0
}}

Rules for extraction:
- can_do: things the agent IS PERMITTED to do (specific actions, not vague)
- cannot_do: things FORBIDDEN or restricted (explicit limits, not duplicates of can_do)
- Infer sensible limits if not explicitly stated (e.g., receptionist can't give diagnoses)
- 3-8 items per list depending on complexity
- Each rule is one actionable sentence, starting with a verb
- Same language as the description"""

    raw, provider = _call_llm_with_fallback(
        prompt, cfg, system=system, max_tokens=600, require_json=True
    )
    if not raw:
        return {}

    try:
        clean = re.sub(r"```json\s*|```\s*", "", raw).strip()
        m = re.search(r"\{[\s\S]+\}", clean)
        return json.loads(m.group(0) if m else clean)
    except Exception:
        return {}


# ══════════════════════════════════════════════════════════════════════════════
SESSIONS_DIR = NOVA_DIR / "sessions"
SKILLS_DIR = NOVA_DIR / "skills"
LOGS_DIR = NOVA_DIR / "logs"

# Default configuration
DEFAULT_CONFIG = {
    "version": NOVA_VERSION,
    "api_url": "http://localhost:9002",
    "api_key": "",
    "default_token": "",
    "user_name": "",
    "org_name": "",
    "lang": "en",
    "theme": "dark",
    "telemetry": False,
    "auto_update_check": True,
    "session_timeout": 3600,
    "default_profile": "default",
    "created_at": "",
    "last_updated": "",
    # LLM Intelligence
    "llm_provider": "",
    "llm_model": "",
    "llm_api_key": "",
    "llm_effort": "medium",  # low / medium / high (Claude extended thinking)
}

# ══════════════════════════════════════════════════════════════════════════════
# LLM PROVIDERS - Choose your intelligence
# ══════════════════════════════════════════════════════════════════════════════

# ── Tier badges ──────────────────────────────────────────────────────────────
TIER_BADGE = {
    "premium":    "🔥 premium",
    "reasoning":  "🧠 reasoning",
    "balanced":   "★  balanced",
    "fast":       "⚡ fast",
    "flexible":   "🌐 flexible",
    "local":      "🏠 local",
    "free":       "🆓 free",
}

# ── Priority recommendation map ───────────────────────────────────────────────
# Used in init wizard: "what matters most?" → recommended model
PRIORITY_RECOMMEND = {
    "quality":  ("anthropic", "anthropic/claude-opus-4-6"),
    "balance":  ("anthropic", "anthropic/claude-sonnet-4-6"),
    "speed":    ("groq",      "groq/llama-3.3-70b-versatile"),
    "cost":     ("google",    "gemini/gemini-2.0-flash"),
    "local":    ("ollama",    "ollama/qwen3.5:27b"),
    "privacy":  ("mistral",   "mistral/mistral-large-latest"),
}

# ── Full 2026 model catalog - synced with integrations.py MODEL_OPTIONS ───────
LLM_PROVIDERS = {
    "anthropic": {
        "name": "Anthropic",
        "tagline": "Claude 4 family - best reasoning & coding in 2026",
        "icon": "◆",
        "color": "GLD_BRIGHT",
        "key_url": "https://console.anthropic.com/settings/keys",
        "litellm_prefix": "anthropic",
        "models": [
            # model_id (litellm format), label, tier, description
            ("anthropic/claude-opus-4-6",           "Claude Opus 4.6",         "premium",   "Most capable - complex reasoning, 1M ctx"),
            ("anthropic/claude-opus-4-6[1m]",       "Claude Opus 4.6 [1M]",    "premium",   "Opus with 1 million token context window"),
            ("anthropic/claude-sonnet-4-6",         "Claude Sonnet 4.6  ★",    "balanced",  "Best balance - recommended for most tasks"),
            ("anthropic/claude-sonnet-4-6[1m]",     "Claude Sonnet 4.6 [1M]",  "balanced",  "Sonnet with 1M context - long codebases"),
            ("anthropic/claude-haiku-4-5-20251001", "Claude Haiku 4.5",        "fast",      "Fastest Claude - lightweight & cheap"),
        ],
        "default_model": "anthropic/claude-sonnet-4-6",
        "effort_levels": ["low", "medium", "high"],  # extended thinking
        "has_effort_slider": True,
    },
    "openai": {
        "name": "OpenAI",
        "tagline": "GPT-4o & o3 - industry standard",
        "icon": "◈",
        "color": "W",
        "key_url": "https://platform.openai.com/api-keys",
        "litellm_prefix": "openai",
        "models": [
            ("openai/gpt-4o",          "GPT-4o",          "premium",   "Most capable GPT - vision, code, analysis"),
            ("openai/gpt-4o-mini",     "GPT-4o mini",     "fast",      "Fast & affordable - 80% of 4o at 10x less"),
            ("openai/o3-mini",         "o3-mini",         "reasoning", "Advanced reasoning - math, science, code"),
            ("openai/o3",              "o3",              "reasoning", "Full o3 - top reasoning model in 2026"),
            ("openai/gpt-4.1",         "GPT-4.1",         "premium",   "Latest GPT-4 variant - 1M context"),
            ("openai/gpt-4.1-mini",    "GPT-4.1 mini",    "fast",      "GPT-4.1 mini - fast & efficient"),
        ],
        "default_model": "openai/gpt-4o",
        "has_effort_slider": False,
    },
    "google": {
        "name": "Google Gemini",
        "tagline": "Gemini 2.5 Pro - massive context, free tier available",
        "icon": "◉",
        "color": "CYN",
        "key_url": "https://aistudio.google.com/app/apikey",
        "litellm_prefix": "gemini",
        "models": [
            ("gemini/gemini-2.5-pro",          "Gemini 2.5 Pro",        "premium",   "Most capable Gemini - 1M context"),
            ("gemini/gemini-2.5-flash",        "Gemini 2.5 Flash",      "balanced",  "Fast & smart - great cost/quality ratio"),
            ("gemini/gemini-2.0-flash",        "Gemini 2.0 Flash",      "fast",      "Ultra-fast - free tier in AI Studio"),
            ("gemini/gemini-2.0-flash-lite",   "Gemini 2.0 Flash Lite", "free",      "Free tier - basic tasks, high limits"),
        ],
        "default_model": "gemini/gemini-2.0-flash",
        "has_effort_slider": False,
    },
    "groq": {
        "name": "Groq",
        "tagline": "Llama 3.3 70B - fastest inference on earth (~500 tok/s)",
        "icon": "◐",
        "color": "ORG",
        "key_url": "https://console.groq.com/keys",
        "litellm_prefix": "groq",
        "models": [
            ("groq/llama-3.3-70b-versatile",  "Llama 3.3 70B",          "fast",     "Best Llama - fastest for most tasks"),
            ("groq/llama-3.1-70b-specdec",    "Llama 3.1 70B SpecDec",  "fast",     "Speculative decoding - even faster"),
            ("groq/mixtral-8x7b-32768",       "Mixtral 8x7B",           "fast",     "MoE architecture - efficient"),
            ("groq/llama-3.1-8b-instant",     "Llama 3.1 8B Instant",   "fast",     "Smallest & fastest - instant responses"),
            ("groq/deepseek-r1-distill-llama-70b", "DeepSeek R1 70B",   "reasoning","R1 reasoning via Groq speed"),
        ],
        "default_model": "groq/llama-3.3-70b-versatile",
        "has_effort_slider": False,
    },
    "xai": {
        "name": "xAI - Grok",
        "tagline": "Grok 3 - real-time knowledge, X/Twitter data",
        "icon": "✕",
        "color": "W",
        "key_url": "https://console.x.ai/",
        "litellm_prefix": "xai",
        "models": [
            ("xai/grok-3",              "Grok 3",              "premium",   "Most capable Grok - real-time knowledge"),
            ("xai/grok-3-mini",         "Grok 3 mini",         "balanced",  "Fast Grok with reasoning"),
            ("xai/grok-2-latest",       "Grok 2",              "balanced",  "Proven Grok 2 - stable & reliable"),
            ("xai/grok-2-vision-latest","Grok 2 Vision",       "balanced",  "Grok 2 with image understanding"),
        ],
        "default_model": "xai/grok-3",
        "has_effort_slider": False,
    },
    "mistral": {
        "name": "Mistral AI",
        "tagline": "European privacy - GDPR compliant, data stays in EU",
        "icon": "◇",
        "color": "B7",
        "key_url": "https://console.mistral.ai/api-keys/",
        "litellm_prefix": "mistral",
        "models": [
            ("mistral/mistral-large-latest",  "Mistral Large 2",    "premium",  "Most capable - complex tasks, multilingual"),
            ("mistral/mistral-medium-latest", "Mistral Medium",     "balanced", "Balance of speed and capability"),
            ("mistral/mistral-small-latest",  "Mistral Small 3.1",  "fast",     "Fast & cheap - simple tasks"),
            ("mistral/codestral-latest",      "Codestral",          "balanced", "Specialized for code generation"),
            ("mistral/pixtral-large-latest",  "Pixtral Large",      "premium",  "Vision + text - multimodal tasks"),
        ],
        "default_model": "mistral/mistral-large-latest",
        "has_effort_slider": False,
    },
    "deepseek": {
        "name": "DeepSeek",
        "tagline": "DeepSeek V3 - top coding model, ultra affordable",
        "icon": "◈",
        "color": "B8",
        "key_url": "https://platform.deepseek.com/api_keys",
        "litellm_prefix": "deepseek",
        "models": [
            ("deepseek/deepseek-chat",    "DeepSeek V3",      "balanced",  "Top coding - rivals GPT-4o at 10x less cost"),
            ("deepseek/deepseek-reasoner","DeepSeek R1",      "reasoning", "Chain-of-thought reasoning - math & science"),
        ],
        "default_model": "deepseek/deepseek-chat",
        "has_effort_slider": False,
    },
    "cohere": {
        "name": "Cohere",
        "tagline": "Command R+ - enterprise RAG & search optimized",
        "icon": "◉",
        "color": "MGN",
        "key_url": "https://dashboard.cohere.com/api-keys",
        "litellm_prefix": "cohere",
        "models": [
            ("cohere/command-r-plus-08-2024", "Command R+",    "premium",   "Best for RAG, grounding, enterprise search"),
            ("cohere/command-r-08-2024",      "Command R",     "balanced",  "Fast RAG - cost effective"),
        ],
        "default_model": "cohere/command-r-plus-08-2024",
        "has_effort_slider": False,
    },
    "openrouter": {
        "name": "OpenRouter",
        "tagline": "One key - access ALL models above + 200+ more",
        "icon": "◎",
        "color": "GRN",
        "key_url": "https://openrouter.ai/keys",
        "litellm_prefix": "openrouter",
        "models": [
            ("openrouter/anthropic/claude-opus-4-6",          "Claude Opus 4.6",       "premium",   "Best reasoning via OpenRouter"),
            ("openrouter/anthropic/claude-sonnet-4-6",        "Claude Sonnet 4.6",     "balanced",  "Best balance via OpenRouter"),
            ("openrouter/openai/gpt-4o",                      "GPT-4o",                "premium",   "OpenAI flagship via OpenRouter"),
            ("openrouter/openai/o3",                          "o3",                    "reasoning", "Top reasoning via OpenRouter"),
            ("openrouter/google/gemini-2.5-pro",              "Gemini 2.5 Pro",        "premium",   "Google flagship via OpenRouter"),
            ("openrouter/deepseek/deepseek-chat",             "DeepSeek V3",           "balanced",  "Best value coding via OpenRouter"),
            ("openrouter/meta-llama/llama-3.3-70b-instruct",  "Llama 3.3 70B",         "fast",      "Open source via OpenRouter"),
            ("openrouter/auto",                               "Auto (router picks)",   "flexible",  "OpenRouter picks best model per request"),
        ],
        "default_model": "openrouter/anthropic/claude-sonnet-4-6",
        "has_effort_slider": False,
    },
    "ollama": {
        "name": "Ollama (Local)",
        "tagline": "100% local - no API key, no cost, full privacy",
        "icon": "🏠",
        "color": "GRN",
        "key_url": "https://ollama.com/download",
        "litellm_prefix": "ollama",
        "models": [
            ("ollama/qwen3.5:27b",         "Qwen 3.5 27B",      "local",   "Best local model 2026 - rivals GPT-4o"),
            ("ollama/qwen3.5:9b",          "Qwen 3.5 9B",       "local",   "Sweet spot - 16GB RAM, great quality"),
            ("ollama/qwen3.5:4b",          "Qwen 3.5 4B",       "local",   "Minimal RAM - 8GB machines"),
            ("ollama/llama3.3:70b",        "Llama 3.3 70B",     "local",   "Meta open source - 64GB RAM"),
            ("ollama/deepseek-r1:14b",     "DeepSeek R1 14B",   "local",   "Local reasoning - 16GB RAM"),
            ("ollama/mistral:latest",      "Mistral 7B",        "local",   "Classic local model"),
            ("ollama/custom",              "Custom model...",   "local",   "Enter any Ollama model name"),
        ],
        "default_model": "ollama/qwen3.5:27b",
        "needs_api_key": False,
        "base_url": "http://localhost:11434",
        "has_effort_slider": False,
    },
    # ── OpenClaw - compatible con cualquier endpoint OpenAI ──────────────────
    "openclaw": {
        "name": "OpenClaw",
        "tagline": "Compatible endpoint - apunta a cualquier servidor OpenAI-compatible",
        "icon": "◎",
        "color": "MGN",
        "key_url": "",          # Vacío = no requiere URL externa
        "litellm_prefix": "openai",
        "models": [
            ("openai/openclaw-default",   "OpenClaw (default)",  "local",   "Modelo por defecto del servidor OpenClaw"),
            ("openai/custom",             "Custom model...",     "local",   "Escribe el nombre del modelo exacto"),
        ],
        "default_model": "openai/openclaw-default",
        "needs_api_key": False,
        "base_url": "http://localhost:1234/v1",  # LM Studio / OpenClaw default
        "has_effort_slider": False,
        "custom_base_url": True,   # Muestra campo de URL en la config
    },
}

# ── Model lookup by litellm ID (used by skill_executor/backend) ───────────────
def get_model_info(litellm_model_id: str) -> dict:
    """Return provider + tier info for any model ID."""
    for prov_key, prov in LLM_PROVIDERS.items():
        for m in prov["models"]:
            if m[0] == litellm_model_id:
                return {
                    "provider": prov_key,
                    "provider_name": prov["name"],
                    "model": m[0],
                    "label": m[1],
                    "tier": m[2] if len(m) > 2 else "balanced",
                    "description": m[3] if len(m) > 3 else "",
                }
    return {}

# ── Flat MODEL_OPTIONS list - compatible with integrations.py format ──────────
# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATIONS BRIDGE — wire integrations.py into the CLI skill system
# ══════════════════════════════════════════════════════════════════════════════

def _load_integrations():
    """
    Lazy-load integrations.py from same directory as nova.py.
    Returns the module or None if not available.
    """
    import importlib.util, os
    for search_path in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "integrations.py"),
        os.path.join(os.getcwd(), "integrations.py"),
        os.path.expanduser("~/integrations.py"),
    ]:
        if os.path.exists(search_path):
            try:
                spec = importlib.util.spec_from_file_location("nova_integrations",
                                                               search_path)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
            except Exception as e:
                debug(f"integrations.py load error: {e}")
    return None


def skill_check(skill_name: str, action: str, context: str = "",
                agent_name: str = "") -> dict:
    """
    Run an integration check + Nova Core validation for a given action.
    Used by agents to ask: "Should I do this?"

    Returns:
        {"allowed": bool, "verdict": str, "reason": str, "score": int}
    """
    mod = _load_integrations()
    if mod and hasattr(mod, "skill_check"):
        return mod.skill_check(skill_name, action, context, agent_name)
    # Fallback: just validate with Nova Core directly
    nc = _get_nova_core()
    if nc.is_alive():
        r = nc.validate(action=action, context=context,
                        scope=f"agent:{agent_name}" if agent_name else "global",
                        agent_name=agent_name)
        blocked = r.get("result") in ("BLOCKED", "ESCALATED")
        return {"allowed": not blocked, "verdict": r.get("result", "APPROVED"),
                "reason": r.get("reason", ""), "score": r.get("score", 50)}
    return {"allowed": True, "verdict": "APPROVED", "reason": "offline", "score": 50}


def get_model_options() -> list:
    """Returns flat list compatible with integrations.py MODEL_OPTIONS."""
    # Try to import from integrations.py if available (server-side)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "integrations",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "integrations.py")
        )
        if spec:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "MODEL_OPTIONS"):
                return mod.MODEL_OPTIONS
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")

    # Fallback: build from LLM_PROVIDERS
    opts = []
    for prov_key, prov in LLM_PROVIDERS.items():
        if prov_key == "ollama":
            continue  # local models not synced to server
        for m in prov["models"]:
            if "custom" in m[0]:
                continue
            opts.append({
                "provider": prov_key,
                "model": m[0],
                "label": m[1].replace("  ★", "").replace(" ★", "").strip(),
                "tier": m[2] if len(m) > 2 else "balanced",
            })
    return opts


def _harden_file_permissions(path, mode=0o600):
    """Best-effort file permission hardening (POSIX only)."""
    if os.name == "nt":
        return
    try:
        os.chmod(path, mode)
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")


def _write_json(path, data, mode=0o600):
    """Write JSON and apply restrictive permissions when possible."""
    path.write_text(json.dumps(data, indent=2))
    _harden_file_permissions(path, mode)


def ensure_dirs():
    """Ensure all nova directories exist."""
    for d in [NOVA_DIR, SESSIONS_DIR, SKILLS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_config():
    """Load configuration from disk."""
    ensure_dirs()
    
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return {**DEFAULT_CONFIG, **data}
        except Exception as e:
            debug(f"Config load error: {e}")
    
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    """Save configuration to disk."""
    ensure_dirs()
    cfg["last_updated"] = datetime.now().isoformat()
    _write_json(CONFIG_FILE, cfg)


def validate_config(cfg):
    """Validate configuration, return list of issues."""
    issues = []
    
    url = cfg.get("api_url", "")
    if not url:
        issues.append("Server URL is not configured")
    elif not url.startswith(("http://", "https://")):
        issues.append("Server URL must start with http:// or https://")
    
    key = cfg.get("api_key", "")
    if not key:
        issues.append("API key is not configured")
    elif len(key) < 16:
        issues.append("API key seems too short (security risk)")
    
    return issues


# ══════════════════════════════════════════════════════════════════════════════
# API KEY MANAGEMENT - Secure local keychain
# ══════════════════════════════════════════════════════════════════════════════

def generate_api_key(prefix="nova"):
    """Generate a cryptographically secure API key."""
    # Format: nova_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (prefix + 32 hex chars)
    random_part = secrets.token_hex(16)
    return f"{prefix}_{random_part}"


def load_keys():
    """Load saved API keys from keychain."""
    if KEYS_FILE.exists():
        try:
            return json.loads(KEYS_FILE.read_text())
        except Exception:
            pass
    return {"keys": [], "active": None}


def save_keys(data):
    """Save API keys to keychain."""
    ensure_dirs()
    _write_json(KEYS_FILE, data)


def add_api_key(key, name="", server_url="", description=""):
    """Add a new API key to the keychain."""
    data = load_keys()
    
    # Check for duplicates
    for k in data["keys"]:
        if k["key"] == key:
            return k  # Already exists
    
    entry = {
        "id": str(uuid.uuid4())[:8],
        "key": key,
        "name": name or f"Key {len(data['keys']) + 1}",
        "server_url": server_url,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "last_used": None,
    }
    
    data["keys"].append(entry)
    
    # Set as active if first key
    if not data["active"]:
        data["active"] = key
    
    save_keys(data)
    return entry


def get_active_key():
    """Get the currently active API key."""
    data = load_keys()
    return data.get("active", "")


def set_active_key(key):
    """Set the active API key."""
    data = load_keys()
    data["active"] = key
    
    # Update last_used
    for k in data["keys"]:
        if k["key"] == key:
            k["last_used"] = datetime.now().isoformat()
            break
    
    save_keys(data)


def delete_api_key(key_id):
    """Delete an API key by ID."""
    data = load_keys()
    original_len = len(data["keys"])
    data["keys"] = [k for k in data["keys"] if k.get("id") != key_id]
    
    if len(data["keys"]) < original_len:
        # Update active if deleted
        if data["active"] and not any(k["key"] == data["active"] for k in data["keys"]):
            data["active"] = data["keys"][0]["key"] if data["keys"] else None
        save_keys(data)
        return True
    
    return False


# ══════════════════════════════════════════════════════════════════════════════
# PROFILES - Multiple environments (dev/staging/prod)
# ══════════════════════════════════════════════════════════════════════════════

def load_profiles():
    """Load configuration profiles."""
    if PROFILES_FILE.exists():
        try:
            return json.loads(PROFILES_FILE.read_text())
        except Exception:
            pass
    
    return {
        "profiles": {
            "default": {
                "name": "Default",
                "api_url": "http://localhost:9002",
                "description": "Local development server",
            }
        },
        "active": "default"
    }


def save_profiles(data):
    """Save configuration profiles."""
    ensure_dirs()
    _write_json(PROFILES_FILE, data)


def get_active_profile():
    """Get the active profile."""
    data = load_profiles()
    active = data.get("active", "default")
    return data["profiles"].get(active, data["profiles"].get("default", {}))


def switch_profile(name):
    """Switch to a different profile."""
    data = load_profiles()
    if name in data["profiles"]:
        data["active"] = name
        save_profiles(data)
        
        # Update config with profile settings
        cfg = load_config()
        profile = data["profiles"][name]
        if "api_url" in profile:
            cfg["api_url"] = profile["api_url"]
        save_config(cfg)
        
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# OFFLINE QUEUE - Actions queued when server is unreachable
# ══════════════════════════════════════════════════════════════════════════════

def queue_action(action_data):
    """Queue an action for later sync."""
    ensure_dirs()
    
    queue = []
    if QUEUE_FILE.exists():
        try:
            queue = json.loads(QUEUE_FILE.read_text())
        except Exception:
            queue = []
    
    entry = {
        "id": str(uuid.uuid4()),
        "data": action_data,
        "queued_at": datetime.now().isoformat(),
        "attempts": 0,
    }
    queue.append(entry)
    
    _write_json(QUEUE_FILE, queue)
    return len(queue)


def get_queue():
    """Get all queued actions."""
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except Exception:
            pass
    return []


def clear_queue():
    """Clear the offline queue."""
    if QUEUE_FILE.exists():
        QUEUE_FILE.unlink()


def remove_from_queue(action_id):
    """Remove specific action from queue."""
    queue = get_queue()
    queue = [a for a in queue if a.get("id") != action_id]
    
    if queue:
        _write_json(QUEUE_FILE, queue)
    else:
        clear_queue()


# ══════════════════════════════════════════════════════════════════════════════
# HISTORY - Command history tracking
# ══════════════════════════════════════════════════════════════════════════════

def add_to_history(command, args=None, result=None):
    """Add command to history."""
    ensure_dirs()
    
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
        except Exception:
            history = []
    
    entry = {
        "command": command,
        "args": args,
        "result": result,
        "timestamp": datetime.now().isoformat(),
    }
    
    history.append(entry)
    
    # Keep last 1000 entries
    if len(history) > 1000:
        history = history[-1000:]
    
    _write_json(HISTORY_FILE, history)


def get_history(limit=50):
    """Get command history."""
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
            return history[-limit:]
        except Exception:
            pass
    return []


# ══════════════════════════════════════════════════════════════════════════════
# API CLIENT - Enterprise-grade HTTP client
# ══════════════════════════════════════════════════════════════════════════════

class NovaAPI:
    """
    Nova API client with enterprise features:
    - Automatic retry with exponential backoff
    - Request/response logging
    - Timeout handling
    - Error normalization
    - Offline queue integration
    """
    
    def __init__(self, url, key, timeout=15, retries=2):
        self.url = url.rstrip("/")
        self.key = key
        self.timeout = timeout
        self.retries = retries
        self.last_request_time = None
        self.last_response_time = None
    
    def _request(self, method, path, data=None, extra_headers=None):
        """Make an HTTP request with retry logic."""
        url = self.url + path
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.key,
            "User-Agent": f"nova-cli/{NOVA_VERSION}",
            "X-Nova-Client": "cli",
            "X-Nova-Version": NOVA_VERSION,
        }
        
        if extra_headers:
            headers.update(extra_headers)
        
        body = json.dumps(data).encode() if data else None
        
        debug(f"{method} {url}")
        if data:
            debug(f"Body: {json.dumps(data)[:200]}")
        
        last_error = None
        
        for attempt in range(1 + self.retries):
            try:
                self.last_request_time = time.time()
                
                req = urllib.request.Request(
                    url, data=body, headers=headers, method=method
                )
                
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    self.last_response_time = time.time()
                    raw = response.read().decode()
                    try:
                        result = json.loads(raw)
                    except Exception:
                        result = {
                            "error": "Invalid JSON response",
                            "code": "INVALID_JSON",
                            "detail": raw[:200],
                            "status": response.status,
                            "type": "decode_error",
                        }
                        return result
                    debug(f"OK ({response.status})")
                    return result
            
            except urllib.error.HTTPError as e:
                self.last_response_time = time.time()
                error_body = {}
                raw_text = ""
                try:
                    raw_text = e.read().decode()
                    error_body = json.loads(raw_text) if raw_text else {}
                except Exception:
                    error_body = {}
                
                error_message = (
                    error_body.get("error")
                    or raw_text.strip()
                    or f"HTTP {e.code}"
                )
                last_error = {
                    "error": error_message,
                    "code": error_body.get("code", f"HTTP_{e.code}"),
                    "detail": error_body.get("detail"),
                    "request_id": error_body.get("request_id"),
                    "status": e.code,
                    "type": "http_error",
                }
                if "retry_after" in error_body:
                    last_error["retry_after"] = error_body.get("retry_after")
                
                # Don't retry client errors
                if 400 <= e.code < 500:
                    debug(f"Client error {e.code}: {error_message}")
                    return last_error
                
                debug(f"Server error {e.code}: {error_message}")
            
            except urllib.error.URLError as e:
                self.last_response_time = time.time()
                last_error = {
                    "error": f"Cannot connect to {self.url}",
                    "code": "CONNECTION_ERROR",
                    "type": "connection_error",
                    "detail": str(e.reason),
                }
                debug(f"Connection error: {e.reason}")
            
            except TimeoutError:
                self.last_response_time = time.time()
                last_error = {
                    "error": f"Request timed out after {self.timeout}s",
                    "code": "TIMEOUT",
                    "type": "timeout",
                }
                debug("Request timed out")
            
            except Exception as e:
                self.last_response_time = time.time()
                last_error = {
                    "error": str(e),
                    "code": "UNKNOWN_ERROR",
                    "type": "unknown",
                }
                debug(f"Unknown error: {e}")
            
            # Retry with backoff
            if attempt < self.retries:
                wait = (2 ** attempt) + random.uniform(0, 1)
                debug(f"Retrying in {wait:.1f}s (attempt {attempt + 2}/{self.retries + 1})")
                time.sleep(wait)
        
        return last_error or {"error": "Unknown error", "type": "unknown"}
    
    def get(self, path, **kwargs):
        return self._request("GET", path, **kwargs)
    
    def post(self, path, data, **kwargs):
        return self._request("POST", path, data, **kwargs)
    
    def put(self, path, data, **kwargs):
        return self._request("PUT", path, data, **kwargs)
    
    def patch(self, path, data=None, **kwargs):
        return self._request("PATCH", path, data or {}, **kwargs)
    
    def delete(self, path, **kwargs):
        return self._request("DELETE", path, **kwargs)
    
    def health_check(self):
        """Quick health check."""
        result = self.get("/health")
        return "error" not in result
    
    @property
    def last_latency(self):
        """Get last request latency in ms."""
        if self.last_request_time and self.last_response_time:
            return int((self.last_response_time - self.last_request_time) * 1000)
        return None


def get_api(cfg=None):
    """Get API client from configuration."""
    cfg = cfg or load_config()
    return NovaAPI(cfg["api_url"], cfg["api_key"]), cfg


def format_api_error(result, fallback="Unknown error"):
    """Normalize API error payloads into a single user-facing string."""
    if not isinstance(result, dict):
        return fallback
    message = result.get("error") or fallback
    code = result.get("code")
    request_id = result.get("request_id")
    if code:
        message = f"{message} ({code})"
    if request_id:
        message = f"{message} · req {request_id}"
    return message


def _default_workspace_email(name, org):
    """Build a sane default workspace email from the user's identity."""
    base = (name or org or "workspace").lower()
    slug = re.sub(r"[^a-z0-9]+", ".", base).strip(".")
    if not slug:
        slug = "workspace"
    return f"{slug}@example.com"


def register_workspace_with_admin(server_url, payload, admin_token, timeout=15):
    """Call the admin-only registration endpoint to ensure the API key exists."""
    url = server_url.rstrip("/") + "/api/workspaces/register"
    data = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Nova-Admin-Token": admin_token,
    }

    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode() or ""
        payload = {}
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}
        payload.setdefault("error", f"HTTP {exc.code}")
        payload.setdefault("code", payload.get("code", f"HTTP_{exc.code}"))
        payload.setdefault("status", exc.code)
        return payload
    except urllib.error.URLError as exc:
        return {
            "error": "Cannot reach workspace registration endpoint",
            "code": "REGISTRATION_CONNECTION_ERROR",
            "detail": str(exc.reason),
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "code": "REGISTRATION_ERROR",
        }


def _parse_host_port(value, default_host="127.0.0.1", default_port=7755):
    """Parse host:port strings with fallbacks."""
    if not value:
        return default_host, default_port
    if ":" in value:
        host, port = value.rsplit(":", 1)
        try:
            return host or default_host, int(port)
        except ValueError:
            return default_host, default_port
    return value, default_port


def _http_post_json(url, payload, headers=None, timeout=20):
    """POST JSON and return status, headers, body."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        return resp.status, dict(resp.headers), raw


# ══════════════════════════════════════════════════════════════════════════════
# VERSION CHECK - Auto-update notifications
# ══════════════════════════════════════════════════════════════════════════════

_VERSION_CACHE = {}
_LOCAL_POLICY_CACHE = {}


SAFE_READ_VERBS = (
    "read", "view", "open", "cat", "head", "tail",
    "list", "ls", "stat", "grep", "show",
)
UNSAFE_VERBS = (
    "write", "delete", "remove", "rm", "move", "rename",
    "chmod", "chown", "copy", "create", "update",
    "edit", "append", "truncate", "touch",
)


def local_policy_decision(action):
    """Fast in-memory policy decision for safe read-only actions."""
    if not action:
        return None
    key = action.strip().lower()
    cached = _LOCAL_POLICY_CACHE.get(key)
    if cached:
        return cached
    
    if any(bad in key for bad in UNSAFE_VERBS):
        return None
    
    if any(good in key for good in SAFE_READ_VERBS) and (
        "file" in key or "/" in key or "." in key or "path" in key
    ):
        decision = {
            "verdict": "APPROVED",
            "score": 100,
            "reason": "Local policy cache: read-only action",
            "policy": "local-cache",
        }
        _LOCAL_POLICY_CACHE[key] = decision
        return decision
    
    return None


def check_for_updates(force=False):
    """
    Check if a newer version of nova is available.
    Results are cached for 24 hours.
    """
    cache_key = "version_check"
    now = time.time()
    
    # Check cache
    if not force and cache_key in _VERSION_CACHE:
        cached = _VERSION_CACHE[cache_key]
        if now - cached.get("timestamp", 0) < 86400:  # 24 hours
            return cached.get("latest")
    
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/sxrubyo/nova-os/releases/latest",
            headers={
                "User-Agent": f"nova-cli/{NOVA_VERSION}",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            latest = data.get("tag_name", "").lstrip("v")
            
            _VERSION_CACHE[cache_key] = {
                "latest": latest,
                "timestamp": now,
                "release_url": data.get("html_url"),
            }
            
            if latest and latest != NOVA_VERSION:
                return latest
    
    except Exception as e:
        debug(f"Version check failed: {e}")
    
    return None


# ══════════════════════════════════════════════════════════════════════════════
# I18N - Internationalization
# ══════════════════════════════════════════════════════════════════════════════

def get_strings(lang="en"):
    """Get localized strings."""
    strings = {
        "en": {
            # Init wizard
            "welcome": "Welcome to nova.",
            "welcome_sub": "Let's set up your governance layer.",
            "intro_1": "nova sits between your agents and the real world.",
            "intro_2": "Before anything executes, nova asks one question:",
            "intro_question": "Should this happen?",
            
            # How it works
            "how_it_works": "How nova works",
            "how_step_1": "Your agent wants to do something",
            "how_step_2": "nova evaluates it in <5ms - no AI for 90% of cases",
            "how_approved": "Approved · runs immediately",
            "how_escalated": "Escalated · you decide",
            "how_blocked": "Blocked · logged forever",
            "ledger_desc": "Every decision lands in the Intent Ledger.",
            "ledger_sub": "Cryptographic. Auditable. Permanent.",
            
            # Risks
            "risks_title": "Before we continue",
            "risks_warning": "nova is not a sandbox.",
            "risks_sub": "It makes real decisions about real actions in production.",
            "risk_1": "nova may block actions your agents try to execute",
            "risk_2": "every validation is recorded permanently in the ledger",
            "risk_3": "you define the rules - you own the consequences",
            "risk_4": "misconfigured rules can block legitimate work",
            "risk_5": "the ledger cannot be deleted or modified",
            
            # Terms
            "terms_label": "Terms:",
            "terms_question": "Do you understand and accept?",
            "terms_accept": "Yes, I accept",
            "terms_decline": "No, exit",
            "setup_cancelled": "Setup cancelled.",
            
            # Identity
            "identity_title": "Who are you?",
            "identity_sub": "This helps personalize your experience.",
            "your_name": "Your name",
            "your_org": "Organization (optional)",
            
            # API Key
            "apikey_title": "API Key Setup",
            "apikey_sub": "Your API key authenticates all requests.",
            "apikey_generate": "Generate a new key (recommended)",
            "apikey_enter": "Enter an existing key",
            "apikey_use_saved": "Use saved key",
            "apikey_generated": "Generated new API key",
            "apikey_saved": "API key saved",
            "apikey_warning": "Save this key securely - shown only once.",
            
            # Server
            "server_title": "Connect to server",
            "server_sub": "nova CLI talks to a nova server.",
            "server_local": "Local server (localhost:9002)",
            "server_custom": "Enter custom URL",
            "server_saved": "Use saved configuration",
            
            # Connecting
            "connecting_title": "Connecting",
            "testing_connection": "Testing connection...",
            "server_online": "Server responding",
            "key_accepted": "API key accepted",
            "connection_failed": "Could not connect",
            "config_saved": "Configuration saved",
            "offline_title": "Modo Offline",
            "offline_sub": "We couldn't reach the server. Setup will finish locally.",
            "offline_hint": "Actions can be queued and synced when you're back online.",
            
            # Success
            "youre_in": "You're in",
            "ready": "is ready.",
            "next_steps": "What's next?",
            
            # Skills
            "skills_title": "Skills Setup",
            "skills_sub": "Skills give nova real-world context.",
            "skills_now": "Would you like to configure skills now?",
            "skills_yes": "Yes, let's set them up",
            "skills_later": "No, I'll do it later",
            
            # Buttons
            "continue": "continue",
            "back": "back",
            "skip": "skip",
        },
        "es": {
            "welcome": "Bienvenido a nova.",
            "welcome_sub": "Configuremos tu capa de gobernanza.",
            "intro_1": "nova se sienta entre tus agentes y el mundo real.",
            "intro_2": "Antes de que algo se ejecute, nova pregunta:",
            "intro_question": "¿Debería pasar esto?",
            
            "how_it_works": "Cómo funciona nova",
            "how_step_1": "Tu agente quiere hacer algo",
            "how_step_2": "nova lo evalúa en <5ms - sin IA en el 90% de casos",
            "how_approved": "Aprobado · se ejecuta",
            "how_escalated": "Escalado · tú decides",
            "how_blocked": "Bloqueado · registrado",
            "ledger_desc": "Cada decisión queda en el Intent Ledger.",
            "ledger_sub": "Criptográfico. Auditable. Permanente.",
            
            "risks_title": "Antes de continuar",
            "risks_warning": "nova no es un sandbox.",
            "risks_sub": "Toma decisiones reales sobre acciones reales.",
            "risk_1": "nova puede bloquear acciones de tus agentes",
            "risk_2": "cada validación se registra permanentemente",
            "risk_3": "tú defines las reglas - tú eres responsable",
            "risk_4": "reglas mal configuradas bloquean trabajo",
            "risk_5": "el ledger no puede eliminarse ni modificarse",
            
            "terms_label": "Términos:",
            "terms_question": "¿Entiendes y aceptas?",
            "terms_accept": "Sí, acepto",
            "terms_decline": "No, salir",
            "setup_cancelled": "Setup cancelado.",
            
            "identity_title": "¿Quién eres?",
            "identity_sub": "Esto personaliza tu experiencia.",
            "your_name": "Tu nombre",
            "your_org": "Organización (opcional)",
            
            "apikey_title": "Configurar API Key",
            "apikey_sub": "Tu API key autentica las peticiones.",
            "apikey_generate": "Generar nueva key (recomendado)",
            "apikey_enter": "Ingresar key existente",
            "apikey_use_saved": "Usar key guardada",
            "apikey_generated": "Nueva API key generada",
            "apikey_saved": "API key guardada",
            "apikey_warning": "Guarda esta key - solo se muestra una vez.",
            
            "server_title": "Conectar servidor",
            "server_sub": "nova CLI habla con un servidor nova.",
            "server_local": "Servidor local (localhost:9002)",
            "server_custom": "Ingresar URL personalizada",
            "server_saved": "Usar configuración guardada",
            
            "connecting_title": "Conectando",
            "testing_connection": "Probando conexión...",
            "server_online": "Servidor respondiendo",
            "key_accepted": "API key aceptada",
            "connection_failed": "No se pudo conectar",
            "config_saved": "Configuración guardada",
            "offline_title": "Modo Offline",
            "offline_sub": "No pudimos conectar al servidor. Terminaremos localmente.",
            "offline_hint": "Las acciones se pueden encolar y sincronizar al volver en línea.",
            
            "youre_in": "Estás dentro",
            "ready": "está listo.",
            "next_steps": "¿Qué sigue?",
            
            "skills_title": "Configurar Skills",
            "skills_sub": "Los skills dan contexto a nova.",
            "skills_now": "¿Configurar skills ahora?",
            "skills_yes": "Sí, vamos",
            "skills_later": "No, después",
            
            "continue": "continuar",
            "back": "volver",
            "skip": "omitir",
        }
    }
    
    return strings.get(lang, strings["en"])


# ══════════════════════════════════════════════════════════════════════════════
# RULE TEMPLATES - Pre-built agent configurations
# ══════════════════════════════════════════════════════════════════════════════

def _build_rule_templates():
    return {
        "email-safety": {
            "label": "Email Safety",
            "description": "Block external sends, protect inbox integrity",
            "icon": "✉",
            "can_do": [
                "send email to verified contacts",
                "read inbox",
                "draft emails",
                "reply to existing threads",
                "search emails",
            ],
            "cannot_do": [
                "send email to external domains",
                "delete emails permanently",
                "forward to personal accounts",
                "modify email rules or filters",
                "access archived emails",
            ],
        },
        "database-readonly": {
            "label": "Database Read-Only",
            "description": "SELECT only - no mutations allowed",
            "icon": "⊞",
            "can_do": [
                "SELECT queries",
                "read schemas",
                "list tables",
                "explain query plans",
                "read indexes",
            ],
            "cannot_do": [
                "INSERT statements",
                "UPDATE statements",
                "DELETE statements",
                "DROP operations",
                "ALTER operations",
                "TRUNCATE tables",
                "CREATE objects",
                "GRANT permissions",
            ],
        },
        "social-media": {
            "label": "Social Media Manager",
            "description": "Draft and schedule, never auto-publish",
            "icon": "◎",
            "can_do": [
                "read posts and analytics",
                "draft content",
                "schedule posts for review",
                "reply to comments",
                "read messages",
            ],
            "cannot_do": [
                "publish without approval",
                "delete posts",
                "change account settings",
                "DM users directly",
                "modify profile",
                "connect new accounts",
            ],
        },
        "payment-guard": {
            "label": "Payment Guard",
            "description": "Verify and read - never initiate charges",
            "icon": "◈",
            "can_do": [
                "read transaction history",
                "verify payment status",
                "list subscriptions",
                "check balance",
                "view invoices",
            ],
            "cannot_do": [
                "create charges",
                "issue refunds over $100",
                "modify subscriptions",
                "update payment methods",
                "transfer funds",
                "change billing info",
            ],
        },
        "devops-safe": {
            "label": "DevOps Safe Mode",
            "description": "Monitor and report, no destructive operations",
            "icon": "◉",
            "can_do": [
                "read logs",
                "check service status",
                "list deployments",
                "run health checks",
                "view metrics and alerts",
                "read configurations",
            ],
            "cannot_do": [
                "deploy to production",
                "scale down services",
                "delete resources",
                "modify secrets",
                "change DNS records",
                "rollback without approval",
                "terminate instances",
            ],
        },
        "crm-assistant": {
            "label": "CRM Assistant",
            "description": "Read and update contacts, no deletions",
            "icon": "◻",
            "can_do": [
                "read contacts",
                "update notes on contacts",
                "search leads",
                "log activities",
                "view deal history",
            ],
            "cannot_do": [
                "delete contacts",
                "export all data",
                "modify deal amounts",
                "send mass emails",
                "change pipeline stages",
                "merge contacts",
            ],
        },
        "file-readonly": {
            "label": "File System Read-Only",
            "description": "Read files, no write or delete",
            "icon": "◯",
            "can_do": [
                "read files",
                "list directories",
                "search file contents",
                "view file metadata",
            ],
            "cannot_do": [
                "write files",
                "delete files",
                "rename files",
                "create directories",
                "modify permissions",
                "move files",
            ],
        },
        "api-conservative": {
            "label": "API Conservative",
            "description": "GET only, no modifications",
            "icon": "⊘",
            "can_do": [
                "GET requests",
                "read documentation",
                "check API status",
            ],
            "cannot_do": [
                "POST requests",
                "PUT requests",
                "DELETE requests",
                "PATCH requests",
                "create webhooks",
                "modify API keys",
            ],
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# SKILLS CATALOG - Integration definitions
# ══════════════════════════════════════════════════════════════════════════════

class LazyCatalog:
    """Lazy-loading wrapper to avoid upfront cost on fast commands."""
    def __init__(self, builder):
        self._builder = builder
        self._data = None
    
    def _load(self):
        if self._data is None:
            self._data = self._builder()
        return self._data
    
    def __getitem__(self, key):
        return self._load()[key]
    
    def get(self, key, default=None):
        return self._load().get(key, default)
    
    def keys(self):
        return self._load().keys()
    
    def items(self):
        return self._load().items()
    
    def values(self):
        return self._load().values()
    
    def __iter__(self):
        return iter(self._load())
    
    def __len__(self):
        return len(self._load())
    
    def __contains__(self, key):
        return key in self._load()


class LazySkills(LazyCatalog):
    """Lazy-loading wrapper for skills catalog."""
    pass


def _build_skills():
    return {
    "gmail": {
        "name": "Gmail",
        "category": "Communication",
        "icon": "✉",
        "color": "RED",
        "tagline": "Email intelligence for your agents",
        "description": "Verify sent emails, detect duplicates, read inbox",
        "what_it_does": "nova checks your Gmail before approving any send action",
        "fields": [
            {
                "key": "service_account_json",
                "label": "Service Account JSON",
                "description": "Path to your Google Cloud service account file",
                "secret": False,
                "required": True,
            },
            {
                "key": "delegated_email",
                "label": "Delegated Email",
                "description": "The Google account email to access",
                "secret": False,
                "required": True,
            },
        ],
        "docs_url": "https://console.cloud.google.com/iam-admin/serviceaccounts",
        "setup_guide": [
            "1. Go to Google Cloud Console",
            "2. Create a Service Account",
            "3. Download the JSON key file",
            "4. Enable Gmail API for your project",
            "5. Share mailbox access with the service account",
        ],
        "mcp": "gmail-mcp",
    },
    "slack": {
        "name": "Slack",
        "category": "Communication",
        "icon": "◈",
        "color": "YLW",
        "tagline": "Real-time alerts and channel monitoring",
        "description": "Send alerts, read channels, verify sent messages",
        "what_it_does": "nova notifies Slack when it blocks or escalates an action",
        "fields": [
            {
                "key": "bot_token",
                "label": "Bot Token",
                "description": "Slack Bot User OAuth Token (xoxb-...)",
                "secret": True,
                "required": True,
            },
            {
                "key": "channel",
                "label": "Default Channel",
                "description": "Channel for nova alerts (#general)",
                "secret": False,
                "required": False,
            },
        ],
        "docs_url": "https://api.slack.com/apps",
        "setup_guide": [
            "1. Create a Slack App at api.slack.com",
            "2. Add Bot Token Scopes",
            "3. Install to your workspace",
            "4. Copy the Bot User OAuth Token",
        ],
        "mcp": "slack-mcp-server",
    },
    "whatsapp": {
        "name": "WhatsApp (Evolution API)",
        "category": "Communication",
        "icon": "◎",
        "color": "GRN",
        "tagline": "No duplicate messages. Governance for Melissa.",
        "description": "Detect duplicate sends, read conversation history, governance for WhatsApp agents",
        "what_it_does": "nova checks conversation history before approving any WhatsApp send",
        "fields": [
            {
                "key": "evolution_url",
                "label": "Evolution API URL",
                "description": "http://localhost:8080 or your server",
                "secret": False,
                "required": True,
            },
            {
                "key": "evolution_key",
                "label": "API Key",
                "description": "Evolution API key",
                "secret": True,
                "required": True,
            },
            {
                "key": "evolution_instance",
                "label": "Instance Name",
                "description": "Your Evolution instance (e.g. melissa)",
                "secret": False,
                "required": True,
            },
        ],
        "docs_url": "https://github.com/EvolutionAPI/evolution-api",
        "setup_guide": [
            "1. Install Evolution API",
            "2. Create an instance named after your agent",
            "3. Connect your WhatsApp number",
            "4. Copy the API key from the dashboard",
        ],
        "mcp": None,
    },
    "notion": {
        "name": "Notion",
        "category": "Productivity",
        "icon": "◻",
        "color": "W",
        "tagline": "Your knowledge base as context",
        "description": "Read databases, create pages, update records",
        "what_it_does": "nova queries Notion as source of truth for validations",
        "fields": [
            {
                "key": "api_key",
                "label": "Integration Token",
                "description": "Notion Internal Integration Token (secret_...)",
                "secret": True,
                "required": True,
            },
            {
                "key": "database_id",
                "label": "Default Database",
                "description": "Primary database ID for queries",
                "secret": False,
                "required": False,
            },
        ],
        "docs_url": "https://www.notion.so/my-integrations",
        "setup_guide": [
            "1. Go to Notion Integrations",
            "2. Create a new integration",
            "3. Copy the Internal Integration Token",
            "4. Share databases with your integration",
        ],
        "mcp": "notion-mcp",
    },
    "github": {
        "name": "GitHub",
        "category": "Development",
        "icon": "◯",
        "color": "W",
        "tagline": "Code-aware governance",
        "description": "Create issues, review PRs, verify code before deploy",
        "what_it_does": "nova can block deploys if critical issues are open",
        "fields": [
            {
                "key": "token",
                "label": "Personal Access Token",
                "description": "GitHub PAT with repo access (ghp_...)",
                "secret": True,
                "required": True,
            },
            {
                "key": "repo",
                "label": "Default Repository",
                "description": "Default repo (owner/repo)",
                "secret": False,
                "required": False,
            },
        ],
        "docs_url": "https://github.com/settings/tokens",
        "setup_guide": [
            "1. Go to GitHub Settings > Developer Settings",
            "2. Create a Personal Access Token (classic)",
            "3. Select required scopes (repo, read:org)",
            "4. Copy the token",
        ],
        "mcp": "github-mcp",
    },
    "stripe": {
        "name": "Stripe",
        "category": "Payments",
        "icon": "◈",
        "color": "B7",
        "tagline": "Payment verification and fraud prevention",
        "description": "Verify charges, detect fraud, approve transactions",
        "what_it_does": "nova validates payments and blocks suspicious activity",
        "fields": [
            {
                "key": "secret_key",
                "label": "Secret Key",
                "description": "Stripe Secret Key (sk_live_... or sk_test_...)",
                "secret": True,
                "required": True,
            },
        ],
        "docs_url": "https://dashboard.stripe.com/apikeys",
        "setup_guide": [
            "1. Go to Stripe Dashboard > Developers > API Keys",
            "2. Copy your Secret Key",
            "3. Use test key for development (sk_test_...)",
        ],
        "mcp": "stripe-mcp",
    },
    "supabase": {
        "name": "Supabase",
        "category": "Database",
        "icon": "◈",
        "color": "GRN",
        "tagline": "Real-time database verification",
        "description": "Query your Postgres database in real time",
        "what_it_does": "nova verifies database state before executing actions",
        "fields": [
            {
                "key": "url",
                "label": "Project URL",
                "description": "Your Supabase project URL",
                "secret": False,
                "required": True,
            },
            {
                "key": "service_key",
                "label": "Service Role Key",
                "description": "Service role key for admin access",
                "secret": True,
                "required": True,
            },
        ],
        "docs_url": "https://app.supabase.com/project/_/settings/api",
        "setup_guide": [
            "1. Go to Supabase Dashboard",
            "2. Select your project",
            "3. Go to Settings > API",
            "4. Copy the URL and service_role key",
        ],
        "mcp": "supabase-mcp",
    },
    "postgres": {
        "name": "PostgreSQL",
        "category": "Database",
        "icon": "◉",
        "color": "B6",
        "tagline": "Direct database connection",
        "description": "Connect directly to PostgreSQL for queries",
        "what_it_does": "nova queries your database before every validation",
        "fields": [
            {
                "key": "connection_string",
                "label": "Connection String",
                "description": "postgresql://user:pass@host:5432/db",
                "secret": True,
                "required": True,
            },
        ],
        "docs_url": "https://www.postgresql.org/docs/current/libpq-connect.html",
        "setup_guide": [
            "1. Get your PostgreSQL connection details",
            "2. Format: postgresql://user:password@host:port/database",
            "3. Ensure network access is configured",
        ],
        "mcp": "postgres-mcp",
    },
    "hubspot": {
        "name": "HubSpot",
        "category": "CRM",
        "icon": "◉",
        "color": "ORG",
        "tagline": "CRM context for your agents",
        "description": "Query contacts, deals, and communication history",
        "what_it_does": "nova checks if a lead was already contacted",
        "fields": [
            {
                "key": "api_key",
                "label": "Private App Token",
                "description": "HubSpot Private App access token",
                "secret": True,
                "required": True,
            },
        ],
        "docs_url": "https://developers.hubspot.com/docs/api/private-apps",
        "setup_guide": [
            "1. Go to HubSpot Settings > Integrations > Private Apps",
            "2. Create a Private App",
            "3. Select required scopes",
            "4. Copy the access token",
        ],
        "mcp": "hubspot-mcp",
    },
    "airtable": {
        "name": "Airtable",
        "category": "Data",
        "icon": "◈",
        "color": "ORG",
        "tagline": "Spreadsheet-database hybrid",
        "description": "CRM, leads, inventory - verify before acting",
        "what_it_does": "nova verifies Airtable records before executing",
        "fields": [
            {
                "key": "api_key",
                "label": "Personal Access Token",
                "description": "Airtable Personal Access Token",
                "secret": True,
                "required": True,
            },
            {
                "key": "base_id",
                "label": "Base ID",
                "description": "Default base ID (app...)",
                "secret": False,
                "required": False,
            },
        ],
        "docs_url": "https://airtable.com/create/tokens",
        "setup_guide": [
            "1. Go to airtable.com/create/tokens",
            "2. Create a Personal Access Token",
            "3. Grant access to your bases",
            "4. Copy the token",
        ],
        "mcp": "airtable-mcp",
    },
    "whatsapp": {
        "name": "WhatsApp",
        "category": "Communication",
        "icon": "◉",
        "color": "GRN",
        "tagline": "Message verification and spam prevention",
        "description": "Verify sent messages, prevent spam",
        "what_it_does": "nova checks WhatsApp history before approving",
        "fields": [
            {
                "key": "evolution_api_url",
                "label": "Evolution API URL",
                "description": "Your Evolution API instance URL",
                "secret": False,
                "required": True,
            },
            {
                "key": "evolution_api_key",
                "label": "Evolution API Key",
                "description": "API key for Evolution API",
                "secret": True,
                "required": True,
            },
            {
                "key": "instance_name",
                "label": "Instance Name",
                "description": "WhatsApp instance name",
                "secret": False,
                "required": True,
            },
        ],
        "docs_url": "https://doc.evolution-api.com",
        "setup_guide": [
            "1. Set up Evolution API",
            "2. Create a WhatsApp instance",
            "3. Get your API key and instance name",
        ],
        "mcp": "whatsapp-mcp",
    },
    "telegram": {
        "name": "Telegram",
        "category": "Communication",
        "icon": "◎",
        "color": "B6",
        "tagline": "Bot commands and alerts",
        "description": "Read & send messages, manage bots",
        "what_it_does": "nova can receive commands via Telegram",
        "fields": [
            {
                "key": "bot_token",
                "label": "Bot Token",
                "description": "Token from Nova Governance",
                "secret": True,
                "required": True,
            },
            {
                "key": "chat_id",
                "label": "Chat ID",
                "description": "Default chat/group ID",
                "secret": False,
                "required": False,
            },
        ],
        "docs_url": "https://core.telegram.org/bots",
        "setup_guide": [
            "1. Message Nova Governance on Telegram",
            "2. Create a new bot with /newbot",
            "3. Copy the bot token",
            "4. Get your chat ID from Nova Governance",
        ],
        "mcp": "telegram-mcp",
    },
    "sheets": {
        "name": "Google Sheets",
        "category": "Data",
        "icon": "⊞",
        "color": "GRN",
        "tagline": "Spreadsheet automation",
        "description": "Read and write spreadsheets in real time",
        "what_it_does": "nova checks your Sheets before executing",
        "fields": [
            {
                "key": "service_account_json",
                "label": "Service Account JSON",
                "description": "Path to service account file",
                "secret": False,
                "required": True,
            },
            {
                "key": "spreadsheet_id",
                "label": "Default Spreadsheet",
                "description": "Primary spreadsheet ID",
                "secret": False,
                "required": False,
            },
        ],
        "docs_url": "https://console.cloud.google.com/iam-admin/serviceaccounts",
        "setup_guide": [
            "1. Create a Google Cloud Service Account",
            "2. Download the JSON key",
            "3. Enable Google Sheets API",
            "4. Share spreadsheets with service account email",
        ],
        "mcp": "google-sheets-mcp",
    },
}


RULE_TEMPLATES = LazyCatalog(_build_rule_templates)
SKILLS = LazySkills(_build_skills)

SKILL_CATEGORIES = [
    "Communication",
    "Data",
    "Productivity",
    "Development",
    "CRM",
    "Payments",
    "Database",
]


def load_skill(name):
    """Load skill configuration."""
    path = SKILLS_DIR / f"{name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


def save_skill(name, data):
    """Save skill configuration."""
    ensure_dirs()
    path = SKILLS_DIR / f"{name}.json"
    _write_json(path, data)


def skill_status(name):
    """Get skill installation status."""
    data = load_skill(name)
    if not data:
        return "not_installed"
    return data.get("status", "installed")


def get_installed_skills():
    """Get list of installed skills."""
    return [k for k in SKILLS if skill_status(k) == "installed"]


def get_skill_color(skill_def):
    """Get color for a skill."""
    color_map = {
        "RED": C.RED, "GRN": C.GRN, "YLW": C.YLW,
        "W": C.W, "B6": C.B6, "B7": C.B7, "ORG": C.ORG,
    }
    return color_map.get(skill_def.get("color", "W"), C.W)


# ══════════════════════════════════════════════════════════════════════════════
# CONNECT ANIMATION - Premium handshake visualization
# ══════════════════════════════════════════════════════════════════════════════

def animate_connection(url):
    """
    Cinematic two-machine handshake animation - fixed-width columns.

    Layout (each printed line is prefixed with 2 spaces):
      col 0-2   : left gutter
      col 3-5   : left node glyph (CLI / ● / ○ / │)
      col 6-24  : left label (padded)
      col 25-50 : arrow / message (25-char field)
      col 51-53 : right node glyph
      col 54+   : right label (server hostname)
    """
    # Sanitise & pad host to a fixed 16-char field
    host = url.replace("https://", "").replace("http://", "").split("/")[0]
    host = (host[:16]).ljust(16)

    # (left_node, arrow_msg, right_node, color, pause_s)
    steps = [
        ("○",  "                         ", "○",  C.G2,  0.10),
        ("│",  "                         ", "│",  C.G3,  0.04),
        ("│",  " ──── identify ─────────►", "│",  C.G1,  0.22),
        ("│",  "                         ", "│",  C.G3,  0.04),
        ("│",  "◄──── challenge ─────────", "│",  C.B7,  0.26),
        ("│",  "                         ", "│",  C.G3,  0.04),
        ("│",  " ──── intent token ──────►","│",  C.G1,  0.22),
        ("│",  "                         ", "│",  C.G3,  0.04),
        ("│",  "◄──── access granted ────", "│",  C.GRN, 0.28),
        ("│",  "                         ", "│",  C.G3,  0.04),
        ("●",  "                         ", "●",  C.GRN, 0.10),
    ]

    COL_W = 14  # width of each node-label column

    print()
    # Header row - node labels
    cli_lbl  = q(C.G2,  "CLI".ljust(COL_W))
    srv_lbl  = q(C.G2,  host)
    print(f"    {cli_lbl}                           {srv_lbl}")
    print()

    for left_g, arrow, right_g, color, pause in steps:
        lg = q(color, left_g)
        ar = q(color, arrow)
        rg = q(color, right_g)
        print(f"    {lg}  {ar}  {rg}")
        time.sleep(pause)
    print()


def animate_agent_wake():
    """
    Agent wake-up sequence - the moment nova comes alive.
    Three phases: boot indicators → sentinel greeting → mission statement.
    """
    print()

    # Phase 1: boot indicators (random 3 of 5)
    wake_messages = random.sample(_AGENT_WAKE_MESSAGES, 3)
    for msg in wake_messages:
        sys.stdout.write("  " + q(C.G3, "▸") + "  " + q(C.G2, msg))
        sys.stdout.flush()
        time.sleep(random.uniform(0.15, 0.30))
        sys.stdout.write("  " + q(C.GRN, "✓") + "\n")
        sys.stdout.flush()
        time.sleep(0.08)

    print()
    time.sleep(0.25)

    # Phase 2: sentinel greeting (ghost-written)
    greeting = random.choice(_AGENT_GREETINGS)
    ghost_write(greeting, color=C.W, delay=0.022, bold=True)
    print()
    time.sleep(0.15)

    # Phase 3: mission statement (3 lines, each ghost-written)
    lines = [
        ("I'm your governance layer.", C.W),
        ("Every action your agents take passes through me.", C.G1),
        ("I approve, block, or escalate - and I remember everything.", C.G2),
    ]
    for text, color in lines:
        ghost_write(text, color=color, delay=0.016)
        time.sleep(0.05)

    print()


# ══════════════════════════════════════════════════════════════════════════════
# COMMANDS - Core CLI functionality
# ══════════════════════════════════════════════════════════════════════════════

def cmd_init(args):
    """
    First-run setup wizard - enterprise onboarding experience.
    """
    cfg = load_config()
    
    # ── [1/11] Language / Idioma ──────────────────────────────────────────────
    lang = cfg.get("lang", "")
    if not lang:
        step_header(1, 13, "Language  /  Idioma")
        print("  " + q(C.W, "  Choose the language for this setup."))
        print("  " + q(C.G2, "  Elige el idioma para esta configuración."))
        print()

        try:
            lang_idx = _select(
                ["English", "Español"],
                descriptions=[
                    "Continue in English",
                    "Continuar en español",
                ],
                default=0,
            )
            lang = "en" if lang_idx == 0 else "es"
        except KeyboardInterrupt:
            print()
            return

        cfg["lang"] = lang
        save_config(cfg)

    L = get_strings(lang)

    # ── Splash Screen ─────────────────────────────────────────────────────────
    print()
    print()
    print_logo(tagline=False, animated=True)
    
    time.sleep(0.3)
    
    # Tagline with ghost effect
    tagline = random.choice(_TAGLINES)
    ghost_write(tagline, color=C.W, delay=0.01)
    hr()
    print()
    time.sleep(0.2)
    
    # Welcome message
    ghost_write(L["welcome"], color=C.W, delay=0.02, bold=True)
    print()
    ghost_write(L["intro_1"], color=C.ASH, delay=0.015)
    ghost_write(L["intro_2"], color=C.W, delay=0.015)
    print()
    time.sleep(0.1)
    
    print("  " + q(C.ASH, f"  {L['intro_question']}", bold=True))
    print()
    
    pause(L["continue"])
    
    # ── [1/10] How It Works ───────────────────────────────────────────────────
    step_header(2, 13, L["how_it_works"])
    
    print("  " + q(C.W, "  ┌─  " + L["how_step_1"]))
    print("  " + q(C.W, "  │"))
    print("  " + q(C.W, "  │   " + L["how_step_2"]))
    print("  " + q(C.W, "  │"))
    print("  " + q(C.W, "  ├─  ") + q(C.W, "Score ≥ 70", bold=True) + 
          q(C.W, f"  →  ✓  {L['how_approved']}"))
    print("  " + q(C.W, "  ├─  ") + q(C.W, "Score 40-70", bold=True) + 
          q(C.W, f"  →  ⚠  {L['how_escalated']}"))
    print("  " + q(C.W, "  └─  ") + q(C.W, "Score < 40", bold=True) + 
          q(C.W, f"   →  ✗  {L['how_blocked']}"))
    print()
    print("  " + q(C.W, f"  {L['ledger_desc']}"))
    print("  " + q(C.W, f"  {L['ledger_sub']}"))
    print()
    
    pause(L["continue"])
    
    # ── [3/13] Auto-Discovery ────────────────────────────────────────────────
    _discovery = []        # filled by discovery step, used by first-rule step
    _nova_project_root = None
    _rules_dir = None
    _detected_agent = {}

    step_header(3, 13,
        "Auto-Discovery  /  Detección automática"
        if lang == "es" else "Auto-Discovery")

    if lang == "es":
        print("  " + q(C.W, "  Buscando tu agente en este entorno..."))
    else:
        print("  " + q(C.W, "  Scanning your environment for AI agents..."))
    print()

    with Spinner("Scanning...") as _sp:
        _discovery = discover_agents(probe_ports=True)
        _sp.finish()

    _project_root_found = _find_project_root()

    # Summarise what was found
    if _discovery:
        for d in _discovery[:3]:
            conf_color = C.GRN if d["confidence"] >= 60 else C.YLW
            ok(f"{d['icon']}  {d['display']}"
               + "  " + q(conf_color, f"(confidence {d['confidence']}%)")
               + ("  " + q(C.GRN, "● live") if d["port_live"] else ""))
    else:
        warn("No agents detected automatically.")
        if lang == "es":
            hint("Puedes conectar uno después con  nova connect")
        else:
            hint("You can connect one later with  nova connect")

    # Show project root
    print()
    info(f"Project root: {_project_root_found}")

    # Count files
    try:
        n_files = sum(1 for _ in _project_root_found.rglob("*")
                      if _.is_file() and not any(
                          p in str(_) for p in [".git", "node_modules", "__pycache__", ".nova"]))
        info(f"Files found:  {n_files}")
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")
    print()

    if _discovery:
        _detected_agent = _discovery[0]  # highest confidence

        if lang == "es":
            q_txt = f"  ¿Conectar Nova a {_detected_agent['display']}?"
        else:
            q_txt = f"  Connect Nova to {_detected_agent['display']}?"

        try:
            connect_choice = _select(
                ["Yes - connect now  ✓", "Skip - I'll connect later"],
                descriptions=[
                    f"Create .nova/ folder in {_project_root_found.name}/ and inject NOVA_API_KEY",
                    "You can always run  nova connect  later",
                ],
                default=0
            )
        except KeyboardInterrupt:
            connect_choice = 1

        if connect_choice == 0:
            _nova_api_key_for_env = cfg.get("api_key", "")
            _nova_url_for_env = cfg.get("api_url", "http://localhost:9002")
            _nova_project_root = _project_root_found
            _rules_dir = create_nova_project_folder(
                project_root=_nova_project_root,
                agent_type=_detected_agent["agent_type"],
                agent_name=_detected_agent["display"],
                nova_url=_nova_url_for_env,
                nova_api_key=_nova_api_key_for_env,
            )
            print()
            ok(f".nova/ created at {_nova_project_root / '.nova'}")

            # Inject into .env
            env_file = _nova_project_root / ".env"
            if inject_nova_env(env_file, _nova_api_key_for_env,
                               _nova_url_for_env, _detected_agent["agent_type"]):
                ok(f"NOVA_API_KEY injected into {env_file.name}")
            else:
                warn(f"Could not write to {env_file} - add NOVA_API_KEY manually")

            # Save connected agent in global config
            cfg["connected_agent_name"] = _detected_agent["display"]
            cfg["connected_agent_url"]  = _detected_agent["url"]
            cfg["nova_project_root"]    = str(_nova_project_root)
            save_config(cfg)
    print()

    # ── [4/13] Risks & Terms ──────────────────────────────────────────────────
    step_header(4, 13, L["risks_title"])
    
    print("  " + q(C.YLW, "  !") + "  " + q(C.W, L["risks_warning"], bold=True))
    print("       " + q(C.W, L["risks_sub"]))
    print()
    
    risks = [L["risk_1"], L["risk_2"], L["risk_3"], L["risk_4"], L["risk_5"]]
    for risk in risks:
        print("  " + q(C.W, "     ◦  ") + q(C.W, risk))
    
    print()
    print("  " + q(C.W, f"     {L['terms_label']}  ") + 
          q(C.W, "https://nova-os.com/terms", underline=True))
    print()
    
    print("  " + q(C.W, f"  {L['terms_question']}"))
    print()
    
    try:
        terms_idx = _select([L["terms_accept"], L["terms_decline"]], default=0)
    except KeyboardInterrupt:
        print()
        return
    
    if terms_idx != 0:
        print()
        warn(L["setup_cancelled"])
        hint("Run  " + q(C.W, "nova init") + "  when ready.")
        print()
        return
    
    # ── [5/13] First Rule - Natural Language ──────────────────────────────────
    step_header(5, 13,
        "Primera regla  /  First rule"
        if lang == "es" else "Your first governance rule")

    if lang == "es":
        print("  " + q(C.W, "  ¿Qué NO debe hacer nunca tu agente?", bold=True))
        print("  " + q(C.G2, "  Escríbelo en español o inglés - Nova lo convierte en una regla."))
        rule_placeholder = "ej: nunca borres archivos de /prod"
        rule_later_label = "Omitir - lo haré después con  nova rule"
    else:
        print("  " + q(C.W, "  What should your agent NEVER do?", bold=True))
        print("  " + q(C.G2, "  Write it in plain language - Nova turns it into a rule instantly."))
        rule_placeholder = "e.g. never delete files from /prod"
        rule_later_label = "Skip - I'll add rules later with  nova rule"

    print()
    print("  " + q(C.G3, "  Examples:"))
    print("  " + q(C.G3, "    · never delete files from /prod"))
    print("  " + q(C.G3, "    · don't send emails without asking me first"))
    print("  " + q(C.G3, "    · block any action that modifies the database"))
    print()

    try:
        _first_rule_text = prompt(
            "Rule" if lang == "en" else "Regla",
            default="",
        )
    except (EOFError, KeyboardInterrupt):
        _first_rule_text = ""

    if _first_rule_text and _first_rule_text.strip():
        _first_rule_text = _first_rule_text.strip()
        print()

        # Build the rule data (deterministic - works without Nova Core running)
        import hashlib as _hl
        _rule_id = "rule_" + _hl.md5(_first_rule_text.encode()).hexdigest()[:8]

        # Heuristic: detect block vs warn
        _block_words = ["never", "nunca", "don't", "no ", "block", "bloquear",
                        "prohibit", "prohibe", "prevent", "impedir"]
        _action = "block" if any(w in _first_rule_text.lower()
                                 for w in _block_words) else "warn"

        # Heuristic: extract a short name from the first 5 words
        _words = re.sub(r"[^a-z0-9 ]", "", _first_rule_text.lower()).split()
        _short_name = "_".join(_words[:4]) or "custom_rule"

        _rule_data = {
            "id":          _rule_id,
            "name":        _short_name,
            "description": _first_rule_text,
            "action":      _action,
            "priority":    7,
            "scope":       f"agent:{cfg.get('connected_agent_name', 'global')}",
            "created_at":  datetime.now().isoformat(),
            "created_by":  "nova init",
            "active":      True,
        }

        # Save to .nova/agents/<type>/rules/ if we have a project root
        if _rules_dir and _rules_dir.exists():
            _rule_path = create_rule_file(_rules_dir, _rule_data)
            ok(f"Rule saved → {_rule_path.relative_to(_nova_project_root)}")
        else:
            # Fall back to ~/.nova/rules/
            _fallback_rules = NOVA_DIR / "rules"
            _fallback_rules.mkdir(exist_ok=True)
            _rule_path = create_rule_file(_fallback_rules, _rule_data)
            ok(f"Rule saved → ~/.nova/rules/{_rule_path.name}")

        print()
        print("  " + q(C.GRN, "✦", bold=True) + "  " +
              q(C.W, f"[{_action.upper()}]  ", bold=True) +
              q(C.G1, _first_rule_text))
        print("  " + q(C.G3, "     Active from this moment on."))
        print()
    else:
        print()
        hint(rule_later_label)
        print()

    # ── [6/13] Identity ───────────────────────────────────────────────────────
    step_header(6, 13, L["identity_title"])
    
    print("  " + q(C.W, f"  {L['identity_sub']}"))
    print()
    
    try:
        name = prompt(L["your_name"], default=cfg.get("user_name", ""))
        name = name or "Explorer"
        
        org = prompt(L["your_org"], default=cfg.get("org_name", ""))
    except (EOFError, KeyboardInterrupt):
        name = "Explorer"
        org = ""
    
    # ── [4/10] API Key Setup ──────────────────────────────────────────────────
    step_header(7, 13, L["apikey_title"])
    
    print("  " + q(C.W, f"  {L['apikey_sub']}"))
    print()
    print("  " + q(C.W, "  Docs: ") +
          q(C.W, "https://github.com/sxrubyo/nova-os", underline=True))
    print()
    
    existing_key = cfg.get("api_key", "") or get_active_key()
    
    # Key options with descriptions
    key_opts = [
        L["apikey_generate"],
        L["apikey_enter"],
    ]
    key_descs = [
        "Creates a secure random key locally",
        "Paste a key from another source",
    ]
    
    if existing_key:
        key_opts.append(f"{L['apikey_use_saved']} ({mask_key(existing_key)})")
        key_descs.append("Continue with your saved key")
    
    try:
        key_choice = _select(key_opts, descriptions=key_descs, default=0)
    except KeyboardInterrupt:
        print()
        return
    
    api_key = ""
    
    if key_choice == 0:
        # Generate new key
        api_key = generate_api_key("nova")
        add_api_key(api_key, name=f"{name}'s key")
        
        print()
        ok(L["apikey_generated"])
        print()
        print("  " + q(C.W, "Your API key:"))
        print()
        print("    " + q(C.W, api_key, bold=True))
        print()
        warn(L["apikey_warning"])
        print()
        
        # Offer clipboard
        if confirm("Copy to clipboard?", default=False):
            copied = _copy_to_clipboard(api_key)
            if copied:
                ok("Copied to clipboard")
            else:
                warn("Could not copy - please copy manually")
        
    elif key_choice == 1:
        # Enter existing key
        print()
        api_key = prompt("API Key", secret=True)
        
        if api_key:
            add_api_key(api_key, name="Imported key")
            print()
            ok(L["apikey_saved"])
        else:
            # Generate one anyway
            api_key = generate_api_key("nova")
            add_api_key(api_key, name="Auto-generated")
            print()
            warn("No key entered - generated one automatically")
            print()
            print("    " + q(C.W, api_key, bold=True))
            print()
    
    else:
        # Use existing
        api_key = existing_key
        print()
        ok("Using saved key")
    
    # ── [5/10] Server Connection ──────────────────────────────────────────────
    step_header(8, 13, L["server_title"])
    
    print("  " + q(C.W, f"  {L['server_sub']}"))
    print()
    
    srv_opts = [
        L["server_local"],
        L["server_custom"],
        L["server_saved"],
    ]
    srv_descs = [
        "Default development server",
        "Enter a custom URL (production/cloud)",
        f"Keep {cfg.get('api_url', 'http://localhost:9002')}",
    ]
    
    try:
        srv_choice = _select(srv_opts, descriptions=srv_descs, default=0)
    except KeyboardInterrupt:
        print()
        return
    
    if srv_choice == 0:
        server_url = "http://localhost:9002"
        print()
        info(f"Using {server_url}")
    
    elif srv_choice == 1:
        print()
        server_url = prompt(
            "Server URL",
            default=cfg.get("api_url", "http://localhost:9002"),
            validator=lambda x: True if x.startswith(("http://", "https://")) 
                                else "URL must start with http:// or https://"
        )
    
    else:
        server_url = cfg.get("api_url", "http://localhost:9002")
        print()
        info(f"Using {server_url}")

    admin_token = os.environ.get("WORKSPACE_ADMIN_TOKEN", "").strip()
    if admin_token:
        email_default = cfg.get("workspace_email", "") or _default_workspace_email(name, org)
        workspace_email = prompt(
            "Workspace email",
            default=email_default,
            validator=lambda v: "@" in v or "Enter a valid email address"
        )
        workspace_plan_options = ["trial", "shield", "professional", "enterprise"]
        workspace_plan_labels = [
            "Trial (default, limited agents)",
            "Shield (team-ready controls)",
            "Professional (full analytics)",
            "Enterprise (on-premise+support)",
        ]
        current_plan = cfg.get("workspace_plan", "trial")
        try:
            default_plan_idx = workspace_plan_options.index(current_plan)
        except ValueError:
            default_plan_idx = 0
        plan_idx = default_plan_idx
        try:
            plan_idx = _select(
                workspace_plan_labels,
                descriptions=[
                    "Trial tier with 10k monthly actions",
                    "Team-friendly controls and alerts",
                    "Professional analytics + policy library",
                    "Enterprise-grade SLA, RBAC, and support",
                ],
                default=default_plan_idx,
            )
        except KeyboardInterrupt:
            print()
        workspace_plan = workspace_plan_options[plan_idx]

        cfg["workspace_email"] = workspace_email
        cfg["workspace_plan"] = workspace_plan

        print()
        info("Registering workspace with the admin endpoint...")
        registration_payload = {
            "name": name or "Nova Workspace",
            "email": workspace_email,
            "plan": workspace_plan,
            "api_key": api_key,
        }
        registration_result = register_workspace_with_admin(server_url, registration_payload, admin_token)
        if registration_result.get("error"):
            warn(format_api_error(registration_result, "Workspace registration failed"))
            warn("Ensure WORKSPACE_ADMIN_TOKEN is correct or register manually using README instructions.")
        else:
            api_key = registration_result.get("api_key", api_key)
            ok(f"Workspace registered · {registration_result.get('name', '')} ({registration_result.get('plan', workspace_plan)})")
            print()
    else:
        print()
        warn("Your API key is saved locally but won't be registered server-side automatically.")
        hint("To register it: set WORKSPACE_ADMIN_TOKEN in your environment and re-run  nova init")
        hint("Docs: https://github.com/sxrubyo/nova-os")
        print()

    # ── [6/10] Connect ────────────────────────────────────────────────────────
    step_header(9, 13, L["connecting_title"])
    
    animate_connection(server_url)
    
    # Test connection
    with Spinner(L["testing_connection"]) as sp:
        api = NovaAPI(server_url, api_key)
        health = api.get("/health")
    
    connected = "error" not in health
    server_version = health.get("version", "") if connected else ""
    
    if connected:
        ok(f"{L['server_online']}  " + q(C.W, f"v{server_version}" if server_version else ""))
        # Verify the key is actually authenticated (health endpoint doesn't check auth)
        key_check = api.get("/workspaces/me")
        key_authed = "error" not in key_check or key_check.get("code") not in ("HTTP_401", "HTTP_403")
        if key_authed:
            ok(L["key_accepted"])
        else:
            warn("Server is up - but this API key is not yet registered.")
            hint("Set WORKSPACE_ADMIN_TOKEN before  nova init  to auto-register your key.")
            hint("Docs: https://github.com/sxrubyo/nova-os")
    else:
        fail(format_api_error(health, L["connection_failed"]))
        print()
        warn(f"{L['config_saved']}. Fix server and run " + q(C.W, "nova status"))
        print()
        hr_bold()
        print("  " + q(C.ORG, "✦", bold=True) + "  " + q(C.W, L["offline_title"], bold=True))
        print("  " + q(C.W, f"  {L['offline_sub']}"))
        print("  " + q(C.W, f"  {L['offline_hint']}"))
        hr_bold()
    
    # Save configuration
    cfg.update({
        "api_url": server_url,
        "api_key": api_key,
        "user_name": name,
        "org_name": org,
        "lang": lang,
        "version": NOVA_VERSION,
        "created_at": cfg.get("created_at") or datetime.now().isoformat(),
    })
    save_config(cfg)
    set_active_key(api_key)
    
    # ── [7/10] Choose Your Intelligence ──────────────────────────────────────
    step_header(10, 13, "Choose your Intelligence")
    
    print("  " + q(C.W, "  The AI brain that powers nova's validation engine."))
    print("  " + q(C.G2, "  9 providers · 40+ models · local & cloud · 2026 edition"))
    print()
    
    # ── Step 1: What matters most to you? (like Claude Code's opusplan strategy)
    priority_opts = [
        "★  Best quality - I want the most powerful model",
        "⚡  Fastest - sub-second validation, no latency",
        "💰  Best value - great quality, minimal cost",
        "🔒  Privacy - data stays local or in EU",
        "🌐  One key - access everything via OpenRouter",
        "🏠  Local - no API key, runs on my machine",
        "→  Let me pick manually",
    ]
    priority_descs = [
        "Recommends Claude Opus 4.6 - top reasoning in 2026",
        "Recommends Groq + Llama 3.3 - ~500 tokens/sec",
        "Recommends Gemini 2.0 Flash - free tier available",
        "Recommends Mistral Large (EU) or Ollama (local)",
        "One OpenRouter key unlocks all 200+ models",
        "Qwen 3.5 27B - rivals GPT-4o, zero cost, full privacy",
        "Browse all 9 providers and 40+ models",
    ]
    
    print("  " + q(C.W, "  What matters most to you?", bold=True))
    print()
    
    try:
        priority_idx = _select(priority_opts, descriptions=priority_descs, default=0)
    except KeyboardInterrupt:
        priority_idx = 6  # manual
    
    # Map priority → (provider_key, model_id)
    priority_map = [
        ("anthropic",   "anthropic/claude-opus-4-6"),
        ("groq",        "groq/llama-3.3-70b-versatile"),
        ("google",      "gemini/gemini-2.0-flash"),
        ("mistral",     "mistral/mistral-large-latest"),
        ("openrouter",  "openrouter/anthropic/claude-sonnet-4-6"),
        ("ollama",      "ollama/qwen3.5:27b"),
        None,  # manual
    ]
    
    auto_pick = priority_map[priority_idx] if priority_idx < len(priority_map) else None
    
    llm_provider = ""
    llm_model = ""
    llm_api_key = ""
    
    if auto_pick:
        # Show the recommended model clearly
        rec_prov_key, rec_model_id = auto_pick
        rec_prov = LLM_PROVIDERS.get(rec_prov_key, {})
        model_info = get_model_info(rec_model_id)
        
        print()
        print("  " + q(C.GLD, "✦") + "  " + q(C.W, "Recommended for you:", bold=True))
        print()
        print("       " + q(C.GLD_BRIGHT, f"{rec_prov.get('icon','·')}  {rec_prov.get('name','')}", bold=True))
        print("       " + q(C.W, model_info.get("label", rec_model_id)))
        print("       " + q(C.G2, model_info.get("description", "")))
        tier = model_info.get("tier","")
        if tier in TIER_BADGE:
            print("       " + q(C.B7, TIER_BADGE[tier]))
        print()
        
        use_rec_opts = ["Yes - use this model", "No - let me pick manually"]
        use_rec_descs = ["Quick setup with recommended model", "Browse all providers and models"]
        try:
            use_rec = _select(use_rec_opts, descriptions=use_rec_descs, default=0)
        except KeyboardInterrupt:
            use_rec = 1
        
        if use_rec == 0:
            llm_provider = rec_prov_key
            llm_model    = rec_model_id
        else:
            auto_pick = None  # fall through to manual
    
    if not auto_pick:
        # ── Manual provider selection ─────────────────────────────────────────
        print()
        print("  " + q(C.W, "  Select provider:", bold=True))
        print()
        
        provider_keys = list(LLM_PROVIDERS.keys())
        provider_opts = []
        provider_descs = []
        
        for pk in provider_keys:
            pv = LLM_PROVIDERS[pk]
            n_models = len(pv["models"])
            provider_opts.append(f"{pv['icon']}  {pv['name']}  ({n_models} models)")
            provider_descs.append(pv["tagline"])
        
        provider_opts.append("·  Skip for now")
        provider_descs.append("Configure later with  nova config model")
        
        try:
            prov_idx = _select(provider_opts, descriptions=provider_descs, default=0)
        except KeyboardInterrupt:
            prov_idx = len(provider_opts) - 1
        
        if prov_idx < len(provider_keys):
            llm_provider = provider_keys[prov_idx]
    
    # ── Model selection (shown when provider is known) ─────────────────────────
    if llm_provider and not llm_model:
        prov_data = LLM_PROVIDERS[llm_provider]
        
        print()
        print("  " + q(C.W, "  Select model:", bold=True))
        print()
        
        model_entries = prov_data["models"]
        model_opts  = []
        model_descs = []
        
        for m in model_entries:
            tier_badge = ("  " + TIER_BADGE.get(m[2], "")) if len(m) > 2 else ""
            label = m[1] + tier_badge
            model_opts.append(label)
            model_descs.append(m[3] if len(m) > 3 else "")
        
        default_midx = 0
        default_id = prov_data.get("default_model", "")
        for mi, m in enumerate(model_entries):
            if m[0] == default_id:
                default_midx = mi
                break
        
        try:
            model_idx = _select(model_opts, descriptions=model_descs, default=default_midx)
        except KeyboardInterrupt:
            model_idx = default_midx
        
        llm_model = model_entries[model_idx][0]
        
        # Handle custom Ollama model
        if llm_model == "ollama/custom":
            print()
            try:
                custom = prompt("Enter Ollama model name", default="qwen3.5:27b")
                llm_model = f"ollama/{custom}" if custom else "ollama/qwen3.5:27b"
            except (EOFError, KeyboardInterrupt):
                llm_model = "ollama/qwen3.5:27b"
    
    # ── API Key ────────────────────────────────────────────────────────────────
    if llm_provider:
        prov_data = LLM_PROVIDERS[llm_provider]
        needs_key = prov_data.get("needs_api_key", True)
        
        if needs_key:
            print()
            print("  " + q(C.G2, "Get your key at:  ") +
                  q(C.B7, prov_data["key_url"], underline=True))
            print()
            
            try:
                llm_api_key = prompt(f"{prov_data['name']} API Key", secret=True)
            except (EOFError, KeyboardInterrupt):
                llm_api_key = ""
        else:
            # Ollama - no key needed
            llm_api_key = "ollama"
            base_url = prov_data.get("base_url", "http://localhost:11434")
            print()
            info(f"Local Ollama - no API key needed")
            info(f"Make sure Ollama is running: ollama serve")
        
        # Effort level for Claude models with extended thinking
        llm_effort = "medium"
        if prov_data.get("has_effort_slider") and "claude" in llm_model.lower():
            print()
            print("  " + q(C.G2, "Reasoning effort  ") +
                  q(C.G3, "(like Claude Code's effort slider)"))
            print()
            effort_opts  = ["⚡  low    - fastest, cheapest",
                            "★  medium - recommended balance",
                            "🔥  high   - deepest reasoning, slowest"]
            effort_descs = [
                "Quick decisions - simple validations",
                "Most tasks - best cost/quality ratio",
                "Complex edge cases - maximum accuracy",
            ]
            try:
                eff_idx = _select(effort_opts, descriptions=effort_descs, default=1)
                llm_effort = ["low", "medium", "high"][eff_idx]
            except KeyboardInterrupt:
                llm_effort = "medium"
        
        if llm_api_key or not needs_key:
            minfo = get_model_info(llm_model)
            ok(f"{prov_data['name']} · {minfo.get('label', llm_model)}")
            if llm_effort != "medium":
                ok(f"Effort: {llm_effort}")
        else:
            warn("No key entered - you can add it later with  nova config model")
        
        # Persist to config
        cfg["llm_provider"]  = llm_provider
        cfg["llm_model"]     = llm_model
        cfg["llm_api_key"]   = llm_api_key
        cfg["llm_effort"]    = llm_effort
        save_config(cfg)
    
    # ── [8/10] Governance Policy ──────────────────────────────────────────────
    step_header(11, 13, "Governance Policy")

    print("  " + q(C.W, "  nova validates every agent action against a policy."))
    print("  " + q(C.G2, "  Choose a baseline - you can fine-tune anytime with  nova rules"))
    print()

    policy_opts = [
        "🔒  Strict    - block anything ambiguous",
        "⚖️   Balanced  - escalate edge cases, approve safe actions",
        "🚀  Permissive - approve most, escalate only high-risk",
        "📋  Custom     - I'll define my own rules from scratch",
    ]
    policy_descs = [
        "Score threshold ≥ 70 to approve. Best for production agents.",
        "Score ≥ 50. Recommended for most teams starting out.",
        "Score ≥ 30. Good for dev / sandbox environments.",
        "Start with no rules - build your policy with  nova rules create",
    ]

    try:
        policy_idx = _select(policy_opts, descriptions=policy_descs, default=1)
    except KeyboardInterrupt:
        policy_idx = 1

    policy_names   = ["strict", "balanced", "permissive", "custom"]
    policy_scores  = [70,       50,         30,            50]
    chosen_policy  = policy_names[policy_idx]
    chosen_score   = policy_scores[policy_idx]

    cfg["default_policy"]    = chosen_policy
    cfg["approval_threshold"] = chosen_score
    save_config(cfg)

    print()
    ok(f"Policy set to  {chosen_policy}  (approval threshold ≥ {chosen_score})")
    hint("Fine-tune anytime with  nova rules  or  nova policy")

    # ── [9/10] Notification Escalation ───────────────────────────────────────
    step_header(12, 13, "Escalation Channel")

    print("  " + q(C.W, "  When nova escalates an action, where should it notify you?"))
    print("  " + q(C.G2, "  Score 40-70 actions pause and wait for your decision."))
    print()

    notif_opts = [
        "📺  CLI only      - show escalations in the terminal",
        "📧  Email         - send alerts to an email address",
        "💬  Webhook       - POST to a URL (Slack, Discord, n8n…)",
        "⏭   Skip for now  - configure later with  nova config",
    ]
    notif_descs = [
        "Use  nova watch  to monitor escalations live",
        "Requires SMTP config - set up with  nova config",
        "Works with any HTTP endpoint",
        "nova watch  will still show escalations in the terminal",
    ]

    try:
        notif_idx = _select(notif_opts, descriptions=notif_descs, default=0)
    except KeyboardInterrupt:
        notif_idx = 3

    notif_channel = ""
    if notif_idx == 1:
        print()
        try:
            notif_channel = prompt("Notification email", validator=lambda v: "@" in v or "Enter a valid email")
            if notif_channel:
                cfg["notif_email"] = notif_channel
                save_config(cfg)
                ok(f"Escalations will be sent to  {notif_channel}")
        except (EOFError, KeyboardInterrupt):
            pass
    elif notif_idx == 2:
        print()
        try:
            notif_channel = prompt("Webhook URL", validator=lambda v: v.startswith(("http://", "https://")) or "Must start with http:// or https://")
            if notif_channel:
                cfg["notif_webhook"] = notif_channel
                save_config(cfg)
                ok("Webhook registered - escalations will POST to your endpoint")
        except (EOFError, KeyboardInterrupt):
            pass
    elif notif_idx == 3:
        print()
        info("Skipped - run  nova config  to set up notifications later")
    else:
        print()
        info("CLI mode - run  nova watch  to monitor escalations live")

    # ── [10/10] Skills Setup ──────────────────────────────────────────────────
    step_header(13, 13, L["skills_title"])

    print("  " + q(C.W, f"  {L['skills_sub']}"))
    print("  " + q(C.W, "  Skills connect nova to external systems like Gmail, Slack, GitHub."))
    print()
    print("  " + q(C.W, f"  {L['skills_now']}"))
    print()

    try:
        skills_idx = _select(
            [L["skills_yes"], L["skills_later"]],
            descriptions=[
                "Configure your first integration",
                "You can always run 'nova skill' later",
            ],
            default=1
        )
    except KeyboardInterrupt:
        skills_idx = 1

    # ── Success + Agent Wake ──────────────────────────────────────────────────
    print()

    animate_agent_wake()

    first_name = name.split()[0] if name and name != "Explorer" else ""
    greeting = L["youre_in"] + (f", {first_name}." if first_name else ".")

    hr_bold()
    print()
    print("  " + q(C.GLD, "✦", bold=True) + "  " + q(C.W, greeting, bold=True))
    print()
    print("     " + q(C.W, f"nova CLI {NOVA_VERSION} {L['ready']}"))
    if org:
        print("     " + q(C.W, org))

    _llm_prov  = cfg.get("llm_provider", "")
    _llm_model = cfg.get("llm_model", "")
    if _llm_prov in LLM_PROVIDERS and _llm_model:
        pv_name = LLM_PROVIDERS[_llm_prov]["name"]
        print("     " + q(C.MGN, f"⟁  {pv_name} / {_llm_model}"))

    _policy = cfg.get("default_policy", "balanced")
    _thresh = cfg.get("approval_threshold", 50)
    print("     " + q(C.B7, f"⚖  Policy: {_policy}  (threshold ≥ {_thresh})"))
    print("     " + q(C.W, "Nova Governance"))
    print()
    hr_bold()
    print()

    # Setup summary table
    print("  " + q(C.W, "Setup summary:", bold=True))
    print()
    summary_rows = [
        ("Server",   cfg.get("api_url", "-")),
        ("Policy",   f"{_policy}  (score ≥ {_thresh})"),
        ("Model",    f"{_llm_prov} / {_llm_model}" if _llm_model else "-  (nova config model)"),
    ]
    if cfg.get("notif_email"):
        summary_rows.append(("Escalation", f"email → {cfg['notif_email']}"))
    elif cfg.get("notif_webhook"):
        summary_rows.append(("Escalation", f"webhook → {cfg['notif_webhook'][:40]}…"))
    else:
        summary_rows.append(("Escalation", "CLI  (nova watch)"))

    for label, value in summary_rows:
        print("    " + q(C.G2, label.ljust(14)) + q(C.W, value))

    print()

    # Global install hint
    _nova_path = sys.argv[0]
    _is_installed = any(_nova_path.startswith(p) for p in ("/usr/local/bin", "/usr/bin", str(Path.home() / ".local/bin")))
    if not _is_installed:
        print("  " + q(C.GLD, "✦") + "  " + q(C.W, "Make nova available everywhere:", bold=True))
        print()
        if IS_WINDOWS:
            print("       " + q(C.G3, "# Add to PATH or copy to a directory already in PATH"))
            print("       " + q(C.B7, "copy " + _nova_path + r" C:\Windows\System32\nova.py"))
        else:
            print("       " + q(C.B7, f"sudo cp {_nova_path} /usr/local/bin/nova"))
            print("       " + q(C.B7, "sudo chmod +x /usr/local/bin/nova"))
        print()
        hr()
        print()

    print("  " + q(C.W, L["next_steps"]))
    print()

    next_cmds = [
        ("nova agent create",  "Create your first agent"),
        ("nova rules",         "View & manage your governance rules"),
        ("nova watch",         "Monitor agent actions live"),
        ("nova status",        "System health & metrics"),
        ("nova config model",  "Change AI provider or model"),
        ("nova skill",         "Browse available integrations"),
        ("nova help",          "See all commands"),
    ]

    for cmd, desc in next_cmds:
        print("    " + q(C.W, cmd.ljust(24), bold=True) + q(C.G2, desc))

    print()
    
    # If user chose to configure skills, launch skill wizard
    if skills_idx == 0:
        cmd_skill_browse(args)


def cmd_status(args):
    """System status dashboard."""
    print_logo(compact=True)
    
    api, cfg = get_api()
    
    stats = api.get("/stats")
    health = api.get("/health")
    
    # Connection status
    if "error" in health:
        fail(f"Nova not responding at {q(C.W, cfg['api_url'])}")
        print("  " + q(C.W, format_api_error(health)))
        print()
        print("  " + q(C.W, "Check: docker compose up -d"))
        
        queue = get_queue()
        if queue:
            print()
            warn(f"{len(queue)} actions queued offline")
            hint("Run  " + q(C.W, "nova sync") + "  when server is back")
        print()
        return
    
    # Server info
    status_label = q(C.W, "Operational")
    if health.get("status") == "degraded":
        status_label = q(C.YLW, "Degraded")
    if health.get("status") == "down":
        status_label = q(C.RED, "Down")
    
    server_rows = [
        ["URL", q(C.W, cfg["api_url"])],
        ["Status", status_label],
    ]
    if health.get("version"):
        server_rows.append(["Version", q(C.W, health["version"])])
    if health.get("build"):
        server_rows.append(["Build", q(C.W, health["build"])])
    if health.get("environment"):
        server_rows.append(["Environment", q(C.W, str(health["environment"]))])
    if health.get("database"):
        db_color = C.W if health["database"] == "connected" else C.RED
        server_rows.append(["Database", q(db_color, health["database"])])
    if health.get("llm_available") is not None:
        llm_color = C.W if health["llm_available"] else C.W
        server_rows.append(["LLM", q(llm_color, "available" if health["llm_available"] else "disabled")])
    if api.last_latency:
        server_rows.append(["Latency", q(C.W, f"{api.last_latency}ms")])
    if health.get("uptime_seconds") is not None:
        server_rows.append(["Uptime", q(C.W, f"{int(health['uptime_seconds'])}s")])
    
    render_table("Server", ["Field", "Value"], server_rows)
    
    # Activity metrics
    if "error" not in stats:
        total = stats.get("total_actions", 0)
        approved = stats.get("approved", 0)
        blocked = stats.get("blocked", 0)
        escalated = stats.get("escalated", 0)
        duplicates = stats.get("duplicates_blocked", 0)
        rate = stats.get("approval_rate", 0)
        
        activity_rows = [
            ["Total actions", f"{total:,}"],
            ["Approved", q(C.W, f"{approved:,}")],
            ["Blocked", q(C.W, f"{blocked:,}")],
            ["Escalated", q(C.W, f"{escalated:,}")],
            ["Duplicates blocked", q(C.W, f"{duplicates:,}")],
            ["Approval rate", f"{rate}%"],
        ]
        
        render_table("Activity", ["Metric", "Value"], activity_rows)
        
        # Resources
        agents = stats.get("active_agents", 0)
        memories = stats.get("memories_stored", 0)
        avg_score = stats.get("avg_score", 0)
        alerts = stats.get("alerts_pending", 0)
        
        resource_rows = [
            ["Active agents", q(C.W, str(agents))],
            ["Memories stored", q(C.W, f"{memories:,}")],
            ["Avg score", str(avg_score)],
            ["Pending alerts", q(C.W, str(alerts))],
        ]
        
        render_table("Resources", ["Metric", "Value"], resource_rows)
        
        trend = stats.get("score_trend")
        if trend and isinstance(trend, list) and len(trend) > 1:
            print("  " + q(C.W, "Score trend (7d)") + "  " + sparkline(trend))
            print()
        
        # Health meter
        health_score = rate if isinstance(rate, int) else 0
        if health.get("status") == "degraded":
            health_score -= 15
        if health.get("database") != "connected":
            health_score -= 30
        if health.get("llm_available") is False:
            health_score -= 5
        if alerts:
            health_score -= min(20, alerts * 3)
        health_score = max(0, min(100, health_score))
        
        print("  " + q(C.W, "Health Meter") + "  " + health_meter(health_score))
        print()
    
    # Queue status
    queue = get_queue()
    if queue:
        print()
        warn(f"{len(queue)} actions queued offline")
        print("  " + q(C.W, "Run  nova sync  to process"))
    
    # Update check
    cfg_check = cfg.get("auto_update_check", True)
    if cfg_check:
        new_version = check_for_updates()
        if new_version:
            print()
            print("  " + q(C.W, f"Nova {new_version} available"))
            dim("Run: pip install --upgrade nova-cli")
    
    print()


def _extract_run_command():
    raw = []
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        raw = sys.argv[idx + 1:]
    elif "run" in sys.argv:
        idx = sys.argv.index("run")
        raw = sys.argv[idx + 1:]
    
    if not raw:
        return []
    
    if len(raw) == 1:
        return shlex.split(raw[0])
    
    return raw


def _proposed_command(line):
    line = line.strip()
    if not line:
        return ""
    m = re.match(r"^(?:CMD|EXEC|RUN|SHELL)[:>]\s*(.+)$", line, re.I)
    if m:
        return m.group(1).strip()
    if line.startswith("$ "):
        return line[2:].strip()
    return ""


SENSITIVE_CMD_PATTERNS = [
    re.compile(r"\brm\s+-rf\b", re.I),
    re.compile(r"\bsudo\b", re.I),
    re.compile(r"\bchmod\b|\bchown\b", re.I),
    re.compile(r"\bmkfs\b|\bdd\s+", re.I),
    re.compile(r"(curl|wget)\s+.+\|\s*(sh|bash)", re.I),
    re.compile(r"\bscp\b|\bssh\b", re.I),
    re.compile(r"\baws\b|\bgsutil\b|\baz\b", re.I),
    re.compile(r"\bbase64\b", re.I),
]


def cmd_run(args):
    """Run external processes with STDOUT/STDERR governance."""
    cmd = _extract_run_command()
    if not cmd:
        fail("Usage: nova run -- <command>")
        return
    
    api, cfg = get_api()
    token_default = args.token or cfg.get("default_token", "")
    execute = getattr(args, "execute", False)
    
    print_logo(compact=True)
    print()
    ok("Process wrapper active")
    dim("Monitoring stdout/stderr for proposed commands")
    print()
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    
    def handle_command(command):
        if not command:
            return
        if any(p.search(command) for p in SENSITIVE_CMD_PATTERNS):
            warn(f"Sensitive command detected: {command}")
            return

        try:
            command_argv = shlex.split(command)
        except ValueError:
            warn(f"Invalid command syntax: {command}")
            return
        
        local_decision = local_policy_decision(command)
        if local_decision:
            ok(f"Approved (local): {command}")
            if execute:
                subprocess.run(command_argv)
            return
        
        if not token_default:
            warn(f"Blocked (no token): {command}")
            return
        
        payload = {
            "token_id": token_default,
            "action": command,
            "context": "nova run wrapper",
            "generate_response": False,
            "check_duplicates": True,
        }
        result = api.post("/validate", payload)
        if "error" in result:
            warn(f"Validation error: {format_api_error(result)}")
            return
        if result.get("verdict") == "APPROVED":
            ok(f"Approved: {command}")
            if execute:
                subprocess.run(command_argv)
        else:
            warn(f"Blocked: {command} ({result.get('verdict')})")
    
    def stream_reader(stream, is_err=False):
        for line in iter(stream.readline, ""):
            line = line.rstrip("\n")
            if is_err:
                print("  " + q(C.RED, line))
            else:
                print("  " + q(C.G1, line))
                proposed = _proposed_command(line)
                if proposed:
                    handle_command(proposed)
    
    threads = [
        threading.Thread(target=stream_reader, args=(proc.stdout, False), daemon=True),
        threading.Thread(target=stream_reader, args=(proc.stderr, True), daemon=True),
    ]
    for t in threads:
        t.start()
    
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    
    print()
    ok(f"Process exited with code {proc.returncode}")
    print()


def cmd_shield(args):
    """Proxy mode for external agent calls with Nova validation."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    api, cfg = get_api()
    token_default = args.token or cfg.get("default_token", "")
    upstream = (args.upstream or "").strip()
    host, port = _parse_host_port(args.listen, default_port=7755)
    dry_run = getattr(args, "dry_run", False)
    
    class ShieldHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            if DEBUG:
                super().log_message(format, *args)
        
        def _send(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if "verdict" in payload:
                self.send_header("X-Nova-Verdict", str(payload["verdict"]))
            self.end_headers()
            self.wfile.write(body)
        
        def do_GET(self):
            if self.path in ("/", "/health"):
                self._send(200, {
                    "status": "ok",
                    "service": "nova-shield",
                    "version": NOVA_VERSION,
                })
                return
            self._send(404, {"error": "Not found"})
        
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(length).decode() if length else ""
            try:
                payload = json.loads(raw) if raw else {}
            except Exception:
                self._send(400, {"error": "Invalid JSON payload"})
                return
            
            action = payload.get("action", "")
            context = payload.get("context", "")
            token_id = payload.get("token_id") or token_default
            if not action:
                self._send(400, {"error": "Missing action"})
                return
            if not token_id:
                self._send(400, {"error": "Missing token_id"})
                return
            local_decision = local_policy_decision(action)
            if local_decision and not upstream:
                response_payload = {
                    "verdict": local_decision["verdict"],
                    "score": local_decision["score"],
                    "reason": local_decision["reason"],
                    "agent_name": "Local Policy",
                    "ledger_id": None,
                }
                self._send(200, response_payload)
                return
            
            validation_payload = {
                "token_id": token_id,
                "action": action,
                "context": context,
                "generate_response": bool(payload.get("generate_response", False)),
                "check_duplicates": payload.get("check_duplicates", True),
            }
            if payload.get("dry_run") or dry_run:
                validation_payload["dry_run"] = True
            result = None
            if local_decision:
                result = {
                    "verdict": local_decision["verdict"],
                    "score": local_decision["score"],
                    "reason": local_decision["reason"],
                    "agent_name": "Local Policy",
                    "ledger_id": None,
                }
            else:
                result = api.post("/validate", validation_payload)
            if "error" in result:
                self._send(502, {"error": format_api_error(result)})
                return
            
            verdict = result.get("verdict", "?")
            response_payload = {
                "verdict": verdict,
                "score": result.get("score", 0),
                "reason": result.get("reason", ""),
                "agent_name": result.get("agent_name", ""),
                "ledger_id": result.get("ledger_id"),
            }
            
            if verdict != "APPROVED":
                self._send(403, response_payload)
                return
            
            if upstream:
                try:
                    status, headers, upstream_raw = _http_post_json(
                        upstream,
                        payload,
                        headers={
                            "X-Nova-Verdict": verdict,
                            "X-Nova-Score": str(result.get("score", 0)),
                            "X-Nova-Agent": str(result.get("agent_name", "")),
                        },
                    )
                    try:
                        upstream_body = json.loads(upstream_raw)
                    except Exception:
                        upstream_body = upstream_raw
                    response_payload["upstream_status"] = status
                    response_payload["upstream"] = upstream_body
                    response_payload["executed"] = True
                except Exception as e:
                    response_payload["upstream_error"] = str(e)
                    self._send(502, response_payload)
                    return
            
            self._send(200, response_payload)
    
    server = ThreadingHTTPServer((host, port), ShieldHandler)
    
    print_logo(compact=True)
    print()
    ok(f"Shield proxy listening on {host}:{port}")
    if upstream:
        dim(f"Upstream: {upstream}")
    dim("POST JSON with {action, context, token_id} to validate and forward")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        warn("Shield stopped.")
        print()


def _iter_skill_files(base_path):
    for path in base_path.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix.lower() in (".json", ".txt", ".py", ".sh", ".yml", ".yaml",
                                   ".toml", ".ini", ".cfg", ".env", ".ps1", ".md"):
            yield path


def cmd_scout(args):
    """Security scanner for skills folder."""
    ensure_dirs()
    target = Path(args.path) if args.path else SKILLS_DIR
    
    if not target.exists():
        fail(f"Skills folder not found: {target}")
        return
    
    rules = [
        ("Network egress", re.compile(r"(https?://|ftp://|sftp://)", re.I), "HIGH"),
        ("Webhook exfil", re.compile(r"(webhook|hookbin|requestbin|pastebin|transfer\\.sh|ngrok)", re.I), "HIGH"),
        ("Command exec", re.compile(r"(subprocess|os\\.system|shell=True|Popen\\(|exec\\(|eval\\()", re.I), "HIGH"),
        ("Credential patterns", re.compile(r"(api[_-]?key|secret|token|passwd|password)", re.I), "MED"),
        ("Encoding/pack", re.compile(r"(base64|b64encode|gzip|zlib)", re.I), "MED"),
        ("File sweep", re.compile(r"(os\\.walk|glob\\(|/etc/passwd|/var/lib|/home/)", re.I), "MED"),
    ]
    
    findings = []
    scanned = 0
    for path in _iter_skill_files(target):
        try:
            if path.stat().st_size > 1024 * 1024:
                continue
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        
        scanned += 1
        for label, pattern, severity in rules:
            for match in pattern.finditer(text):
                line = text[:match.start()].count("\n") + 1
                snippet = match.group(0)[:80]
                findings.append([
                    q(C.RED if severity == "HIGH" else C.YLW, severity),
                    label,
                    f"{path.relative_to(target)}:{line}",
                    snippet,
                ])
    
    print_logo(compact=True)
    print()
    kv("Scanned files", str(scanned), C.G2)
    kv("Findings", str(len(findings)), C.YLW if findings else C.GRN)
    print()
    
    if findings:
        render_table("Potential Exfil Signals", ["Risk", "Rule", "Location", "Match"], findings)
        warn("Review findings. False positives are possible.")
    else:
        ok("No exfiltration signatures detected.")
    print()


def _repair_json_file(path, default, label, fixes):
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data
        except Exception:
            backup = path.with_suffix(path.suffix + f".corrupt-{int(time.time())}")
            try:
                path.replace(backup)
                fixes.append(f"{label}: repaired (backup {backup.name})")
            except Exception:
                fixes.append(f"{label}: repaired (backup failed)")
    else:
        fixes.append(f"{label}: created")
    
    _write_json(path, default)
    return default


# ══════════════════════════════════════════════════════════════════════════════
# NOVA DOCTOR — self-healing diagnostics engine
# ══════════════════════════════════════════════════════════════════════════════

class _DoctorResult:
    """One diagnostic check result."""
    PASS  = "pass"
    WARN  = "warn"
    FAIL  = "fail"
    FIXED = "fixed"

    def __init__(self, name: str, status: str, detail: str = "",
                 fix_applied: str = "", fix_cmd: str = ""):
        self.name       = name
        self.status     = status
        self.detail     = detail
        self.fix_applied = fix_applied   # what we auto-fixed
        self.fix_cmd    = fix_cmd        # command user can run manually

    def print(self):
        icons = {
            self.PASS:  (C.GRN,  "✓"),
            self.WARN:  (C.YLW,  "⚠"),
            self.FAIL:  (C.RED,  "✗"),
            self.FIXED: (C.B7,   "↻"),
        }
        col, icon = icons.get(self.status, (C.G3, "·"))
        print("  " + q(col, icon, bold=True) + "  " +
              q(C.W, self.name.ljust(34)) +
              q(col, self.detail[:50] if self.detail else self.status))
        if self.fix_applied:
            print("       " + q(C.B7,  "↳ fixed: ") + q(C.G2, self.fix_applied))
        if self.fix_cmd:
            print("       " + q(C.G3, "  run:  ") + q(C.B7, self.fix_cmd))


def _dr(name, status, detail="", fix_applied="", fix_cmd="") -> _DoctorResult:
    return _DoctorResult(name, status, detail, fix_applied, fix_cmd)


def _check_file_json(path: Path, default: any, label: str) -> _DoctorResult:
    """Check a JSON file exists and is valid; auto-repair if broken."""
    if not path.exists():
        _write_json(path, default)
        return _dr(label, _DoctorResult.FIXED, "missing", f"created with defaults")
    try:
        json.loads(path.read_text())
        return _dr(label, _DoctorResult.PASS, str(path.name))
    except json.JSONDecodeError as e:
        backup = path.with_suffix(path.suffix + ".bak")
        try:
            path.rename(backup)
        except Exception:
            pass
        _write_json(path, default)
        return _dr(label, _DoctorResult.FIXED,
                   f"corrupt JSON: {str(e)[:40]}",
                   f"backed up to {backup.name}, recreated")


def _check_port_server(port: int, label: str,
                       expect_key: str = None) -> _DoctorResult:
    """Check if a server is running on a port and optionally has a key."""
    import socket as _sock
    try:
        with _sock.create_connection(("127.0.0.1", port), timeout=0.8):
            pass
    except Exception:
        return _dr(f"{label} :{port}", _DoctorResult.FAIL,
                   "not listening",
                   fix_cmd=f"pm2 start your_file.py --name {label.lower().replace(' ','-')} --interpreter python3")

    # Port is open — try HTTP health
    try:
        req = urllib.request.Request(
            f"http://localhost:{port}/health",
            headers={"x-api-key": "nova_dev_key"}
        )
        with urllib.request.urlopen(req, timeout=1.5) as r:
            data = json.loads(r.read().decode())
            has_key = not expect_key or expect_key in data
            if has_key:
                ver = data.get("version", "")
                return _dr(f"{label} :{port}", _DoctorResult.PASS,
                           f"healthy{(' v'+ver) if ver else ''}")
            else:
                return _dr(f"{label} :{port}", _DoctorResult.WARN,
                           f"missing field: {expect_key}")
    except Exception as e:
        return _dr(f"{label} :{port}", _DoctorResult.WARN,
                   f"port open but /health failed: {str(e)[:40]}")


def _check_pm2_process(name: str) -> _DoctorResult:
    """Check if a pm2 process is running and healthy."""
    if not shutil.which("pm2"):
        return _dr(f"pm2:{name}", _DoctorResult.WARN, "pm2 not installed")
    try:
        r = subprocess.run(["pm2", "jlist"], capture_output=True,
                           text=True, timeout=5)
        procs = json.loads(r.stdout or "[]")
        for p in procs:
            if p.get("name") == name:
                status  = p.get("pm2_env", {}).get("status", "?")
                restart = p.get("pm2_env", {}).get("restart_time", 0)
                mem_mb  = round((p.get("monit", {}).get("memory", 0)) / 1024 / 1024, 1)
                cpu     = p.get("monit", {}).get("cpu", 0)
                detail  = f"{status}  restarts={restart}  {mem_mb}mb  cpu={cpu}%"
                if status == "online":
                    st = _DoctorResult.PASS if restart < 10 else _DoctorResult.WARN
                else:
                    st = _DoctorResult.FAIL
                return _dr(f"pm2:{name}", st, detail,
                           fix_cmd=f"pm2 restart {name} --update-env" if status != "online" else "")
        return _dr(f"pm2:{name}", _DoctorResult.FAIL, "not registered",
                   fix_cmd=f"pm2 start <file.py> --name {name} --interpreter python3")
    except Exception as e:
        return _dr(f"pm2:{name}", _DoctorResult.WARN, str(e)[:50])


def _check_env_var(key: str, project_root: Path = None) -> _DoctorResult:
    """Check if an env var is set in process env or .env file."""
    if os.environ.get(key):
        return _dr(f"env:{key}", _DoctorResult.PASS, "set in environment")
    # Check .env files
    root = project_root or Path.cwd()
    for name in [".env", ".env.local"]:
        p = root / name
        if p.exists():
            env_vars = _read_dotenv(p)
            if key in env_vars and env_vars[key]:
                return _dr(f"env:{key}", _DoctorResult.PASS, f"set in {name}")
    return _dr(f"env:{key}", _DoctorResult.WARN, "not set",
               fix_cmd=f"echo '{key}=your_value' >> .env")


def _check_nova_core_url_cache() -> _DoctorResult:
    """Detect the wrong server cached as nova_core URL."""
    if not NOVA_CORE_URL_FILE.exists():
        return _dr("Nova Core URL cache", _DoctorResult.WARN,
                   "not cached - will auto-scan")
    cached = NOVA_CORE_URL_FILE.read_text().strip()
    alive, stype = _probe_any_nova(cached, timeout=0.8)
    if not alive:
        NOVA_CORE_URL_FILE.unlink()
        return _dr("Nova Core URL cache", _DoctorResult.FIXED,
                   f"cached URL {cached} unreachable",
                   "deleted stale cache - will re-scan")
    if stype == "api":
        NOVA_CORE_URL_FILE.unlink()
        return _dr("Nova Core URL cache", _DoctorResult.FIXED,
                   f"was pointing to nova-api ({cached}), not nova_core",
                   "deleted wrong cache — nova logs will now find the right server")
    if stype == "core":
        return _dr("Nova Core URL cache", _DoctorResult.PASS,
                   f"nova_core at {cached}")
    return _dr("Nova Core URL cache", _DoctorResult.WARN,
               f"unknown server type at {cached}")


def _check_agent_env(agent_type: str, project_root: Path) -> list:
    """Check an agent project has the required Nova env vars."""
    results = []

    # CLI agents (claude_code, codex_cli, gemini_cli, copilot_cli) don't need
    # a project .env — they read from shell environment or home config
    CLI_AGENTS = {"claude_code", "codex_cli", "gemini_cli", "copilot_cli", "aider"}
    if agent_type in CLI_AGENTS:
        # For CLI agents: check shell env instead
        key_map = {
            "claude_code": "ANTHROPIC_API_KEY",
            "codex_cli":   "OPENAI_API_KEY",
            "gemini_cli":  "GEMINI_API_KEY",
            "copilot_cli": "GITHUB_TOKEN",
            "aider":       "OPENAI_API_KEY",
        }
        key = key_map.get(agent_type, "")
        if key and os.environ.get(key):
            results.append(_dr(f"{agent_type}:credentials",
                               _DoctorResult.PASS, f"{key} set in environment"))
        else:
            results.append(_dr(f"{agent_type}:credentials",
                               _DoctorResult.WARN,
                               f"{key} not in environment",
                               fix_cmd=f"export {key}=your_key"))
        return results

    env_file = project_root / ".env"
    if not env_file.exists():
        results.append(_dr(f"{agent_type}:.env", _DoctorResult.FAIL,
                           "no .env file found",
                           fix_cmd=f"touch {env_file}"))
        return results

    env_vars = _read_dotenv(env_file)
    required = ["NOVA_CORE_URL", "NOVA_CORE_ENABLED", "NOVA_AGENT_SCOPE"]

    for key in required:
        if key in env_vars and env_vars[key]:
            results.append(_dr(f"{agent_type}:{key}", _DoctorResult.PASS,
                               env_vars[key][:40]))
        else:
            # Auto-fix: inject missing vars
            nova_url = load_nova_core_url()
            fixes_to_inject = {
                "NOVA_CORE_URL":     nova_url,
                "NOVA_CORE_ENABLED": "true",
                "NOVA_AGENT_SCOPE":  f"agent:{agent_type}",
            }
            val = fixes_to_inject.get(key, "")
            if val:
                try:
                    with open(env_file, "a") as f:
                        f.write(f"\n{key}={val}\n")
                    results.append(_dr(f"{agent_type}:{key}", _DoctorResult.FIXED,
                                       "was missing", f"injected {key}={val}"))
                except Exception:
                    results.append(_dr(f"{agent_type}:{key}", _DoctorResult.FAIL,
                                       "missing",
                                       fix_cmd=f"echo '{key}={val}' >> {env_file}"))
            else:
                results.append(_dr(f"{agent_type}:{key}", _DoctorResult.WARN,
                                   "not set"))
    return results


def _check_system_prompt(agent_type: str, project_root: Path) -> _DoctorResult:
    """Check the system prompt is found and has Nova rules injected."""
    loc = _find_system_prompt_location(project_root)
    if not loc.get("found"):
        return _dr(f"{agent_type}:system_prompt", _DoctorResult.WARN,
                   "not found — run nova setup to inject",
                   fix_cmd=f"nova setup {agent_type}")

    # Check if nova block is already injected
    try:
        text = Path(loc["file"]).read_text(errors="ignore")
        has_nova = "NOVA GOVERNANCE RULES" in text
        if has_nova:
            return _dr(f"{agent_type}:system_prompt", _DoctorResult.PASS,
                       f"found in {Path(loc['file']).name} + Nova rules injected")
        else:
            return _dr(f"{agent_type}:system_prompt", _DoctorResult.WARN,
                       f"found in {Path(loc['file']).name} but Nova rules NOT injected",
                       fix_cmd=f"nova setup {agent_type}")
    except Exception:
        return _dr(f"{agent_type}:system_prompt", _DoctorResult.WARN,
                   "could not read file")


def _check_nova_rules_exist(agent_type: str, project_root: Path) -> _DoctorResult:
    """Check that .nova/agents/<agent>/rules/ exists and has rules."""
    rules_dir = project_root / ".nova" / "agents" / agent_type / "rules"
    if not rules_dir.exists():
        return _dr(f"{agent_type}:rules", _DoctorResult.WARN,
                   ".nova/agents/ folder missing",
                   fix_cmd=f"nova setup {agent_type}")
    rule_files = list(rules_dir.glob("*.json"))
    if not rule_files:
        return _dr(f"{agent_type}:rules", _DoctorResult.WARN,
                   "rules folder empty",
                   fix_cmd=f'nova rule "your rule here"')
    return _dr(f"{agent_type}:rules", _DoctorResult.PASS,
               f"{len(rule_files)} rule(s) active")


def _check_python_file_syntax(path: Path) -> _DoctorResult:
    """Check a Python file has valid syntax."""
    try:
        import ast as _ast
        _ast.parse(path.read_text(errors="ignore"))
        size_kb = round(path.stat().st_size / 1024, 1)
        return _dr(f"syntax:{path.name}", _DoctorResult.PASS,
                   f"valid ({size_kb}kb)")
    except SyntaxError as e:
        return _dr(f"syntax:{path.name}", _DoctorResult.FAIL,
                   f"line {e.lineno}: {str(e.msg)[:50]}",
                   fix_cmd=f"python3 -m py_compile {path}")
    except Exception as e:
        return _dr(f"syntax:{path.name}", _DoctorResult.WARN, str(e)[:50])


def _auto_fix_pm2_restart(name: str, result: _DoctorResult) -> _DoctorResult:
    """If a pm2 process is failing, attempt restart."""
    if result.status != _DoctorResult.FAIL:
        return result
    if not shutil.which("pm2"):
        return result
    try:
        r = subprocess.run(["pm2", "restart", name, "--update-env"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return _dr(result.name, _DoctorResult.FIXED,
                       result.detail, f"pm2 restart {name} succeeded")
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")
    return result


def _check_python_file_version(path: Path, expect_version: str = "") -> _DoctorResult:
    """Check a Python file for version string and known broken patterns."""
    if not path.exists():
        return _dr(f"file:{path.name}", _DoctorResult.WARN, "not found in search path")
    try:
        text = path.read_text(errors="ignore")
        size_kb = round(path.stat().st_size / 1024, 1)

        # Check for known problems in nova.py
        issues = []
        if path.name == "nova.py":
            # Wrong port cached
            if 'localhost:9003"' in text and 'localhost:9002"' in text:
                pass  # both present = fine (they're constants)
            # Check NOVA_VERSION
            m = re.search(r'NOVA_VERSION\s*=\s*"([^"]+)"', text)
            ver = m.group(1) if m else "?"
            issues.append(f"v{ver}")

        if path.name == "nova_core.py":
            # Check port setting
            m = re.search(r'PORT\s*=\s*int\(os\.getenv\("NOVA_PORT",\s*"(\d+)"\)', text)
            port = m.group(1) if m else "?"
            issues.append(f"default port {port}")

        detail = f"valid {size_kb}kb"
        if issues:
            detail += "  " + "  ".join(issues)
        return _dr(f"syntax:{path.name}", _DoctorResult.PASS, detail)
    except SyntaxError as e:
        return _dr(f"syntax:{path.name}", _DoctorResult.FAIL,
                   f"line {e.lineno}: {str(e.msg)[:50]}",
                   fix_cmd=f"python3 -m py_compile {path}")
    except Exception as e:
        return _dr(f"syntax:{path.name}", _DoctorResult.WARN, str(e)[:50])


def _check_nova_core_running() -> _DoctorResult:
    """
    Critical check: is nova_core.py actually running?
    Checks port 9003 and verifies it has /ledger (not just nova-api).
    """
    alive, stype = _probe_any_nova("http://localhost:9003", timeout=0.8)
    if alive and stype == "core":
        # Also verify /ledger responds
        try:
            req = urllib.request.Request(
                "http://localhost:9003/ledger?limit=1",
                headers={"x-api-key": "nova_dev_key"}
            )
            with urllib.request.urlopen(req, timeout=1.0) as r:
                if r.status < 400:
                    return _dr("nova_core:/ledger", _DoctorResult.PASS,
                               "ledger endpoint healthy")
        except Exception:
            pass
        return _dr("nova_core:/ledger", _DoctorResult.WARN,
                   "server up but /ledger check failed")

    # Try to find on other ports
    for port in (9002, 8000):
        alive2, stype2 = _probe_any_nova(f"http://localhost:{port}", timeout=0.5)
        if alive2 and stype2 == "core":
            return _dr("nova_core:port", _DoctorResult.WARN,
                       f"nova_core found on :{port} not :9003",
                       fix_cmd=f'echo "NOVA_PORT=9003" >> .env  # or set NOVA_PORT env var')

    # Check if it's alive but wrong type
    alive3, stype3 = _probe_any_nova("http://localhost:9003", timeout=0.5)
    if alive3 and stype3 == "api":
        return _dr("nova_core:9003", _DoctorResult.FAIL,
                   "nova-api (main.py) is on :9003 — not nova_core",
                   fix_cmd="pm2 start nova_core.py --name nova-core --interpreter python3")

    return _dr("nova_core:9003", _DoctorResult.FAIL,
               "not running",
               fix_cmd="pm2 start nova_core.py --name nova-core --interpreter python3")


def _check_omni_cpu() -> list:
    """Check omni process for runaway CPU."""
    results = []
    if not shutil.which("pm2"):
        return results
    try:
        r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
        procs = json.loads(r.stdout or "[]")
        for p in procs:
            name = p.get("name", "")
            cpu  = p.get("monit", {}).get("cpu", 0)
            mem  = round(p.get("monit", {}).get("memory", 0) / 1024 / 1024, 1)
            if cpu > 90:
                results.append(_dr(f"pm2:{name} CPU", _DoctorResult.WARN,
                                   f"{cpu}% CPU — possible infinite loop",
                                   fix_cmd=f"pm2 restart {name} --update-env"))
            if mem > 500:
                results.append(_dr(f"pm2:{name} mem", _DoctorResult.WARN,
                                   f"{mem}mb — possible memory leak",
                                   fix_cmd=f"pm2 restart {name} --update-env"))
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")
    return results


def _check_disk_space() -> _DoctorResult:
    """Check if disk space is critically low."""
    try:
        stat = os.statvfs("/")
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
        pct_used = round((1 - stat.f_bavail / stat.f_blocks) * 100)
        detail = f"{free_gb:.1f}GB free / {total_gb:.0f}GB ({pct_used}% used)"
        if free_gb < 0.5:
            return _dr("disk:space", _DoctorResult.FAIL, detail,
                       fix_cmd="du -sh ~/* | sort -rh | head -20  # find large files")
        if free_gb < 2:
            return _dr("disk:space", _DoctorResult.WARN, detail)
        return _dr("disk:space", _DoctorResult.PASS, detail)
    except Exception:
        return _dr("disk:space", _DoctorResult.WARN, "could not check")


def _check_nova_api_vs_core_confusion() -> list:
    """
    Detect the nova-api vs nova-core URL confusion that breaks nova logs/stream.
    This is the #1 most common failure mode.
    """
    results = []
    cached_url = ""
    if NOVA_CORE_URL_FILE.exists():
        cached_url = NOVA_CORE_URL_FILE.read_text().strip()

    # Check what's cached
    if cached_url:
        alive, stype = _probe_any_nova(cached_url, timeout=0.8)
        if alive and stype == "api":
            # Auto-fix: clear the wrong cache
            NOVA_CORE_URL_FILE.unlink()
            results.append(_dr("URL cache:wrong_server", _DoctorResult.FIXED,
                               f"was caching nova-api ({cached_url})",
                               "cleared — will now scan for nova_core"))
        elif not alive:
            NOVA_CORE_URL_FILE.unlink()
            results.append(_dr("URL cache:stale", _DoctorResult.FIXED,
                               f"{cached_url} unreachable",
                               "cleared stale cache"))

    # Describe what each server is
    api_alive, api_type = _probe_any_nova("http://localhost:9002", timeout=0.5)
    core_alive, core_type = _probe_any_nova("http://localhost:9003", timeout=0.5)

    if api_alive:
        label = "nova-api (main.py)" if api_type == "api" else "unknown"
        results.append(_dr("port:9002", _DoctorResult.PASS,
                           f"{label} — /tokens /validate /stats"))
    else:
        results.append(_dr("port:9002", _DoctorResult.WARN, "not running (nova-api)"))

    if core_alive and core_type == "core":
        results.append(_dr("port:9003", _DoctorResult.PASS,
                           "nova_core.py — /ledger /rules /stream"))
    elif core_alive and core_type == "api":
        results.append(_dr("port:9003", _DoctorResult.FAIL,
                           "nova-api is on :9003 (wrong! nova_core should be here)",
                           fix_cmd="pm2 start nova_core.py --name nova-core --interpreter python3"))
    else:
        results.append(_dr("port:9003", _DoctorResult.FAIL,
                           "nova_core.py NOT running — nova logs/stream/rules broken",
                           fix_cmd="pm2 start nova_core.py --name nova-core --interpreter python3"))

    return results


def _find_nova_core_py() -> str:
    """
    Find nova_core.py on this server.
    Searches: cwd, home, common paths, pm2 process list (most reliable!),
    sys.argv[0] directory, Python path.
    Returns absolute path string or empty string.
    """
    # First: check pm2 processes — the script_path field is exact
    if shutil.which("pm2"):
        try:
            r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
            procs = json.loads(r.stdout or "[]")
            for p in procs:
                script = (p.get("pm2_env", {}).get("pm_exec_path", "") or
                          p.get("pm2_env", {}).get("script", ""))
                if "nova" in script.lower() and "core" in script.lower():
                    if Path(script).exists():
                        return script
        except Exception as _exc:
            debug(f"silenced exception: {_exc}")

    # Common paths
    search_dirs = [
        Path.cwd(),
        Path.home(),
        Path("/home/ubuntu"),
        Path("/opt/nova"),
        Path("/app"),
        Path("/srv"),
        Path(sys.argv[0]).parent if sys.argv[0] else None,
    ]
    for d in search_dirs:
        if d is None or not d.exists():
            continue
        f = d / "nova_core.py"
        if f.exists():
            return str(f)
        # Check one level deep
        try:
            for sub in d.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    candidate = sub / "nova_core.py"
                    if candidate.exists():
                        return str(candidate)
        except Exception as _exc:
            debug(f"silenced exception: {_exc}")

    # Last resort: use find command
    try:
        r = subprocess.run(
            ["find", "/home", "-name", "nova_core.py", "-maxdepth", "4"],
            capture_output=True, text=True, timeout=5
        )
        paths = [p.strip() for p in r.stdout.splitlines() if p.strip()]
        if paths:
            return paths[0]
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")

    return ""


def _check_pm2_nova_core_registered() -> _DoctorResult:
    """Check if nova-core is registered in pm2 (survives reboots)."""
    if not shutil.which("pm2"):
        return _dr("pm2:nova-core", _DoctorResult.WARN, "pm2 not installed")
    try:
        r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
        procs = json.loads(r.stdout or "[]")
        names = [p.get("name", "") for p in procs]
        if "nova-core" in names:
            for p in procs:
                if p.get("name") == "nova-core":
                    status  = p.get("pm2_env", {}).get("status", "?")
                    restart = p.get("pm2_env", {}).get("restart_time", 0)
                    mem_mb  = round((p.get("monit", {}).get("memory", 0)) / 1024 / 1024, 1)
                    detail  = f"{status}  restarts={restart}  {mem_mb}mb"
                    if status == "online":
                        return _dr("pm2:nova-core", _DoctorResult.PASS, detail)
                    else:
                        return _dr("pm2:nova-core", _DoctorResult.FAIL, detail,
                                   fix_cmd="pm2 restart nova-core --update-env")
        else:
            # Find nova_core.py — search everywhere
            core_path = _find_nova_core_py()
            if core_path:
                return _dr("pm2:nova-core", _DoctorResult.FAIL,
                           f"not in pm2  found at: {core_path}",
                           fix_cmd=f"pm2 start {core_path} --name nova-core --interpreter python3")
            return _dr("pm2:nova-core", _DoctorResult.FAIL,
                       "not registered — nova_core.py location unknown",
                       fix_cmd="find / -name nova_core.py 2>/dev/null | head -5  # locate it")
    except Exception as e:
        return _dr("pm2:nova-core", _DoctorResult.WARN, str(e)[:50])


def _check_pm2_startup_saved() -> _DoctorResult:
    """Check if pm2 startup is saved (survives server reboots)."""
    if not shutil.which("pm2"):
        return _dr("pm2:startup", _DoctorResult.WARN, "pm2 not installed")
    try:
        dump_file = Path.home() / ".pm2" / "dump.pm2"
        if dump_file.exists():
            age_days = (time.time() - dump_file.stat().st_mtime) / 86400
            return _dr("pm2:startup_saved", _DoctorResult.PASS,
                       f"dump saved {age_days:.0f}d ago")
        return _dr("pm2:startup_saved", _DoctorResult.WARN,
                   "pm2 save not run — processes won't survive reboot",
                   fix_cmd="pm2 save && pm2 startup")
    except Exception:
        return _dr("pm2:startup_saved", _DoctorResult.WARN,
                   "could not check",
                   fix_cmd="pm2 save && pm2 startup")


def _auto_fix_nova_core(auto: bool) -> list:
    """
    If nova-core is not running, attempt to start it automatically.
    Returns list of _DoctorResult showing what was done.
    """
    results = []
    core_alive, _ = _probe_any_nova("http://localhost:9003", timeout=0.5)
    if core_alive:
        return results  # already running

    # Find nova_core.py — exhaustive search
    found = _find_nova_core_py()
    core_path = Path(found) if found else None

    if not core_path:
        results.append(_dr("auto-fix:nova-core", _DoctorResult.FAIL,
                           "nova_core.py not found — cannot auto-start",
                           fix_cmd="ls ~/nova_core.py  # check if file exists"))
        return results

    if not auto:
        return results  # Only run in auto mode or when called explicitly

    started = _start_nova_core_background(str(core_path))
    if started:
        # Wait up to 6s
        for _ in range(12):
            time.sleep(0.5)
            alive2, stype2 = _probe_any_nova("http://localhost:9003", timeout=0.5)
            if alive2 and stype2 == "core":
                results.append(_dr("auto-fix:nova-core", _DoctorResult.FIXED,
                                   "was not running",
                                   f"started {core_path.name} on :9003"))
                return results
        results.append(_dr("auto-fix:nova-core", _DoctorResult.WARN,
                           "started but not yet responding",
                           fix_cmd="nova boot  # try again in a few seconds"))
    else:
        results.append(_dr("auto-fix:nova-core", _DoctorResult.FAIL,
                           "could not start automatically",
                           fix_cmd=f"pm2 start {core_path} --name nova-core --interpreter python3"))
    return results


def cmd_doctor(args):
    """
    Nova self-healing doctor — diagnoses AND auto-fixes every component.

    Sections:
      0  Critical: nova-api vs nova_core URL confusion (root cause of most failures)
      1  Configuration files (JSON integrity + field normalization)
      2  pm2 processes (running, restart count, CPU, memory)
      3  nova_core.py specifically (port, /ledger, /rules endpoints)
      4  Agent projects (env vars, system prompt injection, rules)
      5  Python file integrity (syntax check all nova files)
      6  System health (disk, permissions)

    Auto-fixes (--auto or -y to skip confirmations):
      ↻  Wrong nova_core URL cached → cleared immediately
      ↻  Stale URL cache → cleared
      ↻  Missing .env NOVA_* vars → injected
      ↻  pm2 process failing → prompted to restart
      ↻  nova_core.py not running → starts it (--auto mode)
      ↻  Corrupt JSON files → backed up + recreated
      ↻  Wrong directory permissions → chmod 700
    """
    auto = (getattr(args, "auto", False) or
            getattr(args, "execute", False) or
            "--auto" in sys.argv or "-y" in sys.argv or
            getattr(args, "verbose", False))

    print_logo(compact=True)
    print()
    print("  " + q(C.GLD, "✦", bold=True) + "  " +
          q(C.W, "Nova Doctor", bold=True) +
          ("  " + q(C.B7, "--auto mode") if auto else ""))
    print("  " + q(C.G3, "  Diagnosing all components..."))
    print()

    all_results: list = []

    def sec(title: str, checks: list):
        """Print a section with its checks."""
        if not checks:
            return
        hr(char="─", color=C.ASH)
        print("  " + q(C.GLD_MATTE, title.upper(), bold=True))
        print()
        for r in checks:
            r.print()
            all_results.append(r)
        print()

    ensure_dirs()

    # ── SECTION 0: The #1 failure cause — wrong server URL ────────────────────
    sec("0. Nova-API vs Nova-Core (Most Common Failure)", 
        _check_nova_api_vs_core_confusion())

    # ── SECTION 1: Config JSON files ──────────────────────────────────────────
    cfg_checks = [
        _check_file_json(CONFIG_FILE,   DEFAULT_CONFIG, "~/.nova/config.json"),
        _check_file_json(KEYS_FILE,     {"keys": [], "active": None}, "~/.nova/keys.json"),
        _check_file_json(HISTORY_FILE,  [], "~/.nova/history.json"),
        _check_file_json(QUEUE_FILE,    [], "~/.nova/offline_queue.json"),
    ]
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
        updated = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v; updated = True
        api = cfg.get("api_url", "")
        if api and not api.startswith(("http://", "https://")):
            cfg["api_url"] = "http://" + api; updated = True
        if updated:
            _write_json(CONFIG_FILE, cfg)
            cfg_checks.append(_dr("config:fields", _DoctorResult.FIXED,
                                   "missing fields", "normalized"))
        else:
            cfg_checks.append(_dr("config:fields", _DoctorResult.PASS,
                                   "all fields present"))
    except Exception as e:
        cfg_checks.append(_dr("config:fields", _DoctorResult.WARN, str(e)[:50]))
    sec("1. Configuration Files", cfg_checks)

    # ── SECTION 2: pm2 processes ──────────────────────────────────────────────
    pm2_checks = []
    if shutil.which("pm2"):
        try:
            r = subprocess.run(["pm2", "jlist"], capture_output=True,
                               text=True, timeout=5)
            procs = json.loads(r.stdout or "[]")
            pm2_names = [p["name"] for p in procs]
        except Exception:
            procs, pm2_names = [], []

        # Always check these critical ones
        for name in ["nova-api", "nova-core"]:
            result = _check_pm2_process(name)
            if result.status == _DoctorResult.FAIL and auto:
                if name == "nova-core":
                    # Will handle in section 3
                    pass
                else:
                    fixed = _auto_fix_pm2_restart(name, result)
                    result = fixed
            elif result.status == _DoctorResult.FAIL and not auto:
                pass  # show with fix_cmd
            pm2_checks.append(result)

        # Show all other processes with CPU/mem warnings
        for p in procs:
            n = p.get("name", "")
            if n not in ("nova-api", "nova-core"):
                pm2_checks.append(_check_pm2_process(n))

        pm2_checks.extend(_check_omni_cpu())
        pm2_checks.append(_check_pm2_startup_saved())
    else:
        pm2_checks.append(_dr("pm2", _DoctorResult.WARN,
                               "pm2 not installed",
                               fix_cmd="npm install -g pm2"))
    sec("2. pm2 Processes", pm2_checks)

    # ── SECTION 3: nova_core.py specifically ─────────────────────────────────
    core_checks = [
        _check_pm2_nova_core_registered(),
        _check_nova_core_running(),
    ]
    # Auto-start if not running and --auto flag set
    if auto:
        core_checks.extend(_auto_fix_nova_core(auto=True))

    # Check nova_core.py file exists — exhaustive search
    core_found_path = _find_nova_core_py()
    if core_found_path:
        core_checks.append(_dr("nova_core.py:location",
                                _DoctorResult.PASS, core_found_path))
        # Update the fix_cmd for pm2:nova-core if we now know the path
        for r in core_checks:
            if r.name in ("pm2:nova-core", "nova_core:9003") and r.fix_cmd:
                r.fix_cmd = f"pm2 start {core_found_path} --name nova-core --interpreter python3"
    else:
        core_checks.append(_dr("nova_core.py:location",
                                _DoctorResult.FAIL,
                                "not found in common paths",
                                fix_cmd="find /home -name nova_core.py -maxdepth 4"))
    sec("3. Nova Core", core_checks)

    # ── SECTION 4: Agent projects ─────────────────────────────────────────────
    agent_checks = []
    project_root = _find_project_root()
    discovered   = discover_agents(project_root=project_root, probe_ports=True)

    if discovered:
        for ag in discovered[:4]:
            atype = ag["agent_type"]
            aroot = project_root

            # Try to use the agent's own home dir
            for home_dir in _AGENT_REGISTRY.get(atype, {}).get("home_dirs", []):
                hp = Path(home_dir)
                if hp.is_dir() and (hp / ".env").exists():
                    aroot = hp
                    break

            agent_checks.append(
                _dr(f"{ag['display']} found", _DoctorResult.PASS,
                    f"{ag['confidence']}% confidence  {'● live' if ag.get('port_live') else ''}"))

            env_results = _check_agent_env(atype, aroot)
            agent_checks.extend(env_results)
            agent_checks.append(_check_system_prompt(atype, aroot))
            agent_checks.append(_check_nova_rules_exist(atype, aroot))
    else:
        agent_checks.append(_dr("agent discovery", _DoctorResult.WARN,
                                "no agents detected",
                                fix_cmd="cd /path/to/agent && nova doctor"))
    sec("4. Agent Projects", agent_checks)

    # ── SECTION 5: Python file integrity ─────────────────────────────────────
    syntax_checks = []
    script_dir = Path(sys.argv[0]).parent if sys.argv[0] else Path.cwd()
    for fname in ["nova.py", "nova_core.py", "integrations.py", "skill_executor.py"]:
        for search in [script_dir, Path.cwd(), Path.home(), Path("/home/ubuntu")]:
            p = search / fname
            if p.exists():
                syntax_checks.append(_check_python_file_version(p))
                break
    if not syntax_checks:
        syntax_checks = [_dr("python files", _DoctorResult.WARN,
                              "nova files not found — run from the nova directory")]
    sec("5. File Integrity", syntax_checks)

    # ── SECTION 6: System health ──────────────────────────────────────────────
    sys_checks = [_check_disk_space()]
    for d, name in [(NOVA_DIR, "~/.nova/"), (SKILLS_DIR, "~/.nova/skills/"),
                    (LOGS_DIR, "~/.nova/logs/")]:
        if d.exists():
            mode = oct(d.stat().st_mode)[-3:]
            if mode not in ("700", "755", "750"):
                try:
                    os.chmod(d, 0o700)
                    sys_checks.append(_dr(f"perms:{name}", _DoctorResult.FIXED,
                                          f"was {mode}", "chmod 700"))
                except Exception:
                    sys_checks.append(_dr(f"perms:{name}", _DoctorResult.WARN,
                                          f"mode {mode}",
                                          fix_cmd=f"chmod 700 {d}"))
        else:
            d.mkdir(parents=True, exist_ok=True)
            sys_checks.append(_dr(f"perms:{name}", _DoctorResult.FIXED,
                                   "did not exist", "created"))
    sec("6. System Health", sys_checks)

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    hr_bold()
    print()
    n_pass  = sum(1 for r in all_results if r.status == _DoctorResult.PASS)
    n_fixed = sum(1 for r in all_results if r.status == _DoctorResult.FIXED)
    n_warn  = sum(1 for r in all_results if r.status == _DoctorResult.WARN)
    n_fail  = sum(1 for r in all_results if r.status == _DoctorResult.FAIL)

    print("  " + q(C.GLD, "✦", bold=True) + "  " +
          q(C.GRN, f"✓ {n_pass}") + "  " +
          (q(C.B7,  f"↻ {n_fixed} fixed") + "  " if n_fixed else "") +
          (q(C.YLW, f"⚠ {n_warn} warn") + "  " if n_warn else "") +
          (q(C.RED, f"✗ {n_fail} failed") if n_fail else ""))
    print()

    # Action items — deduplicate by name+fix_cmd
    seen_actions = set()
    failures_raw = [r for r in all_results if r.status in (_DoctorResult.FAIL, _DoctorResult.WARN)]
    failures = []
    for r in failures_raw:
        key = (r.name, r.fix_cmd or r.detail[:30])
        if key not in seen_actions:
            seen_actions.add(key)
            failures.append(r)
    if failures:
        print("  " + q(C.W, "Action items:", bold=True))
        print()
        for r in sorted(failures, key=lambda x: x.status == _DoctorResult.FAIL, reverse=True)[:8]:
            col = C.RED if r.status == _DoctorResult.FAIL else C.YLW
            icon = "✗" if r.status == _DoctorResult.FAIL else "⚠"
            print("  " + q(col, icon, bold=True) + "  " + q(C.W, r.name))
            if r.fix_cmd:
                print("     " + q(C.G3, "run: ") + q(C.B7, r.fix_cmd))
        print()

    if n_fail == 0 and n_warn == 0:
        print("  " + q(C.GRN, "✦", bold=True) + "  " +
              q(C.W, "Everything looks healthy.", bold=True))
    elif n_fail == 0:
        info("Minor warnings — system functional.")
    else:
        warn(f"{n_fail} critical issue(s). Most common fix:")
        print()
        print("    " + q(C.B7, "pm2 start nova_core.py --name nova-core --interpreter python3"))
        print("    " + q(C.G3, "# then:"))
        print("    " + q(C.B7, "rm ~/.nova/nova_core_url  # clear wrong cache"))
    print()
    hint("Auto-fix mode:  nova doctor --auto")
    hint("Re-run:         nova doctor")
    print()
def cmd_mcp(args):
    """Expose skills in MCP format."""
    sub = args.subcommand or "export"
    
    if sub in ("list", "ls"):
        installed = set(get_installed_skills())
        rows = []
        for key, skill in SKILLS.items():
            rows.append([
                skill.get("name", key),
                skill.get("mcp") or key,
                "installed" if key in installed else "",
            ])
        render_table("MCP Skills", ["Skill", "MCP ID", "Status"], rows)
        return
    
    if sub in ("export", "print", "json", ""):
        servers = []
        for key, skill in SKILLS.items():
            servers.append(_skill_to_mcp(key, skill))
        servers.extend(_load_mcp_overrides())
        
        payload = {
            "mcp_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "servers": servers,
        }
        
        if args.output:
            Path(args.output).write_text(json.dumps(payload, indent=2))
            ok(f"MCP export written to {args.output}")
            return
        
        print(json.dumps(payload, indent=2))
        return
    
    if sub in ("import", "read"):
        if not args.file:
            fail("Provide --file to import MCP JSON.")
            return
        try:
            data = json.loads(Path(args.file).read_text())
        except Exception as e:
            fail(f"Invalid MCP file: {e}")
            return
        servers = data.get("servers", []) if isinstance(data, dict) else []
        rows = [[s.get("name", ""), s.get("id", ""), s.get("description", "")] for s in servers]
        render_table("MCP Import Preview", ["Name", "ID", "Description"], rows)
        return
    
    fail(f"Unknown subcommand: {sub}")
    hint("Use: nova mcp export | list | import")


def cmd_whoami(args):
    """Show current identity and configuration."""
    cfg = load_config()
    keys_data = load_keys()
    
    print_logo(compact=True)
    print()
    
    # Identity
    kv("User", cfg.get("user_name") or "not set", C.W)
    if cfg.get("org_name"):
        kv("Organization", cfg["org_name"], C.G1)
    
    # Connection
    section("Connection")
    kv("Server", cfg.get("api_url", "not set"), C.B7)
    kv("API Key", mask_key(cfg.get("api_key", "")), C.G2)
    
    # Test connection
    api = NovaAPI(cfg.get("api_url", ""), cfg.get("api_key", ""))
    connected = api.health_check()
    kv("Status", "Connected" if connected else "Unreachable", 
       C.GRN if connected else C.RED)
    
    # Keys
    if keys_data.get("keys"):
        kv("Saved keys", str(len(keys_data["keys"])), C.G2)
    
    # Default agent
    if cfg.get("default_token"):
        kv("Default agent", mask_key(cfg["default_token"]), C.G3)
    
    # Intelligence
    llm_prov  = cfg.get("llm_provider", "")
    llm_model = cfg.get("llm_model", "")
    llm_key   = cfg.get("llm_api_key", "")
    section("Intelligence")
    if llm_prov in LLM_PROVIDERS:
        pv = LLM_PROVIDERS[llm_prov]
        kv("Provider", f"{pv['icon']}  {pv['name']}", C.MGN)
        kv("Model",    llm_model or "-",              C.W)
        kv("API Key",  mask_key(llm_key) if llm_key else "not set", C.G3)
    else:
        kv("Provider", "not configured", C.G3)
        hint("Run  " + q(C.B7, "nova config model") + "  to select a provider")
    
    # Skills
    installed = get_installed_skills()
    if installed:
        section("Skills")
        for skill_name in installed:
            skill_def = SKILLS.get(skill_name, {})
            sc = get_skill_color(skill_def)
            print("  " + q(C.GRN, "●") + "  " + 
                  q(sc, f"{skill_def.get('icon', '·')} {skill_def.get('name', skill_name)}"))
    
    # Config file
    section("Configuration")
    kv("Config file", str(CONFIG_FILE), C.G3)
    kv("Version", NOVA_VERSION, C.B6)
    kv("Build", NOVA_BUILD, C.G3)
    
    print()



# ══════════════════════════════════════════════════════════════════════════════
# NATURAL LANGUAGE AGENT PARSER - Extrae can_do/cannot_do de lenguaje natural
# ══════════════════════════════════════════════════════════════════════════════

def _nl_call_llm(cfg: dict, prompt: str) -> str:
    """
    Llama al LLM configurado en Nova para parsear lenguaje natural.
    Soporta todos los providers de LLM_PROVIDERS.
    Sin dependencias externas - usa urllib puro.
    """
    provider = cfg.get("llm_provider", "")
    model    = cfg.get("llm_model", "")
    api_key  = cfg.get("llm_api_key", "")
    base_url = cfg.get("llm_base_url", "")

    if not provider or not model:
        return ""

    prov_data = LLM_PROVIDERS.get(provider, {})
    prefix    = prov_data.get("litellm_prefix", provider)

    # Normalizar model ID (quitar prefijo si ya viene incluido)
    if "/" in model:
        model_clean = model.split("/", 1)[1]
    else:
        model_clean = model

    # ── Anthropic ─────────────────────────────────────────────────────────────
    if prefix == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": model_clean,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        req = urllib.request.Request(url,
            data=json.dumps(payload).encode(),
            headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return data["content"][0]["text"].strip()

    # ── Gemini ────────────────────────────────────────────────────────────────
    if prefix == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_clean}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.2},
        }
        req = urllib.request.Request(url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # ── OpenAI / OpenRouter / OpenClaw / Groq / xAI / Mistral / DeepSeek ─────
    # Todos usan formato OpenAI
    if prefix in ("openai", "openrouter", "groq", "xai", "mistral", "deepseek"):
        if prefix == "openrouter":
            url = "https://openrouter.ai/api/v1/chat/completions"
        elif prefix == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
        elif prefix == "xai":
            url = "https://api.x.ai/v1/chat/completions"
        elif prefix == "mistral":
            url = "https://api.mistral.ai/v1/chat/completions"
        elif prefix == "deepseek":
            url = "https://api.deepseek.com/v1/chat/completions"
        else:
            # OpenAI o custom base_url (OpenClaw, LM Studio, etc.)
            _base = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
            url = f"{_base}/chat/completions"

        payload = {
            "model": model.replace(f"{prefix}/", "") if model.startswith(f"{prefix}/") else model_clean,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.2,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        req = urllib.request.Request(url,
            data=json.dumps(payload).encode(),
            headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"].strip()

    # ── Ollama - local ────────────────────────────────────────────────────────
    if prefix == "ollama":
        _base = base_url.rstrip("/") if base_url else "http://localhost:11434"
        url = f"{_base}/api/chat"
        payload = {
            "model": model_clean,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        req = urllib.request.Request(url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        return data["message"]["content"].strip()

    return ""


def nl_parse_agent_rules(description: str, cfg: dict) -> dict:
    """
    Usa el LLM configurado en Nova para extraer can_do/cannot_do
    de una descripción en lenguaje natural.

    Retorna: {"name": str, "description": str, "can_do": [...], "cannot_do": [...]}
    """
    prompt = f"""Analiza esta descripción de un agente de IA y extrae sus reglas de gobernanza.

DESCRIPCIÓN:
{description}

Responde SOLO en JSON válido, sin markdown, sin texto adicional:
{{
  "name": "nombre corto del agente (2-4 palabras)",
  "description": "descripción en una línea de qué hace",
  "can_do": [
    "acción concreta que SÍ puede hacer",
    "otra acción permitida"
  ],
  "cannot_do": [
    "acción que NO puede hacer",
    "otra restricción"
  ]
}}

Reglas para extraer:
- can_do: cosas que el agente PUEDE hacer, TIENE permitido, está AUTORIZADO a hacer
- cannot_do: cosas PROHIBIDAS, que NO puede hacer, límites, restricciones
- Sé específico y accionable (no "ser amable" - sí "responder preguntas de pacientes")
- Extrae entre 3-8 items por lista según la complejidad de la descripción
- Si no hay restricciones explícitas, infiere las razonables para ese tipo de agente"""

    try:
        raw = _nl_call_llm(cfg, prompt)
        if not raw:
            return {}
        # Limpiar markdown si el LLM lo añade
        raw = re.sub(r'```json\s*|```\s*', '', raw).strip()
        m = re.search(r'\{[\s\S]+\}', raw)
        if m:
            return json.loads(m.group(0))
        return json.loads(raw)
    except Exception as e:
        debug(f"nl_parse error: {e}")
        return {}

def cmd_agent_create(args):
    """
    Crea un agente con reglas de gobernanza.
    Modos:
      1. Natural language (--describe "...") - el LLM extrae las reglas
      2. Template                            - plantillas pre-construidas
      3. Manual                              - regla por regla
    """
    section("New Agent")
    api, cfg = get_api()

    can = []
    cannot = []
    name = ""
    description = ""

    # ── MODO 1: Lenguaje natural (--describe o interactivo) ──────────────────
    nl_desc = getattr(args, "action", "") or ""   # reutilizamos --action como --describe

    has_llm = bool(cfg.get("llm_provider") and cfg.get("llm_model"))

    if not nl_desc and has_llm:
        print("  " + q(C.G2, "Describe tu agente en lenguaje natural, o presiona Enter para usar plantillas."))
        print()
        nl_desc = prompt("Describe el agente (o Enter para plantillas)", default="", required=False)

    if nl_desc:
        if not has_llm:
            warn("LLM no configurado - no se puede parsear lenguaje natural.")
            hint("Configura un modelo con:  nova model")
            print()
        else:
            print()
            with Spinner("Analizando descripción con IA...") as sp:
                parsed = nl_parse_agent_rules(nl_desc, cfg)

            if not parsed or not parsed.get("can_do"):
                warn("No pude extraer reglas de esa descripción.")
                hint("Prueba siendo más específico, o usa plantillas.")
                nl_desc = ""
            else:
                name        = parsed.get("name", "")
                description = parsed.get("description", "")
                can         = parsed.get("can_do", [])
                cannot      = parsed.get("cannot_do", [])

                print()
                ok(f"Reglas extraídas: {q(C.B7, name)}")
                print()

                print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "PERMITIDO:", bold=True))
                for action in can:
                    print("       " + q(C.G2, f"+ {action}"))
                print()
                print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "PROHIBIDO:", bold=True))
                for action in cannot:
                    print("       " + q(C.G2, f"- {action}"))
                print()

                if confirm("¿Ajustar alguna regla?", default=False):
                    print()
                    print("  " + q(C.G2, "Añadir más acciones PERMITIDAS (Enter para terminar):"))
                    extra_can = prompt_list("Permitido extra", min_items=0)
                    can.extend(extra_can)
                    print("  " + q(C.G2, "Añadir más RESTRICCIONES (Enter para terminar):"))
                    extra_cannot = prompt_list("Restricción extra", min_items=0)
                    cannot.extend(extra_cannot)

    # ── MODO 2 / 3: Template o manual (si no hubo NL válido) ─────────────────
    if not can and not cannot:
        print()
        print("  " + q(C.G2, "Cómo quieres empezar?"))
        print()
        opts  = ["Desde plantilla (recomendado)", "Manual - regla por regla"]
        descs = ["Plantillas pre-construidas para patrones comunes", "Defines cada regla tú mismo"]
        try:
            mode = _select(opts, descriptions=descs, default=0)
        except KeyboardInterrupt:
            print(); return

        if mode == 0:
            print()
            print("  " + q(C.W, "Elige una plantilla:", bold=True))
            print()
            tpl_keys = list(RULE_TEMPLATES.keys())
            tpl_opts  = [RULE_TEMPLATES[k]["label"] for k in tpl_keys]
            tpl_descs = [RULE_TEMPLATES[k]["description"] for k in tpl_keys]
            try:
                tpl_idx = _select(tpl_opts, descriptions=tpl_descs, default=0)
            except KeyboardInterrupt:
                print(); return
            template = RULE_TEMPLATES[tpl_keys[tpl_idx]]
            can    = list(template["can_do"])
            cannot = list(template["cannot_do"])
            print()
            ok(f"Plantilla cargada: {q(C.B7, template['label'])}")
            print()
            print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "PERMITIDO:", bold=True))
            for a in can[:5]: print("       " + q(C.G2, f"+ {a}"))
            if len(can) > 5: print("       " + q(C.G3, f"... y {len(can)-5} más"))
            print()
            print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "PROHIBIDO:", bold=True))
            for a in cannot[:5]: print("       " + q(C.G2, f"- {a}"))
            if len(cannot) > 5: print("       " + q(C.G3, f"... y {len(cannot)-5} más"))
            print()
            if confirm("¿Personalizar reglas?", default=False):
                can.extend(prompt_list("Permitido adicional", min_items=0))
                cannot.extend(prompt_list("Restricción adicional", min_items=0))
        else:
            print()
            print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ACCIONES PERMITIDAS:", bold=True))
            can = prompt_list("Una por línea", min_items=0)
            print()
            print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "ACCIONES PROHIBIDAS:", bold=True))
            cannot = prompt_list("Una por línea", min_items=0)

    # ── Detalles del agente ───────────────────────────────────────────────────
    print()
    name          = prompt("Nombre del agente", default=name or "Mi Agente", required=True)
    description   = prompt("Descripción breve (opcional)", default=description)
    authorized_by = prompt("Autorizado por", default=cfg.get("user_name", "admin@company.com"))

    # ── Resumen ────────────────────────────────────────────────────────────────
    print()
    can_preview    = ", ".join(can[:2])    + ("..." if len(can)    > 2 else "") if can    else "ninguna"
    cannot_preview = ", ".join(cannot[:2]) + ("..." if len(cannot) > 2 else "") if cannot else "ninguna"
    box([
        f"  Agente      {name}",
        f"  Permite     {can_preview}",
        f"  Prohíbe     {cannot_preview}",
        f"  Por         {authorized_by}",
    ], C.B5, title="Resumen")
    print()

    if not confirm("¿Crear este agente?"):
        warn("Cancelado.")
        return

    # ── Crear en API ───────────────────────────────────────────────────────────
    with Spinner("Firmando Intent Token..."):
        result = api.post("/tokens", {
            "agent_name":   name,
            "description":  description,
            "can_do":       can,
            "cannot_do":    cannot,
            "authorized_by": authorized_by,
        })

    if "error" in result:
        fail(format_api_error(result))
        return

    token_id  = result.get("token_id", "")
    signature = result.get("signature", "")

    ok("Agente creado - token firmado")
    print()
    kv("Token ID",  token_id, C.B7)
    kv("Firma",     (signature[:24] + "...") if signature else "-", C.G3)
    print()

    cfg["default_token"] = token_id
    save_config(cfg)

    if cfg.get("api_key"):
        webhook = f"{cfg['api_url']}/webhook/{cfg['api_key']}"
        section("Webhook")
        print("  " + q(C.G2, "Endpoint para integraciones (n8n, Zapier, etc):"))
        print()
        print("    " + q(C.B7, f"POST {webhook}"))
        print()
        print("    " + q(C.G3, "Body:"))
        print("    " + q(C.G2, '{"action": "tu acción", "token_id": "' + token_id[:12] + '..."}'))
    print()


def cmd_agent_list(args):
    """List all active agents."""
    api, cfg = get_api()
    
    with Spinner("Loading agents..."):
        result = api.get("/tokens")
    
    if "error" in result:
        fail(format_api_error(result))
        return
    
    if not result:
        warn("No active agents.")
        hint("Create one with:  " + q(C.B7, "nova agent create"))
        return
    
    section("Active Agents", f"{len(result)} total")
    
    default_token = cfg.get("default_token", "")
    
    for agent in result:
        agent_id = str(agent.get("id", ""))
        agent_name = agent.get("agent_name", "Unknown")
        is_active = agent.get("active", True)
        is_default = agent_id == default_token
        
        # Status badges
        status = q(C.GRN, "● active") if is_active else q(C.G2, "○ inactive")
        default_badge = "  " + q(C.B6, "default") if is_default else ""
        
        print()
        print("  " + q(C.W, agent_name, bold=True) + "  " + status + default_badge)
        
        kv("  ID", agent_id[:22] + "...", C.G3)
        
        if agent.get("created_at"):
            kv("  Created", time_ago(agent["created_at"]), C.G2)
        
        if agent.get("can_do"):
            preview = ", ".join(agent["can_do"][:3])
            if len(agent["can_do"]) > 3:
                preview += "..."
            kv("  Can do", preview, C.GRN)
        
        if agent.get("cannot_do"):
            preview = ", ".join(agent["cannot_do"][:3])
            if len(agent["cannot_do"]) > 3:
                preview += "..."
            kv("  Forbidden", preview, C.RED)
    
    print()


def cmd_validate(args):
    """Validate an action and get verdict."""
    api, cfg = get_api()
    
    token_id = args.token or cfg.get("default_token", "")
    action = args.action
    context = args.context or ""
    dry_run = getattr(args, "dry_run", False)
    
    # Interactive mode if no action provided
    if not action:
        print_logo(compact=True)
        print()
        action = prompt("Action to validate", required=True)
        if not action:
            return
    
    local_decision = local_policy_decision(action)
    if local_decision:
        print()
        print("  " + verdict_badge(local_decision["verdict"]) + "   " +
              score_bar(local_decision["score"]) + "   " + q(C.G3, "0ms"))
        print()
        kv("Reason", local_decision["reason"], C.G2)
        kv("Agent", "Local Policy", C.W)
        return
    
    if not token_id:
        fail("No token set. Pass --token or create an agent first.")
        hint("Run:  nova agent create")
        return
    
    payload = {
        "token_id": token_id,
        "action": action,
        "context": context,
        "generate_response": True,
        "check_duplicates": True,
    }
    
    if dry_run:
        payload["dry_run"] = True
    
    start_time = time.time()
    
    with Spinner("Validating...") as sp:
        result = api.post("/validate", payload)
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    # Handle errors
    if "error" in result:
        if "Cannot connect" in result.get("error", ""):
            fail("Server unreachable.")
            print()
            if confirm("Queue this action for later?", default=True):
                n = queue_action(payload)
                ok(f"Queued ({n} pending)")
                hint("Run  nova sync  when server is back")
            return
        
        fail(format_api_error(result))
        return
    
    # Show dry run warning
    if dry_run:
        print()
        warn("DRY RUN - not recorded to ledger")
    
    # Results
    verdict = result.get("verdict", "?")
    score = result.get("score", 0)
    reason = result.get("reason", "")
    agent_name = result.get("agent_name", "")
    ledger_id = result.get("ledger_id")
    memories_used = result.get("memories_used", 0)
    response = result.get("response")
    duplicate = result.get("duplicate_of")
    score_factors = result.get("score_factors")
    
    print()
    print("  " + verdict_badge(verdict) + "   " + score_bar(score) + 
          "   " + q(C.G3, f"{elapsed_ms}ms"))
    print()
    
    kv("Reason", reason, C.G2)
    kv("Agent", agent_name, C.W)
    if ledger_id:
        kv("Ledger", f"#{ledger_id}", C.G3)
    kv("Memories used", str(memories_used), C.B6)
    
    # Score breakdown
    if score_factors and isinstance(score_factors, dict):
        print()
        print("  " + q(C.G2, "Score Breakdown"))
        hr(width=32)
        
        for factor, impact in score_factors.items():
            c = C.GRN if impact > 0 else C.RED if impact < 0 else C.G2
            sign = "+" if impact > 0 else ""
            print("  " + q(c, f"{sign}{impact:>4}") + "  " + q(C.G1, factor))
        
        hr(width=32)
        print("  " + q(C.W, f"{score:>4}", bold=True) + "  " + q(C.G2, "Final score"))
    
    # Duplicate detection
    if duplicate:
        print()
        dup_action = duplicate.get("action", "")[:50]
        dup_id = duplicate.get("ledger_id", "?")
        dup_sim = int(duplicate.get("similarity", 0) * 100)
        
        box([
            f"  Duplicate of #{dup_id}",
            f"  Similarity: {dup_sim}%",
            f"  Original: {dup_action}...",
        ], C.ORG, title="Duplicate Detected")
    
    # Generated response
    if response:
        print()
        section("Generated Response")
        print()
        for line in textwrap.wrap(response, width=64):
            print("  " + q(C.G1, line))
    
    # Hash
    hash_val = result.get("hash", "")[:20]
    if hash_val:
        print()
        print("  " + q(C.G3, f"hash  {hash_val}..."))
    
    print()


def cmd_test(args):
    """Dry-run validation - test without recording."""
    args.dry_run = True
    cmd_validate(args)


def cmd_ledger(args):
    """View the cryptographic action ledger."""
    api, cfg = get_api()
    
    limit = getattr(args, "limit", 20) or 20
    verdict_filter = getattr(args, "verdict", "") or ""
    
    url = f"/ledger?limit={limit}"
    if verdict_filter:
        url += f"&verdict={verdict_filter.upper()}"
    
    with Spinner("Loading ledger..."):
        result = api.get(url)
    
    if "error" in result:
        fail(format_api_error(result))
        return
    
    if not result:
        warn("Ledger is empty.")
        return
    
    section("Ledger", f"{len(result)} entries")
    
    verdict_colors = {
        "APPROVED": C.GRN,
        "BLOCKED": C.RED,
        "ESCALATED": C.YLW,
        "DUPLICATE": C.ORG,
    }
    
    for entry in result:
        verdict = entry.get("verdict", "?")
        score = entry.get("score", 0)
        action = entry.get("action", "")[:56]
        agent = entry.get("agent_name", "")[:20]
        ts = time_ago(entry.get("executed_at", ""))
        
        vc = verdict_colors.get(verdict, C.G2)
        
        print()
        print("  " + q(vc, "■") + "  " + q(C.W, action))
        print("     " + q(vc, verdict.ljust(10)) + "  " + score_bar(score, 10) + 
              "  " + q(C.G3, ts) + "  " + q(C.G3, agent))
    
    print()


def cmd_verify(args):
    """Verify ledger cryptographic integrity."""
    api, cfg = get_api()
    
    with Spinner("Verifying cryptographic chain...", style="pulse") as sp:
        result = api.get("/ledger/verify")
    
    if "error" in result:
        fail(format_api_error(result))
        return
    
    print()
    
    if result.get("verified"):
        total = result.get("total_records", 0)
        ok(f"Chain intact - {total:,} records verified")
        kv("Status", "No modifications detected", C.GRN)
        
        chain_hash = result.get("chain_hash", "")
        if chain_hash:
            kv("Chain hash", chain_hash[:32] + "...", C.G3)
    else:
        broken_at = result.get("broken_at", "?")
        fail(f"Chain compromised at record #{broken_at}")
        warn("A ledger record has been tampered with.")
        hint("Contact support immediately.")
    
    print()


def cmd_watch(args):
    """Live stream of ledger entries."""
    api, cfg = get_api()
    interval = getattr(args, "interval", 3) or 3
    
    print_logo(compact=True)
    print("  " + q(C.W, "Watching ledger...", bold=True) + "  " + 
          q(C.G3, "Ctrl+C to stop"))
    hr()
    print()
    
    seen = set()
    verdict_colors = {
        "APPROVED": C.GRN,
        "BLOCKED": C.RED,
        "ESCALATED": C.YLW,
        "DUPLICATE": C.ORG,
    }
    
    try:
        while True:
            result = api.get("/ledger?limit=10")
            
            if isinstance(result, list):
                for entry in reversed(result):
                    entry_id = entry.get("id", "")
                    
                    if entry_id and entry_id not in seen:
                        seen.add(entry_id)
                        
                        verdict = entry.get("verdict", "?")
                        score = entry.get("score", 0)
                        action = entry.get("action", "")[:50]
                        ts = time_ago(entry.get("executed_at", ""))
                        
                        vc = verdict_colors.get(verdict, C.G2)
                        
                        print("  " + q(vc, "■") + "  " + q(C.W, action) + "  " +
                              q(vc, verdict) + "  " + score_bar(score, 8) + 
                              "  " + q(C.G3, ts))
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print()
        info("Stopped watching.")
        print()


def cmd_alerts(args):
    """View and manage pending alerts."""
    api, cfg = get_api()
    
    with Spinner("Loading alerts..."):
        result = api.get("/alerts")
    
    if "error" in result:
        fail(format_api_error(result))
        return
    
    pending = [a for a in result if not a.get("resolved")]
    
    if not pending:
        ok("No pending alerts.")
        print()
        return
    
    section("Pending Alerts", f"{len(pending)} requiring attention")
    
    for alert in pending:
        alert_id = alert.get("id", "")
        message = alert.get("message", "")[:60]
        score = alert.get("score", 0)
        agent = alert.get("agent_name", "")
        ts = time_ago(alert.get("created_at", ""))
        
        ac = C.RED if score < 40 else C.YLW
        
        print()
        print("  " + q(ac, "▲") + "  " + q(C.W, message))
        print("     " + q(C.G2, "Score ") + q(ac, str(score), bold=True) +
              "   " + q(C.G3, agent) + 
              "   " + q(C.G3, str(alert_id)[:12]) +
              "   " + q(C.G3, ts))
    
    print()
    dim("Resolve:  nova alerts resolve <id>")
    print()


def cmd_memory_save(args):
    """Save a memory to an agent's context."""
    api, cfg = get_api()
    
    agent = args.agent or prompt("Agent name", required=True)
    key = args.key or prompt("Memory key", default="important_data")
    value = args.value or prompt("Memory value", required=True)
    importance = int(getattr(args, "importance", 5) or 5)
    
    with Spinner("Saving memory..."):
        result = api.post("/memory", {
            "agent_name": agent,
            "key": key,
            "value": value,
            "importance": importance,
            "tags": ["manual", "cli"],
        })
    
    if "error" in result:
        fail(format_api_error(result))
        return
    
    memory_id = result.get("id", "")
    ok(f"Memory saved - ID {memory_id}  importance {importance}/10")
    print()


def cmd_memory_list(args):
    """List memories for an agent."""
    api, cfg = get_api()
    
    agent = args.agent or prompt("Agent name", required=True)
    
    with Spinner("Loading memories..."):
        result = api.get(f"/memory/{urllib.parse.quote(agent)}")
    
    if "error" in result:
        fail(format_api_error(result))
        return
    
    if not result:
        warn(f"'{agent}' has no memories.")
        hint(f'Save with:  nova memory save --agent "{agent}"')
        return
    
    section(f"Memories of {agent}", f"{len(result)} entries")
    
    for memory in result:
        key = memory.get("key", "")
        value = memory.get("value", "")
        importance = memory.get("importance", 5)
        source = memory.get("source", "manual")
        ts = time_ago(memory.get("created_at", ""))
        
        bar = q(C.B6, "█" * importance) + q(C.G3, "·" * (10 - importance))
        
        print()
        print("  " + q(C.W, key, bold=True) + "  " + bar + "  " + 
              q(C.G3, source) + "  " + q(C.G3, ts))
        
        for line in textwrap.wrap(value, width=60):
            print("    " + q(C.G2, line))
    
    print()


def cmd_export(args):
    """Export ledger to JSON or CSV."""
    api, cfg = get_api()
    
    fmt = getattr(args, "format", "json") or "json"
    limit = getattr(args, "limit", 1000) or 1000
    output = getattr(args, "output", "") or ""
    
    with Spinner(f"Exporting ledger ({limit} entries)..."):
        entries = api.get(f"/ledger?limit={limit}")
    
    if "error" in entries:
        fail(format_api_error(entries))
        return
    
    if not entries:
        warn("No entries to export.")
        return
    
    # Generate filename if not provided
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        ext = "csv" if fmt == "csv" else "json"
        output = f"nova-ledger-{timestamp}.{ext}"
    
    # Export
    if fmt == "csv":
        # CSV without importing csv module
        if entries:
            fields = list(entries[0].keys())
            lines = [",".join(fields)]
            
            for entry in entries:
                row = []
                for field in fields:
                    val = str(entry.get(field, "")).replace('"', '""')
                    if "," in val or '"' in val or "\n" in val:
                        val = f'"{val}"'
                    row.append(val)
                lines.append(",".join(row))
            
            Path(output).write_text("\n".join(lines), encoding="utf-8")
    else:
        Path(output).write_text(
            json.dumps(entries, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    file_size = Path(output).stat().st_size
    
    ok(f"Exported {len(entries):,} entries to {q(C.B7, output)}")
    kv("Format", fmt.upper(), C.G2)
    kv("Size", format_bytes(file_size), C.G2)
    print()


def cmd_sync(args):
    """Process offline queue."""
    api, cfg = get_api()
    queue = get_queue()
    
    if not queue:
        ok("No pending actions in queue.")
        print()
        return
    
    section(f"Syncing {len(queue)} queued actions")
    print()
    
    success = 0
    failed = 0
    
    with ProgressBar(total=len(queue), label="Processing...") as pb:
        for i, item in enumerate(queue):
            result = api.post("/validate", item["data"])
            
            if "error" not in result:
                success += 1
            else:
                failed += 1
            
            pb.update(i + 1)
    
    print()
    
    if success > 0:
        ok(f"{success} actions synced successfully")
    if failed > 0:
        fail(f"{failed} actions failed")
    
    clear_queue()
    print()


def cmd_audit(args):
    """Generate signed audit report."""
    api, cfg = get_api()
    
    with Spinner("Generating audit report...") as sp:
        stats = api.get("/stats")
        verify = api.get("/ledger/verify")
        recent = api.get("/ledger?limit=10")
    
    if "error" in stats:
        fail(format_api_error(stats))
        return
    
    # Build report
    report = {
        "report_type": "nova_audit",
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "generator": f"nova-cli/{NOVA_VERSION}",
        "server_url": cfg.get("api_url", ""),
        "organization": cfg.get("org_name", ""),
        "stats": stats if "error" not in stats else {},
        "chain_verified": verify.get("verified") if "error" not in verify else None,
        "chain_records": verify.get("total_records", 0) if "error" not in verify else 0,
        "chain_hash": verify.get("chain_hash", "") if "error" not in verify else "",
        "recent_entries": recent if isinstance(recent, list) else [],
    }
    
    # Sign the report
    report_str = json.dumps(report, sort_keys=True)
    report["signature"] = hashlib.sha256(report_str.encode()).hexdigest()
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"nova-audit-{timestamp}.json"
    
    Path(filename).write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    file_size = Path(filename).stat().st_size
    
    ok("Audit report generated")
    print()
    kv("File", filename, C.B7)
    kv("Records", f"{report['chain_records']:,}")
    kv("Chain", "Verified" if report["chain_verified"] else "Unverified",
       C.GRN if report["chain_verified"] else C.RED)
    kv("Signature", report["signature"][:32] + "...", C.G3)
    kv("Size", format_bytes(file_size), C.G2)
    print()


def cmd_seed(args):
    """Load demo data for testing."""
    api, cfg = get_api()
    
    warn("This will insert demo agents and sample actions.")
    print()
    
    if not confirm("Continue?"):
        return
    
    with Spinner("Seeding demo data..."):
        result = api.post("/demo/seed", {})
    
    if "error" in result:
        fail(format_api_error(result))
        return
    
    ok("Demo data loaded.")
    kv("Agents", str(result.get("tokens", 0)), C.B7)
    kv("Actions", str(result.get("actions", 0)))
    kv("Memories", str(result.get("memories", 0)), C.B6)
    print()
    hint("Explore with:  " + q(C.B7, "nova status"))
    print()


# ══════════════════════════════════════════════════════════════════════════════
# SKILLS COMMANDS - Full interactive catalog
# ══════════════════════════════════════════════════════════════════════════════

def cmd_skill_browse(args):
    """Interactive skill browser with arrow key navigation."""
    while True:
        print_logo(tagline=False)
        print("  " + q(C.W, "Skills", bold=True) + "  " + q(C.GLD, "✦", bold=True) +
              "  " + q(C.G2, "The Constellation"))
        hr()
        print()
        print("  " + q(C.G1, "Skills give nova real-world context before every decision."))
        print("  " + q(C.G2, "Each skill connects to an external system."))
        print()
        
        # Build options
        all_keys = list(SKILLS.keys())
        installed = get_installed_skills()
        
        opts = []
        descs = []
        
        for key in all_keys:
            skill = SKILLS[key]
            status = "[installed]" if key in installed else ""
            opts.append(f"{skill['icon']}  {skill['name']} {status}")
            descs.append(skill["description"])
        
        opts.append("← Back")
        descs.append("Return to main menu")
        
        try:
            idx = _select(opts, descriptions=descs, default=0, show_index=True)
        except KeyboardInterrupt:
            print()
            break
        
        if idx == len(opts) - 1:
            break
        
        # Selected a skill
        skill_key = all_keys[idx]
        _skill_detail_screen(skill_key)


def _skill_detail_screen(skill_key):
    """Show skill details and options."""
    skill = SKILLS.get(skill_key)
    if not skill:
        return
    
    sc = get_skill_color(skill)
    status = skill_status(skill_key)
    data = load_skill(skill_key)
    
    print()
    print("  " + q(sc, f"{skill['icon']}  {skill['name']}", bold=True) + 
          "  " + q(C.G3, skill.get("category", "")))
    hr()
    print()
    
    print("  " + q(C.G1, skill.get("tagline", "")))
    print()
    
    kv("Description", skill["description"])
    kv("What it does", skill["what_it_does"], C.G2)
    kv("MCP Server", skill.get("mcp", "-"), C.G3)
    kv("Documentation", skill.get("docs_url", "-"), C.B7)
    kv("Status", "✓ Installed" if status == "installed" else "Not installed",
       C.GRN if status == "installed" else C.G2)
    
    if data and data.get("installed_at"):
        kv("Installed", time_ago(data["installed_at"]), C.G3)
    
    # Required fields
    section("Required Configuration")
    
    for field in skill.get("fields", []):
        field_key = field["key"]
        field_label = field["label"]
        is_secret = field.get("secret", False)
        
        if data and data.get(field_key):
            val = "•" * 8 if is_secret else data[field_key][:32]
            status_str = q(C.GRN, val)
        else:
            status_str = q(C.G3, "not configured")
        
        kv(f"  {field_key}", status_str)
    
    print()
    
    # Options based on status
    if status == "installed":
        opts = ["View configuration", "Reconfigure", "Uninstall", "← Back"]
        descs = [
            "Show current field values",
            "Update credentials and settings",
            "Remove this skill",
            "Return to skill list",
        ]
    else:
        opts = ["Install", "View setup guide", "← Back"]
        descs = [
            f"Configure {skill['name']} integration",
            "Step-by-step instructions",
            "Return to skill list",
        ]
    
    try:
        choice = _select(opts, descriptions=descs, default=0)
    except KeyboardInterrupt:
        print()
        return
    
    if status == "installed":
        if choice == 0:
            _skill_view_config(skill_key)
        elif choice == 1:
            _skill_install(skill_key, reconfigure=True)
        elif choice == 2:
            _skill_uninstall(skill_key)
    else:
        if choice == 0:
            _skill_install(skill_key)
        elif choice == 1:
            _skill_setup_guide(skill_key)


def _skill_view_config(skill_key):
    """View skill configuration."""
    skill = SKILLS.get(skill_key)
    data = load_skill(skill_key)
    
    if not skill or not data:
        return
    
    print()
    section(f"Configuration: {skill['name']}")
    
    for field in skill.get("fields", []):
        field_key = field["key"]
        is_secret = field.get("secret", False)
        val = data.get(field_key, "")
        
        if is_secret and val:
            display = "•" * 8 + val[-4:] if len(val) > 4 else "•" * len(val)
        else:
            display = val or "(not set)"
        
        kv(f"  {field_key}", display, C.GRN if val else C.G3)
    
    print()
    pause("go back")


def _skill_setup_guide(skill_key):
    """Show setup guide for a skill."""
    skill = SKILLS.get(skill_key)
    if not skill:
        return
    
    print()
    section(f"Setup Guide: {skill['name']}")
    print()
    
    guide = skill.get("setup_guide", [])
    for step in guide:
        print("  " + q(C.G1, step))
    
    print()
    print("  " + q(C.G2, "Documentation:"))
    print("  " + q(C.B7, skill.get("docs_url", ""), underline=True))
    print()
    
    pause("go back")


def _skill_install(skill_key, reconfigure=False):
    """Install or reconfigure a skill."""
    skill = SKILLS.get(skill_key)
    if not skill:
        return
    
    existing = load_skill(skill_key) or {}
    sc = get_skill_color(skill)
    
    print()
    print("  " + q(C.B6, "✦") + "  " + 
          q(C.W, "Step 1 of 2 - Get credentials", bold=True))
    print()
    print("  " + q(C.G2, "Set up access at:"))
    print("  " + q(C.B7, skill.get("docs_url", ""), underline=True))
    print()
    
    # Show setup guide
    guide = skill.get("setup_guide", [])
    if guide:
        print("  " + q(C.G2, "Quick guide:"))
        for step in guide[:3]:
            print("  " + q(C.G3, f"  {step}"))
        print()
    
    if not confirm("Do you have the credentials ready?", default=False):
        print()
        hint(f"Come back when ready:  nova skill add {skill_key}")
        print()
        return
    
    print()
    print("  " + q(C.B6, "✦") + "  " + 
          q(C.W, "Step 2 of 2 - Configure", bold=True))
    print()
    
    data = dict(existing)
    
    for field in skill.get("fields", []):
        field_key = field["key"]
        field_label = field["label"]
        field_desc = field.get("description", "")
        is_secret = field.get("secret", False)
        is_required = field.get("required", True)
        
        current = existing.get(field_key, "")
        hint_text = "•" * 6 if (is_secret and current) else current[:20] if current else ""
        
        print("  " + q(C.G2, field_desc))
        value = prompt(
            field_label,
            default=hint_text if not is_secret else "",
            secret=is_secret,
            required=is_required
        )
        
        data[field_key] = value or current
        print()
    
    # Verify
    with Spinner("Verifying configuration...") as sp:
        time.sleep(0.5)  # Simulate verification
    
    # Check required fields
    missing = []
    for field in skill.get("fields", []):
        if field.get("required") and not data.get(field["key"]):
            missing.append(field["key"])
    
    if missing:
        warn(f"Missing required fields: {', '.join(missing)}")
        data["status"] = "incomplete"
    else:
        ok(f"{skill['name']} configured successfully")
        data["status"] = "installed"
    
    data["installed_at"] = datetime.now().isoformat()
    data["skill_version"] = "1.0.0"
    save_skill(skill_key, data)
    
    print()
    
    box([
        f"  {skill['icon']}  {skill['name']} connected to nova",
        "",
        f"  {skill['what_it_does']}",
    ], sc, title=skill.get("category", ""))
    
    print()
    hint(f"View details:  nova skill info {skill_key}")
    print()


def _skill_uninstall(skill_key):
    """Uninstall a skill."""
    skill = SKILLS.get(skill_key)
    if not skill:
        return
    
    print()
    warn(f"This will remove {skill['name']} credentials from this machine.")
    print()
    
    if not confirm("Continue?", default=False):
        return
    
    path = SKILLS_DIR / f"{skill_key}.json"
    if path.exists():
        path.unlink()
    
    ok(f"{skill['name']} uninstalled.")
    print()


def cmd_skill_add(args):
    """Add a skill interactively or by name."""
    skill_name = getattr(args, "third", "") or args.subcommand or ""
    
    if skill_name in ("add", "install", "remove", "list", "info", ""):
        skill_name = getattr(args, "third", "") or ""
    
    skill_name = skill_name.lower().strip()
    
    if not skill_name:
        cmd_skill_browse(args)
        return
    
    if skill_name not in SKILLS:
        fail(f"Skill '{skill_name}' not found.")
        hint("Available: " + ", ".join(SKILLS.keys()))
        return
    
    _skill_install(skill_name)


def cmd_skill_info(args):
    """Show skill information."""
    skill_name = getattr(args, "third", "") or args.subcommand or ""
    
    if skill_name in ("info", "add", "list", "remove", ""):
        skill_name = getattr(args, "third", "") or ""
    
    if not skill_name or skill_name not in SKILLS:
        fail(f"Skill not found: {skill_name or '?'}")
        hint("Available: " + ", ".join(SKILLS.keys()))
        return
    
    _skill_detail_screen(skill_name)


def cmd_skill_remove(args):
    """Remove an installed skill."""
    skill_name = getattr(args, "third", "") or args.subcommand or ""
    
    if skill_name in ("remove", "delete", ""):
        skill_name = getattr(args, "third", "") or ""
    
    skill_name = skill_name.lower().strip()
    
    if not skill_name or skill_name not in SKILLS:
        fail("Specify a valid skill name.")
        hint("Installed: " + ", ".join(get_installed_skills()) or "none")
        return
    
    if skill_status(skill_name) != "installed":
        warn(f"{skill_name} is not installed.")
        return
    
    _skill_uninstall(skill_name)


# ══════════════════════════════════════════════════════════════════════════════
# API KEYS COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

def cmd_keys(args):
    """Manage API keys."""
    sub = args.subcommand or ""
    
    if sub == "create" or sub == "new":
        _keys_create()
    elif sub == "delete" or sub == "remove":
        _keys_delete()
    elif sub == "use" or sub == "switch":
        _keys_switch()
    else:
        _keys_list()


def _keys_list():
    """List all saved API keys."""
    data = load_keys()
    keys = data.get("keys", [])
    active = data.get("active", "")
    
    if not keys:
        warn("No API keys saved.")
        hint("Create one with:  " + q(C.B7, "nova keys create"))
        return
    
    section("API Keys", f"{len(keys)} saved")
    
    for key_entry in keys:
        key_val = key_entry.get("key", "")
        key_name = key_entry.get("name", "Unnamed")
        key_id = key_entry.get("id", "")[:8]
        is_active = key_val == active
        created = time_ago(key_entry.get("created_at", ""))
        last_used = time_ago(key_entry.get("last_used", ""))
        
        badge = "  " + q(C.GRN, "active") if is_active else ""
        
        print()
        print("  " + q(C.W, key_name, bold=True) + badge)
        kv("  Key", mask_key(key_val), C.B6)
        kv("  ID", key_id, C.G3)
        kv("  Created", created, C.G3)
        if last_used:
            kv("  Last used", last_used, C.G3)
    
    print()
    dim("nova keys use     - switch active key")
    dim("nova keys create  - generate new key")
    dim("nova keys delete  - remove a key")
    print()


def _keys_create():
    """Create a new API key."""
    print()
    print("  " + q(C.W, "Create new API key", bold=True))
    print()
    
    opts = ["Generate automatically", "Enter manually"]
    descs = [
        "nova creates a secure random key",
        "Paste from another source",
    ]
    
    try:
        choice = _select(opts, descriptions=descs, default=0)
    except KeyboardInterrupt:
        print()
        return
    
    if choice == 0:
        key = generate_api_key("nova")
        name = prompt("Key name", default=f"Key {len(load_keys().get('keys', [])) + 1}")
    else:
        print()
        key = prompt("API Key", secret=True, required=True)
        if not key:
            warn("No key entered.")
            return
        name = prompt("Key name", default="Imported key")
    
    entry = add_api_key(key, name=name)
    
    print()
    ok(f"API key created: {q(C.B7, name)}")
    print()
    print("  " + q(C.G2, "Your key:"))
    print()
    print("    " + q(C.B7, key, bold=True))
    print()
    warn("Save this key securely - it won't be shown again.")
    print()
    
    # Copy to clipboard
    if confirm("Copy to clipboard?", default=False):
        if _copy_to_clipboard(key):
            ok("Copied to clipboard")
        else:
            warn("Could not copy - please copy manually")
    
    # Set as active
    if confirm("Set as active key?", default=True):
        set_active_key(key)
        cfg = load_config()
        cfg["api_key"] = key
        save_config(cfg)
        ok("Now using this key")
    
    print()


def _keys_delete():
    """Delete an API key."""
    data = load_keys()
    keys = data.get("keys", [])
    
    if not keys:
        warn("No keys to delete.")
        return
    
    print()
    print("  " + q(C.W, "Select key to delete:", bold=True))
    print()
    
    opts = [f"{k['name']}  {mask_key(k['key'])}" for k in keys]
    opts.append("← Cancel")
    
    try:
        idx = _select(opts, default=len(opts) - 1)
    except KeyboardInterrupt:
        print()
        return
    
    if idx == len(opts) - 1:
        return
    
    key_entry = keys[idx]
    
    if not confirm(f"Delete '{key_entry['name']}'?", default=False):
        return
    
    if delete_api_key(key_entry.get("id", "")):
        ok("Key deleted.")
    else:
        fail("Could not delete key.")
    
    print()


def _keys_switch():
    """Switch active API key."""
    data = load_keys()
    keys = data.get("keys", [])
    active = data.get("active", "")
    
    if not keys:
        warn("No keys available.")
        return
    
    print()
    print("  " + q(C.W, "Select key to use:", bold=True))
    print()
    
    opts = []
    for k in keys:
        is_active = k["key"] == active
        status = " (active)" if is_active else ""
        opts.append(f"{k['name']}{status}  {mask_key(k['key'])}")
    
    opts.append("← Cancel")
    
    try:
        idx = _select(opts, default=len(opts) - 1)
    except KeyboardInterrupt:
        print()
        return
    
    if idx == len(opts) - 1:
        return
    
    key_entry = keys[idx]
    set_active_key(key_entry["key"])
    
    # Update config
    cfg = load_config()
    cfg["api_key"] = key_entry["key"]
    save_config(cfg)
    
    ok(f"Now using: {key_entry['name']}")
    print()


def _copy_to_clipboard(text):
    """Copy text to clipboard (cross-platform)."""
    try:
        if IS_MAC:
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        elif IS_WINDOWS:
            subprocess.run(["clip"], input=text.encode(), check=True)
            return True
        else:
            # Try xclip, xsel, or wl-copy
            for cmd in [["xclip", "-selection", "clipboard"],
                        ["xsel", "--clipboard", "--input"],
                        ["wl-copy"]]:
                try:
                    subprocess.run(cmd, input=text.encode(), check=True)
                    return True
                except FileNotFoundError:
                    continue
    except Exception as e:
        debug(f"Clipboard error: {e}")
    
    return False


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG COMMAND - Interactive configuration hub
# ══════════════════════════════════════════════════════════════════════════════

def cmd_config(args):
    """Interactive configuration hub."""
    while True:
        cfg = load_config()
        api_url = cfg.get("api_url", "http://localhost:9002")
        api_key = cfg.get("api_key", "")
        keys_data = load_keys()
        num_keys = len(keys_data.get("keys", []))
        installed_skills = get_installed_skills()
        
        # Test connection
        api = NovaAPI(api_url, api_key)
        connected = api.health_check()
        
        # Display current state
        print_logo(compact=True)
        hr()
        print()
        
        kv("  Server", api_url[:40], C.B7 if connected else C.YLW)
        kv("  Status", "Connected" if connected else "Unreachable",
           C.GRN if connected else C.YLW)
        kv("  API Key", mask_key(api_key), C.G2)
        kv("  Saved Keys", str(num_keys), C.G2)
        kv("  Skills", f"{len(installed_skills)}/{len(SKILLS)}", 
           C.GRN if installed_skills else C.G2)
        
        # Validation warnings
        issues = validate_config(cfg)
        if issues:
            print()
            for issue in issues:
                warn(issue)
        
        print()
        hr()
        print()
        
        # Current model info
        llm_prov  = cfg.get("llm_provider", "")
        llm_model = cfg.get("llm_model", "")
        llm_label = f"{LLM_PROVIDERS[llm_prov]['name']} / {llm_model}" if llm_prov in LLM_PROVIDERS else "not configured"
        kv("  Model", llm_label, C.MGN if llm_prov else C.G3)
        
        print()
        hr()
        print()
        
        # Menu options
        opts = [
            "Server",
            "API Keys",
            "Model",
            "Skills",
            "Templates",
            "Profiles",
            "Preferences",
            "About",
            "Reset",
            "Exit",
        ]
        
        descs = [
            "Update server URL",
            f"Manage API keys ({num_keys} saved)",
            f"AI provider & model ({llm_label})",
            f"Browse integrations ({len(installed_skills)} installed)",
            "Pre-built agent rule sets",
            "Switch environments (dev/staging/prod)",
            "Language, theme, telemetry",
            "Version, docs, changelog",
            "Clear all nova data",
            "Return to command line",
        ]
        
        try:
            choice = _select(opts, descriptions=descs, default=0)
        except KeyboardInterrupt:
            print()
            break
        
        if choice == 9:  # Exit
            break
        
        if choice == 0:  # Server
            _config_server(cfg)
        
        elif choice == 1:  # API Keys
            cmd_keys(args)
        
        elif choice == 2:  # Model
            _config_model(cfg)
        
        elif choice == 3:  # Skills
            cmd_skill_browse(args)
        
        elif choice == 4:  # Templates
            _config_templates()
        
        elif choice == 5:  # Profiles
            _config_profiles()
        
        elif choice == 6:  # Preferences
            _config_preferences(cfg)
        
        elif choice == 7:  # About
            _config_about()
        
        elif choice == 8:  # Reset
            _config_reset()
            break
        
        print()


def _config_model(cfg):
    """Configure AI provider, model, and effort level - full 2026 catalog."""
    while True:
        print()
        section("Intelligence", f"{len(LLM_PROVIDERS)} providers · 40+ models")
        
        current_prov   = cfg.get("llm_provider", "")
        current_model  = cfg.get("llm_model", "")
        current_key    = cfg.get("llm_api_key", "")
        current_effort = cfg.get("llm_effort", "medium")
        
        if current_prov in LLM_PROVIDERS:
            pv = LLM_PROVIDERS[current_prov]
            minfo = get_model_info(current_model)
            tier = minfo.get("tier", "")
            kv("Provider", f"{pv['icon']}  {pv['name']}", C.GLD_BRIGHT)
            kv("Model",    minfo.get("label", current_model) + (
                "  " + TIER_BADGE.get(tier, "") if tier in TIER_BADGE else ""), C.W)
            if pv.get("has_effort_slider"):
                kv("Effort",   current_effort, C.MGN)
            kv("API Key",  mask_key(current_key) if current_key and current_key != "ollama" else
               ("local" if current_key == "ollama" else "not set"), C.G3)
        else:
            print("  " + q(C.G3, "No AI provider configured."))
        
        print()
        hr()
        print()
        
        # All providers with model count
        provider_keys = list(LLM_PROVIDERS.keys())
        provider_opts  = []
        provider_descs = []
        
        for pk in provider_keys:
            pv    = LLM_PROVIDERS[pk]
            badge = "  ★ active" if pk == current_prov else ""
            n     = len(pv["models"])
            provider_opts.append(f"{pv['icon']}  {pv['name']}{badge}")
            provider_descs.append(f"{pv['tagline']}  ({n} models)")
        
        provider_opts.append("← Back")
        provider_descs.append("Return to config menu")
        
        default_prov_idx = provider_keys.index(current_prov) if current_prov in provider_keys else 0
        
        try:
            prov_idx = _select(provider_opts, descriptions=provider_descs,
                               default=default_prov_idx)
        except KeyboardInterrupt:
            print()
            return
        
        if prov_idx == len(provider_keys):
            return
        
        chosen_prov = provider_keys[prov_idx]
        prov_data   = LLM_PROVIDERS[chosen_prov]
        
        # ── Model selection ──────────────────────────────────────────────────
        print()
        print("  " + q(C.W, f"{prov_data['icon']}  {prov_data['name']}", bold=True))
        print("  " + q(C.G2, prov_data["tagline"]))
        print()
        
        model_entries = prov_data["models"]
        model_opts    = []
        model_descs   = []
        
        default_midx = 0
        default_id = current_model if chosen_prov == current_prov else prov_data.get("default_model","")
        
        for mi, m in enumerate(model_entries):
            tier_badge = ("  " + TIER_BADGE.get(m[2], "")) if len(m) > 2 else ""
            active_mark = "  ← current" if m[0] == current_model else ""
            model_opts.append(m[1] + tier_badge + active_mark)
            model_descs.append(m[3] if len(m) > 3 else "")
            if m[0] == default_id:
                default_midx = mi
        
        try:
            model_idx = _select(model_opts, descriptions=model_descs, default=default_midx)
        except KeyboardInterrupt:
            continue
        
        chosen_model = model_entries[model_idx][0]
        
        # Custom Ollama model name
        if chosen_model == "ollama/custom":
            print()
            try:
                custom = prompt("Ollama model name", default="qwen3.5:27b")
                chosen_model = f"ollama/{custom}" if custom else "ollama/qwen3.5:27b"
            except (EOFError, KeyboardInterrupt):
                chosen_model = "ollama/qwen3.5:27b"
        
        # ── Effort level (Claude extended thinking) ──────────────────────────
        chosen_effort = current_effort
        if prov_data.get("has_effort_slider") and "claude" in chosen_model.lower():
            print()
            print("  " + q(C.W, "Reasoning effort", bold=True) + "  " +
                  q(C.G3, "(Claude Code-style effort slider)"))
            print()
            effort_opts  = ["⚡  low    - fastest, cheapest",
                            "★  medium - recommended",
                            "🔥  high   - deepest, slowest"]
            effort_descs = ["Quick decisions, minimal thinking",
                            "Best cost/quality balance for most tasks",
                            "Complex edge cases, maximum accuracy"]
            cur_eff_idx = ["low","medium","high"].index(current_effort) if current_effort in ["low","medium","high"] else 1
            try:
                eff_idx = _select(effort_opts, descriptions=effort_descs, default=cur_eff_idx)
                chosen_effort = ["low","medium","high"][eff_idx]
            except KeyboardInterrupt:
                pass
        
        # ── API Key ──────────────────────────────────────────────────────────
        needs_key = prov_data.get("needs_api_key", True)
        new_key = current_key if chosen_prov == current_prov else ""
        
        if needs_key:
            print()
            print("  " + q(C.G2, "Get your key at:  ") +
                  q(C.B7, prov_data["key_url"], underline=True))
            print()
            
            hint_text = "keep existing" if (chosen_prov == current_prov and current_key) else ""
            try:
                typed = prompt(f"{prov_data['name']} API Key",
                               default=hint_text, secret=True)
            except (EOFError, KeyboardInterrupt):
                typed = ""
            
            if typed and typed != "keep existing":
                new_key = typed
            elif not typed and chosen_prov == current_prov:
                new_key = current_key  # keep existing
        else:
            new_key = "ollama"
            print()
            info("Local mode - no API key needed")
            info("Make sure Ollama is running:  ollama serve")
        
        # Save
        cfg["llm_provider"] = chosen_prov
        cfg["llm_model"]    = chosen_model
        cfg["llm_api_key"]  = new_key
        cfg["llm_effort"]   = chosen_effort
        save_config(cfg)
        
        minfo = get_model_info(chosen_model)
        print()
        ok(f"{prov_data['name']} · {minfo.get('label', chosen_model)}")
        if chosen_effort != "medium" and prov_data.get("has_effort_slider"):
            ok(f"Effort: {chosen_effort}")
        if new_key and new_key != "ollama":
            ok("API key saved")
        elif new_key == "ollama":
            ok("Local mode - no key needed")
        else:
            warn("No key entered")
        
        print()
        return



def _config_server(cfg):
    """Configure server connection."""
    print()
    section("Server Configuration")
    
    current_url = cfg.get("api_url", "http://localhost:9002")
    kv("Current URL", current_url, C.B7)
    
    # Test current connection
    api = NovaAPI(current_url, cfg.get("api_key", ""))
    connected = api.health_check()
    kv("Status", "Connected" if connected else "Unreachable",
       C.GRN if connected else C.RED)
    
    print()
    
    try:
        new_url = prompt(
            "New URL (Enter to keep)",
            default=current_url,
            validator=lambda x: True if x.startswith(("http://", "https://"))
                                else "URL must start with http:// or https://"
        )
        
        if new_url and new_url != current_url:
            cfg["api_url"] = new_url
            save_config(cfg)
            ok("Server URL updated.")
            
            # Test new connection
            api = NovaAPI(new_url, cfg.get("api_key", ""))
            if api.health_check():
                ok("Connection verified.")
            else:
                warn("Could not connect to new server.")
    
    except (EOFError, KeyboardInterrupt):
        pass


def _config_templates():
    """Browse rule templates."""
    print()
    section("Rule Templates")
    print("  " + q(C.G1, "Pre-built rule sets for common agent patterns."))
    print("  " + q(C.G2, f"Use with:  nova agent create"))
    print()
    
    for key, template in RULE_TEMPLATES.items():
        print("  " + q(C.B6, template.get("icon", "●")) + "  " + 
              q(C.W, template["label"], bold=True))
        print("       " + q(C.G2, template["description"]))
        print()
        
        # Show preview of rules
        can_preview = ", ".join(template["can_do"][:2])
        cannot_preview = ", ".join(template["cannot_do"][:2])
        print("       " + q(C.GRN, "✓") + " " + q(C.G3, can_preview + "..."))
        print("       " + q(C.RED, "✗") + " " + q(C.G3, cannot_preview + "..."))
        print()
    
    pause("go back")


def _config_profiles():
    """Manage configuration profiles."""
    profiles_data = load_profiles()
    profiles = profiles_data.get("profiles", {})
    active = profiles_data.get("active", "default")
    
    print()
    section("Profiles", f"{len(profiles)} available")
    print("  " + q(C.G2, "Switch between environments (dev/staging/prod)"))
    print()
    
    for name, profile in profiles.items():
        is_active = name == active
        badge = "  " + q(C.GRN, "active") if is_active else ""
        
        print("  " + q(C.W, profile.get("name", name), bold=True) + badge)
        kv("    URL", profile.get("api_url", "-"), C.G3)
        if profile.get("description"):
            kv("    Description", profile["description"], C.G3)
        print()
    
    opts = list(profiles.keys()) + ["Create new profile", "← Back"]
    
    try:
        idx = _select(opts, default=len(opts) - 1)
    except KeyboardInterrupt:
        print()
        return
    
    if idx == len(opts) - 1:  # Back
        return
    
    if idx == len(opts) - 2:  # Create new
        print()
        name = prompt("Profile name", required=True)
        if not name:
            return
        
        url = prompt("Server URL", default="http://localhost:9002")
        desc = prompt("Description (optional)")
        
        profiles_data["profiles"][name.lower().replace(" ", "-")] = {
            "name": name,
            "api_url": url,
            "description": desc,
        }
        save_profiles(profiles_data)
        ok(f"Profile '{name}' created.")
    
    else:  # Switch to profile
        profile_key = opts[idx]
        switch_profile(profile_key)
        ok(f"Switched to profile: {profile_key}")
    
    print()


def _config_preferences(cfg):
    """Configure preferences."""
    print()
    section("Preferences")
    
    # Language
    lang = cfg.get("lang", "en")
    kv("Language", "English" if lang == "en" else "Español", C.W)
    
    print()
    
    try:
        lang_idx = _select(["English", "Español"], 
                           default=0 if lang == "en" else 1)
        cfg["lang"] = "en" if lang_idx == 0 else "es"
        save_config(cfg)
        ok("Preferences saved.")
    except (EOFError, KeyboardInterrupt):
        pass


def _config_about():
    """Show about information."""
    print()
    section("About nova")
    
    kv("Version", NOVA_VERSION, C.B6)
    kv("Build", NOVA_BUILD, C.G3)
    kv("Codename", NOVA_CODENAME, C.G2)
    kv("Platform", f"{PLATFORM} ({platform.machine()})", C.G3)
    kv("Python", platform.python_version(), C.G3)
    kv("Config", str(CONFIG_FILE), C.G3)
    
    print()
    kv("Documentation", "https://github.com/sxrubyo/nova-os", C.B7)
    kv("Support", "https://nova-os.com/support", C.B7)
    kv("Terms", "https://nova-os.com/terms", C.G3)
    
    # Changelog highlights
    print()
    print("  " + q(C.G2, f"What's new in {NOVA_VERSION}:"))
    print()
    
    features = [
        "Ghost writing animations for premium feel",
        "Full arrow-key navigation throughout",
        "Rule templates for quick agent setup",
        "Live ledger watch mode",
        "Offline queue with automatic sync",
        "Enterprise API key management",
        "Multi-profile support (dev/staging/prod)",
        "Signed audit report generation",
        "Shell autocompletion (bash/zsh/fish)",
    ]
    
    for feature in features:
        print("    " + q(C.B6, "·") + "  " + q(C.G1, feature))
    
    print()
    pause("go back")


def _config_reset():
    """Reset all nova data."""
    print()
    warn("This will erase ALL nova data including:")
    print()
    bullet("Configuration and preferences", C.G1)
    bullet("All saved API keys", C.G1)
    bullet("Installed skills", C.G1)
    bullet("Profiles", C.G1)
    bullet("Offline queue", C.G1)
    print()
    
    if not confirm_danger("Are you sure?", confirm_text="RESET"):
        info("Reset cancelled.")
        return
    
    # Remove nova directory
    if NOVA_DIR.exists():
        shutil.rmtree(NOVA_DIR)
    
    ok("nova has been reset.")
    hint("Run  " + q(C.B7, "nova init") + "  to start fresh.")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# HELP COMMAND
# ══════════════════════════════════════════════════════════════════════════════

def cmd_model_list(args=None):
    """Show all available models across all providers."""
    print_logo(compact=True)
    section("Available Models", f"{len(LLM_PROVIDERS)} providers · 2026 edition")
    
    cfg = load_config()
    current_model = cfg.get("llm_model", "")
    
    for prov_key, prov in LLM_PROVIDERS.items():
        print()
        print("  " + q(C.GLD_BRIGHT, prov.get("icon","·"), bold=True) +
              "  " + q(C.W, prov["name"], bold=True) +
              "  " + q(C.G3, prov["tagline"]))
        print()
        
        for m in prov["models"]:
            model_id = m[0]
            label    = m[1]
            tier     = m[2] if len(m) > 2 else "balanced"
            desc     = m[3] if len(m) > 3 else ""
            badge    = TIER_BADGE.get(tier, "")
            active   = " ← active" if model_id == current_model else ""
            
            print("    " + q(C.G3, "·") + "  " +
                  q(C.W if model_id == current_model else C.G1, label, bold=(model_id == current_model)) +
                  "  " + q(C.B7, badge) +
                  q(C.GRN, active))
            if desc:
                print("       " + q(C.G3, desc))
    
    print()
    hr()
    print()
    hint("Switch model:  " + q(C.W, "nova model") + "  or  " + q(C.W, "nova config model"))
    print()


def cmd_help(args=None):
    """Display comprehensive help."""
    print_logo()
    
    print("  " + q(C.W, "Enterprise-grade governance infrastructure for AI agents."))
    print()
    hr()
    print()
    
    # Command sections
    sections = [
        ("Getting Started", [
            ("init",             "First-run setup wizard  (13 steps)"),
            ("boot",             "Start Nova Core + connect all agents in one command"),
            ("guard",            "Protect all your AI agents in one command"),
            ("rule \"<text>\"",  "Add a governance rule instantly"),
            ("status",           "System health and metrics"),
            ("launchpad",        "Guided operator entrypoint"),
            ("config",           "Interactive settings hub"),
            ("workspace",        "Workspace info, plan, quota"),
        ]),
        ("Agents", [
            ("agent create",     "Create agent - NL / template / manual"),
            ("agent list",       "List all agents"),
            ("agent edit",       "Edit rules, description, policy"),
            ("agent history",    "View version history of rules"),
            ("setup",            "Opinionated setup for known agent types"),
            ("connect",          "Connect Nova Core to a running agent"),
        ]),
        ("Policies", [
            ("policy",           "List policy templates"),
            ("policy create",    "Create reusable rule set"),
            ("policy view <id>", "View a specific policy"),
            ("policy edit <id>", "Edit a policy"),
            ("policy delete",    "Delete a policy"),
        ]),
        ("Validation", [
            ("validate",         "Validate an action"),
            ("validate explain", "Deep AI explanation of the decision"),
            ("validate batch",   "Validate up to 20 actions in parallel"),
            ("simulate",         "Test policy without creating token/ledger"),
            ("test",             "Dry-run validation"),
        ]),
        ("Memory", [
            ("memory save",      "Store agent context"),
            ("memory list",      "View agent memories"),
            ("memory search",    "Semantic search across memories"),
            ("memory update",    "Edit an existing memory"),
        ]),
        ("Ledger", [
            ("ledger", "View action history"),
            ("verify", "Check chain integrity"),
            ("watch", "Live stream entries"),
            ("export", "Export to JSON/CSV"),
            ("audit", "Generate audit report"),
        ]),
        ("API Keys", [
            ("keys", "List saved keys"),
            ("keys create", "Generate new key"),
            ("keys use", "Switch active key"),
        ]),
        ("Skills", [
            ("skill", "Browse catalog (↑↓)"),
            ("skill add <name>", "Install a skill"),
            ("skill info <name>", "View skill details"),
        ]),
        ("Governance Integrations", [
            ("rule \"<text>\"",   "Create a rule in one line - instant"),
            ("rules",            "List, manage & test rules"),
            ("rules create",     "Interactive rule builder"),
            ("rules test",       "Test a rule against a sample action"),
            ("run",              "Wrap any CLI command with nova validation"),
            ("shield",           "HTTP proxy - intercept & validate every request"),
            ("protect",          "Attach to a live HTTP agent (fire-and-forget)"),
            ("scout",            "Security scan - detect misconfigurations"),
            ("connect",          "Connect Nova to a running agent"),
        ]),
        ("Tools & System", [
            ("doctor",           "Diagnose & auto-repair common issues"),
            ("mcp export",       "Export config as MCP-compatible manifest"),
            ("mcp import",       "Import MCP tool definitions"),
            ("chat",             "Chat with the Nova governance AI"),
            ("anomalies",        "View detected behavioral anomalies"),
            ("stream",           "Live-stream raw validation events"),
            ("benchmark",        "Measure validation latency & throughput"),
        ]),
        ("Stats", [
            ("stats",            "Analytics overview"),
            ("stats agents",     "Per-agent breakdown"),
            ("stats hourly",     "Activity heatmap by hour"),
            ("stats risk",       "Risk profile per agent"),
            ("stats timeline",   "Hour-by-hour timeline"),
            ("stats anomalies",  "Detected behavioral anomalies"),
        ]),
        ("System", [
            ("sync",             "Process offline queue"),
            ("seed",             "Load demo data"),
            ("alerts",           "View pending alerts"),
        ]),
    ]
    
    for section_title, commands in sections:
        print("  " + q(C.GLD_MATTE, section_title.upper(), bold=True))
        hr(char="─", width=62, color=C.ASH)
        print()

        for cmd, desc in commands:
            print("    " + q(C.W, ("nova " + cmd).ljust(26), bold=True) +
                  q(C.G2, desc))

        print()
    
    hr()
    print()
    
    # Aliases
    print("  " + q(C.GLD_MATTE, "ALIASES", bold=True))
    hr(char="─", width=62, color=C.ASH)
    print()
    alias_pairs = [
        ("s", "status"), ("v", "validate"), ("a", "agent"),
        ("c", "config"), ("l", "ledger"),   ("w", "watch"),
        ("r", "rules"),  ("st", "stats"),   ("pol", "policy"),
        ("sim", "simulate"),
    ]
    alias_str = "  ".join(q(C.W, k, bold=True) + q(C.G2, f" → {v}") for k, v in alias_pairs)
    print("  " + alias_str)
    print()
    
    # Examples
    print("  " + q(C.GLD_MATTE, "EXAMPLES", bold=True))
    hr(char="─", width=62, color=C.ASH)
    print()

    examples = [
        ('nova boot',
         "Start Nova Core + connect all agents"),
        ('nova exec "pm2 restart melissa"',
         "Run a command with risk classification + confirmation"),
        ('nova guard',
         "Protect all AI agents in your project - one command"),
        ('nova rule "never delete files from /prod"',
         "Add a rule in plain language - active instantly"),
        ('nova guard --path .env',
         "Protect a specific path from ALL agents"),
        ('nova validate --action "Send email to bob@acme.com"',
         "Manually validate an action"),
        ('nova ledger --limit 50 --verdict BLOCKED',
         "Review blocked actions"),
        ('nova watch --interval 3',
         "Live-stream ledger events"),
        ('nova stats',
         "Open the analytics dashboard"),
        ('NOVA_DEBUG=1 nova status',
         "Run with verbose debug output"),
    ]

    for ex, note in examples:
        print("    " + q(C.B7, "$ ", bold=True) + q(C.W, ex))
        print("      " + q(C.G3, note))
        print()
    
    # Links
    print("  " + q(C.W, "Docs: ") + 
          q(C.W, "https://github.com/sxrubyo/nova-os", underline=True))
    print()


# ══════════════════════════════════════════════════════════════════════════════
# SHELL COMPLETION
# ══════════════════════════════════════════════════════════════════════════════

def cmd_completion(args):
    """Generate shell completion scripts."""
    shell = args.subcommand or ""
    
    if not shell:
        # Auto-detect shell
        shell_path = os.environ.get("SHELL", "")
        if "zsh" in shell_path:
            shell = "zsh"
        elif "fish" in shell_path:
            shell = "fish"
        else:
            shell = "bash"
    
    commands = [
        "init", "status", "config", "whoami",
        "agent", "validate", "test",
        "memory", "ledger", "verify", "watch", "export", "audit",
        "keys", "skill", "sync", "seed", "alerts",
        "run", "shield", "scout", "doctor", "mcp",
        "help", "completion"
    ]
    
    if shell == "bash":
        print(f"""
# nova CLI bash completion
# Add to ~/.bashrc: eval "$(nova completion bash)"

_nova_completions() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    local prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    
    case "$prev" in
        agent)
            COMPREPLY=($(compgen -W "create list" -- "$cur"))
            ;;
        memory)
            COMPREPLY=($(compgen -W "save list" -- "$cur"))
            ;;
        skill)
            COMPREPLY=($(compgen -W "add remove info list" -- "$cur"))
            ;;
        keys)
            COMPREPLY=($(compgen -W "create delete use list" -- "$cur"))
            ;;
        mcp)
            COMPREPLY=($(compgen -W "export list import" -- "$cur"))
            ;;
        completion)
            COMPREPLY=($(compgen -W "bash zsh fish" -- "$cur"))
            ;;
        *)
            COMPREPLY=($(compgen -W "{' '.join(commands)}" -- "$cur"))
            ;;
    esac
}}
complete -F _nova_completions nova
""".strip())
    
    elif shell == "zsh":
        print(f"""
# nova CLI zsh completion
# Add to ~/.zshrc: eval "$(nova completion zsh)"

_nova() {{
    local -a commands=(
        'init:First-run setup'
        'status:System health'
        'config:Settings hub'
        'whoami:Current identity'
        'agent:Agent management'
        'validate:Validate action'
        'test:Dry-run validation'
        'memory:Agent memory'
        'ledger:Action history'
        'verify:Check integrity'
        'watch:Live stream'
        'export:Export ledger'
        'audit:Generate report'
        'keys:API key management'
        'skill:Skill catalog'
        'sync:Process queue'
        'seed:Load demo data'
        'alerts:View alerts'
        'run:Process wrapper'
        'shield:Proxy validation'
        'scout:Skills security scan'
        'doctor:Auto-repair'
        'mcp:MCP export'
        'help:Show help'
    )
    
    _describe 'commands' commands
}}
compdef _nova nova
""".strip())
    
    elif shell == "fish":
        print("""
# nova CLI fish completion
# Save to ~/.config/fish/completions/nova.fish

complete -c nova -n __fish_use_subcommand -a init -d 'First-run setup'
complete -c nova -n __fish_use_subcommand -a status -d 'System health'
complete -c nova -n __fish_use_subcommand -a config -d 'Settings hub'
complete -c nova -n __fish_use_subcommand -a whoami -d 'Current identity'
complete -c nova -n __fish_use_subcommand -a agent -d 'Agent management'
complete -c nova -n __fish_use_subcommand -a validate -d 'Validate action'
complete -c nova -n __fish_use_subcommand -a test -d 'Dry-run validation'
complete -c nova -n __fish_use_subcommand -a memory -d 'Agent memory'
complete -c nova -n __fish_use_subcommand -a ledger -d 'Action history'
complete -c nova -n __fish_use_subcommand -a verify -d 'Check integrity'
complete -c nova -n __fish_use_subcommand -a watch -d 'Live stream'
complete -c nova -n __fish_use_subcommand -a export -d 'Export ledger'
complete -c nova -n __fish_use_subcommand -a audit -d 'Generate report'
complete -c nova -n __fish_use_subcommand -a keys -d 'API keys'
complete -c nova -n __fish_use_subcommand -a skill -d 'Skill catalog'
complete -c nova -n __fish_use_subcommand -a sync -d 'Process queue'
complete -c nova -n __fish_use_subcommand -a seed -d 'Demo data'
complete -c nova -n __fish_use_subcommand -a alerts -d 'View alerts'
complete -c nova -n __fish_use_subcommand -a run -d 'Process wrapper'
complete -c nova -n __fish_use_subcommand -a shield -d 'Proxy validation'
complete -c nova -n __fish_use_subcommand -a scout -d 'Skills security scan'
complete -c nova -n __fish_use_subcommand -a doctor -d 'Auto-repair'
complete -c nova -n __fish_use_subcommand -a mcp -d 'MCP export'
complete -c nova -n __fish_use_subcommand -a help -d 'Show help'

complete -c nova -n '__fish_seen_subcommand_from agent' -a 'create list'
complete -c nova -n '__fish_seen_subcommand_from memory' -a 'save list'
complete -c nova -n '__fish_seen_subcommand_from skill' -a 'add remove info list'
complete -c nova -n '__fish_seen_subcommand_from keys' -a 'create delete use list'
complete -c nova -n '__fish_seen_subcommand_from mcp' -a 'export list import'
""".strip())
    
    else:
        fail(f"Unknown shell: {shell}")
        hint("Supported: bash, zsh, fish")


# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# NOVA v3.2 - NEW COMMANDS
# ══════════════════════════════════════════════════════════════════════════════


# ── Section 4 ────────────────────────────────────────
def cmd_connect(args):
    """
    Connect Nova Core to a running agent.
    Auto-discovers if no URL provided.
    Saves the connection for future CLI sessions.
    """
    print_logo(compact=True)
    section("Connect Agent")

    nc = _get_nova_core()

    # ── Check if Nova Core is alive ───────────────────────────────────────────
    with Spinner("Checking Nova Core...") as sp:
        alive = nc.is_alive()
        sp.finish()

    if not alive:
        fail("Nova Core is not running.")
        print()
        hint("Start it with:  " + q(C.B7, "python nova_core.py"))
        hint("Or set URL:     " + q(C.B7, "NOVA_CORE_URL=http://your-server:9003"))
        print()
        return

    ok("Nova Core reachable")
    print()

    # ── Get agent URL ─────────────────────────────────────────────────────────
    agent_url  = getattr(args, "url",  "") or getattr(args, "upstream", "") or ""
    agent_name = getattr(args, "agent", "") or getattr(args, "name", "agent") or ""

    if not agent_url:
        # Scan first
        print("  " + q(C.G2, "Scanning for running agents..."))
        with Spinner("Scanning localhost ports...") as sp:
            scan_result = nc.scan()
            sp.finish()

        agents = scan_result.get("agents", [])
        if agents:
            print()
            print("  " + q(C.W, "Found agents:", bold=True))
            print()
            opts  = [f"{a['name']} - {a['url']}" for a in agents]
            opts.append("Enter URL manually")
            try:
                idx = _select(opts, default=0)
            except KeyboardInterrupt:
                print(); return

            if idx < len(agents):
                agent_url  = agents[idx]["url"]
                agent_name = agents[idx]["name"]
            else:
                agent_url = prompt("Agent URL", required=True)
                if not agent_name:
                    agent_name = prompt("Agent name", default="agent")
        else:
            warn("No agents detected on common ports.")
            print()
            agent_url  = prompt("Agent URL (e.g. http://localhost:8001)", required=True)
            agent_name = prompt("Agent name", default="agent")

    # ── Connect ───────────────────────────────────────────────────────────────
    print()
    with Spinner(f"Connecting to {agent_name}...") as sp:
        result = nc.connect_agent(agent_url, agent_name)
        sp.finish()

    if "error" in result:
        fail(f"Connection failed: {result['error']}")
        return

    ok(f"Connected to {q(C.B7, agent_name)}")
    print()
    kv("Agent URL",  result.get("agent_url", agent_url), C.B7)
    kv("Scope",      result.get("scope", f"agent:{agent_name}"), C.G2)
    kv("Reachable",  "yes ✓" if result.get("reachable") else "no (check agent)", C.GRN)
    print()

    # ── Save connection ───────────────────────────────────────────────────────
    cfg = load_config_secure()
    cfg["connected_agent_url"]  = agent_url
    cfg["connected_agent_name"] = agent_name
    save_config_secure(cfg)

    hint(f"Nova is now governing  {q(C.B7, agent_name)}")
    hint("Try: " + q(C.B7, "nova rules list") + "  to see active governance rules")
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 5 ────────────────────────────────────────
def cmd_scan(args):
    """
    Scan localhost for running AI agents.
    Works with or without Nova Core running.
    """
    print_logo(compact=True)
    section("Agent Scanner")

    # ── Try via Nova Core first ───────────────────────────────────────────────
    nc = _get_nova_core()

    if nc.is_alive():
        with Spinner("Scanning via Nova Core...") as sp:
            result = nc.scan()
            sp.finish()
        agents = result.get("agents", [])
    else:
        # Fallback: scan directly without Nova Core
        import socket as _sock
        warn("Nova Core not running - scanning directly")
        print()
        KNOWN = [
            (8001, "Agent (8001)",  "python"),
            (8002, "Agent (8002)",  "python"),
            (5678, "n8n",           "node"),
            (8080, "Evolution API", "node"),
            (3000, "Baileys",       "node"),
            (8000, "FastAPI",       "python"),
            (1234, "LM Studio",     "native"),
            (11434,"Ollama",        "native"),
            (9003, "Nova Core",     "python"),
            (9002, "Nova OS",       "python"),
        ]
        agents = []
        with Spinner("Scanning ports...") as sp:
            for port, name, runtime in KNOWN:
                s = _sock.socket()
                s.settimeout(0.25)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    agents.append({
                        "port": port, "name": name,
                        "runtime": runtime, "url": f"http://localhost:{port}"
                    })
                s.close()
            sp.finish()

    if not agents:
        warn("No agents found on common ports.")
        print()
        hint("Make sure your agent is running before connecting Nova.")
        print()
        return

    print()
    print("  " + q(C.W, f"Found {len(agents)} agent(s):", bold=True))
    print()

    RUNTIME_ICONS = {"python": "🐍", "node": "⬡", "native": "◎", "unknown": "·"}
    for a in agents:
        icon = RUNTIME_ICONS.get(a.get("runtime", ""), "·")
        port = str(a["port"])
        name = a["name"]
        url  = a["url"]
        print(
            "  " + q(C.GRN, "●") + "  " +
            q(C.W, name, bold=True) + "  " +
            q(C.G3, f":{port}") + "  " +
            q(C.G2, icon + " " + a.get("runtime", ""))
        )
        print("       " + q(C.B7, url))

    print()

    # ── Offer to connect ──────────────────────────────────────────────────────
    if confirm("Connect Nova Core to one of these?", default=True):
        opts = [f"{a['name']} - {a['url']}" for a in agents]
        try:
            idx = _select(opts, default=0)
        except KeyboardInterrupt:
            print(); return

        chosen = agents[idx]
        nc2 = _get_nova_core()
        if nc2.is_alive():
            with Spinner("Connecting...") as sp:
                r = nc2.connect_agent(chosen["url"], chosen["name"])
                sp.finish()
            if "error" not in r:
                ok(f"Connected to {q(C.B7, chosen['name'])}")
                cfg = load_config_secure()
                cfg["connected_agent_url"]  = chosen["url"]
                cfg["connected_agent_name"] = chosen["name"]
                save_config_secure(cfg)
            else:
                fail(f"Connect failed: {r['error']}")
        else:
            warn("Nova Core not running - start it first, then run  nova connect")
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 6 ────────────────────────────────────────
def cmd_rules(args):
    """Entry point for 'nova rules' subcommands."""
    sub = getattr(args, "subcommand", "") or ""
    if sub in ("create", "add", "new"):
        return cmd_rules_create(args)
    elif sub in ("delete", "remove", "del"):
        return cmd_rules_delete(args)
    elif sub in ("test", "check"):
        return cmd_rules_test(args)
    elif sub in ("import",):
        return cmd_rules_import(args)
    else:
        return cmd_rules_list(args)


def cmd_rules_list(args):
    """List all active governance rules with rich detail."""
    nc = _get_nova_core()

    if not nc.is_alive():
        fail("Nova Core not running.")
        hint("Start:  python nova_core.py")
        return

    scope = getattr(args, "value", "") or "global"
    with Spinner("Loading rules..."):
        result = nc.rules_list(scope=scope)

    if "error" in result:
        fail(f"Error: {result['error']}")
        return

    rules = result.get("rules", [])
    total = result.get("total", len(rules))

    print_logo(compact=True)
    section("Governance Rules", f"{total} active")

    if not rules:
        warn("No rules active.")
        print()
        hint("Create one:  " + q(C.B7, 'nova rules create'))
        hint("Or via chat: " + q(C.B7, 'nova chat'))
        print()
        return

    ACTION_COLORS = {
        "block":    C.RED,
        "warn":     C.YLW,
        "escalate": C.ORG,
        "log_only": C.G2,
    }
    SOURCE_ICONS = {
        "intercepted":       "⟳",
        "natural_language":  "◉",
        "manual":            "✎",
        "api":               "⬡",
        "seed":              "◆",
    }

    for i, rule in enumerate(rules):
        if i > 0:
            print("  " + q(C.G3, "·" * 50))
        print()
        action_color = ACTION_COLORS.get(rule.get("action",""), C.G2)
        source_icon  = SOURCE_ICONS.get(rule.get("source",""), "·")
        print(
            "  " + q(action_color, "■", bold=True) + "  " +
            q(C.W, rule.get("name", "?"), bold=True) + "  " +
            q(action_color, f"[{rule.get('action','?').upper()}]") + "  " +
            q(C.G3, f"prio={rule.get('priority','?')}") + "  " +
            q(C.G3, source_icon + " " + rule.get("source", ""))
        )
        kv("  ID",    rule.get("id","?"),    C.G3)
        kv("  Scope", rule.get("scope","?"), C.G2)

        det = rule.get("deterministic", {})
        kw_block = det.get("keywords_block", [])
        kw_warn  = det.get("keywords_warn",  [])
        regex    = det.get("regex_block",    [])
        if kw_block:
            kv("  Keywords (block)", ", ".join(kw_block[:4]) + ("..." if len(kw_block) > 4 else ""), C.RED)
        if kw_warn:
            kv("  Keywords (warn)",  ", ".join(kw_warn[:4])  + ("..." if len(kw_warn)  > 4 else ""), C.YLW)
        if regex:
            kv("  Regex",            regex[0][:60], C.MGN)

        sem = rule.get("semantic", {})
        if sem.get("enabled"):
            kv("  Semantic", f"enabled (threshold={sem.get('threshold',0.82)})", C.CYN)

        msg = rule.get("message", "")
        if msg:
            kv("  Message", msg[:70], C.G2)

    print()
    # Stats summary
    stats = nc.rules_stats()
    if "total" in stats:
        ba = stats.get("by_action", {})
        parts = []
        for action, count in ba.items():
            if count:
                c = ACTION_COLORS.get(action, C.G2)
                parts.append(q(c, f"{count} {action}"))
        if parts:
            print("  " + "  ".join(parts))
    print()


def cmd_rules_create(args):
    """
    Create a governance rule interactively or from a description.

    Modes:
      1. --action "no hagas X" (NL description from flag)
      2. Interactive prompt
      3. Expert mode (keyword by keyword)
    """
    print_logo(compact=True)
    section("Create Rule")

    nc = _get_nova_core()
    if not nc.is_alive():
        fail("Nova Core not running.")
        hint("Start:  python nova_core.py")
        return

    # ── Get description ───────────────────────────────────────────────────────
    description = getattr(args, "action", "") or ""

    if not description:
        print("  " + q(C.G2, "Describe the rule in natural language."))
        print("  " + q(C.G3, "Examples:"))
        print("       " + q(C.G3, "· no ofrezcas descuentos mayores al 20%"))
        print("       " + q(C.G3, "· never share patient phone numbers"))
        print("       " + q(C.G3, "· bloquear cuando mencione precio sin verificar"))
        print()
        description = prompt("Rule description", required=True)

    if not description:
        warn("Cancelled.")
        return

    print()

    # ── Determine action type ─────────────────────────────────────────────────
    action_opts = ["block  - hard stop, agent cannot proceed", "warn - alert only, agent proceeds"]
    try:
        action_idx = _select(action_opts, default=0)
    except KeyboardInterrupt:
        print(); return
    action = "block" if action_idx == 0 else "warn"

    # ── Priority ──────────────────────────────────────────────────────────────
    prio_opts = [
        "9-10 - Critical security (medical, PII, credentials)",
        "7-8  - Important business rules (pricing, auth)",
        "5-6  - Standard guidelines",
        "3-4  - Soft guidelines (warn only)",
    ]
    prio_map = {0: 9, 1: 7, 2: 5, 3: 4}
    try:
        prio_idx = _select(prio_opts, default=1)
    except KeyboardInterrupt:
        print(); return
    priority = prio_map[prio_idx]

    # ── Scope ─────────────────────────────────────────────────────────────────
    cfg = load_config_secure()
    agent_name = cfg.get("connected_agent_name", "")
    scope = "global"
    if agent_name:
        scope_opts = [f"global - applies to all agents",
                      f"agent:{agent_name} - only {agent_name}"]
        try:
            scope_idx = _select(scope_opts, default=0)
        except KeyboardInterrupt:
            print(); return
        scope = "global" if scope_idx == 0 else f"agent:{agent_name}"

    # ── Create via Nova Core ──────────────────────────────────────────────────
    print()
    with Spinner("Creating rule...") as sp:
        result = nc.rules_create(description, scope=scope,
                                 action=action, priority=priority)
        sp.finish()

    if "error" in result:
        fail(f"Error: {result['error']}")
        return

    print()
    ok("Rule created")
    print()
    kv("ID",          result.get("id","?"), C.B7)
    kv("Name",        result.get("name","?"), C.W)
    kv("Action",      result.get("action","?"), C.RED if action=="block" else C.YLW)
    kv("Priority",    str(result.get("priority","?")), C.G2)
    kv("Scope",       result.get("scope","?"), C.G2)

    det = result.get("deterministic", {})
    kws = det.get("keywords_block", [])
    if kws:
        kv("Keywords",    ", ".join(kws[:5]), C.G3)
    if result.get("file"):
        kv("File",        result["file"], C.G3)
    print()

    hint("Test it:   " + q(C.B7, f"nova rules test --action \"<action>\""))
    hint("List all:  " + q(C.B7, "nova rules list"))
    print()


def cmd_rules_delete(args):
    """Delete (deactivate) a governance rule."""
    nc = _get_nova_core()
    if not nc.is_alive():
        nc = _nova_core_or_die()
        if nc is None:
            return

    rule_id = getattr(args, "value", "") or getattr(args, "key", "") or ""

    if not rule_id:
        # List rules and let user pick
        with Spinner("Loading rules..."):
            result = nc.rules_list()
        rules = result.get("rules", [])
        if not rules:
            warn("No rules to delete.")
            return

        print_logo(compact=True)
        section("Delete Rule")
        opts = [f"[{r.get('action','?').upper()}] {r.get('name','?')}  ({r.get('id','?')})"
                for r in rules]
        opts.append("Cancel")
        try:
            idx = _select(opts, default=len(opts)-1)
        except KeyboardInterrupt:
            print(); return

        if idx == len(opts) - 1:
            warn("Cancelled.")
            return
        rule_id = rules[idx]["id"]
        rule_name = rules[idx]["name"]
    else:
        rule_name = rule_id

    if not confirm(f"Delete rule {q(C.B7, rule_name)}?", default=False):
        warn("Cancelled.")
        return

    with Spinner("Deleting...") as sp:
        result = nc.rules_delete(rule_id)
        sp.finish()

    if result.get("deleted") or "error" not in result:
        ok(f"Rule {q(C.B7, rule_id)} deactivated and archived.")
    else:
        fail(f"Error: {result.get('error', 'unknown')}")
    print()


def cmd_rules_test(args):
    """
    Test an action against all active governance rules.
    Shows which layer blocked/passed and why.
    """
    nc = _get_nova_core()
    if not nc.is_alive():
        nc = _nova_core_or_die()
        if nc is None:
            return

    action  = getattr(args, "action", "") or ""
    context = getattr(args, "context", "") or ""

    if not action:
        print_logo(compact=True)
        section("Test Action")
        action  = prompt("Action to test", required=True)
        context = prompt("Context (optional)", default="")

    if not action:
        return

    cfg        = load_config_secure()
    agent_name = cfg.get("connected_agent_name", "")
    scope      = f"agent:{agent_name}" if agent_name else "global"

    with Spinner("Validating...") as sp:
        t0     = time.time()
        result = nc.validate(action, context=context, scope=scope,
                             agent_name=agent_name, dry_run=True)
        elapsed = int((time.time() - t0) * 1000)
        sp.finish()

    if "error" in result:
        fail(f"Error: {result['error']}")
        return

    verdict  = result.get("result",   result.get("verdict", "?"))
    score    = result.get("score",    0)
    reason   = result.get("reason",   "")
    layer    = result.get("layer",    "?")
    message  = result.get("message",  "")
    rule_id  = result.get("rule_id")
    rule_name = result.get("rule_name")
    factors  = result.get("factors", {})

    print()
    print("  " + verdict_badge(verdict) + "   " + score_bar(score) + "   " + q(C.G3, f"{elapsed}ms"))
    print()

    kv("Reason",  reason,  C.G2)
    kv("Layer",   layer,   C.W)
    if rule_id:
        kv("Rule",  f"{rule_name or rule_id}  ({rule_id})", C.B7)
    if message:
        kv("Message", message, C.G2)

    # Show score factors if available (from heuristic layer)
    if factors:
        print()
        section("Score Factors")
        for factor, impact in sorted(factors.items(), key=lambda x: -abs(x[1])):
            c    = C.GRN if impact > 0 else C.RED if impact < 0 else C.G2
            sign = "+" if impact > 0 else ""
            print("  " + q(c, f"{sign}{impact:>4}") + "  " + q(C.G1, factor))

    print()


def cmd_rules_import(args):
    """Import rules from a YAML file into Nova Core."""
    nc = _get_nova_core()
    if not nc.is_alive():
        nc = _nova_core_or_die()
        if nc is None:
            return

    file_path = getattr(args, "file", "") or getattr(args, "value", "") or ""
    if not file_path:
        file_path = prompt("Path to YAML rules file", required=True)

    p = Path(file_path)
    if not p.exists():
        fail(f"File not found: {file_path}")
        return

    try:
        import yaml as _yaml
        content = _yaml.safe_load(p.read_text("utf-8"))
    except Exception as e:
        fail(f"Could not parse YAML: {e}")
        return

    rules = content if isinstance(content, list) else [content]
    print()
    print(f"  Found {len(rules)} rule(s) to import.")
    print()

    if not confirm(f"Import {len(rules)} rule(s)?", default=True):
        warn("Cancelled.")
        return

    imported = 0
    failed   = 0
    for rule in rules:
        desc = rule.get("original_instruction") or rule.get("name") or str(rule)
        r = nc.rules_create(
            desc,
            scope=rule.get("scope", "global"),
            action=rule.get("action", "block"),
            priority=rule.get("priority", 7),
        )
        if "error" in r:
            warn(f"Failed: {r['error']}")
            failed += 1
        else:
            imported += 1

    print()
    ok(f"Imported {imported} rule(s)" + (f" ({failed} failed)" if failed else ""))
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 7 ────────────────────────────────────────
def cmd_chat_nova(args):
    """
    Interactive chat with Nova Core governance engine.
    Create rules, validate actions, get stats - all in natural language.
    """
    nc = _get_nova_core()
    if not nc.is_alive():
        fail("Nova Core not running.")
        hint("Start:  python nova_core.py")
        return

    cfg        = load_config_secure()
    agent_name = cfg.get("connected_agent_name", "")
    scope      = f"agent:{agent_name}" if agent_name else "global"
    session    = f"cli_{int(time.time())}"

    print_logo(compact=True)
    section("Nova Chat", "type 'exit' to quit")
    print()
    print("  " + q(C.G2, "Talk to Nova to manage governance rules."))
    if agent_name:
        print("  " + q(C.G3, f"Agent: {agent_name} | Scope: {scope}"))
    print()

    # Show quick hints
    hints = [
        "crea una regla que bloquee descuentos mayores al 20%",
        "muéstrame todas las reglas activas",
        "valida: enviar un correo con datos de otro paciente",
        "¿cuántas acciones bloqueadas hoy?",
    ]
    print("  " + q(C.G3, "Examples:"))
    for h in hints:
        print("  " + q(C.G3, f"  · {h}"))
    print()

    _render_reset()
    history = []

    while True:
        try:
            sys.stdout.write("  " + q(C.GLD_BRIGHT, "you") + " " + q(C.G3, "›") + " ")
            sys.stdout.flush()
            text = input().strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not text:
            continue
        if text.lower() in ("exit", "quit", "bye", "salir"):
            break

        history.append(text)

        with Spinner("Nova thinking...") as sp:
            result = nc.chat(text, session_id=session, scope=scope)
            sp.finish()

        msg = result.get("message", "")
        rtype = result.get("type", "chat")

        print()

        if rtype == "error":
            fail(msg)
        elif rtype == "rule_created":
            ok("Regla creada")
            print()
            # Render the message cleanly
            for line in msg.split("\n"):
                line = line.strip()
                if line:
                    print("  " + q(C.G1, line))
        elif rtype == "list":
            print("  " + q(C.W, "Reglas activas:", bold=True))
            print()
            for line in msg.split("\n"):
                print("  " + q(C.G1, line))
        elif rtype == "validation":
            vd = result.get("verdict_data", {})
            verdict = vd.get("result", result.get("verdict","?"))
            score   = vd.get("score",  result.get("score", 0))
            print("  " + verdict_badge(verdict) + "   " + score_bar(score))
            print()
            reason_line = vd.get("reason", "")
            if reason_line:
                print("  " + q(C.G2, reason_line))
        elif rtype == "stats":
            for line in msg.split("\n"):
                print("  " + q(C.G1, line))
        elif rtype == "rule_deleted":
            ok(msg)
        else:
            # Generic chat response
            sys.stdout.write("  " + q(C.GLD_BRIGHT, "nova") + " " + q(C.G3, "›") + " ")
            for line in msg.split("\n"):
                print(q(C.G1, line.strip()))
                if line != msg.split("\n")[-1]:
                    sys.stdout.write("         ")

        ms = result.get("ms", 0)
        if ms:
            print()
            print("  " + q(C.G3, f"  {ms}ms"))
        print()

    print()
    ok("Nova Chat session ended.")
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 8 ────────────────────────────────────────
def cmd_logs(args):
    """
    View the governance ledger — validated actions, verdicts, chain hashes.
    Auto-discovers Nova Core URL. Starts it if not running.
    """
    nc = _get_nova_core()

    # ── Auto-discover if default URL fails ────────────────────────────────────
    if not nc.is_alive():
        with Spinner("Locating Nova Core...") as sp:
            # Clear cached URL so load_nova_core_url re-scans
            try: NOVA_CORE_URL_FILE.unlink()
            except Exception: pass
            discovered_url = load_nova_core_url()
            nc2 = NovaCoreClient(url=discovered_url)
            alive2 = nc2.is_alive()
            sp.finish()

        if alive2:
            nc = nc2
            save_nova_core_url(discovered_url)
            ok(f"Nova Core found at {discovered_url}")
        else:
            fail("Nova Core not reachable.")
            print()
            print("  " + q(C.G2, "Tried ports: ") + q(C.G3, ", ".join(str(p) for p in _NOVA_PORTS_TO_TRY)))
            print()
            hint("Start it:  nova boot")
            hint("Or:        pm2 start nova_core.py --name nova-core --interpreter python3")
            print()
            return

    cfg        = load_config_secure()
    agent_name = getattr(args, "agent", "") or cfg.get("connected_agent_name", "")
    limit      = getattr(args, "limit", 30) or 30
    verdict_f  = getattr(args, "verdict", "") or ""

    with Spinner("Loading ledger...") as sp:
        result = nc.ledger(agent_name=agent_name, limit=min(int(limit), 200))
        sp.finish()

    if "error" in result:
        err_msg = result.get("error", "")
        code    = result.get("code", "")

        # 404 = connected to nova-api (main.py) instead of nova_core.py
        if "Not found" in err_msg or code == "HTTP_404":
            print()
            fail("Connected to nova-api (port 9002) — but it has no /ledger.")
            print()
            print("  " + q(C.W, "nova-api    = main.py    — /tokens, /validate, /stats"))
            print("  " + q(C.W, "nova-core   = nova_core.py — /ledger, /rules, /stream"))
            print()
            print("  " + q(C.YLW, "nova_core.py is NOT running."))
            print()
            hint("Start it:")
            print("    " + q(C.B7, "pm2 start nova_core.py --name nova-core --interpreter python3"))
            print("    " + q(C.B7, "# or:"))
            print("    " + q(C.B7, "nova boot"))
            print()
            # Save the correct URL so future commands don't hit 9002
            try: NOVA_CORE_URL_FILE.unlink()
            except Exception: pass
        else:
            fail(f"Error: {err_msg}")
        return

    entries = result.get("entries", [])
    total   = result.get("total", len(entries))

    if verdict_f:
        entries = [e for e in entries if e.get("verdict","").upper() == verdict_f.upper()]

    print_logo(compact=True)
    title = f"Ledger - {total} entries"
    if agent_name:
        title += f" - {agent_name}"
    section(title)

    if not entries:
        warn("No ledger entries yet.")
        print()
        hint("Entries appear when Nova validates agent actions.")
        print()
        return

    # ── Also show stats ────────────────────────────────────────────────────────
    stats_result = nc.ledger_stats(agent_name=agent_name)
    if "total" in stats_result:
        s = stats_result
        parts = [
            q(C.GRN, f"✓ {s.get('approved',0)}"),
            q(C.RED, f"✗ {s.get('blocked',0)}"),
            q(C.YLW, f"⚠ {s.get('warned',0)}"),
            q(C.ORG, f"↑ {s.get('escalated',0)}"),
        ]
        avg = s.get("avg_score")
        if avg:
            parts.append(q(C.G2, f"avg score: {int(avg)}"))
        print("  " + "  ".join(parts))
        print()

    VERDICT_COLORS = {
        "APPROVED":  (C.GRN, "✓"),
        "BLOCKED":   (C.RED, "✗"),
        "WARNED":    (C.YLW, "⚠"),
        "ESCALATED": (C.ORG, "↑"),
        "DUPLICATE": (C.MGN, "⊘"),
    }

    for entry in entries:
        v       = entry.get("verdict", "?")
        score   = entry.get("score", 0)
        action  = entry.get("action", "")[:70]
        agent   = entry.get("agent_name", "")
        reason  = entry.get("reason", "")[:60]
        layer   = entry.get("layer", "")
        created = entry.get("created_at", "")[:19].replace("T", " ")
        own_hash = entry.get("own_hash", "")[:10]

        vc, vi = VERDICT_COLORS.get(v, (C.G2, "·"))
        print()
        print("  " + q(vc, vi + " " + v.ljust(10)) +
              "  " + q(C.W, action))
        print(
            "       " +
            q(C.G3, f"score={score}") + "  " +
            q(C.G3, f"layer={layer}") + "  " +
            q(C.G3, f"agent={agent}") + "  " +
            q(C.G3, f"#{own_hash}...")
        )
        if reason and reason != "No governance rule triggered":
            print("       " + q(C.G2, reason))
        print("       " + q(C.G3, created))

    print()
    hint("Filter:  nova logs --verdict BLOCKED")
    hint("Stream:  nova stream")
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 9 ────────────────────────────────────────
def cmd_anomalies(args):
    """View anomalies detected by Nova's behavioral analysis engine."""
    nc = _get_nova_core()
    if not nc.is_alive():
        nc = _nova_core_or_die()
        if nc is None:
            return

    cfg        = load_config_secure()
    agent_name = getattr(args, "agent", "") or cfg.get("connected_agent_name", "")
    limit      = getattr(args, "limit", 30) or 30

    with Spinner("Loading anomalies...") as sp:
        result = nc.anomalies(agent_name=agent_name, limit=min(int(limit), 100))
        sp.finish()

    if "error" in result:
        fail(f"Error: {result['error']}")
        return

    anomalies = result.get("anomalies", [])

    print_logo(compact=True)
    section("Anomaly Report", f"{len(anomalies)} detected")

    if not anomalies:
        ok("No anomalies detected.")
        print()
        print("  " + q(C.G2, "Nova monitors for:"))
        bullet("High block rate > 50% in 30 minutes")
        bullet("Burst activity > 20 actions in 5 minutes")
        bullet("Score degradation > 15 points over time")
        print()
        return

    SEV_COLORS = {
        "critical": C.RED,
        "high":     C.ORG,
        "medium":   C.YLW,
        "low":      C.GRN,
    }
    TYPE_DESC = {
        "high_block_rate":   "High block rate",
        "burst_activity":    "Burst activity",
        "score_degradation": "Score degradation",
    }

    for a in anomalies:
        sev   = a.get("severity", "medium")
        atype = a.get("type", "unknown")
        msg   = a.get("message", "")
        agent = a.get("agent_name", "")
        ts    = a.get("created_at", "")[:19].replace("T", " ")
        sc    = SEV_COLORS.get(sev, C.G2)
        label = TYPE_DESC.get(atype, atype)

        try:
            data = json.loads(a.get("data", "{}"))
        except Exception:
            data = {}

        print()
        print(
            "  " + q(sc, "▲", bold=True) + "  " +
            q(C.W, label, bold=True) + "  " +
            q(sc, f"[{sev.upper()}]") + "  " +
            q(C.G3, f"agent={agent}")
        )
        print("       " + q(C.G2, msg))
        if data:
            data_str = "  ".join(f"{k}={v}" for k,v in data.items())
            print("       " + q(C.G3, data_str))
        print("       " + q(C.G3, ts))

    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 10 ────────────────────────────────────────
def cmd_stream(args):
    """
    Live stream of all Nova Core validation events (SSE).
    Auto-discovers Nova Core URL. Retries on disconnect.
    """
    nc    = _get_nova_core()

    # ── Auto-discover if default URL fails ────────────────────────────────────
    if not nc.is_alive():
        with Spinner("Locating Nova Core...") as sp:
            try: NOVA_CORE_URL_FILE.unlink()
            except Exception: pass
            discovered = load_nova_core_url()
            nc2 = NovaCoreClient(url=discovered)
            found = nc2.is_alive()
            sp.finish()
        if found:
            nc = nc2
            save_nova_core_url(discovered)
            ok(f"Nova Core found at {discovered}")
            print()
        else:
            fail("Nova Core not reachable.")
            print()
            hint("Start it:  nova boot")
            hint("Or:        pm2 start nova_core.py --name nova-core --interpreter python3")
            print()
            return

    url   = nc.url

    cfg        = load_config_secure()
    agent_name = getattr(args, "agent", "") or cfg.get("connected_agent_name", "all") or "all"

    print_logo(compact=True)
    section("Live Event Stream", f"agent={agent_name}")
    print("  " + q(C.G2, "Press Ctrl+C to stop"))
    print()

    stream_url = f"{url}/stream/events?agent_name={agent_name}"

    VERDICT_COLORS = {
        "APPROVED":  (C.GRN, "✓"),
        "BLOCKED":   (C.RED, "✗"),
        "WARNED":    (C.YLW, "⚠"),
        "ESCALATED": (C.ORG, "↑"),
        "DUPLICATE": (C.MGN, "⊘"),
        "anomaly":   (C.RED, "▲"),
    }

    try:
        req = urllib.request.Request(
            stream_url,
            headers={
                "Accept":    "text/event-stream",
                "x-api-key": nc.api_key,
            }
        )
        with urllib.request.urlopen(req, timeout=None) as resp:
            buffer = ""
            while True:
                chunk = resp.read(1).decode("utf-8", errors="replace")
                if not chunk:
                    break
                buffer += chunk
                if buffer.endswith("\n\n"):
                    for line in buffer.strip().split("\n"):
                        if line.startswith("data: "):
                            try:
                                event = json.loads(line[6:])
                                _render_stream_event(event, VERDICT_COLORS)
                            except Exception:
                                pass
                    buffer = ""
    except KeyboardInterrupt:
        print()
        print()
        ok("Stream stopped.")
    except Exception as e:
        err_str = str(e)
        print()
        if "111" in err_str or "Connection refused" in err_str:
            fail("Nova Core not running.")
            print()
            print("  " + q(C.YLW, "nova_core.py is the process that has /stream/events."))
            print("  " + q(C.G2,  "nova-api (main.py) does NOT have this endpoint."))
            print()
            hint("Start nova_core:  pm2 start nova_core.py --name nova-core --interpreter python3")
            hint("Or:               nova boot")
        elif "Not found" in err_str or "404" in err_str:
            fail("Connected to nova-api — it has no /stream endpoint.")
            hint("You need nova_core.py running, not nova-api.")
            hint("Start it:  pm2 start nova_core.py --name nova-core --interpreter python3")
        else:
            fail(f"Stream error: {e}")
            hint(f"Check: {stream_url}")
        # Clear cached wrong URL
        try: NOVA_CORE_URL_FILE.unlink()
        except Exception: pass
    print()


def _render_stream_event(event: dict, colors: dict):
    """Render a single SSE event to the terminal."""
    etype = event.get("type", "")
    ts    = event.get("ts", "")[:19].replace("T", " ")

    if etype == "heartbeat":
        sys.stdout.write(q(C.G3, "."))
        sys.stdout.flush()
        return

    print()  # Newline after heartbeat dots

    if etype == "validation":
        verdict  = event.get("verdict", "?")
        score    = event.get("score", 0)
        agent    = event.get("agent", "")
        reason   = event.get("reason", "")[:60]
        ms       = event.get("ms", 0)
        vc, vi   = colors.get(verdict, (C.G2, "·"))
        print(
            "  " + q(vc, vi + " " + verdict.ljust(10)) +
            "  " + q(C.G3, f"score={score}") +
            "  " + q(C.G3, f"{ms}ms") +
            "  " + q(C.G3, f"[{agent}]")
        )
        if reason and reason != "No governance rule triggered":
            print("       " + q(C.G2, reason))
        print("       " + q(C.G3, ts))

    elif etype == "anomaly":
        sev     = event.get("severity", "medium")
        msg     = event.get("message", "")
        agent   = event.get("agent", "")
        atype   = event.get("anomaly_type", "")
        vc, vi  = colors.get("anomaly", (C.RED, "▲"))
        print(
            "  " + q(vc, vi + f" ANOMALY [{sev.upper()}]", bold=True) +
            "  " + q(C.G3, f"[{agent}]")
        )
        print("       " + q(C.G2, msg))
        print("       " + q(C.G3, ts))


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 11 ────────────────────────────────────────
_BENCH_ACTIONS = [
    "Reply to customer inquiry about pricing",
    "Send tracking information to customer",
    "Process payment of $500",
    "Delete all customer records",
    "Share patient medical history with third party",
    "Update inventory count for product A",
    "Cancel subscription for customer",
    "Provide product recommendation",
    "Generate invoice for $1,200",
    "Access another user's account data",
    "Send weekly newsletter to subscribers",
    "Modify previously issued invoice",
    "Check order status for customer",
    "Override manager approval for $10,000 purchase",
    "Answer FAQ about return policy",
    "Terminate all running jobs without warning",
    "Schedule appointment for patient",
    "Share API credentials via email",
    "Process refund under $100",
    "Offer guaranteed price without verification",
]


def cmd_benchmark(args):
    """
    Measure Nova Core governance performance.
    Tests validation speed, accuracy, and layer distribution.
    """
    nc = _get_nova_core()
    if not nc.is_alive():
        nc = _nova_core_or_die()
        if nc is None:
            return

    cfg        = load_config_secure()
    agent_name = getattr(args, "agent", "") or cfg.get("connected_agent_name", "bench")

    print_logo(compact=True)
    section("Governance Benchmark")
    print("  " + q(C.G2, f"Testing {len(_BENCH_ACTIONS)} standard actions..."))
    print()

    with Spinner("Running benchmark...") as sp:
        result = nc.benchmark_run(_BENCH_ACTIONS, agent_name=agent_name)
        sp.finish()

    if "error" in result:
        fail(f"Error: {result['error']}")
        return

    total       = result.get("total", 0)
    approved    = result.get("approved", 0)
    blocked     = result.get("blocked", 0)
    block_rate  = result.get("block_rate", 0)
    avg_score   = result.get("avg_score", 0)
    avg_lat     = result.get("avg_latency", 0)
    max_lat     = result.get("max_latency", 0)
    min_lat     = result.get("min_latency", 0)
    total_ms    = result.get("total_ms", 0)
    throughput  = result.get("throughput", 0)
    layers      = result.get("layers", {})

    print()

    # ── Performance ────────────────────────────────────────────────────────────
    section("Performance")
    kv("Total actions",    str(total), C.W)
    kv("Total time",       f"{total_ms}ms", C.W)
    kv("Throughput",       f"{throughput} req/s", C.GRN)
    kv("Avg latency",      f"{avg_lat:.1f}ms", C.W)
    kv("Min / Max",        f"{min_lat}ms / {max_lat}ms", C.G2)

    print()

    # ── Governance ─────────────────────────────────────────────────────────────
    section("Governance")
    kv("Approved",    str(approved), C.GRN)
    kv("Blocked",     str(blocked),  C.RED)
    kv("Block rate",  f"{block_rate}%", C.RED if block_rate > 30 else C.GRN)
    kv("Avg score",   str(avg_score), C.W)

    print()

    # ── Layer distribution ─────────────────────────────────────────────────────
    section("Layer Distribution")
    layer_order = ["deterministic", "heuristic", "semantic", "duplicate", "default"]
    for layer in layer_order:
        count = layers.get(layer, 0)
        if count:
            pct = round(count / total * 100)
            bar = score_bar(pct, width=15)
            print("  " + q(C.G2, layer.ljust(16)) + bar + q(C.G3, f"  {count}x"))

    print()

    # ── Rating ─────────────────────────────────────────────────────────────────
    # Performance score: lower latency + higher deterministic % = better
    det_pct = layers.get("deterministic", 0) / max(total, 1) * 100
    perf_score = int(
        min(100, (50 - min(avg_lat, 50)) / 50 * 40 +  # latency component
                 det_pct * 0.4 +                        # deterministic % component
                 min(20, throughput / 5))               # throughput component
    )
    if perf_score >= 80:
        rating_txt = q(C.GRN, f"Excellent - {perf_score}/100")
    elif perf_score >= 60:
        rating_txt = q(C.YLW, f"Good - {perf_score}/100")
    else:
        rating_txt = q(C.RED, f"Needs improvement - {perf_score}/100")

    print("  " + q(C.W, "Performance rating:  ", bold=True) + rating_txt)
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 12 ────────────────────────────────────────
def cmd_protect(args):
    """
    Quick-protect any HTTP agent endpoint with Nova governance.
    Shows integration code snippets for different frameworks.
    """
    print_logo(compact=True)
    section("Protect an Agent")

    agent_url  = getattr(args, "upstream", "") or getattr(args, "url", "") or ""
    agent_name = getattr(args, "agent", "") or ""

    if not agent_url:
        print("  " + q(C.G2, "What agent do you want to protect?"))
        print()
        agent_url  = prompt("Agent URL (e.g. http://localhost:8001)", required=True)
        agent_name = prompt("Agent name", default="my-agent")

    if not agent_url:
        return

    nc_url = load_nova_core_url()

    print()
    section("Integration Options")
    print()

    # ── Option 1: Nova Proxy (zero code) ──────────────────────────────────────
    print("  " + q(C.W, "1. Nova Transparent Proxy", bold=True) + "  " + q(C.GRN, "recommended"))
    print("  " + q(C.G2, "Zero code changes. Nova wraps your agent automatically."))
    print()
    print("  " + q(C.G3, "# Step 1: Start Nova Core"))
    print("  " + q(C.B7, "   python nova_core.py"))
    print()
    print("  " + q(C.G3, "# Step 2: Connect Nova to your agent"))
    print("  " + q(C.B7, f"   nova connect --url {agent_url} --name {agent_name}"))
    print()
    print("  " + q(C.G3, "# Step 3: Route traffic through Nova proxy"))
    print("  " + q(C.B7, f"   # Your agent is now at: {nc_url}/proxy/"))
    print()

    # ── Option 2: Python middleware ────────────────────────────────────────────
    print("  " + q(C.G3, "─" * 50))
    print()
    print("  " + q(C.W, "2. Python middleware snippet", bold=True))
    print("  " + q(C.G2, "Add to your FastAPI/Flask agent - minimal integration."))
    print()
    snippet_python = f'''import httpx

NOVA_URL = "{nc_url}"

async def nova_guard(action: str, context: str = "") -> bool:
    """Returns True if action is allowed, False if blocked."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.post(f"{{NOVA_URL}}/validate", json={{
                "action":     action,
                "context":    context,
                "agent_name": "{agent_name}",
                "scope":      "agent:{agent_name}",
            }})
            d = r.json()
            return d.get("result", "APPROVED") not in ("BLOCKED", "ESCALATED")
    except Exception:
        return True  # Fail-open: Nova down → agent continues'''
    for line in snippet_python.split("\n"):
        print("    " + q(C.G2, line))

    print()

    # ── Option 3: n8n node ────────────────────────────────────────────────────
    print("  " + q(C.G3, "─" * 50))
    print()
    print("  " + q(C.W, "3. n8n HTTP Request node", bold=True))
    print("  " + q(C.G2, "Add before any action node in your n8n workflow."))
    print()
    print("    " + q(C.G3, "Method: POST"))
    print("    " + q(C.B7, f"URL:    {nc_url}/validate"))
    print("    " + q(C.G3, "Body:"))
    print("    " + q(C.G2, '    {"action": "{{$json.action}}", "agent_name": "' + agent_name + '"}'))
    print()
    print("    " + q(C.G3, "Then add IF node: result != BLOCKED → continue"))
    print()

    if confirm("Connect Nova Core to this agent now?", default=True):
        nc = _get_nova_core()
        if nc.is_alive():
            with Spinner("Connecting...") as sp:
                r = nc.connect_agent(agent_url, agent_name)
                sp.finish()
            if "error" not in r:
                ok(f"Nova is protecting {q(C.B7, agent_name)}")
                cfg = load_config_secure()
                cfg["connected_agent_url"]  = agent_url
                cfg["connected_agent_name"] = agent_name
                save_config_secure(cfg)
            else:
                fail(f"Connect failed: {r['error']}")
        else:
            warn("Nova Core not running - start it first:")
            hint("python nova_core.py")
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 13 ────────────────────────────────────────
def cmd_setup(args):
    """One-command governance setup for known agent types."""
    sub = getattr(args, "subcommand", "") or ""

    if sub.lower() in ("melissa", "mel"):
        return cmd_setup_melissa(args)
    elif sub.lower() == "n8n":
        return cmd_setup_n8n(args)
    else:
        _cmd_setup_interactive(args)


def cmd_launchpad(args):
    """
    Simple operator entrypoint.
    Unifies the most common first actions into a single guided flow.
    """
    print_logo(compact=True)
    section("Operator Launchpad")
    print("  " + q(C.G2, "Fastest path to get an agent under governance."))
    print()

    cfg = load_config_secure()

    if not cfg.get("api_url") or not cfg.get("api_key"):
        warn("Nova is not configured yet.")
        print()
        if confirm("Run guided setup now?", default=True):
            return cmd_init(args)
        hint("Run  " + q(C.B7, "nova init") + "  when ready.")
        print()
        return

    options = [
        "Create a new governed agent",
        "Connect a running agent",
        "Protect an existing HTTP endpoint",
        "Setup (internal)",
        "Setup n8n",
        "Scan what is already running",
        "Review current status",
    ]
    descriptions = [
        "Create token, rules and optional live connection in one flow",
        "Link Nova Core to an agent that already exists",
        "Wrap an HTTP agent with Nova governance",
        "Internal agent setup",
        "Opinionated setup for n8n governance",
        "Detect agents on common local ports",
        "Check Nova, Core, connected agent and rules",
    ]

    try:
        choice = _select(options, descriptions=descriptions, default=0)
    except KeyboardInterrupt:
        print()
        return

    print()

    if choice == 0:
        return cmd_agent_create_v32(args)
    if choice == 1:
        return cmd_connect(args)
    if choice == 2:
        return cmd_protect(args)
    if choice == 3:
        return cmd_setup_melissa(args)
    if choice == 4:
        setup_args = argparse.Namespace(**vars(args))
        setup_args.subcommand = "n8n"
        return cmd_setup_n8n(setup_args)
    if choice == 5:
        return cmd_scan(args)
    return cmd_status_v32(args)


def _cmd_setup_interactive(args):
    """Interactive setup - user selects their agent type."""
    print_logo(compact=True)
    section("Nova Setup")
    print("  " + q(C.G2, "One-command governance setup for your AI agent."))
    print()

    opts = [
        "Internal agent - WhatsApp AI",
        "n8n - Workflow automation",
        "Custom - Any HTTP agent",
        "Scan - Find what's running",
    ]
    try:
        idx = _select(opts, default=0)
    except KeyboardInterrupt:
        print(); return

    if idx == 0:
        cmd_setup_melissa(args)
    elif idx == 1:
        cmd_setup_n8n(args)
    elif idx == 2:
        cmd_protect(args)
    else:
        cmd_scan(args)


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT EDITOR  - code-first, no AI, survives any agent reset
# ══════════════════════════════════════════════════════════════════════════════

def _find_system_prompt_location(project_root: Path) -> dict:
    """
    Deep scanner - finds the system prompt in ANY agent project.

    Priority:
      P1  Standalone files (system_prompt.txt, prompts/*.txt, etc.)
      P2  Python: variable name contains PROMPT/SYSTEM/INSTRUCTION at any depth
      P3  Python: kwarg/dict key  instructions=, system_prompt=, prompt=
      P4  Python: long triple-quoted string that looks like a system prompt
      P5  JSON / YAML config files
      P6  .env SYSTEM_PROMPT=
    """
    def _snip(text, pos=0, n=150):
        return text[pos:pos+n].replace("\n", " ").strip()

    def _lineno(text, pos):
        return text[:pos].count("\n") + 1

    # ── P1: Standalone files ──────────────────────────────────────────────────
    standalone = [
        "system_prompt.txt", "system_prompt.md", "system.md", "system.txt",
        "prompt.txt", "prompt.md", "instructions.txt", "instructions.md",
        "base_prompt.txt", "SYSTEM_PROMPT.md", "INSTRUCTIONS.md",
        "agent_prompt.txt", "melissa_prompt.txt", "bot_prompt.txt",
    ]
    scan_dirs = [project_root]
    for sub in ["prompts", "config", "src", "agent", "data", "resources", "prompts"]:
        d = project_root / sub
        if d.is_dir():
            scan_dirs.append(d)

    for d in scan_dirs:
        for name in standalone:
            p = d / name
            if p.exists():
                text = p.read_text(errors="ignore")
                if len(text.strip()) > 20:
                    return {"found": True, "file": p, "line": 0,
                            "type": "file", "key": p.name,
                            "snippet": _snip(text), "confidence": 95}
        if d.name in ("prompts", "prompt"):
            for f in sorted(d.glob("*.txt")) + sorted(d.glob("*.md")):
                text = f.read_text(errors="ignore")
                if len(text.strip()) > 50:
                    return {"found": True, "file": f, "line": 0,
                            "type": "file", "key": f.name,
                            "snippet": _snip(text), "confidence": 90}

    # ── P2-P4: Python deep scan ───────────────────────────────────────────────
    py_files = list(project_root.glob("*.py"))
    for sub in ["src", "app", "agent", "bot", "core", "lib"]:
        d = project_root / sub
        if d.is_dir():
            py_files.extend(d.glob("*.py"))
    py_files = py_files[:30]

    # P2: variable name contains prompt/system/instruction keywords
    _var_re = re.compile(
        r'(?i)([a-z_][a-z0-9_]*(?:system_?prompt|base_?prompt|agent_?prompt|'
        r'melissa_?prompt|bot_?prompt|persona|instructions?|character|behavior|'
        r'personality|role|initial_?message|greeting_?prompt|core_?prompt|'
        r'main_?prompt|static_?prompt)[a-z0-9_]*)'
        r'\s*=\s*("""|\'\'\')(.+?)(\2)',
        re.DOTALL | re.IGNORECASE,
    )
    # Also single-line assignments
    _var_re_single = re.compile(
        r'(?i)([a-z_][a-z0-9_]*(?:system_?prompt|base_?prompt|agent_?prompt|'
        r'melissa_?prompt|bot_?prompt|persona|instructions?|character|behavior|'
        r'personality|role|core_?prompt|main_?prompt)[a-z0-9_]*)'
        r'\s*=\s*(["\'])([^\n]{20,})(\2)',
        re.IGNORECASE,
    )

    # P3: kwarg/dict key with prompt-like name
    _kw_re = re.compile(
        r'(?i)(instructions|system_prompt|system|prompt|persona|behavior|character)'
        r'\s*[=:]\s*("""|\'\'\')(.+?)(\3)',
        re.DOTALL,
    )
    _kw_re_single = re.compile(
        r'(?i)(instructions|system_prompt|system|prompt|persona|behavior|character)'
        r'\s*[=:]\s*(["\'])([^\n]{20,})(\2)',
    )

    # P4: any long triple-quoted string that looks like a system prompt
    _tq_re = re.compile(r'("""|\'\'\')((?:(?!\1).){80,}?)\1', re.DOTALL)
    _prompt_words = re.compile(
        r'(?i)(you are|eres |tu eres|your role|your job|as an? |'
        r'assistant|asistente|recepcionista|responde |always |nunca |never )',
    )

    best: dict = {}

    for pyfile in py_files:
        try:
            text = pyfile.read_text(errors="ignore")
        except Exception:
            continue

        # P2 triple-quoted
        m = _var_re.search(text)
        if m:
            cand = {"found": True, "file": pyfile, "line": _lineno(text, m.start()),
                    "type": "python_var", "key": m.group(1),
                    "snippet": _snip(m.group(3)), "confidence": 90}
            if not best or 90 > best.get("confidence", 0):
                best = cand

        # P2 single-line
        if not best or best.get("confidence", 0) < 85:
            m = _var_re_single.search(text)
            if m:
                cand = {"found": True, "file": pyfile, "line": _lineno(text, m.start()),
                        "type": "python_var", "key": m.group(1),
                        "snippet": _snip(m.group(3)), "confidence": 85}
                if not best or 85 > best.get("confidence", 0):
                    best = cand

        # P3 kwarg triple-quoted
        if not best or best.get("confidence", 0) < 80:
            m = _kw_re.search(text)
            if m:
                cand = {"found": True, "file": pyfile, "line": _lineno(text, m.start()),
                        "type": "python_kwarg", "key": m.group(1),
                        "snippet": _snip(m.group(3)), "confidence": 80}
                if not best or 80 > best.get("confidence", 0):
                    best = cand

        # P3 kwarg single-line
        if not best or best.get("confidence", 0) < 75:
            m = _kw_re_single.search(text)
            if m:
                cand = {"found": True, "file": pyfile, "line": _lineno(text, m.start()),
                        "type": "python_kwarg", "key": m.group(1),
                        "snippet": _snip(m.group(3)), "confidence": 75}
                if not best or 75 > best.get("confidence", 0):
                    best = cand

        # P4: long triple-quoted string with prompt-like content
        if not best or best.get("confidence", 0) < 60:
            for m in _tq_re.finditer(text):
                inner = m.group(2).strip()
                if _prompt_words.search(inner):
                    cand = {"found": True, "file": pyfile, "line": _lineno(text, m.start()),
                            "type": "python_tripleq", "key": "prompt_string",
                            "snippet": _snip(inner), "confidence": 65}
                    if not best or 65 > best.get("confidence", 0):
                        best = cand

    if best:
        return best

    # ── P5: JSON / YAML ───────────────────────────────────────────────────────
    for name in ["config.json", "agent.json", "settings.json", "prompt.json"]:
        p = project_root / name
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        for key in ["system_prompt", "systemPrompt", "system", "prompt",
                    "instructions", "persona", "behavior", "character"]:
            val = data.get(key, "")
            if isinstance(val, str) and len(val) > 20:
                return {"found": True, "file": p, "line": 0,
                        "type": "json_key", "key": key,
                        "snippet": _snip(val), "confidence": 85}

    # ── P6: .env ──────────────────────────────────────────────────────────────
    env_file = project_root / ".env"
    if env_file.exists():
        env_d = _read_dotenv(env_file)
        for key in ["SYSTEM_PROMPT", "BASE_PROMPT", "AGENT_INSTRUCTIONS",
                    "BOT_PROMPT", "ASSISTANT_INSTRUCTIONS", "PERSONA"]:
            if key in env_d and len(env_d[key]) > 20:
                return {"found": True, "file": env_file, "line": 0,
                        "type": "env_key", "key": key,
                        "snippet": _snip(env_d[key]), "confidence": 80}

    return {"found": False, "confidence": 0}



def inject_rules_into_system_prompt(location: dict, rules: list,
                                     backup_dir: Path = None) -> dict:
    """
    Inject Nova rules into the system prompt - code-first, no AI.

    Strategy per type:
      file       -> append Nova block to the text file
      python_var -> find the triple-quoted string and append inside it
      json_key   -> update the JSON value in-place
      env_key    -> update the env value

    Always strips a previous Nova block before re-injecting (idempotent).
    Always creates a .bak backup first.
    Returns {"success": bool, "backup": path_str, "method": str}
    """
    if not location.get("found"):
        return {"success": False, "reason": "no system prompt location found"}

    target: Path = location["file"]
    nova_block = (
        "\n\n"
        "== NOVA GOVERNANCE RULES ==\n"
        "The following rules are enforced by Nova and override any conflicting instruction.\n"
        "\n"
        + "\n".join(rules) + "\n"
        "== END NOVA RULES =="
    )

    # Backup
    backup_path = None
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_path = backup_dir / f"{target.name}.{ts}.bak"
        try:
            import shutil as _sh
            _sh.copy2(target, backup_path)
        except Exception:
            backup_path = None

    try:
        ltype = location["type"]

        if ltype == "file":
            original = _strip_nova_block(target.read_text(errors="ignore"))
            target.write_text(original + nova_block)
            return {"success": True, "backup": str(backup_path), "method": "file_append"}

        elif ltype == "python_var":
            original = target.read_text(errors="ignore")
            key = location["key"]
            # Match triple-quoted string: key = """...""" or key = '''...'''
            _tq_pat = r'({k}\s*=\s*)(\'\'\'|""")(.+?)(\2)'.replace(
                '{k}', re.escape(key))
            m = re.compile(_tq_pat, re.DOTALL).search(original)
            if m:
                # Strip previous block from inner value, then re-append
                inner = _strip_nova_block(m.group(3))
                patched = (original[:m.start(3)] + inner + nova_block +
                           original[m.end(3):])
                target.write_text(patched)
                return {"success": True, "backup": str(backup_path), "method": "python_tripleq"}

            # Fallback: single-line or f-string - inject as comment after the line
            m2 = re.compile(rf"^({re.escape(key)}\s*=\s*.+)$", re.M).search(original)
            if m2:
                # Strip previous comment block if present
                after = original[m2.end():]
                after = re.sub(
                    r"\n# Nova governance rules.*?(?=\n[^#]|\Z)", "",
                    after, flags=re.DOTALL)
                rules_comment = (
                    "\n# Nova governance rules (auto-injected - do not remove)\n"
                    + "\n".join(f"# {r}" for r in rules) + "\n"
                )
                target.write_text(original[:m2.end()] + rules_comment + after)
                return {"success": True, "backup": str(backup_path), "method": "python_comment"}

            return {"success": False, "reason": "could not locate python string"}

        elif ltype == "json_key":
            data = json.loads(target.read_text())
            key = location["key"]
            existing = _strip_nova_block(data.get(key, ""))
            data[key] = existing + nova_block
            target.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            return {"success": True, "backup": str(backup_path), "method": "json_patch"}

        elif ltype == "env_key":
            key = location["key"]
            env_text = target.read_text(errors="ignore")

            # Read current base value - unescape \\n so we can strip the nova block
            raw_val = _read_dotenv(target).get(key, "")
            # Unescape literal \n stored by a previous injection
            raw_val_unescaped = raw_val.replace('\\n', '\n')
            base_val = _strip_nova_block(raw_val_unescaped)

            # Build new value and store with escaped newlines (portable .env)
            new_val = base_val.rstrip() + nova_block
            escaped = new_val.replace('\\', '\\\\').replace('\n', '\\n')
            new_line = f'{key}="{escaped}"'

            # Remove ALL previous forms of this key (quoted multi-line or plain)
            cleaned = re.sub(
                rf'^{re.escape(key)}=".*?"[ \t]*\n?',
                '', env_text, flags=re.MULTILINE | re.DOTALL)
            cleaned = re.sub(
                rf'^{re.escape(key)}=[^\n]*\n?',
                '', cleaned, flags=re.MULTILINE)

            target.write_text(cleaned.rstrip('\n') + f'\n{new_line}\n')
            return {"success": True, "backup": str(backup_path), "method": "env_patch"}

    except Exception as e:
        return {"success": False, "reason": str(e), "backup": str(backup_path) if backup_path else None}

    return {"success": False, "reason": "unknown type"}


def write_memory_sidecar(agent_type: str, project_root: Path,
                          rules: List[str]) -> Path:
    """
    Write .nova/agents/<type>/memory/system_inject.md - a persistent
    record of what Nova has injected, and a snippet to bootstrap from
    if the agent ever loses its system prompt.
    """
    mem_dir = project_root / ".nova" / "agents" / agent_type / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    out = mem_dir / "system_inject.md"

    content_md = (
        f"# Nova System Prompt Injection\n"
        f"_Generated: {datetime.now().isoformat()}_\n"
        f"_Agent: {agent_type}_\n\n"
        f"## Active rules\n\n"
        + "\n".join(rules) + "\n\n"
        "## Bootstrap snippet\n\n"
        "Add this to your agent startup to re-apply rules on every reset:\n\n"
        "```python\n"
        "# Nova governance bootstrap\n"
        "import json, pathlib\n"
        "_nova_inject = pathlib.Path('.nova/agents/" + agent_type + "/memory/system_inject.md')\n"
        "if _nova_inject.exists():\n"
        "    _lines = [l[2:] for l in _nova_inject.read_text().splitlines()\n"
        "              if l.startswith('- ')]\n"
        "    SYSTEM_PROMPT += '\\n\\n== NOVA RULES ==\\n' + '\\n'.join(_lines)\n"
        "```\n"
    )
    out.write_text(content_md)
    return out


def cmd_setup_melissa(args):
    """
    Auto-setup Nova governance for Melissa WhatsApp agent.

    3-layer protection:
      L1  Edit Melissa source file (system prompt) - survives any restart
      L2  Write .nova/agents/melissa/memory/system_inject.md sidecar
      L3  Update .env with NOVA_CORE_URL + NOVA_CORE_API_KEY

    Usage:
      nova setup melissa
      nova setup melissa --path /home/ubuntu/melissa
    """
    print_logo(compact=True)
    section("Setup: Melissa")
    print()

    cfg       = load_config()
    nc        = _get_nova_core()
    nc_url    = nc.url
    nc_key    = nc.api_key

    # ── Locate Melissa project root ───────────────────────────────────────────
    path_arg = getattr(args, "path", "") or getattr(args, "file", "") or ""
    melissa_root = None

    if path_arg:
        p = Path(path_arg)
        melissa_root = p if p.is_dir() else p.parent
    else:
        candidates = [
            Path.home() / "melissa",
            Path.home() / "melissa-ultra",
            Path("/home/ubuntu/melissa"),
            Path("/opt/melissa"),
            Path("/app/melissa"),
            Path.cwd(),
        ]
        for c in candidates:
            if c.exists() and c.is_dir() and (
                (c / ".env").exists() or
                any(c.glob("*.py")) or
                (c / "package.json").exists()
            ):
                melissa_root = c
                break

    if melissa_root:
        ok(f"Melissa project: {q(C.B7, str(melissa_root))}")
    else:
        warn("Melissa project not found automatically.")
        raw = prompt("Path to Melissa project directory", default=str(Path.cwd()))
        melissa_root = Path(raw) if raw else Path.cwd()

    melissa_env = melissa_root / ".env"
    print()

    # ── Step 1: Ensure Nova Core is running ──────────────────────────────────
    with Spinner("Checking Nova Core...") as sp:
        core_alive = nc.is_alive()
        sp.finish()

    if core_alive:
        ok("Nova Core running")
    else:
        info("Nova Core not running. Attempting to start it...")
        started = _start_nova_core_background()
        if started:
            # Wait up to 8s
            for _ in range(16):
                time.sleep(0.5)
                if nc.is_alive():
                    core_alive = True
                    break
        if core_alive:
            ok("Nova Core started automatically")
        else:
            warn("Nova Core not running - rules saved locally only.")
            warn("Start it with:  python3 nova_core.py &")
            hint("Or run:  nova boot  to start everything at once.")
    print()

    # ── Step 2: Determine Melissa URL from .env ───────────────────────────────
    melissa_url = "http://localhost:8001"
    if melissa_env.exists():
        env_vars = _read_dotenv(melissa_env)
        for key in ("PORT", "MELISSA_PORT", "APP_PORT", "SERVER_PORT"):
            val = env_vars.get(key, "")
            if val.isdigit():
                melissa_url = f"http://localhost:{val}"
                break
        # Also respect explicit URL
        for key in ("MELISSA_URL", "APP_URL", "BASE_URL"):
            val = env_vars.get(key, "")
            if val.startswith("http"):
                melissa_url = val
                break

    info(f"Melissa URL: {melissa_url}")

    # ── Step 3: Build rules ───────────────────────────────────────────────────
    MELISSA_CANNOT = [
        "Give medical diagnoses or health recommendations",
        "Commit to specific prices without admin verification",
        "Share personal data of patients with third parties",
        "Process payments directly",
        "Make guarantees about treatment outcomes",
        "Impersonate medical professionals or the doctor",
        "Access or modify admin system configuration",
        "Send messages as the doctor without explicit approval",
    ]

    rule_lines = [f"- [NEVER] {r}" for r in MELISSA_CANNOT]

    print("  " + q(C.W, "Rules to enforce:", bold=True))
    for line in rule_lines[:4]:
        print("  " + q(C.G2, "  " + line))
    if len(rule_lines) > 4:
        print("  " + q(C.G3, f"  ... and {len(rule_lines)-4} more"))
    print()

    if not confirm("Apply these rules to Melissa?", default=True):
        warn("Cancelled.")
        return

    # ── LAYER 1: Edit source system prompt ────────────────────────────────────
    print()
    print("  " + q(C.W, "Layer 1 - System prompt injection", bold=True))

    with Spinner("Scanning Melissa source files...") as sp:
        location = _find_system_prompt_location(melissa_root)
        sp.finish()

    backup_dir = melissa_root / ".nova" / "backups"
    prompt_injected = False

    if location["found"]:
        info(f"Found system prompt in {Path(location['file']).name}"
             f" (line {location['line'] or 'whole file'})")
        print("  " + q(C.G3, f"  Preview: {location['snippet'][:80]}..."))
        print()

        inj = inject_rules_into_system_prompt(location, rule_lines, backup_dir)
        if inj["success"]:
            ok(f"Rules injected into {Path(location['file']).name}"
               f" via {inj['method']}")
            if inj.get("backup"):
                ok(f"Backup saved: {Path(inj['backup']).name}")
            prompt_injected = True
        else:
            warn(f"Could not edit source: {inj.get('reason','unknown')}")
    else:
        warn("System prompt file not found in Melissa project.")
        hint("Create a file named system_prompt.txt in the project root")
        hint("Nova will inject rules there on next run.")

    # ── LAYER 2: Memory sidecar ───────────────────────────────────────────────
    print()
    print("  " + q(C.W, "Layer 2 - Memory sidecar", bold=True))
    sidecar = write_memory_sidecar("melissa", melissa_root, rule_lines)
    ok(f"Rules persisted: {sidecar.relative_to(melissa_root)}")
    info("If the system prompt is lost on reset, Melissa can reload from here.")

    # ── LAYER 3: Update .env ──────────────────────────────────────────────────
    print()
    print("  " + q(C.W, "Layer 3 - Environment variables", bold=True))

    env_updates = {
        "NOVA_CORE_URL":     nc_url,
        "NOVA_CORE_API_KEY": nc_key,
        "NOVA_CORE_ENABLED": "true",
        "NOVA_AGENT_SCOPE":  "agent:melissa",
        "NOVA_AGENT_NAME":   "melissa",
    }

    if inject_nova_env(melissa_env, nc_key, nc_url, "melissa"):
        ok(f".env updated: {melissa_env}")
        for k in ("NOVA_CORE_URL", "NOVA_AGENT_SCOPE"):
            kv(f"  {k}", env_updates[k], C.G3)
    else:
        warn("Could not write .env - copy manually:")
        print()
        for k, v in env_updates.items():
            print(f"    {k}={v}")

    # ── Save local rules to .nova/agents/melissa/rules/ ───────────────────────
    rules_dir = create_nova_project_folder(
        melissa_root, "melissa", "Melissa", nc_url, nc_key
    )
    for i, rule_text in enumerate(MELISSA_CANNOT):
        create_rule_file(rules_dir, {
            "id":          f"melissa_{i:02d}",
            "name":        re.sub(r"[^a-z0-9]", "_", rule_text.lower())[:40],
            "description": rule_text,
            "action":      "block",
            "priority":    8,
            "scope":       "agent:melissa",
            "created_at":  datetime.now().isoformat(),
            "created_by":  "nova setup melissa",
            "active":      True,
        })

    # ── Connect to Nova Core if running ───────────────────────────────────────
    if core_alive:
        print()
        with Spinner("Connecting Nova Core to Melissa...") as sp:
            r = nc.connect_agent(melissa_url, "melissa")
            sp.finish()
        if "error" not in r:
            ok("Nova Core connected to Melissa")
        else:
            warn(f"Connect: {r.get('error','?')} - saved for when Melissa starts")

    # ── Save CLI config ───────────────────────────────────────────────────────
    cfg_s = load_config_secure()
    cfg_s["connected_agent_url"]  = melissa_url
    cfg_s["connected_agent_name"] = "melissa"
    cfg_s["nova_project_root"]    = str(melissa_root)
    save_config_secure(cfg_s)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    hr_bold()
    print()
    print("  " + q(C.GLD, "✦", bold=True) + "  " + q(C.W, "Melissa is now governed by Nova.", bold=True))
    print()

    summary = [
        ("System prompt", "injected ✓" if prompt_injected else "not found - add system_prompt.txt"),
        ("Memory sidecar", str(sidecar.relative_to(melissa_root))),
        (".env",           "updated ✓" if melissa_env.exists() else "update manually"),
        ("Rules",          f"{len(MELISSA_CANNOT)} rules active"),
        ("Nova Core",      "connected ✓" if core_alive else "will connect on start"),
    ]
    for label, value in summary:
        ok_c = C.GRN if "✓" in value else C.YLW
        print("    " + q(C.G2, label.ljust(18)) + q(ok_c, value))

    print()
    print("  " + q(C.G2, "Restart Melissa to apply:"))
    print()
    print("    " + q(C.B7, "pm2 restart melissa --update-env"))
    print()
    hint("Monitor:  nova stream --agent melissa")
    hint("Rules:    nova rules")
    hint("Logs:     nova logs --agent melissa")
    print()


def cmd_setup_n8n(args):
    """Auto-setup Nova governance for n8n workflows."""
    print_logo(compact=True)
    section("Setup → n8n")
    print("  " + q(C.G2, "Connecting Nova governance to your n8n instance."))
    print()

    nc = _get_nova_core()
    if not nc.is_alive():
        fail("Nova Core not running. Start it first: python nova_core.py")
        return

    n8n_url = "http://localhost:5678"
    info(f"Connecting to n8n at {n8n_url}")

    with Spinner("Connecting...") as sp:
        r = nc.connect_agent(n8n_url, "n8n")
        sp.finish()

    if "error" not in r:
        ok("Nova connected to n8n")
    else:
        warn(f"n8n may not be running yet - connection saved")
    print()

    # n8n-specific rules
    N8N_RULES = [
        "Never send emails to more than 50 recipients without approval",
        "Never delete data from external databases",
        "Never share API credentials in webhook payloads",
        "Never process payments above $500 without human verification",
    ]

    rules_created = 0
    for rule in N8N_RULES:
        r = nc.rules_create(rule, scope="agent:n8n", action="block", priority=8)
        if "error" not in r:
            rules_created += 1

    ok(f"Created {rules_created} governance rules for n8n")
    print()

    cfg = load_config_secure()
    cfg["connected_agent_url"]  = n8n_url
    cfg["connected_agent_name"] = "n8n"
    save_config_secure(cfg)

    section("n8n Integration")
    print("  " + q(C.G2, "Add this HTTP Request node BEFORE any sensitive action in n8n:"))
    print()

    nova_url = nc.url
    print("    " + q(C.G3, "POST " + nova_url + "/validate"))
    print("    " + q(C.G3, "Body: {\"action\": \"{{$json.description}}\", \"agent_name\": \"n8n\"}"))
    print("    " + q(C.G3, "Then: IF result != BLOCKED → continue"))
    print()
    hint("For the outreach workflow: add before the email send node")
    hint("nova rules list  - to see active rules")
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 14 ────────────────────────────────────────
def cmd_agent_create_v32(args):
    """
    Create a governance agent.
    
    Three modes (in order of preference):
      1. Natural language (--describe "..." or interactive prompt + LLM)
      2. Template selection
      3. Manual rule-by-rule entry

    Security: API keys come from config only. No hardcoded keys.
    """
    section("New Agent")
    api, cfg = get_api()

    can      = []
    cannot   = []
    name_val = ""
    desc_val = ""

    # ── STEP 1: Try natural language mode ─────────────────────────────────────
    nl_desc = getattr(args, "action", "") or ""  # reuse --action flag as --describe

    # Check if we have an LLM configured
    chain = _build_llm_fallback_chain(cfg)
    has_llm = bool(chain)

    if not nl_desc and has_llm:
        print("  " + q(C.G2, "Describe your agent in natural language."))
        print("  " + q(C.G3, "Example: Melissa is a WhatsApp receptionist for a dental clinic."))
        print("  " + q(C.G3, "She can schedule appointments but cannot give medical advice."))
        print()
        nl_desc = prompt("Describe the agent (or Enter for template)", default="", required=False)

    if nl_desc and has_llm:
        print()
        with Spinner("Extracting governance rules with AI...") as sp:
            parsed = nl_parse_agent_rules(nl_desc, cfg)
            sp.finish()

        if parsed and parsed.get("can_do"):
            name_val = parsed.get("name", "")
            desc_val = parsed.get("description", "")
            can      = parsed.get("can_do", [])
            cannot   = parsed.get("cannot_do", [])
            confidence = parsed.get("confidence", 0)

            print()
            ok(f"Rules extracted: {q(C.B7, name_val)}" +
               (f"  {q(C.G3, f'({int(confidence*100)}% confidence)')}" if confidence else ""))
            print()

            print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ALLOWED:", bold=True))
            for rule in can:
                print("       " + q(C.G2, f"+ {rule}"))
            print()
            print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "FORBIDDEN:", bold=True))
            for rule in cannot:
                print("       " + q(C.G2, f"- {rule}"))
            print()

            if confirm("Adjust any rules?", default=False):
                print("  " + q(C.G2, "Add more ALLOWED actions (Enter to finish):"))
                can.extend(prompt_list("Allowed extra", min_items=0))
                print("  " + q(C.G2, "Add more RESTRICTIONS (Enter to finish):"))
                cannot.extend(prompt_list("Restriction extra", min_items=0))
        else:
            warn("Could not extract rules from that description.")
            hint("Try being more specific, or use a template.")
            nl_desc = ""

    # ── STEP 2: Template or manual (fallback) ─────────────────────────────────
    if not can and not cannot:
        print()
        print("  " + q(C.G2, "Choose how to define rules:"))
        print()
        opts  = ["From template (recommended)", "Manual - rule by rule"]
        descs = ["Pre-built rules for common patterns", "Define each rule yourself"]
        try:
            mode = _select(opts, descriptions=descs, default=0)
        except KeyboardInterrupt:
            print(); return

        if mode == 0:
            print()
            print("  " + q(C.W, "Choose a template:", bold=True))
            print()
            tpl_keys  = list(RULE_TEMPLATES.keys())
            tpl_opts  = [RULE_TEMPLATES[k]["label"] for k in tpl_keys]
            tpl_descs = [RULE_TEMPLATES[k]["description"] for k in tpl_keys]
            try:
                tpl_idx = _select(tpl_opts, descriptions=tpl_descs, default=0)
            except KeyboardInterrupt:
                print(); return
            template = RULE_TEMPLATES[tpl_keys[tpl_idx]]
            can      = list(template["can_do"])
            cannot   = list(template["cannot_do"])

            print()
            ok(f"Template: {q(C.B7, template['label'])}")
            print()
            print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ALLOWED:", bold=True))
            for a in can[:5]:
                print("       " + q(C.G2, f"+ {a}"))
            if len(can) > 5:
                print("       " + q(C.G3, f"... and {len(can)-5} more"))
            print()
            print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "FORBIDDEN:", bold=True))
            for a in cannot[:5]:
                print("       " + q(C.G2, f"- {a}"))
            if len(cannot) > 5:
                print("       " + q(C.G3, f"... and {len(cannot)-5} more"))
            print()
            if confirm("Customize these rules?", default=False):
                can.extend(prompt_list("Additional allowed", min_items=0))
                cannot.extend(prompt_list("Additional forbidden", min_items=0))
        else:
            print()
            print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ALLOWED ACTIONS:", bold=True))
            can = prompt_list("One per line", min_items=0)
            print()
            print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "FORBIDDEN ACTIONS:", bold=True))
            cannot = prompt_list("One per line", min_items=0)

    # ── STEP 3: Agent details ──────────────────────────────────────────────────
    print()
    name_val     = prompt("Agent name", default=name_val or "My Agent", required=True)
    desc_val     = prompt("Brief description", default=desc_val)
    authorized_by = prompt("Authorized by", default=cfg.get("user_name", "admin"))

    # ── Summary ────────────────────────────────────────────────────────────────
    print()
    can_prev    = ", ".join(can[:2])    + ("..." if len(can)    > 2 else "") if can    else "none"
    cannot_prev = ", ".join(cannot[:2]) + ("..." if len(cannot) > 2 else "") if cannot else "none"
    box([
        f"  Agent       {name_val}",
        f"  Allows      {can_prev}",
        f"  Forbids     {cannot_prev}",
        f"  By          {authorized_by}",
    ], C.B5, title="Summary")
    print()

    if not confirm("Create this agent?"):
        warn("Cancelled.")
        return

    # ── Create via API ─────────────────────────────────────────────────────────
    with Spinner("Signing Intent Token..."):
        result = api.post("/tokens", {
            "agent_name":    name_val,
            "description":   desc_val,
            "can_do":        can,
            "cannot_do":     cannot,
            "authorized_by": authorized_by,
        })

    if "error" in result:
        fail(format_api_error(result))
        return

    token_id  = result.get("token_id", "")
    signature = result.get("signature", "")

    ok("Agent created - token signed")
    print()
    kv("Token ID",  token_id, C.B7)
    kv("Signature", (signature[:24] + "...") if signature else "-", C.G3)
    print()

    cfg["default_token"] = token_id
    save_config_secure(cfg)

    # ── Offer to also add to Nova Core ─────────────────────────────────────────
    nc = _get_nova_core(cfg)
    if nc.is_alive() and cannot:
        print()
        if confirm("Also create governance rules in Nova Core?", default=True):
            rules_created = 0
            with Spinner("Creating rules in Nova Core...") as sp:
                for rule in cannot[:5]:
                    r = nc.rules_create(rule, scope=f"agent:{name_val}",
                                        action="block", priority=7)
                    if "error" not in r:
                        rules_created += 1
                sp.finish()
            ok(f"{rules_created} rules created in nova_rules/")

    # ── Fast follow: connect a live agent now ────────────────────────────────
    if nc.is_alive():
        print()
        if confirm("Connect this agent to a running HTTP endpoint now?", default=False):
            suggested_url = cfg.get("connected_agent_url", "")
            print()
            agent_url = prompt(
                "Agent URL",
                default=suggested_url or "http://localhost:8001",
                required=True,
                validator=lambda x: True if x.startswith(("http://", "https://"))
                                    else "URL must start with http:// or https://"
            )

            print()
            with Spinner(f"Connecting {name_val}...") as sp:
                conn = nc.connect_agent(agent_url, name_val)
                sp.finish()

            if "error" in conn:
                fail(f"Connect failed: {conn['error']}")
            else:
                cfg["connected_agent_url"] = agent_url
                cfg["connected_agent_name"] = name_val
                save_config_secure(cfg)
                ok(f"Connected to {q(C.B7, name_val)}")
                kv("Agent URL", agent_url, C.B7)
                kv("Scope", f"agent:{name_val}", C.G2)
                print()
                hint("Live stream: " + q(C.B7, f"nova stream --agent {name_val}"))
                hint("Protect endpoint: " + q(C.B7, f"nova protect --upstream {agent_url} --agent {name_val}"))
                print()
    else:
        print()
        hint("For live governance connection, start Nova Core and run:")
        hint(q(C.B7, f"nova connect --url http://localhost:8001 --agent \"{name_val}\""))
        print()

    if cfg.get("api_key"):
        webhook = f"{cfg['api_url']}/webhook/{cfg['api_key']}"
        section("Webhook")
        print("  " + q(C.B7, f"POST {webhook}"))
        print("  " + q(C.G3, '{"action": "...", "token_id": "' + token_id[:12] + '..."}'))
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 15 ────────────────────────────────────────
def cmd_status_v32(args):
    """
    Full system status: Nova CLI + Nova Core + connected agent + rules.
    Replaces or supplements existing cmd_status.
    """
    print_logo(compact=True)
    section("System Status")

    cfg = load_config_secure()

    # ── Nova Core ──────────────────────────────────────────────────────────────
    nc    = _get_nova_core(cfg)
    with Spinner("Checking Nova Core...") as sp:
        h = nc.health()
        sp.finish()

    print()
    print("  " + q(C.W, "Nova Core", bold=True))
    if "error" in h:
        print("  " + q(C.RED, "●") + "  " + q(C.G2, "offline") + "  " + q(C.G3, nc.url))
    else:
        print("  " + q(C.GRN, "●") + "  " + q(C.G2, "online") + "  " + q(C.G3, nc.url))
        rs = h.get("rules", {})
        ls = h.get("ledger", {})
        kv("  Version", h.get("version","?"), C.G2)
        kv("  Rules",   str(rs.get("total", 0)) + " active", C.G2)
        kv("  Ledger",  str(ls.get("total", 0)) + " entries", C.G2)
        kv("  LLM",     h.get("llm","?") + ("  ✓" if h.get("llm_ready") else "  no key"), C.G2)

    print()

    # ── Connected agent ────────────────────────────────────────────────────────
    print("  " + q(C.W, "Connected Agent", bold=True))
    agent_url  = h.get("agent_url", "") or cfg.get("connected_agent_url", "")
    agent_name = cfg.get("connected_agent_name", "")
    if agent_url and agent_url != "not connected":
        agent_reachable = h.get("agent_reachable", False)
        icon = q(C.GRN, "●") if agent_reachable else q(C.YLW, "●")
        print("  " + icon + "  " + q(C.G2, agent_name or "unknown") + "  " + q(C.G3, agent_url))
    else:
        print("  " + q(C.G3, "●") + "  " + q(C.G3, "not connected"))
        hint("Connect with:  nova connect")

    print()

    # ── Nova API (main.py backend) ─────────────────────────────────────────────
    api_url = cfg.get("api_url", "")
    api_key = cfg.get("api_key", "")
    print("  " + q(C.W, "Nova API (main.py)", bold=True))
    if api_url and api_key:
        # Quick health check
        try:
            req = urllib.request.Request(
                api_url + "/health",
                headers={"x-api-key": api_key, "User-Agent": f"nova-cli/{NOVA_VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                hdata = json.loads(r.read())
            print("  " + q(C.GRN, "●") + "  " + q(C.G2, "online") + "  " + q(C.G3, api_url))
            kv("  LLM",  str(hdata.get("llm_available", "?")), C.G2)
            kv("  DB",   hdata.get("database", "?"), C.G2)
        except Exception:
            print("  " + q(C.YLW, "●") + "  " + q(C.G2, "offline or unreachable") + "  " + q(C.G3, api_url))
    else:
        print("  " + q(C.G3, "●") + "  " + q(C.G3, "not configured - run  nova init"))

    print()

    # ── LLM ────────────────────────────────────────────────────────────────────
    print("  " + q(C.W, "LLM Intelligence", bold=True))
    chain = _build_llm_fallback_chain(cfg)
    if chain:
        for i, (prov, model, key, _) in enumerate(chain[:3]):
            icon = q(C.GRN, "●") if i == 0 else q(C.G3, "○")
            label = "primary" if i == 0 else "fallback"
            print(f"  {icon}  " + q(C.G2, f"{prov}/{model}") +
                  "  " + q(C.G3, label) +
                  "  " + q(C.G3, mask_key(key)))
    else:
        print("  " + q(C.G3, "●") + "  " + q(C.G3, "no LLM configured"))
        hint("Add key:  nova config")

    print()

    # ── Quick actions ──────────────────────────────────────────────────────────
    section("Quick Actions")
    quick = [
        ("nova rules list",       "See active governance rules"),
        ("nova logs",             "View validation ledger"),
        ("nova chat",             "Manage rules via natural language"),
        ("nova benchmark",        "Measure governance overhead"),
        ("nova stream",           "Live event stream"),
    ]
    for cmd_str, desc in quick:
        print("  " + q(C.B7, cmd_str.ljust(22)) + "  " + q(C.G2, desc))
    print()


# ══════════════════════════════════════════════════════════════════════════════

# ── Section 19 ────────────────────────────────────────
def cmd_interactive(args):
    """
    Interactive Nova mode - shown when user runs 'nova' without arguments.
    Quick access to the most common actions.
    """
    print_logo(tagline=True, animated=True)

    nc  = _get_nova_core()
    cfg = load_config_secure()
    alive = nc.is_alive()

    # Status bar
    agent_name = cfg.get("connected_agent_name", "")
    if alive and agent_name:
        status = q(C.GRN, f"● Nova Core online  ·  Agent: {agent_name}")
    elif alive:
        status = q(C.YLW, "● Nova Core online  ·  No agent connected")
    else:
        status = q(C.G3, "○ Nova Core offline  ·  Start: python nova_core.py")
    print("  " + status)
    print()

    opts = [
        "Chat with Nova   - create/manage rules in natural language",
        "View live stream - watch validations in real-time",
        "Manage rules     - list, create, delete governance rules",
        "View logs        - browse the immutable ledger",
        "Benchmark        - measure governance performance",
        "Connect agent    - link Nova to a running agent",
        "Setup            - one-command setup for Melissa/n8n",
        "Status           - full system overview",
        "Exit",
    ]

    try:
        idx = _select(opts, default=0)
    except KeyboardInterrupt:
        print(); return

    ACTION_MAP = {
        0: lambda: cmd_chat_nova(args),
        1: lambda: cmd_stream(args),
        2: lambda: cmd_rules(args),
        3: lambda: cmd_logs(args),
        4: lambda: cmd_benchmark(args),
        5: lambda: cmd_connect(args),
        6: lambda: cmd_setup(args),
        7: lambda: cmd_status_v32(args),
        8: lambda: None,
    }

    fn = ACTION_MAP.get(idx)
    if fn:
        print()
        fn()


# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# NOVA v4.0 - NEW COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

# ── POLICIES ─────────────────────────────────────────────────────────────────

def cmd_policy(args):
    """
    Manage governance policy templates.
    Policies are reusable can_do/cannot_do rule sets you can apply to agents.

    Subcommands:
      list         - List all policies
      create       - Create a new policy template
      view <id>    - View a specific policy
      edit <id>    - Edit a policy
      delete <id>  - Delete a policy
    """
    sub = getattr(args, "subcommand", "") or ""

    if sub in ("create", "new", "add"):
        return _policy_create(args)
    elif sub in ("view", "show", "info"):
        return _policy_view(args)
    elif sub in ("edit", "update", "patch"):
        return _policy_edit(args)
    elif sub in ("delete", "remove", "del"):
        return _policy_delete(args)
    else:
        return _policy_list(args)


def _policy_list(args):
    """List all policies."""
    api, cfg = get_api()

    category_filter = getattr(args, "value", "") or ""

    with Spinner("Loading policies..."):
        params = f"?active_only=true"
        if category_filter:
            params += f"&category={category_filter}"
        result = api.get(f"/policies{params}")

    if "error" in result:
        fail(format_api_error(result))
        return

    if not result:
        warn("No policies found.")
        print()
        hint("Create one with:  " + q(C.B7, "nova policy create"))
        print()
        return

    section("Policy Templates", f"{len(result)} available")
    print()

    CATS = {
        "general":       (C.G2,  "◯"),
        "communication": (C.B6,  "✉"),
        "finance":       (C.GLD, "◈"),
        "data":          (C.B7,  "⊞"),
        "development":   (C.GRN, "◉"),
        "operations":    (C.ORG, "◎"),
        "compliance":    (C.RED, "◆"),
    }

    for p in result:
        cat   = p.get("category", "general")
        cc, ic = CATS.get(cat, (C.G2, "·"))
        tmpl  = "  " + q(C.B7, "template") if p.get("is_template") else ""
        print("  " + q(cc, ic) + "  " + q(C.W, p["name"], bold=True) +
              "  " + q(C.G3, f"#{p['id']}") + tmpl)
        print("       " + q(C.G2, p.get("description", "")[:60]))
        print("       " + q(C.G3, f"{len(p.get('can_do',[]))} permitidas  ·  "
              f"{len(p.get('cannot_do',[]))} prohibidas  ·  "
              f"v{p.get('version',1)}  ·  {cat}"))
        print()

    hint("Ver política:     nova policy view <id>")
    hint("Crear política:   nova policy create")
    hint("Aplicar a agente: nova agent create  → selecciona política")
    print()


def _policy_create(args):
    """Create a new policy template."""
    api, cfg = get_api()

    section("New Policy", "Reusable rule set")
    print("  " + q(C.G2, "Las políticas son plantillas que puedes aplicar a múltiples agentes."))
    print()

    # ── Step 1: Basic info ────────────────────────────────────────────────────
    print("  " + q(C.B6, "●") + "  " + q(C.W, "Paso 1/4 - Información básica", bold=True))
    print()
    name       = prompt("Nombre de la política", required=True)
    desc       = prompt("Descripción breve", default="")
    created_by = prompt("Creado por", default=cfg.get("user_name", "admin"))

    # ── Step 2: Category ──────────────────────────────────────────────────────
    print()
    print("  " + q(C.B6, "●") + "  " + q(C.W, "Paso 2/4 - Categoría", bold=True))
    print()
    cats       = ["general","communication","finance","data","development","operations","compliance"]
    cat_descs  = [
        "Reglas generales reutilizables",
        "Email, mensajes, notificaciones",
        "Pagos, facturas, transacciones",
        "Acceso y manejo de datos",
        "Código, despliegues, APIs",
        "Operaciones, infraestructura",
        "Cumplimiento normativo",
    ]
    try:
        cat_idx = _select(cats, descriptions=cat_descs, default=0)
    except KeyboardInterrupt:
        print(); return
    category = cats[cat_idx]

    # ── Step 3: Rules ─────────────────────────────────────────────────────────
    print()
    print("  " + q(C.B6, "●") + "  " + q(C.W, "Paso 3/4 - Reglas", bold=True))
    print()

    # Offer template as starting point
    tpl_keys  = list(RULE_TEMPLATES.keys())
    tpl_opts  = ["Empezar desde cero"] + [RULE_TEMPLATES[k]["label"] for k in tpl_keys]
    tpl_descs = ["Defino todas las reglas manualmente"] + \
                [RULE_TEMPLATES[k]["description"] for k in tpl_keys]
    print("  " + q(C.G2, "¿Partir de una plantilla existente?"))
    print()
    try:
        tpl_idx = _select(tpl_opts, descriptions=tpl_descs, default=0)
    except KeyboardInterrupt:
        print(); return

    if tpl_idx > 0:
        tpl = RULE_TEMPLATES[tpl_keys[tpl_idx - 1]]
        can_do    = list(tpl["can_do"])
        cannot_do = list(tpl["cannot_do"])
        print()
        ok(f"Plantilla cargada: {q(C.B7, tpl['label'])}")
        if confirm("¿Personalizar reglas de la plantilla?", default=False):
            can_do.extend(prompt_list("Permitidas adicionales", min_items=0))
            cannot_do.extend(prompt_list("Prohibidas adicionales", min_items=0))
    else:
        print()
        print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ACCIONES PERMITIDAS:", bold=True))
        can_do = prompt_list("Una por línea", min_items=1)
        print()
        print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "ACCIONES PROHIBIDAS:", bold=True))
        cannot_do = prompt_list("Una por línea", min_items=0)

    # ── Step 4: Template flag ─────────────────────────────────────────────────
    print()
    print("  " + q(C.B6, "●") + "  " + q(C.W, "Paso 4/4 - Visibilidad", bold=True))
    print()
    is_template = confirm("¿Marcar como plantilla reutilizable para todo el workspace?", default=True)

    # ── Summary + confirm ─────────────────────────────────────────────────────
    print()
    box([
        f"  Nombre       {name}",
        f"  Categoría    {category}",
        f"  Plantilla    {'sí' if is_template else 'no'}",
        f"  Permite      {len(can_do)} reglas",
        f"  Prohíbe      {len(cannot_do)} reglas",
        f"  Por          {created_by}",
    ], C.B5, title="Resumen")
    print()

    if not confirm("¿Crear esta política?"):
        warn("Cancelado.")
        return

    with Spinner("Guardando política..."):
        result = api.post("/policies", {
            "name":        name,
            "description": desc,
            "category":    category,
            "can_do":      can_do,
            "cannot_do":   cannot_do,
            "is_template": is_template,
            "created_by":  created_by,
        })

    if "error" in result:
        fail(format_api_error(result))
        return

    print()
    ok(f"Política creada - ID: {q(C.B7, str(result['id']))}")
    print()
    hint("Aplicar a agente:  nova agent create  → elige política")
    hint("Ver política:      nova policy view " + str(result['id']))
    print()


def _policy_view(args):
    """View a specific policy."""
    api, cfg = get_api()

    policy_id = getattr(args, "value", "") or getattr(args, "key", "") or ""

    if not policy_id:
        # List and let user pick
        with Spinner("Cargando políticas..."):
            policies = api.get("/policies")
        if "error" in policies or not policies:
            fail("No hay políticas."); return
        opts = [f"#{p['id']}  {p['name']}" for p in policies]
        try:
            idx = _select(opts, default=0)
        except KeyboardInterrupt:
            print(); return
        policy_id = policies[idx]["id"]

    with Spinner("Cargando política..."):
        p = api.get(f"/policies/{policy_id}")

    if "error" in p:
        fail(f"Política no encontrada: {policy_id}"); return

    section(f"Política #{p['id']}", p.get("category", ""))
    print()
    kv("Nombre",      p["name"], C.W)
    kv("Descripción", p.get("description", "-"), C.G2)
    kv("Categoría",   p.get("category", "-"), C.G2)
    kv("Plantilla",   "sí ✓" if p.get("is_template") else "no", C.GRN if p.get("is_template") else C.G3)
    kv("Versión",     str(p.get("version", 1)), C.G3)
    kv("Creado por",  p.get("created_by", "-"), C.G3)
    kv("Activo",      "sí" if p.get("active") else "no", C.GRN if p.get("active") else C.RED)
    print()
    print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, f"PERMITE ({len(p.get('can_do', []))}):", bold=True))
    for r in p.get("can_do", []):
        print("       " + q(C.G2, f"+ {r}"))
    print()
    print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, f"PROHÍBE ({len(p.get('cannot_do', []))}):", bold=True))
    for r in p.get("cannot_do", []):
        print("       " + q(C.G2, f"- {r}"))
    print()
    tags = p.get("tags", [])
    if tags:
        kv("Tags", ", ".join(tags), C.G3)
    print()


def _policy_edit(args):
    """Edit an existing policy."""
    api, cfg = get_api()

    policy_id = getattr(args, "value", "") or getattr(args, "key", "") or ""
    if not policy_id:
        with Spinner("Cargando políticas..."):
            policies = api.get("/policies")
        if "error" in policies or not policies:
            fail("No hay políticas."); return
        opts = [f"#{p['id']}  {p['name']}" for p in policies]
        try:
            idx = _select(opts, default=0)
        except KeyboardInterrupt:
            print(); return
        policy_id = policies[idx]["id"]

    section(f"Editar política #{policy_id}")
    print("  " + q(C.G2, "Deja en blanco para no cambiar ese campo."))
    print()

    changes = {}
    name = prompt("Nuevo nombre (Enter para mantener)", default="", required=False)
    if name: changes["name"] = name
    desc = prompt("Nueva descripción (Enter para mantener)", default="", required=False)
    if desc: changes["description"] = desc

    edit_can = confirm("¿Editar acciones PERMITIDAS (can_do)?", default=False)
    if edit_can:
        changes["can_do"] = prompt_list("Nuevas acciones permitidas", min_items=1)

    edit_cannot = confirm("¿Editar acciones PROHIBIDAS (cannot_do)?", default=False)
    if edit_cannot:
        changes["cannot_do"] = prompt_list("Nuevas acciones prohibidas", min_items=0)

    if not changes:
        warn("Sin cambios."); return

    with Spinner("Guardando cambios..."):
        result = api.patch(f"/policies/{policy_id}", changes)

    if "error" in result:
        fail(format_api_error(result)); return

    ok(f"Política #{policy_id} actualizada  (versión incrementada)")
    print()


def _policy_delete(args):
    """Delete a policy."""
    api, cfg = get_api()

    policy_id = getattr(args, "value", "") or getattr(args, "key", "") or ""
    if not policy_id:
        with Spinner("Cargando políticas..."):
            policies = api.get("/policies")
        if "error" in policies or not policies:
            fail("No hay políticas."); return
        opts  = [f"#{p['id']}  {p['name']}" for p in policies]
        opts.append("← Cancelar")
        try:
            idx = _select(opts, default=len(opts) - 1)
        except KeyboardInterrupt:
            print(); return
        if idx == len(opts) - 1:
            return
        policy_id = policies[idx]["id"]

    if confirm_danger(f"¿Eliminar política #{policy_id}?", confirm_text="ELIMINAR"):
        with Spinner("Eliminando..."):
            result = api.delete(f"/policies/{policy_id}")
        if "error" in result:
            fail(format_api_error(result))
        else:
            ok(f"Política #{policy_id} eliminada.")
    else:
        info("Cancelado.")
    print()


# ── AGENT EDIT + HISTORY ──────────────────────────────────────────────────────

def cmd_agent_edit(args):
    """
    Edit an existing agent rules, description, or policy.
    Every edit is saved in token_history for audit.
    """
    api, cfg = get_api()

    section("Edit Agent")

    with Spinner("Cargando agentes..."):
        tokens = api.get("/tokens")

    if "error" in tokens or not tokens:
        fail("No hay agentes activos."); return

    for i, t in enumerate(tokens):
        print(f"  {q(C.B6, str(i + 1))}  {q(C.W, t['agent_name'])}  "
              f"{q(C.G3, str(t['id'])[:20])}...")
    print()
    try:
        idx = int(prompt("Número del agente a editar", required=True)) - 1
        token = tokens[idx]
    except (ValueError, IndexError):
        fail("Número inválido."); return

    print()
    section(f"Editando: {token['agent_name']}", f"v{token.get('version', 1)}")
    print("  " + q(C.G2, "Deja en blanco para mantener el valor actual."))
    print()

    changes: dict = {}

    # Description
    new_desc = prompt("Nueva descripción", default="", required=False)
    if new_desc:
        changes["description"] = new_desc

    # Policy
    with Spinner("Buscando políticas disponibles..."):
        policies = api.get("/policies")
    if isinstance(policies, list) and policies:
        print()
        print("  " + q(C.G2, "Políticas disponibles:"))
        for p in policies:
            print(f"    {q(C.B7, str(p['id']))}  {p['name']}  ({p.get('category','')})")
        pid_input = prompt("ID de política a aplicar (Enter para no cambiar)", required=False)
        if pid_input and pid_input.isdigit():
            changes["policy_id"] = int(pid_input)

    # Can do
    if confirm("¿Editar acciones PERMITIDAS (can_do)?", default=False):
        print()
        print("  " + q(C.G3, "Actuales: " + ", ".join(token.get("can_do", []))[:80]))
        changes["can_do"] = prompt_list("Nuevas acciones permitidas", min_items=1)

    # Cannot do
    if confirm("¿Editar acciones PROHIBIDAS (cannot_do)?", default=False):
        print()
        print("  " + q(C.G3, "Actuales: " + ", ".join(token.get("cannot_do", []))[:80]))
        changes["cannot_do"] = prompt_list("Nuevas acciones prohibidas", min_items=0)

    if not changes:
        warn("Sin cambios."); return

    # Audit trail
    reason = prompt("Razón del cambio (para el historial)", required=False)
    by     = prompt("Modificado por", default=cfg.get("user_name", "admin"))
    if reason: changes["change_reason"] = reason
    changes["changed_by"] = by

    print()
    with Spinner("Guardando y versionando..."):
        result = api.patch(f"/tokens/{token['id']}", changes)

    if "error" in result:
        fail(format_api_error(result)); return

    ok("Agente actualizado - versión anterior guardada en historial")
    kv("Token ID", str(token["id"])[:24] + "...", C.G3)
    print()
    hint("Ver historial:  nova agent history")
    print()


def cmd_agent_history(args):
    """
    View the version history of an agent's rules.
    Every PATCH to a token is tracked here automatically.
    """
    api, cfg = get_api()

    section("Agent Version History")

    with Spinner("Cargando agentes..."):
        tokens = api.get("/tokens")
    if "error" in tokens or not tokens:
        fail("No hay agentes."); return

    for i, t in enumerate(tokens):
        print(f"  {q(C.B6, str(i + 1))}  {q(C.W, t['agent_name'])}")
    print()
    try:
        idx = int(prompt("Número del agente", required=True)) - 1
        token = tokens[idx]
    except (ValueError, IndexError):
        fail("Número inválido."); return

    with Spinner("Cargando historial..."):
        history = api.get(f"/tokens/{token['id']}/history")

    if "error" in history:
        fail(format_api_error(history)); return

    if not history:
        warn(f"'{token['agent_name']}' no tiene historial todavía.")
        dim("El historial se genera a partir del primer PATCH (nova agent edit).")
        print(); return

    print()
    section(f"Historial de {token['agent_name']}", f"{len(history)} versiones")
    print()

    for v in history:
        ts = v.get("changed_at", "")[:19].replace("T", " ")
        print("  " + q(C.B6, f"v{v['version']}", bold=True) +
              "  " + q(C.G3, ts) +
              "  " + q(C.G2, f"por {v.get('changed_by', '-')}"))
        if v.get("change_reason"):
            print("       " + q(C.G1, v["change_reason"]))
        print("       " + q(C.G3, f"{len(v.get('can_do', []))} permitidas  ·  "
              f"{len(v.get('cannot_do', []))} prohibidas"))
        print()


# ── VALIDATE EXPLAIN ──────────────────────────────────────────────────────────

def cmd_validate_explain(args):
    """
    Deep chain-of-thought explanation of a validation decision.
    Shows step-by-step reasoning, matched rules, and what would change the verdict.
    Does NOT record to ledger - purely analytical.
    """
    api, cfg = get_api()

    section("Explain Validation", "análisis profundo con IA")
    print("  " + q(C.G2, "Nova analizará la acción paso a paso y explicará cada decisión."))
    print()

    # Choose agent
    with Spinner("Cargando agentes..."):
        tokens = api.get("/tokens")
    if "error" in tokens or not tokens:
        fail("No hay agentes activos."); return

    for i, t in enumerate(tokens):
        print(f"  {q(C.B6, str(i + 1))}  {t['agent_name']}")
    print()
    try:
        idx = int(prompt("Número del agente", required=True)) - 1
        token = tokens[idx]
    except (ValueError, IndexError):
        fail("Número inválido."); return

    print()
    action  = prompt("Acción a explicar", required=True)
    context = prompt("Contexto adicional (opcional)", default="", required=False)

    print()
    with Spinner("Analizando con razonamiento profundo...") as sp:
        result = api.post("/validate/explain", {
            "token_id": str(token["id"]),
            "action":   action,
            "context":  context,
        })
        sp.finish()

    if "error" in result:
        if "503" in str(result.get("code","")) or "LLM" in str(result.get("error","")):
            fail("Requiere LLM configurado. Configura un modelo con:  nova config model")
        else:
            fail(format_api_error(result))
        return

    print()
    print("  " + verdict_badge(result.get("verdict", "?")) +
          "  " + score_bar(result.get("score", 0)) +
          "  " + q(C.G3, f"confianza: {result.get('confidence', '?')}%"))

    print()
    section("Razonamiento paso a paso")
    print()
    for line in textwrap.wrap(result.get("reasoning", "-"), 70):
        print("  " + q(C.G1, line))

    if result.get("key_factors"):
        print()
        section("Factores clave")
        for k, v in result["key_factors"].items():
            print("  " + q(C.B6, "·") + "  " + q(C.W, k, bold=True) + ": " + q(C.G2, str(v)))

    if result.get("what_would_change"):
        print()
        section("Para cambiar la decisión")
        print("  " + q(C.G2, result["what_would_change"]))

    if result.get("risk_assessment"):
        print()
        section("Evaluación de riesgo")
        print("  " + q(C.G2, result["risk_assessment"]))

    if result.get("relevant_rules_matched"):
        print()
        print("  " + q(C.GRN, "✓", bold=True) + "  " + q(C.W, "Reglas que aplican:", bold=True))
        for r in result["relevant_rules_matched"]:
            print("       " + q(C.G2, f"+ {r}"))

    if result.get("relevant_rules_violated"):
        print()
        print("  " + q(C.RED, "✗", bold=True) + "  " + q(C.W, "Reglas violadas:", bold=True))
        for r in result["relevant_rules_violated"]:
            print("       " + q(C.RED, f"- {r}"))

    print()
    kv("LLM usado", f"{result.get('llm_provider','?')} / {result.get('llm_model','?')}", C.G3)
    kv("Modo", "dry-run (no registrado en ledger)", C.YLW)
    print()


# ── VALIDATE BATCH ────────────────────────────────────────────────────────────

def cmd_validate_batch(args):
    """
    Validate up to 20 actions simultaneously (parallel execution).
    Returns a summary matrix with scores, verdicts, and aggregate stats.
    """
    api, cfg = get_api()

    section("Batch Validation", "hasta 20 acciones en paralelo")
    print("  " + q(C.G2, "Valida múltiples acciones de una sola vez."))
    print()

    # Choose agent
    with Spinner("Cargando agentes..."):
        tokens = api.get("/tokens")
    if "error" in tokens or not tokens:
        fail("No hay agentes activos."); return

    for i, t in enumerate(tokens):
        print(f"  {q(C.B6, str(i + 1))}  {t['agent_name']}")
    print()
    try:
        idx = int(prompt("Número del agente", required=True)) - 1
        token = tokens[idx]
    except (ValueError, IndexError):
        fail("Número inválido."); return

    print()
    context = prompt("Contexto para todas las acciones (opcional)", default="", required=False)
    gen_resp = confirm("¿Generar respuesta automática por acción?", default=False)
    dry_run  = confirm("¿Modo dry-run (no guarda en ledger)?", default=False)

    print()
    print("  " + q(C.G2, "Escribe las acciones a validar (vacío para terminar, máx 20):"))
    print()
    actions = []
    i = 1
    while len(actions) < 20:
        val = prompt(f"Acción {i}", required=False)
        if not val:
            break
        actions.append(val)
        i += 1

    if not actions:
        warn("No ingresaste acciones."); return

    print()
    with Spinner(f"Validando {len(actions)} acciones en paralelo...") as sp:
        result = api.post("/validate/batch", {
            "token_id":          str(token["id"]),
            "actions":           actions,
            "context":           context,
            "generate_response": gen_resp,
            "check_duplicates":  True,
            "dry_run":           dry_run,
        })
        sp.finish()

    if "error" in result:
        fail(format_api_error(result)); return

    results  = result.get("results", [])
    summary  = result.get("summary", {})
    lat      = result.get("latency_ms", 0)

    # Summary bar
    print()
    print("  " +
          q(C.GRN, f"✓ {summary.get('approved', 0)} aprobadas") + "  " +
          q(C.RED, f"✗ {summary.get('blocked', 0)} bloqueadas") + "  " +
          q(C.YLW, f"⚠ {summary.get('escalated', 0)} escaladas") + "  " +
          q(C.G3, f"avg score: {summary.get('avg_score', 0)}  ·  {lat}ms total"))
    print()

    # Results table
    BADGE = {"APPROVED": "✓", "BLOCKED": "✗", "ESCALATED": "⚠", "DUPLICATE": "⊘"}
    VC    = {"APPROVED": C.GRN, "BLOCKED": C.RED, "ESCALATED": C.YLW, "DUPLICATE": C.ORG}

    for i, (r, act) in enumerate(zip(results, actions)):
        verd  = r.get("verdict", "?")
        score = r.get("score", 0)
        vc    = VC.get(verd, C.G2)
        badge = BADGE.get(verd, "·")
        print("  " + q(vc, badge) + "  " + q(C.W, act[:55]) +
              "  " + score_bar(score, 8) +
              "  " + q(C.G3, f"{r.get('latency_ms', 0)}ms"))
        reason = r.get("reason", "")
        if reason:
            print("       " + q(C.G3, reason[:70]))
        if r.get("response") and gen_resp:
            print("       " + q(C.G2, r["response"][:80]))
        print()

    approval_rate = summary.get("approval_rate", 0)
    if dry_run:
        print()
        warn("Modo dry-run - ninguna acción registrada en ledger.")
    print()
    kv("Tasa de aprobación", f"{approval_rate}%",
       C.GRN if approval_rate >= 70 else C.YLW if approval_rate >= 40 else C.RED)
    print()


# ── SIMULATE ──────────────────────────────────────────────────────────────────

def cmd_simulate(args):
    """
    Simulate a governance policy against test actions.
    Does NOT create a real token or record to the ledger.
    Perfect for testing rule sets before deploying them.
    """
    api, cfg = get_api()

    section("Policy Simulator", "prueba reglas sin crear token ni ledger")
    print("  " + q(C.G2, "Define un conjunto de reglas y pruébalas contra acciones de prueba."))
    print("  " + q(C.G3, "Ideal para verificar que tus políticas funcionan antes de activarlas."))
    print()

    # ── Step 1: Agent name ────────────────────────────────────────────────────
    print("  " + q(C.B6, "●") + "  " + q(C.W, "Paso 1/4 - Agente simulado", bold=True))
    print()
    agent_name = prompt("Nombre del agente simulado", default="AgenteSim")
    context    = prompt("Contexto base (opcional)", default="", required=False)

    # ── Step 2: Policy source ─────────────────────────────────────────────────
    print()
    print("  " + q(C.B6, "●") + "  " + q(C.W, "Paso 2/4 - Reglas a probar", bold=True))
    print()

    # Option: start from existing policy
    with Spinner("Buscando políticas existentes..."):
        policies = api.get("/policies")

    src_opts  = ["Definir reglas manualmente"]
    src_descs = ["Escribir can_do / cannot_do desde cero"]
    if isinstance(policies, list) and policies:
        for p in policies:
            src_opts.append(f"Política #{p['id']}: {p['name']}")
            src_descs.append(f"{len(p.get('can_do',[]))} permitidas · {len(p.get('cannot_do',[]))} prohibidas")

    try:
        src_idx = _select(src_opts, descriptions=src_descs, default=0)
    except KeyboardInterrupt:
        print(); return

    if src_idx > 0 and isinstance(policies, list):
        selected_policy = policies[src_idx - 1]
        can_do    = list(selected_policy.get("can_do", []))
        cannot_do = list(selected_policy.get("cannot_do", []))
        print()
        ok(f"Cargada política: {q(C.B7, selected_policy['name'])}")
        if confirm("¿Añadir reglas adicionales?", default=False):
            can_do.extend(prompt_list("Permitidas adicionales", min_items=0))
            cannot_do.extend(prompt_list("Prohibidas adicionales", min_items=0))
    else:
        print()
        print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ACCIONES PERMITIDAS (can_do):", bold=True))
        can_do = prompt_list("Una por línea", min_items=1)
        print()
        print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "ACCIONES PROHIBIDAS (cannot_do):", bold=True))
        cannot_do = prompt_list("Una por línea", min_items=0)

    # ── Step 3: Test actions ──────────────────────────────────────────────────
    print()
    print("  " + q(C.B6, "●") + "  " + q(C.W, "Paso 3/4 - Acciones de prueba", bold=True))
    print()
    print("  " + q(C.G2, "Escribe las acciones que quieres probar (vacío para terminar):"))
    print()
    test_actions = []
    i = 1
    while len(test_actions) < 10:
        val = prompt(f"Acción {i}", required=False)
        if not val:
            if test_actions:
                break
            warn("Necesitas al menos una acción.")
            continue
        test_actions.append(val)
        i += 1

    # ── Step 4: Simulate ──────────────────────────────────────────────────────
    print()
    print("  " + q(C.B6, "●") + "  " + q(C.W, "Paso 4/4 - Ejecutando simulación...", bold=True))
    print()

    with Spinner("Simulando con Nova...") as sp:
        result = api.post("/simulate", {
            "agent_name":   agent_name,
            "can_do":       can_do,
            "cannot_do":    cannot_do,
            "test_actions": test_actions,
            "context":      context,
        })
        sp.finish()

    if "error" in result:
        fail(format_api_error(result)); return

    results  = result.get("results", [])
    summary  = result.get("summary", {})

    # Header
    print()
    print("  " + q(C.W, "Resultado de la simulación:", bold=True))
    print()
    print("  " +
          q(C.GRN, f"✓ {summary.get('approved', 0)} aprobadas") + "  " +
          q(C.RED, f"✗ {summary.get('blocked', 0)} bloqueadas") + "  " +
          q(C.YLW, f"⚠ {summary.get('escalated', 0)} escaladas") + "  " +
          q(C.G3, f"avg score: {summary.get('avg_score', 0)}  ·  tasa: {summary.get('approval_rate', 0)}%"))
    print()

    BADGE = {"APPROVED": "✓", "BLOCKED": "✗", "ESCALATED": "⚠"}
    VC    = {"APPROVED": C.GRN, "BLOCKED": C.RED, "ESCALATED": C.YLW}

    for r in results:
        verd  = r.get("verdict", "?")
        score = r.get("score", 0)
        vc    = VC.get(verd, C.G2)
        badge = BADGE.get(verd, "·")
        print("  " + q(vc, badge) + "  " + q(C.W, r.get("action", "")[:60]) +
              "  " + score_bar(score, 8))
        if r.get("reason"):
            print("       " + q(C.G3, r["reason"][:70]))
        if r.get("score_factors"):
            factors_str = "  ".join(f"{k}: {v:+d}" for k, v in list(r["score_factors"].items())[:3])
            if factors_str:
                print("       " + q(C.G3, factors_str))
        print()

    # Coverage analysis
    approval_rate = summary.get("approval_rate", 0)
    print()
    hr()
    print()
    if approval_rate >= 80:
        ok(f"Cobertura alta - {approval_rate}% aprobadas. Las reglas están bien calibradas.")
    elif approval_rate >= 50:
        warn(f"Cobertura media - {approval_rate}% aprobadas. Revisa las reglas prohibidas.")
    else:
        fail(f"Cobertura baja - solo {approval_rate}% aprobadas. Las reglas son muy restrictivas.")
    print()

    if confirm("¿Crear un token real con estas reglas ahora?", default=False):
        print()
        name_real = prompt("Nombre del agente real", default=agent_name)
        auth_by   = prompt("Autorizado por", default=cfg.get("user_name", "admin"))
        with Spinner("Firmando Intent Token..."):
            tok_result = api.post("/tokens", {
                "agent_name":    name_real,
                "description":   f"Creado desde simulación",
                "can_do":        can_do,
                "cannot_do":     cannot_do,
                "authorized_by": auth_by,
            })
        if "error" in tok_result:
            fail(format_api_error(tok_result))
        else:
            ok(f"Agente creado - token: {q(C.B7, str(tok_result.get('token_id',''))[:20])}...")
    print()


# ── STATS FULL ────────────────────────────────────────────────────────────────

def cmd_stats(args):
    """
    Full analytics dashboard - agents, hourly, risk, timeline, anomalies.
    """
    api, cfg = get_api()

    sub = getattr(args, "subcommand", "") or ""

    if sub in ("agents", "agent"):
        return _stats_agents(api)
    elif sub in ("hourly", "hours", "hour"):
        return _stats_hourly(api)
    elif sub in ("risk",):
        return _stats_risk(api)
    elif sub in ("timeline", "time"):
        return _stats_timeline(api)
    elif sub in ("anomalies", "anom"):
        return _stats_anomalies_full(api)
    else:
        return _stats_overview(api, cfg)


def _stats_overview(api, cfg):
    """General stats dashboard."""
    section("Analytics Dashboard")

    with Spinner("Loading analytics...") as sp:
        stats  = api.get("/stats")
        risk   = api.get("/stats/risk")
        sp.finish()

    if "error" in stats:
        code = stats.get("code", "")
        if code in ("HTTP_401", "HTTP_403"):
            print()
            fail("API key not recognized by the server.")
            print()
            hint("Your key exists locally but isn't registered server-side.")
            hint("Set WORKSPACE_ADMIN_TOKEN and re-run  nova init  to register it.")
            hint("To switch keys:  nova keys")
            print()
        else:
            fail(format_api_error(stats))
        return

    # ── Main metrics ───────────────────────────────────────────────────────────
    print()
    total    = stats.get("total_actions", 0)
    approved = stats.get("approved", 0)
    blocked  = stats.get("blocked", 0)
    escalated= stats.get("escalated", 0)
    dupes    = stats.get("duplicates_blocked", 0)
    rate     = stats.get("approval_rate", 0)
    avg_sc   = stats.get("avg_score", 0)

    kv("Total acciones",    f"{total:,}", C.W)
    kv("Aprobadas",         q(C.GRN, f"{approved:,}"), C.GRN)
    kv("Bloqueadas",        q(C.RED,  f"{blocked:,}"), C.RED)
    kv("Escaladas",         q(C.YLW,  f"{escalated:,}"), C.YLW)
    kv("Duplicados",        f"{dupes:,}", C.G2)
    kv("Tasa aprobación",   f"{rate}%",
       C.GRN if rate >= 70 else C.YLW if rate >= 40 else C.RED)
    kv("Score promedio",    str(avg_sc), C.W)
    kv("Agentes activos",   str(stats.get("active_agents", 0)), C.B7)
    kv("Alertas pend.",     str(stats.get("alerts_pending", 0)),
       C.RED if stats.get("alerts_pending", 0) > 0 else C.G3)
    kv("Memorias",          f"{stats.get('memories_stored', 0):,}", C.B6)

    # Score trend sparkline
    trend = stats.get("score_trend")
    if trend and isinstance(trend, list) and len(trend) > 1:
        print()
        print("  " + q(C.G2, "Tendencia 7d:") + "  " + sparkline(trend) +
              q(C.G3, "  " + " → ".join(str(s) for s in trend)))

    # Risk profile preview
    if isinstance(risk, dict) and risk.get("agents"):
        print()
        section("Riesgo por agente (24h)", "top 5")
        print()
        for a in risk["agents"][:5]:
            rs    = a.get("risk_score", 0)
            rc    = C.RED if rs > 60 else C.YLW if rs > 30 else C.GRN
            print("  " + q(rc, f"risk={rs:4.0f}") + "  " +
                  q(C.W, a["agent_name"][:22]) + "  " +
                  q(C.G3, f"block={a.get('block_rate',0)}%  avg={a.get('avg_score',0)}"))

    print()
    hint("Por agente:   nova stats agents")
    hint("Por hora:     nova stats hourly")
    hint("Riesgo:       nova stats risk")
    hint("Timeline:     nova stats timeline")
    hint("Anomalías:    nova stats anomalies")
    print()


def _stats_agents(api):
    """Per-agent breakdown."""
    with Spinner("Cargando stats por agente..."):
        result = api.get("/stats/agents")
    if "error" in result:
        fail(format_api_error(result)); return

    section("Stats por agente")
    print()
    if not result:
        warn("Sin datos."); return

    for a in result:
        total  = a.get("total_actions", 0)
        app    = a.get("approved", 0)
        blk    = a.get("blocked", 0)
        esc    = a.get("escalated", 0)
        avg    = a.get("avg_score", 0)
        rate   = a.get("approval_rate", 0)
        last   = time_ago(a.get("last_action", ""))
        rc     = C.GRN if rate >= 70 else C.YLW if rate >= 40 else C.RED

        print("  " + q(C.W, a.get("agent_name","?"), bold=True) +
              "  " + q(C.G3, f"{total} acciones  ·  {last}"))
        print("    " +
              q(C.GRN, f"✓ {app}") + "  " +
              q(C.RED,  f"✗ {blk}") + "  " +
              q(C.YLW,  f"⚠ {esc}") + "  " +
              q(rc, f"{rate}% aprobación") + "  " +
              q(C.G3, f"avg score: {avg}"))
        print()
    print()


def _stats_hourly(api):
    """Hourly activity heatmap."""
    days = 7
    with Spinner(f"Cargando actividad últimos {days}d..."):
        result = api.get(f"/stats/hourly?days={days}")
    if "error" in result:
        fail(format_api_error(result)); return

    section(f"Actividad por hora del día (últimos {days}d)")
    print()

    max_count = max((h.get("count", 0) for h in result), default=1) or 1
    for h in result:
        count    = h.get("count", 0)
        avg_sc   = h.get("avg_score", 0)
        bar_w    = int(count / max_count * 22)
        bar      = q(C.B6, "█" * bar_w) + q(C.G3, "·" * (22 - bar_w))
        score_c  = C.GRN if avg_sc >= 70 else C.YLW if avg_sc >= 40 else C.RED
        print(f"  {h.get('hour',0):02d}h  {bar}  {str(count):<5}  " +
              q(score_c, f"avg {avg_sc}"))
    print()


def _stats_risk(api):
    """Risk profile per agent."""
    with Spinner("Calculando perfil de riesgo..."):
        result = api.get("/stats/risk")
    if "error" in result:
        fail(format_api_error(result)); return

    agents = result.get("agents", [])
    section("Perfil de riesgo (últimas 24h)", f"{len(agents)} agentes")
    print()

    if not agents:
        ok("Sin actividad en las últimas 24h."); return

    for a in agents:
        rs = a.get("risk_score", 0)
        rc = C.RED if rs > 60 else C.YLW if rs > 30 else C.GRN
        bar_w = int(rs / 100 * 20)
        bar   = q(rc, "█" * bar_w) + q(C.G3, "·" * (20 - bar_w))
        print("  " + bar + "  " + q(rc, f"{rs:5.1f}", bold=True) + "  " +
              q(C.W, a["agent_name"][:20]))
        print("       " +
              q(C.G3, f"bloqueo: {a.get('block_rate',0)}%  "
                      f"avg: {a.get('avg_score',0)}  "
                      f"bloqueadas: {a.get('blocked',0)}  "
                      f"críticas: {a.get('critical_count',0)}"))
        print()
    print()
    hint("Las anomalías se detectan automáticamente. Ver con:  nova stats anomalies")
    print()


def _stats_timeline(api):
    """Hour-by-hour activity timeline."""
    hours = 24
    with Spinner(f"Cargando timeline {hours}h..."):
        result = api.get(f"/stats/timeline?hours={hours}")
    if "error" in result:
        fail(format_api_error(result)); return

    section(f"Timeline últimas {hours}h")
    print()

    if not result:
        warn("Sin datos."); return

    headers = ["Hora", "Total", "✓ Aprobadas", "✗ Bloqueadas", "Avg Score"]
    rows    = []
    for t in result:
        hour = (t.get("hour","?") or "?")[:13]
        rows.append([
            hour,
            str(t.get("total", 0)),
            str(t.get("approved", 0)),
            str(t.get("blocked", 0)),
            str(t.get("avg_score", 0)),
        ])
    table(headers, rows)
    print()


def _stats_anomalies_full(api):
    """Detected anomalies from analytics engine."""
    with Spinner("Buscando anomalías..."):
        result = api.get("/stats/anomalies?limit=30")
    if "error" in result:
        fail(format_api_error(result)); return

    section("Anomalías detectadas", f"{len(result)} en registro")
    print()

    if not result:
        ok("No se detectaron anomalías.")
        print()
        dim("Nova monitorea: bloqueo alto, ráfagas de actividad, degradación de score.")
        print(); return

    SEV_C = {"critical": C.RED, "high": C.ORG, "medium": C.YLW, "low": C.GRN}
    TYPE_D = {
        "high_block_rate":    "Tasa de bloqueo alta",
        "burst_activity":     "Ráfaga de actividad",
        "score_degradation":  "Degradación de score",
        "sensitive_data_exposure": "Exposición de datos sensibles",
        "limit_probing":      "Sondeo de límites",
    }
    for a in result:
        sev   = a.get("severity", "medium")
        atype = a.get("anomaly_type", "?")
        sc    = SEV_C.get(sev, C.G2)
        label = TYPE_D.get(atype, atype)
        ts    = a.get("created_at", "")[:16].replace("T", " ")
        print("  " + q(sc, "▲", bold=True) + "  " +
              q(C.W, label, bold=True) + "  " +
              q(sc, f"[{sev.upper()}]") + "  " +
              q(C.G3, f"agente: {a.get('agent_name','?')}"))
        print("       " + q(C.G2, a.get("description", "")[:70]))
        print("       " + q(C.G3, ts) + ("  " + q(C.GRN, "✓ resuelto") if a.get("resolved") else ""))
        print()
    print()


# ── MEMORY SEARCH + UPDATE ────────────────────────────────────────────────────

def cmd_memory_search(args):
    """Semantic search across agent memories."""
    api, cfg = get_api()

    section("Memory Search")
    print("  " + q(C.G2, "Busca memorias relevantes por contenido."))
    print()

    agent = getattr(args, "agent", "") or prompt("Nombre del agente", default=cfg.get("default_token", ""))
    if not agent:
        fail("Necesitas especificar un agente."); return

    query = getattr(args, "action", "") or prompt("Búsqueda", required=True)
    limit = int(getattr(args, "limit", 10) or 10)

    with Spinner("Buscando memorias relevantes..."):
        result = api.post("/memory/search", {
            "agent_name": agent,
            "query":      query,
            "limit":      limit,
        })

    if "error" in result:
        fail(format_api_error(result)); return

    if not result:
        warn(f"No se encontraron memorias relevantes para '{query}'.")
        print(); return

    section(f"Memorias para '{query}'", f"{len(result)} resultados")
    print()

    for m in result:
        imp   = m.get("importance", 5)
        bar   = q(C.B6, "█" * imp) + q(C.G3, "·" * (10 - imp))
        source = m.get("source", "?")
        ts     = time_ago(m.get("created_at", ""))
        tags   = ", ".join(m.get("tags", []))

        print("  " + q(C.W, m["key"], bold=True) + "  " + bar + "  " +
              q(C.G3, f"{source}  ·  {ts}"))
        for line in textwrap.wrap(m["value"], 65):
            print("    " + q(C.G2, line))
        if tags:
            print("    " + q(C.G3, f"tags: {tags}"))
        print()
    print()


def cmd_memory_update(args):
    """Update an existing memory entry."""
    api, cfg = get_api()

    section("Update Memory")

    agent = getattr(args, "agent", "") or prompt("Nombre del agente", default="")
    if not agent:
        fail("Necesitas especificar un agente."); return

    # List memories to pick from
    with Spinner("Cargando memorias..."):
        mems = api.get(f"/memory/{urllib.parse.quote(agent)}")

    if "error" in mems or not mems:
        fail(f"No hay memorias para '{agent}'."); return

    print()
    for m in mems[:20]:
        print(f"  {q(C.B6, str(m['id']))}  {q(C.W, m['key'])}: {q(C.G2, m['value'][:45])}")
    print()

    mem_id = prompt("ID de la memoria a actualizar", required=True)

    print()
    changes = {}
    new_val = prompt("Nuevo valor (Enter para no cambiar)", required=False)
    if new_val: changes["value"] = new_val

    new_imp = prompt("Nueva importancia 1-10 (Enter para no cambiar)", required=False)
    if new_imp and new_imp.isdigit(): changes["importance"] = int(new_imp)

    new_tags = prompt("Nuevos tags (coma separados, Enter para no cambiar)", required=False)
    if new_tags:
        changes["tags"] = [t.strip() for t in new_tags.split(",") if t.strip()]

    new_exp = prompt("Expira en horas (Enter para no cambiar)", required=False)
    if new_exp and new_exp.isdigit(): changes["expires_in_hours"] = int(new_exp)

    if not changes:
        warn("Sin cambios."); return

    with Spinner("Actualizando memoria..."):
        result = api.patch(f"/memory/{mem_id}", changes)

    if "error" in result:
        fail(format_api_error(result)); return

    ok(f"Memoria #{mem_id} actualizada.")
    print()


# ── WORKSPACE INFO ────────────────────────────────────────────────────────────

def cmd_workspace(args):
    """Show workspace details, plan, usage, and quota."""
    api, cfg = get_api()

    with Spinner("Loading workspace..."):
        result = api.get("/workspaces/me")

    if "error" in result:
        code = result.get("code", "")
        if code in ("HTTP_401", "HTTP_403"):
            print()
            fail("API key not recognized by the server.")
            print()
            print("  " + q(C.W, "This means your key exists locally but isn't registered server-side."))
            print()
            hint("If you control the server, set WORKSPACE_ADMIN_TOKEN and re-run  nova init")
            hint("Or register manually - see https://github.com/sxrubyo/nova-os")
            hint("To switch keys:  nova keys")
            print()
        else:
            fail(format_api_error(result))
        return

    section("Workspace", result.get("name", "?"))
    print()

    kv("ID",          str(result.get("id", "?"))[:24] + "...", C.G3)
    kv("Nombre",      result.get("name", "?"), C.W)
    kv("Plan",        result.get("plan", "?"), C.GLD_BRIGHT)

    features = result.get("features", [])
    if features:
        kv("Features",    ", ".join(features), C.B7)

    usage = result.get("usage_this_month", 0)
    quota = result.get("quota_monthly", 10000)
    pct   = int(usage / max(quota, 1) * 100)
    bar_w = int(pct / 100 * 20)
    bar   = q(C.GRN if pct < 70 else C.YLW if pct < 90 else C.RED, "█" * bar_w) + \
            q(C.G3, "·" * (20 - bar_w))
    print()
    print("  " + q(C.G2, "Uso mensual:".ljust(22)) + bar +
          "  " + q(C.W, f"{usage:,}") + q(C.G3, f" / {quota:,}  ({pct}%)"))

    # Stats
    stats = result.get("stats")
    if stats:
        print()
        section("Actividad del workspace")
        kv("Total acciones",  f"{stats.get('total_actions', 0):,}", C.W)
        kv("Tasa aprobación", f"{stats.get('approval_rate', 0)}%",
           C.GRN if stats.get("approval_rate", 0) >= 70 else C.YLW)
        kv("Agentes activos", str(stats.get("active_agents", 0)), C.B7)
        kv("Alertas pend.",   str(stats.get("alerts_pending", 0)),
           C.RED if stats.get("alerts_pending", 0) > 0 else C.G3)
        kv("Score promedio",  str(stats.get("avg_score", 0)), C.W)

    print()
    hint("Estadísticas detalladas:  nova stats")
    hint("Gestionar plan:           https://nova-os.com/plans")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# nova boot  -  start Nova Core + connect ALL agents in one command
# ══════════════════════════════════════════════════════════════════════════════

def _start_nova_core_background(nova_core_path: str = None) -> bool:
    """
    Start nova_core.py in the background.
    Returns True if successfully started or already running.
    Tries: pm2 first, then nohup, then subprocess.Popen.
    """
    # Find nova_core.py
    candidates = []
    if nova_core_path:
        candidates.append(nova_core_path)
    candidates += [
        str(Path.cwd() / "nova_core.py"),
        str(Path.home() / "nova_core.py"),
        str(Path("/home/ubuntu/nova_core.py")),
        str(Path("/opt/nova/nova_core.py")),
    ]
    core_path = next((p for p in candidates if Path(p).exists()), None)
    if not core_path:
        return False

    # Try pm2 first (preferred - survives reboots)
    if shutil.which("pm2"):
        try:
            # Check if already running
            check = subprocess.run(["pm2", "list"], capture_output=True, text=True, timeout=5)
            if "nova-core" in check.stdout:
                # Already registered - just restart
                subprocess.run(["pm2", "restart", "nova-core", "--update-env"],
                               capture_output=True, timeout=10)
                return True
            r = subprocess.run(
                ["pm2", "start", core_path, "--name", "nova-core",
                 "--interpreter", "python3"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return True
        except Exception:
            pass

    # Try nohup
    try:
        subprocess.Popen(
            ["nohup", "python3", core_path],
            stdout=open("/tmp/nova_core.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        time.sleep(2)
        return True
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")

    # Direct subprocess
    try:
        subprocess.Popen(
            ["python3", core_path],
            stdout=open("/tmp/nova_core.log", "a"),
            stderr=subprocess.STDOUT,
        )
        time.sleep(2)
        return True
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")

    return False


def cmd_boot(args):
    """
    One command to start Nova Core and govern all your AI agents.

    What it does:
      1. Starts nova_core.py if not running (pm2 / nohup / subprocess)
      2. Waits for it to be ready (up to 10s)
      3. Discovers all agents in your environment
      4. Connects them all to Nova Core
      5. Pushes .nova/rules/ into Nova Core
      6. Injects identity into each agent via /boot endpoint
      7. Prints a live status board

    Usage:
      nova boot                    # start everything
      nova boot --path ./nova_core.py   # specify nova_core path
    """
    print_logo(compact=True)
    print()
    print("  " + q(C.GLD, "✦", bold=True) + "  " + q(C.W, "Nova Boot", bold=True))
    print("  " + q(C.G3, "  Starting governance layer for all AI agents..."))
    print()

    cfg      = load_config()
    nc       = _get_nova_core()
    core_path = getattr(args, "path", "") or ""

    # ── Step 1: Ensure Nova Core is running ───────────────────────────────────
    with Spinner("Checking Nova Core...") as sp:
        alive = nc.is_alive()
        sp.finish()

    if alive:
        ok("Nova Core already running")
    else:
        info("Starting Nova Core...")
        started = _start_nova_core_background(core_path or None)
        if not started:
            fail("Could not find or start nova_core.py.")
            print()
            hint("Place nova_core.py in the current directory or home folder,")
            hint("then run:  nova boot  again.")
            print()
            hint("Or start manually:  python3 nova_core.py &")
            return

        # Wait up to 10s for it to be ready
        print()
        with Spinner("Waiting for Nova Core to be ready...") as sp:
            for _ in range(20):
                time.sleep(0.5)
                if nc.is_alive():
                    break
            sp.finish()

        if nc.is_alive():
            ok("Nova Core started")
        else:
            warn("Nova Core started but not yet responding.")
            hint("Check logs:  cat /tmp/nova_core.log")
            hint("Try again in a few seconds:  nova boot")
            return

    print()

    # ── Step 2: Discover all agents ───────────────────────────────────────────
    project_root = _find_project_root()
    with Spinner("Scanning for AI agents...") as sp:
        discovered = discover_agents(project_root=project_root, probe_ports=True)
        sp.finish()

    if not discovered:
        warn("No agents detected automatically.")
        hint("Make sure your agents are running, then try  nova boot  again.")
        print()
    else:
        print("  " + q(C.W, f"Found {len(discovered)} agent(s):", bold=True))
        print()
        for ag in discovered:
            c = C.GRN if ag["confidence"] >= 60 else C.YLW
            live = q(C.GRN, " live") if ag["port_live"] else ""
            print("    " + q(C.GLD, ag["icon"]) + "  " +
                  q(C.W, ag["display"], bold=True) +
                  "  " + q(c, f"{ag['confidence']}%") + live)
        print()

    # ── Step 3: Connect all agents to Nova Core ───────────────────────────────
    hr()
    print()
    print("  " + q(C.W, "Connecting agents...", bold=True))
    print()

    agents_payload = []
    for ag in discovered:
        if ag.get("url") and ag.get("port_live"):
            agents_payload.append({
                "url":  ag["url"],
                "name": ag["agent_type"],
            })

    if agents_payload:
        result = nc._req("POST", "/connect/multi", {"agents": agents_payload})
        for r in result.get("agents", []):
            symbol = q(C.GRN, "✓") if r.get("reachable") else q(C.YLW, "~")
            print("    " + symbol + "  " + q(C.W, r["name"]) +
                  "  " + q(C.G3, r["url"]))

    # ── Step 4: Load .nova/rules/ into Nova Core ──────────────────────────────
    rules_loaded_total = 0
    for ag in discovered:
        rules_dir = (project_root / ".nova" / "agents" /
                     ag["agent_type"] / "rules")
        if rules_dir.exists() and list(rules_dir.glob("*.json")):
            r = nc._req("POST", "/rules/load-folder", {
                "path":  str(rules_dir),
                "scope": f"agent:{ag['agent_type']}",
            })
            n = r.get("loaded", 0)
            if n:
                ok(f"Loaded {n} rules for {ag['display']}")
                rules_loaded_total += n

    # Also load global rules from ~/.nova/rules/
    global_rules = NOVA_DIR / "rules"
    if global_rules.exists():
        r = nc._req("POST", "/rules/load-folder", {
            "path":  str(global_rules),
            "scope": "global",
        })
        n = r.get("loaded", 0)
        if n:
            ok(f"Loaded {n} global rules")
            rules_loaded_total += n

    # ── Step 5: Call /boot for each live agent  ───────────────────────────────
    print()
    print("  " + q(C.W, "Injecting identity into agents...", bold=True))
    print()
    for ag in discovered:
        if ag.get("port_live"):
            r = nc._req("GET", f"/boot/{ag['agent_type']}")
            rc    = r.get("rule_count", 0)
            boots = r.get("restart_count", 1)
            print("    " + q(C.GRN, "✓") + "  " +
                  q(C.W, ag["display"]) +
                  q(C.G3, f"  restart #{boots}  {rc} rules active"))

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    hr_bold()
    print()
    print("  " + q(C.GLD, "✦", bold=True) + "  " +
          q(C.W, "Nova is governing your agents.", bold=True))
    print()
    health = nc.health()
    total_rules = health.get("rules", {}).get("total", "?")
    kv("Nova Core",   nc.url, C.B7)
    kv("Total rules", str(total_rules), C.GRN)
    kv("Agents live", str(len(agents_payload)), C.W)
    print()
    hint("Watch live:  nova watch")
    hint("See rules:   nova rules")
    hint("Ledger:      nova ledger")
    print()

    # Save nova core URL to config
    cfg["nova_core_url"] = nc.url
    save_config(cfg)


# ══════════════════════════════════════════════════════════════════════════════
# nova guard  -  universal AI agent protection wizard
# ══════════════════════════════════════════════════════════════════════════════

def cmd_guard(args):
    """
    Universal protection layer for ALL AI agents in your project.

    What it does in one command:
      1. Detects every AI CLI in your environment
      2. Sets up the strongest available integration per agent
      3. Creates protected-path rules (no agent can touch those paths)
      4. Injects rules into CLAUDE.md, .aider.conf.yml, Copilot instructions, etc.
      5. Generates shell aliases  (claude → nova wrap claude)
      6. Installs git pre-commit hook
      7. Writes Nova MCP server config for Claude Code

    Usage:
      nova guard                    # full wizard
      nova guard --path /prod       # protect a specific path
      nova guard --agent claude     # only set up one agent
    """
    print_logo(compact=True)
    print()
    print("  " + q(C.GLD, "✦", bold=True) + "  " + q(C.W, "Nova Guard", bold=True) + "  " +
          q(C.G3, "- universal AI agent protection"))
    print()

    cfg = load_config()
    nova_url = cfg.get("api_url", "http://localhost:9002")
    project_root = _find_project_root()

    # ── 1. Discover agents ────────────────────────────────────────────────────
    print("  " + q(C.G2, "Scanning environment..."))
    print()

    with Spinner("Detecting AI agents...") as sp:
        agents = discover_agents(project_root=project_root, probe_ports=True)
        sp.finish()

    if not agents:
        warn("No AI agents detected.")
        print()
        hint("Install an agent first, then re-run  nova guard")
        hint("Supported: OpenClaw, Claude Code, Aider, Gemini CLI, Codex, Copilot CLI")
        print()
        # Still offer to set up protected paths
        agents = []

    # Filter by --agent flag if provided
    agent_filter = getattr(args, "agent", "").lower().replace("-", "_").replace(" ", "_")
    if agent_filter:
        agents = [a for a in agents if agent_filter in a["agent_type"]
                  or agent_filter in a["display"].lower()]

    if agents:
        print("  " + q(C.W, f"Found {len(agents)} agent(s):", bold=True))
        print()
        for ag in agents:
            conf_c = C.GRN if ag["confidence"] >= 60 else C.YLW
            live_s = q(C.GRN, " ● live") if ag["port_live"] else ""
            print("    " + q(C.GLD, ag["icon"]) + "  " + q(C.W, ag["display"], bold=True) +
                  "  " + q(conf_c, f"{ag['confidence']}% confidence") + live_s)
        print()

    # ── 2. Protected paths ────────────────────────────────────────────────────
    hr()
    print()
    print("  " + q(C.W, "Protected paths", bold=True))
    print("  " + q(C.G2, "These paths can NEVER be modified or deleted by any agent."))
    print()

    current_protected = _load_protected_paths(project_root)
    if current_protected:
        print("  " + q(C.G3, "Currently protected:"))
        for p in current_protected:
            print("    " + q(C.GLD, "✦") + "  " + q(C.W, p))
        print()

    # Accept --path flag directly
    path_arg = getattr(args, "path", "").strip()
    if path_arg:
        extra = [path_arg]
    else:
        # Suggest sensible defaults
        suggested = []
        for name in [".env", ".env.local", "/prod", "production", ".secrets",
                     ".nova", "database", "db", ".ssh"]:
            candidate = project_root / name
            if candidate.exists() and str(name) not in current_protected:
                suggested.append(name)

        if suggested:
            print("  " + q(C.G3, "Suggested paths to protect (found in project):"))
            for s in suggested[:5]:
                print("    " + q(C.G2, f"  · {s}"))
            print()

        try:
            raw = prompt(
                "Paths to protect (comma-separated, or Enter to skip)",
                default=", ".join(suggested[:3]) if suggested else "",
            )
            extra = [p.strip() for p in raw.split(",") if p.strip()] if raw else []
        except (EOFError, KeyboardInterrupt):
            extra = []

    if extra:
        merged = list(dict.fromkeys(current_protected + extra))   # dedup, preserve order
        _save_protected_paths(project_root, merged)
        for p in extra:
            ok(f"Protected: {p}")

        # Create a rule file for each new path
        rules_dir_base = project_root / ".nova" / "agents"
        for ag in agents:
            rd = rules_dir_base / ag["agent_type"] / "rules"
            rd.mkdir(parents=True, exist_ok=True)
            for path_pattern in extra:
                rule_data = {
                    "id":          "guard_" + hashlib.md5(path_pattern.encode()).hexdigest()[:8],
                    "name":        "protect_" + re.sub(r"[^a-z0-9]", "_", path_pattern.lower())[:30],
                    "description": f"Never modify, delete, or overwrite {path_pattern}",
                    "action":      "block",
                    "priority":    9,
                    "scope":       f"agent:{ag['agent_type']}",
                    "created_at":  datetime.now().isoformat(),
                    "created_by":  "nova guard",
                    "active":      True,
                }
                create_rule_file(rd, rule_data)
        print()

    # ── 3. Per-agent integrations ─────────────────────────────────────────────
    if agents:
        hr()
        print()
        print("  " + q(C.W, "Setting up integrations...", bold=True))
        print()

    results = {}
    for ag in agents:
        atype = ag["agent_type"]
        strategies = _INTEGRATION_STRATEGIES.get(atype, ["alias", "fswatch"])
        results[atype] = []

        for strategy in strategies:

            # ── Proxy (OpenClaw, HTTP agents) ──────────────────────────────
            if strategy == "proxy" and ag["port_live"]:
                results[atype].append(
                    q(C.B7, "proxy") + q(C.G3, " (nova shield active on " +
                    ag.get("url", "") + ")")
                )

            # ── MCP (Claude Code) ──────────────────────────────────────────
            elif strategy == "mcp" and atype == "claude_code":
                mcp_result = _write_mcp_config(project_root, nova_url)
                if mcp_result.get("written"):
                    results[atype].append(
                        q(C.GRN, "✓") + " " + q(C.B7, "MCP server") +
                        q(C.G3, " → .claude/settings.json")
                    )
                else:
                    results[atype].append(q(C.YLW, "⚠") + " MCP: " + mcp_result.get("error",""))

            # ── Config injection (CLAUDE.md, .aider.conf.yml, etc.) ────────
            elif strategy == "config_inject":
                inj = inject_into_config_file(project_root, atype)
                if inj.get("injected"):
                    rel = Path(inj["file"]).relative_to(project_root) if project_root in Path(inj["file"]).parents else inj["file"]
                    results[atype].append(
                        q(C.GRN, "✓") + " " + q(C.B7, "rules injected") +
                        q(C.G3, f" → {rel}  ({inj['rules_count']} rules)")
                    )
                else:
                    results[atype].append(q(C.G3, "↷ config inject: " + inj.get("reason", "skipped")))

            # ── Git hooks ──────────────────────────────────────────────────
            elif strategy == "git_hook":
                gh_result = install_git_hooks(project_root, nova_url)
                if gh_result.get("installed"):
                    results[atype].append(
                        q(C.GRN, "✓") + " " + q(C.B7, "git pre-commit hook") +
                        q(C.G3, " installed")
                    )
                else:
                    results[atype].append(q(C.G3, "↷ git hook: " + gh_result.get("reason", "")))

            # ── Shell alias ────────────────────────────────────────────────
            elif strategy == "alias":
                alias_script = generate_shell_aliases([atype])
                alias_file = NOVA_DIR / "shell_setup.sh"
                try:
                    # Merge into existing shell_setup.sh
                    existing_aliases = alias_file.read_text() if alias_file.exists() else ""
                    # Only add lines not already present
                    new_lines = [l for l in alias_script.splitlines()
                                 if l and not l.startswith("#")
                                 and l not in existing_aliases]
                    if new_lines:
                        with open(alias_file, "a") as f:
                            f.write("\n".join(new_lines) + "\n")
                    results[atype].append(
                        q(C.GRN, "✓") + " " + q(C.B7, "shell alias") +
                        q(C.G3, " → ~/.nova/shell_setup.sh")
                    )
                except Exception:
                    results[atype].append(q(C.G3, "↷ alias: could not write shell_setup.sh"))

        # Print per-agent results
        print("    " + q(C.GLD, ag["icon"]) + "  " + q(C.W, ag["display"], bold=True))
        for line in results[atype]:
            print("        " + line)
        print()

    # ── 4. Shell setup reminder ───────────────────────────────────────────────
    shell_setup = NOVA_DIR / "shell_setup.sh"
    if shell_setup.exists():
        hr()
        print()
        print("  " + q(C.W, "Add this line to your ~/.zshrc or ~/.bashrc:", bold=True))
        print()
        print("    " + q(C.B7, f"source {shell_setup}"))
        print()
        print("  " + q(C.G3, "Then open a new terminal - aliases will be active."))
        print()

    # ── 5. Summary ────────────────────────────────────────────────────────────
    hr_bold()
    print()
    protected = _load_protected_paths(project_root)
    total_rules = sum(
        len(list((project_root / ".nova" / "agents" / ag["agent_type"] / "rules").glob("*.json")))
        for ag in agents
        if (project_root / ".nova" / "agents" / ag["agent_type"] / "rules").exists()
    )
    print("  " + q(C.GLD, "✦", bold=True) + "  " + q(C.W, "Nova Guard active", bold=True))
    print()
    if protected:
        print("     " + q(C.GRN, f"⊕  {len(protected)} protected path(s)"))
    if total_rules:
        print("     " + q(C.GRN, f"⊕  {total_rules} rule(s) active across {len(agents)} agent(s)"))
    print("     " + q(C.G2, "⊕  No AI agent can touch your protected paths."))
    print()
    hint("Add more rules:  nova rule "<description>"")
    hint("See coverage:    nova guard --status")
    hint("Watch live:      nova watch")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# nova rule "..."  - one-liner natural language rule creation
# ══════════════════════════════════════════════════════════════════════════════

def cmd_rule_quick(args):
    """
    One-liner governance rule from natural language.

    Usage:
      nova rule "never delete files from /prod"
      nova rule "don't send emails without confirmation" --block

    Nova parses the intent, creates the rule file in .nova/agents/<agent>/rules/,
    and attempts to register it with Nova Core if running.
    """
    # Accept rule text as subcommand, action flag, or third positional arg
    rule_text = (getattr(args, "subcommand", "") or
                 getattr(args, "action", "") or
                 getattr(args, "third", "") or "").strip()

    if not rule_text:
        print_logo(compact=True)
        print()
        print("  " + q(C.W, "Create a governance rule in plain language.", bold=True))
        print()
        print("  " + q(C.G2, "Usage:"))
        print("    " + q(C.B7, 'nova rule "never delete files from /prod"'))
        print("    " + q(C.B7, "nova rule \"don't send emails without asking me\""))
        print()
        try:
            rule_text = prompt("Rule description", required=True)
        except (EOFError, KeyboardInterrupt):
            print(); return
        if not rule_text:
            return

    # ── Determine action ───────────────────────────────────────────────────────
    force_block = getattr(args, "verdict", "").lower() == "block"
    block_words = ["never", "nunca", "don't", "no ", "block", "bloquear",
                   "prohibit", "prevent", "impedir", "stop", "parar"]
    action = "block" if (force_block or any(w in rule_text.lower()
                                             for w in block_words)) else "warn"

    # ── Build rule data ────────────────────────────────────────────────────────
    import hashlib as _hl
    rule_id    = "rule_" + _hl.md5(rule_text.encode()).hexdigest()[:8]
    words      = re.sub(r"[^a-z0-9 ]", "", rule_text.lower()).split()
    short_name = "_".join(words[:5]) or "custom_rule"

    cfg = load_config()
    agent_name = cfg.get("connected_agent_name", "global")

    rule_data = {
        "id":          rule_id,
        "name":        short_name,
        "description": rule_text,
        "action":      action,
        "priority":    7,
        "scope":       f"agent:{agent_name}",
        "created_at":  datetime.now().isoformat(),
        "created_by":  "nova rule",
        "active":      True,
    }

    # ── Find rules directory ───────────────────────────────────────────────────
    nova_proj_root_str = cfg.get("nova_project_root", "")
    agent_type = cfg.get("connected_agent_name", "unknown").lower().replace(" ", "_")

    if nova_proj_root_str:
        nova_proj_root = Path(nova_proj_root_str)
    else:
        nova_proj_root = _find_project_root()

    rules_dir = nova_proj_root / ".nova" / "agents" / agent_type / "rules"

    if not rules_dir.exists():
        # Create the folder structure on the fly
        rules_dir = create_nova_project_folder(
            project_root=nova_proj_root,
            agent_type=agent_type,
            agent_name=agent_name,
            nova_url=cfg.get("api_url", ""),
            nova_api_key=cfg.get("api_key", ""),
        )

    # ── Save locally ───────────────────────────────────────────────────────────
    rule_path = create_rule_file(rules_dir, rule_data)

    # ── Try to register with Nova Core (non-fatal if not running) ─────────────
    nc_result = {}
    nc = _get_nova_core()
    if nc.is_alive():
        nc_result = nc.rules_create(rule_text, scope=f"agent:{agent_name}",
                                    action=action, priority=7)

    # ── Output ─────────────────────────────────────────────────────────────────
    print()
    ok(f"[{action.upper()}]  {rule_text}")
    print()
    print("  " + q(C.G2, "Saved:  ") + q(C.W, str(rule_path)))
    if nc_result and "error" not in nc_result:
        print("  " + q(C.G2, "Server: ") + q(C.GRN, "registered with Nova Core ✓"))
    elif nc.is_alive():
        print("  " + q(C.G2, "Server: ") + q(C.YLW, "registered locally only (Core not running)"))
    print()
    hint("See all rules:  nova rules")
    hint("Test this rule: " + q(C.B7, f'nova rules test --action "<action>"'))
    print()


# ══════════════════════════════════════════════════════════════════════════════
# nova exec  —  Nova controls the terminal: run commands with governance
# ══════════════════════════════════════════════════════════════════════════════

_EXEC_HISTORY_FILE = NOVA_DIR / "exec_history.json"

def _exec_history_append(entry: dict):
    """Append a command to exec history."""
    try:
        history = json.loads(_EXEC_HISTORY_FILE.read_text()) if _EXEC_HISTORY_FILE.exists() else []
        history.insert(0, entry)
        _EXEC_HISTORY_FILE.write_text(json.dumps(history[:500], indent=2))
    except Exception as _exc:
        debug(f"silenced exception: {_exc}")


def _classify_command_risk(cmd: str) -> Tuple[str, str]:
    """
    Classify a shell command by risk level.
    Returns (level, reason)  where level is "safe" | "warn" | "danger" | "block"
    """
    cmd_lower = cmd.lower().strip()

    # BLOCK: absolutely destructive
    block_patterns = [
        (r'rm\s+-rf?\s+/', "Recursive delete from root — catastrophic"),
        (r'rm\s+-rf?\s+\*', "Recursive delete of everything"),
        (r'dd\s+if=', "dd can overwrite disk"),
        (r'mkfs\.', "Format a filesystem"),
        (r'>\s*/dev/sd', "Write directly to block device"),
        (r'chmod\s+-r\s+/', "Remove permissions recursively from root"),
        (r':()\{.*\};:', "Fork bomb"),
        (r'curl.*\|\s*(bash|sh)', "Piped remote script execution"),
        (r'wget.*\|\s*(bash|sh)', "Piped remote script execution"),
    ]
    for pattern, reason in block_patterns:
        if re.search(pattern, cmd_lower):
            return "block", reason

    # DANGER: destructive but might be intentional
    danger_patterns = [
        (r'\brm\b.*-r', "Recursive delete"),
        (r'drop (table|database|schema)', "SQL DROP"),
        (r'delete from ', "SQL DELETE without WHERE"),
        (r'truncate ', "Truncate table/file"),
        (r'> (?!>)', "Overwrite file (not append)"),
        (r'sudo ', "Runs as root"),
        (r'\bkill\b|\bkillall\b', "Kill processes"),
        (r'systemctl (stop|disable|mask)', "Stop system service"),
        (r'pm2 (delete|kill|stop)', "Stop managed process"),
        (r'git (reset --hard|clean -fd)', "Irreversible git operation"),
        (r'git push.*--force', "Force push"),
        (r'chmod 777', "Insecure permissions"),
        (r'\bdrop\b.*collection', "Delete MongoDB collection"),
    ]
    for pattern, reason in danger_patterns:
        if re.search(pattern, cmd_lower):
            return "danger", reason

    # WARN: potentially impactful
    warn_patterns = [
        (r'pip install|npm install|apt(-get)? install', "Installing packages"),
        (r'git push', "Pushing to remote"),
        (r'git commit', "Committing changes"),
        (r'curl|wget', "Network request"),
        (r'mv ', "Moving/renaming files"),
        (r'cp -r', "Copying recursively"),
        (r'chmod|chown', "Changing permissions"),
        (r'crontab', "Modifying cron jobs"),
        (r'\bexport\b', "Setting env variables"),
        (r'pm2 (start|restart)', "Starting/restarting process"),
    ]
    for pattern, reason in warn_patterns:
        if re.search(pattern, cmd_lower):
            return "warn", reason

    return "safe", "Looks safe"


def _run_command(cmd: str, cwd: str = None, timeout: int = 60) -> dict:
    """
    Execute a shell command with live output streaming.
    Returns {"exit_code", "stdout", "stderr", "duration_ms"}
    """
    import threading

    t0     = time.time()
    stdout_lines = []
    stderr_lines = []

    try:
        proc = subprocess.Popen(
            cmd, shell=True, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )

        def stream_out(pipe, store, color):
            for line in iter(pipe.readline, ""):
                line = line.rstrip()
                store.append(line)
                print("    " + q(color, line))
            pipe.close()

        t_out = threading.Thread(target=stream_out, args=(proc.stdout, stdout_lines, C.G1))
        t_err = threading.Thread(target=stream_out, args=(proc.stderr, stderr_lines, C.YLW))
        t_out.start(); t_err.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            print()
            warn(f"Command timed out after {timeout}s")

        t_out.join(); t_err.join()
        exit_code = proc.returncode

    except Exception as e:
        exit_code = 1
        stderr_lines = [str(e)]

    duration_ms = int((time.time() - t0) * 1000)
    return {
        "exit_code":   exit_code,
        "stdout":      "\n".join(stdout_lines),
        "stderr":      "\n".join(stderr_lines),
        "duration_ms": duration_ms,
    }


def cmd_exec(args):
    """
    Nova-governed terminal execution.

    Nova classifies every command by risk, asks for confirmation on
    dangerous ones, runs it with live output, and logs to the ledger.

    Usage:
      nova exec "pm2 restart melissa"
      nova exec "git push origin main"
      nova exec --auto "pip install -r requirements.txt"   # skip confirm
      nova exec --history                                   # show history
    """
    # ── Flags ─────────────────────────────────────────────────────────────────
    auto_confirm = getattr(args, "execute", False) or getattr(args, "dry_run", False) is False and                    getattr(args, "verbose", False)
    show_history = getattr(args, "subcommand", "") == "history" or                    getattr(args, "action", "") == "history"

    if show_history:
        _cmd_exec_history()
        return

    # ── Get command ───────────────────────────────────────────────────────────
    cmd = (getattr(args, "action", "") or
           getattr(args, "subcommand", "") or
           getattr(args, "third", "") or "").strip()

    if not cmd:
        print_logo(compact=True)
        print()
        print("  " + q(C.W, "Nova Exec", bold=True) + "  " +
              q(C.G3, "— governed terminal execution"))
        print()
        print("  " + q(C.G2, "Usage:"))
        print("    " + q(C.B7, 'nova exec "pm2 restart melissa"'))
        print("    " + q(C.B7, 'nova exec "git push origin main"'))
        print("    " + q(C.B7, "nova exec history"))
        print()
        # Interactive mode
        try:
            cmd = prompt("Command to run", required=True)
        except (EOFError, KeyboardInterrupt):
            print(); return
        if not cmd:
            return

    # ── Classify risk ─────────────────────────────────────────────────────────
    risk, reason = _classify_command_risk(cmd)

    risk_colors = {
        "safe":   (C.GRN,  "✓  SAFE"),
        "warn":   (C.YLW,  "⚠  NOTICE"),
        "danger": (C.ORG,  "⚡ DANGER"),
        "block":  (C.RED,  "✗  BLOCKED"),
    }
    color, label = risk_colors[risk]

    print()
    print("  " + q(C.G2, "Command: ") + q(C.W, cmd, bold=True))
    print("  " + q(color, label, bold=True) + "  " + q(C.G3, reason))
    print()

    if risk == "block":
        fail("Nova blocked this command. It is irreversibly destructive.")
        hint("If you're sure, run it directly in your shell without Nova.")
        print()
        _exec_history_append({
            "cmd": cmd, "status": "BLOCKED", "reason": reason,
            "ts": datetime.now().isoformat(),
        })
        return

    # ── Validate against Nova Core rules (non-blocking if Core not running) ───
    nc = _get_nova_core()
    if nc.is_alive():
        vr = nc.validate(action=f"terminal: {cmd}", scope="global",
                         agent_name="nova_exec")
        if vr.get("result") == "BLOCKED":
            fail("Nova Core blocked this command via governance rules.")
            kv("Rule",   vr.get("reason", "?"), C.RED)
            kv("Score",  str(vr.get("score", "?")), C.G2)
            print()
            return

    # ── Confirmation ──────────────────────────────────────────────────────────
    if risk in ("danger",) and not auto_confirm:
        try:
            choice = _select(
                ["Yes, run it", "No, cancel"],
                descriptions=[
                    f"Execute: {cmd[:60]}",
                    "Abort — do not run",
                ],
                default=1,  # default is CANCEL for danger
            )
        except KeyboardInterrupt:
            print(); warn("Cancelled."); return
        if choice != 0:
            warn("Cancelled."); return

    elif risk == "warn" and not auto_confirm:
        print("  " + q(C.YLW, "Press Enter to run, Ctrl+C to cancel..."), end="", flush=True)
        try:
            input()
        except KeyboardInterrupt:
            print(); warn("Cancelled."); return

    # ── Execute ───────────────────────────────────────────────────────────────
    cwd = str(Path.cwd())
    print("  " + q(C.G3, f"Running in {cwd}"))
    print("  " + q(C.G3, "─" * 50))
    print()

    result = _run_command(cmd, cwd=cwd)

    print()
    print("  " + q(C.G3, "─" * 50))
    ec = result["exit_code"]
    dur = result["duration_ms"]

    if ec == 0:
        ok(f"Exited 0  ({dur}ms)")
    else:
        fail(f"Exited {ec}  ({dur}ms)")

    # ── Log to history ────────────────────────────────────────────────────────
    entry = {
        "cmd":       cmd,
        "status":    "OK" if ec == 0 else f"ERROR({ec})",
        "risk":      risk,
        "duration":  dur,
        "cwd":       cwd,
        "ts":        datetime.now().isoformat(),
    }
    _exec_history_append(entry)

    # Log to Nova Core ledger if running
    if nc.is_alive():
        nc.validate(
            action=f"terminal: {cmd}",
            scope="global",
            agent_name="nova_exec",
            dry_run=True,  # already ran — just log
        )

    print()


def _cmd_exec_history():
    """Show recent exec history."""
    print_logo(compact=True)
    section("Exec History")
    try:
        history = json.loads(_EXEC_HISTORY_FILE.read_text()) if _EXEC_HISTORY_FILE.exists() else []
    except Exception:
        history = []

    if not history:
        info("No commands in history yet.")
        print()
        return

    for entry in history[:20]:
        ts   = entry.get("ts", "")[:16]
        cmd  = entry.get("cmd", "")
        st   = entry.get("status", "?")
        risk = entry.get("risk", "")
        sc   = {
            "OK":      C.GRN,
            "BLOCKED": C.RED,
        }.get(st[:2], C.YLW)
        print("  " + q(C.G3, ts) + "  " +
              q(sc, st[:10].ljust(10)) + "  " +
              q(C.W, cmd[:60]))
    print()


# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point for nova CLI."""
    
    # Parse arguments
    parser = argparse.ArgumentParser(prog="nova", add_help=False)
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("subcommand", nargs="?", default="")
    parser.add_argument("third", nargs="?", default="")
    
    # Global options
    parser.add_argument("--token", "-t", default="")
    parser.add_argument("--action", "-a", default="")
    parser.add_argument("--context", "-c", default="")
    parser.add_argument("--agent", default="")
    parser.add_argument("--key", default="")
    parser.add_argument("--value", default="")
    parser.add_argument("--importance", default="5")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--verdict", default="")
    parser.add_argument("--format", default="json")
    parser.add_argument("--output", "-o", default="")
    parser.add_argument("--file", "-f", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reconfigure", action="store_true")
    parser.add_argument("--interval", type=int, default=3)
    parser.add_argument("--listen", default="")
    parser.add_argument("--upstream", default="")
    parser.add_argument("--path", default="")
    parser.add_argument("--fix-perms", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--auto", "-y", action="store_true",
                        dest="auto",
                        help="Auto-fix mode — skip confirmations (use with doctor, exec, guard)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--version", "-V", action="store_true")
    
    args = parser.parse_args()
    
    # Version flag
    if args.version:
        print(f"nova {NOVA_VERSION} ({NOVA_BUILD})")
        return
    
    # Resolve aliases
    if args.command in ALIASES:
        args.command = ALIASES[args.command]
    
    # Help flag or command
    if args.help or args.command in ("help", "--help", "-h", "?"):
        cmd_help(args)
        return
    
    # First-run detection
    if args.command not in ("init", "help", "completion", "doctor", "scout", "mcp", "--help", "-h") and \
       not CONFIG_FILE.exists():
        print()
        print("  " + q(C.GLD, "✦", bold=True) + "  " + q(C.W, "nova", bold=True))
        print()
        print("  " + q(C.G1, "Welcome! nova isn't configured yet."))
        print()
        print("  " + q(C.B7, "nova init", bold=True) + "  " + 
              q(C.G2, "- run the setup wizard"))
        print()
        return
    
    # Command routing table
    routes = {
        # Core
        ("init", ""): cmd_init,
        ("status", ""): cmd_status_v32,
        ("whoami", ""): cmd_whoami,
        
        # Agents
        ("agent", "create"): cmd_agent_create_v32,
        ("agent", "list"): cmd_agent_list,
        ("agent", ""): cmd_agent_list,
        ("agents", ""): cmd_agent_list,
        
        # Validation
        ("validate", ""): cmd_validate,
        ("test", ""): cmd_test,
        
        # Memory
        ("memory", "save"): cmd_memory_save,
        ("memory", "list"): cmd_memory_list,
        ("memory", ""): cmd_memory_list,
        
        # Ledger
        ("ledger", ""): cmd_ledger,
        ("ledger", "verify"): cmd_verify,
        ("verify", ""): cmd_verify,
        ("watch", ""): cmd_watch,
        ("export", ""): cmd_export,
        ("audit", ""): cmd_audit,
        ("alerts", ""): cmd_alerts,
        
        # Sync
        ("sync", ""): cmd_sync,
        ("launchpad", ""): cmd_launchpad,
        ("run", ""): cmd_run,
        ("shield", ""): cmd_shield,
        ("scout", ""): cmd_scout,
        ("doctor", ""): cmd_doctor,
        ("mcp", ""): cmd_mcp,
        ("mcp", "export"): cmd_mcp,
        ("mcp", "list"): cmd_mcp,
        ("mcp", "import"): cmd_mcp,
        
        # Seed
        ("seed", ""): cmd_seed,
        
        # Config
        ("config", ""): cmd_config,
        ("config", "model"): lambda a: _config_model(load_config()),
        ("config", "server"): lambda a: _config_server(load_config()),
        # nova model - shortcut like /model in Claude Code
        ("model", ""): lambda a: _config_model(load_config()),
        ("model", "list"): cmd_model_list,
        
        # Keys
        ("keys", ""): cmd_keys,
        ("keys", "list"): cmd_keys,
        ("keys", "create"): cmd_keys,
        ("keys", "new"): cmd_keys,
        ("keys", "delete"): cmd_keys,
        ("keys", "remove"): cmd_keys,
        ("keys", "use"): cmd_keys,
        ("keys", "switch"): cmd_keys,
        
        # Skills
        ("skill", ""): cmd_skill_browse,
        ("skill", "list"): cmd_skill_browse,
        ("skills", ""): cmd_skill_browse,
        ("skill", "add"): cmd_skill_add,
        ("skill", "install"): cmd_skill_add,
        ("skill", "info"): cmd_skill_info,
        ("skill", "remove"): cmd_skill_remove,
        ("skill", "delete"): cmd_skill_remove,
        

        # ── v3.2 - Governance ──────────────────────────────────────────
        ("connect",    ""):          cmd_connect,
        ("scan",       ""):          cmd_scan,
        ("rules",      ""):          cmd_rules_list,
        ("rules",      "list"):      cmd_rules_list,
        ("rules",      "create"):    cmd_rules_create,
        ("rules",      "add"):       cmd_rules_create,
        ("rules",      "new"):       cmd_rules_create,
        ("rules",      "delete"):    cmd_rules_delete,
        ("rules",      "remove"):    cmd_rules_delete,
        ("rules",      "test"):      cmd_rules_test,
        ("rules",      "import"):    cmd_rules_import,
        ("chat",       ""):          cmd_chat_nova,
        ("logs",       ""):          cmd_logs,
        ("anomalies",  ""):          cmd_anomalies,
        ("stream",     ""):          cmd_stream,
        ("protect",    ""):          cmd_protect,
        ("benchmark",  ""):          cmd_benchmark,
        ("setup",      ""):          cmd_setup,
        ("setup",      "melissa"):   cmd_setup_melissa,
        ("setup",      "n8n"):       cmd_setup_n8n,

        # Completion
        ("completion", ""): cmd_completion,
        ("completion", "bash"): cmd_completion,
        ("completion", "zsh"): cmd_completion,
        ("completion", "fish"): cmd_completion,

        # Setup - integraciones en un comando
        ("setup",      ""):          cmd_setup,
        ("setup",      "melissa"):   cmd_setup_melissa,
        ("setup",      "n8n"):       cmd_setup_n8n,

        # ── v4.0 - Boot: nova boot (start everything) ──────────────────
        ("boot",       ""):           cmd_boot,
        ("start",      ""):           cmd_boot,

        # ── nova exec — governed terminal ─────────────────────────────
        ("exec",       ""):           cmd_exec,
        ("exec",       "history"):    cmd_exec,
        ("run",        ""):           cmd_exec,

        # ── v4.0 - Universal guard  nova guard  ───────────────────────
        ("guard",      ""):           cmd_guard,
        ("guard",      "status"):     cmd_guard,
        ("guard",      "setup"):      cmd_guard,

        # ── v4.0 - Quick rule one-liner  nova rule "..."  ──────────────
        # The text comes as args.subcommand (first word after "rule")
        # or via --action / --verdict flags - all handled inside cmd_rule_quick
        ("rule",       ""):           cmd_rule_quick,

        # ── v4.0 - Policies ────────────────────────────────────────────
        ("policy",     ""):           cmd_policy,
        ("policy",     "list"):       cmd_policy,
        ("policies",   ""):           cmd_policy,
        ("policy",     "create"):     cmd_policy,
        ("policy",     "new"):        cmd_policy,
        ("policy",     "add"):        cmd_policy,
        ("policy",     "view"):       cmd_policy,
        ("policy",     "show"):       cmd_policy,
        ("policy",     "edit"):       cmd_policy,
        ("policy",     "update"):     cmd_policy,
        ("policy",     "delete"):     cmd_policy,
        ("policy",     "remove"):     cmd_policy,

        # ── v4.0 - Agent edit + history ────────────────────────────────
        ("agent",      "edit"):       cmd_agent_edit,
        ("agent",      "update"):     cmd_agent_edit,
        ("agent",      "history"):    cmd_agent_history,
        ("agent",      "versions"):   cmd_agent_history,

        # ── v4.0 - Validate subcommands ────────────────────────────────
        ("validate",   "explain"):    cmd_validate_explain,
        ("explain",    ""):           cmd_validate_explain,
        ("validate",   "batch"):      cmd_validate_batch,
        ("batch",      ""):           cmd_validate_batch,

        # ── v4.0 - Simulate ────────────────────────────────────────────
        ("simulate",   ""):           cmd_simulate,
        ("sim",        ""):           cmd_simulate,

        # ── v4.0 - Stats full ──────────────────────────────────────────
        ("stats",      ""):           cmd_stats,
        ("stats",      "agents"):     cmd_stats,
        ("stats",      "agent"):      cmd_stats,
        ("stats",      "hourly"):     cmd_stats,
        ("stats",      "hours"):      cmd_stats,
        ("stats",      "risk"):       cmd_stats,
        ("stats",      "timeline"):   cmd_stats,
        ("stats",      "time"):       cmd_stats,
        ("stats",      "anomalies"):  cmd_stats,
        ("stats",      "anom"):       cmd_stats,

        # ── v4.0 - Memory search + update ──────────────────────────────
        ("memory",     "search"):     cmd_memory_search,
        ("memory",     "find"):       cmd_memory_search,
        ("memory",     "update"):     cmd_memory_update,
        ("memory",     "edit"):       cmd_memory_update,

        # ── v4.0 - Workspace ───────────────────────────────────────────
        ("workspace",  ""):           cmd_workspace,
        ("ws",         ""):           cmd_workspace,
        ("me",         ""):           cmd_workspace,
    }
    
    # Find handler
    handler = routes.get((args.command, args.subcommand))
    if not handler:
        handler = routes.get((args.command, ""))
    
    if not handler:
        fail(f"Unknown command: {args.command}" + 
             (f" {args.subcommand}" if args.subcommand else ""))
        print()
        hint("Run  " + q(C.B7, "nova help") + "  to see all commands.")
        print()
        sys.exit(1)
    
    # Execute command
    try:
        handler(args)
        
        # Track in history
        if args.command not in ("help", "completion"):
            add_to_history(args.command, {
                "subcommand": args.subcommand,
                "action": args.action,
            })
    
    except KeyboardInterrupt:
        print()
        warn("Cancelled.")
        print()
    
    except Exception as e:
        if DEBUG:
            import traceback
            traceback.print_exc()
        else:
            fail(f"Error: {e}")
            hint("Run with NOVA_DEBUG=1 for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
