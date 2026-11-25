# Cognifence Skills

[![Agent Skills](https://img.shields.io/badge/Agent_Skills-SKILL.md-D97757)](https://agentskills.io)
[![skills CLI](https://img.shields.io/badge/npx-skills_add-CB3837?logo=npm)](https://www.npmjs.com/package/skills)
[![Node.js 22.20+](https://img.shields.io/badge/Node.js-%E2%89%A522.20-5FA04E?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)

[Agent Skills](https://agentskills.io) that teach your coding agent (Claude Code, Codex, Amp,
Cursor, GitHub Copilot, Gemini CLI, OpenCode, …) to connect your agent to the Cognifence
evaluation platform and run evaluations. Each skill is a folder with a `SKILL.md` procedure your
coding agent follows, plus the references it reads when a step needs them.

[Documentation](https://docs.cognifence.ai/skills/) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

## Installation

Requires Node.js 22.20 or newer for the [`skills` CLI](https://www.npmjs.com/package/skills).
Install a skill into your project:

```sh
npx skills add Cognifence/skills --skill cognifence-evaluate
```

Pass `-a` to choose the coding agents to install for (such as `claude-code`, `codex`, `amp`,
`cursor`, `github-copilot`, `gemini-cli`, `opencode`, or another
[supported agent](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)), `-g` to
install for your user instead of the project, and `--list` to list the skills without installing.
Reload your coding agent's skills or restart it afterwards so it discovers the new skill.

Claude Code and Amp prefer a user-level copy of a skill over the project's copy (in Claude Code,
`~/.claude/skills/` wins over `.claude/skills/`; in Amp, user skills win over `.agents/skills/`).
If you installed the skill with `-g` earlier, your coding agent keeps using that copy, so update it
with `npx skills update -g` or remove it with `npx skills remove -g cognifence-evaluate`.
`amp skill info cognifence-evaluate` shows the path Amp loads.

## Quick start

1. Install the `cognifence-evaluate` skill as above.
2. Create an MCP token in the Cognifence app under **Settings → Tokens → MCP clients**, with
   **Read + write** capability, and add the Cognifence MCP server to your coding agent. In Claude
   Code, from your agent's repository:

   ```sh
   claude mcp add --transport http cogni <origin>/mcp --header "Authorization: Bearer <YOUR_TOKEN>"
   ```

   Replace `<origin>` with the Cognifence app origin you sign in to. For Codex, Amp, other
   clients, or a `.mcp.json` your team can share, see
   [Connect a client](https://docs.cognifence.ai/guide/mcp/connect/).
3. In your agent's repository, ask your coding agent:

   ```text
   Connect my chatbot to Cognifence and run an evaluation.
   ```

## Skills

### cognifence-evaluate

Connects your existing chat agent to Cognifence over the Connect WebSocket, provisions it
through the Cognifence MCP tools, and runs a starter evaluation. The procedure is in
[`SKILL.md`](cognifence-evaluate/SKILL.md). It triggers when you ask your coding agent to
connect your agent or chatbot to Cognifence, run an evaluation, or red-team or safety-test
your chatbot.

It needs the [Cognifence MCP server](https://docs.cognifence.ai/guide/mcp/) configured in your
coding agent, and an agent with one function that takes the user's message and returns a reply.
It includes Connect snippets and adapters for JavaScript or TypeScript (Node.js or Bun) and
Python. The [MCP server docs](https://docs.cognifence.ai/guide/mcp/tools/) describe the tools it
calls.

<details>
<summary>What the skill does</summary>

1. Checks that the Cognifence MCP tools are reachable.
2. Finds your agent's `(message) -> reply` function, and asks you which one when several fit.
3. Installs the Connect SDK and adds a single `connect()` call that forwards each chat turn
   to that function. For a hardened long-running process, it copies a fuller
   [adapter template](cognifence-evaluate/references/adapter-templates/) instead.
4. Writes a full description of your agent from your repository, asks you to fill the gaps,
   and creates the agent and a Connect key over MCP; the adapter registers the agent's Connect
   connection itself when it connects (SDK 0.10+). It recommends
   sending your agent's OpenTelemetry spans over the Connect socket, through the tracer provider
   you already use, so the evaluation sees its tool calls.
5. Starts the adapter, confirms it connected, and asks you before starting the starter
   evaluation, because a run calls real LLM providers and costs money.
6. Gives you the agent ID and the link to the evaluation's results.

</details>

The skill never puts the Connect key or MCP token in tracked files. The MCP token stays in your
coding agent's MCP config or environment; the Connect key lives in the adapter's environment or a
gitignored `.env`. Connect URLs must use `wss://`; the SDK refuses plaintext
`ws://` except toward localhost. Only one adapter process may serve a deployment ID at a time;
copies with different deployment IDs, such as staging and a laptop, run side by side.
