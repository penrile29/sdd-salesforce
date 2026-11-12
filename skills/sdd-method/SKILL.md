---
name: sdd-method
description: "Rules of the sdd-salesforce method in a project with sdd.config.json: the Plan → Design → Execution → Review cycle with its gates, roles, Definition of Done, escalation, communication, language, guided conversation, environment verification, change requests (changes after the Design gate), the full and light profiles, parallel orchestration with subagents and the browser for tests. Use it when starting work in an sdd project, when moving to another stage, before a change after the Design gate and to run the environment and traceability checks; also when, in an sdd project, the user says “start”, “continue”, “where are we?”, “I approve”, “there is a bug in…”, “change this requirement or AC” or “record this”, even if they do not name the skill."
---

# sdd-method

The method's rules live here, once, and are updated with the plugin. The project keeps only what is its own: its
`CLAUDE.md` (customer, org, approver, confidentiality), `sdd.config.json` (org, areas, autonomy and adopted version)
and its knowledge. The plugin injects the core at the start of every session, when it is resumed and after it is
compacted, and in the first message of a session that does not have it yet (for example, the bootstrap session); the
rest is read here when moving to another stage.

**Project data:** the org is the `org_alias` in `sdd.config.json`; the approver, `method.approver`; the profile, `method.profile`
(`full` or `light`; without it, `full`); the autonomy, `method.autonomy` (`strict` or `critical`; `light` implies
`critical`); the document language, `method.language`. If the project's `CLAUDE.md`
says something different from a `CLAUDE.md` in a parent folder, the project's own wins within the project, and these
rules prevail over both in matters of method.

<!-- core -->
**sdd-salesforce method: what always applies in this project.**
- **Org:** only the `org_alias` in `sdd.config.json`. Every `sf` command that touches an org carries an explicit
  `--target-org <alias>` (the default org may belong to another project) and `--json`. Draft-first: `validate` and
  `preview` before `publish` and `activate`, which only happen at release (in a light project, when the step is
  integrated: light block). The plugin's guard denies Bash `sf` commands against another org or without
  `--target-org`, and its browser guard denies other orgs in the Playwright MCP; neither sees scripts that call `sf` or
  other MCP tools: with those, check the org yourself.
- **Cycle:** Plan → Design → Execution → Review, without skipping stages or merging gates. These always need the
  approver's OK: the Plan gate, the Design gate, the release, irreversible settings and every external message (Slack,
  email, Support, the customer). Everything else depends on `method.autonomy`.
- **Plan starts by verifying the environment** with the `sdd-method` skill (section "Verify the environment"); each
  gap goes into `docs/delivery-plan/questions.md` as soon as it appears, without asking for an OK. Plan only reads the
  code and the org, but it writes its own documents.
- **Status:** `docs/delivery-plan/status.md` is the single source of truth, and the orchestrator writes it. Nothing
  important lives only in a conversation: if it is needed to resume, it goes into a file.
- **Knowledge before building:** `Active` decisions, gotchas and the spec for the scope (`read-knowledge`). No
  non-trivial functionality without requirements and AC in the spec (`create-spec`).
- **After the Design gate, every change** enters the "Change queue" in `status.md` with its level: 0 bug, 1 tweak,
  2 feature, 3 contract or risk. If it touches the spec, the delta and its row in the "Change log" come before the
  code. One change, one session.
- **Independent review** with a separate context; a self-review counts for no gate.
- **You lead the conversation** (section "Guided conversation"). In the first message, orient the user from
  `status.md`: the stage, what is missing for the next gate and what they have to decide. You load the skills
  yourself: never ask the user to invoke one or give them a `/command` as a step. Every gate, and every escalation
  that `method.autonomy` calls for, ends with the next step in one sentence and **one** concrete question; with
  `critical`, between steps you report and carry on.
