---
name: implementation-integration-plan
description: Structures discovery, technical specifications, decisions and gotchas in knowledge, and derives implementation and integration plans for the agents' work. Use it to prepare or review a project's development method, locally with or without Git, or with remote PRs and CI.
---

# Implementation and integration plan for agents

Apply the cycle **discovery → technical specification → decisions → planning → implementation and integration → knowledge update**. Enter at whichever stage the project needs: reuse what is current and fill its gaps without restarting work that is already settled.

Turn the project's requirements, design and evidence into two related deliverables:

- **Implementation:** what to build, where, in what order and what evidence shows that it works.
- **Integration:** who works in each scope, what can be done in parallel, how local changes or PRs are incorporated and how another session continues.

Produce both when the full method is requested; if the user asks for a single stage, produce that one and reference its dependencies. Adapt phases and detail to the project. Asking for a plan authorizes the documents it needs, not starting agents, posting comments, modifying product code, merging or deploying. If the implementation is already authorized, apply the knowledge lookup and update cycle during that work without asking for another approval as a matter of routine.

## 1. Establish the working baseline

Read the project's instructions and examine its knowledge index before planning or building. Select documents by title, description, status and tags; then read the relevant ones in full, including the gotchas for the affected components and tools. Follow [references/discovery-knowledge.md](references/discovery-knowledge.md) for discovery, specifications and knowledge maintenance. Record:

1. Observable goal, scope and exclusions; the environment where it must be demonstrated.
2. Specification, requirements and current decisions, with link and revision or date. Distinguish approved, proposed, superseded and pending.
3. Observed state of the code and tests, and the actual folders, repositories and branches. Prefer graph tools if they exist; if they are not available, use normal search and reading. An old plan or PR does not prove the current state.
4. Shared contracts, owners, review/CI rules and execution limits that the project already has.
5. Questions that change the design, and exactly which steps they block.
6. Working mode: **local without Git**, **local Git without a remote**, or **repository with remote review**. Identify the available commands, isolation and how evidence is recorded. The absence of GitHub does not block the method, nor does it require creating a remote, using the network or publishing content.
7. Environment: the Salesforce skills and the tools the project requires. In an sdd-salesforce project, the environment verification of the `sdd-method` skill, at the start of Plan and before the discovery; its blockers go into `questions.md` as soon as they appear. Every step in the plan names its execution skill, and that skill must be in the inventory.
8. Level of the change. It sets the artefacts and the depth of review; the project's gates do not change. The first triage question: does the code break an AC that already exists, or does it change what the spec promises?
   - **Level 0 · bug:** the code does not satisfy a current AC. Regression test and fix; the spec does not change. If the bug reveals that an AC is missing, the change is level 1 or higher. Review of the diff.
   - **Level 1 · tweak:** it changes neither observable behaviour nor contracts (text, configuration within a current contract). No new spec: the step carries its AC. The change and a review of the diff; an independent review only if the gate requires it.
   - **Level 2 · feature:** new behaviour within current contracts. Requirements and AC in the spec for the scope; test first; one independent reviewer.
   - **Level 3 · contract or risk:** a new or changed contract, identity and permissions, irreversible data or settings, integrations. Full requirements, design and plan; an independent reviewer and a second perspective for permissions or security.

   When in doubt, the higher level. The level is recorded in the step. After the Design gate, changes follow the change-request path of the `sdd-method` skill (queue, triage, escalation separate from the level, delta before code).

If a specification is missing, draft it from the discovery as a draft traceable to evidence; do not invent requirements or approvals. With an incomplete design, create a useful partial plan and mark the pending decisions; do not declare ready the steps that depend on them. Clarify only what cannot be inferred and what lets the work move forward. Do not force existing authorizations to be approved again.

Set the precedence of documents according to the project. As a baseline: the user's current instructions, current approved decisions, the specification and the plan derived from it. The code describes what exists; differences from the design are explicit work or questions. If two current decisions contradict each other and no supersession has been shown, record the conflict.

## 2. Derive the implementation plan

Read [references/implementation.md](references/implementation.md).

The obligations are the spec's requirements and acceptance criteria, with their IDs. If a requirement has no AC, the step that implements it cannot be declared ready: send it back to the spec instead of inventing the acceptance in the plan. Relate each obligation to an identifiable decision or requirement and to its state in the code. First define the contracts that unblock independent work; then split into steps with verifiable deliverables.

Each step includes scope, artefacts, normative sources, contracts, dependencies, tests with their expected result, limits and state. Use the template in [references/templates.md](references/templates.md). The goal is that another session can implement it without redesigning interfaces or guessing the acceptance.

