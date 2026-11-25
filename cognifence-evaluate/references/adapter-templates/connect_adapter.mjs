// Forward each chat turn to your agent over Cognifence Connect.
//
// Install the SDK with `bun add @cognifence/connect` (or `npm install @cognifence/connect`) and
// run with COGNI_CONNECT_URL, COGNI_CONNECT_KEY, COGNI_CONNECT_DEPLOYMENT_ID and
// COGNI_CONNECT_NAME in .env:
// `node --env-file=.env connect_adapter.mjs`
//
// Run one adapter per COGNI_CONNECT_DEPLOYMENT_ID: a second one replaces the first.

import { connect, SupersededError } from '@cognifence/connect';

/**
 * Return your agent's reply to the user's message.
 *
 * Replace the body with a call to your agent, such as
 * `return await myAgent.reply(message, { signal });`. Pass `signal` on so a cancelled turn stops.
 */
async function reply(message, signal) {
  return `echo: ${message}`;
}

const {
  COGNI_CONNECT_URL: url,
  COGNI_CONNECT_KEY: token,
  COGNI_CONNECT_DEPLOYMENT_ID: deploymentId,
  COGNI_CONNECT_NAME: name,
} = process.env;
if (!url || !token || !deploymentId || !name) {
  console.error(
    'Set COGNI_CONNECT_URL, COGNI_CONNECT_KEY, COGNI_CONNECT_DEPLOYMENT_ID and COGNI_CONNECT_NAME in the environment.',
  );
  process.exit(1);
}

const manifest = {
  channels: [{ name: 'chat', direction: 'duplex' }],
  tools: [],
};

let agent;
try {
  agent = await connect({
    url,
    token,
    // Reused on every restart with the same ID; each start reports the code it runs.
    connection: { mode: 'register', deploymentId, name },
    // For a local checkout, keep its evaluations out of main-line history:
    // code: { main: false },
    manifest,
    onMessage: async (message, context) => reply(message.body, context.signal),
  });
} catch (err) {
  console.error(`[connect] connect failed: ${err.message}`);
  process.exit(1);
}

console.error('[connect] dialed in; serving chat turns');

process.on('SIGTERM', () => void agent.close());
process.on('SIGINT', () => void agent.close());

try {
  await agent.done; // resolves on close(); rejects on a terminal error
} catch (err) {
  if (err instanceof SupersededError) {
    // A newer adapter took over this key; don't restart this one.
    console.error(`[connect] ${err.message}`);
    process.exit(0);
  }
  // Refused, such as for a revoked key or an oversized manifest; redialing won't help.
  console.error(`[connect] terminal error: ${err.message}`);
  process.exit(1);
}
