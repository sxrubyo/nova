"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  NOVA CORE  v3.1  —  Governance Engine                                      ║
║  "The agent never changes. Nova wraps it from outside."                      ║
║                                                                              ║
║  Layers:                                                                     ║
║    0  Rule Folder   nova_rules/*.yaml — source of truth, git-friendly        ║
║    1  Deterministic keyword/regex/amount — zero LLM, sub-ms                 ║
║    2  Heuristic     scoring without LLM (from main.py ScoringEngine)        ║
║    3  Semantic      optional LLM — only when L1+L2 are ambiguous            ║
║    4  Interceptor   "no hagas X" → rule auto-created in nova_rules/         ║
║    5  Chat          natural language rule management (WS + HTTP)            ║
║    6  Ledger        immutable SQLite audit trail with chain hashing          ║
║    7  Anomaly       burst / block-rate / score-degradation detection        ║
║    8  Proxy         transparent HTTP proxy — agent sees nothing             ║
║                                                                              ║
║  Install: pip install fastapi uvicorn httpx pyyaml aiosqlite               ║
║  Run:     python nova_core.py                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import socket
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import httpx
import yaml
from fastapi import (
    FastAPI, HTTPException, WebSocket, WebSocketDisconnect,
    Request, Header, BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

class S:
    PORT            = int(os.getenv("NOVA_PORT",              "9003"))
    API_KEY         = os.getenv("NOVA_API_KEY",               "nova_dev_key")
    SECRET_KEY      = os.getenv("NOVA_SECRET_KEY",            "nova_signing_key_change_in_production")
    DEV_MODE        = os.getenv("NOVA_DEV_MODE",              "true").lower()  == "true"   # default: no auth in dev
    FAIL_OPEN       = os.getenv("NOVA_FAIL_OPEN",             "true").lower()  == "true"
    RULES_DIR       = Path(os.getenv("NOVA_RULES_DIR",        "./nova_rules"))
    DB_PATH         = os.getenv("NOVA_DB_PATH",               "./nova.db")
    AGENT_URL       = os.getenv("NOVA_AGENT_URL",             "")
    AGENT_NAME      = os.getenv("NOVA_AGENT_NAME",            "agent")
    # LLM
    LLM_PROVIDER    = os.getenv("NOVA_LLM_PROVIDER",          "openrouter")
    LLM_MODEL       = os.getenv("NOVA_LLM_MODEL",             "google/gemini-2.5-flash")
    LLM_API_KEY     = os.getenv("NOVA_LLM_API_KEY",   os.getenv("OPENROUTER_API_KEY", ""))
    LLM_BASE_URL    = os.getenv("NOVA_LLM_BASE_URL",          "")
    LLM_TIMEOUT     = float(os.getenv("NOVA_LLM_TIMEOUT",     "8.0"))
    # Thresholds
    SCORE_BLOCK     = int(os.getenv("NOVA_SCORE_BLOCK",        "40"))
    SCORE_ESCALATE  = int(os.getenv("NOVA_SCORE_ESCALATE",     "68"))
    ANOMALY_BURST   = int(os.getenv("NOVA_ANOMALY_BURST",      "20"))
    ANOMALY_BLOCKRT = float(os.getenv("NOVA_ANOMALY_BLOCKRATE","0.5"))
    ANOMALY_DROP    = float(os.getenv("NOVA_ANOMALY_SCORE_DROP","15.0"))
    DEDUP_WINDOW    = int(os.getenv("NOVA_DEDUP_WINDOW",       "60"))
    DEDUP_THRESHOLD = float(os.getenv("NOVA_DEDUP_THRESHOLD",  "0.82"))
    RATE_LIMIT      = int(os.getenv("NOVA_RATE_LIMIT",         "200"))


S.RULES_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("nova")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk(score: int) -> str:
    if score >= 90: return "none"
    if score >= 70: return "low"
    if score >= 40: return "medium"
    if score >= 20: return "high"
    return "critical"


def _jac(a: str, b: str) -> float:
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _parse_json(raw: str) -> Optional[Dict]:
    if not raw:
        return None
    try:
        clean = re.sub(r"```json\s*|```\s*", "", raw).strip()
        m = re.search(r"\{[\s\S]+\}", clean)
        return json.loads(m.group(0) if m else clean)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 0 — RULE FOLDER  nova_rules/*.yaml
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Rule:
    id:                   str
    name:                 str
    created_at:           str
    created_by:           str
    source:               str        # natural_language | intercepted | manual | api | seed
    original_instruction: str
    active:               bool
    priority:             int        # 1-10, higher = checked first
    scope:                str        # global | agent:melissa

    # Layer 1 — deterministic signals
    keywords_block: List[str]
    keywords_warn:  List[str]
    regex_block:    List[str]
    exact_block:    List[str]
    max_amount:     Optional[float]

    # Layer 3 — semantic check config
    sem_enabled:     bool
    sem_description: str
    sem_threshold:   float

    # Effect
    action:      str           # block | warn | escalate | log_only
    message:     str           # shown to user when blocked
    escalate_to: str
    log:         bool
    notify:      List[str]

    @classmethod
    def from_dict(cls, d: Dict) -> "Rule":
        det = d.get("deterministic", {})
        sem = d.get("semantic", {})
        return cls(
            id=d.get("id", "r" + secrets.token_hex(4)),
            name=d.get("name", "Unnamed"),
            created_at=d.get("created_at", _now()),
            created_by=d.get("created_by", "system"),
            source=d.get("source", "manual"),
            original_instruction=d.get("original_instruction", ""),
            active=d.get("active", True),
            priority=int(d.get("priority", 5)),
            scope=d.get("scope", "global"),
            keywords_block=det.get("keywords_block", []),
            keywords_warn=det.get("keywords_warn", []),
            regex_block=det.get("regex_block", []),
            exact_block=det.get("exact_block", []),
            max_amount=det.get("max_amount"),
            sem_enabled=sem.get("enabled", False),
            sem_description=sem.get("description", ""),
            sem_threshold=float(sem.get("threshold", 0.82)),
            action=d.get("action", "block"),
            message=d.get("message", "Acción no permitida."),
            escalate_to=d.get("escalate_to", ""),
            log=d.get("log", True),
            notify=d.get("notify", []),
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "source": self.source,
            "original_instruction": self.original_instruction,
            "active": self.active,
            "priority": self.priority,
            "scope": self.scope,
            "deterministic": {
                "keywords_block": self.keywords_block,
                "keywords_warn": self.keywords_warn,
                "regex_block": self.regex_block,
                "exact_block": self.exact_block,
                "max_amount": self.max_amount,
            },
            "semantic": {
                "enabled": self.sem_enabled,
                "description": self.sem_description,
                "threshold": self.sem_threshold,
            },
            "action": self.action,
            "message": self.message,
            "escalate_to": self.escalate_to,
            "log": self.log,
            "notify": self.notify,
        }

    def to_yaml(self) -> str:
        return yaml.dump(
            self.to_dict(), allow_unicode=True,
            default_flow_style=False, sort_keys=False,
        )


class RuleEngine:
    def __init__(self):
        self._r: Dict[str, Rule] = {}
        self._ts: float = 0.0
        self.load()

    def load(self) -> int:
        self._r = {}
        for f in sorted(S.RULES_DIR.glob("*.yaml")):
            try:
                d = yaml.safe_load(f.read_text("utf-8"))
                if d:
                    r = Rule.from_dict(d)
                    if r.active:
                        self._r[r.id] = r
            except Exception as e:
                log.warning(f"[rules] {f.name}: {e}")
        self._ts = time.time()
        return len(self._r)

    def _refresh(self):
        if time.time() - self._ts > 5:
            self.load()

    def all(self, scope: str = "global") -> List[Rule]:
        self._refresh()
        return sorted(
            [r for r in self._r.values()
             if r.scope == "global" or r.scope == scope],
            key=lambda r: -r.priority,
        )

    def get(self, rid: str) -> Optional[Rule]:
        self._refresh()
        return self._r.get(rid)

    def save(self, rule: Rule) -> Path:
        safe = re.sub(r"[^\w-]", "_", rule.name.lower())[:36]
        p = S.RULES_DIR / f"{rule.id}_{safe}.yaml"
        p.write_text(rule.to_yaml(), "utf-8")
        self._r[rule.id] = rule
        log.info(f"[rules] saved {p.name}")
        return p

    def deactivate(self, rid: str) -> bool:
        r = self.get(rid)
        if not r:
            return False
        r.active = False
        self.save(r)
        del self._r[rid]
        return True

    def stats(self) -> Dict:
        self._refresh()
        rs = list(self._r.values())
        return {
            "total": len(rs),
            "by_action": {
                a: sum(1 for r in rs if r.action == a)
                for a in ("block", "warn", "escalate", "log_only")
            },
            "by_source": {
                s: sum(1 for r in rs if r.source == s)
                for s in ("intercepted", "natural_language", "manual", "api", "seed")
            },
        }


# ══════════════════════════════════════════════════════════════════════════════
# CRYPTOGRAPHY
# ══════════════════════════════════════════════════════════════════════════════

class Crypto:
    @staticmethod
    def sign(d: Dict) -> str:
        payload = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(
            (S.SECRET_KEY + ":" + payload).encode()
        ).hexdigest()

    @staticmethod
    def chain(prev: str, rec: Dict) -> str:
        payload = json.dumps(
            {"prev": prev, "rec": rec}, sort_keys=True, default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def rid() -> str:
        return "req_" + uuid.uuid4().hex[:16]


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 6 — LEDGER  (SQLite, immutable chain)
# ══════════════════════════════════════════════════════════════════════════════

class Ledger:
    def __init__(self):
        self._c: Optional[aiosqlite.Connection] = None
        self._prev = "GENESIS"
        self._sse: Dict[str, List[asyncio.Queue]] = defaultdict(list)

    async def init(self):
        self._c = await aiosqlite.connect(S.DB_PATH)
        self._c.row_factory = aiosqlite.Row
        await self._c.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                action     TEXT NOT NULL,
                context    TEXT DEFAULT '',
                scope      TEXT DEFAULT 'global',
                verdict    TEXT NOT NULL,
                score      INTEGER NOT NULL,
                risk       TEXT NOT NULL,
                reason     TEXT NOT NULL,
                rule_id    TEXT DEFAULT '',
                rule_name  TEXT DEFAULT '',
                layer      TEXT NOT NULL,
                message    TEXT DEFAULT '',
                request_id TEXT DEFAULT '',
                factors    TEXT DEFAULT '{}',
                prev_hash  TEXT NOT NULL,
                own_hash   TEXT NOT NULL,
                latency_ms INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await self._c.execute("""
            CREATE TABLE IF NOT EXISTS anomalies (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                type       TEXT NOT NULL,
                severity   TEXT NOT NULL,
                message    TEXT NOT NULL,
                data       TEXT DEFAULT '{}',
                resolved   INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await self._c.commit()
        row = await (await self._c.execute(
            "SELECT own_hash FROM entries ORDER BY id DESC LIMIT 1"
        )).fetchone()
        if row:
            self._prev = row["own_hash"]
        log.info(f"[ledger] {S.DB_PATH} | chain tip: {self._prev[:16]}...")

    async def record(
        self,
        agent: str,
        action: str,
        verdict: str,
        score: int,
        reason: str,
        rule_id: str = "",
        rule_name: str = "",
        layer: str = "default",
        message: str = "",
        context: str = "",
        scope: str = "global",
        rid: str = "",
        ms: int = 0,
        factors: Optional[Dict] = None,
    ) -> int:
        rec = {
            "agent": agent,
            "action": action[:200],
            "verdict": verdict,
            "score": score,
            "ts": _now(),
        }
        own = Crypto.chain(self._prev, rec)
        risk = _risk(score)
        async with self._c.execute(
            """INSERT INTO entries
               (agent_name,action,context,scope,verdict,score,risk,reason,
                rule_id,rule_name,layer,message,request_id,factors,
                prev_hash,own_hash,latency_ms,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                agent, action[:2000], context[:500], scope, verdict, score, risk,
                reason[:300], rule_id, rule_name, layer, message[:300], rid,
                json.dumps(factors or {}), self._prev, own, ms, _now(),
            ),
        ):
            pass
        await self._c.commit()
        self._prev = own
        row = await (await self._c.execute("SELECT last_insert_rowid()")).fetchone()
        entry_id = row[0]
        await self._sse_push(agent, {
            "type": "validation",
            "entry_id": entry_id,
            "agent": agent,
            "verdict": verdict,
            "score": score,
            "reason": reason[:100],
            "ms": ms,
            "ts": _now(),
        })
        return entry_id

    async def recent(self, agent: str = "", limit: int = 50) -> List[Dict]:
        if agent:
            rows = await (await self._c.execute(
                "SELECT * FROM entries WHERE agent_name=? ORDER BY id DESC LIMIT ?",
                (agent, limit),
            )).fetchall()
        else:
            rows = await (await self._c.execute(
                "SELECT * FROM entries ORDER BY id DESC LIMIT ?", (limit,)
            )).fetchall()
        return [dict(r) for r in rows]

    async def stats(self, agent: str = "") -> Dict:
        where = "WHERE agent_name=?" if agent else ""
        params = (agent,) if agent else ()
        row = await (await self._c.execute(
            f"""SELECT
                COUNT(*) total,
                SUM(verdict='APPROVED')  approved,
                SUM(verdict='BLOCKED')   blocked,
                SUM(verdict='ESCALATED') escalated,
                SUM(verdict='DUPLICATE') duplicates,
                SUM(verdict='WARNED')    warned,
                AVG(score) avg_score,
                COUNT(DISTINCT agent_name) agents
            FROM entries {where}""",
            params,
        )).fetchone()
        return dict(row) if row else {}

    async def timeline(self, agent: str = "", hours: int = 24) -> List[Dict]:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        where_extra = "AND agent_name=?" if agent else ""
        params = (since, agent) if agent else (since,)
        rows = await (await self._c.execute(
            f"""SELECT
                substr(created_at,1,13) hr,
                COUNT(*) total,
                SUM(verdict='APPROVED') approved,
                SUM(verdict='BLOCKED')  blocked,
                CAST(AVG(score) AS INTEGER) avg_score
            FROM entries
            WHERE created_at > ? {where_extra}
            GROUP BY hr ORDER BY hr ASC""",
            params,
        )).fetchall()
        return [dict(r) for r in rows]

    async def check_dup(
        self, agent: str, action: str,
        window: int = 60, thr: float = 0.82,
    ) -> Optional[Dict]:
        since = (datetime.now(timezone.utc) - timedelta(minutes=window)).isoformat()
        rows = await (await self._c.execute(
            """SELECT id, action FROM entries
               WHERE agent_name=? AND verdict='APPROVED' AND created_at>?
               ORDER BY id DESC LIMIT 50""",
            (agent, since),
        )).fetchall()
        for row in rows:
            s = _jac(action, row["action"])
            if s >= thr:
                return {
                    "entry_id": row["id"],
                    "action": row["action"],
                    "similarity": round(s, 3),
                }
        return None

    async def log_anomaly(
        self, agent: str, atype: str, severity: str,
        message: str, data: Optional[Dict] = None,
    ) -> bool:
        # Deduplicate — skip if same anomaly logged in last 30 min
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        ex = await (await self._c.execute(
            "SELECT id FROM anomalies WHERE agent_name=? AND type=? AND created_at>? LIMIT 1",
            (agent, atype, cutoff),
        )).fetchone()
        if ex:
            return False
        await self._c.execute(
            "INSERT INTO anomalies(agent_name,type,severity,message,data,created_at) VALUES(?,?,?,?,?,?)",
            (agent, atype, severity, message[:300], json.dumps(data or {}), _now()),
        )
        await self._c.commit()
        log.warning(f"[anomaly] {severity.upper()} {agent}: {message}")
        await self._sse_push(agent, {
            "type": "anomaly",
            "agent": agent,
            "anomaly_type": atype,
            "severity": severity,
            "message": message,
            "ts": _now(),
        })
        return True

    # ── SSE ────────────────────────────────────────────────────────────────────
    def sse_subscribe(self, key: str = "all") -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._sse[key].append(q)
        return q

    def sse_unsubscribe(self, key: str, q: asyncio.Queue):
        try:
            self._sse[key].remove(q)
        except ValueError:
            pass

    async def _sse_push(self, agent: str, event: Dict):
        for key in (agent, "all"):
            dead = []
            for q in self._sse.get(key, []):
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                try:
                    self._sse[key].remove(q)
                except ValueError:
                    pass


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-MODEL LLM CLIENT
# All providers. Returns None on any failure — never blocks the agent.
# ══════════════════════════════════════════════════════════════════════════════

class LLM:
    async def complete(
        self, prompt: str, system: str = "", max_tokens: int = 400
    ) -> Optional[str]:
        if not S.LLM_API_KEY:
            return None
        try:
            return await asyncio.wait_for(
                self._call(prompt, system, max_tokens), S.LLM_TIMEOUT
            )
        except Exception as e:
            log.debug(f"[llm] {type(e).__name__}: {e}")
            return None

    async def _call(
        self, prompt: str, system: str, max_tokens: int
    ) -> Optional[str]:
        p = S.LLM_PROVIDER
        k = S.LLM_API_KEY
        m = S.LLM_MODEL

        async with httpx.AsyncClient(timeout=S.LLM_TIMEOUT) as c:

            # ── Anthropic ────────────────────────────────────────────────────
            if p == "anthropic":
                body: Dict = {
                    "model": re.sub(r"^[a-z]+/", "", m),
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if system:
                    body["system"] = system
                r = await c.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": k,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                r.raise_for_status()
                return r.json()["content"][0]["text"].strip()

            # ── Gemini ───────────────────────────────────────────────────────
            if p == "gemini":
                mc = re.sub(r"^[a-z]+/", "", m)
                body2: Dict = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": 0.1,
                    },
                }
                if system:
                    body2["systemInstruction"] = {"parts": [{"text": system}]}
                r = await c.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{mc}:generateContent?key={k}",
                    json=body2,
                )
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # ── Ollama ───────────────────────────────────────────────────────
            if p == "ollama":
                base = (S.LLM_BASE_URL or "http://localhost:11434").rstrip("/")
                msgs = (
                    [{"role": "system", "content": system}] if system else []
                ) + [{"role": "user", "content": prompt}]
                r = await c.post(
                    f"{base}/api/chat",
                    json={
                        "model": m, "messages": msgs,
                        "stream": False, "options": {"temperature": 0.1},
                    },
                )
                r.raise_for_status()
                return r.json()["message"]["content"].strip()

            # ── OpenAI-compatible (OpenAI / OpenRouter / Groq / xAI /
            #    Mistral / DeepSeek / OpenClaw) ─────────────────────────────
            URL_MAP = {
                "openai":     "https://api.openai.com/v1/chat/completions",
                "openrouter": "https://openrouter.ai/api/v1/chat/completions",
                "groq":       "https://api.groq.com/openai/v1/chat/completions",
                "xai":        "https://api.x.ai/v1/chat/completions",
                "mistral":    "https://api.mistral.ai/v1/chat/completions",
                "deepseek":   "https://api.deepseek.com/v1/chat/completions",
                "openclaw":   (S.LLM_BASE_URL or "http://localhost:1234/v1")
                              + "/chat/completions",
            }
            url = URL_MAP.get(p, URL_MAP["openai"])
            mc2 = re.sub(r"^[a-z]+/", "", m)
            msgs2 = (
                [{"role": "system", "content": system}] if system else []
            ) + [{"role": "user", "content": prompt}]
            r = await c.post(
                url,
                headers={
                    "Authorization": f"Bearer {k}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": mc2,
                    "messages": msgs2,
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()


# ══════════════════════════════════════════════════════════════════════════════
# VERDICT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Verdict:
    result:       str           # APPROVED | BLOCKED | WARNED | ESCALATED | DUPLICATE
    score:        int           # 0-100
    rule_id:      Optional[str]
    rule_name:    Optional[str]
    reason:       str
    message:      str
    action:       str
    layer:        str           # deterministic | heuristic | semantic | duplicate | default
    ms:           int
    notify:       List[str]
    factors:      Dict          = field(default_factory=dict)
    duplicate_of: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def blocked(self) -> bool:
        return self.result in ("BLOCKED", "ESCALATED")


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — DETERMINISTIC VALIDATOR
# Zero LLM. Zero network. Zero uncertainty.
# ══════════════════════════════════════════════════════════════════════════════

class L1:
    def __init__(self, engine: RuleEngine):
        self.engine = engine

    def check(self, text: str, scope: str = "global") -> Optional[Verdict]:
        t0 = time.time()
        lo = (text or "").lower()
        for rule in self.engine.all(scope):
            trigger = self._match(rule, lo)
            if trigger is None:
                continue
            verdict_map = {
                "block":    "BLOCKED",
                "warn":     "WARNED",
                "escalate": "ESCALATED",
                "log_only": "APPROVED",
            }
            result = verdict_map.get(rule.action, "BLOCKED")
            # For keyword_warn triggers, force WARNED regardless of action field
            if trigger.startswith("warn:"):
                result = "WARNED"
            score = {
                "BLOCKED": 8, "WARNED": 58,
                "ESCALATED": 35, "APPROVED": 82,
            }.get(result, 8)
            return Verdict(
                result=result,
                score=score,
                rule_id=rule.id,
                rule_name=rule.name,
                reason=f'Rule "{rule.name}" triggered [{trigger}]',
                message=rule.message,
                action=rule.action,
                layer="deterministic",
                ms=int((time.time() - t0) * 1000),
                notify=rule.notify,
            )
        return None

    def _match(self, rule: Rule, lo: str) -> Optional[str]:
        for kw in rule.keywords_block:
            if kw.lower() in lo:
                return f"keyword_block:{kw}"
        for pat in rule.regex_block:
            try:
                if re.search(pat, lo, re.IGNORECASE):
                    return f"regex:{pat[:30]}"
            except re.error:
                pass
        for ph in rule.exact_block:
            if ph.lower() == lo.strip():
                return f"exact:{ph[:30]}"
        if rule.max_amount is not None:
            for a in re.findall(r"\$?\s*(\d[\d,.]*)", lo):
                try:
                    v = float(a.replace(",", ""))
                    if v > rule.max_amount:
                        return f"amount:{v}>{rule.max_amount}"
                except ValueError:
                    pass
        for kw in rule.keywords_warn:
            if kw.lower() in lo:
                return f"warn:{kw}"
        return None


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — HEURISTIC SCORING  (no LLM)
# Ported and improved from main.py ScoringEngine.
# Used when token can_do/cannot_do lists are provided.
# ══════════════════════════════════════════════════════════════════════════════

_HR_ES = [
    "eliminar", "borrar", "cancelar", "modificar", "alterar",
    "deshabilitar", "terminar", "destruir", "revocar", "suspender",
    "desactivar", "anular", "suprimir", "truncar",
]
_HR_EN = [
    "delete", "remove", "cancel", "modify", "override", "disable",
    "terminate", "destroy", "drop", "purge", "revoke", "deactivate",
    "wipe", "truncate", "kill",
]
_SENS_RE = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)[\"\'\s:=]+[\w-]{8,}"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
]
_STOP = {
    "para", "todos", "todas", "desde", "hasta", "entre", "sobre",
    "with", "from", "that", "this", "have", "will", "been", "more",
    "than", "when", "what", "which", "there", "their", "would",
}


class L2:
    @staticmethod
    def score(
        action: str, can_do: List[str], cannot_do: List[str]
    ) -> Tuple[int, str, Dict]:
        lo = action.lower()
        factors: Dict[str, int] = {}

        # 1. Sensitive data in action text
        if any(p.search(action) for p in _SENS_RE):
            factors["sensitive_data_detected"] = -15

        # 2. High-risk verb analysis
        for verb in _HR_ES + _HR_EN:
            if verb not in lo:
                continue
            # Verb explicitly forbidden
            for rule in cannot_do:
                if verb in rule.lower():
                    factors["high_risk_verb_forbidden"] = -70
                    return 12, f'High-risk "{verb}" violates "{rule[:50]}"', factors
            # Verb not explicitly allowed either
            if not any(verb in r.lower() for r in can_do):
                factors["high_risk_verb_not_authorized"] = -50
                return 32, f'High-risk "{verb}" not explicitly authorized', factors
            factors["high_risk_verb_authorized"] = 10

        # 3. Numeric limit check
        action_nums: List[float] = []
        for n in re.findall(r"\d[\d,]*(?:\.\d+)?", lo):
            try:
                action_nums.append(float(n.replace(",", "")))
            except ValueError:
                pass
        for rule in cannot_do:
            m = re.search(r">\s*\$?\s*(\d[\d,.]*)", rule.lower())
            if m:
                try:
                    limit = float(m.group(1).replace(",", ""))
                    if any(n > limit for n in action_nums):
                        factors["exceeds_numeric_limit"] = -80
                        return 8, f'Exceeds limit {limit} in rule "{rule[:40]}"', factors
                except ValueError:
                    pass

        # 4. Forbidden rule keyword match
        for rule in cannot_do:
            kws = [
                w for w in set(re.findall(r"\w+", rule.lower()))
                if len(w) > 4 and w not in _STOP
            ]
            if not kws:
                continue
            hits = sum(1 for kw in kws if kw in lo)
            if (hits >= 1 and len(kws) <= 3) or hits >= 2:
                factors["forbidden_rule_keyword_match"] = -60
                return 18, f'Matches forbidden rule "{rule[:50]}"', factors

        # 5. Allowed rule match
        best_rule: Optional[str] = None
        best_ratio = 0.0
        for rule in can_do:
            kws = [
                w for w in set(re.findall(r"\w+", rule.lower())) if len(w) > 4
            ]
            if not kws:
                continue
            ratio = sum(1 for kw in kws if kw in lo) / len(kws)
            if ratio > best_ratio:
                best_ratio, best_rule = ratio, rule

        if best_rule and best_ratio >= 0.3:
            s = int(70 + best_ratio * 25)
            factors["allowed_rule_match"] = int(20 + best_ratio * 60)
            return s, f'Aligned with "{best_rule[:50]}"', factors

        factors["no_clear_match"] = 0
        return 55, "No clear rule match — escalating for review", factors


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — SEMANTIC VALIDATOR  (optional LLM)
# Only runs when a rule has sem_enabled=true and L1+L2 passed.
# Fail-open: returns None if LLM unavailable.
# ══════════════════════════════════════════════════════════════════════════════

class L3:
    def __init__(self, engine: RuleEngine, llm: LLM):
        self.engine = engine
        self.llm    = llm

    async def check(self, text: str, scope: str = "global") -> Optional[Verdict]:
        sem_rules = [r for r in self.engine.all(scope) if r.sem_enabled]
        if not sem_rules:
            return None
        t0 = time.time()
        descs = "\n".join(
            f"  {i+1}. id={r.id} — {r.sem_description or r.name}"
            for i, r in enumerate(sem_rules[:6])
        )
        thr = min(r.sem_threshold for r in sem_rules)
        prompt = (
            f'Agent action: "{text[:500]}"\n\n'
            f"Rules to check:\n{descs}\n\n"
            "Does this action violate any rule?\n"
            'Reply ONLY valid JSON: '
            '{"violates":true/false,"rule_id":"id_or_null",'
            '"confidence":0.0-1.0,"reason":"brief one sentence"}'
        )
        raw = await self.llm.complete(
            prompt, system="Governance validator. Be strict. JSON only."
        )
        if not raw:
            return None
        d = _parse_json(raw)
        if not d or not d.get("violates"):
            return None
        confidence = float(d.get("confidence", 0))
        if confidence < thr:
            return None
        rule = self.engine.get(d.get("rule_id", ""))
        result = "BLOCKED" if (rule and rule.action == "block") else "WARNED"
        score  = int((1 - confidence) * 40)
        reason = "Semantic: " + str(d.get("reason", "")) + \
                 " (" + str(round(confidence * 100)) + "%)"
        return Verdict(
            result=result,
            score=score,
            rule_id=d.get("rule_id"),
            rule_name=rule.name if rule else None,
            reason=reason,
            message=rule.message if rule else "Bloqueado por revisión semántica.",
            action=rule.action if rule else "block",
            layer="semantic",
            ms=int((time.time() - t0) * 1000),
            notify=rule.notify if rule else [],
        )


# ══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE ENGINE — orchestrates L1 + L2 + L3 + duplicate check
# ══════════════════════════════════════════════════════════════════════════════

class Gov:
    def __init__(self, engine: RuleEngine, ledger: Ledger, llm: LLM):
        self.l1     = L1(engine)
        self.l2     = L2()
        self.l3     = L3(engine, llm)
        self.ledger = ledger
        self.engine = engine

    async def validate(
        self,
        action:     str,
        scope:      str              = "global",
        context:    str              = "",
        agent_name: str              = "",
        can_do:     Optional[List[str]] = None,
        cannot_do:  Optional[List[str]] = None,
        check_dups: bool             = True,
        dry_run:    bool             = False,
    ) -> Verdict:
        t0  = time.time()
        rid = Crypto.rid()

        # ── Duplicate check ────────────────────────────────────────────────────
        if check_dups and agent_name:
            dup = await self.ledger.check_dup(
                agent_name, action, S.DEDUP_WINDOW, S.DEDUP_THRESHOLD
            )
            if dup:
                v = Verdict(
                    result="DUPLICATE",
                    score=100,
                    rule_id=None,
                    rule_name=None,
                    reason=(
                        "Duplicate of entry #" + str(dup["entry_id"]) +
                        " (" + str(round(dup["similarity"] * 100)) + "%)"
                    ),
                    message="",
                    action="allow",
                    layer="duplicate",
                    ms=int((time.time() - t0) * 1000),
                    notify=[],
                    duplicate_of=dup,
                )
                if not dry_run:
                    await self._record(v, action, context, scope, agent_name, rid)
                return v

        # ── L1: deterministic ──────────────────────────────────────────────────
        v = self.l1.check(action, scope)
        if v:
            if not dry_run:
                await self._record(v, action, context, scope, agent_name, rid)
            return v

        # ── L2: heuristic (only when token rules provided) ─────────────────────
        if can_do is not None or cannot_do is not None:
            sc, reason, factors = self.l2.score(
                action, can_do or [], cannot_do or []
            )
            if sc < S.SCORE_BLOCK:
                result = "BLOCKED"
            elif sc < S.SCORE_ESCALATE:
                result = "ESCALATED"
            else:
                result = "APPROVED"

            if result != "APPROVED":
                v = Verdict(
                    result=result,
                    score=sc,
                    rule_id=None,
                    rule_name=None,
                    reason=reason,
                    message="",
                    action=result.lower(),
                    layer="heuristic",
                    ms=int((time.time() - t0) * 1000),
                    notify=[],
                    factors=factors,
                )
                if not dry_run:
                    await self._record(
                        v, action, context, scope, agent_name, rid, factors
                    )
                return v

        # ── L3: semantic ───────────────────────────────────────────────────────
        if S.LLM_API_KEY:
            v = await self.l3.check(action, scope)
            if v:
                if not dry_run:
                    await self._record(v, action, context, scope, agent_name, rid)
                return v

        # ── Default: APPROVED ──────────────────────────────────────────────────
        v = Verdict(
            result="APPROVED",
            score=95,
            rule_id=None,
            rule_name=None,
            reason="No governance rule triggered",
            message="",
            action="allow",
            layer="default",
            ms=int((time.time() - t0) * 1000),
            notify=[],
        )
        if not dry_run:
            await self._record(v, action, context, scope, agent_name, rid)
        return v

    async def _record(
        self,
        v: Verdict,
        action: str,
        context: str,
        scope: str,
        agent: str,
        rid: str,
        factors: Optional[Dict] = None,
    ):
        if not agent:
            return
        await self.ledger.record(
            agent=agent,
            action=action,
            verdict=v.result,
            score=v.score,
            reason=v.reason,
            rule_id=v.rule_id or "",
            rule_name=v.rule_name or "",
            layer=v.layer,
            message=v.message,
            context=context,
            scope=scope,
            rid=rid,
            ms=v.ms,
            factors=factors or v.factors,
        )


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 7 — ANOMALY DETECTOR
# block-rate / burst / score-degradation — deduped per 30 min
# ══════════════════════════════════════════════════════════════════════════════

class Anomaly:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    async def run(self, agent: str):
        await asyncio.gather(
            self._block_rate(agent),
            self._burst(agent),
            self._score_degradation(agent),
            return_exceptions=True,
        )

    async def _block_rate(self, agent: str):
        rows = await self.ledger.recent(agent, 100)
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        recent = [r for r in rows if r.get("created_at", "") > cutoff]
        if len(recent) < 5:
            return
        blocked = sum(1 for r in recent if r["verdict"] == "BLOCKED")
        rate = blocked / len(recent)
        if rate >= S.ANOMALY_BLOCKRT:
            await self.ledger.log_anomaly(
                agent, "high_block_rate", "high",
                f"Block rate {rate:.0%} in last 30 min ({blocked}/{len(recent)})",
                {"rate": rate, "sample_size": len(recent)},
            )

    async def _burst(self, agent: str):
        rows = await self.ledger.recent(agent, 100)
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        n = sum(1 for r in rows if r.get("created_at", "") > cutoff)
        if n >= S.ANOMALY_BURST:
            await self.ledger.log_anomaly(
                agent, "burst_activity", "medium",
                f"Burst: {n} actions in 5 minutes",
                {"count": n},
            )

    async def _score_degradation(self, agent: str):
        """Flag if average score dropped > ANOMALY_DROP points over last 50 entries."""
        rows = await self.ledger.recent(agent, 50)
        filtered = [r for r in rows if r["verdict"] != "DUPLICATE"]
        if len(filtered) < 10:
            return
        mid = len(filtered) // 2
        old_avg = sum(r["score"] for r in filtered[:mid]) / mid
        new_avg = sum(r["score"] for r in filtered[mid:]) / (len(filtered) - mid)
        drop = old_avg - new_avg
        if drop >= S.ANOMALY_DROP:
            await self.ledger.log_anomaly(
                agent, "score_degradation", "medium",
                f"Score drop {drop:.1f} pts ({old_avg:.0f} -> {new_avg:.0f})",
                {
                    "old_avg": round(old_avg, 1),
                    "new_avg": round(new_avg, 1),
                    "drop": round(drop, 1),
                },
            )


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — CONVERSATION INTERCEPTOR
# Detects governance instructions in any message.
# "no hagas X" → rule auto-created in nova_rules/ silently.
# The agent never knows.
# ══════════════════════════════════════════════════════════════════════════════

_INTERCEPT_PATTERNS = [
    # Spanish — prohibitions
    re.compile(r"no\s+(hagas?|puedes?|debes?|pued[ae]s?)\s+(.{5,150})", re.I),
    re.compile(r"nunca\s+(hagas?|digas?|compartas?|env[íi]es?|prometas?|ofrezcas?)\s+(.{5,150})", re.I),
    re.compile(r"est[áa]\s+prohibid[ao]\s+(.{5,120})", re.I),
    re.compile(r"prohibid[ao]\s+(.{5,120})", re.I),
    re.compile(r"no\s+est[áa]s?\s+autorizado?\s+(?:para\s+)?(.{5,100})", re.I),
    re.compile(r"bajo\s+ninguna\s+circunstancia\s+(.{5,150})", re.I),
    re.compile(r"si\s+alguien\s+(?:te\s+)?pide?\s+(.{5,100}),?\s+(?:rechaza|niega|ignora|bloquea)", re.I),
    # Spanish — explicit rule creation
    re.compile(r"(?:nueva\s+)?regla:\s+(.{5,200})", re.I),
    re.compile(r"pol[íi]tica:\s+(.{5,200})", re.I),
    re.compile(r"agrega?\s+(?:esta\s+)?regla\s+(?:de\s+)?(?:que\s+)?(.{5,200})", re.I),
    # English — prohibitions
    re.compile(r"never\s+(?:do|say|share|send|give|promise|commit|allow)\s+(.{5,150})", re.I),
    re.compile(r"don'?t\s+(?:do|say|share|send|allow|make|promise|give)\s+(.{5,150})", re.I),
    re.compile(r"you\s+(?:are\s+not|cannot|must\s+not)\s+(?:allowed\s+to\s+)?(.{5,100})", re.I),
    # English — explicit rule creation
    re.compile(r"rule:\s+(.{5,200})", re.I),
    re.compile(r"policy:\s+(.{5,200})", re.I),
    re.compile(r"forbidden\s+to\s+(.{5,100})", re.I),
    re.compile(r"always\s+refuse\s+(?:to\s+)?(.{5,100})", re.I),
]


class Interceptor:
    def __init__(self, engine: RuleEngine, llm: LLM):
        self.engine = engine
        self.llm    = llm

    def detect(self, text: str) -> Optional[str]:
        for pat in _INTERCEPT_PATTERNS:
            m = pat.search(text)
            if m:
                groups = [g for g in m.groups() if g]
                return groups[-1].strip() if groups else m.group(0).strip()
        return None

    async def process(
        self, message: str, sender: str = "admin", scope: str = "global"
    ) -> Optional[Rule]:
        inst = self.detect(message)
        if not inst:
            return None
        enriched = await self._enrich(message, inst)
        rule = Rule.from_dict({
            "id":            "r" + secrets.token_hex(4),
            "name":          enriched.get("name", "Auto: " + inst[:40]),
            "created_at":    _now(),
            "created_by":    sender,
            "source":        "intercepted",
            "original_instruction": message[:500],
            "active":        True,
            "priority":      int(enriched.get("priority", 7)),
            "scope":         scope,
            "deterministic": {
                "keywords_block": enriched.get("keywords_block", []),
                "keywords_warn":  enriched.get("keywords_warn", []),
                "regex_block":    enriched.get("regex_block", []),
                "exact_block":    [],
                "max_amount":     None,
            },
            "semantic": {
                "enabled":     False,
                "description": "",
                "threshold":   0.82,
            },
            "action":      enriched.get("action", "block"),
            "message":     enriched.get("message", "No autorizado: " + inst[:80]),
            "escalate_to": "",
            "log":         True,
            "notify":      [],
        })
        self.engine.save(rule)
        log.info(f'[interceptor] rule "{rule.name}" created | scope={scope}')
        return rule

    async def _enrich(self, full: str, inst: str) -> Dict:
        fallback = {
            "name":           "Auto: " + inst[:42],
            "keywords_block": [w.lower() for w in inst.split() if len(w) > 3][:5],
            "keywords_warn":  [],
            "regex_block":    [],
            "action":         "block",
            "message":        "No puedo hacer eso: " + inst[:80],
            "priority":       7,
        }
        if not S.LLM_API_KEY:
            return fallback
        prompt = (
            'Admin instruction: "' + full[:400] + '"\n'
            'Prohibition: "' + inst + '"\n\n'
            "Extract governance rule. Reply ONLY JSON:\n"
            '{"name":"short rule name (max 8 words)",'
            '"keywords_block":["exact phrases to match and block"],'
            '"keywords_warn":[],"regex_block":[],"action":"block",'
            '"priority":7,"message":"response in same language as instruction"}'
        )
        raw = await self.llm.complete(
            prompt, system="Governance rule extractor. Specific keywords. JSON only."
        )
        if not raw:
            return fallback
        d = _parse_json(raw)
        return d if d else fallback


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 5 — NOVA CHAT
# Natural language governance management.  WebSocket + HTTP.
# ══════════════════════════════════════════════════════════════════════════════

_CHAT_SYSTEM = """You are Nova, an AI governance layer for agents.
Answer in the EXACT SAME LANGUAGE as the user (Spanish or English).
Reply ONLY with valid JSON — no prose, no markdown fences.

INTENT MAPPING:
- Create/add a rule    → {"intent":"create_rule","instruction":"the prohibition in user words","action":"block|warn","priority":7}
- List/show rules      → {"intent":"list_rules"}
- Validate an action   → {"intent":"validate","text":"action text to validate"}
- Delete/remove rule   → {"intent":"delete_rule","rule_id":"the_id"}
- Stats/overview       → {"intent":"stats"}
- Ledger/history       → {"intent":"ledger","limit":20}
- Help or anything else → {"intent":"chat","message":"your concise answer in user language"}

EXAMPLES:
User: "crea una regla que bloquee descuentos mayores al 20%"
→ {"intent":"create_rule","instruction":"no ofrezcas descuentos mayores al 20%","action":"block","priority":8}

User: "never share patient phone numbers"
→ {"intent":"create_rule","instruction":"never share patient phone numbers","action":"block","priority":9}

User: "muéstrame todas las reglas"  → {"intent":"list_rules"}
User: "¿cuántas acciones bloqueadas?"  → {"intent":"stats"}
User: "valida: dar 30% de descuento"  → {"intent":"validate","text":"dar 30% de descuento"}
"""


class Chat:
    def __init__(
        self,
        engine:      RuleEngine,
        gov:         Gov,
        interceptor: Interceptor,
        ledger:      Ledger,
        llm:         LLM,
    ):
        self.engine      = engine
        self.gov         = gov
        self.interceptor = interceptor
        self.ledger      = ledger
        self.llm         = llm
        self._history: Dict[str, List[Dict]] = {}

    async def send(
        self, text: str, session: str = "default", scope: str = "global"
    ) -> Dict:
        t0 = time.time()
        h  = self._history.setdefault(session, [])

        history_ctx = "\n".join(
            m["role"].upper() + ": " + m["content"][:120]
            for m in h[-6:]
        )
        prompt = (
            ("HISTORY:\n" + history_ctx + "\n\n" if history_ctx else "") +
            "USER: " + text
        )

        raw = await self.llm.complete(
            prompt, system=_CHAT_SYSTEM, max_tokens=400
        )
        if not raw:
            return {
                "type": "error",
                "message": "LLM not available. Check NOVA_LLM_API_KEY in .env.",
                "ms": 0,
            }

        parsed = _parse_json(raw) or {"intent": "chat", "message": raw}
        result = await self._handle(parsed, text, scope)
        result["ms"] = int((time.time() - t0) * 1000)

        h.append({"role": "user",      "content": text})
        h.append({"role": "assistant",  "content": result.get("message", "")})
        if len(h) > 20:
            self._history[session] = h[-20:]

        return result

    async def _handle(
        self, d: Dict, original: str, scope: str
    ) -> Dict:
        intent = d.get("intent", "chat")

        # ── Create rule ────────────────────────────────────────────────────────
        if intent == "create_rule":
            inst   = d.get("instruction", original)
            action = d.get("action", "block")
            prio   = int(d.get("priority", 7))
            rule   = await self.interceptor.process(
                "regla: " + inst, sender="nova_chat", scope=scope
            )
            if rule:
                rule.action   = action
                rule.priority = prio
                self.engine.save(rule)
                return {
                    "type":    "rule_created",
                    "rule_id": rule.id,
                    "message": (
                        "Regla creada: **" + rule.name + "**\n"
                        "Acción: `" + rule.action + "` | "
                        "Prioridad: " + str(rule.priority) + "\n"
                        "Archivo: `nova_rules/" + rule.id + ".yaml`"
                    ),
                }
            return {
                "type": "error",
                "message": "No pude crear la regla. Descríbela más específicamente.",
            }

        # ── List rules ─────────────────────────────────────────────────────────
        if intent == "list_rules":
            rules = self.engine.all(scope)
            if not rules:
                return {
                    "type": "list",
                    "message": "No hay reglas activas. Puedes crear una con lenguaje natural.",
                    "rules": [],
                }
            lines = "\n".join(
                "  `" + r.id + "` **" + r.name + "** — " +
                r.action + " | prio=" + str(r.priority) + " | " + r.source
                for r in rules[:20]
            )
            return {
                "type":    "list",
                "message": str(len(rules)) + " reglas activas:\n" + lines,
                "rules":   [r.to_dict() for r in rules],
            }

        # ── Validate ───────────────────────────────────────────────────────────
        if intent == "validate":
            v = await self.gov.validate(d.get("text", original), scope)
            emoji_map = {
                "APPROVED":  "✓",
                "BLOCKED":   "✗",
                "WARNED":    "⚠",
                "ESCALATED": "↑",
                "DUPLICATE": "⊘",
            }
            emoji = emoji_map.get(v.result, "?")
            return {
                "type":         "validation",
                "verdict":      v.result,
                "score":        v.score,
                "message": (
                    emoji + " **" + v.result + "** "
                    "(score=" + str(v.score) + ")\n" + v.reason
                ),
                "verdict_data": v.to_dict(),
            }

        # ── Delete rule ────────────────────────────────────────────────────────
        if intent == "delete_rule":
            rid = d.get("rule_id", "")
            if self.engine.deactivate(rid):
                return {
                    "type":    "rule_deleted",
                    "message": "Regla `" + rid + "` desactivada y archivada.",
                }
            return {
                "type":    "error",
                "message": "No encontré `" + rid + "`. Usa 'ver reglas' para listarlas.",
            }

        # ── Stats ──────────────────────────────────────────────────────────────
        if intent == "stats":
            ls = await self.ledger.stats()
            rs = self.engine.stats()
            total    = str(ls.get("total", 0))
            approved = str(ls.get("approved", 0))
            blocked  = str(ls.get("blocked", 0))
            escalated = str(ls.get("escalated", 0))
            n_rules  = str(rs["total"])
            return {
                "type": "stats",
                "message": (
                    "**Ledger:** " + total + " acciones | "
                    "✓ " + approved + " aprobadas | "
                    "✗ " + blocked + " bloqueadas | "
                    "↑ " + escalated + " escaladas\n"
                    "**Reglas:** " + n_rules + " activas"
                ),
                "ledger": ls,
                "rules":  rs,
            }

        # ── Ledger ─────────────────────────────────────────────────────────────
        if intent == "ledger":
            limit   = int(d.get("limit", 20))
            entries = await self.ledger.recent(limit=min(limit, 50))
            lines   = "\n".join(
                "  [" + str(e["verdict"]) + "] " +
                str(e["agent_name"]) + " — " +
                str(e["action"])[:60] +
                " (score=" + str(e["score"]) + ")"
                for e in entries[:10]
            )
            return {
                "type":    "ledger",
                "message": (
                    "Últimas " + str(len(entries)) + " entradas:\n" + lines
                ),
                "entries": entries,
            }

        # ── Chat fallback ──────────────────────────────────────────────────────
        return {"type": "chat", "message": d.get("message", "")}


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 8 — TRANSPARENT PROXY
# Nova sits in front of the agent. Agent sees normal requests.
# ══════════════════════════════════════════════════════════════════════════════

class Proxy:
    async def forward(self, request: Request, path: str) -> Response:
        if not S.AGENT_URL:
            raise HTTPException(
                503, "No agent connected. POST /connect first."
            )
        body    = await request.body()
        url     = S.AGENT_URL.rstrip("/") + "/" + path.lstrip("/")
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length")
        }
        async with httpx.AsyncClient(timeout=30.0) as c:
            resp = await c.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )


# ══════════════════════════════════════════════════════════════════════════════
# AGENT DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════

_KNOWN_PORTS = [
    # ── Your agents ────────────────────────────────────────────────────────────
    (8001, "melissa",            "python"),
    (8002, "melissa-alt",        "python"),
    # ── OpenClaw ───────────────────────────────────────────────────────────────
    (18789, "openclaw",          "python"),
    (1234,  "openclaw-legacy",   "python"),
    (11434,"ollama",             "native"),
    # ── Common agentic servers ─────────────────────────────────────────────────
    (5678, "n8n",                "node"),
    (8080, "evolution-api",      "node"),
    (3000, "baileys-bridge",     "node"),
    (8000, "agent-8000",         "python"),
    (8003, "agent-8003",         "python"),
    (8004, "agent-8004",         "python"),
    (3001, "agent-3001",         "node"),
    (3002, "agent-3002",         "node"),
    (9000, "agent-9000",         "unknown"),
    (9002, "nova-api",           "nova"),
]

# CLI agents detected by binary presence (no port needed)
_CLI_AGENTS = {
    "claude":  "claude_code",
    "aider":   "aider",
    "gemini":  "gemini_cli",
    "codex":   "codex_cli",
    "gh":      "copilot_cli",
}


async def scan_agents() -> List[Dict]:
    found = []
    for port, name, runtime in _KNOWN_PORTS:
        s = socket.socket()
        s.settimeout(0.25)
        try:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                found.append({
                    "port":    port,
                    "name":    name,
                    "runtime": runtime,
                    "url":     f"http://localhost:{port}",
                })
        except Exception:
            pass
        finally:
            s.close()
    return found


# ══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER  (in-memory, per API key)
# ══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    def __init__(self):
        self._reqs: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        self._reqs[key] = [t for t in self._reqs[key] if t > now - 60]
        if len(self._reqs[key]) >= S.RATE_LIMIT:
            return False
        self._reqs[key].append(now)
        return True


# ══════════════════════════════════════════════════════════════════════════════
# SEED — default rules on first run
# ══════════════════════════════════════════════════════════════════════════════

_SEEDS: List[Dict] = [
    {
        "id":   "seed_001",
        "name": "No medical diagnoses",
        "source": "seed",
        "priority": 9,
        "scope": "global",
        "original_instruction": "Never give medical diagnoses or health recommendations",
        "deterministic": {
            "keywords_block": [
                "tienes cáncer", "te diagnostico", "definitivamente tienes",
                "you have cancer", "i diagnose you", "padeces de", "sufres de",
            ]
        },
        "action":  "block",
        "message": "Para diagnósticos necesitas hablar directamente con el médico.",
    },
    {
        "id":   "seed_002",
        "name": "No PII of other people",
        "source": "seed",
        "priority": 9,
        "scope": "global",
        "original_instruction": "Never share personal data of other people",
        "deterministic": {
            "keywords_block": [
                "datos del otro paciente", "other patient data",
                "cédula del paciente", "información del otro usuario",
            ]
        },
        "action":  "block",
        "message": "No puedo compartir información personal de otras personas.",
    },
    {
        "id":   "seed_003",
        "name": "No price guarantees",
        "source": "seed",
        "priority": 6,
        "scope": "global",
        "original_instruction": "Warn when making price commitments without verification",
        "deterministic": {
            "keywords_warn": [
                "precio garantizado", "guaranteed price",
                "te garantizo el precio", "sin costo adicional",
            ]
        },
        "action":  "warn",
        "message": "Los precios exactos los confirma el equipo — permíteme verificar.",
    },
    {
        "id":   "seed_004",
        "name": "No raw credentials in actions",
        "source": "seed",
        "priority": 8,
        "scope": "global",
        "original_instruction": "Block actions containing raw API keys or passwords",
        "deterministic": {
            "regex_block": [
                r"(?i)(api[_-]?key|secret|password|token)[\"\'\s:=]+[\w-]{8,}"
            ]
        },
        "action":  "block",
        "message": "No proceso acciones que contengan credenciales o secretos expuestos.",
    },
]


def _seed(engine: RuleEngine):
    if list(S.RULES_DIR.glob("*.yaml")):
        return
    base: Dict = {
        "created_at":  _now(),
        "created_by":  "nova_seed",
        "active":      True,
        "log":         True,
        "notify":      [],
        "escalate_to": "",
        "semantic":    {"enabled": False, "description": "", "threshold": 0.82},
        "message":     "",
    }
    for d in _SEEDS:
        engine.save(Rule.from_dict({**base, **d}))
    log.info(f"[seed] {len(_SEEDS)} default rules created in {S.RULES_DIR}")


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

_engine      = RuleEngine()
_llm         = LLM()
_ledger      = Ledger()
_gov         = Gov(_engine, _ledger, _llm)
_interceptor = Interceptor(_engine, _llm)
_chat        = Chat(_engine, _gov, _interceptor, _ledger, _llm)
_anomaly     = Anomaly(_ledger)
_proxy       = Proxy()
_rl          = RateLimiter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _ledger.init()
    _seed(_engine)
    n      = _engine.stats()["total"]
    lstats = await _ledger.stats()
    log.info("━" * 64)
    log.info("  Nova Core  v3.1")
    log.info(f"  Rules     : {n} active in {S.RULES_DIR}")
    log.info(f"  Ledger    : {lstats.get('total', 0)} entries in {S.DB_PATH}")
    llm_status = "ready ✓" if S.LLM_API_KEY else "NO KEY — L1+L2 only"
    log.info(f"  LLM       : {S.LLM_PROVIDER}/{S.LLM_MODEL} | {llm_status}")
    agent_info = S.AGENT_URL or "not connected — POST /connect"
    log.info(f"  Agent     : {agent_info}")
    log.info(f"  Fail-open : {S.FAIL_OPEN}  |  Dev mode: {S.DEV_MODE}")
    log.info("━" * 64)
    yield


app = FastAPI(
    title="Nova Core",
    version="3.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth + rate-limit ─────────────────────────────────────────────────────────

def _auth(x_api_key: Optional[str] = Header(None, alias="x-api-key")) -> str:
    if not S.DEV_MODE and x_api_key != S.API_KEY:
        raise HTTPException(401, "Invalid API key")
    key = x_api_key or "dev"
    if not _rl.check(key):
        raise HTTPException(429, "Rate limit exceeded (200 req/min)")
    return key


# ── Pydantic models ───────────────────────────────────────────────────────────

class ValidateReq(BaseModel):
    action:     str
    context:    str              = ""
    scope:      str              = "global"
    agent_name: str              = ""
    can_do:     Optional[List[str]] = None
    cannot_do:  Optional[List[str]] = None
    check_dups: bool             = True
    dry_run:    bool             = False


class BatchValidateReq(BaseModel):
    actions:    List[str]
    agent_name: str              = ""
    scope:      str              = "global"
    can_do:     Optional[List[str]] = None
    cannot_do:  Optional[List[str]] = None


class InterceptReq(BaseModel):
    message: str
    sender:  str = "admin"
    scope:   str = "global"


class CreateRuleReq(BaseModel):
    description: str
    scope:       str = "global"
    created_by:  str = "api"
    action:      str = "block"
    priority:    int = 7


class ChatReq(BaseModel):
    message:    str
    session_id: str = "default"
    scope:      str = "global"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    reach = False
    if S.AGENT_URL:
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                reach = (await c.get(f"{S.AGENT_URL}/health")).status_code < 400
        except Exception:
            pass
    ls = await _ledger.stats()
    return {
        "status":          "ok",
        "version":         "3.1.0",
        "rules":           _engine.stats(),
        "ledger":          ls,
        "agent_url":       S.AGENT_URL or "not connected",
        "agent_reachable": reach,
        "llm":             f"{S.LLM_PROVIDER}/{S.LLM_MODEL}",
        "llm_ready":       bool(S.LLM_API_KEY),
        "rules_dir":       str(S.RULES_DIR),
        "db":              S.DB_PATH,
        "fail_open":       S.FAIL_OPEN,
        "timestamp":       _now(),
    }


@app.post("/validate")
async def validate(req: ValidateReq, bg: BackgroundTasks):
    """
    Validate an agent action through all governance layers.
    L1 (deterministic) always runs — sub-millisecond.
    L2 (heuristic) runs when can_do/cannot_do provided.
    L3 (semantic/LLM) runs only if rules require it and LLM is configured.
    """
    v = await _gov.validate(
        action=req.action,
        scope=req.scope,
        context=req.context,
        agent_name=req.agent_name,
        can_do=req.can_do,
        cannot_do=req.cannot_do,
        check_dups=req.check_dups,
        dry_run=req.dry_run,
    )
    if req.agent_name and not req.dry_run:
        bg.add_task(_anomaly.run, req.agent_name)
    return v.to_dict()


@app.post("/validate/batch")
async def validate_batch(req: BatchValidateReq):
    """Validate up to 20 actions simultaneously."""
    results = await asyncio.gather(*[
        _gov.validate(
            action=a,
            scope=req.scope,
            agent_name=req.agent_name,
            can_do=req.can_do,
            cannot_do=req.cannot_do,
        )
        for a in req.actions[:20]
    ])
    blocked  = sum(1 for v in results if v.blocked)
    approved = sum(1 for v in results if v.result == "APPROVED")
    return {
        "results":  [v.to_dict() for v in results],
        "total":    len(results),
        "approved": approved,
        "blocked":  blocked,
    }


@app.post("/intercept")
async def intercept(req: InterceptReq):
    """
    Feed any admin/user message here.
    If it contains a governance instruction, a rule is auto-created
    in nova_rules/ and the agent never knows.
    """
    rule = await _interceptor.process(req.message, req.sender, req.scope)
    if rule:
        safe_name = rule.name[:20].lower().replace(" ", "_")
        return {
            "rule_created": True,
            "rule_id":      rule.id,
            "rule_name":    rule.name,
            "rule_scope":   rule.scope,
            "rule_action":  rule.action,
            "file":         str(S.RULES_DIR / f"{rule.id}_{safe_name}.yaml"),
        }
    return {"rule_created": False}


@app.post("/rules")
async def create_rule(req: CreateRuleReq):
    """Create a rule from a natural language description."""
    rule = await _interceptor.process(
        "regla: " + req.description,
        sender=req.created_by,
        scope=req.scope,
    )
    if not rule:
        raise HTTPException(
            422, "Could not parse description into a rule. Be more specific."
        )
    rule.action   = req.action
    rule.priority = req.priority
    _engine.save(rule)
    return {**rule.to_dict(), "file": f"nova_rules/{rule.id}.yaml"}


@app.get("/rules")
async def list_rules(scope: str = "global"):
    rules = _engine.all(scope)
    return {"rules": [r.to_dict() for r in rules], "total": len(rules)}


@app.get("/rules/stats")
async def rule_stats():
    return _engine.stats()


@app.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    r = _engine.get(rule_id)
    if not r:
        raise HTTPException(404, f"Rule {rule_id} not found")
    return r.to_dict()


@app.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    if _engine.deactivate(rule_id):
        return {"deleted": True, "rule_id": rule_id}
    raise HTTPException(404, f"Rule {rule_id} not found")


@app.get("/ledger")
async def ledger_list(agent_name: str = "", limit: int = 50):
    entries = await _ledger.recent(agent_name, min(limit, 200))
    return {"entries": entries, "total": len(entries)}


@app.get("/ledger/stats")
async def ledger_stats(agent_name: str = ""):
    return await _ledger.stats(agent_name)


@app.get("/ledger/timeline")
async def ledger_timeline(agent_name: str = "", hours: int = 24):
    return {
        "timeline": await _ledger.timeline(agent_name, hours),
        "hours": hours,
    }


@app.post("/chat")
async def chat(req: ChatReq):
    """Nova Chat — create and manage governance rules via natural language."""
    return await _chat.send(req.message, req.session_id, req.scope)


@app.websocket("/chat/ws")
async def chat_ws(ws: WebSocket):
    """WebSocket Nova Chat for real-time governance management."""
    await ws.accept()
    session = "ws_" + secrets.token_hex(4)
    try:
        while True:
            data    = await ws.receive_json()
            msg     = data.get("message", "")
            scope   = data.get("scope", "global")
            session = data.get("session_id", session)
            if not msg:
                continue
            await ws.send_json({"type": "thinking"})
            result = await _chat.send(msg, session, scope)
            await ws.send_json(result)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.get("/stream/events")
async def stream_events(agent_name: str = "all"):
    """
    SSE stream of real-time validation events and anomalies.
    Connect from dashboard or nova CLI.
    """
    q = _ledger.sse_subscribe(agent_name)

    async def generate():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield "data: " + json.dumps(event) + "\n\n"
                except asyncio.TimeoutError:
                    yield "data: " + json.dumps(
                        {"type": "heartbeat", "ts": _now()}
                    ) + "\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _ledger.sse_unsubscribe(agent_name, q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/anomalies")
async def anomalies(agent_name: str = "", limit: int = 50):
    where  = "WHERE agent_name=?" if agent_name else ""
    params = (agent_name, min(limit, 200)) if agent_name else (min(limit, 200),)
    rows   = await (await _ledger._c.execute(
        f"SELECT * FROM anomalies {where} ORDER BY id DESC LIMIT ?", params
    )).fetchall()
    return {"anomalies": [dict(r) for r in rows], "total": len(rows)}


@app.get("/scan")
async def scan():
    """Discover running AI agents on localhost."""
    agents = await scan_agents()
    return {"agents": agents, "count": len(agents)}


@app.post("/connect")
async def connect(request: Request):
    """
    Connect Nova to an agent.
    Auto-discovers the first running agent if agent_url not provided.
    """
    d    = await request.json()
    url  = d.get("agent_url", "").rstrip("/")
    name = d.get("agent_name", "agent")
    if not url:
        agents = await scan_agents()
        if not agents:
            raise HTTPException(
                404, "No agents found on localhost. Provide agent_url."
            )
        url  = agents[0]["url"]
        name = agents[0]["name"]
    S.AGENT_URL  = url
    S.AGENT_NAME = name
    reach = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            reach = (await c.get(f"{url}/health")).status_code < 400
    except Exception:
        pass
    log.info(f"[proxy] connected to {name} at {url} (reachable={reach})")
    return {
        "connected":  True,
        "agent_url":  url,
        "agent_name": name,
        "reachable":  reach,
        "scope":      f"agent:{name}",
        "message":    f'Nova is now governing "{name}" at {url}',
    }


@app.api_route(
    "/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(path: str, request: Request):
    """
    Transparent proxy — forwards everything to the connected agent.
    The agent never knows Nova exists.
    """
    return await _proxy.forward(request, path)


# ── /boot/{agent_name}  — identity + rules at agent startup ─────────────────

class BootResponse(BaseModel):
    agent_name:   str
    rules:        List[Dict]
    rule_count:   int
    system_block: str          # drop this into your system prompt
    restart_count: int
    ts:           str


@app.get("/boot/{agent_name}", response_model=None)
async def boot(agent_name: str):
    """
    Called by an agent when it starts or restarts.
    Returns active rules + a pre-formatted system-prompt block.

    Drop the returned system_block into your SYSTEM_PROMPT and the agent
    remembers who it is even after a crash, restart, or redeploy.

    Usage from agent:
        import httpx
        resp = httpx.get("http://localhost:9003/boot/melissa").json()
        SYSTEM_PROMPT += resp["system_block"]
    """
    rules    = _engine.all(scope=f"agent:{agent_name}")
    g_rules  = _engine.all(scope="global")
    all_rules = g_rules + [r for r in rules if r not in g_rules]

    lines = []
    for r in all_rules:
        verb  = "NEVER" if r.action == "block" else "AVOID"
        lines.append(f"- [{verb}] {r.original_instruction or r.name}")

    block = ""
    if lines:
        block = (
            "\n\n== NOVA GOVERNANCE RULES (auto-injected at boot) ==\n"
            + "\n".join(lines)
            + "\n== END NOVA RULES =="
        )

    # Track restart count in ledger (non-blocking)
    restarts = 0
    try:
        rows = await _ledger._c.execute(
            "SELECT COUNT(*) FROM ledger WHERE agent_name=? AND result=?",
            (agent_name, "BOOT")
        )
        row = await rows.fetchone()
        restarts = row[0] if row else 0
        await _ledger._c.execute(
            "INSERT INTO ledger (id,agent_name,action,result,score,layer,reason,ts,prev_hash,hash)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), agent_name, "agent_boot", "BOOT",
             100, "system", "Agent started — Nova identity injected",
             _now(), "", secrets.token_hex(16))
        )
        await _ledger._c.commit()
    except Exception:
        pass

    return {
        "agent_name":    agent_name,
        "rules":         [r.to_dict() for r in all_rules],
        "rule_count":    len(all_rules),
        "system_block":  block,
        "restart_count": restarts + 1,
        "ts":            _now(),
    }


# ── /connect/multi  — connect several agents in one call ─────────────────────

@app.post("/connect/multi")
async def connect_multi(request: Request):
    """
    Connect Nova to multiple agents at once.
    Body: {"agents": [{"url": "http://...", "name": "..."}, ...]}
    """
    d      = await request.json()
    agents = d.get("agents", [])
    if not agents:
        # Auto-scan
        agents = [{"url": a["url"], "name": a["name"]}
                  for a in await scan_agents()]
    results = []
    for ag in agents:
        url  = ag.get("url", "").rstrip("/")
        name = ag.get("name", "agent")
        if not url:
            continue
        reach = False
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                reach = (await c.get(f"{url}/health")).status_code < 400
        except Exception:
            pass
        results.append({
            "name":      name,
            "url":       url,
            "reachable": reach,
            "scope":     f"agent:{name}",
        })
        log.info(f"[multi-connect] {name} @ {url}  reachable={reach}")
    # Set primary agent as the first reachable one
    for r in results:
        if r["reachable"]:
            S.AGENT_URL  = r["url"]
            S.AGENT_NAME = r["name"]
            break
    return {
        "connected": len(results),
        "agents":    results,
    }


# ── /rules/load-folder  — bulk load rules from a .nova/agents/ folder ─────────

@app.post("/rules/load-folder")
async def load_rules_folder(request: Request):
    """
    Load all .json rule files from a .nova/agents/<name>/rules/ folder.
    Nova CLI calls this after running nova setup to push local rules into Core.
    """
    import json as _json
    d      = await request.json()
    folder = Path(d.get("path", ""))
    scope  = d.get("scope", "global")
    if not folder.exists():
        raise HTTPException(404, f"Folder not found: {folder}")
    loaded = 0
    errors = []
    for f in sorted(folder.glob("*.json")):
        try:
            data = _json.loads(f.read_text())
            data.setdefault("scope",  scope)
            data.setdefault("active", True)
            data.setdefault("source", "nova_folder")
            data.setdefault("log",    True)
            data.setdefault("notify", [])
            data.setdefault("escalate_to", "")
            data.setdefault("semantic", {"enabled": False, "description": "", "threshold": 0.82})
            data.setdefault("deterministic", {
                "keywords_block": [],
                "keywords_warn":  [],
                "regex_block":    [],
                "regex_warn":     [],
                "amount_block":   None,
                "amount_warn":    None,
            })
            data.setdefault("original_instruction", data.get("description", data.get("name", "")))
            rule = Rule.from_dict(data)
            _engine.save(rule)
            loaded += 1
        except Exception as e:
            errors.append({"file": f.name, "error": str(e)})
    return {"loaded": loaded, "errors": errors, "total": loaded + len(errors)}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("nova_core:app", host="0.0.0.0", port=S.PORT, reload=False)
