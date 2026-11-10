# Why the method is the way it is: rules M-01 to M-10

What each rule says is in the `SKILL.md` of `sdd-method`; here, why it was chosen and what was discarded. M-10 also
gives its detail here, because the core only summarizes it. A project adopts the rules with its seed decision 001
("We adopt sdd-salesforce vX.Y") and cites them by ID ("rule M-08"). To depart from one in a project, record a project
decision that says so and justifies it.

## M-01 · Cycle with independent review
**Why:** a project with an extensive customer design, a single integration org and several Claude sessions needs what
was agreed to be verifiable, the status not to depend on any conversation, and whoever reviews not to be whoever
writes. "Ready to integrate", "integrated", "deployed" and "accepted" are different states: a step only counts as
integrated when the integrator has deployed it and verified it in the org.
**Discarded:** only the 4 gates, with no method (no contracts, traceability or independent review); only ADLC (it
covers the Agentforce agent, not the metadata, the portal or the integration).

## M-02 · Local git and baseline tags
**Why:** the org has no source tracking that is useful across several sessions, and the status has to be identified
by a commit, not by whatever is in the org. The tags `baseline-<date>` (Plan gate), `design-approved` (Design gate)
and `release-N` (each release) fix where changes are counted from. Each step goes on its own branch; the candidate
under review is a specific commit plus its diff.
**Discarded:** no git (there is no way to pin down what was reviewed or to revert); a remote from the start (it forces
an early decision on where the customer's code lives).

## M-03 · Document structure
**Why:** to separate what lasts (the why and what was agreed, in `knowledge/`) from what changes every day (status
and plan, in `docs/delivery-plan/`) and to isolate the customer's material (`docs/client/`, outside git). That way any
session starts cold with `CLAUDE.md` → `handover.md` → `status.md` and chooses what to read by the headers.
**Discarded:** everything in one specs folder (it mixes what was agreed with the status and the customer's material).

## M-04 · Orchestration, status and communication
**Why:** with several sessions, the status gets lost if it lives in a conversation, and a message sent on the
approver's behalf cannot be undone. That is why `status.md` has a single writer and every external message needs its
own OK.
**Discarded:** coordinating through a Slack channel (the status ends up outside the repository and mixed with
customers).

## M-05 · "Verified with"
**Why:** the customer's design says what they want; what the platform can do is said by the skills, the official
documentation, Slack and the org itself. A choice backed only by the customer's design may be impossible or fragile.
Whatever is not documented becomes a validation in the org before building.
**Discarded:** deciding from the customer's design alone (fast, but it leads to contracts the platform cannot meet).

## M-06 · Requirements and AC first, with levels of ceremony
**Why:** if the agents build against a design without verifiable criteria, nobody can check that the result complies.
The rules: A, requirements with AC before the design; B, the what separated from the how; C, traceability checked by
a script; D, test-first limited to level 3 and to Apex and agent logic; E, levels of ceremony 0-3, because the usual
criticism of SDD is that it applies the same ceremony to everything.
**Discarded:** a free-form spec (without IDs and AC, traceability cannot be checked); test-first everywhere (in Screen
Flows, OmniScripts and sites there are no automated tests to write beforehand).

## M-07 · Escalation according to autonomy
**Why:** asking for an OK on every detail slows the work down; not asking for it on what changes the product takes
control away from whoever answers to the customer. The project chooses `strict` or `critical` at bootstrap (in its
seed decision 001 and in `sdd.config.json`) and can change it with a new decision.
**Discarded:** a single level for every project.

## M-08 · Verify the environment at the start of Plan
**Why:** the method relies on the Salesforce skills, the ADLC plugin and the CLI. If one is missing, or an old copy
shadows the good one, the work comes out worse without anyone noticing. The minimums are read from the frontmatter of
the sf-skills themselves (`metadata.cliTools`, `metadata.minApiVersion`), so they are not maintained by hand. An
unchecked API is a blocker because, without it, the gate cannot know whether it is below the minimum.
**Discarded:** trusting the skills to activate on their own (if they are not installed, nobody sees it); a fixed list
of versions (it goes stale).

## M-09 · Change requests
**Why:** the cycle is designed for building something the first time. Without a path for later changes, either they
skip the spec and the spec stops describing the system, or the whole cycle is applied to them and the method is
abandoned; and if they are all made in the orchestrator's conversation, the why is lost when it is compacted. The
delta is written before the code, with its approval pending, so that what gets approved is what was written and not a
proposal in the conversation.
**Discarded:** editing the spec without a trace; a new spec per change request (it fragments the contract); a folder
per change with a proposal and deltas (more ceremony: left for a later version).

## M-10 · Language
**The rule:**
- Answer in the user's language, whatever language the project's documents are in.
- Write the project's documents (spec, decisions, gotchas, delivery plan, `status.md`, handover, step reports, reviews)
  in `method.language` of `sdd.config.json` (for example, `"es"`); if it is not set, in the user's language. Every
  brief to an author or reviewer subagent states that language.
- Structural tokens stay exactly as in the project's templates, in the project's vocabulary (`method.vocabulary`),
  whatever the language: the headings, field names and frontmatter keys of the templates, above all those the checks
  read (`## Change log`, `Depends on`, `Satisfies`, `Test first`, `## Verification cases`, the verification labels
  and the evidence states), IDs (`R-…`, `AC-…`, `W1.2`, `CH-NNN`, `P-NN`, `Q-NN`), git tags and file names. Translate
  the prose, never those tokens.
- In a project bootstrapped with 0.2 or 0.3 (vocabulary `es`), its templates are the Spanish ones it was created with:
  copy the headings and fields from the project's own documents, never from the plugin's templates, which are English.
  The hook's equivalences line gives each English token with its Spanish name in that project.

**Why:** the plugin keeps a single copy of its rules and templates, in English, and the people who use it work in
different languages. Answering in the user's language keeps the conversation natural. A single document language per
project keeps it from mixing languages when several people or subagents write in it, which is why each brief states
it. The checks read headings, fields, IDs, tags and paths literally, in the project's vocabulary: a translated
heading or field is no longer found, and the check reports an error or stops seeing what it should check. The
accepted cost is that a project in Spanish has its prose in Spanish and the template headings in English.
**Discarded:** a copy of the rules and templates per language (two copies to keep in sync); checks that accept both
languages at once (short separators and markers such as "and", "to" or "except" multiply the false positives);
writing each document in whatever language the session that writes it speaks (the project ends up mixing languages).
