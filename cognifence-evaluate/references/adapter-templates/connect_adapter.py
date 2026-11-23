"""Forward each chat turn to your agent over Cognifence Connect.

Install the SDK with `uv add cognifence-connect` (Python 3.12 or later) and run with
COGNI_CONNECT_URL and COGNI_CONNECT_KEY in .env:

    uv run --env-file .env python connect_adapter.py

Run one adapter per Connect key: a second one replaces the first.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from typing import TYPE_CHECKING

from cognifence_connect import ConnectError, SupersededError, connect
from cognifence_connect.schema import Manifest, ManifestChannelDecl

if TYPE_CHECKING:
    from cognifence_connect import MessageContext
    from cognifence_connect.schema import ChannelSendParams

MANIFEST = Manifest(channels=[ManifestChannelDecl(name="chat", direction="duplex")], tools=[])


async def reply(message: str) -> str:
    """Return your agent's reply to the user's message.

    Replace the body with a call to your agent, such as `return await my_agent.reply(message)`.
    Let `asyncio.CancelledError` propagate so a cancelled turn stops.
    """
    return f"echo: {message}"


async def on_message(message: ChannelSendParams, _context: MessageContext) -> str | None:
    return await reply(message.body)


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
            # A newer adapter took over this key; don't restart this one.
            print(f"[connect] {exc}", file=sys.stderr)
            sys.exit(0)
        except ConnectError as exc:
            # Refused, such as for a revoked key; redialing won't help.
            print(f"[connect] terminal error: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    ended.cancel()
    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
