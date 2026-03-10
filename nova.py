#!/usr/bin/env python3
"""
Nova CLI — Agents that answer for themselves.
Zero dependencies. Python 3.8+.
"""

import sys, os, json, time, urllib.request, urllib.error
import urllib.parse, hashlib, argparse, textwrap, random
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
# COLOR SYSTEM
# ══════════════════════════════════════════════════════════════════

USE_COLOR = (
    not os.environ.get("NO_COLOR") and
    (os.environ.get("FORCE_COLOR") or (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()))
)

def _e(code): return f"\033[{code}m" if USE_COLOR else ""

class C:
    # Reset
    R    = _e("0")
    BOLD = _e("1")
    DIM  = _e("2")
    ITAL = _e("3")

    # Blues — dark to electric (the soul of Nova)
    B0   = _e("38;5;17")    # Midnight
    B1   = _e("38;5;18")
    B2   = _e("38;5;19")
    B3   = _e("38;5;20")
    B4   = _e("38;5;21")    # Pure blue
    B5   = _e("38;5;27")
    B6   = _e("38;5;33")
    B7   = _e("38;5;39")    # Electric blue
    B8   = _e("38;5;45")    # Cyan-electric

    # Neutrals — all close to black
    W    = _e("38;5;255")   # Almost white
    G1   = _e("38;5;250")   # Light gray
    G2   = _e("38;5;244")   # Mid gray
    G3   = _e("38;5;238")   # Dark gray
    G4   = _e("38;5;234")   # Very dark
    G5   = _e("38;5;232")   # Near black

    # Semantic
    GRN  = _e("38;5;84")    # Success green
    YLW  = _e("38;5;220")   # Warning yellow
    RED  = _e("38;5;196")   # Error red
    ORG  = _e("38;5;208")   # Orange (duplicate)

def q(color, text, bold=False):
    b = C.BOLD if bold else ""
    return f"{b}{color}{text}{C.R}"


# ══════════════════════════════════════════════════════════════════
# THE LOGO — Premium ASCII, azul noche → eléctrico
# ══════════════════════════════════════════════════════════════════

LOGO_LINES = [
    "  ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗  ",
    "  ████╗  ██║██╔═══██╗██║   ██║██╔══██╗ ",
    "  ██╔██╗ ██║██║   ██║██║   ██║███████║ ",
    "  ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║ ",
    "  ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║ ",
    "  ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝ ",
]

LOGO_COLORS = [C.B1, C.B2, C.B3, C.B5, C.B6, C.B7]

# Smart taglines — one is picked per session
TAGLINES = [
    "Agents that answer for themselves.",
    "The layer between intent and chaos.",
    "Your agents, accountable.",
    "What your agents do. Provably.",
    "Intelligence with memory. Actions with limits.",
    "Where intent becomes law.",
]

_tagline = random.choice(TAGLINES)

def print_logo(tagline: bool = True):
    print()
    for i, line in enumerate(LOGO_LINES):
        print(f"{LOGO_COLORS[i]}{C.BOLD}{line}{C.R}")

    if tagline:
        print()
        # The identity bar
        W = 44
        left  = q(C.G2, "Nova CLI")
        sep   = q(C.G4, "  ·  ")
        right = q(C.G3, _tagline)
        pad   = q(C.G4, "─" * W)
        print(f"  {left}{sep}{right}")
        print(f"  {pad}")
    print()


# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════

NOVA_DIR    = os.path.expanduser("~/.nova")
CONFIG_FILE = os.path.join(NOVA_DIR, "config.json")

DEFAULTS = {
    "api_url": "http://localhost:8000",
    "api_key": "",
    "default_token": "",
    "version": "2.0.0"
}

