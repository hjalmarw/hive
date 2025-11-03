"""Message model and utilities"""
import secrets
from datetime import datetime
from typing import Optional, Tuple


def generate_message_id() -> str:
    """
    Generate a unique message ID.

    Format: msg_{16-char-hex}

    Returns:
        str: Generated message ID
    """
    return f"msg_{secrets.token_hex(8)}"


def create_dm_channel_key(agent1: str, agent2: str) -> str:
    """
    Create a consistent DM channel key from two agent IDs.
    Orders agents alphabetically to ensure same key regardless of who initiated.

    Args:
        agent1: First agent ID
        agent2: Second agent ID

    Returns:
        str: DM channel key in format "agent1:agent2"
    """
    agents = sorted([agent1, agent2])
    return f"{agents[0]}:{agents[1]}"


def parse_dm_channel_key(channel_key: str) -> Tuple[str, str]:
    """
    Parse a DM channel key into two agent IDs.

    Args:
        channel_key: Channel key in format "agent1:agent2"

    Returns:
        tuple: (agent1, agent2)
    """
    parts = channel_key.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid DM channel key: {channel_key}")
    return parts[0], parts[1]


def format_message_for_storage(
    message_id: str,
    from_agent: str,
    content: str,
    to_agent: Optional[str] = None,
    thread_id: Optional[str] = None,
    timestamp: Optional[datetime] = None
) -> dict:
    """
    Format message data for storage.

    Args:
        message_id: Message ID
        from_agent: Sender agent ID
        content: Message content
        to_agent: Recipient agent ID (None for public)
        thread_id: Optional thread ID
        timestamp: Message timestamp (defaults to now)

    Returns:
        dict: Formatted message data
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    return {
        "message_id": message_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "channel": "dm" if to_agent else "public",
        "content": content,
        "timestamp": timestamp.isoformat(),
        "thread_id": thread_id
    }
