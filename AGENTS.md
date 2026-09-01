# Cognifence Skills

This directory is a catalog of Cognifence [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills).
Each subdirectory is one self-contained skill, and its own `SKILL.md` is the single source of truth
for that skill's procedure. This file adds no procedure of its own.

Codex, Copilot, Gemini, and any other agent runtime: to carry out a skill, read and follow that
skill's `SKILL.md` (each folder also carries an `AGENTS.md` pointing to it).

## Skills

- **[`cognifence-evaluate`](cognifence-evaluate/SKILL.md)** — connect an agent to Cognifence over
  the Connect WebSocket, provision it through the Cognifence MCP tools, and run an evaluation.
  Requires the Cognifence MCP server (see
  [`cognifence-evaluate/references/mcp-setup.md`](cognifence-evaluate/references/mcp-setup.md)).

When you add a skill, add a row here and in [`README.md`](README.md).
