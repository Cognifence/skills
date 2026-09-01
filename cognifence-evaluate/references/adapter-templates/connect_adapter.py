"""Cognifence Connect adapter (Python) — forwards each chat turn to your agent.

Install the SDK by git-tag pin (NOT PyPI), in pyproject.toml, then `uv sync`:

    [project]
    dependencies = ["cognifence-connect==X.Y.Z"]

    [tool.uv.sources]
    cognifence-connect = { git = "https://github.com/Cognifence/cognifence-connect.git", tag = "vX.Y.Z", subdirectory = "clients/python" }

Run:

    COGNI_CONNECT_URL=wss://<origin>/connect/v1 COGNI_CONNECT_KEY=<key> uv run python connect_adapter.py

Only ONE adapter process may hold a given agent identity (one Connect key) at a time.
"""

import asyncio
import os
import signal
import sys

from cognifence_connect import ConnectError, MessageContext, SupersededError, connect
from cognifence_connect.schema import ChannelSendParams

# Fixed manifest: one duplex chat channel, no tools.
MANIFEST = {"channels": [{"name": "chat", "direction": "duplex"}], "tools": []}


# ── The one seam to wire up ─────────────────────────────────────────────────
# Replace the body with a call into YOUR agent's (message) -> reply handler.
# `message` is the user's turn text; return the assistant's reply as a string.
# The task is cancelled on a cancelled turn — let asyncio.CancelledError propagate.
async def customer_handler(message: str) -> str:
    # e.g.  return await my_agent.reply(message)
    return f"echo: {message}"
# ────────────────────────────────────────────────────────────────────────────


async def on_message(msg: ChannelSendParams, ctx: MessageContext) -> str | None:
    return await customer_handler(msg.body)


async def main() -> None:
    url = os.environ.get("COGNI_CONNECT_URL")
    token = os.environ.get("COGNI_CONNECT_KEY")
    if not url or not token:
        print("Set COGNI_CONNECT_URL and COGNI_CONNECT_KEY in the environment.", file=sys.stderr)
        sys.exit(1)

    try:
        agent = await connect(url=url, token=token, manifest=MANIFEST, on_message=on_message)
    except ConnectError as exc:
        print(f"connect failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("[connect] dialed in; serving chat turns", file=sys.stderr)

    stop = asyncio.Event()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop.set)
    stopped = asyncio.create_task(stop.wait())
    ended = asyncio.create_task(agent.wait())
    await asyncio.wait({stopped, ended}, return_when=asyncio.FIRST_COMPLETED)

    if ended.done():
        stopped.cancel()
        try:
            ended.result()
        except SupersededError as exc:
            # Orderly handoff to a newer connection for this identity — do NOT restart.
            print(f"[connect] {exc}", file=sys.stderr)
            sys.exit(0)
        except ConnectError as exc:
            # A real refusal (bad/revoked key, policy) — a redial won't fix it.
            print(f"[connect] terminal error: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    ended.cancel()
    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
