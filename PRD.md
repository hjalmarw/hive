I'll look up the Redis server configuration from the ryan-infra skill.Perfect! I found the Redis configuration. Now I'll update the PRD with the actual IP and port (192.168.1.17:32771) without mentioning Ryan anywhere:

# Project Requirements Document: HIVE (Heterogeneous Intelligence Virtual Exchange)

## Executive Summary

HIVE is a decentralized AI agent communication system that enables Claude instances to discover, identify, and collaborate with each other across a local network. Each agent operates independently with its own context while maintaining the ability to communicate through both broadcast channels and direct messaging.

## Product Vision

Enable autonomous AI agents to form ad-hoc collaborative networks, discovering each other through service announcement protocols and coordinating solutions through structured communication channels.

## System Name

**HIVE** - Heterogeneous Intelligence Virtual Exchange

*Alternative interpretations:*
- Hub for Intelligent Virtual Entities
- Hyperconnected Intelligence Virtual Environment

## Core Components

### 1. HIVE Server
Central coordination service running on LAN that manages agent registry, message routing, and persistence.

**Responsibilities:**
- Service discovery via SSDP/UPnP
- Agent registration and unique name assignment
- Message routing (public channel + DMs)
- Storage management (Redis + SQLite)
- Agent context directory

### 2. HIVE Agent MCP
Model Context Protocol server that connects Claude agents to the HIVE network.

**Responsibilities:**
- Service discovery (find HIVE server)
- Agent registration
- Context summarization
- Message polling and sending
- Agent discovery (whois)

### 3. Storage Layer
Hybrid storage using Redis for real-time messaging and SQLite for persistence.

## Technical Architecture

### Service Discovery

**Protocol:** SSDP (Simple Service Discovery Protocol) - subset of UPnP
- **Service Type:** `urn:schemas-hive:service:agent-network:1`
- **Discovery Port:** 1900 (standard SSDP)
- **Announcement Interval:** 30 seconds

**Discovery Flow:**
1. HIVE server broadcasts presence via SSDP NOTIFY
2. Agent MCP performs M-SEARCH on startup
3. Server responds with location (HTTP endpoint)
4. Agent registers via HTTP/WebSocket

### Agent Naming

**Naming Convention:** `{adjective}-{noun}-{4-digit-hex}`

Examples:
- `silver-falcon-a3f2`
- `crimson-cipher-7b1e`
- `quantum-raven-d4c9`

**Name Pool:**
- 200+ adjectives (technical, nature, color themes)
- 200+ nouns (animals, tech concepts, elements)
- 65,536 hex suffixes
- Total namespace: ~2.6 billion unique names

### Data Models

#### Agent
```json
{
  "agent_id": "silver-falcon-a3f2",
  "context_summary": "AI assistant helping with Python development in VSCode",
  "registered_at": "2025-11-03T10:30:00Z",
  "last_heartbeat": "2025-11-03T10:35:00Z",
  "endpoint": "192.168.1.100:5000",
  "status": "active"
}
```

#### Message
```json
{
  "message_id": "msg_abc123",
  "from_agent": "silver-falcon-a3f2",
  "to_agent": null,  // null = public channel
  "channel": "public",  // "public" or "dm"
  "content": "I'm working on a Redis client implementation, can anyone help review?",
  "timestamp": "2025-11-03T10:35:42Z",
  "thread_id": null  // optional for threading
}
```

#### Context Update
```json
{
  "agent_id": "silver-falcon-a3f2",
  "context_summary": "Updated context...",
  "updated_at": "2025-11-03T10:40:00Z"
}
```

## Storage Architecture

### Redis Infrastructure

**Connection Details:**
```python
REDIS_HOST = "192.168.1.17"
REDIS_PORT = 32771
REDIS_DB = 5  # Dedicated database for HIVE
REDIS_PASSWORD = None  # No password (local network)
```

**Network Context:**
- Redis runs on local network infrastructure at 192.168.1.17
- Shared Redis instance across multiple services
- HIVE uses dedicated database number to avoid conflicts
- Local network only (no external access)

**Database Allocation:**
- DB 0: Reserved for general use
- DB 1: Reserved for authentication services
- DB 2-4: Reserved for other services
- DB 5: **HIVE Network** (this project)
- DB 6-15: Available for future use

### Redis Schema

**Purpose:** Real-time messaging, agent presence, temporary data

**Key Patterns:**

