---
title: "Operational status of {{PROJECT}} (single source of truth)"
description: "Stage, external requests, sessions, steps, reservations, changes in the org, blockers and evidence; a single writer"
updated_at: {{DATE}}
tags: [status, orchestration]
---

# Operational status — single source of truth

> **A single writer: the orchestrator** (the main session). The other sessions return their status to it and it
> consolidates it here. If something contradicts this file, verified reality wins (org, files, git) and it is
> corrected here. Last reconciliation: **{{DATE}}**, when bootstrapping the project.

## Current stage — map

| Stage | What it is | State |
|---|---|---|
| **1. Plan** | Environment verification (rule M-08) and discovery | ⏳ In progress since {{DATE}} |
| **2. Design** | Spec (requirements and AC, then design), decisions, delivery plan and its independent review | — |
| **3. Execution** | Steps by wave, with tests first and independent review | — |
| **4. Review** | Integration, Definition of Done and release | — |

## Requests and work items
Requests to third parties or work outside the steps. Every external message, with {{APPROVER}}'s OK.

| ID | Request / work item | Channel | Owner | State | Evidence / next action |
|---|---|---|---|---|---|

### Change queue
Every change after the Design gate (rule M-09, `sdd-method` skill). Level: 0 bug · 1 tweak · 2 feature · 3 contract
or risk. If it touches the spec, its row goes in the spec's "Change log".

| ID | Origin | What changes | Level | Escalated | Session and branch | State |
|---|---|---|---|---|---|---|

## Linked sessions

| Session | Outcome | State | Proposal |
|---|---|---|---|

## Steps
Filled in when the Design gate is approved, one step per row. State: pending, active, ready to integrate, integrated
or accepted. `check-traceability.py` reads the "State" column.

| Step | Scope and session | Branch and commit | State | Step report | Review | Evidence in the org |
|---|---|---|---|---|---|---|

## File reservations
None.

<!-- if profile=light -->
## Org versions
Light profile: deploy, publish and activate need no OK. Each activated version and the previous one, to roll back.

| Date | Step | What was deployed or activated (agent and version) | Previous version | Verification |
|---|---|---|---|---|

<!-- end if -->
## Changes in the org outside the code

| Date | Change | Who / how | Verification |
|---|---|---|---|

## Blockers
None.

## Latest evidence
- `sdd-salesforce` method bootstrapped on {{DATE}}; no baseline yet (tagged when the Plan gate is approved).
