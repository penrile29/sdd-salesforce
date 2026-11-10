---
title: "Handover of {{PROJECT}}"
description: "Operational entry point and the last dated handover; the live status is in status.md"
updated_at: {{DATE}}
tags: [handover, orchestration]
---

# Handover — {{DATE}}

> Dated snapshot. The live status is in [status.md](status.md); check it against reality (git, the org) before
> acting. At each handover, the main session rewrites this whole file with the new date.

- **Operational entry point:** [../../CLAUDE.md](../../CLAUDE.md) and the `sdd-method` skill (rules, orchestrator
  template and communication protocol).
- **Mode:** local git in this folder. Baseline: the bootstrap commit (no baseline tag yet). Org: **{{ORG}}**, which
  expires on **{{EXPIRY}}**.
- **Stage:** **Plan.** First step: the environment verification (`sdd-method` skill); then, the discovery.
- **Observed baseline:** project just bootstrapped with `sdd-salesforce` {{VERSION}}; `knowledge/` with adoption
  decision 001 and no discovery, specs or gotchas.
- **Active scopes and reservations:** none.
- **Change queue** (in `status.md`, with the level of each change) **and blockers:** none.
- **External messages:** none pending. Every message sent needs {{APPROVER}}'s OK.
- **Next executable step:** the full environment verification (`sdd-method` skill), with the blockers recorded in
  `questions.md`; then, the discovery of the sources in `docs/client/` and the org snapshot in `docs/baseline/`.
