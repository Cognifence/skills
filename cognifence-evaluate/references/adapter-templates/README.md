# Connect adapter templates

Drop-in adapters that dial the Cognifence Connect WebSocket and forward each chat turn to the
user's existing agent. Copy the one that matches the user's stack:

- **`connect_adapter.mjs`** — JS/TS projects (Node or Bun).
- **`connect_adapter.py`** — Python projects (run with `uv`).

Both are minimal, runnable, and env-driven. They declare the same fixed manifest — one duplex
channel named `chat`, no tools — and handle the SDK's terminal states (exit 0 on
`SupersededError`, non-zero on a real refusal).

## The seam

Each file has exactly one clearly-marked seam:

- JS: `async function customerHandler(message, signal)`
- Python: `async def customer_handler(message)`

Replace its body with a call into the user's `(message) -> reply` handler (the one found in step 2
of `SKILL.md`). `message` is the user's turn text; return the assistant's reply as a string.
Everything else in the template can stay as-is.

## Environment

Both read two variables — never hard-code them:

- `COGNI_CONNECT_URL` — the `wss://` Connect endpoint (the `connectUrl` returned by
  `mint_connect_key`, else `wss://<origin>/connect/v1`).
- `COGNI_CONNECT_KEY` — the Connect key minted by `mint_connect_key` (shown once; keep it in the
  environment or an already-gitignored `.env`, never in a tracked file).

## Run

- JS: `COGNI_CONNECT_URL=… COGNI_CONNECT_KEY=… node connect_adapter.mjs`
- Python: `COGNI_CONNECT_URL=… COGNI_CONNECT_KEY=… uv run python connect_adapter.py`

Start the adapter and confirm it prints `dialed in` BEFORE starting an evaluation run.

## One process per identity

Only ONE adapter process may hold a given agent identity (one Connect key) at a time. Starting a
second with the same key supersedes the first — the first exits 0 and stops. Do not run duplicates.
