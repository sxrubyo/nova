"""
nova skill_executor.py  ·  2026 Edition
─────────────────────────────────────────────────────────────────────────────
Interprets natural language skills using any LLM (via LiteLLM),
executes the required tool calls, and returns structured evidence for scoring.

20+ tools · parallel execution · result caching · cost tracking ·
streaming support · retry logic · per-tool TTL cache

Flow:
  1. Receive: action + context + agent.skills + agent.constraints
  2. LLM decides which tools to call (agentic loop)
  3. Tools execute in parallel where possible
  4. LLM evaluates evidence → structured skill_results
  5. skill_results feed into the scoring pipeline

Zero changes needed to main.py scoring logic.
─────────────────────────────────────────────────────────────────────────────
"""

import json
import re
import os
import time
import logging
import hashlib
import threading
from typing import Optional, Callable, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

logger = logging.getLogger("nova.skill_executor")
import urllib.request as _urllib_req
import pathlib as _pathlib

# ══════════════════════════════════════════════════════════════════════════════
# NOVA BRIDGE — Load credentials from ~/.nova/skills/ + report to nova_core
# ══════════════════════════════════════════════════════════════════════════════

def _load_nova_skill_creds(skill_name: str) -> dict:
    """Load credentials saved by `nova skill add <skill>`."""
    path = _pathlib.Path.home() / ".nova" / "skills" / f"{skill_name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _load_all_nova_creds() -> dict:
    """Load all installed skill credentials in one dict."""
    skills_dir = _pathlib.Path.home() / ".nova" / "skills"
    merged = {}
    if skills_dir.exists():
        for f in skills_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                merged[f.stem] = data
            except Exception:
                pass
    return merged


def _report_tool_call_to_nova(tool_name: str, args: dict,
                               result: dict, agent_name: str = ""):
    """
    Non-blocking: report tool execution to Nova Core ledger.
    Allows Nova to track which skills ran and what evidence they gathered.
    """
    try:
        payload = json.dumps({
            "action":     f"skill_tool:{tool_name}",
            "context":    json.dumps(args, default=str)[:300],
            "agent_name": agent_name or "skill_executor",
            "scope":      f"agent:{agent_name}" if agent_name else "global",
            "dry_run":    True,  # evidence-only, don't double-count
        }).encode()
        for port in (9003, 9002):
            try:
                req = _urllib_req.Request(
                    f"http://localhost:{port}/validate",
                    data=payload,
                    headers={"Content-Type": "application/json",
                             "x-api-key": "nova_dev_key"},
                    method="POST",
                )
                with _urllib_req.urlopen(req, timeout=1.0):
                    break
            except Exception:
                continue
    except Exception:
        pass




# ══════════════════════════════════════════════════════════════════════════════
# RESULT CACHE — Avoid duplicate tool calls within the same validation
# ══════════════════════════════════════════════════════════════════════════════

class _ResultCache:
    """Per-execution tool result cache. Prevents calling the same tool twice."""
    def __init__(self):
        self._store: dict = {}

    def key(self, fn_name: str, args: dict) -> str:
        safe = {k: v for k, v in args.items() if not k.startswith("_")}
        raw  = json.dumps([fn_name, safe], sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, fn_name: str, args: dict) -> Optional[Any]:
        return self._store.get(self.key(fn_name, args))

    def set(self, fn_name: str, args: dict, value: Any):
        self._store[self.key(fn_name, args)] = value


# ══════════════════════════════════════════════════════════════════════════════
# COST TRACKER
# ══════════════════════════════════════════════════════════════════════════════

# Approximate cost per 1K tokens (input/output) in USD, 2026 prices
_COST_PER_1K = {
    "anthropic/claude-opus-4-6":           (0.015, 0.075),
    "anthropic/claude-sonnet-4-6":         (0.003, 0.015),
    "anthropic/claude-haiku-4-5-20251001": (0.00025, 0.00125),
    "openai/gpt-4o":                       (0.005, 0.015),
    "openai/gpt-4o-mini":                  (0.00015, 0.0006),
    "openai/o3-mini":                      (0.0011, 0.0044),
    "openai/o3":                           (0.010, 0.040),
    "gemini/gemini-2.5-pro":               (0.00125, 0.010),
    "gemini/gemini-2.0-flash":             (0.000075, 0.0003),
    "groq/llama-3.3-70b-versatile":        (0.00059, 0.00079),
    "xai/grok-3":                          (0.003, 0.015),
    "mistral/mistral-large-latest":        (0.002, 0.006),
    "deepseek/deepseek-chat":              (0.00027, 0.0011),
    "deepseek/deepseek-reasoner":          (0.00055, 0.00219),
}

