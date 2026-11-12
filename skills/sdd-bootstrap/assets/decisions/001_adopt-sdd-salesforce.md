---
title: "We adopt sdd-salesforce {{VERSION}}"
description: "The project works with the rules of the sdd-salesforce {{VERSION}} method (M-01 to M-12, in the sdd-method skill), with {{APPROVER}} as approver, the {{PROFILE}} profile, {{AUTONOMY}} autonomy and the channels and areas set at bootstrap"
updated_at: {{DATE}}
status: Active
author: "{{APPROVER}} + sdd-salesforce"
tags: [method]
---

# We adopt sdd-salesforce {{VERSION}}

**Decided by:** {{APPROVER}}, when bootstrapping the project
**Date:** {{DATE}}

## Context
The project needs what is agreed to be verifiable, the status not to depend on any conversation and the reviewer not
to be the author. The sdd-salesforce method solves this; its rules live in the plugin so that every project uses the
same ones and they improve together.

## Decision
- **The method's rules are those of the plugin's `sdd-method` skill**, version {{VERSION}}: cycle and gates (M-01),
  local git with tags (M-02), document structure (M-03), orchestration and communication (M-04), "Verified with"
  (M-05), requirements and AC first with levels 0-3 (M-06), escalation (M-07), verifying the environment (M-08),
  change requests (M-09), language (M-10), profiles (M-11) and the browser (M-12). They are not copied here. If a new version of the plugin changes
  something that affects the project, it is recorded with a new decision.
- **Approver:** {{APPROVER}}. Approves the gates and the release, decides what is escalated to them and authorizes
  every external message.
- **Org:** {{ORG}}, the only one for the project. Local git with no remote.
<!-- if mode=light -->
- **Light profile:** the same gates (Plan, Design and release) and the spec with requirements and AC, with less
  ceremony around them: a flat delivery plan, parallel subagents with one reviewer per step, no test-first, and
  deploying, publishing and activating in {{ORG}} without an OK. The release gate is "demo accepted". Every external
  message and every irreversible org setting still needs {{APPROVER}}'s OK. The autonomy is critical.
<!-- end if -->
<!-- if mode=strict -->
- **Strict autonomy:** every gate waits for {{APPROVER}}'s OK, including the one for each Execution step.
<!-- end if -->
<!-- if mode=critical -->
- **Critical-only autonomy:** escalate to {{APPROVER}}, and wait for the answer, only for a substantial change to the
  user experience, a departure from the approved requirements or AC, a change of stack, product or licence or an
  irreversible org setting, or a blocker that cannot be resolved. Everything else is decided and recorded.
<!-- end if -->
<!-- if language -->
- **Document language:** `{{LANGUAGE}}` (`method.language`). The project's documents are written in it; the
  headings, fields, IDs, git tags and file names of the templates stay exactly as they are (M-10).
<!-- end if -->
- **Allowed channels:** {{CHANNELS}}.
- **Planned areas:** {{AREAS}}.

<!-- if browser -->
- **Browser:** UI tests with the project's Playwright MCP (`.mcp.json`) and Playwright's own Chromium, only against
  {{ORG}} (M-12).
<!-- end if -->

## Alternatives considered
- **Copying the method's rules into the project** — each project would be left with its own version and the copies
  would end up contradicting each other.
<!-- if mode=strict -->
- **Critical-only autonomy** — faster, but {{APPROVER}} prefers to review every diff before deploying.
<!-- end if -->
<!-- if mode=light -->
- **Full profile** — the whole ceremony (waves, test-first, review of the spec and the plan, OK to publish and
  activate); more control, but slower to build a demo.
<!-- end if -->
<!-- if mode=critical -->
- **Strict autonomy** — more control, but it slows down work on steps without risk.
<!-- end if -->

## Consequences
The project keeps only what is its own. Departing from a method rule, or changing the profile or the autonomy, requires a new
decision that supersedes or completes this one.

## Verified with
Not applicable: method decision.
