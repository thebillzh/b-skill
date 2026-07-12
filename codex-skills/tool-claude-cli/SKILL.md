---
name: tool-claude-cli
description: >-
  Run Claude Code CLI from Codex correctly: stream JSONL, Opus, no USD caps, parallel tracked jobs, and stale-session checks.
user-invocable: true
codex-only: true
---

# Claude CLI from Codex

Use this skill whenever Codex invokes `claude` directly for reviews, audits, comparisons, or delegated analysis.

## Rules

1. **Use JSON streams.** Always pass `--input-format stream-json --output-format stream-json --verbose`.
2. **Use Opus.** Default to `--model opus`; use the `opus[1m]` long-context alias only when the account supports it and the task needs the larger context. Honor an explicit human model choice.
3. **No USD caps.** Never pass `--max-budget-usd`.
4. **Prefer stdin over `-p`.** Send prompts as stream-json user messages over stdin so stdout remains machine-parseable JSONL.
5. **Parallelize independent jobs.** Start independent Claude reviewers/auditors together; wait after launch, not between launches.
6. **Track every job.** Keep a PID, stdout JSONL log, stderr log, start time, and cleanup path for each process.
7. **Parse JSONL, not tails.** Use the final `result` event as the source of truth. A missing result, `is_error: true`, or nonzero exit is a failed job.
8. **Detect stale sessions from JSONL.** While waiting, check process liveness plus JSONL mtime/size and the last event. If output stops moving, inspect whether it is waiting on permissions/tools/rate limits before deciding to continue, retry, or kill.
9. **Reviewer jobs are read-only.** For review/audit calls, also disallow editing tools and state “make no edits” in the prompt.
10. **Use macOS-safe timeouts.** Do not assume GNU `timeout` exists.

## Protocol shape

Use stream-json as the protocol: stdin carries user messages, stdout is logged as JSONL, stderr is separate, and callers parse structured result events.
