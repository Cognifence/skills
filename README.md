# Cognifence Skills

Distributable [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills)
that teach a coding agent (Claude Code, Codex, Copilot, Gemini, …) how to work with Cognifence.

Each subdirectory here is one self-contained skill. A user installs one into their agent's skills
directory with the `skills` CLI (see below); from then on the agent can carry out that workflow —
connect an app to Cognifence, run an evaluation, and so on — without the user having to know the
API by hand.

## Catalog

| Skill | What it does |
| --- | --- |
| [`cognifence-evaluate`](cognifence-evaluate/) | Wire the user's existing chat agent to Cognifence over the Connect WebSocket, provision it through the Cognifence MCP tools, and kick off a starter evaluation. |

## Anatomy of a skill

Every skill folder follows the same layout:

- **`SKILL.md`** — the single source of truth. YAML frontmatter (`name`, `description`) tells the
  agent when to reach for the skill; the body is the step-by-step procedure it follows. The
  `description` is the only text most runtimes see up front, so it carries the trigger phrasing.
- **`AGENTS.md`** — a thin pointer for non-Claude runtimes (Codex, Copilot, Gemini): "read and
  follow `SKILL.md`." It adds no procedure of its own.
- **`references/`** — supporting detail the procedure links to (setup guides, SDK notes, copyable
  templates). Kept out of `SKILL.md` so the main procedure stays short and the agent pulls in
  detail only when a step needs it.

## Installing a skill

Install a skill with the `skills` CLI, pointing it at this repo and naming the skill to add:

```bash
npx skills add Cognifence/skills --skill cognifence-evaluate
```

`Cognifence/skills` is this repo; `--skill <name>` picks which skill in it to install. The CLI
fetches the skill and installs it into your agent's skills directory (Claude Code, Codex, Copilot,
Gemini, …). After it finishes, reload the agent's plugins/skills or restart it (e.g. restart Claude
Code) so the new skill is discovered.

Most skills also need the [Cognifence MCP server](cognifence-evaluate/references/mcp-setup.md)
configured — see the individual skill for what it requires.

## Authoring a new skill

Add a directory named for the skill and follow the conventions above:

1. Write `SKILL.md` with `name` (matching the directory) and a `description` that spells out the
   situations the skill should trigger on. Keep the body an ordered, load-bearing procedure and
   push detail down into `references/`.
2. Add an `AGENTS.md` that points cross-runtime agents at `SKILL.md`.
3. Add the skill to the **Catalog** table above and to the top-level [`AGENTS.md`](AGENTS.md).

Bake in the guardrails the existing skill uses: confirm before any paid/irreversible action, never
commit or echo secrets (keep tokens in the environment or an already-gitignored `.env`), and read
config from the environment rather than hard-coding it.
