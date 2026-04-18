"""Discovery and universal agent management routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from nova.api.dependencies import get_current_workspace, get_kernel_dependency, to_payload
from nova.api.schemas.discovery_schemas import DiscoveryConnectRequest, DiscoveryTaskRequest
from nova.discovery.agent_manifest import AgentTask
from nova.kernel import NovaKernel

router = APIRouter()


@router.get("/api/discovery/scan")
async def scan(
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    agents = await kernel.discovery.scan(force=True)
    return {
        "agents": [to_payload(agent) for agent in agents],
        "last_scan_at": kernel.discovery.last_scan_at,
        "duration_ms": kernel.discovery.last_scan_duration_ms,
    }


@router.get("/api/discovery/agents")
async def list_discovered_agents(
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    agents = await kernel.discovery.scan(force=False)
    return {
        "agents": [to_payload(agent) for agent in agents],
        "last_scan_at": kernel.discovery.last_scan_at,
        "duration_ms": kernel.discovery.last_scan_duration_ms,
    }


@router.post("/api/discovery/agents/{agent_key}/connect")
async def connect_discovered_agent(
    agent_key: str,
    payload: DiscoveryConnectRequest | None = Body(default=None),
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    result = await kernel.discovery.connect(
        agent_key=agent_key,
        workspace_id=current_workspace["workspace_id"],
        config=payload.config if payload else {},
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "failed to connect agent")
    return to_payload(result)


@router.delete("/api/discovery/agents/{agent_key}/disconnect")
async def disconnect_discovered_agent(
    agent_key: str,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    if not await kernel.discovery.disconnect(agent_key):
        raise HTTPException(status_code=404, detail="agent not connected")
    return {"disconnected": True, "agent_key": agent_key}


@router.get("/api/discovery/agents/{agent_key}/status")
async def discovered_agent_status(
    agent_key: str,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    status = await kernel.discovery.get_status(agent_key)
    if status.get("error"):
        raise HTTPException(status_code=404, detail=status["error"])
    return to_payload(status)


@router.post("/api/discovery/agents/{agent_key}/task")
async def send_discovery_task(
    agent_key: str,
    payload: DiscoveryTaskRequest,
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    result = await kernel.discovery.send_task(
        agent_key=agent_key,
        workspace_id=current_workspace["workspace_id"],
        task=AgentTask(
            prompt=payload.prompt,
            model=payload.model,
            payload=payload.payload,
            approval_mode=payload.approval_mode,
            working_directory=payload.working_directory,
            timeout=payload.timeout,
        ),
    )
    return to_payload(result)


@router.get("/api/discovery/agents/{agent_key}/logs")
async def discovered_agent_logs(
    agent_key: str,
    limit: int = 100,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> list[dict]:
    return await kernel.discovery.get_logs(agent_key, limit=limit)


@router.post("/api/discovery/agents/{agent_key}/pause")
async def pause_discovered_agent(
    agent_key: str,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    return {"paused": await kernel.discovery.pause(agent_key), "agent_key": agent_key}


@router.post("/api/discovery/agents/{agent_key}/resume")
async def resume_discovered_agent(
    agent_key: str,
    _: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    return {"resumed": await kernel.discovery.resume(agent_key), "agent_key": agent_key}
