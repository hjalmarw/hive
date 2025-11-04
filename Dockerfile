FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ ./server/
COPY shared/ ./shared/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Set Python path
ENV PYTHONPATH=/app

# Run MCP server
CMD ["python3", "-m", "server.mcp_server"]
