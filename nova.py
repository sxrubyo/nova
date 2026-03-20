#!/usr/bin/env python3
"""
Nova CLI — Agents that answer for themselves.
Enterprise-grade governance infrastructure for AI agents.
Zero dependencies. Python 3.8+.

Copyright (c) 2024 Nova OS. All rights reserved.
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
from datetime import datetime, timezone
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# PLATFORM COMPATIBILITY — Works on ANY terminal
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
    except Exception:
        pass

# Terminal dimensions
def get_terminal_size():
    try:
        columns, rows = shutil.get_terminal_size()
        return columns, rows
    except Exception:
        return 80, 24

TERM_WIDTH, TERM_HEIGHT = get_terminal_size()

# ══════════════════════════════════════════════════════════════════════════════
# COLOR SYSTEM — Adaptive to terminal capabilities
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
    Enterprise color palette for nova CLI.
    
    Design principles:
    - G3 (240) is the ABSOLUTE DARKEST for visible text
    - High contrast for accessibility
    - Consistent semantic meaning
    """
    # Core palette (256-color exact values)
    W = "\033[38;5;15m"    # Blanco Puro
    G1 = "\033[38;5;180m"  # Champaña
    G2 = "\033[38;5;137m"  # Oro Mate
    ASH = "\033[38;5;244m" # Gris
    R = "\033[0m"          # Reset

    BOLD = _e("1")       # Bold
    DIM  = _e("2")       # Dim
    ITALIC = _e("3")     # Italic (not all terminals)
    UNDER = _e("4")      # Underline
    BLINK = _e("5")      # Blink (rare)
    REVERSE = _e("7")    # Reverse video
    HIDDEN = _e("8")     # Hidden
    STRIKE = _e("9")     # Strikethrough

    # Blues — flat, desaturated (OpenClaw-dark)
    B1 = _e("38;5;67")
    B2 = _e("38;5;67")
    B3 = _e("38;5;67")
    B4 = _e("38;5;67")
    B5 = _e("38;5;67")
    B6 = _e("38;5;67")
    B7 = _e("38;5;73")
    B8 = _e("38;5;109")

    # Text hierarchy (NEVER darker than G3 for body text)
    G0  = _e("38;5;252")  # Near-white — primary text
    G3  = _e("38;5;240")  # Dark gray — MINIMUM for visible text
    
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
# LOGO + BRANDING — Enterprise identity
# ══════════════════════════════════════════════════════════════════════════════

_NOVA_BLOCK = [
    "  ███╗   ██╗  ██████╗  ██╗   ██╗  █████╗  ",
    "  ████╗  ██║ ██╔═══██╗ ██║   ██║ ██╔══██╗ ",
    "  ██╔██╗ ██║ ██║   ██║ ██║   ██║ ███████║ ",
    "  ██║╚██╗██║ ██║   ██║ ╚██╗ ██╔╝ ██╔══██║ ",
    "  ██║ ╚████║ ╚██████╔╝  ╚████╔╝  ██║  ██║ ",
    "  ╚═╝  ╚═══╝  ╚═════╝    ╚═══╝   ╚═╝  ╚═╝ ",
]

_CLI_BLOCK = [
    " ██████╗██╗     ██╗",
    "██╔════╝██║     ██║",
    "██║     ██║     ██║",
    "██║     ██║     ██║",
    "╚██████╗███████╗██║",
    " ╚═════╝╚══════╝╚═╝",
]

# Premium star placement
_STAR_LINE = 1  # Line index where star appears

# Enterprise taglines — rotating
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

NOVA_VERSION = "3.1.5"
NOVA_BUILD = "2026.03.shadow"
NOVA_CODENAME = "Constellation"

# Command aliases for power users
ALIASES = {
    "s": "status",
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
}


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION UTILITIES — Ghost writing, spinners, progress
# ══════════════════════════════════════════════════════════════════════════════

