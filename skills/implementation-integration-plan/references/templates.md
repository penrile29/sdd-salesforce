# Adaptable templates

Replace the bracketed fields with evidence, or mark explicitly what is unknown. Remove fields that do not apply; never
deliver an empty template as a plan.

## Plan context

```markdown
# [Project] — delivery plan
Date and revision: [date, folders/repos and commit+diff or snapshot consulted]
Mode: [local without Git / local Git / remote review]
Observable goal: [behaviour, recipient and environment]
Scope / exclusions: [...]
Sources and precedence: [discovery, specification, active decisions, gotchas, current rules]
Observed state: [existing and verified / unverified / to be built]
Ready to start: [steps and the conditions they meet]
Open items: [question → affected steps]

| Phase | Outcome | Dependencies | Exit evidence |
|---|---|---|---|
| [phase] | [...] | [...] | [...] |
```

## Requirement and acceptance criteria

```markdown
### R-<AREA>-01 — [behaviour, in one sentence]
- Source: [customer document and page, decision]
- Priority: [P0/P1] · Status: [Draft/Ready/Implemented/Accepted]
- AC-<AREA>-01.1 — Given [context], when [stimulus], then [observable result] ([where it is checked]).
- AC-<AREA>-01.2 — Given [context], when [error or rejection], then [observable result] ([where]).
- Open items: [PENDING: Q-NN] or "none".
```

## Implementation step

The ID, the title and the bold fields are what `check-traceability.py` reads: write them exactly as shown, with
`- **Field:**` at the start of the line and continuation lines indented by two spaces.

```markdown
### W<n>.<m> — [concrete outcome]
- **Scope:** [scope in integration.md] · [its own folders and prefixes, role]
- **Touches:** [folders and metadata it changes; the orchestrator reserves them and does not launch two steps that touch the same thing]
- **Builds:** [artefacts and observable behaviour]
- **Satisfies:** [R-<AREA>-NN (AC-…), individual AC or R-<AREA>-NN (except AC-…)]. **Source:** [spec, decision and section]
- **Knowledge:** [spec, active decisions and gotchas to read]
- **Contracts:** [IDs, version, producer/consumer]
- **Depends on:** [integrated steps]; to close: [steps]; [P-NN if there is an external dependency]
- **Parallel with:** [steps, and under what conditions]
- **Test first:** [yes/no] — `[TestClass]`, `[sf agent test case]`, with the AC ID that each one covers
- **Done when:**
  - [AC-ID] [test or check]: given [input], [observable result] happens.
  - [composition or deployment check, if it applies].
- **Out of scope:** [...]
- **Observability / known risks:** [signal and relevant evidence]
- **Skill:** `[execution skill]` (it must be in the environment inventory)
- **Level:** [0/1/2/3]
- **Size:** [S/M/L]
- **Back to knowledge:** [affected specs/decisions/gotchas, or no new learning]
```

The state of each step and its evidence do not go in the step: they go in `status.md`, the single source of truth.

**Flat step (sdd-salesforce light profile).** One wave (`W1.n`), no sizes or critical path; the same field names, so
the traceability check reads it as it is:

```markdown
### W1.<m> — [concrete outcome]
- **Satisfies:** [AC or R-<AREA>-NN]. **Source:** [spec and section]
- **Touches:** [folders and metadata]
- **Depends on:** [steps, only if there is a dependency]
- **Skill:** `[execution skill]`
- **Done when:** [AC-ID] [verification]: given [input], [observable result].
```

## Traceability

One row per AC, with the IDs exactly as they are in the spec and the step exactly as it is in the plan. The
verification uses only the labels of the vocabulary in `sdd.config.json` (the template
`docs/delivery-plan/traceability.md` lists them), and the evidence state starts at `planned`, moves to `exists` and
ends at `passes (<commit>)`.

```markdown
| Requirement | AC | Source and status | Step | Verification | Evidence state |
|---|---|---|---|---|---|
| R-<AREA>-NN | AC-<AREA>-NN.M | [spec, status of the requirement] | W<n>.<m> | [labels from the closed vocabulary, separated by `;`: e.g. `Apex test; code review`] | planned |

| Exclusion | Reason | Who/when agreed it, or proposed status | Future review |
|---|---|---|---|
| [ID] | [deferred/superseded/no code needed] | [...] | [...] |
```

## Integration plan

