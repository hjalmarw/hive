"""MCP Session Management for HIVE"""

import os
import platform
import logging
from typing import Optional, Dict
from datetime import datetime

from server.models.agent import generate_agent_name

logger = logging.getLogger(__name__)


# Global session state: Maps session_id → agent_id
_session_registry: Dict[str, str] = {}


def get_session_id() -> str:
    """
    Get a unique session identifier for this MCP connection.
    Uses process ID as a simple session identifier.

    Returns:
        str: Session identifier
    """
    return str(os.getpid())


def register_session(session_id: str, agent_id: str):
    """
    Register a session with its agent ID.

    Args:
        session_id: Session identifier
        agent_id: Agent identifier assigned to this session
    """
    _session_registry[session_id] = agent_id
    logger.info(f"Session {session_id} registered as agent {agent_id}")


def get_agent_for_session(session_id: str) -> Optional[str]:
    """
    Get the agent ID for a given session.

    Args:
        session_id: Session identifier

    Returns:
        str: Agent ID or None if session not registered
    """
    return _session_registry.get(session_id)


def unregister_session(session_id: str):
    """
    Unregister a session.

    Args:
        session_id: Session identifier
    """
    if session_id in _session_registry:
        agent_id = _session_registry.pop(session_id)
        logger.info(f"Session {session_id} (agent {agent_id}) unregistered")


def generate_context_summary() -> str:
    """
    Generate a context summary for auto-registration.

    The summary includes:
    - Platform information
    - Working directory context
    - User/environment hints

    Returns:
        Context summary string (max 200 chars)
    """
    try:
        # Get basic environment info
        system = platform.system()
        user = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
        cwd = os.getcwd()

        # Try to determine what this agent is working on
        cwd_name = os.path.basename(cwd) if cwd else "unknown"

        # Build context string
        context_parts = []

        # Add role
        context_parts.append("Claude AI assistant")

        # Add location context
        if cwd_name and cwd_name != "unknown":
            context_parts.append(f"working in '{cwd_name}' project")

        # Add system context
        context_parts.append(f"on {system}")

        # Join with natural language
        summary = " ".join(context_parts)

        # Truncate if necessary (max 200 chars)
        if len(summary) > 200:
            summary = summary[:197] + "..."

        logger.debug(f"Generated context summary: {summary}")
        return summary

    except Exception as e:
        logger.warning(f"Failed to generate detailed context: {e}")
        # Fallback to minimal context
        return "Claude AI assistant (context unavailable)"
