"""HIVE Server Configuration"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """HIVE Server Settings"""

    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8080

    # Redis Configuration
    redis_host: str = "192.168.1.17"
    redis_port: int = 32771
    redis_db: int = 5
    redis_password: Optional[str] = None
    redis_max_connections: int = 50
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5

    # SQLite Configuration
    sqlite_path: str = "./data/hive.db"
    sqlite_sync_interval: int = 30

    # Messaging Configuration
    public_channel_max_size: int = 1000
    dm_channel_max_size: int = 500
    message_max_size: int = 10240

    # Agent Configuration
    heartbeat_interval: int = 30
    stale_threshold: int = 120
    removal_threshold: int = 300
    max_agents: int = 1000

    # Discovery Configuration
    ssdp_announce_interval: int = 30
    service_type: str = "urn:schemas-hive:service:agent-network:1"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_prefix = "HIVE_"
        case_sensitive = False


# Global settings instance
settings = Settings()
