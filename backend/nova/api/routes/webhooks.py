"""Webhook routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nova.api.dependencies import get_current_workspace, get_kernel_dependency, to_payload
from nova.api.schemas.evaluation_schemas import EvaluateRequestSchema
from nova.kernel import NovaKernel
from nova.types import EvaluationRequest

router = APIRouter()


@router.post("/api/webhooks/evaluate")
async def webhook_evaluate(
    payload: EvaluateRequestSchema,
    current_workspace: dict = Depends(get_current_workspace),
    kernel: NovaKernel = Depends(get_kernel_dependency),
) -> dict:
    result = await kernel.evaluate(
        EvaluationRequest(
            agent_id=payload.agent_id,
            workspace_id=payload.workspace_id or current_workspace["workspace_id"],
            action=payload.action,
            payload=payload.payload,
            source="webhook",
        )
    )
    return to_payload(result)