```markdown
# Integration of the agents' work
Mode: [local without Git / local Git / remote review]
Baseline per folder/repository: [snapshot/manifest or branch and commit+diff]
Responsible for assignment / review / incorporation: [roles]
Shared contracts and change procedure: [...]
Reserved scopes and common files: [...]
Concurrency limit and test resources: [figure or explicit assumption]

| Wave | Step | Scope/owner | Unblocked by | Target of the change | Possible conflicts |
|---|---|---|---|---|---|
| [...] | [...] | [...] | [...] | [...] | [...] |

Gates: [applicable local commands/remote checks, review, validated content and composition]
Incorporation order: [dependencies and serialization]
Post-incorporation verification: [manifest/diff, local or remote Git and integrated tests]
Failure handling: [affected dependents, repair and owner]
Persistent state and handover: [authorized location/channel]
Closing: [functional demonstration and who accepts it]
```

## Individual brief for an agent

```text
Implement [ID and outcome] in [folder/worktree], from [verifiable baseline].
Mode: [local without Git / local Git / remote review].
Read [common rules], [step/phase], [spec sections],
[contracts/active decisions], [relevant gotchas].
Your scope: [files and artefacts]. Do not edit [reserved scopes].
Dependencies available: [IDs, versions, evidence].
Deliverables and acceptance: [AC IDs and their verification; tests you write first]; out of scope: [...].
Shared contracts: [versions and procedure for proposing changes].
Validation: [real commands/gates]; review: [project policy].
Target and delivery: [local change with diff/snapshot, local commits or authorized PR].
Allowed assumptions and decisions you must escalate: [...].
Update [authorized persistent state] with the scope and revision of the content,
what is done, what is pending, evidence and blockers after significant changes.
Return the changes, identifiable final content, tests/results and open items.
Update knowledge with decisions, gotchas and spec changes when relevant;
link the evidence or state that there was no new learning.
Incorporation is done by [role], according to [integration plan].
```

## Change record and handover

```markdown
### [Step/change; PR if there is one] — [state]
- Level: [0/1/2/3] · Escalated: [yes/no]
- Delta: [row in the spec's Change log, or "does not touch the spec"]
- Mode: [local without Git / local Git / remote review]
- Origin: [folder/repo, snapshot/manifest or branch and commit+diff]
- Target/validation baseline: [...]
- Review: [file/link, content reviewed, author/type of review and findings]
- Verification: [local commands/remote checks, expected/performed, environment and results]
- AC covered: [IDs, verification and result]
- Composition: [baseline, result and evidence]
- Incorporation: [pending, or the resulting commit/manifest, verified]
- Decisions/assumptions and affected consumers: [...]
- Knowledge updated: [specs, decisions, gotchas, evidence; or nothing new]
- Next action and owner: [...]

### Handover — [date and time zone]
- Operational entry point: [current rules, communication protocol, orchestrator template]
- Main source of state and last reconciliation: [location, date and evidence]
- Observed baseline: [...]
- Active scopes and reservations: [...]
- Change queue / blockers: [...]
- Last valid evidence per scope: [...]
- Contracts, pending decisions and new gotchas: [...]
- Scope changes not yet delivered: [...]
- Channels: [last message handled, requests awaiting an answer and deliveries to verify]
- Monitoring: [proposed/configured/active and verified, owner, cadence, last cycle and stop]
- Next executable step and condition: [...]
```

For the protocol of acknowledgement, response and publication verification, and for the orchestrator's startup
template, use [orchestration-communication.md](orchestration-communication.md). Adapt the record to local or remote
mode; do not create channels or automations without authorization.

## Change queue and Change log

Queue row, in `status.md` (every change after the Design gate):

```markdown
| ID | Origin | What changes | Level | Escalated | Session and branch | State |
|---|---|---|---|---|---|---|
| CH-001 | [approver / F-… / V-… / build / customer] | [one sentence] | [0-3] | [yes/no] | [session, branch] | [pending / active / ready to integrate / integrated] |
```

Change log row, at the end of the spec (only changes to requirements and AC, in the same commit as the change):

```markdown
## Change log

| Date | Type | IDs | Before → after | Changes behaviour? | Origin | Approval | Commit |
|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | ADDED / MODIFIED / REMOVED | `R-…`, `AC-…` | [one sentence] | [yes/no] | `CH-NNN`, decision, `F-…` or `V-…` | [who, or "pending"] | `abc1234` |
```

## Plan review log

```markdown
| Pass | Sources/sections reviewed | Finding | Correction | Open item |
|---|---|---|---|---|
| [discovery/spec/coverage/composition/acceptance/knowledge] | [...] | [...] | [...] | [...] |
```