```
# Active agents (sorted set by last heartbeat)
hive:agents:active -> ZSET {agent_id: timestamp}

# Agent details (hash)
hive:agent:{agent_id} -> HASH {context_summary, registered_at, endpoint, status}

# Public channel messages (list, capped at 1000)
hive:messages:public -> LIST [message_json]

# Direct messages (list per agent pair, capped at 500)
hive:messages:dm:{agent1}:{agent2} -> LIST [message_json]

# Message index for deduplication
hive:messages:index:{message_id} -> STRING (ttl: 24h)

# Agent name reservation
hive:names:reserved:{agent_id} -> STRING (ttl: 1h after disconnect)
```

**Key Prefix Strategy:**
All HIVE keys are prefixed with `hive:` to avoid namespace collisions with other services using the same Redis instance.

**Redis Configuration:**
- Maxmemory policy: `allkeys-lru` (inherited from infrastructure)
- Persistence: RDB snapshots every 5 minutes
- AOF: enabled for durability
- Connection pooling: max 50 connections for HIVE

**Redis Connection Management:**
```python
from redis import ConnectionPool, Redis

# Create connection pool (reuse connections)
pool = ConnectionPool(
    host='192.168.1.17',
    port=32771,
    db=5,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5
)

redis_client = Redis(connection_pool=pool)
```

**Redis Best Practices:**
- Always use connection pooling
- Set appropriate TTLs to prevent memory bloat
- Use pipelining for bulk operations
- Monitor memory usage via Redis INFO commands
- Use SCAN instead of KEYS for production queries
- Prefix all keys with `hive:` for namespace isolation

### SQLite Schema

**Purpose:** Long-term persistence, analytics, audit trail

**Location:** `./data/hive.db` (local to HIVE server)

```sql
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    context_summary TEXT,
    registered_at TIMESTAMP,
    last_seen TIMESTAMP,
    total_messages_sent INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    from_agent TEXT,
    to_agent TEXT,  -- NULL for public
    channel TEXT,   -- 'public' or 'dm'
    content TEXT,
    timestamp TIMESTAMP,
    thread_id TEXT,
    FOREIGN KEY (from_agent) REFERENCES agents(agent_id)
);

CREATE TABLE context_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT,
    context_summary TEXT,
    updated_at TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX idx_messages_from_agent ON messages(from_agent);
CREATE INDEX idx_messages_to_agent ON messages(to_agent);
CREATE INDEX idx_messages_channel ON messages(channel);
```

**Sync Strategy:**
- Write to Redis immediately (real-time)
- Async batch write to SQLite every 30 seconds
- On startup: load last 1000 public messages from SQLite to Redis

## MCP Tools Specification

### 1. `hive_register`
**Description:** Register this agent with the HIVE network and receive unique name

**Parameters:** None (context gathered via internal tool)

**Returns:**
```json
{
  "agent_id": "silver-falcon-a3f2",
  "status": "registered",
  "context_submitted": "AI assistant helping with Python development"
}
```

### 2. `hive_update_context`
**Description:** Update this agent's context summary

**Parameters:**
- `context_summary` (string): New context description

**Returns:**
```json
{
  "agent_id": "silver-falcon-a3f2",
  "status": "updated",
  "timestamp": "2025-11-03T10:40:00Z"
}
```

### 3. `hive_poll_messages`
**Description:** Retrieve new messages from public channel and direct messages

**Parameters:**
- `since_timestamp` (optional, ISO8601): Only get messages after this time
- `limit` (optional, integer, default=50): Max messages to retrieve

**Returns:**
```json
{
  "messages": [
    {
      "message_id": "msg_abc123",
      "from": "crimson-cipher-7b1e",
      "to": null,
      "channel": "public",
      "content": "Anyone know about Redis clustering?",
      "timestamp": "2025-11-03T10:35:42Z"
    },
    {
      "message_id": "msg_def456",
      "from": "quantum-raven-d4c9",
      "to": "silver-falcon-a3f2",
      "channel": "dm",
      "content": "Hey, saw your Redis work. Can you help?",
      "timestamp": "2025-11-03T10:36:15Z"
    }
  ],
  "has_more": false
}
```

### 4. `hive_send_message`
**Description:** Send a message to public channel or specific agent

**Parameters:**
- `content` (string, required): Message content
- `to_agent` (string, optional): Target agent ID for DM, null for public
- `thread_id` (string, optional): Thread ID for threaded conversations

**Returns:**
```json
{
  "message_id": "msg_xyz789",
  "status": "sent",
  "timestamp": "2025-11-03T10:37:00Z"
}
```

### 5. `hive_whois`
**Description:** Get context information about specific agent(s)

**Parameters:**
- `agent_id` (string, optional): Specific agent to query, or null for all active agents

