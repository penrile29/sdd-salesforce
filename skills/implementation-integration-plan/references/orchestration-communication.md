# Orchestration, communication and handover

Read this reference when the plan includes coordinating agents or continuity between sessions. Define documents with clear responsibilities; reuse the existing ones and combine pieces if the project is small. The names below are an adaptable convention, not provider requirements.

## Map of document responsibilities

| Piece | Responsibility | Avoid duplicating |
|---|---|---|
| The project's entry instructions, such as `AGENTS.md` or an existing equivalent | Point to the current rules, knowledge and operational documents; set the reading order | Do not copy the state of each task |
| The plan's `README.md` | Phases, dependencies, test strategy, acceptance and completion criteria | Do not use it as a communication inbox |
| `handover.md` | Operational entry point for the orchestrator: handover, current rules by reference, coordination, gates and configured monitoring | Do not turn an old snapshot into the current state or duplicate all the rules |
| Communication protocol (in sdd-salesforce, `sdd-method/references/communication.md`) | Channels, acknowledgement, response, delivery verification, polling frequency and escalation | Do not store daily progress here |
| Common brief (in sdd-salesforce, `sdd-method/references/author-brief.md`) | Common instructions and the assignment contract for builders and reviewers | Do not confuse it with instructions for whoever directs the whole |
| Orchestrator template (in sdd-salesforce, `sdd-method/references/orchestrator.md`) | Assignment to start or resume directing the work | Do not fix a baseline, counter or list of agents that will go stale |
| Source of operational state | Active work, owners, reservations, blockers, evidence and progress reports | Do not keep an issue and a file as contradictory sources |

The entry point refers to the handover and the protocol for how to direct and communicate; after that, the plan, the briefs and the relevant technical sources are consulted. Use valid relative links. Modify the entry instructions only within the authorized scope; otherwise, deliver the proposed addition.

The operational state can live in a local file, for example `status.md`, or in an authorized remote system. The handover is a dated summary with a link to that source and rules for checking it against reality. If a mirror is used, state which one is the main source and when it was synced.

## Communication protocol

Define a record per channel: purpose, owners, location, who can post, polling frequency, escalation criterion and last message handled. Separate requests/decisions from progress reports even if they share a medium. Use configurable roles; do not inherit people, issue numbers or channels from another project.

For each request that requires work:

1. **Read and classify.** Record ID/link, author, scope, owner and whether it asks for action, a decision or only information. Check that the request fits the current instructions and authorizations.
2. **Acknowledge receipt.** When appropriate, prepare the acknowledgement (`ON IT` or the agreed equivalent, with the owner and the scope taken on) and send it only with the approver's OK for that message, like any other message sent. The acknowledgement says that the request has been picked up; it does not certify a solution or acceptance of a decision beyond one's authority.
3. **Work and respond.** Return the result, verifiable evidence, open items and next action. Record blockers with the decision or information needed. Do not send repeated messages without progress.
4. **Verify delivery.** Confirm the publication with the service's response and, when necessary, a later read of the message at its destination. Keep the ID/link. A drafted response or a failed call is not a publication. If the result is ambiguous, inspect the destination before retrying to avoid duplicates.
5. **Close the follow-up.** Mark the request as handled when the response has been delivered and its closing condition is met. Separate received, in progress, answered and closed; answering does not always resolve the matter.

Preparing this protocol does not authorize sending messages. If there is no authorization or tool, leave the response prepared and identify it as still unpublished. Do not invent a delivery. An OK is valid for one message: the next one, even to the same channel, needs its own.

Locally, use the same states in a persistent record: ID, request, owner, acknowledgement, response, evidence, pending. Verify the write by reading the record back. This proves local persistence, not that another person has read the response. If several agents write, assign one writer or use separate records per agent with serialized consolidation.

## Review frequency and heartbeat

The plan defines the monitoring policy; creating a recurring process is a separate action. Record whether it is **proposed**, **configured** or **active and verified**. Inherit the cadence of the current project when there is one; if it is missing, propose a frequency proportionate to the work and make it explicit that there is no active monitor yet. Do not copy intervals from another project or create automations merely because you are planning.

Specify:

- Owner, channels and signals to check: new requests, deliveries, checks, blockers and agent activity.
- Frequency or events that trigger the review, time zone when it matters, and the end condition.
- Cursor or last event handled; when the last cycle was completed and the next pending matters.
- Which changes justify a notification: a decision needed, completion, a relevant failure or blocker. Stay silent if nothing changed, unless periodic reports have been requested.
- Recovery after an interruption: check the real state, detect pending cycles/operations and avoid duplicating messages, assignments or integration.

A heartbeat does not prove product progress. Do not claim continuous monitoring if only a one-off check was done. Integration control still requires current content and evidence.

## Orchestrator entry template

```text
Direct [authorized scope] in [local/remote mode].
Read [entry instructions], [handover] and [communication protocol].
Consult [main operational state], [plan/phases/dependencies] and [common brief].
Load the specs, active decisions and gotchas of the steps you are going to coordinate.
Check the handover against real content, active agents, reservations and pending operations.
Identify what is ready, blocked, in review or really integrated.
Assign only authorized work, with an explicit baseline, scope, dependencies and acceptance.
Separate author, reviewer and integrator according to the current review protocol.
Collect requests and prepare acknowledgements and responses; send each one only with the approver's OK for that message, and verify the delivery.
Apply [agreed cadence/events]; do not declare active a monitor that does not exist.
Check gates on the final content and the composition before incorporating changes.
Update [main state] with facts, evidence, blockers and next action.
After an interruption, inspect the result before repeating operations.
When handing over, leave a dated snapshot, current references, the queue, reservations,
the last messages handled and the next executable action.
```

Do not fill the template with fictitious attributions or capabilities. The authority to integrate, resolve decisions or start agents must come from the assignment and the applicable rules.
