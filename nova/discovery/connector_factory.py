"""Factory for discovery connectors."""

from __future__ import annotations

from typing import Any

from nova.discovery.agent_manifest import DiscoveredAgent
from nova.discovery.connectors import AutoGenConnector, CodexConnector, CrewAIConnector, CustomAgentConnector, DockerConnector, LangChainConnector, N8NConnector, OpenClawConnector, ProcessConnector


CONNECTOR_MAP = {
    "codex_cli": CodexConnector,
    "n8n": N8NConnector,
    "open_interpreter": OpenClawConnector,
    "openclaw": OpenClawConnector,
    "langchain_agent": LangChainConnector,
    "crewai": CrewAIConnector,
    "autogen": AutoGenConnector,
    "generic_docker_agent": DockerConnector,
    "generic_process_agent": ProcessConnector,
}

TYPE_MAP = {
    "codex": "codex_cli",
    "codex_cli": "codex_cli",
    "n8n": "n8n",
    "openclaw": "openclaw",
    "open_interpreter": "open_interpreter",
    "langchain": "langchain_agent",
    "langchain_agent": "langchain_agent",
    "crewai": "crewai",
    "autogen": "autogen",
    "docker": "generic_docker_agent",
    "process": "generic_process_agent",
    "custom": "custom",
}


class ConnectorFactory:
    """Instantiate the right connector for a discovered or managed agent."""

    @classmethod
    def create(cls, agent: DiscoveredAgent, config: dict[str, Any] | None = None):
        connector_cls = CONNECTOR_MAP.get(agent.fingerprint_key, CustomAgentConnector)
        return connector_cls(config=config)

    @classmethod
    def fingerprint_for_type(cls, agent_type: str) -> str:
        return TYPE_MAP.get(agent_type, "custom")

    @classmethod
    def create_for_type(cls, agent_type: str, config: dict[str, Any] | None = None):
        fingerprint_key = cls.fingerprint_for_type(agent_type)
        connector_cls = CONNECTOR_MAP.get(fingerprint_key, CustomAgentConnector)
        return connector_cls(config=config)
