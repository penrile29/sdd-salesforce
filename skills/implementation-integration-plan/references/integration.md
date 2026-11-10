# Integration plan for the agents' work

This document explains how to produce the coordination plan. It does not start an orchestration. The later execution requires the scope and authorizations of that session.

## 0. Choose the mode according to the environment

| Mode | Unit of work | Review and validation | Incorporation evidence |
|---|---|---|---|
| Local without Git | An identified change, a patch or an isolated copy of the files in scope | Diff against a snapshot, local review and the commands run | Before/after snapshot/manifest, hashes, changes applied and tests |
| Local Git, without a remote | Branch/worktree and local commits; or a working diff if that is how the project operates | Local diff, recorded review and local commands | Resulting commit/baseline and state of the tree; no PR or push |
| Repository with remote review | Branch and PR or equivalent | Review and available CI checks, plus the required local validation | Remote change incorporated and integrated baseline verified |

Select the mode from the user's preference and what is available. Do not create Git, a remote, issues, PRs, workflows or accounts just to apply the method. If local work is requested, do not publish or sync externally by default. If the project requires a remote check, do not declare it passed by silently replacing it: record that limitation and the pending policy change.

Without Git, define evidence kept outside the scope of the snapshot: a manifest of relative paths and before/after hashes, files added/removed and a recoverable copy of the files that will be modified. Include the relevant files; exclude secrets and data unrelated to the work. Hashes identify content but do not restore it: keep the copies you need. Reuse equivalent existing mechanisms. For a small change by a single agent, a comparison and a backup proportionate to the scope are enough.

Before applying a patch or copying a file, check that the baseline matches the manifest. If it has changed, compare and resolve the conflict; never blindly overwrite someone else's changes. Verify additions, deletions and unexpected changes, and validate the combined result. Avoid two agents editing a shared file at the same time: use isolated copies or turns and an integrator.

With Git, a SHA does not identify uncommitted changes: also record the diff and the relevant new files, or use a work-in-progress commit when appropriate. Do not demand a clean tree by discarding the user's work. Without a remote there is no fetch, PR status or remote CI to check: the source of truth is the local repository and the saved evidence.

## 1. Define responsibilities and scopes

Establish who assigns work, who reviews and who integrates. They are roles, not fixed people or models. An integration owner maintains the graph, the file reservations, the change queue and the shared state.

The scopes table contains step, owner, folder/repo, files it may edit, contracts it consumes/exposes and exclusions. Look especially for migrations, lockfiles, registries, schemas, configuration, exports and knowledge indexes. A different folder does not guarantee independence.

Assign shared files to an owner or serialize their changes. Agents can propose corrections outside their scope; the plan explains how to reassign them without two agents applying them at the same time. Reserve migration/decision IDs or use unique identifiers to avoid collisions.

## 2. Plan waves from the graph

A step can be assigned when its dependencies meet the declared condition and its scope is free. Consumers can move ahead against a published contract if the step allows it; their final integration still needs composition tests.

State the baseline and starting revision for each assignment: commit/diff or snapshot, depending on the mode. With Git, use the existing development branch; propose a dedicated integration branch only if the project needs to accumulate changes before a joint delivery.

With Git, use isolated worktrees/checkouts when there are concurrent agents; without Git, bounded copies or exclusive scopes with turns for common files. Isolation does not remove semantic conflicts or automatically incorporate other people's work. Document how the baseline is updated and when that invalidates an earlier result.

The parallelism limit depends on memory, disk, runners, quota and shared files. If heavy tests compete for resources, plan an exclusive resource or a queue. A gate blocker must not prevent saving progress and resuming.

## 3. Prepare executable briefs

Use the assignment template in `templates.md`. Each brief includes specific readings of the spec, active decisions and gotchas, the step, artefacts, tests, mode, baseline, dependencies, its own and others' files, frozen contracts, the AC the step must satisfy and the tests it must write first, and the result it must return. Include the obligation to return knowledge updates when there is new learning.

Keep common rules in a shared brief; the individual assignment adds the scope and what is new. Avoid duplicating the whole specification. The agent needs the sections that define its work, and enough context not to break contracts.

Do not fix a model/provider unless the user prefers one or there is a real constraint. Do not invent attribution of authors or sessions. Do not assign incompatible work to agents that are already active without an explicit handover.

## 4. Design the incorporation gate

Name the verifications the project requires and where that list comes from. Record local commands, working directory, scope, environment, skip policy, output/result and remote evidence only if it exists. Adapt the tests to the change and to the project's rules. Without CI, the gate is an explicit set of local verifications, not the absence of validation.

Define the review criterion: the tool/person available, open findings, how false positives are handled with evidence and which changes require a new review. The review can be saved in a local file. A self-review must be identified as such; do not present it as independent. A provider or a score is mandatory only if the project requires it. A reviewer failure is not an approval; leave the change pending, allow independent work and use a substitute only if it is authorized.

### Review capability of the agents

When it is available, apply `$independent-code-review`. The plan must specify this minimum contract even if the skill is not installed:

