#!/usr/bin/env python3
"""
Auto-Detection Scanner for Nova OS — Detects running agents and services.

Strategic Purpose:
  - Makes Nova the active scanner, not a passive prompter
  - Auto-detects Melissa (port 8001), n8n (port 5678), local Python agents
  - Eliminates setup friction: users don't "connect" — Nova finds them
  - Creates the foundation for viral growth (as Vercel detects Next.js automatically)
"""

import socket
import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import urllib.request
import urllib.error

# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DetectedService:
    """Represents a detected service/agent."""
    name: str              # "Melissa", "n8n", "Custom Agent"
    service_type: str      # "agent", "workflow", "api", "process"
    port: Optional[int]    # Port number if applicable
    url: Optional[str]     # Full URL if available
    status: str            # "running", "configured", "available"
    metadata: Dict         # Additional context
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "service_type": self.service_type,
            "port": self.port,
            "url": self.url,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class ScanResult:
    """Results of the scanner sweep."""
    found: List[DetectedService]      # Confirmed running services
    suggested: List[Dict]             # Services with partial matches (env vars, configs)
    demo_recommended: bool            # True if no services found
    scan_time_ms: float               # Time taken for scan
    
    def to_dict(self) -> Dict:
        return {
            "found": [s.to_dict() for s in self.found],
            "suggested": self.suggested,
            "demo_recommended": self.demo_recommended,
            "scan_time_ms": self.scan_time_ms,
        }


