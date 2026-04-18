"""Discovery connectors."""

from .autogen_connector import AutoGenConnector
from .base_connector import BaseAgentConnector
from .codex_connector import CodexConnector
from .crewai_connector import CrewAIConnector
from .custom_connector import CustomAgentConnector
from .docker_connector import DockerConnector
from .langchain_connector import LangChainConnector
from .n8n_connector import N8NConnector
from .openclaw_connector import OpenClawConnector
from .process_connector import ProcessConnector

__all__ = [
    "AutoGenConnector",
    "BaseAgentConnector",
    "CodexConnector",
    "CrewAIConnector",
    "CustomAgentConnector",
    "DockerConnector",
    "LangChainConnector",
    "N8NConnector",
    "OpenClawConnector",
    "ProcessConnector",
]