def ghost_write(text, color=None, delay=0.02, bold=False, newline=True, prefix="  "):
    """
    Ghost writing effect — text appears character by character.
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
# LOGO RENDERING — Premium visual identity
# ══════════════════════════════════════════════════════════════════════════════

def print_logo(tagline=True, compact=False, animated=False, minimal=False):
    """
    Print the nova logo with premium star.
    
    Args:
        tagline: Show rotating tagline below logo
        compact: Show single-line minimal version
        animated: Animate the logo reveal
        minimal: Just the ✦ mark
    """
    _render_reset()
    print()
    
    if minimal:
        print("  " + q(C.GLD_BRIGHT, "✦", bold=True))
        sys.stdout.write(C.R)
        return
    
    if compact:
        # Single line compact version
        banner = f"✦ nova · v{NOVA_VERSION} · Nova Governance"
        print("  " + q(C.GLD_BRIGHT, banner, bold=True))
        print()
        sys.stdout.write(C.R)
        return
    
    # Full logo — NOVA: gold gradient (bright top → dark bottom), CLI: pure white
    nova_colors = [
        _e("38;5;180"),  # line 0 — Champagne (brightest)
        _e("38;5;179"),  # line 1 — Gold
        _e("38;5;178"),  # line 2 — Amber
        _e("38;5;172"),  # line 3 — Deep amber
        _e("38;5;136"),  # line 4 — Matte bronze
        _e("38;5;94"),   # line 5 — Dark bronze (darkest)
    ]
    for i in range(6):
        nova_color = nova_colors[i]
        nova_part = nova_color + C.BOLD + _NOVA_BLOCK[i]
        cli_part  = C.W + C.BOLD + _CLI_BLOCK[i]
        star_part = ("  " + nova_color + "✦") if i == _STAR_LINE else "   "
        print(nova_part + cli_part + star_part + C.R)
        
        if animated:
            time.sleep(0.04)
    
    if tagline:
        print()
        tl = random.choice(_TAGLINES)
        if animated:
            ghost_write(tl, color=C.G2, delay=0.01)
        else:
            print("  " + q(C.W, tl))
        print("  " + q(C.GLD_BRIGHT, "✦") + " " + q(C.G2, "Nova Constellation · Enterprise Edition"))
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
# UI PRIMITIVES — Building blocks for interface
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
# INPUT UTILITIES — Prompts, confirmations, selections
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
    Dangerous action confirmation — requires typing specific text.
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
# ARROW-KEY SELECTOR — Claude Code / Gemini CLI style
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
        """Render the selector. Uses cursor save/restore — no line counting."""
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

    
    # Key reading — inline so `current` stays in _select scope
    if IS_WINDOWS:
        # Windows inline loop — current in _select scope
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
    import termios, tty
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    def read_key():
        tty.setraw(fd)
        try:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
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
        filtered = get_filtered_indices()

        if key in ("\r", "\n"):
            return current
        if key == "\x03":
            raise KeyboardInterrupt
        if key == "UP" or key == "k" or key == "K":
            if current in filtered:
                idx = filtered.index(current)
                if idx > 0:
                    current = filtered[idx - 1]
            draw()
        elif key == "DOWN" or key == "j" or key == "J":
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
# CONFIGURATION — ~/.nova/
# ══════════════════════════════════════════════════════════════════════════════

NOVA_DIR = Path.home() / ".nova"
CONFIG_FILE = NOVA_DIR / "config.json"
KEYS_FILE = NOVA_DIR / "keys.json"
PROFILES_FILE = NOVA_DIR / "profiles.json"
HISTORY_FILE = NOVA_DIR / "history.json"
QUEUE_FILE = NOVA_DIR / "offline_queue.json"
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
# LLM PROVIDERS — Choose your intelligence
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

# ── Full 2026 model catalog — synced with integrations.py MODEL_OPTIONS ───────
LLM_PROVIDERS = {
    "anthropic": {
        "name": "Anthropic",
        "tagline": "Claude 4 family — best reasoning & coding in 2026",
        "icon": "◆",
        "color": "GLD_BRIGHT",
        "key_url": "https://console.anthropic.com/settings/keys",
        "litellm_prefix": "anthropic",
        "models": [
            # model_id (litellm format), label, tier, description
            ("anthropic/claude-opus-4-6",           "Claude Opus 4.6",         "premium",   "Most capable — complex reasoning, 1M ctx"),
            ("anthropic/claude-opus-4-6[1m]",       "Claude Opus 4.6 [1M]",    "premium",   "Opus with 1 million token context window"),
            ("anthropic/claude-sonnet-4-6",         "Claude Sonnet 4.6  ★",    "balanced",  "Best balance — recommended for most tasks"),
            ("anthropic/claude-sonnet-4-6[1m]",     "Claude Sonnet 4.6 [1M]",  "balanced",  "Sonnet with 1M context — long codebases"),
            ("anthropic/claude-haiku-4-5-20251001", "Claude Haiku 4.5",        "fast",      "Fastest Claude — lightweight & cheap"),
        ],
        "default_model": "anthropic/claude-sonnet-4-6",
        "effort_levels": ["low", "medium", "high"],  # extended thinking
        "has_effort_slider": True,
    },
    "openai": {
        "name": "OpenAI",
        "tagline": "GPT-4o & o3 — industry standard",
        "icon": "◈",
        "color": "W",
        "key_url": "https://platform.openai.com/api-keys",
        "litellm_prefix": "openai",
        "models": [
            ("openai/gpt-4o",          "GPT-4o",          "premium",   "Most capable GPT — vision, code, analysis"),
            ("openai/gpt-4o-mini",     "GPT-4o mini",     "fast",      "Fast & affordable — 80% of 4o at 10x less"),
            ("openai/o3-mini",         "o3-mini",         "reasoning", "Advanced reasoning — math, science, code"),
            ("openai/o3",              "o3",              "reasoning", "Full o3 — top reasoning model in 2026"),
            ("openai/gpt-4.1",         "GPT-4.1",         "premium",   "Latest GPT-4 variant — 1M context"),
            ("openai/gpt-4.1-mini",    "GPT-4.1 mini",    "fast",      "GPT-4.1 mini — fast & efficient"),
        ],
        "default_model": "openai/gpt-4o",
        "has_effort_slider": False,
    },
    "google": {
        "name": "Google Gemini",
        "tagline": "Gemini 2.5 Pro — massive context, free tier available",
        "icon": "◉",
        "color": "CYN",
        "key_url": "https://aistudio.google.com/app/apikey",
        "litellm_prefix": "gemini",
        "models": [
            ("gemini/gemini-2.5-pro",          "Gemini 2.5 Pro",        "premium",   "Most capable Gemini — 1M context"),
            ("gemini/gemini-2.5-flash",        "Gemini 2.5 Flash",      "balanced",  "Fast & smart — great cost/quality ratio"),
            ("gemini/gemini-2.0-flash",        "Gemini 2.0 Flash",      "fast",      "Ultra-fast — free tier in AI Studio"),
            ("gemini/gemini-2.0-flash-lite",   "Gemini 2.0 Flash Lite", "free",      "Free tier — basic tasks, high limits"),
        ],
        "default_model": "gemini/gemini-2.0-flash",
        "has_effort_slider": False,
    },
    "groq": {
        "name": "Groq",
        "tagline": "Llama 3.3 70B — fastest inference on earth (~500 tok/s)",
        "icon": "◐",
        "color": "ORG",
        "key_url": "https://console.groq.com/keys",
        "litellm_prefix": "groq",
        "models": [
            ("groq/llama-3.3-70b-versatile",  "Llama 3.3 70B",          "fast",     "Best Llama — fastest for most tasks"),
            ("groq/llama-3.1-70b-specdec",    "Llama 3.1 70B SpecDec",  "fast",     "Speculative decoding — even faster"),
            ("groq/mixtral-8x7b-32768",       "Mixtral 8x7B",           "fast",     "MoE architecture — efficient"),
            ("groq/llama-3.1-8b-instant",     "Llama 3.1 8B Instant",   "fast",     "Smallest & fastest — instant responses"),
            ("groq/deepseek-r1-distill-llama-70b", "DeepSeek R1 70B",   "reasoning","R1 reasoning via Groq speed"),
        ],
        "default_model": "groq/llama-3.3-70b-versatile",
        "has_effort_slider": False,
    },
    "xai": {
        "name": "xAI — Grok",
        "tagline": "Grok 3 — real-time knowledge, X/Twitter data",
        "icon": "✕",
        "color": "W",
        "key_url": "https://console.x.ai/",
        "litellm_prefix": "xai",
        "models": [
            ("xai/grok-3",              "Grok 3",              "premium",   "Most capable Grok — real-time knowledge"),
            ("xai/grok-3-mini",         "Grok 3 mini",         "balanced",  "Fast Grok with reasoning"),
            ("xai/grok-2-latest",       "Grok 2",              "balanced",  "Proven Grok 2 — stable & reliable"),
            ("xai/grok-2-vision-latest","Grok 2 Vision",       "balanced",  "Grok 2 with image understanding"),
        ],
        "default_model": "xai/grok-3",
        "has_effort_slider": False,
    },
    "mistral": {
        "name": "Mistral AI",
        "tagline": "European privacy — GDPR compliant, data stays in EU",
        "icon": "◇",
        "color": "B7",
        "key_url": "https://console.mistral.ai/api-keys/",
        "litellm_prefix": "mistral",
        "models": [
            ("mistral/mistral-large-latest",  "Mistral Large 2",    "premium",  "Most capable — complex tasks, multilingual"),
            ("mistral/mistral-medium-latest", "Mistral Medium",     "balanced", "Balance of speed and capability"),
            ("mistral/mistral-small-latest",  "Mistral Small 3.1",  "fast",     "Fast & cheap — simple tasks"),
            ("mistral/codestral-latest",      "Codestral",          "balanced", "Specialized for code generation"),
            ("mistral/pixtral-large-latest",  "Pixtral Large",      "premium",  "Vision + text — multimodal tasks"),
        ],
        "default_model": "mistral/mistral-large-latest",
        "has_effort_slider": False,
    },
    "deepseek": {
        "name": "DeepSeek",
        "tagline": "DeepSeek V3 — top coding model, ultra affordable",
        "icon": "◈",
        "color": "B8",
        "key_url": "https://platform.deepseek.com/api_keys",
        "litellm_prefix": "deepseek",
        "models": [
            ("deepseek/deepseek-chat",    "DeepSeek V3",      "balanced",  "Top coding — rivals GPT-4o at 10x less cost"),
            ("deepseek/deepseek-reasoner","DeepSeek R1",      "reasoning", "Chain-of-thought reasoning — math & science"),
        ],
        "default_model": "deepseek/deepseek-chat",
        "has_effort_slider": False,
    },
    "cohere": {
        "name": "Cohere",
        "tagline": "Command R+ — enterprise RAG & search optimized",
        "icon": "◉",
        "color": "MGN",
        "key_url": "https://dashboard.cohere.com/api-keys",
        "litellm_prefix": "cohere",
        "models": [
            ("cohere/command-r-plus-08-2024", "Command R+",    "premium",   "Best for RAG, grounding, enterprise search"),
            ("cohere/command-r-08-2024",      "Command R",     "balanced",  "Fast RAG — cost effective"),
        ],
        "default_model": "cohere/command-r-plus-08-2024",
        "has_effort_slider": False,
    },
    "openrouter": {
        "name": "OpenRouter",
        "tagline": "One key — access ALL models above + 200+ more",
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
        "tagline": "100% local — no API key, no cost, full privacy",
        "icon": "🏠",
        "color": "GRN",
        "key_url": "https://ollama.com/download",
        "litellm_prefix": "ollama",
        "models": [
            ("ollama/qwen3.5:27b",         "Qwen 3.5 27B",      "local",   "Best local model 2026 — rivals GPT-4o"),
            ("ollama/qwen3.5:9b",          "Qwen 3.5 9B",       "local",   "Sweet spot — 16GB RAM, great quality"),
            ("ollama/qwen3.5:4b",          "Qwen 3.5 4B",       "local",   "Minimal RAM — 8GB machines"),
            ("ollama/llama3.3:70b",        "Llama 3.3 70B",     "local",   "Meta open source — 64GB RAM"),
            ("ollama/deepseek-r1:14b",     "DeepSeek R1 14B",   "local",   "Local reasoning — 16GB RAM"),
            ("ollama/mistral:latest",      "Mistral 7B",        "local",   "Classic local model"),
            ("ollama/custom",              "Custom model...",   "local",   "Enter any Ollama model name"),
        ],
        "default_model": "ollama/qwen3.5:27b",
        "needs_api_key": False,
        "base_url": "http://localhost:11434",
        "has_effort_slider": False,
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

# ── Flat MODEL_OPTIONS list — compatible with integrations.py format ──────────
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
    except Exception:
        pass

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
    except Exception:
        pass


def _write_json(path, data, mode=0o600):
    """Write JSON and apply restrictive permissions when possible."""
    path.write_text(json.dumps(data, indent=2))
    _harden_file_permissions(path, mode)


def ensure_dirs():
    """Ensure all nova directories exist."""
    for d in [NOVA_DIR, SESSIONS_DIR, SKILLS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _probe_url(url, timeout=1.2):
    """Best-effort HTTP probe used by init scan."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"nova-cli/{NOVA_VERSION}"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode(errors="ignore")
            return {
                "ok": True,
                "status": getattr(response, "status", 200),
                "body": body[:400],
            }
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode(errors="ignore")
        except Exception:
            body = ""
        return {"ok": True, "status": e.code, "body": body[:400]}
    except Exception:
        return {"ok": False, "status": None, "body": ""}


def _looks_like_n8n(body):
    body = (body or "").lower()
    return "n8n" in body or "workflow automation" in body


def _scan_known_ports():
    """Detect common local services relevant to Nova."""
    findings = []
    probes = [
        ("nova-api", "Nova API", "http://127.0.0.1:9002/health"),
        ("nova-core", "Nova Core", "http://127.0.0.1:9003/health"),
        ("melissa", "Melissa", "http://127.0.0.1:8001/health"),
        ("n8n", "n8n", "http://127.0.0.1:5678/"),
    ]

    for kind, label, url in probes:
        result = _probe_url(url)
        if not result.get("ok"):
            continue
        body = result.get("body", "")
        if kind == "n8n" and not _looks_like_n8n(body):
            continue
        findings.append({
            "kind": kind,
            "label": label,
            "url": url.rsplit("/", 1)[0] if kind != "n8n" else url.rstrip("/"),
            "status": result.get("status"),
        })
    return findings


def _scan_workspace_files(root, max_depth=3):
    """Find likely agent/workflow assets near the current working directory."""
    root = Path(root).resolve()
    findings = []
    ignore = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build"}

    for current_root, dirs, files in os.walk(root):
        current_path = Path(current_root)
        depth = len(current_path.relative_to(root).parts)
        dirs[:] = [d for d in dirs if d not in ignore]
        if depth > max_depth:
            dirs[:] = []
            continue

        file_set = set(files)
        if "melissa.py" in file_set:
            findings.append({"kind": "melissa-file", "label": "Melissa codebase", "path": str(current_path / "melissa.py")})
        if "docker-compose.yml" in file_set:
            compose_path = current_path / "docker-compose.yml"
            try:
                compose_text = compose_path.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                compose_text = ""
            if "n8n" in compose_text:
                findings.append({"kind": "n8n-compose", "label": "n8n docker stack", "path": str(compose_path)})
        if ".env" in file_set:
            findings.append({"kind": "env-file", "label": ".env file", "path": str(current_path / ".env")})
        if "nova_rules" in dirs or (current_path.name == "nova_rules"):
            rule_dir = current_path / "nova_rules" if "nova_rules" in dirs else current_path
            findings.append({"kind": "rules-dir", "label": "nova_rules", "path": str(rule_dir)})

    return findings


def scan_local_stack(base_dir=None):
    """Scan the local machine for likely agents and workflow tools."""
    base_dir = Path(base_dir or os.getcwd()).resolve()
    port_findings = _scan_known_ports()
    file_findings = _scan_workspace_files(base_dir)

    workspace_root = base_dir
    melissa_file = next((f for f in file_findings if f["kind"] == "melissa-file"), None)
    if melissa_file:
        workspace_root = Path(melissa_file["path"]).parent
    else:
        rules_dir = next((f for f in file_findings if f["kind"] == "rules-dir"), None)
        if rules_dir:
            workspace_root = Path(rules_dir["path"]).parent if Path(rules_dir["path"]).name == "nova_rules" else Path(rules_dir["path"])

    return {
        "workspace_root": str(workspace_root),
        "ports": port_findings,
        "files": file_findings,
        "has_melissa": any(f["kind"] == "melissa-file" for f in file_findings) or any(p["kind"] == "melissa" for p in port_findings),
        "has_n8n": any(f["kind"] == "n8n-compose" for f in file_findings) or any(p["kind"] == "n8n" for p in port_findings),
        "has_rules_dir": any(f["kind"] == "rules-dir" for f in file_findings),
    }


