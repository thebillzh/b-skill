---
name: x-diagram
description: Generate a summary ASCII diagram for a topic or the entire project. Takes optional user input to scope the diagram to a specific area.
user-invocable: true
---

## Instructions

### Step 1 - Determine scope

Parse user input after `/x-diagram`:
- **No input** → scope is the entire project. Read the project root, key directories, and entrypoints to understand the full architecture.
- **Topic provided** → scope is that specific topic. Search the codebase for relevant files (use Grep/Glob to find related modules, classes, functions).

### Step 2 - Explore the codebase

Read the relevant source files to understand:

- **Components / modules**: what are the major building blocks?
- **Data flow**: how does data move between components? What triggers what?
- **External boundaries**: APIs, databases, message queues, external services
- **Key patterns**: event buses, pub/sub, middleware chains, plugin systems
- **Entry points**: CLI commands, API routes, cron triggers, channel handlers

For the entire project, focus on the top-level architecture - don't dive into every helper function. For a specific topic, go deeper into that subsystem.

### Step 3 - Generate the diagram

Build an ASCII diagram following these rules:

**Layout direction**: Choose the orientation that best fits the flow:

- **Vertical (top-to-bottom)**: Default for deep pipelines - request enters at top, flows through processing stages, exits at bottom. Best for sequential processing chains.
- **Horizontal (left-to-right)**: Better for wide, shallow flows - multi-service communication, event fan-out, or parallel systems at the same depth. Use `──→` arrows between side-by-side containers.
- **Hybrid**: Vertical for the main spine, horizontal branches for parallel steps or service-to-service calls within a stage.

Pick whichever makes the diagram most readable. Don't force vertical when the flow is naturally lateral.

**Boxes**: Use `┌─┐│└─┘` box-drawing characters. Each component gets its own box with a descriptive title and 1-2 lines of detail.

**Fixed-width alignment**: Keep box widths roughly consistent within a container; Step 4's fix-diagram.py owns exact alignment.

**Parallel / sibling components**: Show side-by-side boxes at the same vertical level:

```
│  ┌─────────────────────┐ ┌────────────────────┐  │
│  │ Component A         │ │ Component B        │  │
│  │ detail              │ │ detail             │  │
│  └─────────────────────┘ └────────────────────┘  │
```

**Nesting**: Group related components inside a larger container box (e.g., "Agent" wraps tools, memory, loop).

**Arrows**: Use `▼` for vertical flow, `──→` for horizontal flow, `←` for responses/callbacks.

**Abstraction level**:
- DO show: component names, responsibilities, key interfaces, external service calls
- DO show: architectural names that help understanding - modules, classes, services, protocols
- DO show: data shapes at boundaries (what flows between components)
- DO NOT show: internal helper functions, temporary variables, implementation details
- Keep boxes concise: 1-3 lines of detail max

**Width**: Keep lines under 80 chars where possible. Max 100.

### Step 4 - Fix diagram alignment

Run `fix-diagram.py` from this skill's own directory — `$SKILL_DIR` below is the directory this `SKILL.md` was loaded from, not a hardcoded `~/.claude/skills` path (skills can be installed elsewhere, e.g. project-local or `~/.agents/skills`). Feed the diagram through a quoted heredoc rather than `echo '...'`, since apostrophes or other quote characters in diagram text break a single-quoted string:

```bash
python3 "$SKILL_DIR/fix-diagram.py" <<'EOF'
<diagram>
EOF
```

Use the script's output as the final diagram.

### Step 5 - Output the diagram

Output the final diagram in a fenced code block with:
1. A title line (the topic or "Project Architecture")
2. The ASCII diagram (after fix-diagram.py alignment)
3. A 1-2 sentence summary explaining the key insight or flow
