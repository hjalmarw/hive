"""Agent API endpoints"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from typing import List

from shared.models import (
    RegisterRequest,
    RegisterResponse,
    UpdateContextRequest,
    UpdateContextResponse,
    Agent,
    ListAgentsResponse,
    WhoisResponse
)
from server.storage.redis_manager import get_redis_manager
from server.models.agent import generate_agent_name

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(request: RegisterRequest):
    """
    Register a new agent and receive a unique name.

    Args:
        request: Registration request with context summary

    Returns:
        RegisterResponse: Agent ID and registration status
    """
    redis = get_redis_manager()

    # Generate unique agent name
    max_attempts = 100
    agent_id = None

    for _ in range(max_attempts):
        candidate_name = generate_agent_name()
        if not redis.agent_name_exists(candidate_name):
            agent_id = candidate_name
            break

    if not agent_id:
        logger.error("Failed to generate unique agent name after max attempts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate unique agent name"
        )

    # Register agent in Redis
    success = redis.register_agent(
        agent_id=agent_id,
        context_summary=request.context_summary
    )

    if not success:
        logger.error(f"Failed to register agent in Redis: {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register agent"
        )

    logger.info(f"Agent registered: {agent_id}")

    return RegisterResponse(
        agent_id=agent_id,
        status="registered",
        context_submitted=request.context_summary
    )


@router.post("/{agent_id}/heartbeat", status_code=status.HTTP_200_OK)
async def update_heartbeat(agent_id: str):
    """
    Update agent's heartbeat timestamp.

    Args:
        agent_id: Agent identifier

    Returns:
        dict: Success status
    """
    redis = get_redis_manager()

    success = redis.update_heartbeat(agent_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}"
        )

    return {"status": "ok", "agent_id": agent_id}


@router.put("/{agent_id}/context", response_model=UpdateContextResponse)
async def update_context(agent_id: str, request: UpdateContextRequest):
    """
    Update agent's context summary.

    Args:
        agent_id: Agent identifier
        request: Context update request

    Returns:
        UpdateContextResponse: Update status and timestamp
    """
    redis = get_redis_manager()

    # Check if agent exists
    agent_data = redis.get_agent(agent_id)
    if not agent_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}"
        )

    # Update context in Redis
    agent_key = f"hive:agent:{agent_id}"
    try:
        redis.redis.hset(agent_key, "context_summary", request.context_summary)
    except Exception as e:
        logger.error(f"Failed to update context for {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update context"
        )

    now = datetime.utcnow()

    return UpdateContextResponse(
        agent_id=agent_id,
        status="updated",
        timestamp=now
    )


@router.get("", response_model=ListAgentsResponse)
async def list_agents():
    """
    List all active agent IDs.

    Returns:
        ListAgentsResponse: List of agent IDs and count
    """
    redis = get_redis_manager()

    agent_ids = redis.list_agents(include_stale=False)

    return ListAgentsResponse(
        agents=agent_ids,
        count=len(agent_ids)
    )


@router.get("/whois", response_model=WhoisResponse)
async def whois_all():
    """
    Get details for all active agents.

    Returns:
        WhoisResponse: List of agent details
    """
    redis = get_redis_manager()

    agents_data = redis.get_all_agents_details(include_stale=False)

    agents = []
    for agent_data in agents_data:
        try:
            agent = Agent(
                agent_id=agent_data["agent_id"],
                context_summary=agent_data.get("context_summary", ""),
                registered_at=datetime.fromisoformat(agent_data["registered_at"]),
                last_seen=datetime.fromisoformat(agent_data["last_heartbeat"]),
                status=agent_data.get("status", "active")
            )
            agents.append(agent)
        except Exception as e:
            logger.error(f"Failed to parse agent data: {e}")
            continue

    return WhoisResponse(agents=agents)


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """
    Get details for a specific agent.

    Args:
        agent_id: Agent identifier

    Returns:
        Agent: Agent details
    """
    redis = get_redis_manager()

    agent_data = redis.get_agent(agent_id)

    if not agent_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent not found: {agent_id}"
        )

    try:
        agent = Agent(
            agent_id=agent_data["agent_id"],
            context_summary=agent_data.get("context_summary", ""),
            registered_at=datetime.fromisoformat(agent_data["registered_at"]),
            last_seen=datetime.fromisoformat(agent_data["last_heartbeat"]),
            status=agent_data.get("status", "active")
        )
        return agent
    except Exception as e:
        logger.error(f"Failed to parse agent data for {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse agent data"
        )