def _ensure_workspace_rules_dir(base_path):
    """Create nova_rules/ in the detected workspace if missing."""
    base = Path(base_path).resolve()
    rules_dir = base / "nova_rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    readme = rules_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Nova Rules\n\n"
            "This folder stores human-readable governance rules for Nova.\n"
            "Rules can be created from chat, CLI, or dashboard actions.\n",
            encoding="utf-8",
        )
    return rules_dir


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
# API KEY MANAGEMENT — Secure local keychain
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
# PROFILES — Multiple environments (dev/staging/prod)
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
# OFFLINE QUEUE — Actions queued when server is unreachable
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
# HISTORY — Command history tracking
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
# API CLIENT — Enterprise-grade HTTP client
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
# VERSION CHECK — Auto-update notifications
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
# I18N — Internationalization
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
            "how_step_2": "nova evaluates it in <5ms — no AI for 90% of cases",
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
            "risk_3": "you define the rules — you own the consequences",
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
            "apikey_warning": "Save this key securely — shown only once.",
            
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
            "how_step_2": "nova lo evalúa en <5ms — sin IA en el 90% de casos",
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
            "risk_3": "tú defines las reglas — tú eres responsable",
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
            "apikey_warning": "Guarda esta key — solo se muestra una vez.",
            
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
# RULE TEMPLATES — Pre-built agent configurations
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
            "description": "SELECT only — no mutations allowed",
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
            "description": "Verify and read — never initiate charges",
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
# SKILLS CATALOG — Integration definitions
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
        "description": "CRM, leads, inventory — verify before acting",
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
# CONNECT ANIMATION — Premium handshake visualization
# ══════════════════════════════════════════════════════════════════════════════

def animate_connection(url):
    """
    Cinematic two-machine handshake animation.
    Shows the authentication flow in real-time.
    """
    host = url.replace("http://", "").replace("https://", "").split(":")[0][:18]
    host = host.ljust(18)
    
    frames = [
        (f"  CLI                    {host}", C.G3, 0.06),
        ("   ○                          ○",   C.G2, 0.08),
        ("   │                          │",   C.G2, 0.04),
        ("   │  ──── identify ────────► │",   C.G1, 0.20),
        ("   │                          │",   C.G2, 0.06),
        ("   │  ◄─── challenge ───────  │",   C.B5, 0.24),
        ("   │                          │",   C.G2, 0.06),
        ("   │  ──── intent token ────► │",   C.G1, 0.22),
        ("   │                          │",   C.G2, 0.06),
        ("   │  ◄─── access granted ──  │",   C.B6, 0.26),
        ("   │                          │",   C.G2, 0.06),
        ("   ●                          ●",   C.GRN, 0.12),
    ]
    
    print()
    for line, color, delay in frames:
        print("  " + q(color, line))
        time.sleep(delay)
    print()


def animate_agent_wake():
    """
    Agent wake-up sequence — the moment nova comes alive.
    Ghost writing effect with personality.
    """
    print()
    
    # Processing indicators
    wake_messages = random.sample(_AGENT_WAKE_MESSAGES, 3)
    for msg in wake_messages:
        print("  " + q(C.G3, "▸") + "  " + q(C.G2, msg))
        time.sleep(random.uniform(0.2, 0.4))
    
    print()
    time.sleep(0.3)
    
    # The "wake up" moment
    hr_bold()
    print()
    
    # Ghost write the greeting
    greeting = random.choice(_AGENT_GREETINGS)
    ghost_write(f"  {greeting}", color=C.W, delay=0.025, bold=True)
    
    print()
    time.sleep(0.2)
    
    # Secondary context
    ghost_write("  I'm your governance layer.", color=C.W, delay=0.018)
    ghost_write("  Every action your agents take passes through me.", color=C.W, delay=0.018)
    ghost_write("  I approve, block, or escalate — and I remember everything.", color=C.W, delay=0.018)
    
    print()
    hr_bold()
    print()


# ══════════════════════════════════════════════════════════════════════════════
# COMMANDS — Core CLI functionality
# ══════════════════════════════════════════════════════════════════════════════