- **Language:** answer in the user's language. Write the project's documents in `method.language` of
  `sdd.config.json` (if it is not set, in the user's language) and state it in every subagent brief. Headings and
  fields the checks read, IDs, git tags and file names stay exactly as in the project's templates: translate the
  prose, never those tokens (rule M-10).
- **Profile:** `method.profile`. In a `light` project the plugin injects, after this core, the light block of this
  skill: it wins where it differs. Without the key, the project is `full`.
- **Browser:** to see the UI in tests, only the Playwright MCP of the project (`.mcp.json`, server `playwright`) with
  its own Chromium, and only against the project's org (section "Browser"). Never the managed Chrome, the Browser pane
  or Claude in Chrome. The user logs in by hand; you never type passwords.
- When you start a stage or a change, read the whole `sdd-method` skill.
<!-- /core -->

<!-- light -->
**Light profile (`method.profile: light`): what changes in this project.** It wins over the core and over the rest of
this skill where they differ; everything else applies as it is.
- **Gates:** Plan, Design and release keep the approver's OK and their tags. The gate of each Execution step is the
  reviewer's verdict (`no_blocking_findings`): you report and carry on. The autonomy is `critical`.
- **Org:** deploying, `sf agent publish` and `sf agent activate` against the project's org need no OK: do them when the
  step is integrated, and record in `status.md` each version activated and the previous one, to roll back. The release
  gate is "demo accepted": the approver validates the demo walkthrough, and the tag `release-N` is set. **Still with the
  approver's OK:** every external message and every irreversible org setting (closed list in `references/rules.md`,
  M-11). Any other org is still denied.
- **Plan:** the environment verification runs as in full, but its gaps are warnings that go into `questions.md` and the
  approver sees them at the Plan gate. Discovery: the customer's sources and a minimal snapshot of the org;
  documentation and Slack only when a question needs them.
- **Design:** requirements with IDs and AC in the spec (`create-spec`), as always; the design part, brief. Decisions
  only for a stack, product or licence choice, an irreversible setting or a departure from the method, with "Verified
  with" in one line. No independent review of the spec and the plan before the Design gate. The delivery plan is a
  **flat list** of steps `W1.n` (one wave), each with `Satisfies`, `Touches`, `Skill` and, if there is one,
  `Depends on`; no sizes or critical path (`--graph` is not used).
- **Execution:** parallel orchestration with subagents (section "Parallel orchestration"): authors in their own
  worktrees, one reviewer per step and serial integration. No test-first: the tests the deployment requires (Apex
  coverage) and the agent cases of the demo walkthrough. The step report only has `## Verification cases`, with the
  evidence.
- **Change requests:** levels 0 to 2 write the delta and the code in the same commit, without "Approval: pending";
  level 3 goes back to the approver.
- **Handover:** only when the conversation is compacted or at the end of the working day, not at each gate.
- **Definition of Done:** deployment without errors; preview with the traces of the demo script; `browser check` of the
  UI AC; (agents) the security review without BLOCK findings; the traceability check without errors; and the demo
  walkthrough run in Chromium.
<!-- /light -->

## Cycle and gates

1. **Plan** (role *Explorer*: reads the code and the org only; writes its documents, `docs/baseline/`,
   `knowledge/discovery/` and `questions.md`, without asking for an OK).
   - **First, the environment verification** (below).
   - Then the **discovery**: the customer's sources (`docs/client/`), a snapshot of the org (`docs/baseline/`),
     official documentation and internal Slack, read-only. It goes into `knowledge/discovery/`; open questions, into
     `questions.md`. If it reveals new areas, repeat the verification.
   - → **Plan gate:** the approver validates the discovery and the environment inventory (no gaps, or the gaps
     accepted as a decision). On approval, the tag `baseline-<date>` is set.
