---
name: cognifence-evaluate
description: Onboards a chat agent or chatbot to Cognifence end to end. It connects the agent over the Connect WebSocket, provisions it with the Cognifence MCP tools, runs the integration check until every channel and tool is triggered or skipped, and runs an orange-teaming evaluation. Use when the user wants to connect or onboard their agent to Cognifence, or to evaluate, orange-team, red-team or safety-test it with Cognifence.
---

# Onboard an agent to Cognifence and run an evaluation

The user's code dials out to Cognifence, so it needs no public endpoint. Follow the steps in
order: the adapter must be connected before a check or run starts. Onboarding moves the agent
from **Draft** to **Integrated**; `get_agent` returns its `stage` (`draft`, `integrated` or `ready`)
and a `nextStep` that names what comes next. After Integrated the agent is a regular agent, ready
for evaluation; agents created before onboarding report `ready`.

The **integration check** is a short run in which a simulated user tries to trigger every item of
the agent once: each channel and tool its Connect manifest declares, and each of the agent's own
tools, which the check learns from the agent's OpenTelemetry spans and from asking the agent what
it can do. Cognifence pays for it, so it needs no cost approval, but an agent gets only 10 a day.
The agent is Integrated once the latest check finished and every item is triggered or skipped.

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
  `.mcp.json` is not a secret: don't tell the user to untrack it or rotate the token. Never paste
  or ask for the MCP token in chat: the user exports `COGNI_MCP_TOKEN` themselves.
- **Never skip an integration-check item on your own.** Before each `skip_integration_item`, tell
  the user which item, what the check found and why skipping it is reasonable, and call it only
  after they agree in a later message. A skip to make the check pass is never reasonable while a
  fix is possible.
- **Connect only.** Never use the `openai_responses` or `hosted_model` protocols, even when Connect
  is blocked: the first needs a public endpoint, the second evaluates a model Cognifence hosts
  instead of the user's code, and the app shows neither as connected. Stop and tell the user what
  blocks Connect.

## Steps