- **Inputs:** identified baseline/candidate, scope and acceptance, spec, active decisions and gotchas, access to the code and the required verifications. The reviewer's first analysis starts from those artefacts, without inheriting the author's diagnosis.
- **Investigation:** fidelity to contracts, consequences for producers/consumers outside the diff and quality of tests/oracles. A graph must correspond to the sources reviewed. Findings require a scenario, impact and static evidence or a reproduction; distinguish tests that were read from tests that were run.
- **Separation:** the author fixes; the reviewer investigates and verifies closures; the integrator checks content and composition. The reviewer does not edit the candidate. Without a separate context, record a self-review and do not satisfy an independence gate.
- **Persistence:** stable IDs, severity, content/location, expected/observed, evidence and state. Keep rounds and responses; a proposed fix does not close the finding. Verified rebuttals are recorded too.
- **Output:** `changes_required` if there are confirmed blocking defects; `incomplete` if material evidence is missing with no other conclusive blocker; `no_blocking_findings` when the review is complete with no blockers. None of them, on its own, means checks passed or work integrated.
- **Closing:** revalidate fixes and regressions on the final content; verify that oracles, skips or expectations were not weakened to hide errors. A new baseline requires reviewing composition effects. Preserve knowledge when there is verified learning.

Fit the depth to the risk; do not require several reviewers as a matter of routine. If the infrastructure prevents verification, or a disagreement repeats with no new evidence, keep the results and mark what is pending. A round limit does not turn the result into an approval. To replace a mandatory reviewer, first evaluate the method and change the policy with the corresponding authority.

### Readiness record

The record of readiness to integrate includes:

- Folder/repo, change ID, target and origin/baseline content: SHA plus diff, or snapshot manifest; PR only if one exists.
- Scope of the step, AC covered with their verification and result, and the output of the traceability check.
- Verifications expected and performed, results and paths/links; a required one that is missing is not passed. The absence of CI is not a failure when the defined gate is local.
- A review that corresponds to the final content, including findings outside the diff handled according to the project's policy.
- Assumptions, pending decisions and contract changes that affect consumers.
- A composition test against the current baseline when there are relevant concurrent changes; review of the affected specs, decisions and gotchas.

Separate **ready to integrate** from **integrated**. An author can propose the state in their delivery, but the shared state only records integration when the result is verified.

## 5. Sequence and verify the incorporation

The plan describes this procedure for whoever is authorized to integrate:

1. Verify the current baseline and check that the dependencies exist in it. Query the remote only in the authorized remote mode.
2. Revalidate scope, final content, review and expected verifications. Reject evidence for other content.
3. Compose against the current baseline: a merge queue if there is one, integration of a local branch, or a patch/copy validated against the snapshot. If the combined behaviour changed, the earlier evidence is not enough.
4. Incorporate in dependency order; serialize changes that share files or contracts. A single integrator updates each shared baseline at a time.
5. With Git, check the resulting commit and the working changes: for a merge commit, ancestry; for squash/rebase, the expected diff/content, without requiring the original SHA's ancestry. Without Git, compare manifests and files with the reviewed change. Query remote state only when it exists.
6. If an incorporation is interrupted or its response is ambiguous, inspect the state before repeating; avoid double application or loss of files.
7. Check the defined local/remote gates on the integrated baseline and the affected flow. Update knowledge, state and evidence; then unblock dependents.

If composition fails, keep the evidence, mark the affected scope, stop its dependents and prepare the repair. Going back to a snapshot or reverting follows the project's rules, preserving other people's later work. Do not assume that restoring code restores data or reverts a migration.

"Changes validated individually" and "system accepted" are different milestones. Include a closing that exercises the real path, with components connected and correct startup/configuration when they are in scope.

## 6. Handle questions and changes

Classify a doubt by impact: a reversible detail within the design, a contract change, a new business rule, permissions or an irreversible risk. A doubt does not become an authorization because a decision has been written.

A conservative, reversible interpretation can be recorded as an assumption within the assignment. Significant decisions stay proposed/pending unless that authority has been expressly delegated. Explain which steps they block; continue with independent work.

When a contract changes, list the producers, consumers, active changes, fixtures, specs and tests that must be updated. An extension of a finished step is a follow-up: its historical state does not prove that the new scope is delivered. Apply the decision and gotcha cycle in `discovery-knowledge.md`.

### Changes after the Design gate (change requests)

The approved spec is the contract and must keep describing the system. In an sdd-salesforce project, every later
change follows the change-request path of the `sdd-method` skill: the change queue in `status.md`, triage by levels
0-3, one change per session, the delta and its row in the "Change log" before the code, gates according to the level,
closing and rotation of the orchestrator. When integrating a change, the integrator also checks that the traceability
check reports no change-log errors.

## 7. Design communication and resumption

Follow `orchestration-communication.md` for the document map, the channel protocol and the orchestrator template. Choose one main source of persistent state: a local document or an existing authorized channel. Preparing a plan does not authorize posting to issues, Slack or other people's chats. Inherit current cadences or propose the missing ones; distinguish the documented policy from a configured or active monitor. Do not inherit automations from another project.

Each useful update identifies the agent/scope, the baseline/delivery content, the work finished, the next action, the evidence and the blocker. Use branches/SHAs/PRs only where they exist. A local state file and change records are enough without external services. Save events after significant changes.

The handover distinguishes a dated snapshot from the current verifiable state. It includes mode, baseline, queue, reservations, contracts, decisions/gotchas, pending verifications and next action. When resuming, compare it against files/manifests, or local or remote Git depending on the mode; do not restart from an old counter or duplicate another agent's work.

As the operational entry point, the handover also links the current rules, the communication protocol, the orchestrator template and the main state. Record the requests awaiting an answer, the last message handled per channel and the real state of monitoring, so that the handover does not lose communication obligations.
