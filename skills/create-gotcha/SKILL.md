---
name: create-gotcha
description: Documents in knowledge/gotchas a counter-intuitive trap of the platform, a tool or the org, with its evidence, so that nobody pays for it twice. Use it right after losing time to a surprising behaviour of Salesforce, the CLI or a skill.
---

# create-gotcha

Record one trap per file in `knowledge/gotchas/`. A good gotcha turns the time that has **already** been lost into
time that someone else will **not** have to lose.

## When to use it
- The platform, the CLI, a skill or the org behaved in a surprising or undocumented way.
- A test or a deployment failed for a non-obvious reason that another change could trigger again.
- There is an invariant that, if broken, fails in a confusing way.

Write it **at the moment**, when you understand the cause and the fix.

## File name
`knowledge/gotchas/<slug>.md`, in short kebab-case that describes the trap (`anonymous-apex-without-system-mode`).

## Format

Write the gotcha in `method.language` of `sdd.config.json` (if it is not set, in the user's language). The
template's headings and frontmatter keys stay exactly as they are (rule M-10).

```markdown
---
title: <the trap, in one line>
description: <one sentence: the symptom and the cause>
updated_at: <YYYY-MM-DD>
project_version: <tag or version, if there is one>
tags: [<topics>]
evidence: "<Reproduced in <org alias> on <YYYY-MM-DD> (<step>): “<actual error text>” | Slack: <link> | Documentation: <title and URL>"
---

# <title>

## Symptom
<What is observed: the literal error, the wrong output, the confusing behaviour.>

## Cause
<The underlying reason. This is the valuable part.>

## Fix
<What to do instead, with a snippet if it helps.>

## How to avoid it
<The general rule so that this class of problem does not come back, and which parts of the project it touches.>

## Related
- [<decision that mitigates it, step or step report where it appeared>](<relative path>)
```

## Rules
- One trap per file; if there is a family of them, link them.
- Start with the **symptom** (how it is recognized) and then the **cause**.
- **`evidence` always:** say whether it was reproduced in the org (which one and when) or whether it comes from Slack
  or from the documentation. A gotcha without evidence is a suspicion: record it as a validation in `questions.md`.
- Concrete: the actual error text and real snippets are worth more than abstract advice.
- If a decision mitigates the gotcha, link the two in both directions.
