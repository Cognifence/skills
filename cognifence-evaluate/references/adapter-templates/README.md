# Connect adapter templates

Adapters that dial the Cognifence Connect WebSocket and forward each chat turn to the user's
existing agent. Copy the one that matches the user's stack:

- **`connect_adapter.mjs`**: JS/TS projects (Node or Bun).
- **`connect_adapter.py`**: Python projects (run with `uv`).

Both declare the same fixed manifest (one duplex channel named `chat`, no tools), read
`COGNI_CONNECT_URL` and `COGNI_CONNECT_KEY` from the environment, and handle the SDK's terminal
states: exit 0 on `SupersededError`, non-zero on a real refusal.

## Wire up the handler

Each file has one function to wire up, which returns a placeholder `echo:` reply until you do:

- JS: `async function reply(message, signal)`
- Python: `async def reply(message)`

Replace its body with a call into the user's `(message) -> reply` handler (the one found in step 2
of `SKILL.md`) before running an evaluation. `message` is the user's turn text; return the
assistant's reply as a string.

## Run

- JS: `node --env-file=.env connect_adapter.mjs`
- Python: `uv run --env-file .env python connect_adapter.py`

For an evaluation, start it in its own session as step 5 of `SKILL.md` shows, and confirm it logs
`dialed in` before the run starts.
