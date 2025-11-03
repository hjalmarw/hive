"""Shared data models for HIVE network."""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Agent(BaseModel):
    """Agent information model."""
    agent_id: str
    context_summary: str
    registered_at: datetime
    last_seen: datetime
    status: str = "active"


class Message(BaseModel):
    """Message model."""
    message_id: str
    from_agent: str
    to_agent: Optional[str] = None  # None for public channel
    channel: str  # "public" or "dm"
    content: str
    timestamp: datetime
    thread_id: Optional[str] = None


class RegisterRequest(BaseModel):
    """Agent registration request."""
    context_summary: str = Field(..., max_length=200)


class RegisterResponse(BaseModel):
    """Agent registration response."""
    agent_id: str
    status: str
    context_submitted: str


class UpdateContextRequest(BaseModel):
    """Context update request."""
    context_summary: str = Field(..., max_length=200)


class UpdateContextResponse(BaseModel):
    """Context update response."""
    agent_id: str
    status: str
    timestamp: datetime


class SendMessageRequest(BaseModel):
    """Send message request."""
    content: str = Field(..., max_length=10240)
    to_agent: Optional[str] = None
    thread_id: Optional[str] = None


class SendMessageResponse(BaseModel):
    """Send message response."""
    message_id: str
    status: str
    timestamp: datetime


class PollMessagesResponse(BaseModel):
    """Poll messages response."""
    messages: List[Message]
    has_more: bool


class WhoisResponse(BaseModel):
    """Whois response."""
    agents: List[Agent]


class ListAgentsResponse(BaseModel):
    """List agents response."""
    agents: List[str]
    count: int
