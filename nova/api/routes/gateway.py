"""Gateway routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nova.api.dependencies import get_current_workspace, get_kernel_dependency
from nova.kernel import NovaKernel

router = APIRouter()

PROVIDER_CATALOG = {
    "openai": {"label": "OpenAI", "logo": "/llm-brands/openai.svg"},
    "anthropic": {"label": "Anthropic", "logo": "/llm-brands/anthropic.svg"},
    "gemini": {"label": "Gemini", "logo": "/llm-brands/gemini.svg"},
    "groq": {"label": "Groq", "logo": "/llm-brands/groq.svg"},
    "openrouter": {"label": "OpenRouter", "logo": "/llm-brands/openrouter.svg"},
    "xai": {"label": "xAI", "logo": "/llm-brands/xai.svg"},
    "mistral": {"label": "Mistral", "logo": "/llm-brands/mistral.svg"},
    "deepseek": {"label": "DeepSeek", "logo": "/llm-brands/deepseek.png"},
    "cohere": {"label": "Cohere", "logo": "/llm-brands/cohere.svg"},
}


@router.get("/api/gateway/status")
async def gateway_status(_: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return {"providers": kernel.gateway.status()}


@router.get("/api/gateway/latency")
async def gateway_latency(_: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    return {"latency_ms": kernel.metrics.provider_snapshot()}


@router.get("/api/assistant/models")
async def assistant_models(_: dict = Depends(get_current_workspace), kernel: NovaKernel = Depends(get_kernel_dependency)) -> dict:
    providers = []
    for key, provider in kernel.gateway.providers.items():
        catalog = PROVIDER_CATALOG.get(key, {"label": key.title(), "logo": None})
        providers.append(
            {
                "key": key,
                "label": catalog["label"],
                "logo": catalog["logo"],
                "available": provider.configured,
                "default_model": provider.models[0] if provider.models else None,
                "models": [{"id": model, "label": model} for model in provider.models],
            }
        )
    return {"providers": providers}