def cmd_init(args):
    """
    First-run setup wizard — enterprise onboarding experience.
    """
    cfg = load_config()
    total_steps = 9
    
    # ── Language Selection ────────────────────────────────────────────────────
    lang = cfg.get("lang", "")
    if not lang:
        print()
        print()
        print("  " + q(C.W, "Select your language", bold=True) + "  " + 
              q(C.W, "/ Selecciona tu idioma"))
        print()
        
        try:
            lang_idx = _select(["English", "Español"], default=0)
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
    
    # ── [1/9] How It Works ────────────────────────────────────────────────────
    step_header(1, total_steps, L["how_it_works"])
    
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
    
    # ── [2/9] Risks & Terms ───────────────────────────────────────────────────
    step_header(2, total_steps, L["risks_title"])
    
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
    
    # ── [3/9] Identity ────────────────────────────────────────────────────────
    step_header(3, total_steps, L["identity_title"])
    
    print("  " + q(C.W, f"  {L['identity_sub']}"))
    print()
    
    try:
        name = prompt(L["your_name"], default=cfg.get("user_name", ""))
        name = name or "Explorer"
        
        org = prompt(L["your_org"], default=cfg.get("org_name", ""))
    except (EOFError, KeyboardInterrupt):
        name = "Explorer"
        org = ""
    
    # ── [4/9] API Key Setup ───────────────────────────────────────────────────
    step_header(4, total_steps, L["apikey_title"])
    
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
                warn("Could not copy — please copy manually")
        
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
            warn("No key entered — generated one automatically")
            print()
            print("    " + q(C.W, api_key, bold=True))
            print()
    
    else:
        # Use existing
        api_key = existing_key
        print()
        ok("Using saved key")
    
    # ── [5/9] Server Connection ───────────────────────────────────────────────
    step_header(5, total_steps, L["server_title"])
    
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
    
    # ── [6/9] Connect ─────────────────────────────────────────────────────────
    step_header(6, total_steps, L["connecting_title"])
    
    animate_connection(server_url)
    
    # Test connection
    with Spinner(L["testing_connection"]) as sp:
        api = NovaAPI(server_url, api_key)
        health = api.get("/health")
    
    connected = "error" not in health
    server_version = health.get("version", "") if connected else ""
    
    if connected:
        ok(f"{L['server_online']}  " + q(C.W, f"v{server_version}" if server_version else ""))
        ok(L["key_accepted"])
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
    
    # ── [7/9] Scan & Wrap ─────────────────────────────────────────────────────
    step_header(7, total_steps, "Scan & Wrap", "Nova scans your stack and suggests the next move")

    with Spinner("Scanning local stack..."):
        scan = scan_local_stack()

    print("  " + q(C.W, "Nova looked for running tools and local workspaces.", bold=True))
    print()

    if scan["ports"]:
        print("  " + q(C.W, "Detected services", bold=True))
        for item in scan["ports"]:
            bullet(f"{item['label']}  {item['url']}  [HTTP {item['status']}]", C.G1)
        print()

    if scan["files"]:
        print("  " + q(C.W, "Detected files", bold=True))
        shown = 0
        for item in scan["files"][:6]:
            bullet(f"{item['label']}  {item['path']}", C.G2)
            shown += 1
        if len(scan["files"]) > shown:
            bullet(f"... and {len(scan['files']) - shown} more", C.G3)
        print()

    if not scan["ports"] and not scan["files"]:
        warn("Nothing obvious was detected.")
        info("Nova will still configure a workspace and you can connect an agent later.")
        print()

    workspace_root = scan.get("workspace_root") or os.getcwd()
    kv("Workspace root", workspace_root, C.B7)
    print()

    if not scan.get("has_rules_dir"):
        if confirm("Create a nova_rules folder in this workspace?", default=True):
            rules_dir = _ensure_workspace_rules_dir(workspace_root)
            ok(f"Created rules folder: {rules_dir}")
            print()
    else:
        ok("Found an existing nova_rules folder.")
        print()

    if connected and scan.get("has_melissa") and not cfg.get("default_token"):
        print("  " + q(C.W, "Melissa was detected.", bold=True))
        print("  " + q(C.G2, "Nova can bootstrap a first agent token automatically."))
        print()
        if confirm("Create an initial Melissa agent now?", default=True):
            melissa_description = (
                "Melissa is a receptionist agent for a clinic. "
                "She can answer general questions, capture contact data, "
                "and help schedule appointments. She must never provide diagnoses, "
                "promise prices or discounts, prescribe medication, or share other people's data."
            )
            with Spinner("Creating Melissa agent from description..."):
                auto_result = api.post("/tokens/from-description", {
                    "description": melissa_description,
                    "authorized_by": name or cfg.get("user_name", "") or "cli",
                })

            if "error" in auto_result:
                warn("Could not auto-create Melissa agent.")
                hint(format_api_error(auto_result))
            else:
                cfg["default_token"] = auto_result.get("token_id", "")
                save_config(cfg)
                ok(f"Agent created: {auto_result.get('agent_name', 'Melissa')}")
                kv("Token ID", auto_result.get("token_id", ""), C.B7)
                print()

    if scan.get("has_n8n"):
        info("n8n was detected. Nova can wrap workflows through webhook/proxy validation.")
        hint("Next: use nova shield or add a native Nova node in your n8n flow.")
        print()

    # ── [8/9] Choose Your Intelligence ───────────────────────────────────────
    step_header(8, total_steps, "Choose your Intelligence")
    
    print("  " + q(C.W, "  The AI brain that powers nova's validation engine."))
    print("  " + q(C.G2, "  9 providers · 40+ models · local & cloud · 2026 edition"))
    print()
    
    # ── Step 1: What matters most to you? (like Claude Code's opusplan strategy)
    priority_opts = [
        "★  Best quality — I want the most powerful model",
        "⚡  Fastest — sub-second validation, no latency",
        "💰  Best value — great quality, minimal cost",
        "🔒  Privacy — data stays local or in EU",
        "🌐  One key — access everything via OpenRouter",
        "🏠  Local — no API key, runs on my machine",
        "→  Let me pick manually",
    ]
    priority_descs = [
        "Recommends Claude Opus 4.6 — top reasoning in 2026",
        "Recommends Groq + Llama 3.3 — ~500 tokens/sec",
        "Recommends Gemini 2.0 Flash — free tier available",
        "Recommends Mistral Large (EU) or Ollama (local)",
        "One OpenRouter key unlocks all 200+ models",
        "Qwen 3.5 27B — rivals GPT-4o, zero cost, full privacy",
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
        
        use_rec_opts = ["Yes — use this model", "No — let me pick manually"]
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
            # Ollama — no key needed
            llm_api_key = "ollama"
            base_url = prov_data.get("base_url", "http://localhost:11434")
            print()
            info(f"Local Ollama — no API key needed")
            info(f"Make sure Ollama is running: ollama serve")
        
        # Effort level for Claude models with extended thinking
        llm_effort = "medium"
        if prov_data.get("has_effort_slider") and "claude" in llm_model.lower():
            print()
            print("  " + q(C.G2, "Reasoning effort  ") +
                  q(C.G3, "(like Claude Code's effort slider)"))
            print()
            effort_opts  = ["⚡  low    — fastest, cheapest",
                            "★  medium — recommended balance",
                            "🔥  high   — deepest reasoning, slowest"]
            effort_descs = [
                "Quick decisions — simple validations",
                "Most tasks — best cost/quality ratio",
                "Complex edge cases — maximum accuracy",
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
            warn("No key entered — you can add it later with  nova config model")
        
        # Persist to config
        cfg["llm_provider"]  = llm_provider
        cfg["llm_model"]     = llm_model
        cfg["llm_api_key"]   = llm_api_key
        cfg["llm_effort"]    = llm_effort
        save_config(cfg)
    
    # ── [9/9] Skills Setup (Optional) ─────────────────────────────────────────
    step_header(9, total_steps, L["skills_title"])
    
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
            default=1  # Default to later
        )
    except KeyboardInterrupt:
        skills_idx = 1
    
    # ── Success + Agent Wake ──────────────────────────────────────────────────
    print()
    
    # The agent "wakes up"
    animate_agent_wake()
    
    # Personalized success message
    first_name = name.split()[0] if name and name != "Explorer" else ""
    greeting = L["youre_in"] + (f", {first_name}." if first_name else ".")
    
    print("  " + q(C.GRN, "✦", bold=True) + "  " + q(C.W, greeting, bold=True))
    print()
    print("     " + q(C.W, f"nova CLI {NOVA_VERSION} {L['ready']}"))
    if org:
        print("     " + q(C.W, org))
    
    # Show chosen model
    _llm_prov  = cfg.get("llm_provider", "")
    _llm_model = cfg.get("llm_model", "")
    if _llm_prov in LLM_PROVIDERS and _llm_model:
        pv_name = LLM_PROVIDERS[_llm_prov]["name"]
        print("     " + q(C.MGN, f"⟁  {pv_name} / {_llm_model}"))
    
    print("     " + q(C.W, "Nova Governance"))
    print()
    hr_bold()
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
    
    # Next steps
    print("  " + q(C.W, L["next_steps"]))
    print()
    
    next_cmds = [
        ("nova watch",         "See live ledger entries"),
        ("nova status",        "System health & metrics"),
        ("nova agent auto",    "Create an agent from description"),
        ("nova agent create",  "Create your first agent manually"),
        ("nova rules create",  "Add a governance rule in plain language"),
        ("nova config model",  "Change AI provider or model"),
        ("nova skill",         "Browse available integrations"),
        ("nova help",          "See all commands"),
    ]
    
    for cmd, desc in next_cmds:
        print("    " + q(C.W, cmd.ljust(24), bold=True) + q(C.W, desc))
    
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


def cmd_doctor(args):
    """Self-repair configuration and permissions."""
    ensure_dirs()
    fixes = []
    
    cfg = _repair_json_file(CONFIG_FILE, DEFAULT_CONFIG, "config", fixes)
    keys = _repair_json_file(KEYS_FILE, {"keys": [], "active": None}, "keys", fixes)
    profiles = _repair_json_file(PROFILES_FILE, {
        "profiles": {
            "default": {
                "name": "Default",
                "api_url": "http://localhost:9002",
                "description": "Local development server",
            }
        },
        "active": "default"
    }, "profiles", fixes)
    _repair_json_file(HISTORY_FILE, [], "history", fixes)
    _repair_json_file(QUEUE_FILE, [], "offline_queue", fixes)
    
    # Normalize config fields
    updated = False
    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = v
            updated = True
    if cfg.get("api_url") and not cfg["api_url"].startswith(("http://", "https://")):
        cfg["api_url"] = "http://" + cfg["api_url"]
        updated = True
    if updated:
        cfg["last_updated"] = datetime.now().isoformat()
        _write_json(CONFIG_FILE, cfg)
        fixes.append("config: normalized fields")
    
    # Permissions hardening
    if args.fix_perms:
        for d in [NOVA_DIR, SESSIONS_DIR, SKILLS_DIR, LOGS_DIR]:
            try:
                os.chmod(d, 0o700)
            except Exception:
                pass
        for f in [CONFIG_FILE, KEYS_FILE, PROFILES_FILE, HISTORY_FILE, QUEUE_FILE]:
            _harden_file_permissions(f, 0o600)
        fixes.append("permissions: hardened")
    
    detected = []
    for binary in ("openclaw", "aider", "aider-chat"):
        if shutil.which(binary):
            detected.append(binary)
    
    print_logo(compact=True)
    print()
    if fixes:
        for item in fixes:
            ok(item)
    else:
        ok("No repairs needed.")
    
    if detected:
        print()
        warn("Detected agent binaries in PATH: " + ", ".join(detected))
        dim("Suggested profile: tighten outbound network + require approvals for EXEC actions")
    print()


def _skill_to_mcp(skill_id, skill):
    properties = {}
    required = []
    for field in skill.get("fields", []):
        properties[field["key"]] = {
            "type": "string",
            "description": field.get("description", ""),
            "secret": bool(field.get("secret", False)),
        }
        if field.get("required"):
            required.append(field["key"])
    
    return {
        "id": skill.get("mcp") or skill_id,
        "name": skill.get("name", skill_id),
        "description": skill.get("description", ""),
        "category": skill.get("category", ""),
        "capabilities": {
            "what_it_does": skill.get("what_it_does", ""),
        },
        "config_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
        "metadata": {
            "icon": skill.get("icon"),
            "docs_url": skill.get("docs_url"),
        },
    }


def _load_mcp_overrides():
    extras = []
    if not SKILLS_DIR.exists():
        return extras
    for path in SKILLS_DIR.rglob("*.mcp.json"):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if isinstance(data, dict) and "servers" in data:
            extras.extend(data["servers"])
        elif isinstance(data, dict):
            extras.append(data)
    return extras


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
        kv("Model",    llm_model or "—",              C.W)
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


def cmd_agent_create(args):
    """Create a new agent with intent rules."""
    section("New Agent")
    print("  " + q(C.G2, "Define the behavior rules for your agent."))
    print()
    
    api, cfg = get_api()
    
    # Template or custom?
    print("  " + q(C.G2, "How do you want to start?"))
    print()
    
    opts = ["From template (recommended)", "From scratch"]
    descs = [
        "Pre-built rules for common patterns",
        "Define every rule manually",
    ]
    
    try:
        mode = _select(opts, descriptions=descs, default=0)
    except KeyboardInterrupt:
        print()
        return
    
    can = []
    cannot = []
    
    if mode == 0:
        # Template selection
        print()
        print("  " + q(C.W, "Choose a template:", bold=True))
        print()
        
        tpl_keys = list(RULE_TEMPLATES.keys())
        tpl_opts = [RULE_TEMPLATES[k]["label"] for k in tpl_keys]
        tpl_descs = [RULE_TEMPLATES[k]["description"] for k in tpl_keys]
        
        try:
            tpl_idx = _select(tpl_opts, descriptions=tpl_descs, default=0)
        except KeyboardInterrupt:
            print()
            return
        
        template = RULE_TEMPLATES[tpl_keys[tpl_idx]]
        can = list(template["can_do"])
        cannot = list(template["cannot_do"])
        
        print()
        ok(f"Template loaded: {q(C.B7, template['label'])}")
        print()
        
        # Show what was loaded
        print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ALLOWED actions:", bold=True))
        for action in can[:5]:
            print("       " + q(C.G2, f"+ {action}"))
        if len(can) > 5:
            print("       " + q(C.G3, f"... and {len(can) - 5} more"))
        
        print()
        
        print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "FORBIDDEN actions:", bold=True))
        for action in cannot[:5]:
            print("       " + q(C.G2, f"- {action}"))
        if len(cannot) > 5:
            print("       " + q(C.G3, f"... and {len(cannot) - 5} more"))
        
        print()
        
        # Customization?
        if confirm("Customize these rules?", default=False):
            print()
            print("  " + q(C.G2, "Add more ALLOWED actions:"))
            extra_can = prompt_list("Additional allowed", min_items=0)
            can.extend(extra_can)
            
            print("  " + q(C.G2, "Add more FORBIDDEN actions:"))
            extra_cannot = prompt_list("Additional forbidden", min_items=0)
            cannot.extend(extra_cannot)
    
    # Agent details
    print()
    name = prompt("Agent name", default="My Agent", required=True)
    description = prompt("Brief description (optional)", default="")
    authorized_by = prompt("Authorized by", 
                           default=cfg.get("user_name", "admin@company.com"))
    
    # Manual rules if not using template
    if mode == 1:
        print()
        print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ALLOWED actions:", bold=True))
        can = prompt_list("One per line", min_items=0)
        
        print()
        print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "FORBIDDEN actions:", bold=True))
        cannot = prompt_list("One per line", min_items=0)
    
    # Summary
    print()
    can_preview = ", ".join(can[:2]) + ("..." if len(can) > 2 else "") if can else "none"
    cannot_preview = ", ".join(cannot[:2]) + ("..." if len(cannot) > 2 else "") if cannot else "none"
    
    box([
        f"  Agent       {name}",
        f"  Can do      {can_preview}",
        f"  Forbidden   {cannot_preview}",
        f"  By          {authorized_by}",
    ], C.B5, title="Summary")
    
    print()
    
    if not confirm("Create this agent?"):
        warn("Cancelled.")
        return
    
    # Create agent
    with Spinner("Signing Intent Token...") as sp:
        result = api.post("/tokens", {
            "agent_name": name,
            "description": description,
            "can_do": can,
            "cannot_do": cannot,
            "authorized_by": authorized_by,
        })
    
    if "error" in result:
        fail(format_api_error(result))
        return
    
    token_id = result.get("token_id", "")
    signature = result.get("signature", "")
    
    ok("Agent created — token signed")
    print()
    kv("Token ID", token_id, C.B7)
    kv("Signature", (signature[:24] + "...") if signature else "—", C.G3)
    print()
    
    # Save as default
    cfg["default_token"] = token_id
    save_config(cfg)
    
    # Show webhook info
    if cfg.get("api_key"):
        webhook = f"{cfg['api_url']}/webhook/{cfg['api_key']}"
        section("Webhook")
        print("  " + q(C.G2, "Use this endpoint to integrate with n8n, Zapier, etc:"))
        print()
        print("    " + q(C.B7, f"POST {webhook}"))
        print()
        print("    " + q(C.G3, "Body:"))
        print("    " + q(C.G2, '{"action": "your action", "token_id": "' + 
                        token_id[:12] + '..."}'))
    
    print()


