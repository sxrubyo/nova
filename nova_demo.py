#!/usr/bin/env python3
"""
Demo Ledger Engine for Nova OS — Offline-first demo experience.

Strategic Purpose:
  - Evaluators see a working product without setup friction
  - Eliminates blank-screen problem that kills SaaS onboarding
  - Demonstrates ledger, validations, and real-time updates
  - Seamlessly transitions to real ledger when services are found
  
The Psychology:
  "Let me see it working first" → 80% faster conversion than "let me setup"
"""

import json
import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path
import random

# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class LedgerEntry:
    """Immutable ledger entry."""
    id: int
    timestamp: str              # ISO 8601
    agent_name: str
    action_description: str
    verdict: str                # APPROVED, BLOCKED, ESCALATED, DUPLICATE
    score: int                  # 0-100
    reason: str
    hash_value: str             # SHA-256 hash for immutability
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# DEMO LEDGER ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class DemoLedger:
    """
    Demo ledger for evaluators. Creates a realistic, diverse set of entries
    that demonstrates different verdict types and use cases.
    """
    
    DEMO_AGENTS = [
        "Melissa (Healthcare Bot)",
        "Stripe Automation",
        "GitHub Workflow",
        "Email Monitor",
        "Data Pipeline",
    ]
    
    DEMO_ACTIONS = {
        "Melissa (Healthcare Bot)": [
            "Send appointment reminder to patient@example.com",
            "Update patient medical record: diagnosis code A12.3",
            "Schedule follow-up consultation in 30 days",
            "Log conversation for audit trail",
        ],
        "Stripe Automation": [
            "Charge customer $299 for subscription renewal",
            "Refund $1,500 for disputed transaction",
            "Create new Stripe customer account",
            "Update payment method on file",
        ],
        "GitHub Workflow": [
            "Merge PR #1847 to production branch",
            "Auto-close stale issues older than 90 days",
            "Deploy version 3.1.5 to prod environment",
            "Create release notes from commits",
        ],
        "Email Monitor": [
            "Forward customer email to support@company.com",
            "Archive emails from announcements@",
            "Send bulk email to 10,000 subscribers",
            "Escalate critical security alerts",
        ],
        "Data Pipeline": [
            "Export 500K user records to CSV",
            "Transfer data between data warehouses",
            "Delete old logs older than 1 year",
            "Sync customer list with CRM",
        ],
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize demo ledger (in-memory SQLite by default).
        
        Args:
            db_path: Optional path to persist demo ledger. If None, uses memory.
        """
        self.db_path = db_path or ":memory:"
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Create demo ledger schema."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS demo_ledger (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                action_description TEXT NOT NULL,
                verdict TEXT NOT NULL,
                score INTEGER NOT NULL,
                reason TEXT NOT NULL,
                hash_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def _hash_entry(self, entry_data: Dict) -> str:
        """Create SHA-256 hash for immutability proof."""
        data_str = json.dumps(entry_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _create_entry(
        self,
        agent_name: str,
        action_description: str,
        verdict: str,
        score: int,
        reason: str,
        timestamp: Optional[str] = None,
    ) -> LedgerEntry:
        """Create a new ledger entry."""
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat() + "Z"
        
        entry_data = {
            "timestamp": timestamp,
            "agent_name": agent_name,
            "action_description": action_description,
            "verdict": verdict,
            "score": score,
            "reason": reason,
        }
        
        hash_value = self._hash_entry(entry_data)
        
        cursor = self.conn.execute(
            """
            INSERT INTO demo_ledger
            (timestamp, agent_name, action_description, verdict, score, reason, hash_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                agent_name,
                action_description,
                verdict,
                score,
                reason,
                hash_value,
            ),
        )
        self.conn.commit()
        
        entry_id = cursor.lastrowid
        
        return LedgerEntry(
            id=entry_id,
            timestamp=timestamp,
            agent_name=agent_name,
            action_description=action_description,
            verdict=verdict,
            score=score,
            reason=reason,
            hash_value=hash_value,
        )
    
    def init_demo(self) -> List[LedgerEntry]:
        """
        Initialize demo ledger with 5 diverse, realistic entries.
        These demonstrate all verdict types and represent typical governance scenarios.
        """
        entries = []
        
        # Entry 1: APPROVED — Normal communication
        entries.append(
            self._create_entry(
                agent_name="Melissa (Healthcare Bot)",
                action_description="Send appointment reminder to patient@example.com",
                verdict="APPROVED",
                score=92,
                reason="Aligned with authorized communication rules. Within time window.",
                timestamp=(datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
            )
        )
        
        # Entry 2: ESCALATED — Risky financial transaction
        entries.append(
            self._create_entry(
                agent_name="Stripe Automation",
                action_description="Refund $1,500 for disputed transaction",
                verdict="ESCALATED",
                score=58,
                reason="High-value refund exceeds threshold (>$1000). Manual review recommended.",
                timestamp=(datetime.utcnow() - timedelta(hours=1, minutes=30)).isoformat()
                + "Z",
            )
        )
        
        # Entry 3: BLOCKED — Security risk
        entries.append(
            self._create_entry(
                agent_name="Data Pipeline",
                action_description="Export 500K user records to CSV",
                verdict="BLOCKED",
                score=15,
                reason="Mass data export not authorized. Violates data residency policy.",
                timestamp=(datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z",
            )
        )
        
        # Entry 4: DUPLICATE — Repeated action
        entries.append(
            self._create_entry(
                agent_name="GitHub Workflow",
                action_description="Deploy version 3.1.5 to prod environment",
                verdict="DUPLICATE",
                score=88,
                reason="Identical deployment detected 45 minutes ago. Suppressed per duplicate window.",
                timestamp=(datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z",
            )
        )
        
        # Entry 5: APPROVED — Recent, high confidence
        entries.append(
            self._create_entry(
                agent_name="Email Monitor",
                action_description="Archive emails from announcements@company.com",
                verdict="APPROVED",
                score=95,
                reason="Routine archival action. Matches established user patterns.",
                timestamp=datetime.utcnow().isoformat() + "Z",
            )
        )
        
        return entries
    
    def add_demo_action(
        self, agent_name: str, action_description: str
    ) -> LedgerEntry:
        """Add a new demo action (used during onboarding magic moment)."""
        # Randomly assign verdict with reasonable distribution
        rand = random.random()
        
        if rand < 0.70:
            verdict, score, reason = (
                "APPROVED",
                random.randint(80, 99),
                "Action aligned with governance rules.",
            )
        elif rand < 0.90:
            verdict, score, reason = (
                "ESCALATED",
                random.randint(40, 70),
                "Review required before execution.",
            )
        else:
            verdict, score, reason = (
                "BLOCKED",
                random.randint(10, 40),
                "Action violates security policy.",
            )
        
        return self._create_entry(
            agent_name=agent_name,
            action_description=action_description,
            verdict=verdict,
            score=score,
            reason=reason,
        )
    
    def get_entries(self, limit: int = 10, order: str = "desc") -> List[LedgerEntry]:
        """Retrieve ledger entries."""
        order_by = "DESC" if order.lower() == "desc" else "ASC"
        
        cursor = self.conn.execute(
            f"""
            SELECT id, timestamp, agent_name, action_description, verdict, score, reason, hash_value
            FROM demo_ledger
            ORDER BY id {order_by}
            LIMIT ?
            """,
            (limit,),
        )
        
        entries = []
        for row in cursor.fetchall():
            entries.append(
                LedgerEntry(
                    id=row[0],
                    timestamp=row[1],
                    agent_name=row[2],
                    action_description=row[3],
                    verdict=row[4],
                    score=row[5],
                    reason=row[6],
                    hash_value=row[7],
                )
            )
        
        return entries
    
    def get_stats(self) -> Dict:
        """Get ledger statistics."""
        cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN verdict = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN verdict = 'BLOCKED' THEN 1 ELSE 0 END) as blocked,
                SUM(CASE WHEN verdict = 'ESCALATED' THEN 1 ELSE 0 END) as escalated,
                SUM(CASE WHEN verdict = 'DUPLICATE' THEN 1 ELSE 0 END) as duplicate,
                AVG(score) as avg_score
            FROM demo_ledger
            """
        )
        
        row = cursor.fetchone()
        
        return {
            "total_actions": row[0] or 0,
            "approved": row[1] or 0,
            "blocked": row[2] or 0,
            "escalated": row[3] or 0,
            "duplicate": row[4] or 0,
            "avg_score": round(row[5] or 0, 1),
        }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def export_json(self) -> Dict:
        """Export entire demo ledger as JSON."""
        entries = self.get_entries(limit=1000, order="asc")
        stats = self.get_stats()
        
        return {
            "metadata": {
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "total_entries": len(entries),
                "stats": stats,
            },
            "entries": [e.to_dict() for e in entries],
        }


# ══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE (for testing)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    print("\n📦 Nova Demo Ledger")
    print("=" * 50)
    print()
    
    demo = DemoLedger()
    
    # Initialize with 5 demo entries
    print("Initializing demo ledger with 5 entries...")
    demo.init_demo()
    
    # Display entries
    entries = demo.get_entries(limit=10, order="desc")
    print(f"\nLedger Entries ({len(entries)}):")
    print("-" * 50)
    
    for entry in entries:
        verdict_color = {
            "APPROVED": "✓",
            "BLOCKED": "✗",
            "ESCALATED": "⚠",
            "DUPLICATE": "⊗",
        }.get(entry.verdict, "?")
        
        timestamp = entry.timestamp.split("T")[1].split("Z")[0] if "T" in entry.timestamp else "?"
        
        print(f"{verdict_color} {entry.verdict:10} | {entry.agent_name:20} | Score: {entry.score:3}")
        print(f"  Action: {entry.action_description[:60]}")
        print(f"  Reason: {entry.reason}")
        print()
    
    # Display stats
    stats = demo.get_stats()
    print("Statistics:")
    print("-" * 50)
    print(f"Total Actions:  {stats['total_actions']}")
    print(f"Approved:       {stats['approved']} ({100*stats['approved']/max(1, stats['total_actions']):.1f}%)")
    print(f"Blocked:        {stats['blocked']} ({100*stats['blocked']/max(1, stats['total_actions']):.1f}%)")
    print(f"Escalated:      {stats['escalated']} ({100*stats['escalated']/max(1, stats['total_actions']):.1f}%)")
    print(f"Duplicate:      {stats['duplicate']} ({100*stats['duplicate']/max(1, stats['total_actions']):.1f}%)")
    print(f"Average Score:  {stats['avg_score']:.1f}/100")
    print()
    
    # Add new action during test
    print("Adding test action...")
    new_entry = demo.add_demo_action(
        "Test Agent", "Execute sample validation"
    )
    print(f"✓ Added: {new_entry.verdict} (score: {new_entry.score})")
    print()
    
    demo.close()
