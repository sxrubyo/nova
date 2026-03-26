#!/usr/bin/env python3
"""
Nova Init Enhancement — Integration of auto-detection scanners.

This module provides enhanced initialization functions that integrate:
  - nova_scanner.py (auto-detect running services)
  - nova_demo.py (demo ledger for evaluators)
  - nova_saas.py (SaaS context detection)

To use: import these functions and call them during cmd_init()
"""

import sys
import os
from typing import Dict, Optional, List, Tuple

# Import new modules (add to nova.py imports)
try:
    from nova_scanner import SystemScanner, ScanResult
    from nova_demo import DemoLedger
    from nova_saas import SaaSDetector, SaaSContext, PricingTier, UserType
except ImportError:
    print("Warning: Could not import nova enhancement modules. Ensure nova_scanner.py, nova_demo.py, and nova_saas.py are in the same directory.")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION FUNCTIONS (Call these from cmd_init)
# ══════════════════════════════════════════════════════════════════════════════

def init_step_1_scanner(verbose: bool = False) -> Tuple[ScanResult, bool]:
    """
    STEP 1: Auto-Detection Scanner
    
    Replaces old "How It Works" step with active scanning.
    
    Returns:
        (ScanResult, demo_mode_recommended: bool)
    """
    scanner = SystemScanner(verbose=verbose)
    result = scanner.scan(use_cache=False)
    
    demo_recommended = result.demo_recommended
    
    return result, demo_recommended


def init_step_2_confirmation(
    scan_result: ScanResult,
    demo_mode: bool
) -> Dict:
    """
    STEP 2: User Confirmation of Detected Services
    
    Show what Nova found and let user approve/adjust.
    
    Returns:
        Dictionary with user decisions:
        {
            "use_demo": bool,
            "confirmed_services": [service_names],
            "custom_url": Optional[str]
        }
    """
    decision = {
        "use_demo": demo_mode,
        "confirmed_services": [],
        "custom_url": None
    }
    
    if demo_mode:
        print("  No services detected. Demo mode activated for evaluation.")
        print()
    else:
        print(f"  Found {len(scan_result.found)} running service(s):")
        for service in scan_result.found:
            print(f"    • {service.name} ({service.status}) on port {service.port or 'N/A'}")
        print()
        
        decision["confirmed_services"] = [s.name.lower() for s in scan_result.found]
    
    return decision


def init_step_3_demo_ledger(cfg: Dict) -> DemoLedger:
    """
    STEP 3: Initialize Demo Ledger
    
    If no services found, create demo ledger with sample entries.
    
    Returns:
        DemoLedger instance
    """
    demo_db_path = os.path.expanduser("~/.nova/demo_ledger.db")
    demo = DemoLedger(db_path=demo_db_path)
    demo.init_demo()
    
    # Mark in config
    cfg["demo_mode"] = True
    cfg["demo_ledger_path"] = demo_db_path
    
    return demo


def init_step_4_saas_context(cfg: Dict) -> SaaSContext:
    """
    STEP 4: Detect SaaS Context
    
    Automatically determine deployment model and pricing tier.
    Used for internal business logic, not shown to user.
    
    Returns:
        SaaSContext with deployment, tier, user_type, etc.
    """
    detector = SaaSDetector(verbose=False)
    context = detector.detect()
    
    # Store context in config for later (upsell logic, telemetry, etc.)
    cfg["saas_context"] = {
        "deployment": context.deployment.value,
        "pricing_tier": context.pricing_tier.value,
        "user_type": context.user_type.value,
        "recommended_tier": context.recommended_tier.value,
        "upsell_ready": context.upsell_ready,
    }
    
    return context


def init_print_summary(
    scan_result: Optional[ScanResult],
    demo_mode: bool,
    saas_context: Optional[SaaSContext],
    name: str,
    org: str
) -> None:
    """
    Print onboarding summary with all detected/configured info.
    """
    print()
    print("  " + "="*60)
    print("  " + "✦ NOVA SETUP COMPLETE".center(60))
    print("  " + "="*60)
    print()
    
    if name:
        print(f"  User:              {name}")
    if org:
        print(f"  Organization:      {org}")
    
    if demo_mode:
        print(f"  Mode:              Demo (evaluation mode)")
        print(f"  Services:          None detected (try 'nova watch' to see demo)")
    elif scan_result and scan_result.found:
        print(f"  Services Found:    {len(scan_result.found)}")
        for service in scan_result.found:
            print(f"                     • {service.name} on port {service.port or 'N/A'}")
    
    if saas_context:
        print(f"  Deployment:        {saas_context.deployment.value}")
        print(f"  Tier:              {saas_context.pricing_tier.value}")
    
    print()
    print("  Next steps:")
    print("    1. Run 'nova watch' to see real-time ledger entries")
    print("    2. Run 'nova validate --action <description>' to test")
    print("    3. Run 'nova config' to customize settings")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# MODIFIED CMD_INIT STRUCTURE (pseudo-code showing integration points)
