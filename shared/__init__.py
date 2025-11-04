"""Shared utilities and models for HIVE network."""

from .models import (
    Agent,
    Message,
    RegisterRequest,
    RegisterResponse,
    UpdateContextRequest,
    UpdateContextResponse,
    SendMessageRequest,
    SendMessageResponse,
    PollMessagesResponse,
    WhoisResponse,
    ListAgentsResponse,
)
from .constants import (
    API_VERSION,
    API_BASE_PATH,
    MESSAGE_MAX_SIZE,
    CONTEXT_SUMMARY_MAX_LENGTH,
    HEARTBEAT_INTERVAL,
    AGENT_STATUS_ACTIVE,
    AGENT_STATUS_INACTIVE,
    CHANNEL_PUBLIC,
    CHANNEL_DM,
)

__all__ = [
    "Agent",
    "Message",
    "RegisterRequest",
    "RegisterResponse",
    "UpdateContextRequest",
    "UpdateContextResponse",
    "SendMessageRequest",
    "SendMessageResponse",
    "PollMessagesResponse",
    "WhoisResponse",
    "ListAgentsResponse",
    "API_VERSION",
    "API_BASE_PATH",
    "MESSAGE_MAX_SIZE",
    "CONTEXT_SUMMARY_MAX_LENGTH",
    "HEARTBEAT_INTERVAL",
    "AGENT_STATUS_ACTIVE",
    "AGENT_STATUS_INACTIVE",
    "CHANNEL_PUBLIC",
    "CHANNEL_DM",
]
