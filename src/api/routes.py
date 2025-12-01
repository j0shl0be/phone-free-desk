import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


class DNDStatus(BaseModel):
    """DND status request/response model."""
    active: bool


class DNDStatusResponse(BaseModel):
    """Extended DND status response with timestamp."""
    active: bool
    last_updated: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str


# Shared state (will be injected by orchestrator)
_dnd_state = {"active": False, "last_updated": datetime.now()}


def get_dnd_state():
    """Get the current DND state dict."""
    return _dnd_state


@router.post("/dnd", response_model=DNDStatus)
async def set_dnd_status(status: DNDStatus):
    """
    Set the DND status.

    Args:
        status: DNDStatus with active boolean

    Returns:
        Confirmed DNDStatus
    """
    _dnd_state["active"] = status.active
    _dnd_state["last_updated"] = datetime.now()
    logger.info(f"DND status set to: {status.active}")
    return status


@router.get("/dnd", response_model=DNDStatusResponse)
async def get_dnd_status():
    """
    Get the current DND status.

    Returns:
        DNDStatusResponse with active status and last updated time
    """
    return DNDStatusResponse(
        active=_dnd_state["active"],
        last_updated=_dnd_state["last_updated"].isoformat()
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        HealthResponse with status and timestamp
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat()
    )
