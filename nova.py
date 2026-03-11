#!/usr/bin/env python3
"""
Nova CLI — Agents that answer for themselves.
Zero dependencies. Python 3.8+.
"""

import sys, os, json, time, urllib.request, urllib.error
import urllib.parse, hashlib, argparse, textwrap, random
from datetime import datetime

# Force UTF-8 on Windows (PowerShell uses cp1252 by default)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.system("chcp 65001 >nul 2>&1")

# ══════════════════════════════════════════════════════════════════
# COLOR SYSTEM
# ══════════════════════════════════════════════════════════════════

USE_COLOR = (
    not os.environ.get("NO_COLOR") and
    (os.environ.get("FORCE_COLOR") or
     (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()))
)

def _e(code): return "\033[" + code + "m" if USE_COLOR else ""

class C:
    R    = _e("0")
    BOLD = _e("1")
    DIM  = _e("2")

    # Blues — midnight to electric
    B0 = _e("38;5;17")
    B1 = _e("38;5;18")
    B2 = _e("38;5;19")
    B3 = _e("38;5;20")
    B4 = _e("38;5;21")
    B5 = _e("38;5;27")
    B6 = _e("38;5;33")
    B7 = _e("38;5;39")
    B8 = _e("38;5;45")

    # Neutrals
    W  = _e("38;5;255")
    G1 = _e("38;5;250")
    G2 = _e("38;5;244")
    G3 = _e("38;5;238")
    G4 = _e("38;5;234")
    G5 = _e("38;5;232")

    # Semantic
    GRN = _e("38;5;84")
    YLW = _e("38;5;220")
    RED = _e("38;5;196")
    ORG = _e("38;5;208")


def q(color, text, bold=False):
    b = C.BOLD if bold else ""
    return b + color + str(text) + C.R


# ══════════════════════════════════════════════════════════════════
# LOGO — NOVA azul gradiente + CLI blanco, side by side
# ══════════════════════════════════════════════════════════════════

_NOVA = [
    "  ███╗   ██╗  ██████╗  ██╗   ██╗  █████╗  ",
    "  ████╗  ██║ ██╔═══██╗ ██║   ██║ ██╔══██╗ ",
    "  ██╔██╗ ██║ ██║   ██║ ██║   ██║ ███████║ ",
    "  ██║╚██╗██║ ██║   ██║ ╚██╗ ██╔╝ ██╔══██║ ",
    "  ██║ ╚████║ ╚██████╔╝  ╚████╔╝  ██║  ██║ ",
    "  ╚═╝  ╚═══╝  ╚═════╝    ╚═══╝   ╚═╝  ╚═╝ ",
]
_NOVA_COLORS = [C.B1, C.B2, C.B4, C.B5, C.B6, C.B7]

_CLI = [
    " ██████╗██╗     ██╗",
    "██╔════╝██║     ██║",
    "██║     ██║     ██║",
    "██║     ██║     ██║",
    "╚██████╗███████╗██║",
    " ╚═════╝╚══════╝╚═╝",
]

_TAGLINES = [
    "Agents that answer for themselves.",
    "The layer between intent and chaos.",
    "Your agents, accountable.",
    "What your agents do. Provably.",
    "Where intent becomes law.",
    "Intelligence with limits. Actions with proof.",
    "Every action, signed. Every intent, provable.",
    "The nervous system for autonomous agents.",
]
_tagline = random.choice(_TAGLINES)

NOVA_VERSION = "2.1.0"


def print_logo(tagline=True, compact=False):
    print()
    if compact:
        # One-line mark for sub-screens
        print("  " + q(C.B6, "✦", bold=True) + "  " + q(C.W, "nova", bold=True) +
              q(C.G2, "  ·  CLI " + NOVA_VERSION))
    else:
        for i in range(6):
            nova_part = _NOVA_COLORS[i] + C.BOLD + _NOVA[i] + C.R
            cli_part  = C.W + C.BOLD + _CLI[i] + C.R
            print(nova_part + cli_part)
        if tagline:
            print()
            print("  " + q(C.G2, _tagline))
            print("  " + q(C.G3, "─" * 54))
    print()


def _step_header(n, total, title):
    bar = q(C.B6, "█" * n, bold=True) + q(C.G3, "░" * (total - n))
    print()
    print("  " + bar + "  " + q(C.G2, str(n) + "/" + str(total)) +
          "  " + q(C.W, title, bold=True))
    print("  " + q(C.G3, "─" * 54))
    print()


def _pause(label="continue"):
    print()
    print("  " + q(C.G2, "  ↵  ") + q(C.W, "Press Enter to " + label, bold=False) +
          q(C.G3, " ···"), end="", flush=True)
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print()
    print()


# ══════════════════════════════════════════════════════════════════
# ARROW-KEY SELECTOR  (zero deps, cross-platform)
# ══════════════════════════════════════════════════════════════════

def _select(options, title="", default=0):
    """
    Arrow-key selector. Zero deps. Cross-platform.
    Up/Down arrows  ·  Enter to confirm  ·  j/k vi-style
    Falls back to numbered list when stdin is not a TTY (e.g. curl | bash).
    """
    # Strip any ANSI codes from options for display length calculation
    is_tty = False
    try:
        is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        pass

    # ── Non-interactive fallback (pipe / redirect) ──────────────
    if not is_tty:
        if title:
            print("  " + q(C.G2, title))
        print()
        for i, opt in enumerate(options):
            marker = q(C.B6, "▸", bold=True) if i == default else "  "
            label  = q(C.W, opt, bold=True) if i == default else q(C.G2, opt)
            print("  " + marker + "  " + label)
        print()
        print("  " + q(C.G3, "Select [1-" + str(len(options)) + "]:") + "  ",
              end="", flush=True)
        try:
            v = input().strip()
            if v.isdigit():
                idx = int(v) - 1
                if 0 <= idx < len(options):
                    return idx
        except (EOFError, KeyboardInterrupt):
            pass
        return default

    # ── Draw menu (always in NORMAL terminal mode) ───────────────
    def _draw(current, first=False):
        out = []
        if not first:
            n = (1 if title else 0) + 1 + len(options) + 1
            out.append("\033[" + str(n) + "A\033[J")
        if title:
            out.append("  " + q(C.G2, title) + "\n")
        out.append("\n")
        for i, opt in enumerate(options):
            if i == current:
                out.append("  " + q(C.B6, "▸", bold=True) + "  " +
                            q(C.W, opt, bold=True) + "\n")
            else:
                out.append("     " + q(C.G2, opt) + "\n")
        out.append("\n")
        sys.stdout.write("".join(out))
        sys.stdout.flush()

    # ── Windows ─────────────────────────────────────────────────
    if sys.platform == "win32":
        import msvcrt
        current = default
        _draw(current, first=True)
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                return current
            if ch in ("\x00", "\xe0"):
                ch2 = msvcrt.getwch()
                if   ch2 == "H": current = (current - 1) % len(options)
                elif ch2 == "P": current = (current + 1) % len(options)
            elif ch == "\x03":
                raise KeyboardInterrupt
            _draw(current)
        return current

    # ── Unix / Linux / Mac ───────────────────────────────────────
    import termios, tty

    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    def _read_key():
        """Enter raw mode, read one keypress, restore immediately."""
        tty.setraw(fd)
        try:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if   ch3 == "A": return "UP"
                    elif ch3 == "B": return "DOWN"
                    return ch3
                return ch2
            return ch
        finally:
            # Always restore BEFORE we write anything to screen
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    current = default
    _draw(current, first=True)

    while True:
        key = _read_key()
        if key in ("\r", "\n"):
            return current
        elif key == "\x03":
            raise KeyboardInterrupt
        elif key in ("UP",   "k", "K"):
            current = (current - 1) % len(options)
        elif key in ("DOWN", "j", "J"):
            current = (current + 1) % len(options)
        _draw(current)


def _select_lang():
    """First-run language picker — called before anything else."""
    print()
    print()
    print("  " + q(C.W, "Select your language", bold=True) +
          "  " + q(C.G3, "/ Selecciona tu idioma"))
    print()
    langs = ["English", "Español"]
    idx = _select(langs, default=0)
    return "en" if idx == 0 else "es"


