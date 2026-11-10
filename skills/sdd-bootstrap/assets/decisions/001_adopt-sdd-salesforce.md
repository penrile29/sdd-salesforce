---
title: "We adopt sdd-salesforce {{VERSION}}"
description: "The project works with the rules of the sdd-salesforce {{VERSION}} method (M-01 to M-10, in the sdd-method skill), with {{APPROVER}} as approver, {{AUTONOMY}} autonomy and the channels and areas set at bootstrap"
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
  change requests (M-09) and language (M-10). They are not copied here. If a new version of the plugin changes
  something that affects the project, it is recorded with a new decision.
- **Approver:** {{APPROVER}}. Approves the gates and the release, decides what is escalated to them and authorizes
  every external message.
- **Org:** {{ORG}}, the only one for the project. Local git with no remote.
<!-- if autonomy=strict -->
- **Strict autonomy:** every gate waits for {{APPROVER}}'s OK, including the one for each Execution step.
<!-- end if -->
<!-- if autonomy=critical -->
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

## Alternatives considered
- **Copying the method's rules into the project** — each project would be left with its own version and the copies
  would end up contradicting each other.
<!-- if autonomy=strict -->
- **Critical-only autonomy** — faster, but {{APPROVER}} prefers to review every diff before deploying.
<!-- end if -->
<!-- if autonomy=critical -->
- **Strict autonomy** — more control, but it slows down work on steps without risk.
<!-- end if -->

## Consequences
The project keeps only what is its own. Departing from a method rule, or changing the autonomy, requires a new
decision that supersedes or completes this one.

## Verified with
Not applicable: method decision.
