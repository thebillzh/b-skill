---
name: x-review-plan-loop
description: Stress-test a plan in .ai/plans/ via parallel adversarial review — one general-purpose subagent + one codex adversarial agent (or a second general-purpose subagent if the Codex plugin isn't installed) per round, consolidate, fix, commit, repeat. 2 rounds by default. Pairs with x-plan-init; runs before x-plan-exec.
user-invocable: true
---

# x-review-plan-loop

Hardens a plan written by `/x-plan-init` before `/x-plan-exec` touches code.

## The loop

Default 2 rounds of review (If the user specifies a different number, use that instead). Each round:

1. Launch two reviewers in **parallel** (single message, two Agent calls):
   - `general-purpose` subagent
   - `codex:codex-rescue` subagent — requires the Codex plugin for Claude Code. If it isn't installed, launch a second independent `general-purpose` subagent instead (same round prompt, no shared context with the first).
2. Same prompt to both. Self-contained — they don't see the conversation.
3. Consolidate findings. **Address every finding** — either fix it, or push back with a one-line note in the round's commit message explaining why it's being skipped (hallucinated, ceremony-only, already covered, accepted trade-off).
4. Commit + push with message `plan review round <N>: <changelog>` — `<changelog>` is a short summary of what was fixed this round (and any rejected findings, one-line each). Next round reviews a clean target.

Stop when both reviewers say **"CONVERGED: no critical or important findings"** in the same round or after the specified number of rounds.

## Round prompt must include

- Absolute paths to plan files in `.ai/plans/pr-<num>/`
- One-line project context
- **Previously-rejected findings with rebuttals** (carried forward from earlier rounds — agents are stateless, the same hallucination recurs otherwise)
- Output format: numbered findings with `Title / Where / Confidence / Severity (nit|minor|important|critical) / Flaw / Resolution`
- "State 'CONVERGED: no critical or important findings' at the top if you find none"
- "DO NOT modify any files"

## Note

Reviewers hallucinate past saturation. If a finding cites text not in the plan, refute, log it in the rejected list, and carry it into the next round's prompt — don't invent contradictions to satisfy the reviewer.