# ══════════════════════════════════════════════════════════════════
# CONNECT ANIMATION  (two machines, starship style)
# ══════════════════════════════════════════════════════════════════

def _animate_connect(url):
    """
    Shows a cinematic two-machine handshake while the real
    connection happens in the background.
    """
    host = url.replace("http://", "").replace("https://", "").split(":")[0][:20]
    pad  = max(0, 20 - len(host))
    srv  = host + " " * pad

    frames = [
        ("  CLI                    " + srv,      C.G3),
        ("   ○                          ○",      C.G2),
        ("   │                          │",      C.G2),
        ("   │  ──── identify ────────► │",      C.G2),
        ("   │                          │",      C.G2),
        ("   │  ◄─── challenge ───────  │",      C.B5),
        ("   │                          │",      C.G2),
        ("   │  ──── intent token ────► │",      C.G2),
        ("   │                          │",      C.G2),
        ("   │  ◄─── access granted ──  │",      C.B6),
        ("   │                          │",      C.G2),
        ("   ●                          ●",      C.GRN),
    ]

    delays = [0.05, 0.08, 0.04, 0.18, 0.04, 0.22,
              0.04, 0.20, 0.04, 0.24, 0.04, 0.10]

    print()
    for (line, color), delay in zip(frames, delays):
        print("  " + q(color, line))
        time.sleep(delay)
    print()


# ══════════════════════════════════════════════════════════════════
# CONFIG — ~/.nova/config.json
# ══════════════════════════════════════════════════════════════════

NOVA_DIR    = os.path.expanduser("~/.nova")
CONFIG_FILE = os.path.join(NOVA_DIR, "config.json")

DEFAULTS = {
    "api_url":       "http://localhost:8000",
    "api_key":       "",
    "default_token": "",
    "version":       "2.0.0",
}


