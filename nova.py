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
# IDENTITY — ✦ nova  (the star IS the mark)
# ══════════════════════════════════════════════════════════════════

_TAGLINES = [
    "Agents that answer for themselves.",
    "The layer between intent and chaos.",
    "Your agents, accountable.",
    "What your agents do. Provably.",
    "Where intent becomes law.",
    "Intelligence with limits. Actions with proof.",
]
_tagline = random.choice(_TAGLINES)

NOVA_VERSION = "2.1.0"


def print_logo(tagline=True, compact=False):
    """The star IS the mark."""
    print()
    if compact:
        print("  " + q(C.B6, "✦", bold=True) + "  " + q(C.W, "nova", bold=True))
    else:
        print("  " + q(C.B5, "✦", bold=True) + "  " +
              q(C.W, "n", bold=True) + q(C.B7, "o", bold=True) +
              q(C.W, "v", bold=True) + q(C.B6, "a", bold=True) +
              q(C.G3, "  ·  " + NOVA_VERSION))
        if tagline:
            print()
            print("  " + q(C.G3, "     " + _tagline))
            print("  " + q(C.G4, "     " + "─" * 42))
    print()


def _step_header(n, total, title):
    progress = q(C.G4, "  [") + q(C.B6, str(n) + "/" + str(total), bold=True) + q(C.G4, "]")
    print()
    print(progress + "  " + q(C.W, title, bold=True))
    print("  " + q(C.G4, "     " + "─" * 42))
    print()


def _pause(label="continuar"):
    print("  " + q(C.G4, "     → ") + q(C.G4, "Enter para " + label + " "), end="", flush=True)
    try:
        input()
    except (EOFError, KeyboardInterrupt):
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
            return {"error": "No se puede conectar a " + self.url + " — ejecuta: docker ps"}
        except Exception as e:
            return {"error": str(e)}

    def get(self, p):           return self._req("GET",    p)
    def post(self, p, d):       return self._req("POST",   p, d)
    def delete(self, p):        return self._req("DELETE", p)
    def patch(self, p, d=None): return self._req("PATCH",  p, d or {})


# ══════════════════════════════════════════════════════════════════
# UI PRIMITIVES
# ══════════════════════════════════════════════════════════════════

def ok(msg):   print("  " + q(C.GRN, "✓") + "  " + q(C.G1, msg))
def fail(msg): print("  " + q(C.RED, "✗") + "  " + q(C.W,  msg))
def warn(msg): print("  " + q(C.YLW, "!") + "  " + q(C.G2, msg))
def info(msg): print("  " + q(C.B6,  "·") + "  " + q(C.G2, msg))
def dim(msg):  print("  " + q(C.G4,  " ") + "  " + q(C.G3, msg))


def section(title, subtle=""):
    sub = "  " + q(C.G4, subtle) if subtle else ""
    print()
    print("  " + q(C.W, title, bold=True) + sub)
    print("  " + q(C.G4, "─" * (len(title) + 2)))


def kv(key, val, vc=None):
    vc = vc or C.W
    print("  " + q(C.G3, key.ljust(20)) + "  " + q(vc, str(val)))


def loading(msg):
    print("  " + q(C.B5, "○") + "  " + q(C.G3, msg), end="", flush=True)


def clear_line():
    print("\r\033[K", end="", flush=True)


def score_bar(score, width=18):
    filled = max(0, int((score / 100) * width))
    empty  = width - filled
    c = C.GRN if score >= 70 else (C.YLW if score >= 40 else C.RED)
    bar = c + C.BOLD + ("█" * filled) + C.R + q(C.G4, "░" * empty)
    num = q(c, str(score), bold=True)
    return q(C.G3, "[") + bar + q(C.G3, "]") + " " + num


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
    bc = color or C.G4
    inner_w = max((len(l) for l in lines), default=30) + 4
    w = max(inner_w, len(title) + 6)
    if title:
        tpad = max(0, w - len(title) - 4)
        print("  " + q(bc, "┌─ ") + q(C.G2, title) + " " + q(bc, "─" * tpad + "┐"))
    else:
        print("  " + q(bc, "┌" + "─" * w + "┐"))
    for line in lines:
        pad = max(0, w - len(line) - 2)
        print("  " + q(bc, "│") + " " + q(C.G1, line) + " " * pad + " " + q(bc, "│"))
    print("  " + q(bc, "└" + "─" * w + "┘"))


def prompt(label, default=""):
    hint = " " + q(C.G4, "(" + default + ")") if default else ""
    print("  " + q(C.B6, "?") + "  " + q(C.G1, label) + hint + "  ", end="", flush=True)
    val = input().strip()
    return val or default


def prompt_list(label, hint="línea vacía para terminar"):
    print("  " + q(C.B6, "?") + "  " + q(C.G1, label) + "  " + q(C.G4, "(" + hint + ")"))
    items = []
    while True:
        print("    " + q(C.G4, "+  "), end="", flush=True)
        v = input().strip()
        if not v:
            break
        items.append(v)
    return items


def confirm(label, default=True):
    hint = q(C.G4, "Y/n" if default else "y/N")
    print("  " + q(C.B6, "?") + "  " + q(C.G1, label) + "  " + hint + "  ", end="", flush=True)
    v = input().strip().lower()
    return default if not v else v in ("y", "yes", "s", "si", "sí")


