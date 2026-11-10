# Discovery, specification and project knowledge

## Look things up before acting

First look for the existing structure and its conventions. If `knowledge/` exists, read its index and the headers of candidate documents; filter by component, topic, version and status. Read the relevant documents in full, follow their links and verify that they still apply to the observed code/configuration. Repeat this selection when you change scope.

The reading is part of every agent's brief, locally too. Do not load the whole history indiscriminately, and do not treat a search result as knowledge already read. When the project has a skill available for creating specs, decisions or gotchas, use it and respect its rules. If there is none, apply the conventions of this reference; do not depend on private plugins.

## 1. Discovery with evidence

Before choosing a solution, identify:

- Problem, users/actors, current situation, desired outcome and how it will be measured.
- Real flows, edge cases, input/output data, owners and systems involved.
- Constraints on scope, compatibility, operation, resources and data.
- Existing capabilities that can be reused, and the gap to the required behaviour.
- Alternatives, hypotheses, risks and questions that can change the solution.

Use local documents, examples, code, tests and the user's answers. Use external sources only when they are necessary and accessible; working without GitHub does not rule out other authorized sources, but it does not require connectivity either. If something cannot be verified, record the limitation.

For each finding record the source, date/revision, observation and consequence for the design. Distinguish **observed fact**, **stated need**, **hypothesis** and **proposal**. A prototype shows a possibility; on its own it neither validates the need nor constitutes the approved architecture.

Investigate decisive uncertainties with the smallest useful check: reading a real path, comparing against a contract, an existing test or a bounded experiment if it is authorized. Specify the question, the expected result and the conclusion. An experiment must not introduce unrequested permanent changes.

Output: a summary of the problem and the flows, the evidence, the options and the questions, prioritized by the steps they affect. Move on to the specification when the problem and scope are defined well enough. If doubts remain, allow the independent part to be designed and mark explicitly what is pending.

## 2. Technical specification before non-trivial development

Write the spec with the user from what has already been expressed and settled; ask about relevant product or design choices that are still open. Do not add an approval ceremony if the direction is already authorized. Do not present a proposed decision as accepted.

The spec has two parts, in this order. The design of a part does not move to `Ready` without its requirements.

**Requirements (why and what).** No implementation decisions, except those imposed by the customer's design.
1. Problem, discovery evidence, goal and observable measures of success.
2. Scope, exclusions and actors.
3. Requirements with a stable ID: `R-<AREA>-NN`, or the project's IDs if they already identify a behaviour and not a piece of design. Each one has a source, a priority and at least one acceptance criterion:
   `AC-<AREA>-NN.M — Given <context>, when <stimulus>, then <observable result> (<where it is checked>).`
   Include the errors, rejections and denied permissions that matter, not only the happy path.
4. Assumptions and open items, marked inline with `[PENDING: Q-NN]` and linked to `questions.md`.

**Design (how).**
5. Architecture, responsibilities and source of truth.
6. Contracts: data, states and transitions, inputs and outputs, invariants. Each contract cites the requirements it satisfies.
7. Applicable concerns (identity and permissions, failures, observability, delivery) and the gotchas it avoids.
8. Links to the decisions that justify the choices; the alternatives live in the decisions.
9. Test strategy: what type of verification covers each family of AC.

Fit the depth to the change; do not impose a distributed architecture or migrations where there are none. For new work, write one spec per feature or contract that can be approved and tested separately; if there are several, an index spec links them. A spec already in progress can remain a single one, with blocks per area. The spec defines behaviour and contracts. The order and the division of work live in the plan, and progress in the source of state; never in the spec.

Before declaring a part `Ready`, check the quality of its requirements:
- every requirement has at least one AC;
- every AC is falsifiable (stimulus, result and where it is checked) and does not use vague terms such as "fast", "adequate" or "correct";
- the requirements do not prescribe implementation that the customer does not impose;
- they do not contradict current decisions;
- no `[PENDING]` that blocks that part remains.

Then check that its interfaces and rules can be implemented without guessing.

The `create-spec` skill of this plugin already applies these rules: the requirements part with AC is mandatory, the
spec carries no plan or progress checkboxes (only a link to the delivery plan) and open items are marked inline with
`[PENDING: Q-NN]`. If the project uses another spec template, this reference prevails on those three points.

