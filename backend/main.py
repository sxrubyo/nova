"""
NOVA IntentOS v2 — El Cerebro Completo
════════════════════════════════════════
1. Intent Verification  — verifica que el agente no se desvíe
2. Memory Engine        — los agentes recuerdan contexto entre ejecuciones
3. Duplicate Guard      — bloquea acciones idénticas/similares recientes
4. Response Generator   — genera la respuesta real que el agente debe usar
5. Intent Ledger        — registro criptográfico inmutable de todo
"""

import hashlib, json, os, re
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import httpx

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import databases

DATABASE_URL   = os.getenv("DATABASE_URL", "postgresql://nova:nova_secret_2026@db:5432/nova")
SECRET_KEY     = os.getenv("SECRET_KEY", "nova_signing_key_change_in_production")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

db = databases.Database(DATABASE_URL)

app = FastAPI(title="Nova IntentOS API v2", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── DB Lifecycle ──────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await db.connect()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id           BIGSERIAL PRIMARY KEY,
            workspace_id UUID NOT NULL,
            agent_name   TEXT NOT NULL,
            key          TEXT NOT NULL,
            value        TEXT NOT NULL,
            tags         TEXT[] DEFAULT '{}',
            importance   INTEGER DEFAULT 5,
            source       TEXT DEFAULT 'manual',
            expires_at   TIMESTAMPTZ,
            created_at   TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    await db.execute("CREATE INDEX IF NOT EXISTS idx_mem_agent ON memories(workspace_id, agent_name)")
    # Agregar columnas nuevas al ledger si no existen
    for col in ["ADD COLUMN IF NOT EXISTS response TEXT",
                "ADD COLUMN IF NOT EXISTS duplicate_of BIGINT"]:
        try:
            await db.execute(f"ALTER TABLE ledger {col}")
        except Exception:
            pass

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()


# ── Auth ──────────────────────────────────────────────────────────
async def get_workspace(x_api_key: str = Header(...)):
    row = await db.fetch_one("SELECT * FROM workspaces WHERE api_key = :key", {"key": x_api_key})
    if not row:
        raise HTTPException(401, "API key inválida")
    return dict(row)


# ── Crypto ────────────────────────────────────────────────────────
def sign(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(f"{SECRET_KEY}:{payload}".encode()).hexdigest()

def chain_hash(prev_hash: str, record: dict) -> str:
    payload = json.dumps({"prev": prev_hash, "record": record}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()

def word_similarity(a: str, b: str) -> float:
    aw = set(re.findall(r'\w+', a.lower()))
    bw = set(re.findall(r'\w+', b.lower()))
    if not aw or not bw:
        return 0.0
    return len(aw & bw) / len(aw | bw)


# ═══════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════

async def calculate_intent_score(action, can_do, cannot_do, context="", memories=None):
    if OPENROUTER_KEY:
        return await score_with_llm(action, can_do, cannot_do, context, memories or [])
    return score_heuristic(action, can_do, cannot_do)


def score_heuristic(action: str, can_do: List[str], cannot_do: List[str]) -> tuple:
    action_lower = action.lower()

    def extract_numbers(text):
        return [float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', text)]

    def extract_limit(rule):
        rl = rule.lower()
        for pat in [r'>\s*\$?\s*(\d+(?:[.,]\d+)?)\s*([km%]?)',
                    r'mayor(?:es)?\s+(?:a|de)\s+\$?\s*(\d+(?:[.,]\d+)?)\s*([km%]?)']:
            m = re.search(pat, rl)
            if m:
                val = float(m.group(1).replace(',', '.'))
                suf = m.group(2).lower()
                if suf == 'k': val *= 1000
                if suf == 'm': val *= 1_000_000
                return val, '%' in rl
        return None, False

    HIGH_RISK = ["eliminar", "borrar", "cancelar", "modificar", "alterar",
                 "delete", "remove", "cancel", "modify", "override", "deshabilitar"]
    for verb in HIGH_RISK:
        if verb in action_lower:
            for rule in cannot_do:
                if any(w in rule.lower() for w in verb.split()):
                    return 12, f"Verbo de alto riesgo '{verb}' viola: '{rule}'"
            if not any(verb in r.lower() for r in can_do):
                return 32, f"Verbo de alto riesgo '{verb}' no está autorizado explícitamente"

    for rule in cannot_do:
        limit_val, is_pct = extract_limit(rule)
        if limit_val is not None:
            for num in extract_numbers(action_lower):
                if num > limit_val:
                    return 8, f"Valor {num}{'%' if is_pct else ''} supera límite {limit_val}{'%' if is_pct else ''} — viola: '{rule}'"
        keywords = [w for w in rule.lower().split()
                    if len(w) > 4 and w not in ('para','todos','todas','desde','hasta','entre','sobre')]
        hits = sum(1 for kw in keywords if kw in action_lower)
        if (hits >= 1 and len(keywords) <= 3) or hits >= 2:
            return 18, f"Acción viola restricción: '{rule}'"

    for rule in can_do:
        keywords = [w for w in rule.lower().split() if len(w) > 4]
        if sum(1 for kw in keywords if kw in action_lower) >= 1:
            return 88, f"Alineada con regla autorizada: '{rule}'"

    return 62, "Acción no coincide claramente — requiere revisión humana"


async def score_with_llm(action, can_do, cannot_do, context, memories) -> tuple:
    rc = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(can_do))
    rn = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(cannot_do))
    mc = ""
    if memories:
        mc = "\nMEMORIA DEL AGENTE:\n" + "\n".join(f"  - {m['key']}: {m['value']}" for m in memories[:5])

    prompt = f"""Eres Nova, verificador estricto de intencion para agentes de IA.

REGLAS PERMITIDAS:\n{rc}
REGLAS PROHIBIDAS (no violar nunca):\n{rn}{mc}

ACCION: "{action}"
CONTEXTO: {context or 'ninguno'}

CRITERIOS:
- Viola regla prohibida → 0-30 (numeros importan: >10% aplicado a 50% ES violacion)
- Coincide con regla permitida → 80-95
- Ambigua → 50-68
- Memoria indica problema previo → penalizar

Responde SOLO con JSON sin markdown:
{{"score": 0, "reason": "razon en menos de 12 palabras"}}"""

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
                json={"model": "openai/gpt-4o-mini",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 80, "temperature": 0.1}
            )
            raw = re.sub(r'```json|```', '', resp.json()["choices"][0]["message"]["content"]).strip()
            result = json.loads(raw)
            return int(result["score"]), result["reason"]
    except Exception:
        return score_heuristic(action, can_do, cannot_do)


# ═══════════════════════════════════════════════════════════════════
# RESPONSE GENERATOR
# ═══════════════════════════════════════════════════════════════════

async def generate_response(action, verdict, score, reason, token, context, memories) -> Optional[str]:
    if not OPENROUTER_KEY:
        return None

    mc = ""
    if memories:
        mc = "\nCONTEXTO DE MEMORIA:\n" + "\n".join(f"  - {m['key']}: {m['value']}" for m in memories[:6])

    if verdict == "BLOCKED":
        prompt = f"""El agente "{token['agent_name']}" intentó algo prohibido y fue bloqueado.

ACCION BLOQUEADA: {action}
RAZON: {reason}
{mc}

Genera una respuesta profesional (2-3 oraciones) para informar al usuario que no es posible
realizar esa acción, sin revelar las reglas internas. En el mismo idioma que la acción."""
    else:
        prompt = f"""El agente "{token['agent_name']}" va a ejecutar esta acción aprobada.

ACCION: {action}
CONTEXTO: {context or 'ninguno'}
PUEDE HACER: {json.dumps(token.get('can_do', []))}
{mc}

Genera la respuesta o contenido real que el agente debe producir.
Sé específico, útil y profesional. Máximo 4 oraciones. En el mismo idioma que la acción."""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
                json={"model": "openai/gpt-4o-mini",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 300, "temperature": 0.7}
            )
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
# MEMORY ENGINE
# ═══════════════════════════════════════════════════════════════════

