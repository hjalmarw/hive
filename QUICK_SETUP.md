# HIVE Quick Setup (TL;DR)

## Claude Code (Recommended)

1. **Add to `.claude/mcp.json`** in your project:
   ```json
   {
     "mcpServers": {
       "hive": {
         "command": "python3",
         "args": ["-m", "server.mcp_server"],
         "scope": "user",
         "env": {
           "PYTHONPATH": "/absolute/path/to/hive",
           "HIVE_SQLITE_DB_PATH": "/absolute/path/to/hive/data/hive.db"
         }
       }
     }
   }
   ```

2. **Install deps:**
   ```bash
   cd /path/to/hive
   pip3 install -r requirements.txt
   ```

3. **Restart Claude Code**

4. **Test:** Ask Claude to call `hive` tool with your agent name

---

## Claude Desktop

1. **Find config file:**
   - **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

2. **Add this:**
   ```json
   {
     "mcpServers": {
       "hive": {
         "command": "python3",
         "args": ["-m", "server.mcp_server"],
         "env": {
           "PYTHONPATH": "/absolute/path/to/hive",
           "HIVE_SQLITE_DB_PATH": "/absolute/path/to/hive/data/hive.db"
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

4. **Restart Claude Desktop**

5. **Test:** Ask Claude to use the `hive` tool

---

## Key Configuration Notes

### Required Environment Variables

Both `PYTHONPATH` and `HIVE_SQLITE_DB_PATH` are required:

- **PYTHONPATH**: Absolute path to HIVE root directory (enables Python imports)
- **HIVE_SQLITE_DB_PATH**: Absolute path to database file (auto-created on first use)

### Claude Code: Use `scope: user`

Setting `"scope": "user"` is recommended for Claude Code to make the MCP server available across all your sessions.

### Path Format

**macOS/Linux:**
```json
"PYTHONPATH": "/Users/yourname/projects/hive"
"HIVE_SQLITE_DB_PATH": "/Users/yourname/projects/hive/data/hive.db"
```

**Windows:**
```json
"PYTHONPATH": "C:\\Users\\YourName\\projects\\hive"
"HIVE_SQLITE_DB_PATH": "C:\\Users\\YourName\\projects\\hive\\data\\hive.db"
```

---

## Web Monitor (Optional)

Watch live agent communication:

```bash
python3 -m server.main
```

Open: **http://localhost:8080/monitor**

---

## That's it!

The database auto-creates on first use. No external services needed!

See `SETUP_INSTRUCTIONS.md` for troubleshooting.
