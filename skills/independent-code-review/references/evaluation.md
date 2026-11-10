# Evaluating effectiveness before replacing a reviewer

Use this protocol when asked to evaluate or adopt the capability. Creating the skill does not authorize starting an
expensive benchmark, publishing reviews or changing gates. Adapt size and cost to the project; leave the pilot as a
proposal if it has not been run yet.

## Retrospective corpus

As a starting point, select 10–15 heterogeneous changes: known bugs, changes with no known defects, adjudicated false
positives, effects beyond the diff and weak oracles. Separate the cases used to improve the method from the cases
held back for evaluation. Do not describe a change as bug-free just because its history contains none.

Give the reviewer the candidate as it was before the fix, its base and only the spec/knowledge available at that
time. Hide diagnoses, other reviewers' comments, the solution and later corrective tests. Isolate branches, indexes,
future history and documentation that could reveal the answer. If you cannot avoid that contamination, declare it and
do not present the test as blind.

An adjudicator other than whoever raised the finding checks its validity with evidence; the historical catalog is
incomplete and may be extended with new defects. Do not use the author's acceptance or word matching as technical
truth.

## Prospective pilot

Propose reviewing ten new changes in parallel with the current mechanism, on the same content. Both reviewers deliver
their first review without seeing the other's; then the findings are compared, adjudicated and corrected. Keep the
current rules in force during the pilot. These numbers are a practical start, not a statistical equivalence
threshold.

Measure by risk and severity:

- Known defects detected / known defects that can be evaluated; this is not recall over every possible bug.
- Valid findings and adjudicated false positives; keep unresolved ones separate and report their denominators.
- New confirmed defects, escapes discovered later and oracle failures detected.
- Rounds to closure, reviewer time and total delivery time.
- Execution/model cost, human validation time and context maintenance.

Set adoption criteria before looking at the results: tolerance for serious omissions, false positives and cost. For
example, no known serious defect missed in the held-back corpus can be an initial target, without reading it as a
guarantee in production. If the results only support certain areas, adopt in a limited or hybrid way.

Deliver the corpus and the identified reviews, the adjudication method, metrics with denominators, limitations and a
recommendation. Changing the mandatory policy requires the corresponding authorization; a good result does not by
itself change the gate.
