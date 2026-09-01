---
name: cognifence-evaluate
description: Use when the user wants to connect my agent/chatbot to Cognifence, run an evaluation, red-team or safety-test my chatbot, or wire their agent up to the Cognifence Connect WebSocket for evaluation. Requires the Cognifence MCP server to be configured (see references/mcp-setup.md).
---

# Connect an agent to Cognifence and run an evaluation

Wire the user's existing chat agent to Cognifence over the Connect WebSocket, provision it
through the Cognifence MCP tools, and kick off a starter evaluation. Work through the steps in
order — the ordering is load-bearing (an adapter must be dialed in before a run is started).

**Install this skill** (via the `skills` CLI):

```bash
npx skills add Cognifence/skills --skill cognifence-evaluate
```

The CLI fetches the skill from the `Cognifence/skills` repo and installs it into your agent's
skills directory (Claude Code, Codex, Copilot, Gemini, …). After it finishes, reload the agent's
plugins/skills or restart it (e.g. restart Claude Code) so this skill is discovered.

## Steps

1. **Confirm MCP tools are reachable.** Verify the Cognifence MCP tools `create_agent`,
   `set_agent_connection`, `mint_connect_key`, and `run_starter_evaluation` are callable in this
   session. If they are not, set the server up per `references/mcp-setup.md` (the token comes from
   the app under **Organization > Integrations > MCP clients** — never invent one, never commit
   one).

2. **Find the chat handler.** Detect the single `(message) -> reply` function in the user's repo —
   the one that takes user text and returns the agent's reply. If more than one plausibly fits, ask
   the user which one; otherwise proceed with the obvious one.

3. **Wire up Connect.** The whole integration is a single `connect()` call wired to the handler
   from step 2 — a few lines, not a new subsystem. Prefer the smallest change that works:
   - **Install the SDK** — NOT from a public registry. JS: `bun add`/`npm i` the GitHub Release
     tarball. Python: pin it in `[tool.uv.sources]` by git tag. Exact commands and options:
     `references/connect-sdk.md`.
   - **Drop in the minimal snippet** at an entry point in the user's app, replacing only the marked
     line with a call into the step-2 handler:

     JS:
     ```js
     import { connect } from "@cognifence/connect";
     const agent = await connect({
       url: process.env.COGNI_CONNECT_URL,
       token: process.env.COGNI_CONNECT_KEY,
       manifest: { channels: [{ name: "chat", direction: "duplex" }], tools: [] },
       onMessage: async (msg) => reply(msg.body),   // ← the step-2 (message)->reply handler
     });
     await agent.done;
     ```

     Python:
     ```python
     from cognifence_connect import connect
     async def on_message(msg, ctx):
         return await reply(msg.body)               # ← the step-2 (message)->reply handler
     agent = await connect(
         url=os.environ["COGNI_CONNECT_URL"],
         token=os.environ["COGNI_CONNECT_KEY"],
         manifest={"channels": [{"name": "chat", "direction": "duplex"}], "tools": []},
         on_message=on_message,
     )
     await agent.wait()
     ```
   - That snippet IS the integration — nothing else to bolt on. In particular, do NOT add
     OpenTelemetry/OTEL tracing or any observability wiring (Cognifence already captures traces for
     a Connect agent). The manifest is fixed (one duplex channel named `chat`, no tools; tools are
     optional). Read `COGNI_CONNECT_URL` and `COGNI_CONNECT_KEY` from the environment — do not
     hard-code them; the URL must be `wss://` (plaintext `ws://` is refused except toward localhost).
   - **Only if the user needs a hardened long-running process** (graceful SIGTERM shutdown,
     terminal-error exit codes, env-var validation, cancellation via `ctx.signal`), copy the fuller
     adapter from `references/adapter-templates/` (`connect_adapter.mjs` / `connect_adapter.py`)
     instead — it is the same `connect()` call with that scaffolding around it.

4. **Provision over MCP.** Collect a SHORT blurb from the user: the agent's name plus 1–3
   sentences on what it does. Then, in order:
   - `create_agent` `{ name, description }` -> keep the returned `agentId`.
   - `set_agent_connection` `{ agentId, protocol: "cognifence_connect" }`.
   - `mint_connect_key` `{ agentId }` -> store the returned `token` as `COGNI_CONNECT_KEY` in the
     user's env (the plaintext token is shown ONCE and is unrecoverable). Use the returned
     `connectUrl` as `COGNI_CONNECT_URL`; if it is null, fall back to `wss://<origin>/connect/v1`.

5. **Start the adapter, then run.** Launch the adapter and confirm it dialed in (the SDK completes
   `session.hello` on start; a clean start with no error means the session is live). The adapter
   MUST be connected BEFORE the run starts. Then — **confirm with the user before spending**, since
   a run calls real LLM providers and incurs real cost — call `run_starter_evaluation`
   `{ agentId, agentBlurb }` with the same blurb. Poll `get_run_status` `{ runId }` until it
   completes. Keep the adapter process up for the whole run.

6. **Report back.** Give the user the `agentId` and the report link
   `<origin>/agents/<agentId>/report/<reportId>` — `reportId` (== the run id) comes from
   `run_starter_evaluation`; `get_run_status` reports progress and `reportExists`, not a URL.

## Guardrails

- **Confirm before paid runs.** `run_starter_evaluation` (and every dispatch tool) spends real
  money. Get explicit confirmation first.
- **Never commit secrets.** The Connect key and MCP token go in the environment / an
  already-gitignored `.env`, never into tracked files.
- **Don't add observability yourself.** Do NOT instrument the app with OpenTelemetry/OTEL, spans, or
  trace exporters as part of connecting, and don't offer to. Cognifence already captures traces for
  a Connect agent, so adding your own is redundant — wire only the `connect()` call from step 3.
- **`wss://` only.** The SDK refuses to put the bearer token on plaintext `ws://` (except
  localhost).
- **Ordering is load-bearing.** create -> set connection -> mint key -> adapter dialed in ->
  run. Only one adapter process may hold a given agent identity at a time.

See `references/mcp-setup.md`, `references/connect-sdk.md`, and
`references/adapter-templates/README.md` for the detail behind each step.