def print_error(r):
    fail(r.get("error", "Error desconocido"))


# ══════════════════════════════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════════════════════════════

def cmd_init(args):
    cfg = load_config()

    # ── SPLASH ────────────────────────────────────────────────────
    print()
    print()
    print("  " + q(C.B5, "✦", bold=True))
    print()
    print("  " + q(C.W, "Welcome to nova.", bold=True))
    print()
    print("  " + q(C.G2, "The governance layer for AI agents."))
    print()
    print("  " + q(C.G4, "     " + "─" * 42))
    print()
    print("  " + q(C.G3, "  nova sits between your agents and the real world."))
    print("  " + q(C.G3, "  Before anything executes, nova asks one question:"))
    print()
    print("  " + q(C.B6, "       Should this happen?", bold=True))
    print()
    _pause()

    # ── [1/5] HOW IT WORKS ────────────────────────────────────────
    _step_header(1, 5, "How nova works")
    print("  " + q(C.G4, "  ┌─  Your agent wants to do something"))
    print("  " + q(C.G4, "  │"))
    print("  " + q(C.G4, "  │   ") + q(C.G2, "nova evaluates the action in <5ms"))
    print("  " + q(C.G4, "  │"))
    print("  " + q(C.G4, "  ├─  ") + q(C.GRN, "Score ≥ 70", bold=True) + q(C.G3, "   →  ✓  Approved  ·  runs"))
    print("  " + q(C.G4, "  ├─  ") + q(C.YLW, "Score 40-70", bold=True) + q(C.G3, "  →  ⚠  Escalated  ·  you decide"))
    print("  " + q(C.G4, "  └─  ") + q(C.RED, "Score < 40", bold=True) + q(C.G3, "   →  ✗  Blocked   ·  logged forever"))
    print()
    print("  " + q(C.G3, "  Every decision lands in the") + " " +
          q(C.B7, "Intent Ledger", bold=True) + q(C.G3, "."))
    print("  " + q(C.G3, "  Cryptographic. Auditable. Permanent."))
    print()
    _pause()

    # ── [2/5] RISKS + T&C ─────────────────────────────────────────
    _step_header(2, 5, "Before we continue")
    print("  " + q(C.YLW, "  !") + "  " + q(C.G1, "nova is not a sandbox.", bold=True))
    print("  " + q(C.G3, "     It makes real decisions about real actions in production."))
    print()
    print("  " + q(C.G2, "  You should know:"))
    print()

    risks = [
        "nova may block actions your agents try to execute",
        "every validation is recorded permanently in the ledger",
        "you define the rules — you own the consequences",
        "misconfigured rules can block legitimate work",
        "the ledger cannot be deleted or modified",
    ]
    for r in risks:
        print("  " + q(C.G4, "     ◦  ") + q(C.G2, r))
    print()
    print("  " + q(C.G4, "     ") + q(C.G4, "Terms:  ") + q(C.B6, "https://nova-os.com/terms"))
    print()

    try:
        accepted = confirm("  I understand and accept these terms", default=False)
    except (EOFError, KeyboardInterrupt):
        print(); return
    if not accepted:
        print()
        warn("Setup cancelled. Run " + q(C.B7, "nova init") + " when ready.")
        print()
        return

    # ── [3/5] PERSONALIZATION ─────────────────────────────────────
    _step_header(3, 5, "Tell us who you are")
    print("  " + q(C.G3, "  This personalizes your nova experience."))
    print()
    try:
        name = prompt("  Your name or organization", cfg.get("user_name", ""))
        if not name:
            name = "Explorer"
    except (EOFError, KeyboardInterrupt):
        print(); name = "Explorer"

    # ── [4/5] SERVER CONFIG ───────────────────────────────────────
    _step_header(4, 5, "Connect to your nova server")
    print("  " + q(C.G3, "  nova CLI communicates with a nova server."))
    print("  " + q(C.G3, "  Self-hosted or an existing instance."))
    print()
    print("  " + q(C.G4, "  Docs: ") + q(C.B6, "https://github.com/Santiagorubioads/nova-os"))
    print()

    try:
        url = prompt("  Server URL", cfg.get("api_url", "http://localhost:8000"))
        print()
        import getpass
        print("  " + q(C.B6, "?") + "  " + q(C.G1, "API Key") + "  ", end="", flush=True)
        key = getpass.getpass("").strip() or cfg.get("api_key", "")
    except (EOFError, KeyboardInterrupt):
        print(); url = cfg.get("api_url", "http://localhost:8000"); key = cfg.get("api_key", "")

    # ── [5/5] TEST + SUCCESS ──────────────────────────────────────
    _step_header(5, 5, "Connecting")

    loading("  Reaching " + url + " ...")
    api    = NovaAPI(url, key)
    health = api.get("/health")
    clear_line()

    connected = "error" not in health
    server_ver = health.get("version", "online") if connected else "—"

    if connected:
        ok("  Server responding  ·  " + q(C.G4, server_ver))
        ok("  API key accepted")
    else:
        fail("  " + health.get("error", "Could not connect"))
        print()
        warn("  Saving config anyway. Fix the server and run " + q(C.B7, "nova status") + ".")

    cfg.update({"api_url": url, "api_key": key, "user_name": name})
    save_config(cfg)

    # ── SUCCESS SCREEN ────────────────────────────────────────────
    print()
    print("  " + q(C.G4, "     " + "─" * 42))
    print()
    print("  " + q(C.B5, "  ✦", bold=True))
    print()
    print("  " + q(C.W, "  You're in" + (", " + name.split()[0] + "." if name and name != "Explorer" else "."), bold=True))
    print()
    print("  " + q(C.G2, "  nova CLI is ready."))
    print()
    print("  " + q(C.G4, "     " + "─" * 42))
    print()

    # ── NEXT STEPS ────────────────────────────────────────────────
    print("  " + q(C.G3, "  What to do next:"))
    print()
    nexts = [
        ("nova agent create",  "Create your first agent"),
        ("nova status",        "System health & metrics"),
        ("nova config",        "Skills, preferences, settings"),
        ("nova help",          "See all commands"),
    ]
    for cmd, desc in nexts:
        print("  " + q(C.B7, "  " + cmd.ljust(22), bold=True) + "  " + q(C.G3, desc))
    print()


