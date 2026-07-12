# b-skills

Reusable Claude Code and Codex skills for production workflows.

Each skill is a self-contained `SKILL.md` procedure an agent loads on demand: committing and landing PRs, planning and stress-testing implementation work, running guardrail refactor loops, end-to-end test-and-fix cycles, drawing architecture diagrams, and analyzing agent session performance.

Install once, then invoke skills as slash commands (e.g. `/x-land`) or let them trigger automatically when their description matches the task. They work with Claude Code, Codex, and any other agent that reads the `SKILL.md` format.

This repository is intentionally standalone: project-specific workflows and private automations stay outside it, while the general-purpose set lives here.

## Install

```bash
./install.sh
```

For Codex setups that should see existing global Claude skills too:

```bash
./install.sh --mirror-claude
```

The installer links:

1. `skills/*` into `~/.claude/skills` and `~/.agents/skills`.
2. `codex-skills/*` into `~/.codex/skills`.

`~/.agents/skills` is a cross-agent skills directory read by both Claude-compatible agents and Codex, so anything linked there is picked up by either.

Directories used, each overridable with its env var:

1. `~/.claude/skills` — `CLAUDE_SKILLS_DIR`.
2. `~/.agents/skills` — `AGENTS_SKILLS_DIR`.
3. `~/.codex/skills` — `CODEX_SKILLS_DIR`.

Install is symlink-based: keep this cloned repo at its install location, since moving or deleting it breaks every link above.

To remove those links:

```bash
./install.sh --uninstall
```

`--uninstall` only removes symlinks that resolve back into this repo's checkout — it leaves anything else in those directories alone.

## Layout

1. `skills/` — portable skills for Claude-compatible agents.
2. `codex-skills/` — Codex-only skills.
3. `docs/` — authoring guidance and operating docs; see [`skill-design-guide.md`](docs/skill-design-guide.md) before writing a new skill.

## Skills

| Skill | Purpose |
| --- | --- |
| `analyze-codex-turn` | Parse Codex rollout JSONL into structured evidence, then write a grounded time-spent/stuck-point analysis. |
| `x-diagram` | Generate a summary ASCII diagram for a topic or the whole project. |
| `x-dryrun` | Preview the numbered steps for a task, without executing any mutations. |
| `x-e2e-test-and-fix` | Plan, run, fix, and rerun end-to-end tests until the current PR or a named flow has no open issue. |
| `x-git-commit` | Commit and push a finished unit of work on a feature branch. |
| `x-grill` | Interview the user in batched question rounds to stress-test a plan or design. |
| `x-guardrail-loop` | Run a detector-fix-audit loop on refactors and cleanups until the repo mechanically rejects the target bad pattern. |
| `x-hotpatch` | Push files straight to `main` without leaving the current branch. |
| `x-land` | Run the local quality gate, address review comments, and squash-merge a ready PR. |
| `x-plan-exec` | Execute a saved PR plan end to end into a merge-ready PR. |
| `x-plan-init` | Persist a PR implementation plan so another agent can execute it autonomously. |
| `x-review-plan-loop` | Stress-test a saved plan with parallel adversarial review rounds before execution starts. |
| `tool-claude-cli` *(codex-skills/, Codex-only)* | Run the Claude Code CLI correctly from Codex — streaming JSON, model choice, parallel tracked jobs. |

Skills named `x-*` are user-invocable workflow skills, run as slash commands (e.g. `/x-land`); the rest trigger from their description matching the task at hand.

## Prerequisites

1. `git` and `bash`.
2. Python 3 — 3.9+ recommended; `analyze-codex-turn`'s parser falls back to UTC-only timestamps on older versions.
3. GitHub CLI (`gh`) for the skills that read or act on PRs (e.g. `x-git-commit`, `x-land`).
4. Codex CLI (optional) — only needed for skills under `codex-skills/`.
5. Optional: documentation MCP tools (context7, DeepWiki) and the OpenAI Codex plugin for Claude Code — a few skills use these when available and degrade gracefully without them.

## Scope

These general-purpose skills are designed for use across projects and users.

1. General, reusable workflows belong here.
2. Project-specific workflows stay in that project's own repo.
3. Personal or private automations stay in your own personal global skills, not here.
4. Before adding a skill, follow the authoring guide and scrub repo paths, private assumptions, and project-specific commands from it.

## License

Licensed under the Apache License 2.0 — see [LICENSE](LICENSE).