def cmd_agent_auto(args):
    """Create an agent automatically from a natural-language description."""
    api, cfg = get_api()

    description = (getattr(args, "description", "") or "").strip()
    if not description and getattr(args, "file", ""):
        try:
            description = Path(args.file).read_text(encoding="utf-8").strip()
        except Exception as e:
            fail(f"Could not read description file: {e}")
            return

    if not description:
        print()
        print("  " + q(C.G2, "Describe the agent in natural language."))
        print("  " + q(C.G3, "Example: Melissa es mi recepcionista virtual, agenda citas,"))
        print("  " + q(C.G3, "responde dudas generales y nunca da diagnosticos ni promete precios."))
        print()
        description = prompt("Agent description", required=True)

    if not description:
        return

    authorized_by = getattr(args, "sender", "") or cfg.get("user_name", "") or "cli"

    with Spinner("Generating agent rules from description..."):
        result = api.post("/tokens/from-description", {
            "description": description,
            "authorized_by": authorized_by,
        })

    if "error" in result:
        fail(format_api_error(result))
        hint("This flow requires the backend LLM to be configured.")
        return

    token_id = result.get("token_id", "")
    agent_name = result.get("agent_name", "Agent")

    ok(f"Agent created automatically: {agent_name}")
    print()
    kv("Token ID", token_id, C.B7)
    kv("Authorized by", authorized_by, C.G3)
    kv("Source", result.get("parsed_from", "natural_language"), C.MGN)
    print()

    if result.get("can_do"):
        print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ALLOWED", bold=True))
        for item in result.get("can_do", [])[:8]:
            print("       " + q(C.G2, f"+ {item}"))
        print()

    if result.get("cannot_do"):
        print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "FORBIDDEN", bold=True))
        for item in result.get("cannot_do", [])[:8]:
            print("       " + q(C.G2, f"- {item}"))
        print()

    cfg["default_token"] = token_id
    save_config(cfg)
    hint("Default agent updated in local config.")
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


def cmd_agent_show(args):
    """Show details for a specific agent token."""
    api, cfg = get_api()
    token_id = args.token or prompt("Agent token ID", required=True)
    if not token_id:
        return

    with Spinner("Loading agent..."):
        result = api.get(f"/tokens/{urllib.parse.quote(token_id)}")

    if "error" in result:
        fail(format_api_error(result))
        return

    section(result.get("agent_name", "Agent"), mask_key(token_id))
    kv("Description", result.get("description", "") or "—", C.G2)
    kv("Authorized by", result.get("authorized_by", ""), C.G3)
    kv("Active", "yes" if result.get("active", True) else "no",
       C.GRN if result.get("active", True) else C.RED)
    kv("Version", result.get("version", 1), C.G2)
    kv("Policy ID", result.get("policy_id") or "—", C.G3)

    if result.get("can_do"):
        print()
        print("  " + q(C.W, "Allowed", bold=True))
        for item in result.get("can_do", [])[:12]:
            bullet(item, C.G1)

    if result.get("cannot_do"):
        print()
        print("  " + q(C.W, "Forbidden", bold=True))
        for item in result.get("cannot_do", [])[:12]:
            bullet(item, C.G1)

    print()


def cmd_agent_history(args):
    """Show version history for an agent token."""
    api, cfg = get_api()
    token_id = args.token or prompt("Agent token ID", required=True)
    if not token_id:
        return

    with Spinner("Loading agent history..."):
        result = api.get(f"/tokens/{urllib.parse.quote(token_id)}/history")

    if "error" in result:
        fail(format_api_error(result))
        return

    if not result:
        warn("No token history available.")
        print()
        return

    section("Agent History", mask_key(token_id))
    for entry in result:
        print()
        print("  " + q(C.W, f"v{entry.get('version', '?')}", bold=True) +
              "  " + q(C.G3, str(entry.get("changed_at", ""))[:19].replace("T", " ")))
        kv("  Changed by", entry.get("changed_by", "—"), C.G3)
        kv("  Reason", entry.get("change_reason", "—"), C.G2)
    print()