# ══════════════════════════════════════════════════════════════════════════════
# CORE SCANNER ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class SystemScanner:
    """Auto-detection engine for Nova services."""
    
    # Common ports to scan
    COMMON_PORTS = {
        "melissa": 8001,
        "melissa-alt": 8000,
        "n8n": 5678,
        "api": 8080,
        "uvicorn": 8000,
        "flask": 5000,
    }
    
    # Service detection definitions
    SERVICES = {
        "melissa": {
            "ports": [8001, 8000],
            "env_prefix": "MELISSA_",
            "process_names": ["melissa", "melissa.py"],
            "health_endpoint": "/health",
        },
        "n8n": {
            "ports": [5678],
            "env_prefix": "N8N_",
            "process_names": ["n8n", "n8n-cli"],
            "health_endpoint": "/rest/health",
        },
        "nova": {
            "ports": [9001],
            "env_prefix": "NOVA_",
            "process_names": ["nova"],
            "health_endpoint": "/health",
        },
    }
    
    def __init__(self, timeout: float = 2.0, verbose: bool = False):
        self.timeout = timeout
        self.verbose = verbose
        self._cache: Dict[str, ScanResult] = {}
        self._cache_time: Dict[str, float] = {}
    
    def scan(self, use_cache: bool = True) -> ScanResult:
        """
        Execute full scan for running services.
        
        Strategy:
          1. Check environment variables (NOVA_*, MELISSA_*, etc.)
          2. Scan common ports with HTTP health checks
          3. Scan running processes
          4. Parse .env files in common locations
          5. Combine results and return
        """
        cache_key = "full_scan"
        
        # Return cached result if valid (5 min TTL)
        if use_cache and cache_key in self._cache:
            if (time.time() - self._cache_time.get(cache_key, 0)) < 300:
                if self.verbose:
                    print("[scanner] Using cached scan result")
                return self._cache[cache_key]
        
        start_time = time.time()
        
        found: List[DetectedService] = []
        suggested: List[Dict] = []
        
        # 1. Check environment variables
        env_matches = self._scan_env_vars()
        found.extend(env_matches)
        
        # 2. Scan ports
        port_matches = self._scan_ports()
        found.extend(port_matches)
        
        # 3. Check running processes
        process_matches = self._scan_processes()
        found.extend(process_matches)
        
        # 4. Parse .env files
        env_file_matches = self._scan_env_files()
        suggested.extend(env_file_matches)
        
        # 5. Deduplicate (keep best version of each service)
        found = self._deduplicate_services(found)
        
        # Determine if demo mode should be recommended
        demo_recommended = len(found) == 0 and len(suggested) == 0
        
        scan_time_ms = (time.time() - start_time) * 1000
        
        result = ScanResult(
            found=found,
            suggested=suggested,
            demo_recommended=demo_recommended,
            scan_time_ms=scan_time_ms,
        )
        
        # Cache result
        self._cache[cache_key] = result
        self._cache_time[cache_key] = time.time()
        
        return result
    
    def _scan_env_vars(self) -> List[DetectedService]:
        """Detect services from environment variables."""
        found = []
        
        for service_name, config in self.SERVICES.items():
            prefix = config["env_prefix"]
            env_vars = {k: v for k, v in os.environ.items() if k.startswith(prefix)}
            
            if env_vars:
                # Found env vars for this service
                url = env_vars.get(f"{prefix}URL") or env_vars.get(f"{prefix}API_URL")
                
                service = DetectedService(
                    name=service_name.upper(),
                    service_type="api",
                    port=None,
                    url=url,
                    status="configured",
                    metadata={
                        "source": "environment",
                        "env_count": len(env_vars),
                        "keys": list(env_vars.keys()),
                    }
                )
                found.append(service)
                
                if self.verbose:
                    print(f"[scanner] Found {service_name} via env vars: {len(env_vars)} keys")
        
        return found
    
    def _scan_ports(self) -> List[DetectedService]:
        """Scan common ports with HTTP health checks."""
        found = []
        
        for service_name, config in self.SERVICES.items():
            for port in config["ports"]:
                if self._check_port(port, service_name, config):
                    url = f"http://localhost:{port}"
                    
                    service = DetectedService(
                        name=service_name.upper(),
                        service_type="api",
                        port=port,
                        url=url,
                        status="running",
                        metadata={
                            "source": "port_scan",
                            "health_endpoint": config.get("health_endpoint"),
                        }
                    )
                    found.append(service)
                    
                    if self.verbose:
                        print(f"[scanner] Found {service_name} on port {port}")
        
        return found
    
    def _check_port(self, port: int, service_name: str, config: Dict) -> bool:
        """Check if a service is running on a specific port."""
        try:
            # Try socket connection first (fast fail)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            
            if result != 0:
                return False
            
            # Port is open, try health endpoint
            health_ep = config.get("health_endpoint", "/health")
            url = f"http://localhost:{port}{health_ep}"
            
            try:
                req = urllib.request.Request(url, method="GET")
                req.add_header("Connection", "close")
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    return response.status in (200, 204)
            except (urllib.error.URLError, urllib.error.HTTPError, Exception):
                # Port is open but no health endpoint, still valid
                return True
        
        except Exception as e:
            if self.verbose:
                print(f"[scanner] Error checking port {port}: {e}")
            return False
    
    def _scan_processes(self) -> List[DetectedService]:
        """Detect running processes by name."""
        found = []
        
        try:
            # Use 'ps' on Unix-like systems
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            ps_output = result.stdout
        except Exception:
            if self.verbose:
                print("[scanner] Could not read process list")
            return found
        
        for service_name, config in self.SERVICES.items():
            for proc_name in config["process_names"]:
                if proc_name in ps_output:
                    service = DetectedService(
                        name=service_name.upper(),
                        service_type="process",
                        port=None,
                        url=None,
                        status="running",
                        metadata={
                            "source": "process_scan",
                            "process_name": proc_name,
                        }
                    )
                    found.append(service)
                    
                    if self.verbose:
                        print(f"[scanner] Found {service_name} process: {proc_name}")
        
        return found
    
    def _scan_env_files(self) -> List[Dict]:
        """Parse .env files in common locations."""
        suggested = []
        
        env_paths = [
            Path.home() / ".env",
            Path.home() / ".nova" / "config.json",
            Path("/etc/nova/.env"),
            Path.cwd() / ".env",
        ]
        
        for env_path in env_paths:
            if not env_path.exists():
                continue
            
            try:
                if env_path.name == ".env":
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("NOVA_") or line.startswith("MELISSA_"):
                                suggested.append({
                                    "source": "env_file",
                                    "path": str(env_path),
                                    "line": line.split("=")[0] if "=" in line else line,
                                })
                
                elif env_path.name == "config.json":
                    with open(env_path) as f:
                        config = json.load(f)
                        if "server" in config or "api_key" in config:
                            suggested.append({
                                "source": "config_file",
                                "path": str(env_path),
                                "keys": list(config.keys()),
                            })
            except Exception as e:
                if self.verbose:
                    print(f"[scanner] Error reading {env_path}: {e}")
        
        return suggested
    
    def _deduplicate_services(
        self, services: List[DetectedService]
    ) -> List[DetectedService]:
        """Deduplicate services, keeping the best (running > configured > process)."""
        by_name: Dict[str, DetectedService] = {}
        
        status_priority = {"running": 3, "configured": 2, "process": 1}
        
        for service in services:
            key = service.name.lower()
            
            if key not in by_name:
                by_name[key] = service
            else:
                # Keep the one with higher status priority
                current_priority = status_priority.get(service.status, 0)
                existing_priority = status_priority.get(by_name[key].status, 0)
                
                if current_priority > existing_priority:
                    by_name[key] = service
        
        return list(by_name.values())
    
    def scan_melissa(self) -> Optional[DetectedService]:
        """Convenience method: scan specifically for Melissa."""
        result = self.scan(use_cache=True)
        for service in result.found:
            if "melissa" in service.name.lower():
                return service
        return None
    
    def scan_n8n(self) -> Optional[DetectedService]:
        """Convenience method: scan specifically for n8n."""
        result = self.scan(use_cache=True)
        for service in result.found:
            if "n8n" in service.name.lower():
                return service
        return None
    
    def clear_cache(self):
        """Clear cached scan results."""
        self._cache.clear()
        self._cache_time.clear()


# ══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE (for testing)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    scanner = SystemScanner(verbose=verbose)
    
    print("\n🔍 Nova System Scanner")
    print("=" * 50)
    print()
    
    result = scanner.scan()
    
    print(f"Scan Time: {result.scan_time_ms:.1f}ms")
    print()
    
    if result.found:
        print("✓ Found Services:")
        for service in result.found:
            print(f"  • {service.name} ({service.status}) on port {service.port or 'N/A'}")
            if service.url:
                print(f"    URL: {service.url}")
            if service.metadata:
                print(f"    Source: {service.metadata.get('source', 'unknown')}")
        print()
    else:
        print("✗ No services detected")
        print()
    
    if result.suggested:
        print(f"💡 Suggested ({len(result.suggested)} found):")
        for sugg in result.suggested:
            print(f"  • {sugg.get('source', 'unknown')}: {sugg.get('path', sugg.get('line', '?'))}")
        print()
    
    if result.demo_recommended:
        print("📦 No services detected. Demo mode recommended for evaluation.")
        print()
    
    print(f"Summary: {len(result.found)} running, {len(result.suggested)} configured")
