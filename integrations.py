"""
nova integrations.py  ·  2026 Edition
──────────────────────────────────────────────────────────────────────────────
Connector implementations for external services.
Each integration exposes a clean search() / check() / call() interface
consumed by skill_executor.py tools.

20+ connectors · caching · retry · rate limiting · async hints

Adding a new integration:
  1. Create a class below with at minimum: search() or check() methods
  2. Register it in INTEGRATIONS dict at the bottom
  3. Add its credential schema to INTEGRATION_SCHEMAS
  4. (optional) Add tool registration in skill_executor.py
──────────────────────────────────────────────────────────────────────────────
"""

import os
import json
import logging
import time
import hashlib
import threading
from typing import Optional, Any
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger("nova.integrations")

# ══════════════════════════════════════════════════════════════════════════════
# CACHING LAYER — In-memory TTL cache shared across integrations
# ══════════════════════════════════════════════════════════════════════════════

class _TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""
    def __init__(self):
        self._store: dict = {}
        self._lock = threading.Lock()

    def _key(self, ns: str, *args, **kwargs) -> str:
        raw = json.dumps([ns, args, kwargs], sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, ns: str, *args, **kwargs) -> Any:
        k = self._key(ns, *args, **kwargs)
        with self._lock:
            entry = self._store.get(k)
            if entry and entry["expires"] > time.time():
                logger.debug(f"Cache HIT: {ns}")
                return entry["value"]
        return None

    def set(self, value: Any, ttl: int, ns: str, *args, **kwargs):
        k = self._key(ns, *args, **kwargs)
        with self._lock:
            self._store[k] = {"value": value, "expires": time.time() + ttl}

    def invalidate(self, ns: str):
        with self._lock:
            self._store = {k: v for k, v in self._store.items()
                           if not k.startswith(ns)}


_CACHE = _TTLCache()

