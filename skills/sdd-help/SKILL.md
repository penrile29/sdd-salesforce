---
name: sdd-help
description: "Explains the sdd-salesforce plugin to someone who has just installed it or wants to use it: what it is, what it installs and what it creates in a project, how to use it in a simple or a complex POC, good practices of spec-driven development in Salesforce and where the guide and the map are. Use it when they ask what sdd-salesforce is, how to get started, what the plugin does, how to apply SDD in Salesforce, or ask for help with the method."
---

# sdd-help

Answer what they ask, in a few lines, and offer the rest. If they do not know where to start, tell them "What it is"
and "How to use it" first. The method's operational rules are not here: they are in the `sdd-method` skill.

## What it is

`sdd-salesforce` applies **spec-driven development with agents** to Salesforce projects (demos, POCs, RFPs): before
building, a spec with requirements and verifiable acceptance criteria is agreed; then the work is planned, built step
by step with tests, an independent review checks each step and a script checks that nothing is left unverified. The
approver (whoever answers to the client) gives the OK at the points that change the product. After the first design,
every change follows its own path so that the spec keeps describing the system.

## What it installs

**In Claude Code**, when the plugin is installed:
- **Skills:** `sdd-method` (the method's rules and scripts), `sdd-bootstrap` (bootstrapping a project),
  `implementation-integration-plan` (discovery, plan and integration), `independent-code-review` (review with a
  separate context), `create-spec`, `create-decision`, `create-gotcha`, `read-knowledge` and this one, `sdd-help`.
- **Hooks:** when a session starts in a method project (or at its first message, if the project was bootstrapped in
  it), they inject its rules and the project's data; before each command, they stop an `sf` command from touching any
  org other than the project's and ask for confirmation before publishing or activating an agent.
- **Scripts:** the environment verification (skills, tools and the org's API) and the traceability check.

**It does not install**, and the method needs them: the sf-skills (`forcedotcom/sf-skills`), the ADLC plugin
(`agentforce-adlc`) if there are Agentforce agents, Salesforce CLI (`sf`), `git` and `python3`. The environment
verification says what is missing.

**In each project**, only when it is bootstrapped with `sdd-bootstrap` (about 20 files): a short `CLAUDE.md` with the
org, the approver, the autonomy and confidentiality; `sdd.config.json`; `knowledge/` (discovery, specs, decisions,
with adoption decision 001, and gotchas); `docs/delivery-plan/` (status with the change queue, handover, questions,
delivery plan, integration and traceability); `docs/baseline/`, `docs/client/` (outside git) and `reviews/`; and
local git.

## How to use it

Everything is asked for by talking; whoever uses the method does not need to know the names of the skills.

1. **Create the project** with `sf project generate` (or an empty folder) and open Claude Code inside it. Each POC in
   its own folder, with its own git and its own org.
2. **Bootstrap it:** say what you want ("I want to set up a Salesforce POC for Acme") and answer the interview
   (client, org alias, approver, autonomy, areas, confidentiality, channels and, if it is not clear, the language of
   the documents).
3. **Prepare the environment**, in the same session: log in to the org (`sf org login web --alias <org>`) and put the
   client's sources in `docs/client/`.
4. **Say "start".** Claude will follow the cycle: **Plan** (verifies the environment and does the discovery) →
   **Design** (spec with requirements and AC, decisions, delivery plan and its review) → **Execution** (one step at a
   time, tests first where they apply, independent review) → **Review** (integration in the org and release). It
   stops at each gate to wait for your OK ("I approve"). To resume in another session, ask "where are we?".
5. **After the first design,** describe any change ("change this AC", "there is a bug in…"): it enters the change
   queue with its level, from 0 (bug) to 3 (contract or risk), and the spec is updated before the code.

- **Simple POC:** one or two waves, level 1 or 2 steps, one session that writes and a subagent that reviews.
- **Complex POC:** an orchestrator that hands out steps to author sessions on their own branches, with separate
  reviewers; the method brings the orchestrator template and the authors' brief.

Claude answers in your language. The project's documents are written in the language set at bootstrap
(`method.language` in `sdd.config.json`) or, if it is not set, in yours; the headings and fields the checks read stay
in English.

## Good practices of SDD in Salesforce

1. **Requirements and acceptance criteria before the design.** Each AC states the stimulus, the observable result and
   where it is checked, and includes the errors and denied permissions that matter. What cannot be checked is not an
   AC.
2. **Each kind of piece, its own test.** Apex with its test (and `runAs` for permissions); the agent, with
   `sf agent test` and the preview with traces; LWC with Jest; Flows, OmniScripts and sites, with a verification case
   in the step report.
3. **Check every decision against the platform, not only against the client's design:** the area's sf-skills and the
   official documentation. Whatever is not documented is tested with a spike in the org before building on top of it.
4. **Contracts first.** Objects, fields, permissions and shared metadata are deployed and frozen before whatever
   consumes them; changing them later is a step of its own.
5. **The org is the integration base and is not forked:** branches work locally, deployments go one at a time, with a
   dry run first, and every command carries the alias of the POC's org (the default org may belong to another
   client).
6. **Agents, draft-first:** validate and test in preview before publishing; publishing does not activate, and both
   are the release.
7. **What happens outside the code counts too:** changes in Setup, permissions that Support enables or changes through
   the API are recorded with their evidence and, if they are metadata, brought back with a retrieve.
8. **Synthetic data only** in the demo org, and the client's sources outside git, cited by document and page.
9. **The reviewer is not the author:** a review with a separate context on a specific commit; a self-review approves
   nothing.
10. **Nothing important lives only in a conversation:** decisions, gotchas and status go into files, so that a new
    session can pick up the work cold.
11. **The spec stays alive:** after the design, every change to a requirement or AC leaves its trace in the spec, and
    the ceremony matches the risk (a wording tweak is not treated like a change of permissions).
12. **Demo orgs expire:** the plan is made against that date.

## Where to read more

- **The method guide for the team:** `${CLAUDE_PLUGIN_ROOT}/GUIDE.md`.
- **Interactive map** of the files, the stages and the skills: `${CLAUDE_PLUGIN_ROOT}/MAP.html`. Offer to open it
  (on macOS, `open "${CLAUDE_PLUGIN_ROOT}/MAP.html"`).
- **Installation, requirements and several POCs on the same machine:** `${CLAUDE_PLUGIN_ROOT}/README.md`; the changes
  in each version, `${CLAUDE_PLUGIN_ROOT}/CHANGELOG.md`.
- **The method's rules, in full:** the `sdd-method` skill.
