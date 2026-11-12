---
title: "Integration of the work in {{PROJECT}}"
description: "Scopes and own files, contracts and what is specific to the project in incorporation; the procedure is in implementation-integration-plan"
updated_at: {{DATE}}
tags: [integration, orchestration]
---

# Integration of the work

> Written in Design with `implementation-integration-plan`, together with the delivery plan. The procedure (roles,
> readiness report, gate and incorporation sequence, failures) is in that skill, reference `integration.md`; only
> what is specific to the project goes here.

- **Mode:** local git with no remote. **Base:** the commit tagged `design-approved`. **Org:** {{ORG}}, always with
  `--target-org {{ORG}}`.
- **Unit of work:** one step = one branch `w<wave>/<step>-<slug>`; with several author sessions, each in its own
  worktree.

## Scopes and files
The traceability check (`--graph`) reads this table: column 1 is the scope, column 2 its steps.

| Scope | Steps | Own folders and prefixes | Consumes | Exposes |
|---|---|---|---|---|

**Shared files** (only the integrator changes them, with the patches from the step reports): <permission sets,
profiles, dispatchers, CMDT, FlexiPages… of this project>.

## Contracts

| Contract | Producer | Consumers | Canonical source | Frozen at | Contract test |
|---|---|---|---|---|---|

## Platform-specific steps in this project
<OmniStudio (activation order), LWR site (republish), agent (publish and activate only at release; with the light profile, when the step is
integrated)… whatever
applies.>

## Verified with
<Skills and documentation against which the deployment sequence and the platform-specific steps were checked.>
