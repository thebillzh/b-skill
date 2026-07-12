# Skill Design Guide

Principles for writing effective `skills/` SKILL.md files.


## Context window is a public good

Skills share the context window with system prompt, conversation history, other skills, and the user's request. The model is already smart - only add what it doesn't already know.

Challenge every paragraph: "Does this justify its token cost?"

Prefer concise examples over verbose explanations.

## Progressive disclosure

Skills load in three levels:

1. **Metadata** (name + description in frontmatter) - always in context (~100 words)
2. **SKILL.md body** - loaded when skill triggers (keep under 500 lines)
3. **Bundled resources** (`scripts/`, `references/`, `assets/`) - loaded on demand

If a skill grows large, split heavy reference material into sub-files and reference them from SKILL.md. The body should say *when* to read each sub-file.

## Degrees of freedom

Match specificity to fragility:

- **High freedom** (prose guidance): multiple valid approaches, context-dependent decisions
- **Medium freedom** (pseudocode/parameterized scripts): preferred pattern exists, some variation OK
- **Low freedom** (exact scripts, few params): fragile operations, consistency critical, specific sequence required

Narrow bridge with cliffs → exact guardrails. Open field → loose guidance.

## Triggering

The `description` field in frontmatter is the primary trigger mechanism. Include both what the skill does and when to use it. "When to use" sections in the body are useless - the body only loads *after* triggering.

## What not to include

- README, CHANGELOG, or meta-docs about the skill itself
- Information the model already knows (common CLI tools, standard APIs)
- Setup/installation instructions for the skill author
- Instructions to show, transcribe, echo, or explain internal reasoning in output — ask for evidence and justification of conclusions instead (reasoning-echo instructions can trigger refusal classifiers on newer Claude models)
- Instructions a newer model no longer needs — on each model capability jump, re-audit skills and remove them; over-prescriptive skills written for older models degrade output
- Hard rules without the reason attached — instructions perform better when the why travels with them