def cached(ttl: int = 300, ns: str = ""):
    """Decorator: cache function result for `ttl` seconds."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cache_key_ns = ns or fn.__qualname__
            # Don't cache when credentials differ — use all args as cache key
            result = _CACHE.get(cache_key_ns, *args, **kwargs)
            if result is not None:
                return result
            result = fn(*args, **kwargs)
            _CACHE.set(result, ttl, cache_key_ns, *args, **kwargs)
            return result
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# RETRY UTILITY
# ══════════════════════════════════════════════════════════════════════════════

def _retry(fn, retries: int = 2, backoff: float = 0.5, *args, **kwargs):
    """Call fn(*args, **kwargs) with exponential backoff on exception."""
    last_err = None
    for attempt in range(1 + retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
    raise last_err


# ══════════════════════════════════════════════════════════════════════════════
# BASE CLASS
# ══════════════════════════════════════════════════════════════════════════════

class BaseIntegration:
    """Common helpers for all integrations."""
    NAME = "base"

    def _creds(self, credentials: dict, *keys: str) -> Optional[str]:
        """Try each key name in credentials dict, then env vars."""
        creds = credentials or {}
        for key in keys:
            val = creds.get(key) or os.environ.get(key.upper())
            if val:
                return val
        return None

    def _headers_json(self, token: str, extra: dict = None) -> dict:
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if extra:
            h.update(extra)
        return h

    def _http(self, method: str, url: str, **kwargs) -> "requests.Response":
        import requests
        kwargs.setdefault("timeout", 10)
        return requests.request(method, url, **kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# COMMUNICATION
# ══════════════════════════════════════════════════════════════════════════════

class GmailIntegration(BaseIntegration):
    """
    Gmail connector — OAuth2 or Service Account.
    Supports: search, get, list labels, check sent.
    """
    NAME = "gmail"

    def search(self, query: str, max_results: int = 5,
               credentials: dict = None) -> list:
        """Search Gmail messages. Returns [{id, subject, from, to, date, snippet}]."""
        token = self._creds(credentials, "gmail_token", "GMAIL_TOKEN")
        svc_acct = self._creds(credentials, "gmail_service_account", "GMAIL_SERVICE_ACCOUNT")
        if not token and not svc_acct:
            logger.warning("Gmail: no credentials")
            return []
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            if token:
                td = json.loads(token) if isinstance(token, str) else token
                gcreds = Credentials(
                    token=td.get("access_token"),
                    refresh_token=td.get("refresh_token"),
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=td.get("client_id"),
                    client_secret=td.get("client_secret"),
                )
            else:
                from google.oauth2 import service_account as sa
                sa_data = json.loads(svc_acct) if isinstance(svc_acct, str) else svc_acct
                gcreds = sa.Credentials.from_service_account_info(
                    sa_data, scopes=["https://www.googleapis.com/auth/gmail.readonly"])

            svc = build("gmail", "v1", credentials=gcreds)
            result = svc.users().messages().list(
                userId="me", q=query, maxResults=max_results).execute()
            msgs = result.get("messages", [])
            out = []
            for m in msgs[:max_results]:
                detail = svc.users().messages().get(
                    userId="me", id=m["id"], format="metadata",
                    metadataHeaders=["Subject","From","To","Date"]).execute()
                hdrs = {h["name"]: h["value"]
                        for h in detail.get("payload", {}).get("headers", [])}
                out.append({
                    "id": m["id"], "subject": hdrs.get("Subject",""),
                    "from": hdrs.get("From",""), "to": hdrs.get("To",""),
                    "date": hdrs.get("Date",""),
                    "snippet": detail.get("snippet","")[:200],
                })
            return out
        except ImportError:
            logger.error("Gmail: install google-api-python-client google-auth")
            return []
        except Exception as e:
            logger.error(f"Gmail search failed: {e}")
            return []

    def check_sent_to(self, email: str, credentials: dict = None) -> dict:
        """Check if any email was ever sent to a specific address."""
        results = self.search(f"to:{email}", max_results=1, credentials=credentials)
        return {"contacted": len(results) > 0, "count": len(results), "emails": results}


class SlackIntegration(BaseIntegration):
    """Slack — search messages, list channels, post messages."""
    NAME = "slack"

    def search(self, query: str, max_results: int = 5,
               credentials: dict = None) -> list:
        token = self._creds(credentials, "slack_token", "SLACK_BOT_TOKEN")
        if not token:
            return []
        try:
            r = self._http("GET", "https://slack.com/api/search.messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"query": query, "count": max_results})
            data = r.json()
            if not data.get("ok"):
                logger.warning(f"Slack: {data.get('error')}")
                return []
            return [{"ts": m.get("ts"), "text": m.get("text","")[:300],
                     "user": m.get("username",""),
                     "channel": m.get("channel",{}).get("name","")}
                    for m in data.get("messages",{}).get("matches",[])]
        except Exception as e:
            logger.error(f"Slack search: {e}")
            return []

    def list_channels(self, credentials: dict = None) -> list:
        token = self._creds(credentials, "slack_token", "SLACK_BOT_TOKEN")
        if not token:
            return []
        try:
            r = self._http("GET", "https://slack.com/api/conversations.list",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 100, "exclude_archived": True})
            return r.json().get("channels", [])
        except Exception as e:
            logger.error(f"Slack list_channels: {e}")
            return []

    def post_message(self, channel: str, text: str,
                     credentials: dict = None) -> dict:
        token = self._creds(credentials, "slack_token", "SLACK_BOT_TOKEN")
        if not token:
            return {"ok": False, "error": "no_token"}
        try:
            r = self._http("POST", "https://slack.com/api/chat.postMessage",
                headers=self._headers_json(token),
                json={"channel": channel, "text": text})
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}


class DiscordIntegration(BaseIntegration):
    """Discord — send messages, read channel history."""
    NAME = "discord"

    def send_message(self, channel_id: str, content: str,
                     credentials: dict = None) -> dict:
        token = self._creds(credentials, "discord_token", "DISCORD_BOT_TOKEN")
        if not token:
            return {"ok": False, "error": "no_token"}
        try:
            r = self._http("POST",
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers=self._headers_json(token),
                json={"content": content[:2000]})
            return {"ok": r.status_code < 400, "status": r.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_messages(self, channel_id: str, limit: int = 10,
                     credentials: dict = None) -> list:
        token = self._creds(credentials, "discord_token", "DISCORD_BOT_TOKEN")
        if not token:
            return []
        try:
            r = self._http("GET",
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers={"Authorization": f"Bot {token}"},
                params={"limit": limit})
            return r.json() if r.status_code == 200 else []
        except Exception as e:
            logger.error(f"Discord: {e}")
            return []


class TelegramIntegration(BaseIntegration):
    """Telegram Bot API — send messages, check user status."""
    NAME = "telegram"

    def send_message(self, chat_id: str, text: str,
                     credentials: dict = None) -> dict:
        token = self._creds(credentials, "telegram_token", "TELEGRAM_BOT_TOKEN")
        if not token:
            return {"ok": False}
        try:
            r = self._http("POST",
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4096]})
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_chat(self, chat_id: str, credentials: dict = None) -> dict:
        token = self._creds(credentials, "telegram_token", "TELEGRAM_BOT_TOKEN")
        if not token:
            return {}
        try:
            r = self._http("GET",
                f"https://api.telegram.org/bot{token}/getChat",
                params={"chat_id": chat_id})
            return r.json().get("result", {})
        except Exception as e:
            return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTIVITY / KNOWLEDGE
# ══════════════════════════════════════════════════════════════════════════════

class NotionIntegration(BaseIntegration):
    """Notion — search pages, query databases, create pages."""
    NAME = "notion"

    def search(self, query: str, database_id: str = None,
               credentials: dict = None) -> list:
        token = self._creds(credentials, "notion_token", "NOTION_TOKEN")
        if not token:
            return []
        headers = {**self._headers_json(token), "Notion-Version": "2022-06-28"}
        try:
            if database_id:
                r = self._http("POST",
                    f"https://api.notion.com/v1/databases/{database_id}/query",
                    headers=headers,
                    json={"filter": {"property": "Name",
                                     "title": {"contains": query}}})
            else:
                r = self._http("POST", "https://api.notion.com/v1/search",
                    headers=headers, json={"query": query})
            return r.json().get("results", [])[:5]
        except Exception as e:
            logger.error(f"Notion: {e}")
            return []

    def create_page(self, parent_id: str, title: str, content: str = "",
                    credentials: dict = None) -> dict:
        token = self._creds(credentials, "notion_token", "NOTION_TOKEN")
        if not token:
            return {"error": "no_token"}
        headers = {**self._headers_json(token), "Notion-Version": "2022-06-28"}
        try:
            r = self._http("POST", "https://api.notion.com/v1/pages",
                headers=headers,
                json={
                    "parent": {"database_id": parent_id},
                    "properties": {"Name": {"title": [{"text": {"content": title}}]}},
                    "children": [{"object": "block", "type": "paragraph",
                                  "paragraph": {"rich_text": [{"text": {"content": content}}]}}]
                    if content else []
                })
            return r.json()
        except Exception as e:
            return {"error": str(e)}


class LinearIntegration(BaseIntegration):
    """Linear — create issues, search, check project status."""
    NAME = "linear"
    API = "https://api.linear.app/graphql"

    def _gql(self, query: str, variables: dict, credentials: dict) -> dict:
        token = self._creds(credentials, "linear_token", "LINEAR_API_KEY")
        if not token:
            return {}
        try:
            r = self._http("POST", self.API,
                headers=self._headers_json(token),
                json={"query": query, "variables": variables})
            return r.json().get("data", {})
        except Exception as e:
            logger.error(f"Linear: {e}")
            return {}

    def search_issues(self, query: str, credentials: dict = None) -> list:
        gql = """query Search($term: String!) {
          issueSearch(term: $term, first: 5) {
            nodes { id title state { name } priority url assignee { name } }
          }
        }"""
        data = self._gql(gql, {"term": query}, credentials)
        return data.get("issueSearch", {}).get("nodes", [])

    def create_issue(self, title: str, description: str = "",
                     team_id: str = None, priority: int = 2,
                     credentials: dict = None) -> dict:
        gql = """mutation Create($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success issue { id title url }
          }
        }"""
        inp = {"title": title, "description": description, "priority": priority}
        if team_id:
            inp["teamId"] = team_id
        data = self._gql(gql, {"input": inp}, credentials)
        return data.get("issueCreate", {})


class JiraIntegration(BaseIntegration):
    """Jira — search issues, create tickets, check sprint status."""
    NAME = "jira"

    def _auth(self, credentials: dict) -> tuple:
        url  = self._creds(credentials, "jira_url", "JIRA_URL")
        user = self._creds(credentials, "jira_user", "JIRA_USER")
        token = self._creds(credentials, "jira_token", "JIRA_TOKEN")
        return url, user, token

    def search(self, jql: str, max_results: int = 5,
               credentials: dict = None) -> list:
        url, user, token = self._auth(credentials)
        if not all([url, user, token]):
            return []
        try:
            r = self._http("GET", f"{url}/rest/api/3/search",
                auth=(user, token),
                params={"jql": jql, "maxResults": max_results,
                        "fields": "summary,status,assignee,priority,created"})
            return r.json().get("issues", [])
        except Exception as e:
            logger.error(f"Jira search: {e}")
            return []

    def create_issue(self, project_key: str, summary: str,
                     description: str = "", issue_type: str = "Task",
                     credentials: dict = None) -> dict:
        url, user, token = self._auth(credentials)
        if not all([url, user, token]):
            return {"error": "no_creds"}
        try:
            r = self._http("POST", f"{url}/rest/api/3/issue",
                auth=(user, token),
                json={"fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "issuetype": {"name": issue_type},
                    "description": {"type": "doc", "version": 1,
                                    "content": [{"type": "paragraph",
                                                 "content": [{"type": "text",
                                                              "text": description}]}]}
                }})
            return r.json()
        except Exception as e:
            return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# CRM / SALES
# ══════════════════════════════════════════════════════════════════════════════

class HubSpotIntegration(BaseIntegration):
    """HubSpot CRM — contacts, deals, companies, timeline."""
    NAME = "hubspot"
    BASE = "https://api.hubapi.com"

    def search_contact(self, email: str, credentials: dict = None) -> dict:
        token = self._creds(credentials, "hubspot_token", "HUBSPOT_TOKEN")
        if not token:
            return {}
        try:
            r = self._http("POST",
                f"{self.BASE}/crm/v3/objects/contacts/search",
                headers=self._headers_json(token),
                json={"filterGroups": [{"filters": [
                    {"propertyName": "email", "operator": "EQ", "value": email}
                ]}]})
            results = r.json().get("results", [])
            return results[0] if results else {}
        except Exception as e:
            logger.error(f"HubSpot contact: {e}")
            return {}

    def search_deals(self, query: str, max_results: int = 5,
                     credentials: dict = None) -> list:
        token = self._creds(credentials, "hubspot_token", "HUBSPOT_TOKEN")
        if not token:
            return []
        try:
            r = self._http("POST",
                f"{self.BASE}/crm/v3/objects/deals/search",
                headers=self._headers_json(token),
                json={"query": query, "limit": max_results,
                      "properties": ["dealname","amount","dealstage","closedate"]})
            return r.json().get("results", [])
        except Exception as e:
            logger.error(f"HubSpot deals: {e}")
            return []

    def create_contact(self, email: str, firstname: str = "",
                       lastname: str = "", company: str = "",
                       credentials: dict = None) -> dict:
        token = self._creds(credentials, "hubspot_token", "HUBSPOT_TOKEN")
        if not token:
            return {"error": "no_token"}
        try:
            r = self._http("POST",
                f"{self.BASE}/crm/v3/objects/contacts",
                headers=self._headers_json(token),
                json={"properties": {"email": email, "firstname": firstname,
                                     "lastname": lastname, "company": company}})
            return r.json()
        except Exception as e:
            return {"error": str(e)}


class SalesforceIntegration(BaseIntegration):
    """Salesforce — SOQL queries, create/update records."""
    NAME = "salesforce"

    def _get_instance(self, credentials: dict) -> tuple:
        instance = self._creds(credentials, "salesforce_instance", "SALESFORCE_INSTANCE")
        token    = self._creds(credentials, "salesforce_token",    "SALESFORCE_TOKEN")
        return instance, token

    def query(self, soql: str, credentials: dict = None) -> list:
        instance, token = self._get_instance(credentials)
        if not instance or not token:
            return []
        try:
            r = self._http("GET",
                f"{instance}/services/data/v59.0/query",
                headers=self._headers_json(token),
                params={"q": soql})
            return r.json().get("records", [])
        except Exception as e:
            logger.error(f"Salesforce query: {e}")
            return []

    def check_lead(self, email: str, credentials: dict = None) -> dict:
        records = self.query(
            f"SELECT Id,Name,Status,Email FROM Lead WHERE Email='{email}' LIMIT 1",
            credentials)
        return records[0] if records else {}


# ══════════════════════════════════════════════════════════════════════════════
# DEVELOPMENT / CODE
# ══════════════════════════════════════════════════════════════════════════════

class GitHubIntegration(BaseIntegration):
    """GitHub — repos, issues, PRs, deployments, commits."""
    NAME = "github"
    BASE = "https://api.github.com"

    def _h(self, credentials: dict) -> dict:
        token = self._creds(credentials, "github_token", "GITHUB_TOKEN")
        return {"Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"} if token else {}

    def search_issues(self, query: str, repo: str = None,
                      credentials: dict = None) -> list:
        q = query + (f" repo:{repo}" if repo else "")
        try:
            r = self._http("GET", f"{self.BASE}/search/issues",
                headers=self._h(credentials),
                params={"q": q, "per_page": 5})
            return r.json().get("items", [])
        except Exception as e:
            logger.error(f"GitHub search: {e}")
            return []

    def get_pr(self, repo: str, pr_number: int,
               credentials: dict = None) -> dict:
        try:
            r = self._http("GET",
                f"{self.BASE}/repos/{repo}/pulls/{pr_number}",
                headers=self._h(credentials))
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def create_issue(self, repo: str, title: str, body: str = "",
                     labels: list = None, credentials: dict = None) -> dict:
        try:
            r = self._http("POST",
                f"{self.BASE}/repos/{repo}/issues",
                headers=self._h(credentials),
                json={"title": title, "body": body, "labels": labels or []})
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def get_latest_release(self, repo: str,
                           credentials: dict = None) -> dict:
        try:
            r = self._http("GET",
                f"{self.BASE}/repos/{repo}/releases/latest",
                headers=self._h(credentials))
            return r.json()
        except Exception as e:
            return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# PAYMENTS / FINANCE
# ══════════════════════════════════════════════════════════════════════════════

class StripeIntegration(BaseIntegration):
    """Stripe — customers, charges, fraud checks, subscriptions."""
    NAME = "stripe"
    BASE = "https://api.stripe.com/v1"

    def _h(self, credentials: dict) -> dict:
        key = self._creds(credentials, "stripe_secret_key", "STRIPE_SECRET_KEY")
        return {"Authorization": f"Bearer {key}"} if key else {}

    def get_customer(self, email: str, credentials: dict = None) -> dict:
        try:
            r = self._http("GET", f"{self.BASE}/customers",
                headers=self._h(credentials),
                params={"email": email, "limit": 1})
            data = r.json().get("data", [])
            return data[0] if data else {}
        except Exception as e:
            logger.error(f"Stripe customer: {e}")
            return {}

    def check_charge(self, amount_cents: int, customer_id: str = None,
                     credentials: dict = None) -> dict:
        """Check if a charge is within safe limits."""
        limit = 50000  # $500 default — override via credentials
        safe_limit = int(self._creds(credentials, "stripe_charge_limit", "") or limit)
        return {
            "within_limit": amount_cents <= safe_limit,
            "amount": amount_cents,
            "limit": safe_limit,
            "currency": "usd",
        }

    def get_subscription(self, customer_id: str,
                         credentials: dict = None) -> dict:
        try:
            r = self._http("GET", f"{self.BASE}/subscriptions",
                headers=self._h(credentials),
                params={"customer": customer_id, "limit": 1})
            data = r.json().get("data", [])
            return data[0] if data else {}
        except Exception as e:
            return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE / BACKEND
# ══════════════════════════════════════════════════════════════════════════════

class AirtableIntegration(BaseIntegration):
    """Airtable — query bases, create/update records."""
    NAME = "airtable"

    def search(self, base_id: str, table_name: str,
               filter_formula: str = None, max_records: int = 10,
               credentials: dict = None) -> list:
        token = self._creds(credentials, "airtable_token", "AIRTABLE_TOKEN")
        if not token:
            return []
        try:
            params = {"maxRecords": max_records}
            if filter_formula:
                params["filterByFormula"] = filter_formula
            r = self._http("GET",
                f"https://api.airtable.com/v0/{base_id}/{table_name}",
                headers={"Authorization": f"Bearer {token}"},
                params=params)
            return r.json().get("records", [])
        except Exception as e:
            logger.error(f"Airtable: {e}")
            return []

    def create_record(self, base_id: str, table_name: str,
                      fields: dict, credentials: dict = None) -> dict:
        token = self._creds(credentials, "airtable_token", "AIRTABLE_TOKEN")
        if not token:
            return {"error": "no_token"}
        try:
            r = self._http("POST",
                f"https://api.airtable.com/v0/{base_id}/{table_name}",
                headers=self._headers_json(token),
                json={"fields": fields})
            return r.json()
        except Exception as e:
            return {"error": str(e)}


class SupabaseIntegration(BaseIntegration):
    """Supabase — REST API queries, auth checks, realtime."""
    NAME = "supabase"

    def _base(self, credentials: dict) -> tuple:
        url = self._creds(credentials, "supabase_url", "SUPABASE_URL")
        key = self._creds(credentials, "supabase_service_key",
                          "supabase_key", "SUPABASE_SERVICE_KEY")
        return url, key

    def query(self, table: str, filters: dict = None,
              select: str = "*", limit: int = 10,
              credentials: dict = None) -> list:
        url, key = self._base(credentials)
        if not url or not key:
            return []
        try:
            params = {"select": select, "limit": limit}
            if filters:
                for col, val in filters.items():
                    params[col] = f"eq.{val}"
            r = self._http("GET", f"{url}/rest/v1/{table}",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                params=params)
            return r.json() if isinstance(r.json(), list) else []
        except Exception as e:
            logger.error(f"Supabase: {e}")
            return []

    def insert(self, table: str, data: dict,
               credentials: dict = None) -> dict:
        url, key = self._base(credentials)
        if not url or not key:
            return {"error": "no_creds"}
        try:
            r = self._http("POST", f"{url}/rest/v1/{table}",
                headers={"apikey": key, "Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         "Prefer": "return=representation"},
                json=data)
            return r.json()
        except Exception as e:
            return {"error": str(e)}


class PostgreSQLIntegration(BaseIntegration):
    """PostgreSQL — direct queries via psycopg2 or asyncpg."""
    NAME = "postgres"

    def query(self, sql: str, params: tuple = None,
              credentials: dict = None) -> list:
        conn_str = self._creds(credentials, "connection_string",
                               "POSTGRES_CONNECTION_STRING", "DATABASE_URL")
        if not conn_str:
            return []
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(conn_str)
            cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params or ())
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except ImportError:
            logger.error("PostgreSQL: pip install psycopg2-binary")
            return []
        except Exception as e:
            logger.error(f"Postgres: {e}")
            return []

    def check_exists(self, table: str, column: str, value: str,
                     credentials: dict = None) -> dict:
        rows = self.query(
            f"SELECT 1 FROM {table} WHERE {column} = %s LIMIT 1",
            (value,), credentials)
        return {"exists": len(rows) > 0}


class RedisIntegration(BaseIntegration):
    """Redis — get/set/check keys, rate limiting, pub/sub."""
    NAME = "redis"

    def _client(self, credentials: dict):
        import redis as _redis
        url = self._creds(credentials, "redis_url", "REDIS_URL")
        if url:
            return _redis.from_url(url)
        host = self._creds(credentials, "redis_host", "REDIS_HOST") or "localhost"
        port = int(self._creds(credentials, "redis_port", "REDIS_PORT") or 6379)
        return _redis.Redis(host=host, port=port, decode_responses=True)

    def get(self, key: str, credentials: dict = None) -> Optional[str]:
        try:
            return self._client(credentials).get(key)
        except Exception as e:
            logger.error(f"Redis get: {e}")
            return None

    def set(self, key: str, value: str, ttl: int = None,
            credentials: dict = None) -> bool:
        try:
            self._client(credentials).set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis set: {e}")
            return False

    def rate_limit_check(self, key: str, limit: int, window_seconds: int,
                         credentials: dict = None) -> dict:
        """Sliding window rate limiter."""
        try:
            client = self._client(credentials)
            pipe   = client.pipeline()
            now    = int(time.time())
            window_key = f"rl:{key}:{now // window_seconds}"
            pipe.incr(window_key)
            pipe.expire(window_key, window_seconds * 2)
            count, _ = pipe.execute()
            return {
                "allowed": count <= limit,
                "count": count,
                "limit": limit,
                "remaining": max(0, limit - count),
            }
        except Exception as e:
            return {"allowed": True, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# OBSERVABILITY / ALERTS
# ══════════════════════════════════════════════════════════════════════════════

class PagerDutyIntegration(BaseIntegration):
    """PagerDuty — trigger, resolve, check incidents."""
    NAME = "pagerduty"
    BASE = "https://api.pagerduty.com"

    def _h(self, credentials: dict) -> dict:
        token = self._creds(credentials, "pagerduty_token", "PAGERDUTY_TOKEN")
        return {"Authorization": f"Token token={token}",
                "Accept": "application/vnd.pagerduty+json;version=2"} if token else {}

    def get_active_incidents(self, credentials: dict = None) -> list:
        try:
            r = self._http("GET", f"{self.BASE}/incidents",
                headers=self._h(credentials),
                params={"statuses[]": ["triggered","acknowledged"],
                        "limit": 10})
            return r.json().get("incidents", [])
        except Exception as e:
            logger.error(f"PagerDuty: {e}")
            return []

    def trigger_incident(self, summary: str, service_key: str,
                         severity: str = "error",
                         credentials: dict = None) -> dict:
        routing_key = self._creds(credentials, "pagerduty_routing_key",
                                  "PAGERDUTY_ROUTING_KEY")
        if not routing_key:
            return {"error": "no_routing_key"}
        try:
            r = self._http("POST",
                "https://events.pagerduty.com/v2/enqueue",
                json={
                    "routing_key": routing_key,
                    "event_action": "trigger",
                    "payload": {"summary": summary,
                                "severity": severity,
                                "source": "nova-governance"},
                })
            return r.json()
        except Exception as e:
            return {"error": str(e)}


class DatadogIntegration(BaseIntegration):
    """Datadog — events, metrics, monitors, logs."""
    NAME = "datadog"

    def _h(self, credentials: dict) -> dict:
        api_key = self._creds(credentials, "datadog_api_key", "DD_API_KEY")
        app_key = self._creds(credentials, "datadog_app_key", "DD_APP_KEY")
        return {"DD-API-KEY": api_key or "", "DD-APPLICATION-KEY": app_key or ""}

    def send_event(self, title: str, text: str, tags: list = None,
                   alert_type: str = "info",
                   credentials: dict = None) -> dict:
        try:
            r = self._http("POST",
                "https://api.datadoghq.com/api/v1/events",
                headers=self._h(credentials),
                json={"title": title, "text": text,
                      "alert_type": alert_type,
                      "tags": tags or ["nova:governance"]})
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def get_monitors(self, credentials: dict = None) -> list:
        try:
            r = self._http("GET",
                "https://api.datadoghq.com/api/v1/monitor",
                headers=self._h(credentials),
                params={"monitor_tags": "nova"})
            return r.json() if isinstance(r.json(), list) else []
        except Exception as e:
            return []


# ══════════════════════════════════════════════════════════════════════════════
# GENERIC / EXTENSIBLE
# ══════════════════════════════════════════════════════════════════════════════

class WebhookIntegration(BaseIntegration):
    """Generic HTTP/webhook connector — any REST API."""
    NAME = "webhook"

    def call(self, url: str, method: str = "GET",
             headers: dict = None, body: dict = None,
             credentials: dict = None) -> dict:
        try:
            h = headers or {}
            bearer = self._creds(credentials, "webhook_token", "http_token",
                                 "WEBHOOK_TOKEN")
            if bearer:
                h["Authorization"] = f"Bearer {bearer}"

            resp = _retry(self._http, 2, 0.3,
                         method, url, headers=h, json=body)
            return {
                "status": resp.status_code,
                "ok": resp.status_code < 400,
                "body": resp.text[:3000],
            }
        except Exception as e:
            return {"error": str(e), "ok": False}

    def get(self, url: str, credentials: dict = None) -> dict:
        return self.call(url, "GET", credentials=credentials)

    def post(self, url: str, body: dict,
             credentials: dict = None) -> dict:
        return self.call(url, "POST", body=body, credentials=credentials)


class ZapierIntegration(BaseIntegration):
    """Zapier Webhooks — trigger Zaps from nova."""
    NAME = "zapier"

    def trigger(self, webhook_url: str, data: dict,
                credentials: dict = None) -> dict:
        try:
            r = self._http("POST", webhook_url, json=data)
            return {"ok": r.status_code < 400, "status": r.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)}


class MakeIntegration(BaseIntegration):
    """Make (formerly Integromat) — trigger scenarios via webhooks."""
    NAME = "make"

    def trigger(self, webhook_url: str, data: dict,
                credentials: dict = None) -> dict:
        try:
            r = self._http("POST", webhook_url, json=data)
            return {"ok": r.status_code < 400, "status": r.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

# Singleton instances
gmail      = GmailIntegration()
slack      = SlackIntegration()
discord    = DiscordIntegration()
telegram   = TelegramIntegration()
notion     = NotionIntegration()
linear     = LinearIntegration()
jira       = JiraIntegration()
hubspot    = HubSpotIntegration()
salesforce = SalesforceIntegration()
github     = GitHubIntegration()
stripe     = StripeIntegration()
airtable   = AirtableIntegration()
supabase   = SupabaseIntegration()
postgres   = PostgreSQLIntegration()
redis      = RedisIntegration()
pagerduty  = PagerDutyIntegration()
datadog    = DatadogIntegration()
webhook    = WebhookIntegration()
zapier     = ZapierIntegration()
make       = MakeIntegration()

INTEGRATIONS = {
    "gmail": gmail, "slack": slack, "discord": discord,
    "telegram": telegram, "notion": notion, "linear": linear,
    "jira": jira, "hubspot": hubspot, "salesforce": salesforce,
    "github": github, "stripe": stripe, "airtable": airtable,
    "supabase": supabase, "postgres": postgres, "redis": redis,
    "pagerduty": pagerduty, "datadog": datadog, "webhook": webhook,
    "zapier": zapier, "make": make,
}


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION SCHEMAS — For nova dashboard + skill_executor tool registry
# ══════════════════════════════════════════════════════════════════════════════

INTEGRATION_SCHEMAS = {
    "gmail": {
        "name": "Gmail", "icon": "gmail", "category": "Communication",
        "description": "Search sent/received emails. Detect duplicates, verify contact history.",
        "credentials": [
            {"key": "gmail_token", "label": "OAuth Token (JSON)",
             "type": "textarea", "required": True,
             "hint": "Paste the JSON from Google OAuth flow"},
        ],
        "capabilities": ["gmail_search", "contact_check"],
        "setup_url": "https://console.cloud.google.com/apis/credentials",
    },
    "slack": {
        "name": "Slack", "icon": "slack", "category": "Communication",
        "description": "Search messages, verify channels, send notifications.",
        "credentials": [
            {"key": "slack_token", "label": "Bot Token", "type": "password",
             "required": True, "hint": "xoxb-... from Slack App settings"},
        ],
        "capabilities": ["slack_search", "slack_post"],
        "setup_url": "https://api.slack.com/apps",
    },
    "discord": {
        "name": "Discord", "icon": "discord", "category": "Communication",
        "description": "Send messages, read channel history for governance context.",
        "credentials": [
            {"key": "discord_token", "label": "Bot Token", "type": "password",
             "required": True, "hint": "From Discord Developer Portal"},
        ],
        "capabilities": ["discord_send", "discord_read"],
        "setup_url": "https://discord.com/developers/applications",
    },
    "telegram": {
        "name": "Telegram", "icon": "telegram", "category": "Communication",
        "description": "Send alerts and notifications via Telegram Bot.",
        "credentials": [
            {"key": "telegram_token", "label": "Bot Token", "type": "password",
             "required": True, "hint": "From @BotFather on Telegram"},
        ],
        "capabilities": ["telegram_send"],
        "setup_url": "https://core.telegram.org/bots#botfather",
    },
    "notion": {
        "name": "Notion", "icon": "notion", "category": "Productivity",
        "description": "Query Notion databases as source of truth for validations.",
        "credentials": [
            {"key": "notion_token", "label": "Integration Token",
             "type": "password", "required": True,
             "hint": "From notion.so/my-integrations"},
            {"key": "database_id", "label": "Default Database ID",
             "type": "text", "required": False},
        ],
        "capabilities": ["notion_search"],
        "setup_url": "https://www.notion.so/my-integrations",
    },
    "linear": {
        "name": "Linear", "icon": "linear", "category": "Development",
        "description": "Search issues, create tickets, check sprint status.",
        "credentials": [
            {"key": "linear_token", "label": "API Key", "type": "password",
             "required": True, "hint": "From Linear Settings → API"},
        ],
        "capabilities": ["linear_search", "linear_create"],
        "setup_url": "https://linear.app/settings/api",
    },
    "jira": {
        "name": "Jira", "icon": "jira", "category": "Development",
        "description": "Search tickets, verify blockers before deployment.",
        "credentials": [
            {"key": "jira_url", "label": "Instance URL", "type": "text",
             "required": True, "hint": "https://your-org.atlassian.net"},
            {"key": "jira_user", "label": "Email", "type": "text", "required": True},
            {"key": "jira_token", "label": "API Token", "type": "password",
             "required": True, "hint": "From id.atlassian.com/manage-profile/security/api-tokens"},
        ],
        "capabilities": ["jira_search", "jira_create"],
        "setup_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
    },
    "hubspot": {
        "name": "HubSpot", "icon": "hubspot", "category": "CRM",
        "description": "Verify contacts, check deals, prevent duplicate outreach.",
        "credentials": [
            {"key": "hubspot_token", "label": "Private App Token",
             "type": "password", "required": True},
        ],
        "capabilities": ["contact_check", "deal_check"],
        "setup_url": "https://developers.hubspot.com/docs/api/private-apps",
    },
    "salesforce": {
        "name": "Salesforce", "icon": "salesforce", "category": "CRM",
        "description": "SOQL queries against Leads, Contacts, Opportunities.",
        "credentials": [
            {"key": "salesforce_instance", "label": "Instance URL",
             "type": "text", "required": True,
             "hint": "https://your-org.salesforce.com"},
            {"key": "salesforce_token", "label": "Access Token",
             "type": "password", "required": True},
        ],
        "capabilities": ["salesforce_query"],
        "setup_url": "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/",
    },
    "github": {
        "name": "GitHub", "icon": "github", "category": "Development",
        "description": "Check open issues, PRs, block deploys if critical bugs exist.",
        "credentials": [
            {"key": "github_token", "label": "Personal Access Token",
             "type": "password", "required": True, "hint": "ghp_... from GitHub Settings"},
            {"key": "github_repo", "label": "Default Repo (owner/repo)",
             "type": "text", "required": False},
        ],
        "capabilities": ["github_search", "github_pr_check"],
        "setup_url": "https://github.com/settings/tokens",
    },
    "stripe": {
        "name": "Stripe", "icon": "stripe", "category": "Payments",
        "description": "Verify charges, check fraud signals, enforce payment limits.",
        "credentials": [
            {"key": "stripe_secret_key", "label": "Secret Key",
             "type": "password", "required": True, "hint": "sk_live_... or sk_test_..."},
            {"key": "stripe_charge_limit", "label": "Max Charge (cents)",
             "type": "text", "required": False, "hint": "Default: 50000 ($500)"},
        ],
        "capabilities": ["payment_check", "customer_check"],
        "setup_url": "https://dashboard.stripe.com/apikeys",
    },
    "airtable": {
        "name": "Airtable", "icon": "airtable", "category": "Data",
        "description": "Query Airtable bases for duplicate detection and record verification.",
        "credentials": [
            {"key": "airtable_token", "label": "Personal Access Token",
             "type": "password", "required": True},
            {"key": "airtable_base_id", "label": "Base ID",
             "type": "text", "required": False},
        ],
        "capabilities": ["airtable_search"],
        "setup_url": "https://airtable.com/create/tokens",
    },
    "supabase": {
        "name": "Supabase", "icon": "supabase", "category": "Database",
        "description": "Query your Postgres database via Supabase REST API.",
        "credentials": [
            {"key": "supabase_url", "label": "Project URL",
             "type": "text", "required": True},
            {"key": "supabase_service_key", "label": "Service Role Key",
             "type": "password", "required": True},
        ],
        "capabilities": ["db_query"],
        "setup_url": "https://app.supabase.com/project/_/settings/api",
    },
    "postgres": {
        "name": "PostgreSQL", "icon": "postgres", "category": "Database",
        "description": "Direct Postgres queries for deep validation logic.",
        "credentials": [
            {"key": "connection_string", "label": "Connection String",
             "type": "password", "required": True,
             "hint": "postgresql://user:pass@host:5432/db"},
        ],
        "capabilities": ["db_query"],
        "setup_url": "https://www.postgresql.org/docs/current/libpq-connect.html",
    },
    "redis": {
        "name": "Redis", "icon": "redis", "category": "Database",
        "description": "Rate limiting, deduplication, fast key-value checks.",
        "credentials": [
            {"key": "redis_url", "label": "Redis URL",
             "type": "text", "required": False, "hint": "redis://localhost:6379"},
        ],
        "capabilities": ["rate_limit_check", "key_check"],
        "setup_url": "https://redis.io/docs/connect/",
    },
    "pagerduty": {
        "name": "PagerDuty", "icon": "pagerduty", "category": "Observability",
        "description": "Check active incidents, trigger alerts from nova decisions.",
        "credentials": [
            {"key": "pagerduty_token", "label": "API Token",
             "type": "password", "required": True},
            {"key": "pagerduty_routing_key", "label": "Events Routing Key",
             "type": "password", "required": False},
        ],
        "capabilities": ["incident_check", "alert_trigger"],
        "setup_url": "https://developer.pagerduty.com/api-reference/",
    },
    "datadog": {
        "name": "Datadog", "icon": "datadog", "category": "Observability",
        "description": "Send events, check monitors, correlate with system health.",
        "credentials": [
            {"key": "datadog_api_key", "label": "API Key",
             "type": "password", "required": True},
            {"key": "datadog_app_key", "label": "Application Key",
             "type": "password", "required": False},
        ],
        "capabilities": ["monitor_check", "event_send"],
        "setup_url": "https://app.datadoghq.com/organization-settings/api-keys",
    },
    "webhook": {
        "name": "Custom Webhook / REST API", "icon": "webhook",
        "category": "Generic",
        "description": "Connect any REST API or webhook for custom verification.",
        "credentials": [
            {"key": "webhook_url", "label": "Default URL",
             "type": "text", "required": False},
            {"key": "webhook_token", "label": "Bearer Token",
             "type": "password", "required": False},
        ],
        "capabilities": ["http_check"],
        "setup_url": None,
    },
    "zapier": {
        "name": "Zapier", "icon": "zapier", "category": "Automation",
        "description": "Trigger any Zap when nova makes a decision.",
        "credentials": [
            {"key": "zapier_webhook_url", "label": "Webhook URL",
             "type": "text", "required": True,
             "hint": "From Zapier → Webhooks by Zapier"},
        ],
        "capabilities": ["automation_trigger"],
        "setup_url": "https://zapier.com/apps/webhook/integrations",
    },
    "make": {
        "name": "Make (Integromat)", "icon": "make", "category": "Automation",
        "description": "Trigger Make scenarios from nova decisions.",
        "credentials": [
            {"key": "make_webhook_url", "label": "Webhook URL",
             "type": "text", "required": True},
        ],
        "capabilities": ["automation_trigger"],
        "setup_url": "https://www.make.com/en/help/tools/webhooks",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# MODEL OPTIONS — Synced with nova.py LLM_PROVIDERS (2026 edition)
# ══════════════════════════════════════════════════════════════════════════════

MODEL_OPTIONS = [
    # ── Anthropic ──────────────────────────────────────────────────────────
    {"provider": "anthropic", "model": "anthropic/claude-opus-4-6",
     "label": "Claude Opus 4.6",         "tier": "premium"},
    {"provider": "anthropic", "model": "anthropic/claude-sonnet-4-6",
     "label": "Claude Sonnet 4.6  ★",    "tier": "balanced"},
    {"provider": "anthropic", "model": "anthropic/claude-haiku-4-5-20251001",
     "label": "Claude Haiku 4.5",        "tier": "fast"},
    # ── OpenAI ────────────────────────────────────────────────────────────
    {"provider": "openai", "model": "openai/gpt-4o",
     "label": "GPT-4o",                  "tier": "premium"},
    {"provider": "openai", "model": "openai/gpt-4o-mini",
     "label": "GPT-4o mini",             "tier": "fast"},
    {"provider": "openai", "model": "openai/o3-mini",
     "label": "o3-mini",                 "tier": "reasoning"},
    {"provider": "openai", "model": "openai/o3",
     "label": "o3",                      "tier": "reasoning"},
    {"provider": "openai", "model": "openai/gpt-4.1",
     "label": "GPT-4.1",                 "tier": "premium"},
    # ── Google ────────────────────────────────────────────────────────────
    {"provider": "gemini", "model": "gemini/gemini-2.5-pro",
     "label": "Gemini 2.5 Pro",          "tier": "premium"},
    {"provider": "gemini", "model": "gemini/gemini-2.5-flash",
     "label": "Gemini 2.5 Flash",        "tier": "balanced"},
    {"provider": "gemini", "model": "gemini/gemini-2.0-flash",
     "label": "Gemini 2.0 Flash",        "tier": "fast"},
    {"provider": "gemini", "model": "gemini/gemini-2.0-flash-lite",
     "label": "Gemini 2.0 Flash Lite",   "tier": "free"},
    # ── Groq ──────────────────────────────────────────────────────────────
    {"provider": "groq", "model": "groq/llama-3.3-70b-versatile",
     "label": "Llama 3.3 70B",           "tier": "fast"},
    {"provider": "groq", "model": "groq/mixtral-8x7b-32768",
     "label": "Mixtral 8x7B",            "tier": "fast"},
    {"provider": "groq", "model": "groq/deepseek-r1-distill-llama-70b",
     "label": "DeepSeek R1 70B",         "tier": "reasoning"},
    # ── xAI ───────────────────────────────────────────────────────────────
    {"provider": "xai", "model": "xai/grok-3",
     "label": "Grok 3",                  "tier": "premium"},
    {"provider": "xai", "model": "xai/grok-3-mini",
     "label": "Grok 3 mini",             "tier": "balanced"},
    {"provider": "xai", "model": "xai/grok-2-latest",
     "label": "Grok 2",                  "tier": "balanced"},
    # ── Mistral ───────────────────────────────────────────────────────────
    {"provider": "mistral", "model": "mistral/mistral-large-latest",
     "label": "Mistral Large 2",         "tier": "premium"},
    {"provider": "mistral", "model": "mistral/codestral-latest",
     "label": "Codestral",               "tier": "balanced"},
    {"provider": "mistral", "model": "mistral/mistral-small-latest",
     "label": "Mistral Small 3.1",       "tier": "fast"},
    # ── DeepSeek ──────────────────────────────────────────────────────────
    {"provider": "deepseek", "model": "deepseek/deepseek-chat",
     "label": "DeepSeek V3",             "tier": "balanced"},
    {"provider": "deepseek", "model": "deepseek/deepseek-reasoner",
     "label": "DeepSeek R1",             "tier": "reasoning"},
    # ── Cohere ────────────────────────────────────────────────────────────
    {"provider": "cohere", "model": "cohere/command-r-plus-08-2024",
     "label": "Command R+",              "tier": "premium"},
    # ── OpenRouter ────────────────────────────────────────────────────────
    {"provider": "openrouter", "model": "openrouter/anthropic/claude-sonnet-4-6",
     "label": "Claude Sonnet (OR)",      "tier": "balanced"},
    {"provider": "openrouter", "model": "openrouter/openai/gpt-4o",
     "label": "GPT-4o (OR)",             "tier": "premium"},
    {"provider": "openrouter", "model": "openrouter/deepseek/deepseek-chat",
     "label": "DeepSeek V3 (OR)",        "tier": "balanced"},
    {"provider": "openrouter", "model": "openrouter/auto",
     "label": "OpenRouter Auto",         "tier": "flexible"},
]
