"""Connector registry routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nova.api.dependencies import get_current_workspace
from nova.connector_registry import build_connector_inventory

router = APIRouter()


@router.get("/api/connectors")
async def list_connectors(_: dict = Depends(get_current_workspace)) -> dict:
    return build_connector_inventory()