def cmd_status(args):
    print_logo()
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    loading("Cargando...")
    stats  = api.get("/stats")
    health = api.get("/health")
    clear_line()

    if "error" in health:
        fail("Nova no responde en " + q(C.G3, cfg["api_url"]))
        print()
        dim("Verifica: docker compose -f ~/nova-os/docker-compose.yml up -d")
        print()
        return

    section("Servidor")
    kv("URL",    cfg["api_url"], C.B6)
    kv("Estado", "Operacional",  C.GRN)

    if "error" not in stats:
        section("Actividad")
        t = stats.get("total_actions", 0)
        a = stats.get("approved", 0)
        b = stats.get("blocked", 0)
        d = stats.get("duplicates_blocked", 0)

        kv("Total acciones",       str(t))
        kv("Aprobadas",           str(a), C.GRN)
        kv("Bloqueadas",          str(b), C.RED if b > 0 else C.G3)
        kv("Duplicados evitados", str(d), C.ORG if d > 0 else C.G3)
        kv("Tasa aprobación",     str(stats.get("approval_rate", 0)) + "%")

        section("Recursos")
        alr = stats.get("alerts_pending", 0)
        kv("Agentes activos",    str(stats.get("active_agents", 0)),  C.B7)
        kv("Memorias guardadas", str(stats.get("memories_stored", 0)), C.B6)
        kv("Score promedio",     str(stats.get("avg_score", 0)))
        kv("Alertas pendientes", str(alr), C.YLW if alr > 0 else C.G3)
    print()


def cmd_agent_create(args):
    section("Nuevo agente")
    print("  " + q(C.G2, "Define las reglas de comportamiento de tu agente."))
    print()

    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    name = prompt("Nombre del agente", "Mi Agente")
    desc = prompt("Descripción breve (opcional)", "")
    auth = prompt("Autorizado por", "admin@empresa.com")
    print()

    print("  " + q(C.B7, "●", bold=True) + "  " + q(C.W, "Acciones PERMITIDAS:"))
    can  = prompt_list("Una por línea")
    print()
    print("  " + q(C.RED, "●", bold=True) + "  " + q(C.W, "Acciones PROHIBIDAS:"))
    cant = prompt_list("Una por línea")
    print()

    can_preview  = (", ".join(can[:2])  + ("..." if len(can)  > 2 else "")) if can  else "ninguna"
    cant_preview = (", ".join(cant[:2]) + ("..." if len(cant) > 2 else "")) if cant else "ninguna"
    box([
        "  Agente     " + name,
        "  Puede      " + can_preview,
        "  Prohibido  " + cant_preview,
        "  Por        " + auth,
    ], C.B4, title="Resumen")
    print()

    if not confirm("¿Crear este agente?"):
        warn("Cancelado.")
        return

    loading("Firmando Intent Token...")
    result = api.post("/tokens", {
        "agent_name": name, "description": desc,
        "can_do": can, "cannot_do": cant, "authorized_by": auth,
    })
    clear_line()

    if "error" in result:
        print_error(result)
        return

    tid = result.get("token_id", "")
    ok("Agente creado — token firmado")
    print()
    kv("Token ID", tid, C.B7)
    kv("Firma",    result.get("signature", "")[:24] + "...", C.G3)
    print()

    cfg["default_token"] = tid
    save_config(cfg)

    webhook = cfg["api_url"] + "/webhook/" + cfg["api_key"]
    section("Webhook listo para n8n")
    box([
        "  POST  " + webhook,
        "",
        '  Body:  {"action": "{{$json.texto}}", "token_id": "' + tid[:16] + '..."}',
    ], C.B5)
    print()


