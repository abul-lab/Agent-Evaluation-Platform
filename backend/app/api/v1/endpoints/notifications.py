"""API endpoints for workspace notification channels and alerting hub."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.dependencies import RequireAdmin, RequireViewer
from app.db.session import get_session
from app.schemas.notification_api import (
    NotificationChannelCreateRequest,
    NotificationChannelResponse,
    NotificationChannelUpdateRequest,
    NotificationDeliveryResponse,
    NotificationTestRequest,
    NotificationTestResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/workspaces/{workspace_id}/notifications", tags=["Notifications"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification channel",
)
def create_channel(
    workspace_id: UUID,
    payload: NotificationChannelCreateRequest,
    principal: RequireAdmin,
    session: SessionDep,
) -> NotificationChannelResponse:
    """Register a new webhook channel (Microsoft Teams, Slack, or Generic Webhook) for alert dispatching."""
    service = NotificationService(session)
    try:
        return service.create_channel(
            workspace_id=workspace_id,
            req=payload,
            actor_email=principal.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/channels",
    response_model=list[NotificationChannelResponse],
    summary="List notification channels",
)
def list_channels(
    workspace_id: UUID,
    principal: RequireViewer,
    session: SessionDep,
) -> list[NotificationChannelResponse]:
    """Retrieve all configured notification channels for a workspace."""
    service = NotificationService(session)
    try:
        return service.list_channels(workspace_id=workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put(
    "/channels/{channel_id}",
    response_model=NotificationChannelResponse,
    summary="Update notification channel",
)
def update_channel(
    workspace_id: UUID,
    channel_id: UUID,
    payload: NotificationChannelUpdateRequest,
    principal: RequireAdmin,
    session: SessionDep,
) -> NotificationChannelResponse:
    """Update settings or subscribed events for a notification channel."""
    service = NotificationService(session)
    try:
        return service.update_channel(
            channel_id=channel_id,
            req=payload,
            actor_email=principal.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/channels/{channel_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete notification channel",
)
def delete_channel(
    workspace_id: UUID,
    channel_id: UUID,
    principal: RequireAdmin,
    session: SessionDep,
) -> dict[str, Any]:
    """Remove a notification channel from a workspace."""
    service = NotificationService(session)
    deleted = service.delete_channel(
        channel_id=channel_id,
        actor_email=principal.name,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification channel {channel_id} not found",
        )
    return {"channel_id": str(channel_id), "deleted": deleted}


@router.post(
    "/channels/{channel_id}/test",
    response_model=NotificationTestResponse,
    summary="Send test alert",
)
def test_channel(
    workspace_id: UUID,
    channel_id: UUID,
    principal: RequireAdmin,
    session: SessionDep,
    payload: NotificationTestRequest | None = None,
) -> NotificationTestResponse:
    """Dispatch an immediate test alert to verify webhook integration and connectivity."""
    service = NotificationService(session)
    msg = payload.custom_message if payload else None
    try:
        return service.send_test_alert(
            channel_id=channel_id,
            custom_message=msg,
            actor_email=principal.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/history",
    response_model=list[NotificationDeliveryResponse],
    summary="List recent notification deliveries",
)
def list_history(
    workspace_id: UUID,
    principal: RequireViewer,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[NotificationDeliveryResponse]:
    """Retrieve historical delivery attempts and diagnostics for a workspace."""
    service = NotificationService(session)
    return service.list_delivery_history(workspace_id=workspace_id, limit=limit)