def load_config():
    os.makedirs(NOVA_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            return dict(DEFAULTS, **json.load(open(CONFIG_FILE)))
        except Exception:
            pass
    return dict(DEFAULTS)


def save_config(cfg):
    os.makedirs(NOVA_DIR, exist_ok=True)
    json.dump(cfg, open(CONFIG_FILE, "w"), indent=2)


# ══════════════════════════════════════════════════════════════════
# API CLIENT — urllib puro, zero deps
# ══════════════════════════════════════════════════════════════════

class NovaAPI:
    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key

    def _req(self, method, path, data=None):
        url  = self.url + path
        hdrs = {"Content-Type": "application/json", "x-api-key": self.key}
        body = json.dumps(data).encode() if data else None
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:    return {"error": json.loads(e.read().decode()).get("detail", str(e))}
            except: return {"error": "HTTP " + str(e.code)}
        except urllib.error.URLError:
            return {"error": "Cannot connect to " + self.url + " — run: docker ps"}
        except Exception as e:
            return {"error": str(e)}

    def get(self, p):           return self._req("GET",    p)
    def post(self, p, d):       return self._req("POST",   p, d)
    def delete(self, p):        return self._req("DELETE", p)
    def patch(self, p, d=None): return self._req("PATCH",  p, d or {})


# ══════════════════════════════════════════════════════════════════
# UI PRIMITIVES
# ══════════════════════════════════════════════════════════════════

def ok(msg):   print("  " + q(C.GRN, "✓") + "  " + q(C.W,  msg))
def fail(msg): print("  " + q(C.RED, "✗") + "  " + q(C.W,  msg))
def warn(msg): print("  " + q(C.YLW, "!") + "  " + q(C.G1, msg))
def info(msg): print("  " + q(C.B6,  "·") + "  " + q(C.G1, msg))
def dim(msg):  print("  " + q(C.G3,  " ") + "  " + q(C.G2, msg))


def section(title, subtle=""):
    sub = "  " + q(C.G2, subtle) if subtle else ""
    print()
    print("  " + q(C.W, title, bold=True) + sub)
    print("  " + q(C.G3, "─" * (len(title) + 2)))


def kv(key, val, vc=None):
    vc = vc or C.W
    print("  " + q(C.G2, key.ljust(20)) + "  " + q(vc, str(val)))


def loading(msg):
    print("  " + q(C.B5, "○") + "  " + q(C.G1, msg), end="", flush=True)


def clear_line():
    print("\r\033[K", end="", flush=True)


def score_bar(score, width=18):
    filled = max(0, int((score / 100) * width))
    empty  = width - filled
    c = C.GRN if score >= 70 else (C.YLW if score >= 40 else C.RED)
    bar = c + C.BOLD + ("█" * filled) + C.R + q(C.G3, "░" * empty)
    num = q(c, str(score), bold=True)
    return q(C.G2, "[") + bar + q(C.G2, "]") + " " + num


def verdict_badge(v):
    m = {
        "APPROVED":  (C.GRN, "✓", "APPROVED"),
        "BLOCKED":   (C.RED, "✗", "BLOCKED"),
        "ESCALATED": (C.YLW, "⚠", "ESCALATED"),
        "DUPLICATE": (C.ORG, "⊘", "DUPLICATE"),
    }
    c, sym, label = m.get(v, (C.G2, "·", v))
    return q(c, sym) + "  " + q(c, label, bold=True)


def box(lines, color=None, title=""):
    bc = color or C.G3
    inner_w = max((len(l) for l in lines), default=30) + 4
    w = max(inner_w, len(title) + 6)
    if title:
        tpad = max(0, w - len(title) - 4)
        print("  " + q(bc, "┌─ ") + q(C.G1, title) + " " + q(bc, "─" * tpad + "┐"))
    else:
        print("  " + q(bc, "┌" + "─" * w + "┐"))
    for line in lines:
        pad = max(0, w - len(line) - 2)
        print("  " + q(bc, "│") + " " + q(C.G1, line) + " " * pad + " " + q(bc, "│"))
    print("  " + q(bc, "└" + "─" * w + "┘"))


def prompt(label, default=""):
    hint = " " + q(C.G3, "(" + default + ")") if default else ""
    print("  " + q(C.B6, "?") + "  " + q(C.G1, label) + hint + "  ", end="", flush=True)
    val = input().strip()
    return val or default


def prompt_list(label, hint="empty line to finish"):
    print("  " + q(C.B6, "?") + "  " + q(C.G1, label) + "  " + q(C.G3, "(" + hint + ")"))
    items = []
    while True:
        print("    " + q(C.G3, "+  "), end="", flush=True)
        v = input().strip()
        if not v:
            break
        items.append(v)
    return items


def confirm(label, default=True):
    hint = q(C.G3, "Y/n" if default else "y/N")
    print("  " + q(C.B6, "?") + "  " + q(C.G1, label) + "  " + hint + "  ", end="", flush=True)
    v = input().strip().lower()
    return default if not v else v in ("y", "yes", "s", "si", "sí")


def print_error(r):
    fail(r.get("error", "Unknown error"))


# ══════════════════════════════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════════════════════════════

def cmd_init(args):
    cfg = load_config()

    # ── [0] LANGUAGE ─────────────────────────────────────────────
    lang = cfg.get("lang", "")
    if not lang:
        try:
            lang = _select_lang()
        except KeyboardInterrupt:
            print(); return
        cfg["lang"] = lang
        save_config(cfg)

    L = _i18n(lang)

    # ── SPLASH ────────────────────────────────────────────────────
    print()
    print()
    for i in range(6):
        print(_NOVA_COLORS[i] + C.BOLD + _NOVA[i] + C.R + C.W + C.BOLD + _CLI[i] + C.R)
        time.sleep(0.06)

    print()
    print("  " + q(C.G2, L["tagline"]))
    print("  " + q(C.G3, "─" * 54))
    print()
    time.sleep(0.3)

    print("  " + q(C.W, L["welcome"], bold=True))
    print()
    print("  " + q(C.G1, L["intro1"]))
    print("  " + q(C.G1, L["intro2"]))
    print()
    print("  " + q(C.B7, "  " + L["question"], bold=True))
    print()
    _pause(L["p_continue"])

    # ── [1/5] HOW IT WORKS ───────────────────────────────────────
    _step_header(1, 5, L["h_howworks"])
    # Print how-it-works with colored verdicts
    print("  " + q(C.G2,  "  ┌─  " + L["how1"]))
    print("  " + q(C.G3,  "  │"))
    print("  " + q(C.G1,  "  │   " + L["how_ev"]))
    print("  " + q(C.G3,  "  │"))
    print("  " + q(C.G3,  "  ├─  ") + q(C.GRN, "Score ≥ 70", bold=True) +
          q(C.G2, "   →  ✓  " + L["approved"]))
    print("  " + q(C.G3,  "  ├─  ") + q(C.YLW, "Score 40–70", bold=True) +
          q(C.G2, "  →  ⚠  " + L["escalated"]))
    print("  " + q(C.G3,  "  └─  ") + q(C.RED, "Score < 40", bold=True) +
          q(C.G2, "   →  ✗  " + L["blocked"]))
    print()
    print("  " + q(C.G1, "  " + L["ledger_desc"]))
    print("  " + q(C.G2, "  " + L["ledger_sub"]))
    print()
    _pause(L["p_continue"])

    # ── [2/5] RISKS + T&C ─────────────────────────────────────────
    _step_header(2, 5, L["h_risks"])
    print("  " + q(C.YLW, "  !") + "  " + q(C.W, L["risk_title"], bold=True))
    print("  " + q(C.G1, "     " + L["risk_sub"]))
    print()

    risks = [L["r1"], L["r2"], L["r3"], L["r4"], L["r5"]]
    for r in risks:
        print("  " + q(C.G3, "     ◦  ") + q(C.G1, r))
    print()
    print("  " + q(C.G3, "     " + L["terms_label"] + "  ") + q(C.B6, "https://nova-os.com/terms"))
    print()

    # Arrow-key accept/decline
    print("  " + q(C.G2, "  " + L["terms_q"]))
    print()
    try:
        idx = _select([L["accept"], L["decline"]], default=0)
    except KeyboardInterrupt:
        print(); return

    if idx != 0:
        print()
        warn(L["cancelled"] + "  nova init")
        print()
        return

    # ── [3/5] PERSONALIZATION ─────────────────────────────────────
    _step_header(3, 5, L["h_who"])
    print("  " + q(C.G1, "  " + L["who_sub"]))
    print()
    try:
        name = prompt("  " + L["your_name"], cfg.get("user_name", ""))
        name = name or "Explorer"
    except (EOFError, KeyboardInterrupt):
        name = "Explorer"

    # ── [4/5] SERVER CONFIG ───────────────────────────────────────
    _step_header(4, 5, L["h_server"])
    print("  " + q(C.G1, "  " + L["server_sub"]))
    print()
    print("  " + q(C.G3, "  Docs: ") + q(C.B6, "https://github.com/Santiagorubioads/nova-os"))
    print()
    print("  " + q(C.G2, "  " + L["server_opts"]))
    print()

    # Arrow-key server options
    try:
        srv_idx = _select([
            L["srv_local"],
            L["srv_remote"],
            L["srv_already"],
        ], default=0)
    except KeyboardInterrupt:
        print(); return

    if srv_idx == 0:
        url = "http://localhost:8000"
        print()
        info(L["using"] + " http://localhost:8000")
    elif srv_idx == 1:
        print()
        try:
            url = prompt("  " + L["server_url"], cfg.get("api_url", "http://localhost:8000"))
        except (EOFError, KeyboardInterrupt):
            url = cfg.get("api_url", "http://localhost:8000")
    else:
        url = cfg.get("api_url", "http://localhost:8000")
        print()
        info(L["using"] + " " + url)

    print()
    try:
        import getpass
        print("  " + q(C.B6, "?") + "  " + q(C.G1, "  API Key") + "  ", end="", flush=True)
        key = getpass.getpass("").strip() or cfg.get("api_key", "")
    except (EOFError, KeyboardInterrupt):
        key = cfg.get("api_key", "")

    # ── [5/5] CONNECT ANIMATION ───────────────────────────────────
    _step_header(5, 5, L["h_connecting"])
    _animate_connect(url)

    loading(L["testing"])
    api    = NovaAPI(url, key)
    health = api.get("/health")
    clear_line()

    connected  = "error" not in health
    srv_ver    = health.get("version", "online") if connected else "—"

    if connected:
        ok(L["srv_ok"] + "  · " + q(C.G3, srv_ver))
        ok(L["key_ok"])
    else:
        fail(health.get("error", L["srv_fail"]))
        print()
        warn(L["saved_anyway"] + "  " + q(C.B7, "nova status"))

    cfg.update({"api_url": url, "api_key": key, "user_name": name, "lang": lang})
    save_config(cfg)

    # ── SUCCESS ───────────────────────────────────────────────────
    print()
    print("  " + q(C.G3, "─" * 54))
    print()
    first = name.split()[0] if name and name != "Explorer" else ""
    greeting = L["youre_in"] + (", " + first + "." if first else ".")
    print("  " + q(C.W, greeting, bold=True))
    print()
    print("  " + q(C.G1, "  nova CLI " + L["ready"]))
    print()
    print("  " + q(C.G3, "─" * 54))
    print()

    nexts = [
        ("nova agent create",  L["n1"]),
        ("nova status",        L["n2"]),
        ("nova config",        L["n3"]),
        ("nova skill",         L["n4"]),
    ]
    print("  " + q(C.G2, "  " + L["next_steps"]))
    print()
    for cmd, desc in nexts:
        print("  " + q(C.B7, "  " + cmd.ljust(20), bold=True) + "  " + q(C.G2, desc))
    print()


def _i18n(lang="en"):
    """Returns all UI strings for the given language."""
    strings = {
        "en": {
            "tagline":    random.choice(_TAGLINES),
            "welcome":    "Welcome to nova.",
            "intro1":     "nova sits between your agents and the real world.",
            "intro2":     "Before anything executes, nova asks one question:",
            "question":   "Should this happen?",
            "p_continue": "continue",
            "h_howworks": "How nova works",
            "how1":       "Your agent wants to do something",
            "how_ev":     "nova evaluates it in <5ms  —  no AI for 90% of cases",
            "approved":   "Approved  ·  runs",
            "escalated":  "Escalated  ·  you decide",
            "blocked":    "Blocked  ·  logged forever",
            "ledger_desc":"Every decision lands in the Intent Ledger.",
            "ledger_sub": "Cryptographic. Auditable. Permanent.",
            "h_risks":    "Before we continue",
            "risk_title": "nova is not a sandbox.",
            "risk_sub":   "It makes real decisions about real actions in production.",
            "r1":         "nova may block actions your agents try to execute",
            "r2":         "every validation is recorded permanently in the ledger",
            "r3":         "you define the rules — you own the consequences",
            "r4":         "misconfigured rules can block legitimate work",
            "r5":         "the ledger cannot be deleted or modified",
            "terms_label":"Terms:",
            "terms_q":    "Do you understand and accept?",
            "accept":     "Yes, I accept",
            "decline":    "No, exit",
            "cancelled":  "Setup cancelled. Run",
            "h_who":      "Who are you?",
            "who_sub":    "This personalizes your nova experience.",
            "your_name":  "Your name or organization",
            "h_server":   "Connect to your server",
            "server_sub": "nova CLI talks to a nova server. Self-hosted or cloud.",
            "server_opts":"How do you want to connect?",
            "srv_local":  "Local server  (http://localhost:8000)",
            "srv_remote": "Enter a custom URL",
            "srv_already":"Use saved config",
            "using":      "Using",
            "server_url": "Server URL",
            "h_connecting":"Connecting",
            "testing":    "Testing connection ...",
            "srv_ok":     "Server responding",
            "key_ok":     "API key accepted",
            "srv_fail":   "Could not connect",
            "saved_anyway":"Config saved. Fix server then run",
            "youre_in":   "You're in",
            "ready":      "is ready.",
            "next_steps": "What to do next:",
            "n1":         "Create your first agent",
            "n2":         "System health & metrics",
            "n3":         "Skills, server, preferences",
            "n4":         "Browse available integrations",
        },
        "es": {
            "tagline":    random.choice(_TAGLINES),
            "welcome":    "Bienvenido a nova.",
            "intro1":     "nova se sienta entre tus agentes y el mundo real.",
            "intro2":     "Antes de que algo se ejecute, nova hace una pregunta:",
            "question":   "¿Debería pasar esto?",
            "p_continue": "continuar",
            "h_howworks": "Cómo funciona nova",
            "how1":       "Tu agente quiere hacer algo",
            "how_ev":     "nova lo evalúa en <5ms  —  sin IA en el 90% de casos",
            "approved":   "Aprobado  ·  se ejecuta",
            "escalated":  "Escalado  ·  tú decides",
            "blocked":    "Bloqueado  ·  registrado para siempre",
            "ledger_desc":"Cada decisión queda en el Intent Ledger.",
            "ledger_sub": "Criptográfico. Auditable. Permanente.",
            "h_risks":    "Antes de continuar",
            "risk_title": "nova no es un sandbox.",
            "risk_sub":   "Toma decisiones reales sobre acciones reales en producción.",
            "r1":         "nova puede bloquear acciones que tus agentes intentan ejecutar",
            "r2":         "cada validación se registra permanentemente en el ledger",
            "r3":         "tú defines las reglas — tú eres responsable de las consecuencias",
            "r4":         "reglas mal configuradas pueden bloquear trabajo legítimo",
            "r5":         "el ledger no puede eliminarse ni modificarse",
            "terms_label":"Términos:",
            "terms_q":    "¿Entiendes y aceptas?",
            "accept":     "Sí, acepto",
            "decline":    "No, salir",
            "cancelled":  "Setup cancelado. Ejecuta",
            "h_who":      "¿Quién eres?",
            "who_sub":    "Esto personaliza tu experiencia con nova.",
            "your_name":  "Tu nombre u organización",
            "h_server":   "Conecta tu servidor",
            "server_sub": "nova CLI habla con un servidor nova. Self-hosted o cloud.",
            "server_opts":"¿Cómo quieres conectar?",
            "srv_local":  "Servidor local  (http://localhost:8000)",
            "srv_remote": "Ingresar URL personalizada",
            "srv_already":"Usar configuración guardada",
            "using":      "Usando",
            "server_url": "URL del servidor",
            "h_connecting":"Conectando",
            "testing":    "Probando conexión ...",
            "srv_ok":     "Servidor respondiendo",
            "key_ok":     "API key aceptada",
            "srv_fail":   "No se puede conectar",
            "saved_anyway":"Config guardada. Arregla el servidor y ejecuta",
            "youre_in":   "Estás dentro",
            "ready":      "está listo.",
            "next_steps": "Qué hacer ahora:",
            "n1":         "Crea tu primer agente",
            "n2":         "Estado del sistema y métricas",
            "n3":         "Skills, servidor, preferencias",
            "n4":         "Ver integraciones disponibles",
        }
    }
    return strings.get(lang, strings["en"])


def cmd_status(args):
    print_logo()
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    loading("Loading...")
    stats  = api.get("/stats")
    health = api.get("/health")
    clear_line()

    if "error" in health:
        fail("Nova not responding at " + q(C.G3, cfg["api_url"]))
        print()
        dim("Check: docker compose -f ~/nova-os/docker-compose.yml up -d")
        print()
        return

    section("Server")
    kv("URL",    cfg["api_url"], C.B6)
    kv("Status", "Operational",  C.GRN)

    if "error" not in stats:
        section("Activity")
        t = stats.get("total_actions", 0)
        a = stats.get("approved", 0)
        b = stats.get("blocked", 0)
        d = stats.get("duplicates_blocked", 0)

        kv("Total actions",       str(t))
        kv("Approved",           str(a), C.GRN)
        kv("Blocked",          str(b), C.RED if b > 0 else C.G3)
        kv("Duplicates avoided", str(d), C.ORG if d > 0 else C.G3)
        kv("Approval rate",     str(stats.get("approval_rate", 0)) + "%")

        section("Resources")
        alr = stats.get("alerts_pending", 0)
        kv("Active agents",    str(stats.get("active_agents", 0)),  C.B7)
        kv("Memories stored", str(stats.get("memories_stored", 0)), C.B6)
        kv("Avg score",     str(stats.get("avg_score", 0)))
        kv("Pending alerts", str(alr), C.YLW if alr > 0 else C.G3)
    print()


def cmd_agent_create(args):
    section("New agent")
    print("  " + q(C.G2, "Define the behavior rules for your agent."))
    print()

    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    name = prompt("Agent name", "My Agent")
    desc = prompt("Brief description (optional)", "")
    auth = prompt("Authorized by", "admin@company.com")
    print()

    print("  " + q(C.B7, "●", bold=True) + "  " + q(C.W, "ALLOWED actions:"))
    can  = prompt_list("One per line")
    print()
    print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "FORBIDDEN actions:"))
    cant = prompt_list("One per line")
    print()

    can_preview  = (", ".join(can[:2])  + ("..." if len(can)  > 2 else "")) if can  else "none"
    cant_preview = (", ".join(cant[:2]) + ("..." if len(cant) > 2 else "")) if cant else "none"
    box([
        "  Agent      " + name,
        "  Can do     " + can_preview,
        "  Forbidden  " + cant_preview,
        "  By         " + auth,
    ], C.B4, title="Summary")
    print()

    if not confirm("Create this agent?"):
        warn("Cancelled.")
        return

    loading("Signing Intent Token...")
    result = api.post("/tokens", {
        "agent_name": name, "description": desc,
        "can_do": can, "cannot_do": cant, "authorized_by": auth,
    })
    clear_line()

    if "error" in result:
        print_error(result)
        return

    tid = result.get("token_id", "")
    ok("Agent created — token signed")
    print()
    kv("Token ID", tid, C.B7)
    kv("Signature",    result.get("signature", "")[:24] + "...", C.G3)
    print()

    cfg["default_token"] = tid
    save_config(cfg)

    webhook = cfg["api_url"] + "/webhook/" + cfg["api_key"]
    section("Webhook ready for n8n")
    box([
        "  POST  " + webhook,
        "",
        '  Body:  {"action": "{{$json.texto}}", "token_id": "' + tid[:16] + '..."}',
    ], C.B5)
    print()


