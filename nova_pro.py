"""
Nova Pro Foundation — OpenRouter connectivity + Auto-Repair core.
Minimal scaffolding for future expansion.
"""

import os
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import urllib.request
import urllib.error


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/auto"


@dataclass
class OpenRouterConfig:
    api_key: str
    base_url: str = OPENROUTER_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_s: int = 60


class OpenRouterClient:
    """Thin OpenRouter client for chat completions."""

    def __init__(self, cfg: OpenRouterConfig):
        self.cfg = cfg

    def chat(self, messages: List[Dict[str, str]], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
        }
        if extra:
            payload.update(extra)

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.cfg.base_url}/chat/completions",
            data=body,
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.cfg.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8") if e.fp else str(e)
            return {"error": "http_error", "status": e.code, "detail": detail}
        except Exception as e:
            return {"error": "request_failed", "detail": str(e)}


@dataclass
class RepairIssue:
    title: str
    details: str
    severity: str = "medium"  # low | medium | high


class AutoRepairEngine:
    """Basic auto-repair skeleton with local heuristics."""

    def __init__(self):
        self.last_run_ts = 0.0

    def diagnose(self) -> List[RepairIssue]:
        issues: List[RepairIssue] = []
        # Placeholder for future probes: config sanity, permissions, connectivity.
        return issues

    def repair(self, issues: List[RepairIssue]) -> Dict[str, Any]:
        results = []
        for issue in issues:
            results.append({
                "title": issue.title,
                "status": "skipped",
                "notes": "Auto-repair not implemented for this issue yet.",
            })
        return {"ok": True, "results": results}

    def run(self) -> Dict[str, Any]:
        self.last_run_ts = time.time()
        issues = self.diagnose()
        return self.repair(issues)


def load_openrouter_config() -> Optional[OpenRouterConfig]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return OpenRouterConfig(api_key=api_key, model=model)


def example_usage() -> Dict[str, Any]:
    cfg = load_openrouter_config()
    if not cfg:
        return {"error": "missing_api_key"}

    client = OpenRouterClient(cfg)
    return client.chat([
        {"role": "system", "content": "You are Nova Pro."},
        {"role": "user", "content": "Ping"},
    ])
