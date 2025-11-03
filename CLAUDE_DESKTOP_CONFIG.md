# Claude Desktop Configuration for HIVE MCP Agent

## Configuration File Locations

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

## Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hive-agent": {
      "command": "python",
      "args": ["-m", "mcp"],
      "cwd": "/mnt/e/projects/hive",
      "env": {
        "PYTHONPATH": "/mnt/e/projects/hive"
      }
    }
  }
}
```

## Windows Users

For Windows, use Windows-style paths:

```json
{
  "mcpServers": {
    "hive-agent": {
      "command": "python",
      "args": ["-m", "mcp"],
      "cwd": "E:\\projects\\hive",
      "env": {
        "PYTHONPATH": "E:\\projects\\hive"
      }
    }
  }
}
```

## Alternative: Using Installed Package

If you installed via `pip install -e .`:

```json
{
  "mcpServers": {
    "hive-agent": {
      "command": "hive-mcp"
    }
  }
}
```

## Verification

1. Save the configuration file
2. Restart Claude Desktop
3. Open Claude Desktop Developer Console:
   - **macOS/Linux**: View → Toggle Developer Tools
   - **Windows**: Help → Toggle Developer Tools
4. Look for logs indicating the MCP server started:
   ```
   Starting HIVE MCP Agent Server...
   ```

## Testing the Connection

Once configured, ask Claude:

```
Can you register me with the HIVE network?
```

You should see Claude call the `hive_register` tool. If successful:

```
Successfully registered with HIVE network!

Agent ID: silver-falcon-a3f2
Status: registered
Context: Claude AI assistant working in 'hive' project on Linux
```

## Troubleshooting

### "MCP server not found"

1. Check that Python is in your PATH
2. Verify the `cwd` path exists
3. Check Developer Console for error messages

### "Module not found"

1. Ensure dependencies are installed:
   ```bash
   cd /mnt/e/projects/hive/mcp
   pip install -r requirements.txt
   ```

2. Or install the full package:
   ```bash
   cd /mnt/e/projects/hive
   pip install -e .
   ```

### "HIVE server not found"

This is expected if the HIVE server isn't running yet. The MCP agent will:
1. Attempt SSDP discovery when you call `hive_register`
2. Wait up to 10 seconds for server response
3. Throw error if server not found

Make sure the HIVE server is running before registering.

## Environment Variables (Optional)

You can customize behavior with environment variables:

```json
{
  "mcpServers": {
    "hive-agent": {
      "command": "python",
      "args": ["-m", "mcp"],
      "cwd": "/mnt/e/projects/hive",
      "env": {
        "PYTHONPATH": "/mnt/e/projects/hive",
        "LOG_LEVEL": "DEBUG",
        "SSDP_DISCOVERY_TIMEOUT": "15"
      }
    }
  }
}
```

Available variables:
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `SSDP_DISCOVERY_TIMEOUT`: Seconds to wait for server (default: 10)

## Multiple Agents

You can run multiple HIVE agents from different Claude instances:

```json
{
  "mcpServers": {
    "hive-agent-1": {
      "command": "python",
      "args": ["-m", "mcp"],
      "cwd": "/mnt/e/projects/hive"
    },
    "hive-agent-2": {
      "command": "python",
      "args": ["-m", "mcp"],
      "cwd": "/mnt/e/projects/hive"
    }
  }
}
```

Each will get a unique agent ID when registered.

## Next Steps

1. Configure Claude Desktop with the JSON above
2. Restart Claude Desktop
3. Start the HIVE server (see server/README.md)
4. Register your agent: "Register me with HIVE"
5. Start collaborating with other agents!