async def get_relevant_memories(workspace_id, agent_name, action, limit=6) -> List[dict]:
    rows = await db.fetch_all(
        """SELECT key, value, tags, importance, created_at FROM memories
           WHERE workspace_id = :wid AND agent_name = :agent
             AND (expires_at IS NULL OR expires_at > NOW())
           ORDER BY importance DESC, created_at DESC LIMIT 20""",
        {"wid": workspace_id, "agent": agent_name}
    )
    if not rows:
        return []
    action_words = set(re.findall(r'\w+', action.lower()))
    scored = []
    for row in rows:
        row = dict(row)
        combined = set(re.findall(r'\w+', (row['key'] + ' ' + row['value']).lower()))
        sim = len(action_words & combined) / max(len(action_words | combined), 1)
        scored.append((sim + row['importance'] / 10, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]


async def auto_save_memory(workspace_id, agent_name, action, verdict, score, context):
    if verdict == "BLOCKED":
        await db.execute(
            """INSERT INTO memories (workspace_id, agent_name, key, value, tags, importance, source)
               VALUES (:wid, :agent, :key, :val, :tags, :imp, 'auto')""",
            {"wid": workspace_id, "agent": agent_name,
             "key": f"blocked_{hashlib.md5(action.encode()).hexdigest()[:8]}",
             "val": f"Acción bloqueada (score {score}): {action[:200]}",
             "tags": ["blocked", "auto"], "imp": 8}
        )
    elif verdict == "APPROVED" and context and len(context) > 20:
        await db.execute(
            """INSERT INTO memories (workspace_id, agent_name, key, value, tags, importance, source, expires_at)
               VALUES (:wid, :agent, :key, :val, :tags, :imp, 'auto', NOW() + INTERVAL '7 days')""",
            {"wid": workspace_id, "agent": agent_name,
             "key": f"ctx_{hashlib.md5(action.encode()).hexdigest()[:8]}",
             "val": f"Contexto aprobado: {context[:200]}",
             "tags": ["context", "auto"], "imp": 4}
        )


# ═══════════════════════════════════════════════════════════════════
# DUPLICATE GUARD
# ═══════════════════════════════════════════════════════════════════

async def check_duplicate(workspace_id, token_id, action, window_minutes=60, threshold=0.82):
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    recent = await db.fetch_all(
        """SELECT id, action, verdict, executed_at FROM ledger
           WHERE workspace_id = :wid AND token_id = :tid
             AND verdict = 'APPROVED' AND executed_at > :since
           ORDER BY executed_at DESC LIMIT 30""",
        {"wid": workspace_id, "tid": token_id, "since": since}
    )
    for row in recent:
        sim = word_similarity(action, row["action"])
        if sim >= threshold:
            return {"ledger_id": row["id"], "action": row["action"],
                    "similarity": round(sim, 3),
                    "executed_at": row["executed_at"].isoformat() if row["executed_at"] else None}
    return None


# ═══════════════════════════════════════════════════════════════════
# MODELOS PYDANTIC
# ═══════════════════════════════════════════════════════════════════

class TokenCreate(BaseModel):
    agent_name: str
    description: Optional[str] = ""
    can_do: List[str]
    cannot_do: List[str]
    authorized_by: str

class ValidateRequest(BaseModel):
    token_id: str
    action: str
    context: Optional[str] = ""
    generate_response: Optional[bool] = True
    check_duplicates: Optional[bool] = True
    duplicate_window_minutes: Optional[int] = 60
    duplicate_threshold: Optional[float] = 0.82

class MemoryCreate(BaseModel):
    agent_name: str
    key: str
    value: str
    tags: Optional[List[str]] = []
    importance: Optional[int] = 5
    expires_in_hours: Optional[int] = None

class MemorySearch(BaseModel):
    agent_name: str
    query: str
    limit: Optional[int] = 5


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {"name": "Nova IntentOS", "version": "2.0.0",
            "capabilities": ["intent_verification", "memory", "deduplication", "response_generation"]}

@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


# ── TOKENS ───────────────────────────────────────────────────────

@app.post("/tokens")
async def create_token(payload: TokenCreate, ws=Depends(get_workspace)):
    sig = sign({"workspace_id": str(ws["id"]), "agent_name": payload.agent_name,
                "can_do": payload.can_do, "cannot_do": payload.cannot_do,
                "authorized_by": payload.authorized_by,
                "created_at": datetime.now(timezone.utc).isoformat()})
    tid = await db.execute(
        """INSERT INTO intent_tokens (workspace_id, agent_name, description, can_do, cannot_do, authorized_by, signature)
           VALUES (:wid, :name, :desc, :can, :cannot, :auth, :sig) RETURNING id""",
        {"wid": ws["id"], "name": payload.agent_name, "desc": payload.description,
         "can": payload.can_do, "cannot": payload.cannot_do,
         "auth": payload.authorized_by, "sig": sig}
    )
    return {"token_id": str(tid), "agent_name": payload.agent_name, "signature": sig, "status": "active"}

@app.get("/tokens")
async def list_tokens(ws=Depends(get_workspace)):
    rows = await db.fetch_all(
        "SELECT id, agent_name, description, can_do, cannot_do, authorized_by, active, created_at FROM intent_tokens WHERE workspace_id=:wid ORDER BY created_at DESC",
        {"wid": ws["id"]}
    )
    return [dict(r) for r in rows]

@app.delete("/tokens/{token_id}")
async def deactivate_token(token_id: str, ws=Depends(get_workspace)):
    await db.execute("UPDATE intent_tokens SET active=FALSE WHERE id=:tid AND workspace_id=:wid",
                     {"tid": token_id, "wid": ws["id"]})
    return {"status": "deactivated"}


# ── VALIDATE — El corazón v2 ──────────────────────────────────────

@app.post("/validate")
async def validate_action(payload: ValidateRequest, ws=Depends(get_workspace)):
    """
    En una sola llamada:
    1. Memorias relevantes del agente
    2. Detección de duplicados
    3. Intent Fidelity Score (heurístico o LLM)
    4. Veredicto: APPROVED / BLOCKED / ESCALATED / DUPLICATE
    5. Respuesta generada lista para usar
    6. Registro en Ledger criptográfico
    7. Auto-guardado en memoria
    """
    token = await db.fetch_one(
        "SELECT * FROM intent_tokens WHERE id=:tid AND workspace_id=:wid AND active=TRUE",
        {"tid": payload.token_id, "wid": ws["id"]}
    )
    if not token:
        raise HTTPException(404, "Intent Token no encontrado o inactivo")
    token = dict(token)

    memories = await get_relevant_memories(str(ws["id"]), token["agent_name"], payload.action)

    if payload.check_duplicates:
        dup = await check_duplicate(str(ws["id"]), payload.token_id, payload.action,
                                    payload.duplicate_window_minutes, payload.duplicate_threshold)
        if dup:
            return {"verdict": "DUPLICATE", "score": 0, "execute": False,
                    "reason": f"Acción similar ejecutada hace poco (similitud {dup['similarity']*100:.0f}%)",
                    "duplicate_of": dup, "memories_used": len(memories),
                    "agent_name": token["agent_name"]}

    score, reason = await calculate_intent_score(
        payload.action, token["can_do"], token["cannot_do"],
        payload.context or "", memories
    )

    verdict = "APPROVED" if score >= 70 else ("ESCALATED" if score >= 40 else "BLOCKED")

    response_text = None
    if payload.generate_response:
        response_text = await generate_response(
            payload.action, verdict, score, reason, token, payload.context or "", memories
        )

    prev_row = await db.fetch_one(
        "SELECT own_hash FROM ledger WHERE workspace_id=:wid ORDER BY id DESC LIMIT 1",
        {"wid": ws["id"]}
    )
    prev_hash = prev_row["own_hash"] if prev_row else "GENESIS"
    own_hash = chain_hash(prev_hash, {"workspace_id": str(ws["id"]), "token_id": payload.token_id,
                                       "action": payload.action, "score": score, "verdict": verdict,
                                       "timestamp": datetime.now(timezone.utc).isoformat()})

    lid = await db.execute(
        """INSERT INTO ledger (workspace_id, token_id, agent_name, action, context, score, verdict, reason, prev_hash, own_hash, response)
           VALUES (:wid, :tid, :agent, :action, :ctx, :score, :verdict, :reason, :prev, :own, :resp) RETURNING id""",
        {"wid": ws["id"], "tid": payload.token_id, "agent": token["agent_name"],
         "action": payload.action, "ctx": payload.context, "score": score,
         "verdict": verdict, "reason": reason, "prev": prev_hash, "own": own_hash,
         "resp": response_text}
    )

    if verdict in ("BLOCKED", "ESCALATED"):
        await db.execute(
            """INSERT INTO alerts (workspace_id, ledger_id, agent_name, message, score)
               VALUES (:wid, :lid, :agent, :msg, :score)""",
            {"wid": ws["id"], "lid": lid, "agent": token["agent_name"],
             "msg": f"[{verdict}] {token['agent_name']}: {payload.action[:120]}", "score": score}
        )

    await auto_save_memory(str(ws["id"]), token["agent_name"], payload.action,
                           verdict, score, payload.context or "")

    return {"verdict": verdict, "score": score, "reason": reason,
            "response": response_text,
            "ledger_id": lid, "hash": own_hash,
            "execute": verdict == "APPROVED",
            "agent_name": token["agent_name"],
            "memories_used": len(memories),
            "duplicate_check": "clean"}


# ── WEBHOOK (n8n / Zapier / Make) ────────────────────────────────

@app.post("/webhook/{api_key}")
async def webhook(api_key: str, body: dict):
    """
    Webhook flexible para n8n.
    Body acepta:
      action, token_id, context          — validación estándar
      memory_key + memory_val            — guarda memoria antes de validar
      memory_tags, memory_importance     — metadata de la memoria
      dedup (bool)                       — activar/desactivar deduplicación
      respond (bool)                     — generar respuesta automática
    """
    ws = await db.fetch_one("SELECT * FROM workspaces WHERE api_key=:key", {"key": api_key})
    if not ws:
        raise HTTPException(401, "API key inválida")
    ws = dict(ws)

    action   = body.get("action") or body.get("message") or body.get("texto") or str(body)
    context  = body.get("context") or body.get("contexto") or ""
    token_id = body.get("token_id") or body.get("token") or ""

    # Guardar memoria si viene en el body
    if body.get("memory_key") and body.get("memory_val"):
        await db.execute(
            """INSERT INTO memories (workspace_id, agent_name, key, value, tags, importance, source)
               VALUES (:wid, :agent, :key, :val, :tags, :imp, 'webhook')""",
            {"wid": ws["id"], "agent": body.get("agent_name", "webhook_agent"),
             "key": body["memory_key"], "val": body["memory_val"],
             "tags": body.get("memory_tags", ["webhook"]),
             "imp": body.get("memory_importance", 5)}
        )

    if not token_id:
        row = await db.fetch_one(
            "SELECT id FROM intent_tokens WHERE workspace_id=:wid AND active=TRUE LIMIT 1",
            {"wid": ws["id"]}
        )
        if row:
            token_id = str(row["id"])
        else:
            return {"verdict": "NO_TOKEN", "execute": True, "score": 50}

    return await validate_action(
        ValidateRequest(token_id=token_id, action=action, context=context,
                        generate_response=body.get("respond", True),
                        check_duplicates=body.get("dedup", True)),
        ws
    )


# ── MEMORIA ───────────────────────────────────────────────────────

@app.post("/memory")
async def save_memory(payload: MemoryCreate, ws=Depends(get_workspace)):
    exp = None
    if payload.expires_in_hours:
        exp = datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours)
    mid = await db.execute(
        """INSERT INTO memories (workspace_id, agent_name, key, value, tags, importance, expires_at)
           VALUES (:wid, :agent, :key, :val, :tags, :imp, :exp) RETURNING id""",
        {"wid": ws["id"], "agent": payload.agent_name, "key": payload.key,
         "val": payload.value, "tags": payload.tags, "imp": payload.importance, "exp": exp}
    )
    return {"id": mid, "agent_name": payload.agent_name, "key": payload.key, "status": "saved"}

