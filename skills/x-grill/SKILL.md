---
name: x-grill
description: Interview the user iteratively about a plan or design until shared understanding is reached. Walks each branch of the decision tree, batching up to 5 questions per round. Use when the user asks to be grilled, stress-tested, or wants to pressure-test a plan.
user-invocable: true
---

# x-grill

Stress-test a plan or design through iterative interrogation. Walk each branch of the decision tree, resolving dependencies between decisions until shared understanding emerges.

## Asking

Batch questions in numbered rounds of **up to 5**. For each question, give your recommended answer in one short line. Keep each question to 1-2 sentences. No preamble between questions.

After the user answers, generate the next round based on what their answers unblocked. Continue until every branch resolves.

## What to ask vs. look up

If a question can be answered by exploring the codebase, explore instead of asking. For library or framework details, use documentation-lookup MCP tools if available (e.g. `context7`, DeepWiki).

Focus questions on:

- Decisions that block downstream choices
- Implicit assumptions in the plan
- Edge cases and failure modes
- Scope boundaries

## Stopping

When you can write a complete spec without further input, say so: "I have what I need. Run `/x-plan-init` to persist the plan on this branch."
