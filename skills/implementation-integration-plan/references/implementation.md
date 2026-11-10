# Deriving the implementation from the design

## From the design to verifiable obligations

Go through the discovery, normative sections, active decisions, relevant gotchas, examples and test plan. If design is missing, apply `discovery-knowledge.md` before declaring the affected steps ready. For each obligation record: ID, source/revision, status, required behaviour, existing implementation and evidence. Examples can reveal rules the summary left out: errors, intermediate states, concurrency, permissions or versions.

Classify each obligation as existing and verified, existing and unchecked, to be built, deferred with a reason, superseded, or needing no implementation. Do not count a proposal as an approved decision, or a reference in the code as compliance.

Use the spec's requirement and AC IDs. If the spec does not have them, propose adding them to the spec, not only to the plan, so that spec, plan, tests and traceability share the same IDs. Do not fabricate an approval history. Separate reversible assumptions from pending design decisions; only the former allow detailing a provisional implementation without further authorization.

## Contracts that unblock the work

Identify the boundaries between scopes: data and event schemas, APIs, tools, model client, storage, configuration, authentication, migrations and fixtures. Include only those that apply.

For each contract record producer, consumers, canonical source, version, owner, compatibility and test. Its first deliverable can be schema + validator + stub + fixture. A stub lets consumers be developed, but it does not prove the connection with the final implementation.

The initial phase must resolve the contracts that really block parallelism. Avoid designing the whole system up front. Freezing a contract means controlling its changes; a correction requires analysing consumers and updating their evidence, not forbidding necessary changes.

## Splitting and sequencing

Group by dependencies and reviewable scopes, respecting the existing repositories. An indicative sequence is foundations/contracts → core → independent components → composition → delivery and acceptance. The project's graph determines the real phases.

A step should fit in one coherent review and produce observable evidence. In remote mode it can be a branch/PR; with local Git, a branch or a set of commits; without Git, a change identified with a diff/snapshot and a verification. Split steps that are too large and document justified groupings. Do not turn a historical estimate of "one day" into a promise.

For each dependency, specify the unblocking condition: a versioned contract, a merged implementation, an available migration or acceptance in an environment. Identify the path that blocks delivery; do not compute durations without effort/capacity data.

Test the decomposition by following at least one complete user or data journey. There must be steps to connect components, register routes/services, configure startup and run workers, not only to implement isolated classes. An available constructor does not show that the application uses it.

## Designing the evidence when writing the step

Each "done when" criterion defines the stimulus, the expected result and where it is checked. It can be an automated test or a justified manual check. Proposed test names are future targets, not existing tests.

Choose layers according to risk:

| Risk or property | Useful verification |
|---|---|
| Interface between components | Consumer against fixtures produced by the provider, and vice versa; schema and version pinned |
| State derived from events | Live state = rebuilt state; idempotence and ordering, only if the design requires replay |
| Concurrent writes | Truly overlapping operations, invariants and no loss/double application |
| Identity and access | Allowed and rejected cases; isolation and context propagated across boundaries |
| Calculations | Limits, empty inputs, precision and relevant properties |
| Pipeline | Full flow with synthetic data and explicit substitutes; then with authorized real components |
| Delivery | Deployed artefact/version, startup and one representative observable operation |
| Failures | Retry, recovery, interruption or compensation, according to the contract |

At level 3 (contracts, identity and permissions, irreversible data or settings, and integrations) and in Apex and agent logic, the test comes first: the step's first deliverable is the tests or test cases for its AC, written before the implementation and with the AC ID in the name or in a comment. In Salesforce, with a single integration org, there is no need to show the red by deploying an earlier version: it is enough that the test precedes the implementation in the history (a commit with the test and a stub) and that its oracle detects the failure, even if they are deployed together. In Screen Flows and OmniScripts, test first means writing the test case first. Everywhere else, the AC and its verification are defined before building, and the tests go in the same commit.

| AC about… | Verification |
|---|---|
| Apex logic, triggers and transitions | Apex test with `--code-coverage`; at least one method per AC |
| Autolaunched and record-triggered flows | Test Mode (Beta), with Scenario Testing Automation and assertions, or an Apex test that fires the flow |
| Screen Flows | Apex test of their invocable logic and a demo step with evidence; there are no automated Screen Flow tests |
| Agent | `sf agent test` case (YAML) and a trace of `sf agent preview --use-live-actions` |
| Permissions and sharing | "Allowed / denied" tests with `System.runAs`, with the permission set assigned (user mode from API 67) |
| Metadata (objects, fields, CMDT) | `sf project deploy start --dry-run` and a describe or a verification SOQL query; tests, separately |
| LWC | Jest (`sfdx-lwc-jest`) for the component's logic |
| React micro-app | Its own unit tests |
| OmniScripts and site | A step of the demo walkthrough with evidence (screenshot or trace), justified as manual |

Do not impose a ledger, replay, tenancy or AI on projects that do not need them. Do not count a test that reproduces the code's logic as an independent validation of the result.

For operational decisions that are hard to diagnose, add an observable event, correlation, rule/result and verification. Define signals proportionate to the system and avoid sensitive content.

## Traceability and audit

Build two maps: obligation → steps/verifications, and acceptance criterion → verification. Include cross-cutting principles in the steps that enforce them. Explain deferred and superseded items and requirements with no code; do not silently remove them from the denominator.

Also check the reverse direction: every step answers an obligation or an explicit technical need. Mark decisions as proposed if the decomposition introduces new behaviour.

A coverage table shows planning, not correctness. Except for a tweak that changes neither observable behaviour nor contracts, the traceability check reads the IDs from the spec, from `traceability.md` and from the test sources, and validates unknown or duplicate IDs, broken references, cycles, active AC without verification and tests without a match. A local script is enough; a hook can run it when the spec is saved or before the gate. To claim that the tests exist, check that the runner discovers them; to claim that they pass, use a concrete run and review.

Record the findings of each round and their corrections. The closing condition is verified coverage and consistency, or visible blockers, not a preset number of reviews. If the budget runs out first, state what is left to review.
