# Cognifence Connect SDK

`cognifence_connect` (Python) / `@cognifence/connect` (JS/TS) is the customer client for the
Cognifence Connect dial-out WebSocket protocol. Your adapter dials the platform, completes the
`session.hello` handshake, and serves inbound chat turns by calling your handler. The client
redials on a drop on its own — you do not manage the socket.

## Install (not from a public registry)

Both packages ship together as a single **GitHub Release** — nothing is on PyPI or the npm
registry. Use the latest `vX.Y.Z` release tag.

**JS/TS** — depend on the release tarball:

```bash
bun add https://github.com/Cognifence/cognifence-connect/releases/download/vX.Y.Z/cognifence-connect-X.Y.Z.tgz
# or: npm i <same URL>
```

**Python** — pin it by git tag in `pyproject.toml` (house convention), then `uv sync`:

```toml
[project]
dependencies = ["cognifence-connect==X.Y.Z"]

[tool.uv.sources]
cognifence-connect = { git = "https://github.com/Cognifence/cognifence-connect.git", tag = "vX.Y.Z", subdirectory = "clients/python" }
```

## `connect()` options

**JS** — `connect(options)` returns a `ConnectedAgent { done, close() }`:

```ts
import { connect } from "@cognifence/connect";

const agent = await connect({
  url: process.env.COGNI_CONNECT_URL,   // wss://…
  token: process.env.COGNI_CONNECT_KEY, // rides the WS upgrade as Authorization: Bearer
  manifest: { channels: [{ name: "chat", direction: "duplex" }], tools: [] },
  onMessage: async (msg, ctx) => `...reply...`, // return a string reply, or undefined for none
  onToolCall: async (call) => ({ ok: true }),   // optional
  onRunSetup: async (run) => {},                 // optional
  onRunCancel: async (run) => {},                // optional
});

await agent.done;   // resolves after close(); REJECTS with a terminal error (e.g. SupersededError)
// await agent.close(); // orderly shutdown
```

**Python** — `await connect(...)` returns a `ConnectAgent`; keyword args are snake_case:

```python
from cognifence_connect import connect, ConnectError, SupersededError

agent = await connect(
    url=os.environ["COGNI_CONNECT_URL"],
    token=os.environ["COGNI_CONNECT_KEY"],
    manifest={"channels": [{"name": "chat", "direction": "duplex"}], "tools": []},
    on_message=on_message,       # async (msg, ctx) -> str | None
    on_tool_call=on_tool_call,   # optional
    on_run_setup=on_run_setup,   # optional
    on_run_cancel=on_run_cancel, # optional
)
await agent.wait()   # returns after close(); RAISES SupersededError / ConnectError on a terminal end
# await agent.close()
```

In JS the `manifest.tools` array must be present (pass `tools: []` when you declare none); in
Python the manifest is validated and `tools` may be omitted, but passing `"tools": []` keeps the
two adapters symmetric.

## Manifest and channels

The manifest declares what the platform may drive. Each channel has a `direction`:

- `duplex` — the platform sends turns to the agent AND the agent replies. This is what a chat
  agent needs.
- `inbound` — platform -> agent only.
- `outbound` — agent -> platform only (an inbound `channel.send` on an outbound-only channel is
  refused).

For a chat agent the whole manifest is one duplex channel named `chat` and no tools. Tools are
optional; only declare them if the platform should be able to invoke functions on your agent, and
then also pass `onToolCall`. The manifest is hashed (JCS/RFC 8785) into the handshake, so it must be
byte-stable between runs of the same agent identity.

## Handling a turn: `onMessage`, `ctx.send`, cancellation

`onMessage(msg, ctx)` is called once per inbound chat turn. `msg.body` is the user text (plus
`msg.channel`, `msg.runId`, `msg.callId`, `msg.conversationId`). Two ways to reply:

- **Return a string** — sent as the single reply for that turn. Return `undefined`/`None` to send
  nothing.
- **Stream with `ctx.send(part)`** — call it any number of times to emit reply parts, then return
  `undefined`/`None` (returning a string as well would send an extra reply). After the turn is
  cancelled, `ctx.send` is a silent no-op.

**Cancellation.** The platform can cancel an in-flight turn (`call.cancel`, a deadline, or a socket
drop). Honor it so you stop spending on a turn nobody is waiting for:

- JS: `ctx.signal` is an `AbortSignal` — pass it into your handler / fetch and stop when it aborts.
  Tool calls likewise get `call.signal`.
- Python: the handler task is cancelled — `asyncio.CancelledError` is raised into it. Let it
  propagate (don't swallow it), and `ctx.send` after cancellation is ignored.

`onToolCall(call)` (if declared) returns a plain object/dict result. `onRunSetup` / `onRunCancel`
are optional lifecycle hooks; a chat-only adapter usually needs neither.

## Reconnect-lite and terminal states

The client is reconnect-lite: a dropped socket is redialed with jittered exponential backoff and a
fresh `session.hello` — there is no resume, and anything in flight at drop time fails fast. You
never redial yourself. Two ends are **terminal** (the client stops for good — do NOT restart the
process into a redial loop):

- **`SupersededError`** — the platform closed the socket because another connection took over this
  agent identity (e.g. a rolling deploy, or a second adapter started with the same key). This is an
  orderly handoff: `agent.done` rejects (JS) / `agent.wait()` raises (Python). **Exit 0** so an
  on-failure supervisor does not restart this instance and fight its successor.
- **`ConnectError` with `terminal: true`** (JS) / a non-retriable `ConnectError` (Python) — a real
  refusal a redial cannot fix: bad/revoked token (HTTP 401/403), policy rejection, or an oversized
  manifest. Surface it and exit non-zero; the fix is a new key or a smaller manifest, not a retry.

A transient failure (unreachable proxy, timed-out hello) is handled internally by the backoff loop
— you only observe the two terminal ends above.

## Transport rules

- **`wss://` only.** The client refuses to send the bearer token over plaintext `ws://` unless the
  host is loopback (`localhost` / `127.0.0.0/8` / `::1`). Always use `wss://` in real use.
- **Frame cap.** One wire frame is capped at `MAX_FRAME_BYTES` (256 KiB). A reply larger than that
  is rejected — the SDK surfaces it as a wire error, not a crash — so keep individual replies
  bounded; stream long output as multiple `ctx.send` parts instead of one huge frame.
- **Liveness** is the transport's job (WS ping/pong); there are no application heartbeat verbs to
  implement.
