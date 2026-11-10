# Common brief for author sessions

The orchestrator sends each author session this brief plus the individual assignment below. The rules of the
`sdd-method` skill and the project's `CLAUDE.md` still apply; this does not replace them.

## Common rules
1. **Read before touching anything:**
   - the project's `CLAUDE.md`;
   - your step in `docs/delivery-plan/implementation/` and its rows in `docs/delivery-plan/traceability.md`: the
     "Verification" column says what evidence your step builds for each AC;
   - the sections of the spec that the step cites (requirements with their AC, and the design);
   - the `Active` decisions and the gotchas that the step cites.
2. **Your scope is the folders and prefixes of your step** (`docs/delivery-plan/integration.md`). Do not edit shared
   files (permission sets, profiles, dispatchers, CMDT, FlexiPages…): request the change in your step report, as a
   patch. Do not change a frozen contract: propose the change.
3. **Test first** where the step says so (level 3 and Apex and agent logic):
   - first commit: the tests for the AC (with a stub if they do not compile without one) and the **verification
     cases** of your step report, `docs/delivery-plan/step-reports/<step>.md`, under the heading
     `## Verification cases`: for each demo, record, preview or manual-test AC, the stimulus, the expected result and
     where it is checked;
   - second commit: the implementation;
   - each test cites its AC, in the method name or in a comment (`// AC-<AREA>-01.2`), in the classes named in the
     `Test first` of your step;
   - a test does not reproduce the code's logic: its oracle is the result that the AC asks for.
4. **Do not deploy.** Only the integrator deploys. You may run, with an explicit `--target-org <org_alias>`, the
   dry-run with the same scope and test level as the deployment
   (`sf project deploy start --dry-run --source-dir <paths> --test-level RunSpecifiedTests --tests <classes> --target-org <org_alias> --json`),
   Jest and the local tests, and `sf agent validate`.
5. **Always:** `--json` in `sf`; explicit access mode in Apex; no personal data in logs, errors or responses;
   synthetic data only.
6. **Temporary files:** only in a subfolder of the scratch area named with your step's ID.
7. **Nothing external:** no Slack, no Support, no customer. If you are blocked by something only the orchestrator or
   the approver knows, ask it in a single message and stop.
8. **If a product rule is not in the spec,** do not invent it: record it as a question in your step report. You may
   take a reversible assumption within the design, marking it as such.
9. **Do not write `status.md`:** return your status to the orchestrator.

## What you return (step report, in `docs/delivery-plan/step-reports/<step>.md`)
- Branch, commits and diff against `main`.
- The verification cases, with their local result when they can be run without deploying.
- AC covered, with their verification and their local result.
- Output of the traceability check with `--step <step> --no-review` (`sdd-method` skill).
- Result of the dry-run, of Jest and of `sf agent validate`, depending on the step.
- Changes you request in shared files (as a patch) or in contracts.
- Assumptions taken, open questions and what is left out.
- Knowledge: new decisions or gotchas you propose (with their evidence), or "no new learning".

## Individual assignment template

```text
Implement [W<n>.<m> — outcome] in your worktree, branch w<n>/<n>.<m>-<slug>, from main at [commit].
Mode: local Git with no remote.
Read the common brief (sdd-method skill, references/author-brief.md), your step in
docs/delivery-plan/implementation/[file] and spec [number] in [sections]. Decisions: [IDs]. Gotchas: [slugs].
Change level: [0/1/2/3]. Queue entry, if it is a change request: [CH-NNN].
Document language: [method.language in sdd.config.json, or the user's language]. Write the prose in it; headings,
fields, IDs, tags and file names stay as in the project's templates (rule M-10).
Your scope: [folders and prefixes]. Do not edit: [the shared files at this moment].
Dependencies available in main: [steps and commits]; frozen contracts: [contracts with their version].
AC you must satisfy: [IDs and verification, according to traceability.md]; tests you write first: [classes and cases].
Execution skill: [the step's, which is in docs/baseline/environment.json].
Your step report: docs/delivery-plan/step-reports/[step].md, with the verification cases in the first commit.
Local validation: dry-run with --source-dir and --target-org [org_alias], [Jest / sf agent validate], and the
traceability check with --step [step] --no-review.
Review: [planned reviewer] on your final commit[, and the second security perspective].
Allowed assumptions: [...]. Decisions you must escalate: [...].
Return the step report of the common brief. The orchestrator does the merge.
```