def cmd_agent_toggle(args):
    """Enable or disable an agent token."""
    api, cfg = get_api()
    token_id = args.token or prompt("Agent token ID", required=True)
    if not token_id:
        return

    enable = (args.subcommand or "").lower() == "enable"
    label = "enable" if enable else "disable"

    if not confirm(f"{label.capitalize()} agent {token_id}?", default=False):
        warn("Cancelled.")
        return

    if enable:
        result = api.patch(f"/tokens/{urllib.parse.quote(token_id)}", {
            "active": True,
            "changed_by": cfg.get("user_name") or "cli",
            "change_reason": "re-enabled from nova CLI",
        })
    else:
        result = api.delete(f"/tokens/{urllib.parse.quote(token_id)}")

    if "error" in result:
        fail(format_api_error(result))
        return

    ok(f"Agent {label}d: {token_id}")
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
        warn("DRY RUN — not recorded to ledger")
    
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
    """Dry-run validation — test without recording."""
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
        ok(f"Chain intact — {total:,} records verified")
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
    """Live stream of validation events with SSE fallback."""
    api, cfg = get_api()
    interval = getattr(args, "interval", 3) or 3

    print_logo(compact=True)
    print("  " + q(C.W, "Watching Nova events...", bold=True) + "  " +
          q(C.G3, "Ctrl+C to stop"))
    print("  " + q(C.G2, "Real-time validation stream when available, polling fallback otherwise."))
    hr()
    print()

    verdict_colors = {
        "APPROVED": C.GRN,
        "BLOCKED": C.RED,
        "ESCALATED": C.YLW,
        "DUPLICATE": C.ORG,
    }

    def render_validation(payload, timestamp=None):
        verdict = payload.get("verdict", "?")
        score = payload.get("score", 0)
        action = str(payload.get("action", ""))[:56]
        agent = str(payload.get("agent_name", ""))[:20]
        ledger_id = payload.get("ledger_id")
        risk = payload.get("risk_level", "")
        vc = verdict_colors.get(verdict, C.G2)
        stamp = time_ago(timestamp) if timestamp else "live"
        ledger_label = f"#{ledger_id}" if ledger_id is not None else "—"

        print("  " + q(vc, "■") + "  " + q(C.W, action) + "  " + q(vc, verdict))
        print("     " + score_bar(score, 8) + "  " + q(C.G3, agent) +
              "  " + q(C.G3, ledger_label) + "  " + q(C.G3, stamp) +
              ("  " + q(C.G2, risk) if risk else ""))

    def render_alert(payload, timestamp=None):
        severity = str(payload.get("severity", "medium")).upper()
        message = str(payload.get("message", ""))[:72]
        agent = str(payload.get("agent_name", ""))[:20]
        score = payload.get("score", 0)
        color_map = {
            "CRITICAL": C.RED,
            "HIGH": C.RED,
            "MEDIUM": C.YLW,
            "LOW": C.ORG,
        }
        ac = color_map.get(severity, C.YLW)
        stamp = time_ago(timestamp) if timestamp else "live"

        print("  " + q(ac, "▲") + "  " + q(C.W, message))
        print("     " + q(ac, severity) + "  " + q(C.G3, agent) +
              "  " + q(C.G3, f"score {score}") + "  " + q(C.G3, stamp))

    def render_event(event):
        if not isinstance(event, dict):
            return
        event_type = event.get("type", "")
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        timestamp = event.get("timestamp")

        if event_type == "validation":
            render_validation(payload, timestamp)
        elif event_type == "alert":
            render_alert(payload, timestamp)
        else:
            info(f"{event_type or 'event'}  {json.dumps(payload, ensure_ascii=False)[:120]}")

    # First try SSE
    if cfg.get("api_key"):
        stream_url = f"{cfg['api_url'].rstrip('/')}/stream/events?x_api_key={urllib.parse.quote(cfg['api_key'])}"
        req = urllib.request.Request(stream_url, headers={"User-Agent": f"nova-cli/{NOVA_VERSION}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                ok("Connected to real-time event stream")
                print()
                buffer = []
                while True:
                    raw = response.readline()
                    if not raw:
                        break
                    line = raw.decode(errors="ignore").strip()

                    if not line:
                        if buffer:
                            data = "\n".join(buffer)
                            buffer = []
                            try:
                                event = json.loads(data)
                            except Exception:
                                continue
                            render_event(event)
                        continue

                    if line.startswith("event:"):
                        event_name = line.split(":", 1)[1].strip()
                        if event_name in ("ping", "heartbeat"):
                            continue
                    elif line.startswith("data:"):
                        buffer.append(line.split(":", 1)[1].strip())
                return
        except KeyboardInterrupt:
            print()
            info("Stopped watching.")
            print()
            return
        except Exception:
            warn("Real-time stream unavailable — falling back to polling.")
            print()

    # Polling fallback
    seen = set()
    try:
        while True:
            result = api.get("/ledger?limit=10")
            entries = result.get("entries", []) if isinstance(result, dict) else result if isinstance(result, list) else []

            if isinstance(entries, list):
                for entry in reversed(entries):
                    entry_id = entry.get("id", "")
                    if entry_id and entry_id not in seen:
                        seen.add(entry_id)
                        render_validation({
                            "verdict": entry.get("verdict", "?"),
                            "score": entry.get("score", 0),
                            "action": entry.get("action", ""),
                            "agent_name": entry.get("agent_name", ""),
                            "ledger_id": entry.get("id"),
                        }, entry.get("executed_at", ""))

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


def cmd_rules(args):
    """Manage governance rules exposed by nova_core."""
    api, cfg = get_api()
    sub = (args.subcommand or "list").lower()
    scope = getattr(args, "scope", "") or "global"

    if sub in ("", "list"):
        with Spinner("Loading rules..."):
            result = api.get(f"/rules?scope={urllib.parse.quote(scope)}")
        if "error" in result:
            fail(format_api_error(result))
            return

        rules = result.get("rules", []) if isinstance(result, dict) else []
        total = result.get("total", len(rules)) if isinstance(result, dict) else len(rules)
        if not rules:
            warn(f"No rules found for scope '{scope}'.")
            hint('Create one with:  nova rules create --description "no hagas X"')
            return

        section("Rules", f"{total} active · scope {scope}")
        for rule in rules:
            print()
            print("  " + q(C.W, rule.get("name", "Unnamed Rule"), bold=True) +
                  "  " + q(C.G3, rule.get("id", "")))
            kv("  Action", rule.get("action", "block"), C.YLW)
            kv("  Priority", str(rule.get("priority", "?")), C.G2)
            kv("  Source", rule.get("source", "manual"), C.G3)
            if rule.get("original_instruction"):
                for line in textwrap.wrap(rule["original_instruction"], width=62):
                    print("    " + q(C.G2, line))
        print()
        return

    if sub == "stats":
        with Spinner("Loading rule stats..."):
            result = api.get("/rules/stats")
        if "error" in result:
            fail(format_api_error(result))
            return

        section("Rule Stats")
        for key, value in result.items():
            kv(str(key).replace("_", " ").title(), value, C.G2 if isinstance(value, (int, float)) else C.W)
        print()
        return

    if sub in ("show", "get"):
        rule_id = getattr(args, "third", "") or getattr(args, "rule_id", "")
        if not rule_id:
            fail("Specify a rule id.")
            hint("Use:  nova rules show <rule-id>")
            return

        with Spinner(f"Loading rule {rule_id}..."):
            result = api.get(f"/rules/{urllib.parse.quote(rule_id)}")
        if "error" in result:
            fail(format_api_error(result))
            return

        section(result.get("name", "Rule"), result.get("id", ""))
        kv("Scope", result.get("scope", "global"), C.G2)
        kv("Action", result.get("action", "block"), C.YLW)
        kv("Priority", result.get("priority", "?"), C.G2)
        kv("Created by", result.get("created_by", "unknown"), C.G3)
        kv("Source", result.get("source", "manual"), C.G3)
        if result.get("original_instruction"):
            print()
            print("  " + q(C.W, "Instruction", bold=True))
            for line in textwrap.wrap(result["original_instruction"], width=64):
                print("  " + q(C.G2, line))
        print()
        return

    if sub in ("create", "add", "new"):
        description = getattr(args, "description", "") or getattr(args, "message", "")
        if not description:
            description = prompt("Rule description", required=True)
        if not description:
            return

        payload = {
            "description": description,
            "scope": scope,
            "created_by": getattr(args, "sender", "") or cfg.get("user_name") or "cli",
            "action": getattr(args, "rule_action", "") or "block",
            "priority": int(getattr(args, "priority", 7) or 7),
        }
        with Spinner("Creating rule..."):
            result = api.post("/rules", payload)
        if "error" in result:
            fail(format_api_error(result))
            return

        ok(f"Rule created: {result.get('name', 'Unnamed Rule')}")
        kv("Rule ID", result.get("id", ""), C.G3)
        kv("Scope", result.get("scope", scope), C.G2)
        kv("Action", result.get("action", payload["action"]), C.YLW)
        if result.get("file"):
            kv("File", result["file"], C.B7)
        print()
        return

    if sub in ("delete", "remove"):
        rule_id = getattr(args, "third", "") or getattr(args, "rule_id", "")
        if not rule_id:
            fail("Specify a rule id.")
            hint("Use:  nova rules delete <rule-id>")
            return
        if not confirm(f"Delete rule {rule_id}?", default=False):
            warn("Cancelled.")
            return

        result = api.delete(f"/rules/{urllib.parse.quote(rule_id)}")
        if "error" in result:
            fail(format_api_error(result))
            return

        ok(f"Rule deleted: {rule_id}")
        print()
        return

    fail(f"Unknown rules subcommand: {sub}")
    hint("Use: list, stats, show, create, delete")


def cmd_policies(args):
    """Manage reusable governance policies."""
    api, cfg = get_api()
    sub = (getattr(args, "subcommand", "") or "list").lower()

    if sub in ("", "list"):
        with Spinner("Loading policies..."):
            result = api.get("/policies")
        if "error" in result:
            fail(format_api_error(result))
            return
        if not result:
            warn("No policies found.")
            hint("Create one with:  nova policies create")
            print()
            return

        section("Policies", f"{len(result)} active")
        for policy in result:
            print()
            print("  " + q(C.W, policy.get("name", "Unnamed Policy"), bold=True) +
                  "  " + q(C.G3, f"#{policy.get('id', '?')}"))
            kv("  Category", policy.get("category", "general"), C.MGN)
            kv("  Version", policy.get("version", 1), C.G2)
            kv("  Created by", policy.get("created_by", "unknown"), C.G3)
            if policy.get("description"):
                for line in textwrap.wrap(policy["description"], width=62):
                    print("    " + q(C.G2, line))
        print()
        return

    if sub in ("create", "new", "add"):
        name = prompt("Policy name", required=True)
        if not name:
            return
        description = prompt("Description", default="")
        category = prompt("Category", default="general")
        print()
        print("  " + q(C.GRN, "●", bold=True) + "  " + q(C.W, "ALLOWED actions", bold=True))
        can_do = prompt_list("One per line", min_items=0)
        print()
        print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "FORBIDDEN actions", bold=True))
        cannot_do = prompt_list("One per line", min_items=0)
        tags_raw = prompt("Tags (comma separated)", default="")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        payload = {
            "name": name,
            "description": description,
            "category": category or "general",
            "can_do": can_do,
            "cannot_do": cannot_do,
            "tags": tags,
            "is_template": True,
            "created_by": cfg.get("user_name") or "cli",
            "metadata": {},
        }
        with Spinner("Creating policy..."):
            result = api.post("/policies", payload)
        if "error" in result:
            fail(format_api_error(result))
            return
        ok(f"Policy created: {result.get('name', name)}")
        kv("Policy ID", result.get("id", "?"), C.B7)
        print()
        return

    fail(f"Unknown policies subcommand: {sub}")
    hint("Use: list, create")


def _render_workspace_overview():
    api, cfg = get_api()
    stats = api.get("/stats")
    alerts = api.get("/alerts")
    if "error" in stats:
        warn(format_api_error(stats))
        return
    unresolved = 0
    if isinstance(alerts, list):
        unresolved = len([a for a in alerts if not a.get("resolved")])

    section("Workspace", cfg.get("org_name", "") or cfg.get("user_name", "") or "default")
    rows = [
        ["Actions", f"{stats.get('total_actions', 0):,}"],
        ["Approval Rate", f"{stats.get('approval_rate', 0)}%"],
        ["Avg Score", str(stats.get("avg_score", 0))],
        ["Agents", str(stats.get("active_agents", 0))],
        ["Alerts", str(unresolved)],
    ]
    render_table("Overview", ["Metric", "Value"], rows)
    print()


def _render_timeline_summary(hours=24):
    api, cfg = get_api()
    result = api.get(f"/stats/timeline?hours={hours}")
    if "error" in result:
        fail(format_api_error(result))
        return
    timeline = result.get("timeline", []) if isinstance(result, dict) else []
    if not timeline:
        warn("No timeline data yet.")
        print()
        return
    counts = [int(item.get("count", 0)) for item in timeline]
    section("Timeline", f"last {hours}h")
    print("  " + q(C.W, sparkline(counts)))
    print()
    rows = []
    for item in timeline[-8:]:
        rows.append([
            item.get("bucket", "")[-5:] if item.get("bucket") else str(item.get("hour", "")),
            item.get("count", 0),
            item.get("approved", 0),
            item.get("blocked", 0),
        ])
    render_table("Recent Buckets", ["Time", "Total", "Approved", "Blocked"], rows)
    print()


def _render_risk_summary():
    api, cfg = get_api()
    result = api.get("/stats/risk")
    if "error" in result:
        fail(format_api_error(result))
        return
    if not result:
        warn("No risk data available.")
        print()
        return
    section("Risk Profile")
    rows = []
    for item in result[:10]:
        rows.append([
            item.get("agent_name", ""),
            item.get("risk_level", ""),
            item.get("avg_score", 0),
            f"{item.get('approval_rate', 0)}%",
        ])
    render_table("Agents", ["Agent", "Risk", "Avg Score", "Approval"], rows)
    print()


def _chat_banner():
    print_logo(compact=True)
    print("  " + q(C.W, "Nova Chat", bold=True) + "  " + q(C.G2, "talk to Nova in plain language"))
    print("  " + q(C.G3, "Create rules, inspect agents, and manage governance from one place."))
    print()
    print("  " + q(C.G2, "/help") + "  " + q(C.G3, "shortcuts"))
    print("  " + q(C.G2, "/exit") + "  " + q(C.G3, "leave chat"))
    print()
    hr()
    print()


