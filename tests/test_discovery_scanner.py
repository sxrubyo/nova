"""Discovery scanner confirmation rules."""

from __future__ import annotations

from nova.discovery.agent_manifest import DiscoveredAgent
from nova.discovery.scanner import SystemScanner


def discovered_agent(
    fingerprint_key: str,
    *,
    detection_methods: list[str],
    is_running: bool = False,
    is_healthy: bool | None = None,
) -> DiscoveredAgent:
    agent = DiscoveredAgent(
        agent_key=f"{fingerprint_key}-test",
        fingerprint_key=fingerprint_key,
        name=fingerprint_key,
        type="test",
        confidence=0.7,
        detection_method=detection_methods[0],
        detection_methods=[],
        metadata={},
    )
    for method in detection_methods:
        agent.add_evidence(method, f"{method}-detail", 0.7)
    agent.is_running = is_running
    agent.is_healthy = is_healthy
    return agent


def test_filter_confirmed_agents_requires_multiple_signals_for_ambiguous_runtimes() -> None:
    scanner = SystemScanner()

    langchain_port_only = discovered_agent("langchain_agent", detection_methods=["port"], is_running=True, is_healthy=True)
    n8n_confirmed = discovered_agent("n8n", detection_methods=["config_file", "docker"], is_running=True, is_healthy=True)
    openclaw_installed = discovered_agent("openclaw", detection_methods=["config_file", "binary"])
    generic_container = discovered_agent("generic_docker_agent", detection_methods=["docker"], is_running=True, is_healthy=True)

    confirmed = scanner._filter_confirmed_agents(
        [langchain_port_only, n8n_confirmed, openclaw_installed, generic_container]
    )
    confirmed_keys = {agent.fingerprint_key for agent in confirmed}

    assert "langchain_agent" not in confirmed_keys
    assert "generic_docker_agent" not in confirmed_keys
    assert "n8n" in confirmed_keys
    assert "openclaw" in confirmed_keys

    n8n_metadata = next(agent.metadata for agent in confirmed if agent.fingerprint_key == "n8n")
    assert n8n_metadata["matched_signals"] == 2
    assert n8n_metadata["required_matches"] == 2
    assert n8n_metadata["logo_path"] == "/agent-logos/n8n.svg"
