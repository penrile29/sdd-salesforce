---
name: independent-code-review
description: Reviews code changes in a context independent of the author, investigates consequences beyond the diff and verifies findings and fixes with evidence. Use it to review a local candidate, with or without Git, or a PR, and to establish its readiness to integrate.
---

# Independent code review

Look for actionable defects against the project's contract. The output is a review traceable to specific content,
with findings, evidence, limitations and a verdict; not a confidence score or a claim that there are no bugs.

## Responsibilities and scope

- **Author:** implements and fixes; provides tests and responses to the findings.
- **Reviewer:** investigates the candidate in a context separate from the author's and verifies the responses. Does
  not modify the candidate; may create reproductions in an isolated copy within the authorized scope.
- **Integrator:** checks the final content, the mandatory verifications and how it composes with the base before
  incorporating it.

One independent reviewer is usually enough. Propose a second perspective for specific risks around state,
concurrency, permissions, migrations or oracles; do not impose a fixed number of agents or a provider. The skill on its
own does not authorize starting agents, posting comments or integrating. If the session wrote the change, it needs
another authorized context to claim independence. Without one, deliver a **self-review**, state the limitation
explicitly and do not satisfy a gate that requires independence. Separate sessions do not guarantee independent
errors.

Respect the project's current rules and the user's authorizations. A mandatory service or check remains mandatory
until the corresponding authority changes the policy. Reviewing a PR does not authorize posting comments or resolving
its threads.

## Flow

1. **Pin down the assignment.** Identify the objective, scope, base, candidate, local/remote mode and acceptance
   requirements. Read the project's instructions and select from knowledge the relevant spec, active decisions and
   gotchas. Distinguish facts, proposals and contradictions. If the base is missing, you can still review the current
   state, but not attribute defects to this change without evidence.
2. **Pin down the content.** Follow [references/review-method.md](references/review-method.md) to identify the
   candidate, walk the context beyond the diff and validate hypotheses. Include uncommitted changes and new files; a
   SHA alone does not identify a modified tree.
3. **Investigate.** Review contract and acceptance, correctness and integration, and the validity of tests and
   oracles. Test each suspicion against consumers, invariants and existing mechanisms before reporting it. Prioritize
   real consequences over style preferences. If the candidate is a spec or another document, also apply the
   requirements-quality perspective of `review-method.md`.
4. **Record.** Use [references/reporting.md](references/reporting.md) for the review, the findings and their states.
   Separate static reading, your own execution and evidence declared by third parties. Keep only useful artifacts, in
   the existing structure or in `reviews/<change-id>/`.
5. **Revalidate.** Keep IDs and the history of rounds. An author's response does not close the finding: check the fix
   or the refutation and possible regressions. Do not lower the acceptance bar or weaken tests to get a favourable
   result.
6. **Deliver.** Issue `changes_required`, `no_blocking_findings` or `incomplete`, together with the content reviewed
   and the coverage. The integrator also applies all of the project's checks and verifies the composition. A
   favourable verdict does not mean integrated, deployed or accepted.

If material context is missing, infrastructure fails or a disagreement repeats without new evidence, keep what has
been demonstrated and point out the pending verification or decision. A time limit does not approve the change.
Continue with independent areas if they are authorized.

## Closing and learning

Recompute the candidate's identity when closing. If it changed, review the delta and its consequences before renewing
the verdict; justify which evidence still applies. Composition with a new base can also invalidate evidence even if
the author's diff does not change.

Feed learnings back into knowledge when appropriate: verified, reproducible gotchas; decisions with their status and
authority; changes to the spec/acceptance if it was decided to change the behaviour. An isolated comment does not
create a universal rule. Do not publish private reasoning, secrets or unnecessary data in the artifacts.

It can be used on its own or as a capability of `$implementation-integration-plan`, if available. To evaluate its
effectiveness or replace an existing reviewer, follow [references/evaluation.md](references/evaluation.md). Validating
these files does not demonstrate equivalence with another reviewer.
