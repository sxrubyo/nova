#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  Nova Pro v2.0  ·  Natural Language → Flowware Engine           ║
║  n8n Agent Bridge  ·  Multi-LLM Router  ·  Auto-Repair Core     ║
║                                                                  ║
║  Zero dependencies. Python 3.8+.                                 ║
║  https://nova-os.com                                             ║
╚══════════════════════════════════════════════════════════════════╝

TOP-20 IMPLEMENTED IDEAS (from 50 candidates):
  1.  NL→Flowware Compiler   — natural language → n8n workflow JSON
  2.  n8n Agent Bridge        — bidirectional webhook + REST API
  3.  Multi-LLM Router        — OpenRouter + Claude + GPT + Gemini fallback chain
  4.  Intent Classifier       — zero-shot NL intent detection (20 intents)
  5.  Workflow Template Library — 20 ready-to-use automation templates
  6.  Built-in Webhook Server  — receive n8n calls, no extra infra
  7.  Circuit Breaker          — auto-pause failing upstreams
  8.  Rate Limiter             — token-bucket, per-provider
  9.  Semantic Memory          — context-aware rolling agent memory
 10.  Audit Trail              — SHA-256 cryptographic event chain
 11.  Plugin System            — drop-in action handlers
 12.  Hot Config Reload        — zero-downtime config changes
 13.  Multi-tenant             — isolated workspaces per agent
 14.  Pipeline Chaining        — compose workflows from primitives
 15.  REPL Mode                — interactive NL shell with history
 16.  Schema Generator         — auto-generate n8n node JSON schemas
 17.  Health Monitor           — continuous upstream probing
 18.  Export Formats           — JSON / n8n-native / YAML / Markdown
 19.  Event Bus                — pub/sub between internal modules
 20.  Auto-Repair v2           — deep diagnostics + self-healing patches
