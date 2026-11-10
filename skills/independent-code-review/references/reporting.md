# Reports, states and gate

Respect the existing format. If there is none, use `reviews/<change-id>/round-01.md` and successive rounds. For
automation, a `review.json` can be added as a derived view of the current state; do not keep two diverging sources of
truth. Keep previous rounds and link later corrections. There is no need to create one file per field.

In an sdd project, write the review in `method.language` of `sdd.config.json` (if it is not set, in the user's
language); the template's field names, IDs, states and verdicts stay exactly as they are (rule M-10).

## Review record

```text
Change / round / date:
Mode and directory:
Author / reviewer / integrator (known identities only):
Independence: independent | self-review; limitations:
Base for attribution / target for composition:
Candidate: commit + local differences, or snapshot/manifest:
Objective, scope and exclusions:
AC in scope and their verification (IDs):
Spec, active decisions and gotchas consulted:
Paths and contracts examined, including consumers beyond the diff:
Required checks and the source of that obligation:
Evidence: command/inspection, content, result, location and who ran it:
Areas not verified and their effect on the conclusion:
Findings: new IDs and state of the previous ones:
Verdict and justification:
Next action, owner and condition to resume:
```

For each check, distinguish `passed`, `failed`, `not_run`, `unavailable` and a justified `not_applicable`. A skipped
test is not a passed test; assess skips against the agreed gate. State the result and its scope: a partial suite does
not represent the full suite.

## Actionable finding

```text
Stable ID: F-001
Title: concrete consequence
Severity per the project / impact:
Classification: introduced | relevant pre-existing | out of scope
Content and file/location (lines only if verified):
Scenario and triggering conditions:
Expected / observed:
Relevant contract or requirement:
Evidence: static | run by the reviewer | provided by a third party
Walkthrough or reproduction / result / artifact:
State / author's response / reviewer's revalidation:
```

Use the existing severity scale. If there is none, classify by impact: critical, high, medium, low. Keep severity
separate from confidence and from whether it blocks. Define the latter from the policy or the criteria of the
assignment; an unmet acceptance requirement does not become optional by being labelled low. Group symptoms with the
same cause; do not multiply comments to give an appearance of coverage.

### Finding lifecycle

- `open`: confirmed and awaiting a response or a fix.
- `fix_proposed`: the author claims it is fixed; awaiting verification.
- `dispute_pending`: there is a refutation or disagreement not yet assessed.
- `closed_fixed`: the reviewer verified the fix on identified content.
- `closed_refuted`: the reviewer verified evidence that invalidates the finding.
- `deferred`: follow-up accepted by whoever has the authority, with a reason and a reference. It does not mean fixed
  and does not allow skipping a mandatory requirement.

The author does not unilaterally declare an independent closure. A resolved thread or a commit with a fix-like title
is not sufficient evidence. Keep the same ID across rounds; if it reappears, reopen it and record the new content.
Correct false positives without deleting the history.

## Review verdict and readiness to integrate

| Verdict | Condition |
|---|---|
| `changes_required` | There is at least one confirmed defect that blocks acceptance. It may coexist with areas not yet verified, which are declared. |
| `incomplete` | There is no confirmed blocker that determines the verdict, but material evidence or context is missing to conclude, or the required independence was not met. |
| `no_blocking_findings` | The review scope was completed and no blocking findings remain open. There may be non-blocking observations and explicit limits. It does not guarantee the absence of defects. |

The verdict does not replace the integration gate. For example, a complete reading can yield `no_blocking_findings`
while the gate is still pending because a mandatory check was not run. If that run was needed to resolve a material
hypothesis of the review itself, the verdict is `incomplete`.

Before declaring **ready to integrate**, the integrator checks all of the following together:

1. The current identity of the candidate and the base for composition; evidence that applies to the final content.
2. The review completed, with independence if required, and all blocking findings closed with evidence.
3. All required checks present and passed; exceptions only where the policy allows them and there is a recorded
   authority.
4. Fixes that do not degrade the oracles or hide errors through unjustified filters, skips or changes of
   expectations.
5. Composition and acceptance of the scope verified, including the real wiring where required: every AC in scope with
   its verification `passed` or with an authorized exception, and the traceability check without gaps.
6. Affected decisions, gotchas and contracts updated when there is a learning or a legitimate change.

Actual integration also requires verifying the incorporated result. If an operation is interrupted, inspect the state
before repeating it. An exhausted budget, the reviewer's silence or a tool failure is not an approval.
