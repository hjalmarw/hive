"""Test Redis connection"""
import redis
import sys

def test_redis_connection():
    """Test connection to Redis server"""
    print("Testing Redis connection...")
    print(f"Host: 192.168.1.17")
    print(f"Port: 32771")
    print(f"DB: 5")
    print("-" * 50)

    try:
        # Create Redis client
        r = redis.Redis(
            host='192.168.1.17',
            port=32771,
            db=5,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True
        )

        # Test ping
        print("Testing PING...")
        result = r.ping()
        print(f"✓ PING successful: {result}")

        # Test set/get
        print("\nTesting SET/GET...")
        test_key = "hive:test:connection"
        test_value = "Hello from HIVE!"
        r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
        retrieved = r.get(test_key)
        print(f"✓ SET/GET successful: {retrieved}")

        # Clean up test key
        r.delete(test_key)
        print(f"✓ Cleanup successful")

        # Get Redis info
        print("\nRedis Server Info:")
        info = r.info('server')
        print(f"  Redis Version: {info.get('redis_version', 'unknown')}")
        print(f"  OS: {info.get('os', 'unknown')}")
        print(f"  Uptime (days): {info.get('uptime_in_days', 'unknown')}")

        # Get memory info
        memory_info = r.info('memory')
        used_memory_mb = memory_info.get('used_memory', 0) / (1024 * 1024)
        print(f"  Used Memory: {used_memory_mb:.2f} MB")

        # Get keyspace info
        keyspace = r.info('keyspace')
        db5_info = keyspace.get('db5', 'No keys in DB 5')
        print(f"  DB 5 Info: {db5_info}")

        print("\n" + "=" * 50)
        print("✓ All Redis connection tests passed!")
        print("=" * 50)
        return True

    except redis.ConnectionError as e:
        print(f"\n✗ Connection Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if Redis server is running")
        print("  2. Verify network connectivity to 192.168.1.17")
        print("  3. Confirm Redis is listening on port 32771")
        print("  4. Check firewall rules")
        return False

    except redis.TimeoutError as e:
        print(f"\n✗ Timeout Error: {e}")
        print("\nThe connection timed out. Redis may be slow or unreachable.")
        return False

    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        return False


if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)
