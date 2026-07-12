---
name: x-dryrun
description: "Dry-run a task - research the codebase and show numbered steps you'd take, without executing any mutations. Use when the user wants to preview an approach before committing to it."
user-invocable: true
---

## Instructions

### Input

Parse user input after `/x-dryrun`. The remainder is the task description.

### Constraints

- **Allowed tools**: Read, Grep, Glob, Agent (Explore only), WebFetch, WebSearch, context7/DeepWiki (if available) - anything read-only
- **Forbidden tools**: Edit, Write, Bash (mutating), NotebookEdit, Skill, any MCP tool that creates/modifies state
- Do NOT enter plan mode - this is a lightweight single-pass output

### Workflow

1. **Research** - explore the codebase to understand what files, functions, and systems the task would touch. Be thorough - the value of a dryrun is an *informed* plan, not a guess.

2. **Output** - produce a numbered step list in this format:

   ```
   ## Dryrun: <task summary>

   ### Steps

   1. **<action>** - `<tool>` on `<target>`
      <what and why, 1-2 lines>

   2. ...

   ### Risks / open questions
   - <anything uncertain or worth discussing before executing>
   ```

3. **Stop** - do not offer to execute. End with the plan.
