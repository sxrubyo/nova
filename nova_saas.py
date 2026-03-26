#!/usr/bin/env python3
"""
SaaS Context Detection for Nova OS — Auto-detect deployment model & pricing tier.

Strategic Purpose:
  - Automatically determine if Nova is running locally or in cloud
  - Infer pricing tier based on detected usage patterns
  - Enable automatic upsell logic without friction
  - Track telemetry for business intelligence
  
The Business Model:
  - Community (free self-hosted): Local Melissa + simple setup
  - Team ($49/mo cloud): Multiple agents + team_size > 3
  - Enterprise (custom): 10+ agents + high ledger volume
  
No user selects a tier — Nova recommends based on context.
"""

import os
import json
import socket
import platform
from dataclasses import dataclass
from typing import Dict, Optional, List
from pathlib import Path
from enum import Enum

# ══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

class DeploymentModel(Enum):
    """Where is Nova running?"""
    LOCAL_DEV = "local_dev"              # Running on developer machine
    LOCAL_PROD = "local_prod"            # Self-hosted on local network/server
    DOCKER = "docker"                     # Running in Docker container
    KUBERNETES = "kubernetes"             # Running in K8s cluster
    CLOUD_AWS = "cloud_aws"               # AWS deployment
    CLOUD_GCP = "cloud_gcp"               # Google Cloud deployment
    CLOUD_AZURE = "cloud_azure"           # Azure deployment
    SERVERLESS = "serverless"             # Lambda/Cloud Functions


class PricingTier(Enum):
    """Inferred pricing tier."""
    COMMUNITY = "community"               # Free, self-hosted
    TEAM = "team"                        # $49/mo, cloud
    ENTERPRISE = "enterprise"             # Custom pricing, on-prem
    TRIAL = "trial"                       # Evaluation mode


class UserType(Enum):
    """Inferred user type."""
    BUILDER = "builder"                   # Creating agents
    EVALUATOR = "evaluator"               # Monitoring/governance
    HYBRID = "hybrid"                     # Both


@dataclass
class SaaSContext:
    """Complete SaaS context detection result."""
    deployment: DeploymentModel
    pricing_tier: PricingTier
    user_type: UserType
    team_size: int                        # Inferred or configured
    agent_count: int                      # Detected agents
    ledger_volume: int                    # Approximate ledger entries
    is_containerized: bool                # Running in container
    recommended_tier: PricingTier         # What we should recommend
    upsell_ready: bool                    # Should we show upsell
    telemetry: Dict                       # Track for analytics


