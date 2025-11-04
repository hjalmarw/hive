"""HIVE Server - Hybrid FastAPI/MCP Application"""
import sys
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from server.config import settings
from server.api import agents, messages
from server.storage.sqlite_manager import get_sqlite_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global state
start_time = time.time()
cleanup_task: asyncio.Task = None


async def cleanup_inactive_agents_task():
    """Background task to cleanup inactive agents"""
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            db = await get_sqlite_manager()
            removed = await db.cleanup_inactive_agents()
            if removed > 0:
                logger.info(f"Cleaned up {removed} inactive agents")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    global cleanup_task

    # Startup
    logger.info("Starting HIVE HTTP API server...")

    # Initialize and test database connection
    db = await get_sqlite_manager()
    if not await db.ping():
        logger.error("Failed to connect to database!")
        raise Exception("Database connection failed")

    logger.info(f"Database connected: {settings.sqlite_db_path}")

    # Start cleanup task
    cleanup_task = asyncio.create_task(cleanup_inactive_agents_task())
    logger.info("Cleanup task started")

    logger.info(f"HIVE HTTP API server ready on port {settings.server_port}")

    yield

    # Shutdown
    logger.info("Shutting down HIVE HTTP API server...")

    if cleanup_task:
        cleanup_task.cancel()

    await db.close()
    logger.info("HIVE HTTP API server shutdown complete")


# Create FastAPI app (for HTTP mode)
app = FastAPI(
    title="HIVE HTTP API",
    description="Heterogeneous Intelligence Virtual Exchange - HTTP Monitoring API",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN only, so allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Health status and statistics
    """
    db = await get_sqlite_manager()
    db_connected = await db.ping()
    stats = await db.get_stats()

    uptime = time.time() - start_time

    return {
        "status": "healthy" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected",
        "active_agents": stats.get("active_agents", 0),
        "uptime_seconds": round(uptime, 2)
    }


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "service": "HIVE HTTP API",
        "version": "2.0.0",
        "description": "Heterogeneous Intelligence Virtual Exchange - HTTP Monitoring API",
        "note": "For MCP client access, use server/mcp_server.py instead",
        "api_base": "/api/v1",
        "endpoints": {
            "agents": "/api/v1/agents",
            "messages": "/api/v1/messages",
            "health": "/health",
            "monitor": "/monitor"
        }
    }


@app.get("/monitor", status_code=status.HTTP_200_OK)
async def monitor():
    """
    Serve the HIVE network monitor web UI.
    """
    static_file = Path(__file__).parent / "static" / "hive_monitor.html"
    return FileResponse(static_file)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
        reload=False
    )
