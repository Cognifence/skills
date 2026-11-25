---
name: cognifence-evaluate
description: Connects a chat agent or chatbot to Cognifence over the Connect WebSocket, provisions it with the Cognifence MCP tools, and runs an orange-teaming evaluation. Use when the user wants to connect their agent to Cognifence, or to evaluate, orange-team, red-team or safety-test it with Cognifence.
---

# Connect an agent to Cognifence and run an evaluation

The user's code dials out to Cognifence, so it needs no public endpoint. Follow the steps in
order: the adapter must be connected before a run starts.

The evaluation is **orange teaming**: attacker agents hold multi-turn conversations with the
user's agent, each trying to make it fail in one of the run's **failure modes** (such as making up
facts or acting outside its scope), and a judge scores every conversation against those modes.
Explain it to the user in those words; the MCP tools use the term without defining it.

## Rules

- **Approval before every paid run.** `run_starter_evaluation`, `run_evaluation` and every other
  dispatch tool spend real money. Call one only after the user approves that run's quoted cost in a
  later message, even in a non-interactive session such as `codex exec`. A request to "run an
  evaluation" or an approval for an earlier run is not approval.
- **Keep secrets out of tracked files and output.** Keep the MCP token in the coding agent's MCP
  config or environment and the Connect key in the adapter's environment or a gitignored `.env`.
  Never commit or invent either, and never show either in output, except the Connect key in the
  tool result step 4 describes. A literal `${COGNI_MCP_TOKEN}` in a tracked config such as
  `.mcp.json` is not a secret: don't tell the user to untrack it or rotate the token.
- **Connect only.** Never use the `openai_responses` or `hosted_model` protocols, even when Connect
  is blocked: the first needs a public endpoint, the second evaluates a model Cognifence hosts
  instead of the user's code, and the app shows neither as connected. Stop and tell the user what
  blocks Connect.

## Steps

