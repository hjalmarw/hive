"""Message API endpoints"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional

from shared.models import (
    SendMessageRequest,
    SendMessageResponse,
    Message,
    PollMessagesResponse
)
from server.storage.sqlite_manager import get_sqlite_manager
from server.models.message import generate_message_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/public", response_model=SendMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_public_message(from_agent: str, request: SendMessageRequest):
    """
    Send a message to the public channel.

    Args:
        from_agent: Sender agent ID (query parameter)
        request: Message content and optional thread_id

    Returns:
        SendMessageResponse: Message ID and timestamp
    """
    db = await get_sqlite_manager()

    # Verify agent exists
    agent = await db.get_agent(from_agent)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {from_agent}"
        )

    # Generate message ID
    message_id = generate_message_id()
    now = datetime.utcnow()

    # Store message
    success = await db.send_message(
        message_id=message_id,
        from_agent=from_agent,
        content=request.content,
        to_agent=None,  # Public channel
        thread_id=request.thread_id
    )

    if not success:
        logger.error(f"Failed to send public message from {from_agent}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

    logger.info(f"Public message sent: {message_id} from {from_agent}")

    return SendMessageResponse(
        message_id=message_id,
        status="sent",
        timestamp=now
    )


@router.post("/dm", response_model=SendMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_direct_message(from_agent: str, to_agent: str, request: SendMessageRequest):
    """
    Send a direct message to a specific agent.

    Args:
        from_agent: Sender agent ID (query parameter)
        to_agent: Recipient agent ID (query parameter)
        request: Message content and optional thread_id

    Returns:
        SendMessageResponse: Message ID and timestamp
    """
    db = await get_sqlite_manager()

    # Verify sender exists
    sender = await db.get_agent(from_agent)
    if not sender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sender agent not found: {from_agent}"
        )

    # Verify recipient exists
    recipient = await db.get_agent(to_agent)
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient agent not found: {to_agent}"
        )

    # Generate message ID
    message_id = generate_message_id()
    now = datetime.utcnow()

    # Store message
    success = await db.send_message(
        message_id=message_id,
        from_agent=from_agent,
        content=request.content,
        to_agent=to_agent,
        thread_id=request.thread_id
    )

    if not success:
        logger.error(f"Failed to send DM from {from_agent} to {to_agent}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

    logger.info(f"DM sent: {message_id} from {from_agent} to {to_agent}")

    return SendMessageResponse(
        message_id=message_id,
        status="sent",
        timestamp=now
    )


@router.get("/public", response_model=PollMessagesResponse)
async def get_public_messages(
    since_timestamp: Optional[str] = Query(None, description="ISO format timestamp"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages")
):
    """
    Get messages from the public channel.

    Args:
        since_timestamp: Only get messages after this timestamp (ISO format)
        limit: Maximum number of messages to retrieve (1-100)

    Returns:
        PollMessagesResponse: List of messages and has_more flag
    """
    db = await get_sqlite_manager()

    # Parse timestamp if provided
    since_dt = None
    if since_timestamp:
        try:
            since_dt = datetime.fromisoformat(since_timestamp)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp format. Use ISO format (e.g., 2025-11-03T10:30:00)"
            )

    # Get messages
    messages_data = await db.get_public_messages(
        since_timestamp=since_dt,
        limit=limit
    )

    # Convert to Message objects
    messages = []
    for msg_data in messages_data:
        try:
            message = Message(
                message_id=msg_data["message_id"],
                from_agent=msg_data["from_agent"],
                to_agent=msg_data.get("to_agent"),
                channel=msg_data["channel"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                thread_id=msg_data.get("thread_id")
            )
            messages.append(message)
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            continue

    return PollMessagesResponse(
        messages=messages,
        has_more=len(messages) >= limit
    )


@router.get("/dm/{agent_id}", response_model=PollMessagesResponse)
async def get_direct_messages(
    agent_id: str,
    other_agent_id: Optional[str] = Query(None, description="Filter by specific agent"),
    since_timestamp: Optional[str] = Query(None, description="ISO format timestamp"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages")
):
    """
    Get direct messages for an agent.

    Args:
        agent_id: Agent ID to get messages for
        other_agent_id: Optional - only get DMs with this specific agent
        since_timestamp: Only get messages after this timestamp (ISO format)
        limit: Maximum number of messages to retrieve (1-100)

    Returns:
        PollMessagesResponse: List of messages and has_more flag
    """
    db = await get_sqlite_manager()

    # Verify agent exists
    agent = await db.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}"
        )

    # Parse timestamp if provided
    since_dt = None
    if since_timestamp:
        try:
            since_dt = datetime.fromisoformat(since_timestamp)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp format. Use ISO format (e.g., 2025-11-03T10:30:00)"
            )

    # Get messages
    messages_data = await db.get_dm_messages(
        agent_id=agent_id,
        other_agent_id=other_agent_id,
        since_timestamp=since_dt,
        limit=limit
    )

    # Convert to Message objects
    messages = []
    for msg_data in messages_data:
        try:
            message = Message(
                message_id=msg_data["message_id"],
                from_agent=msg_data["from_agent"],
                to_agent=msg_data.get("to_agent"),
                channel=msg_data["channel"],
                content=msg_data["content"],
                timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                thread_id=msg_data.get("thread_id")
            )
            messages.append(message)
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            continue

    return PollMessagesResponse(
        messages=messages,
        has_more=len(messages) >= limit
    )