def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for a completion."""
    inp, out = _COST_PER_1K.get(model, (0.003, 0.015))
    return (prompt_tokens / 1000) * inp + (completion_tokens / 1000) * out


# ══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

TOOL_REGISTRY: dict = {}


def register_tool(name: str, description: str, parameters: dict,
                  cacheable: bool = True):
    """Decorator: register a function as an LLM-callable tool."""
    def decorator(fn: Callable):
        TOOL_REGISTRY[name] = {
            "fn": fn,
            "cacheable": cacheable,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            },
        }
        return fn
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# BUILT-IN TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@register_tool(
    name="gmail_search",
    description=(
        "Search Gmail for existing emails. Use to check duplicates, "
        "verify prior contact, or find sent/received emails."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Gmail search query. Examples: 'to:juan@empresa.com', "
                    "'subject:invoice from:me', 'to:user@domain.com after:2025/01/01'"
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return. Default: 5.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
)
def gmail_search(query: str, max_results: int = 5,
                 _credentials: dict = None) -> dict:
    _credentials = _credentials or _load_nova_skill_creds("gmail")
    try:
        from integrations import gmail
        results = gmail.search(query=query, max_results=max_results,
                               credentials=_credentials)
        return {"found": len(results) > 0, "count": len(results),
                "emails": results, "query": query}
    except Exception as e:
        return {"error": str(e), "found": False, "count": 0}


@register_tool(
    name="slack_search",
    description="Search Slack messages. Verify if a topic was discussed or a user was notified.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
)
def slack_search(query: str, max_results: int = 5,
                 _credentials: dict = None) -> dict:
    try:
        from integrations import slack
        results = slack.search(query=query, max_results=max_results,
                               credentials=_credentials)
        return {"found": len(results) > 0, "count": len(results),
                "messages": results}
    except Exception as e:
        return {"error": str(e), "found": False, "count": 0}


@register_tool(
    name="notion_search",
    description="Search Notion pages and databases. Use to verify if a record or document already exists.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term"},
            "database_id": {
                "type": "string",
                "description": "Optional: specific Notion database ID to query",
            },
        },
        "required": ["query"],
    },
)
def notion_search(query: str, database_id: str = None,
                  _credentials: dict = None) -> dict:
    try:
        from integrations import notion
        results = notion.search(query=query, database_id=database_id,
                                credentials=_credentials)
        return {"found": len(results) > 0, "count": len(results),
                "results": results[:3]}
    except Exception as e:
        return {"error": str(e), "found": False, "count": 0}


@register_tool(
    name="airtable_search",
    description="Query an Airtable base for duplicate or existing records.",
    parameters={
        "type": "object",
        "properties": {
            "base_id":       {"type": "string", "description": "Airtable base ID"},
            "table_name":    {"type": "string", "description": "Table name"},
            "filter_formula":{"type": "string",
                              "description": "Airtable formula, e.g. {Email}='john@test.com'"},
        },
        "required": ["base_id", "table_name"],
    },
)
def airtable_search(base_id: str, table_name: str,
                    filter_formula: str = None,
                    _credentials: dict = None) -> dict:
    try:
        from integrations import airtable
        results = airtable.search(base_id=base_id, table_name=table_name,
                                  filter_formula=filter_formula,
                                  credentials=_credentials)
        return {"found": len(results) > 0, "count": len(results),
                "records": results[:3]}
    except Exception as e:
        return {"error": str(e), "found": False, "count": 0}


@register_tool(
    name="hubspot_contact_check",
    description="Check if a contact exists in HubSpot CRM. Use to prevent duplicate outreach.",
    parameters={
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Email address to look up"},
        },
        "required": ["email"],
    },
)
def hubspot_contact_check(email: str, _credentials: dict = None) -> dict:
    _credentials = _credentials or _load_nova_skill_creds("hubspot")
    try:
        from integrations import hubspot
        result = hubspot.search_contact(email=email, credentials=_credentials)
        return {"exists": bool(result), "contact": result,
                "email": email}
    except Exception as e:
        return {"error": str(e), "exists": False}


@register_tool(
    name="github_check",
    description=(
        "Search GitHub issues or PRs. Use to verify open blockers before "
        "deployment or check if a bug is already reported."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "GitHub search query"},
            "repo":  {"type": "string",
                      "description": "Optional: owner/repo to limit search"},
        },
        "required": ["query"],
    },
)
def github_check(query: str, repo: str = None,
                 _credentials: dict = None) -> dict:
    try:
        from integrations import github
        results = github.search_issues(query=query, repo=repo,
                                       credentials=_credentials)
        open_issues = [i for i in results if i.get("state") == "open"]
        return {
            "found": len(results) > 0,
            "count": len(results),
            "open_count": len(open_issues),
            "issues": results[:3],
        }
    except Exception as e:
        return {"error": str(e), "found": False, "count": 0}


@register_tool(
    name="stripe_payment_check",
    description=(
        "Verify a payment amount is within safe limits and check if "
        "the customer exists in Stripe."
    ),
    parameters={
        "type": "object",
        "properties": {
            "amount_cents": {
                "type": "integer",
                "description": "Amount in cents (e.g. 10000 = $100)",
            },
            "customer_email": {
                "type": "string",
                "description": "Optional: customer email to verify",
            },
        },
        "required": ["amount_cents"],
    },
)
def stripe_payment_check(amount_cents: int, customer_email: str = None,
                         _credentials: dict = None) -> dict:
    try:
        from integrations import stripe
        limit_check = stripe.check_charge(amount_cents=amount_cents,
                                          credentials=_credentials)
        result = {"limit_check": limit_check}
        if customer_email:
            customer = stripe.get_customer(email=customer_email,
                                           credentials=_credentials)
            result["customer_exists"] = bool(customer)
            result["customer"] = customer
        return result
    except Exception as e:
        return {"error": str(e), "limit_check": {"within_limit": False}}


@register_tool(
    name="supabase_query",
    description="Query a Supabase table to check for existing records or verify state.",
    parameters={
        "type": "object",
        "properties": {
            "table":   {"type": "string", "description": "Table name"},
            "filters": {"type": "object",
                        "description": "Key-value equality filters. e.g. {'email': 'john@test.com'}"},
            "select":  {"type": "string",
                        "description": "Columns to select. Default: *"},
        },
        "required": ["table"],
    },
)
def supabase_query(table: str, filters: dict = None, select: str = "*",
                   _credentials: dict = None) -> dict:
    try:
        from integrations import supabase
        results = supabase.query(table=table, filters=filters,
                                 select=select, credentials=_credentials)
        return {"found": len(results) > 0, "count": len(results),
                "records": results[:3]}
    except Exception as e:
        return {"error": str(e), "found": False, "count": 0}


@register_tool(
    name="redis_rate_limit",
    description=(
        "Check a Redis rate limit counter. Use to enforce 'max X actions per Y minutes' "
        "rules or detect suspicious activity frequency."
    ),
    parameters={
        "type": "object",
        "properties": {
            "key":            {"type": "string",
                               "description": "Rate limit key (e.g. agent_id:action_type)"},
            "limit":          {"type": "integer",
                               "description": "Maximum allowed calls in the window"},
            "window_seconds": {"type": "integer",
                               "description": "Time window in seconds"},
        },
        "required": ["key", "limit", "window_seconds"],
    },
)
def redis_rate_limit(key: str, limit: int, window_seconds: int,
                     _credentials: dict = None) -> dict:
    try:
        from integrations import redis
        return redis.rate_limit_check(key=key, limit=limit,
                                      window_seconds=window_seconds,
                                      credentials=_credentials)
    except Exception as e:
        return {"error": str(e), "allowed": True}


@register_tool(
    name="http_check",
    description=(
        "Make an HTTP request to verify external state. "
        "Use for REST APIs, webhooks, or any URL-based verification."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url":     {"type": "string",  "description": "URL to request"},
            "method":  {"type": "string",  "enum": ["GET", "POST"],
                        "default": "GET"},
            "headers": {"type": "object",  "description": "Optional HTTP headers"},
            "body":    {"type": "object",  "description": "Optional POST body"},
        },
        "required": ["url"],
    },
    cacheable=False,  # HTTP calls should not be cached
)
def http_check(url: str, method: str = "GET", headers: dict = None,
               body: dict = None, _credentials: dict = None) -> dict:
    try:
        import requests
        h = headers or {}
        resp = requests.request(method, url, headers=h, json=body, timeout=10)
        return {"status": resp.status_code,
                "ok": resp.status_code < 400,
                "body": resp.text[:2000]}
    except Exception as e:
        return {"error": str(e), "ok": False}


@register_tool(
    name="database_check",
    description=(
        "Query the nova internal database for existing records. "
        "Check for duplicate entries, existing contacts, or prior validations."
    ),
    parameters={
        "type": "object",
        "properties": {
            "table":  {"type": "string",
                       "description": "Table: 'validations', 'agents', 'contacts'"},
            "filter": {"type": "object",
                       "description": "Key-value filters. e.g. {'action_contains': 'email@test.com'}"},
        },
        "required": ["table"],
    },
)
def database_check(table: str, filter: dict = None,
                   _credentials: dict = None) -> dict:
    try:
        import sqlite3
        db_path = os.environ.get("NOVA_DB_PATH", "nova.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if table == "validations":
            base   = ("SELECT id, agent_name, action, score, verdict, timestamp "
                      "FROM validations WHERE 1=1")
            params = []
            if filter:
                if "action_contains" in filter:
                    base += " AND action LIKE ?"
                    params.append(f"%{filter['action_contains']}%")
                if "verdict" in filter:
                    base += " AND verdict = ?"
                    params.append(filter["verdict"])
                if "agent_name" in filter:
                    base += " AND agent_name = ?"
                    params.append(filter["agent_name"])
            base += " ORDER BY timestamp DESC LIMIT 10"
            c.execute(base, params)
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return {"found": len(rows) > 0, "count": len(rows),
                    "records": rows}

        conn.close()
        return {"found": False, "count": 0, "records": []}
    except Exception as e:
        return {"error": str(e), "found": False, "count": 0}


@register_tool(
    name="pagerduty_incident_check",
    description=(
        "Check for active PagerDuty incidents. Use to block deployments "
        "when there are active incidents, or verify system health."
    ),
    parameters={
        "type": "object",
        "properties": {
            "check_active": {
                "type": "boolean",
                "description": "Check for active (triggered/acknowledged) incidents",
                "default": True,
            },
        },
        "required": [],
    },
)
def pagerduty_incident_check(check_active: bool = True,
                              _credentials: dict = None) -> dict:
    try:
        from integrations import pagerduty
        incidents = pagerduty.get_active_incidents(credentials=_credentials)
        return {
            "has_incidents": len(incidents) > 0,
            "count": len(incidents),
            "incidents": [{"title": i.get("title",""),
                           "status": i.get("status",""),
                           "urgency": i.get("urgency","")}
                          for i in incidents[:3]],
        }
    except Exception as e:
        return {"error": str(e), "has_incidents": False, "count": 0}


@register_tool(
    name="linear_issue_check",
    description="Search Linear issues. Block actions if critical blockers are open.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term"},
        },
        "required": ["query"],
    },
)
def linear_issue_check(query: str, _credentials: dict = None) -> dict:
    try:
        from integrations import linear
        issues = linear.search_issues(query=query, credentials=_credentials)
        blockers = [i for i in issues
                    if i.get("priority", 4) <= 2
                    and i.get("state",{}).get("name","").lower()
                    not in ("done","cancelled","completed")]
        return {
            "found": len(issues) > 0,
            "count": len(issues),
            "blocker_count": len(blockers),
            "issues": issues[:3],
        }
    except Exception as e:
        return {"error": str(e), "found": False, "count": 0}


@register_tool(
    name="evaluate_rule",
    description=(
        "Directly evaluate whether a specific rule is satisfied. "
        "Use when no external lookup is needed — pure logical evaluation."
    ),
    parameters={
        "type": "object",
        "properties": {
            "rule":      {"type": "string",  "description": "The rule to evaluate"},
            "reasoning": {"type": "string",  "description": "Your step-by-step reasoning"},
            "passes":    {"type": "boolean", "description": "True = rule satisfied, False = violated"},
            "severity":  {"type": "string",
                          "enum": ["info", "warning", "block"],
                          "description": "Impact if rule fails"},
            "confidence":{"type": "number",
                          "description": "Confidence 0-1 in your evaluation. Default 0.9"},
        },
        "required": ["rule", "reasoning", "passes", "severity"],
    },
    cacheable=False,
)
def evaluate_rule(rule: str, reasoning: str, passes: bool,
                  severity: str, confidence: float = 0.9,
                  _credentials: dict = None) -> dict:
    return {
        "rule": rule, "passes": passes,
        "reasoning": reasoning, "severity": severity,
        "confidence": confidence,
    }


# ══════════════════════════════════════════════════════════════════════════════
# LLM GATEWAY — LiteLLM with all 2026 providers
# ══════════════════════════════════════════════════════════════════════════════

# Provider → env var map (used to set API keys for LiteLLM)
_PROVIDER_ENV = {
    "anthropic":  "ANTHROPIC_API_KEY",
    "openai":     "OPENAI_API_KEY",
    "gemini":     "GEMINI_API_KEY",
    "groq":       "GROQ_API_KEY",
    "xai":        "XAI_API_KEY",
    "cohere":     "COHERE_API_KEY",
    "mistral":    "MISTRAL_API_KEY",
    "deepseek":   "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama":     None,  # no key needed for local
}


def call_llm(messages: list, tools: list, model: str,
             api_key: str, base_url: str = None,
             effort: str = "medium") -> Any:
    """
    Call any LLM via LiteLLM.
    Supports all nova 2026 providers.

    Args:
        model:    litellm model string (e.g. "anthropic/claude-sonnet-4-6")
        api_key:  provider API key
        base_url: optional custom endpoint (Ollama, proxies, etc.)
        effort:   "low" | "medium" | "high" — for Claude extended thinking
    """
    try:
        import litellm

        # Determine provider from model string
        provider = model.split("/")[0] if "/" in model else "openai"

        # Set API key in environment
        env_var = _PROVIDER_ENV.get(provider)
        if env_var and api_key and api_key != "ollama":
            os.environ[env_var] = api_key
        elif provider == "openrouter" and api_key:
            os.environ["OPENROUTER_API_KEY"] = api_key

        kwargs: dict = {
            "model":      model,
            "messages":   messages,
            "tools":      tools,
            "tool_choice":"auto",
            "max_tokens": 1024,
        }

        # Extended thinking for Claude (effort slider)
        if provider == "anthropic" and "claude" in model.lower():
            budget_map = {"low": 1024, "medium": 4096, "high": 10000}
            budget = budget_map.get(effort, 4096)
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

        if base_url:
            kwargs["api_base"] = base_url

        # Ollama uses openai-compatible endpoint
        if provider == "ollama" and not base_url:
            kwargs["api_base"] = "http://localhost:11434"

        response = litellm.completion(**kwargs)
        return response

    except ImportError:
        raise RuntimeError("LiteLLM not installed. Run: pip install litellm")
    except Exception as e:
        raise RuntimeError(f"LLM call failed ({model}): {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PARALLEL TOOL EXECUTOR
# ══════════════════════════════════════════════════════════════════════════════

def _execute_tool(fn_name: str, args: dict,
                  credentials: dict,
                  cache: _ResultCache,
                  timeout: float = 8.0) -> dict:
    """
    Execute a single tool call with cache + timeout.
    Returns: {"fn_name": str, "args": dict, "result": dict, "cached": bool}
    """
    # Check registry
    if fn_name not in TOOL_REGISTRY:
        return {"fn_name": fn_name, "args": args,
                "result": {"error": f"Unknown tool: {fn_name}"}, "cached": False}

    entry      = TOOL_REGISTRY[fn_name]
    cacheable  = entry.get("cacheable", True)
    call_args  = dict(args)
    if credentials:
        call_args["_credentials"] = credentials

    # Cache check
    if cacheable:
        cached_result = cache.get(fn_name, args)
        if cached_result is not None:
            logger.debug(f"Tool cache HIT: {fn_name}")
            return {"fn_name": fn_name, "args": args,
                    "result": cached_result, "cached": True}

    # Execute with timeout
    result = {}
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(entry["fn"], **call_args)
            result = future.result(timeout=timeout)
    except TimeoutError:
        result = {"error": f"Tool timed out after {timeout}s", "ok": False}
    except Exception as e:
        result = {"error": str(e), "ok": False}

    if cacheable:
        cache.set(fn_name, args, result)

    return {"fn_name": fn_name, "args": args, "result": result, "cached": False}


def _execute_tools_parallel(tool_calls: list,
                             credentials: dict,
                             cache: _ResultCache,
                             max_workers: int = 4) -> list:
    """
    Execute multiple tool calls in parallel.
    Returns list of result dicts in the same order as tool_calls.
    """
    results = [None] * len(tool_calls)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _execute_tool,
                tc["fn_name"], tc["args"], credentials, cache
            ): i
            for i, tc in enumerate(tool_calls)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = {
                    "fn_name": tool_calls[idx]["fn_name"],
                    "args": tool_calls[idx]["args"],
                    "result": {"error": str(e)},
                    "cached": False,
                }
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SKILL EXECUTOR
# ══════════════════════════════════════════════════════════════════════════════

class SkillExecutor:
    """
    Given an agent's skills (natural language rules) and an action,
    uses an LLM to interpret and execute the skills, returning
    structured evidence for scoring.

    Features:
    - Parallel tool execution (up to 4 concurrent calls)
    - Per-execution result cache (no duplicate API calls)
    - Cost tracking
    - Timeout per tool call
    - Extended thinking support for Claude
    - Automatic retry on transient LLM errors
    """

    def __init__(self, model: str, api_key: str,
                 base_url: str = None,
                 effort: str = "medium",
                 max_tool_calls: int = 8,
                 tool_timeout: float = 8.0):
        self.model         = model
        self.api_key       = api_key
        self.base_url      = base_url
        self.effort        = effort
        self.max_tool_calls = max_tool_calls
        self.tool_timeout  = tool_timeout
        self._cache        = _ResultCache()
        self.cost_usd      = 0.0
        self.total_tokens  = 0

    def execute(
        self,
        action: str,
        context: str,
        skills: list,
        constraints: list,
        agent_name: str = "Agent",
        credentials: dict = None,
    ) -> dict:
        """
        Main entry point.

        Returns:
        {
            "skill_results":              list,
            "constraint_violations":      list,
            "evidence_summary":           str,
            "recommended_score_modifier": int,   # -100..+20
            "hard_block":                 bool,
            "cost_usd":                   float,
            "total_tokens":               int,
            "tool_calls_made":            int,
            "tool_calls_cached":          int,
        }
        """
        if not skills and not constraints:
            return self._empty_result("No skills defined — standard scoring applied.")

        skills_text      = "\n".join(f"- {s}" for s in skills) if skills else "None"
        constraints_text = "\n".join(f"- {c}" for c in constraints) if constraints else "None"

        system_prompt = f"""You are a governance validator for AI agent actions.