# ══════════════════════════════════════════════════════════════════════════════
# SAAS DETECTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class SaaSDetector:
    """Automatically detect deployment context and pricing tier."""
    
    def __init__(self, config_path: Optional[str] = None, verbose: bool = False):
        """
        Initialize SaaS detector.
        
        Args:
            config_path: Path to Nova config (default: ~/.nova/config.json)
            verbose: Enable debug output
        """
        self.config_path = config_path or str(Path.home() / ".nova" / "config.json")
        self.verbose = verbose
        self._config: Dict = {}
        self._load_config()
    
    def _load_config(self):
        """Load Nova configuration if exists."""
        try:
            with open(self.config_path) as f:
                self._config = json.load(f)
        except Exception:
            self._config = {}
    
    def detect(self) -> SaaSContext:
        """Execute full SaaS context detection."""
        
        # 1. Determine deployment model
        deployment = self._detect_deployment()
        is_containerized = deployment in (
            DeploymentModel.DOCKER,
            DeploymentModel.KUBERNETES,
            DeploymentModel.SERVERLESS,
        )
        
        # 2. Infer team size
        team_size = self._infer_team_size()
        
        # 3. Count detected agents
        agent_count = self._count_agents()
        
        # 4. Estimate ledger volume
        ledger_volume = self._estimate_ledger_volume()
        
        # 5. Infer user type
        user_type = self._infer_user_type()
        
        # 6. Infer pricing tier
        pricing_tier = self._infer_tier(team_size, agent_count, ledger_volume)
        
        # 7. Recommend tier (what they should upgrade to)
        recommended_tier = self._recommend_tier(
            pricing_tier, team_size, agent_count, deployment
        )
        
        # 8. Determine upsell readiness
        upsell_ready = self._is_upsell_ready(
            pricing_tier, team_size, agent_count, deployment
        )
        
        # 9. Collect telemetry
        telemetry = {
            "deployment": deployment.value,
            "user_type": user_type.value,
            "team_size": team_size,
            "agent_count": agent_count,
            "ledger_volume": ledger_volume,
            "detected_at": self._get_timestamp(),
        }
        
        context = SaaSContext(
            deployment=deployment,
            pricing_tier=pricing_tier,
            user_type=user_type,
            team_size=team_size,
            agent_count=agent_count,
            ledger_volume=ledger_volume,
            is_containerized=is_containerized,
            recommended_tier=recommended_tier,
            upsell_ready=upsell_ready,
            telemetry=telemetry,
        )
        
        if self.verbose:
            print(f"[saas] Detected: {deployment.value}")
            print(f"[saas] Tier: {pricing_tier.value} → {recommended_tier.value}")
            print(f"[saas] Team: {team_size}, Agents: {agent_count}, Upsell: {upsell_ready}")
        
        return context
    
    def _detect_deployment(self) -> DeploymentModel:
        """Detect where Nova is running."""
        
        # Check for containerization (Docker)
        if self._is_in_docker():
            # Check for Kubernetes
            if self._is_in_kubernetes():
                return DeploymentModel.KUBERNETES
            
            # Check for cloud environments
            if self._is_aws_lambda():
                return DeploymentModel.SERVERLESS
            if self._is_gcp_cloud_run():
                return DeploymentModel.SERVERLESS
            if self._is_azure_functions():
                return DeploymentModel.SERVERLESS
            
            # Generic docker
            return DeploymentModel.DOCKER
        
        # Check for cloud provider
        if self._is_aws_ec2():
            return DeploymentModel.CLOUD_AWS
        if self._is_gcp_instance():
            return DeploymentModel.CLOUD_GCP
        if self._is_azure_vm():
            return DeploymentModel.CLOUD_AZURE
        
        # Check for production server indicators
        if self._looks_like_prod_server():
            return DeploymentModel.LOCAL_PROD
        
        # Default: local development
        return DeploymentModel.LOCAL_DEV
    
    def _is_in_docker(self) -> bool:
        """Check if running in Docker container."""
        try:
            with open("/.dockerenv") as f:
                return True
        except FileNotFoundError:
            pass
        
        try:
            with open("/proc/self/cgroup") as f:
                content = f.read()
                return "docker" in content or "containerd" in content
        except FileNotFoundError:
            pass
        
        return False
    
    def _is_in_kubernetes(self) -> bool:
        """Check if running in Kubernetes."""
        return os.environ.get("KUBERNETES_SERVICE_HOST") is not None
    
    def _is_aws_lambda(self) -> bool:
        """Check if running in AWS Lambda."""
        return os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
    
    def _is_gcp_cloud_run(self) -> bool:
        """Check if running in Google Cloud Run."""
        return os.environ.get("K_SERVICE") is not None
    
    def _is_azure_functions(self) -> bool:
        """Check if running in Azure Functions."""
        return os.environ.get("AzureWebJobsStorage") is not None
    
    def _is_aws_ec2(self) -> bool:
        """Check if running on AWS EC2."""
        try:
            # AWS IMDSv2 check
            import urllib.request
            
            req = urllib.request.Request(
                "http://169.254.169.254/latest/meta-data/instance-id",
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
                method="HEAD",
            )
            with urllib.request.urlopen(req, timeout=1):
                return True
        except Exception:
            pass
        
        return False
    
    def _is_gcp_instance(self) -> bool:
        """Check if running on Google Cloud."""
        try:
            import urllib.request
            
            with urllib.request.urlopen(
                "http://metadata.google.internal/computeMetadata/v1/instance/id",
                timeout=1,
            ):
                return True
        except Exception:
            pass
        
        return False
    
    def _is_azure_vm(self) -> bool:
        """Check if running on Azure."""
        try:
            import urllib.request
            
            with urllib.request.urlopen(
                "http://169.254.169.254/metadata/instance?api-version=2019-06-01",
                timeout=1,
            ):
                return True
        except Exception:
            pass
        
        return False
    
    def _looks_like_prod_server(self) -> bool:
        """Check indicators of production server (nginx, systemd services, etc)."""
        indicators = [
            "/etc/systemd/",
            "/var/log/nginx/",
            "/etc/nginx/",
            "/etc/apache2/",
        ]
        
        for indicator in indicators:
            if Path(indicator).exists():
                return True
        
        return False
    
    def _infer_team_size(self) -> int:
        """Infer team size from config or environment."""
        
        # Explicit config
        if "team_size" in self._config:
            return int(self._config["team_size"])
        
        # Environment variable
        if os.environ.get("NOVA_TEAM_SIZE"):
            try:
                return int(os.environ.get("NOVA_TEAM_SIZE"))
            except ValueError:
                pass
        
        # Heuristic: check for multiple users/SSH keys
        ssh_keys_path = Path.home() / ".ssh" / "authorized_keys"
        if ssh_keys_path.exists():
            try:
                with open(ssh_keys_path) as f:
                    line_count = len(f.readlines())
                    if line_count > 1:
                        return min(10, line_count)
            except Exception:
                pass
        
        # Default: assume solo developer
        return 1
    
    def _count_agents(self) -> int:
        """Detect running agents (Melissa, n8n workflows, etc)."""
        count = 0
        
        # Check for Melissa
        if self._check_service_running(8001):
            count += 1
        
        # Check for n8n
        if self._check_service_running(5678):
            count += 1
        
        # Check environment for configured agents
        for key in os.environ:
            if "NOVA_AGENT_" in key or "AGENT_CONFIG" in key:
                count += 1
        
        # Check config file
        if "agents" in self._config:
            if isinstance(self._config["agents"], list):
                count += len(self._config["agents"])
        
        return count
    
    def _estimate_ledger_volume(self) -> int:
        """Estimate approximate ledger entries."""
        
        # Check for local ledger database
        ledger_paths = [
            Path.home() / ".nova" / "ledger.db",
            Path.home() / ".nova" / "nova.db",
            Path("/var/lib/nova/ledger.db"),
        ]
        
        for ledger_path in ledger_paths:
            if ledger_path.exists():
                try:
                    import sqlite3
                    
                    conn = sqlite3.connect(str(ledger_path))
                    cursor = conn.execute("SELECT COUNT(*) FROM ledger")
                    count = cursor.fetchone()[0]
                    conn.close()
                    return count
                except Exception:
                    pass
        
        # Default: estimate based on deployment
        if self._config.get("setup_date"):
            # Rough estimate: 100 actions/day for active instance
            from datetime import datetime
            
            setup_date = datetime.fromisoformat(self._config["setup_date"])
            days = (datetime.utcnow() - setup_date).days
            return max(1, days * 100)
        
        return 0
    
    def _infer_user_type(self) -> UserType:
        """Infer if user is builder, evaluator, or hybrid."""
        
        # Check explicit config
        if "user_type" in self._config:
            user_type_str = self._config["user_type"].lower()
            if "builder" in user_type_str:
                return UserType.BUILDER
            if "evaluator" in user_type_str:
                return UserType.EVALUATOR
            if "hybrid" in user_type_str:
                return UserType.HYBRID
        
        # Heuristic: check for demo mode (evaluator) vs real agents (builder)
        if self._config.get("mode") == "demo":
            return UserType.EVALUATOR
        
        # Heuristic: multiple agents = builder, single = evaluator
        agent_count = self._count_agents()
        if agent_count >= 2:
            return UserType.BUILDER
        if agent_count == 1:
            return UserType.HYBRID
        
        # Default: assume hybrid (safest)
        return UserType.HYBRID
    
    def _infer_tier(self, team_size: int, agent_count: int, ledger_volume: int) -> PricingTier:
        """Infer current pricing tier based on usage."""
        
        # Check explicit tier
        if "tier" in self._config:
            tier_str = self._config["tier"].lower()
            if tier_str == "enterprise":
                return PricingTier.ENTERPRISE
            if tier_str == "team":
                return PricingTier.TEAM
            if tier_str == "community":
                return PricingTier.COMMUNITY
        
        # Check if trial
        if self._config.get("trial_mode", False):
            return PricingTier.TRIAL
        
        # Heuristic inference
        if agent_count >= 10 or ledger_volume >= 10000 or team_size >= 20:
            return PricingTier.ENTERPRISE
        
        if agent_count >= 3 or ledger_volume >= 1000 or team_size >= 5:
            return PricingTier.TEAM
        
        return PricingTier.COMMUNITY
    
    def _recommend_tier(
        self,
        current_tier: PricingTier,
        team_size: int,
        agent_count: int,
        deployment: DeploymentModel,
    ) -> PricingTier:
        """Recommend next tier for upsell."""
        
        # Already enterprise: no upgrade
        if current_tier == PricingTier.ENTERPRISE:
            return PricingTier.ENTERPRISE
        
        # Growing: recommend team tier
        if agent_count >= 3 or team_size >= 5 or agent_count >= 2:
            if current_tier != PricingTier.TEAM:
                return PricingTier.TEAM
        
        # In cloud: recommend team for scaling
        if deployment in (DeploymentModel.DOCKER, DeploymentModel.KUBERNETES):
            if current_tier != PricingTier.TEAM:
                return PricingTier.TEAM
        
        # No change needed
        return current_tier
    
    def _is_upsell_ready(
        self,
        current_tier: PricingTier,
        team_size: int,
        agent_count: int,
        deployment: DeploymentModel,
    ) -> bool:
        """Determine if user is ready for upsell messaging."""
        
        # Already enterprise: no upsell
        if current_tier == PricingTier.ENTERPRISE:
            return False
        
        # Has multiple agents or team size: ready for team tier
        if agent_count >= 3 or team_size >= 5:
            return True
        
        # Running in cloud: ready for managed tier
        if deployment in (DeploymentModel.DOCKER, DeploymentModel.KUBERNETES):
            return True
        
        # After 7 days with activity: light upsell
        if self._config.get("setup_date"):
            from datetime import datetime, timedelta
            
            setup_date = datetime.fromisoformat(self._config["setup_date"])
            age_days = (datetime.utcnow() - setup_date).days
            
            if age_days >= 7 and agent_count >= 1:
                return True
        
        return False
    
    def _check_service_running(self, port: int) -> bool:
        """Check if a service is running on a port."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _get_timestamp(self) -> str:
        """Get ISO 8601 timestamp."""
        from datetime import datetime
        
        return datetime.utcnow().isoformat() + "Z"


# ══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE (for testing)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    print("\n🏗️  Nova SaaS Context Detection")
    print("=" * 50)
    print()
    
    detector = SaaSDetector(verbose=verbose)
    context = detector.detect()
    
    print(f"Deployment:      {context.deployment.value}")
    print(f"Containerized:   {context.is_containerized}")
    print(f"Current Tier:    {context.pricing_tier.value}")
    print(f"Recommended:     {context.recommended_tier.value}")
    print()
    print(f"User Type:       {context.user_type.value}")
    print(f"Team Size:       {context.team_size}")
    print(f"Agent Count:     {context.agent_count}")
    print(f"Ledger Volume:   {context.ledger_volume}")
    print()
    print(f"Upsell Ready:    {context.upsell_ready}")
    print()
    
    if context.upsell_ready:
        print(
            f"💰 Upsell Opportunity: {context.pricing_tier.value} → {context.recommended_tier.value}"
        )
    
    print()
