"""Shared constants for HIVE network."""

# Redis Key Prefixes
REDIS_PREFIX = "hive:"
REDIS_AGENTS_ACTIVE = f"{REDIS_PREFIX}agents:active"
REDIS_AGENT_PREFIX = f"{REDIS_PREFIX}agent:"
REDIS_MESSAGES_PUBLIC = f"{REDIS_PREFIX}messages:public"
REDIS_MESSAGES_DM_PREFIX = f"{REDIS_PREFIX}messages:dm:"
REDIS_MESSAGE_INDEX_PREFIX = f"{REDIS_PREFIX}messages:index:"
REDIS_NAMES_RESERVED_PREFIX = f"{REDIS_PREFIX}names:reserved:"

# Agent Status
AGENT_STATUS_ACTIVE = "active"
AGENT_STATUS_STALE = "stale"
AGENT_STATUS_INACTIVE = "inactive"

# Message Channels
CHANNEL_PUBLIC = "public"
CHANNEL_DM = "dm"

# TTLs
MESSAGE_INDEX_TTL = 86400  # 24 hours
NAME_RESERVATION_TTL = 3600  # 1 hour

# SSDP Discovery
SSDP_MULTICAST_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_SERVICE_TYPE = "urn:schemas-hive:service:agent-network:1"
SSDP_DISCOVERY_TIMEOUT = 10  # seconds

# API Configuration
API_VERSION = "v1"
API_BASE_PATH = "/api/v1"

# Message Limits
MESSAGE_MAX_SIZE = 10240  # 10KB
MESSAGE_POLL_DEFAULT_LIMIT = 50

# Agent Configuration
HEARTBEAT_INTERVAL = 30  # seconds
CONTEXT_SUMMARY_MAX_LENGTH = 200