1. **Check the MCP tools.** Confirm `create_agent`, `mint_connect_key`, `list_agent_connections`
   and `run_starter_evaluation` are callable. The server has more tools; use only those named in
   this skill. If only `start_integration_check` and `get_integration_check` are missing, the
   server predates the integration check: continue, skip step 6 and tell the user so in step 8.
   If the others are missing, diagnose before you advise:
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
   user text and returns the agent's reply. If several fit, ask the user which one. Also list the
   tools the agent's LLM can call (function or tool definitions passed to the model): the
   integration check tries each of them.

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

   - Keep the manifest unchanged. Declare only the channels and tools the adapter serves over
     Connect: each becomes an integration-check item. Your LLM's own tools stay out of the
     manifest; the check verifies them through spans.
   - Keep `connection`: the adapter registers its connection on the first start and reuses it on
     every restart with the same deployment ID, and every start reports the branch, commit,
     repository, path and uncommitted changes it runs, which the app shows on the connection and
     each evaluation. Step 4 writes both variables. SDK 0.11 registers a connection even without
     `connection`, one per host and working directory, but a stable deployment ID keeps one
     connection across machines and containers. Either way the SDK creates the connection: never
     call `set_agent_connection` or `create_agent_connection` for a Connect agent.
   - Keep `code: { main: false }` while the adapter runs from a local checkout, so its evaluations
     stay out of the agent's main-line failure-mode history. Remove it only for a deployed build
     of the main branch.
   - Message fields are snake_case in Python (`msg.run_id`) and camelCase in JS (`msg.runId`).
   - Neither snippet reads `.env`: start the adapter with `node --env-file=.env` or
     `uv run --env-file .env`. If any of the four `COGNI_CONNECT_*` variables is missing, the
     snippet fails at start: JS with `Set <variable> in .env`, Python with `KeyError: '<variable>'`.
   - **Check that the handler replies**: call it once with a short sample message, the way
     `onMessage` will, and confirm it returns text, before you start the adapter.
   - **Send OpenTelemetry spans** whenever the agent calls tools. The check verifies the agent's
     own tools only in turns that carry a trace; without one it marks every own tool
     `cant_verify`, and the judge can't tell answers backed by tools or the prompt from made-up
     ones. Install the extra (`uv add "cognifence-connect[otel]"`, or the `@opentelemetry/*`
     packages the [TypeScript guide](https://docs.cognifence.ai/connect/latest/typescript/#opentelemetry)
     lists) and set up the provider after `connect()`, before waiting on the agent:
     - Python: `instrument(agent, provider)` from `cognifence_connect.otel`, passing the app's
       existing SDK `TracerProvider` if it has one, else a new one set with
       `trace.set_tracer_provider`.
     - JS: put `instrument(agent)` from `@cognifence/connect/otel` in the `spanProcessors` of the
       provider you build after `connect()` (a `BasicTracerProvider`, or the app's own), and set it
       with `trace.setGlobalTracerProvider`. Without `NodeSDK`, also register
       `new AsyncLocalStorageContextManager().enable()` from
       `@opentelemetry/context-async-hooks` with `context.setGlobalContextManager`, or spans lose
       their turn across `await`; `NodeSDK` already installs one, so don't add a second.

     Then:
     - wrap each `onMessage` call in one span for the turn, like the guide's `answer` span
       (`startActiveSpan("answer", …)` in JS, `start_as_current_span("answer")` in Python),
       unless an LLM-client instrumentation already creates spans in every turn. A turn with no
       span carries no trace, even when the agent called no tool;
     - wrap each tool call in a span with `gen_ai.operation.name` set to `execute_tool`,
       `gen_ai.tool.name` set to the tool's exact name, and the call's input and output in
       `gen_ai.tool.call.arguments` and `gen_ai.tool.call.result`. If the app already uses an
       OpenTelemetry, OpenInference or Traceloop instrumentation for its LLM client, its LLM spans
       also carry the tool definitions the check lists;
     - add a `retrieval` span for facts the agent takes from its prompt or other injected context,
       with the attributes the
       [Python](https://docs.cognifence.ai/connect/latest/python/#opentelemetry) or
       [TypeScript](https://docs.cognifence.ai/connect/latest/typescript/#opentelemetry) guide
       lists;
     - create the spans inside `onMessage` or code it calls, in the process that runs `connect()`:
       spans from another process don't reach the socket.
   - Only when the user wants a hardened long-running process (clean shutdown, exit codes), copy
     `references/adapter-templates/connect_adapter.mjs` or `connect_adapter.py` instead.

   The SDK guides at https://docs.cognifence.ai/connect/latest/ cover everything else (streaming,
   tools, cancellation, reconnects).

4. **Provision over MCP.** Write the agent's **name** and a **short description**: 1-3 sentences
   of plain present-tense prose covering what the agent is and its core job, who uses it, and its
   main tasks. Discovery refines the description later, so don't write a long one. Take what you
   can from the repo (README, system prompt, tool wiring) and ask the user about the gaps instead
   of inventing systems, channels or policies. Use the same text as the `agentBlurb` in step 7.
   Then:
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

5. **Start the adapter and test it.** Some harnesses (such as `codex exec`) stop the processes they
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
   `{ agentId, connectionId }`: it sends the agent one real message and returns `status`,
   `replyExcerpt` and `tracesSeen`. On `failed`, read the adapter log, fix the handler and test
   again. If `tracesSeen` is false, the turn carried no trace: add the per-turn span from step 3
   (or check that it is created inside `onMessage`) before step 6.

6. **Run the integration check until the agent is Integrated.** Before the first check, review
   the manifest and the agent's own tools for items that reach real people or systems, such as
   an outbound email or SMS channel or a tool with side effects (refunds, bookings, writes to a
   live system). The check tries every item, so list them for the user and ask which to skip
   first; skip only those they name, as the rules say. Manifest items can be skipped right away;
   the server knows the agent's own tools only once a check lists them, so they can't be skipped
   until then: before the first check, point any own tool with side effects at test systems. Then call
   `start_integration_check` `{ agentId, connectionId }`; an agent with a Connect connection must be checked on it (409
   `integration_check_connect_required` otherwise). The limit is 10 checks per agent per day (429); on it, stop
   and tell the user. Then poll `get_integration_check` `{ agentId }` about every 30
   seconds until `check.status` is `finished` or `failed` (a few minutes). On `failed`, read
   `check.error`, fix the cause and start a new check. On `finished`, go through every item whose
   `status` is not `triggered` or `skipped`:
   - `cant_verify`: one of the agent's own tools that no turn carried a trace for, or a
     self-reported tool the check never tried. Add the spans from step 3, including the per-turn
     span, and restart the adapter.
   - `not_triggered`: the simulated user couldn't get the agent to use it in `attempts` tries. For
     an own tool, check that its span sets `gen_ai.tool.name` to the name the check lists and that
     the tool is wired in and reachable from a normal user request; for a channel or manifest tool,
     check that the adapter handles it. A note saying the check's budget ran out means the check stopped,
     not that the item is broken. An `agent_tool` with `source` `self_report` that matches no real
     tool came from the agent claiming a tool it lacks: fix the agent's description or system
     prompt so it stops claiming it, or ask the user to skip it.
   - `errored`: read the item's `note` and the adapter log, then fix the handler.
   - An item the agent cannot or must not trigger, such as an outbound channel that would message
     real customers: ask the user, as the rules say, and call `skip_integration_item`
     `{ agentId, kind, name }` only after they agree. `unskip_integration_item` undoes it. The main
     channel the check talks on can't be skipped (409 `integration_check_main_channel`); fix it.

   After fixes, start a new check; skips carry over. Don't start one without a change to test, and
   stop after three checks that don't improve: tell the user which items still fail and what you
   tried. The agent is Integrated once `passes` is `true` (it needs at least one triggered item), and `get_agent` then returns `nextStep`
   `start_discovery`. If `newItems` is not empty, the manifest changed since the check, so run it
   again.

7. **Run an evaluation.** Quote the estimate and spend cap from the `run_starter_evaluation`
   description (if it states none, say a starter run stops at $5 and takes about 10 to 15
   minutes), say the run is optional, and end your turn asking for approval. After it, call
   `run_starter_evaluation` `{ agentId, connectionId, agentBlurb }` with that description as the
   blurb; `connectionId` is required even with one connection. (`cancel_run` stops a
   run that is still spending; `run_evaluation` runs chosen failure modes at a chosen size.) If the
   user wants an evaluation before the agent is Integrated, it works, but say that onboarding is
   not finished (its `stage` is `draft`).

   Poll `get_run_status` `{ evaluationId }` until its `status` is terminal, through the whole 10 to
   15 minutes, and tell the user its progress (turns used of the turn budget) and spend against the
   budget as you go. The conversation count fills in once attacking ends. Once the run is terminal,
   read the findings with `get_orange_results` `{ evaluationId }` (large: if your harness truncates
   it, save it outside the repo). Keep the adapter up until the run ends.

8. **Report back.** Give the user the `agentId`, its stage and, after a run, the `resultsUrl` that
   `run_starter_evaluation` and `get_run_status` return. Say what you integrated: the integration
   check's items with their status, which items the user chose to skip and why, whether
   `instrument` sends spans, and which tools they cover. After a run, always read two or three conversations with
   `get_orange_conversation`. If none show tool calls, check the adapter log for whether the agent
   called a tool; if it did, check that its spans set the guide's attributes and are created inside
   `onMessage`, and tell the user the results lack tool context until that is fixed.
