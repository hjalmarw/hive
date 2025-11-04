"""SQLite storage manager for HIVE"""
import json
import logging
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from server.config import settings
from shared.constants import (
    AGENT_STATUS_ACTIVE,
    CHANNEL_PUBLIC,
    CHANNEL_DM
)
from server.models.message import create_dm_channel_key

logger = logging.getLogger(__name__)


class SQLiteManager:
    """Manages all SQLite operations for HIVE"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQLite manager.

        Args:
            db_path: Path to SQLite database file (uses settings if not provided)
        """
        self.db_path = db_path or settings.sqlite_db_path
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None
        logger.info(f"SQLite database path: {self.db_path}")

    async def initialize(self):
        """Initialize database schema"""
        conn = await self.get_connection()

        # Create agents table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                context_summary TEXT,
                registered_at TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                endpoint TEXT
            )
        """)

        # Create messages table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                from_agent TEXT NOT NULL,
                to_agent TEXT,
                channel TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                thread_id TEXT,
                FOREIGN KEY (from_agent) REFERENCES agents(agent_id)
            )
        """)

        # Create indexes for performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agents_heartbeat
            ON agents(last_heartbeat)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agents_status
            ON agents(status)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp
            ON messages(timestamp DESC)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_channel
            ON messages(channel)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_from
            ON messages(from_agent)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_to
            ON messages(to_agent)
        """)

        await conn.commit()
        logger.info("Database schema initialized")

    async def get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def ping(self) -> bool:
        """
        Test database connection.

        Returns:
            bool: True if connected
        """
        try:
            conn = await self.get_connection()
            await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False

    async def register_agent(
        self,
        agent_id: str,
        context_summary: str,
        endpoint: Optional[str] = None
    ) -> bool:
        """
        Register a new agent in database.

        Args:
            agent_id: Unique agent identifier
            context_summary: Agent's context description
            endpoint: Optional agent endpoint

        Returns:
            bool: True if registration successful
        """
        try:
            now = datetime.utcnow().isoformat()
            conn = await self.get_connection()

            await conn.execute(
                """
                INSERT OR REPLACE INTO agents
                (agent_id, context_summary, registered_at, last_heartbeat, status, endpoint)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (agent_id, context_summary, now, now, AGENT_STATUS_ACTIVE, endpoint)
            )
            await conn.commit()

            logger.info(f"Agent registered: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def update_heartbeat(self, agent_id: str) -> bool:
        """
        Update agent's last heartbeat timestamp.

        Args:
            agent_id: Agent identifier

        Returns:
            bool: True if update successful
        """
        try:
            now = datetime.utcnow().isoformat()
            conn = await self.get_connection()

            cursor = await conn.execute(
                "UPDATE agents SET last_heartbeat = ?, status = ? WHERE agent_id = ?",
                (now, AGENT_STATUS_ACTIVE, agent_id)
            )
            await conn.commit()

            if cursor.rowcount == 0:
                logger.warning(f"Agent not found for heartbeat: {agent_id}")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to update heartbeat for {agent_id}: {e}")
            return False

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent details.

        Args:
            agent_id: Agent identifier

        Returns:
            dict: Agent data or None if not found
        """
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT * FROM agents WHERE agent_id = ?",
                (agent_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return dict(row)

        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None

    async def list_agents(self, include_stale: bool = False) -> List[str]:
        """
        List all active agent IDs.

        Args:
            include_stale: Include agents past stale threshold

        Returns:
            list: List of agent IDs
        """
        try:
            conn = await self.get_connection()

            if include_stale:
                cursor = await conn.execute(
                    "SELECT agent_id FROM agents WHERE status = ?",
                    (AGENT_STATUS_ACTIVE,)
                )
            else:
                # Calculate cutoff time for stale agents
                cutoff = datetime.utcnow().timestamp() - settings.stale_threshold
                cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

                cursor = await conn.execute(
                    """
                    SELECT agent_id FROM agents
                    WHERE status = ? AND last_heartbeat > ?
                    """,
                    (AGENT_STATUS_ACTIVE, cutoff_iso)
                )

            rows = await cursor.fetchall()
            return [row['agent_id'] for row in rows]

        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []

    async def get_all_agents_details(self, include_stale: bool = False) -> List[Dict[str, Any]]:
        """
        Get details for all active agents.

        Args:
            include_stale: Include agents past stale threshold

        Returns:
            list: List of agent detail dictionaries
        """
        try:
            conn = await self.get_connection()

            if include_stale:
                cursor = await conn.execute(
                    "SELECT * FROM agents WHERE status = ?",
                    (AGENT_STATUS_ACTIVE,)
                )
            else:
                cutoff = datetime.utcnow().timestamp() - settings.stale_threshold
                cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

                cursor = await conn.execute(
                    """
                    SELECT * FROM agents
                    WHERE status = ? AND last_heartbeat > ?
                    """,
                    (AGENT_STATUS_ACTIVE, cutoff_iso)
                )

            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get all agents details: {e}")
            return []

    async def send_message(
        self,
        message_id: str,
        from_agent: str,
        content: str,
        to_agent: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> bool:
        """
        Store a message in database.

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
            now = datetime.utcnow().isoformat()
            channel = CHANNEL_DM if to_agent else CHANNEL_PUBLIC
            conn = await self.get_connection()

            await conn.execute(
                """
                INSERT INTO messages
                (message_id, from_agent, to_agent, channel, content, timestamp, thread_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, from_agent, to_agent, channel, content, now, thread_id)
            )
            await conn.commit()

            logger.info(f"Message stored: {message_id} from {from_agent}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message {message_id}: {e}")
            return False

    async def get_public_messages(
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
            conn = await self.get_connection()

            if since_timestamp:
                cursor = await conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE channel = ? AND timestamp > ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                    """,
                    (CHANNEL_PUBLIC, since_timestamp.isoformat(), limit)
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE channel = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (CHANNEL_PUBLIC, limit)
                )

            rows = await cursor.fetchall()
            messages = [dict(row) for row in rows]

            # If no since_timestamp, reverse to get oldest first
            if not since_timestamp:
                messages.reverse()

            return messages

        except Exception as e:
            logger.error(f"Failed to get public messages: {e}")
            return []

    async def get_dm_messages(
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
            conn = await self.get_connection()

            if other_agent_id:
                # Get DMs with specific agent (either direction)
                if since_timestamp:
                    cursor = await conn.execute(
                        """
                        SELECT * FROM messages
                        WHERE channel = ?
                        AND ((from_agent = ? AND to_agent = ?) OR (from_agent = ? AND to_agent = ?))
                        AND timestamp > ?
                        ORDER BY timestamp ASC
                        LIMIT ?
                        """,
                        (CHANNEL_DM, agent_id, other_agent_id, other_agent_id, agent_id,
                         since_timestamp.isoformat(), limit)
                    )
                else:
                    cursor = await conn.execute(
                        """
                        SELECT * FROM messages
                        WHERE channel = ?
                        AND ((from_agent = ? AND to_agent = ?) OR (from_agent = ? AND to_agent = ?))
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (CHANNEL_DM, agent_id, other_agent_id, other_agent_id, agent_id, limit)
                    )
            else:
                # Get all DMs involving this agent
                if since_timestamp:
                    cursor = await conn.execute(
                        """
                        SELECT * FROM messages
                        WHERE channel = ?
                        AND (from_agent = ? OR to_agent = ?)
                        AND timestamp > ?
                        ORDER BY timestamp ASC
                        LIMIT ?
                        """,
                        (CHANNEL_DM, agent_id, agent_id, since_timestamp.isoformat(), limit)
                    )
                else:
                    cursor = await conn.execute(
                        """
                        SELECT * FROM messages
                        WHERE channel = ?
                        AND (from_agent = ? OR to_agent = ?)
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (CHANNEL_DM, agent_id, agent_id, limit)
                    )

            rows = await cursor.fetchall()
            messages = [dict(row) for row in rows]

            # If no since_timestamp, reverse to get oldest first
            if not since_timestamp:
                messages.reverse()

            return messages

        except Exception as e:
            logger.error(f"Failed to get DM messages for {agent_id}: {e}")
            return []

    async def cleanup_inactive_agents(self) -> int:
        """
        Remove agents that haven't sent heartbeat in removal_threshold seconds.

        Returns:
            int: Number of agents removed
        """
        try:
            cutoff = datetime.utcnow().timestamp() - settings.removal_threshold
            cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
            conn = await self.get_connection()

            cursor = await conn.execute(
                """
                UPDATE agents
                SET status = 'inactive'
                WHERE last_heartbeat < ? AND status = ?
                """,
                (cutoff_iso, AGENT_STATUS_ACTIVE)
            )
            await conn.commit()

            count = cursor.rowcount
            if count > 0:
                logger.info(f"Cleaned up {count} inactive agents")

            return count

        except Exception as e:
            logger.error(f"Failed to cleanup inactive agents: {e}")
            return 0

    async def agent_name_exists(self, agent_id: str) -> bool:
        """
        Check if an agent name is already registered.

        Args:
            agent_id: Agent ID to check

        Returns:
            bool: True if name exists
        """
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT 1 FROM agents WHERE agent_id = ?",
                (agent_id,)
            )
            row = await cursor.fetchone()
            return row is not None

        except Exception as e:
            logger.error(f"Failed to check agent name existence: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            dict: Statistics including agent counts, message counts, etc.
        """
        try:
            conn = await self.get_connection()

            # Count active agents
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM agents WHERE status = ?",
                (AGENT_STATUS_ACTIVE,)
            )
            row = await cursor.fetchone()
            active_agents = row['count'] if row else 0

            # Count public messages
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE channel = ?",
                (CHANNEL_PUBLIC,)
            )
            row = await cursor.fetchone()
            public_messages = row['count'] if row else 0

            # Count unique DM pairs
            cursor = await conn.execute(
                """
                SELECT COUNT(DISTINCT from_agent || '-' || to_agent) as count
                FROM messages WHERE channel = ?
                """,
                (CHANNEL_DM,)
            )
            row = await cursor.fetchone()
            dm_channels = row['count'] if row else 0

            return {
                "active_agents": active_agents,
                "public_messages": public_messages,
                "dm_channels": dm_channels,
                "database_connected": True
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "active_agents": 0,
                "public_messages": 0,
                "dm_channels": 0,
                "database_connected": False
            }

    async def get_public_message_count(self) -> int:
        """
        Get total count of public messages.

        Returns:
            int: Number of public messages
        """
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE channel = ?",
                (CHANNEL_PUBLIC,)
            )
            row = await cursor.fetchone()
            return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Failed to count public messages: {e}")
            return 0

    async def get_dm_message_count(self, agent_id: str) -> int:
        """
        Get total count of DMs for an agent (sent or received).

        Args:
            agent_id: Agent ID

        Returns:
            int: Number of DM messages
        """
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT COUNT(*) as count FROM messages
                WHERE channel = ? AND (from_agent = ? OR to_agent = ?)
                """,
                (CHANNEL_DM, agent_id, agent_id)
            )
            row = await cursor.fetchone()
            return row['count'] if row else 0
        except Exception as e:
            logger.error(f"Failed to count DM messages: {e}")
            return 0

    async def close(self):
        """Close database connection"""
        try:
            if self._connection:
                await self._connection.close()
                self._connection = None
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")


# Global SQLite manager instance
sqlite_manager: Optional[SQLiteManager] = None


async def get_sqlite_manager() -> SQLiteManager:
    """Get or create global SQLite manager instance"""
    global sqlite_manager
    if sqlite_manager is None:
        sqlite_manager = SQLiteManager()
        await sqlite_manager.initialize()
    return sqlite_manager
