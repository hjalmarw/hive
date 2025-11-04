"""Test SQLite database connection"""
import asyncio
import sys
from pathlib import Path

from server.storage.sqlite_manager import SQLiteManager


async def test_sqlite_connection():
    """Test connection to SQLite database"""
    print("Testing SQLite database connection...")
    print(f"Database: ./data/hive.db")
    print("-" * 50)

    try:
        # Create SQLite manager
        db = SQLiteManager()

        # Initialize database schema
        print("\nInitializing database schema...")
        await db.initialize()
        print("✓ Database schema initialized")

        # Test ping
        print("\nTesting connection...")
        result = await db.ping()
        print(f"✓ Connection successful: {result}")

        # Test agent registration
        print("\nTesting agent registration...")
        success = await db.register_agent(
            agent_id="test-agent-1234",
            context_summary="Test agent for database validation"
        )
        print(f"✓ Agent registration successful: {success}")

        # Test agent retrieval
        print("\nTesting agent retrieval...")
        agent = await db.get_agent("test-agent-1234")
        print(f"✓ Agent retrieved: {agent['agent_id']}")

        # Test message sending
        print("\nTesting message storage...")
        success = await db.send_message(
            message_id="msg-test-1234",
            from_agent="test-agent-1234",
            content="Hello from HIVE!"
        )
        print(f"✓ Message stored successfully: {success}")

        # Get database stats
        print("\nDatabase Statistics:")
        stats = await db.get_stats()
        print(f"  Active Agents: {stats.get('active_agents', 0)}")
        print(f"  Public Messages: {stats.get('public_messages', 0)}")
        print(f"  DM Channels: {stats.get('dm_channels', 0)}")
        print(f"  Database Connected: {stats.get('database_connected', False)}")

        # Get database file size
        db_path = Path(db.db_path)
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            size_kb = size_bytes / 1024
            print(f"  Database Size: {size_kb:.2f} KB")

        # Cleanup test data
        print("\nCleaning up test data...")
        conn = await db.get_connection()
        await conn.execute("DELETE FROM messages WHERE message_id = ?", ("msg-test-1234",))
        await conn.execute("DELETE FROM agents WHERE agent_id = ?", ("test-agent-1234",))
        await conn.commit()
        print("✓ Test data cleaned up")

        # Close connection
        await db.close()

        print("\n" + "=" * 50)
        print("✓ All SQLite database tests passed!")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if data directory exists")
        print("  2. Verify write permissions")
        print("  3. Check disk space")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_sqlite_connection())
    sys.exit(0 if success else 1)
