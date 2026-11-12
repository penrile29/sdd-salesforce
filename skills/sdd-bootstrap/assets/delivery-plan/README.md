---
title: "Delivery plan of {{PROJECT}}"
description: "Steps, dependencies, waves, critical path and size of the work; written in Design with implementation-integration-plan and approved at the Design gate"
updated_at: {{DATE}}
tags: [plan, waves]
---

# Delivery plan — {{PROJECT}}

> Written in **Design**, after the spec and the decisions, with the `implementation-integration-plan` skill, which
> carries the step template the check reads. The Design gate approves it. The state of each step does **not** go
> here: it goes in [status.md](status.md). The steps live in [implementation/](implementation/), one file per wave.

## Goal, sources and scope
<Observable goal, the specs and decisions the plan comes from, and what is left out.>

<!-- if profile=light -->
> **Light profile:** a flat list of steps `W1.n` in `implementation/W1.md` (one wave), each with `Satisfies`,
> `Touches`, `Skill` and, if there is one, `Depends on`; the waves table below does not apply.

<!-- end if -->
## Waves

| Wave | Outcome | Steps |
|---|---|---|
| **W0 · Validate** | Spikes in {{ORG}} of what the documentation does not guarantee (the validations in `questions.md`) | |
| **W1 · Contracts** | The spec's contracts deployed and frozen | |
| **W2 · Build** | The pieces, in parallel by scope | |
| **W3 · AI and advanced pieces** | Agent, generative AI, documents, apps | |
| **W4 · Composition and release** | Demo data, end-to-end walkthrough, Definition of Done and release | |

Adjust the waves to the project: in a simple POC there may be one or two. What is fixed is that contracts come before
whatever consumes them.

## What can start
<The steps with no pending dependencies.>

## Open items that affect the plan
<Those in questions.md that block steps, with the steps they block.>

## Verified with
<Skills and documentation against which the order and the verifications of the plan were checked.>