In an sdd-salesforce project with the light profile (`method.profile: light`), the plan is a flat list of steps in a single wave, with the flat step template: `Satisfies`, `Touches`, `Skill` and, only if there is one, `Depends on`. `Touches` is also used in the full profile: it is what lets the orchestrator launch authors in parallel without collisions.

Build a dependency graph without cycles. Distinguish functional dependency, contract dependency and file collision. Define what can start against a stub and what requires an integrated implementation. Do not copy the number of phases or the architecture of the project the method came from.

## 3. Derive the integration plan

Read [references/integration.md](references/integration.md).

To coordinate agents or prepare handovers, also follow [references/orchestration-communication.md](references/orchestration-communication.md): document map, orchestrator entry point, acknowledgement/response/verification protocol, operational state and local or remote monitoring.

From the steps and the graph, define owners, exclusive scopes, shared files, baseline/target, waves and the incorporation procedure for the chosen mode. Plan with the real capabilities and limits of the environment, without fixing a review provider, model or number of agents out of habit.

Define review as a capability of the method: an author who fixes, a reviewer with a separate context who investigates and verifies, and an integrator who checks the gate. If it is available, use `$independent-code-review` for the review protocol, findings and closing. If it is not, apply the minimum contract in `references/integration.md`; its absence does not require installing services. Planning these roles does not start agents or replace reviewers the project requires.

Review and test evidence belongs to specific content: a commit plus local changes, or a snapshot/manifest if there is no Git. If the content to be integrated changes, determine which evidence must be renewed. A missing required check, an old review or an open PR is not integrated work. Without CI, record local commands, results and limitations. The plan describes how to verify the incorporation and replan dependents when something fails.

## 4. Audit both plans

Make passes with different purposes and record findings/corrections:

- **Coverage:** section by section and decision by decision; every active requirement has a step and a verification, or a justified exclusion.
- **Executability:** no step needs to invent a contract, a dependency, an owner or a business rule.
- **Composition:** parallel work can coexist; contract changes reach all their consumers; the tests check the combined result.
- **Acceptance:** the tests have an oracle and exercise the real path; the phase and product criteria include wiring and operation, where relevant. Every AC in scope has a named verification (automated test or justified manual step), and the traceability check reports no gaps.
- **Resumption:** another session can identify mode, baseline, active work, pending changes, decisions and next action without relying on private memory.
- **Knowledge:** discovery findings have sources; the spec cites the relevant decisions and gotchas; new learning goes back to knowledge and reaches the affected steps.

Correct and review the affected parts again. Finish when no critical gaps remain hidden; if information is missing, deliver the explicit gaps and the executable scope. Do not set an arbitrary number of rounds or claim independent reviews if a single session did them.

## 5. Deliver and maintain

Respect the existing document structure. If there is none, keep discovery, specs, decisions and gotchas in `knowledge/` as the reference describes. For plans use `docs/delivery-plan/`:

- `README.md`: goal, sources, scope, phase map, dependencies and what is ready.
- `implementation/`: phases and steps; for a small project one file is enough.
- `integration.md`: local/remote mode, division of work, waves, contracts, gates and incorporation sequence.
- `traceability.md`: requirement/decision → step → test or verification, with justified exclusions.
- `questions.md`: pending decisions and affected steps; omit it if there are none.
- `handover.md`: operational entry point and handover; current rules by reference, coordination, gates, configured monitoring and a dated snapshot linking to the main state. Do not fill it with fictitious progress.
- Main source of operational state: an explicit location, local such as `status.md` or remote if authorized; it holds work items, reservations, blockers and progress with evidence.
- In an sdd-salesforce project, the communication protocol, the orchestrator template and the common brief for authors are in the `sdd-method` skill (`references/`): they are not copied into the project. Outside an sdd project, create them only if there is coordination between agents.

Use [references/templates.md](references/templates.md) as a base, removing fields that do not apply. Do not create a catalogue of empty documents. Except for a tweak that changes neither observable behaviour nor contracts, propose or implement, if it is in scope, a local traceability check (see `implementation.md`) that detects AC without verification, verifications with unknown IDs and duplicates. Do not say that CI verifies it if you have only written Markdown.

A requirement change updates the spec, decisions, steps, dependencies, contracts, tests and traceability. A finished step keeps its historical scope: extensions are new steps or follow-ups, with their own state. When closing authorized work, record new decisions, reproduced gotchas, evidence and affected documents; if there was no new learning, say so without fabricating entries.

When delivering, link the artefacts and state what can start, what is pending and which verifications you performed. Do not confuse **plan ready**, **implemented**, **integrated**, **deployed** and **accepted**.