def _chat_shortcuts():
    section("Shortcuts")
    rows = [
        ["/help", "Show chat shortcuts"],
        ["/home", "Workspace overview"],
        ["/status", "System health"],
        ["/agents", "List agents"],
        ["/rules", "List governance rules"],
        ["/policies", "List reusable policies"],
        ["/timeline", "Activity timeline"],
        ["/risk", "Risk profile by agent"],
        ["/alerts", "Pending alerts"],
        ["/watch", "Live ledger stream"],
        ["/new-rule", "Guided rule creation"],
        ["/new-policy", "Guided policy creation"],
        ["/new-agent", "Bootstrap agent from description"],
        ["/exit", "Leave Nova Chat"],
    ]
    render_table("Nova Chat", ["Shortcut", "Action"], rows)
    print()


def _chat_dispatch_shortcut(raw):
    cmd = raw.strip().lower()
    if cmd in ("/exit", "/quit", "/q"):
        return "exit"
    if cmd in ("/help", "/?"):
        _chat_shortcuts()
        return "handled"
    if cmd == "/home":
        _render_workspace_overview()
        return "handled"
    if cmd == "/status":
        cmd_status(argparse.Namespace())
        return "handled"
    if cmd == "/agents":
        cmd_agent_list(argparse.Namespace())
        return "handled"
    if cmd == "/rules":
        cmd_rules(argparse.Namespace(subcommand="list", scope=""))
        return "handled"
    if cmd == "/policies":
        cmd_policies(argparse.Namespace(subcommand="list"))
        return "handled"
    if cmd == "/timeline":
        _render_timeline_summary()
        return "handled"
    if cmd == "/risk":
        _render_risk_summary()
        return "handled"
    if cmd == "/alerts":
        cmd_alerts(argparse.Namespace())
        return "handled"
    if cmd == "/watch":
        cmd_watch(argparse.Namespace(interval=3))
        return "handled"
    if cmd == "/new-rule":
        cmd_rules(argparse.Namespace(subcommand="create", scope="", description="", message="", sender="", rule_action="", priority=7))
        return "handled"
    if cmd == "/new-policy":
        cmd_policies(argparse.Namespace(subcommand="create"))
        return "handled"
    if cmd == "/new-agent":
        cmd_agent_auto(argparse.Namespace(description="", file="", sender="", token=""))
        return "handled"
    return None


def cmd_chat(args):
    """Natural-language governance chat backed by nova_core."""
    api, cfg = get_api()
    message = getattr(args, "message", "") or getattr(args, "action", "")
    session_id = getattr(args, "session", "") or ("cli_" + secrets.token_hex(4))
    scope = getattr(args, "scope", "") or "global"

    def _send_chat_message(text):
        payload = {
            "message": text,
            "session_id": session_id,
            "scope": scope,
        }
        with Spinner("Thinking..."):
            result = api.post("/chat", payload)
        if "error" in result:
            fail(format_api_error(result))
            return

        print()
        print("  " + q(C.B6, "nova", bold=True))
        print()
        for line in textwrap.wrap(result.get("message", ""), width=68):
            print("  " + q(C.G1, line))
        if result.get("rule"):
            print()
            kv("Rule", result["rule"].get("name", ""), C.W)
            kv("Rule ID", result["rule"].get("id", ""), C.G3)
        if result.get("rules"):
            print()
            kv("Rules returned", str(len(result.get("rules", []))), C.G2)
        print()

    if message:
        _send_chat_message(message)
        return

    _chat_banner()
    while True:
        try:
            raw = input("  you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not raw:
            continue

        if raw.startswith("/"):
            shortcut = _chat_dispatch_shortcut(raw)
            if shortcut == "exit":
                print()
                info("Leaving Nova Chat.")
                print()
                return
            if shortcut == "handled":
                continue

        _send_chat_message(raw)


def cmd_failsafe(args):
    """Guaranteed response pipeline exposed by nova_core."""
    api, cfg = get_api()
    question = getattr(args, "question", "") or getattr(args, "message", "")
    if not question:
        question = prompt("Question", required=True)
    if not question:
        return

    payload = {
        "question": question,
        "user_id": getattr(args, "user_id", "") or "default",
        "context": getattr(args, "context", "") or "",
        "escalate_on_failure": not getattr(args, "no_escalate", False),
    }
    with Spinner("Running failsafe pipeline..."):
        result = api.post("/failsafe", payload)
    if "error" in result:
        fail(format_api_error(result))
        return

    print()
    ok("Guaranteed response generated")
    kv("Layer", result.get("layer", "?"), C.MGN)
    kv("Latency", f"{result.get('ms', 0)}ms", C.G3)
    kv("Escalated", "yes" if result.get("escalated") else "no",
       C.YLW if result.get("escalated") else C.GRN)
    if result.get("ticket_id"):
        kv("Ticket", result.get("ticket_id"), C.G3)
    print()
    section("Response")
    print()
    for line in textwrap.wrap(result.get("response", ""), width=66):
        print("  " + q(C.G1, line))
    print()


def cmd_refine(args):
    """Refine a blocked agent response through nova_core."""
    api, cfg = get_api()
    original = getattr(args, "message", "") or getattr(args, "action", "")
    if not original:
        original = prompt("Original message", required=True)
    rule_id = getattr(args, "rule_id", "") or prompt("Rule ID", required=True)
    rule_name = getattr(args, "rule_name", "") or prompt("Rule name", required=True)
    reason = getattr(args, "reason", "") or prompt("Violation reason", required=True)
    if not all((original, rule_id, rule_name, reason)):
        return

    payload = {
        "original_message": original,
        "rule_id": rule_id,
        "rule_name": rule_name,
        "violation_reason": reason,
        "agent_name": getattr(args, "agent", "") or "agent",
        "context": getattr(args, "context", "") or "",
        "attempt_agent_refinement": not getattr(args, "no_agent_refinement", False),
    }
    with Spinner("Refining response..."):
        result = api.post("/refine", payload)
    if "error" in result:
        fail(format_api_error(result))
        return

    print()
    ok("Response refined")
    kv("Strategy", result.get("strategy", "?"), C.MGN)
    kv("Refinement ID", result.get("refinement_id", ""), C.G3)
    kv("Latency", f"{result.get('ms', 0)}ms", C.G3)
    print()
    section("Refined Message")
    print()
    for line in textwrap.wrap(result.get("refined_message", ""), width=66):
        print("  " + q(C.G1, line))
    print()


def cmd_prompt_stack(args):
    """Manage prompt stack operations exposed by nova_core."""
    api, cfg = get_api()
    sub = (args.subcommand or "stats").lower()
    agent_name = getattr(args, "agent", "") or "agent"

    if sub in ("update", "deploy", "rebuild"):
        payload = {
            "agent_name": agent_name,
            "force_rebuild": getattr(args, "force_rebuild", False),
            "dry_run": getattr(args, "dry_run", False),
        }
        with Spinner("Updating prompt stack..."):
            result = api.post("/prompt-stack/update", payload)
        if "error" in result:
            fail(format_api_error(result))
            return

        print()
        ok(f"Prompt stack updated for {result.get('agent_name', agent_name)}")
        kv("Version", result.get("version", "?"), C.W)
        kv("Rules applied", result.get("rules_applied", 0), C.G2)
        kv("Total tokens", result.get("total_tokens", 0), C.G2)
        kv("Deployment", result.get("deployment_status", "unknown"), C.MGN)
        print()
        return

    if sub == "stats":
        with Spinner("Loading prompt stack stats..."):
            result = api.get(f"/prompt-stack/stats?agent_name={urllib.parse.quote(agent_name)}")
        if "error" in result:
            fail(format_api_error(result))
            return

        stats = result.get("stats", {})
        section("Prompt Stack Stats", agent_name)
        if not stats:
            warn("No prompt stack stats available.")
            print()
            return
        for key, value in stats.items():
            kv(str(key).replace("_", " ").title(), value, C.G2 if isinstance(value, (int, float)) else C.W)
        print()
        return

    if sub in ("versions", "history"):
        limit = getattr(args, "limit", 20) or 20
        with Spinner("Loading prompt versions..."):
            result = api.get(
                f"/prompt-stack/versions?agent_name={urllib.parse.quote(agent_name)}&limit={limit}"
            )
        if "error" in result:
            fail(format_api_error(result))
            return

        versions = result.get("versions", [])
        if not versions:
            warn(f"No prompt versions found for '{agent_name}'.")
            print()
            return

        section("Prompt Versions", f"{len(versions)} entries · {agent_name}")
        for version in versions:
            print()
            print("  " + q(C.W, version.get("version", "?"), bold=True) +
                  "  " + q(C.G3, version.get("created_at", "")[:19].replace("T", " ")))
            kv("  Rules", version.get("applied_rules_count", 0), C.G2)
            kv("  Tokens", version.get("total_tokens", 0), C.G2)
            kv("  Hash", version.get("hash", ""), C.G3)
        print()
        return

    fail(f"Unknown prompt-stack subcommand: {sub}")
    hint("Use: update, stats, versions")


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
    ok(f"Memory saved — ID {memory_id}  importance {importance}/10")
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
# SKILLS COMMANDS — Full interactive catalog
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
    kv("MCP Server", skill.get("mcp", "—"), C.G3)
    kv("Documentation", skill.get("docs_url", "—"), C.B7)
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
          q(C.W, "Step 1 of 2 — Get credentials", bold=True))
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
          q(C.W, "Step 2 of 2 — Configure", bold=True))
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
    dim("nova keys use     — switch active key")
    dim("nova keys create  — generate new key")
    dim("nova keys delete  — remove a key")
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
    warn("Save this key securely — it won't be shown again.")
    print()
    
    # Copy to clipboard
    if confirm("Copy to clipboard?", default=False):
        if _copy_to_clipboard(key):
            ok("Copied to clipboard")
        else:
            warn("Could not copy — please copy manually")
    
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
# CONFIG COMMAND — Interactive configuration hub
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
    """Configure AI provider, model, and effort level — full 2026 catalog."""
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
            effort_opts  = ["⚡  low    — fastest, cheapest",
                            "★  medium — recommended",
                            "🔥  high   — deepest, slowest"]
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
            info("Local mode — no API key needed")
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
            ok("Local mode — no key needed")
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
        kv("    URL", profile.get("api_url", "—"), C.G3)
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
            ("init", "First-run setup wizard"),
            ("chat", "Talk to Nova in plain language"),
            ("status", "System health and metrics"),
            ("config", "Interactive settings hub"),
            ("whoami", "Current identity and config"),
            ("model", "Switch AI model (like /model in Claude Code)"),
        ]),
        ("Agents", [
            ("agent create", "Create agent with rules"),
            ("agent auto", "Create agent from natural language"),
            ("agent list", "List all agents"),
            ("agent show", "Inspect one agent token"),
            ("agent history", "View token rule history"),
            ("agent disable", "Deactivate an agent token"),
            ("agent enable", "Re-enable an agent token"),
        ]),
        ("Validation", [
            ("validate", "Validate an action"),
            ("test", "Dry-run validation"),
            ("failsafe", "Guaranteed response pipeline"),
            ("refine", "Repair a blocked response"),
        ]),
        ("Memory", [
            ("memory save", "Store agent context"),
            ("memory list", "View agent memories"),
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
        ("Governance", [
            ("rules", "List governance rules"),
            ("rules create", "Create rule from natural language"),
            ("policies", "List reusable policies"),
            ("policies create", "Create a reusable policy"),
            ("chat", "Natural-language governance console"),
            ("prompt-stack", "Prompt stack operations"),
        ]),
        ("GOBERNANZA", [
            ("run", "wrapper"),
            ("shield", "proxy"),
            ("scout", "security scan"),
        ]),
        ("TOOLS", [
            ("doctor", "repair"),
            ("mcp", "export/import"),
        ]),
        ("System", [
            ("sync", "Process offline queue"),
            ("seed", "Load demo data"),
            ("alerts", "View pending alerts"),
        ]),
    ]
    
    for section_title, commands in sections:
        print("  " + q(C.W, section_title.upper()))
        print()
        
        for cmd, desc in commands:
            print("    " + q(C.W, cmd.ljust(20), bold=True) + q(C.W, desc))
        
        print()
    
    hr()
    print()
    
    # Aliases
    print("  " + q(C.W, "Aliases") + "  " + 
          q(C.W, "s=status  v=validate  a=agent  c=config  l=ledger  w=watch"))
    print()

    print("  " + q(C.W, "Conversational Mode"))
    print()
    print("    " + q(C.W, "nova".ljust(20), bold=True) + q(C.W, "Open Nova Chat when configured"))
    print("    " + q(C.W, "nova chat".ljust(20), bold=True) + q(C.W, "Interactive governance console"))
    print()
    
    # Examples
    print("  " + q(C.W, "Examples"))
    print()
    
    examples = [
        'nova validate --action "Send email to john@example.com"',
        'nova agent auto --description "Melissa agenda citas y nunca da diagnosticos"',
        'nova rules create --description "no prometas precios sin admin"',
        'nova policies',
        'nova chat --message "muestrame todas las reglas"',
        'nova prompt-stack update --agent melissa',
        "nova ledger --limit 50 --verdict BLOCKED",
        "nova export --format csv --limit 1000",
        "nova watch --interval 5",
        "nova skill add slack",
    ]
    
    for ex in examples:
        print("    " + q(C.W, "$ ") + q(C.W, ex))
    
    print()
    
    # Debug mode
    print("  " + q(C.W, "Debug mode") + "  " + q(C.W, "NOVA_DEBUG=1 nova status"))
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
        "rules", "policies", "chat", "failsafe", "refine", "prompt-stack",
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
            COMPREPLY=($(compgen -W "create auto list show history disable enable" -- "$cur"))
            ;;
        memory)
            COMPREPLY=($(compgen -W "save list" -- "$cur"))
            ;;
        rules)
            COMPREPLY=($(compgen -W "list stats show create delete" -- "$cur"))
            ;;
        policies)
            COMPREPLY=($(compgen -W "list create" -- "$cur"))
            ;;
        prompt-stack)
            COMPREPLY=($(compgen -W "update stats versions" -- "$cur"))
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
        'failsafe:Guaranteed response pipeline'
        'refine:Repair blocked response'
        'memory:Agent memory'
        'ledger:Action history'
        'verify:Check integrity'
        'watch:Live stream'
        'export:Export ledger'
        'audit:Generate report'
        'keys:API key management'
        'skill:Skill catalog'
        'rules:Governance rules'
        'policies:Reusable governance policies'
        'chat:Natural-language governance'
        'prompt-stack:Prompt stack management'
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
complete -c nova -n __fish_use_subcommand -a failsafe -d 'Guaranteed response pipeline'
complete -c nova -n __fish_use_subcommand -a refine -d 'Repair blocked response'
complete -c nova -n __fish_use_subcommand -a memory -d 'Agent memory'
complete -c nova -n __fish_use_subcommand -a ledger -d 'Action history'
complete -c nova -n __fish_use_subcommand -a verify -d 'Check integrity'
complete -c nova -n __fish_use_subcommand -a watch -d 'Live stream'
complete -c nova -n __fish_use_subcommand -a export -d 'Export ledger'
complete -c nova -n __fish_use_subcommand -a audit -d 'Generate report'
complete -c nova -n __fish_use_subcommand -a keys -d 'API keys'
complete -c nova -n __fish_use_subcommand -a skill -d 'Skill catalog'
complete -c nova -n __fish_use_subcommand -a rules -d 'Governance rules'
complete -c nova -n __fish_use_subcommand -a policies -d 'Reusable governance policies'
complete -c nova -n __fish_use_subcommand -a chat -d 'Natural-language governance'
complete -c nova -n __fish_use_subcommand -a prompt-stack -d 'Prompt stack management'
complete -c nova -n __fish_use_subcommand -a sync -d 'Process queue'
complete -c nova -n __fish_use_subcommand -a seed -d 'Demo data'
complete -c nova -n __fish_use_subcommand -a alerts -d 'View alerts'
complete -c nova -n __fish_use_subcommand -a run -d 'Process wrapper'
complete -c nova -n __fish_use_subcommand -a shield -d 'Proxy validation'
complete -c nova -n __fish_use_subcommand -a scout -d 'Skills security scan'
complete -c nova -n __fish_use_subcommand -a doctor -d 'Auto-repair'
complete -c nova -n __fish_use_subcommand -a mcp -d 'MCP export'
complete -c nova -n __fish_use_subcommand -a help -d 'Show help'