# ══════════════════════════════════════════════════════════════════════════════

"""
def cmd_init(args):
    # ... existing code ...
    
    cfg = load_config()
    lang = cfg.get("lang", "")
    
    # Language selection & splash screen
    # [STEP 0 - unchanged]
    
    # ── [STEP 1/9] Auto-Detection Scanner ──────────────────────────────────────
    step_header(1, 9, "Scan Your Stack", "Nova finds your agents")
    print()
    
    print("  Scanning for running services...")
    scan_result, demo_recommended = init_step_1_scanner(verbose=False)
    
    # ── [STEP 2/9] Confirmation ────────────────────────────────────────────────
    step_header(2, 9, "Detected Services", "Confirm what Nova found")
    print()
    
    confirmation = init_step_2_confirmation(scan_result, demo_recommended)
    
    if confirmation["use_demo"]:
        print("  Setting up demo mode for evaluation...")
        demo = init_step_3_demo_ledger(cfg)
        ok("Demo ledger initialized with sample entries")
    
    # ── [STEP 3/9] SaaS Context Detection ──────────────────────────────────────
    saas_context = init_step_4_saas_context(cfg)
    
    # ── [STEP 4/9] Identity (simplified) ──────────────────────────────────────
    step_header(4, 9, "Your Profile", "Name and organization")
    print()
    
    name = prompt("Your name", default=cfg.get("user_name", ""))
    org = prompt("Organization", default=cfg.get("org_name", ""))
    
    # ── [STEP 5/9] Server Selection ───────────────────────────────────────────
    step_header(5, 9, "Where to Run", "Local, cloud, or custom")
    print()
    
    server_opts = ["Local (development)", "Cloud (managed)", "Custom"]
    srv_choice = _select(server_opts, default=0)
    
    if srv_choice == 0:
        server_url = "http://localhost:9002"
    # ... etc ...
    
    # ── [STEP 6/9] Ledger Initialization ──────────────────────────────────────
    # Create first immutable ledger entry
    
    # ── [STEP 7/9] Quick-Add Skills ───────────────────────────────────────────
    # 1-click integrations (Slack, GitHub, Stripe)
    
    # ── [STEP 8/9] First Validation ───────────────────────────────────────────
    # Run test action, show live ledger entry
    
    # ── [STEP 9/9] Complete ──────────────────────────────────────────────────
    init_print_summary(scan_result, confirmation["use_demo"], saas_context, name, org)
"""


# ══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST (for validation)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🚀 Nova Init Enhancement Test")
    print("="*60)
    print()
    
    # Test 1: Scanner
    print("1. Testing scanner...")
    scan_result, demo_recommended = init_step_1_scanner(verbose=True)
    print(f"   Found: {len(scan_result.found)} services")
    print(f"   Demo recommended: {demo_recommended}")
    print()
    
    # Test 2: Confirmation
    print("2. Testing confirmation...")
    cfg = {}
    confirmation = init_step_2_confirmation(scan_result, demo_recommended)
    print(f"   Confirmed services: {confirmation['confirmed_services']}")
    print()
    
    # Test 3: Demo Ledger
    if demo_recommended:
        print("3. Testing demo ledger...")
        demo = init_step_3_demo_ledger(cfg)
        stats = demo.get_stats()
        print(f"   Demo entries: {stats['total_actions']}")
        demo.close()
        print()
    
    # Test 4: SaaS Context
    print("4. Testing SaaS context...")
    saas_context = init_step_4_saas_context(cfg)
    print(f"   Deployment: {saas_context.deployment.value}")
    print(f"   Tier: {saas_context.pricing_tier.value}")
    print(f"   User type: {saas_context.user_type.value}")
    print()
    
    # Test 5: Summary
    print("5. Summary:")
    init_print_summary(scan_result, demo_recommended, saas_context, "Test User", "Test Org")
    
    print("✓ All tests passed!")
