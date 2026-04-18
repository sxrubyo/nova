"""Regex-based sensitive data detection without third-party services."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from nova.types import SensitivityFinding, SensitivityResult
from nova.utils.text import flatten_payload

API_KEY_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"sk-ant-[a-zA-Z0-9]{20,}",
    r"AIza[a-zA-Z0-9_-]{35}",
    r"ghp_[a-zA-Z0-9]{36}",
    r"xoxb-[0-9]{10,}",
    r"AKIA[A-Z0-9]{16}",
    r"[a-zA-Z0-9]{32,}_secret_[a-zA-Z0-9]+",
]

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b.*?\b\d{3}-\d{3}-\d{4}\b",
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b",
]

CREDENTIAL_PATTERNS = [
    r"password\s*[=:]\s*\S+",
    r"passwd\s*[=:]\s*\S+",
    r"token\s*[=:]\s*\S+",
    r"secret\s*[=:]\s*\S+",
    r"Bearer\s+[a-zA-Z0-9._-]+",
    r"Basic\s+[a-zA-Z0-9+/=]+",
]

FINANCIAL_PATTERNS = [
    r"\b(?:visa|mastercard|amex)\b",
    r"\b(?:routing|iban|swift)\b",
    r"\b\d{9,18}\b",
]


@dataclass(slots=True)
class PatternGroup:
    name: str
    patterns: list[str]


class SensitivityScanner:
    """Scans payloads for secrets, PII, credentials, and financial data."""

    GROUPS = [
        PatternGroup(name="api_key", patterns=API_KEY_PATTERNS),
        PatternGroup(name="pii", patterns=PII_PATTERNS),
        PatternGroup(name="credential", patterns=CREDENTIAL_PATTERNS),
        PatternGroup(name="financial", patterns=FINANCIAL_PATTERNS),
    ]

    async def scan(self, payload: Any, patterns: list[str] | None = None) -> SensitivityResult:
        payload_text = flatten_payload(payload)
        findings: list[SensitivityFinding] = []
        flags: list[str] = []
        for group in self.GROUPS:
            if patterns and group.name not in patterns and group.name not in {"password", "credit_card", "email_pii", "phone"}:
                continue
            group_found = False
            for pattern in group.patterns:
                for match in re.finditer(pattern, payload_text, re.IGNORECASE):
                    group_found = True
                    findings.append(SensitivityFinding(flag=group.name, start=match.start(), end=match.end()))
            if group_found:
                flags.append(group.name)
        severity = "none"
        if len(flags) == 1:
            severity = "medium" if flags[0] in {"pii", "financial"} else "high"
        elif len(flags) > 1:
            severity = "critical"
        preview = payload_text
        for finding in reversed(findings):
            preview = f"{preview[:finding.start]}[REDACTED]{preview[finding.end:]}"
        return SensitivityResult(flags=flags, findings=findings, severity=severity, redacted_preview=preview[:400])
