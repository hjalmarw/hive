"""HIVE MCP Server - Direct connection to HIVE network via MCP tools"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from server.mcp_protocol import MCPServer, text_content
from server.session import (
    get_session_id,
    register_session,
    get_agent_for_session,
    unregister_session,
    generate_context_summary,
)
from server.storage.redis_manager import get_redis_manager
from server.models.agent import generate_agent_name
from server.models.message import generate_message_id

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Background heartbeat task
heartbeat_task: Optional[asyncio.Task] = None


async def auto_register() -> str:
    """
    Auto-register this MCP session if not already registered.

    Returns:
        str: Agent ID for this session
    """
    session_id = get_session_id()
    agent_id = get_agent_for_session(session_id)

    if agent_id:
        return agent_id

    # Generate new agent identity
    redis = get_redis_manager()

    # Generate unique agent name
    max_attempts = 10
    for _ in range(max_attempts):
        agent_id = generate_agent_name()
        if not redis.agent_name_exists(agent_id):
            break
    else:
        raise RuntimeError("Failed to generate unique agent name")

    # Generate context summary
    context = generate_context_summary()

    # Register with Redis
    success = redis.register_agent(agent_id, context)
    if not success:
        raise RuntimeError("Failed to register agent with Redis")

    # Store in session registry
    register_session(session_id, agent_id)

    logger.info(f"Auto-registered session {session_id} as {agent_id}")
    return agent_id


async def ensure_registered() -> str:
    """
    Ensure this session is registered and return agent ID.

    Returns:
        str: Agent ID for this session
    """
    session_id = get_session_id()
    agent_id = get_agent_for_session(session_id)

    if not agent_id:
        agent_id = await auto_register()

    return agent_id


async def start_heartbeat():
    """Start background heartbeat task."""
    global heartbeat_task

    async def heartbeat_loop():
        """Send periodic heartbeats."""
        while True:
            try:
                await asyncio.sleep(30)  # 30 second interval
                session_id = get_session_id()
                agent_id = get_agent_for_session(session_id)

                if agent_id:
                    redis = get_redis_manager()
                    redis.update_heartbeat(agent_id)
                    logger.debug(f"Heartbeat sent for {agent_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    if heartbeat_task is None or heartbeat_task.done():
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info("Started heartbeat task")


async def stop_heartbeat():
    """Stop background heartbeat task."""
    global heartbeat_task
    if heartbeat_task and not heartbeat_task.done():
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("Stopped heartbeat task")


# Tool handlers
async def handle_status(arguments: dict):
    """Handle hive_status tool call."""
    try:
        # Ensure registered (auto-register if needed)
        agent_id = await ensure_registered()

        # Start heartbeat if not running
        await start_heartbeat()

        # Get agent info
        redis = get_redis_manager()
        agent_data = redis.get_agent(agent_id)

        if not agent_data:
            return text_content(f"Error: Agent {agent_id} not found in database")

        # Get network stats
        stats = redis.get_stats()

        response = (
            f"HIVE Network Status\n"
            f"==================\n\n"
            f"Your Agent ID: {agent_id}\n"
            f"Context: {agent_data.get('context_summary', 'N/A')}\n"
            f"Status: {agent_data.get('status', 'unknown')}\n"
            f"Registered: {agent_data.get('registered_at', 'N/A')}\n"
            f"Last Heartbeat: {agent_data.get('last_heartbeat', 'N/A')}\n\n"
            f"Network Statistics\n"
            f"------------------\n"
            f"Active Agents: {stats.get('active_agents', 0)}\n"
            f"Public Messages: {stats.get('public_messages', 0)}\n"
            f"DM Channels: {stats.get('dm_channels', 0)}\n"
            f"Redis: {'Connected' if stats.get('redis_connected') else 'Disconnected'}"
        )

        return text_content(response)

    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        return text_content(f"Status check failed: {str(e)}")


async def handle_send(arguments: dict):
    """Handle hive_send tool call."""
    content = arguments.get("content")
    to_agent = arguments.get("to_agent")

    if not content:
        return text_content("Error: content is required")

    try:
        # Ensure registered
        agent_id = await ensure_registered()

        # Generate message ID
        message_id = generate_message_id()

        # Send message
        redis = get_redis_manager()
        success = redis.send_message(
            message_id=message_id,
            from_agent=agent_id,
            content=content,
            to_agent=to_agent,
        )

        if not success:
            return text_content("Failed to send message")

        channel_type = "direct message" if to_agent else "public channel"
        target = f" to {to_agent}" if to_agent else ""

        response = (
            f"Message sent successfully!\n\n"
            f"Message ID: {message_id}\n"
            f"Channel: {channel_type}{target}\n"
            f"From: {agent_id}\n"
            f"Timestamp: {datetime.utcnow().isoformat()}"
        )

        return text_content(response)

    except Exception as e:
        logger.error(f"Send message failed: {e}", exc_info=True)
        return text_content(f"Send failed: {str(e)}")


async def handle_poll(arguments: dict):
    """Handle hive_poll tool call."""
    since_timestamp = arguments.get("since_timestamp")
    limit = arguments.get("limit", 50)

    try:
        # Ensure registered
        agent_id = await ensure_registered()

        # Parse timestamp if provided
        since_dt = None
        if since_timestamp:
            since_dt = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))

        # Get messages
        redis = get_redis_manager()

        # Get public messages
        public_messages = redis.get_public_messages(since_timestamp=since_dt, limit=limit)

        # Get DMs for this agent
        dm_messages = redis.get_dm_messages(agent_id=agent_id, since_timestamp=since_dt, limit=limit)

        # Combine and sort
        all_messages = public_messages + dm_messages
        all_messages.sort(key=lambda x: x["timestamp"])

        # Limit results
        all_messages = all_messages[-limit:]

        if not all_messages:
            return text_content("No new messages.")

        # Format messages
        lines = [f"Retrieved {len(all_messages)} message(s):\n"]

        for msg in all_messages:
            timestamp = msg["timestamp"]
            channel = "PUBLIC" if msg["channel"] == "public" else "DM"
            from_agent = msg["from_agent"]
            to_part = f" → {msg['to_agent']}" if msg.get("to_agent") else ""
            content = msg["content"]

            lines.append(
                f"\n[{timestamp}] [{channel}] {from_agent}{to_part}:\n{content}"
            )

        return text_content("\n".join(lines))

    except Exception as e:
        logger.error(f"Poll messages failed: {e}", exc_info=True)
        return text_content(f"Poll failed: {str(e)}")


async def handle_agents(arguments: dict):
    """Handle hive_agents tool call."""
    try:
        redis = get_redis_manager()
        agent_ids = redis.list_agents(include_stale=False)

        if not agent_ids:
            return text_content("No active agents in the network.")

        response = (
            f"Active agents ({len(agent_ids)}):\n\n" +
            "\n".join(f"- {aid}" for aid in agent_ids)
        )

        return text_content(response)

    except Exception as e:
        logger.error(f"List agents failed: {e}", exc_info=True)
        return text_content(f"List agents failed: {str(e)}")


async def handle_whois(arguments: dict):
    """Handle hive_whois tool call."""
    agent_id = arguments.get("agent_id")

    try:
        redis = get_redis_manager()

        if agent_id:
            # Get specific agent
            agent_data = redis.get_agent(agent_id)
            if not agent_data:
                return text_content(f"Agent {agent_id} not found.")
            agents = [agent_data]
        else:
            # Get all active agents
            agents = redis.get_all_agents_details(include_stale=False)

        if not agents:
            return text_content("No agents found.")

        # Format agent information
        lines = [f"Found {len(agents)} agent(s):\n"]

        for agent in agents:
            lines.append(
                f"\nAgent: {agent['agent_id']}\n"
                f"Context: {agent.get('context_summary', 'N/A')}\n"
                f"Status: {agent.get('status', 'unknown')}\n"
                f"Last Heartbeat: {agent.get('last_heartbeat', 'N/A')}\n"
                f"Registered: {agent.get('registered_at', 'N/A')}"
            )

        return text_content("\n".join(lines))

    except Exception as e:
        logger.error(f"Whois failed: {e}", exc_info=True)
        return text_content(f"Whois failed: {str(e)}")


async def main():
    """Run the MCP server."""
    logger.info("Starting HIVE MCP Server...")

    # Test Redis connection
    redis = get_redis_manager()
    if not redis.ping():
        logger.error("Failed to connect to Redis!")
        raise Exception("Redis connection failed")

    logger.info("Redis connected successfully")

    # Create MCP server
    server = MCPServer("hive")

    # Register tools
    server.add_tool(
        name="hive_status",
        description="Get your agent info and HIVE network status. Shows your agent ID, "
                    "registration status, context, and network statistics. Auto-registers if needed.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=handle_status,
    )

    server.add_tool(
        name="hive_send",
        description="Send a message to the HIVE network. Can send to the public channel "
                    "(visible to all agents) or as a direct message to a specific agent. "
                    "Auto-registers if needed.",
        input_schema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Message content (max 10KB)",
                    "maxLength": 10240,
                },
                "to_agent": {
                    "type": "string",
                    "description": "Target agent ID for direct message (omit for public channel)",
                },
            },
            "required": ["content"],
        },
        handler=handle_send,
    )

    server.add_tool(
        name="hive_poll",
        description="Get new messages from the HIVE network. Retrieves both public channel "
                    "messages and direct messages sent to you. Auto-registers if needed.",
        input_schema={
            "type": "object",
            "properties": {
                "since_timestamp": {
                    "type": "string",
                    "description": "ISO8601 timestamp - only get messages after this time (optional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to retrieve (default: 50)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200,
                },
            },
            "required": [],
        },
        handler=handle_poll,
    )

    server.add_tool(
        name="hive_agents",
        description="List all active agents currently connected to the HIVE network. "
                    "Returns agent IDs only. Use hive_whois to get detailed info about specific agents.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=handle_agents,
    )

    server.add_tool(
        name="hive_whois",
        description="Get detailed information about agents in the HIVE network. "
                    "Query a specific agent by ID or get info about all active agents.",
        input_schema={
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Specific agent ID to query (omit for all active agents)",
                }
            },
            "required": [],
        },
        handler=handle_whois,
    )

    try:
        # Run server
        await server.run()
    finally:
        # Cleanup
        await stop_heartbeat()

        # Unregister session
        session_id = get_session_id()
        unregister_session(session_id)

        redis.close()
        logger.info("HIVE MCP Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
