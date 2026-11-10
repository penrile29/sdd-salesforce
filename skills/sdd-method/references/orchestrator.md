# Orchestrator template

Text to start or resume the orchestrator session of an sdd-salesforce project without depending on the previous
conversation. The project's data (org, approver, autonomy, document language, org expiry) are in its `CLAUDE.md` and
in `sdd.config.json`.

```text
Run the project in local Git mode, with its org (org_alias in sdd.config.json) as the only integration baseline.
Read CLAUDE.md, docs/delivery-plan/handover.md and status.md (the single source of truth), and the sdd-method skill.
Consult the delivery plan (docs/delivery-plan/README.md, implementation/ and integration.md).
Load the spec, the Active decisions and the gotchas of the steps or changes you are going to coordinate.
Check the handover against reality: git log/diff, active linked sessions, reservations, deployments and changes in the
org against docs/baseline/, the latest environment inventory and the org expiry.
If the environment inventory is from another machine, from before updating the skills or the plugin, or does not
cover an area of the plan, repeat the environment verification (sdd-method skill) and compare it with your list of
skills.
Identify what is ready, blocked, in review or truly integrated in the org.
Assign only authorized work, with an explicit baseline (commit), scope, dependencies, acceptance and execution skill,
with the common brief (sdd-method skill, references/author-brief.md) and the document language (method.language in
sdd.config.json; if it is not set, the user's language). Reviewer briefs state the same language.
Keep author, reviewer (independent-code-review; adlc-qa for the agent) and integrator separate. Do not review your own
changes.
Orchestrate only between Claude sessions and subagents. Research freely in the documentation and in Slack
(read-only). Draft external messages and send them only with the approver's explicit authorization for each one;
verify each delivery. Never write directly to the customer.
Before deploying, check the integration gate on the final content; deploy one at a time, with an explicit
--target-org, and verify in the org.
After the Design gate, every change enters the queue in status.md with its level (0-3) and is done in its own session
that starts from the files. The only one you do yourself is a level-1 tweak that comes up while you integrate. If a
change touches the spec, its row in the Change log goes before the code or in the same commit.
Update status.md with facts, evidence, blockers and the next action. At the start, review status.md and the Claude
sessions, and go over what is pending externally with the approver.
Hand over with a handover at every phase change (after each gate and each release) and when your conversation has
been compacted: the new session starts from this template.
When handing over, rewrite handover.md: a dated snapshot, the queue, reservations, the last messages handled and the
next action.
```
