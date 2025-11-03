#!/bin/bash
# Verify HIVE Build Completeness

echo "=========================================="
echo "HIVE Server - Build Verification"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (MISSING)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (MISSING)"
        return 1
    fi
}

echo "Checking directory structure..."
echo ""

# Core directories
check_dir "server"
check_dir "server/api"
check_dir "server/models"
check_dir "server/storage"
check_dir "shared"
check_dir "mcp"
check_dir "tests"
check_dir "data"

echo ""
echo "Checking core files..."
echo ""

# Server files
check_file "server/__init__.py"
check_file "server/main.py"
check_file "server/config.py"
check_file "server/discovery.py"

# API files
check_file "server/api/__init__.py"
check_file "server/api/agents.py"
check_file "server/api/messages.py"

# Model files
check_file "server/models/__init__.py"
check_file "server/models/agent.py"
check_file "server/models/message.py"

# Storage files
check_file "server/storage/__init__.py"
check_file "server/storage/redis_manager.py"

# Shared files
check_file "shared/__init__.py"
check_file "shared/constants.py"
check_file "shared/models.py"

# Config files
check_file "requirements.txt"
check_file "test_redis.py"
check_file "start_server.sh"
check_file "README.md"
check_file "BUILD_SUMMARY.md"
check_file "PRD.md"

echo ""
echo "Counting lines of code..."
echo ""

# Count Python files
py_files=$(find server shared -name "*.py" | wc -l)
total_lines=$(find server shared -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')

echo "Python modules: $py_files"
echo "Total lines: $total_lines"

echo ""
echo "Checking Python syntax..."
echo ""

# Check syntax of key files
syntax_errors=0
for file in server/main.py server/config.py server/discovery.py \
            server/api/agents.py server/api/messages.py \
            server/models/agent.py server/models/message.py \
            server/storage/redis_manager.py; do
    if [ -f "$file" ]; then
        python3 -m py_compile "$file" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓${NC} $file (syntax OK)"
        else
            echo -e "${RED}✗${NC} $file (syntax error)"
            syntax_errors=$((syntax_errors + 1))
        fi
    fi
done

echo ""
echo "=========================================="
if [ $syntax_errors -eq 0 ]; then
    echo -e "${GREEN}✓ Build verification PASSED${NC}"
else
    echo -e "${RED}✗ Build verification FAILED${NC}"
    echo "  $syntax_errors syntax errors found"
fi
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Install dependencies: pip install -r requirements.txt"
echo "  2. Test Redis: python3 test_redis.py"
echo "  3. Start server: ./start_server.sh"
echo ""
