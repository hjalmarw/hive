#!/bin/bash
# Start HIVE Server

echo "Starting HIVE Server..."
echo "======================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
pip list | grep fastapi > /dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Test Redis connection
echo ""
echo "Testing Redis connection..."
python3 test_redis.py
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Redis connection failed!"
    echo "Please check your Redis server at 192.168.1.17:32771"
    exit 1
fi

echo ""
echo "Starting HIVE server on port 8080..."
echo "Press Ctrl+C to stop"
echo ""

# Start server
python3 -m server.main
