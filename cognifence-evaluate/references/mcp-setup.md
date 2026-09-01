# Cognifence MCP server setup

The skill drives Cognifence through its MCP server at `<origin>/mcp` (HTTP transport, streamable
JSON-RPC). Replace `<origin>` with the Cognifence app origin the user signs in to (for example
`https://app.cognifence.ai`, or the customer's own tenant origin).

## Get a token

Mint an MCP token in the app under **Organization > Integrations > MCP clients**. It rides every
request as `Authorization: Bearer <YOUR_TOKEN>`.

Secret hygiene: never invent a token, never paste one into a tracked file, and never print it back
to the user in full. Keep it in the environment or an already-gitignored `.env`. If a token leaks,
revoke it on the Integrations page and mint a new one.

## Claude Code (native HTTP MCP)

One-liner:

```bash
claude mcp add --transport http cogni <origin>/mcp --header "Authorization: Bearer <YOUR_TOKEN>"
```

Or as a checked-in-shape `.mcp.json` (keep the real token out of source control — reference an env
var or a local, gitignored file):

```json
{
  "mcpServers": {
    "cogni": {
      "type": "http",
      "url": "<origin>/mcp",
      "headers": { "Authorization": "Bearer <YOUR_TOKEN>" }
    }
  }
}
```

## Codex / Copilot / Gemini / other clients (stdio only)

Clients without native remote-HTTP MCP reach the same endpoint through the `mcp-remote` stdio
bridge (run on demand with `npx`, no install):

```json
{
  "mcpServers": {
    "cogni": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "<origin>/mcp", "--header", "Authorization: Bearer <YOUR_TOKEN>"]
    }
  }
}
```

The exact config file and key differ per client (Codex `~/.codex/config.toml` under an
`[mcp_servers.cogni]` table, Gemini/Copilot their own MCP config) — the `command` + `args` shape
above is what each needs: launch `mcp-remote`, point it at `<origin>/mcp`, and pass the bearer
header.

## Verify

After configuring, confirm the tools are live before running the skill's steps. List the server's
tools and check for `create_agent`, `set_agent_connection`, `mint_connect_key`,
`run_starter_evaluation`, and `get_run_status`:

- Claude Code: `claude mcp list` shows `cogni` as connected; the tools appear as `mcp__cogni__*`.
- Any client: a quick `tools/list` round trip should return the tool names above.

A quick end-to-end check: call `list_agents` (a read-only tool) — a successful response with your
org's agents (or an empty list) proves auth and transport are working.
