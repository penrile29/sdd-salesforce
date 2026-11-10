# Communication protocol

## 1. Orchestration: only within Claude
- The main session (the orchestrator) coordinates Claude sessions and subagents. Author sessions receive the common
  brief (`author-brief.md`) plus their assignment and return their step report; they do not write `status.md`.
- A session that gets blocked asks the orchestrator in a single message and stops.
- Work is not coordinated through Slack, issues or other channels.

## 2. External messages: only with the approver's authorization
- **Allowed channels:** those listed in the project's `CLAUDE.md`. A new channel is added with a decision.
- Every message (Slack, email, Support case, the customer or their partner), **including an acknowledgement**, is
  **drafted** first and **sent** only with the approver's explicit OK for that message. One OK does not cover the
  next message, even on the same channel.
- **Never** write directly to the customer.
- Before sending, say exactly what goes in the message. If it contains personal or payment data, identifiers or
  credentials, they are replaced with placeholders unless the approver confirms otherwise.
- **Verify delivery:** after sending, check that the message arrived (the thread or the case exists) and record it in
  `status.md` with its link.

## 3. Research: allowed without asking
- Reading official (`platform-docs-get`) and internal documentation.
- Searching and reading internal Slack, read-only. What is learned goes into the discovery with its link.

## 4. External requests
- Every request to third parties (Support, other teams, the partner) has an ID `P-NN` in the "Requests and work items"
  table of `status.md`, with its channel, owner, state and next action.
- **No external monitoring:** at the start of each session, review `status.md` and the Claude sessions, and go over
  what is pending with the approver.

The detail of acknowledgement, response and publication verification is in `implementation-integration-plan`,
reference `orchestration-communication.md`.