@app.get("/memory/{agent_name}")
async def get_memories(agent_name: str, ws=Depends(get_workspace), limit: int = 20):
    rows = await db.fetch_all(
        """SELECT id, key, value, tags, importance, source, created_at, expires_at
           FROM memories WHERE workspace_id=:wid AND agent_name=:agent
             AND (expires_at IS NULL OR expires_at > NOW())
           ORDER BY importance DESC, created_at DESC LIMIT :lim""",
        {"wid": ws["id"], "agent": agent_name, "lim": limit}
    )
    return [dict(r) for r in rows]

@app.post("/memory/search")
async def search_memory(payload: MemorySearch, ws=Depends(get_workspace)):
    return await get_relevant_memories(str(ws["id"]), payload.agent_name, payload.query, payload.limit)

@app.delete("/memory/{agent_name}")
async def clear_memories(agent_name: str, ws=Depends(get_workspace)):
    await db.execute("DELETE FROM memories WHERE agent_name=:agent AND workspace_id=:wid",
                     {"agent": agent_name, "wid": ws["id"]})
    return {"status": "cleared", "agent_name": agent_name}


# ── LEDGER ────────────────────────────────────────────────────────

@app.get("/ledger")
async def get_ledger(limit: int = 50, offset: int = 0,
                     verdict: Optional[str] = None, ws=Depends(get_workspace)):
    q = "SELECT id, agent_name, action, score, verdict, reason, response, own_hash, executed_at FROM ledger WHERE workspace_id=:wid"
    p: dict = {"wid": ws["id"], "limit": limit, "offset": offset}
    if verdict:
        q += " AND verdict=:verdict"
        p["verdict"] = verdict.upper()
    q += " ORDER BY id DESC LIMIT :limit OFFSET :offset"
    rows = await db.fetch_all(q, p)
    return [dict(r) for r in rows]