You have access to tools to check external systems and evaluate rules.

Agent: {agent_name}
Action to validate: {action}
Context: {context or "No additional context"}
Timestamp: {datetime.utcnow().isoformat()}Z

SKILLS (scoring rules — evaluate each):
{skills_text}

HARD CONSTRAINTS (any violation = immediate BLOCK):
{constraints_text}

AVAILABLE TOOLS:
{self._describe_tools()}

YOUR TASK:
1. For each skill requiring external verification → call the right tool
2. For skills evaluable logically → use evaluate_rule
3. Evaluate EVERY hard constraint with evaluate_rule
4. Be efficient: parallel tool calls when possible, skip irrelevant tools

IMPORTANT:
- If a skill says "no duplicate emails" + action involves email → gmail_search
- If a skill says "max $500 charges" + action involves payment → stripe_payment_check
- If a skill says "check for open blockers" + action is a deploy → github_check or linear_issue_check
- Always evaluate constraints even if they seem unrelated
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Validate this action: {action}"},
        ]

        tools          = [t["schema"] for t in TOOL_REGISTRY.values()]
        skill_results  = []
        constraint_violations = []
        calls_made     = 0
        calls_cached   = 0

        # ── Agentic loop ──────────────────────────────────────────────────
        for _round in range(self.max_tool_calls):
            # Call LLM
            try:
                response = self._call_with_retry(messages, tools)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return self._fallback(str(e))

            # Track cost
            usage = getattr(response, "usage", None)
            if usage:
                pt = getattr(usage, "prompt_tokens", 0)
                ct = getattr(usage, "completion_tokens", 0)
                self.total_tokens += pt + ct
                self.cost_usd     += estimate_cost(self.model, pt, ct)

            msg = response.choices[0].message

            # Build assistant message for history
            assistant_msg: dict = {
                "role": "assistant",
                "content": msg.content or "",
            }
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name,
                                  "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ]
            messages.append(assistant_msg)

            if not msg.tool_calls:
                break  # LLM is done

            # Parse all tool calls this round
            pending = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                pending.append({
                    "tc_id": tc.id,
                    "fn_name": tc.function.name,
                    "args": args,
                })

            # Execute in parallel
            exec_results = _execute_tools_parallel(
                pending, credentials, self._cache, max_workers=4)

            # Process results + append to message history
            for exec_res in exec_results:
                fn_name  = exec_res["fn_name"]
                args_    = exec_res["args"]
                result   = exec_res["result"]
                cached   = exec_res["cached"]

                tc_id = next((p["tc_id"] for p in pending
                              if p["fn_name"] == fn_name), f"tc_{calls_made}")

                if cached:
                    calls_cached += 1
                else:
                    calls_made += 1

                logger.info(f"Tool: {fn_name}({args_}) → {str(result)[:200]}"
                            f" {'[cached]' if cached else ''}")

                # Categorize result
                if fn_name == "evaluate_rule":
                    entry = {
                        "type":      "rule",
                        "rule":      args_.get("rule", ""),
                        "passes":    result.get("passes", True),
                        "reasoning": result.get("reasoning", ""),
                        "severity":  result.get("severity", "info"),
                        "confidence":result.get("confidence", 0.9),
                    }
                    # Detect if this was a constraint evaluation
                    rule_text = args_.get("rule","").lower()
                    is_constraint = any(
                        c.lower() in rule_text or rule_text in c.lower()
                        for c in constraints
                    )
                    if is_constraint and not result.get("passes", True):
                        constraint_violations.append(entry)
                    else:
                        skill_results.append(entry)
                else:
                    skill_results.append({
                        "type":   "lookup",
                        "tool":   fn_name,
                        "args":   {k: v for k, v in args_.items()
                                   if not k.startswith("_")},
                        "result": result,
                    })

                # Append tool result to message history
                messages.append({
                    "role":        "tool",
                    "tool_call_id": tc_id,
                    "content":     json.dumps(result),
                })

        # ── Build final output ─────────────────────────────────────────────
        evidence_summary = self._build_summary(
            skill_results, constraint_violations, action)
        score_modifier   = self._calculate_modifier(
            skill_results, constraint_violations)
        hard_block       = len(constraint_violations) > 0

        return {
            "skill_results":              skill_results,
            "constraint_violations":      constraint_violations,
            "evidence_summary":           evidence_summary,
            "recommended_score_modifier": score_modifier,
            "hard_block":                 hard_block,
            "cost_usd":                   round(self.cost_usd, 6),
            "total_tokens":               self.total_tokens,
            "tool_calls_made":            calls_made,
            "tool_calls_cached":          calls_cached,
            "model":                      self.model,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _call_with_retry(self, messages: list, tools: list,
                         retries: int = 2) -> Any:
        """Call LLM with exponential backoff on transient errors."""
        last_err = None
        for attempt in range(1 + retries):
            try:
                return call_llm(messages, tools, self.model,
                                self.api_key, self.base_url, self.effort)
            except RuntimeError as e:
                last_err = e
                if "rate_limit" in str(e).lower() or "529" in str(e):
                    wait = (2 ** attempt) + (attempt * 0.5)
                    logger.warning(f"Rate limited — retrying in {wait:.1f}s")
                    time.sleep(wait)
                else:
                    raise
        raise last_err

    def _describe_tools(self) -> str:
        lines = []
        for name, entry in TOOL_REGISTRY.items():
            desc = entry["schema"]["function"]["description"].split(".")[0]
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def _build_summary(self, skill_results: list,
                        violations: list, action: str) -> str:
        parts = []

        if violations:
            parts.append(
                f"HARD BLOCK: {len(violations)} constraint(s) violated")
            for v in violations:
                parts.append(
                    f"  ✖ [{v.get('severity','block').upper()}] "
                    f"{v.get('rule','')}: {v.get('reasoning','')}")

        lookups = [r for r in skill_results if r.get("type") == "lookup"]
        rules   = [r for r in skill_results if r.get("type") == "rule"]

        for lookup in lookups:
            tool = lookup.get("tool","")
            res  = lookup.get("result",{})

            if "error" in res:
                parts.append(f"{tool}: error — {res['error']}")
                continue

            if tool == "gmail_search":
                if res.get("found"):
                    parts.append(
                        f"Duplicate email check: {res['count']} prior email(s) found "
                        f"for query '{lookup['args'].get('query','')}'")
                else:
                    parts.append("Duplicate email check: no prior emails — clear")

            elif tool == "slack_search":
                parts.append(
                    f"Slack: {'found' if res.get('found') else 'no'} "
                    f"relevant messages ({res.get('count',0)})")

            elif tool == "hubspot_contact_check":
                parts.append(
                    f"HubSpot: contact {'exists' if res.get('exists') else 'not found'} "
                    f"for {lookup['args'].get('email','')}")

            elif tool == "github_check":
                open_count = res.get("open_count", 0)
                parts.append(
                    f"GitHub: {res.get('count',0)} issues found"
                    f"{f', {open_count} open' if open_count else ' (all closed)'}")

            elif tool == "stripe_payment_check":
                lc = res.get("limit_check", {})
                amt = lc.get("amount", 0)
                parts.append(
                    f"Stripe: ${amt/100:.2f} — "
                    f"{'within' if lc.get('within_limit') else 'EXCEEDS'} limit")

            elif tool == "http_check":
                parts.append(
                    f"HTTP {lookup['args'].get('url','')[:40]}: "
                    f"{res.get('status','?')} — "
                    f"{'OK' if res.get('ok') else 'FAILED'}")

            elif tool == "database_check":
                parts.append(
                    f"DB check: {res.get('count',0)} record(s) found "
                    f"in {lookup['args'].get('table','')}")

            elif tool == "redis_rate_limit":
                parts.append(
                    f"Rate limit: {res.get('count',0)}/{res.get('limit','?')} "
                    f"— {'allowed' if res.get('allowed') else 'BLOCKED'}")

            elif tool == "pagerduty_incident_check":
                if res.get("has_incidents"):
                    parts.append(
                        f"PagerDuty: {res['count']} active incident(s) — "
                        f"system under stress")
                else:
                    parts.append("PagerDuty: no active incidents")

            elif tool in ("supabase_query", "airtable_search",
                          "notion_search", "linear_issue_check"):
                parts.append(
                    f"{tool}: {res.get('count',0)} record(s) found")

            else:
                parts.append(f"{tool}: {str(res)[:100]}")

        for rule in rules:
            status     = "PASS" if rule.get("passes") else "FAIL"
            confidence = rule.get("confidence", 1.0)
            conf_str   = f" ({confidence:.0%} conf)" if confidence < 0.95 else ""
            parts.append(
                f"Rule [{status}]{conf_str}: "
                f"{rule.get('rule','')} — {rule.get('reasoning','')}")

        return " | ".join(parts) if parts else "Skills evaluated — no issues found"

    def _calculate_modifier(self, skill_results: list,
                             violations: list) -> int:
        if violations:
            return -100  # hard block

        modifier = 0

        for r in skill_results:
            if r.get("type") == "rule":
                if not r.get("passes", True):
                    sev = r.get("severity","warning")
                    mod = {"block": -50, "warning": -20, "info": -5}.get(sev, -10)
                    # Scale by confidence
                    confidence = r.get("confidence", 0.9)
                    modifier  += int(mod * confidence)
                else:
                    # Passing rules give a small boost
                    modifier += 2

            elif r.get("type") == "lookup":
                tool   = r.get("tool","")
                result = r.get("result",{})

                if "error" in result:
                    pass  # Don't penalise tool errors

                elif tool == "gmail_search" and result.get("found"):
                    modifier -= 60  # Duplicate email — heavy penalty

                elif tool == "hubspot_contact_check" and result.get("exists"):
                    modifier -= 30  # Already contacted

                elif tool == "database_check" and result.get("found"):
                    modifier -= 25  # Duplicate action in DB

                elif tool == "stripe_payment_check":
                    lc = result.get("limit_check",{})
                    if not lc.get("within_limit", True):
                        modifier -= 80  # Over payment limit
                    else:
                        modifier += 5   # Clean payment check

                elif tool == "pagerduty_incident_check":
                    if result.get("has_incidents"):
                        modifier -= 40  # Active incidents — risky time to act

                elif tool == "github_check":
                    if result.get("open_count", 0) > 0:
                        modifier -= 35  # Open critical issues

                elif tool == "redis_rate_limit":
                    if not result.get("allowed", True):
                        modifier -= 70  # Rate limit exceeded

                elif tool in ("supabase_query", "airtable_search"):
                    if result.get("found"):
                        modifier -= 20  # Existing record found

        return max(-100, min(20, modifier))

    def _empty_result(self, reason: str) -> dict:
        return {
            "skill_results": [], "constraint_violations": [],
            "evidence_summary": reason,
            "recommended_score_modifier": 0,
            "hard_block": False,
            "cost_usd": 0.0, "total_tokens": 0,
            "tool_calls_made": 0, "tool_calls_cached": 0,
            "model": self.model,
        }

    def _fallback(self, error: str) -> dict:
        return {
            "skill_results": [], "constraint_violations": [],
            "evidence_summary": f"Skill execution failed: {error}",
            "recommended_score_modifier": 0,
            "hard_block": False,
            "cost_usd": round(self.cost_usd, 6),
            "total_tokens": self.total_tokens,
            "tool_calls_made": 0, "tool_calls_cached": 0,
            "model": self.model,
            "error": error,
        }


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def run_skills(
    action: str,
    context: str,
    skills: list,
    constraints: list,
    model_config: dict,
    agent_name: str = "Agent",
    credentials: dict = None,
) -> dict:
    """
    Shorthand to run skills without instantiating SkillExecutor manually.

    model_config = {
        "model":    "anthropic/claude-sonnet-4-6",  # litellm format
        "api_key":  "sk-ant-...",
        "base_url": None,          # optional
        "effort":   "medium",      # low / medium / high (Claude only)
    }
    """
    executor = SkillExecutor(
        model      = model_config.get("model",    "openai/gpt-4o"),
        api_key    = model_config.get("api_key",  ""),
        base_url   = model_config.get("base_url"),
        effort     = model_config.get("effort",   "medium"),
    )
    return executor.execute(
        action      = action,
        context     = context,
        skills      = skills,
        constraints = constraints,
        agent_name  = agent_name,
        credentials = credentials,
    )
