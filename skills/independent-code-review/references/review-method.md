# Investigation and verification method

## Content and environment

| Mode | Identity and comparison | Validation |
|---|---|---|
| Local without Git | Snapshot of base and candidate; manifest of paths and hashes, including additions and deletions | Compare copies and run local commands in an isolated environment |
| Local Git | Explicit base, candidate commit, diff of staged/unstaged changes and relevant new files | Local diff and tests; without requiring a remote, PR or CI |
| Remote | Base and PR revision plus any local difference used | Checks associated with that revision, the actual scope of each check and applicable local tests |

Define which base answers the question: the ancestor to attribute the change, the current target for composition. Do
not confuse the two. Store the review in a directory excluded from the candidate's identity so that the report itself
does not change it.

Without Git, keep bounded recoverable copies as well as hashes. Identify deletions and, if they affect behaviour,
permissions and symbolic links; do not follow links outside the scope without need. Exclude secrets and third-party
data. If a necessary configuration is excluded, record its requirement without copying values and limit the
conclusion when that prevents verifying the behaviour. Do not initialize Git or create services just to review.

Do not discard the user's modifications to get a clean tree. The author's base, the reviewed candidate and the
composed result are distinct identities. The integrator verifies the base before applying and stops applying if there
are unreconciled changes by others.

## Independent context

The initial assignment provides the objective, the relevant spec/decisions/gotchas, base/candidate, acceptance
criteria and access to the code. Avoid handing over the author's reasoning or a preset diagnosis before the first
investigation. The author's claims and tests are evidence to be tested. In later rounds, the previous findings and
responses are needed to keep continuity.

Use graph tools if available; index the repository if needed and check that the sources correspond to the content
under review. Check doubtful or stale results against the actual tree. If the graph is not enough, search and read the
code directly. Do not mistake an index of another branch for evidence about this candidate.

From the modified points, follow producers, consumers, entry paths, persistence and side effects until the affected
contract is covered. Consult startup, registrations, configuration, migrations and transaction boundaries when
relevant. Declare the areas you could not examine.

## Perspectives

### Contract and acceptance

Relate each changed behaviour to the spec, active decisions and requirements. Check inputs, outputs, errors,
compatibility and invariants. A test that describes the current code does not show that it meets the requirement. If
a decisive product rule is missing, record the question instead of inventing the expected result. Check that each AC
in scope has its verification, that the test references its ID and, at level 3 (contracts, identity and permissions,
irreversible data or settings, and integrations) and in Apex and agent logic, that it was written before the
implementation (history). An AC without verification is a finding, not an observation.

Distinguish delivering a component from real integration. If the assignment is only the component, record the limit;
if it requires the full flow, verify its connection from the real entry point, not only through a direct call from a
test.

### Correctness and composition

Choose scenarios according to risk: errors and recovery, repetition/idempotency, missing versus empty data, reverse
transitions, concurrent writes, authorization, migrations and volume. Do not turn this list into a mandatory checklist
for every change.

In persistent state, compare required behaviour, materialized state and reconstruction where they exist. Two paths
producing the same result does not rule out both being wrong. In concurrency, check the effective scope of locks and
transactions, not just their presence. For performance, show how the work grows with the input and which real path
triggers it.

Look for consequences beyond the diff. Label the defect as introduced, pre-existing that affects the scope, or an
improvement unrelated to the assignment. Do not attribute a pre-existing defect to the change without comparing; do
report it if it prevents acceptance under the project's rules.

### Tests and oracles

Check that the assertions detect the relevant failure and that mocks, fixtures and adapters represent the contract.
Review changes to expectations, goldens, skips, xfail, filters and exemptions. Investigate whether a normalization
loses significant differences, whether a comparison only covers one direction, or whether a matching allows many
elements against one when it must be bijective.

Do not accept deleting scenarios, widening exemptions or adding xfail as the fix for a defect the contract requires. A
legitimate contract change needs its corresponding decision and acceptance. Do not demand trivial new tests for
low-impact changes: ask for evidence proportionate to the risk.

### Requirements quality (if the candidate is a spec)

- Each requirement has at least one AC, and each AC is falsifiable: stimulus, result and where it is checked.
- The AC cover the errors, rejections and denied permissions that matter, not only the happy path.
- The requirements do not prescribe implementation that the customer does not impose.
- They are consistent with the `Active` decisions and with the sources cited.
- Each `[PENDING]` is linked to `questions.md`.
- Each contract in the design cites the requirements it satisfies, and no requirement is left without a contract or an
  exclusion.

## From hypothesis to finding

1. Formulate a reachable scenario, the invariant violated and a concrete consequence.
2. Look for mechanisms that could refute it: prior validation, filtering, constraints, compensation, consumers that
   change the interpretation.
3. Confirm it with a sufficiently concrete static walkthrough or a minimal reproduction. Label unverified conditions;
   a suspicion without support is not a confirmed defect.
4. For relevant behavioural bugs, favour a regression test that fails on the defective candidate and passes with the
   fix, plus neighbouring controls when they add value. The base before the change does not always contain the bug.
5. Use an isolated environment, synthetic data and authorized commands. Do not change the candidate or run against
   production merely for the sake of reviewing. Document dependencies that prevented reproduction.

Keep commands, directory, relevant environment, results and minimal snippets of sanitized evidence. A suite the author
says they ran is labelled as such until you consult its verifiable result; reading a test is never the same as running
it.

## Reviewing the fix

Review the corrective diff and the adjacent paths. Check whether the case fails before and passes after, or explain why
static evidence was enough. If the author refutes, verify their premises; do not force a change to correct code just
to close a comment.

When integrating, recheck the affected contracts against the current base. If two changes were correct in isolation
but not together, open the composition finding and block the affected dependants. Keep the earlier evidence as
historical.