1. **Check the MCP tools.** Confirm `create_agent`, `mint_connect_key`, `list_agent_connections`
   and `run_starter_evaluation` are callable. The server has more tools;
   use only those named in this skill. If they are missing, diagnose before you advise:
   - Check the token without printing it: `[ -n "$COGNI_MCP_TOKEN" ] && echo set || echo unset`.
     An unset variable is not a rejected or leaked token.
   - Run the harness's status command (`claude mcp list`, `codex mcp list` or `amp mcp doctor`)
     and read its full output, without `head` or `tail`; it can take a minute.
   - Tell the user only what those commands printed. Don't quote an HTTP status or error you did
     not see, and don't redact the config before you read it.

   Then set the server up as [Connect a client](https://docs.cognifence.ai/guide/mcp/connect/)
   shows, with a **Read + write** token, and use
   [Troubleshooting](https://docs.cognifence.ai/guide/mcp/troubleshooting/) to match what the
   commands printed to a cause.

2. **Find the chat handler**: the one `(message) -> reply` function in the user's repo that takes
   user text and returns the agent's reply. If several fit, ask the user which one.

3. **Wire up Connect.** The integration is one `connect()` call around that handler, not a new
   subsystem. Install SDK 0.10 or later (Python 3.12 or later), since older SDKs reject
   `code: { main: false }`: `uv add cognifence-connect` or `bun add @cognifence/connect`
   (or `npm install`). Then add this at an entry point, replacing
   only the call to `reply`:

   ```js
   import { connect } from "@cognifence/connect";
   for (const name of ["URL", "KEY", "DEPLOYMENT_ID", "NAME"].map((n) => `COGNI_CONNECT_${n}`))
     if (!process.env[name]) throw new Error(`Set ${name} in .env`);
   const agent = await connect({
     url: process.env.COGNI_CONNECT_URL,
     token: process.env.COGNI_CONNECT_KEY,
     connection: {
       mode: "register",
       deploymentId: process.env.COGNI_CONNECT_DEPLOYMENT_ID,
       name: process.env.COGNI_CONNECT_NAME,
     },
     code: { main: false },   // a local checkout; drop for a deployed build of the main branch
     manifest: { channels: [{ name: "chat", direction: "duplex" }], tools: [] },
     onMessage: async (msg) => reply(msg.body),   // ← the step-2 handler
   });
   await agent.done;
   ```

   ```python
   import asyncio
   import os

   from cognifence_connect import connect
   from cognifence_connect.schema import (
       CodeVersion, Manifest, ManifestChannelDecl, RegisterConnection,
   )

   async def on_message(msg, ctx):
       return await reply(msg.body)  # step-2 handler; drop `await` if it is synchronous

   async def main():
       agent = await connect(
           url=os.environ["COGNI_CONNECT_URL"],
           token=os.environ["COGNI_CONNECT_KEY"],
           connection=RegisterConnection(
               mode="register",
               deployment_id=os.environ["COGNI_CONNECT_DEPLOYMENT_ID"],
               name=os.environ["COGNI_CONNECT_NAME"],
           ),
           code=CodeVersion(main=False),  # a local checkout; drop for a deployed main build
           manifest=Manifest(channels=[ManifestChannelDecl(name="chat", direction="duplex")], tools=[]),
           on_message=on_message,
       )
       await agent.wait()

   asyncio.run(main())
   ```

   - Keep the manifest unchanged.
   - Keep `connection`: the adapter registers its connection on the first start and reuses it on
     every restart with the same deployment ID, and every start reports the branch, commit,
     repository, path and uncommitted changes it runs, which the app shows on the connection and
     each evaluation. Step 4 writes both variables.
   - Keep `code: { main: false }` while the adapter runs from a local checkout, so its evaluations
     stay out of the agent's main-line failure-mode history. Remove it only for a deployed build
     of the main branch.
   - Message fields are snake_case in Python (`msg.run_id`) and camelCase in JS (`msg.runId`).
   - Neither snippet reads `.env`: start the adapter with `node --env-file=.env` or
     `uv run --env-file .env`. If any of the four `COGNI_CONNECT_*` variables is missing, the
     snippet fails at start: JS with `Set <variable> in .env`, Python with `KeyError: '<variable>'`.
   - **Check that the handler replies**: call it once with a short sample message, the way
     `onMessage` will, and confirm it returns text. Cognifence's connection test sends no message,
     so this is the only check that the agent answers instead of crashing on every turn.
   - Only when the user wants a hardened long-running process (clean shutdown, exit codes), copy
     `references/adapter-templates/connect_adapter.mjs` or `connect_adapter.py` instead.

   The SDK guides at https://docs.cognifence.ai/connect/latest/ cover everything else (streaming,
   tools, cancellation, reconnects).

4. **Provision over MCP.** Write the agent's **name** and a **full description**: plain
   present-tense prose of about 1000–2500 characters that the app shows and the evaluation uses, so
   make it specific and testable. Cover the points the `create_agent` `description` field lists:
   1. what the agent is and its core job, in one sentence;
   2. who uses it and who it serves;
   3. its main tasks, concretely;
   4. the channels it works through (chat, email, SMS, phone, API, …);
   5. the systems and tools it connects to, and whether it reads or writes them;
   6. what it may do on its own vs. what waits for human approval;
   7. how it behaves when it is unsure;
   8. anything it must never do.

   Take what you can from the repo (README, system prompt, tool wiring) and ask the user about the
   gaps instead of inventing systems, channels or policies. Also write a **1–3 sentence blurb**
   (points 1–3) for step 5. Then:
   - `create_agent` `{ name, description }` returns the `id` that the next calls take as `agentId`.
     First check `list_agents`; if an agent with exactly that name exists, ask whether to reuse it.
   - `mint_connect_key` `{ agentId }`, once per agent: each call creates another live key, so if a
     write fails, write the same token again. Call it with your harness's MCP tools, not a script or
     MCP client of your own; in Amp, call it from `code_exec` and output only `token` and
     `connectUrl`. Write `token` to `.env` as `COGNI_CONNECT_KEY` with your file-edit tool, not the
     shell, once `git check-ignore -q .env` passes (else add `.env` to `.gitignore`; if tracked, ask
     the user), and never print `.env`, repeat the token in a reply or put it on a command line.
     Write `connectUrl` as `COGNI_CONNECT_URL`; if it is null, stop and tell the user Connect is not
     configured for this deployment and their administrator must enable it. Don't use the app origin
     instead.
   - No connection is needed beforehand: the adapter registers its own. Write
     `COGNI_CONNECT_DEPLOYMENT_ID` and `COGNI_CONNECT_NAME` to `.env`: a stable ID for where
     this adapter runs, 1–128 ASCII letters, digits or `._:-` starting with a letter or digit (such
     as `alice-laptop` or `staging`), and the name the app shows (such as `Alice's laptop`). Ask the
     user only if the right place is unclear. Reuse the same ID on every restart; give each
     concurrently running copy its own.
   - **Recommended:** record tool calls, and facts the agent takes from its prompt or other injected
     context, as OpenTelemetry spans and send them over the same socket with
     `instrument(agent, provider)` from `cognifence_connect.otel` (extra `cognifence-connect[otel]`)
     or `instrument(agent)` from `@cognifence/connect/otel`. Add it to the app's existing tracer
     provider rather than replacing it. Without these spans the judge can't tell answers backed by
     tools or the prompt from made-up ones. Set the attributes the
     [Python](https://docs.cognifence.ai/connect/latest/python/#opentelemetry) or
     [TypeScript](https://docs.cognifence.ai/connect/latest/typescript/#opentelemetry) guide lists
     for tool-call and `retrieval` spans, and create spans inside `onMessage` or code it calls.

5. **Start the adapter, then run.** Some harnesses (such as `codex exec`) stop the processes they
   started when the session or turn ends, including while you wait for approval, and `nohup … &` is
   not enough. Start the adapter in its own session, with `setsid` on Linux or, on macOS too:

   ```bash
   python3 -c 'import subprocess; p = subprocess.Popen(["uv", "run", "--env-file", ".env",
     "python", "connect_adapter.py"], stdout=open("adapter.log", "w"), stderr=subprocess.STDOUT,
     start_new_session=True); open("adapter.pid", "w").write(str(p.pid))'
   ```

   Check it with `kill -0 $(cat adapter.pid)` and stop its process group with
   `kill -- -$(cat adapter.pid)`; never find or stop it by name (`pgrep -f`, `pkill`).

   For JS, replace the list with `["node", "--env-file=.env", "connect_adapter.mjs"]`. On macOS, put
   `"caffeinate", "-i",` first in the list so the Mac stays awake until the adapter exits; a
   sleeping Mac drops the adapter and fails the run, and closing the lid still sleeps it. Run one
   adapter per deployment ID: a second with the same `COGNI_CONNECT_DEPLOYMENT_ID` replaces the
   first.

   Check that the log shows no error; the minimal snippet logs nothing when it connects, so an
   empty log is normal. Call `list_agent_connections` `{ agentId }` and pick the eligible, online
   connection whose `deploymentId` is `COGNI_CONNECT_DEPLOYMENT_ID`; names aren't unique, so don't
   match on them. Its `metadata` should hold the branch and commit; outside a git checkout with no
   CI variables it may not, which is fine, so continue. Call `test_agent_connection`
   `{ agentId, connectionId }`; it checks only that the adapter holds a live session. **Then
   stop:** quote the estimate and spend cap from the `run_starter_evaluation` description (if it
   states none, say a starter run stops at $5 and takes about 10 to 15 minutes), say the run is
   optional, and end your turn asking for approval. After
   it, call `run_starter_evaluation` `{ agentId, connectionId, agentBlurb }` with the short blurb,
   not the full description; `connectionId` is required even with one connection. (`cancel_run`
   stops a run that is still spending; `run_evaluation` runs chosen failure modes at a chosen size.)

   Poll `get_run_status` `{ evaluationId }` until its `status` is terminal, through the whole 10 to
   15 minutes, and tell the user its progress (turns used of the turn budget) and spend against the
   budget as you go. The conversation count fills in once attacking ends. Once the run is terminal,
   read the findings with `get_orange_results` `{ evaluationId }` (large: if your harness truncates
   it, save it outside the repo). Keep the adapter up until the run ends.

6. **Report back.** Give the user the `agentId` and, after a run, the `resultsUrl` that
   `run_starter_evaluation` and `get_run_status` return. Say what you integrated, because the app
   shows only "connected" either way: the manifest's channels and tools, whether `instrument` sends
   spans, and which tools they cover. After a run, always read two or three conversations with
   `get_orange_conversation`. If none show tool calls, check the adapter log for whether the agent
   called a tool; if it did, check that its spans set the guide's attributes and are created inside
   `onMessage`, and tell the user the results lack tool context until that is fixed.
