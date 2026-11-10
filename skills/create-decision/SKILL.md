---
name: create-decision
description: Records an architecture, design, scope or method decision in knowledge/decisions, with its status (Active, Superseded or Proposed), author, alternatives and “Verified with”. Use it when the approver or you make a choice with consequences whose why must outlive the code, or to supersede an earlier decision.
---

# create-decision

Record one decision per file in `knowledge/decisions/`. A decision says **why** something was chosen over the
alternatives, so that nobody (person or agent) reopens it or undoes it by accident.

## When to use it
- The approver makes a choice with consequences (scope, stack, data model, identity, escalation).
- **You** make a judgement call while working (a name, a default value with trade-offs, a structure) because the spec
  did not settle it.
- A current decision changes: a **new** one is created that supersedes it; history is never rewritten.
- A proposal that needs an OK: it is recorded as `Proposed` and noted in `docs/delivery-plan/questions.md`.

## File name
`knowledge/decisions/<YYYY-MM-DD>-<NNN>_<slug>.md`

- `<YYYY-MM-DD>`: today's date (`date +%Y-%m-%d`).
- `<NNN>`: the project's **global sequence** of decisions, in three digits: the number after the highest one in
  `knowledge/decisions/`, whatever its date. That way a decision is cited by its number (“decision 048”).
- `<slug>`: a short kebab-case summary.
- Example: `2026-11-05-012_passwordless-login-with-otp.md`.

## Format

Write the decision in `method.language` of `sdd.config.json` (if it is not set, in the user's language). The
template's headings, frontmatter keys, status values and IDs stay exactly as they are (rule M-10).

```markdown
---
title: <the decision, in one line>
description: <one sentence: what was decided and why, briefly>
updated_at: <YYYY-MM-DD>
project_version: <tag or version, if there is one; do not make it up>
status: Active            # Active | Superseded | Proposed
author: <name of whoever decided, `agent`, or `Name + agent`>
tags: [<topics>]
---

# <title>

**Decided by:** <same as `author`, with nuances if there are any>
**Date:** <YYYY-MM-DD>

## Context
<The situation and the forces at play. Link the discovery, the gotchas or the review that prompt it.>

## Decision
<The choice, stated directly: “We use…”, “The portal does not…”.>

## Alternatives considered
- **<Option B>** — <why not>
- **<Option C>** — <why not>

## Consequences
<What it enables, what it costs, what it fixes in place and what needs watching.>

## Verified with
<Salesforce skills consulted, official documentation (`platform-docs-get`, with the page title), spikes in the org or
Slack threads. In a scope or method decision with no technical component: “Not applicable: scope decision”.>

## Related
- [<another decision, spec or gotcha>](<relative path>)
```

## Superseding a decision
1. In the **old** one: `status: Superseded`, `updated_at` to today and, under the title,
   `> Superseded by [<new title>](<new file>.md)`.
2. In the **new** one: `> Supersedes [<old title>](<old file>.md)`, and in **Context**, what changed and why it is
   justified.
3. Both are kept: the old one is the history.

## Rules
- One decision per file. Short; link instead of duplicating.
- **`author` always:** the **name** of the person who decided, `agent` if the choice was yours, or `Name + agent`.
  The agent's decisions stay visible so that the approver can supersede them.
- **Only `Active` decisions bind.** `Superseded` is history; `Proposed` is a proposal and is not acted on until the
  approver confirms it (then it becomes `Active`, with their name in `author`).
- **“Verified with” before recording it:** every technical decision is checked against the area's Salesforce skills
  and the official documentation, not only against the customer's design. Whatever is not documented becomes a
  validation in `questions.md`, and the decision stays `Proposed` or conditional on it.
- Never delete a decision. Once written, link it from the specs, gotchas and steps that use it.