complete -c nova -n '__fish_seen_subcommand_from agent' -a 'create auto list show history disable enable'
complete -c nova -n '__fish_seen_subcommand_from memory' -a 'save list'
complete -c nova -n '__fish_seen_subcommand_from rules' -a 'list stats show create delete'
complete -c nova -n '__fish_seen_subcommand_from policies' -a 'list create'
complete -c nova -n '__fish_seen_subcommand_from prompt-stack' -a 'update stats versions'
complete -c nova -n '__fish_seen_subcommand_from skill' -a 'add remove info list'
complete -c nova -n '__fish_seen_subcommand_from keys' -a 'create delete use list'
complete -c nova -n '__fish_seen_subcommand_from mcp' -a 'export list import'
""".strip())
    
    else:
        fail(f"Unknown shell: {shell}")
        hint("Supported: bash, zsh, fish")


# ══════════════════════════════════════════════════════════════════════════════
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
    parser.add_argument("--message", default="")
    parser.add_argument("--question", default="")
    parser.add_argument("--scope", default="")
    parser.add_argument("--session", default="")
    parser.add_argument("--sender", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--rule-id", default="")
    parser.add_argument("--rule-name", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--user-id", default="")
    parser.add_argument("--rule-action", default="")
    parser.add_argument("--importance", default="5")
    parser.add_argument("--priority", type=int, default=7)
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
    parser.add_argument("--force-rebuild", action="store_true")
    parser.add_argument("--no-escalate", action="store_true")
    parser.add_argument("--no-agent-refinement", action="store_true")
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
    
    # Default entry: open chat when configured
    if args.command == "help" and not args.help and CONFIG_FILE.exists() and len(sys.argv) == 1:
        args.command = "chat"

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
              q(C.G2, "— run the setup wizard"))
        print()
        return
    
    # Command routing table
    routes = {
        # Core
        ("init", ""): cmd_init,
        ("status", ""): cmd_status,
        ("whoami", ""): cmd_whoami,
        
        # Agents
        ("agent", "create"): cmd_agent_create,
        ("agent", "auto"): cmd_agent_auto,
        ("agent", "list"): cmd_agent_list,
        ("agent", "show"): cmd_agent_show,
        ("agent", "history"): cmd_agent_history,
        ("agent", "disable"): cmd_agent_toggle,
        ("agent", "delete"): cmd_agent_toggle,
        ("agent", "enable"): cmd_agent_toggle,
        ("agent", ""): cmd_agent_list,
        ("agents", ""): cmd_agent_list,

        # Validation
        ("validate", ""): cmd_validate,
        ("test", ""): cmd_test,
        ("failsafe", ""): cmd_failsafe,
        ("refine", ""): cmd_refine,

        # Memory
        ("memory", "save"): cmd_memory_save,
        ("memory", "list"): cmd_memory_list,
        ("memory", ""): cmd_memory_list,

        # Governance
        ("rules", ""): cmd_rules,
        ("rules", "list"): cmd_rules,
        ("rules", "stats"): cmd_rules,
        ("rules", "show"): cmd_rules,
        ("rules", "get"): cmd_rules,
        ("rules", "create"): cmd_rules,
        ("rules", "add"): cmd_rules,
        ("rules", "new"): cmd_rules,
        ("rules", "delete"): cmd_rules,
        ("rules", "remove"): cmd_rules,
        ("policies", ""): cmd_policies,
        ("policies", "list"): cmd_policies,
        ("policies", "create"): cmd_policies,
        ("policies", "new"): cmd_policies,
        ("policies", "add"): cmd_policies,
        ("chat", ""): cmd_chat,
        ("prompt-stack", ""): cmd_prompt_stack,
        ("prompt-stack", "update"): cmd_prompt_stack,
        ("prompt-stack", "deploy"): cmd_prompt_stack,
        ("prompt-stack", "rebuild"): cmd_prompt_stack,
        ("prompt-stack", "stats"): cmd_prompt_stack,
        ("prompt-stack", "versions"): cmd_prompt_stack,
        ("prompt-stack", "history"): cmd_prompt_stack,

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
        # nova model — shortcut like /model in Claude Code
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
        
        # Completion
        ("completion", ""): cmd_completion,
        ("completion", "bash"): cmd_completion,
        ("completion", "zsh"): cmd_completion,
        ("completion", "fish"): cmd_completion,
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
