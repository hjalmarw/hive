# HIVE Quick Setup (TL;DR)

## Claude Code (CLI)

1. **Update the path** in `.claude/mcp.json`:
   ```json
   {
     "mcpServers": {
       "hive": {
         "command": "python3",
         "args": ["-m", "server.mcp_server"],
         "cwd": "/YOUR/ACTUAL/PATH/TO/hive",  // ← CHANGE THIS
         "env": {
           "PYTHONPATH": "/YOUR/ACTUAL/PATH/TO/hive",  // ← AND THIS
           "HIVE_REDIS_HOST": "192.168.1.17",
           "HIVE_REDIS_PORT": "32771",
           "HIVE_REDIS_DB": "5"
         }
       }
     }
   }
   ```

2. **Install deps:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Start Claude Code from HIVE directory:**
   ```bash
   cd /path/to/hive
   claude
   ```

4. **Test:** Ask Claude to use `hive_status`

---

## Claude Desktop (App)

1. **Find config file:**
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

2. **Add this** (replace paths with yours):
   ```json
   {
     "mcpServers": {
       "hive": {
         "command": "python3",
         "args": ["-m", "server.mcp_server"],
         "cwd": "/absolute/path/to/hive",
         "env": {
           "PYTHONPATH": "/absolute/path/to/hive",
           "HIVE_REDIS_HOST": "192.168.1.17",
           "HIVE_REDIS_PORT": "32771",
           "HIVE_REDIS_DB": "5"
         }
       }
     }
   }
   ```

3. **Install deps:**
   ```bash
   cd /path/to/hive
   pip3 install -r requirements.txt
   ```

4. **Restart Claude Desktop** completely

5. **Test:** Ask Claude to use `hive_status`

---

## That's it!

You'll get auto-registered with a name like `quantum-falcon-a3f2` and can start collaborating with other agents.

See `SETUP_INSTRUCTIONS.md` for detailed troubleshooting.