def load_config() -> dict:
    os.makedirs(NOVA_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            return {**DEFAULTS, **json.load(open(CONFIG_FILE))}
        except Exception:
            pass
    return DEFAULTS.copy()

def save_config(cfg: dict):
    os.makedirs(NOVA_DIR, exist_ok=True)
    json.dump(cfg, open(CONFIG_FILE, "w"), indent=2)


# ══════════════════════════════════════════════════════════════════
# API CLIENT
# ══════════════════════════════════════════════════════════════════

class NovaAPI:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key

    def _req(self, method, path, data=None):
        url  = f"{self.url}{path}"
        hdrs = {"Content-Type": "application/json", "x-api-key": self.key}
        body = json.dumps(data).encode() if data else None
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:    return {"error": json.loads(e.read().decode()).get("detail", str(e))}
            except: return {"error": f"HTTP {e.code}"}
        except urllib.error.URLError:
            return {"error": f"No se puede conectar a {self.url}\n    ¿Está Nova corriendo? → docker ps"}
        except Exception as e:
            return {"error": str(e)}

    def get(self, p):        return self._req("GET",    p)
    def post(self, p, d):    return self._req("POST",   p, d)
    def delete(self, p):     return self._req("DELETE", p)
    def patch(self, p, d=None): return self._req("PATCH", p, d or {})


# ══════════════════════════════════════════════════════════════════
# UI PRIMITIVES
# ══════════════════════════════════════════════════════════════════

def ok(msg):    print(f"  {q(C.GRN, '✓')}  {q(C.G1, msg)}")
def fail(msg):  print(f"  {q(C.RED, '✗')}  {q(C.W, msg)}")
def warn(msg):  print(f"  {q(C.YLW, '!')}  {q(C.G2, msg)}")
def info(msg):  print(f"  {q(C.B6,  '·')}  {q(C.G2, msg)}")
def dim(msg):   print(f"  {q(C.G4,  ' ')}  {q(C.G3, msg)}")

def section(title: str, subtle: str = ""):
    sub = f"  {q(C.G4, subtle)}" if subtle else ""
    print()
    print(f"  {q(C.W, title, bold=True)}{sub}")
    print(f"  {q(C.G4, '─' * (len(title) + 2))}")

def kv(key: str, val: str, vc=None):
    vc = vc or C.W
    print(f"  {q(C.G3, key.ljust(20))}  {q(vc, str(val))}")

def loading(msg: str):
    """Inline spinner — call before API, then clear_line()"""
    print(f"  {q(C.B5, '○')}  {q(C.G3, msg)}", end="", flush=True)

def clear_line():
    print("\r\033[K", end="", flush=True)

def score_bar(score: int, width: int = 18) -> str:
    filled = max(0, int((score / 100) * width))
    empty  = width - filled
    c = C.GRN if score >= 70 else (C.YLW if score >= 40 else C.RED)
    bar = f"{c}{C.BOLD}{'█' * filled}{C.R}{q(C.G4, '░' * empty)}"
    num = q(c, str(score), bold=True)
    return f"{q(C.G3, '[')}{bar}{q(C.G3, ']')} {num}"

def verdict_badge(v: str) -> str:
    m = {
        "APPROVED":  (C.GRN, "✓", "APPROVED"),
        "BLOCKED":   (C.RED, "✗", "BLOCKED"),
        "ESCALATED": (C.YLW, "⚠", "ESCALATED"),
        "DUPLICATE": (C.ORG, "⊘", "DUPLICATE"),
    }
    c, sym, label = m.get(v, (C.G2, "·", v))
    return f"{q(c, sym)}  {q(c, label, bold=True)}"

def box(lines: list, color=None, title: str = ""):
    bc = color or C.G4
    inner_w = max((len(l) for l in lines), default=30) + 4
    w = max(inner_w, len(title) + 6)

    if title:
        tpad = w - len(title) - 4
        print(f"  {q(bc, '┌─')} {q(C.G2, title)} {q(bc, '─' * max(0,tpad) + '┐')}")
    else:
        print(f"  {q(bc, '┌' + '─' * w + '┐')}")

    for line in lines:
        pad = w - len(line) - 2
        print(f"  {q(bc, '│')} {q(C.G1, line)}{' ' * max(0,pad)} {q(bc, '│')}")
    print(f"  {q(bc, '└' + '─' * w + '┘')}")

def prompt(label: str, default: str = "", secret: bool = False) -> str:
    hint = f" {q(C.G4, f'({default})')}" if default else ""
    print(f"  {q(C.B6, '?')}  {q(C.G1, label)}{hint}  ", end="", flush=True)
    import getpass
    val = getpass.getpass("") if secret else input().strip()
    return val or default

def prompt_list(label: str, hint: str = "línea vacía para terminar") -> list:
    print(f"  {q(C.B6, '?')}  {q(C.G1, label)}  {q(C.G4, f'({hint})')}")
    items = []
    while True:
        print(f"    {q(C.G4, '+  ')}", end="", flush=True)
        v = input().strip()
        if not v: break
        items.append(v)
    return items

def confirm(label: str, default: bool = True) -> bool:
    hint = q(C.G4, "Y/n" if default else "y/N")
    print(f"  {q(C.B6, '?')}  {q(C.G1, label)}  {hint}  ", end="", flush=True)
    v = input().strip().lower()
    return default if not v else v in ("y", "yes", "s", "si", "sí")

def print_error(r: dict):
    fail(r.get("error", "Error desconocido"))


# ══════════════════════════════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════════════════════════════

def cmd_init(args):
    print_logo()
    print(f"  {q(C.W, 'Conecta Nova CLI con tu servidor.', bold=True)}")
    print(f"  {q(C.G3, 'Tarda 30 segundos.')}")
    print()

    cfg = load_config()
    url = prompt("URL del servidor", cfg.get("api_url", "http://localhost:8000"))
    key = prompt("API Key", cfg.get("api_key", ""), secret=False)

    print()
    loading("Verificando conexión...")
    api    = NovaAPI(url, key)
    health = api.get("/health")
    clear_line()

    if "error" in health:
        fail(health["error"])
        warn("Guardando config de todas formas.")
    else:
        ok("Conectado")

    cfg.update({"api_url": url, "api_key": key})
    save_config(cfg)
    print()
    ok(f"Config guardada → {q(C.G3, CONFIG_FILE)}")
    print()
    info(f"Siguiente:  {q(C.B7, 'nova agent create')}")
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
        fail(f"Nova no responde en {q(C.G3, cfg['api_url'])}")
        print()
        dim("Verifica que el servidor esté corriendo:")
        print(f"    {q(C.B6, 'docker compose -f ~/nova-os/docker-compose.yml up -d')}")
        print()
        return

    section("Servidor")
    kv("URL",       cfg["api_url"], C.B6)
    kv("Estado",    "Operacional",  C.GRN)

    if "error" not in stats:
        section("Actividad")
        t = stats.get("total_actions", 0)
        a = stats.get("approved", 0)
        b = stats.get("blocked", 0)
        d = stats.get("duplicates_blocked", 0)
        r = stats.get("approval_rate", 0)

        kv("Total acciones",      str(t))
        kv("Aprobadas",          str(a), C.GRN)
        kv("Bloqueadas",         str(b), C.RED if b > 0 else C.G3)
        kv("Duplicados evitados",str(d), C.ORG if d > 0 else C.G3)
        kv("Tasa de aprobación", f"{r}%")

        section("Recursos")
        alr = stats.get("alerts_pending", 0)
        kv("Agentes activos",    str(stats.get("active_agents", 0)), C.B7)
        kv("Memorias guardadas", str(stats.get("memories_stored", 0)), C.B6)
        kv("Score promedio",     str(stats.get("avg_score", 0)))
        kv("Alertas pendientes", str(alr), C.YLW if alr > 0 else C.G3)
    print()


def cmd_agent_create(args):
    section("Nuevo agente")
    print(f"  {q(C.G2, 'Define las reglas de comportamiento de tu agente.')}")
    print()

    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    name    = prompt("Nombre del agente", "Mi Agente")
    desc    = prompt("Descripción breve (opcional)", "")
    auth    = prompt("Autorizado por", "admin@empresa.com")
    print()

    print(f"  {q(C.B7, '●', bold=True)}  {q(C.W, 'Acciones PERMITIDAS:')}")
    can = prompt_list("Una por línea")
    print()
    print(f"  {q(C.RED, '●', bold=True)}  {q(C.W, 'Acciones PROHIBIDAS:')}")
    cant = prompt_list("Una por línea")
    print()

    box([
        f"  Agente     {name}",
        f"  Puede      {', '.join(can[:2])}{'...' if len(can)>2 else ''}",
        f"  Prohibido  {', '.join(cant[:2])}{'...' if len(cant)>2 else ''}",
        f"  Por        {auth}",
    ], C.B4, title="Resumen")
    print()

    if not confirm("¿Crear este agente?"):
        warn("Cancelado.")
        return

    loading("Firmando Intent Token...")
    result = api.post("/tokens", {
        "agent_name": name, "description": desc,
        "can_do": can, "cannot_do": cant, "authorized_by": auth
    })
    clear_line()

    if "error" in result:
        print_error(result)
        return

    tid = result.get("token_id", "")
    ok(f"Agente creado — token firmado con Ed25519")
    print()
    kv("Token ID", tid, C.B7)
    kv("Firma",    result.get("signature","")[:24] + "...", C.G3)
    print()

    cfg["default_token"] = tid
    save_config(cfg)

    section("Webhook listo para n8n")
    webhook = f"{cfg['api_url']}/webhook/{cfg['api_key']}"
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
        info(f"Crea uno con:  {q(C.B7,'nova agent create')}")
        return

    section(f"Agentes activos", f"{len(result)} total")
    default_id = load_config().get("default_token", "")

    for t in result:
        is_default = str(t["id"]) == default_id
        badge = f"  {q(C.B6,'default')}" if is_default else ""
        st = q(C.GRN, "● activo") if t.get("active") else q(C.G4, "○ inactivo")
        print()
        print(f"  {q(C.W, t['agent_name'], bold=True)}  {st}{badge}")
        kv("  ID",        str(t["id"])[:20] + "...", C.G3)
        if t.get("can_do"):
            kv("  Puede",    ", ".join(t["can_do"][:3]) + ("..." if len(t["can_do"])>3 else ""), C.GRN)
        if t.get("cannot_do"):
            kv("  Prohibido",", ".join(t["cannot_do"][:3]) + ("..." if len(t["cannot_do"])>3 else ""), C.RED)
    print()


def cmd_validate(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

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
        "token_id": tid, "action": action,
        "context": ctx, "generate_response": True, "check_duplicates": True
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
    print(f"  {verdict_badge(verdict)}   {score_bar(score)}   {q(C.G4, f'{ms}ms')}")
    print()
    kv("Razón",         reason, C.G2)
    kv("Agente",        result.get("agent_name",""), C.W)
    kv("Ledger",        f"#{result.get('ledger_id','?')}", C.G3)
    kv("Memorias usadas", str(result.get("memories_used", 0)), C.B6)

    if dup:
        print()
        box([
            f"  Duplicado del registro #{dup.get('ledger_id')}",
            f"  Similitud  {int(dup.get('similarity',0)*100)}%",
            f"  Original   {dup.get('action','')[:52]}{'…' if len(dup.get('action',''))>52 else ''}",
        ], C.ORG, title="Duplicado detectado")

    if resp:
        print()
        section("Respuesta generada")
        print()
        for line in textwrap.wrap(resp, width=64):
            print(f"  {q(C.G1, line)}")

    print()
    print(f"  {q(C.G5, 'hash  ' + result.get('hash','')[:20] + '...')}")
    print()


def cmd_memory_save(args):
    cfg    = load_config()
    api    = NovaAPI(cfg["api_url"], cfg["api_key"])
    agent  = args.agent or prompt("Agente")
    key    = args.key   or prompt("Clave", "dato_importante")
    value  = args.value or prompt("Valor")
    imp    = int(getattr(args, "importance", None) or "5")

    loading("Guardando...")
    r = api.post("/memory", {"agent_name": agent, "key": key, "value": value, "importance": imp, "tags": ["manual"]})
    clear_line()

    if "error" in r: print_error(r); return
    ok(f"Memoria guardada  —  ID {r.get('id')}  importancia {imp}/10")
    print()


def cmd_memory_list(args):
    cfg   = load_config()
    api   = NovaAPI(cfg["api_url"], cfg["api_key"])
    agent = args.agent or prompt("Agente")

    loading("Cargando memorias...")
    result = api.get(f"/memory/{urllib.parse.quote(agent)}")
    clear_line()

    if "error" in result: print_error(result); return
    if not result:
        warn(f"'{agent}' no tiene memorias.")
        info(f"Guarda con:  {q(C.B7,'nova memory save --agent \"'+agent+'\"')}")
        return

    section(f"Memorias de {agent}", f"{len(result)} entradas")
    for m in result:
        imp = m.get("importance", 5)
        bar = q(C.B6, "█" * imp) + q(C.G4, "░" * (10 - imp))
        src = q(C.G4, m.get("source","manual"))
        print()
        print(f"  {q(C.W, m['key'], bold=True)}  {bar}  {src}")
        for line in textwrap.wrap(m["value"], width=62):
            print(f"    {q(C.G2, line)}")
    print()


def cmd_ledger(args):
    cfg     = load_config()
    api     = NovaAPI(cfg["api_url"], cfg["api_key"])
    limit   = getattr(args, "limit", 10) or 10
    verdict = getattr(args, "verdict", "") or ""
    url     = f"/ledger?limit={limit}" + (f"&verdict={verdict.upper()}" if verdict else "")

    loading("Cargando ledger...")
    result = api.get(url)
    clear_line()

    if "error" in result: print_error(result); return

    section("Ledger", f"{len(result)} entradas")
    for e in result:
        v  = e.get("verdict","?")
        s  = e.get("score", 0)
        vc = {
            "APPROVED": C.GRN, "BLOCKED": C.RED,
            "ESCALATED": C.YLW, "DUPLICATE": C.ORG
        }.get(v, C.G3)
        act = e.get("action","")
        ts  = (e.get("executed_at") or "")[:16]
        print()
        print(f"  {q(vc, '■')}  {q(C.W, act[:56])}{'…' if len(act)>56 else ''}")
        print(f"     {q(vc, v.ljust(10))}  score {score_bar(s, 10)}  {q(C.G4, ts)}  {q(C.G4, e.get('agent_name','')[:22])}")
    print()


def cmd_verify(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])

    loading("Verificando cadena criptográfica...")
    r = api.get("/ledger/verify")
    clear_line()

    if "error" in r: print_error(r); return
    print()
    if r.get("verified"):
        ok(f"Cadena íntegra  —  {r.get('total_records',0)} registros verificados")
        kv("Estado", "Sin modificaciones detectadas", C.GRN)
    else:
        fail(f"Cadena comprometida en registro #{r.get('broken_at')}")
        warn("Un registro del ledger fue alterado.")
    print()


def cmd_alerts(args):
    cfg = load_config()
    api = NovaAPI(cfg["api_url"], cfg["api_key"])
    loading("Cargando alertas...")
    r = api.get("/alerts")
    clear_line()

    if "error" in r: print_error(r); return
    pending = [a for a in r if not a.get("resolved")]

    if not pending:
        ok("Sin alertas pendientes.")
        print()
        return

    section("Alertas pendientes", str(len(pending)))
    for a in pending:
        s = a.get("score", 0)
        c = C.RED if s < 40 else C.YLW
        print()
        print(f"  {q(c,'▲')}  {q(C.W, a.get('message','')[:62])}")
        print(f"     {q(C.G2,'Score')} {q(c, str(s), bold=True)}   {q(C.G3, a.get('agent_name',''))}   {q(C.G4, str(a['id'])[:12])}")

    print()
    dim(f"Resolver:  nova alerts resolve <id>")
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

    if "error" in r: print_error(r); return
    ok("Datos demo cargados")
    kv("Agentes",   str(r.get("tokens", 0)), C.B7)
    kv("Acciones",  str(r.get("actions", 0)))
    kv("Memorias",  str(r.get("memories", 0)), C.B6)
    print()
    info(f"Explora con:  {q(C.B7,'nova status')}")
    print()


def cmd_config(args):
    cfg = load_config()
    section("Configuración")
    kv("Servidor",      cfg.get("api_url",""),   C.B6)
    kv("API Key",       (cfg.get("api_key","")[:12] + "..." if cfg.get("api_key") else q(C.G4, "no configurada")))
    kv("Token default", (cfg.get("default_token","")[:16] + "..." if cfg.get("default_token") else q(C.G4, "ninguno")))
    kv("Config",        CONFIG_FILE, C.G3)
    print()


def cmd_help(args=None):
    print_logo()

    cmds = [
        ("init",           "Conecta Nova CLI con tu servidor"),
        ("status",         "Estado del sistema y métricas en tiempo real"),
        ("agent create",   "Crea un agente con sus reglas de comportamiento"),
        ("agent list",     "Lista todos los agentes activos"),
        ("validate",       "Valida una acción — veredicto + respuesta generada"),
        ("memory save",    "Guarda un dato en la memoria de un agente"),
        ("memory list",    "Muestra las memorias de un agente"),
        ("ledger",         "Historial criptográfico de acciones"),
        ("ledger verify",  "Verifica la integridad de la cadena"),
        ("alerts",         "Alertas de acciones bloqueadas/escaladas"),
        ("seed",           "Carga datos demo para explorar"),
        ("config",         "Configuración actual"),
    ]

    section("Comandos")
    for cmd, desc in cmds:
        print(f"  {q(C.B7, ('nova ' + cmd).ljust(22), bold=True)}  {q(C.G2, desc)}")

    section("Flags")
    for flag, desc in [
        ("--token  <id>",    "Token ID a usar para validate"),
        ("--action <texto>", "Acción a validar (sin prompt interactivo)"),
        ("--agent  <nombre>","Agente para memory list/save"),
        ("--limit  <n>",     "Cantidad de entradas en ledger (default 10)"),
        ("--verdict <v>",    "Filtrar ledger: APPROVED / BLOCKED"),
    ]:
        print(f"  {q(C.B5, flag.ljust(22))}  {q(C.G3, desc)}")

    section("Ejemplo rápido")
    examples = [
        ("nova init",                                     "primera vez"),
        ("nova agent create",                             "crear agente interactivo"),
        ('nova validate --action "Enviar email"',         "validar una acción"),
        ('nova memory save --agent "Bot" --key "x" --value "y"', "guardar memoria"),
        ("nova ledger --limit 20 --verdict BLOCKED",      "ver bloqueados"),
    ]
    for ex, note in examples:
        print(f"  {q(C.G4,'$')} {q(C.W, ex)}  {q(C.G4, f'# {note}')}")

    print()


# ══════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(prog="nova", add_help=False)
    p.add_argument("command",    nargs="?", default="help")
    p.add_argument("subcommand", nargs="?", default="")
    p.add_argument("--token",    "-t", default="")
    p.add_argument("--action",   "-a", default="")
    p.add_argument("--context",  "-c", default="")
    p.add_argument("--agent",    default="")
    p.add_argument("--key",      default="")
    p.add_argument("--value",    default="")
    p.add_argument("--importance",default="5")
    p.add_argument("--limit",    type=int, default=10)
    p.add_argument("--verdict",  default="")
    p.add_argument("--help",     "-h", action="store_true")
    args = p.parse_args()

    if args.help or args.command in ("help", "--help", "-h"):
        cmd_help(args); return

    routes = {
        ("init",     ""):         cmd_init,
        ("status",   ""):         cmd_status,
        ("agent",    "create"):   cmd_agent_create,
        ("agent",    "list"):     cmd_agent_list,
        ("agents",   ""):         cmd_agent_list,
        ("validate", ""):         cmd_validate,
        ("memory",   "save"):     cmd_memory_save,
        ("memory",   "list"):     cmd_memory_list,
        ("ledger",   ""):         cmd_ledger,
        ("ledger",   "verify"):   cmd_verify,
        ("verify",   ""):         cmd_verify,
        ("alerts",   ""):         cmd_alerts,
        ("seed",     ""):         cmd_seed,
        ("config",   ""):         cmd_config,
    }

    fn = routes.get((args.command, args.subcommand)) or routes.get((args.command, ""))

    if not fn:
        fail(f"Comando desconocido: {args.command}")
        print()
        info(f"Usa  {q(C.B7,'nova help')}  para ver todos los comandos.")
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
