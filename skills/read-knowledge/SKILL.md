---
name: read-knowledge
description: Reads the why of the current project before planning or building. Reviews the Active decisions, the gotchas, the specs, the discovery and the operational status in THIS project's knowledge/ and docs/delivery-plan/, never those of sibling folders. Use it when starting any non-trivial task, before writing code or a plan.
---

# read-knowledge

The project's `CLAUDE.md` asks you to read `knowledge/` before anything else. This skill says **how** to do it
without loading whole documents and **how far** the reading goes.

## Scope: this project only
- Read the `knowledge/` and the `docs/delivery-plan/` of the project you are working in: the folder with its
  `CLAUDE.md`, which is usually the root of its git repository (`git rev-parse --show-toplevel`).
- **Do not read sibling folders**, even if they have their own `knowledge/`. In a workspace with one folder per
  customer (`clients/<customer>/`), each belongs to a different customer: reading them mixes confidential information
  and orgs that are not yours.
- Only if the project's `CLAUDE.md` declares **related bases** (for example, a team's common knowledge with no
  customer data), read them too, and only those.

## Reading rules
- **Triage by headers.** Start with `ls` and the frontmatter (`title`, `description`, `status`, `tags`, `evidence`);
  open in full only the files relevant to the task.
  ```bash
  ls knowledge/discovery knowledge/specs knowledge/decisions knowledge/gotchas 2>/dev/null
  head -12 knowledge/decisions/*.md
  ```
- **Decisions:** only `status: Active` ones bind. `Superseded` ones say what used to be true; `Proposed` ones await
  the approver's OK and are not applied. Do not undo an `Active` decision without superseding it with another.
- **Gotchas:** read them before touching the pieces they name.
- **Specs:** the agreed requirements with their AC and the design. If you are going to build something non-trivial
  that is not in a spec, stop and write it with the approver (`create-spec`).
- **Discovery:** the evidence of the AS-IS and which sources each item came from.
- **Status and open items:** `docs/delivery-plan/status.md` is the single source of truth for the status;
  `questions.md`, what is still to be decided or validated; `handover.md`, the latest dated handover. If they
  contradict reality (git, the org), reality wins and the orchestrator is told.
- **Precedence:** the approver's current instructions → `Active` decisions → spec → delivery plan. The code says what
  exists; if it does not match the design, that is work to do or an explicit question.

## Before building
Sum up in a few lines the `Active` decisions, gotchas and requirements that constrain the task, with their links, and
the open items that block it. Then plan or build against them.

## Relationship with the other skills
- What your work **produces** is recorded in this same project: `create-decision`, `create-gotcha`, `create-spec`.
- To set up the system in a project that does not have it, `sdd-bootstrap`.
