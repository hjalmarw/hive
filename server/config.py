"""HIVE Server Configuration"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """HIVE Server Settings"""

    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8080

    # SQLite Configuration
    sqlite_db_path: str = "./data/hive.db"

    # Messaging Configuration
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