2. **Design.**
   - The **spec**: first the requirements with IDs and AC; then the design and the contracts (`create-spec`). With an
     Agentforce agent, its Agent Spec (`agentforce-generate`).
   - The **decisions**, with "Verified with" (`create-decision`).
   - The **delivery plan**: steps, dependencies, waves and traceability AC → step → verification
     (`implementation-integration-plan`).
   - The **independent review** of the spec and the plan (`independent-code-review`).
   - → **Design gate:** the approver approves the spec, the decisions and the plan. On approval, the tag
     `design-approved` is set.
3. **Execution** (role *Implementer*): one step at a time, within its scope, draft-first.
   - First the tests for its AC (at level 3 and in Apex and agent logic, in an earlier commit); then the
     implementation and the step report, with the diff.
   - The independent review, on a specific commit.
   - → **Gate for each step:** the reviewer's verdict (`no_blocking_findings`) and the step report. With `strict`
     autonomy, also the approver's OK on the diff before deploying; with `critical`, it is not needed (see
     "Escalation").
4. **Review** (role *Verifier*): serial integration in the org and the Definition of Done. Findings are reported.
   - → **Release gate:** the approver's explicit OK before `publish` or `activate`. On approval, the tag `release-N`
     is set.

When something is ambiguous, or the scope grows, stop and ask. One change or task at a time; whatever comes up outside
the scope is listed and asked about. Prefer minimal, reversible changes.

## Guided conversation

The person using the method just talks; they do not need to know what the skills are called. The main session keeps
the thread: it decides which skill is needed, loads it and tells the user where they stand and what is up to them.

- **When starting or resuming:** read `status.md` (and the handover, if there is one) and sum up in two or three lines
  the stage, what is done, what is missing for the next gate and what you expect from the user. If the project has
  just been bootstrapped, offer to start the Plan and remind them of what only they can do (log in to the org and put
  the sources in `docs/client/`).
- **What to do with what they say:**

  | The user says | What you do |
  |---|---|
  | "start", "continue", "go ahead" | You continue the current stage according to `status.md` |
  | "where are we?", "what's left?" | You summarize `status.md` and the change queue, and propose the next step |
  | "I approve", "OK to the Plan", "go ahead with the design" | The gate's actions: its tag (`baseline-<date>`, `design-approved`, `release-N`), `status.md` and, at a phase change, the handover |
  | "there is a bug in…", "change this AC", "add…" | A change request: an entry in the queue with its level and the path it takes (section "Change requests") |
  | "record this", "note that…" | `create-decision` if it is a choice with consequences; `create-gotcha` if it is a trap |
  | "what is this?", "how does the method work?" | `sdd-help`, in a few lines |

  If it is not clear what they mean, ask with options instead of assuming.
- **Questions:** those in `questions.md`, one at a time or grouped by topic, with options when they are closed. What
  is already known about the project, propose it instead of asking.
- **When closing a gate, or a step that the autonomy escalates:** what is done (with the paths of the files), what is
  missing and **one** question: the approval, the correction or the doubt that unblocks what comes next. With
  `critical`, a step that is not escalated is closed by reporting, and you move on to the next one without waiting for
  an answer. Never close with "invoke the X skill" or with a `/command`; if the user uses one, it works as a shortcut.
