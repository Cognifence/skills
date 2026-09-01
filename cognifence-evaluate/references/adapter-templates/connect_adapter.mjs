// Cognifence Connect adapter (JS/TS) — forwards each chat turn to your agent.
//
// Install the SDK from the GitHub Release tarball (NOT a public registry):
//   bun add https://github.com/Cognifence/cognifence-connect/releases/download/vX.Y.Z/cognifence-connect-X.Y.Z.tgz
//
// Run:
//   COGNI_CONNECT_URL=wss://<origin>/connect/v1 COGNI_CONNECT_KEY=<key> node connect_adapter.mjs
//
// Only ONE adapter process may hold a given agent identity (one Connect key) at a time.

import { connect, SupersededError } from "@cognifence/connect";

// ── The one seam to wire up ────────────────────────────────────────────────
// Replace the body with a call into YOUR agent's (message) -> reply handler.
// `message` is the user's turn text; return the assistant's reply as a string.
// `signal` is an AbortSignal — honor it so a cancelled turn stops spending.
async function customerHandler(message, signal) {
  // e.g.  return await myAgent.reply(message, { signal });
  return `echo: ${message}`;
}
// ───────────────────────────────────────────────────────────────────────────

const url = process.env.COGNI_CONNECT_URL;
const token = process.env.COGNI_CONNECT_KEY;
if (!url || !token) {
  console.error("Set COGNI_CONNECT_URL and COGNI_CONNECT_KEY in the environment.");
  process.exit(1);
}

// Fixed manifest: one duplex chat channel, no tools.
const manifest = { channels: [{ name: "chat", direction: "duplex" }], tools: [] };

const agent = await connect({
  url,
  token,
  manifest,
  onMessage: async (msg, ctx) => customerHandler(msg.body, ctx.signal),
});

console.error("[connect] dialed in; serving chat turns");

process.on("SIGTERM", () => void agent.close());
process.on("SIGINT", () => void agent.close());

try {
  await agent.done; // resolves on close(); rejects on a terminal error
} catch (err) {
  if (err instanceof SupersededError) {
    // Orderly handoff to a newer connection for this identity — do NOT restart.
    console.error(`[connect] ${err.message}`);
    process.exit(0);
  }
  // A real refusal (bad/revoked key, policy, oversized manifest) — a redial won't fix it.
  console.error(`[connect] terminal error: ${err.message}`);
  process.exit(1);
}