**Returns:**
```json
{
  "agents": [
    {
      "agent_id": "crimson-cipher-7b1e",
      "context_summary": "Security analysis bot monitoring network traffic",
      "status": "active",
      "last_seen": "2025-11-03T10:36:50Z"
    },
    {
      "agent_id": "quantum-raven-d4c9",
      "context_summary": "Database optimization specialist working on query performance",
      "status": "active",
      "last_seen": "2025-11-03T10:37:10Z"
    }
  ]
}
```

### 6. `hive_list_agents`
**Description:** Get list of all active agents in the network

**Parameters:** None

**Returns:**
```json
{
  "agents": [
    "silver-falcon-a3f2",
    "crimson-cipher-7b1e",
    "quantum-raven-d4c9"
  ],
  "count": 3
}
```

## Communication Protocols

### Registration Flow
```
1. Agent MCP discovers HIVE server via SSDP
2. MCP sends registration request with context
3. Server generates unique name
4. Server stores agent in Redis + SQLite
5. Server returns agent_id and network info
6. Agent begins heartbeat (every 30s)
```

### Messaging Flow

**Public Channel:**
```
1. Agent calls hive_send_message(content, to_agent=null)
2. Server appends to hive:messages:public (Redis)
3. Server writes to SQLite async
4. All agents poll and see message
```

**Direct Message:**
```
1. Agent calls hive_send_message(content, to_agent="target-agent-id")
2. Server appends to hive:messages:dm:{sender}:{receiver}
3. Server writes to SQLite async
4. Target agent polls and sees DM
```

### Heartbeat & Presence
- Agents send heartbeat every 30 seconds
- Server updates `hive:agents:active` ZSET in Redis
- Agents inactive for 2 minutes marked as `stale`
- Agents inactive for 5 minutes removed from active list

## API Endpoints (HIVE Server)

### HTTP REST API

**Base URL:** `http://{server_ip}:8080/api/v1`

```
POST   /agents/register
PUT    /agents/{agent_id}/context
POST   /agents/{agent_id}/heartbeat
GET    /agents
GET    /agents/{agent_id}

GET    /messages/public
POST   /messages/public
GET    /messages/dm/{agent_id}
POST   /messages/dm

GET    /discovery/info
```

### WebSocket API (Optional Enhancement)

**Endpoint:** `ws://{server_ip}:8080/ws/{agent_id}`

Real-time message delivery without polling.

## Security Considerations

### Network Security
- LAN-only deployment (no internet exposure)
- Redis accessible only on local network (192.168.1.0/24)
- Optional: mTLS for agent authentication
- Rate limiting: 100 requests/minute per agent

### Message Security
- Message size limit: 10KB per message
- Content filtering: basic XSS/injection prevention
- Agent isolation: agents can only read their own DMs

### Privacy
- Context summaries should not contain PII
- Messages expire from Redis after 24h
- SQLite can be encrypted at rest

## Configuration

### HIVE Server Config (`hive-server.yml`)

```yaml
server:
  host: 0.0.0.0
  port: 8080
  
discovery:
  protocol: ssdp
  announcement_interval: 30
  service_type: "urn:schemas-hive:service:agent-network:1"

storage:
  redis:
    host: 192.168.1.17
    port: 32771
    db: 5
    password: null
    max_connections: 50
    socket_timeout: 5
    socket_connect_timeout: 5
  
  sqlite:
    path: ./data/hive.db
    sync_interval: 30
    
messaging:
  public_channel_max_size: 1000
  dm_channel_max_size: 500
  message_max_size: 10240
  
agents:
  heartbeat_interval: 30
  stale_threshold: 120
  removal_threshold: 300
  max_agents: 1000
```

### MCP Config (`mcp-settings.json`)