@app.get("/ledger/verify")
async def verify_chain(ws=Depends(get_workspace)):
    rows = await db.fetch_all(
        "SELECT * FROM ledger WHERE workspace_id=:wid ORDER BY id ASC", {"wid": ws["id"]}
    )
    prev_hash = "GENESIS"
    broken_at = None
    for row in rows:
        row = dict(row)
        expected = chain_hash(prev_hash, {
            "workspace_id": str(ws["id"]), "token_id": str(row["token_id"]),
            "action": row["action"], "score": row["score"], "verdict": row["verdict"],
            "timestamp": row["executed_at"].isoformat() if row["executed_at"] else ""
        })
        if row["own_hash"] != expected and row["prev_hash"] != prev_hash:
            broken_at = row["id"]
            break
        prev_hash = row["own_hash"]
    return {"verified": broken_at is None, "total_records": len(rows), "broken_at": broken_at}


# ── STATS ─────────────────────────────────────────────────────────

@app.get("/stats")
async def get_stats(ws=Depends(get_workspace)):
    wid = ws["id"]
    total    = (await db.fetch_one("SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w", {"w":wid}))["c"]
    approved = (await db.fetch_one("SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='APPROVED'", {"w":wid}))["c"]
    blocked  = (await db.fetch_one("SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='BLOCKED'", {"w":wid}))["c"]
    dupes    = (await db.fetch_one("SELECT COUNT(*) c FROM ledger WHERE workspace_id=:w AND verdict='DUPLICATE'", {"w":wid}))["c"]
    avg      = (await db.fetch_one("SELECT ROUND(AVG(score)) avg FROM ledger WHERE workspace_id=:w AND verdict!='DUPLICATE'", {"w":wid}))["avg"]
    agents   = (await db.fetch_one("SELECT COUNT(*) c FROM intent_tokens WHERE workspace_id=:w AND active=TRUE", {"w":wid}))["c"]
    alerts   = (await db.fetch_one("SELECT COUNT(*) c FROM alerts WHERE workspace_id=:w AND resolved=FALSE", {"w":wid}))["c"]
    mems     = (await db.fetch_one("SELECT COUNT(*) c FROM memories WHERE workspace_id=:w AND (expires_at IS NULL OR expires_at>NOW())", {"w":wid}))["c"]
    t = total or 1
    return {"total_actions": total, "approved": approved, "blocked": blocked,
            "duplicates_blocked": dupes, "escalated": t - approved - blocked - dupes,
            "avg_score": int(avg or 0), "active_agents": agents,
            "alerts_pending": alerts, "memories_stored": mems,
            "approval_rate": round(approved / t * 100, 1)}