def cmd_agent_list(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    loading("Loading agents...")
    result = api.get("/tokens")
    clear_line()

    if "error" in result:
        print_error(result)
        return
    if not result:
        warn("No active agents.")
        info("Create one with:  nova agent create")
        return

    default_id = cfg.get("default_token", "")
    section("Active agents", str(len(result)) + " total")

    for t in result:
        is_def = str(t["id"]) == default_id
        badge  = "  " + q(C.B6, "default") if is_def else ""
        st     = q(C.GRN, "● active") if t.get("active") else q(C.G4, "○ inactive")
        print()
        print("  " + q(C.W, t["agent_name"], bold=True) + "  " + st + badge)
        kv("  ID",         str(t["id"])[:22] + "...", C.G3)
        if t.get("can_do"):
            preview = ", ".join(t["can_do"][:3]) + ("..." if len(t["can_do"]) > 3 else "")
            kv("  Can do",    preview, C.GRN)
        if t.get("cannot_do"):
            preview = ", ".join(t["cannot_do"][:3]) + ("..." if len(t["cannot_do"]) > 3 else "")
            kv("  Forbidden", preview, C.RED)
    print()


def cmd_validate(args):
    cfg    = load_config()
    api    = NovaAPI(cfg["api_url"], cfg["api_key"])
    tid    = args.token or cfg.get("default_token", "")
    action = args.action or prompt("Action to validate")
    ctx    = args.context or ""

    if not tid:
        fail("No token set. Pass --token or create an agent first.")
        return

    print()
    loading("Validating...")
    t0     = time.time()
    result = api.post("/validate", {
        "token_id": tid, "action": action, "context": ctx,
        "generate_response": True, "check_duplicates": True,
    })
    ms = int((time.time() - t0) * 1000)
    clear_line()

    if "error" in result:
        print_error(result)
        return

    verdict = result.get("verdict", "?")
    score   = result.get("score", 0)
    reason  = result.get("reason", "")
    resp    = result.get("response")
    dup     = result.get("duplicate_of")

    print()
    print("  " + verdict_badge(verdict) + "   " + score_bar(score) + "   " + q(C.G4, str(ms) + "ms"))
    print()
    kv("Reason",          reason, C.G2)
    kv("Agent",         result.get("agent_name", ""), C.W)
    kv("Ledger",         "#" + str(result.get("ledger_id", "?")), C.G3)
    kv("Memories used", str(result.get("memories_used", 0)), C.B6)

    if dup:
        print()
        dup_action = dup.get("action", "")
        dup_short  = dup_action[:52] + ("…" if len(dup_action) > 52 else "")
        box([
            "  Duplicado del registro #" + str(dup.get("ledger_id")),
            "  Similitud  " + str(int(dup.get("similarity", 0) * 100)) + "%",
            "  Original   " + dup_short,
        ], C.ORG, title="Duplicate detected")

    if resp:
        print()
        section("Generated response")
        print()
        for line in textwrap.wrap(resp, width=64):
            print("  " + q(C.G1, line))

    print()
    h = result.get("hash", "")[:20]
    print("  " + q(C.G5, "hash  " + h + "..."))
    print()


def cmd_memory_save(args):
    cfg   = load_config()
    api   = NovaAPI(cfg["api_url"], cfg["api_key"])
    agent = args.agent or prompt("Agent")
    key   = args.key   or prompt("Key", "important_data")
    value = args.value or prompt("Value")
    imp   = int(getattr(args, "importance", None) or "5")

    loading("Saving...")
    r = api.post("/memory", {
        "agent_name": agent, "key": key, "value": value,
        "importance": imp, "tags": ["manual"],
    })
    clear_line()

    if "error" in r:
        print_error(r)
        return
    ok("Memory saved  —  ID " + str(r.get("id")) + "  importance " + str(imp) + "/10")
    print()


def cmd_memory_list(args):
    cfg   = load_config()
    api   = NovaAPI(cfg["api_url"], cfg["api_key"])
    agent = args.agent or prompt("Agent")

    loading("Loading memories...")
    result = api.get("/memory/" + urllib.parse.quote(agent))
    clear_line()

    if "error" in result:
        print_error(result)
        return
    if not result:
        warn("'" + agent + "' no tiene memorias.")
        # Fixed: no backslash inside f-string — build string first
        cmd_hint = 'nova memory save --agent "' + agent + '"'
        info("Save with:  " + q(C.B7, cmd_hint))
        return

    section("Memories of " + agent, str(len(result)) + " entries")
    for m in result:
        imp = m.get("importance", 5)
        bar = q(C.B6, "█" * imp) + q(C.G4, "░" * (10 - imp))
        src = q(C.G4, m.get("source", "manual"))
        print()
        print("  " + q(C.W, m["key"], bold=True) + "  " + bar + "  " + src)
        for line in textwrap.wrap(m["value"], width=62):
            print("    " + q(C.G2, line))
    print()


def cmd_ledger(args):
    cfg     = load_config()
    api     = NovaAPI(cfg["api_url"], cfg["api_key"])
    limit   = getattr(args, "limit", 10) or 10
    verdict = getattr(args, "verdict", "") or ""
    url     = "/ledger?limit=" + str(limit) + ("&verdict=" + verdict.upper() if verdict else "")

    loading("Loading ledger...")
    result = api.get(url)
    clear_line()

    if "error" in result:
        print_error(result)
        return

    section("Ledger", str(len(result)) + " entries")
    vc_map = {
        "APPROVED": C.GRN, "BLOCKED": C.RED,
        "ESCALATED": C.YLW, "DUPLICATE": C.ORG,
    }
    for e in result:
        v   = e.get("verdict", "?")
        s   = e.get("score", 0)
        vc  = vc_map.get(v, C.G3)
        act = e.get("action", "")
        ts  = (e.get("executed_at") or "")[:16]
        print()
        short = act[:56] + ("…" if len(act) > 56 else "")
        print("  " + q(vc, "■") + "  " + q(C.W, short))
        print("     " + q(vc, v.ljust(10)) + "  score " + score_bar(s, 10) +
              "  " + q(C.G4, ts) + "  " + q(C.G4, e.get("agent_name", "")[:22]))
    print()


def cmd_verify(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    loading("Verifying cryptographic chain...")
    r = api.get("/ledger/verify")
    clear_line()

    if "error" in r:
        print_error(r)
        return
    print()
    if r.get("verified"):
        ok("Chain intact  —  " + str(r.get("total_records", 0)) + " records verified")
        kv("Status", "No modifications detected", C.GRN)
    else:
        fail("Chain compromised at record #" + str(r.get("broken_at")))
        warn("A ledger record has been tampered with.")
    print()


def cmd_alerts(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    loading("Loading alerts...")
    r = api.get("/alerts")
    clear_line()

    if "error" in r:
        print_error(r)
        return

    pending = [a for a in r if not a.get("resolved")]
    if not pending:
        ok("No pending alerts.")
        print()
        return

    section("Pending alerts", str(len(pending)))
    for a in pending:
        s  = a.get("score", 0)
        ac = C.RED if s < 40 else C.YLW
        print()
        print("  " + q(ac, "▲") + "  " + q(C.W, a.get("message", "")[:62]))
        print("     " + q(C.G2, "Score ") + q(ac, str(s), bold=True) +
              "   " + q(C.G3, a.get("agent_name", "")) +
              "   " + q(C.G4, str(a["id"])[:12]))
    print()
    dim("Resolve:  nova alerts resolve <id>")
    print()


def cmd_seed(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    warn("This will insert demo agents and actions.")
    if not confirm("Continue?"):
        return

    loading("Seeding demo data...")
    r = api.post("/demo/seed", {})
    clear_line()

    if "error" in r:
        print_error(r)
        return
    ok("Demo data loaded.")
    kv("Agents",  str(r.get("tokens", 0)),   C.B7)
    kv("Actions", str(r.get("actions", 0)))
    kv("Memories", str(r.get("memories", 0)), C.B6)
    print()
    info("Explore with:  " + q(C.B7, "nova status"))
    print()


def cmd_config(args):
    """Interactive configuration hub."""
    while True:
        cfg       = load_config()
        api_url   = cfg.get("api_url", "http://localhost:8000")
        api_key   = cfg.get("api_key", "")
        installed = [k for k in SKILLS if skill_status(k) == "installed"]

        connected = False
        try:
            h = NovaAPI(api_url, api_key).get("/health")
            connected = "error" not in h
        except Exception:
            pass

        key_display = ("*" * 8 + api_key[-4:]) if len(api_key) >= 4 else ("not set" if not api_key else api_key)
        srv_status  = ("connected" if connected else "unreachable")
        skill_count = str(len(installed)) + "/" + str(len(SKILLS)) + " installed"

        print_logo(compact=True)
        print("  " + q(C.G3, "─" * 52))
        print()
        kv("  Server", api_url[:38], C.B6 if connected else C.YLW)
        kv("  Status", srv_status,   C.GRN if connected else C.YLW)
        kv("  API Key", key_display, C.G2)
        kv("  Skills",  skill_count, C.GRN if installed else C.G2)
        print()
        print("  " + q(C.G3, "─" * 52))
        print()

        opts = [
            "Server        — update URL",
            "API Key       — update credentials",
            "Skills  ✦     — install integrations",
            "Preferences   — language",
            "About         — version · docs",
            "Reset         — clear all settings",
            "Exit",
        ]

        try:
            choice = _select(opts, default=0)
        except KeyboardInterrupt:
            print(); break

        if choice == 6:
            break

        if choice == 0:
            print()
            section("Server")
            kv("URL", api_url, C.B6)
            kv("Status", "Connected" if connected else "Unreachable",
               C.GRN if connected else C.RED)
            print()
            try:
                new_url = prompt("New URL (Enter to keep)", api_url)
                if new_url and new_url != api_url:
                    cfg["api_url"] = new_url
                    save_config(cfg)
                    ok("Server URL updated.")
            except (EOFError, KeyboardInterrupt):
                pass

        elif choice == 1:
            print()
            section("API Key")
            kv("Current", key_display, C.G2)
            print()
            try:
                import getpass
                print("  " + q(C.B6, "?") + "  " + q(C.G1, "New API Key (Enter to keep)") +
                      "  ", end="", flush=True)
                new_key = getpass.getpass("").strip()
                if new_key:
                    cfg["api_key"] = new_key
                    save_config(cfg)
                    ok("API Key updated.")
            except (EOFError, KeyboardInterrupt):
                pass

        elif choice == 2:
            _config_skills_hub()

        elif choice == 3:
            print()
            section("Preferences")
            lang = cfg.get("lang", "en")
            kv("Language", "English" if lang == "en" else "Español", C.W)
            print()
            try:
                lang_idx = _select(["English", "Español"],
                                   default=0 if lang == "en" else 1)
                cfg["lang"] = "en" if lang_idx == 0 else "es"
                save_config(cfg)
                ok("Saved.")
            except (EOFError, KeyboardInterrupt):
                pass

        elif choice == 4:
            print()
            section("About nova")
            kv("Version", NOVA_VERSION, C.B6)
            kv("Config",  CONFIG_FILE,  C.G2)
            kv("Skills",  skill_count,  C.G2)
            kv("Docs",    "https://github.com/Santiagorubioads/nova-os", C.B6)
            kv("Support", "https://nova-os.com/support", C.B6)
            print()
            _pause("go back")

        elif choice == 5:
            print()
            warn("This will erase all local nova config and installed skills.")
            print()
            try:
                idx = _select(["Cancel", "Yes, reset everything"], default=0)
                if idx == 1:
                    import shutil
                    shutil.rmtree(NOVA_DIR, ignore_errors=True)
                    ok("nova reset. Run " + q(C.B7, "nova init") + " to start fresh.")
                    print()
                    break
            except (EOFError, KeyboardInterrupt):
                pass
        print()


def _config_skills_hub():
    """Skills hub — arrow-key browsable catalog."""
    while True:
        installed = [k for k in SKILLS if skill_status(k) == "installed"]
        available = [k for k in SKILLS if skill_status(k) != "installed"]
        all_keys  = list(SKILLS.keys())

        print()
        print_logo(compact=True)
        print("  " + q(C.W, "Skills  ", bold=True) + q(C.B6, "✦") +
              "  " + q(C.G2, "The Constellation"))
        print("  " + q(C.G3, "─" * 52))
        print()
        print("  " + q(C.G1, "  Skills give nova real-world context before every decision."))
        print("  " + q(C.G2, "  Install what you need. Nothing else runs."))
        print()

        # Build arrow-key options (NO ANSI codes inside option strings)
        opts = []
        for k in all_keys:
            s   = SKILLS[k]
            st  = skill_status(k)
            tag = " ✓" if st == "installed" else "  "
            opts.append(s["icon"] + "  " + s["name"].ljust(14) + tag + "  " + s["desc"][:28])
        opts.append("← Back")

        try:
            idx = _select(opts, default=0)
        except KeyboardInterrupt:
            print(); break

        if idx == len(opts) - 1:  # Back
            break

        name = all_keys[idx]
        fake = type("A", (), {"third": name, "subcommand": "add",
                              "agent": "", "reconfigure": False})()
        cmd_skill_add(fake)


def cmd_help(args=None):
    print_logo()

    print("  " + q(C.G1, "Governance infrastructure for AI agents."))
    print()
    print("  " + q(C.G3, "─" * 54))
    print()

    sections_data = [
        ("Getting started", [
            ("nova init",            "First-run setup · T&C · server connection"),
            ("nova status",          "System health, metrics, active agents"),
            ("nova config",          "Skills, server, preferences — everything"),
        ]),
        ("Agents", [
            ("nova agent create",    "Create an agent with intent rules"),
            ("nova agent list",      "List all active agents"),
        ]),
        ("Validation", [
            ("nova validate",        "Validate an action — verdict + response"),
        ]),
        ("Memory", [
            ("nova memory save",     "Store context in an agent's memory"),
            ("nova memory list",     "Read an agent's memories"),
        ]),
        ("Ledger", [
            ("nova ledger",          "Full cryptographic action history"),
            ("nova ledger verify",   "Verify chain integrity"),
            ("nova alerts",          "Blocked & escalated action alerts"),
        ]),
        ("Skills", [
            ("nova skill",           "Skill catalog — all available integrations"),
            ("nova skill add",       "Install a skill step by step"),
            ("nova skill info",      "Details & status of a skill"),
        ]),
    ]

    for title, cmds in sections_data:
        print("  " + q(C.G2, title.upper()))
        print()
        for cmd, desc in cmds:
            print("  " + q(C.B7, "  " + cmd.ljust(24), bold=True) + "  " + q(C.G2, desc))
        print()

    print("  " + q(C.G3, "─" * 54))
    print()
    print("  " + q(C.G2, "Examples:"))
    print()
    examples = [
        ('nova validate --action "Send email to john@x.com"', ""),
        ("nova ledger --limit 20 --verdict BLOCKED",          ""),
        ("nova config",                                        "→ then select [3] for Skills"),
    ]
    for ex, note in examples:
        line = "  " + q(C.G3, "  $ ") + q(C.W, ex)
        if note:
            line += "  " + q(C.G3, note)
        print(line)
    print()


# ══════════════════════════════════════════════════════════════════
# SKILLS CATALOG — Nova · Constellation
# ══════════════════════════════════════════════════════════════════

SKILLS = {
    # ── Comunicación ───────────────────────────────────────────────
    "gmail": {
        "name": "Gmail",
        "category": "Communication",
        "icon": "✉",
        "color": "RED",
        "desc": "Verify sent emails, detect duplicates, read inbox",
        "what": "nova checks your Gmail before approving any send action",
        "fields": [
            ("service_account_json", "Path to Service Account JSON file", False),
            ("delegated_email",      "Your Google account email",        False),
        ],
        "docs": "https://console.cloud.google.com/iam-admin/serviceaccounts",
        "mcp":  "gmail-mcp",
    },
    "sheets": {
        "name": "Google Sheets",
        "category": "Data",
        "icon": "⊞",
        "color": "GRN",
        "desc": "Read and write your spreadsheets in real time",
        "what": "nova checks your Sheet before executing actions",
        "fields": [
            ("service_account_json", "Ruta al JSON de Service Account", False),
            ("spreadsheet_id",       "Main Spreadsheet ID",     False),
        ],
        "docs": "https://console.cloud.google.com/iam-admin/serviceaccounts",
        "mcp":  "google-sheets-mcp",
    },
    "slack": {
        "name": "Slack",
        "category": "Communication",
        "icon": "◈",
        "color": "YLW",
        "desc": "Send alerts, read channels, verify sent messages",
        "what": "nova notifies Slack when it blocks or escalates an action",
        "fields": [
            ("bot_token",   "Bot Token (xoxb-...)",       False),
            ("channel",     "Default channel (#general)",   False),
        ],
        "docs": "https://api.slack.com/apps",
        "mcp":  "slack-mcp-server",
    },
    "whatsapp": {
        "name": "WhatsApp",
        "category": "Comunicación",
        "icon": "◉",
        "color": "GRN",
        "desc": "Verify sent messages, prevent spam, manage contacts",
        "what": "nova checks WhatsApp history before approving messages",
        "fields": [
            ("evolution_api_url", "Evolution API URL",   False),
            ("evolution_api_key", "Evolution API Key",   True),
            ("instance_name",     "Instance name", False),
        ],
        "docs": "https://doc.evolution-api.com",
        "mcp":  "whatsapp-mcp",
    },
    "telegram": {
        "name": "Telegram",
        "category": "Comunicación",
        "icon": "◎",
        "color": "B6",
        "desc": "Read & send messages, manage bots, verify channels",
        "what": "nova can receive commands and send alerts via Telegram",
        "fields": [
            ("bot_token",  "Bot Token de @BotFather", True),
            ("chat_id",    "Main Chat ID",       False),
        ],
        "docs": "https://core.telegram.org/bots",
        "mcp":  "telegram-mcp",
    },
    # ── Productividad ──────────────────────────────────────────────
    "notion": {
        "name": "Notion",
        "category": "Productivity",
        "icon": "◻",
        "color": "W",
        "desc": "Read databases, create pages, update records",
        "what": "nova can query and update your Notion as source of truth",
        "fields": [
            ("api_key",     "Integration Token (secret_...)", True),
            ("database_id", "Main database ID",  False),
        ],
        "docs": "https://www.notion.so/my-integrations",
        "mcp":  "notion-mcp",
    },
    "airtable": {
        "name": "Airtable",
        "category": "Data",
        "icon": "◈",
        "color": "ORG",
        "desc": "CRM, leads database, inventory — check before acting",
        "what": "nova verifies Airtable records before executing",
        "fields": [
            ("api_key",  "Personal Access Token", True),
            ("base_id",  "Base ID (app...)",       False),
        ],
        "docs": "https://airtable.com/create/tokens",
        "mcp":  "airtable-mcp",
    },
    "github": {
        "name": "GitHub",
        "category": "Development",
        "icon": "◯",
        "color": "W",
        "desc": "Create issues, review PRs, verify code before deploy",
        "what": "nova can block deploys if critical issues are open",
        "fields": [
            ("token",  "Personal Access Token (ghp_...)", True),
            ("repo",   "Default repo (owner/repo)",       False),
        ],
        "docs": "https://github.com/settings/tokens",
        "mcp":  "github-mcp",
    },
    # ── Pagos ──────────────────────────────────────────────────────
    "stripe": {
        "name": "Stripe",
        "category": "Pagos",
        "icon": "◈",
        "color": "B7",
        "desc": "Verify charges, detect fraud, approve transactions",
        "what": "nova validates payments and blocks suspicious transactions",
        "fields": [
            ("secret_key", "Secret Key (sk_live_... o sk_test_...)", True),
        ],
        "docs": "https://dashboard.stripe.com/apikeys",
        "mcp":  "stripe-mcp",
    },
    "hubspot": {
        "name": "HubSpot",
        "category": "CRM",
        "icon": "◉",
        "color": "ORG",
        "desc": "Query contacts, deals, communication history",
        "what": "nova checks if a lead was already contacted before approving",
        "fields": [
            ("api_key", "Private App Token", True),
        ],
        "docs": "https://developers.hubspot.com/docs/api/private-apps",
        "mcp":  "hubspot-mcp",
    },
    # ── Infraestructura ────────────────────────────────────────────
    "supabase": {
        "name": "Supabase",
        "category": "Database",
        "icon": "◈",
        "color": "GRN",
        "desc": "Query your Postgres database in real time",
        "what": "nova can verify any table before executing actions",
        "fields": [
            ("url",         "Project URL (https://xxx.supabase.co)", False),
            ("service_key", "Service Role Key",                       True),
        ],
        "docs": "https://app.supabase.com/project/_/settings/api",
        "mcp":  "supabase-mcp",
    },
    "postgres": {
        "name": "PostgreSQL",
        "category": "Base de datos",
        "icon": "◉",
        "color": "B6",
        "desc": "Direct connection to your PostgreSQL database",
        "what": "nova queries your DB before every critical validation",
        "fields": [
            ("connection_string", "postgresql://user:pass@host:5432/db", True),
        ],
        "docs": "https://www.postgresql.org/docs/current/libpq-connect.html",
        "mcp":  "postgres-mcp",
    },
}

SKILL_CATEGORIES = ["Communication", "Data", "Productivity", "Development", "CRM", "Payments", "Database"]

SKILLS_DIR = os.path.join(NOVA_DIR, "skills")


def load_skill(name):
    path = os.path.join(SKILLS_DIR, name + ".json")
    if os.path.exists(path):
        try: return json.load(open(path))
        except: pass
    return None


def save_skill(name, data):
    os.makedirs(SKILLS_DIR, exist_ok=True)
    json.dump(data, open(os.path.join(SKILLS_DIR, name + ".json"), "w"), indent=2)


def skill_status(name):
    d = load_skill(name)
    if not d: return "not_installed"
    return d.get("status", "installed")


def _skill_color(skill_def):
    color_map = {
        "RED": C.RED, "GRN": C.GRN, "YLW": C.YLW,
        "W": C.W, "B6": C.B6, "B7": C.B7, "ORG": C.ORG,
    }
    return color_map.get(skill_def.get("color", "W"), C.W)


# ── nova skill list ──────────────────────────────────────────────
def cmd_skill_list(args):
    print_logo(tagline=False)
    print("  " + q(C.W, "Available Skills", bold=True) + "  " + q(C.G4, "· connect nova to the world"))
    print("  " + q(C.G4, "─" * 54))
    print()

    # Star intro — nova branding
    print("  " + q(C.B5, "✦") + "  " + q(C.G2, "nova is a new star. skills are its constellation."))
    print("  " + q(C.G5, "   instala los que necesites · cada uno amplifica lo que nova puede ver"))
    print()

    for cat in SKILL_CATEGORIES:
        cat_skills = [(k, v) for k, v in SKILLS.items() if v["category"] == cat]
        if not cat_skills: continue

        print("  " + q(C.G3, cat.upper()))
        print()

        for name, s in cat_skills:
            st    = skill_status(name)
            sc    = _skill_color(s)
            icon  = s["icon"]

            if st == "installed":
                badge = q(C.GRN, " installed", bold=True)
                dot   = q(C.GRN, "●")
            else:
                badge = q(C.G4, " ·")
                dot   = q(C.G4, "○")

            print("  " + dot + "  " + q(sc, icon + " " + s["name"], bold=True) +
                  badge + "  " + q(C.G3, s["desc"]))

        print()

    print("  " + q(C.G4, "─" * 54))
    print()
    print("  " + q(C.B7, "nova skill add <nombre>", bold=True) + q(C.G3, "   install a skill"))
    print("  " + q(C.B5, "nova skill info <nombre>") + q(C.G3, "   view details"))
    print("  " + q(C.B5, "nova skill remove <nombre>") + q(C.G3, "   uninstall"))
    print()


# ── nova skill info ──────────────────────────────────────────────
def cmd_skill_info(args):
    name = getattr(args, "third", "") or args.subcommand or args.agent or ""
    if name in ("info", "add", "list", "remove", ""):
        name = getattr(args, "third", "") or args.agent or ""
        fail("Skill not found: " + (name or "?"))
        print()
        info("Available skills: " + ", ".join(SKILLS.keys()))
        return

    s  = SKILLS[name]
    sc = _skill_color(s)
    st = skill_status(name)
    data = load_skill(name)

    print()
    print("  " + q(sc, s["icon"] + "  " + s["name"], bold=True) +
          "  " + q(C.G4, s["category"]))
    print()
    kv("Description",  s["desc"])
    kv("What it does",  s["what"], C.G2)
    kv("MCP",          s["mcp"], C.G3)
    kv("Docs",         s["docs"], C.B6)
    kv("Status",       ("✓ installed" if st == "installed" else "not installed"),
       C.GRN if st == "installed" else C.G4)

    if data and data.get("installed_at"):
        kv("Instalado",    data["installed_at"][:10], C.G3)

    section("Required fields")
    for field, label, secret in s["fields"]:
        val = ""
        if data and data.get(field):
            v = data[field]
            val = q(C.GRN, ("*" * 8) if secret else v[:32])
        else:
            val = q(C.G4, "not configured")
        kv("  " + field, val if val else label)

    print()
    if st != "installed":
        info("Install:  " + q(C.B7, "nova skill add " + name))
    else:
        info("Reconfigure:  " + q(C.B7, "nova skill add " + name + " --reconfigure"))
    print()


# ── nova skill add ───────────────────────────────────────────────
def cmd_skill_add(args):
    raw = getattr(args, "third", "") or args.subcommand or args.agent or ""
    if raw in ("add", "remove", "list", "info", "install", ""):
        raw = getattr(args, "third", "") or args.agent or ""
    name = raw.lower().strip()

    if not name:
        # Interactive picker
        print()
        print("  " + q(C.W, "Which skill do you want to install?", bold=True))
        print()
        for i, (k, s) in enumerate(SKILLS.items()):
            sc = _skill_color(s)
            st = "  " + q(C.GRN, "✓") if skill_status(k) == "installed" else ""
            print("  " + q(C.G3, str(i+1).rjust(2) + ".") + "  " +
                  q(sc, s["icon"] + " " + s["name"], bold=True) + st +
                  "  " + q(C.G3, s["desc"][:48]))
        print()
        print("  ", end="")
        try:
            choice = input(q(C.B6, "Number or name: ")).strip()
        except (EOFError, KeyboardInterrupt):
            print(); return

        if choice.isdigit():
            idx = int(choice) - 1
            keys = list(SKILLS.keys())
            if 0 <= idx < len(keys):
                name = keys[idx]
        else:
            name = choice.lower()

    if name not in SKILLS:
        fail("Skill '" + name + "' not found.")
        info("Available skills: " + ", ".join(SKILLS.keys()))
        return

    s   = SKILLS[name]
    sc  = _skill_color(s)
    st  = skill_status(name)
    existing = load_skill(name) or {}
    reconfigure = getattr(args, "reconfigure", False) or st == "installed"

    # ── HEADER
    print()
    print("  " + q(sc, s["icon"] + "  " + s["name"], bold=True) + "  " + q(C.G4, "skill"))
    print("  " + q(C.G4, "─" * 40))
    print()
    print("  " + q(C.G2, s["what"]))
    print()

    if st == "installed" and not reconfigure:
        ok("Already installed.")
        info("To reconfigure:  " + q(C.B7, "nova skill add " + name + " --reconfigure"))
        print()
        return

    # ── STEP 1: docs
    print("  " + q(C.B6, "✦") + "  " + q(C.W, "Step 1 of 2 — Get your credentials", bold=True))
    print()
    print("  " + q(C.G2, "Set up access at:"))
    print("  " + q(C.B7, "  " + s["docs"]))
    print()
    if not confirm("Do you have the credentials ready?", default=False):
        print()
        info("Once ready, come back with:  " + q(C.B7, "nova skill add " + name))
        print()
        return

    # ── STEP 2: fields
    print()
    print("  " + q(C.B6, "✦") + "  " + q(C.W, "Step 2 of 2 — Configure the skill", bold=True))
    print()

    data = dict(existing)

    for field, label, secret in s["fields"]:
        current = existing.get(field, "")
        display_current = ("***" if secret and current else current[:20] if current else "")
        hint = display_current or ""
        print("  " + q(C.B6, "?") + "  " + q(C.G1, label) +
              ("  " + q(C.G4, "(" + hint + ")") if hint else "") + "  ", end="", flush=True)
        try:
            if secret:
                import getpass
                val = getpass.getpass("").strip()
            else:
                val = input().strip()
        except (EOFError, KeyboardInterrupt):
            val = ""
        data[field] = val or current

    # ── TEST
    print()
    loading("Verifying skill...")
    time.sleep(0.6)
    clear_line()

    # Basic validation — check required fields are filled
    missing = [f for f, _, _ in s["fields"] if not data.get(f)]
    if missing:
        warn("Missing fields: " + ", ".join(missing))
        warn("Saved as incomplete. Reconfigure with:  nova skill add " + name)
        data["status"] = "incomplete"
    else:
        ok(s["name"] + " skill configured")
        data["status"] = "installed"

    data["installed_at"] = datetime.now().isoformat()
    data["version"] = "1.0.0"
    save_skill(name, data)

    # ── SUMMARY
    print()
    box([
        "  " + s["icon"] + "  " + s["name"] + " connected to nova",
        "",
        "  " + s["what"],
    ], sc, title=s["category"])
    print()
    info("View details:  " + q(C.B7, "nova skill info " + name))
    print()


# ── nova skill remove ────────────────────────────────────────────
def cmd_skill_remove(args):
    name = (args.subcommand or args.agent or "").lower()
    if name in ("remove", ""):
        name = args.agent or ""

    if not name or name not in SKILLS:
        fail("Specify a valid skill name.")
        return

    if skill_status(name) != "installed":
        warn(name + " is not installed.")
        return

    warn("This will remove credentials for " + SKILLS[name]["name"] + " from this machine.")
    if not confirm("Continue?", default=False):
        return

    path = os.path.join(SKILLS_DIR, name + ".json")
    if os.path.exists(path):
        os.remove(path)
    ok(SKILLS[name]["name"] + " uninstalled.")
    print()


# ══════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(prog="nova", add_help=False)
    p.add_argument("command",     nargs="?", default="help")
    p.add_argument("subcommand",  nargs="?", default="")
    p.add_argument("third",       nargs="?", default="")
    p.add_argument("--token",  "-t", default="")
    p.add_argument("--action", "-a", default="")
    p.add_argument("--context","-c", default="")
    p.add_argument("--agent",        default="")
    p.add_argument("--key",          default="")
    p.add_argument("--value",        default="")
    p.add_argument("--importance",   default="5")
    p.add_argument("--limit",  type=int, default=10)
    p.add_argument("--verdict",      default="")
    p.add_argument("--reconfigure",  action="store_true")
    p.add_argument("--help",   "-h", action="store_true")
    args = p.parse_args()

    if args.help or args.command in ("help", "--help", "-h"):
        cmd_help(args)
        return

    # First-run detection — no config file yet
    if args.command not in ("init", "help", "--help", "-h") and not os.path.exists(CONFIG_FILE):
        print()
        print("  " + q(C.B5, "✦", bold=True) + "  " + q(C.W, "nova", bold=True))
        print()
        print("  " + q(C.G2, "  nova isn't configured yet."))
        print()
        print("  " + q(C.B7, "  nova init", bold=True) + q(C.G3, "  — run setup to get started"))
        print()
        return

    # No command — show mark + status hint
    if args.command == "help" or (not args.command):
        cmd_help(args)
        return

    routes = {
        ("init",     ""):        cmd_init,
        ("status",   ""):        cmd_status,
        ("agent",    "create"):  cmd_agent_create,
        ("agent",    "list"):    cmd_agent_list,
        ("agents",   ""):        cmd_agent_list,
        ("validate", ""):        cmd_validate,
        ("memory",   "save"):    cmd_memory_save,
        ("memory",   "list"):    cmd_memory_list,
        ("ledger",   ""):        cmd_ledger,
        ("ledger",   "verify"):  cmd_verify,
        ("verify",   ""):        cmd_verify,
        ("alerts",   ""):        cmd_alerts,
        ("seed",     ""):        cmd_seed,
        ("config",   ""):        cmd_config,
        # Skills
        ("skill",    ""):        cmd_skill_list,
        ("skill",    "list"):    cmd_skill_list,
        ("skills",   ""):        cmd_skill_list,
        ("skill",    "add"):     cmd_skill_add,
        ("skill",    "install"): cmd_skill_add,
        ("skill",    "info"):    cmd_skill_info,
        ("skill",    "remove"):  cmd_skill_remove,
        ("skill",    "delete"):  cmd_skill_remove,
    }

    fn = routes.get((args.command, args.subcommand)) or routes.get((args.command, ""))

    if not fn:
        fail("Unknown command: " + args.command)
        print()
        info("Run  " + q(C.B7, "nova help") + "  para ver todos los comandos.")
        print()
        sys.exit(1)

    try:
        fn(args)
    except KeyboardInterrupt:
        print()
        warn("Cancelled.")
        print()


if __name__ == "__main__":
    main()