def cmd_agent_list(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    loading("Cargando agentes...")
    result = api.get("/tokens")
    clear_line()

    if "error" in result:
        print_error(result)
        return
    if not result:
        warn("No hay agentes activos.")
        info("Crea uno con:  nova agent create")
        return

    default_id = cfg.get("default_token", "")
    section("Agentes activos", str(len(result)) + " total")

    for t in result:
        is_def = str(t["id"]) == default_id
        badge  = "  " + q(C.B6, "default") if is_def else ""
        st     = q(C.GRN, "● activo") if t.get("active") else q(C.G4, "○ inactivo")
        print()
        print("  " + q(C.W, t["agent_name"], bold=True) + "  " + st + badge)
        kv("  ID",         str(t["id"])[:22] + "...", C.G3)
        if t.get("can_do"):
            preview = ", ".join(t["can_do"][:3]) + ("..." if len(t["can_do"]) > 3 else "")
            kv("  Puede",    preview, C.GRN)
        if t.get("cannot_do"):
            preview = ", ".join(t["cannot_do"][:3]) + ("..." if len(t["cannot_do"]) > 3 else "")
            kv("  Prohibido", preview, C.RED)
    print()


def cmd_validate(args):
    cfg    = load_config()
    api    = NovaAPI(cfg["api_url"], cfg["api_key"])
    tid    = args.token or cfg.get("default_token", "")
    action = args.action or prompt("Acción a validar")
    ctx    = args.context or ""

    if not tid:
        fail("No hay token. Pasa --token o crea un agente primero.")
        return

    print()
    loading("Validando...")
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
    kv("Razón",          reason, C.G2)
    kv("Agente",         result.get("agent_name", ""), C.W)
    kv("Ledger",         "#" + str(result.get("ledger_id", "?")), C.G3)
    kv("Memorias usadas", str(result.get("memories_used", 0)), C.B6)

    if dup:
        print()
        dup_action = dup.get("action", "")
        dup_short  = dup_action[:52] + ("…" if len(dup_action) > 52 else "")
        box([
            "  Duplicado del registro #" + str(dup.get("ledger_id")),
            "  Similitud  " + str(int(dup.get("similarity", 0) * 100)) + "%",
            "  Original   " + dup_short,
        ], C.ORG, title="Duplicado detectado")

    if resp:
        print()
        section("Respuesta generada")
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
    agent = args.agent or prompt("Agente")
    key   = args.key   or prompt("Clave", "dato_importante")
    value = args.value or prompt("Valor")
    imp   = int(getattr(args, "importance", None) or "5")

    loading("Guardando...")
    r = api.post("/memory", {
        "agent_name": agent, "key": key, "value": value,
        "importance": imp, "tags": ["manual"],
    })
    clear_line()

    if "error" in r:
        print_error(r)
        return
    ok("Memoria guardada  —  ID " + str(r.get("id")) + "  importancia " + str(imp) + "/10")
    print()


def cmd_memory_list(args):
    cfg   = load_config()
    api   = NovaAPI(cfg["api_url"], cfg["api_key"])
    agent = args.agent or prompt("Agente")

    loading("Cargando memorias...")
    result = api.get("/memory/" + urllib.parse.quote(agent))
    clear_line()

    if "error" in result:
        print_error(result)
        return
    if not result:
        warn("'" + agent + "' no tiene memorias.")
        # Fixed: no backslash inside f-string — build string first
        cmd_hint = 'nova memory save --agent "' + agent + '"'
        info("Guarda con:  " + q(C.B7, cmd_hint))
        return

    section("Memorias de " + agent, str(len(result)) + " entradas")
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

    loading("Cargando ledger...")
    result = api.get(url)
    clear_line()

    if "error" in result:
        print_error(result)
        return

    section("Ledger", str(len(result)) + " entradas")
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

    loading("Verificando cadena criptográfica...")
    r = api.get("/ledger/verify")
    clear_line()

    if "error" in r:
        print_error(r)
        return
    print()
    if r.get("verified"):
        ok("Cadena íntegra  —  " + str(r.get("total_records", 0)) + " registros verificados")
        kv("Estado", "Sin modificaciones detectadas", C.GRN)
    else:
        fail("Cadena comprometida en registro #" + str(r.get("broken_at")))
        warn("Un registro del ledger fue alterado.")
    print()


def cmd_alerts(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    loading("Cargando alertas...")
    r = api.get("/alerts")
    clear_line()

    if "error" in r:
        print_error(r)
        return

    pending = [a for a in r if not a.get("resolved")]
    if not pending:
        ok("Sin alertas pendientes.")
        print()
        return

    section("Alertas pendientes", str(len(pending)))
    for a in pending:
        s  = a.get("score", 0)
        ac = C.RED if s < 40 else C.YLW
        print()
        print("  " + q(ac, "▲") + "  " + q(C.W, a.get("message", "")[:62]))
        print("     " + q(C.G2, "Score ") + q(ac, str(s), bold=True) +
              "   " + q(C.G3, a.get("agent_name", "")) +
              "   " + q(C.G4, str(a["id"])[:12]))
    print()
    dim("Resolver:  nova alerts resolve <id>")
    print()


def cmd_seed(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    warn("Insertará agentes y acciones de demostración.")
    if not confirm("¿Continuar?"):
        return

    loading("Sembrando datos demo...")
    r = api.post("/demo/seed", {})
    clear_line()

    if "error" in r:
        print_error(r)
        return
    ok("Datos demo cargados")
    kv("Agentes",  str(r.get("tokens", 0)),   C.B7)
    kv("Acciones", str(r.get("actions", 0)))
    kv("Memorias", str(r.get("memories", 0)), C.B6)
    print()
    info("Explora con:  " + q(C.B7, "nova status"))
    print()


def cmd_config(args):
    """Interactive configuration hub — the power center of nova."""
    while True:
        cfg        = load_config()
        api_url    = cfg.get("api_url", "http://localhost:8000")
        api_key    = cfg.get("api_key", "")
        user_name  = cfg.get("user_name", "")

        # Count installed skills
        installed = [k for k in SKILLS if skill_status(k) == "installed"]
        total     = len(SKILLS)

        # Connection badge
        connected = False
        try:
            api    = NovaAPI(api_url, api_key)
            health = api.get("/health")
            connected = "error" not in health
        except Exception:
            pass

        conn_badge = q(C.GRN, "✓  connected", bold=True) if connected else q(C.YLW, "!  check server")
        key_display = ("*" * 8 + api_key[-4:]) if len(api_key) >= 4 else (q(C.G4, "not set") if not api_key else api_key)
        skill_badge = (q(C.GRN, str(len(installed)) + " active") if installed else q(C.G4, "none installed")) + q(C.G3, "  /  " + str(total) + " available")

        print_logo(compact=True)
        print("  " + q(C.G4, "     " + "─" * 42))
        print()

        # Menu entries
        menu = [
            ("1", "Server",           api_url[:38],                conn_badge),
            ("2", "API Key",          key_display,                 ""),
            ("3", "Skills  ✦",        "connect nova to the world", skill_badge),
            ("4", "Preferences",      "color · language · output", ""),
            ("5", "About nova",       "version · docs · support",  ""),
            ("6", "Reset",            "clear all settings",        ""),
        ]

        for num, title, sub, badge in menu:
            b = "  " + badge if badge else ""
            print("  " + q(C.G4, "  [") + q(C.B6, num, bold=True) + q(C.G4, "]") +
                  "  " + q(C.W, title.ljust(16), bold=True) +
                  q(C.G3, sub[:36]) + b)

        print()
        print("  " + q(C.G4, "     " + "─" * 42))
        print()
        print("  " + q(C.B6, "?") + "  " + q(C.G3, "  Select") + "  " + q(C.G4, "[1-6]  or Enter to exit:") + "  ", end="", flush=True)

        try:
            choice = input().strip()
        except (EOFError, KeyboardInterrupt):
            print(); break

        if not choice:
            break

        # ── [1] Server ─────────────────────────────────────────────
        if choice == "1":
            print()
            print("  " + q(C.W, "  Server & Connection", bold=True))
            print()
            kv("  Current URL", api_url, C.B6)
            kv("  Status",      "Connected" if connected else "Unreachable",
               C.GRN if connected else C.RED)
            print()
            try:
                new_url = prompt("  New URL (Enter to keep)", api_url)
                if new_url and new_url != api_url:
                    cfg["api_url"] = new_url
                    save_config(cfg)
                    ok("  Server URL updated.")
            except (EOFError, KeyboardInterrupt):
                pass

        # ── [2] API Key ────────────────────────────────────────────
        elif choice == "2":
            print()
            print("  " + q(C.W, "  API Key", bold=True))
            print()
            kv("  Current", key_display, C.G3)
            print()
            try:
                import getpass
                print("  " + q(C.B6, "?") + "  " + q(C.G1, "  New API Key (Enter to keep)") + "  ", end="", flush=True)
                new_key = getpass.getpass("").strip()
                if new_key:
                    cfg["api_key"] = new_key
                    save_config(cfg)
                    ok("  API Key updated.")
            except (EOFError, KeyboardInterrupt):
                pass

        # ── [3] Skills ─────────────────────────────────────────────
        elif choice == "3":
            _config_skills_hub()

        # ── [4] Preferences ────────────────────────────────────────
        elif choice == "4":
            print()
            print("  " + q(C.W, "  Preferences", bold=True))
            print()
            prefs = cfg.get("prefs", {})
            lang  = prefs.get("lang", "es")
            print("  " + q(C.G3, "  Language:  ") + q(C.W, lang))
            print("  " + q(C.G3, "  Color:     ") + q(C.W, "auto"))
            print()
            try:
                new_lang = prompt("  Language [es/en]", lang)
                if new_lang in ("es", "en"):
                    cfg.setdefault("prefs", {})["lang"] = new_lang
                    save_config(cfg)
                    ok("  Preference saved.")
            except (EOFError, KeyboardInterrupt):
                pass

        # ── [5] About ──────────────────────────────────────────────
        elif choice == "5":
            print()
            print("  " + q(C.B5, "✦", bold=True) + "  " + q(C.W, "nova", bold=True) + q(C.G3, "  ·  " + NOVA_VERSION))
            print()
            kv("  Build",   NOVA_VERSION,                     C.B6)
            kv("  Config",  CONFIG_FILE,                      C.G3)
            kv("  Skills",  str(len(installed)) + " installed", C.G3)
            kv("  Docs",    "https://github.com/Santiagorubioads/nova-os", C.B6)
            kv("  Support", "https://nova-os.com/support",    C.B6)
            print()
            try:
                input("  " + q(C.G4, "  Enter to go back  "))
            except (EOFError, KeyboardInterrupt):
                pass

        # ── [6] Reset ──────────────────────────────────────────────
        elif choice == "6":
            print()
            warn("  This will erase all local nova config and skills.")
            try:
                if confirm("  Continue?", default=False):
                    import shutil
                    shutil.rmtree(NOVA_DIR, ignore_errors=True)
                    ok("  nova reset. Run " + q(C.B7, "nova init") + " to start fresh.")
                    print()
                    break
            except (EOFError, KeyboardInterrupt):
                pass

        print()


def _config_skills_hub():
    """Skills section within nova config."""
    while True:
        installed = [k for k in SKILLS if skill_status(k) == "installed"]
        available = [k for k in SKILLS if skill_status(k) != "installed"]

        print()
        print("  " + q(C.B5, "✦", bold=True) + "  " + q(C.W, "Skills — The Constellation", bold=True))
        print("  " + q(C.G4, "     " + "─" * 42))
        print()
        print("  " + q(C.G3, "  Skills give nova access to real data before deciding."))
        print("  " + q(C.G3, "  Install what you need. Nothing else runs."))
        print()

        if installed:
            print("  " + q(C.GRN, "  ● Installed  ", bold=True) + q(C.G4, str(len(installed)) + " active"))
            print()
            for k in installed:
                s  = SKILLS[k]
                sc = _skill_color(s)
                print("  " + q(C.GRN, "  ✓") + "  " + q(sc, s["icon"] + "  " + s["name"].ljust(16), bold=True) +
                      q(C.G3, s["desc"][:40]))
            print()

        if available:
            print("  " + q(C.G3, "  ○ Available  ") + q(C.G4, str(len(available)) + " skills"))
            print()
            for k in available:
                s  = SKILLS[k]
                sc = _skill_color(s)
                print("  " + q(C.G4, "     ") + q(sc, s["icon"] + "  " + s["name"].ljust(16)) +
                      q(C.G4, s["desc"][:40]))
            print()

        print("  " + q(C.G4, "     " + "─" * 42))
        print()
        print("  " + q(C.B6, "?") + "  " + q(C.G3, "  Skill name to configure  ") +
              q(C.G4, "(Enter to go back):") + "  ", end="", flush=True)

        try:
            choice = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(); break

        if not choice:
            break

        if choice in SKILLS:
            fake_args = type("A", (), {"third": choice, "subcommand": "add", "agent": "", "reconfigure": False})()
            cmd_skill_add(fake_args)
        else:
            # Try partial match
            matches = [k for k in SKILLS if k.startswith(choice) or choice in SKILLS[k]["name"].lower()]
            if len(matches) == 1:
                fake_args = type("A", (), {"third": matches[0], "subcommand": "add", "agent": "", "reconfigure": False})()
                cmd_skill_add(fake_args)
            elif matches:
                print()
                info("  Did you mean: " + ", ".join(matches))
            else:
                warn("  Skill '" + choice + "' not found. Available: " + ", ".join(SKILLS.keys()))


def cmd_help(args=None):
    print_logo()

    print("  " + q(C.G3, "  Governance infrastructure for AI agents."))
    print()
    print("  " + q(C.G4, "     " + "─" * 42))
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
        print("  " + q(C.G3, "  " + title.upper()))
        print()
        for cmd, desc in cmds:
            print("  " + q(C.B7, "  " + cmd.ljust(26), bold=True) + "  " + q(C.G3, desc))
        print()

    print("  " + q(C.G4, "     " + "─" * 42))
    print()
    print("  " + q(C.G4, "  Examples:"))
    print()
    examples = [
        ('nova validate --action "Send email to john@x.com"', ""),
        ("nova ledger --limit 20 --verdict BLOCKED",          ""),
        ("nova config",                                        "→ then select [3] for Skills"),
    ]
    for ex, note in examples:
        line = "  " + q(C.G4, "  $ ") + q(C.W, ex)
        if note:
            line += "  " + q(C.G4, note)
        print(line)
    print()


# ══════════════════════════════════════════════════════════════════
# SKILLS CATALOG — Nova · Constellation
# ══════════════════════════════════════════════════════════════════

SKILLS = {
    # ── Comunicación ───────────────────────────────────────────────
    "gmail": {
        "name": "Gmail",
        "category": "Comunicación",
        "icon": "✉",
        "color": "RED",
        "desc": "Verifica emails enviados, detecta duplicados, lee bandeja",
        "what": "nova consulta tu Gmail antes de aprobar cualquier envío",
        "fields": [
            ("service_account_json", "Ruta al JSON de Service Account", False),
            ("delegated_email",      "Email de tu cuenta Google",        False),
        ],
        "docs": "https://console.cloud.google.com/iam-admin/serviceaccounts",
        "mcp":  "gmail-mcp",
    },
    "sheets": {
        "name": "Google Sheets",
        "category": "Datos",
        "icon": "⊞",
        "color": "GRN",
        "desc": "Lee y escribe en tus hojas de cálculo en tiempo real",
        "what": "nova verifica registros en tu Sheet antes de ejecutar acciones",
        "fields": [
            ("service_account_json", "Ruta al JSON de Service Account", False),
            ("spreadsheet_id",       "ID del Spreadsheet principal",     False),
        ],
        "docs": "https://console.cloud.google.com/iam-admin/serviceaccounts",
        "mcp":  "google-sheets-mcp",
    },
    "slack": {
        "name": "Slack",
        "category": "Comunicación",
        "icon": "◈",
        "color": "YLW",
        "desc": "Envía alertas, lee canales, valida mensajes enviados",
        "what": "nova puede notificar en Slack cuando bloquea o escala una acción",
        "fields": [
            ("bot_token",   "Bot Token (xoxb-...)",       False),
            ("channel",     "Canal default (#general)",   False),
        ],
        "docs": "https://api.slack.com/apps",
        "mcp":  "slack-mcp-server",
    },
    "whatsapp": {
        "name": "WhatsApp",
        "category": "Comunicación",
        "icon": "◉",
        "color": "GRN",
        "desc": "Verifica mensajes enviados, evita spam, gestiona contactos",
        "what": "nova consulta el historial de WhatsApp antes de aprobar mensajes",
        "fields": [
            ("evolution_api_url", "URL de Evolution API",   False),
            ("evolution_api_key", "API Key de Evolution",   True),
            ("instance_name",     "Nombre de la instancia", False),
        ],
        "docs": "https://doc.evolution-api.com",
        "mcp":  "whatsapp-mcp",
    },
    "telegram": {
        "name": "Telegram",
        "category": "Comunicación",
        "icon": "◎",
        "color": "B6",
        "desc": "Lee y envía mensajes, gestiona bots, verifica canales",
        "what": "nova puede recibir comandos y enviar alertas por Telegram",
        "fields": [
            ("bot_token",  "Bot Token de @BotFather", True),
            ("chat_id",    "Chat ID principal",       False),
        ],
        "docs": "https://core.telegram.org/bots",
        "mcp":  "telegram-mcp",
    },
    # ── Productividad ──────────────────────────────────────────────
    "notion": {
        "name": "Notion",
        "category": "Productividad",
        "icon": "◻",
        "color": "W",
        "desc": "Lee bases de datos, crea páginas, actualiza registros",
        "what": "nova puede consultar y actualizar tu Notion como fuente de verdad",
        "fields": [
            ("api_key",     "Integration Token (secret_...)", True),
            ("database_id", "ID de base de datos principal",  False),
        ],
        "docs": "https://www.notion.so/my-integrations",
        "mcp":  "notion-mcp",
    },
    "airtable": {
        "name": "Airtable",
        "category": "Datos",
        "icon": "◈",
        "color": "ORG",
        "desc": "CRM, base de leads, inventario — consulta antes de actuar",
        "what": "nova verifica registros en Airtable antes de ejecutar",
        "fields": [
            ("api_key",  "Personal Access Token", True),
            ("base_id",  "Base ID (app...)",       False),
        ],
        "docs": "https://airtable.com/create/tokens",
        "mcp":  "airtable-mcp",
    },
    "github": {
        "name": "GitHub",
        "category": "Desarrollo",
        "icon": "◯",
        "color": "W",
        "desc": "Crea issues, revisa PRs, verifica código antes de deploy",
        "what": "nova puede bloquear deploys si hay issues críticos abiertos",
        "fields": [
            ("token",  "Personal Access Token (ghp_...)", True),
            ("repo",   "Repo default (owner/repo)",       False),
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
        "desc": "Verifica cobros, detecta fraude, aprueba transacciones",
        "what": "nova valida pagos y bloquea transacciones sospechosas",
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
        "desc": "Consulta contactos, deals, historial de comunicación",
        "what": "nova verifica si un lead ya fue contactado antes de aprobar",
        "fields": [
            ("api_key", "Private App Token", True),
        ],
        "docs": "https://developers.hubspot.com/docs/api/private-apps",
        "mcp":  "hubspot-mcp",
    },
    # ── Infraestructura ────────────────────────────────────────────
    "supabase": {
        "name": "Supabase",
        "category": "Base de datos",
        "icon": "◈",
        "color": "GRN",
        "desc": "Consulta tu base de datos Postgres en tiempo real",
        "what": "nova puede verificar cualquier tabla antes de ejecutar acciones",
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
        "desc": "Conexión directa a tu base de datos PostgreSQL",
        "what": "nova consulta tu DB antes de cada validación crítica",
        "fields": [
            ("connection_string", "postgresql://user:pass@host:5432/db", True),
        ],
        "docs": "https://www.postgresql.org/docs/current/libpq-connect.html",
        "mcp":  "postgres-mcp",
    },
}

SKILL_CATEGORIES = ["Comunicación", "Datos", "Productividad", "Desarrollo", "CRM", "Pagos", "Base de datos"]

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
    print("  " + q(C.W, "Skills disponibles", bold=True) + "  " + q(C.G4, "· conecta nova con el mundo"))
    print("  " + q(C.G4, "─" * 54))
    print()

    # Star intro — nova branding
    print("  " + q(C.B5, "✦") + "  " + q(C.G2, "nova es una estrella nueva. los skills son su constelación."))
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
    print("  " + q(C.B7, "nova skill add <nombre>", bold=True) + q(C.G3, "   instalar un skill"))
    print("  " + q(C.B5, "nova skill info <nombre>") + q(C.G3, "   ver detalles"))
    print("  " + q(C.B5, "nova skill remove <nombre>") + q(C.G3, " desinstalar"))
    print()


# ── nova skill info ──────────────────────────────────────────────
def cmd_skill_info(args):
    name = getattr(args, "third", "") or args.subcommand or args.agent or ""
    if name in ("info", "add", "list", "remove", ""):
        name = getattr(args, "third", "") or args.agent or ""
        fail("Skill no encontrado: " + (name or "?"))
        print()
        info("Skills disponibles: " + ", ".join(SKILLS.keys()))
        return

    s  = SKILLS[name]
    sc = _skill_color(s)
    st = skill_status(name)
    data = load_skill(name)

    print()
    print("  " + q(sc, s["icon"] + "  " + s["name"], bold=True) +
          "  " + q(C.G4, s["category"]))
    print()
    kv("Descripción",  s["desc"])
    kv("Lo que hace",  s["what"], C.G2)
    kv("MCP",          s["mcp"], C.G3)
    kv("Docs",         s["docs"], C.B6)
    kv("Estado",       ("✓ instalado" if st == "installed" else "no instalado"),
       C.GRN if st == "installed" else C.G4)

    if data and data.get("installed_at"):
        kv("Instalado",    data["installed_at"][:10], C.G3)

    section("Campos requeridos")
    for field, label, secret in s["fields"]:
        val = ""
        if data and data.get(field):
            v = data[field]
            val = q(C.GRN, ("*" * 8) if secret else v[:32])
        else:
            val = q(C.G4, "no configurado")
        kv("  " + field, val if val else label)

    print()
    if st != "installed":
        info("Instalar:  " + q(C.B7, "nova skill add " + name))
    else:
        info("Reconfigurar:  " + q(C.B7, "nova skill add " + name + " --reconfigure"))
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
        print("  " + q(C.W, "¿Qué skill quieres agregar?", bold=True))
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
            choice = input(q(C.B6, "Número o nombre: ")).strip()
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
        fail("Skill '" + name + "' no existe.")
        info("Skills disponibles: " + ", ".join(SKILLS.keys()))
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
        ok("Ya instalado.")
        info("Para reconfigurar:  " + q(C.B7, "nova skill add " + name + " --reconfigure"))
        print()
        return

    # ── STEP 1: docs
    print("  " + q(C.B6, "✦") + "  " + q(C.W, "Paso 1 de 2 — Obtén tus credenciales", bold=True))
    print()
    print("  " + q(C.G2, "Necesitas configurar el acceso en:"))
    print("  " + q(C.B7, "  " + s["docs"]))
    print()
    if not confirm("¿Ya tienes las credenciales listas?", default=False):
        print()
        info("Cuando las tengas, vuelve con:  " + q(C.B7, "nova skill add " + name))
        print()
        return

    # ── STEP 2: fields
    print()
    print("  " + q(C.B6, "✦") + "  " + q(C.W, "Paso 2 de 2 — Configura el skill", bold=True))
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
    loading("Verificando skill...")
    time.sleep(0.6)
    clear_line()

    # Basic validation — check required fields are filled
    missing = [f for f, _, _ in s["fields"] if not data.get(f)]
    if missing:
        warn("Faltan campos: " + ", ".join(missing))
        warn("Guardado como incompleto. Reconfigura con:  nova skill add " + name)
        data["status"] = "incomplete"
    else:
        ok(s["name"] + " skill configurado")
        data["status"] = "installed"

    data["installed_at"] = datetime.now().isoformat()
    data["version"] = "1.0.0"
    save_skill(name, data)

    # ── SUMMARY
    print()
    box([
        "  " + s["icon"] + "  " + s["name"] + " conectado a nova",
        "",
        "  " + s["what"],
    ], sc, title=s["category"])
    print()
    info("Ver detalles:  " + q(C.B7, "nova skill info " + name))
    print()


# ── nova skill remove ────────────────────────────────────────────
def cmd_skill_remove(args):
    name = (args.subcommand or args.agent or "").lower()
    if name in ("remove", ""):
        name = args.agent or ""

    if not name or name not in SKILLS:
        fail("Especifica un skill válido.")
        return

    if skill_status(name) != "installed":
        warn(name + " no está instalado.")
        return

    warn("Esto eliminará las credenciales de " + SKILLS[name]["name"] + " de este equipo.")
    if not confirm("¿Continuar?", default=False):
        return

    path = os.path.join(SKILLS_DIR, name + ".json")
    if os.path.exists(path):
        os.remove(path)
    ok(SKILLS[name]["name"] + " desinstalado.")
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
        fail("Comando desconocido: " + args.command)
        print()
        info("Usa  " + q(C.B7, "nova help") + "  para ver todos los comandos.")
        print()
        sys.exit(1)

    try:
        fn(args)
    except KeyboardInterrupt:
        print()
        warn("Cancelado.")
        print()


if __name__ == "__main__":
    main()
