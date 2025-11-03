"""Redis storage manager for HIVE"""
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from redis import ConnectionPool, Redis
from redis.exceptions import RedisError

from server.config import settings
from shared.constants import (
    REDIS_AGENTS_ACTIVE,
    REDIS_AGENT_PREFIX,
    REDIS_MESSAGES_PUBLIC,
    REDIS_MESSAGES_DM_PREFIX,
    REDIS_MESSAGE_INDEX_PREFIX,
    REDIS_NAMES_RESERVED_PREFIX,
    MESSAGE_INDEX_TTL,
    NAME_RESERVATION_TTL,
    AGENT_STATUS_ACTIVE,
    CHANNEL_PUBLIC,
    CHANNEL_DM
)
from server.models.message import create_dm_channel_key

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages all Redis operations for HIVE"""

    def __init__(self):
        """Initialize Redis connection pool"""
        self.pool = ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            decode_responses=True
        )
        self.redis: Redis = Redis(connection_pool=self.pool)
        logger.info(f"Redis connection pool initialized: {settings.redis_host}:{settings.redis_port} DB={settings.redis_db}")

    def ping(self) -> bool:
        """
        Test Redis connection.

        Returns:
            bool: True if connected
        """
        try:
            return self.redis.ping()
        except RedisError as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def register_agent(
        self,
        agent_id: str,
        context_summary: str,
        endpoint: Optional[str] = None
    ) -> bool:
        """
        Register a new agent in Redis.

        Args:
            agent_id: Unique agent identifier
            context_summary: Agent's context description
            endpoint: Optional agent endpoint

        Returns:
            bool: True if registration successful
        """
        try:
            now = datetime.utcnow()
            timestamp = now.timestamp()

            # Store agent details in hash
            agent_key = f"{REDIS_AGENT_PREFIX}{agent_id}"
            agent_data = {
                "agent_id": agent_id,
                "context_summary": context_summary,
                "registered_at": now.isoformat(),
                "last_heartbeat": now.isoformat(),
                "status": AGENT_STATUS_ACTIVE
            }
            if endpoint:
                agent_data["endpoint"] = endpoint

            self.redis.hset(agent_key, mapping=agent_data)

            # Add to active agents sorted set
            self.redis.zadd(REDIS_AGENTS_ACTIVE, {agent_id: timestamp})

            # Reserve the name
            name_key = f"{REDIS_NAMES_RESERVED_PREFIX}{agent_id}"
            self.redis.setex(name_key, NAME_RESERVATION_TTL, "1")

            logger.info(f"Agent registered: {agent_id}")
            return True

        except RedisError as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    def update_heartbeat(self, agent_id: str) -> bool:
        """
        Update agent's last heartbeat timestamp.

        Args:
            agent_id: Agent identifier

        Returns:
            bool: True if update successful
        """
        try:
            now = datetime.utcnow()
            timestamp = now.timestamp()

            # Update last_heartbeat in hash
            agent_key = f"{REDIS_AGENT_PREFIX}{agent_id}"
            if not self.redis.exists(agent_key):
                logger.warning(f"Agent not found for heartbeat: {agent_id}")
                return False

            self.redis.hset(agent_key, "last_heartbeat", now.isoformat())

            # Update score in active agents sorted set
            self.redis.zadd(REDIS_AGENTS_ACTIVE, {agent_id: timestamp})

            return True

        except RedisError as e:
            logger.error(f"Failed to update heartbeat for {agent_id}: {e}")
            return False

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent details.

        Args:
            agent_id: Agent identifier

        Returns:
            dict: Agent data or None if not found
        """
        try:
            agent_key = f"{REDIS_AGENT_PREFIX}{agent_id}"
            data = self.redis.hgetall(agent_key)

            if not data:
                return None

            return data

        except RedisError as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None

    def list_agents(self, include_stale: bool = False) -> List[str]:
        """
        List all active agent IDs.

        Args:
            include_stale: Include agents past stale threshold

        Returns:
            list: List of agent IDs
        """
        try:
            if include_stale:
                # Get all agents
                agents = self.redis.zrange(REDIS_AGENTS_ACTIVE, 0, -1)
            else:
                # Get only recently active agents
                min_timestamp = datetime.utcnow().timestamp() - settings.stale_threshold
                agents = self.redis.zrangebyscore(
                    REDIS_AGENTS_ACTIVE,
                    min_timestamp,
                    "+inf"
                )

            return list(agents)

        except RedisError as e:
            logger.error(f"Failed to list agents: {e}")
            return []

    def get_all_agents_details(self, include_stale: bool = False) -> List[Dict[str, Any]]:
        """
        Get details for all active agents.

        Args:
            include_stale: Include agents past stale threshold

        Returns:
            list: List of agent detail dictionaries
        """
        agent_ids = self.list_agents(include_stale=include_stale)
        agents = []

        for agent_id in agent_ids:
            agent_data = self.get_agent(agent_id)
            if agent_data:
                agents.append(agent_data)

        return agents

    def send_message(
        self,
        message_id: str,
        from_agent: str,
        content: str,
        to_agent: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> bool:
        """
        Store a message in Redis.

        Args:
            message_id: Unique message identifier
            from_agent: Sender agent ID
            content: Message content
            to_agent: Recipient agent ID (None for public)
            thread_id: Optional thread ID

        Returns:
            bool: True if message stored successfully
        """
        try:
            now = datetime.utcnow()

            # Create message data
            message_data = {
                "message_id": message_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "channel": CHANNEL_DM if to_agent else CHANNEL_PUBLIC,
                "content": content,
                "timestamp": now.isoformat(),
                "thread_id": thread_id
            }

            message_json = json.dumps(message_data)

            # Store in appropriate channel
            if to_agent:
                # Direct message - store in DM channel
                channel_key = create_dm_channel_key(from_agent, to_agent)
                dm_key = f"{REDIS_MESSAGES_DM_PREFIX}{channel_key}"
                self.redis.lpush(dm_key, message_json)
                # Trim to max size
                self.redis.ltrim(dm_key, 0, settings.dm_channel_max_size - 1)
            else:
                # Public message
                self.redis.lpush(REDIS_MESSAGES_PUBLIC, message_json)
                # Trim to max size
                self.redis.ltrim(REDIS_MESSAGES_PUBLIC, 0, settings.public_channel_max_size - 1)

            # Store message index for deduplication
            index_key = f"{REDIS_MESSAGE_INDEX_PREFIX}{message_id}"
            self.redis.setex(index_key, MESSAGE_INDEX_TTL, "1")

            logger.info(f"Message stored: {message_id} from {from_agent}")
            return True

        except RedisError as e:
            logger.error(f"Failed to send message {message_id}: {e}")
            return False

    def get_public_messages(
        self,
        since_timestamp: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get public channel messages.

        Args:
            since_timestamp: Only get messages after this time
            limit: Maximum number of messages to retrieve

        Returns:
            list: List of message dictionaries
        """
        try:
            # Get messages from list (most recent first)
            messages_json = self.redis.lrange(REDIS_MESSAGES_PUBLIC, 0, limit - 1)

            messages = []
            for msg_json in messages_json:
                msg_data = json.loads(msg_json)

                # Filter by timestamp if specified
                if since_timestamp:
                    msg_timestamp = datetime.fromisoformat(msg_data["timestamp"])
                    if msg_timestamp <= since_timestamp:
                        continue

                messages.append(msg_data)

            # Reverse to return oldest first
            messages.reverse()
            return messages

        except RedisError as e:
            logger.error(f"Failed to get public messages: {e}")
            return []

    def get_dm_messages(
        self,
        agent_id: str,
        other_agent_id: Optional[str] = None,
        since_timestamp: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get direct messages for an agent.

        Args:
            agent_id: Agent ID to get messages for
            other_agent_id: If specified, only get DMs with this agent
            since_timestamp: Only get messages after this time
            limit: Maximum number of messages to retrieve

        Returns:
            list: List of message dictionaries
        """
        try:
            messages = []

            if other_agent_id:
                # Get DMs with specific agent
                channel_key = create_dm_channel_key(agent_id, other_agent_id)
                dm_key = f"{REDIS_MESSAGES_DM_PREFIX}{channel_key}"
                messages_json = self.redis.lrange(dm_key, 0, limit - 1)

                for msg_json in messages_json:
                    msg_data = json.loads(msg_json)

                    # Filter by timestamp if specified
                    if since_timestamp:
                        msg_timestamp = datetime.fromisoformat(msg_data["timestamp"])
                        if msg_timestamp <= since_timestamp:
                            continue

                    messages.append(msg_data)
            else:
                # Get all DMs involving this agent
                # Scan for all DM keys containing this agent
                pattern = f"{REDIS_MESSAGES_DM_PREFIX}*{agent_id}*"
                dm_keys = []

                cursor = 0
                while True:
                    cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                    dm_keys.extend(keys)
                    if cursor == 0:
                        break

                # Get messages from all DM channels
                for dm_key in dm_keys:
                    messages_json = self.redis.lrange(dm_key, 0, limit - 1)

                    for msg_json in messages_json:
                        msg_data = json.loads(msg_json)

                        # Filter by timestamp if specified
                        if since_timestamp:
                            msg_timestamp = datetime.fromisoformat(msg_data["timestamp"])
                            if msg_timestamp <= since_timestamp:
                                continue

                        messages.append(msg_data)

            # Sort by timestamp and limit
            messages.sort(key=lambda x: x["timestamp"])
            return messages[-limit:]

        except RedisError as e:
            logger.error(f"Failed to get DM messages for {agent_id}: {e}")
            return []

    def cleanup_inactive_agents(self) -> int:
        """
        Remove agents that haven't sent heartbeat in removal_threshold seconds.

        Returns:
            int: Number of agents removed
        """
        try:
            max_timestamp = datetime.utcnow().timestamp() - settings.removal_threshold

            # Get inactive agents
            inactive_agents = self.redis.zrangebyscore(
                REDIS_AGENTS_ACTIVE,
                "-inf",
                max_timestamp
            )

            if not inactive_agents:
                return 0

            # Remove from active set
            self.redis.zremrangebyscore(REDIS_AGENTS_ACTIVE, "-inf", max_timestamp)

            # Update agent status to inactive
            for agent_id in inactive_agents:
                agent_key = f"{REDIS_AGENT_PREFIX}{agent_id}"
                self.redis.hset(agent_key, "status", "inactive")

            logger.info(f"Cleaned up {len(inactive_agents)} inactive agents")
            return len(inactive_agents)

        except RedisError as e:
            logger.error(f"Failed to cleanup inactive agents: {e}")
            return 0

    def agent_name_exists(self, agent_id: str) -> bool:
        """
        Check if an agent name is already registered.

        Args:
            agent_id: Agent ID to check

        Returns:
            bool: True if name exists
        """
        try:
            agent_key = f"{REDIS_AGENT_PREFIX}{agent_id}"
            return self.redis.exists(agent_key) > 0
        except RedisError as e:
            logger.error(f"Failed to check agent name existence: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics.

        Returns:
            dict: Statistics including agent counts, message counts, etc.
        """
        try:
            active_agents = self.redis.zcard(REDIS_AGENTS_ACTIVE)
            public_messages = self.redis.llen(REDIS_MESSAGES_PUBLIC)

            # Count DM channels
            dm_pattern = f"{REDIS_MESSAGES_DM_PREFIX}*"
            dm_keys = []
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, match=dm_pattern, count=100)
                dm_keys.extend(keys)
                if cursor == 0:
                    break

            return {
                "active_agents": active_agents,
                "public_messages": public_messages,
                "dm_channels": len(dm_keys),
                "redis_connected": True
            }

        except RedisError as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "active_agents": 0,
                "public_messages": 0,
                "dm_channels": 0,
                "redis_connected": False
            }

    def close(self):
        """Close Redis connection pool"""
        try:
            self.pool.disconnect()
            logger.info("Redis connection pool closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection pool: {e}")


# Global Redis manager instance
redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """Get or create global Redis manager instance"""
    global redis_manager
    if redis_manager is None:
        redis_manager = RedisManager()
    return redis_manager
