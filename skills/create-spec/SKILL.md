---
name: create-spec
description: Writes a spec in knowledge/specs before building anything non-trivial, in two parts and in this order. First, requirements with IDs and “Given/When/Then” acceptance criteria that say where they are checked. Then, the design and the contracts. No plan and no progress checkboxes. Use it in the Design stage and for any level 2 or 3 change.
---

# create-spec

Write the spec in `knowledge/specs/` **before** building, with the project's approver. The spec is the contract: it
says what the system has to do, how you know it does it and how it is designed. It does **not** say in what order it
is built or how much is left: the order and the split of the work live in the delivery plan (`docs/delivery-plan/`),
and progress in `docs/delivery-plan/status.md`.

> Design choices and their why go into **decisions** (`create-decision`), not here. When a choice has already been
> made while you write the spec, record it **at that moment** and link it; do not leave “record decision X” as a
> pending task.

## When to use it
- In the **Design** stage, after the Plan gate has validated the discovery.
- Before any level 2 or 3 feature, subsystem or redesign (levels in `implementation-integration-plan`).
- For new work, one spec per feature or contract that can be approved and tested separately. If there are several, an
  index spec links them. A spec already in progress can remain a single one, with blocks per area.
- If the project has an Agentforce agent, its Agent Spec goes in a separate spec with the `agentforce-generate`
  (ADLC) template, and it also carries requirements with AC and its test plan with `sf agent test`, including the
  security tests (`agentforce-test`, Mode C).

## File name
`knowledge/specs/<YYYY-MM-DD>-<NNN>_<slug>.md`

- `<YYYY-MM-DD>`: today's date (`date +%Y-%m-%d`).
- `<NNN>`: the project's **global sequence** of specs, in three digits: the number after the highest one in
  `knowledge/specs/`, whatever its date. That way a spec is cited by its number (“spec 002”).
- `<slug>`: short kebab-case.
- Example: `2026-11-05-001_self-service-portal.md`.

## What goes where

| It is… | It goes in |
|---|---|
| A behaviour the system must have | A requirement with its AC (Part 1) |
| Something not yet known that blocks | `[PENDING: Q-NN]` inline, with its entry in `docs/delivery-plan/questions.md` |
| A choice already made (technology, pattern, scope) | A decision, recorded now and linked |
| A state that must be true **before** building | Preconditions (Part 2) |
| The order, the split of the work and what is done later | The delivery plan, never the spec |
| A trap already paid for | A gotcha (`create-gotcha`), linked from the part of the design that avoids it |

## Format

Write the spec in `method.language` of `sdd.config.json` (if it is not set, in the user's language). The template's
headings, frontmatter keys, field names and IDs stay exactly as they are: translate the prose, never those tokens
(rule M-10).

```markdown
---
title: <name of the spec, in one line>
description: <one sentence saying what it specifies>
updated_at: <YYYY-MM-DD>
project_version: <tag or version, if there is one; do not make it up>
status: Draft            # Draft | Ready | Implemented | Accepted
author: <approver's name + agent, or whoever writes it>
tags: [<topics>]
---

# <title>

# Part 1 · Requirements

## Why
<The problem, for whom, and what success looks like, with observable measures. Cite the discovery.>

## What
<What is in scope, in terms of behaviour.>

### Exclusions (non-goals)
- <what is not done, and why>

## Actors
<Who uses or touches the system: profiles, internal users, guest user, the agent, external systems.>

## Requirements

### R-<AREA>-01 — <behaviour, in one sentence>
- Source: <customer document and page, discovery, decision>
- Priority: <P0 | P1> · Status: <Draft | Ready | Implemented | Accepted>
- AC-<AREA>-01.1 — Given <context>, when <stimulus>, then <observable result> (<where it is checked>).
- AC-<AREA>-01.2 — Given <context>, when <error, rejection or denied permission>, then <result> (<where>).
- Open items: [PENDING: Q-NN] or “none”.

## Assumptions and open items
<Reversible assumptions being made, marked as such, and the list of this spec's `[PENDING: Q-NN]`.>

# Part 2 · Design

## Preconditions
- [ ] <predicate that must hold before building: licence, org setting, permission that Support enables…>

## Architecture and source of truth
<Pieces, responsibilities, and which object or system owns each piece of data.>

## Contracts
<The contracts that unblock parallel work: data model, states and transitions, integrations, identity and access.
Each contract cites the requirements it satisfies and its invariants.>

## <Thematic sections>
<Whatever is needed to build without guessing: closed lists of values, data shapes, API names, configuration, edge
cases.>

## Cross-cutting concerns
<Identity and permissions, failures and retries, observability, delivery and deployment; the gotchas this design
avoids.>

## Test strategy
<Which kind of verification covers each family of AC (verification table of `implementation-integration-plan`,
reference `implementation.md`): Apex test, `sf agent test`, Jest, allowed/denied test with `runAs`, demo step…>

## References
- Decisions: [<title>](../decisions/<file>.md)
- Gotchas: [<title>](../gotchas/<file>.md)
- Discovery: [<title>](../discovery/<file>.md)
- Delivery plan: [README](../../docs/delivery-plan/README.md)

## Verified with
<Salesforce skills and official documentation (`platform-docs-get`) against which the technical choices and the AC
were checked; whatever could not be confirmed, as a pending validation in `questions.md`.>

## Change log
<Empty until the Design gate. After it, one row for each requirement or AC added, modified or removed.>

| Date | Type | IDs | Before → after | Changes behaviour? | Origin | Approval | Commit |
|---|---|---|---|---|---|---|---|
```

## Rules
- **Requirements and AC first.** No requirement without at least one AC, and no contract moves to `Ready` without AC.
- **Falsifiable AC:** stimulus, observable result and where it is checked. No “fast”, “adequate” or “correct”. They
  also cover the errors, rejections and denied permissions that matter.
- **Requirements do not prescribe implementation**, except what the customer imposes.
- **Before moving a part to `Ready`:** its requirements meet the above, do not contradict `Active` decisions, and no
  `[PENDING]` that blocks it remains. Detail in `implementation-integration-plan`, reference
  `discovery-knowledge.md` §2.
- **No plan or progress in the spec:** neither step checkboxes nor “done”. The status per requirement, if it differs
  from the spec's, lives in `docs/delivery-plan/traceability.md`.
- **Customer sources:** cited by document and page (“Requirements document v2, p. 12”), not copied.
- **“Verified with”:** every technical choice and every AC is checked against the area's skills and the official
  documentation, not only against the customer's design. If something is not documented, it becomes a validation in
  `questions.md` instead of being taken for granted.
- **Changes to a spec that is `Ready` or later:** with the decision or finding that motivates them, linked, and
  reviewing their rows in `traceability.md` and the steps that cite it. It is not rewritten silently.
- **Change log, from the Design gate on:** every requirement or AC added, modified or removed leaves its row in the
  “Change log”, before the code or in the same commit (Type `ADDED`, `MODIFIED` or `REMOVED`). It is written with
  “Approval: pending”, and what was written is what gets approved: at level 2, by the orchestrator or, if it is
  escalated, by the approver. A removed AC leaves Part 1 and moves to the exclusions of `traceability.md`.
  `check-traceability.py` reports an error if an ID changed since the last tag (`release-N` or `design-approved`)
  without its row. Bugs and tweaks that do not touch the spec do not go here: they go to the queue in `status.md`
  (the change-request path of the `sdd-method` skill).