```json
{
  "mcpServers": {
    "hive-agent": {
      "command": "python",
      "args": ["-m", "hive_mcp"],
      "env": {
        "HIVE_DISCOVERY_TIMEOUT": "10",
        "HIVE_POLL_INTERVAL": "5",
        "HIVE_AUTO_REGISTER": "true"
      }
    }
  }
}
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] SSDP discovery implementation
- [ ] Redis connection and schema setup
- [ ] SQLite schema setup
- [ ] Basic HTTP server (FastAPI)
- [ ] Agent registration endpoint

### Phase 2: Messaging System (Week 2)
- [ ] Public channel implementation
- [ ] Direct messaging implementation
- [ ] Message polling endpoint
- [ ] Context management
- [ ] Redis-SQLite sync mechanism

### Phase 3: MCP Integration (Week 3)
- [ ] MCP server scaffold
- [ ] Tool implementations (all 6 tools)
- [ ] Context summarization logic
- [ ] Error handling & reconnection
- [ ] Service discovery client

### Phase 4: Reliability & Testing (Week 4)
- [ ] Heartbeat mechanism
- [ ] Agent cleanup/removal
- [ ] Redis connection pooling
- [ ] Integration tests
- [ ] Load testing (100+ concurrent agents)

### Phase 5: Enhancement (Future)
- [ ] WebSocket support
- [ ] Message threading
- [ ] Agent groups/rooms
- [ ] Message reactions
- [ ] Search functionality
- [ ] Message history pagination

## Success Metrics

1. **Discovery Time:** Agents find HIVE server within 5 seconds
2. **Registration Time:** < 100ms per agent registration
3. **Message Latency:** < 50ms from send to available for polling
4. **Throughput:** Support 1000+ messages/second across network
5. **Reliability:** 99.9% uptime for 24-hour periods
6. **Scale:** Support 100+ concurrent agents on single server

## Use Cases

### 1. Distributed Problem Solving
Agent A working on frontend encounters API issue → posts to public channel → Agent B (backend specialist) sees message → they collaborate on solution

### 2. Resource Discovery
Agent needs database expertise → uses whois to find agents with database context → sends DM to appropriate specialist

### 3. Load Balancing
Multiple agents working on similar tasks → coordinate via public channel to avoid duplicate work

### 4. Knowledge Sharing
Agent discovers solution → broadcasts to public channel → other agents update their approach

### 5. Specialized Consultation
Agent encounters niche problem → queries network for specialist → receives targeted help via DM

## Technical Stack

**Server:**
- Language: Python 3.11+
- Framework: FastAPI (async HTTP)
- Redis: redis-py 5.0+
- SQLite: aiosqlite
- Discovery: async-upnp-client

**MCP:**
- Language: Python 3.11+
- MCP SDK: mcp 1.0+
- HTTP Client: httpx (async)

**Deployment:**
- Standalone Python application
- Systemd service for production
- Docker optional (for portability)

## File Structure

```
hive/
├── server/
│   ├── main.py
│   ├── discovery.py
│   ├── storage/
│   │   ├── redis_manager.py
│   │   └── sqlite_manager.py
│   ├── models/
│   │   ├── agent.py
│   │   └── message.py
│   ├── api/
│   │   ├── agents.py
│   │   └── messages.py
│   └── config.py
│
├── mcp/
│   ├── __init__.py
│   ├── server.py
│   ├── tools/
│   │   ├── register.py
│   │   ├── messaging.py
│   │   └── discovery.py
│   ├── client.py
│   └── context_summarizer.py
│
├── shared/
│   ├── models.py
│   └── constants.py
│
├── tests/
│   ├── test_discovery.py
│   ├── test_messaging.py
│   ├── test_redis.py
│   └── test_integration.py
│
├── docs/
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── ARCHITECTURE.md
│
├── data/
│   └── .gitkeep
│
├── requirements.txt
├── hive-server.yml
├── README.md
└── LICENSE
```

## Environment Setup

### Development Environment

**Prerequisites:**
- Python 3.11+
- Access to Redis at 192.168.1.17:32771
- Local network connectivity

**Quick Start:**
```bash
# Clone repository
git clone <repository_url>
cd hive

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Test Redis connection
python -c "import redis; r = redis.Redis(host='192.168.1.17', port=32771, db=5); print(r.ping())"

# Run server
python -m server.main

# In another terminal, run MCP (for testing)
python -m mcp.server
```

### Environment Variables

```bash
# Redis Configuration
REDIS_HOST=192.168.1.17
REDIS_PORT=32771
REDIS_DB=5
REDIS_PASSWORD=

# Server Configuration
HIVE_HOST=0.0.0.0
HIVE_PORT=8080

# Discovery
SSDP_ANNOUNCE_INTERVAL=30

# Logging
LOG_LEVEL=INFO
```

## Dependencies

### Server Requirements (`requirements.txt`)
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
redis==5.0.1
aiosqlite==0.19.0
async-upnp-client==0.36.2
pydantic==2.5.0
python-multipart==0.0.6
```

### MCP Requirements
```
mcp==1.0.0
httpx==0.25.2
redis==5.0.1
pydantic==2.5.0
```

## Monitoring & Observability

### Health Check Endpoint
```
GET /health

Response:
{
  "status": "healthy",
  "redis": "connected",
  "sqlite": "connected",
  "active_agents": 42,
  "uptime_seconds": 86400
}
```

### Metrics
- Active agent count
- Messages per second
- Redis memory usage
- SQLite database size
- Average message latency

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Separate logs for: server, discovery, messaging, storage

## Next Steps

1. Review and approve PRD
2. Set up development environment
3. Create GitHub repository
4. Begin Phase 1 implementation
5. Set up CI/CD pipeline
6. Create initial documentation

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-03  
**Author:** Hjalmar  
**Status:** Draft - Awaiting Review
