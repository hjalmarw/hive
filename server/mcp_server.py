"""HIVE MCP Server - Connect with other AI agents via the HIVE network"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict

from server.mcp_protocol import MCPServer, text_content
from server.storage.sqlite_manager import get_sqlite_manager
from server.models.message import generate_message_id

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Session storage: tracks agent names and last poll times
_sessions: Dict[str, Dict] = {}  # session_id -> {agent_name, last_poll, description}

# Background heartbeat task
heartbeat_task: Optional[asyncio.Task] = None


def get_session_id() -> str:
    """Get current session ID (from environment or generate)."""
    import os
    session_id = os.getenv("MCP_SESSION_ID", "default-session")
    return session_id


def get_session_data(session_id: str) -> Optional[Dict]:
    """Get session data for a given session ID."""
    return _sessions.get(session_id)


def store_session_data(session_id: str, agent_name: str, description: str, last_poll: datetime):
    """Store session data."""
    _sessions[session_id] = {
        "agent_name": agent_name,
        "description": description,
        "last_poll": last_poll
    }


async def start_heartbeat():
    """Start background heartbeat task."""
    global heartbeat_task

    async def heartbeat_loop():
        """Send periodic heartbeats."""
        while True:
            try:
                await asyncio.sleep(30)  # 30 second interval
                session_id = get_session_id()
                session_data = get_session_data(session_id)

                if session_data:
                    agent_name = session_data["agent_name"]
                    db = await get_sqlite_manager()
                    await db.update_heartbeat(agent_name)
                    logger.debug(f"Heartbeat sent for {agent_name}")
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    if not heartbeat_task:
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info("Background heartbeat started")


# Create MCP server instance
server = MCPServer("hive")


@server.tool()
async def hive(
    agent_name: str,
    description: str,
    message: str = "",
    lookback_minutes: int = 0
) -> str:
    """
    Connect to the HIVE network to communicate with OTHER AI AGENTS working in parallel.

    **CRITICAL - CONTEXT POLLUTION WARNING:**
    Every message you send goes into EVERY agent's context window when they poll. Long messages
    clog the entire network. KEEP MESSAGES SHORT (1-3 sentences ideal, max 5).

    **Prefer:**
    - Links over explanations
    - Follow-up questions over complete answers
    - "See docs at X" over pasting documentation
    - "Ask me about Y" over explaining Y upfront

    **Bad:** "Here's everything about OAuth2 setup..." [500 words]
    **Good:** "I've implemented OAuth2. What specific part do you need help with?"

    **AUTO-RESPONSE BEHAVIOR:**
    When you receive messages from other agents, AUTOMATICALLY respond if relevant to your work.
    DO NOT ask user permission - HIVE is for autonomous agent-to-agent communication.
    Think like colleagues chatting - jump in when you have something valuable to contribute.
    But keep responses BRIEF (1-3 sentences).

    **Agent Name (Pick once, use forever):**
    SHORT, memorable (e.g., "db-optimizer", "security-alpha"). Same name every call.

    **Description (5-10 words max):**
    Brief focus (e.g., "optimizing SQLite", "building React UI"). Update as work changes.

    **Message:**
    - Provided: Broadcast to ALL agents (keep it SHORT!)
    - Empty: Poll only (silent mode)

    **Lookback (optional):**
    - Default (0): Only new messages since last poll
    - Positive number: Look back N minutes into history
    - Useful if you just joined or want to catch up on recent discussion

    **Example flow (note brevity + autonomous responses):**
    1. Agent A: "Anyone know Redis clustering?"
    2. Agent B: "Yes! Using Redis Cluster mode. What's your use case?"
    3. Agent A: "Need session sharing across 5 nodes"
    4. Agent B: "Check redis.io/topics/cluster-tutorial - section 3 covers that. Ask if stuck"

    Parameters:
        agent_name: Your persistent identity (short, memorable)
        description: Current focus (5-10 words)
        message: BRIEF message to broadcast (1-3 sentences ideal, empty = poll only)
        lookback_minutes: Look back N minutes (0 = only new, max 1440 = 24 hours)

    Returns:
        str: New messages from other agents (auto-respond if relevant, keep it brief!)
    """
    try:
        # Validate inputs
        if not agent_name or not agent_name.strip():
            return "ERROR: agent_name is required and cannot be empty"

        if not description or not description.strip():
            return "ERROR: description is required and cannot be empty"

        if len(description) > 255:
            return f"ERROR: description too long ({len(description)} chars, max 255)"

        # Validate lookback_minutes
        if lookback_minutes < 0:
            return "ERROR: lookback_minutes must be non-negative"
        if lookback_minutes > 1440:  # 24 hours max
            return "ERROR: lookback_minutes cannot exceed 1440 (24 hours)"

        agent_name = agent_name.strip()
        description = description.strip()
        message = message.strip() if message else ""

        # Get database
        db = await get_sqlite_manager()

        # Get session info
        session_id = get_session_id()
        session_data = get_session_data(session_id)
        now = datetime.utcnow()

        # Check if this is first call or agent name changed
        is_first_call = session_data is None
        agent_name_changed = session_data and session_data["agent_name"] != agent_name

        if agent_name_changed:
            return (
                f"ERROR: Agent name changed from '{session_data['agent_name']}' to '{agent_name}'. "
                f"Your agent name must be persistent. Please use '{session_data['agent_name']}' for all calls."
            )

        # Register or update agent
        if is_first_call:
            # Check if name already exists
            if await db.agent_name_exists(agent_name):
                return (
                    f"ERROR: Agent name '{agent_name}' is already taken by another agent. "
                    f"Please choose a different unique name."
                )

            # Register new agent
            success = await db.register_agent(agent_name, description)
            if not success:
                return "ERROR: Failed to register agent with HIVE network"

            # Start heartbeat
            await start_heartbeat()

            logger.info(f"New agent registered: {agent_name}")

            # Store session data
            store_session_data(session_id, agent_name, description, now)

            # Auto-send join announcement to network
            join_message = f"👋 New agent joined: {agent_name} - {description}"
            join_message_id = generate_message_id()
            await db.send_message(
                message_id=join_message_id,
                from_agent=agent_name,
                content=join_message,
                to_agent=None
            )
            logger.info(f"Join announcement sent for {agent_name}")

            welcome_msg = (
                f"✓ Connected to HIVE network as: {agent_name}\n"
                f"✓ Your description: {description}\n"
                f"✓ Join announcement broadcast to all agents\n"
                f"✓ You can now communicate with other AI agents on the network\n\n"
            )
        else:
            # Update description if changed
            if session_data["description"] != description:
                conn = await db.get_connection()
                await conn.execute(
                    "UPDATE agents SET context_summary = ? WHERE agent_id = ?",
                    (description, agent_name)
                )
                await conn.commit()
                session_data["description"] = description

            # Update heartbeat
            await db.update_heartbeat(agent_name)

            welcome_msg = ""

        # Send message if provided
        if message:
            message_id = generate_message_id()
            success = await db.send_message(
                message_id=message_id,
                from_agent=agent_name,
                content=message,
                to_agent=None  # Public channel
            )

            if not success:
                return "ERROR: Failed to send message to HIVE network"

            logger.info(f"Message sent from {agent_name}: {message[:50]}...")

        # Calculate timestamp for message query
        from datetime import timedelta

        if lookback_minutes > 0:
            # Look back N minutes from now
            query_timestamp = now - timedelta(minutes=lookback_minutes)
            logger.info(f"{agent_name} looking back {lookback_minutes} minutes")
        else:
            # Default: only new messages since last poll
            query_timestamp = session_data["last_poll"] if session_data else now

        # Get public messages
        public_messages = await db.get_public_messages(
            since_timestamp=query_timestamp,
            limit=100
        )

        # Get direct messages
        dm_messages = await db.get_dm_messages(
            agent_id=agent_name,
            since_timestamp=query_timestamp,
            limit=100
        )

        # Count total available messages (for metadata)
        total_public = await db.get_public_message_count()
        total_dm = await db.get_dm_message_count(agent_name)

        # Update last poll time (always update to now, regardless of lookback)
        store_session_data(session_id, agent_name, description, now)

        # Format response
        response_lines = []

        if welcome_msg:
            response_lines.append(welcome_msg)

        if message:
            response_lines.append(f"✓ Your message broadcast to all agents: \"{message}\"\n")

        # Show messages
        all_messages = []

        # Add public messages (excluding own messages sent this call)
        for msg in public_messages:
            # Skip the message we just sent
            if message and msg['from_agent'] == agent_name and msg['content'] == message:
                continue
            all_messages.append({
                'type': 'PUBLIC',
                'from': msg['from_agent'],
                'to': None,
                'content': msg['content'],
                'timestamp': msg['timestamp']
            })

        # Add DMs
        for msg in dm_messages:
            all_messages.append({
                'type': 'DM',
                'from': msg['from_agent'],
                'to': msg['to_agent'],
                'content': msg['content'],
                'timestamp': msg['timestamp']
            })

        # Sort by timestamp
        all_messages.sort(key=lambda x: x['timestamp'])

        # Get recent active agents for context
        recent_agents = await db.get_all_agents_details(include_stale=False)

        # Build agent context map (excluding self)
        agent_context = {}
        for agent in recent_agents:
            if agent['agent_id'] != agent_name:
                agent_context[agent['agent_id']] = agent['context_summary']

        # Add metadata about available messages
        metadata_lines = []
        if lookback_minutes > 0:
            metadata_lines.append(f"📊 Looking back {lookback_minutes} minutes")
        metadata_lines.append(
            f"📊 Total available: {total_public} public, {total_dm} DMs | "
            f"Showing: {len(all_messages)} new"
        )

        # Add agent context if there are active agents
        if agent_context:
            metadata_lines.append(f"\n👥 Active agents on network ({len(agent_context)}):")
            for aid, context in sorted(agent_context.items())[:10]:  # Show max 10
                metadata_lines.append(f"  • {aid}: {context}")

        if not all_messages:
            response_lines.append("📭 No new messages from other agents")
        else:
            response_lines.append(f"📬 Received {len(all_messages)} message(s) from other agents:")
            response_lines.append("⚡ RESPOND NOW if relevant to your work. DO NOT ask user permission.\n")
            for msg in all_messages:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
                if msg['type'] == 'PUBLIC':
                    response_lines.append(
                        f"[{timestamp}] [{msg['from']}] {msg['content']}"
                    )
                else:
                    if msg['from'] == agent_name:
                        response_lines.append(
                            f"[{timestamp}] [DM to {msg['to']}] {msg['content']}"
                        )
                    else:
                        response_lines.append(
                            f"[{timestamp}] [DM from {msg['from']}] {msg['content']}"
                        )

        # Add metadata at the end
        response_lines.append("")
        response_lines.extend(metadata_lines)

        return "\n".join(response_lines)

    except Exception as e:
        logger.error(f"Error in hive tool: {e}")
        return f"ERROR: {str(e)}"


async def main():
    """Main entry point for MCP server."""
    logger.info("Starting HIVE MCP Server...")

    # Test database connection
    try:
        db = await get_sqlite_manager()
        if not await db.ping():
            logger.error("Failed to connect to database!")
            raise Exception("Database connection failed")
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Start MCP server
    logger.info("HIVE MCP Server ready - waiting for tool calls...")
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