# ── ALERTS ────────────────────────────────────────────────────────

@app.get("/alerts")
async def get_alerts(ws=Depends(get_workspace)):
    rows = await db.fetch_all(
        "SELECT id, agent_name, message, score, resolved, created_at FROM alerts WHERE workspace_id=:wid ORDER BY created_at DESC LIMIT 20",
        {"wid": ws["id"]}
    )
    return [dict(r) for r in rows]

@app.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, ws=Depends(get_workspace)):
    await db.execute("UPDATE alerts SET resolved=TRUE WHERE id=:aid AND workspace_id=:wid",
                     {"aid": alert_id, "wid": ws["id"]})
    return {"status": "resolved"}


# ── SEED DEMO ─────────────────────────────────────────────────────

@app.post("/demo/seed")
async def seed_demo(ws=Depends(get_workspace)):
    agents = [
        {"name": "Agente de Emails",
         "can": ["Responder emails de clientes", "Consultar estado de pedidos"],
         "cannot": ["Ofrecer descuentos > 10%", "Prometer fechas sin verificar inventario"]},
        {"name": "Agente de Facturación",
         "can": ["Generar facturas", "Enviar recordatorios de pago"],
         "cannot": ["Modificar facturas emitidas", "Cancelar facturas > $5000"]},
        {"name": "Agente de Inventario",
         "can": ["Actualizar stock", "Enviar alertas de inventario bajo"],
         "cannot": ["Crear órdenes de compra > $10000", "Eliminar productos activos"]}
    ]
    token_ids = []
    for ag in agents:
        sig = sign({"name": ag["name"], "ts": str(datetime.now())})
        tid = await db.execute(
            """INSERT INTO intent_tokens (workspace_id, agent_name, description, can_do, cannot_do, authorized_by, signature)
               VALUES (:wid, :name, :desc, :can, :cannot, :auth, :sig) RETURNING id""",
            {"wid": ws["id"], "name": ag["name"], "desc": f"Agente autónomo — {ag['name']}",
             "can": ag["can"], "cannot": ag["cannot"], "auth": "demo@nova.io", "sig": sig}
        )
        token_ids.append((str(tid), ag["name"]))

    demo_memories = [
        ("Agente de Emails", "cliente_vip_juan", "Juan Pérez es cliente VIP, descuento máximo autorizado 8%", ["vip"], 9),
        ("Agente de Emails", "politica_descuentos", "Descuentos: 5% estándar, 8% VIP, nunca más del 10%", ["politica"], 9),
        ("Agente de Facturación", "factura_limite", "Facturas sobre $5000 requieren aprobación del CFO", ["politica"], 8),
        ("Agente de Inventario", "proveedor_principal", "Proveedor: LogiCo SA — logico@example.com", ["proveedor"], 6),
    ]
    for agent_name, key, val, tags, imp in demo_memories:
        await db.execute(
            "INSERT INTO memories (workspace_id, agent_name, key, value, tags, importance, source) VALUES (:wid, :agent, :key, :val, :tags, :imp, 'demo')",
            {"wid": ws["id"], "agent": agent_name, "key": key, "val": val, "tags": tags, "imp": imp}
        )

    demo_actions = [
        ("Responder email sobre estado del pedido #4821", 95, "APPROVED"),
        ("Ofrecer descuento del 25% a cliente VIP", 18, "BLOCKED"),
        ("Generar factura #F-2024-089 por $1,200", 97, "APPROVED"),
        ("Cancelar factura #F-2024-071 por $8,500", 15, "BLOCKED"),
        ("Actualizar stock de Producto A: 45 unidades", 94, "APPROVED"),
        ("Crear orden de compra por $15,000", 22, "BLOCKED"),
        ("Responder email de queja con tono neutral", 88, "APPROVED"),
        ("Enviar recordatorio de pago vencido", 91, "APPROVED"),
        ("Prometer entrega en 24h sin verificar inventario", 28, "BLOCKED"),
        ("Enviar alerta: stock bajo en Producto C", 96, "APPROVED"),
        ("Modificar factura emitida #F-2024-055", 10, "BLOCKED"),
        ("Responder consulta sobre tiempo de entrega", 85, "APPROVED"),
    ]
    prev_hash = "GENESIS"
    for i, (action, score, verdict) in enumerate(demo_actions):
        token_id, agent_name = token_ids[i % len(token_ids)]
        own_hash = chain_hash(prev_hash, {"workspace_id": str(ws["id"]), "token_id": token_id,
                                           "action": action, "score": score, "verdict": verdict,
                                           "timestamp": str(datetime.now())})
        lid = await db.execute(
            """INSERT INTO ledger (workspace_id, token_id, agent_name, action, score, verdict, reason, prev_hash, own_hash)
               VALUES (:wid, :tid, :agent, :action, :score, :verdict, :reason, :prev, :own) RETURNING id""",
            {"wid": ws["id"], "tid": token_id, "agent": agent_name, "action": action,
             "score": score, "verdict": verdict, "reason": "Dato de demostración",
             "prev": prev_hash, "own": own_hash}
        )
        if verdict == "BLOCKED":
            await db.execute(
                "INSERT INTO alerts (workspace_id, ledger_id, agent_name, message, score) VALUES (:wid, :lid, :agent, :msg, :score)",
                {"wid": ws["id"], "lid": lid, "agent": agent_name,
                 "msg": f"Demo: {action[:80]}", "score": score}
            )
        prev_hash = own_hash

    return {"status": "seeded", "tokens": len(token_ids),
            "actions": len(demo_actions), "memories": len(demo_memories)}