- **After the Plan gate, the Design gate or a release is approved** (not the gate of each step), the orchestrator is
  rotated (section "Change requests"): leave the handover and tell the user, in one sentence, that the next stage
  continues in a new session in the project folder and that there it is enough to ask "where are we?". That is the
  only thing you ask them to do outside the conversation, along with what only they can do (logging in, the
  customer's sources).

## Roles

- **Explorer:** maps the code and the org, answers and proposes. Does not edit the code or the org; writes the Plan
  documents.
- **Implementer (author):** one step within its scope. Does not deploy or write `status.md`.
- **Verifier (reviewer):** reviews what it did not write, with a separate context; does not fix anything unless asked.
- **Orchestrator and integrator:** the main session. Assigns steps, reserves files, checks the step report, merges,
  is **the only one that deploys** and the only one that writes `status.md`. Does not review its own changes. Its
  startup template is in `references/orchestrator.md`; the rules for author sessions, in `references/author-brief.md`.

In Agentforce, the ADLC subagents: `adlc-author` and `adlc-engineer` (author), `adlc-qa` (reviewer).

## Skills by stage

| Stage | Skills |
|---|---|
| Plan | `sdd-method` (verify the environment), `read-knowledge`, `platform-docs-get`, reading the org |
| Design | `create-spec`, `create-decision`, `create-gotcha`, `implementation-integration-plan`, `independent-code-review`; with an agent, `agentforce-generate` |
| Execution | The execution skill of each step; `independent-code-review`, or `adlc-qa` and `agentforce-test` |
| Review | `implementation-integration-plan` (integration), `sdd-method` (traceability), `platform-apex-test-run`, `agentforce-test` |
| Change request | `sdd-method` (below), `create-spec` (Change log) and the execution skill of the change |

## Definition of Done

- `sf agent validate` and `sf project deploy start --dry-run` without errors;
- the relevant tests pass (`sf apex run test --code-coverage`, `sf agent test`);
- the preview with `--use-live-actions` confirms the behaviour, with the traces reviewed;
- (agents) the security review has no BLOCK findings;
- (UI) the UI AC have their `browser check` in Chromium (section "Browser");
- every AC in scope has its verification and the traceability check ends without errors;
- the diff is reviewed and approved.

## Escalation

- **`strict`:** every gate waits for the approver's OK, including the gate of each Execution step.
- **`critical`:** you escalate, and wait for an answer, only for (1) a substantial change to the user experience, (2)
  a departure from the approved requirements or AC, including being unable to satisfy an AC, (3) a change of stack or
  of platform functionality, a new product or licence, or an irreversible org setting, or (4) a blocker that cannot be
  resolved. Everything else (deployments to the org, spikes, synthetic data, reversible assumptions, review fixes) is
  decided and recorded in `status.md` or in a decision with author `agent`.
- **`light`:** as `critical`, and deploying, `publish` and `activate` against the project's org are not escalated
  (light block).
- **In all of them:** the Plan gate, the Design gate, the release, irreversible settings, every external message and org
  isolation.

## Profiles: full and light

The project chooses its profile at bootstrap, in the same question as the autonomy, and the orchestrator reminds the
approver of it, with what it implies, when the Plan starts. Up to the Plan gate it is changed in `sdd.config.json` and
decision 001; after that, with a new decision that supersedes 001 (M-11).

| Option | `sdd.config.json` | What it implies |
|---|---|---|
| Full, OK at every step | `profile: full`, `autonomy: strict` | The whole method; the approver also approves the diff of every step before deploying |
| Full, critical only | `profile: full`, `autonomy: critical` | The whole method; between steps, only what is critical is escalated |
| Light | `profile: light` (autonomy `critical`) | The same gates and the spec with AC; less ceremony around them, parallel subagents and an automatic deploy, publish and activate in the project's org (light block) |

Recommend full with `strict` the first time with the method, and light for demos with little risk and a short
deadline. Going from light to full loses nothing: the requirements, the AC and the traceability already exist; the
pieces of full (waves, sizes, test-first, the full step reports) are added from that moment.

## Parallel orchestration

In both profiles; the default way of executing the plan.
- **Reservations by `Touches`:** each step lists the folders and the metadata it touches. Two steps that touch the same
  thing are not launched at the same time. The shared files (profiles, permission sets, layouts, FlexiPages, the
  `.object` files of shared objects) belong to the orchestrator: authors request the change as a patch in their step
  report, and the orchestrator applies it when it closes each batch.
- **Authors as subagents** (the Agent tool with `isolation: worktree`), with the common brief
  (`references/author-brief.md`) and the assignment. For an Agentforce agent, `adlc-author` and `adlc-engineer`. Launch
  in one message every step that is ready and does not collide; the results come back to you in the same turn.
- **One reviewer per step,** also a subagent, with a separate context: `independent-code-review`, or `adlc-qa` for the
  `.agent`. It is independent review (M-01): neither the author nor the orchestrator reviews it.
- **Serial integration:** there is a single org. The orchestrator merges and deploys one step at a time and verifies it
  in the org, with the browser if the step has UI AC.
- Separate author sessions still work in `full` (for example, a very long step); then the handover between sessions of
  `references/orchestrator.md` applies.

## Browser

To see and test the UI (Lightning pages, LWC, sites, the Enhanced Chat widget, the demo walkthrough). Rule M-12; the
detail and the Salesforce gotchas are in `references/browser.md`.
- **Only the project's Playwright MCP** (`.mcp.json`, server `playwright`, tools `mcp__playwright__*`), with
  Playwright's own Chromium and its profile in `.playwright/profile`. Never the managed Chrome, the Browser pane or
  Claude in Chrome: in Salesforce enterprise orgs they are disabled. If the tools are not in your session, say so: the
  project needs its `.mcp.json` (`sdd-bootstrap` creates it), the user's approval of the MCP and a new session.
- **Only the project's org:** the plugin's browser guard denies other orgs' hosts. The user logs in by hand, once, in
  the Chromium window; you never type passwords.
- **Plan:** a read-only tour of the org's UI, with screenshots in `docs/baseline/`.
- **Execution:** a UI AC is verified with the label `browser check` after the deployment, by the integrator: what was
  seen goes into `## Verification cases` of the step report, with the selected screenshots in
  `docs/delivery-plan/evidence/<step>/`.
- **Review:** the demo walkthrough is run in Chromium and fills `demo-walkthrough.md`.
- **Never** click an irreversible setting in Setup without the approver's OK, and only synthetic data on screen.

## Communication

- Orchestration happens only between Claude sessions and subagents.
- Every external message, even an acknowledgement, needs the approver's OK **for that message**; it can be drafted
  beforehand. Never write directly to the customer. The allowed channels are in the project's `CLAUDE.md`; the
  protocol for acknowledgement and delivery verification, in `references/communication.md`.
- Reading official and internal documentation and searching Slack are allowed without asking.

## Verify the environment

From the project root:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check-environment.py --query-org
```

- `--query-org` only reads the API version of the `org_alias` in `sdd.config.json`; it does not use the default org
  or show the token, so there is no need to confirm the target org first. Without a login on that alias, the error is
  one more blocker, or you pass the version the approver gives you with `--api-org <version>`.
- Compare the result with the list of skills in your session, which is the source of truth. The inventory is written
  to `docs/baseline/`.
- **Blockers:** a required skill missing or shadowed, a tool or API below the minimum, or the API not checked. Each one
  goes into `questions.md` as soon as it appears, without waiting for the verification to finish or asking for an OK.
  The Plan gate does not pass unless the approver accepts the gap as a decision.
- Repeat the verification if the plan adds an area, when sf-skills or the plugin are updated and when changing
  machines.

## Check traceability

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/check-traceability.py             # the whole project
python3 ${CLAUDE_SKILL_DIR}/scripts/check-traceability.py --step W2.1 # the evidence of one step
python3 ${CLAUDE_SKILL_DIR}/scripts/check-traceability.py --graph     # waves and critical path
```

It checks the spec, `traceability.md`, the steps, the step reports, the reviews, each step's `Skill` against the
inventory and, from the Design gate on, that every requirement or AC changed since the last tag (`release-N` or
`design-approved`) has its row in the `## Change log`. The configuration is in `sdd.config.json`; whatever is missing
takes the script's defaults.

**Project vocabulary:** these rules give the names of a new project (`method.vocabulary: "en"`): `AC-…`, `Depends on`,
`## Change log`, `docs/delivery-plan/step-reports/`, the tag `design-approved`, `docs/baseline/environment.json`. A
project bootstrapped with 0.2 or 0.3 keeps its Spanish vocabulary (`CA-…`, `Depende de`, `## Registro de cambios`,
`fichas/`, `diseno-aprobado`, `docs/baseline/entorno.json`, `docs/cliente/`) and the checks read it as it is:
`method.vocabulary`, or the Spanish `metodo` key, decides. In such a project, use its names where these rules give the
English ones, and copy headings and fields from its own documents, never from the plugin's templates; the hook's
equivalences line gives each pair.

## Change requests: changes after the Design gate

Every change enters the **"Change queue"** in `status.md` (`CH-NNN`, origin, what changes, level, escalation, session
and branch, state). The orchestrator writes it; with no active orchestrator, the session that receives the change takes
on the role from `references/orchestrator.md`. First triage question: **does the code break a current AC, or does the
change alter what the spec promises?** When in doubt, the higher level. Escalation to the approver is separate from the
level. A change that grows goes back to triage; one discovered while building is not a bug.

**Short path, the most frequent:**
- **0 · bug** (the code does not satisfy a current AC): a failing regression test, the fix, a review of the diff. The
  spec does not change and there is no row in the change log. If the bug reveals that an AC is missing, it is level 1
  or higher.
- **1 · tweak** (it changes neither the observable behaviour nor the contracts): the change and a review of the diff;
  an independent review only if the gate requires it. If it touches the spec (for example, resolving a `[PENDING]`
  without changing what the AC asks for), its row in the change log. The orchestrator can do it if it comes up while
  integrating; several tweaks can go in one maintenance session, each with its own entry in the queue.

**Full path:**
- **2 · feature** (new or different behaviour within the current contracts): the delta is written into the spec right
  away, with its row and "Approval: pending", and the code waits until what was written is approved: by the
  orchestrator or, if it is escalated, by the approver. Then test-first in Apex and agent logic, and an independent
  reviewer.
- **3 · contract or risk** (a new or changed contract, identity and permissions, irreversible data or settings,
  integrations): the modified spec and its rows go through the Design gate again; test-first, a reviewer and a second
  security perspective.

**Common rules:**
- **One change, one session,** started from the files: `CLAUDE.md` → handover → the queue entry → the spec for the
  scope. If it needs "what was discussed", the method has failed: write it down.
- **The delta before the code** (or in the same commit). The change log records only spec changes; the queue, all of
  them. A withdrawn AC leaves the requirements and moves to the `Exclusions` of `traceability.md`.
- **Closing:** the row links the commit; affected decisions are superseded by new ones; the traceability check passes;
  the queue marks the change integrated; gotchas are captured.
- **The orchestrator is rotated** with a handover at every phase change (after each gate and each release) and when its
  conversation has been compacted.
- **A baseline per release:** the tag `release-N` at each release; deltas are counted from the latest one (or from
  `design-approved`). In a project that adopts the change log with prior history, put a `release-0` tag on the
  adoption commit.

## Org, data and confidentiality

- The project's org is the only integration baseline: serial deployments, `--json`, draft-first. Changes outside the
  code (Setup, permissions that Support enables, changes made with an MCP or through the API) are recorded with their
  evidence in `status.md` and, if they are metadata, brought back with a retrieve.
- `docs/client/` is confidential and not versioned; the discovery cites it by document and page. In the org and in
  `data/`, synthetic data only.

## References

- `references/rules.md`: the why of each rule (M-01 to M-12) and what was discarded.
- `references/browser.md`: the browser with Playwright, its setup, its limits and the Salesforce gotchas.
- `references/orchestrator.md`: the template to start or resume the orchestrator.
- `references/author-brief.md`: the common rules of an author session and its assignment.
- `references/communication.md`: the protocol for channels, acknowledgement and delivery verification.