The rest of its format stays as it is. If a decision or gotcha changes, review the specs and steps that cite it.

## 3. Knowledge structure and metadata

Keep the project's structure. If there is none, this base is enough; create only folders/documents with real content:

```text
knowledge/
  README.md       # index, conventions and entry point
  discovery/      # evidence and questions about the problem
  specs/          # technical design and acceptance
  decisions/      # choices and their reasons
  gotchas/        # verified non-obvious problems and how to prevent them
```

Use relative Markdown links between documents so that they work without a remote repository. Add brief metadata for choosing what to read: `title`, `description`, `updated_at`, `tags` and `project_version` when it is known. Do not invent versions. Specs carry `status` in the frontmatter: `Draft`, `Ready`, `Implemented` or `Accepted`. If their parts are in different states, the per-requirement status lives in `traceability.md`. Discovery can use the project's states. Distinguish declared implementation from verified implementation.

Avoid IDs that collide between agents: reserve ranges, use a date+unique slug or centralize assignment. A single owner updates the shared index when there is concurrency.

## 4. Decisions: keep the reasons

One decision per document: context, choice, discarded alternatives, consequences, author, status and sources. Capture both human choices and choices delegated to agents, without falsifying authorship.

Use `Proposed`, `Active`, `Superseded` if there is no prior convention. Keep separately who accepted it or which delegation allows it to be activated. A new business rule does not become Active just because an agent wrote it. Active decisions are read as current; superseded ones serve to understand the history.

To change a current decision, create another that supersedes it and link both ways. In the earlier one, update only its status/supersession link and the necessary metadata; preserve the original reasoning. Adjust the affected specs, contracts, plans and tests. Do not delete decisions to remove contradictions.

## 5. Gotchas: turning a failure into prevention

Create an entry when there is non-obvious behaviour backed by evidence: an execution condition, a tool/protocol quirk or a limitation that has caused a failure or can reproduce one. Do not turn suspicions into facts; an unconfirmed cause stays as a discovery hypothesis or an issue.

Record the symptom, the affected conditions/versions, the reproduction or evidence, the verified cause or the degree of uncertainty, the solution/prevention and how to verify it. Link the change or decision that mitigates it and the affected components. Use synthetic or sanitized data; never copy secrets or private content into a reproducible recipe.

Consult gotchas when writing the spec, assigning a step and reviewing the integration. When one constrains the work, include it in the brief and in the corresponding acceptance criterion. If it stops applying, record the version/condition under which it was resolved; do not keep imposing it universally.

## 6. Closing the loop during implementation

Include this protocol in the execution method, local or remote:

1. Before the step: read the spec, active decisions and gotchas for the scope; record the version/baseline used.
2. During the step: detect discrepancies with the design, new assumptions, choices and surprises. Do not redesign silently.
3. Classify: uncertainty → discovery/question; choice → decision; verified non-obvious failure → gotcha; agreed behaviour change → the spec's requirements and AC; then, the plan and the tests.
4. When integrating: check the affected documents, links, state and evidence. Integrate code and knowledge updates consistently, without mixing in cleanup outside the scope.
5. When delivering: state the documents created/updated, the pending decisions and what the next session needs to know. If there is no new learning, do not create filler entries.

Keep a navigable chain: **evidence → spec → decision/gotcha → step → test → integrated change**. A gotcha can point to a decision that avoids it; the decision cites the gotcha in return. Reuse canonical sources instead of duplicating them in briefs.

## Minimal templates

```markdown
---
title: "[Title]"
description: "[One sentence that lets the reader decide whether to read it]"
updated_at: "[YYYY-MM-DD]"
tags: ["[component]"]
---
```

- **Discovery:** problem and actors; current/desired flows; finding/type/source/consequence table; alternatives; hypotheses and checks; questions and blocked scopes.
- **Spec:** why; what; how; contracts/invariants; alternatives and decisions; gotchas; acceptance and tests; excluded scope; questions and status.
- **Decision:** add `author` and `status`; context; decision; alternatives; consequences; authority/evidence; links to specs/gotchas; supersedes/superseded by when it applies.
- **Gotcha:** symptom; environment/versions; evidence/reproduction; cause or uncertainty; prevention/solution; verification; applicability status and links.

The bracketed fields are template instructions: replace them before delivering documents.
