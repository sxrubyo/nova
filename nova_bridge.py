"""
nova_bridge.py  —  Puente multi-tenant entre Melissa y Nova Core

ARQUITECTURA CORREGIDA:
  ✗ Antes → llamaba a nova-api (puerto 9002, main.py) que NO tiene /ledger ni /rules
  ✓ Ahora → llama a nova-core (puerto 9003, nova_core.py) que tiene TODO

FLUJO POR INSTANCIA:
  1. Melissa arranca con INSTANCE_ID="clinica-dental-medellin"
  2. boot() → GET /boot/clinica-dental-medellin → devuelve system_block con sus reglas
  3. Melissa inyecta ese bloque en su system prompt → cada instancia tiene sus propias reglas
  4. Cliente escribe "no hagas X" → intercept_from_chat() detecta el patrón
     → POST /intercept en nova_core → la regla queda en scope agent:clinica-dental-medellin
     → solo esa instancia queda afectada
  5. Antes de enviar un mensaje → validate() → POST /validate en nova_core
     → APPROVED / BLOCKED / WARNED

MULTI-TENANT:
  Cada instancia de Melissa tiene su propio INSTANCE_ID.
  Las reglas viven en nova_core con scope "agent:{INSTANCE_ID}".
  No hay reglas en código. No hay nova setup. Solo lenguaje natural.

ENV:
  NOVA_CORE_URL   = http://localhost:9003  ← nova_core.py, NO main.py
  NOVA_API_KEY    = nova_dev_key
  NOVA_ENABLED    = true
  INSTANCE_ID     = clinica-dental-medellin  ← identifica esta instancia
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from typing import Dict, List, Optional, Tuple

import httpx

log = logging.getLogger("melissa.nova")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

# Nova CORE — puerto 9003, nova_core.py (tiene /ledger, /rules, /stream, /intercept)
NOVA_CORE_URL = os.getenv("NOVA_CORE_URL", "http://localhost:9003")
NOVA_API_KEY  = os.getenv("NOVA_API_KEY",  "nova_dev_key")
NOVA_ENABLED  = os.getenv("NOVA_ENABLED",  "true").lower() == "true"
NOVA_TIMEOUT  = float(os.getenv("NOVA_TIMEOUT", "3.0"))

# ID único de esta instancia — determina el scope de las reglas
# Ejemplos: "clinica-dental-medellin", "spa-bogota", "melissa-demo"
INSTANCE_ID   = os.getenv("INSTANCE_ID", os.getenv("CLINIC_NAME", "melissa")).lower()
INSTANCE_ID   = re.sub(r"[^a-z0-9-]", "-", INSTANCE_ID).strip("-") or "melissa"

# Scope de Nova para esta instancia
AGENT_SCOPE   = f"agent:{INSTANCE_ID}"

# Veredictos
APPROVED  = "APPROVED"
BLOCKED   = "BLOCKED"
ESCALATED = "ESCALATED"
WARNED    = "WARNED"
UNKNOWN   = "UNKNOWN"

log.info(f"[nova_bridge] instance={INSTANCE_ID} scope={AGENT_SCOPE} core={NOVA_CORE_URL}")


# ══════════════════════════════════════════════════════════════════════════════
# CACHE LOCAL
# ══════════════════════════════════════════════════════════════════════════════

_decision_cache: Dict[str, Tuple[str, float]] = {}
_CACHE_TTL = 120  # 2 min — más corto para que las reglas nuevas apliquen rápido

def _cache_key(action: str, scope: str) -> str:
    return hashlib.md5(f"{scope}|{action}".encode()).hexdigest()[:12]

def _cache_get(key: str) -> Optional[str]:
    if key in _decision_cache:
        verdict, ts = _decision_cache[key]
        if time.time() - ts < _CACHE_TTL:
            return verdict
    return None

def _cache_set(key: str, verdict: str):
    _decision_cache[key] = (verdict, time.time())

def _cache_bust():
    """Limpia el cache — llamar cuando se crea una regla nueva."""
    _decision_cache.clear()


# ══════════════════════════════════════════════════════════════════════════════
# PRE-CHECK LOCAL (sub-millisegundo, sin red)
# ══════════════════════════════════════════════════════════════════════════════

_ALWAYS_BLOCK = [
    r"(diagnóstico médico|tienes cáncer|toma.*pastilla|dosis.*recomend)",
    r"(precio.*gratis|descuento.*100%|sin costo.*siempre)",
    r"(mándame.*foto.*privada|manda.*fotos.*íntimas)",
    r"(datos.*otro.*paciente|información.*otro.*cliente)",
]
_ALWAYS_APPROVE = [
    r"^(hola|buenas|buenos días|buenas tardes|buenas noches)[\s!.]*$",
    r"^(ok|listo|dale|claro|perfecto|entendido)[\s!.]*$",
    r"(horario|horarios|dirección|ubicación|servicios disponibles)",
    r"(gracias por escribir|con gusto|estoy aquí para ayudar)",
]

def _local_pre_check(text: str) -> Optional[str]:
    t = text.lower().strip()
    for p in _ALWAYS_BLOCK:
        if re.search(p, t):
            return BLOCKED
    for p in _ALWAYS_APPROVE:
        if re.search(p, t):
            return APPROVED
    return None


# ══════════════════════════════════════════════════════════════════════════════
# NOVA CORE CLIENT
# Cliente que apunta CORRECTAMENTE a nova_core (puerto 9003)
# ══════════════════════════════════════════════════════════════════════════════

class NovaCoreClient:
    """
    Cliente para nova_core.py (puerto 9003).
    Tiene acceso a: /validate, /rules, /ledger, /stream, /intercept, /boot, /anomalies
    """

    def __init__(self):
        self.base   = NOVA_CORE_URL.rstrip("/")
        self._ok:   Optional[bool] = None
        self._ok_ts = 0.0

    def _headers(self) -> Dict:
        return {
            "Content-Type":  "application/json",
            "x-api-key":     NOVA_API_KEY,
            "User-Agent":    "melissa-bridge/2.0",
        }

    # ── Health ──────────────────────────────────────────────────────────────

    async def is_alive(self) -> bool:
        now = time.time()
        if now - self._ok_ts < 30 and self._ok is not None:
            return self._ok
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                r = await c.get(f"{self.base}/health", headers=self._headers())
                self._ok    = r.status_code < 400
                self._ok_ts = now
                return self._ok
        except Exception:
            self._ok    = False
            self._ok_ts = now
            return False

    # ── Boot — reglas dinámicas por instancia ────────────────────────────────

    async def boot(self, instance_id: str = INSTANCE_ID) -> Dict:
        """
        Llama GET /boot/{instance_id} en nova_core.
        Devuelve las reglas activas y un system_block listo para inyectar en el prompt.
        
        Llamar una vez al arrancar Melissa, y cada vez que se recarga la config.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(
                    f"{self.base}/boot/{instance_id}",
                    headers=self._headers()
                )
                r.raise_for_status()
                data = r.json()
                log.info(
                    f"[nova_boot] {instance_id} — "
                    f"{data.get('rule_count', 0)} reglas activas | "
                    f"restart #{data.get('restart_count', 0)}"
                )
                return data
        except Exception as e:
            log.warning(f"[nova_boot] error — {e} — sin reglas dinámicas")
            return {"rule_count": 0, "system_block": "", "rules": []}

    # ── Validate — antes de enviar cada mensaje ──────────────────────────────

    async def validate(
        self,
        action:     str,
        context:    str = "",
        scope:      str = AGENT_SCOPE,
        agent_name: str = INSTANCE_ID,
        dry_run:    bool = False,
    ) -> Dict:
        """
        Valida una acción contra las reglas de esta instancia.
        Retorna: {"verdict": "APPROVED|BLOCKED|WARNED|ESCALATED", "score": 0-100, ...}
        """
        payload = {
            "action":      action,
            "context":     context,
            "scope":       scope,
            "agent_name":  agent_name,
            "dry_run":     dry_run,
            "check_dups":  False,
        }
        try:
            async with httpx.AsyncClient(timeout=NOVA_TIMEOUT) as c:
                r = await c.post(
                    f"{self.base}/validate",
                    json=payload,
                    headers=self._headers()
                )
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 403:
                    d = r.json()
                    return {"verdict": BLOCKED, "score": 0,
                            "reason": d.get("reason", "blocked"), "message": d.get("message", "")}
                return {"verdict": APPROVED, "reason": f"nova_http_{r.status_code}"}
        except asyncio.TimeoutError:
            log.warning("[nova] timeout — modo degradado (approve)")
            return {"verdict": APPROVED, "reason": "nova_timeout"}
        except Exception as e:
            log.debug(f"[nova] validate error: {e}")
            return {"verdict": APPROVED, "reason": f"nova_error"}

    # ── Intercept — regla desde lenguaje natural ─────────────────────────────

    async def intercept(
        self,
        message:    str,
        sender:     str = "admin",
        scope:      str = AGENT_SCOPE,
    ) -> Optional[Dict]:
        """
        Envía un mensaje a nova_core para que detecte instrucciones de gobernanza.
        Si detecta "no hagas X" → crea la regla en el scope de esta instancia.
        
        Retorna la regla creada o None si no detectó ninguna instrucción.
        
        Ejemplos de mensajes que activan esto:
          "no le digas precios a nadie"
          "nunca menciones descuentos"
          "no hagas promesas de resultados"
          "regla: siempre pide el nombre primero"
        """
        try:
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.post(
                    f"{self.base}/intercept",
                    json={
                        "message": message,
                        "sender":  sender,
                        "scope":   scope,
                    },
                    headers=self._headers()
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("rule_created"):
                        _cache_bust()  # las reglas nuevas aplican de inmediato
                        log.info(
                            f"[nova_intercept] regla creada: "
                            f"{data.get('rule', {}).get('name', '?')} | scope={scope}"
                        )
                        return data
                return None
        except Exception as e:
            log.debug(f"[nova_intercept] error: {e}")
            return None

    # ── Rules — gestión directa ──────────────────────────────────────────────

    async def get_rules(self, scope: str = AGENT_SCOPE) -> List[Dict]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(
                    f"{self.base}/rules?scope={scope}",
                    headers=self._headers()
                )
                r.raise_for_status()
                return r.json().get("rules", [])
        except Exception as e:
            log.warning(f"[nova] get_rules error: {e}")
            return []

    async def create_rule(self, rule_data: Dict) -> Dict:
        """Crea una regla directamente (sin pasar por el interceptor NL)."""
        rule_data.setdefault("scope",    AGENT_SCOPE)
        rule_data.setdefault("source",   "melissa_bridge")
        rule_data.setdefault("active",   True)
        rule_data.setdefault("priority", 7)
        try:
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.post(
                    f"{self.base}/rules",
                    json=rule_data,
                    headers=self._headers()
                )
                r.raise_for_status()
                _cache_bust()
                return r.json()
        except Exception as e:
            log.error(f"[nova] create_rule error: {e}")
            return {"error": str(e)}

    # ── Ledger ───────────────────────────────────────────────────────────────

    async def get_ledger(
        self, agent: str = INSTANCE_ID, limit: int = 20
    ) -> List[Dict]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(
                    f"{self.base}/ledger?agent={agent}&limit={limit}",
                    headers=self._headers()
                )
                r.raise_for_status()
                return r.json().get("entries", r.json() if isinstance(r.json(), list) else [])
        except Exception as e:
            log.warning(f"[nova] get_ledger error: {e}")
            return []

    # ── Stats ────────────────────────────────────────────────────────────────

    async def get_stats(self, agent: str = INSTANCE_ID) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(
                    f"{self.base}/stats?agent={agent}",
                    headers=self._headers()
                )
                r.raise_for_status()
                return r.json()
        except Exception:
            return {}


# ══════════════════════════════════════════════════════════════════════════════
# MELISSA GUARD
# Interceptor principal — se llama antes de cada mensaje al paciente
# ══════════════════════════════════════════════════════════════════════════════

class MelissaGuard:
    """
    Guarda de gobernanza de Melissa.
    
    Uso típico en melissa.py:
        guard = get_guard()
        ok, reason, ledger_id = await guard.should_send(message, chat_id, context)
        if not ok:
            # no enviar — usar mensaje alternativo
    """

    def __init__(self, client: NovaCoreClient):
        self.client = client
        self._system_block = ""      # reglas inyectadas en el prompt
        self._rules_loaded = False

    @property
    def system_block(self) -> str:
        """Bloque de reglas para inyectar en el system prompt de Melissa."""
        return self._system_block

    async def boot(self) -> str:
        """
        Llama a nova_core al arrancar y carga las reglas de esta instancia.
        Retorna el system_block para inyectar en el prompt.
        Llamar en el lifespan de Melissa, no en cada mensaje.
        """
        if not NOVA_ENABLED:
            return ""
        data = await self.client.boot(INSTANCE_ID)
        self._system_block = data.get("system_block", "")
        self._rules_loaded = True
        n = data.get("rule_count", 0)
        if n:
            log.info(f"[nova_guard] {n} reglas cargadas para {INSTANCE_ID}")
        return self._system_block

    async def should_send(
        self,
        message:        str,
        patient_chat_id: str = "",
        context:         str = "",
        clinic_name:     str = "",
    ) -> Tuple[bool, str, str]:
        """
        Decide si Melissa puede enviar este mensaje.
        Retorna: (can_send, reason, ledger_id)
        """
        if not NOVA_ENABLED:
            return True, "nova_disabled", ""

        # 1. Pre-check local (< 1ms)
        local = _local_pre_check(message)
        if local == BLOCKED:
            return False, "local_policy_blocked", ""
        if local == APPROVED:
            return True, "local_approved", ""

        # 2. Cache
        ck = _cache_key(message[:100], AGENT_SCOPE)
        cached = _cache_get(ck)
        if cached:
            return cached == APPROVED, f"cached_{cached.lower()}", ""

        # 3. Nova Core validate
        action = f"Send message to patient {patient_chat_id}: {message[:300]}"
        ctx    = f"clinic={clinic_name or INSTANCE_ID} | {context[:200]}"

        result  = await self.client.validate(action=action, context=ctx)
        verdict = result.get("verdict", UNKNOWN)
        reason  = result.get("reason", "")
        msg     = result.get("message", "")  # mensaje alternativo de Nova
        lid     = str(result.get("entry_id", ""))

        _cache_set(ck, verdict)

        if verdict in (APPROVED, UNKNOWN):
            return True, reason, lid
        if verdict == WARNED:
            # WARNED = puede enviar pero queda registrado
            log.info(f"[nova] WARNED: {message[:60]}")
            return True, f"warned: {reason}", lid
        if verdict == ESCALATED:
            log.info(f"[nova] ESCALATED: {message[:60]}")
            return False, f"escalated: {reason}", lid

        # BLOCKED
        log.info(f"[nova] BLOCKED (#{lid}): {reason}")
        return False, msg or reason, lid

    async def filter_bubbles(
        self,
        bubbles:         List[str],
        patient_chat_id: str = "",
        context:         str = "",
        clinic_name:     str = "",
    ) -> Tuple[List[str], List[str]]:
        """
        Filtra una lista de burbujas.
        Retorna: (burbujas_permitidas, burbujas_bloqueadas)
        """
        allowed, blocked = [], []
        for b in bubbles:
            ok, reason, _ = await self.should_send(b, patient_chat_id, context, clinic_name)
            (allowed if ok else blocked).append(b)
            if not ok and not reason.startswith("local_"):
                log.info(f"[nova] burbuja bloqueada: {b[:60]} | {reason}")
        return allowed, blocked

    async def intercept_from_chat(
        self,
        message: str,
        sender:  str = "admin",
    ) -> Optional[Dict]:
        """
        Detecta instrucciones de gobernanza en mensajes del chat del admin.
        
        Si el admin escribe "no le digas precios a nadie" →
          nova_core crea la regla en el scope de ESTA instancia.
        
        Retorna el objeto de regla creada, o None si no había instrucción.
        
        Ejemplos que activan esto:
          "no hagas promesas de resultados garantizados"
          "nunca menciones otras clínicas"
          "regla: siempre pide nombre antes de dar precios"
          "prohibido dar descuentos sin autorización"
        """
        if not NOVA_ENABLED:
            return None
        return await self.client.intercept(
            message=message,
            sender=sender,
            scope=AGENT_SCOPE,
        )


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS PÚBLICOS
# ══════════════════════════════════════════════════════════════════════════════

async def get_ledger_summary(limit: int = 10) -> str:
    """Resumen del ledger para mostrar al admin vía chat."""
    client  = get_client()
    if not client:
        return "Nova no está iniciado."
    entries = await client.get_ledger(limit=limit)
    if not entries:
        return "El ledger de Nova está vacío para esta instancia."
    lines = [f"Últimas {len(entries)} decisiones de Nova ({INSTANCE_ID}):\n"]
    for e in entries:
        verdict = e.get("verdict", "?")
        action  = (e.get("action", "") or "")[:60]
        reason  = (e.get("reason",  "") or "")[:40]
        ts      = (e.get("created_at", "") or "")[:16]
        icon    = {"APPROVED": "✓", "BLOCKED": "✗", "WARNED": "⚠", "ESCALATED": "!"}.get(verdict, "?")
        lines.append(f"  {icon} [{ts}] {action} — {reason}")
    return "\n".join(lines)


async def nl_to_nova_rules(
    instruction: str,
    llm_complete_fn=None,
    existing_rules: Dict = None,
) -> Dict:
    """
    Compatibilidad hacia atrás.
    Ahora el flujo correcto es usar intercept_from_chat() que delega
    la extracción NL → regla al interceptor de nova_core.
    Este método se mantiene por si se llama desde melissa.py directamente.
    """
    guard = get_guard()
    if guard:
        result = await guard.intercept_from_chat(instruction, sender="admin")
        if result and result.get("rule_created"):
            rule = result.get("rule", {})
            return {
                "can_do":      [],
                "cannot_do":   [rule.get("original_instruction", instruction)],
                "explanation": f"Regla creada: {rule.get('name', '?')}",
                "rule_id":     rule.get("id", ""),
            }
    return {
        "can_do":      [],
        "cannot_do":   [instruction],
        "explanation": "Procesado localmente — nova_core no disponible",
    }


# ══════════════════════════════════════════════════════════════════════════════
# INSTANCIA GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

_guard:  Optional[MelissaGuard]   = None
_client: Optional[NovaCoreClient] = None


def init_nova() -> MelissaGuard:
    """
    Inicializa el bridge. Llamar una vez al arrancar Melissa.
    Seguro aunque nova_core no esté activo — Melissa funciona igual.
    """
    global _guard, _client
    _client = NovaCoreClient()
    _guard  = MelissaGuard(_client)
    if NOVA_ENABLED:
        log.info(f"[nova_bridge] → nova_core {NOVA_CORE_URL} | instance={INSTANCE_ID}")
    else:
        log.info("[nova_bridge] desactivado (NOVA_ENABLED=false)")
    return _guard


async def boot_nova() -> str:
    """
    Carga reglas dinámicas de nova_core al arrancar.
    Llamar en el lifespan de Melissa (después de init_nova).
    
    Retorna el system_block para inyectar en el system prompt.
    
    Ejemplo en melissa.py:
        @asynccontextmanager
        async def lifespan(app):
            init_nova()
            system_block = await boot_nova()
            SYSTEM_PROMPT += system_block   # ← reglas de esta instancia
            yield
    """
    if not _guard:
        init_nova()
    return await _guard.boot()


def get_guard() -> Optional[MelissaGuard]:
    return _guard


def get_client() -> Optional[NovaCoreClient]:
    return _client


# ══════════════════════════════════════════════════════════════════════════════
# SETUP — compatibilidad con nova_bridge anterior (ya no necesario)
# ══════════════════════════════════════════════════════════════════════════════

async def setup_melissa_agent(*args, **kwargs) -> Optional[str]:
    """
    DEPRECADO — ya no es necesario.
    Las reglas se cargan dinámicamente desde nova_core via boot().
    No hay setup manual. El cliente dice "no hagas X" y la regla existe.
    """
    log.warning(
        "[nova_bridge] setup_melissa_agent() está deprecado. "
        "Las reglas se cargan dinámicamente via boot_nova()."
    )
    return INSTANCE_ID