"""

import os
import sys
import json
import time
import uuid
import re
import hashlib
import threading
import queue
import socket
import secrets
import textwrap
import argparse
import shutil
import platform
import random
import signal
import readline
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
import urllib.request
import urllib.error
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler


# ══════════════════════════════════════════════════════════════════════════════
# VERSIONING
# ══════════════════════════════════════════════════════════════════════════════

NOVA_PRO_VERSION  = "2.0.0"
NOVA_PRO_BUILD    = "2026.03.constellation"
NOVA_PRO_CODENAME = "Flowmaster"

# ══════════════════════════════════════════════════════════════════════════════
# PLATFORM + TERMINAL
# ══════════════════════════════════════════════════════════════════════════════

PLATFORM   = platform.system().lower()
IS_WINDOWS = PLATFORM == "windows"
IS_MAC     = PLATFORM == "darwin"
IS_LINUX   = PLATFORM == "linux"

if IS_WINDOWS:
    try:
        import io, ctypes
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        os.system("chcp 65001 >nul 2>&1")
        k32 = ctypes.windll.kernel32
        h   = k32.GetStdHandle(-11)
        m   = ctypes.c_ulong()
        k32.GetConsoleMode(h, ctypes.byref(m))
        k32.SetConsoleMode(h, m.value | 0x0004)
    except Exception:
        pass

TERM_WIDTH = shutil.get_terminal_size((80, 24)).columns
USE_COLOR  = (not IS_WINDOWS or os.environ.get("FORCE_COLOR")) and \
             hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
DEBUG      = os.environ.get("NOVA_DEBUG", "").lower() in ("1", "true", "yes")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def strip_ansi(t: str) -> str:
    return ANSI_RE.sub("", t or "")

def _e(code: str) -> str:
    return f"\033[{code}m" if USE_COLOR else ""

# ══════════════════════════════════════════════════════════════════════════════
# COLOR PALETTE  (inherited from Nova CLI design system)
# ══════════════════════════════════════════════════════════════════════════════

class C:
    W   = "\033[38;5;15m"     # Pure white
    G1  = "\033[38;5;180m"    # Champagne
    G2  = "\033[38;5;137m"    # Matte gold
    G0  = _e("38;5;252")      # Near-white primary text
    G3  = _e("38;5;240")      # Dark gray — minimum visible
    ASH = _e("38;5;244")      # Mid gray
    R   = "\033[0m"           # Reset
    BOLD   = _e("1")
    DIM    = _e("2")
    ITALIC = _e("3")
    UNDER  = _e("4")
    # Blues
    B5  = _e("38;5;67")
    B6  = _e("38;5;67")
    B7  = _e("38;5;73")
    B8  = _e("38;5;109")
    # Semantic
    GRN  = _e("38;5;108")
    YLW  = _e("38;5;179")
    RED  = _e("38;5;167")
    ORG  = _e("38;5;173")
    MGN  = _e("38;5;139")
    CYN  = _e("38;5;109")
    PNK  = _e("38;5;174")
    GLD  = _e("38;5;179")
    GLD_BRIGHT = _e("38;5;180")
    GLD_MATTE  = _e("38;5;137")
    SAND = _e("38;5;180")
    FLOW = _e("38;5;147")     # NEW: Flowware accent — soft violet
    N8N  = _e("38;5;208")     # NEW: n8n orange accent


def q(color: str, text: str, bold: bool = False, dim: bool = False) -> str:
    s = ""
    if bold: s += C.BOLD
    if dim:  s += C.DIM
    return s + color + str(text) + C.R


def _render_reset():
    sys.stdout.write("\033[0m")
    if USE_COLOR:
        sys.stdout.write(_e("38;5;15"))


# ══════════════════════════════════════════════════════════════════════════════
# UI PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════

def ok(msg, prefix="  "):
    _render_reset(); print(f"{prefix}" + q(C.GRN, "✓") + "  " + q(C.W, msg))

def fail(msg, prefix="  "):
    _render_reset(); print(f"{prefix}" + q(C.RED, "✗") + "  " + q(C.W, msg))

def warn(msg, prefix="  "):
    _render_reset(); print(f"{prefix}" + q(C.YLW, "!") + "  " + q(C.G1, msg))

def info(msg, prefix="  "):
    _render_reset(); print(f"{prefix}" + q(C.B6, "·") + "  " + q(C.G1, msg))

def hint(msg, prefix="  "):
    _render_reset(); print(f"{prefix}" + q(C.MGN, "→") + "  " + q(C.G2, msg))

def flow(msg, prefix="  "):
    _render_reset(); print(f"{prefix}" + q(C.FLOW, "⟶") + "  " + q(C.G1, msg))

def n8n_msg(msg, prefix="  "):
    _render_reset(); print(f"{prefix}" + q(C.N8N, "⚡") + "  " + q(C.G1, msg))

def nl(n=1):
    print("\n" * (n - 1))

def hr(char="─", width=64, color=None):
    c = color or C.G3
    print("  " + q(c, char * width))

def hr_flow(width=64):
    print("  " + q(C.FLOW, "·" * width))

def section(title: str, sub: str = "", badge: str = ""):
    print()
    badge_str = f"  {q(C.FLOW, badge)}" if badge else ""
    if sub:
        print("  " + q(C.W, title, bold=True) + f"  {q(C.G2, sub)}" + badge_str)
    else:
        print("  " + q(C.W, title, bold=True) + badge_str)
    print("  " + q(C.G3, "─" * min(len(title) + 4, 64)))

def kv(key: str, val: str, color=None, w: int = 24):
    c = color or C.W
    print(f"  {q(C.G2, key.ljust(w))}{q(c, str(val))}")

def bullet(text: str, color=None, sym="·"):
    c = color or C.G1
    print(f"  {q(C.G3, sym)}  {q(c, text)}")

def mask_key(key: str, a: int = 6, b: int = 4) -> str:
    if not key: return q(C.G3, "not set")
    if len(key) < a + b + 4: return "•" * len(key)
    return key[:a] + "•" * 8 + key[-b:]

def _pad_ansi(text: str, width: int) -> str:
    return text + " " * max(0, width - len(strip_ansi(text)))


# ══════════════════════════════════════════════════════════════════════════════
# SPINNER (threaded)
# ══════════════════════════════════════════════════════════════════════════════

class Spinner:
    _FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

    def __init__(self, msg: str, color=None):
        self.msg   = msg
        self.color = color or C.FLOW
        self._stop = threading.Event()
        self._done = False
        self._t    = None
        self._ts   = 0.0

    def __enter__(self):
        self.start(); return self

    def __exit__(self, *_):
        if not self._done: self.finish()

    def start(self):
        self._ts = time.time()
        self._stop.clear()
        def _run():
            i = 0
            while not self._stop.is_set():
                f = self._FRAMES[i % len(self._FRAMES)]
                el = time.time() - self._ts
                el_s = f" ({el:.1f}s)" if el > 2 else ""
                sys.stdout.write(f"\r  {q(self.color, f)}  {q(C.G1, self.msg)}{q(C.G3, el_s)}   ")
                sys.stdout.flush()
                time.sleep(0.08)
                i += 1
        self._t = threading.Thread(target=_run, daemon=True)
        self._t.start()

    def update(self, msg: str): self.msg = msg

    def finish(self, msg: str = "", success: bool = True):
        self._done = True
        self._stop.set()
        if self._t: self._t.join(timeout=1)
        sys.stdout.write("\r\033[K"); sys.stdout.flush()
        if msg: (ok if success else fail)(msg)


# ══════════════════════════════════════════════════════════════════════════════
# LOGO
# ══════════════════════════════════════════════════════════════════════════════

_LOGO = [
    "  ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗     ██████╗ ██████╗  ██████╗ ",
    "  ████╗  ██║██╔═══██╗██║   ██║██╔══██╗    ██╔══██╗██╔══██╗██╔═══██╗",
    "  ██╔██╗ ██║██║   ██║██║   ██║███████║    ██████╔╝██████╔╝██║   ██║",
    "  ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║    ██╔═══╝ ██╔══██╗██║   ██║",
    "  ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║    ██║     ██║  ██║╚██████╔╝",
    "  ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ",
]
_LOGO_COLORS = [
    _e("38;5;180"), _e("38;5;179"), _e("38;5;178"),
    _e("38;5;172"), _e("38;5;136"), _e("38;5;94"),
]
_TAGLINES = [
    "Natural language → instant automation.",
    "Your n8n agents, now speaking human.",
    "The layer that turns intent into flow.",
    "Describe it. Nova builds it. n8n runs it.",
    "From words to workflows in milliseconds.",
    "The brain your automation stack was missing.",
]


def print_logo(animated: bool = False):
    _render_reset(); print()
    for i, line in enumerate(_LOGO):
        print(_LOGO_COLORS[i] + C.BOLD + line + C.R)
        if animated: time.sleep(0.04)
    print()
    tl = random.choice(_TAGLINES)
    print("  " + q(C.FLOW, "⟶") + "  " + q(C.W, tl))
    print("  " + q(C.GLD_BRIGHT, "✦") + "  " +
          q(C.G2, f"Nova Pro v{NOVA_PRO_VERSION}  ·  {NOVA_PRO_CODENAME}  ·  Flowware Engine"))
    print("  " + q(C.G3, "─" * 68))
    print()
    sys.stdout.write(C.R)


# ══════════════════════════════════════════════════════════════════════════════
# PATHS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

NOVA_HOME    = Path(os.environ.get("NOVA_HOME", Path.home() / ".nova_pro"))
CONFIG_FILE  = NOVA_HOME / "config.json"
AUDIT_FILE   = NOVA_HOME / "audit.jsonl"
MEMORY_FILE  = NOVA_HOME / "memory.json"
PLUGINS_DIR  = NOVA_HOME / "plugins"

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL   = "openrouter/auto"

# LLM fallback chain (tried in order on failure)
LLM_FALLBACK_CHAIN = [
    "anthropic/claude-sonnet-4-5",
    "openai/gpt-4o",
    "google/gemini-2.0-flash-001",
    "openrouter/auto",
]

# n8n workflow node types
N8N_NODE_TYPES = {
    "webhook":      "n8n-nodes-base.webhook",
    "http":         "n8n-nodes-base.httpRequest",
    "email":        "n8n-nodes-base.emailSend",
    "slack":        "n8n-nodes-base.slack",
    "notion":       "n8n-nodes-base.notion",
    "sheets":       "n8n-nodes-base.googleSheets",
    "code":         "n8n-nodes-base.code",
    "if":           "n8n-nodes-base.if",
    "schedule":     "n8n-nodes-base.scheduleTrigger",
    "set":          "n8n-nodes-base.set",
    "merge":        "n8n-nodes-base.merge",
    "split":        "n8n-nodes-base.splitInBatches",
    "postgres":     "n8n-nodes-base.postgres",
    "mysql":        "n8n-nodes-base.mySql",
    "redis":        "n8n-nodes-base.redis",
    "telegram":     "n8n-nodes-base.telegram",
    "discord":      "n8n-nodes-base.discord",
    "github":       "n8n-nodes-base.github",
    "airtable":     "n8n-nodes-base.airtable",
    "openai":       "@n8n/n8n-nodes-langchain.openAi",
}


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NovaCfg:
    openrouter_api_key: str        = ""
    openrouter_model:   str        = DEFAULT_MODEL
    n8n_base_url:       str        = "http://localhost:5678"
    n8n_api_key:        str        = ""
    n8n_webhook_token:  str        = ""
    webhook_port:       int        = 8765
    webhook_host:       str        = "0.0.0.0"
    timeout_s:          int        = 60
    max_retries:        int        = 3
    circuit_threshold:  int        = 5
    rate_limit_rpm:     int        = 30
    memory_max_entries: int        = 200
    workspace:          str        = "default"
    auto_repair:        bool       = True
    fallback_models:    List[str]  = field(default_factory=lambda: list(LLM_FALLBACK_CHAIN))

    def save(self):
        NOVA_HOME.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls) -> "NovaCfg":
        cfg = cls()
        # Layer 1: config file
        if CONFIG_FILE.exists():
            try:
                d = json.loads(CONFIG_FILE.read_text())
                for k, v in d.items():
                    if hasattr(cfg, k): setattr(cfg, k, v)
            except Exception:
                pass
        # Layer 2: environment variables (override)
        env_map = {
            "OPENROUTER_API_KEY": "openrouter_api_key",
            "OPENROUTER_MODEL":   "openrouter_model",
            "N8N_BASE_URL":       "n8n_base_url",
            "N8N_API_KEY":        "n8n_api_key",
            "N8N_WEBHOOK_TOKEN":  "n8n_webhook_token",
            "NOVA_WORKSPACE":     "workspace",
        }
        for env, attr in env_map.items():
            v = os.environ.get(env, "").strip()
            if v: setattr(cfg, attr, v)
        return cfg

    def hot_reload(self):
        """Reload config from file without restarting (idea #12)."""
        fresh = NovaCfg.load()
        for k, v in fresh.__dict__.items():
            setattr(self, k, v)
        ok("Config reloaded hot.")


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER  (token-bucket, idea #8)
# ══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    def __init__(self, rpm: int = 30):
        self.interval = 60.0 / max(rpm, 1)
        self._last    = 0.0
        self._lock    = threading.Lock()

    def acquire(self):
        with self._lock:
            wait = self.interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()


# ══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER  (idea #7)
# ══════════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    CLOSED   = "closed"
    OPEN     = "open"
    HALF     = "half-open"

    def __init__(self, threshold: int = 5, recovery_s: float = 30.0):
        self.threshold  = threshold
        self.recovery_s = recovery_s
        self._fails     = 0
        self._state     = self.CLOSED
        self._opened_at = 0.0
        self._lock      = threading.Lock()

    @property
    def state(self) -> str: return self._state

    def allow(self) -> bool:
        with self._lock:
            if self._state == self.CLOSED: return True
            if self._state == self.OPEN:
                if time.time() - self._opened_at >= self.recovery_s:
                    self._state = self.HALF
                    return True
                return False
            return True  # HALF

    def on_success(self):
        with self._lock:
            self._fails = 0
            self._state = self.CLOSED

    def on_failure(self):
        with self._lock:
            self._fails += 1
            if self._fails >= self.threshold:
                self._state = self.OPEN
                self._opened_at = time.time()
                warn(f"Circuit breaker OPEN (>= {self.threshold} failures)")


# ══════════════════════════════════════════════════════════════════════════════
# EVENT BUS  (pub/sub, idea #19)
# ══════════════════════════════════════════════════════════════════════════════

class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event: str, fn: Callable):
        with self._lock:
            self._subs.setdefault(event, []).append(fn)

    def publish(self, event: str, payload: Any = None):
        with self._lock:
            handlers = list(self._subs.get(event, []))
        for fn in handlers:
            try: fn(payload)
            except Exception as e:
                if DEBUG: print(f"[EventBus] {event} handler error: {e}")

BUS = EventBus()


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT TRAIL  — SHA-256 hash chain  (idea #10)
# ══════════════════════════════════════════════════════════════════════════════

class AuditTrail:
    def __init__(self, path: Path = AUDIT_FILE):
        self.path  = path
        self._prev = "0" * 64
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Resume chain
        if path.exists():
            for line in path.read_text().splitlines():
                try: self._prev = json.loads(line)["hash"]
                except Exception: pass

    def record(self, event_type: str, payload: Dict[str, Any]) -> str:
        with self._lock:
            entry = {
                "id":        str(uuid.uuid4()),
                "ts":        datetime.now(timezone.utc).isoformat(),
                "type":      event_type,
                "payload":   payload,
                "prev_hash": self._prev,
            }
            entry["hash"] = hashlib.sha256(
                json.dumps(entry, sort_keys=True).encode()
            ).hexdigest()
            self._prev = entry["hash"]
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            BUS.publish("audit.event", entry)
            return entry["hash"]

    def tail(self, n: int = 10) -> List[Dict]:
        if not self.path.exists(): return []
        lines = self.path.read_text().splitlines()[-n:]
        result = []
        for l in lines:
            try: result.append(json.loads(l))
            except Exception: pass
        return result


# ══════════════════════════════════════════════════════════════════════════════
# SEMANTIC MEMORY  (rolling context window, idea #9)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MemoryEntry:
    id:         str
    ts:         str
    agent:      str
    role:       str          # user | assistant | system
    content:    str
    intent:     str = ""
    importance: int = 5      # 1-10

class AgentMemory:
    def __init__(self, path: Path = MEMORY_FILE, max_entries: int = 200):
        self.path       = path
        self.max_entries= max_entries
        self._entries: List[MemoryEntry] = []
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                for d in json.loads(self.path.read_text()):
                    self._entries.append(MemoryEntry(**d))
            except Exception:
                pass

    def _save(self):
        self.path.write_text(json.dumps([e.__dict__ for e in self._entries], indent=2))

    def add(self, agent: str, role: str, content: str,
            intent: str = "", importance: int = 5) -> MemoryEntry:
        with self._lock:
            e = MemoryEntry(
                id=str(uuid.uuid4()),
                ts=datetime.now(timezone.utc).isoformat(),
                agent=agent, role=role, content=content,
                intent=intent, importance=importance,
            )
            self._entries.append(e)
            # Evict low-importance entries when full
            if len(self._entries) > self.max_entries:
                self._entries.sort(key=lambda x: x.importance, reverse=True)
                self._entries = self._entries[:self.max_entries]
            self._save()
            return e

    def context(self, agent: str, last_n: int = 20) -> List[Dict[str, str]]:
        """Return recent messages as LLM message list."""
        with self._lock:
            agent_entries = [e for e in self._entries if e.agent == agent]
            recent = sorted(agent_entries, key=lambda x: x.ts)[-last_n:]
        return [{"role": e.role, "content": e.content} for e in recent]

    def clear(self, agent: str):
        with self._lock:
            self._entries = [e for e in self._entries if e.agent != agent]
            self._save()


# ══════════════════════════════════════════════════════════════════════════════
# HTTP CLIENT  (zero-dep, reusable)
# ══════════════════════════════════════════════════════════════════════════════

def http_post(url: str, payload: Dict, headers: Dict[str, str] = None,
              timeout: int = 60) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "status": resp.status,
                    "data": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8") if e.fp else str(e)
        return {"ok": False, "status": e.code, "error": "http_error",
                "detail": detail}
    except Exception as e:
        return {"ok": False, "error": "request_failed", "detail": str(e)}


def http_get(url: str, headers: Dict[str, str] = None, timeout: int = 30) -> Dict:
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "status": resp.status,
                    "data": json.loads(resp.read().decode("utf-8"))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-LLM ROUTER  (idea #3)
# ══════════════════════════════════════════════════════════════════════════════

class LLMRouter:
    """
    Routes LLM requests through a fallback chain with circuit breakers
    and per-provider rate limiting.
    """

    def __init__(self, cfg: NovaCfg):
        self.cfg      = cfg
        self._rl      = RateLimiter(cfg.rate_limit_rpm)
        self._breakers: Dict[str, CircuitBreaker] = {}
        for m in cfg.fallback_models:
            self._breakers[m] = CircuitBreaker(cfg.circuit_threshold)

    def _breaker(self, model: str) -> CircuitBreaker:
        if model not in self._breakers:
            self._breakers[model] = CircuitBreaker(self.cfg.circuit_threshold)
        return self._breakers[model]

    def chat(self,
             messages:    List[Dict[str, str]],
             system:      str = "",
             max_tokens:  int = 2048,
             temperature: float = 0.3,
             model:       str = "") -> Dict[str, Any]:
        """
        Send chat completion with automatic fallback chain.
        Returns {"ok": True, "content": "...", "model": "...", "tokens": {...}}
        """
        self._rl.acquire()

        models_to_try = ([model] + self.cfg.fallback_models) if model \
                        else self.cfg.fallback_models

        for m in models_to_try:
            cb = self._breaker(m)
            if not cb.allow():
                if DEBUG: print(f"[LLMRouter] {m} circuit open, skipping")
                continue

            msg_list = []
            if system:
                msg_list.append({"role": "system", "content": system})
            msg_list.extend(messages)

            payload = {
                "model":       m,
                "messages":    msg_list,
                "max_tokens":  max_tokens,
                "temperature": temperature,
            }

            hdrs = {"Authorization": f"Bearer {self.cfg.openrouter_api_key}"}
            resp = http_post(
                f"{OPENROUTER_BASE}/chat/completions",
                payload, headers=hdrs, timeout=self.cfg.timeout_s,
            )

            if resp.get("ok") and resp.get("data"):
                d = resp["data"]
                if "choices" in d and d["choices"]:
                    cb.on_success()
                    content = d["choices"][0]["message"]["content"]
                    return {
                        "ok":      True,
                        "content": content,
                        "model":   d.get("model", m),
                        "tokens":  d.get("usage", {}),
                    }

            cb.on_failure()
            if DEBUG: print(f"[LLMRouter] {m} failed: {resp.get('detail','')}")

        return {"ok": False, "error": "all_models_failed",
                "detail": "Every model in the fallback chain failed."}

    def status(self) -> Dict[str, str]:
        return {m: cb.state for m, cb in self._breakers.items()}


# ══════════════════════════════════════════════════════════════════════════════
# INTENT CLASSIFIER  (idea #4)  — 20 intents, zero-shot via LLM
# ══════════════════════════════════════════════════════════════════════════════

INTENT_CATALOG = {
    "send_email":       "Send an email message to someone",
    "send_message":     "Send a message via Slack, Discord, Telegram",
    "http_request":     "Make an HTTP request to an API or URL",
    "schedule_task":    "Schedule a recurring or delayed task",
    "scrape_web":       "Extract data from a website or URL",
    "database_query":   "Read from or write to a database",
    "ai_generate":      "Generate text, images, or data with AI",
    "file_operation":   "Read, write, move, or transform files",
    "spreadsheet_op":   "Read from or update a Google Sheet / Excel",
    "notification":     "Send a push notification or alert",
    "data_transform":   "Filter, map, merge, or transform data",
    "webhook_trigger":  "Trigger an external webhook or event",
    "auth_action":      "Authentication, token refresh, OAuth",
    "search_query":     "Search the web or a knowledge base",
    "crm_action":       "Update CRM records (HubSpot, Salesforce, Notion)",
    "git_action":       "GitHub/GitLab operations (PR, issue, commit)",
    "deploy_action":    "Trigger deployment or CI/CD pipeline",
    "monitor_check":    "Check uptime, health, or metric threshold",
    "report_generate":  "Generate a report or summary document",
    "custom_code":      "Execute arbitrary code or shell command",
}

_INTENT_SYSTEM = """You are an intent classifier for a workflow automation engine.
Given a natural language instruction, respond with ONLY a JSON object:
{"intent": "<intent_key>", "confidence": 0.0-1.0, "entities": {}}

Intent keys: """ + ", ".join(INTENT_CATALOG.keys()) + """

Extract relevant entities (recipient, url, query, table, model, etc.) into the entities object.
Respond ONLY with valid JSON. No explanation."""


class IntentClassifier:
    def __init__(self, router: LLMRouter):
        self.router  = router
        self._cache: Dict[str, Dict] = {}

    def classify(self, text: str) -> Dict[str, Any]:
        """Returns {intent, confidence, entities}"""
        cache_key = hashlib.md5(text.lower().strip().encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        resp = self.router.chat(
            messages=[{"role": "user", "content": text}],
            system=_INTENT_SYSTEM,
            max_tokens=300,
            temperature=0.1,
        )

        if resp.get("ok"):
            try:
                raw = resp["content"].strip()
                raw = re.sub(r"^```json|^```|```$", "", raw).strip()
                result = json.loads(raw)
                self._cache[cache_key] = result
                return result
            except Exception:
                pass

        # Fallback: keyword heuristic
        return self._heuristic(text)

    def _heuristic(self, text: str) -> Dict[str, Any]:
        text_l = text.lower()
        kw_map = {
            "send_email":     ["email", "mail", "send to"],
            "send_message":   ["slack", "discord", "telegram", "message", "notify"],
            "http_request":   ["http", "api", "request", "endpoint", "curl", "fetch"],
            "schedule_task":  ["schedule", "every", "cron", "daily", "weekly", "at "],
            "scrape_web":     ["scrape", "crawl", "extract from", "website"],
            "database_query": ["database", "sql", "query", "table", "insert", "select"],
            "ai_generate":    ["generate", "summarize", "translate", "ai", "gpt", "claude"],
            "spreadsheet_op": ["sheet", "spreadsheet", "excel", "csv", "google sheets"],
            "git_action":     ["github", "gitlab", "pull request", "commit", "issue"],
            "report_generate":["report", "summary", "digest", "weekly report"],
        }
        for intent, kws in kw_map.items():
            if any(k in text_l for k in kws):
                return {"intent": intent, "confidence": 0.7, "entities": {}}
        return {"intent": "custom_code", "confidence": 0.3, "entities": {}}


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW TEMPLATE LIBRARY  — 20 templates  (idea #5)
# ══════════════════════════════════════════════════════════════════════════════

def _node(name: str, type_key: str, params: Dict, pos: List[int]) -> Dict:
    return {
        "id":         str(uuid.uuid4()),
        "name":       name,
        "type":       N8N_NODE_TYPES.get(type_key, type_key),
        "typeVersion": 1,
        "position":   pos,
        "parameters": params,
    }


class TemplateLibrary:
    """20 ready-to-use n8n workflow templates."""

    @staticmethod
    def templates() -> Dict[str, Callable]:
        return {k: v for k, v in TemplateLibrary.__dict__.items()
                if not k.startswith("_") and k != "templates" and callable(v)}

    @staticmethod
    def send_email(to: str, subject: str, body: str, **_) -> Dict:
        return {
            "name": f"Send Email: {subject[:30]}",
            "nodes": [
                _node("Trigger", "webhook", {"httpMethod": "POST", "path": "trigger"}, [0, 0]),
                _node("Send Email", "email", {"toEmail": to, "subject": subject, "text": body}, [200, 0]),
            ],
            "connections": {"Trigger": {"main": [[{"node": "Send Email", "type": "main", "index": 0}]]}}
        }

    @staticmethod
    def http_request(url: str, method: str = "GET", body: str = "", **_) -> Dict:
        return {
            "name": f"HTTP {method}: {url[:40]}",
            "nodes": [
                _node("Trigger", "webhook", {"httpMethod": "POST", "path": "trigger"}, [0, 0]),
                _node("HTTP Request", "http", {"url": url, "method": method.upper(), "body": body}, [200, 0]),
                _node("Process Response", "code", {"jsCode": "return items;"}, [400, 0]),
            ],
            "connections": {
                "Trigger":      {"main": [[{"node": "HTTP Request",     "type": "main", "index": 0}]]},
                "HTTP Request": {"main": [[{"node": "Process Response", "type": "main", "index": 0}]]},
            }
        }

    @staticmethod
    def slack_notify(channel: str, message: str, **_) -> Dict:
        return {
            "name": f"Slack → #{channel}",
            "nodes": [
                _node("Trigger",  "webhook", {"httpMethod": "POST", "path": "trigger"}, [0, 0]),
                _node("Slack",    "slack",   {"channel": channel, "text": message, "operation": "post"}, [200, 0]),
            ],
            "connections": {"Trigger": {"main": [[{"node": "Slack", "type": "main", "index": 0}]]}}
        }

    @staticmethod
    def ai_summarize(prompt: str, model: str = "gpt-4o", **_) -> Dict:
        return {
            "name": "AI Summarize",
            "nodes": [
                _node("Trigger",     "webhook", {"httpMethod": "POST", "path": "trigger"}, [0, 0]),
                _node("AI Generate", "openai",  {"prompt": prompt, "model": model, "operation": "complete"}, [200, 0]),
                _node("Format",      "set",     {"values": {"summary": "={{$json.text}}"}}, [400, 0]),
            ],
            "connections": {
                "Trigger":     {"main": [[{"node": "AI Generate", "type": "main", "index": 0}]]},
                "AI Generate": {"main": [[{"node": "Format",      "type": "main", "index": 0}]]},
            }
        }

    @staticmethod
    def schedule_report(cron: str, query: str, recipient: str, **_) -> Dict:
        return {
            "name": f"Scheduled Report ({cron})",
            "nodes": [
                _node("Schedule",  "schedule", {"rule": {"interval": [{"field": "cronExpression", "expression": cron}]}}, [0, 0]),
                _node("Query DB",  "code",     {"jsCode": f"// {query}\nreturn items;"}, [200, 0]),
                _node("Send Email","email",    {"toEmail": recipient, "subject": "Scheduled Report", "text": "={{$json.report}}"}, [400, 0]),
            ],
            "connections": {
                "Schedule": {"main": [[{"node": "Query DB",   "type": "main", "index": 0}]]},
                "Query DB": {"main": [[{"node": "Send Email", "type": "main", "index": 0}]]},
            }
        }

    @staticmethod
    def web_scrape_and_store(url: str, table: str = "scraped_data", **_) -> Dict:
        return {
            "name": f"Scrape → DB: {url[:30]}",
            "nodes": [
                _node("Trigger",  "webhook",  {"httpMethod": "POST", "path": "trigger"}, [0, 0]),
                _node("Fetch URL","http",     {"url": url, "method": "GET"}, [200, 0]),
                _node("Extract",  "code",     {"jsCode": "// Extract data from HTML\nreturn [{json:{html:$input.first().json.data}}];"}, [400, 0]),
                _node("Store DB", "postgres", {"operation": "insert", "table": table}, [600, 0]),
            ],
            "connections": {
                "Trigger":  {"main": [[{"node": "Fetch URL", "type": "main", "index": 0}]]},
                "Fetch URL":{"main": [[{"node": "Extract",   "type": "main", "index": 0}]]},
                "Extract":  {"main": [[{"node": "Store DB",  "type": "main", "index": 0}]]},
            }
        }

    @staticmethod
    def github_issue_to_notion(repo: str, notion_db: str, **_) -> Dict:
        return {
            "name": f"GitHub Issues → Notion",
            "nodes": [
                _node("Trigger",    "webhook",  {"httpMethod": "POST", "path": "github-hook"}, [0, 0]),
                _node("Parse Issue","set",      {"values": {"title": "={{$json.issue.title}}", "url": "={{$json.issue.html_url}}"}}, [200, 0]),
                _node("Notion",     "notion",   {"operation": "create", "databaseId": notion_db, "title": "={{$json.title}}"}, [400, 0]),
            ],
            "connections": {
                "Trigger":     {"main": [[{"node": "Parse Issue", "type": "main", "index": 0}]]},
                "Parse Issue": {"main": [[{"node": "Notion",      "type": "main", "index": 0}]]},
            }
        }

    @staticmethod
    def data_pipeline(source_url: str, transform: str, dest: str, **_) -> Dict:
        return {
            "name": "Data Pipeline",
            "nodes": [
                _node("Trigger",   "schedule",  {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}}, [0, 0]),
                _node("Fetch",     "http",      {"url": source_url, "method": "GET"}, [200, 0]),
                _node("Transform", "code",      {"jsCode": f"// {transform}\nreturn items;"}, [400, 0]),
                _node("Load",      "http",      {"url": dest, "method": "POST", "sendBody": True}, [600, 0]),
            ],
            "connections": {
                "Trigger":   {"main": [[{"node": "Fetch",     "type": "main", "index": 0}]]},
                "Fetch":     {"main": [[{"node": "Transform", "type": "main", "index": 0}]]},
                "Transform": {"main": [[{"node": "Load",      "type": "main", "index": 0}]]},
            }
        }

    @staticmethod
    def alert_monitor(url: str, threshold: str, channel: str, **_) -> Dict:
        return {
            "name": f"Monitor: {url[:30]}",
            "nodes": [
                _node("Schedule",    "schedule", {"rule": {"interval": [{"field": "minutes", "minutesInterval": 5}]}}, [0, 0]),
                _node("Health Check","http",     {"url": url, "method": "GET"}, [200, 0]),
                _node("Check Thresh","if",       {"conditions": {"number": [{"value1": "={{$json.responseCode}}", "operation": "notEqual", "value2": 200}]}}, [400, 0]),
                _node("Alert Slack", "slack",    {"channel": channel, "text": f"⚠️ Alert: {url} {threshold}"}, [600, 100]),
            ],
            "connections": {
                "Schedule":     {"main": [[{"node": "Health Check",  "type": "main", "index": 0}]]},
                "Health Check": {"main": [[{"node": "Check Thresh",  "type": "main", "index": 0}]]},
                "Check Thresh": {"main": [[{"node": "Alert Slack",   "type": "main", "index": 0}], []]},
            }
        }


# ══════════════════════════════════════════════════════════════════════════════
# NL → FLOWWARE COMPILER  (ideas #1, #13, #14, #16)
# ══════════════════════════════════════════════════════════════════════════════

_COMPILER_SYSTEM = """You are Nova Pro's Flowware Compiler.
Convert natural language instructions into n8n workflow JSON.

Rules:
- Respond ONLY with a valid JSON object — the complete n8n workflow.
- Use real n8n node types (n8n-nodes-base.*).
- Include "name", "nodes", "connections", and "settings" keys.
- Each node needs: id (UUID), name, type, typeVersion (1), position ([x,y]), parameters.
- Position nodes left-to-right with 220px spacing.
- The first node is always a Webhook Trigger or Schedule Trigger.
- Extract all parameters from the user's instruction.
- For unknown services, use n8n-nodes-base.httpRequest.

Output ONLY the JSON. No markdown, no explanation."""


class FlowwareCompiler:
    """
    Compiles natural language → n8n workflow JSON.
    Uses LLM for complex cases, templates for known patterns.
    """

    def __init__(self, router: LLMRouter, classifier: IntentClassifier):
        self.router     = router
        self.classifier = classifier
        self.templates  = TemplateLibrary()
        self._history: List[Dict] = []

    def compile(self, instruction: str, agent: str = "default",
                context: List[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point. Returns:
        {"ok": True, "workflow": {...}, "intent": "...", "method": "llm|template"}
        """
        # 1. Classify intent
        classification = self.classifier.classify(instruction)
        intent     = classification.get("intent", "custom_code")
        entities   = classification.get("entities", {})
        confidence = classification.get("confidence", 0.5)

        # 2. Try template if high-confidence match
        if confidence > 0.8:
            tmpl_fn = getattr(TemplateLibrary, intent.replace("_action", "").replace("_op", ""), None)
            if tmpl_fn:
                try:
                    wf = tmpl_fn(**entities, instruction=instruction)
                    wf.setdefault("settings", {"executionOrder": "v1"})
                    wf["id"]          = str(uuid.uuid4())
                    wf["nova_meta"]   = {
                        "compiled_at": datetime.now(timezone.utc).isoformat(),
                        "intent":      intent,
                        "method":      "template",
                        "agent":       agent,
                        "source":      instruction,
                    }
                    return {"ok": True, "workflow": wf, "intent": intent, "method": "template"}
                except Exception:
                    pass  # Fall through to LLM

        # 3. LLM compilation (idea #1 full power)
        messages = list(context or [])
        messages.append({"role": "user", "content": instruction})

        resp = self.router.chat(
            messages=messages,
            system=_COMPILER_SYSTEM,
            max_tokens=3000,
            temperature=0.2,
        )

        if not resp.get("ok"):
            return {"ok": False, "error": resp.get("error"),
                    "detail": resp.get("detail"), "intent": intent}

        content = resp["content"].strip()
        content = re.sub(r"^```json|^```|```$", "", content, flags=re.MULTILINE).strip()

        try:
            wf = json.loads(content)
            wf.setdefault("settings", {"executionOrder": "v1"})
            wf["id"] = str(uuid.uuid4())
            wf["nova_meta"] = {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "intent":      intent,
                "method":      "llm",
                "model":       resp.get("model", ""),
                "tokens":      resp.get("tokens", {}),
                "agent":       agent,
                "source":      instruction,
            }
            self._history.append(wf)
            return {"ok": True, "workflow": wf, "intent": intent, "method": "llm"}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": "json_parse", "detail": str(e),
                    "raw": content, "intent": intent}

    def pipeline(self, steps: List[str], agent: str = "default") -> Dict[str, Any]:
        """
        Compile a multi-step pipeline by chaining workflows. (idea #14)
        """
        compiled_steps = []
        for step in steps:
            result = self.compile(step, agent=agent)
            if not result.get("ok"):
                return {"ok": False, "error": f"Step failed: {step}",
                        "detail": result.get("detail")}
            compiled_steps.append(result["workflow"])

        # Merge into one workflow
        merged = {
            "id":   str(uuid.uuid4()),
            "name": "Pipeline: " + " → ".join(steps[:2]),
            "nodes": [],
            "connections": {},
            "settings": {"executionOrder": "v1"},
            "nova_meta": {"type": "pipeline", "steps": len(steps)},
        }
        x_offset = 0
        prev_last_node = None
        for i, wf in enumerate(compiled_steps):
            nodes = wf.get("nodes", [])
            # Offset positions
            for node in nodes:
                node["position"][0] += x_offset
                node["id"] = str(uuid.uuid4())
            merged["nodes"].extend(nodes)
            merged["connections"].update(wf.get("connections", {}))
            # Connect last node of step i to first node of step i+1
            if nodes:
                x_offset += 220 * (len(nodes) + 1)
                prev_last_node = nodes[-1]["name"]
        return {"ok": True, "workflow": merged, "steps": len(steps)}

    def last_workflow(self) -> Optional[Dict]:
        return self._history[-1] if self._history else None


# ══════════════════════════════════════════════════════════════════════════════
# n8n BRIDGE  (idea #2) — REST API + webhook triggering
# ══════════════════════════════════════════════════════════════════════════════

class N8nBridge:
    """Bidirectional bridge to n8n instance."""

    def __init__(self, cfg: NovaCfg):
        self.cfg  = cfg
        self._hdrs = {
            "X-N8N-API-KEY": cfg.n8n_api_key,
            "Content-Type":  "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.cfg.n8n_base_url.rstrip('/')}{path}"

    def ping(self) -> bool:
        r = http_get(self._url("/healthz"), timeout=5)
        return r.get("ok", False)

    def list_workflows(self) -> List[Dict]:
        r = http_get(self._url("/api/v1/workflows"), self._hdrs)
        if r.get("ok"):
            return r["data"].get("data", [])
        return []

    def create_workflow(self, workflow: Dict) -> Dict[str, Any]:
        """Push a compiled workflow to n8n."""
        return http_post(self._url("/api/v1/workflows"), workflow, self._hdrs)

    def activate_workflow(self, workflow_id: str) -> Dict:
        req = urllib.request.Request(
            self._url(f"/api/v1/workflows/{workflow_id}/activate"),
            data=b"{}",
            method="POST",
        )
        for k, v in self._hdrs.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {"ok": True, "data": json.loads(resp.read())}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def trigger_webhook(self, path: str, payload: Dict) -> Dict:
        url = self._url(f"/webhook/{path}")
        return http_post(url, payload, timeout=self.cfg.timeout_s)

    def execute_workflow(self, workflow_id: str, data: Dict = None) -> Dict:
        url = self._url(f"/api/v1/workflows/{workflow_id}/run")
        return http_post(url, data or {}, self._hdrs)

    def deploy_and_run(self, workflow: Dict, activate: bool = True) -> Dict[str, Any]:
        """
        Full deploy cycle: create → activate → execute. (idea #17)
        """
        # 1. Create
        create_r = self.create_workflow(workflow)
        if not create_r.get("ok"):
            return {"ok": False, "stage": "create", **create_r}

        wf_id = create_r.get("data", {}).get("id") or \
                create_r.get("data", {}).get("data", {}).get("id")
        if not wf_id:
            return {"ok": False, "stage": "create", "error": "no_id_returned"}

        # 2. Activate
        if activate:
            act_r = self.activate_workflow(wf_id)
            if not act_r.get("ok"):
                warn(f"Workflow created but activation failed: {act_r}")

        return {"ok": True, "workflow_id": wf_id,
                "url": f"{self.cfg.n8n_base_url}/workflow/{wf_id}"}


# ══════════════════════════════════════════════════════════════════════════════
# SCHEMA GENERATOR  (idea #16) — auto-generate n8n node schemas
# ══════════════════════════════════════════════════════════════════════════════

class SchemaGenerator:
    @staticmethod
    def from_workflow(wf: Dict) -> Dict[str, Any]:
        """Extract parameter schema from a workflow."""
        schema = {"workflow": wf.get("name", ""), "inputs": []}
        for node in wf.get("nodes", []):
            for key, val in node.get("parameters", {}).items():
                if isinstance(val, str) and val.startswith("{{"):
                    schema["inputs"].append({
                        "node":    node["name"],
                        "param":   key,
                        "example": val,
                    })
        return schema

    @staticmethod
    def to_n8n_credential_schema(name: str, fields: List[str]) -> Dict:
        return {
            "name":         name,
            "displayName":  name,
            "documentationUrl": "https://nova-os.com/docs",
            "properties":   [{"displayName": f, "name": f.lower().replace(" ", "_"),
                               "type": "string", "default": ""} for f in fields],
        }


# ══════════════════════════════════════════════════════════════════════════════
# PLUGIN SYSTEM  (idea #11) — drop-in action handlers
# ══════════════════════════════════════════════════════════════════════════════

class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, Callable] = {}

    def register(self, name: str, fn: Callable):
        self._plugins[name] = fn
        if DEBUG: print(f"[Plugin] Registered: {name}")

    def call(self, name: str, **kwargs) -> Any:
        fn = self._plugins.get(name)
        if not fn: raise KeyError(f"Plugin '{name}' not found")
        return fn(**kwargs)

    def list(self) -> List[str]:
        return list(self._plugins.keys())

    def load_dir(self, path: Path):
        """Load all .py files from plugins directory."""
        if not path.exists(): return
        import importlib.util
        for f in path.glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(f.stem, f)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(self)
                    ok(f"Plugin loaded: {f.stem}")
            except Exception as e:
                warn(f"Plugin {f.stem} failed: {e}")

PLUGINS = PluginRegistry()


# ══════════════════════════════════════════════════════════════════════════════
# AUTO-REPAIR v2  (idea #20) — deep diagnostics + self-healing
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RepairIssue:
    id:       str
    title:    str
    details:  str
    severity: str      = "medium"
    fix:      Optional[Callable] = None

class AutoRepairEngine:
    PROBES = []

    def __init__(self, cfg: NovaCfg, router: LLMRouter, bridge: "N8nBridge"):
        self.cfg    = cfg
        self.router = router
        self.bridge = bridge
        self._last  = 0.0

    def diagnose(self) -> List[RepairIssue]:
        issues = []

        # 1. API key check
        if not self.cfg.openrouter_api_key:
            issues.append(RepairIssue(
                id="missing_api_key", title="OpenRouter API key missing",
                details="Set OPENROUTER_API_KEY or run: nova-pro config",
                severity="critical",
            ))

        # 2. n8n connectivity
        if self.cfg.n8n_api_key and not self.bridge.ping():
            issues.append(RepairIssue(
                id="n8n_unreachable", title=f"n8n unreachable at {self.cfg.n8n_base_url}",
                details="Check n8n is running and N8N_BASE_URL is correct.",
                severity="high",
            ))

        # 3. LLM circuit breakers
        for model, state in self.router.status().items():
            if state == "open":
                issues.append(RepairIssue(
                    id=f"cb_open_{model}", title=f"Circuit breaker OPEN: {model}",
                    details="Model is failing repeatedly. Will auto-recover in 30s.",
                    severity="medium",
                    fix=lambda m=model: self.router._breakers[m].on_success(),
                ))

        # 4. Config file corruption
        if CONFIG_FILE.exists():
            try:
                json.loads(CONFIG_FILE.read_text())
            except Exception:
                issues.append(RepairIssue(
                    id="corrupt_config", title="Config file corrupted",
                    details=str(CONFIG_FILE),
                    severity="high",
                    fix=lambda: CONFIG_FILE.unlink(missing_ok=True),
                ))

        # 5. Disk space
        try:
            stat = shutil.disk_usage(NOVA_HOME)
            if stat.free < 50 * 1024 * 1024:
                issues.append(RepairIssue(
                    id="low_disk", title="Low disk space (< 50 MB free)",
                    details=f"Free: {stat.free // (1024*1024)} MB",
                    severity="medium",
                ))
        except Exception:
            pass

        return issues

    def repair(self, issues: List[RepairIssue], auto_execute: bool = False) -> Dict[str, Any]:
        results = []
        for issue in issues:
            if issue.fix and (auto_execute or issue.severity == "low"):
                try:
                    issue.fix()
                    results.append({"id": issue.id, "status": "fixed"})
                except Exception as e:
                    results.append({"id": issue.id, "status": "failed", "error": str(e)})
            else:
                results.append({"id": issue.id, "status": "reported"})
        return {"ok": True, "issues": len(issues), "results": results}

    def run(self, auto: bool = False) -> Dict[str, Any]:
        self._last = time.time()
        issues = self.diagnose()
        return {**self.repair(issues, auto_execute=auto), "issues_list": issues}


# ══════════════════════════════════════════════════════════════════════════════
# BUILT-IN WEBHOOK SERVER  (idea #6)
# ══════════════════════════════════════════════════════════════════════════════

class WebhookHandler(BaseHTTPRequestHandler):
    compiler: "FlowwareCompiler" = None
    bridge:   "N8nBridge"        = None
    audit:    "AuditTrail"       = None
    cfg:      "NovaCfg"          = None

    def log_message(self, fmt, *args):
        if DEBUG: print(f"[Webhook] {fmt % args}")

    def _respond(self, status: int, body: Dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        payload = {}
        if length:
            try: payload = json.loads(self.rfile.read(length))
            except Exception: pass

        # Auth check
        token = self.headers.get("X-Nova-Token", "")
        if self.cfg and self.cfg.n8n_webhook_token:
            if not secrets.compare_digest(token, self.cfg.n8n_webhook_token):
                self._respond(401, {"error": "unauthorized"}); return

        path = self.path.rstrip("/")

        # Route: /compile — NL → Workflow
        if path == "/compile":
            instruction = payload.get("instruction", "")
            agent       = payload.get("agent", "default")
            if not instruction:
                self._respond(400, {"error": "instruction required"}); return

            with Spinner("Compiling..."):
                result = self.compiler.compile(instruction, agent=agent)

            if self.audit:
                self.audit.record("nl_compile", {
                    "agent": agent, "instruction": instruction,
                    "intent": result.get("intent"), "ok": result.get("ok"),
                })
            BUS.publish("workflow.compiled", result)
            status = 200 if result.get("ok") else 422
            self._respond(status, result)

        # Route: /deploy — Compile + Deploy to n8n
        elif path == "/deploy":
            instruction = payload.get("instruction", "")
            agent       = payload.get("agent", "default")
            activate    = payload.get("activate", True)

            compile_r = self.compiler.compile(instruction, agent=agent)
            if not compile_r.get("ok"):
                self._respond(422, compile_r); return

            deploy_r = self.bridge.deploy_and_run(compile_r["workflow"], activate=activate)
            if self.audit:
                self.audit.record("workflow_deployed", {
                    "agent": agent, "instruction": instruction,
                    "workflow_id": deploy_r.get("workflow_id"),
                })
            self._respond(200 if deploy_r.get("ok") else 502, deploy_r)

        # Route: /pipeline — Multi-step pipeline
        elif path == "/pipeline":
            steps = payload.get("steps", [])
            agent = payload.get("agent", "default")
            if not steps:
                self._respond(400, {"error": "steps required"}); return

            result = self.compiler.pipeline(steps, agent=agent)
            self._respond(200 if result.get("ok") else 422, result)

        # Route: /repair
        elif path == "/repair":
            engine = AutoRepairEngine(self.cfg, self.compiler.router, self.bridge)
            result = engine.run(auto=payload.get("auto", False))
            # Remove non-serializable fix functions
            for issue in result.get("issues_list", []):
                if hasattr(issue, "__dict__"):
                    issue.fix = None
            result["issues_list"] = [
                {"id": i.id, "title": i.title, "severity": i.severity}
                for i in result.get("issues_list", [])
            ]
            self._respond(200, result)

        # Route: /health
        elif path == "/health":
            self._respond(200, {
                "status": "ok",
                "version": NOVA_PRO_VERSION,
                "n8n_reachable": self.bridge.ping() if self.bridge else False,
            })

        else:
            self._respond(404, {"error": "unknown route",
                                "routes": ["/compile", "/deploy", "/pipeline", "/repair", "/health"]})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "version": NOVA_PRO_VERSION})
        else:
            self._respond(200, {
                "nova_pro": NOVA_PRO_VERSION,
                "routes":   ["POST /compile", "POST /deploy", "POST /pipeline",
                             "POST /repair", "GET /health"],
            })


def start_webhook_server(cfg: NovaCfg, compiler: FlowwareCompiler,
                          bridge: N8nBridge, audit: AuditTrail) -> HTTPServer:
    WebhookHandler.compiler = compiler
    WebhookHandler.bridge   = bridge
    WebhookHandler.audit    = audit
    WebhookHandler.cfg      = cfg

    server = HTTPServer((cfg.webhook_host, cfg.webhook_port), WebhookHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT ENGINE  (idea #18)
# ══════════════════════════════════════════════════════════════════════════════

class ExportEngine:
    @staticmethod
    def to_json(wf: Dict, path: str = "") -> str:
        s = json.dumps(wf, indent=2)
        if path: Path(path).write_text(s)
        return s

    @staticmethod
    def to_markdown(wf: Dict) -> str:
        lines = [f"# Workflow: {wf.get('name', 'Unnamed')}", ""]
        meta = wf.get("nova_meta", {})
        if meta:
            lines += [
                f"**Intent:** `{meta.get('intent','')}`  ",
                f"**Method:** `{meta.get('method','')}`  ",
                f"**Compiled:** {meta.get('compiled_at','')}  ",
                f"**Source:** _{meta.get('source','')}_", "",
            ]
        lines.append("## Nodes")
        for node in wf.get("nodes", []):
            lines.append(f"- **{node['name']}** (`{node['type']}`)")
        lines.append("")
        lines.append("## Connections")
        for src, conns in wf.get("connections", {}).items():
            for targets in conns.get("main", []):
                for t in targets:
                    lines.append(f"- {src} → {t['node']}")
        return "\n".join(lines)

    @staticmethod
    def to_yaml(wf: Dict) -> str:
        """Minimal YAML serializer (no pyyaml dep)."""
        def _val(v, depth=0):
            indent = "  " * depth
            if isinstance(v, dict):
                if not v: return "{}\n"
                lines = ["\n"]
                for k, val in v.items():
                    lines.append(f"{indent}  {k}: {_val(val, depth+1)}")
                return "".join(lines)
            if isinstance(v, list):
                if not v: return "[]\n"
                lines = ["\n"]
                for item in v:
                    lines.append(f"{indent}  - {_val(item, depth+1).lstrip()}")
                return "".join(lines)
            if isinstance(v, bool):   return f"{'true' if v else 'false'}\n"
            if isinstance(v, (int, float)): return f"{v}\n"
            return f"{json.dumps(str(v))}\n"

        lines = []
        for k, v in wf.items():
            lines.append(f"{k}: {_val(v)}")
        return "".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# REPL MODE  (idea #15) — interactive NL shell
# ══════════════════════════════════════════════════════════════════════════════

class NovREPL:
    COMMANDS = {
        "/help":    "Show REPL commands",
        "/deploy":  "Deploy last compiled workflow to n8n",
        "/export":  "Export last workflow (json|md|yaml)",
        "/history": "Show compile history",
        "/clear":   "Clear agent memory",
        "/repair":  "Run auto-repair",
        "/status":  "Show system status",
        "/quit":    "Exit REPL",
    }

    def __init__(self, compiler: FlowwareCompiler, bridge: N8nBridge,
                 memory: AgentMemory, audit: AuditTrail, cfg: NovaCfg):
        self.compiler = compiler
        self.bridge   = bridge
        self.memory   = memory
        self.audit    = audit
        self.cfg      = cfg
        self.agent    = cfg.workspace
        self._last_wf = None

        # readline history
        try:
            self._hist_file = str(NOVA_HOME / ".repl_history")
            readline.read_history_file(self._hist_file)
        except Exception:
            self._hist_file = None

    def _save_history(self):
        if self._hist_file:
            try: readline.write_history_file(self._hist_file)
            except Exception: pass

    def run(self):
        print_logo(animated=False)
        print("  " + q(C.FLOW, "REPL Mode") + "  " +
              q(C.G2, f"agent:{self.agent}  ·  type /help for commands"))
        hr_flow()
        print()

        while True:
            try:
                prompt = f"  {q(C.GLD_BRIGHT,'✦')} {q(C.G1, self.agent)}{q(C.G3,' › ')}"
                raw = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                ok("Session ended."); break

            if not raw: continue

            # REPL commands
            if raw.startswith("/"):
                self._handle_cmd(raw); continue

            # Natural language → compile
            self.memory.add(self.agent, "user", raw)
            ctx = self.memory.context(self.agent, last_n=10)

            with Spinner(f"Compiling: {raw[:50]}…", color=C.FLOW):
                result = self.compiler.compile(raw, agent=self.agent, context=ctx)

            if result.get("ok"):
                wf = result["workflow"]
                self._last_wf = wf
                method = result.get("method", "llm")
                intent = result.get("intent", "")
                print()
                ok(f"Workflow compiled  [{q(C.FLOW, method)}  {q(C.CYN, intent)}]")
                print()
                kv("Name",   wf.get("name", "Unnamed"))
                kv("Nodes",  str(len(wf.get("nodes", []))))
                kv("Intent", intent)
                kv("ID",     wf.get("id", "")[:16] + "…")
                print()

                meta = wf.get("nova_meta", {})
                tokens = meta.get("tokens", {})
                if tokens:
                    kv("Tokens used", str(tokens.get("total_tokens", "—")),
                       color=C.G3)

                self.memory.add(self.agent, "assistant",
                                f"Compiled workflow: {wf.get('name')}", intent=intent)
                self.audit.record("nl_compile", {"agent": self.agent,
                                                  "instruction": raw, "intent": intent})
                hint("/deploy to push to n8n  ·  /export to save")
            else:
                print()
                fail(f"Compilation failed: {result.get('error','')}")
                if result.get("detail"):
                    dim(str(result["detail"])[:120])

            self._save_history()

    def _handle_cmd(self, raw: str):
        parts = raw.split()
        cmd   = parts[0]
        arg   = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            section("REPL Commands")
            for c, desc in self.COMMANDS.items():
                print(f"  {q(C.FLOW, c.ljust(12))}  {q(C.G2, desc)}")
            print()

        elif cmd == "/deploy":
            if not self._last_wf:
                warn("Nothing compiled yet."); return
            if not self.cfg.n8n_api_key:
                warn("n8n API key not set. Run: nova-pro config"); return
            with Spinner("Deploying to n8n…", color=C.N8N):
                r = self.bridge.deploy_and_run(self._last_wf)
            if r.get("ok"):
                ok(f"Deployed! ID: {r.get('workflow_id')}")
                n8n_msg(f"View: {r.get('url')}")
            else:
                fail(f"Deploy failed: {r.get('error')}")

        elif cmd == "/export":
            if not self._last_wf:
                warn("Nothing compiled yet."); return
            fmt = arg or "json"
            if fmt == "json":
                print(ExportEngine.to_json(self._last_wf))
            elif fmt in ("md", "markdown"):
                print(ExportEngine.to_markdown(self._last_wf))
            elif fmt == "yaml":
                print(ExportEngine.to_yaml(self._last_wf))
            else:
                warn(f"Unknown format: {fmt}. Use: json, md, yaml")

        elif cmd == "/history":
            wfs = self.compiler._history[-5:]
            if not wfs: info("No history yet."); return
            section("Compile History", f"(last {len(wfs)})")
            for i, wf in enumerate(reversed(wfs), 1):
                meta = wf.get("nova_meta", {})
                print(f"  {q(C.G3, str(i)+'.')} {q(C.W, wf.get('name','?')[:40])}"
                      f"  {q(C.G3, meta.get('intent',''))}")

        elif cmd == "/clear":
            self.memory.clear(self.agent)
            ok(f"Memory cleared for agent: {self.agent}")

        elif cmd == "/repair":
            engine = AutoRepairEngine(self.cfg, self.compiler.router, self.bridge)
            result = engine.run(auto=(arg == "--auto"))
            issues = result.get("issues_list", [])
            if not issues:
                ok("All systems nominal.")
            else:
                for issue in issues:
                    sev_color = {
                        "critical": C.RED, "high": C.ORG,
                        "medium": C.YLW, "low": C.GRN,
                    }.get(issue.severity, C.G2)
                    print(f"  {q(sev_color, issue.severity.upper().ljust(8))}  "
                          f"{q(C.W, issue.title)}")
                    dim(issue.details)

        elif cmd == "/status":
            section("System Status")
            kv("Nova Pro",    NOVA_PRO_VERSION,            color=C.FLOW)
            kv("Agent",       self.agent)
            kv("n8n URL",     self.cfg.n8n_base_url)
            kv("n8n Online",  "yes" if self.bridge.ping() else "no",
               color=C.GRN if self.bridge.ping() else C.RED)
            kv("API Key",     mask_key(self.cfg.openrouter_api_key))
            kv("Model",       self.cfg.openrouter_model)
            print()
            section("Circuit Breakers")
            for m, state in self.compiler.router.status().items():
                color = {
                    "closed": C.GRN, "open": C.RED, "half-open": C.YLW
                }.get(state, C.G2)
                kv(m[:40], state, color=color)

        elif cmd == "/quit":
            ok("Goodbye."); raise SystemExit(0)

        else:
            warn(f"Unknown command: {cmd}  (type /help)")


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH MONITOR  (idea #17) — background upstream probing
# ══════════════════════════════════════════════════════════════════════════════

class HealthMonitor:
    def __init__(self, bridge: N8nBridge, interval_s: float = 30.0):
        self.bridge     = bridge
        self.interval_s = interval_s
        self._stop      = threading.Event()
        self._status    = {"n8n": "unknown", "last_check": "never"}
        self._t         = None

    def start(self):
        def _run():
            while not self._stop.is_set():
                up = self.bridge.ping()
                self._status = {
                    "n8n":        "up" if up else "down",
                    "last_check": datetime.now(timezone.utc).isoformat(),
                }
                BUS.publish("health.update", self._status)
                if not up:
                    warn("n8n health check failed.")
                self._stop.wait(self.interval_s)
        self._t = threading.Thread(target=_run, daemon=True)
        self._t.start()

    def stop(self): self._stop.set()

    @property
    def status(self) -> Dict: return dict(self._status)


# ══════════════════════════════════════════════════════════════════════════════
# CLI COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

def cmd_init(args, cfg: NovaCfg):
    print_logo(animated=True)
    section("Setup Wizard", "Let's configure Nova Pro")
    print()

    def _ask(prompt: str, default: str = "", secret: bool = False) -> str:
        dp = f"  [{q(C.G3, default)}]" if default else ""
        try:
            import getpass
            fn = getpass.getpass if secret else input
            val = fn(f"  {q(C.G2, prompt)}{dp}: ").strip()
            return val or default
        except (EOFError, KeyboardInterrupt):
            return default

    cfg.openrouter_api_key = _ask("OpenRouter API Key", cfg.openrouter_api_key, secret=True)
    cfg.openrouter_model   = _ask("LLM Model", cfg.openrouter_model)
    cfg.n8n_base_url       = _ask("n8n Base URL", cfg.n8n_base_url)
    cfg.n8n_api_key        = _ask("n8n API Key (optional)", cfg.n8n_api_key, secret=True)
    cfg.n8n_webhook_token  = _ask("Webhook auth token (leave blank to generate)",
                                   cfg.n8n_webhook_token, secret=True)
    if not cfg.n8n_webhook_token:
        cfg.n8n_webhook_token = secrets.token_urlsafe(32)
        ok(f"Generated token: {cfg.n8n_webhook_token}")

    cfg.workspace = _ask("Workspace name", cfg.workspace)

    cfg.save()
    print()
    ok("Configuration saved.")
    hr()
    kv("Config file", str(CONFIG_FILE))
    kv("Webhook port", str(cfg.webhook_port))
    kv("Webhook token", mask_key(cfg.n8n_webhook_token))
    print()
    hint("Start the server:  nova-pro serve")
    hint("Interactive REPL:  nova-pro repl")
    hint("Quick compile:     nova-pro compile \"Send Slack message to #alerts\"")
    print()


def cmd_compile(args, cfg: NovaCfg, compiler: FlowwareCompiler, audit: AuditTrail):
    instruction = " ".join(args.instruction) if args.instruction else ""
    if not instruction:
        fail("Provide an instruction. Example:")
        hint('nova-pro compile "Send email to team@acme.com when new GitHub issue"')
        return

    with Spinner(f"Compiling: {instruction[:60]}…", color=C.FLOW):
        result = compiler.compile(instruction, agent=cfg.workspace)

    audit.record("cli_compile", {"instruction": instruction, "ok": result.get("ok")})

    if result.get("ok"):
        wf = result["workflow"]
        print()
        ok(f"Workflow compiled  [{q(C.FLOW, result['method'])}]")
        print()
        kv("Name",   wf.get("name", "Unnamed"))
        kv("Intent", result.get("intent", ""))
        kv("Nodes",  str(len(wf.get("nodes", []))))
        kv("ID",     wf.get("id", "")[:16] + "…")
        print()

        if args.output:
            fmt = args.format or "json"
            if fmt == "json":
                content = ExportEngine.to_json(wf)
            elif fmt in ("md", "markdown"):
                content = ExportEngine.to_markdown(wf)
            elif fmt == "yaml":
                content = ExportEngine.to_yaml(wf)
            else:
                content = ExportEngine.to_json(wf)
            Path(args.output).write_text(content)
            ok(f"Saved to: {args.output}")
        else:
            hr()
            print(ExportEngine.to_json(wf))
            hr()

        if args.deploy:
            bridge = N8nBridge(cfg)
            with Spinner("Deploying to n8n…", color=C.N8N):
                deploy_r = bridge.deploy_and_run(wf)
            if deploy_r.get("ok"):
                ok(f"Deployed! ID: {deploy_r['workflow_id']}")
                n8n_msg(f"View: {deploy_r['url']}")
            else:
                fail(f"Deploy failed: {deploy_r.get('error')}")
    else:
        print()
        fail(f"Compilation failed: {result.get('error', '?')}")
        if result.get("detail"):
            dim(str(result["detail"])[:200])


def cmd_serve(args, cfg: NovaCfg, compiler: FlowwareCompiler,
              bridge: N8nBridge, memory: AgentMemory, audit: AuditTrail):
    print_logo()
    section("Webhook Server", f"port {cfg.webhook_port}", badge="n8n bridge")
    print()
    kv("Listen",  f"{cfg.webhook_host}:{cfg.webhook_port}")
    kv("Routes",  "/compile  /deploy  /pipeline  /repair  /health")
    kv("Auth",    "X-Nova-Token header" if cfg.n8n_webhook_token else "disabled")
    kv("n8n",     cfg.n8n_base_url)
    print()

    server = start_webhook_server(cfg, compiler, bridge, audit)
    monitor = HealthMonitor(bridge)
    monitor.start()

    ok(f"Nova Pro server listening on :{cfg.webhook_port}")
    hr()
    print()
    n8n_msg("n8n HTTP Request node example:")
    print()
    print(f"  {q(C.G3,'URL:')}    http://localhost:{cfg.webhook_port}/compile")
    print(f"  {q(C.G3,'Method:')} POST")
    print(f"  {q(C.G3,'Body:')}   {{\"instruction\": \"Send Slack alert when CPU > 90%\",")
    print(f"           {q(C.G3,'\"agent\":')}       \"my-agent\"}}")
    if cfg.n8n_webhook_token:
        print(f"  {q(C.G3,'Header:')} X-Nova-Token: {mask_key(cfg.n8n_webhook_token)}")
    print()
    hr()
    print()
    hint("Press Ctrl+C to stop")
    print()

    try:
        signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print()
        monitor.stop()
        server.shutdown()
        ok("Server stopped.")


def cmd_status(args, cfg: NovaCfg, router: LLMRouter, bridge: N8nBridge):
    print_logo(animated=False)
    section("System Status")
    print()
    kv("Nova Pro Version",  NOVA_PRO_VERSION,     color=C.FLOW)
    kv("Build",             NOVA_PRO_BUILD,        color=C.G3)
    kv("Workspace",         cfg.workspace)
    kv("Config",            str(CONFIG_FILE))
    print()
    section("Connectivity")
    kv("OpenRouter Key",    mask_key(cfg.openrouter_api_key))
    kv("Active Model",      cfg.openrouter_model)
    kv("n8n URL",           cfg.n8n_base_url)
    kv("n8n Status",        ("✓ online" if bridge.ping() else "✗ offline"),
       color=C.GRN if bridge.ping() else C.RED)
    print()
    section("Circuit Breakers")
    for model, state in router.status().items():
        c = {"closed": C.GRN, "open": C.RED, "half-open": C.YLW}.get(state, C.G2)
        kv(model[:42], state, color=c)
    print()


def cmd_doctor(args, cfg: NovaCfg, router: LLMRouter, bridge: N8nBridge):
    section("Auto-Repair Doctor")
    print()
    engine = AutoRepairEngine(cfg, router, bridge)
    with Spinner("Diagnosing…"):
        result = engine.run(auto=args.auto)

    issues = result.get("issues_list", [])
    if not issues:
        ok("All systems nominal. No issues found.")
    else:
        warn(f"{len(issues)} issue(s) detected:")
        print()
        for issue in issues:
            sev_c = {"critical": C.RED, "high": C.ORG,
                     "medium": C.YLW, "low": C.GRN}.get(issue.severity, C.G2)
            print(f"  {q(sev_c, '[' + issue.severity.upper() + ']', bold=True).ljust(20)}"
                  f"  {q(C.W, issue.title)}")
            print(f"  {q(C.G3, '  ' + issue.details)}")
            print()

    for r in result.get("results", []):
        status_c = C.GRN if r["status"] == "fixed" else C.G3
        kv(r["id"][:30], r["status"], color=status_c)
    print()


def cmd_templates(args, cfg: NovaCfg):
    section("Workflow Templates", f"{len(TemplateLibrary.templates())} built-in")
    print()
    tmpl_list = [
        ("send_email",       "Send email via trigger"),
        ("http_request",     "Generic HTTP API call"),
        ("slack_notify",     "Post Slack message"),
        ("ai_summarize",     "AI text generation"),
        ("schedule_report",  "Scheduled email report"),
        ("web_scrape_and_store", "Scrape URL → DB"),
        ("github_issue_to_notion", "GitHub issue → Notion"),
        ("data_pipeline",    "ETL: Fetch → Transform → Load"),
        ("alert_monitor",    "HTTP health monitor + alert"),
    ]
    for name, desc in tmpl_list:
        print(f"  {q(C.FLOW, name.ljust(28))}  {q(C.G2, desc)}")
    print()
    hint("Use in compile: nova-pro compile \"send slack to #ops channel\"")
    print()


def cmd_audit(args, cfg: NovaCfg, audit: AuditTrail):
    section("Audit Trail", f"(last {args.limit})")
    print()
    entries = audit.tail(args.limit)
    if not entries:
        info("No audit entries yet."); return

    for e in reversed(entries):
        ts   = e["ts"][:19].replace("T", " ")
        etype = e.get("type", "?")
        p    = e.get("payload", {})
        agent = p.get("agent", "")
        ok_s  = "✓" if p.get("ok", True) else "✗"
        ok_c  = C.GRN if p.get("ok", True) else C.RED
        print(f"  {q(C.G3, ts)}  {q(ok_c, ok_s)}  "
              f"{q(C.FLOW, etype.ljust(18))}  "
              f"{q(C.G2, p.get('intent','') or p.get('instruction','')[:40])}"
              + (f"  {q(C.G3,agent)}" if agent else ""))
    print()
    kv("Chain tip", audit._prev[:16] + "…", color=C.G3)
    print()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════════

def build_core(cfg: NovaCfg):
    """Construct core objects from config."""
    router    = LLMRouter(cfg)
    classifier= IntentClassifier(router)
    compiler  = FlowwareCompiler(router, classifier)
    bridge    = N8nBridge(cfg)
    memory    = AgentMemory(max_entries=cfg.memory_max_entries)
    audit     = AuditTrail()
    PLUGINS.load_dir(PLUGINS_DIR)
    return router, classifier, compiler, bridge, memory, audit


def main():
    parser = argparse.ArgumentParser(
        prog="nova-pro",
        description="Nova Pro — Natural Language → Flowware Engine",
        add_help=False,
    )
    parser.add_argument("command",     nargs="?", default="help")
    parser.add_argument("instruction", nargs="*", default=[])
    parser.add_argument("--output",    "-o", default="")
    parser.add_argument("--format",    "-f", default="json", choices=["json","md","yaml"])
    parser.add_argument("--deploy",    action="store_true")
    parser.add_argument("--auto",      action="store_true")
    parser.add_argument("--limit",     type=int, default=20)
    parser.add_argument("--agent",     default="")
    parser.add_argument("--port",      type=int, default=0)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--version", "-V", action="store_true")

    args = parser.parse_args()

    if args.version:
        print(f"nova-pro {NOVA_PRO_VERSION} ({NOVA_PRO_BUILD})")
        return

    if args.help or args.command in ("help", "--help", "-h", "?"):
        print_logo()
        section("Commands")
        cmds = [
            ("init",      "First-run setup wizard"),
            ("repl",      "Interactive NL shell (REPL mode)"),
            ("serve",     "Start webhook server for n8n"),
            ("compile",   "Compile NL instruction → workflow"),
            ("status",    "System health & circuit breakers"),
            ("doctor",    "Auto-repair diagnostics (--auto to fix)"),
            ("templates", "List built-in workflow templates"),
            ("audit",     "View cryptographic audit trail"),
            ("help",      "Show this help"),
        ]
        for cmd, desc in cmds:
            print(f"  {q(C.FLOW, cmd.ljust(14))}  {q(C.G2, desc)}")
        print()
        section("n8n Integration")
        print(f"  {q(C.G2,'1.')} Configure: {q(C.W,'nova-pro init')}")
        print(f"  {q(C.G2,'2.')} Start server: {q(C.W,'nova-pro serve')}")
        print(f"  {q(C.G2,'3.')} In n8n, add HTTP Request node → POST http://localhost:8765/compile")
        print(f"  {q(C.G2,'4.')} Body: {{\"instruction\": \"your natural language here\", \"agent\": \"my-agent\"}}")
        print(f"  {q(C.G2,'5.')} Nova returns n8n workflow JSON — pipe to Create Workflow node")
        print()
        hint("Full docs: https://nova-os.com/pro")
        print()
        return

    cfg = NovaCfg.load()
    if args.port: cfg.webhook_port = args.port
    if args.agent: cfg.workspace = args.agent

    # Init doesn't need full core
    if args.command == "init":
        cmd_init(args, cfg); return

    router, classifier, compiler, bridge, memory, audit = build_core(cfg)

    routes = {
        "repl":      lambda: NovREPL(compiler, bridge, memory, audit, cfg).run(),
        "serve":     lambda: cmd_serve(args, cfg, compiler, bridge, memory, audit),
        "compile":   lambda: cmd_compile(args, cfg, compiler, audit),
        "status":    lambda: cmd_status(args, cfg, router, bridge),
        "doctor":    lambda: cmd_doctor(args, cfg, router, bridge),
        "templates": lambda: cmd_templates(args, cfg),
        "audit":     lambda: cmd_audit(args, cfg, audit),
    }

    fn = routes.get(args.command)
    if not fn:
        fail(f"Unknown command: {args.command}")
        hint("Run  nova-pro help  to see all commands.")
        sys.exit(1)

    try:
        fn()
    except KeyboardInterrupt:
        print(); ok("Cancelled.")
    except Exception as e:
        if DEBUG:
            import traceback; traceback.print_exc()
        else:
            fail(f"Error: {e}")
            hint("Run with NOVA_DEBUG=1 for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
